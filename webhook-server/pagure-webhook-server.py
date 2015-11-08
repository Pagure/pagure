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


def call_web_hooks(project, topic, msg):
    ''' Sends the web-hook notification. '''
    log.info("Processing project %s - sending: %s" % (
        project.fullname, topic)
    )
    log.debug('msg: %s' % msg)

    # Send web-hooks notification
    global _i
    _i += 1
    year = datetime.datetime.now().year
    if isinstance(topic, six.text_type):
        topic = to_bytes(topic, encoding='utf8', nonstring="passthru")
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
    headers = {
        'X-Pagure-Topic': topic,
        'X-Pagure-Signature': hashhex
    }
    msg = json.dumps(msg)
    for url in project.settings.get('Web-hooks').split('\n'):
        url = url.strip()
        log.info('Calling url %s' % url)
        try:
            req = requests.post(
                url,
                headers=headers,
                data={'payload': msg}
            )
            if not req:
                raise pagure.exceptions.PagureException(
                    'An error occured while querying: %s - '
                    'Error code: %s' % (url, req.status_code))
        except (requests.exceptions.RequestException, Exception) as err:
            raise pagure.exceptions.PagureException(
                'An error occured while querying: %s - Error: %s' % (
                    url, err))


@trollius.coroutine
def handle_client():
        connection = yield trollius.From(trollius_redis.Connection.create(
            host='0.0.0.0', port=6379, db=0))

        # Create subscriber.
        subscriber = yield trollius.From(connection.start_subscribe())

        # Subscribe to channel.
        yield trollius.From(subscriber.subscribe(['hook']))

        # Inside a while loop, wait for incoming events.
        while True:
            reply = yield trollius.From(subscriber.next_published())
            print(u'Received: ', repr(reply.value), u'on channel', reply.channel)
            data = json.loads(reply.value)
            username = None
            if '/' in data['project']:
                username, projectname = data['project'].split('/', 1)
            else:
                projectname = data['project']
            project = pagure.lib.get_project(
                session=pagure.SESSION, name=projectname, user=username)
            call_web_hooks(project, data['topic'], data['msg'])


def main():
    server = None
    try:
        loop = trollius.get_event_loop()
        tasks = [
            trollius.async(handle_client()),
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
