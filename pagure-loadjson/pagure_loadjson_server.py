#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>


This server listens to message sent to redis via post commits hook and find
the list of files modified by the commits listed in the message and sync
them into the database.

Using this mechanism, we no longer need to block the git push until all the
files have been uploaded (which when migrating some large projects over to
pagure can be really time-consuming).

"""

import json
import logging
import os
import traceback

import requests
import trollius
import trollius_redis

from sqlalchemy.exc import SQLAlchemyError

_log = logging.getLogger(__name__)

if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    print 'Using configuration file `/etc/pagure/pagure.cfg`'
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure
import pagure.exceptions
import pagure.lib
import pagure.lib.notify


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


@trollius.coroutine
def handle_messages():
    ''' Handles connecting to redis and acting upon messages received.
    In this case, it means logging into the DB the commits specified in the
    message for the specified repo.

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
          "data_type": "ticket",
          "agent": "pingou",
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
    yield trollius.From(subscriber.subscribe(['pagure.loadjson']))

    # Inside a while loop, wait for incoming events.
    while True:
        reply = yield trollius.From(subscriber.next_published())
        _log.info(
            'Received: %s on channel: %s',
            repr(reply.value), reply.channel)
        data = json.loads(reply.value)

        commits = data['commits']
        abspath = data['abspath']
        repo = data['project']['name']
        username = data['project']['username']['name'] \
            if data['project']['parent'] else None
        namespace = data['project']['namespace']
        data_type = data['data_type']
        agent = data['agent']

        if data_type not in ['ticket', 'pull-request']:
            _log.info('Invalid data_type retrieved: %s', data_type)
            continue

        session = pagure.lib.create_session(pagure.APP.config['DB_URL'])

        _log.info('Looking for project: %s%s of user: %s',
                 '%s/' % namespacerepo if namespace else '',
                 repo, username)
        project = pagure.lib.get_project(
            session, repo, user=username, namespace=namespace)

        if not project:
            _log.info('No project found')
            continue

        _log.info('Found project: %s', project.fullname)

        _log.info(
            '%s: Processing %s commits in %s', project.fullname,
            len(commits), abspath)

        file_list = set(get_files_to_load(project.fullname, commits, abspath))
        n = len(file_list)
        _log.info('%s files to process' % n)
        mail_body = []

        for idx, filename in enumerate(file_list):
            _log.info('Loading: %s -- %s/%s', filename, idx+1, n)
            tmp = 'Loading: %s -- %s/%s' % (filename, idx+1, n)
            json_data = None
            data = ''.join(
                pagure.lib.git.read_git_lines(
                    ['show', 'HEAD:%s' % filename], abspath))
            if data and not filename.startswith('files/'):
                try:
                    json_data = json.loads(data)
                except:
                    pass
            if json_data:
                try:
                    if data_type == 'ticket':
                        pagure.lib.git.update_ticket_from_git(
                            session,
                            reponame=repo,
                            namespace=namespace,
                            username=username,
                            issue_uid=filename,
                            json_data=json_data
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

    # Turn down the logs coming from python-markdown
    mklog = logging.getLogger("MARKDOWN")
    mklog.setLevel(logging.WARN)

    shellhandler.setFormatter(formatter)
    _log.addHandler(shellhandler)
    main()
