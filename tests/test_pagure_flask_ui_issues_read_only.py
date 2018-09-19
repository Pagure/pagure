# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

import json
import unittest
import sys
import os

from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure  # noqa
import pagure.lib  # noqa
import tests  # noqa


class PagureFlaskIssuesReadOnlytests(tests.Modeltests):
    """ Tests for flask issues controller of pagure with read-only tickets
    """

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskIssuesReadOnlytests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        # Make the project's issue tracker read-only
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['issue_tracker_read_only'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        # Create a couple of issue
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')

        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
            private=False,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')

    def test_issue_list_authenticated_commit(self):
        """ Test the list of issues when user is authenticated and has
        access to the project.
        """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issues')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issues - test - Pagure</title>', output_text)
            self.assertIn(
                '<span class="fa fa-fw fa-exclamation-circle"></span>'
                ' 2 Open Issues\n', output_text)

    def test_field_comment(self):
        """ Test if the field commit is present on the issue page.
        """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue #1 - test - Pagure</title>',
                output_text)
            self.assertNotIn(
                'value="Update Issue" title="Comment and Update Metadata" '
                'tabindex=2 />', output_text)
            self.assertIn(
                'This issue tracker is read-only.', output_text)

    def test_update_ticket(self):
        """ Test updating a ticket.
        """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                '/test/issue/1/update', data={}, follow_redirects=True)
            self.assertEqual(output.status_code, 401)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Unauthorized :\'( - Pagure</title>', output_text)
            self.assertIn(
                '<p>The issue tracker for this project is read-only</p>',
                output_text)

    def test_edit_comment(self):
        """ Test editing a comment from a ticket.
        """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                '/test/issue/1/comment/1/edit', data={},
                follow_redirects=True)
            self.assertEqual(output.status_code, 401)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Unauthorized :\'( - Pagure</title>', output_text)
            self.assertIn(
                '<p>The issue tracker for this project is read-only</p>',
                output_text)

    def test_edit_ticket(self):
        """ Test editing a ticket.
        """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                '/test/issue/1/edit', data={}, follow_redirects=True)
            self.assertEqual(output.status_code, 401)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Unauthorized :\'( - Pagure</title>', output_text)
            self.assertIn(
                '<p>The issue tracker for this project is read-only</p>',
                output_text)

    def test_new_issue(self):
        """ Test creating a new ticket.
        """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/test/new_issue/', data={})
            self.assertEqual(output.status_code, 401)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Unauthorized :\'( - Pagure</title>', output_text)
            self.assertIn(
                '<p>The issue tracker for this project is read-only</p>',
                output_text)

    def test_deleting_issue(self):
        """ Test deleting a new ticket.
        """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/test/issue/1/drop', data={})
            self.assertEqual(output.status_code, 401)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Unauthorized :\'( - Pagure</title>', output_text)
            self.assertIn(
                '<p>The issue tracker for this project is read-only</p>',
                output_text)

    def test_uploading_to_issue(self):
        """ Test uploading to a new ticket.
        """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/test/issue/1/upload', data={})
            self.assertEqual(output.status_code, 401)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Unauthorized :\'( - Pagure</title>', output_text)
            self.assertIn(
                '<p>The issue tracker for this project is read-only</p>',
                output_text)


class PagureFlaskAPIIssuesReadOnlytests(PagureFlaskIssuesReadOnlytests):
    """ Tests for flask API issues controller of pagure with read-only tickets
    """

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskAPIIssuesReadOnlytests, self).setUp()

    def test_api_new_issue(self):
        """ Test creating a new ticket.
        """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/api/0/test/new_issue', data={})
            self.assertEqual(output.status_code, 401)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'error': u'The issue tracker of this project is read-only',
                    u'error_code': u'ETRACKERREADONLY'
                }
            )

    def test_api_change_status_issue(self):
        """ Test closing a ticket. """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/api/0/test/issue/1/status', data={})
            self.assertEqual(output.status_code, 401)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'error': u'The issue tracker of this project is read-only',
                    u'error_code': u'ETRACKERREADONLY'
                }
            )

    def test_api_change_milestone_issue(self):
        """ Test change the milestone of a ticket. """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/api/0/test/issue/1/milestone', data={})
            self.assertEqual(output.status_code, 401)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'error': u'The issue tracker of this project is read-only',
                    u'error_code': u'ETRACKERREADONLY'
                }
            )

    def test_api_comment_issue(self):
        """ Test comment on a ticket. """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/api/0/test/issue/1/comment', data={})
            self.assertEqual(output.status_code, 401)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'error': u'The issue tracker of this project is read-only',
                    u'error_code': u'ETRACKERREADONLY'
                }
            )

    def test_api_assign_issue(self):
        """ Test assigning a ticket. """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/api/0/test/issue/1/assign', data={})
            self.assertEqual(output.status_code, 401)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'error': u'The issue tracker of this project is read-only',
                    u'error_code': u'ETRACKERREADONLY'
                }
            )

    def test_api_subscribe_issue(self):
        """ Test subscribing to a ticket. """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/api/0/test/issue/1/subscribe', data={})
            self.assertEqual(output.status_code, 401)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'error': u'The issue tracker of this project is read-only',
                    u'error_code': u'ETRACKERREADONLY'
                }
            )

    def test_api_update_custom_field(self):
        """ Test updating a specific custom fields on a ticket. """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/api/0/test/issue/1/custom/foo', data={})
            self.assertEqual(output.status_code, 401)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'error': u'The issue tracker of this project is read-only',
                    u'error_code': u'ETRACKERREADONLY'
                }
            )

    def test_api_update_custom_fields(self):
        """ Test updating custom fields on a ticket. """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/api/0/test/issue/1/custom', data={})
            self.assertEqual(output.status_code, 401)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(
                data,
                {
                    u'error': u'The issue tracker of this project is read-only',
                    u'error_code': u'ETRACKERREADONLY'
                }
            )


class PagureFlaskIssuesAndPRDisabledtests(tests.Modeltests):
    """ Tests for flask issues controller of pagure with tickets and PRs
    disabled.
    """

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskIssuesAndPRDisabledtests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        # Make the project's issue tracker read-only
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        settings['issue_tracker_read_only'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        # Create a couple of issue
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')

        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
            private=False,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')

    def test_edit_tag(self):
        """ Test editing a ticket tag.
        """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/test/tag/tag1/edit', data={})
            self.assertEqual(output.status_code, 401)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Unauthorized :\'( - Pagure</title>', output_text)
            self.assertIn(
                '<p>The issue tracker for this project is read-only</p>',
                output_text)

    def test_drop_tags(self):
        """ Test dropping a ticket tag.
        """
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post('/test/droptag/', data={})
            self.assertEqual(output.status_code, 401)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Unauthorized :\'( - Pagure</title>', output_text)
            self.assertIn(
                '<p>The issue tracker for this project is read-only</p>',
                output_text)

if __name__ == '__main__':
    unittest.main(verbosity=2)
