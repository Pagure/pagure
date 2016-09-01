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

import json
import logging
import os
import requests

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


@trollius.coroutine
def handle_messages():
    host = pagure.APP.config.get('REDIS_HOST', '0.0.0.0')
    port = pagure.APP.config.get('REDIS_PORT', 6379)
    db = pagure.APP.config.get('REDIS_DB', 0)
    connection = yield trollius.From(trollius_redis.Connection.create(
        host=host, port=port, db=db))

    # Create subscriber.
    subscriber = yield trollius.From(connection.start_subscribe())

    # Subscribe to channel.
    yield trollius.From(subscriber.subscribe(['pagure.ci']))

    # Inside a while loop, wait for incoming events.
    while True:
        reply = yield trollius.From(subscriber.next_published())
        log.info(
            'Received: %s on channel: %s',
            repr(reply.value), reply.channel)
        data = json.loads(reply.value)

        pr_id = data['pr']['id']
        project = data['pr']['project']['name']
        branch = data['pr']['branch_from']

        username = None
        projectname = data['pr']['project']['name']
        if data['pr'].get('parent'):
            username, data['pr']['project']['user']['user']

        project = pagure.lib.get_project(
            session=pagure.SESSION, name=projectname, user=username)

        if not project:
            log.warning(
                'No project could be found from the message %s' % data)
            continue

        repo = data['pr'].get('remote_git')
        if not repo:
            base = pagure.APP.config['APP_URL']
            if base.endswith('/'):
                base[:-1]
            base += '/%s' % project.path

        log.info(
            "Trigger on %s PR #%s from %s: %s",
            project.fullname, pr_id, repo, branch)

        url = project.ci_hook.ci_url.rstrip('/')

        if data['ci_type'] == 'jenkins':
            url = url + '/buildWithParameters'
            log.info('Triggering the build at: %s', url)
            requests.post(
                url,
                data={
                    'token': project.ci_hook.pagure_ci_token,
                    'cause': pr_id,
                    'REPO': project.fullname,
                    'BRANCH': branch
                }
            )
        else:
            log.warning('Un-supported CI type')

        log.info('Ready for another')


def main():
    server = None
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

    log.info("End Connection")
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
