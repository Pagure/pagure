# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

import unittest
import sys
import os

from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure  # noqa
import pagure.lib  # noqa
import tests  # noqa


class PagureFlaskIssuesPrivatetests(tests.Modeltests):
    """ Tests for flask issues controller of pagure with private tickets
    """

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskIssuesPrivatetests, self).setUp()

        # Create a 3rd user
        item = pagure.lib.model.User(
            user='random',
            fullname='Random user',
            password='foo',
            default_email='random@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='random@bar.com')
        self.session.add(item)
        self.session.commit()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
            private=True,
            ticketfolder=None
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
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')

    def test_issue_list_anonymous(self):
        """ Test the list of issues when user is logged out. """

        output = self.app.get('/test/issues')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>Issues - test - Pagure</title>', output_text)
        self.assertIn(
            '<span class="fa fa-fw fa-exclamation-circle"></span> 1 Open Issues\n', output_text)

    def test_issue_list_admin(self):
        """ Test the list of issues when user is an admin of the project.
        """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issues')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issues - test - Pagure</title>', output_text)
            self.assertIn(
                '<span class="fa fa-fw fa-exclamation-circle"></span> 2 Open Issues\n', output_text)

    def test_issue_list_author(self):
        """ Test the list of issues when user is an admin of the project.
        """

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issues')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issues - test - Pagure</title>', output_text)
            self.assertIn(
                '<span class="fa fa-fw fa-exclamation-circle"></span> 2 Open Issues\n', output_text)

    def test_issue_list_authenticated(self):
        """ Test the list of issues when user is authenticated but has no
        special access to the project.
        """

        user = tests.FakeUser(username='random')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issues')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issues - test - Pagure</title>', output_text)
            self.assertIn(
                '<span class="fa fa-fw fa-exclamation-circle"></span> 1 Open Issues\n', output_text)

    def test_issue_list_authenticated_ticket(self):
        """ Test the list of issues when user is authenticated but has
        ticket level access to the project.
        """
        repo = pagure.lib._get_project(self.session, 'test')
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='random',
            user='pingou',
            access='ticket',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        user = tests.FakeUser(username='random')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issues')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issues - test - Pagure</title>', output_text)
            self.assertIn(
                '<span class="fa fa-fw fa-exclamation-circle"></span> 1 Open Issues\n', output_text)

    def test_issue_list_authenticated_commit(self):
        """ Test the list of issues when user is authenticated but has
        commit level access to the project.
        """
        repo = pagure.lib._get_project(self.session, 'test')
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='random',
            user='pingou',
            access='commit',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        user = tests.FakeUser(username='random')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issues')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issues - test - Pagure</title>', output_text)
            self.assertIn(
                '<span class="fa fa-fw fa-exclamation-circle"></span> 2 Open Issues\n', output_text)

    def test_issue_list_authenticated_assigned(self):
        """ Test the list of issues when user is authenticated and is
        assigned to one of the issue.
        """

        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        issue.assignee_id = 3  # random
        self.session.add(issue)
        self.session.commit()

        user = tests.FakeUser(username='random')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issues')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issues - test - Pagure</title>', output_text)
            self.assertIn(
                '<span class="fa fa-fw fa-exclamation-circle"></span> 2 Open Issues\n', output_text)

    def test_view_issue_anonymous(self):
        """ Test accessing a private ticket when user is logged out. """

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

    def test_view_issue_admin(self):
        """ Test accessing a private ticket when user is an admin of the
        project.
        """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue #1 - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<span class="issueid badge badge-secondary">#1</span>\n',
                output_text)

    def test_view_issue_author(self):
        """ Test accessing a private ticket when user opened the ticket.
        """

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue #1 - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<span class="issueid badge badge-secondary">#1</span>\n',
                output_text)

    def test_view_issue_authenticated(self):
        """ Test accessing a private ticket when user is authenticated but
        has no special access to the project.
        """

        user = tests.FakeUser(username='random')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 404)

    def test_view_issue_authenticated_ticket(self):
        """ Test accessing a private ticket when user is authenticated and
        has ticket level access to the project.
        """
        repo = pagure.lib._get_project(self.session, 'test')
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='random',
            user='pingou',
            access='ticket',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        user = tests.FakeUser(username='random')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 404)

    def test_view_issue_authenticated_commit(self):
        """ Test accessing a private ticket when user is authenticated and
        has commit level access to the project.
        """
        repo = pagure.lib._get_project(self.session, 'test')
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='random',
            user='pingou',
            access='commit',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        user = tests.FakeUser(username='random')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue #1 - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<span class="issueid badge badge-secondary">#1</span>\n',
                output_text)

    def test_view_issue_authenticated_assigned(self):
        """ Test accessing a private ticket when user is authenticated and
        is assigned to one of the issue.
        """

        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        issue.assignee_id = 3  # random
        self.session.add(issue)
        self.session.commit()

        user = tests.FakeUser(username='random')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue #1 - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<span class="issueid badge badge-secondary">#1</span>\n',
                output_text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
