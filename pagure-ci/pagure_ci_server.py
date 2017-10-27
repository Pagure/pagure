#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>


This server listens to message sent via redis and send the corresponding
web-hook request.

Using this mechanism, we no longer block the main application if the
receiving end is offline or so.

"""

from __future__ import print_function
import json
import logging
import os
import requests

import trollius
import trollius_redis


_log = logging.getLogger(__name__)

if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    print('Using configuration file `/etc/pagure/pagure.cfg`')
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure
import pagure.lib


@trollius.coroutine
def handle_messages():
    ''' Handles connecting to redis and acting upon messages received.
    In this case, it means triggering a build on jenkins based on the
    information provided.
    '''

    host = pagure.APP.config.get('REDIS_HOST', '0.0.0.0')
    port = pagure.APP.config.get('REDIS_PORT', 6379)
    dbname = pagure.APP.config.get('REDIS_DB', 0)
    connection = yield trollius.From(trollius_redis.Connection.create(
        host=host, port=port, db=dbname))

    # Create subscriber.
    subscriber = yield trollius.From(connection.start_subscribe())

    # Subscribe to channel.
    yield trollius.From(subscriber.subscribe(['pagure.ci']))

    # Inside a while loop, wait for incoming events.
    while True:
        reply = yield trollius.From(subscriber.next_published())
        _log.info(
            'Received: %s on channel: %s',
            repr(reply.value), reply.channel)
        data = json.loads(reply.value)

        pr_id = data['pr']['id']
        pr_uid = data['pr']['uid']
        branch = data['pr']['branch_from']
        _log.info('Looking for PR: %s', pr_uid)
        session = pagure.lib.create_session(pagure.APP.config['DB_URL'])
        request = pagure.lib.get_request_by_uid(session, pr_uid)

        _log.info('PR retrieved: %s', request)

        if not request:
            _log.warning(
                'No request could be found from the message %s', data)
            session.close()
            continue

        _log.info(
            "Trigger on %s PR #%s from %s: %s",
            request.project.fullname, pr_id,
            request.project_from.fullname, branch)

        url = request.project.ci_hook.ci_url.rstrip('/')

        if data['ci_type'] == 'jenkins':
            url = url + '/buildWithParameters'
            repo = '%s/%s' % (
                pagure.APP.config['GIT_URL_GIT'].rstrip('/'),
                request.project_from.path)
            _log.info(
                'Triggering the build at: %s, for repo: %s', url, repo)
            try:
                requests.post(
                    url,
                    data={
                        'token': request.project.ci_hook.pagure_ci_token,
                        'cause': pr_id,
                        'REPO': repo,
                        'BRANCH': branch
                    },
                    timeout=60,
                )
            except requests.exceptions.Timeout as err:
                _log.debug('Request timed-out: %s' % err)
        else:
            _log.warning('Un-supported CI type')

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
