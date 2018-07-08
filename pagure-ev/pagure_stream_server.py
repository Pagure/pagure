#!/usr/bin/env python

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>


Streaming server for pagure's eventsource feature
This server takes messages sent to redis and publish them at the specified
endpoint

To test, run this script and in another terminal
nc localhost 8080
  HELLO

  GET /test/issue/26?foo=bar HTTP/1.1

"""

from __future__ import unicode_literals

import logging
import os


import redis
from trololio import asyncio as trololio

from six.moves.urllib.parse import urlparse

log = logging.getLogger(__name__)


if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    print('Using configuration file `/etc/pagure/pagure.cfg`')
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure  # noqa: E402
import pagure.lib  # noqa: E402
from pagure.exceptions import PagureEvException  # noqa: E402

SERVER = None
SESSION = None
POOL = redis.ConnectionPool(
    host=pagure.config.config['REDIS_HOST'],
    port=pagure.config.config['REDIS_PORT'],
    db=pagure.config.config['REDIS_DB'])


def _get_session():
    global SESSION
    if SESSION is None:
        print(pagure.config.config['DB_URL'])
        SESSION = pagure.lib.create_session(pagure.config.config['DB_URL'])

    return SESSION


def _get_issue(repo, objid):
    """Get a Ticket (issue) instance for a given repo (Project) and
    objid (issue number).
    """
    issue = None
    if not repo.settings.get('issue_tracker', True):
        raise PagureEvException("No issue tracker found for this project")

    session = _get_session()
    issue = pagure.lib.search_issues(session, repo, issueid=objid)

    if issue is None or issue.project != repo:
        raise PagureEvException("Issue '%s' not found" % objid)

    if issue.private:
        # TODO: find a way to do auth
        raise PagureEvException(
            "This issue is private and you are not allowed to view it")

    return issue


def _get_pull_request(repo, objid):
    """Get a PullRequest instance for a given repo (Project) and objid
    (request number).
    """
    if not repo.settings.get('pull_requests', True):
        raise PagureEvException(
            "No pull-request tracker found for this project")

    session = _get_session()
    request = pagure.lib.search_pull_requests(
        session, project_id=repo.id, requestid=objid)

    if request is None or request.project != repo:
        raise PagureEvException("Pull-Request '%s' not found" % objid)

    return request


# Dict representing known object types that we handle requests for,
# and the bound functions for getting an object instance from the
# parsed path data. Has to come after the functions it binds
OBJECTS = {
    'issue': _get_issue,
    'pull-request': _get_pull_request
}


def _parse_path(path):
    """Get the repo name, object type, object ID, and (if present)
    username and/or namespace from a URL path component. Will only
    handle the known object types from the OBJECTS dict. Assumes:
    * Project name comes immediately before object type
    * Object ID comes immediately after object type
    * If a fork, path starts with /fork/(username)
    * Namespace, if present, comes after fork username (if present) or at start
    * No other components come before the project name
    * None of the parsed items can contain a /
    """
    username = None
    namespace = None
    # path always starts with / so split and throw away first item
    items = path.split('/')[1:]
    # find the *last* match for any object type
    try:
        objtype = [item for item in items if item in OBJECTS][-1]
    except IndexError:
        raise PagureEvException(
            "No known object type found in path: %s" % path)
    try:
        # objid is the item after objtype, we need all items up to it
        items = items[:items.index(objtype) + 2]
        # now strip the repo, objtype and objid off the end
        (repo, objtype, objid) = items[-3:]
        items = items[:-3]
    except (IndexError, ValueError):
        raise PagureEvException(
            "No project or object ID found in path: %s" % path)
    # now check for a fork
    if items and items[0] == 'fork':
        try:
            # get the username and strip it and 'fork'
            username = items[1]
            items = items[2:]
        except IndexError:
            raise PagureEvException(
                "Path starts with /fork but no user found! Path: %s" % path)
    # if we still have an item left, it must be the namespace
    if items:
        namespace = items.pop(0)
    # if we have any items left at this point, we've no idea
    if items:
        raise PagureEvException(
            "More path components than expected! Path: %s" % path)

    return username, namespace, repo, objtype, objid


def get_obj_from_path(path):
    """ Return the Ticket or Request object based on the path provided.
    """
    (username, namespace, reponame, objtype, objid) = _parse_path(path)
    session = _get_session()
    repo = pagure.lib.get_authorized_project(
            session, reponame, user=username, namespace=namespace)

    if repo is None:
        raise PagureEvException("Project '%s' not found" % reponame)

    # find the appropriate object getter function from OBJECTS
    try:
        getfunc = OBJECTS[objtype]
    except KeyError:
        raise PagureEvException("Invalid object provided: '%s'" % objtype)

    return getfunc(repo, objid)


@trololio.coroutine
def handle_client(client_reader, client_writer):
    data = None
    while True:
        # give client a chance to respond, timeout after 10 seconds
        line = yield trololio.From(trololio.wait_for(
            client_reader.readline(),
            timeout=10.0))
        if not line.decode().strip():
            break
        line = line.decode().rstrip()
        if data is None:
            data = line

    if data is None:
        log.warning("Expected ticket uid, received None")
        return

    data = data.decode().rstrip().split()
    log.info("Received %s", data)
    if not data:
        log.warning("No URL provided: %s" % data)
        return

    if '/' not in data[1]:
        log.warning("Invalid URL provided: %s" % data[1])
        return

    url = urlparse(data[1])

    try:
        obj = get_obj_from_path(url.path)
    except PagureEvException as err:
        log.warning(err.message)
        return

    origin = pagure.config.config.get('APP_URL')
    if origin.endswith('/'):
        origin = origin[:-1]

    client_writer.write((
        "HTTP/1.0 200 OK\n"
        "Content-Type: text/event-stream\n"
        "Cache: nocache\n"
        "Connection: keep-alive\n"
        "Access-Control-Allow-Origin: %s\n\n" % origin
    ).encode())


    conn = redis.Redis(connection_pool=POOL)
    subscriber = conn.pubsub(ignore_subscribe_messages=True)

    try:
        subscriber.subscribe('pagure.%s' % obj.uid)

        # Inside a while loop, wait for incoming events.
        oncall = 0
        while True:
            msg = subscriber.get_message()
            if msg is None:
                # Send a ping to see if the client is still alive
                if oncall >= 5:
                    # Only send a ping once every 5 seconds
                    client_writer.write(('event: ping\n\n').encode())
                    oncall = 0
                oncall += 1
                yield trololio.From(client_writer.drain())
                yield trololio.From(trololio.sleep(1))
            else:
                log.info("Sending %s", msg['data'])
                client_writer.write(('data: %s\n\n' % msg['data']).encode())
                yield trololio.From(client_writer.drain())

    except OSError:
        log.info("Client closed connection")
    except trololio.ConnectionResetError as err:
        log.exception("ERROR: ConnectionResetError in handle_client")
    except Exception as err:
        log.exception("ERROR: Exception in handle_client")
        log.info(type(err))
    finally:
        # Wathever happens, close the connection.
        log.info("Client left. Goodbye!")
        subscriber.close()
        client_writer.close()


@trololio.coroutine
def stats(client_reader, client_writer):

    try:
        log.info('Clients: %s', SERVER.active_count)
        client_writer.write((
            "HTTP/1.0 200 OK\n"
            "Cache: nocache\n\n"
        ).encode())
        client_writer.write(('data: %s\n\n' % SERVER.active_count).encode())
        yield trololio.From(client_writer.drain())

    except trololio.ConnectionResetError as err:
        log.info(err)
    finally:
        client_writer.close()
    return


def main():
    global SERVER
    _get_session()

    try:
        loop = trololio.get_event_loop()
        coro = trololio.start_server(
            handle_client,
            host=None,
            port=pagure.config.config['EVENTSOURCE_PORT'],
            loop=loop)
        SERVER = loop.run_until_complete(coro)
        log.info(
            'Serving server at {}'.format(SERVER.sockets[0].getsockname()))
        if pagure.config.config.get('EV_STATS_PORT'):
            stats_coro = trololio.start_server(
                stats,
                host=None,
                port=pagure.config.config.get('EV_STATS_PORT'),
                loop=loop)
            stats_server = loop.run_until_complete(stats_coro)
            log.info('Serving stats  at {}'.format(
                stats_server.sockets[0].getsockname()))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except trololio.ConnectionResetError as err:
        log.exception("ERROR: ConnectionResetError in main")
    except Exception:
        log.exception("ERROR: Exception in main")
    finally:
        # Close the server
        SERVER.close()
        if pagure.config.config.get('EV_STATS_PORT'):
            stats_server.close()
        log.info("End Connection")
        loop.run_until_complete(SERVER.wait_closed())
        loop.close()
        log.info("End")


if __name__ == '__main__':
    log = logging.getLogger("")
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(module)s:%(lineno)d] %(message)s")

    # setup console logging
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    aslog = logging.getLogger("asyncio")
    aslog.setLevel(logging.DEBUG)

    ch.setFormatter(formatter)
    log.addHandler(ch)
    main()
