#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>


This server listens to message sent via redis post commits and log the
user's activity in the database.

Using this mechanism, we no longer need to block the git push until all the
activity has been logged (which is you push the kernel tree for the first
time can be really time-consuming).

"""

import json
import logging
import os
from sqlalchemy.exc import SQLAlchemyError

import trollius
import trollius_redis


_log = logging.getLogger(__name__)

if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    print 'Using configuration file `/etc/pagure/pagure.cfg`'
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure
import pagure.lib


@trollius.coroutine
def handle_messages():
    ''' Handles connecting to redis and acting upon messages received.
    In this case, it means logging into the DB the commits specified in the
    message for the default repo or sending commit notification emails.

    The currently accepted message format looks like:

    ::

        {
          "project": {
            "name": "foo",
            "namespace": null,
            "parent": null,
            "username": {
              "name": "user"
            }
          },
          "abspath": "/srv/git/repositories/pagure.git",
          "commits": [
            "b7b4059c44d692d7df3227ce58ce01191e5407bd",
            "f8d0899bb6654590ffdef66b539fd3b8cf873b35",
            "9b6fdc48d3edab82d3de28953271ea52b0a96117"
          ],
          "branch": "master",
          "default_branch": "master"
        }

    '''

    host = pagure.APP.config.get('REDIS_HOST', '0.0.0.0')
    port = pagure.APP.config.get('REDIS_PORT', 6379)
    dbname = pagure.APP.config.get('REDIS_DB', 0)
    connection = yield trollius.From(trollius_redis.Connection.create(
        host=host, port=port, db=dbname))

    # Create subscriber.
    subscriber = yield trollius.From(connection.start_subscribe())

    # Subscribe to channel.
    yield trollius.From(subscriber.subscribe(['pagure.logcom']))

    # Inside a while loop, wait for incoming events.
    while True:
        reply = yield trollius.From(subscriber.next_published())
        _log.info(
            'Received: %s on channel: %s',
            repr(reply.value), reply.channel)
        data = json.loads(reply.value)

        commits = data['commits']
        abspath = data['abspath']
        branch = data['branch']
        default_branch = data['default_branch']
        repo = data['project']['name']
        username = data['project']['user']['name'] \
            if data['project']['parent'] else None
        namespace = data['project']['namespace']

        session = pagure.lib.create_session(pagure.APP.config['DB_URL'])

        _log.info('Looking for project: %s%s of %s',
                 '%s/' % namespace if namespace else '',
                 repo, username)
        project = pagure.lib._get_project(
            pagure.SESSION, repo, user=username, namespace=namespace)

        if not project:
            _log.info('No project found')
            continue

        _log.info('Found project: %s', project.fullname)

        _log.info('Processing %s commits in %s', len(commits), abspath)

        # Only log commits when the branch is the default branch
        if branch == default_branch:
            pagure.lib.git.log_commits_to_db(
                session, project, commits, abspath)

        # Notify subscribed users that there are new commits
        pagure.lib.notify.notify_new_commits(
            abspath, project, branch, commits)

        try:
            session.commit()
        except SQLAlchemyError as err:  # pragma: no cover
            session.rollback()
        finally:
            session.close()
        _log.info('Ready for another')


def main():
    ''' Start the main async loop. '''

    try:
        loop = trollius.get_event_loop()
        tasks = [
            trollius.async(handle_messages()),
        ]
        loop.run_until_complete(trollius.wait(tasks))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except trollius.ConnectionResetError:
        pass

    _log.info("End Connection")
    loop.close()
    _log.info("End")


if __name__ == '__main__':
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(module)s:%(lineno)d] %(message)s")

    logging.basicConfig(level=logging.DEBUG)

    # setup console logging
    _log.setLevel(logging.DEBUG)
    shellhandler = logging.StreamHandler()
    shellhandler.setLevel(logging.DEBUG)

    aslog = logging.getLogger("asyncio")
    aslog.setLevel(logging.DEBUG)
    aslog = logging.getLogger("trollius")
    aslog.setLevel(logging.DEBUG)

    shellhandler.setFormatter(formatter)
    _log.addHandler(shellhandler)
    main()
