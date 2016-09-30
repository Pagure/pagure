# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

from unittest.case import SkipTest
import json
import unittest
import shutil
import sys
import os
try:
    import pyclamd
except:
    pyclamd = None
import tempfile

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskIssuestests(tests.Modeltests):
    """ Tests for flask issues controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskIssuestests, self).setUp()

        pagure.APP.config['TESTING'] = True
        # TODO: Figure a way to enable this test on jenkins
        if not os.environ.get('BUILD_ID'):
            pagure.APP.config['VIRUS_SCAN_ATTACHMENTS'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.issues.SESSION = self.session
        pagure.ui.repo.SESSION = self.session
        pagure.ui.filters.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = tests.HERE
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = pagure.APP.test_client()

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_new_issue(self, p_send_email, p_ugt):
        """ Test the new_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        # No Git repo
        output = self.app.get('/foo/new_issue')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/foo/new_issue')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(
                os.path.join(tests.HERE), bare=True)

            output = self.app.get('/test/new_issue')
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<div class="card-header">\n        New issue'
                in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
            }

            # Insufficient input
            output = self.app.post('/test/new_issue', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<div class="card-header">\n        New issue'
                in output.data)
            self.assertEqual(output.data.count(
                'This field is required.'), 2)

            data['title'] = 'Test issue'
            output = self.app.post('/test/new_issue', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<div class="card-header">\n        New issue'
                in output.data)
            self.assertEqual(output.data.count(
                'This field is required.'), 1)

            data['issue_content'] = 'We really should improve on this issue'
            data['status'] = 'Open'
            output = self.app.post('/test/new_issue', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<div class="card-header">\n        New issue'
                in output.data)
            self.assertEqual(output.data.count(
                '</button>\n                      This field is required.'),
                0)

            # Invalid user
            data['csrf_token'] = csrf_token
            output = self.app.post('/test/new_issue', data=data)
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                '<p>No such user found in the database: username</p>',
                output.data)

        # User not logged in
        output = self.app.get('/test/new_issue')
        self.assertEqual(output.status_code, 302)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post(
                '/test/new_issue', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)

        # Project w/o issue tracker
        repo = pagure.lib.get_project(self.session, 'test')
        repo.settings = {'issue_tracker': False}
        self.session.add(repo)
        self.session.commit()

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post(
                '/test/new_issue', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_new_issue_w_file(self, p_send_email, p_ugt):
        """ Test the new_issue endpoint with a file. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE), bare=True)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'tickets'), bare=True)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/new_issue')
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<div class="card-header">\n        New issue'
                in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            with open(os.path.join(tests.HERE, 'placebo.png'), 'r') as stream:
                data = {
                    'title': 'Test issue',
                    'issue_content': 'We really should improve on this issue\n'
                                     '<!!image>',
                    'status': 'Open',
                    'filestream': stream,
                    'enctype': 'multipart/form-data',
                    'csrf_token': csrf_token,
                }

                output = self.app.post(
                    '/test/new_issue', data=data, follow_redirects=True)

            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)

        # Project w/o issue tracker
        repo = pagure.lib.get_project(self.session, 'test')
        repo.settings = {'issue_tracker': False}
        self.session.add(repo)
        self.session.commit()

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            with open(os.path.join(tests.HERE, 'placebo.png'), 'r') as stream:
                data = {
                    'title': 'Test issue',
                    'issue_content': 'We really should improve on this issue',
                    'status': 'Open',
                    'filestream': stream,
                    'enctype': 'multipart/form-data',
                    'csrf_token': csrf_token,
                }

                output = self.app.post(
                    '/test/new_issue', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_view_issues(self, p_send_email, p_ugt):
        """ Test the view_issues endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/issues')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE), bare=True)

        output = self.app.get('/test/issues')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'div class="projectinfo m-t-1 m-b-1">\ntest project #1        '
            '</div>', output.data)
        self.assertTrue(
            '<h2>\n      0 Open Issues' in output.data)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test invalid issue',
            content='This really is not related',
            user='pingou',
            status='Invalid',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test invalid issue')

        # Whole list
        output = self.app.get('/test/issues')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Issues - test - Pagure</title>', output.data)
        self.assertTrue(
            '<h2>\n      1 Open Issues' in output.data)

        # Status = closed (all but open)
        output = self.app.get('/test/issues?status=cloSED')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Issues - test - Pagure</title>', output.data)
        self.assertTrue(
            '<h2>\n      1 Closed Issues' in output.data)

        # Status = fixed
        output = self.app.get('/test/issues?status=fixed')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Issues - test - Pagure</title>', output.data)
        self.assertTrue(
            '<h2>\n      0 Closed Issues' in output.data)

        # Status = Invalid
        output = self.app.get('/test/issues?status=Invalid')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Issues - test - Pagure</title>', output.data)
        self.assertTrue(
            '<h2>\n      1 Closed Issues' in output.data)

        # All tickets
        output = self.app.get('/test/issues?status=all')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Issues - test - Pagure</title>', output.data)
        self.assertTrue(
            '<h2>\n      2 Issues' in output.data)

        # New issue button is shown
        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'class="btn btn-success btn-sm">New Issue</a>',
                output.data)

        # Project w/o issue tracker
        repo = pagure.lib.get_project(self.session, 'test')
        repo.settings = {'issue_tracker': False}
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/issues')
        self.assertEqual(output.status_code, 404)

        # New issue button is hidden
        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test')
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                'class="btn btn-success btn-sm">New Issue</a>',
                output.data)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_view_issue(self, p_send_email, p_ugt):
        """ Test the view_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/issue/1')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE), bare=True)

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 200)
        # Not authentified = No edit
        self.assertNotIn(
            '<a class="btn btn-primary btn-sm" href="/test/issue/1/edit" '
            'title="Edit this issue">',
            output.data)
        self.assertTrue(
            '<a href="/login/?next=http%3A%2F%2Flocalhost%2Ftest%2Fissue%2F1">'
            'Login</a>\n            to comment on this ticket.'
            in output.data)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            # Not author nor admin = No edit
            self.assertNotIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertNotIn(
                '<button class="btn btn-danger btn-sm" type="submit"',
                output.data)
            self.assertNotIn('title="Delete this ticket">', output.data)
            self.assertFalse(
                '<a href="/login/">Login</a> to comment on this ticket.'
                in output.data)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '<button class="btn btn-danger btn-sm" type="submit"',
                output.data)
            self.assertIn('title="Delete this ticket">', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

        # Create private issue
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Not logged in
        output = self.app.get('/test/issue/2')
        self.assertEqual(output.status_code, 403)

        # Wrong user
        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/2')
            self.assertEqual(output.status_code, 403)

        # reporter
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/2')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #2: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<span class="oi red-icon" data-glyph="lock-locked" '
                'title="Private issue"></span>', output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/2/edit" title="Edit this issue">',
                output.data)

        # Project w/o issue tracker
        repo = pagure.lib.get_project(self.session, 'test')
        repo.settings = {'issue_tracker': False}
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_update_issue(self, p_send_email, p_ugt):
        """ Test the update_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        # No Git repo
        output = self.app.get('/foo/issue/1/update')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE), bare=True)

        output = self.app.get('/test/issue/1/update')
        self.assertEqual(output.status_code, 302)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'status': 'fixed'
            }

            # Invalid repo
            output = self.app.post('/bar/issue/1/update', data=data)
            self.assertEqual(output.status_code, 404)

            # Non-existing issue
            output = self.app.post('/test/issue/100/update', data=data)
            self.assertEqual(output.status_code, 404)

            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertFalse(
                '<option selected value="Fixed">Fixed</option>'
                in output.data)

            # Right status, wrong csrf
            data['status'] = 'Fixed'
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertFalse(
                '<option selected value="Fixed">Fixed</option>'
                in output.data)

            # working status update
            data['csrf_token'] = csrf_token
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      Successfully edited issue #1',
                output.data)
            self.assertTrue(
                '<option selected value="Fixed">Fixed</option>'
                in output.data)
            self.assertIn(
                '<small><p><a href="{app_url}/user/pingou"> '
                '@pingou</a> changed the status to <code>Fixed</code>'
                '</p></small>'.format(app_url=pagure.APP.config['APP_URL']),
                output.data)

            # Add new comment
            data = {
                'csrf_token': csrf_token,
                'status': 'Fixed',
                'comment': 'Woohoo a second comment !',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      Comment added',
                output.data)
            self.assertNotIn(
                '</button>\n                      No changes to edit',
                output.data)
            self.assertTrue(
                '<p>Woohoo a second comment !</p>' in output.data)
            self.assertEqual(output.data.count('comment_body">'), 2)
            self.assertTrue(
                '<option selected value="Fixed">Fixed</option>'
                in output.data)

            # Add new tag
            data = {
                'csrf_token': csrf_token,
                'status': 'Fixed',
                'tag': 'tag2',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      '
                'Successfully edited issue #1',
                output.data)
            self.assertTrue(
                '<p>Woohoo a second comment !</p>' in output.data)
            self.assertEqual(output.data.count('comment_body">'), 2)
            self.assertTrue(
                '<option selected value="Fixed">Fixed</option>'
                in output.data)

            # Assign issue to an non-existent user
            data = {
                'csrf_token': csrf_token,
                'status': 'Fixed',
                'assignee': 'ralph',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      No user &#34;ralph&#34; found',
                output.data)
            self.assertTrue(
                '<p>Woohoo a second comment !</p>' in output.data)
            self.assertEqual(output.data.count('comment_body">'), 2)
            self.assertTrue(
                '<option selected value="Fixed">Fixed</option>'
                in output.data)

            # Assign issue properly
            data = {
                'csrf_token': csrf_token,
                'status': 'Fixed',
                'assignee': 'pingou',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      Issue assigned',
                output.data)
            self.assertTrue(
                '<a href="/test/issues?assignee=pingou">' in output.data)
            self.assertTrue(
                '<p>Woohoo a second comment !</p>' in output.data)
            self.assertEqual(output.data.count('comment_body">'), 2)
            self.assertTrue(
                '<option selected value="Fixed">Fixed</option>'
                in output.data)

        # Create another issue with a dependency
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Reset the status of the first issue
        parent_issue = pagure.lib.search_issues(
            self.session, repo, issueid=2)
        parent_issue.status = 'Open'
        # Add the dependency relationship
        self.session.add(parent_issue)
        issue = pagure.lib.search_issues(self.session, repo, issueid=2)
        issue.parents.append(parent_issue)
        self.session.add(issue)
        self.session.commit()

        with tests.user_set(pagure.APP, user):

            data['csrf_token'] = csrf_token
            output = self.app.post(
                '/test/issue/2/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #2: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/2/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      You cannot close a ticket '
                'that has ticket depending that are still open.',
                output.data)
            self.assertTrue(
                '<option selected value="Open">Open</option>'
                in output.data)

        # Create private issue
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Wrong user
        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post(
                '/test/issue/3/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        # Project w/o issue tracker
        repo = pagure.lib.get_project(self.session, 'test')
        repo.settings = {'issue_tracker': False}
        self.session.add(repo)
        self.session.commit()

        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1/update')
            self.assertEqual(output.status_code, 302)

            # Repo not set-up for issue tracker
            output = self.app.post('/test/issue/1/update', data=data)
            self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_update_issue_drop_comment(self, p_send_email, p_ugt):
        """ Test droping comment via the update_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE), bare=True)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Add new comment
            data = {
                'csrf_token': csrf_token,
                'comment': 'Woohoo a second comment !',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      Comment added',
                output.data)
            self.assertTrue(
                '<p>Woohoo a second comment !</p>' in output.data)
            self.assertEqual(output.data.count('comment_body">'), 2)

        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)

        data = {
            'csrf_token': csrf_token,
            'drop_comment': 1,
        }

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            # Wrong issue id
            output = self.app.post(
                '/test/issue/3/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Wrong user
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            # Drop the new comment
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      Comment removed',
                output.data)

            # Drop non-existant comment
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_update_issue_depend(self, p_send_email, p_ugt):
        """ Test adding dependency via the update_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE), bare=True)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this again',
            user='foo',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Add a dependent ticket
            data = {
                'csrf_token': csrf_token,
                'depends': '2',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      '
                'Successfully edited issue #1',
                output.data)

            # Add an invalid dependent ticket
            data = {
                'csrf_token': csrf_token,
                'depends': '2,abc',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertNotIn(
                '</button>\n                      '
                'Successfully edited issue #1',
                output.data)

        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.depends_text, [2])
        self.assertEqual(issue.blocks_text, [])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_update_issue_block(self, p_send_email, p_ugt):
        """ Test adding blocked issue via the update_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE), bare=True)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this again',
            user='foo',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Add a dependent ticket
            data = {
                'csrf_token': csrf_token,
                'blocks': '2',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      '
                'Successfully edited issue #1',
                output.data)

            # Add an invalid dependent ticket
            data = {
                'csrf_token': csrf_token,
                'blocks': '2,abc',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertNotIn(
                '</button>\n                      '
                'Successfully edited issue #1',
                output.data)

        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.depends_text, [])
        self.assertEqual(issue.blocks_text, [2])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_upload_issue(self, p_send_email, p_ugt):
        """ Test the upload_issue endpoint. """
        if not pyclamd:
            raise SkipTest()
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE), bare=True)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'tickets'), bare=True)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            output = self.app.post('/foo/issue/1/upload')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/issue/100/upload')
            self.assertEqual(output.status_code, 404)

            # Invalid upload
            data = {
                'enctype': 'multipart/form-data',
            }
            output = self.app.post(
                '/test/issue/1/upload', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            json_data = json.loads(output.data)
            exp = {'output': 'notok'}
            self.assertDictEqual(json_data, exp)

            # TODO: Figure a way to enable this test on jenkins
            # Try to attach a virus
            if not os.environ.get('BUILD_ID'):
                with tempfile.NamedTemporaryFile() as eicarfile:
                    eicarfile.write(pyclamd.ClamdUnixSocket().EICAR())
                    eicarfile.flush()
                    with open(eicarfile.name, 'rb') as stream:
                        data = {
                            'csrf_token': csrf_token,
                            'filestream': stream,
                            'enctype': 'multipart/form-data',
                        }
                        output = self.app.post(
                            '/test/issue/1/upload', data=data, follow_redirects=True)
                    self.assertEqual(output.status_code, 200)
                    json_data = json.loads(output.data)
                    exp = {
                        'output': 'notok',
                    }
                    self.assertDictEqual(json_data, exp)

            # Attach a file to a ticket
            with open(os.path.join(tests.HERE, 'placebo.png'), 'rb') as stream:
                data = {
                    'csrf_token': csrf_token,
                    'filestream': stream,
                    'enctype': 'multipart/form-data',
                }
                output = self.app.post(
                    '/test/issue/1/upload', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            json_data = json.loads(output.data)

            folder = os.path.dirname(
                os.path.abspath(__file__))[1:].replace('/', '_')
            exp = {
                'output': 'ok',
                'filelocation': '/test/issue/raw/files/8a06845923010b27bfd8'
                                'e7e75acff7badc40d1021b4994e01f5e11ca40bc3a'
                                'be-%s_placebo.png' % folder,
                'filename': '%s_placebo.png' % folder,
            }
            self.assertDictEqual(json_data, exp)

        # Project w/o issue tracker
        repo = pagure.lib.get_project(self.session, 'test')
        repo.settings = {'issue_tracker': False}
        self.session.add(repo)
        self.session.commit()

        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/issue/1/upload')
            self.assertEqual(output.status_code, 404)

    def test_view_issue_raw_file_empty(self):
        """ Test the view_issue_raw_file endpoint. """
        # Create the project and git repos
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'tickets'), bare=True)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        url = '/issue/raw/files/8a06845923010b27bfd8'\
            'e7e75acff7badc40d1021b4994e01f5e11ca40bc3a'\
            'be-home_pierrey_repos_gitrepo_pagure_tests'\
            '_placebo.png'

        output = self.app.get('/foo' + url)
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/test' + url)
        self.assertEqual(output.status_code, 404)

        # Project w/o issue tracker
        repo = pagure.lib.get_project(self.session, 'test')
        repo.settings = {'issue_tracker': False}
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test' + url)
        self.assertEqual(output.status_code, 404)

    def test_view_issue_raw_file(self):
        """ Test the view_issue_raw_file endpoint. """
        # Create the issue and upload to it
        self.test_upload_issue()

        # Project w/ issue tracker
        repo = pagure.lib.get_project(self.session, 'test')
        repo.settings = {'issue_tracker': True}
        self.session.add(repo)
        self.session.commit()

        url = '/issue/raw/files/8a06845923010b27bfd8'\
            'e7e75acff7badc40d1021b4994e01f5e11ca40bc3a'\
            'be-%s_placebo.png' % os.path.dirname(
                os.path.abspath(__file__))[1:].replace('/', '_')

        output = self.app.get('/foo' + url)
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/test/issue/raw/files/test.png')
        self.assertEqual(output.status_code, 404)

        # Access file by name
        output = self.app.get('/test' + url)
        self.assertEqual(output.status_code, 200)

        # Project w/o issue tracker
        repo = pagure.lib.get_project(self.session, 'test')
        repo.settings = {'issue_tracker': False}
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test' + url)
        self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_edit_issue(self, p_send_email, p_ugt):
        """ Test the edit_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        # No Git repo
        output = self.app.get('/foo/issue/1/edit')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/foo/issue/1/edit')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(
                os.path.join(tests.HERE), bare=True)

            output = self.app.get('/test/issue/1/edit')
            self.assertEqual(output.status_code, 404)

        # User not logged in
        output = self.app.get('/foo/issue/1/edit')
        self.assertEqual(output.status_code, 404)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1/edit')
            self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1/edit')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1/edit')
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<div class="card-header">\n        Edit '
                'issue #1\n      </div>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'issue_content': 'We should work on this!'
            }

            output = self.app.post('/test/issue/1/edit', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<div class="card-header">\n        Edit '
                'issue #1\n      </div>' in output.data)
            self.assertEqual(output.data.count(
                '<small>\n            This field is required.&nbsp;\n'
                '          </small>'), 1)
            self.assertEqual(output.data.count(
                '<small>\n            Not a valid choice&nbsp;'
                '\n          </small>'), 1)

            data['status'] = 'Open'
            data['title'] = 'Test issue #1'
            output = self.app.post('/test/issue/1/edit', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<div class="card-header">\n        Edit '
                'issue #1\n      </div>' in output.data)
            self.assertEqual(output.data.count(
                '<small>\n            This field is required.&nbsp;\n'
                '          </small>'), 0)
            self.assertEqual(output.data.count(
                '<small>\n            Not a valid choice&nbsp;'
                '\n          </small>'), 0)

            data['csrf_token'] = csrf_token
            output = self.app.post(
                '/test/issue/1/edit', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Successfully edited issue #1',
                output.data)
            self.assertIn(
                '<span class="issueid label label-default">#1</span>\n'
                '    <span id="issuetitle">Test issue #1</span>',
                output.data)
            self.assertEqual(output.data.count(
                '<option selected value="Open">Open</option>'), 1)
            self.assertEqual(output.data.count('comment_body">'), 1)
            self.assertEqual(output.data.count(
                '<p>We should work on this!</p>'), 1)

        # Project w/o issue tracker
        repo = pagure.lib.get_project(self.session, 'test')
        repo.settings = {'issue_tracker': False}
        self.session.add(repo)
        self.session.commit()

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/issue/1/edit', data=data)
            self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_edit_tag(self, p_send_email, p_ugt):
        """ Test the edit_tag endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        # No Git repo
        output = self.app.get('/foo/tag/foo/edit')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/foo/tag/foo/edit')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(tests.HERE)

            output = self.app.get('/test/tag/foo/edit')
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.get('/test/tag/foo/edit')
        self.assertEqual(output.status_code, 302)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Add a tag to the issue
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        msg = pagure.lib.add_tag_obj(
            session=self.session,
            obj=issue,
            tags='tag1',
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Tag added: tag1')

        # Before edit, list tags
        tags = pagure.lib.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ['tag1'])

        # Edit tag
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            #Edit a tag that doesn't exit
            output = self.app.get('/test/tag/does_not_exist/edit')
            self.assertEqual(output.status_code, 404)

            output = self.app.get('/test/tag/tag1/edit')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Edit tag: tag1</h2>' in output.data)
            self.assertTrue(
                '<p>Enter in the field below the new name for the tag: '
                '"tag1"</p>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'tag': 'tag2'}

            output = self.app.post('/test/tag/tag1/edit', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Edit tag: tag1</h2>' in output.data)
            self.assertTrue(
                '<p>Enter in the field below the new name for the tag: '
                '"tag1"</p>' in output.data)

            data['csrf_token'] = csrf_token
            output = self.app.post(
                '/test/tag/tag1/edit', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn(
                '</button>\n                      Edited tag: tag1 to tag2',
                output.data)

        # After edit, list tags
        tags = pagure.lib.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ['tag2'])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_remove_tag(self, p_send_email, p_ugt):
        """ Test the remove_tag endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        # No Git repo
        output = self.app.post('/foo/droptag/')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/droptag/')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(tests.HERE)

            output = self.app.post('/test/droptag/')
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.post('/test/droptag/')
        self.assertEqual(output.status_code, 302)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Add a tag to the issue
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        msg = pagure.lib.add_tag_obj(
            session=self.session,
            obj=issue,
            tags='tag1',
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Tag added: tag1')

        # Before edit, list tags
        tags = pagure.lib.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ['tag1'])

        # Edit tag
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post(
                '/test/droptag/', data={}, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<title>Settings - test - Pagure</title>' in output.data)
            self.assertTrue("<h3>Settings for test</h3>" in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'tag': 'tag1'}

            output = self.app.post(
                '/test/droptag/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue("<h3>Settings for test</h3>" in output.data)

            data['csrf_token'] = csrf_token
            output = self.app.post(
                '/test/droptag/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue("<h3>Settings for test</h3>" in output.data)
            self.assertIn(
                '</button>\n                      Removed tag: tag1',
                output.data)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_delete_issue(self, p_send_email, p_ugt):
        """ Test the delete_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(tests.HERE)
        tests.create_projects_git(os.path.join(tests.HERE, 'tickets'))

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post(
                '/foo/issue/1/drop', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            output = self.app.post(
                '/test/issue/100/drop', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            output = self.app.post(
                '/test/issue/1/drop', follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post(
                '/test/issue/1/drop', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
            }

            # No CSRF token
            output = self.app.post(
                '/test/issue/1/drop', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)

            data['csrf_token'] = csrf_token
            output = self.app.post(
                '/test/issue/1/drop', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issues - test - Pagure</title>', output.data)
            self.assertIn(
                '</button>\n                      Issue deleted',
                output.data)

        # Project w/o issue tracker
        repo = pagure.lib.get_project(self.session, 'test')
        repo.settings = {'issue_tracker': False}
        self.session.add(repo)
        self.session.commit()

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/issue/1/drop', data=data)
            self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_update_issue_edit_comment(self,  p_send_email, p_ugt):
        """ Test the issues edit comment endpoint """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE), bare=True)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Add new comment
            data = {
                'csrf_token': csrf_token,
                'comment': 'Woohoo a second comment !',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      Comment added',
                output.data)
            self.assertTrue(
                '<p>Woohoo a second comment !</p>' in output.data)
            self.assertEqual(output.data.count('comment_body">'), 2)

        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(
            issue.comments[0].comment,
            'Woohoo a second comment !')

        data = {
            'csrf_token': csrf_token,
            'edit_comment': 1,
            'update_comment': 'Updated comment',
        }

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            # Wrong issue id
            output = self.app.post(
                '/test/issue/3/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Wrong user
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            # Edit comment
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      Comment updated',
                output.data)

        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.comments[0].comment, 'Updated comment')

        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1/comment/1/edit')
            self.assertIn(
                '<title>test - Pagure</title>', output.data)
            self.assertTrue('<div id="edit">' in output.data)
            self.assertTrue('<section class="edit_comment">' in output.data)
            self.assertTrue(
                '<textarea class="form-control" id="update_comment"'
                in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data['csrf_token'] = csrf_token
            data['update_comment'] = 'Second update'

            # Edit the comment with the other endpoint
            output = self.app.post(
                '/test/issue/1/comment/1/edit',
                data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '</button>\n                      Comment updated',
                output.data)

        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.comments[0].comment, 'Second update')


    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_git_urls(self,  p_send_email, p_ugt):
        """ Check that the url to the git repo for issues is present/absent when
        it should.
        """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_view_issues()

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            # Check that the git issue URL is present
            output = self.app.get('/test')
            self.assertNotIn(
                '<h5><strong>Issues GIT URLs</strong></h5>', output.data)

            # Project w/o issue tracker
            repo = pagure.lib.get_project(self.session, 'test')
            repo.settings = {'issue_tracker': True}
            self.session.add(repo)
            self.session.commit()

            # Check that the git issue URL is gone
            output = self.app.get('/test')
            self.assertIn(
                '<h5><strong>Issues GIT URLs</strong></h5>', output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagureFlaskIssuestests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
