# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

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
except ImportError:
    pyclamd = None
import six
import tempfile
import re
from datetime import datetime, timedelta
from six.moves.urllib.parse import urlparse, parse_qs

import pygit2
from bs4 import BeautifulSoup
from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests


class PagureFlaskIssuesOpenAccesstests(tests.Modeltests):
    """ Tests for flask issues controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskIssuesOpenAccesstests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, 'tickets'), bare=True)

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['open_metadata_access_to_all'] = True
        repo.settings = settings
        repo.milestones = {'v1.0': '', 'v2.0': 'Tomorrow!'}
        self.session.add(repo)
        self.session.commit()

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_new_issue_with_metadata(self):
        """ Test the new_issue endpoint when the user has access to the
        project. """

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/new_issue')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-4">New Issue</h4>\n',
                output_text)
            self.assertIn('<strong>Tags</strong>', output_text)
            self.assertIn(
                '<strong>Assignee</strong>', output_text)

            csrf_token = self.get_csrf(output=output)

            data = {
                    'title': 'Test issue3',
                    'issue_content': 'We really should improve on this issue\n',
                    'status': 'Open',
                    'assignee': 'foo',
                    'milestone': 'v2.0',
                    'tag': 'tag2',
                    'csrf_token': csrf_token,
                }

            output = self.app.post(
                '/test/new_issue', data=data, follow_redirects=True)

            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue3 - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">\n',
                output_text)
            # Check the metadata
            self.assertIn(
                'title="comma separated list of tags"\n                '
                'value="tag2" />', output_text)
            self.assertIn(
                'placeholder="username"\n              value="foo" />\n',
                output_text)
            self.assertIn(
                'href="/test/roadmap/v2.0/"',
                output_text)

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_new_issue_with_metadata_not_user(self):
        """ Test the new_issue endpoint when the user does not have access
        to the project but still tries to.
        """

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/new_issue')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-4">New Issue</h4>\n',
                output_text)
            self.assertIn('<strong>Tags</strong>', output_text)
            self.assertIn('<strong>Assignee</strong>', output_text)

            csrf_token = self.get_csrf(output=output)

            data = {
                    'title': 'Test issue3',
                    'issue_content': 'We really should improve on this issue\n',
                    'status': 'Open',
                    'assignee': 'foo',
                    'milestone': 'v2.0',
                    'tag': 'tag2',
                    'csrf_token': csrf_token,
                }

            output = self.app.post(
                '/test/new_issue', data=data, follow_redirects=True)

            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue3 - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">\n',
                output_text)
            # Check the metadata
            self.assertIn(
                'title="comma separated list of tags"\n                '
                'value="tag2" />', output_text)
            self.assertIn(
                'placeholder="username"\n              value="foo" />\n',
                output_text)
            self.assertIn(
                '<div class="ml-2" id="milestone_plain">'
                '\n              <span>'
                '\n                <a href="/test/roadmap/v2.0/">'
                '\n                  v2.0\n', output_text)

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_view_issue(self):
        """ Test the view_issue endpoint. """
        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        # Not authentified = No edit
        self.assertNotIn(
            '<a class="btn btn-outline-secondary btn-sm border-0" '
            'href="/test/issue/1/edit" title="Edit this issue">\n',
            output_text)
        self.assertIn(
            '<a href="/login/?next=http%3A%2F%2Flocalhost%2Ftest%2Fissue%2F1">'
            'Login</a>\n          to comment on this ticket.',
            output_text)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Not author nor admin = No edit
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertNotIn(
                '<a class="dropdown-item text-danger" href="javascript:void(0)" id="closeticket"\n'
                '                title="Delete this ticket">\n',
                output_text)
            self.assertFalse(
                '<a href="/login/">Login</a> to comment on this ticket.'
                in output_text)
            # Not author nor admin but open_access = take
            self.assertIn('function take_issue(){', output_text)
            self.assertNotIn('function drop_issue(){', output_text)
            self.assertIn(
                '<a href="javascript:void(0)" id="take-btn"\n',
                output_text)

            csrf_token = self.get_csrf(output=output)

        # Create private issue
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Not logged in
        output = self.app.get('/test/issue/2')
        self.assertEqual(output.status_code, 404)

        # Wrong user
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/2')
            self.assertEqual(output.status_code, 404)

        # another user
        user.username = 'foo'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/2')
            self.assertEqual(output.status_code, 404)

        # Project w/o issue tracker
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        repo.settings = {'issue_tracker': False}
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_view_issue_user_ticket(self):
        """ Test the view_issue endpoint. """

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        # Not authentified = No edit
        self.assertNotIn(
            '<a class="btn btn-outline-secondary btn-sm border-0" '
            'href="/test/issue/1/edit" title="Edit this issue">\n',
            output_text)
        self.assertTrue(
            '<a href="/login/?next=http%3A%2F%2Flocalhost%2Ftest%2Fissue%2F1">'
            'Login</a>\n          to comment on this ticket.'
            in output_text)

        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')

        # Add user 'foo' with ticket access on repo
        msg = pagure.lib.add_user_to_project(
            self.session,
            repo,
            new_user='foo',
            user='pingou',
            access='ticket',
        )
        self.assertEqual(msg, 'User added')
        self.session.commit()

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Not author nor admin = No edit
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertNotIn(
                '<a class="dropdown-item text-danger" href="javascript:void(0)" id="closeticket"\n'
                '                title="Delete this ticket">\n',
                output_text)
            self.assertFalse(
                '<a href="/login/">Login</a> to comment on this ticket.'
                in output_text)
            # user has ticket = take ok
            self.assertIn('function take_issue(){', output_text)
            self.assertIn('function drop_issue(){', output_text)
            self.assertIn(
                '<a href="javascript:void(0)" id="take-btn"\n',
                output_text)

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_view_issue_custom_field_user_ticket(self):
        """ Test the view_issue endpoint. """
        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Add user 'foo' with ticket access on repo
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.add_user_to_project(
            self.session,
            repo,
            new_user='foo',
            user='pingou',
            access='ticket',
        )
        self.assertEqual(msg, 'User added')
        self.session.commit()

        # Set some custom fields
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.set_custom_key_fields(
            self.session,
            repo,
            ['bugzilla', 'upstream', 'reviewstatus'],
            ['link', 'boolean', 'list'],
            ['unused data for non-list type', '', 'ack, nack ,  needs review'],
            [None, None, None])
        self.session.commit()
        self.assertEqual(msg, 'List of custom fields updated')

        # User with no rights
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertNotIn(
                '<a class="dropdown-item text-danger" href="javascript:void(0)" id="closeticket"\n'
                '                title="Delete this ticket">\n',
                output_text)
            # user no ACLs but open_access = take action/button - no drop
            self.assertIn('function take_issue(){', output_text)
            self.assertNotIn('function drop_issue(){', output_text)
            self.assertIn(
                '<a href="javascript:void(0)" id="take-btn"\n',
                output_text)

            # user no ACLs = no metadata form
            self.assertNotIn(
                '<input                  class="form-control" '
                'name="bugzilla" id="bugzilla"/>', output_text)
            self.assertNotIn(
                '<select class="form-control" name="reviewstatus" '
                'id="reviewstatus>', output_text)
            self.assertNotIn(
                '<input type="checkbox"                   '
                'class="form-control" name="upstream" id="upstream"/>',
                output_text)

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertNotIn(
                '<a class="dropdown-item text-danger" href="javascript:void(0)" id="closeticket"\n'
                '                title="Delete this ticket">\n',
                output_text)
            self.assertNotIn(
                '<a href="/login/">Login</a> to comment on this ticket.',
                output_text)
            # user has ticket = take ok
            self.assertIn('function take_issue(){', output_text)
            self.assertIn('function drop_issue(){', output_text)
            self.assertIn(
                '<a href="javascript:void(0)" id="take-btn"\n',
                output_text)

            # user has ticket == Sees the metadata
            self.assertIn(
                '<input                    class="form-control" '
                'name="bugzilla" id="bugzilla"/>', output_text)
            self.assertIn(
                '<select class="form-control"\n'
                '                      name="reviewstatus"\n'
                '                      id="reviewstatus">\n',
                output_text)
            self.assertIn(
                '<input type="checkbox"                     '
                'class="form-control" name="upstream" id="upstream"/>',
                output_text)

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_view_issue_non_ascii_milestone(self):
        """ Test the view_issue endpoint with non-ascii milestone. """
        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

        stone = 'käpy'
        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Add a non-ascii milestone to the issue but project has no milestone
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        message = pagure.lib.edit_issue(
            self.session,
            issue=issue,
            milestone=stone,
            private=False,
            user='pingou',
        )
        self.assertEqual(
            message,
            [
                'Issue set to the milestone: k\xe4py'
            ]
        )
        self.session.commit()

        # View the issue
        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>Issue #1: Test issue - test - Pagure</title>',
            output_text)
        self.assertIn(stone, output_text)

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_view_issue_list_no_data(self):
        """ Test the view_issue endpoint when the issue has a custom field
        of type list with no data attached. """
        repo = pagure.lib.get_authorized_project(self.session, 'test')

        # Add custom fields to the project
        msg = pagure.lib.set_custom_key_fields(
            session=self.session,
            project=repo,
            fields=['test1'],
            types=['list'],
            data=[None],
            notify=[None]
        )
        self.session.commit()
        self.assertEqual(msg, 'List of custom fields updated')

        # Create issues to play with
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Big problÈm!',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Big problÈm!')

        # Assign a value to the custom key on that ticket
        cfield = pagure.lib.get_custom_key(
            session=self.session,
            project=repo,
            keyname='test1')
        msg = pagure.lib.set_custom_key_value(
            session=self.session,
            issue=msg,
            key=cfield,
            value='item')
        self.session.commit()
        self.assertEqual(msg, 'Custom field test1 adjusted to item')

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_update_issue(self):
        """ Test the update_issue endpoint. """
        output = self.app.get('/test/issue/1/update')
        self.assertEqual(output.status_code, 302)

        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertEqual(output_text.count('title="PY C (pingou)"'), 1)

            csrf_token = self.get_csrf(output=output)

            data = {
                'status': 'Closed',
                'close_status': 'fixed'
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
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertFalse(
                '<option selected value="Fixed">Fixed</option>'
                in output_text)

            # Right status, wrong csrf
            data['close_status'] = 'Fixed'
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertFalse(
                '<option selected value="Fixed">Fixed</option>'
                in output_text)

            # status update - blocked, open_access doesn't allow changing status
            data['csrf_token'] = csrf_token
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertNotIn(
                'Issue close_status updated to: Fixed',
                output_text)
            self.assertNotIn(
                'Issue status updated to: Closed (was: Open)',
                output_text)
            self.assertNotIn(
                '<option selected value="Fixed">Fixed</option>',
                output_text)

            # Add new comment
            data = {
                'csrf_token': csrf_token,
                'status': 'Closed',
                'close_status': 'Fixed',
                'comment': 'Woohoo a second comment!',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertIn(
                'Comment added',
                output_text)
            self.assertNotIn(
                'No changes to edit',
                output_text)
            self.assertIn(
                '<p>Woohoo a second comment!</p>',
                output_text)
            self.assertEqual(
                output_text.count('comment_body">'), 2)
            self.assertNotIn(
                '<option selected value="Fixed">Fixed</option>',
                output_text)
            # 1: one for the original comment
            self.assertEqual(
                output_text.count('title="PY C (pingou)"'),
                1)

            # Add new tag
            data = {
                'csrf_token': csrf_token,
                'status': 'Closed',
                'close_status': 'Fixed',
                'tag': 'tag2',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertIn(
                '<p>Woohoo a second comment!</p>',
                output_text)
            self.assertEqual(
                output_text.count('comment_body">'), 2)
            self.assertNotIn(
                '<option selected value="Fixed">Fixed</option>',
                output_text)

            # Assign issue to an non-existent user
            data = {
                'csrf_token': csrf_token,
                'status': 'Closed',
                'close_status': 'Fixed',
                'assignee': 'ralph',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertIn(
                'No user &#34;ralph&#34; found',
                output_text)
            self.assertIn(
                '<p>Woohoo a second comment!</p>',
                output_text)
            self.assertEqual(
                output_text.count('comment_body">'), 2)
            self.assertNotIn(
                '<option selected value="Fixed">Fixed</option>',
                output_text)

            # Assign issue properly
            data = {
                'csrf_token': csrf_token,
                'status': 'Closed',
                'close_status': 'Fixed',
                'assignee': 'pingou',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertIn('Issue assigned to pingou', output_text)
            self.assertIn(
                '<a href="/test/issues?assignee=pingou" title="PY C (pingou)"',
                output_text)
            self.assertIn(
                '<p>Woohoo a second comment!</p>', output_text)
            self.assertEqual(
                output_text.count('comment_body">'), 2)
            self.assertNotIn(
                '<option selected value="Fixed">Fixed</option>',
                output_text)

        # Create another issue with a dependency
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Reset the status of the first issue
        parent_issue = pagure.lib.search_issues(
            self.session, repo, issueid=1)
        parent_issue.status = 'Open'
        self.session.add(parent_issue)
        # Add the dependency relationship
        self.session.add(parent_issue)
        issue = pagure.lib.search_issues(self.session, repo, issueid=2)
        issue.parents.append(parent_issue)
        self.session.add(issue)
        self.session.commit()

        with tests.user_set(self.app.application, user):

            data['csrf_token'] = csrf_token
            output = self.app.post(
                '/test/issue/2/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #2: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/2/edit" title="Edit this issue">',
                output_text)
            self.assertNotIn(
                'You cannot close a ticket '
                'that has ticket depending that are still open.',
                output_text)
            self.assertNotIn(
                '<option selected value="Open">Open</option>',
                output_text)

        # Create private issue
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Wrong user
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                '/test/issue/3/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        # Project w/o issue tracker
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        repo.settings = {'issue_tracker': False}
        self.session.add(repo)
        self.session.commit()

        with tests.user_set(self.app.application, user):
            # Repo not set-up for issue tracker
            output = self.app.post('/test/issue/1/update', data=data)
            self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_update_issue_depend(self):
        """ Test adding dependency via the update_issue endpoint. """
        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this again',
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)

            csrf_token = self.get_csrf(output=output)

            # Add a dependent ticket
            data = {
                'csrf_token': csrf_token,
                'depending': '2',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)

            # Add an invalid dependent ticket
            data = {
                'csrf_token': csrf_token,
                'depending': '2,abc',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertNotIn(
                'Successfully edited issue #1',
                output_text)

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.depending_text, [2])
        self.assertEqual(issue.blocking_text, [])

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_update_issue_block(self):
        """ Test adding blocked issue via the update_issue endpoint. """
        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this again',
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')

        # User is not an admin of the project
        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.get_data(as_text=True))

            csrf_token = self.get_csrf(output=output)

            # Add a dependent ticket
            data = {
                'csrf_token': csrf_token,
                'blocking': '2',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output.get_data(as_text=True))

            repo = pagure.lib.get_authorized_project(self.session, 'test')
            issue = pagure.lib.search_issues(self.session, repo, issueid=1)
            self.assertEqual(issue.depending_text, [])
            self.assertEqual(issue.blocking_text, [2])

            # Add an invalid dependent ticket
            data = {
                'csrf_token': csrf_token,
                'blocking': '2,abc',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertNotIn(
                'Successfully edited issue #1',
                output_text)

        self.session.commit()
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.depending_text, [])
        self.assertEqual(issue.blocking_text, [2])

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_update_issue_edit_comment(self):
        """ Test the issues edit comment endpoint """
        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                ' href="/test/issue/1/edit" title="Edit this issue">\n',
                output_text)

            csrf_token = self.get_csrf(output=output)

            # Add new comment
            data = {
                'csrf_token': csrf_token,
                'comment': 'Woohoo a second comment!',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                ' href="/test/issue/1/edit" title="Edit this issue">\n',
                output_text)
            self.assertIn('Comment added', output_text)
            self.assertIn(
                '<p>Woohoo a second comment!</p>',
                output_text)
            self.assertEqual(
                output_text.count('comment_body">'), 2)

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(
            issue.comments[0].comment,
            'Woohoo a second comment!')

        data = {
            'csrf_token': csrf_token,
            'edit_comment': 1,
            'update_comment': 'Updated comment',
        }

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            # Wrong issue id
            output = self.app.post(
                '/test/issue/3/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Wrong user
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            # Edit comment
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertIn('Comment updated', output_text)

        self.session.commit()
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.comments[0].comment, 'Updated comment')

        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1/comment/1/edit')
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>test - Pagure</title>', output_text)
            self.assertTrue('<div id="edit">' in output_text)
            self.assertTrue('<section class="edit_comment">' in output_text)
            self.assertTrue(
                '<textarea class="form-control" id="update_comment"'
                in output_text)

            csrf_token = self.get_csrf(output=output)

            data['csrf_token'] = csrf_token
            data['update_comment'] = 'Second update'

            # Edit the comment with the other endpoint
            output = self.app.post(
                '/test/issue/1/comment/1/edit',
                data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertIn('Comment updated', output_text)

        self.session.commit()
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.comments[0].comment, 'Second update')

        # Create another issue from someone else
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.status, 'Open')

        issue = pagure.lib.search_issues(self.session, repo, issueid=2)
        self.assertEqual(len(issue.comments), 0)
        self.assertEqual(issue.status, 'Open')

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            data = {
                'csrf_token': csrf_token,
                'comment': 'Nevermind figured it out',
                'status': 'Closed',
                'close_status': 'Invalid'
            }

            # Add a comment and close the ticket #1
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn('Successfully edited issue #1\n', output_text)
            self.assertIn('Comment added', output_text)
            self.assertIn(
                '<a class="btn btn-outline-primary border-0 btn-sm issue-metadata-display'
                ' editmetadatatoggle" href="javascript:void(0)" style="display: inline-block;">'
                '<i class="fa fa-fw fa-pencil">',
                output_text
            )

            data = {
                'csrf_token': csrf_token,
                'comment': 'Nevermind figured it out',
                'status': 'Closed',
                'close_status': 'Invalid'
            }

            # Add a comment and close the ticket #2
            output = self.app.post(
                '/test/issue/2/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Issue close_status updated to: Invalid',
                output_text
            )
            self.assertIn('Comment added', output_text)
            self.assertIn(
                'Issue status updated to: Closed (was: Open)',
                output_text
            )
            self.assertIn(
                '<a class="btn btn-outline-primary border-0 btn-sm issue-metadata-display'
                ' editmetadatatoggle" href="javascript:void(0)" style="display: inline-block;">'
                '<i class="fa fa-fw fa-pencil">',
                output_text
            )

        # Ticket #1 has one more comment and is still open
        self.session.commit()
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 2)
        self.assertEqual(issue.status, 'Open')

        # Ticket #2 has one less comment and is closed
        issue = pagure.lib.search_issues(self.session, repo, issueid=2)
        self.assertEqual(len(issue.comments), 2)
        self.assertEqual(
            issue.comments[0].comment,
            'Nevermind figured it out')
        self.assertEqual(
            issue.comments[1].comment,
            '**Metadata Update from @foo**:\n'
            '- Issue close_status updated to: Invalid\n'
            '- Issue status updated to: Closed (was: Open)')
        self.assertEqual(issue.status, 'Closed')

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_view_issue_closed(self):
        """ Test viewing a closed issue. """
        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)

            csrf_token = self.get_csrf(output=output)

            # Add new comment
            data = {
                'csrf_token': csrf_token,
                'status': 'Closed',
                'close_status': 'Fixed',
                'comment': 'Woohoo a second comment!',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                 ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text)
            self.assertIn('Comment added', output_text)
            self.assertIn(
                '<p>Woohoo a second comment!</p>', output_text)
            self.assertEqual(output_text.count('comment_body">'), 2)
            self.assertNotIn(
                '<option selected value="Fixed">Fixed</option>',
                output_text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
