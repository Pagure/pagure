#!/usr/bin/env python

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>


This server listens to message sent via redis and send the corresponding
web-hook request.

Using this mechanism, we no longer block the main application if the
receiving end is offline or so.

"""

import datetime
import hashlib
import hmac
import json
import logging
import os
import requests
import time
import uuid

import six
import trollius
import trollius_redis

from kitchen.text.converters import to_bytes


log = logging.getLogger(__name__)


if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    print 'Using configuration file `/etc/pagure/pagure.cfg`'
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure
import pagure.lib
from pagure.exceptions import PagureEvException

_i = 0


def call_web_hooks(project, topic, msg, urls):
    ''' Sends the web-hook notification. '''
    log.info(
        "Processing project: %s - topic: %s", project.fullname, topic)
    log.debug('msg: %s', msg)

    # Send web-hooks notification
    global _i
    _i += 1
    year = datetime.datetime.now().year
    if isinstance(topic, six.text_type):
        topic = to_bytes(topic, encoding='utf8', nonstring="passthru")
    msg['pagure_instance'] = pagure.APP.config['APP_URL']
    msg['project_fullname'] = project.fullname
    msg = dict(
        topic=topic.decode('utf-8'),
        msg=msg,
        timestamp=int(time.time()),
        msg_id=str(year) + '-' + str(uuid.uuid4()),
        i=_i,
    )

    content = json.dumps(msg)
    hashhex = hmac.new(
        str(project.hook_token), content, hashlib.sha1).hexdigest()
    hashhex256 = hmac.new(
        str(project.hook_token), content, hashlib.sha256).hexdigest()
    headers = {
        'X-Pagure': pagure.APP.config['APP_URL'],
        'X-Pagure-project': project.fullname,
        'X-Pagure-Signature': hashhex,
        'X-Pagure-Signature-256': hashhex256,
        'X-Pagure-Topic': topic,
        'Content-Type': 'application/json',
    }
    for url in urls:
        url = url.strip()
        log.info('Calling url %s' % url)
        try:
            req = requests.post(
                url,
                headers=headers,
                data=content,
                timeout=60,
            )
            if not req:
                log.info(
                    'An error occured while querying: %s - '
                    'Error code: %s' % (url, req.status_code))
        except (requests.exceptions.RequestException, Exception) as err:
            log.info(
                'An error occured while querying: %s - Error: %s' % (
                    url, err))


@trollius.coroutine
def handle_messages():
    host = pagure.APP.config.get('REDIS_HOST', '0.0.0.0')
    port = pagure.APP.config.get('REDIS_PORT', 6379)
    dbname = pagure.APP.config.get('REDIS_DB', 0)
    connection = yield trollius.From(trollius_redis.Connection.create(
        host=host, port=port, db=dbname))

    # Create subscriber.
    subscriber = yield trollius.From(connection.start_subscribe())

    # Subscribe to channel.
    yield trollius.From(subscriber.subscribe(['pagure.hook']))

    # Inside a while loop, wait for incoming events.
    while True:
        reply = yield trollius.From(subscriber.next_published())
        log.info(
            'Received: %s on channel: %s',
            repr(reply.value), reply.channel)
        data = json.loads(reply.value)
        username = None
        if data['project'].startswith('forks'):
            username, projectname = data['project'].split('/', 2)[1:]
        else:
            projectname = data['project']

        namespace = None
        if '/' in projectname:
            namespace, projectname = projectname.split('/', 1)

        log.info(
            'Searching %s/%s/%s' % (username, namespace, projectname))
        session = pagure.lib.create_session(pagure.APP.config['DB_URL'])
        project = pagure.lib._get_project(
            session=session, name=projectname, user=username,
            namespace=namespace,
            case=pagure.APP.config.get('CASE_SENSITIVE', False))
        if not project:
            log.info('No project found with these criteria')
            session.close()
            continue
        urls = project.settings.get('Web-hooks')
        session.close()
        if not urls:
            log.info('No URLs set: %s' % urls)
            continue
        urls = urls.split('\n')
        log.info('Got the project, going to the webhooks')
        call_web_hooks(project, data['topic'], data['msg'], urls)


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
