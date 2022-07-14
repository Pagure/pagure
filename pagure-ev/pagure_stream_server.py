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

from __future__ import unicode_literals, absolute_import

import logging
import os


import redis
import trololio

from six.moves.urllib.parse import urlparse

log = logging.getLogger(__name__)


if "PAGURE_CONFIG" not in os.environ and os.path.exists(
    "/etc/pagure/pagure.cfg"
):
    print("Using configuration file `/etc/pagure/pagure.cfg`")
    os.environ["PAGURE_CONFIG"] = "/etc/pagure/pagure.cfg"


import pagure  # noqa: E402
import pagure.lib.model_base  # noqa: E402
import pagure.lib.query  # noqa: E402
from pagure.exceptions import PagureException, PagureEvException  # noqa: E402

SERVER = None
SESSION = None
POOL = redis.ConnectionPool(
    host=pagure.config.config["REDIS_HOST"],
    port=pagure.config.config["REDIS_PORT"],
    db=pagure.config.config["REDIS_DB"],
)


def _get_session():
    global SESSION
    if SESSION is None:
        print(pagure.config.config["DB_URL"])
        SESSION = pagure.lib.model_base.create_session(
            pagure.config.config["DB_URL"]
        )

    return SESSION


def _get_issue(repo, objid):
    """Get a Ticket (issue) instance for a given repo (Project) and
    objid (issue number).
    """
    issue = None
    if not repo.settings.get("issue_tracker", True):
        raise PagureEvException("No issue tracker found for this project")

    session = _get_session()
    issue = pagure.lib.query.search_issues(session, repo, issueid=objid)

    if issue is None or issue.project != repo:
        raise PagureEvException("Issue '%s' not found" % objid)

    if issue.private:
        # TODO: find a way to do auth
        raise PagureEvException(
            "This issue is private and you are not allowed to view it"
        )

    return issue


def _get_pull_request(repo, objid):
    """Get a PullRequest instance for a given repo (Project) and objid
    (request number).
    """
    if not repo.settings.get("pull_requests", True):
        raise PagureEvException(
            "No pull-request tracker found for this project"
        )

    session = _get_session()
    request = pagure.lib.query.search_pull_requests(
        session, project_id=repo.id, requestid=objid
    )

    if request is None or request.project != repo:
        raise PagureEvException("Pull-Request '%s' not found" % objid)

    return request


# Dict representing known object types that we handle requests for,
# and the bound functions for getting an object instance from the
# parsed path data. Has to come after the functions it binds
OBJECTS = {"issue": _get_issue, "pull-request": _get_pull_request}


def get_obj_from_path(path):
    """ Return the Ticket or Request object based on the path provided.
    """
    (username, namespace, reponame, objtype, objid) = pagure.utils.parse_path(
        path
    )
    session = _get_session()
    repo = pagure.lib.query.get_authorized_project(
        session, reponame, user=username, namespace=namespace
    )

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
        line = yield trololio.From(
            trololio.asyncio.wait_for(client_reader.readline(), timeout=10.0)
        )
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

    if "/" not in data[1]:
        log.warning("Invalid URL provided: %s" % data[1])
        return

    url = urlparse(data[1])

    try:
        obj = get_obj_from_path(url.path)
    except PagureException as err:
        log.warning(str(err))
        return

    origin = pagure.config.config.get("APP_URL")
    if origin.endswith("/"):
        origin = origin[:-1]

    client_writer.write(
        (
            "HTTP/1.0 200 OK\n"
            "Content-Type: text/event-stream\n"
            "Cache: nocache\n"
            "Connection: keep-alive\n"
            "Access-Control-Allow-Origin: %s\n\n" % origin
        ).encode()
    )

    conn = redis.Redis(connection_pool=POOL)
    subscriber = conn.pubsub(ignore_subscribe_messages=True)

    try:
        subscriber.subscribe("pagure.%s" % obj.uid)

        # Inside a while loop, wait for incoming events.
        oncall = 0
        while True:
            msg = subscriber.get_message()
            if msg is None:
                # Send a ping to see if the client is still alive
                if oncall >= 5:
                    # Only send a ping once every 5 seconds
                    client_writer.write(("event: ping\n\n").encode())
                    oncall = 0
                oncall += 1
                yield trololio.From(client_writer.drain())
                yield trololio.From(trololio.asyncio.sleep(1))
            else:
                log.info("Sending %s", msg["data"])
                client_writer.write(("data: %s\n\n" % msg["data"]).encode())
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
        log.info("Clients: %s", SERVER.active_count)
        client_writer.write(
            ("HTTP/1.0 200 OK\n" "Cache: nocache\n\n").encode()
        )
        client_writer.write(("data: %s\n\n" % SERVER.active_count).encode())
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
        loop = trololio.asyncio.get_event_loop()
        coro = trololio.asyncio.start_server(
            handle_client,
            host=None,
            port=pagure.config.config["EVENTSOURCE_PORT"],
            loop=loop,
        )
        SERVER = loop.run_until_complete(coro)
        log.info(
            "Serving server at {}".format(SERVER.sockets[0].getsockname())
        )
        if pagure.config.config.get("EV_STATS_PORT"):
            stats_coro = trololio.asyncio.start_server(
                stats,
                host=None,
                port=pagure.config.config.get("EV_STATS_PORT"),
                loop=loop,
            )
            stats_server = loop.run_until_complete(stats_coro)
            log.info(
                "Serving stats  at {}".format(
                    stats_server.sockets[0].getsockname()
                )
            )
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
        if pagure.config.config.get("EV_STATS_PORT"):
            stats_server.close()
        log.info("End Connection")
        loop.run_until_complete(SERVER.wait_closed())
        loop.close()
        log.info("End")


if __name__ == "__main__":
    log = logging.getLogger("")
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(module)s:%(lineno)d] %(message)s"
    )

    # setup console logging
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    aslog = logging.getLogger("asyncio")
    aslog.setLevel(logging.DEBUG)

    ch.setFormatter(formatter)
    log.addHandler(ch)
    main()
