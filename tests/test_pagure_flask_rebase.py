# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import unittest
import shutil
import sys
import os

import json
from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib.query
import pagure.lib.tasks
import tests


class PagureRebasetests(tests.Modeltests):
    """ Tests rebasing pull-request in pagure """

    maxDiff = None

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureRebasetests, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        tests.add_content_to_git(
            os.path.join(self.path, 'repos', 'test.git'),
            branch='master', content="foobarbaz", filename="testfile")
        tests.add_content_to_git(
            os.path.join(self.path, 'repos', 'test.git'),
            branch='test', content="foobar", filename="sources")
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'test.git'))

        # Create a PR for these changes
        project = pagure.lib.query.get_authorized_project(
            self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='test',
            repo_to=project,
            branch_to='master',
            title='PR from the test branch',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the test branch')

        self.project = pagure.lib.query.get_authorized_project(
            self.session, 'test')
        self.assertEqual(len(project.requests), 1)
        self.request = self.project.requests[0]

    def test_merge_status_merge(self):
        """ Test that the PR can be merged with a merge commit. """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            data = {'requestid': self.request.uid, 'csrf_token': self.get_csrf()}
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'code': u'MERGE',
                    u'message': u'The pull-request can be merged with a '
                        u'merge commit',
                    u'short_code': u'With merge'
                }
            )

    def test_merge_status_needsrebase(self):
        """ Test that the PR is marked as needing a rebase if the project
        disables non-fast-forward merges. """
        self.project = pagure.lib.query.get_authorized_project(
            self.session, 'test')
        settings = self.project.settings
        settings['disable_non_fast-forward_merges'] = True
        self.project.settings = settings
        self.session.add(self.project)
        self.session.commit()

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            data = {'requestid': self.request.uid, 'csrf_token': self.get_csrf()}
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'code': u'NEEDSREBASE',
                    u'message': u'The pull-request must be rebased before '
                        u'merging',
                    u'short_code': u'Needs rebase'
                }
            )

    def test_rebase_task(self):
        """ Test the rebase PR task and its outcome. """
        pagure.lib.tasks.rebase_pull_request(
            'test', namespace=None, user=None, requestid=self.request.id,
            user_rebaser='pingou')

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            data = {'requestid': self.request.uid, 'csrf_token': self.get_csrf()}
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'code': u'FFORWARD',
                    u'message': u'The pull-request can be merged and '
                        u'fast-forwarded',
                    u'short_code': u'Ok'
                }
            )

    def test_rebase_api_ui_logged_in(self):
        """ Test the rebase PR API endpoint when logged in from the UI and
        its outcome. """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            # Get the merge status first so it's cached and can be refreshed
            csrf_token = self.get_csrf()
            data = {'requestid': self.request.uid, 'csrf_token': csrf_token}
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'code': u'MERGE',
                    u'message': u'The pull-request can be merged with '
                        u'a merge commit',
                    u'short_code': u'With merge'
                }
            )

            output = self.app.post('/api/0/test/pull-request/1/rebase')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {u'message': u'Pull-request rebased'}
            )

            data = {'requestid': self.request.uid, 'csrf_token': csrf_token}
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'code': u'FFORWARD',
                    u'message': u'The pull-request can be merged and '
                        u'fast-forwarded',
                    u'short_code': u'Ok'
                }
            )

            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn('rebased onto', output_text)
            repo = pagure.lib.query._get_project(self.session, 'test')
            self.assertEqual(
                repo.requests[0].comments[0].user.username, 'pingou')

    def test_rebase_api_ui_logged_in_different_user(self):
        """ Test the rebase PR API endpoint when logged in from the UI and
        its outcome. """
        # Add 'foo' to the project 'test' so 'foo' can rebase the PR
        repo = pagure.lib.query._get_project(self.session, 'test')
        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            # Get the merge status first so it's cached and can be refreshed
            csrf_token = self.get_csrf()
            data = {'requestid': self.request.uid, 'csrf_token': csrf_token}
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'code': u'MERGE',
                    u'message': u'The pull-request can be merged with '
                        u'a merge commit',
                    u'short_code': u'With merge'
                }
            )

            output = self.app.post('/api/0/test/pull-request/1/rebase')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {u'message': u'Pull-request rebased'}
            )

            data = {'requestid': self.request.uid, 'csrf_token': csrf_token}
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'code': u'FFORWARD',
                    u'message': u'The pull-request can be merged and '
                        u'fast-forwarded',
                    u'short_code': u'Ok'
                }
            )

            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn('rebased onto', output_text)
            repo = pagure.lib.query._get_project(self.session, 'test')
            self.assertEqual(repo.requests[0].comments[0].user.username, 'foo')

    def test_rebase_api_api_logged_in(self):
        """ Test the rebase PR API endpoint when using an API token and
        its outcome. """

        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        output = self.app.post('/api/0/test/pull-request/1/rebase', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {u'message': u'Pull-request rebased'}
        )

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):

            data = {'requestid': self.request.uid, 'csrf_token': self.get_csrf()}
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'code': u'FFORWARD',
                    u'message': u'The pull-request can be merged and '
                        u'fast-forwarded',
                    u'short_code': u'Ok'
                }
            )

    def test_rebase_api_conflicts(self):
        """ Test the rebase PR API endpoint when logged in from the UI and
        its outcome. """
        tests.add_content_to_git(
            os.path.join(self.path, 'repos', 'test.git'),
            branch='master', content="foobar baz")

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/api/0/test/pull-request/1/rebase')
            self.assertEqual(output.status_code, 400)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'error': u'Did not manage to rebase this pull-request',
                    u'error_code': u'ENOCODE'
                }
            )

            data = {'requestid': self.request.uid, 'csrf_token': self.get_csrf()}
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'code': u'CONFLICTS',
                    u'message': u'The pull-request cannot be merged due '
                        u'to conflicts',
                    u'short_code': u'Conflicts'
                }
            )

    def test_rebase_api_api_logged_in_unknown_project(self):
        """ Test the rebase PR API endpoint when the project doesn't exist """

        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        output = self.app.post('/api/0/unknown/pull-request/1/rebase', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {u'error': u'Project not found', u'error_code': u'ENOPROJECT'}
        )

    def test_rebase_api_api_logged_in_unknown_pr(self):
        """ Test the rebase PR API endpoint when the PR doesn't exist """

        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        output = self.app.post('/api/0/test/pull-request/404/rebase', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {u'error': u'Pull-Request not found', u'error_code': u'ENOREQ'}
        )

    def test_rebase_api_api_logged_in_unknown_token(self):
        """ Test the rebase PR API endpoint with an invalid API token """

        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token unknown'}

        output = self.app.post('/api/0/test/pull-request/1/rebase', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                u'error': u'Invalid or expired token. Please visit '
                    'http://localhost.localdomain/settings#api-keys to get '
                    'or renew your API token.',
                u'error_code': u'EINVALIDTOK',
                u'errors': 'Invalid token',
            }
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
