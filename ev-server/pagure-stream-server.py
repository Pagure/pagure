#!/usr/bin/env python

"""
 (c) 2015 - Copyright Red Hat Inc

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

import datetime
import logging
import os
import urlparse

import trollius
import trollius_redis

log = logging.getLogger(__name__)


if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    print 'Using configuration file `/etc/pagure/pagure.cfg`'
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure
import pagure.lib
from pagure.exceptions import PagureEvException


clients = {}


def get_obj_from_path(path):
    """ Return the Ticket or Request object based on the path provided.
    """
    username = None
    if path.startswith('/fork'):
        username, repo, obj, objid = path.split('/')[2:6]
    else:
        repo, obj, objid = path.split('/')[1:4]

    repo = pagure.lib.get_project(pagure.SESSION, repo, user=username)

    if repo is None:
        raise PagureEvException("Project '%s' not found" % repo)

    output = None
    if obj == 'issue':
        if not repo.settings.get('issue_tracker', True):
            raise PagureEvException("No issue tracker found for this project")

        output = pagure.lib.search_issues(
            pagure.SESSION, repo, issueid=objid)

        if output is None or output.project != repo:
            raise PagureEvException("Issue '%s' not found" % objid)

        if output.private:
            # TODO: find a way to do auth
            raise PagureEvException(
                "This issue is private and you are not allowed to view it")
    else:
        if not repo.settings.get('pull_requests', True):
            raise PagureEvException(
                "No pull-request tracker found for this project")

        output = pagure.lib.search_pull_requests(
            pagure.SESSION, project_id=repo.id, requestid=objid)

        if output is None or output.project != repo:
            raise PagureEvException("Pull-Request '%s' not found" % objid)

    return output


@trollius.coroutine
def handle_client(client_reader, client_writer):
    # give client a chance to respond, timeout after 10 seconds
    data = yield trollius.From(trollius.wait_for(
        client_reader.readline(),
        timeout=10.0))

    if data is None:
        log.warning("Expected ticket uid, received None")
        return

    data = data.decode().rstrip().split()
    log.info("Received %s", data)
    if not data:
        log.warning("No URL provided: %s" % data)
        return

    if not '/' in data[1]:
        log.warning("Invalid URL provided: %s" % data[1])
        return

    url = urlparse.urlsplit(data[1])

    client_writer.write((
        "HTTP/1.0 200 OK\n"
        "Content-Type: text/event-stream\n"
        "Cache: nocache\n"
        "Connection: keep-alive\n"
        "Access-Control-Allow-Origin: *\n\n"
    ).encode())

    try:
        obj = get_obj_from_path(url.path)
    except PagureEvException as err:
        log.warning(err.message)
        return

    try:
        connection = yield trollius.From(trollius_redis.Connection.create(
            host=pagure.APP.config['REDIS_HOST'],
            port=pagure.APP.config['REDIS_PORT'],
            db=pagure.APP.config['REDIS_DB']))

        # Create subscriber.
        subscriber = yield trollius.From(connection.start_subscribe())

        # Subscribe to channel.
        yield trollius.From(subscriber.subscribe([obj.uid]))

        # Inside a while loop, wait for incoming events.
        while True:
            reply = yield trollius.From(subscriber.next_published())
            #print(u'Received: ', repr(reply.value), u'on channel', reply.channel)
            log.info(reply)
            log.info("Sending %s", reply.value)
            client_writer.write(('data: %s\n\n' % reply.value).encode())
            yield trollius.From(client_writer.drain())

    except trollius.ConnectionResetError:
        pass
    finally:
        # Wathever happens, close the connection.
        connection.close()
        client_writer.close()


def main():

    try:
        loop = trollius.get_event_loop()
        coro = trollius.start_server(
            handle_client, host=None, port=8080, loop=loop)
        server = loop.run_until_complete(coro)
        print('Serving on {}'.format(server.sockets[0].getsockname()))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except trollius.ConnectionResetError:
        pass

    # Close the server
    server.close()
    log.info("End Connection")
    loop.run_until_complete(server.wait_closed())
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
