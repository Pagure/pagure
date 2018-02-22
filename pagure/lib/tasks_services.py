# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import datetime
import hashlib
import hmac
import inspect
import json
import logging
import os
import os.path
import time
import traceback
import uuid

import requests
import six

from celery import Celery
from kitchen.text.converters import to_bytes
from sqlalchemy.exc import SQLAlchemyError

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


@conn.task(queue=pagure_config.get('LOGCOM_CELERY_QUEUE', None), bind=True)
@set_status
def log_commit_send_notifications(
        self, name, commits, abspath, branch, default_branch,
        namespace=None, username=None):
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

    _log.info(
        'Looking for project: %s%s of %s',
        '%s/' % namespace if namespace else '',
        name,
        username)
    project = pagure.lib._get_project(
        session, name, user=username, namespace=namespace,
        case=pagure_config.get('CASE_SENSITIVE', False))

    if not project:
        _log.info('No project found')
        return

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
        _log.exception(err)
        session.rollback()
    finally:
        session.close()


def format_callstack():
    """ Format the callstack to find out the stack trace. """
    ind = 0
    for ind, frame in enumerate(f[0] for f in inspect.stack()):
        if '__name__' not in frame.f_globals:
            continue
        modname = frame.f_globals['__name__'].split('.')[0]
        if modname != "logging":
            break

    def _format_frame(frame):
        """ Format the frame. """
        return '  File "%s", line %i in %s\n    %s' % (frame)

    stack = traceback.extract_stack()
    stack = stack[:-ind]
    return "\n".join([_format_frame(frame) for frame in stack])


def get_files_to_load(title, new_commits_list, abspath):

    _log.info('%s: Retrieve the list of files changed' % title)
    file_list = []
    new_commits_list.reverse()
    n = len(new_commits_list)
    for idx, commit in enumerate(new_commits_list):
        if (idx % 100) == 0:
            _log.info(
                'Loading files change in commits for %s: %s/%s',
                title, idx, n)
        if commit == new_commits_list[0]:
            filenames = pagure.lib.git.read_git_lines(
                ['diff-tree', '--no-commit-id', '--name-only', '-r', '--root',
                    commit], abspath)
        else:
            filenames = pagure.lib.git.read_git_lines(
                ['diff-tree', '--no-commit-id', '--name-only', '-r', commit],
                abspath)
        for line in filenames:
            if line.strip():
                file_list.append(line.strip())

    return file_list


@conn.task(queue=pagure_config.get('LOADJSON_CELERY_QUEUE', None), bind=True)
@set_status
def load_json_commits_to_db(
        self, name, commits, abspath, data_type, agent,
        namespace=None, username=None):
    ''' Loads into the database the specified commits that have been pushed
    to either the tickets or the pull-request repository.

    '''

    if data_type not in ['ticket', 'pull-request']:
        _log.info('Invalid data_type retrieved: %s', data_type)
        return

    session = pagure.lib.create_session(pagure_config['DB_URL'])

    _log.info(
        'Looking for project: %s%s of user: %s',
        '%s/' % namespace if namespace else '',
        name, username)

    project = pagure.lib._get_project(
        session, name, user=username, namespace=namespace,
        case=pagure_config.get('CASE_SENSITIVE', False))

    if not project:
        _log.info('No project found')
        return

    _log.info('Found project: %s', project.fullname)

    _log.info(
        '%s: Processing %s commits in %s', project.fullname,
        len(commits), abspath)

    file_list = set(get_files_to_load(project.fullname, commits, abspath))
    n = len(file_list)
    _log.info('%s files to process' % n)
    mail_body = []

    for idx, filename in enumerate(file_list):
        _log.info(
            'Loading: %s: %s -- %s/%s',
            project.fullname, filename, idx + 1, n)
        tmp = 'Loading: %s -- %s/%s' % (filename, idx + 1, n)
        json_data = None
        data = ''.join(
            pagure.lib.git.read_git_lines(
                ['show', 'HEAD:%s' % filename], abspath))
        if data and not filename.startswith('files/'):
            try:
                json_data = json.loads(data)
            except ValueError:
                pass
        if json_data:
            try:
                if data_type == 'ticket':
                    pagure.lib.git.update_ticket_from_git(
                        session,
                        reponame=name,
                        namespace=namespace,
                        username=username,
                        issue_uid=filename,
                        json_data=json_data,
                        agent=agent,
                    )
                elif data_type == 'pull-request':
                    pagure.lib.git.update_request_from_git(
                        session,
                        reponame=name,
                        namespace=namespace,
                        username=username,
                        request_uid=filename,
                        json_data=json_data,
                    )
                tmp += ' ... ... Done'
            except Exception as err:
                _log.info('data: %s', json_data)
                session.rollback()
                _log.exception(err)
                tmp += ' ... ... FAILED\n'
                tmp += format_callstack()
                break
            finally:
                mail_body.append(tmp)
        else:
            tmp += ' ... ... SKIPPED - No JSON data'
            mail_body.append(tmp)

    try:
        session.commit()
        _log.info(
            'Emailing results for %s to %s', project.fullname, agent)
        try:
            if not agent:
                raise pagure.exceptions.PagureException(
                    'No agent found: %s' % agent)
            user_obj = pagure.lib.get_user(session, agent)
            pagure.lib.notify.send_email(
                '\n'.join(mail_body),
                'Issue import report',
                user_obj.default_email)
        except pagure.exceptions.PagureException as err:
            _log.exception('Could not find user %s' % agent)
    except SQLAlchemyError as err:  # pragma: no cover
        session.rollback()
    finally:
        session.close()
    _log.info('Ready for another')
