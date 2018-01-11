# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import datetime
import hashlib
import hmac
import json
import logging
import os
import os.path
import time
import uuid


import pygit2
import requests
import six

from celery import Celery
from kitchen.text.converters import to_bytes

import pagure.lib
from pagure.config import config as pagure_config
from pagure.lib.tasks import set_status

# logging.config.dictConfig(pagure_config.get('LOGGING') or {'version': 1})
_log = logging.getLogger(__name__)
_i = 0


if os.environ.get('PAGURE_BROKER_URL'):
    broker_url = os.environ['PAGURE_BROKER_URL']
elif pagure_config.get('BROKER_URL'):
    broker_url = pagure_config['BROKER_URL']
else:
    broker_url = 'redis://%s' % pagure_config['REDIS_HOST']

conn = Celery('tasks', broker=broker_url, backend=broker_url)
conn.conf.update(pagure_config['CELERY_CONFIG'])


def call_web_hooks(project, topic, msg, urls):
    ''' Sends the web-hook notification. '''
    _log.info(
        "Processing project: %s - topic: %s", project.fullname, topic)
    _log.debug('msg: %s', msg)

    # Send web-hooks notification
    global _i
    _i += 1
    year = datetime.datetime.utcnow().year
    if isinstance(topic, six.text_type):
        topic = to_bytes(topic, encoding='utf8', nonstring="passthru")
    msg['pagure_instance'] = pagure_config['APP_URL']
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
        'X-Pagure': pagure_config['APP_URL'],
        'X-Pagure-project': project.fullname,
        'X-Pagure-Signature': hashhex,
        'X-Pagure-Signature-256': hashhex256,
        'X-Pagure-Topic': topic,
        'Content-Type': 'application/json',
    }
    for url in urls:
        url = url.strip()
        _log.info('Calling url %s' % url)
        try:
            req = requests.post(
                url,
                headers=headers,
                data={'payload': content},
                timeout=60,
            )
            if not req:
                _log.info(
                    'An error occured while querying: %s - '
                    'Error code: %s' % (url, req.status_code))
        except (requests.exceptions.RequestException, Exception) as err:
            _log.info(
                'An error occured while querying: %s - Error: %s' % (
                    url, err))


@conn.task(queue=pagure_config.get('WEBHOOK_CELERY_QUEUE', None), bind=True)
@set_status
def webhook_notification(
        self, topic, msg, namespace=None, name=None, user=None):
    """ Send webhook notifications about an event on that project.

    :arg topic: the topic for the notification
    :type topic: str
    :arg msg: the message to send via web-hook
    :type msg: str
    :kwarg namespace: the namespace of the project
    :type namespace: None or str
    :kwarg name: the name of the project
    :type name: None or str
    :kwarg user: the user of the project, only set if the project is a fork
    :type user: None or str

    """
    session = pagure.lib.create_session(pagure_config['DB_URL'])
    project = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user,
        case=pagure_config.get('CASE_SENSITIVE', False))

    if not project:
        session.close()
        raise RuntimeError(
            'Project: %s/%s from user: %s not found in the DB' % (
                namespace, name, user))

    urls = project.settings.get('Web-hooks')
    if not urls:
        _log.info('No URLs set: %s' % urls)
        return

    urls = urls.split('\n')
    _log.info('Got the project and urls, going to the webhooks')
    call_web_hooks(project, topic, msg, urls)
    session.close()
