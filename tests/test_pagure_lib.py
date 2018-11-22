# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import datetime
import unittest
import shutil
import sys
import os

import markdown
from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib.query
import pagure.lib.model
import tests


class PagureLibtests_search_user(tests.Modeltests):
    """
    Test the pagure.lib search_user() method
    """

    maxDiff = None

    def test_search_user_all(self):
        """
        Test the method returns all the users for the given session
        """

        # Retrieve all users
        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(2, len(items))
        self.assertEqual(2, items[0].id)
        self.assertEqual('foo', items[0].user)
        self.assertEqual('foo', items[0].username)
        self.assertEqual([], items[1].groups)
        self.assertEqual(1, items[1].id)
        self.assertEqual('pingou', items[1].user)
        self.assertEqual('pingou', items[1].username)
        self.assertEqual([], items[1].groups)

    def test_search_user_username(self):
        """
        Test the method returns the user for a given username
        """

        # Retrieve user by username
        item = pagure.lib.query.search_user(self.session, username='foo')
        self.assertEqual('foo', item.user)
        self.assertEqual('foo', item.username)
        self.assertEqual([], item.groups)

        item = pagure.lib.query.search_user(self.session, username='bar')
        self.assertEqual(None, item)

    def test_search_user_email(self):
        """
        Test the method returns a user for a given email address
        """

        # Retrieve user by email
        item = pagure.lib.query.search_user(self.session, email='foo@foo.com')
        self.assertEqual(None, item)

        item = pagure.lib.query.search_user(self.session, email='foo@bar.com')
        self.assertEqual('foo', item.user)
        self.assertEqual('foo', item.username)
        self.assertEqual([], item.groups)
        self.assertEqual(
            ['foo@bar.com'], [email.email for email in item.emails])

        item = pagure.lib.query.search_user(self.session, email='foo@pingou.com')
        self.assertEqual('pingou', item.user)
        self.assertEqual(
            sorted(['bar@pingou.com', 'foo@pingou.com']),
            sorted([email.email for email in item.emails]))

    def test_search_user_token(self):
        """
        Test the method returns a user for a given token
        """

        # Retrieve user by token
        item = pagure.lib.query.search_user(self.session, token='aaa')
        self.assertEqual(None, item)

        item = pagure.lib.model.User(
            user='pingou2',
            fullname='PY C',
            token='aaabbb',
            default_email='bar@pingou.com',
        )
        self.session.add(item)
        self.session.commit()

        item = pagure.lib.query.search_user(self.session, token='aaabbb')
        self.assertEqual('pingou2', item.user)
        self.assertEqual('PY C', item.fullname)

    def test_search_user_pattern(self):
        """
        Test the method returns a user for a given pattern
        """

        # Retrieve user by pattern
        item = pagure.lib.query.search_user(self.session, pattern='a*')
        self.assertEqual([], item)

        item = pagure.lib.model.User(
            user='pingou2',
            fullname='PY C',
            token='aaabbb',
            default_email='bar@pingou.com',
        )
        self.session.add(item)
        self.session.commit()

        items = pagure.lib.query.search_user(self.session, pattern='p*')
        self.assertEqual(2, len(items))
        self.assertEqual(1, items[0].id)
        self.assertEqual('pingou', items[0].user)
        self.assertEqual('pingou', items[0].username)
        self.assertEqual([], items[0].groups)
        self.assertEqual(
            sorted(['bar@pingou.com', 'foo@pingou.com']),
            sorted([email.email for email in items[0].emails]))
        self.assertEqual(3, items[1].id)
        self.assertEqual('pingou2', items[1].user)
        self.assertEqual('pingou2', items[1].username)
        self.assertEqual([], items[1].groups)
        self.assertEqual(
            [], [email.email for email in items[1].emails])


class PagureLibtests_search_projects(tests.Modeltests):
    """
    Test the pagure.lib search_projects() method
    """

    def setUp(self):
        super(PagureLibtests_search_projects, self).setUp()
        tests.create_projects(self.session)

    def test_search_projects_all(self):
        """
        Test the method returns all the projects for the given session
        """

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 3)
        self.assertEqual(projects[0].id, 1)
        self.assertEqual(projects[1].id, 2)

    def test_search_projects_username(self):
        """
        Test the method returns all the projects for the given username
        """
        projects = pagure.lib.query.search_projects(self.session, username='foo')
        self.assertEqual(len(projects), 0)

        projects = pagure.lib.query.search_projects(self.session, username='pingou')
        self.assertEqual(len(projects), 3)
        self.assertEqual(projects[0].id, 1)
        self.assertEqual(projects[1].id, 2)

    def test_search_projects_start(self):
        """
        Test the method returns all the projects for the given start
        """
        projects = pagure.lib.query.search_projects(self.session, start=1)
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0].id, 2)

    def test_search_projects_limit(self):
        """
        Test the method returns all the projects for the given limit
        """
        projects = pagure.lib.query.search_projects(self.session, limit=1)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].id, 1)

    def test_search_projects_count(self):
        """
        Test the method returns the count of the projects
        """
        projects = pagure.lib.query.search_projects(self.session, count=True)
        self.assertEqual(projects, 3)

    def test_search_projects_commit_access(self):
        """
        Test the method returns the project of user with only commit access
        """
        # Also check if the project shows up if a user doesn't
        # have admin access in the project
        # Check with commit access first
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='commit'
        )

        self.assertEqual(msg, 'User added')
        self.session.commit()
        projects = pagure.lib.query.search_projects(self.session, username='foo')
        self.assertEqual(len(projects), 1)

    def test_search_projects_ticket_access(self):
        """
        Test the method does not returns the project of user with only ticket access
        """
        # Now check with only ticket access
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='ticket'
        )
        self.assertEqual(msg, 'User added')
        self.session.commit()
        projects = pagure.lib.query.search_projects(self.session, username='foo')
        self.assertEqual(len(projects), 0)

    def test_search_project_forked(self):
        """
        Test the search_project for forked projects in pagure.lib.query.
        """

        # Create two forked repo
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            description='test project #1',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbttt',
        )
        self.session.add(item)

        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test2',
            description='test project #2',
            is_fork=True,
            parent_id=2,
            hook_token='aaabbbuuu',
        )
        self.session.add(item)

        # Since we have two forks, let's search them
        projects = pagure.lib.query.search_projects(self.session, fork=True)
        self.assertEqual(len(projects), 2)
        projects = pagure.lib.query.search_projects(self.session, fork=False)
        self.assertEqual(len(projects), 3)

    def test_search_projects_private(self):
        """
        Test the method for private projects
        """

        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='private_test',
            description='Private test project #1',
            hook_token='aaabbbcccpp',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        # non authenticated
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 3)
        self.assertEqual(
            [p.path for p in projects],
            ['test.git', 'test2.git',
             'somenamespace/test3.git']
        )

        # non authenticated
        projects = pagure.lib.query.search_projects(
            self.session, username='pingou')
        self.assertEqual(len(projects), 3)
        self.assertEqual(
            [p.path for p in projects],
            ['test.git', 'test2.git',
             'somenamespace/test3.git']
        )

        # authenticated as pingou
        projects = pagure.lib.query.search_projects(
            self.session, username='pingou', private='pingou')
        self.assertEqual(len(projects), 4)
        self.assertEqual(
            [p.path for p in projects],
            ['private_test.git', 'test.git', 'test2.git',
             'somenamespace/test3.git']
        )

        # authenticated as foo
        projects = pagure.lib.query.search_projects(
            self.session, username='pingou', private='foo')
        self.assertEqual(len(projects), 3)
        self.assertEqual(
            [p.path for p in projects],
            ['test.git', 'test2.git',
             'somenamespace/test3.git']
        )

    def test_search_projects_tags(self):
        """
        Test the method returns all the projects for the given tags
        """

        # Add tags to the project
        project = pagure.lib.query._get_project(self.session, 'test')
        tag = pagure.lib.model.Tag(
            tag='fedora'
        )
        self.session.add(tag)
        self.session.commit()
        tp = pagure.lib.model.TagProject(
            project_id=project.id,
            tag='fedora'
        )
        self.session.add(tp)
        self.session.commit()

        projects = pagure.lib.query.search_projects(
            self.session, tags='fedora')
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].path, 'test.git')

    def test_search_projects_pattern(self):
        """
        Test the method returns all the projects for the given pattern
        """

        projects = pagure.lib.query.search_projects(
            self.session, pattern='test*')
        self.assertEqual(len(projects), 3)
        self.assertEqual(
            [p.path for p in projects],
            ['test.git', 'test2.git', 'somenamespace/test3.git']
        )

    def test_search_projects_sort(self):
        """
        Test the method returns all the projects sorted by lastest and oldest
        """

        projects = pagure.lib.query.search_projects(
            self.session, pattern='*', sort='latest')
        self.assertEqual(len(projects), 3)
        self.assertEqual(
            [p.path for p in projects],
            ['somenamespace/test3.git', 'test2.git', 'test.git']
        )

        projects = pagure.lib.query.search_projects(
            self.session, pattern='*', sort='oldest')
        self.assertEqual(len(projects), 3)
        self.assertEqual(
            [p.path for p in projects],
            ['test.git', 'test2.git', 'somenamespace/test3.git']
        )


class PagureLibtests(tests.Modeltests):
    """ Tests for pagure.lib """

    maxDiff = None

    def test_get_repotypes(self):
        """ Test the get_repotypes function of pagure.lib.query. """
        with patch.dict(pagure.config.config,
                        {"ENABLE_TICKETS": False, "ENABLE_DOCS": False}):
            self.assertEqual(
                set(("main", "requests")),
                set(pagure.lib.query.get_repotypes())
            )

        with patch.dict(pagure.config.config,
                        {"ENABLE_TICKETS": True, "ENABLE_DOCS": False}):
            self.assertEqual(
                set(("main", "requests", "tickets")),
                set(pagure.lib.query.get_repotypes())
            )

        with patch.dict(pagure.config.config,
                        {"ENABLE_TICKETS": False, "ENABLE_DOCS": True}):
            self.assertEqual(
                set(("main", "requests", "docs")),
                set(pagure.lib.query.get_repotypes())
            )

        with patch.dict(pagure.config.config,
                        {"ENABLE_TICKETS": True, "ENABLE_DOCS": True}):
            self.assertEqual(
                set(("main", "requests", "tickets", "docs")),
                set(pagure.lib.query.get_repotypes())
            )

    def test_get_next_id(self):
        """ Test the get_next_id function of pagure.lib.query. """
        tests.create_projects(self.session)
        self.assertEqual(1, pagure.lib.query.get_next_id(self.session, 1))

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_new_issue(self, p_send_email, p_ugt):
        """ Test the new_issue of pagure.lib.query. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        repo = pagure.lib.query._get_project(self.session, 'test')
        # Set some priorities to the project
        repo.priorities = {'1': 'High', '2': 'Normal'}
        self.session.add(repo)
        self.session.commit()

        # Before
        issues = pagure.lib.query.search_issues(self.session, repo)
        self.assertEqual(len(issues), 0)
        self.assertEqual(repo.open_tickets, 0)
        self.assertEqual(repo.open_tickets_public, 0)

        # See where it fails
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.new_issue,
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='blah',
        )

        # Fails since we're trying to give a non-existant priority
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.new_issue,
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            priority=0,
        )

        # Add an extra user to project `foo`
        repo = pagure.lib.query._get_project(self.session, 'test')
        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou'
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # Try adding again this extra user to project `foo`
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_user_to_project,
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou'
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # Create issues to play with
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')
        self.assertEqual(repo.open_tickets, 1)
        self.assertEqual(repo.open_tickets_public, 1)

        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')
        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

        # After
        issues = pagure.lib.query.search_issues(self.session, repo)
        self.assertEqual(len(issues), 2)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_edit_issue(self, p_send_email, p_ugt):
        """ Test the edit_issue of pagure.lib.query. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()

        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)

        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

        # Edit the issue
        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, None)

        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            title='Test issue #2',
            content='We should work on this for the second time',
            status='Open',
        )
        self.session.commit()
        self.assertEqual(msg, None)

        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            title='Foo issue #2',
            content='We should work on this period',
            status='Closed',
            close_status='Invalid',
            private=True,
        )
        self.session.commit()
        self.assertEqual(
            msg,
            [
                'Issue status updated to: Closed (was: Open)',
                'Issue close_status updated to: Invalid',
                'Issue private status set to: True'
            ]
        )

        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            title='Foo issue #2',
            content='Fixed!',
            status='Closed',
            close_status='Fixed',
            private=False,
        )
        self.session.commit()
        self.assertEqual(
            msg,
            [
                'Issue close_status updated to: Fixed (was: Invalid)',
                'Issue private status set to: False (was: True)'
            ]
        )

        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(repo.open_tickets, 1)
        self.assertEqual(repo.open_tickets_public, 1)
        self.assertEqual(repo.issues[1].status, 'Closed')
        self.assertEqual(repo.issues[1].close_status, 'Fixed')

        # Edit the status: re-open the ticket
        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            status='Open',
            private=True,
        )
        self.session.commit()
        self.assertEqual(
            msg,
            [
                'Issue status updated to: Open (was: Closed)',
                'Issue private status set to: True'
            ]
        )

        repo = pagure.lib.query._get_project(self.session, 'test')
        for issue in repo.issues:
            self.assertEqual(issue.status, 'Open')
            self.assertEqual(issue.close_status, None)
        # 2 open but one of them is private
        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 1)

        # Edit the status: re-close the ticket
        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            status='Closed',
            close_status='Invalid',
            private=True,
        )
        self.session.commit()
        self.assertEqual(
            msg,
            [
                'Issue status updated to: Closed (was: Open)',
                'Issue close_status updated to: Invalid'
            ]
        )

        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(repo.open_tickets, 1)
        self.assertEqual(repo.open_tickets_public, 1)
        self.assertEqual(repo.issues[1].status, 'Closed')
        self.assertEqual(repo.issues[1].close_status, 'Invalid')

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_edit_issue_close_status(self, p_send_email, p_ugt):
        """ Test the edit_issue of pagure.lib.query. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()

        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)
        self.assertEqual(issue.status, 'Open')
        self.assertEqual(issue.close_status, None)

        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

        # Edit the issue, providing just a close_status should also close
        # the ticket
        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            close_status='Fixed',
        )
        self.session.commit()
        self.assertEqual(msg, ['Issue close_status updated to: Fixed'])

        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)
        self.assertEqual(issue.status, 'Closed')
        self.assertEqual(issue.close_status, 'Fixed')

        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(repo.open_tickets, 1)
        self.assertEqual(repo.open_tickets_public, 1)

        # Edit the issue, editing the status to open, should reset the
        # close_status
        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            status='Open',
        )
        self.session.commit()
        self.assertEqual(
            msg, ['Issue status updated to: Open (was: Closed)'])

        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)
        self.assertEqual(issue.status, 'Open')
        self.assertEqual(issue.close_status, None)

        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_edit_issue_priority(self, p_send_email, p_ugt):
        """ Test the edit_issue of pagure.lib when changing the priority.
        """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)

        # Set some priorities to the repo
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        repo.priorities = {'1': 'High', '2': 'Normal'}
        self.session.add(repo)
        self.session.commit()

        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

        # Edit the issue -- Wrong priority value: No changes
        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            priority=3,
        )
        self.session.commit()
        self.assertEqual(msg, None)

        # Edit the issue -- Good priority
        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            priority=2,
        )
        self.session.commit()
        self.assertEqual(
            msg,
            [
                'Issue priority set to: Normal'
            ]
        )

        # Edit the issue -- Update priority
        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            priority=1,
        )
        self.session.commit()
        self.assertEqual(
            msg,
            [
                'Issue priority set to: High (was: Normal)'
            ]
        )

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_edit_issue_depending(self, p_send_email, p_ugt):
        """ Test the edit_issue of pagure.lib when the issue depends on
        another.
        """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')

        # Create 3 issues
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')

        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')

        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #3',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #3')

        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)

        self.assertEqual(repo.open_tickets, 3)
        self.assertEqual(repo.open_tickets_public, 3)

        # Make issue #2 blocking on issue #1
        msgs = pagure.lib.query.update_blocked_issue(
            self.session,
            repo,
            issue,
            blocks=['1'],
            username='pingou',
        )
        self.assertEqual(msgs, ['Issue marked as blocking: #1'])

        # Make issue #2 depend on issue #3
        msgs = pagure.lib.query.update_dependency_issue(
            self.session,
            repo,
            issue,
            depends=['3'],
            username='pingou',
        )
        self.assertEqual(msgs, ['Issue marked as depending on: #3'])

        # Edit the issue #3
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=3)
        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, None)

        msg = pagure.lib.query.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            title='Foo issue #2',
            content='We should work on this period',
            status='Closed',
            close_status='Invalid',
            private=True,
        )
        self.session.commit()
        self.assertEqual(
            msg,
            [
                'Issue status updated to: Closed (was: Open)',
                'Issue close_status updated to: Invalid',
                'Issue private status set to: True'
            ]
        )

        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

    @patch('pagure.lib.query.REDIS', MagicMock(return_value=True))
    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_add_issue_dependency(self):
        """ Test the add_issue_dependency of pagure.lib.query. """

        self.test_new_issue()
        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        issue_blocked = pagure.lib.query.search_issues(
            self.session, repo, issueid=2)

        # Before
        self.assertEqual(issue.parents, [])
        self.assertEqual(issue.children, [])
        self.assertEqual(issue_blocked.parents, [])
        self.assertEqual(issue_blocked.children, [])

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_issue_dependency,
            session=self.session,
            issue=issue,
            issue_blocked=issue,
            user='pingou',
        )

        msg = pagure.lib.query.add_issue_dependency(
            session=self.session,
            issue=issue,
            issue_blocked=issue_blocked,
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue marked as depending on: #2')

        # After
        self.assertEqual(len(issue.parents), 0)
        self.assertEqual(issue.parents, [])
        self.assertEqual(len(issue.children), 1)
        self.assertEqual(issue.children[0].id, 2)
        self.assertEqual(issue.depending_text, [])
        self.assertEqual(issue.blocking_text, [2])

        self.assertEqual(len(issue_blocked.children), 0)
        self.assertEqual(issue_blocked.children, [])
        self.assertEqual(len(issue_blocked.parents), 1)
        self.assertEqual(issue_blocked.parents[0].id, 1)
        self.assertEqual(issue_blocked.depending_text, [1])
        self.assertEqual(issue_blocked.blocking_text, [])

    @patch('pagure.lib.query.REDIS')
    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_edit_comment(self, mock_redis):
        """ Test the edit_issue of pagure.lib.query. """
        mock_redis.return_value = True

        self.test_add_issue_comment()

        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

        self.assertEqual(mock_redis.publish.call_count, 0)

        # Before
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.comments[0].comment, 'Hey look a comment!')

        # Edit one of the
        msg = pagure.lib.query.edit_comment(
            session=self.session,
            parent=issue,
            comment=issue.comments[0],
            user='pingou',
            updated_comment='Edited comment',
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment updated')
        self.assertEqual(mock_redis.publish.call_count, 1)

        # After
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.comments[0].comment, 'Edited comment')

    @patch('pagure.lib.query.REDIS')
    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_edit_comment_private(self, mock_redis):
        """ Test the edit_issue of pagure.lib.query. """

        self.test_add_issue_comment_private()

        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(repo.open_tickets, 1)
        self.assertEqual(repo.open_tickets_public, 0)

        self.assertEqual(mock_redis.publish.call_count, 0)

        # Before
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.comments[0].comment, 'Hey look a comment!')

        # Edit one of the
        msg = pagure.lib.query.edit_comment(
            session=self.session,
            parent=issue,
            comment=issue.comments[0],
            user='pingou',
            updated_comment='Edited comment',
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment updated')
        self.assertEqual(mock_redis.publish.call_count, 1)

        # After
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.comments[0].comment, 'Edited comment')

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    @patch('pagure.lib.query.REDIS')
    def test_add_tag_obj(self, mock_redis):
        """ Test the add_tag_obj of pagure.lib.query. """
        mock_redis.return_value=True

        self.test_edit_issue()
        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertFalse(issue.private)
        self.assertFalse(issue.project.private)

        args = mock_redis.publish.call_args_list
        self.assertEqual(len(args), 4)

        # Add a tag to the issue
        msg = pagure.lib.query.add_tag_obj(
            session=self.session,
            obj=issue,
            tags='tag1',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue tagged with: tag1')

        args = mock_redis.publish.call_args_list
        self.assertEqual(len(args), 5)
        # Get the arguments of the last call and get the second of these
        # arguments (the first one changing for each test run)
        self.assertJSONEqual(
            args[-1:][0][0][1],
            '{"added_tags_color": ["DeepSkyBlue"], "added_tags": ["tag1"]}'
        )

        # Try a second time
        msg = pagure.lib.query.add_tag_obj(
            session=self.session,
            obj=issue,
            tags='tag1',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Nothing to add')

        issues = pagure.lib.query.search_issues(self.session, repo, tags='tag1')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 1)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual([tag.tag for tag in issues[0].tags], ['tag1'])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_remove_tags(self, p_send_email, p_ugt):
        """ Test the remove_tags of pagure.lib.query. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_add_tag_obj()
        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.remove_tags,
            session=self.session,
            project=repo,
            tags='foo',
            user='pingou',
        )

        msgs = pagure.lib.query.remove_tags(
            session=self.session,
            project=repo,
            tags='tag1',
            user='pingou',
        )

        self.assertEqual(msgs, ['Tag: tag1 has been deleted'])

    @patch('pagure.lib.query.REDIS', MagicMock(return_value=True))
    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_remove_tags_obj(self):
        """ Test the remove_tags_obj of pagure.lib.query. """

        self.test_add_tag_obj()
        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)

        msgs = pagure.lib.query.remove_tags_obj(
            session=self.session,
            obj=issue,
            tags='tag1',
            user='pingou',
        )
        self.assertEqual(msgs, 'Issue **un**tagged with: tag1')

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_remove_tags_obj_from_project(self, p_send_email, p_ugt):
        """ Test the remove_tags_obj of pagure.lib from a project. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)

        # Add a tag to the project
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        msg = pagure.lib.query.add_tag_obj(
            self.session, repo,
            tags=['pagure', 'test'],
            user='pingou',
        )
        self.assertEqual(msg, 'Project tagged with: pagure, test')
        self.session.commit()

        # Check the tags
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        self.assertEqual(repo.tags_text, ['pagure', 'test'])

        # Remove one of the the tag
        msgs = pagure.lib.query.remove_tags_obj(
            session=self.session,
            obj=repo,
            tags='test',
            user='pingou',
        )
        self.assertEqual(msgs, 'Project **un**tagged with: test')
        self.session.commit()

        # Check the tags
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        self.assertEqual(repo.tags_text, ['pagure'])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_edit_issue_tags(self, p_send_email, p_ugt):
        """ Test the edit_issue_tags of pagure.lib.query. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_add_tag_obj()
        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.edit_issue_tags,
            session=self.session,
            project=repo,
            old_tag='foo',
            new_tag='bar',
            new_tag_description='lorem ipsum',
            new_tag_color='black',
            user='pingou',
        )

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.edit_issue_tags,
            session=self.session,
            project=repo,
            old_tag=None,
            new_tag='bar',
            new_tag_description='lorem ipsum',
            new_tag_color='black',
            user='pingou',
        )

        msgs = pagure.lib.query.edit_issue_tags(
            session=self.session,
            project=repo,
            old_tag='tag1',
            new_tag='tag2',
            new_tag_description='lorem ipsum',
            new_tag_color='black',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(
            msgs,
            ['Edited tag: tag1()[DeepSkyBlue] to tag2(lorem ipsum)[black]']
        )

        # Try editing the tag without changing anything
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.edit_issue_tags,
            session=self.session,
            project=repo,
            old_tag='tag2',
            new_tag='tag2',
            new_tag_description='lorem ipsum',
            new_tag_color='black',
            user='pingou',
        )

        # Add a new tag
        msg = pagure.lib.query.add_tag_obj(
            session=self.session,
            obj=issue,
            tags='tag3',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue tagged with: tag3')
        self.assertEqual([tag.tag for tag in issue.tags], ['tag2', 'tag3'])

        # Attempt to rename an existing tag into another existing one
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.edit_issue_tags,
            session=self.session,
            project=repo,
            old_tag='tag2',
            new_tag='tag3',
            new_tag_description='lorem ipsum',
            new_tag_color='red',
            user='pingou',
        )

        # Rename an existing tag
        msgs = pagure.lib.query.edit_issue_tags(
            session=self.session,
            project=repo,
            old_tag='tag2',
            new_tag='tag4',
            new_tag_description='ipsum lorem',
            new_tag_color='purple',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msgs, ['Edited tag: tag2(lorem ipsum)[black] to tag4(ipsum lorem)[purple]'])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_search_issues(self, p_send_email, p_ugt):
        """ Test the search_issues of pagure.lib.query. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_edit_issue()
        repo = pagure.lib.query._get_project(self.session, 'test')

        # All issues
        issues = pagure.lib.query.search_issues(self.session, repo)
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[1].id, 1)
        self.assertEqual(issues[1].project_id, 1)
        self.assertEqual(issues[1].status, 'Open')
        self.assertEqual(issues[1].tags, [])
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Closed')
        self.assertEqual(issues[0].close_status, 'Invalid')
        self.assertEqual(issues[0].tags, [])

        # Issues by status
        issues = pagure.lib.query.search_issues(
            self.session, repo, status='Closed')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Closed')
        self.assertEqual(issues[0].close_status, 'Invalid')
        self.assertEqual(issues[0].tags, [])

        # Issues closed
        issues = pagure.lib.query.search_issues(
            self.session, repo, closed=True)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Closed')
        self.assertEqual(issues[0].close_status, 'Invalid')
        self.assertEqual(issues[0].tags, [])

        # Issues by tag
        issues = pagure.lib.query.search_issues(self.session, repo, tags='foo')
        self.assertEqual(len(issues), 0)
        issues = pagure.lib.query.search_issues(self.session, repo, tags='!foo')
        self.assertEqual(len(issues), 2)

        # Issue by id
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.title, 'Test issue')
        self.assertEqual(issue.user.user, 'pingou')
        self.assertEqual(issue.tags, [])

        # Issues by authors
        issues = pagure.lib.query.search_issues(self.session, repo, author='foo')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Closed')
        self.assertEqual(issues[0].close_status, 'Invalid')
        self.assertEqual(issues[0].tags, [])

        # Issues by assignee
        issues = pagure.lib.query.search_issues(self.session, repo, assignee='foo')
        self.assertEqual(len(issues), 0)
        issues = pagure.lib.query.search_issues(self.session, repo, assignee='!foo')
        self.assertEqual(len(issues), 2)

        issues = pagure.lib.query.search_issues(self.session, repo, private='foo')
        self.assertEqual(len(issues), 2)

    @patch('pagure.lib.query.REDIS', MagicMock(return_value=True))
    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_add_issue_assignee(self):
        """ Test the add_issue_assignee of pagure.lib.query. """

        self.test_new_issue()
        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)

        # Before
        issues = pagure.lib.query.search_issues(
            self.session, repo, assignee='pingou')
        self.assertEqual(len(issues), 0)

        # Test when it fails
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_issue_assignee,
            session=self.session,
            issue=issue,
            assignee='foo@foobar.com',
            user='foo@pingou.com',
        )

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_issue_assignee,
            session=self.session,
            issue=issue,
            assignee='foo@bar.com',
            user='foo@foopingou.com',
        )

        # Set the assignee by its email
        msg = pagure.lib.query.add_issue_assignee(
            session=self.session,
            issue=issue,
            assignee='foo@bar.com',
            user='foo@pingou.com',
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue assigned to foo@bar.com')

        # Change the assignee to someone else by its username
        msg = pagure.lib.query.add_issue_assignee(
            session=self.session,
            issue=issue,
            assignee='pingou',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue assigned to pingou (was: foo)')

        # After  -- Searches by assignee
        issues = pagure.lib.query.search_issues(
            self.session, repo, assignee='pingou')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual(issues[0].tags, [])

        issues = pagure.lib.query.search_issues(
            self.session, repo, assignee=True)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].title, 'Test issue #2')
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual(issues[0].tags, [])

        issues = pagure.lib.query.search_issues(
            self.session, repo, assignee=False)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 1)
        self.assertEqual(issues[0].title, 'Test issue')
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual(issues[0].tags, [])

        # Reset the assignee to no-one
        msg = pagure.lib.query.add_issue_assignee(
            session=self.session,
            issue=issue,
            assignee=None,
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Assignee reset')

        issues = pagure.lib.query.search_issues(
            self.session, repo, assignee=False)
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[1].id, 1)

        issues = pagure.lib.query.search_issues(
            self.session, repo, assignee=True)
        self.assertEqual(len(issues), 0)

    @patch('pagure.lib.query.REDIS', MagicMock(return_value=True))
    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_add_issue_comment(self):
        """ Test the add_issue_comment of pagure.lib.query. """

        self.test_new_issue()
        repo = pagure.lib.query._get_project(self.session, 'test')

        # Before
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        # Set the assignee by its email
        msg = pagure.lib.query.add_issue_assignee(
            session=self.session,
            issue=issue,
            assignee='foo@bar.com',
            user='foo@pingou.com',
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue assigned to foo@bar.com')

        # Add a comment to that issue
        msg = pagure.lib.query.add_issue_comment(
            session=self.session,
            issue=issue,
            comment='Hey look a comment!',
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        # After
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.comments[0].comment, 'Hey look a comment!')
        self.assertEqual(issue.comments[0].user.user, 'foo')

    @patch('pagure.lib.query.REDIS', MagicMock(return_value=True))
    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_add_issue_comment_private(self):
        """ Test the add_issue_comment of pagure.lib.query. """
        tests.create_projects(self.session)
        project = pagure.lib.query._get_project(self.session, 'test')

        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=project,
            title='Test issue #1',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')
        self.assertEqual(project.open_tickets, 1)
        self.assertEqual(project.open_tickets_public, 0)

        # Before
        issue = pagure.lib.query.search_issues(self.session, project, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        # Add a comment to that issue
        msg = pagure.lib.query.add_issue_comment(
            session=self.session,
            issue=issue,
            comment='Hey look a comment!',
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        # After
        issue = pagure.lib.query.search_issues(self.session, project, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.comments[0].comment, 'Hey look a comment!')
        self.assertEqual(issue.comments[0].user.user, 'foo')

    @patch('pagure.lib.notify.send_email')
    def test_add_user_to_project(self, p_send_email):
        """ Test the add_user_to_project of pagure.lib.query. """
        p_send_email.return_value = True

        tests.create_projects(self.session)

        # Before
        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(len(repo.users), 0)

        # Add an user to a project
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_user_to_project,
            session=self.session,
            project=repo,
            new_user='foobar',
            user='pingou',
        )

        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # After
        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(len(repo.users), 1)
        self.assertEqual(repo.users[0].user, 'foo')
        self.assertEqual(repo.admins[0].user, 'foo')

        # Try adding the same user with the same access
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_user_to_project,
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='admin'
        )

        # Update the access of the user
        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')
        self.assertEqual(len(repo.users), 1)
        self.assertEqual(repo.users[0].user, 'foo')
        self.assertEqual(repo.committers[0].user, 'foo')

    def test_new_project(self):
        """ Test the new_project of pagure.lib.query. """
        gitfolder = os.path.join(self.path, 'repos')
        docfolder = os.path.join(gitfolder, 'docs')
        ticketfolder = os.path.join(gitfolder, 'tickets')
        requestfolder = os.path.join(gitfolder, 'requests')

        # Try creating a blacklisted project
        self.assertRaises(
            pagure.exceptions.ProjectBlackListedException,
            pagure.lib.query.new_project,
            session=self.session,
            user='pingou',
            name='static',
            repospanner_region=None,
            blacklist=['static'],
            allowed_prefix=[],
            description='description for static',
            parent_id=None,
        )

        # Try creating a project that's blacklisted by wildcard match
        self.assertRaises(
            pagure.exceptions.ProjectBlackListedException,
            pagure.lib.query.new_project,
            session=self.session,
            user='pingou',
            namespace='space',
            name='static',
            repospanner_region=None,
            blacklist=['space/*'],
            allowed_prefix=[],
            description='description for static',
            parent_id=None,
        )

        # Try creating a 40 chars project
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.new_project,
            session=self.session,
            user='pingou',
            name='s' * 40,
            namespace='pingou',
            repospanner_region=None,
            blacklist=['static'],
            allowed_prefix=['pingou'],
            description='description for 40 chars length project',
            parent_id=None,
            prevent_40_chars=True,
        )

        # Create a new project
        pagure.config.config['GIT_FOLDER'] = gitfolder
        task = pagure.lib.query.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            repospanner_region=None,
            blacklist=[],
            allowed_prefix=[],
            description='description for testproject',
            parent_id=None,
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {'endpoint': 'ui_ns.view_repo',
             'repo': 'testproject',
             'namespace': None})

        # Try creating an existing project using a different case
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.new_project,
            session=self.session,
            user='pingou',
            name='TestProject',
            repospanner_region=None,
            blacklist=[],
            allowed_prefix=[],
            description='description for testproject',
            parent_id=None,
        )

        # Now test that creation fails if ignore_existing_repo is False
        self.session.commit()
        repo = pagure.lib.query.get_authorized_project(self.session, 'testproject')
        self.assertEqual(repo.path, 'testproject.git')

        gitrepo = os.path.join(gitfolder, repo.path)
        docrepo = os.path.join(docfolder, repo.path)
        ticketrepo = os.path.join(ticketfolder, repo.path)
        requestrepo = os.path.join(requestfolder, repo.path)

        self.assertTrue(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Try re-creating it but all repos are existing
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.new_project,
            session=self.session,
            user='pingou',
            name='testproject',
            repospanner_region=None,
            blacklist=[],
            allowed_prefix=[],
            description='description for testproject',
            parent_id=None
        )
        self.session.rollback()

        self.assertTrue(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Try re-creating it ignoring the existing repos- but repo in the DB
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.new_project,
            session=self.session,
            user='pingou',
            name='testproject',
            repospanner_region=None,
            blacklist=[],
            allowed_prefix=[],
            description='description for testproject',
            parent_id=None
        )
        self.session.rollback()

        # Re-create it, ignoring the existing repos on disk
        repo = pagure.lib.query._get_project(self.session, 'testproject')
        self.session.delete(repo)
        self.session.commit()

        task = pagure.lib.query.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            repospanner_region=None,
            blacklist=[],
            allowed_prefix=[],
            description='description for testproject',
            parent_id=None,
            ignore_existing_repo=True
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {'endpoint': 'ui_ns.view_repo',
             'repo': 'testproject',
             'namespace': None})

        # Delete the repo from the DB so we can try again
        repo = pagure.lib.query._get_project(self.session, 'testproject')
        self.session.delete(repo)
        self.session.commit()

        self.assertTrue(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Drop the main git repo and try again
        shutil.rmtree(gitrepo)
        task = pagure.lib.query.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            repospanner_region=None,
            blacklist=[],
            allowed_prefix=[],
            description='description for testproject',
            parent_id=None)
        self.assertIn(
            'already exists',
            str(task.get(propagate=False)))

        self.assertFalse(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Drop the doc repo and try again
        shutil.rmtree(docrepo)
        with self.assertRaises(pagure.exceptions.RepoExistsException):
            task = pagure.lib.query.new_project(
                session=self.session,
                user='pingou',
                name='testproject',
                repospanner_region=None,
                blacklist=[],
                allowed_prefix=[],
                description='description for testproject',
                parent_id=None,
            )
            task.get()
        self.assertFalse(os.path.exists(gitrepo))
        self.assertFalse(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Drop the request repo and try again
        shutil.rmtree(ticketrepo)
        with self.assertRaises(pagure.exceptions.RepoExistsException):
            task = pagure.lib.query.new_project(
                session=self.session,
                user='pingou',
                name='testproject',
                repospanner_region=None,
                blacklist=[],
                allowed_prefix=[],
                description='description for testproject',
                parent_id=None,
            )
            task.get()
        self.assertFalse(os.path.exists(gitrepo))
        self.assertFalse(os.path.exists(docrepo))
        self.assertFalse(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Re-Try creating a 40 chars project this time allowing it
        task = pagure.lib.query.new_project(
            session=self.session,
            user='pingou',
            name='pingou/' + 's' * 40,
            repospanner_region=None,
            blacklist=['static'],
            allowed_prefix=['pingou'],
            description='description for 40 chars length project',
            parent_id=None,
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {'endpoint': 'ui_ns.view_repo',
             'repo': 'pingou/ssssssssssssssssssssssssssssssssssssssss',
             'namespace': None})

    def test_new_project_user_ns(self):
        """ Test the new_project of pagure.lib with user_ns on. """
        gitfolder = os.path.join(self.path, 'repos')
        docfolder = os.path.join(gitfolder, 'docs')
        ticketfolder = os.path.join(gitfolder, 'tickets')
        requestfolder = os.path.join(gitfolder, 'requests')

        # Create a new project with user_ns as True
        pagure.config.config['GIT_FOLDER'] = gitfolder
        task = pagure.lib.query.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            repospanner_region=None,
            blacklist=[],
            allowed_prefix=[],
            description='description for testproject',
            parent_id=None,
            user_ns=True,
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {'endpoint': 'ui_ns.view_repo',
             'repo': 'testproject',
             'namespace': 'pingou'})

        repo = pagure.lib.query._get_project(
            self.session, 'testproject', namespace='pingou')
        self.assertEqual(repo.path, 'pingou/testproject.git')

        gitrepo = os.path.join(gitfolder, repo.path)
        docrepo = os.path.join(docfolder, repo.path)
        ticketrepo = os.path.join(ticketfolder, repo.path)
        requestrepo = os.path.join(requestfolder, repo.path)

        for path in [gitrepo, docrepo, ticketrepo, requestrepo]:
            self.assertTrue(os.path.exists(path))
            shutil.rmtree(path)

        # Create a new project with a namespace and user_ns as True
        pagure.config.config['GIT_FOLDER'] = gitfolder
        task = pagure.lib.query.new_project(
            session=self.session,
            user='pingou',
            name='testproject2',
            namespace='testns',
            repospanner_region=None,
            blacklist=[],
            allowed_prefix=['testns'],
            description='description for testproject2',
            parent_id=None,
            user_ns=True,
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {'endpoint': 'ui_ns.view_repo',
             'repo': 'testproject2',
             'namespace': 'testns'})

        repo = pagure.lib.query._get_project(
            self.session, 'testproject2', namespace='testns')
        self.assertEqual(repo.path, 'testns/testproject2.git')

        gitrepo = os.path.join(gitfolder, repo.path)
        docrepo = os.path.join(docfolder, repo.path)
        ticketrepo = os.path.join(ticketfolder, repo.path)
        requestrepo = os.path.join(requestfolder, repo.path)

        for path in [gitrepo, docrepo, ticketrepo, requestrepo]:
            self.assertTrue(os.path.exists(path))
            shutil.rmtree(path)

    @patch('pagure.lib.notify.log')
    def test_update_project_settings(self, mock_log):
        """ Test the update_project_settings of pagure.lib.query. """

        tests.create_projects(self.session)

        # Before
        repo = pagure.lib.query._get_project(self.session, 'test2')
        self.assertTrue(repo.settings['issue_tracker'])
        self.assertFalse(repo.settings['project_documentation'])

        msg = pagure.lib.query.update_project_settings(
            session=self.session,
            repo=repo,
            settings={
                'issue_tracker': True,
                'project_documentation': False,
                'pull_requests': True,
                'Only_assignee_can_merge_pull-request': False,
                'Minimum_score_to_merge_pull-request': -1,
                'Web-hooks': None,
                'Enforce_signed-off_commits_in_pull-request': False,
                'always_merge': False,
                'issues_default_to_private': False,
                'fedmsg_notifications': True,
                'stomp_notifications': True,
                'pull_request_access_only': False,
            },
            user='pingou',
        )
        self.assertEqual(msg, 'No settings to change')
        mock_log.assert_not_called()

        # Invalid `Minimum_score_to_merge_pull-request`
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.update_project_settings,
            session=self.session,
            repo=repo,
            settings={
                'issue_tracker': False,
                'project_documentation': True,
                'pull_requests': False,
                'Only_assignee_can_merge_pull-request': None,
                'Minimum_score_to_merge_pull-request': 'foo',
                'Web-hooks': 'https://pagure.io/foobar',
                'Enforce_signed-off_commits_in_pull-request': False,
                'issues_default_to_private': False,
                'fedmsg_notifications': True,
                'stomp_notifications': True,
                'pull_request_access_only': False,
            },
            user='pingou',
        )

        msg = pagure.lib.query.update_project_settings(
            session=self.session,
            repo=repo,
            settings={
                'issue_tracker': False,
                'project_documentation': True,
                'pull_requests': False,
                'Only_assignee_can_merge_pull-request': None,
                'Minimum_score_to_merge_pull-request': None,
                'Web-hooks': 'https://pagure.io/foobar',
                'Enforce_signed-off_commits_in_pull-request': False,
                'issues_default_to_private': False,
                'fedmsg_notifications': True,
                'stomp_notifications': True,
                'pull_request_access_only': False,
            },
            user='pingou',
        )
        self.assertEqual(msg, 'Edited successfully settings of repo: test2')
        self.assertEqual(mock_log.call_count, 1)
        args = mock_log.call_args
        self.assertEqual(len(args), 2)
        self.assertEqual(args[0][0].fullname, 'test2')
        self.assertEqual(
            sorted(args[1]['msg']['fields']),
            sorted([
                'Web-hooks', 'project_documentation',
                'issue_tracker', 'pull_requests'
            ])
        )
        self.assertEqual(args[1]['topic'], 'project.edit')

        # After
        repo = pagure.lib.query._get_project(self.session, 'test2')
        self.assertFalse(repo.settings['issue_tracker'])
        self.assertTrue(repo.settings['project_documentation'])
        self.assertFalse(repo.settings['pull_requests'])

    def test_search_issues_milestones_invalid(self):
        """ Test the search_issues of pagure.lib.query. """

        self.test_edit_issue()
        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(len(repo.issues), 2)

        issues = pagure.lib.query.search_issues(
            self.session, repo, milestones='foo')
        self.assertEqual(len(issues), 0)

        issues = pagure.lib.query.search_issues(
            self.session, repo, milestones='foo', no_milestones=True)
        self.assertEqual(len(issues), 2)

    def test_search_issues_custom_search(self):
        """ Test the search_issues of pagure.lib.query. """

        self.test_edit_issue()
        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(len(repo.issues), 2)

        issues = pagure.lib.query.search_issues(
            self.session, repo, custom_search={'foo': '*'})
        self.assertEqual(len(issues), 0)

    def test_search_issues_offset(self):
        """ Test the search_issues of pagure.lib.query. """

        self.test_edit_issue()
        repo = pagure.lib.query._get_project(self.session, 'test')

        issues = pagure.lib.query.search_issues(self.session, repo)
        self.assertEqual(len(issues), 2)
        self.assertEqual([i.id for i in issues], [2, 1])

        issues = pagure.lib.query.search_issues(self.session, repo, offset=1)
        self.assertEqual(len(issues), 1)
        self.assertEqual([i.id for i in issues], [1])

    def test_search_issues_tags(self):
        """ Test the search_issues of pagure.lib.query. """

        self.test_edit_issue()
        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(len(repo.issues), 2)

        # Add `tag1` to one issues and `tag2` only to the other one
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        msg = pagure.lib.query.add_tag_obj(
            session=self.session,
            obj=issue,
            tags='tag1',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue tagged with: tag1')

        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)
        msg = pagure.lib.query.add_tag_obj(
            session=self.session,
            obj=issue,
            tags='tag2',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue tagged with: tag2')

        # Search all issues tagged with `tag1`
        issues = pagure.lib.query.search_issues(self.session, repo, tags='tag1')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 1)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual([tag.tag for tag in issues[0].tags], ['tag1'])

        # Search all issues *not* tagged with `tag1`
        issues = pagure.lib.query.search_issues(self.session, repo, tags='!tag1')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(
            [tag.tag for tag in issues[0].tags], ['tag2'])

        # Search all issues *not* tagged with `tag1` but tagged with `tag2`
        issues = pagure.lib.query.search_issues(
            self.session, repo, tags=['!tag1', 'tag2'])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(
            [tag.tag for tag in issues[0].tags], ['tag2'])

    def test_get_tags_of_project(self):
        """ Test the get_tags_of_project of pagure.lib.query. """

        self.test_add_tag_obj()
        repo = pagure.lib.query._get_project(self.session, 'test')

        tags = pagure.lib.query.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ['tag1'])

        tags = pagure.lib.query.get_tags_of_project(
            self.session, repo, pattern='T*')
        self.assertEqual([tag.tag for tag in tags], ['tag1'])

        repo = pagure.lib.query._get_project(self.session, 'test2')

        tags = pagure.lib.query.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], [])

    def test_get_issue_statuses(self):
        """ Test the get_issue_statuses of pagure.lib.query. """
        statuses = pagure.lib.query.get_issue_statuses(self.session)
        self.assertEqual(sorted(statuses), ['Closed', 'Open'])

    @patch.dict(pagure.config.config, {
        'ALLOWED_EMAIL_DOMAINS': ["fp.o"]}, clear=True)
    def test_set_up_user(self):
        """ Test the set_up_user of pagure.lib.query. """

        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(2, len(items))
        self.assertEqual(2, items[0].id)
        self.assertEqual('foo', items[0].user)
        self.assertEqual(1, items[1].id)
        self.assertEqual('pingou', items[1].user)

        pagure.lib.query.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth',
            default_email='skvidal@fp.o',
            keydir=pagure.config.config.get('GITOLITE_KEYDIR', None),
            ssh_key='ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDtgzSO9d1IrKdmyBFUvtAJPLgGOhp0lSySkWRSe+/+3KXYjSnsLnCJQlO5M7JfaXhtTHEow86rh4W9+FoJdzo5iocAwH5xPZ5ttHLy7VHgTzNMUeMgKpjy6bBOdPoGPPG4mo7QCMCRJdWBRDv4OSEMLU5jQAvC272YK2V8L918VQ== root@test',
        )
        self.session.commit()

        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(3, len(items))
        self.assertEqual(2, items[0].id)
        self.assertEqual('foo', items[0].user)
        self.assertEqual(1, items[1].id)
        self.assertEqual('pingou', items[1].user)
        self.assertEqual(3, items[2].id)
        self.assertEqual('skvidal', items[2].user)
        self.assertEqual('Seth', items[2].fullname)
        self.assertEqual(
            ['skvidal@fp.o'], [email.email for email in items[2].emails])

        # Add the user a second time
        pagure.lib.query.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth V',
            default_email='skvidal@fp.o',
            keydir=pagure.config.config.get('GITOLITE_KEYDIR', None),
        )
        self.session.commit()
        # Nothing changed
        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(3, len(items))
        self.assertEqual('skvidal', items[2].user)
        self.assertEqual('Seth V', items[2].fullname)
        self.assertEqual(
            ['skvidal@fp.o'], [email.email for email in items[2].emails])

        # Add the user a third time with a different email
        pagure.lib.query.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth',
            default_email='svidal@fp.o',
            keydir=pagure.config.config.get('GITOLITE_KEYDIR', None),
        )
        self.session.commit()
        # Email added
        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(3, len(items))
        self.assertEqual('skvidal', items[2].user)
        self.assertEqual(
            sorted(['skvidal@fp.o', 'svidal@fp.o']),
            sorted([email.email for email in items[2].emails]))
        # add again with forbidden email domain
        pagure.lib.query.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth',
            default_email='svidal@example.o',
            keydir=pagure.config.config.get('GITOLITE_KEYDIR', None),
        )
        self.session.commit()
        # Email should not be added
        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(3, len(items))
        self.assertEqual('skvidal', items[2].user)
        self.assertEqual(
            sorted(['skvidal@fp.o', 'svidal@fp.o']),
            sorted([email.email for email in items[2].emails]))

    @patch.dict(pagure.config.config, {
        'ALLOWED_EMAIL_DOMAINS': ["fp.o", "example.c"]}, clear=True)
    def test_set_up_user_multiple_emaildomains(self):
        """ Test the set_up_user of pagure.lib when there are
        multimple domains configured in ALLOWED_EMAIL_DOMAINS"""

        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(2, len(items))
        self.assertEqual(2, items[0].id)
        self.assertEqual('foo', items[0].user)
        self.assertEqual(1, items[1].id)
        self.assertEqual('pingou', items[1].user)

        pagure.lib.query.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth',
            default_email='skvidal@fp.o',
            keydir=pagure.config.config.get('GITOLITE_KEYDIR', None),
        )
        self.session.commit()

        # Add the user a second time with a different email
        pagure.lib.query.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth',
            default_email='skvidal@example.c',
            keydir=pagure.config.config.get('GITOLITE_KEYDIR', None),
        )
        self.session.commit()
        # Email added
        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(3, len(items))
        self.assertEqual('skvidal', items[2].user)
        self.assertEqual(
            sorted(['skvidal@fp.o', 'skvidal@example.c']),
            sorted([email.email for email in items[2].emails]))
        # add again with forbidden email domain
        pagure.lib.query.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth',
            default_email='svidal@example.o',
            keydir=pagure.config.config.get('GITOLITE_KEYDIR', None),
        )
        self.session.commit()
        # Email should not be added
        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(3, len(items))
        self.assertEqual('skvidal', items[2].user)
        self.assertEqual(
            sorted(['skvidal@fp.o', 'skvidal@example.c']),
            sorted([email.email for email in items[2].emails]))

    def avatar_url_from_email(self):
        """ Test the avatar_url_from_openid of pagure.lib.query. """
        output = pagure.lib.query.avatar_url_from_email('pingou@fedoraproject.org')
        self.assertEqual(
            output,
            'https://seccdn.libravatar.org/avatar/'
            'b3ee7bb4de70b6522c2478df3b4cd6322b5ec5d62ac7ceb1128e3d4ff42f6928'
            '?s=64&d=retro')

        output = pagure.lib.query.avatar_url_from_email('zoé@çëfò.org')
        self.assertEqual(
            output,
            'https://seccdn.libravatar.org/avatar/'
            '8fa6110d1f6a7a013969f012e1149ff89bf1252d4f15d25edee31d4662878656'
            '?s=64&d=retro')

    def test_fork_project_with_branch(self):
        """ Test the fork_project of pagure.lib.query. """
        gitfolder = os.path.join(self.path, 'repos')
        docfolder = os.path.join(gitfolder, 'docs')
        ticketfolder = os.path.join(gitfolder, 'tickets')
        requestfolder = os.path.join(gitfolder, 'requests')
        pagure.config.config['GIT_FOLDER'] = gitfolder

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        # Create a new project
        task = pagure.lib.query.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            repospanner_region=None,
            blacklist=[],
            allowed_prefix=[],
            description='description for testproject',
            parent_id=None,
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {'endpoint': 'ui_ns.view_repo',
             'repo': 'testproject',
             'namespace': None})

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        project = pagure.lib.query._get_project(self.session, 'testproject')
        gitrepo = os.path.join(gitfolder, project.path)
        docrepo = os.path.join(docfolder, project.path)
        ticketrepo = os.path.join(ticketfolder, project.path)
        requestrepo = os.path.join(requestfolder, project.path)

        # Add content to the main repo into three branches
        tests.add_content_git_repo(gitrepo, 'master')
        tests.add_content_git_repo(gitrepo, 'feature1')
        tests.add_content_git_repo(gitrepo, 'feature2')

        # Check the branches of the main repo
        self.assertEqual(
            sorted(pagure.lib.git.get_git_branches(project)),
            ['feature1', 'feature2', 'master']
        )

        # Fork

        task = pagure.lib.query.fork_project(
            session=self.session,
            user='foo',
            repo=project,
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {'endpoint': 'ui_ns.view_repo',
             'repo': 'testproject',
             'namespace': None,
             'username': 'foo'})

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 2)

        project = pagure.lib.query._get_project(
            self.session, 'testproject', user='foo')
        # Check the branches of the fork
        self.assertEqual(
            sorted(pagure.lib.git.get_git_branches(project)),
            ['feature1', 'feature2', 'master']
        )

    def test_fork_project_namespaced(self):
        """ Test the fork_project of pagure.lib on a namespaced project. """
        gitfolder = os.path.join(self.path, 'repos')
        docfolder = os.path.join(gitfolder, 'docs')
        ticketfolder = os.path.join(gitfolder, 'tickets')
        requestfolder = os.path.join(gitfolder, 'requests')

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        # Create a new project
        task = pagure.lib.query.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            namespace='foonamespace',
            repospanner_region=None,
            blacklist=[],
            allowed_prefix=['foonamespace'],
            description='description for testproject',
            parent_id=None,
        )
        self.session.commit()
        self.assertEqual(task.get(),
                         {'endpoint': 'ui_ns.view_repo',
                          'repo': 'testproject',
                          'namespace': 'foonamespace'})

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        repo = pagure.lib.query._get_project(self.session, 'testproject', namespace='foonamespace')
        gitrepo = os.path.join(gitfolder, repo.path)
        docrepo = os.path.join(docfolder, repo.path)
        ticketrepo = os.path.join(ticketfolder, repo.path)
        requestrepo = os.path.join(requestfolder, repo.path)

        self.assertTrue(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Fork worked

        task = pagure.lib.query.fork_project(
            session=self.session,
            user='foo',
            repo=repo,
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {'endpoint': 'ui_ns.view_repo',
             'repo': 'testproject',
             'namespace': 'foonamespace',
             'username': 'foo'})

        # Fork a fork

        repo = pagure.lib.query._get_project(self.session, 'testproject', user='foo', namespace='foonamespace')

        task = pagure.lib.query.fork_project(
            session=self.session,
            user='pingou',
            repo=repo,
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {'endpoint': 'ui_ns.view_repo',
             'repo': 'testproject',
             'namespace': 'foonamespace',
             'username': 'pingou'})

    @patch('pagure.lib.notify.send_email')
    def test_new_pull_request(self, mockemail):
        """ test new_pull_request of pagure.lib.query. """
        mockemail.return_value = True

        tests.create_projects(self.session)

        # Create a forked repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test',
            description='test project #1',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbrrr',
        )
        self.session.commit()
        self.session.add(item)

        # Add an extra user to project `foo`
        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(repo.open_requests, 0)

        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        repo = pagure.lib.query._get_project(self.session, 'test')
        forked_repo = pagure.lib.query._get_project(
            self.session, 'test', user='pingou')

        # Fails for the lack of repo_from and remote_git
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.new_pull_request,
            session=self.session,
            repo_from=None,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )

        # Let's pretend we turned on the CI hook for the project
        project = pagure.lib.query._get_project(self.session, 'test')
        obj = pagure.hooks.pagure_ci.PagureCITable(
            project_id=project.id,
            active=True
        )
        self.session.add(obj)
        self.session.commit()

        # Create the new PR
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')
        self.assertEqual(repo.open_requests, 1)

    @patch('pagure.lib.query.REDIS')
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_add_pull_request_comment(self, mock_redis):
        """ Test add_pull_request_comment of pagure.lib.query. """
        mock_redis.return_value = True

        self.test_new_pull_request()

        request = pagure.lib.query.search_pull_requests(self.session, requestid=1)

        msg = pagure.lib.query.add_pull_request_comment(
            session=self.session,
            request=request,
            commit='commithash',
            tree_id=None,
            filename='file',
            row=None,
            comment='This is awesome, I got to remember it!',
            user='foo',
            notification=True,
        )
        self.assertEqual(msg, 'Comment added')
        self.session.commit()

        self.assertEqual(len(request.discussion), 0)
        self.assertEqual(len(request.comments), 1)
        self.assertEqual(request.score, 0)
        self.assertEqual(mock_redis.publish.call_count, 1)

    @patch('pagure.lib.query.REDIS')
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    @patch('pagure.lib.query.PAGURE_CI', MagicMock(return_value=True))
    def test_add_pull_request_comment_to_re_run_ci(self, mock_redis):
        """ Test add_pull_request_comment of pagure.lib.query. """
        mock_redis.return_value = True

        self.test_new_pull_request()
        self.assertEqual(mock_redis.publish.call_count, 0)

        # Let's pretend we turned on the CI hook for the project
        project = pagure.lib.query._get_project(self.session, 'test')
        if not project.ci_hook or not project.ci_hook.active:
            obj = pagure.hooks.pagure_ci.PagureCITable(
                project_id=project.id,
                active=True
            )
            self.session.add(obj)
            self.session.commit()

        request = pagure.lib.query.search_pull_requests(self.session, requestid=1)
        msg = pagure.lib.query.add_pull_request_comment(
            session=self.session,
            request=request,
            commit='commithash',
            tree_id=None,
            filename='file',
            row=None,
            comment='Pretty please pagure-ci rebuild',
            user='foo',
            notification=True,
            trigger_ci=['pretty please pagure-ci rebuild'],
        )
        self.assertEqual(msg, 'Comment added')
        self.session.commit()

        self.assertEqual(len(request.discussion), 0)
        self.assertEqual(len(request.comments), 1)
        self.assertEqual(request.score, 0)
        self.assertEqual(mock_redis.publish.call_count, 1)

    @patch('pagure.lib.notify.send_email')
    def test_add_pull_request_flag(self, mockemail):
        """ Test add_pull_request_flag of pagure.lib.query. """
        mockemail.return_value = True

        self.test_new_pull_request()
        tests.create_tokens(self.session)

        request = pagure.lib.query.search_pull_requests(self.session, requestid=1)
        self.assertEqual(len(request.flags), 0)

        msg = pagure.lib.query.add_pull_request_flag(
            session=self.session,
            request=request,
            username="jenkins",
            percent=100,
            comment="Build passes",
            status='success',
            url="http://jenkins.cloud.fedoraproject.org",
            uid="jenkins_build_pagure_34",
            user='foo',
            token='aaabbbcccddd',
        )
        self.assertEqual(msg, ('Flag added', 'jenkins_build_pagure_34'))
        self.session.commit()

        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].token_id, 'aaabbbcccddd')

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_search_pull_requests(self):
        """ Test search_pull_requests of pagure.lib.query. """

        self.test_new_pull_request()

        prs = pagure.lib.query.search_pull_requests(
            session=self.session
        )
        self.assertEqual(len(prs), 1)

        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            project_id=1
        )
        self.assertEqual(len(prs), 1)

        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            project_id_from=4
        )
        self.assertEqual(len(prs), 1)

        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            status=False
        )
        self.assertEqual(len(prs), 0)

        # All non-assigned PR
        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            assignee=False
        )
        self.assertEqual(len(prs), 1)

        prs[0].assignee_id = 1
        self.session.add(prs[0])
        self.session.commit()

        # All the PR assigned
        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            assignee=True
        )
        self.assertEqual(len(prs), 1)

        # Basically the same as above but then for a specific user
        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            assignee='pingou'
        )
        self.assertEqual(len(prs), 1)

        # All PR except those assigned to pingou
        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            assignee='!pingou'
        )
        self.assertEqual(len(prs), 0)

        # All PR created by the specified author
        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            author='pingou'
        )
        self.assertEqual(len(prs), 1)

        # Count the PR instead of listing them
        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            author='pingou',
            count=True
        )
        self.assertEqual(prs, 1)

        dt = datetime.datetime.utcnow()

        # Create the second PR
        repo = pagure.lib.query._get_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='feature',
            repo_to=repo,
            branch_to='master',
            title='test pull-request #2',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 2)
        self.assertEqual(req.title, 'test pull-request #2')
        self.assertEqual(repo.open_requests, 2)

        # Ensure we have 2 PRs
        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            author='pingou',
        )
        self.assertEqual(len(prs), 2)

        # Test the offset
        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            author='pingou',
            offset=1,
        )
        self.assertEqual(len(prs), 1)

        # Test the updated_after

        # Test updated after before the second PR was created
        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            author='pingou',
            updated_after=dt,
        )
        self.assertEqual(len(prs), 1)

        # Test updated after, 1h ago
        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            author='pingou',
            updated_after=dt - datetime.timedelta(hours=1),
        )
        self.assertEqual(len(prs), 2)

    @patch('pagure.lib.notify.send_email')
    def test_close_pull_request(self, send_email):
        """ Test close_pull_request of pagure.lib.query. """
        send_email.return_value = True

        self.test_new_pull_request()

        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(repo.open_requests, 1)
        request = pagure.lib.query.search_pull_requests(self.session, requestid=1)

        pagure.lib.query.close_pull_request(
            session=self.session,
            request=request,
            user='pingou',
            merged=True,
        )
        self.session.commit()
        repo = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(repo.open_requests, 0)

        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            status=False
        )
        self.assertEqual(len(prs), 1)

        # Does not change much, just the notification sent

        pagure.lib.query.close_pull_request(
            session=self.session,
            request=request,
            user='pingou',
            merged=False,
        )
        self.session.commit()

        prs = pagure.lib.query.search_pull_requests(
            session=self.session,
            status=False
        )
        self.assertEqual(len(prs), 1)

    @patch('pagure.lib.query.REDIS', MagicMock(return_value=True))
    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_remove_issue_dependency(self):
        """ Test remove_issue_dependency of pagure.lib.query. """

        self.test_add_issue_dependency()
        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        issue_blocked = pagure.lib.query.search_issues(
            self.session, repo, issueid=2)

        # Before
        self.assertEqual(len(issue.children), 1)
        self.assertEqual(issue.children[0].id, 2)
        self.assertEqual(len(issue.parents), 0)
        self.assertEqual(issue.parents, [])

        self.assertEqual(len(issue_blocked.children), 0)
        self.assertEqual(issue_blocked.children, [])
        self.assertEqual(len(issue_blocked.parents), 1)
        self.assertEqual(issue_blocked.parents[0].id, 1)

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.remove_issue_dependency,
            session=self.session,
            issue=issue,
            issue_blocked=issue,
            user='pingou',
        )

        # Wrong order of issues
        msg = pagure.lib.query.remove_issue_dependency(
            session=self.session,
            issue=issue,
            issue_blocked=issue_blocked,
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, None)

        # Drop deps
        msg = pagure.lib.query.remove_issue_dependency(
            session=self.session,
            issue=issue_blocked,
            issue_blocked=issue,
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue **un**marked as depending on: #1')

        # After
        self.assertEqual(issue.parents, [])
        self.assertEqual(issue.children, [])
        self.assertEqual(issue_blocked.parents, [])
        self.assertEqual(issue_blocked.children, [])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_get_issue_comment(self, p_send_email, p_ugt):
        """ Test the get_issue_comment of pagure.lib.query. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_add_issue_comment()

        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)

        self.assertEqual(
            pagure.lib.query.get_issue_comment(self.session, issue.uid, 10),
            None
        )

        comment = pagure.lib.query.get_issue_comment(self.session, issue.uid, 1)
        self.assertEqual(comment.comment, 'Hey look a comment!')

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_get_issue_by_uid(self, p_send_email, p_ugt):
        """ Test the get_issue_by_uid of pagure.lib.query. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()

        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)

        self.assertEqual(
            pagure.lib.query.get_issue_by_uid(self.session, 'foobar'),
            None
        )

        new_issue = pagure.lib.query.get_issue_by_uid(self.session, issue.uid)
        self.assertEqual(issue, new_issue)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_update_tags(self, p_send_email, p_ugt):
        """ Test the update_tags of pagure.lib.query. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()
        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)

        # before
        self.assertEqual(repo.tags_colored, [])
        self.assertEqual(issue.tags_text, [])

        messages = pagure.lib.query.update_tags(
            self.session, issue, 'tag', 'pingou')
        self.assertEqual(messages, ['Issue tagged with: tag'])

        # after
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)

        self.assertEqual(
            [t.tag for t in repo.tags_colored], ['tag'])
        self.assertEqual(issue.tags_text, ['tag'])

        # Replace the tag by two others
        messages = pagure.lib.query.update_tags(
            self.session, issue, ['tag2', 'tag3'], 'pingou')
        self.assertEqual(
            messages, [
                'Issue tagged with: tag2, tag3',
                'Issue **un**tagged with: tag'
            ]
        )

        # after
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)

        self.assertEqual(
            sorted([t.tag for t in repo.tags_colored]),
            ['tag', 'tag2', 'tag3'])
        self.assertEqual(sorted(issue.tags_text), ['tag2', 'tag3'])


    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_update_dependency_issue(self, p_send_email, p_ugt):
        """ Test the update_dependency_issue of pagure.lib.query. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()
        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)

        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

        # Create issues to play with
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #3',
            content='We should work on this (3rd time!)',
            user='pingou',
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #3')

        self.assertEqual(repo.open_tickets, 3)
        self.assertEqual(repo.open_tickets_public, 2)

        # before
        self.assertEqual(issue.tags_text, [])
        self.assertEqual(issue.depending_text, [])
        self.assertEqual(issue.blocking_text, [])

        messages = pagure.lib.query.update_dependency_issue(
            self.session, repo, issue, '2', 'pingou')
        self.assertEqual(messages, ['Issue marked as depending on: #2'])
        messages = pagure.lib.query.update_dependency_issue(
            self.session, repo, issue, ['3', '4', 5], 'pingou')
        self.assertEqual(
            messages,
            [
                'Issue marked as depending on: #3',
                'Issue marked as depending on: #4',
                'Issue marked as depending on: #5',
                'Issue **un**marked as depending on: #2'
            ]
        )

        # after
        self.assertEqual(issue.tags_text, [])
        self.assertEqual(issue.depending_text, [3])
        self.assertEqual(issue.blocking_text, [])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_update_blocked_issue(self, p_send_email, p_ugt):
        """ Test the update_blocked_issue of pagure.lib.query. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()
        repo = pagure.lib.query._get_project(self.session, 'test')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)

        # Create issues to play with
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #3',
            content='We should work on this (3rd time!)',
            user='pingou',
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #3')

        # before
        self.assertEqual(issue.tags_text, [])
        self.assertEqual(issue.depending_text, [])
        self.assertEqual(issue.blocking_text, [])

        messages = pagure.lib.query.update_blocked_issue(
            self.session, repo, issue, '2', 'pingou')
        self.assertEqual(messages, ['Issue marked as blocking: #2'])
        messages = pagure.lib.query.update_blocked_issue(
            self.session, repo, issue, ['3', '4', 5], 'pingou')
        self.assertEqual(
            messages, [
                'Issue marked as blocking: #3',
                'Issue marked as blocking: #4',
                'Issue marked as blocking: #5',
                'Issue **un**marked as blocking: #2'])

        # after
        self.assertEqual(issue.tags_text, [])
        self.assertEqual(issue.depending_text, [])
        self.assertEqual(issue.blocking_text, [3])

    @patch('pagure.lib.notify.send_email')
    def test_add_pull_request_assignee(self, mockemail):
        """ Test add_pull_request_assignee of pagure.lib.query. """
        mockemail.return_value = True

        self.test_new_pull_request()

        request = pagure.lib.query.search_pull_requests(self.session, requestid=1)

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_pull_request_assignee,
            session=self.session,
            request=request,
            assignee='bar',
            user='foo',
        )

        # Assign
        msg = pagure.lib.query.add_pull_request_assignee(
            session=self.session,
            request=request,
            assignee='pingou',
            user='foo',
        )
        self.assertEqual(msg, 'Request assigned')

        # Reset
        msg = pagure.lib.query.add_pull_request_assignee(
            session=self.session,
            request=request,
            assignee=None,
            user='foo',
        )
        self.assertEqual(msg, 'Request reset')

        # Try resetting again
        msg = pagure.lib.query.add_pull_request_assignee(
            session=self.session,
            request=request,
            assignee=None,
            user='foo',
        )
        self.assertEqual(msg, None)

    def test_search_pending_email(self):
        """ Test search_pending_email of pagure.lib.query. """

        self.assertEqual(
            pagure.lib.query.search_pending_email(self.session), None)

        user = pagure.lib.query.search_user(self.session, username='pingou')

        email_pend = pagure.lib.model.UserEmailPending(
            user_id=user.id,
            email='foo@fp.o',
            token='abcdef',
        )
        self.session.add(email_pend)
        self.session.commit()

        self.assertNotEqual(
            pagure.lib.query.search_pending_email(self.session), None)
        self.assertNotEqual(
            pagure.lib.query.search_pending_email(self.session, token='abcdef'),
            None)

        pend = pagure.lib.query.search_pending_email(self.session, token='abcdef')
        self.assertEqual(pend.user.username, 'pingou')
        self.assertEqual(pend.email, 'foo@fp.o')
        self.assertEqual(pend.token, 'abcdef')

        pend = pagure.lib.query.search_pending_email(self.session, email='foo@fp.o')
        self.assertEqual(pend.user.username, 'pingou')
        self.assertEqual(pend.email, 'foo@fp.o')
        self.assertEqual(pend.token, 'abcdef')

    def test_generate_hook_token(self):
        """ Test generate_hook_token of pagure.lib.query. """

        tests.create_projects(self.session)

        projects = pagure.lib.query.search_projects(self.session)
        for proj in projects:
            self.assertIn(proj.hook_token, ['aaabbbccc', 'aaabbbddd', 'aaabbbeee'])

        pagure.lib.query.generate_hook_token(self.session)

        projects = pagure.lib.query.search_projects(self.session)
        for proj in projects:
            self.assertNotIn(proj.hook_token, ['aaabbbccc', 'aaabbbddd', 'aaabbbeee'])

    @patch('pagure.lib.notify.send_email')
    def test_pull_request_score(self, mockemail):
        """ Test PullRequest.score of pagure.lib.model. """
        mockemail.return_value = True

        self.test_new_pull_request()

        request = pagure.lib.query.search_pull_requests(self.session, requestid=1)

        msg = pagure.lib.query.add_pull_request_comment(
            session=self.session,
            request=request,
            commit=None,
            tree_id=None,
            filename=None,
            row=None,
            comment='This looks great :thumbsup:',
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        msg = pagure.lib.query.add_pull_request_comment(
            session=self.session,
            request=request,
            commit=None,
            tree_id=None,
            filename=None,
            row=None,
            comment='I disagree -1',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        msg = pagure.lib.query.add_pull_request_comment(
            session=self.session,
            request=request,
            commit=None,
            tree_id=None,
            filename=None,
            row=None,
            comment='NM this looks great now +1000',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        self.assertEqual(len(request.discussion), 3)
        self.assertEqual(request.score, 1)

    def test_add_group(self):
        """ Test the add_group method of pagure.lib.query. """
        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 0)
        self.assertEqual(groups, [])

        # Invalid type
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_group,
            self.session,
            group_name='foo',
            display_name='foo group',
            description=None,
            group_type='bar',
            user='pingou',
            is_admin=True,
            blacklist=[],
        )
        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 0)
        self.assertEqual(groups, [])

        # Invalid user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_group,
            self.session,
            group_name='foo',
            display_name='foo group',
            description=None,
            group_type='user',
            user='test',
            is_admin=False,
            blacklist=[],
        )
        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 0)
        self.assertEqual(groups, [])

        # Invalid group name
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_group,
            self.session,
            group_name='foo group',
            display_name='foo group',
            description=None,
            group_type='user',
            user='test',
            is_admin=False,
            blacklist=[],
        )
        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 0)
        self.assertEqual(groups, [])

        msg = pagure.lib.query.add_group(
            self.session,
            group_name='foo',
            display_name='foo group',
            description=None,
            group_type='bar',
            user='pingou',
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, 'User `pingou` added to the group `foo`.')

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_name, 'foo')

        # Group with this name already exists
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_group,
            self.session,
            group_name='foo',
            display_name='foo group',
            description=None,
            group_type='bar',
            user='pingou',
            is_admin=False,
            blacklist=[],
        )

        # Group with this display name already exists
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_group,
            self.session,
            group_name='foo1',
            display_name='foo group',
            description=None,
            group_type='bar',
            user='pingou',
            is_admin=False,
            blacklist=[],
        )

        # Group with a blacklisted prefix
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_group,
            self.session,
            group_name='forks',
            display_name='foo group',
            description=None,
            group_type='bar',
            user='pingou',
            is_admin=False,
            blacklist=['forks'],
        )

    def test_add_user_to_group(self):
        """ Test the add_user_to_group method of pagure.lib.query. """
        self.test_add_group()
        group = pagure.lib.query.search_groups(self.session, group_name='foo')
        self.assertNotEqual(group, None)
        self.assertEqual(group.group_name, 'foo')

        # Invalid new user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_user_to_group,
            self.session,
            username='foobar',
            group=group,
            user='foo',
            is_admin=False,
        )

        # Invalid user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_user_to_group,
            self.session,
            username='foo',
            group=group,
            user='foobar',
            is_admin=False,
        )

        # User not allowed
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_user_to_group,
            self.session,
            username='foo',
            group=group,
            user='foo',
            is_admin=False,
        )

        msg = pagure.lib.query.add_user_to_group(
            self.session,
            username='foo',
            group=group,
            user='pingou',
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, 'User `foo` added to the group `foo`.')

        msg = pagure.lib.query.add_user_to_group(
            self.session,
            username='foo',
            group=group,
            user='pingou',
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(
            msg, 'User `foo` already in the group, nothing to change.')

    def test_is_group_member(self):
        """ Test the is_group_member method of pagure.lib.query. """
        self.test_add_group()

        self.assertFalse(
            pagure.lib.query.is_group_member(self.session, None, 'foo'))

        self.assertFalse(
            pagure.lib.query.is_group_member(self.session, 'bar', 'foo'))

        self.assertFalse(
            pagure.lib.query.is_group_member(self.session, 'foo', 'foo'))

        self.assertTrue(
            pagure.lib.query.is_group_member(self.session, 'pingou', 'foo'))

    def test_get_user_group(self):
        """ Test the get_user_group method of pagure.lib.query. """

        self.test_add_group()

        item = pagure.lib.query.get_user_group(self.session, 1, 1)
        self.assertEqual(item.user_id, 1)
        self.assertEqual(item.group_id, 1)

        item = pagure.lib.query.get_user_group(self.session, 1, 2)
        self.assertEqual(item, None)

        item = pagure.lib.query.get_user_group(self.session, 2, 1)
        self.assertEqual(item, None)

    def test_get_group_types(self):
        """ Test the get_group_types method of pagure.lib.query. """

        self.test_add_group()

        groups = pagure.lib.query.get_group_types(self.session, 'user')
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_type, 'user')

        groups = pagure.lib.query.get_group_types(self.session)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].group_type, 'admin')
        self.assertEqual(groups[1].group_type, 'user')

    def test_search_groups(self):
        """ Test the search_groups method of pagure.lib.query. """

        self.assertEqual(pagure.lib.query.search_groups(self.session), [])

        msg = pagure.lib.query.add_group(
            self.session,
            group_name='foo',
            display_name='foo group',
            description=None,
            group_type='bar',
            user='pingou',
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, 'User `pingou` added to the group `foo`.')

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_name, 'foo')

        msg = pagure.lib.query.add_group(
            self.session,
            group_name='bar',
            display_name='bar group',
            description=None,
            group_type='admin',
            user='pingou',
            is_admin=True,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, 'User `pingou` added to the group `bar`.')

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].group_name, 'bar')
        self.assertEqual(groups[1].group_name, 'foo')

        groups = pagure.lib.query.search_groups(self.session, group_type='user')
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_name, 'foo')

        groups = pagure.lib.query.search_groups(self.session, group_type='admin')
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_name, 'bar')

        groups = pagure.lib.query.search_groups(self.session, group_name='foo')
        self.assertEqual(groups.group_name, 'foo')

    def test_delete_user_of_group(self):
        """ Test the delete_user_of_group method of pagure.lib.query. """
        self.test_add_user_to_group()

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_name, 'foo')

        # Invalid username
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.delete_user_of_group,
            self.session,
            username='bar',
            groupname='foo',
            user='pingou',
            is_admin=False,
        )

        # Invalid groupname
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.delete_user_of_group,
            self.session,
            username='foo',
            groupname='bar',
            user='pingou',
            is_admin=False,
        )

        # Invalid user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.delete_user_of_group,
            self.session,
            username='foo',
            groupname='foo',
            user='test',
            is_admin=False,
        )

        # User not in the group
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar',
            password='foo',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)
        self.session.commit()

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.delete_user_of_group,
            self.session,
            username='bar',
            groupname='foo',
            user='pingou',
            is_admin=False,
        )

        # User is not allowed to remove the username
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.delete_user_of_group,
            self.session,
            username='foo',
            groupname='foo',
            user='bar',
            is_admin=False,
        )

        # Username is the creator of the group
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.delete_user_of_group,
            self.session,
            username='pingou',
            groupname='foo',
            user='pingou',
            is_admin=False,
        )

        # All good
        group = pagure.lib.query.search_groups(self.session, group_name='foo')
        self.assertEqual(len(group.users), 2)

        pagure.lib.query.delete_user_of_group(
            self.session,
            username='foo',
            groupname='foo',
            user='pingou',
            is_admin=False,
        )
        self.session.commit()

        group = pagure.lib.query.search_groups(self.session, group_name='foo')
        self.assertEqual(len(group.users), 1)

    def test_edit_group_info(self):
        """ Test the edit_group_info method of pagure.lib.query. """
        self.test_add_group()
        group = pagure.lib.query.search_groups(self.session, group_name='foo')
        self.assertNotEqual(group, None)
        self.assertEqual(group.group_name, 'foo')

        # Invalid new user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.edit_group_info,
            self.session,
            group=group,
            display_name='edited name',
            description=None,
            user='foo',
            is_admin=False,
        )

        # Invalid user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.edit_group_info,
            self.session,
            group=group,
            display_name='edited name',
            description=None,
            user='foobar',
            is_admin=False,
        )

        # User not allowed
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.edit_group_info,
            self.session,
            group=group,
            display_name='edited name',
            description=None,
            user='bar',
            is_admin=False,
        )

        msg = pagure.lib.query.edit_group_info(
            self.session,
            group=group,
            display_name='edited name',
            description=None,
            user='pingou',
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, 'Group "edited name" (foo) edited')

        msg = pagure.lib.query.edit_group_info(
            self.session,
            group=group,
            display_name='edited name',
            description=None,
            user='pingou',
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, 'Nothing changed')

    def test_add_group_to_project(self):
        """ Test the add_group_to_project method of pagure.lib.query. """
        tests.create_projects(self.session)
        self.test_add_group()

        project = pagure.lib.query._get_project(self.session, 'test2')

        # Group does not exist
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_group_to_project,
            session=self.session,
            project=project,
            new_group='bar',
            user='foo',
        )

        # Group does not exist, but allow creating it
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group='bar',
            user='pingou',
            create=True,
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')
        self.assertEqual(project.groups[0].group_name, 'bar')
        self.assertEqual(len(project.admin_groups), 1)
        self.assertEqual(project.admin_groups[0].group_name, 'bar')

        # User does not exist
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_group_to_project,
            session=self.session,
            project=project,
            new_group='foo',
            user='bar',
        )

        # User not allowed
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_group_to_project,
            session=self.session,
            project=project,
            new_group='foo',
            user='foo',
        )

        # All good
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')
        self.assertEqual(project.groups[0].group_name, 'bar')
        self.assertEqual(project.groups[1].group_name, 'foo')
        self.assertEqual(len(project.admin_groups), 2)
        self.assertEqual(project.admin_groups[0].group_name, 'bar')
        self.assertEqual(project.admin_groups[1].group_name, 'foo')
        self.assertEqual(len(project.committer_groups), 2)

        # Group already associated with the project
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_group_to_project,
            session=self.session,
            project=project,
            new_group='foo',
            user='pingou',
        )

        # Update the access of group in the project
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group='foo',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')
        self.assertEqual(project.groups[0].group_name, 'bar')
        self.assertEqual(project.groups[1].group_name, 'foo')
        self.assertEqual(len(project.admin_groups), 1)
        self.assertEqual(project.admin_groups[0].group_name, 'bar')
        self.assertEqual(len(project.committer_groups), 2)

        # Update the access of group in the project
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group='foo',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')
        self.assertEqual(project.groups[0].group_name, 'bar')
        self.assertEqual(project.groups[1].group_name, 'foo')
        self.assertEqual(len(project.admin_groups), 1)
        self.assertEqual(project.admin_groups[0].group_name, 'bar')
        self.assertEqual(len(project.committer_groups), 1)
        self.assertEqual(project.committer_groups[0].group_name, 'bar')

    def test_update_watch_status(self):
        """ Test the update_watch_status method of pagure.lib.query. """
        tests.create_projects(self.session)

        project = pagure.lib.query._get_project(self.session, 'test')

        # User does not exist
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.update_watch_status,
            session=self.session,
            project=project,
            user='aavrug',
            watch='1',
        )

        # Invalid watch status
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.update_watch_status,
            session=self.session,
            project=project,
            user='pingou',
            watch='me fail',
        )

        # All good and when user selected reset watch option.
        msg = pagure.lib.query.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch='-1',
        )
        self.session.commit()
        self.assertEqual(msg, 'Watch status is already reset')

        # All good and when user selected watch issues option.
        msg = pagure.lib.query.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch='1',
        )
        self.session.commit()
        self.assertEqual(
            msg, 'You are now watching issues and PRs on this project')

        # All good and when user selected unwatch option.
        msg = pagure.lib.query.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch='0',
        )
        self.session.commit()
        self.assertEqual(msg, 'You are no longer watching this project')

        # All good and when user seleted reset watch option.
        msg = pagure.lib.query.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch='-1',
        )
        self.session.commit()
        self.assertEqual(msg, 'Watch status reset')

    def test_get_watch_level_on_repo_invalid(self):
        """ test the get_watch_level_on_repo method of pagure.lib.query. """

        self.assertRaises(
            RuntimeError,
            pagure.lib.query.get_watch_level_on_repo,
            session=self.session,
            user='pingou',
            repo=None,
            repouser=None,
            namespace=None,
        )

    def test_get_watch_level_on_repo(self):
        """ Test the get_watch_level_on_repo method of pagure.lib.query. """
        tests.create_projects(self.session)
        self.test_add_group()

        project = pagure.lib.query._get_project(self.session, 'test')
        project2 = pagure.lib.query._get_project(self.session, 'test2')

        # If user not logged in
        watch_level = pagure.lib.query.get_watch_level_on_repo(
            session=self.session,
            user=None,
            repo='test',
        )
        self.assertEqual(watch_level, [])

        # User does not exist
        user = tests.FakeUser()
        user.username = 'aavrug'
        watch_level = pagure.lib.query.get_watch_level_on_repo(
            session=self.session,
            user=user,
            repo='test',
        )
        self.assertEqual(watch_level, [])

        # Invalid project
        watch = pagure.lib.query.get_watch_level_on_repo(
            session=self.session,
            user=user,
            repo='invalid',
        )
        self.assertFalse(watch)

        pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group='foo',
            user='pingou',
        )
        self.session.commit()

        group = pagure.lib.query.search_groups(self.session, group_name='foo')
        pagure.lib.query.add_user_to_group(
            self.session,
            username='foo',
            group=group,
            user='pingou',
            is_admin=False,
        )
        self.session.commit()
        group = pagure.lib.query.search_groups(self.session, group_name='foo')

        # If user belongs to any group of that project
        user.username = 'foo'
        msg = watch_level = pagure.lib.query.get_watch_level_on_repo(
            session=self.session,
            user=user,
            repo='test',
        )
        self.assertEqual(watch_level, ['issues'])

        # If user is the creator
        user.username = 'pingou'
        watch_level = pagure.lib.query.get_watch_level_on_repo(
            session=self.session,
            user=user,
            repo='test',
        )
        self.assertEqual(watch_level, ['issues'])

        # Entry into watchers table for issues and commits
        msg = pagure.lib.query.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch='3',
        )
        self.session.commit()
        self.assertEqual(
            msg,
            'You are now watching issues, PRs, and commits on this project')

        # From watchers table
        watch_level = pagure.lib.query.get_watch_level_on_repo(
            session=self.session,
            user=user,
            repo='test',
        )
        self.assertEqual(['issues', 'commits'], watch_level)

        # Make sure that when a user watches more than one repo explicitly
        # they get the correct watch status
        msg = pagure.lib.query.update_watch_status(
            session=self.session,
            project=project2,
            user='pingou',
            watch='1',
        )
        self.session.commit()
        self.assertEqual(
            msg,
            'You are now watching issues and PRs on this project')

        # From watchers table
        watch_level = pagure.lib.query.get_watch_level_on_repo(
            session=self.session,
            user=user,
            repo='test2',
        )
        self.assertEqual(['issues'], watch_level)

        # Entry into watchers table for just commits
        msg = pagure.lib.query.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch='2',
        )
        self.session.commit()
        self.assertEqual(
            msg, 'You are now watching commits on this project')

        # From watchers table
        watch_level = pagure.lib.query.get_watch_level_on_repo(
            session=self.session,
            user=user,
            repo='test',
        )
        self.assertEqual(['commits'], watch_level)

        # Entry into watchers table for issues
        msg = pagure.lib.query.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch='1',
        )
        self.session.commit()
        self.assertEqual(
            msg, 'You are now watching issues and PRs on this project')

        # From watchers table
        watch_level = pagure.lib.query.get_watch_level_on_repo(
            session=self.session,
            user=user,
            repo='test',
        )
        self.assertEqual(['issues'], watch_level)

        # Entry into watchers table for no watching
        msg = pagure.lib.query.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch='0',
        )
        self.session.commit()
        self.assertEqual(msg, 'You are no longer watching this project')

        # From watchers table
        watch_level = pagure.lib.query.get_watch_level_on_repo(
            session=self.session,
            user=user,
            repo='test',
        )
        self.assertEqual(watch_level, [])

        # Add a contributor to the project
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar foo',
            password='foo',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)
        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=project,
            new_user='bar',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # Check if the new contributor is watching
        user.username = 'bar'
        watch_level = pagure.lib.query.get_watch_level_on_repo(
            session=self.session,
            user=user,
            repo='test',
        )
        self.assertEqual(watch_level, ['issues'])

        # wrong project
        user.username = 'bar'
        watch_level = pagure.lib.query.get_watch_level_on_repo(
            session=self.session,
            user=user,
            repo='test',
            namespace='somenamespace',
        )
        self.assertEqual(watch_level, [])

    def test_user_watch_list(self):
        ''' test user watch list method of pagure.lib '''

        tests.create_projects(self.session)

        # He should be watching
        user = tests.FakeUser()
        user.username = 'pingou'
        watch_list_objs = pagure.lib.query.user_watch_list(
            session=self.session,
            user='pingou',
        )
        watch_list = [obj.name for obj in watch_list_objs]
        self.assertEqual(watch_list, ['test', 'test2', 'test3'])

        # Make pingou unwatch the test3 project
        project =pagure.lib.query._get_project(
            self.session, 'test3', namespace='somenamespace')
        msg = pagure.lib.query.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch='0'
        )
        self.session.commit()
        self.assertEqual(msg, 'You are no longer watching this project')

        # Re-check the watch list
        watch_list_objs = pagure.lib.query.user_watch_list(
            session=self.session,
            user='pingou',
        )
        watch_list = [obj.name for obj in watch_list_objs]
        self.assertEqual(watch_list, ['test', 'test2'])

        # He isn't in the db, thus not watching anything
        user.username = 'vivek'
        watch_list_objs = pagure.lib.query.user_watch_list(
            session=self.session,
            user='vivek',
        )
        watch_list = [obj.name for obj in watch_list_objs]
        self.assertEqual(watch_list, [])

        # He shouldn't be watching anything
        user.username = 'foo'
        watch_list_objs = pagure.lib.query.user_watch_list(
            session=self.session,
            user='foo',
        )
        watch_list = [obj.name for obj in watch_list_objs]
        self.assertEqual(watch_list, [])

    @patch('flask.request.url', 'http://localhost.localdomain/test/issue/69')
    @patch('flask.request.url_root', 'http://localhost.localdomain/')
    @patch('flask.request.args.get', return_value=None)
    @patch('flask.request')
    @patch('flask.g')
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_text2markdown(self, g, req, reqget):
        ''' Test the test2markdown method in pagure.lib.query. '''
        pagure.config.config['TESTING'] = True
        pagure.config.config['SERVER_NAME'] = 'localhost.localdomain'

        # This creates:
        # project: test
        # fork: pingou/test
        # PR#1 to project test
        self.test_new_pull_request()

        # create an issue (will be #2) in 'test' project
        repo = pagure.lib.query._get_project(self.session, 'test')
        iss = pagure.lib.query.new_issue(
            issue_id=2,
            session=self.session,
            repo=repo,
            title='test issue',
            content='content test issue',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(iss.id, 2)
        self.assertEqual(iss.title, 'test issue')

        # create PR#2 to project pingou/test
        forked_repo = pagure.lib.query._get_project(self.session, 'test', user='pingou')
        req = pagure.lib.query.new_pull_request(
            requestid=2,
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=forked_repo,
            branch_to='master',
            title='test pull-request in fork',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 2)
        self.assertEqual(req.title, 'test pull-request in fork')

        # Create the project ns/test
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        self.session.add(item)
        self.session.commit()

        iss = pagure.lib.query.new_issue(
            issue_id=4,
            session=self.session,
            repo=item,
            title='test issue',
            content='content test issue',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(iss.id, 4)
        self.assertEqual(iss.title, 'test issue')

        # Fork ns/test to pingou
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test',
            namespace='ns',
            description='Forked namespaced test project #1',
            is_fork=True,
            parent_id=item.id,
            hook_token='aaabbbrrrbb',
        )
        self.session.add(item)
        self.session.commit()

        iss = pagure.lib.query.new_issue(
            issue_id=7,
            session=self.session,
            repo=item,
            title='test issue #7',
            content='content test issue #7 in forked repo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(iss.id, 7)
        self.assertEqual(iss.title, 'test issue #7')

        iss = pagure.lib.query.new_issue(
            issue_id=8,
            session=self.session,
            repo=item,
            title='private issue #8',
            content='Private content test issue #8 in forked repo',
            user='pingou',
            private=True,
        )
        self.session.commit()
        self.assertEqual(iss.id, 8)
        self.assertEqual(iss.title, 'private issue #8')

        # newer bleach allow to customize the protocol supported
        import bleach
        bleach_v = bleach.__version__.split('.')
        for idx, val in enumerate(bleach_v):
            try:
                val = int(val)
            except ValueError:
                pass
            bleach_v[idx] = val

        texts = [
            'foo bar test#1 see?',
            'foo bar pingou/test#2 I mean, really',
            'foo bar fork/pingou/test#2 bouza!',
            'foo bar forks/pingou/test#2 bouza!',
            'foo bar ns/test3#4 bouza!',
            'foo bar fork/user/ns/test#5 bouza!',
            'foo bar fork/pingou/ns/test#7 bouza!',
            'test#1 bazinga!',
            'pingou opened the PR forks/pingou/test#2',
            'fork/pingou/ns/test#8 is private',
            'implicit link to #1',
            'implicit link .#1. with non-whitespace, non-word characters',
            '#2 - implicit link at start of line',
            '#2. implicit link at start of line with no whitespace after',
            '#regular header',
            '#34 looks like an implicit link, but no issue 34',
            'pingou committed on test#9364354a4555ba17aa60f0dc844d70b74eb1aecd',
            'irc://pagure.io',
            'ircs://pagure.io',
            'http://pagure.io',
            'https://pagure.io',
            '<https://pagure.io/pagure>',
            '~~foo~~',
            '~~foo bar~~',
            '~~[BZ#1435310](https://bugzilla.redhat.com/1435310)~~',
            "~~[BZ#1435310](https://bugzilla.redhat.com/1435310) avc denial "
            "during F26AH boot 'error_name=org.freedesktop.systemd1."
            "NoSuchDynamicUser'~~",
            '``~~foo bar~~``',
            '~~foo bar~~ and ~~another ~~',
            'lets mention @pingou',
            '@pingou at start of line',
            'but not someone@pingou.com',
            '[![Fedora_infinity_small.png]'
            '(/test/issue/raw/Fedora_infinity_small.png)]'
            '(/test/issue/raw/Fedora_infinity_small.png)',
        ]
        expected = [
            # 'foo bar test#1 see?',
            '<p>foo bar <a href="http://localhost.localdomain/test/pull-request/1"'
            ' title="[Open] test pull-request">test#1</a> see?</p>',
            # 'foo bar pingou/test#2 I mean, really', -- unknown namespace
            '<p>foo bar pingou/test#2 I mean, really</p>',
            # 'foo bar fork/pingou/test#2 bouza!',
            '<p>foo bar <a href="http://localhost.localdomain/fork/'
            'pingou/test/pull-request/2" title="[Open] test pull-request in fork">'
            'pingou/test#2</a> bouza!</p>',
            # 'foo bar forks/pingou/test#2 bouza!',  -- the 's' doesn't matter
            '<p>foo bar <a href="http://localhost.localdomain/fork/'
            'pingou/test/pull-request/2" title="[Open] test pull-request in fork">'
            'pingou/test#2</a> bouza!</p>',
            # 'foo bar ns/test3#4 bouza!',
            '<p>foo bar <a href="http://localhost.localdomain/ns/test3/issue/4"'
            ' title="[Open] test issue">ns/test3#4</a> bouza!</p>',
            # 'foo bar fork/user/ns/test#5 bouza!', -- unknown fork
            '<p>foo bar user/ns/test#5 bouza!</p>',
            # 'foo bar fork/pingou/ns/test#7 bouza!',
            '<p>foo bar <a href="http://localhost.localdomain/'
            'fork/pingou/ns/test/issue/7" title="[Open] test issue #7">'
            'pingou/ns/test#7</a> bouza!</p>',
            # 'test#1 bazinga!',
            '<p><a href="http://localhost.localdomain/test/pull-request/1" '
            'title="[Open] test pull-request">test#1</a> bazinga!</p>',
            # 'pingou opened the PR forks/pingou/test#2'
            '<p>pingou opened the PR <a href="http://localhost.localdomain/'
            'fork/pingou/test/pull-request/2" '
            'title="[Open] test pull-request in fork">pingou/test#2</a></p>',
            # 'fork/pingou/ns/test#8 is private',
            '<p><a href="http://localhost.localdomain/fork/pingou/ns/test/issue/8" '
            'title="Private issue">pingou/ns/test#8</a> is private</p>',
            # 'implicit link to #1',
            '<p>implicit link to <a href="http://localhost.localdomain/test/pull-request/1" title="[Open] test pull-request">#1</a></p>',
            # 'implicit link .#1. with non-whitespace, non-word characters',
            '<p>implicit link .<a href="http://localhost.localdomain/test/pull-request/1" title="[Open] test pull-request">#1</a>. with non-whitespace, non-word characters</p>',
            # '#2 - implicit link at start of line',
            '<p><a href="http://localhost.localdomain/test/issue/2" title="[Open] test issue">#2</a> - implicit link at start of line</p>',
            # '#2. implicit link at start of line with no whitespace after',
            '<p><a href="http://localhost.localdomain/test/issue/2" title="[Open] test issue">#2</a>. implicit link at start of line with no whitespace after</p>',
            # '#regular header',
            '<h1>regular header</h1>',
            # '#34 looks like an implicit link, but no issue 34',
            '<h1>34 looks like an implicit link, but no issue 34</h1>',
            # 'pingou committed on test#9364354a4555ba17aa60f0dc844d70b74eb1aecd',
            '<p>pingou committed on <a href="http://localhost.localdomain/'
            'test/c/9364354a4555ba17aa60f0dc844d70b74eb1aecd" '
            'title="Commit 9364354a4555ba17aa60f0dc844d70b74eb1aecd"'
            '>test#9364354a4555ba17aa60f0dc844d70b74eb1aecd</a></p>',
            # 'irc://pagure.io'
            '<p><a href="irc://pagure.io">irc://pagure.io</a></p>',
            # 'ircs://pagure.io' - This is getting cleaned by python-bleach
            # and the version 1.4.3 that we have won't let us adjust the
            # list of supported protocols
            # '<p><a href="ircs://pagure.io">ircs://pagure.io</a></p>',
            '<p><a href="ircs://pagure.io">ircs://pagure.io</a></p>' if
            tuple(bleach_v) >= (1, 5, 0)
            else '<p><a>ircs://pagure.io</a></p>',
            # 'http://pagure.io'
            '<p><a href="http://pagure.io">http://pagure.io</a></p>',
            # 'https://pagure.io'
            '<p><a href="https://pagure.io">https://pagure.io</a></p>',
            # '<https://pagure.io/pagure>'
            '<p><a href="https://pagure.io/pagure">https://pagure.io/pagure'
            '</a></p>',
            # '~~foo~~'
            '<p><del>foo</del></p>',
            # '~~foo bar~~'
            '<p><del>foo bar</del></p>',
            # '~~[BZ#1435310](https://bugzilla.redhat.com/1435310)~~'
            '<p><del><a href="https://bugzilla.redhat.com/1435310">'
            'BZ#1435310</a></del></p>',
            # '~~[BZ#1435310](https://bugzilla.redhat.com/1435310) avc
            # denial during F26AH boot 'error_name=org.freedesktop.systemd1
            # .NoSuchDynamicUser~~'
            "<p><del><a href=\"https://bugzilla.redhat.com/1435310\">"
            "BZ#1435310</a> avc denial during F26AH boot 'error_name="
            "org.freedesktop.systemd1.NoSuchDynamicUser'</del></p>",
            # '``~~foo bar~~``'
            '<p><code>~~foo bar~~</code></p>',
            # '~~foo bar~~ and ~~another ~~',
            '<p><del>foo bar</del> and <del>another </del></p>',
            # 'lets mention @pingou',
            '<p>lets mention <a href="http://localhost.localdomain/user/pingou">@pingou</a></p>',
            # '@pingou at start of line',
            '<p><a href="http://localhost.localdomain/user/pingou">@pingou</a> at start of line</p>',
            # 'but not someone@pingou.com',
            '<p>but not someone@pingou.com</p>',
            # '[![Fedora_infinity_small.png]'
            # '(/test/issue/raw/Fedora_infinity_small.png)]'
            # '(/test/issue/raw/Fedora_infinity_small.png)',
            '<p><a href="/test/issue/raw/Fedora_infinity_small.png"><span>'
            '<img alt="Fedora_infinity_small.png" class="lazyload" '
            'data-src="/test/issue/raw/Fedora_infinity_small.png" src="">'
            '<noscript>'
            '<img alt="Fedora_infinity_small.png" '
            'src="/test/issue/raw/Fedora_infinity_small.png">'
            '</noscript></span></a></p>',
        ]

        with self.app.application.app_context():
            g.session = self.session
            for idx, text in enumerate(texts):
                html = pagure.lib.query.text2markdown(text)
                self.assertEqual(html, expected[idx])

    def test_text2markdown_exception(self):
        ''' Test the test2markdown method in pagure.lib.query. '''

        text = 'test#1 bazinga!'
        expected_html = 'test#1 bazinga!'

        html = pagure.lib.query.text2markdown(text)
        self.assertEqual(html, expected_html)

    def test_text2markdown_empty_string(self):
        ''' Test the test2markdown method in pagure.lib.query. '''

        text = ''
        expected_html = ''

        html = pagure.lib.query.text2markdown(text)
        self.assertEqual(html, expected_html)

    def test_get_access_levels(self):
        ''' Test the get_access_levels method in pagure.lib '''

        acls = pagure.lib.query.get_access_levels(self.session)
        self.assertEqual(
            sorted(['admin', 'commit', 'ticket']),
            sorted(acls)
        )

    def test_get_project_users(self):
        ''' Test the get_project_users method when combine is True
        '''

        tests.create_projects(self.session)
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')

        # Default value of combine is True
        # which means the an admin is a user, committer as well
        # and a committer is also a user
        # and a user is just a user
        users = project.get_project_users(access='admin')

        # Only pingou is the admin as of now
        # But, he is the creator and
        # the creator of the project is not listed in user_projects
        # table. Thus, get_projec_users won't return him as an admin
        # He has all the access of an admin though
        self.assertEqual(len(users), 0)
        self.assertEqual(project.user.username, 'pingou')

        # Wrong access level, should raise Accesslevelnotfound exception
        self.assertRaises(
            pagure.exceptions.AccessLevelNotFound,
            project.get_project_users,
            access='owner',
        )

        # Let's add a new user to the project, 'foo'
        # By default, if no access is specified, he becomes an admin
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou'
        )
        self.session.commit()
        # since, he is an admin, the msg should be 'User added'
        self.assertEqual(msg, 'User added')

        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        users = project.get_project_users(access='admin')

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'foo')

        # foo should be a committer as well, since he is an admin
        users = project.get_project_users(access='commit')

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'foo')

        # the admin also has ticket access
        users = project.get_project_users(access='ticket')

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'foo')

        # let's update the access of foo to 'committer'
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')

        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        # No admin now, even though pingou the creator is there
        users = project.get_project_users(access='admin')
        self.assertEqual(len(users), 0)

        users = project.get_project_users(access='commit')
        # foo is the committer currently
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'foo')

        users = project.get_project_users(access='ticket')

        # foo also has ticket rights
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'foo')

        # let's update the access of foo to 'ticket'
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')

        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        # No admin now, even though pingou the creator is there
        users = project.get_project_users(access='admin')
        self.assertEqual(len(users), 0)

        users = project.get_project_users(access='commit')
        # foo deosn't have commit rights now
        self.assertEqual(len(users), 0)

        users = project.get_project_users(access='ticket')

        # foo does have tickets right though
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'foo')

    def test_get_project_users_combine_false(self):
        ''' Test the get_project_users method when combine is False
        '''

        tests.create_projects(self.session)
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')

        # Let's add a new user to the project, 'foo'
        # By default, if no access is specified, he becomes an admin
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou'
        )
        self.session.commit()
        # since, he is an admin, the msg should be 'User added'
        self.assertEqual(msg, 'User added')

        # only one admin
        users = project.get_project_users(access='admin', combine=False)

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'foo')

        # No user with only commit access
        users = project.get_project_users(access='commit', combine=False)
        self.assertEqual(len(users), 0)

        # No user with only ticket access
        users = project.get_project_users(access='ticket', combine=False)
        self.assertEqual(len(users), 0)

        # Update the access level of foo user to commit
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')

        # He is just a committer
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        users = project.get_project_users(access='admin', combine=False)

        self.assertEqual(len(users), 0)

        # He is just a committer
        users = project.get_project_users(access='commit', combine=False)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'foo')

        # He is just a committer
        users = project.get_project_users(access='ticket', combine=False)
        self.assertEqual(len(users), 0)

        # Update the access level of foo user to ticket
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')

        # He is just a ticketer
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        users = project.get_project_users(access='admin',combine=False)

        self.assertEqual(len(users), 0)

        # He is just a ticketer
        users = project.get_project_users(access='commit', combine=False)
        self.assertEqual(len(users), 0)

        # He is just a ticketer
        users = project.get_project_users(access='ticket', combine=False)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'foo')

    def test_get_project_groups(self):
        ''' Test the get_project_groups method when combine is True
        '''

        # Create some projects
        tests.create_projects(self.session)
        # Create a group in database
        msg = pagure.lib.query.add_group(
            self.session,
            group_name='JL',
            display_name='Justice League',
            description='Nope, it\'s not JLA anymore',
            group_type='user',
            user='foo',
            is_admin=False,
            blacklist=pagure.config.config.get('BLACKLISTED_PROJECTS')
        )

        self.assertEqual(
            msg,
            'User `foo` added to the group `JL`.'
        )

        # Add the group to project we just created, test
        # First add it as an admin
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        msg = pagure.lib.query.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

        # Now, the group is an admin in the project
        # so, it must have access to everything
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        groups = project.get_project_groups(access='admin')

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].display_name, 'Justice League')
        self.assertEqual(len(project.admin_groups), 1)
        self.assertEqual(
            project.admin_groups[0].display_name,
            'Justice League'
        )

        # The group should be committer as well
        groups = project.get_project_groups(access='commit')
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].display_name, 'Justice League')
        self.assertEqual(len(project.committer_groups), 1)
        self.assertEqual(
            project.committer_groups[0].display_name,
            'Justice League'
        )

        # The group should be ticketer as well
        groups = project.get_project_groups(access='ticket')
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].display_name, 'Justice League')
        self.assertEqual(len(project.groups), 1)
        self.assertEqual(
            project.groups[0].display_name,
            'Justice League'
        )

        # Update the access level of the group, JL to commit
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        msg = pagure.lib.query.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')

        # It shouldn't be an admin
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        groups = project.get_project_groups(access='admin')

        self.assertEqual(len(groups), 0)
        self.assertEqual(len(project.admin_groups), 0)

        # It is a committer
        groups = project.get_project_groups(access='commit')
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].display_name, 'Justice League')
        self.assertEqual(len(project.committer_groups), 1)
        self.assertEqual(
            project.committer_groups[0].display_name,
            'Justice League'
        )

        # The group should be ticketer as well
        groups = project.get_project_groups(access='ticket')
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].display_name, 'Justice League')
        self.assertEqual(len(project.groups), 1)
        self.assertEqual(
            project.groups[0].display_name,
            'Justice League'
        )

        # Update the access of group JL to ticket
        msg = pagure.lib.query.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')

        # It is not an admin
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        groups = project.get_project_groups(access='admin')

        self.assertEqual(len(groups), 0)
        self.assertEqual(len(project.admin_groups), 0)

        # The group shouldn't be a committer
        groups = project.get_project_groups(access='commit')
        self.assertEqual(len(groups), 0)
        self.assertEqual(len(project.committer_groups), 0)

        # The group should be ticketer
        groups = project.get_project_groups(access='ticket')
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].display_name, 'Justice League')
        self.assertEqual(len(project.groups), 1)
        self.assertEqual(
            project.groups[0].display_name,
            'Justice League'
        )

    def test_get_project_groups_combine_false(self):
        ''' Test the get_project_groups method when combine is False
        '''

        # Create some projects
        tests.create_projects(self.session)
        # Create a group in database
        msg = pagure.lib.query.add_group(
            self.session,
            group_name='JL',
            display_name='Justice League',
            description='Nope, it\'s not JLA anymore',
            group_type='user',
            user='foo',
            is_admin=False,
            blacklist=pagure.config.config.get('BLACKLISTED_PROJECTS')
        )

        self.assertEqual(
            msg,
            'User `foo` added to the group `JL`.'
        )

        # Add the group to project we just created, test
        # First add it as an admin
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        msg = pagure.lib.query.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

        # Now, the group is an admin in the project
        # so, it must have access to everything
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        groups = project.get_project_groups(access='admin', combine=False)

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].display_name, 'Justice League')
        self.assertEqual(len(project.admin_groups), 1)
        self.assertEqual(
            project.admin_groups[0].display_name,
            'Justice League'
        )

        # The group shoudn't be a committer
        groups = project.get_project_groups(access='commit', combine=False)
        self.assertEqual(len(groups), 0)

        # The group shoudn't be a ticketer
        groups = project.get_project_groups(access='ticket', combine=False)
        self.assertEqual(len(groups), 0)

        # Update the access level of the group, JL to commit
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        msg = pagure.lib.query.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')

        # It shouldn't be an admin
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        groups = project.get_project_groups(access='admin', combine=False)

        self.assertEqual(len(groups), 0)

        # It is a committer
        groups = project.get_project_groups(access='commit', combine=False)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].display_name, 'Justice League')
        self.assertEqual(len(project.committer_groups), 1)
        self.assertEqual(
            project.committer_groups[0].display_name,
            'Justice League'
        )

        # The group shouldn't be ticketer
        groups = project.get_project_groups(access='ticket', combine=False)
        self.assertEqual(len(groups), 0)

        # Update the access of group JL to ticket
        msg = pagure.lib.query.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')

        # It is not an admin
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        groups = project.get_project_groups(access='admin', combine=False)

        self.assertEqual(len(groups), 0)

        # The group shouldn't be a committer
        groups = project.get_project_groups(access='commit', combine=False)
        self.assertEqual(len(groups), 0)

        # The group should be ticketer
        groups = project.get_project_groups(access='ticket', combine=False)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].display_name, 'Justice League')
        self.assertEqual(len(project.groups), 1)
        self.assertEqual(
            project.groups[0].display_name,
            'Justice League'
        )

    def test_get_obj_access_user(self):
        """ Test the get_obj_access method of pagure.lib
        for model.User object """

        # Create the projects
        tests.create_projects(self.session)

        # Add a user object - make him an admin first
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou'
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        user = pagure.lib.query.get_user(self.session, key='foo')
        # He should be an admin
        access_obj = pagure.lib.query.get_obj_access(
            self.session,
            project_obj=project,
            obj=user
        )
        self.assertEqual(access_obj.access, 'admin')

        # Update and check for commit access
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')

        # He should be a committer
        access_obj = pagure.lib.query.get_obj_access(
            self.session,
            project_obj=project,
            obj=user
        )
        self.assertEqual(access_obj.access, 'commit')

        # Update and check for ticket access
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')

        # He should be a ticketer
        access_obj = pagure.lib.query.get_obj_access(
            self.session,
            project_obj=project,
            obj=user
        )
        self.assertEqual(access_obj.access, 'ticket')

    def test_get_obj_access_group(self):
        """ Test the get_obj_access method of pagure.lib
        for model.PagureGroup object """

        # Create the projects
        tests.create_projects(self.session)

        # Create a group in database
        msg = pagure.lib.query.add_group(
            self.session,
            group_name='JL',
            display_name='Justice League',
            description='Nope, it\'s not JLA anymore',
            group_type='user',
            user='foo',
            is_admin=False,
            blacklist=pagure.config.config.get('BLACKLISTED_PROJECTS')
        )

        self.assertEqual(
            msg,
            'User `foo` added to the group `JL`.'
        )

        # Add a group object - make him an admin first
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        msg = pagure.lib.query.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

        group = pagure.lib.query.search_groups(self.session, group_name='JL')
        # He should be an admin
        access_obj = pagure.lib.query.get_obj_access(
            self.session,
            project_obj=project,
            obj=group
        )
        self.assertEqual(access_obj.access, 'admin')

        # Update and check for commit access
        msg = pagure.lib.query.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')

        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        # He should be a committer
        access_obj = pagure.lib.query.get_obj_access(
            self.session,
            project_obj=project,
            obj=group,
        )
        self.assertEqual(access_obj.access, 'commit')

        # Update and check for ticket access
        msg = pagure.lib.query.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')
        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')

        # He should be a ticketer
        access_obj = pagure.lib.query.get_obj_access(
            self.session,
            project_obj=project,
            obj=group,
        )
        self.assertEqual(access_obj.access, 'ticket')

    def test_set_watch_obj(self):
        """ Test the set_watch_obj method in pagure.lib """
        # Create the project ns/test
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Create the ticket
        iss = pagure.lib.query.new_issue(
            issue_id=4,
            session=self.session,
            repo=item,
            title='test issue',
            content='content test issue',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(iss.id, 4)
        self.assertEqual(iss.title, 'test issue')

        # Unknown user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.set_watch_obj,
            self.session, 'unknown', iss, True
        )

        # Invalid object to watch - project
        self.assertRaises(
            pagure.exceptions.InvalidObjectException,
            pagure.lib.query.set_watch_obj,
            self.session, 'foo', iss.project, True
        )

        # Invalid object to watch - string
        self.assertRaises(
            AttributeError,
            pagure.lib.query.set_watch_obj,
            self.session, 'foo', 'ticket', True
        )

        # Watch the ticket
        out = pagure.lib.query.set_watch_obj(self.session, 'foo', iss, True)
        self.assertEqual(out, 'You are now watching this issue')

        # Un-watch the ticket
        out = pagure.lib.query.set_watch_obj(self.session, 'foo', iss, False)
        self.assertEqual(out, 'You are no longer watching this issue')


    def test_tokenize_search_string(self):
        """ Test the tokenize_search_string function. """
        # These are the tests performed to make sure we tokenize correctly.
        # This is in the form: input string, custom fields, remaining pattern
        tests = [
            ('test123', {}, 'test123'),
            ('test:key test123', {'test': 'key'}, 'test123'),
            ('test:"key with spaces" test123', {'test': 'key with spaces'},
             'test123'),
            ('test123 test:key test456', {'test': 'key'}, 'test123 test456'),
            ('test123 test:"key with spaces" key2:value12 test456',
             {'test': 'key with spaces', 'key2': 'value12'},
             'test123 test456')
            ]
        for inp, flds, rem in tests:
            self.assertEqual(pagure.lib.query.tokenize_search_string(inp),
                             (flds, rem))

    def test_save_report(self):
        """ Test the save_report function. """
        # Create the projects
        tests.create_projects(self.session)

        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        self.assertEqual(project.reports, {})

        name = 'test report'
        url = '?foo=bar&baz=biz'

        pagure.lib.query.save_report(
            self.session,
            repo=project,
            name=name,
            url=url,
            username=None
        )

        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        self.assertEqual(
            project.reports,
            {'test report': {'baz': 'biz', 'foo': 'bar'}}
        )

        name = 'test report #2'
        url = '?foo=bar&foo=none&foo=baz'

        pagure.lib.query.save_report(
            self.session,
            repo=project,
            name=name,
            url=url,
            username=None
        )

        project = pagure.lib.query.get_authorized_project(self.session, project_name='test')
        self.assertEqual(
            project.reports,
            {
                'test report': {'baz': 'biz', 'foo': 'bar'},
                'test report #2': {'foo': ['bar', 'none', 'baz']}
            }
        )

    def test_text2markdown_table(self):
        """ Test the text2markdown function with a markdown table. """
        v = tuple([int(c) for c in markdown.version.split('.')])

        if v < (2, 6, 7):
            raise unittest.case.SkipTest(
                'Skipping on old markdown that do not strip the orientation row'
            )

        text = """
| Left-aligned | Center-aligned | Right-aligned |
| :---         |    :---:       |          ---: |
| git status   | git status     | git status    |
| git diff     | git diff       | git diff      |


foo bar
        """

        expected = """<table>
<thead>
<tr>
<th align="left">Left-aligned</th>
<th align="center">Center-aligned</th>
<th align="right">Right-aligned</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">git status</td>
<td align="center">git status</td>
<td align="right">git status</td>
</tr>
<tr>
<td align="left">git diff</td>
<td align="center">git diff</td>
<td align="right">git diff</td>
</tr>
</tbody>
</table>
<p>foo bar</p>"""

        with self.app.application.app_context():
            html = pagure.lib.query.text2markdown(text)
            self.assertEqual(html, expected)


    def test_text2markdown_table_old_mk(self):
        """ Test the text2markdown function with a markdown table using the old
        format where the orientation instruction are provided next to the column
        delimiter unlike what can be done with more recent version of markdown.
        """

        text = """
| Left-aligned | Center-aligned | Right-aligned |
|:---          |:--------------:|           ---:|
| git status   | git status     | git status    |
| git diff     | git diff       | git diff      |


foo bar
        """

        expected = """<table>
<thead>
<tr>
<th align="left">Left-aligned</th>
<th align="center">Center-aligned</th>
<th align="right">Right-aligned</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">git status</td>
<td align="center">git status</td>
<td align="right">git status</td>
</tr>
<tr>
<td align="left">git diff</td>
<td align="center">git diff</td>
<td align="right">git diff</td>
</tr>
</tbody>
</table>
<p>foo bar</p>"""

        with self.app.application.app_context():
            html = pagure.lib.query.text2markdown(text)
            self.assertEqual(html, expected)

    def test_set_redis(self):
        """ Test the set_redis function of pagure.lib.query. """
        self.assertIsNone(pagure.lib.query.REDIS)
        pagure.lib.query.set_redis('0.0.0.0', 6379, 0)
        self.assertIsNotNone(pagure.lib.query.REDIS)

    def test_set_pagure_ci(self):
        """ Test the set_pagure_ci function of pagure.lib.query. """
        # self.assertIn(pagure.lib.query.PAGURE_CI, [None, ['jenkins']])
        pagure.lib.query.set_pagure_ci(True)
        self.assertIsNotNone(pagure.lib.query.PAGURE_CI)
        self.assertTrue(pagure.lib.query.PAGURE_CI)

    def test_get_user_invalid_user(self):
        """ Test the get_user function of pagure.lib.query. """
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.get_user,
            self.session,
            'unknown'
        )

    def test_get_user_username(self):
        """ Test the get_user function of pagure.lib.query. """
        user = pagure.lib.query.get_user(self.session, 'foo')
        self.assertEqual(user.username, 'foo')

    def test_get_user_email(self):
        """ Test the get_user function of pagure.lib.query. """
        user = pagure.lib.query.get_user(self.session, 'bar@pingou.com')
        self.assertEqual(user.username, 'pingou')

    def test_is_valid_ssh_key_empty(self):
        """ Test the is_valid_ssh_key function of pagure.lib.query. """
        self.assertIsNone(pagure.lib.query.is_valid_ssh_key(''))

    def test_is_valid_ssh_key_invalid(self):
        """ Test the is_valid_ssh_key function of pagure.lib.query. """
        self.assertEqual(pagure.lib.query.is_valid_ssh_key('nonsense'), False)

    def test_is_valid_ssh_key(self):
        """ Test the is_valid_ssh_key function of pagure.lib.query. """
        keyinfo = pagure.lib.query.is_valid_ssh_key('''ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDtgzSO9d1IrKdmyBFUvtAJPLgGOhp0lSySkWRSe+/+3KXYjSnsLnCJQlO5M7JfaXhtTHEow86rh4W9+FoJdzo5iocAwH5xPZ5ttHLy7VHgTzNMUeMgKpjy6bBOdPoGPPG4mo7QCMCRJdWBRDv4OSEMLU5jQAvC272YK2V8L918VQ== root@test''')
        keys = keyinfo.split('\n')
        self.assertEqual(len(keys), 2)
        self.assertEqual(keys[1], '')
        key = keys[0].split(' ')
        self.assertEqual(key[0], '1024')
        # We should always get the SHA256 version
        self.assertEqual(key[1], 'SHA256:ztcRXIq7y/HNfwwscrexCyDF46/Pn/oHTkBZx87GwI8')
        self.assertEqual(key[3], '(RSA)')

    def test_create_deploykeys_ssh_keys_on_disk_empty(self):
        """ Test the create_deploykeys_ssh_keys_on_disk function of
        pagure.lib.query. """
        self.assertIsNone(
            pagure.lib.query.create_deploykeys_ssh_keys_on_disk(None, None))
        self.assertFalse(
            os.path.exists(os.path.join(self.path, 'deploykeys', 'test')))

    def test_create_deploykeys_ssh_keys_on_disk_nokey(self):
        """ Test the create_deploykeys_ssh_keys_on_disk function of
        pagure.lib.query. """
        tests.create_projects(self.session)
        project = pagure.lib.query._get_project(self.session, 'test')

        self.assertIsNone(
            pagure.lib.query.create_deploykeys_ssh_keys_on_disk(
                project, self.path))
        self.assertTrue(
            os.path.exists(os.path.join(self.path, 'deploykeys', 'test')))
        self.assertEqual(
            os.listdir(os.path.join(self.path, 'deploykeys', 'test')), [])

    @patch('pagure.lib.query.is_valid_ssh_key', MagicMock(return_value='foo bar'))
    def test_create_deploykeys_ssh_keys_on_disk(self):
        """ Test the create_deploykeys_ssh_keys_on_disk function of
        pagure.lib.query. """
        tests.create_projects(self.session)
        project = pagure.lib.query._get_project(self.session, 'test')

        # Add a deploy key to the project
        pingou = pagure.lib.query.get_user(self.session, 'pingou')
        msg = pagure.lib.query.add_sshkey_to_project_or_user(
            self.session,
            project=project,
            ssh_key='foo bar',
            pushaccess=False,
            creator=pingou,
        )
        self.assertEqual(msg, 'SSH key added')

        self.assertIsNone(
            pagure.lib.query.create_deploykeys_ssh_keys_on_disk(
                project, self.path))
        self.assertTrue(
            os.path.exists(os.path.join(self.path, 'deploykeys', 'test')))
        self.assertEqual(
            os.listdir(os.path.join(self.path, 'deploykeys', 'test')),
            ['deploykey_test_1.pub'])

        # Remove the deploykey
        project = pagure.lib.query._get_project(self.session, 'test')
        self.session.delete(project.deploykeys[0])
        self.session.commit()

        # Remove the file on disk
        self.assertIsNone(
            pagure.lib.query.create_deploykeys_ssh_keys_on_disk(
                project, self.path))
        self.assertTrue(
            os.path.exists(os.path.join(self.path, 'deploykeys', 'test')))
        self.assertEqual(
            os.listdir(os.path.join(self.path, 'deploykeys', 'test')), [])

    @patch('pagure.lib.query.is_valid_ssh_key', MagicMock(return_value='\nfoo bar'))
    def test_create_deploykeys_ssh_keys_on_disk_empty_first_key(self):
        """ Test the create_deploykeys_ssh_keys_on_disk function of
        pagure.lib.query. """
        tests.create_projects(self.session)
        project = pagure.lib.query._get_project(self.session, 'test')

        # Add a deploy key to the project
        new_key_obj = pagure.lib.model.SSHKey(
            project_id=project.id,
            pushaccess=False,
            public_ssh_key='\n foo bar',
            ssh_short_key='\n foo bar',
            ssh_search_key='\n foo bar',
            creator_user_id=1  # pingou
        )

        self.session.add(new_key_obj)
        self.session.commit()

        self.assertIsNone(
            pagure.lib.query.create_deploykeys_ssh_keys_on_disk(
                project, self.path))
        self.assertTrue(
            os.path.exists(os.path.join(self.path, 'deploykeys', 'test')))
        self.assertEqual(
            os.listdir(os.path.join(self.path, 'deploykeys', 'test')),
            [])

    def test_create_deploykeys_ssh_keys_on_disk_invalid(self):
        """ Test the create_deploykeys_ssh_keys_on_disk function of
        pagure.lib.query. """
        tests.create_projects(self.session)
        project = pagure.lib.query._get_project(self.session, 'test')

        # Add a deploy key to the project
        new_key_obj = pagure.lib.model.SSHKey(
            project_id=project.id,
            pushaccess=False,
            public_ssh_key='foo bar',
            ssh_short_key='foo bar',
            ssh_search_key='foo bar',
            creator_user_id=1  # pingou
        )

        self.session.add(new_key_obj)
        self.session.commit()

        self.assertIsNone(
            pagure.lib.query.create_deploykeys_ssh_keys_on_disk(
                project, self.path))
        self.assertTrue(
            os.path.exists(os.path.join(self.path, 'deploykeys', 'test')))
        self.assertEqual(
            os.listdir(os.path.join(self.path, 'deploykeys', 'test')),
            [])

    def test_create_user_ssh_keys_on_disk_none(self):
        """ Test the create_user_ssh_keys_on_disk function of pagure.lib.query. """
        self.assertIsNone(
            pagure.lib.query.create_user_ssh_keys_on_disk(None, None))

    def test_update_user_settings_invalid_user(self):
        """ Test the update_user_settings function of pagure.lib.query. """
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.update_user_settings,
            session=self.session,
            settings={},
            user='invalid'
        )

    def test_update_user_settings_no_change(self):
        """ Test the update_user_settings function of pagure.lib.query. """

        # First update the setting
        msg = pagure.lib.query.update_user_settings(
            session=self.session,
            settings={'cc_me_to_my_actions': True},
            user='pingou'
        )
        self.assertEqual(msg, 'Successfully edited your settings')

        # Then change it back to its default
        msg = pagure.lib.query.update_user_settings(
            session=self.session,
            settings={},
            user='pingou'
        )
        self.assertEqual(msg, 'Successfully edited your settings')

    def test_update_user_settings_no_data(self):
        """ Test the update_user_settings function of pagure.lib.query. """

        msg = pagure.lib.query.update_user_settings(
            session=self.session,
            settings={'cc_me_to_my_actions': False},
            user='pingou'
        )
        self.assertEqual(msg, 'No settings to change')

    def test_update_user_settings(self):
        """ Test the update_user_settings function of pagure.lib.query. """

        msg = pagure.lib.query.update_user_settings(
            session=self.session,
            settings={'cc_me_to_my_actions': True},
            user='pingou'
        )
        self.assertEqual(msg, 'Successfully edited your settings')

    @patch.dict(pagure.config.config, {
        'ALLOWED_EMAIL_DOMAINS': ["pingoured.fr"]}, clear=True)
    def test_add_email_to_user_with_logs(self):
        """ Test the add_email_to_user function of pagure.lib when there
        are log entries associated to the email added.
        """
        user = pagure.lib.query.search_user(self.session, username='pingou')

        # Add a couple of log entries associated with the new email
        for i in range(3):
            log = pagure.lib.model.PagureLog(
                user_email='new_email@pingoured.fr',
                log_type='commit',
                ref_id=i
            )
            self.session.add(log)
            self.session.commit()

        # Check emails before
        self.assertEqual(len(user.emails), 2)

        # Add the new_email to the user
        pagure.lib.query.add_email_to_user(
            self.session, user, 'new_email@pingoured.fr'
        )
        self.session.commit()

        # Check emails after
        self.assertEqual(len(user.emails), 3)

        # add another email address that is not in an allowed domain
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_email_to_user,
            session=self.session,
            user=user,
            user_email='foo@bar.com'
        )
        self.session.commit()
        # Check emails after
        self.assertEqual(len(user.emails), 3)

        # redo tests with 2 allowed domains
        pagure.config.config['ALLOWED_EMAIL_DOMAINS'] = ["pingoured.fr", "example.com"]
        # Add the new_email to the user
        pagure.lib.query.add_email_to_user(
            self.session, user, 'another_email@example.com'
        )
        self.session.commit()
        # Check emails after
        self.assertEqual(len(user.emails), 4)

        # add another email address that is not in an allowed domain
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_email_to_user,
            session=self.session,
            user=user,
            user_email='another_foo@bar.com'
        )
        self.session.commit()
        # Check emails after
        self.assertEqual(len(user.emails), 4)

    @patch('pagure.lib.query.is_valid_ssh_key', MagicMock(return_value='foo bar'))
    def test_update_user_ssh_valid_key(self):
        """ Test the update_user_ssh function of pagure.lib.query. """
        pagure.SESSION = self.session

        pagure.lib.query.update_user_ssh(
            self.session,
            user='pingou',
            ssh_key='foo key',
            keydir=self.path,
        )
        self.session.commit()

        self.assertTrue(
            os.path.exists(os.path.join(self.path, 'keys_0'))
        )
        self.assertEqual(
            os.listdir(os.path.join(self.path, 'keys_0')),
            ['pingou.pub']
        )

    def test_add_user_pending_email_existing_email(self):
        """ Test the add_user_pending_email function of pagure.lib.query. """
        user = pagure.lib.query.search_user(self.session, username='pingou')

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_user_pending_email,
            session=self.session,
            userobj=user,
            email='foo@bar.com'
        )

    @patch('pagure.lib.notify.notify_new_email', MagicMock(return_value=True))
    @patch.dict(pagure.config.config, {
        'ALLOWED_EMAIL_DOMAINS': ["pingoured.fr"]}, clear=True)
    def test_add_user_pending_email(self):
        """ Test the add_user_pending_email function of pagure.lib.query. """
        user = pagure.lib.query.search_user(self.session, username='pingou')

        self.assertEqual(len(user.emails), 2)
        self.assertEqual(len(user.emails_pending), 0)

        pagure.lib.query.add_user_pending_email(
            session=self.session,
            userobj=user,
            email='new_mail@pingoured.fr'
        )
        self.session.commit()

        self.assertEqual(len(user.emails), 2)
        self.assertEqual(len(user.emails_pending), 1)
        # add another email address that is not allowed
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.add_user_pending_email,
            session=self.session,
            userobj=user,
            email='foo@bar.com'
        )
        self.session.commit()

        self.assertEqual(len(user.emails), 2)
        self.assertEqual(len(user.emails_pending), 1)

    def test_resend_pending_email_someone_else_email(self):
        """ Test the resend_pending_email function of pagure.lib.query. """
        user = pagure.lib.query.search_user(self.session, username='pingou')

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.resend_pending_email,
            session=self.session,
            userobj=user,
            email='foo@bar.com'
        )

    def test_resend_pending_email_email_validated(self):
        """ Test the resend_pending_email function of pagure.lib.query. """
        user = pagure.lib.query.search_user(self.session, username='pingou')

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.query.resend_pending_email,
            session=self.session,
            userobj=user,
            email='foo@pingou.com'
        )

    def test_get_acls(self):
        """ Test the get_acls function of pagure.lib.query. """
        acls = pagure.lib.query.get_acls(self.session)
        self.assertEqual(
            sorted([a.name for a in acls]),
            [
                'commit_flag',
                'create_branch',
                'create_project',
                'fork_project',
                'generate_acls_project',
                'internal_access',
                'issue_assign',
                'issue_change_status',
                'issue_comment',
                'issue_create',
                'issue_subscribe',
                'issue_update',
                'issue_update_custom_fields',
                'issue_update_milestone',
                'modify_project',
                'pull_request_close',
                'pull_request_comment',
                'pull_request_create',
                'pull_request_flag',
                'pull_request_merge',
                'pull_request_rebase',
                'pull_request_subscribe',
                'update_watch_status',
            ]
        )

    def test_get_acls_restrict_one(self):
        """ Test the get_acls function of pagure.lib.query. """
        acls = pagure.lib.query.get_acls(self.session, restrict='create_project')
        self.assertEqual([a.name for a in acls], ['create_project'])

    def test_get_acls_restrict_two(self):
        """ Test the get_acls function of pagure.lib.query. """
        acls = pagure.lib.query.get_acls(
            self.session, restrict=['create_project', 'issue_create'])
        self.assertEqual(
            [a.name for a in acls],
            ['create_project', 'issue_create'])

    def test_filter_img_src(self):
        """ Test the filter_img_src function of pagure.lib.query. """
        for name in ('alt', 'height', 'width', 'class'):
            self.assertTrue(pagure.lib.query.filter_img_src(name, 'caption'))

        self.assertTrue(pagure.lib.query.filter_img_src(
            'src', '/path/to/image'))
        self.assertTrue(pagure.lib.query.filter_img_src(
            'src', 'http://localhost.localdomain/path/to/image'))
        self.assertFalse(pagure.lib.query.filter_img_src(
            'src', 'http://foo.org/path/to/image'))

        self.assertFalse(pagure.lib.query.filter_img_src(
            'anything', 'http://foo.org/path/to/image'))

    def test_clean_input(self):
        """ Test the clean_input function of pagure.lib.query. """
        text = '<a href="/path" title="click me!">Click here</a>'
        output = pagure.lib.query.clean_input(text)
        self.assertEqual(output, text)

    def test_could_be_text(self):
        """ Test the could_be_text function of pagure.lib.query. """
        self.assertTrue(pagure.lib.query.could_be_text(b'foo'))
        self.assertTrue(pagure.lib.query.could_be_text('fâö'.encode("utf-8")))
        self.assertFalse(pagure.lib.query.could_be_text(b'\x89PNG\r\n\x1a\n\x00'))

    def test_set_custom_key_fields_empty(self):
        """ Test the set_custom_key_fields function of pagure.lib.query. """
        tests.create_projects(self.session)
        project = pagure.lib.query._get_project(self.session, 'test')
        self.assertIsNotNone(project)

        msg = pagure.lib.query.set_custom_key_fields(
            session=self.session,
            project=project,
            fields=[],
            types=[],
            data=[],
            notify=False
        )
        self.session.commit()
        self.assertEqual(msg, 'List of custom fields updated')

    def test_set_custom_key_fields(self):
        """ Test the set_custom_key_fields function of pagure.lib.query. """
        tests.create_projects(self.session)
        project = pagure.lib.query._get_project(self.session, 'test')
        self.assertIsNotNone(project)

        # Set a custom key
        msg = pagure.lib.query.set_custom_key_fields(
            session=self.session,
            project=project,
            fields=['upstream'],
            types=['url'],
            data=[None],
            notify=False
        )
        self.session.commit()
        self.assertEqual(msg, 'List of custom fields updated')

        # Set another one, with notifications on
        msg = pagure.lib.query.set_custom_key_fields(
            session=self.session,
            project=project,
            fields=['bugzilla_url'],
            types=['url'],
            data=[None],
            notify=['on']
        )
        self.session.commit()
        self.assertEqual(msg, 'List of custom fields updated')

        # Re-set the second one but with notifications off
        msg = pagure.lib.query.set_custom_key_fields(
            session=self.session,
            project=project,
            fields=['bugzilla_url'],
            types=['url'],
            data=[None],
            notify=['off']
        )
        self.session.commit()
        self.assertEqual(msg, 'List of custom fields updated')

    @patch('pagure.lib.query.REDIS')
    def test_set_custom_key_value_boolean(self, mock_redis):
        """ Test the set_custom_key_value function of pagure.lib.query. """
        mock_redis.return_value = True

        tests.create_projects(self.session)
        project = pagure.lib.query._get_project(self.session, 'test')
        self.assertIsNotNone(project)

        # Set a custom key
        msg = pagure.lib.query.set_custom_key_fields(
            session=self.session,
            project=project,
            fields=['tested'],
            types=['boolean'],
            data=[None],
            notify=False
        )
        self.session.commit()
        self.assertEqual(msg, 'List of custom fields updated')

        # Create issues
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=project,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        issue = pagure.lib.query.search_issues(self.session, project, issueid=1)

        self.assertEqual(len(project.issue_keys), 1)
        self.assertEqual(project.issue_keys[0].key_type, 'boolean')
        msg = pagure.lib.query.set_custom_key_value(
            session=self.session,
            issue=issue,
            key=project.issue_keys[0],
            value=True
        )
        self.session.commit()
        self.assertEqual(msg, 'Custom field tested adjusted to True')

        # Update it a second time to trigger edit
        msg = pagure.lib.query.set_custom_key_value(
            session=self.session,
            issue=issue,
            key=project.issue_keys[0],
            value=False
        )
        if str(self.session.bind.engine.url).startswith('sqlite'):
            self.assertEqual(
                msg, 'Custom field tested reset (from 1)')
        else:
            self.assertEqual(
                msg, 'Custom field tested reset (from true)')

        self.assertEqual(mock_redis.publish.call_count, 2)

    @patch('pagure.lib.query.REDIS')
    def test_set_custom_key_value_boolean_private_issue(self, mock_redis):
        """ Test the set_custom_key_value function of pagure.lib.query. """
        mock_redis.return_value = True

        tests.create_projects(self.session)
        project = pagure.lib.query._get_project(self.session, 'test')
        self.assertIsNotNone(project)

        # Set a custom key
        msg = pagure.lib.query.set_custom_key_fields(
            session=self.session,
            project=project,
            fields=['tested'],
            types=['boolean'],
            data=[None],
            notify=False
        )
        self.session.commit()
        self.assertEqual(msg, 'List of custom fields updated')

        # Create issues
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=project,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        issue = pagure.lib.query.search_issues(self.session, project, issueid=1)

        self.assertEqual(len(project.issue_keys), 1)
        self.assertEqual(project.issue_keys[0].key_type, 'boolean')
        msg = pagure.lib.query.set_custom_key_value(
            session=self.session,
            issue=issue,
            key=project.issue_keys[0],
            value=True
        )
        self.session.commit()
        self.assertEqual(msg, 'Custom field tested adjusted to True')

        # Update it a second time to trigger edit
        msg = pagure.lib.query.set_custom_key_value(
            session=self.session,
            issue=issue,
            key=project.issue_keys[0],
            value=False
        )
        self.session.commit()
        if str(self.session.bind.engine.url).startswith('sqlite'):
            self.assertEqual(
                msg, 'Custom field tested reset (from 1)')
        else:
            self.assertEqual(
                msg, 'Custom field tested reset (from true)')

        self.assertEqual(mock_redis.publish.call_count, 2)

    @patch('pagure.lib.query.REDIS')
    def test_set_custom_key_value_text(self, mock_redis):
        """ Test the set_custom_key_value function of pagure.lib.query. """
        mock_redis.return_value = True

        tests.create_projects(self.session)
        project = pagure.lib.query._get_project(self.session, 'test')
        self.assertIsNotNone(project)

        # Set a custom key
        msg = pagure.lib.query.set_custom_key_fields(
            session=self.session,
            project=project,
            fields=['tested'],
            types=['text'],
            data=[None],
            notify=False
        )
        self.session.commit()
        self.assertEqual(msg, 'List of custom fields updated')

        # Create issues
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=project,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        issue = pagure.lib.query.search_issues(self.session, project, issueid=1)

        self.assertEqual(len(project.issue_keys), 1)
        self.assertEqual(project.issue_keys[0].key_type, 'text')
        msg = pagure.lib.query.set_custom_key_value(
            session=self.session,
            issue=issue,
            key=project.issue_keys[0],
            value='In progress'
        )
        self.session.commit()
        self.assertEqual(msg, 'Custom field tested adjusted to In progress')

        # Update it a second time to trigger edit
        msg = pagure.lib.query.set_custom_key_value(
            session=self.session,
            issue=issue,
            key=project.issue_keys[0],
            value='Done'
        )
        self.assertEqual(
            msg, 'Custom field tested adjusted to Done (was: In progress)')

        self.assertEqual(mock_redis.publish.call_count, 2)

    def test_log_action_invalid(self):
        """ Test the log_action function of pagure.lib.query. """
        obj = MagicMock
        obj.isa = "invalid"
        self.assertRaises(
            pagure.exceptions.InvalidObjectException,
            pagure.lib.query.log_action,
            session=self.session,
            action="foo",
            obj=obj,
            user_obj=None,
        )

    def test_search_token_no_acls(self):
        """ Test the search_token function of pagure.lib.query. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        out = pagure.lib.query.search_token(
            self.session,
            []
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].id, 'aaabbbcccddd')

    def test_search_token_single_acls(self):
        """ Test the search_token function of pagure.lib.query. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        out = pagure.lib.query.search_token(
            self.session,
            'issue_create',
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].id, 'aaabbbcccddd')

    def test_search_token_single_acls_user(self):
        """ Test the search_token function of pagure.lib.query. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        out = pagure.lib.query.search_token(
            self.session,
            'issue_create',
            user='pingou',
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].id, 'aaabbbcccddd')

        out = pagure.lib.query.search_token(
            self.session,
            'issue_create',
            user='foo',
        )
        self.assertEqual(len(out), 0)

    def test_search_token_single_acls_active(self):
        """ Test the search_token function of pagure.lib.query. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        out = pagure.lib.query.search_token(
            self.session,
            'issue_create',
            active=True
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].id, 'aaabbbcccddd')

        out = pagure.lib.query.search_token(
            self.session,
            'issue_create',
            expired=True
        )
        self.assertEqual(len(out), 0)

    def test_update_read_only_mode(self):
        """ Test the update_read_only_mode method of pagure.lib """

        tests.create_projects(self.session)

        project_obj = pagure.lib.query._get_project(self.session, 'test')
        # Default mode of project is read only
        self.assertEqual(project_obj.read_only, True)

        # Remove read only
        pagure.lib.query.update_read_only_mode(self.session, project_obj, False)
        self.session.commit()

        project_obj = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(project_obj.read_only, False)

        # Try reversing it back
        pagure.lib.query.update_read_only_mode(self.session, project_obj, True)
        self.session.commit()

        project_obj = pagure.lib.query._get_project(self.session, 'test')
        self.assertEqual(project_obj.read_only, True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
