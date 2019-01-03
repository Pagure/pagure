# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import os
import shutil
import sys
import tempfile
import time
import unittest

import pygit2
import six
from mock import ANY, patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib.tasks_services
import pagure.lib.query
import tests

import pagure.lib.tasks_services


class PagureLibTaskServicestests(tests.Modeltests):
    """ Tests for pagure.lib.task_services """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureLibTaskServicestests, self).setUp()

        tests.create_projects(self.session)

        # Create a fork of test for foo
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            is_fork=True,
            parent_id=1,
            description='test project #1',
            hook_token='aaabbbccc_foo',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        self.session.add(item)
        self.session.commit()

    def test_webhook_notification_invalid_project(self):
        """ Test the webhook_notification method. """

        self.assertRaises(
            RuntimeError,
            pagure.lib.tasks_services.webhook_notification,
            topic='topic',
            msg={'payload': ['a', 'b', 'c']},
            namespace=None,
            name='invalid',
            user=None)

    @patch('pagure.lib.tasks_services.call_web_hooks')
    def test_webhook_notification_no_webhook(self, call_wh):
        """ Test the webhook_notification method. """

        output = pagure.lib.tasks_services.webhook_notification(
            topic='topic',
            msg={'payload': ['a', 'b', 'c']},
            namespace=None,
            name='test',
            user=None)
        self.assertIsNone(output)
        call_wh.assert_not_called()

    @patch('pagure.lib.git.log_commits_to_db')
    def test_log_commit_send_notifications_invalid_project(self, log):
        """ Test the log_commit_send_notifications method. """
        output = pagure.lib.tasks_services.log_commit_send_notifications(
            name='invalid',
            commits=[],
            abspath=None,
            branch=None,
            default_branch=None,
            namespace=None,
            username=None)
        self.assertIsNone(output)
        log.assert_not_called()

    @patch('pagure.lib.notify.notify_new_commits')
    @patch('pagure.lib.git.log_commits_to_db')
    def test_log_commit_send_notifications_valid_project(self, log, notif):
        """ Test the log_commit_send_notifications method. """
        output = pagure.lib.tasks_services.log_commit_send_notifications(
            name='test',
            commits=['hash1', 'hash2'],
            abspath='/path/to/git',
            branch='master',
            default_branch='master',
            namespace=None,
            username=None)
        self.assertIsNone(output)
        log.assert_called_once_with(
            ANY, ANY, ['hash1', 'hash2'], '/path/to/git'
        )
        notif.assert_called_once_with(
            '/path/to/git', ANY, 'master', ['hash1', 'hash2']
        )

    @patch('pagure.lib.tasks_services.trigger_jenkins_build')
    def test_trigger_ci_build_invalid_project(self, trigger_jenk):
        """ Test the trigger_ci_build method. """
        output = pagure.lib.tasks_services.trigger_ci_build(
            project_name='invalid',
            cause='PR#ID',
            branch='feature',
            ci_type='jenkins')
        self.assertIsNone(output)
        trigger_jenk.assert_not_called()

    @patch('pagure.lib.tasks_services.trigger_jenkins_build')
    def test_trigger_ci_build_not_configured_project(self, trigger_jenk):
        """ Test the trigger_ci_build method. """
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.tasks_services.trigger_ci_build,
            project_name='test',
            cause='PR#ID',
            branch='feature',
            ci_type='jenkins')
        trigger_jenk.assert_not_called()

    @patch('pagure.lib.tasks_services.trigger_jenkins_build')
    def test_trigger_ci_build_not_configured_project_fork(self, trigger_jenk):
        """ Test the trigger_ci_build method. """
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.tasks_services.trigger_ci_build,
            project_name='forks/foo/test',
            cause='PR#ID',
            branch='feature',
            ci_type='jenkins')
        trigger_jenk.assert_not_called()

    @patch('pagure.lib.query._get_project')
    def test_load_json_commits_to_db_invalid_data_type(self, get_project):
        """ Test the load_json_commits_to_db method. """
        output = pagure.lib.tasks_services.load_json_commits_to_db(
            name='test',
            commits=['hash1', 'hash2'],
            abspath='/path/to/git',
            data_type='invalid',
            agent='pingou',
            namespace=None,
            username=None)
        self.assertIsNone(output)
        get_project.assert_not_called()

    @patch('pagure.lib.tasks_services.get_files_to_load')
    def test_load_json_commits_to_db_invalid_project(self, get_files):
        """ Test the load_json_commits_to_db method. """
        output = pagure.lib.tasks_services.load_json_commits_to_db(
            name='invalid',
            commits=['hash1', 'hash2'],
            abspath='/path/to/git',
            data_type='ticket',
            agent='pingou',
            namespace=None,
            username=None)
        self.assertIsNone(output)
        get_files.assert_not_called()

    @patch('pagure.lib.git.update_request_from_git')
    @patch('pagure.lib.git.update_ticket_from_git')
    def test_load_json_commits_to_db_invalid_path(self, up_issue, up_pr):
        """ Test the load_json_commits_to_db method. """
        output = pagure.lib.tasks_services.load_json_commits_to_db(
            name='test',
            commits=['hash1', 'hash2'],
            abspath=self.path,
            data_type='ticket',
            agent='pingou',
            namespace=None,
            username=None)
        self.assertIsNone(output)
        up_issue.assert_not_called()
        up_pr.assert_not_called()

    @patch('pagure.lib.git.update_request_from_git')
    @patch('pagure.lib.git.update_ticket_from_git')
    def test_load_json_commits_to_db_invalid_path_one_commit(self, up_issue, up_pr):
        """ Test the load_json_commits_to_db method. """
        output = pagure.lib.tasks_services.load_json_commits_to_db(
            name='test',
            commits=['hash1'],
            abspath=self.path,
            data_type='ticket',
            agent='pingou',
            namespace=None,
            username=None)
        self.assertIsNone(output)
        up_issue.assert_not_called()
        up_pr.assert_not_called()

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.lib.git.update_request_from_git')
    @patch('pagure.lib.git.update_ticket_from_git')
    def test_load_json_commits_to_db_no_agent(self, up_issue, up_pr, send):
        """ Test the load_json_commits_to_db method. """
        output = pagure.lib.tasks_services.load_json_commits_to_db(
            name='test',
            commits=[],
            abspath=None,
            data_type='ticket',
            agent=None,
            namespace=None,
            username=None)
        self.assertIsNone(output)
        up_issue.assert_not_called()
        up_pr.assert_not_called()
        send.assert_not_called()

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.lib.git.update_request_from_git')
    @patch('pagure.lib.git.update_ticket_from_git')
    @patch('pagure.lib.git.read_git_lines')
    def test_load_json_commits_to_db_no_agent(
            self, git, up_issue, up_pr, send):
        """ Test the load_json_commits_to_db method. """
        git.side_effect = [
            ['file1'], ['file2'], ['files/image'], ['file1']]

        output = pagure.lib.tasks_services.load_json_commits_to_db(
            name='test',
            commits=['hash1', 'hash2'],
            abspath=self.path,
            data_type='ticket',
            agent=None,
            namespace=None,
            username=None)
        self.assertIsNone(output)
        up_issue.assert_not_called()
        up_pr.assert_not_called()
        send.assert_not_called()

    @patch('json.loads')
    @patch('pagure.lib.notify.send_email')
    @patch('pagure.lib.git.update_request_from_git')
    @patch('pagure.lib.git.update_ticket_from_git')
    @patch('pagure.lib.git.read_git_lines')
    def test_load_json_commits_to_db_tickets(
            self, git, up_issue, up_pr, send, json_loads):
        """ Test the load_json_commits_to_db method. """
        git.side_effect = [
            ['file1'], ['file2'], ['files/image'], ['file1']]
        json_loads.return_value = 'foobar'

        output = pagure.lib.tasks_services.load_json_commits_to_db(
            name='test',
            commits=['hash1', 'hash2'],
            abspath=self.path,
            data_type='ticket',
            agent=None,
            namespace=None,
            username=None)
        self.assertIsNone(output)

        calls = [
            call(
                ANY, agent=None, issue_uid=u'file1', json_data=u'foobar',
                namespace=None, reponame=u'test', username=None
            ),
            call(
                ANY, agent=None, issue_uid=u'file2', json_data=u'foobar',
                namespace=None, reponame=u'test', username=None
            ),
        ]
        self.assertEqual(
            calls,
            up_issue.mock_calls
        )
        up_pr.assert_not_called()
        send.assert_not_called()

    @patch('json.loads')
    @patch('pagure.lib.notify.send_email')
    @patch('pagure.lib.git.update_request_from_git')
    @patch('pagure.lib.git.update_ticket_from_git')
    @patch('pagure.lib.git.read_git_lines')
    def test_load_json_commits_to_db_prs(
            self, git, up_issue, up_pr, send, json_loads):
        """ Test the load_json_commits_to_db method. """
        git.side_effect = [
            ['file1'], ['file2'], ['files/image'], ['file1']]
        json_loads.return_value = 'foobar'

        output = pagure.lib.tasks_services.load_json_commits_to_db(
            name='test',
            commits=['hash1', 'hash2'],
            abspath=self.path,
            data_type='pull-request',
            agent='pingou',
            namespace=None,
            username=None)
        self.assertIsNone(output)

        calls = [
            call(
                ANY, json_data=u'foobar', namespace=None, reponame=u'test',
                request_uid=u'file1', username=None
            ),
            call(
                ANY, json_data=u'foobar', namespace=None, reponame=u'test',
                request_uid=u'file2', username=None
            ),
        ]
        up_issue.assert_not_called()
        self.assertEqual(
            calls,
            up_pr.mock_calls
        )
        calls = [
            call(
                u'Loading: file1 -- 1/2 ... ... Done\n'
                u'Loading: file2 -- 2/2 ... ... Done',
                u'Issue import report',
                u'bar@pingou.com'
            )
        ]
        self.assertEqual(
            calls,
            send.mock_calls
        )

    @patch('json.loads')
    @patch('pagure.lib.notify.send_email')
    @patch('pagure.lib.git.update_request_from_git')
    @patch('pagure.lib.git.update_ticket_from_git')
    @patch('pagure.lib.git.read_git_lines')
    def test_load_json_commits_to_db_prs_raises_error(
            self, git, up_issue, up_pr, send, json_loads):
        """ Test the load_json_commits_to_db method. """
        git.side_effect = [
            ['file1'], ['file2'], ['files/image'], ['file1']]
        json_loads.return_value = 'foobar'
        up_pr.side_effect = Exception('foo error')

        output = pagure.lib.tasks_services.load_json_commits_to_db(
            name='test',
            commits=['hash1', 'hash2'],
            abspath=self.path,
            data_type='pull-request',
            agent='pingou',
            namespace=None,
            username=None)
        self.assertIsNone(output)

        calls = [
            call(
                ANY, json_data=u'foobar', namespace=None, reponame=u'test',
                request_uid=u'file1', username=None
            )
        ]
        up_issue.assert_not_called()
        self.assertEqual(
            calls,
            up_pr.mock_calls
        )

        calls = [
            call(
                u'Loading: file1 -- 1/2 ... ... FAILED\n',
                u'Issue import report',
                u'bar@pingou.com'
            )
        ]
        self.assertEqual(
            calls,
            send.mock_calls
        )


class PagureLibTaskServicesWithWebHooktests(tests.Modeltests):
    """ Tests for pagure.lib.task_services """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureLibTaskServicesWithWebHooktests, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None
        self.sshkeydir = os.path.join(self.path, 'sshkeys')
        pagure.config.config['MIRROR_SSHKEYS_FOLDER'] = self.sshkeydir

        tests.create_projects(self.session)
        project = pagure.lib.query._get_project(self.session, 'test')
        settings = project.settings
        settings['Web-hooks'] = 'http://foo.com/api/flag\nhttp://bar.org/bar'
        project.settings = settings
        self.session.add(project)
        self.session.commit()

    @patch('pagure.lib.tasks_services.call_web_hooks')
    def test_webhook_notification_no_webhook(self, call_wh):
        """ Test the webhook_notification method. """

        output = pagure.lib.tasks_services.webhook_notification(
            topic='topic',
            msg={'payload': ['a', 'b', 'c']},
            namespace=None,
            name='test',
            user=None)
        self.assertIsNone(output)

        project = pagure.lib.query._get_project(self.session, 'test')
        call_wh.assert_called_once_with(
            ANY, u'topic', {u'payload': [u'a', u'b', u'c']},
            [u'http://foo.com/api/flag', u'http://bar.org/bar']
        )

    @patch('time.time', MagicMock(return_value=2))
    @patch('uuid.uuid4', MagicMock(return_value='not_so_random'))
    @patch('datetime.datetime')
    @patch('requests.post')
    def test_webhook_notification_no_webhook(self, post, dt):
        """ Test the webhook_notification method. """
        post.return_value = False
        utcnow = MagicMock()
        utcnow.year = 2018
        dt.utcnow.return_value = utcnow

        output = pagure.lib.tasks_services.webhook_notification(
            topic='topic',
            msg={'payload': ['a', 'b', 'c']},
            namespace=None,
            name='test',
            user=None)
        self.assertIsNone(output)

        project = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(post.call_count, 2)

        calls = [
            call(
                'http://bar.org/bar',
                data='{'
                        '"i": 1, '
                        '"msg": {'
                            '"pagure_instance": "http://localhost.localdomain/", '
                            '"payload": ["a", "b", "c"], '
                            '"project_fullname": "test"}, '
                        '"msg_id": "2018-not_so_random", '
                        '"timestamp": 2, '
                        '"topic": "topic"}'
                ,
                headers={
                    'X-Pagure': 'http://localhost.localdomain/',
                    'X-Pagure-project': 'test',
                    'X-Pagure-Signature': '74b12f0b25bf7767014a0c0de9f3c10'
                    '191e943d8',
                    'X-Pagure-Signature-256': 'f3d757796554466eac49a5282b2'
                    '4ee32a1ecfb65dedd6c6231fb207240a9fe58',
                    'X-Pagure-Topic': b'topic',
                    'Content-Type': 'application/json'
                },
                timeout=60
            ),
            call(
                'http://foo.com/api/flag',
                data='{'
                        '"i": 1, '
                        '"msg": {'
                            '"pagure_instance": "http://localhost.localdomain/", '
                            '"payload": ["a", "b", "c"], '
                            '"project_fullname": "test"}, '
                        '"msg_id": "2018-not_so_random", '
                        '"timestamp": 2, '
                        '"topic": "topic"}'
                ,
                headers={
                    'X-Pagure': 'http://localhost.localdomain/',
                    'X-Pagure-project': 'test',
                    'X-Pagure-Signature': '74b12f0b25bf7767014a0c0de9f3c10'
                    '191e943d8',
                    'X-Pagure-Signature-256': 'f3d757796554466eac49a5282b2'
                    '4ee32a1ecfb65dedd6c6231fb207240a9fe58',
                    'X-Pagure-Topic': b'topic',
                    'Content-Type': 'application/json'
                },
                timeout=60
            )
        ]

        print(post.mock_calls)

        self.assertEqual(
            calls,
            post.mock_calls
        )


class PagureLibTaskServicesJenkinsCItests(tests.Modeltests):
    """ Tests for pagure.lib.task_services """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureLibTaskServicesJenkinsCItests, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None
        self.sshkeydir = os.path.join(self.path, 'sshkeys')
        pagure.config.config['MIRROR_SSHKEYS_FOLDER'] = self.sshkeydir

        tests.create_projects(self.session)
        project = pagure.lib.query.get_authorized_project(self.session, 'test')

        # Install the plugin at the DB level
        plugin = pagure.lib.plugins.get_plugin('Pagure CI')
        dbobj = plugin.db_object()
        dbobj.ci_url = 'https://ci.server.org/'
        dbobj.ci_job = 'pagure'
        dbobj.pagure_ci_token = 'random_token'
        dbobj.project_id = project.id
        self.session.add(dbobj)
        self.session.commit()

        # Create a fork of test for foo
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            is_fork=True,
            parent_id=1,
            description='test project #1',
            hook_token='aaabbbccc_foo',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        self.session.add(item)
        self.session.commit()

    @patch('pagure.lib.tasks_services.trigger_jenkins_build')
    def test_trigger_ci_build_invalid_ci(self, trigger_jenk):
        """ Test the trigger_ci_build method. """
        output = pagure.lib.tasks_services.trigger_ci_build(
            project_name='test',
            cause='PR#ID',
            branch='feature',
            ci_type='travis')
        self.assertIsNone(output)
        trigger_jenk.assert_not_called()

    @patch('pagure.lib.tasks_services.trigger_jenkins_build')
    def test_trigger_ci_build_invalid_ci_fork(self, trigger_jenk):
        """ Test the trigger_ci_build method. """
        output = pagure.lib.tasks_services.trigger_ci_build(
            project_name='forks/foo/test',
            cause='PR#ID',
            branch='feature',
            ci_type='travis')
        self.assertIsNone(output)
        trigger_jenk.assert_not_called()

    @patch('pagure.lib.tasks_services.trigger_jenkins_build')
    def test_trigger_ci_build_valid_project(self, trigger_jenk):
        """ Test the trigger_ci_build method. """
        output = pagure.lib.tasks_services.trigger_ci_build(
            project_name='test',
            cause='PR#ID',
            branch='feature',
            ci_type='jenkins')
        self.assertIsNone(output)
        trigger_jenk.assert_called_once_with(
           branch=u'feature',
           cause=u'PR#ID',
           job=u'pagure',
           project_path=u'test.git',
           token=u'random_token',
           url=u'https://ci.server.org/'
        )

    @patch('pagure.lib.tasks_services.trigger_jenkins_build')
    def test_trigger_ci_build_valid_project_fork(self, trigger_jenk):
        """ Test the trigger_ci_build method. """
        output = pagure.lib.tasks_services.trigger_ci_build(
            project_name='forks/foo/test',
            cause='PR#ID',
            branch='feature',
            ci_type='jenkins')
        self.assertIsNone(output)
        trigger_jenk.assert_called_once_with(
           branch=u'feature',
           cause=u'PR#ID',
           job=u'pagure',
           project_path=u'forks/foo/test.git',
           token=u'random_token',
           url=u'https://ci.server.org/'
        )


class PagureLibTaskServicesLoadJsonTickettests(tests.Modeltests):
    """ Tests for pagure.lib.task_services """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureLibTaskServicesLoadJsonTickettests, self).setUp()

        tests.create_projects(self.session)

        self.gitrepo = os.path.join(self.path, 'repos', 'tickets', 'test.git')
        repopath = os.path.join(self.path, 'repos', 'tickets')
        os.makedirs(self.gitrepo)
        self.repo_obj = pygit2.init_repository(self.gitrepo, bare=True)

        project = pagure.lib.query.get_authorized_project(self.session, 'test')
        # Create an issue to play with
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=project,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.assertEqual(msg.title, 'Test issue')

        issue = pagure.lib.query.search_issues(self.session, project, issueid=1)

        # Add a couple of comment on the ticket
        msg = pagure.lib.query.add_issue_comment(
            session=self.session,
            issue=issue,
            comment='Hey look a comment!',
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        commits = [
            commit
            for commit in self.repo_obj.walk(
                self.repo_obj.head.target, pygit2.GIT_SORT_NONE)
        ]
        # 2 commits: creation - new comment
        self.assertEqual(len(commits), 2)

        issue = pagure.lib.query.search_issues(self.session, project, issueid=1)
        self.assertEqual(len(issue.comments), 1)

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.lib.git.update_request_from_git')
    def test_loading_issue_json(self, up_pr, send):
        """ Test loading the JSON file of a ticket. """
        project = pagure.lib.query.get_authorized_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, project, issueid=1)

        commits = [
            commit.oid.hex
            for commit in self.repo_obj.walk(
                self.repo_obj.head.target, pygit2.GIT_SORT_NONE)
        ]

        output = pagure.lib.tasks_services.load_json_commits_to_db(
            name='test',
            commits=commits,
            abspath=self.gitrepo,
            data_type='ticket',
            agent='pingou',
            namespace=None,
            username=None)
        self.assertIsNone(output)

        up_pr.assert_not_called()
        calls = [
            call(
                u'Loading: %s -- 1/1 ... ... Done' % issue.uid,
                u'Issue import report',
                u'bar@pingou.com'
            )
        ]
        self.assertEqual(
            calls,
            send.mock_calls
        )

        project = pagure.lib.query.get_authorized_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, project, issueid=1)
        self.assertEqual(len(issue.comments), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
