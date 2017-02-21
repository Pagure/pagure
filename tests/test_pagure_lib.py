# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import pagure.lib.model
import tests


class PagureLibtests(tests.Modeltests):
    """ Tests for pagure.lib """

    def test_get_next_id(self):
        """ Test the get_next_id function of pagure.lib. """
        tests.create_projects(self.session)
        self.assertEqual(1, pagure.lib.get_next_id(self.session, 1))

    def test_search_user_all(self):
        """ Test the search_user of pagure.lib. """

        # Retrieve all users
        items = pagure.lib.search_user(self.session)
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
        """ Test the search_user of pagure.lib. """

        # Retrieve user by username
        item = pagure.lib.search_user(self.session, username='foo')
        self.assertEqual('foo', item.user)
        self.assertEqual('foo', item.username)
        self.assertEqual([], item.groups)

        item = pagure.lib.search_user(self.session, username='bar')
        self.assertEqual(None, item)

    def test_search_user_email(self):
        """ Test the search_user of pagure.lib. """

        # Retrieve user by email
        item = pagure.lib.search_user(self.session, email='foo@foo.com')
        self.assertEqual(None, item)

        item = pagure.lib.search_user(self.session, email='foo@bar.com')
        self.assertEqual('foo', item.user)
        self.assertEqual('foo', item.username)
        self.assertEqual([], item.groups)
        self.assertEqual(
            ['foo@bar.com'], [email.email for email in item.emails])

        item = pagure.lib.search_user(self.session, email='foo@pingou.com')
        self.assertEqual('pingou', item.user)
        self.assertEqual(
            sorted(['bar@pingou.com', 'foo@pingou.com']),
            sorted([email.email for email in item.emails]))

    def test_search_user_token(self):
        """ Test the search_user of pagure.lib. """

        # Retrieve user by token
        item = pagure.lib.search_user(self.session, token='aaa')
        self.assertEqual(None, item)

        item = pagure.lib.model.User(
            user='pingou2',
            fullname='PY C',
            token='aaabbb',
            default_email='bar@pingou.com',
        )
        self.session.add(item)
        self.session.commit()

        item = pagure.lib.search_user(self.session, token='aaabbb')
        self.assertEqual('pingou2', item.user)
        self.assertEqual('PY C', item.fullname)

    def test_search_user_pattern(self):
        """ Test the search_user of pagure.lib. """

        # Retrieve user by pattern
        item = pagure.lib.search_user(self.session, pattern='a*')
        self.assertEqual([], item)

        item = pagure.lib.model.User(
            user='pingou2',
            fullname='PY C',
            token='aaabbb',
            default_email='bar@pingou.com',
        )
        self.session.add(item)
        self.session.commit()

        items = pagure.lib.search_user(self.session, pattern='p*')
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

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_new_issue(self, p_send_email, p_ugt):
        """ Test the new_issue of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        repo = pagure.lib._get_project(self.session, 'test')

        # Before
        issues = pagure.lib.search_issues(self.session, repo)
        self.assertEqual(len(issues), 0)
        self.assertEqual(repo.open_tickets, 0)
        self.assertEqual(repo.open_tickets_public, 0)

        # See where it fails
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.new_issue,
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='blah',
            ticketfolder=None
        )

        # Add an extra user to project `foo`
        repo = pagure.lib._get_project(self.session, 'test')
        msg = pagure.lib.add_user_to_project(
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
            pagure.lib.add_user_to_project,
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou'
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # Create issues to play with
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
        self.assertEqual(repo.open_tickets, 1)
        self.assertEqual(repo.open_tickets_public, 1)

        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')
        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

        # After
        issues = pagure.lib.search_issues(self.session, repo)
        self.assertEqual(len(issues), 2)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_edit_issue(self, p_send_email, p_ugt):
        """ Test the edit_issue of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()

        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=2)

        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

        # Edit the issue
        msg = pagure.lib.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, None)

        msg = pagure.lib.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            ticketfolder=None,
            title='Test issue #2',
            content='We should work on this for the second time',
            status='Open',
        )
        self.session.commit()
        self.assertEqual(msg, None)

        msg = pagure.lib.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            ticketfolder=None,
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

        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(repo.open_tickets, 1)
        self.assertEqual(repo.open_tickets_public, 1)
        self.assertEqual(repo.issues[1].status, 'Closed')
        self.assertEqual(repo.issues[1].close_status, 'Invalid')

        # Edit the status: re-open the ticket
        msg = pagure.lib.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            status='Open',
            ticketfolder=None,
            private=True,
        )
        self.session.commit()
        self.assertEqual(
            msg, ['Issue status updated to: Open (was: Closed)'])

        repo = pagure.lib._get_project(self.session, 'test')
        for issue in repo.issues:
            self.assertEqual(issue.status, 'Open')
            self.assertEqual(issue.close_status, None)
        # 2 open but one of them is private
        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 1)

        # Edit the status: re-close the ticket
        msg = pagure.lib.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            status='Closed',
            close_status='Invalid',
            ticketfolder=None,
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

        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(repo.open_tickets, 1)
        self.assertEqual(repo.open_tickets_public, 1)
        self.assertEqual(repo.issues[1].status, 'Closed')
        self.assertEqual(repo.issues[1].close_status, 'Invalid')

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_edit_issue_priority(self, p_send_email, p_ugt):
        """ Test the edit_issue of pagure.lib when changing the priority.
        """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()

        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=2)

        # Set some priorities to the repo
        repo = pagure.lib.get_project(self.session, 'test')
        repo.priorities = {'1': 'High', '2': 'Normal'}
        self.session.add(repo)
        self.session.commit()

        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

        # Edit the issue -- Wrong priority value: No changes
        msg = pagure.lib.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            ticketfolder=None,
            priority=3,
        )
        self.session.commit()
        self.assertEqual(msg, None)

        # Edit the issue -- Good priority
        msg = pagure.lib.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            ticketfolder=None,
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
        msg = pagure.lib.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            ticketfolder=None,
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
        repo = pagure.lib.get_project(self.session, 'test')

        # Create 3 issues
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
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
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')

        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #3',
            content='We should work on this for the second time',
            user='foo',
            status='Open',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #3')

        issue = pagure.lib.search_issues(self.session, repo, issueid=2)

        self.assertEqual(repo.open_tickets, 3)
        self.assertEqual(repo.open_tickets_public, 3)

        # Make issue #2 blocking on issue #1
        msgs = pagure.lib.update_blocked_issue(
            self.session,
            repo,
            issue,
            blocks=['1'],
            username='pingou',
            ticketfolder=None,
        )
        self.assertEqual(msgs, ['Issue marked as blocking: #1'])

        # Make issue #2 depend on issue #3
        msgs = pagure.lib.update_dependency_issue(
            self.session,
            repo,
            issue,
            depends=['3'],
            username='pingou',
            ticketfolder=None,
        )
        self.assertEqual(msgs, ['Issue marked as depending on: #3'])

        # Edit the issue #3
        issue = pagure.lib.search_issues(self.session, repo, issueid=3)
        msg = pagure.lib.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, None)

        msg = pagure.lib.edit_issue(
            session=self.session,
            issue=issue,
            user='pingou',
            ticketfolder=None,
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

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_add_issue_dependency(self, p_send_email, p_ugt):
        """ Test the add_issue_dependency of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()
        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        issue_blocked = pagure.lib.search_issues(
            self.session, repo, issueid=2)

        # Before
        self.assertEqual(issue.parents, [])
        self.assertEqual(issue.children, [])
        self.assertEqual(issue_blocked.parents, [])
        self.assertEqual(issue_blocked.children, [])

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_issue_dependency,
            session=self.session,
            issue=issue,
            issue_blocked=issue,
            user='pingou',
            ticketfolder=None)

        msg = pagure.lib.add_issue_dependency(
            session=self.session,
            issue=issue,
            issue_blocked=issue_blocked,
            user='pingou',
            ticketfolder=None)
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

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_add_tag_obj(self, p_send_email, p_ugt):
        """ Test the add_tag_obj of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_edit_issue()
        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)

        # Add a tag to the issue
        msg = pagure.lib.add_tag_obj(
            session=self.session,
            obj=issue,
            tags='tag1',
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Issue tagged with: tag1')

        # Try a second time
        msg = pagure.lib.add_tag_obj(
            session=self.session,
            obj=issue,
            tags='tag1',
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Nothing to add')

        issues = pagure.lib.search_issues(self.session, repo, tags='tag1')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 1)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual([tag.tag for tag in issues[0].tags], ['tag1'])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_remove_tags(self, p_send_email, p_ugt):
        """ Test the remove_tags of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_add_tag_obj()
        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.remove_tags,
            session=self.session,
            project=repo,
            tags='foo',
            user='pingou',
            ticketfolder=None)

        msgs = pagure.lib.remove_tags(
            session=self.session,
            project=repo,
            tags='tag1',
            user='pingou',
            ticketfolder=None)

        self.assertEqual(msgs, ['Issue **un**tagged with: tag1'])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_remove_tags_obj(self, p_send_email, p_ugt):
        """ Test the remove_tags_obj of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_add_tag_obj()
        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)

        msgs = pagure.lib.remove_tags_obj(
            session=self.session,
            obj=issue,
            tags='tag1',
            user='pingou',
            ticketfolder=None)
        self.assertEqual(msgs, 'Issue **un**tagged with: tag1')

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_remove_tags_obj_from_project(self, p_send_email, p_ugt):
        """ Test the remove_tags_obj of pagure.lib from a project. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)

        # Add a tag to the project
        repo = pagure.get_authorized_project(self.session, 'test')
        msg = pagure.lib.add_tag_obj(
            self.session, repo,
            tags=['pagure', 'test'],
            user='pingou',
            ticketfolder=None)
        self.assertEqual(msg, 'Issue tagged with: pagure, test')
        self.session.commit()

        # Check the tags
        repo = pagure.get_authorized_project(self.session, 'test')
        self.assertEqual(repo.tags_text, ['pagure', 'test'])

        # Remove one of the the tag
        msgs = pagure.lib.remove_tags_obj(
            session=self.session,
            obj=repo,
            tags='test',
            user='pingou',
            ticketfolder=None)
        self.assertEqual(msgs, 'Issue **un**tagged with: test')
        self.session.commit()

        # Check the tags
        repo = pagure.get_authorized_project(self.session, 'test')
        self.assertEqual(repo.tags_text, ['pagure'])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_edit_issue_tags(self, p_send_email, p_ugt):
        """ Test the edit_issue_tags of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_add_tag_obj()
        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.edit_issue_tags,
            session=self.session,
            project=repo,
            old_tag='foo',
            new_tag='bar',
            new_tag_description='lorem ipsum',
            new_tag_color='black',
            user='pingou',
            ticketfolder=None,
        )

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.edit_issue_tags,
            session=self.session,
            project=repo,
            old_tag=None,
            new_tag='bar',
            new_tag_description='lorem ipsum',
            new_tag_color='black',
            user='pingou',
            ticketfolder=None,
        )

        msgs = pagure.lib.edit_issue_tags(
            session=self.session,
            project=repo,
            old_tag='tag1',
            new_tag='tag2',
            new_tag_description='lorem ipsum',
            new_tag_color='black',
            user='pingou',
            ticketfolder=None,
        )
        self.session.commit()
        self.assertEqual(
            msgs,
            ['Edited tag: tag1()[DeepSkyBlue] to tag2(lorem ipsum)[black]']
        )

        # Add a new tag
        msg = pagure.lib.add_tag_obj(
            session=self.session,
            obj=issue,
            tags='tag3',
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Issue tagged with: tag3')
        self.assertEqual([tag.tag for tag in issue.tags], ['tag2', 'tag3'])

        # Attempt to rename an existing tag into another existing one
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.edit_issue_tags,
            session=self.session,
            project=repo,
            old_tag='tag2',
            new_tag='tag3',
            new_tag_description='lorem ipsum',
            new_tag_color='red',
            user='pingou',
            ticketfolder=None,
        )

        # Rename an existing tag
        msgs = pagure.lib.edit_issue_tags(
            session=self.session,
            project=repo,
            old_tag='tag2',
            new_tag='tag4',
            new_tag_description='ipsum lorem',
            new_tag_color='purple',
            user='pingou',
            ticketfolder=None,
        )
        self.session.commit()
        self.assertEqual(msgs, ['Edited tag: tag2(lorem ipsum)[black] to tag4(ipsum lorem)[purple]'])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_search_issues(self, p_send_email, p_ugt):
        """ Test the search_issues of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_edit_issue()
        repo = pagure.lib._get_project(self.session, 'test')

        # All issues
        issues = pagure.lib.search_issues(self.session, repo)
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
        issues = pagure.lib.search_issues(
            self.session, repo, status='Closed')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Closed')
        self.assertEqual(issues[0].close_status, 'Invalid')
        self.assertEqual(issues[0].tags, [])

        # Issues closed
        issues = pagure.lib.search_issues(
            self.session, repo, closed=True)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Closed')
        self.assertEqual(issues[0].close_status, 'Invalid')
        self.assertEqual(issues[0].tags, [])

        # Issues by tag
        issues = pagure.lib.search_issues(self.session, repo, tags='foo')
        self.assertEqual(len(issues), 0)
        issues = pagure.lib.search_issues(self.session, repo, tags='!foo')
        self.assertEqual(len(issues), 2)

        # Issue by id
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.title, 'Test issue')
        self.assertEqual(issue.user.user, 'pingou')
        self.assertEqual(issue.tags, [])

        # Issues by authors
        issues = pagure.lib.search_issues(self.session, repo, author='foo')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Closed')
        self.assertEqual(issues[0].close_status, 'Invalid')
        self.assertEqual(issues[0].tags, [])

        # Issues by assignee
        issues = pagure.lib.search_issues(self.session, repo, assignee='foo')
        self.assertEqual(len(issues), 0)
        issues = pagure.lib.search_issues(self.session, repo, assignee='!foo')
        self.assertEqual(len(issues), 2)

        issues = pagure.lib.search_issues(self.session, repo, private='foo')
        self.assertEqual(len(issues), 2)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_add_issue_assignee(self, p_send_email, p_ugt):
        """ Test the add_issue_assignee of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()
        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=2)

        # Before
        issues = pagure.lib.search_issues(
            self.session, repo, assignee='pingou')
        self.assertEqual(len(issues), 0)

        # Test when it fails
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_issue_assignee,
            session=self.session,
            issue=issue,
            assignee='foo@foobar.com',
            user='foo@pingou.com',
            ticketfolder=None,
        )

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_issue_assignee,
            session=self.session,
            issue=issue,
            assignee='foo@bar.com',
            user='foo@foopingou.com',
            ticketfolder=None,
        )

        # Set the assignee by its email
        msg = pagure.lib.add_issue_assignee(
            session=self.session,
            issue=issue,
            assignee='foo@bar.com',
            user='foo@pingou.com',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Issue assigned to foo@bar.com')

        # Change the assignee to someone else by its username
        msg = pagure.lib.add_issue_assignee(
            session=self.session,
            issue=issue,
            assignee='pingou',
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Issue assigned to pingou (was: foo)')

        # After  -- Searches by assignee
        issues = pagure.lib.search_issues(
            self.session, repo, assignee='pingou')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual(issues[0].tags, [])

        issues = pagure.lib.search_issues(
            self.session, repo, assignee=True)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].title, 'Test issue #2')
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual(issues[0].tags, [])

        issues = pagure.lib.search_issues(
            self.session, repo, assignee=False)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 1)
        self.assertEqual(issues[0].title, 'Test issue')
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual(issues[0].tags, [])

        # Reset the assignee to no-one
        msg = pagure.lib.add_issue_assignee(
            session=self.session,
            issue=issue,
            assignee=None,
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Assignee reset')

        issues = pagure.lib.search_issues(
            self.session, repo, assignee=False)
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[1].id, 1)

        issues = pagure.lib.search_issues(
            self.session, repo, assignee=True)
        self.assertEqual(len(issues), 0)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_add_issue_comment(self, p_send_email, p_ugt):
        """ Test the add_issue_comment of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()
        repo = pagure.lib._get_project(self.session, 'test')

        # Before
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        # Set the assignee by its email
        msg = pagure.lib.add_issue_assignee(
            session=self.session,
            issue=issue,
            assignee='foo@bar.com',
            user='foo@pingou.com',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Issue assigned to foo@bar.com')

        # Add a comment to that issue
        msg = pagure.lib.add_issue_comment(
            session=self.session,
            issue=issue,
            comment='Hey look a comment!',
            user='foo',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        # After
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.comments[0].comment, 'Hey look a comment!')
        self.assertEqual(issue.comments[0].user.user, 'foo')

    @patch('pagure.lib.notify.send_email')
    def test_add_user_to_project(self, p_send_email):
        """ Test the add_user_to_project of pagure.lib. """
        p_send_email.return_value = True

        tests.create_projects(self.session)

        # Before
        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(len(repo.users), 0)

        # Add an user to a project
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_user_to_project,
            session=self.session,
            project=repo,
            new_user='foobar',
            user='pingou',
        )

        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # After
        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(len(repo.users), 1)
        self.assertEqual(repo.users[0].user, 'foo')
        self.assertEqual(repo.admins[0].user, 'foo')

        # Try adding the same user with the same access
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_user_to_project,
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='admin'
        )

        # Update the access of the user
        msg = pagure.lib.add_user_to_project(
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
        """ Test the new_project of pagure.lib. """
        gitfolder = os.path.join(self.path, 'repos')
        docfolder = os.path.join(self.path, 'docs')
        ticketfolder = os.path.join(self.path, 'tickets')
        requestfolder = os.path.join(self.path, 'requests')

        # Try creating a blacklisted project
        self.assertRaises(
            pagure.exceptions.ProjectBlackListedException,
            pagure.lib.new_project,
            session=self.session,
            user='pingou',
            name='static',
            blacklist=['static'],
            allowed_prefix=[],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for static',
            parent_id=None,
        )

        # Try creating a 40 chars project
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.new_project,
            session=self.session,
            user='pingou',
            name='s' * 40,
            namespace='pingou',
            blacklist=['static'],
            allowed_prefix=['pingou'],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for 40 chars length project',
            parent_id=None,
            prevent_40_chars=True,
        )

        # Create a new project
        pagure.APP.config['GIT_FOLDER'] = gitfolder
        msg = pagure.lib.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            blacklist=[],
            allowed_prefix=[],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for testproject',
            parent_id=None,
        )
        self.session.commit()
        self.assertEqual(msg, 'Project "testproject" created')

        # Try creating an existing project using a different case
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.new_project,
            session=self.session,
            user='pingou',
            name='TestProject',
            blacklist=[],
            allowed_prefix=[],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for testproject',
            parent_id=None,
        )

        repo = pagure.get_authorized_project(self.session, 'testproject')
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
            pagure.lib.new_project,
            session=self.session,
            user='pingou',
            name='testproject',
            blacklist=[],
            allowed_prefix=[],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for testproject',
            parent_id=None
        )
        self.session.rollback()

        self.assertTrue(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Try re-creating it ignoring the existing repos - but repo in the DB
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.new_project,
            session=self.session,
            user='pingou',
            name='testproject',
            blacklist=[],
            allowed_prefix=[],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for testproject',
            parent_id=None
        )
        self.session.rollback()

        # Re-create it, ignoring the existing repos on disk
        repo = pagure.lib._get_project(self.session, 'testproject')
        self.session.delete(repo)
        self.session.commit()

        msg = pagure.lib.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            blacklist=[],
            allowed_prefix=[],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for testproject',
            parent_id=None,
            ignore_existing_repo=True
        )
        self.session.commit()
        self.assertEqual(msg, 'Project "testproject" created')

        self.assertTrue(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Drop the main git repo and try again
        shutil.rmtree(gitrepo)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.new_project,
            session=self.session,
            user='pingou',
            name='testproject',
            blacklist=[],
            allowed_prefix=[],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for testproject',
            parent_id=None
        )
        self.session.rollback()

        self.assertFalse(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Drop the doc repo and try again
        shutil.rmtree(docrepo)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.new_project,
            session=self.session,
            user='pingou',
            name='testproject',
            blacklist=[],
            allowed_prefix=[],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for testproject',
            parent_id=None
        )
        self.session.rollback()
        self.assertFalse(os.path.exists(gitrepo))
        self.assertFalse(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Drop the request repo and try again
        shutil.rmtree(ticketrepo)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.new_project,
            session=self.session,
            user='pingou',
            name='testproject',
            blacklist=[],
            allowed_prefix=[],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for testproject',
            parent_id=None
        )
        self.session.rollback()
        self.assertFalse(os.path.exists(gitrepo))
        self.assertFalse(os.path.exists(docrepo))
        self.assertFalse(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Re-Try creating a 40 chars project this time allowing it
        msg = pagure.lib.new_project(
            session=self.session,
            user='pingou',
            name='pingou/' + 's' * 40,
            blacklist=['static'],
            allowed_prefix=['pingou'],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for 40 chars length project',
            parent_id=None,
        )
        self.session.commit()
        self.assertEqual(
            msg,
            'Project "pingou/ssssssssssssssssssssssssssssssssssssssss" '
            'created')

    def test_new_project_user_ns(self):
        """ Test the new_project of pagure.lib with user_ns on. """
        gitfolder = os.path.join(self.path, 'repos')
        docfolder = os.path.join(self.path, 'docs')
        ticketfolder = os.path.join(self.path, 'tickets')
        requestfolder = os.path.join(self.path, 'requests')

        # Create a new project with user_ns as True
        pagure.APP.config['GIT_FOLDER'] = gitfolder
        msg = pagure.lib.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            blacklist=[],
            allowed_prefix=[],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for testproject',
            parent_id=None,
            user_ns=True,
        )
        self.session.commit()
        self.assertEqual(msg, 'Project "pingou/testproject" created')

        repo = pagure.lib._get_project(
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
        pagure.APP.config['GIT_FOLDER'] = gitfolder
        msg = pagure.lib.new_project(
            session=self.session,
            user='pingou',
            name='testproject2',
            namespace='testns',
            blacklist=[],
            allowed_prefix=['testns'],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for testproject2',
            parent_id=None,
            user_ns=True,
        )
        self.session.commit()
        self.assertEqual(msg, 'Project "testns/testproject2" created')

        repo = pagure.lib._get_project(
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
        """ Test the update_project_settings of pagure.lib. """

        tests.create_projects(self.session)

        # Before
        repo = pagure.lib._get_project(self.session, 'test2')
        self.assertTrue(repo.settings['issue_tracker'])
        self.assertFalse(repo.settings['project_documentation'])

        msg = pagure.lib.update_project_settings(
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
                'pull_request_access_only': False,
            },
            user='pingou',
        )
        self.assertEqual(msg, 'No settings to change')
        mock_log.assert_not_called()

        msg = pagure.lib.update_project_settings(
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
            args[1]['msg']['fields'],
            [
                'Web-hooks', 'project_documentation',
                'issue_tracker', 'pull_requests'
            ]
        )
        self.assertEqual(args[1]['topic'], 'project.edit')

        # After
        repo = pagure.lib._get_project(self.session, 'test2')
        self.assertFalse(repo.settings['issue_tracker'])
        self.assertTrue(repo.settings['project_documentation'])
        self.assertFalse(repo.settings['pull_requests'])

    def test_search_projects(self):
        """ Test the search_projects of pagure.lib. """
        tests.create_projects(self.session)

        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 3)
        self.assertEqual(projects[0].id, 1)
        self.assertEqual(projects[1].id, 2)

        projects = pagure.lib.search_projects(self.session, username='foo')
        self.assertEqual(len(projects), 0)

        projects = pagure.lib.search_projects(self.session, username='pingou')
        self.assertEqual(len(projects), 3)
        self.assertEqual(projects[0].id, 1)
        self.assertEqual(projects[1].id, 2)

        projects = pagure.lib.search_projects(self.session, start=1)
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0].id, 2)

        projects = pagure.lib.search_projects(self.session, limit=1)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].id, 1)

        projects = pagure.lib.search_projects(self.session, count=True)
        self.assertEqual(projects, 3)

        # Also check if the project shows up if a user doesn't
        # have admin access in the project
        # Check with commit access first
        project = pagure.lib.get_project(self.session, name='test')
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='commit'
        )

        self.assertEqual(msg, 'User added')
        self.session.commit()
        projects = pagure.lib.search_projects(self.session, username='foo')
        self.assertEqual(len(projects), 1)

        # Now check with only ticket access
        project = pagure.lib.get_project(self.session, name='test')
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='ticket'
        )
        self.assertEqual(msg, 'User access updated')
        self.session.commit()
        projects = pagure.lib.search_projects(self.session, username='foo')
        self.assertEqual(len(projects), 0)

    def test_search_project_forked(self):
        """ Test the search_project for forked projects in pagure.lib. """
        tests.create_projects(self.session)

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
        projects = pagure.lib.search_projects(self.session, fork=True)
        self.assertEqual(len(projects), 2)
        projects = pagure.lib.search_projects(self.session, fork=False)
        self.assertEqual(len(projects), 3)

    def test_get_tags_of_project(self):
        """ Test the get_tags_of_project of pagure.lib. """

        self.test_add_tag_obj()
        repo = pagure.lib._get_project(self.session, 'test')

        tags = pagure.lib.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ['tag1'])

        tags = pagure.lib.get_tags_of_project(
            self.session, repo, pattern='T*')
        self.assertEqual([tag.tag for tag in tags], ['tag1'])

        repo = pagure.lib._get_project(self.session, 'test2')

        tags = pagure.lib.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], [])

    def test_get_issue_statuses(self):
        """ Test the get_issue_statuses of pagure.lib. """
        statuses = pagure.lib.get_issue_statuses(self.session)
        self.assertEqual(sorted(statuses), ['Closed', 'Open'])

    def test_set_up_user(self):
        """ Test the set_up_user of pagure.lib. """

        items = pagure.lib.search_user(self.session)
        self.assertEqual(2, len(items))
        self.assertEqual(2, items[0].id)
        self.assertEqual('foo', items[0].user)
        self.assertEqual(1, items[1].id)
        self.assertEqual('pingou', items[1].user)

        pagure.lib.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth',
            default_email='skvidal@fp.o',
            keydir=pagure.APP.config.get('GITOLITE_KEYDIR', None),
        )
        self.session.commit()

        items = pagure.lib.search_user(self.session)
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
        pagure.lib.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth V',
            default_email='skvidal@fp.o',
            keydir=pagure.APP.config.get('GITOLITE_KEYDIR', None),
        )
        self.session.commit()
        # Nothing changed
        items = pagure.lib.search_user(self.session)
        self.assertEqual(3, len(items))
        self.assertEqual('skvidal', items[2].user)
        self.assertEqual('Seth V', items[2].fullname)
        self.assertEqual(
            ['skvidal@fp.o'], [email.email for email in items[2].emails])

        # Add the user a third time with a different email
        pagure.lib.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth',
            default_email='svidal@fp.o',
            keydir=pagure.APP.config.get('GITOLITE_KEYDIR', None),
        )
        self.session.commit()
        # Email added
        items = pagure.lib.search_user(self.session)
        self.assertEqual(3, len(items))
        self.assertEqual('skvidal', items[2].user)
        self.assertEqual(
            sorted(['skvidal@fp.o', 'svidal@fp.o']),
            sorted([email.email for email in items[2].emails]))

    def test_update_user_ssh(self):
        """ Test the update_user_ssh of pagure.lib. """

        # Before
        user = pagure.lib.search_user(self.session, username='foo')
        self.assertEqual(user.public_ssh_key, None)

        msg = pagure.lib.update_user_ssh(self.session, user, 'blah', keydir=None)
        user = pagure.lib.search_user(self.session, username='foo')
        self.assertEqual(user.public_ssh_key, 'blah')

        msg = pagure.lib.update_user_ssh(self.session, user, 'blah', keydir=None)
        user = pagure.lib.search_user(self.session, username='foo')
        self.assertEqual(user.public_ssh_key, 'blah')

        msg = pagure.lib.update_user_ssh(self.session, 'foo', None, keydir=None)
        user = pagure.lib.search_user(self.session, username='foo')
        self.assertEqual(user.public_ssh_key, None)

    def avatar_url_from_email(self):
        """ Test the avatar_url_from_openid of pagure.lib. """
        output = pagure.lib.avatar_url_from_email('pingou@fedoraproject.org')
        self.assertEqual(
            output,
            'https://seccdn.libravatar.org/avatar/'
            'b3ee7bb4de70b6522c2478df3b4cd6322b5ec5d62ac7ceb1128e3d4ff42f6928'
            '?s=64&d=retro')

        output = pagure.lib.avatar_url_from_email(u'zoé@çëfò.org')
        self.assertEqual(
            output,
            'https://seccdn.libravatar.org/avatar/'
            '8fa6110d1f6a7a013969f012e1149ff89bf1252d4f15d25edee31d4662878656'
            '?s=64&d=retro')

    def test_fork_project(self):
        """ Test the fork_project of pagure.lib. """
        gitfolder = os.path.join(self.path, 'repos')
        docfolder = os.path.join(self.path, 'docs')
        ticketfolder = os.path.join(self.path, 'tickets')
        requestfolder = os.path.join(self.path, 'requests')
        pagure.APP.config['GIT_FOLDER'] = gitfolder

        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        # Create a new project
        msg = pagure.lib.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            blacklist=[],
            allowed_prefix=[],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for testproject',
            parent_id=None,
        )
        self.session.commit()
        self.assertEqual(msg, 'Project "testproject" created')

        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        repo = pagure.lib._get_project(self.session, 'testproject')
        gitrepo = os.path.join(gitfolder, repo.path)
        docrepo = os.path.join(docfolder, repo.path)
        ticketrepo = os.path.join(ticketfolder, repo.path)
        requestrepo = os.path.join(requestfolder, repo.path)

        self.assertTrue(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Git repo exists
        grepo = '%s.git' % os.path.join(
            gitfolder, 'forks', 'foo', 'testproject')
        os.makedirs(grepo)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.fork_project,
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )
        self.session.rollback()
        shutil.rmtree(grepo)

        # Doc repo exists
        grepo = '%s.git' % os.path.join(
            docfolder, 'forks', 'foo', 'testproject')
        os.makedirs(grepo)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.fork_project,
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )
        self.session.rollback()
        shutil.rmtree(grepo)

        # Ticket repo exists
        grepo = '%s.git' % os.path.join(
            ticketfolder, 'forks', 'foo', 'testproject')
        os.makedirs(grepo)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.fork_project,
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )
        self.session.rollback()
        shutil.rmtree(grepo)

        # Request repo exists
        grepo = '%s.git' % os.path.join(
            requestfolder, 'forks', 'foo', 'testproject')
        os.makedirs(grepo)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.fork_project,
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )
        self.session.rollback()
        shutil.rmtree(grepo)

        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        # Fork worked

        msg = pagure.lib.fork_project(
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )
        self.session.commit()
        self.assertEqual(
            msg, 'Repo "testproject" cloned to "foo/testproject"')

        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 2)

        # Fork a fork

        repo = pagure.lib._get_project(
            self.session, 'testproject', user='foo')

        msg = pagure.lib.fork_project(
            session=self.session,
            user='pingou',
            repo=repo,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )
        self.session.commit()
        self.assertEqual(
            msg, 'Repo "testproject" cloned to "pingou/testproject"')

        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 3)

    def test_fork_project_namespaced(self):
        """ Test the fork_project of pagure.lib on a namespaced project. """
        gitfolder = os.path.join(self.path, 'repos')
        docfolder = os.path.join(self.path, 'docs')
        ticketfolder = os.path.join(self.path, 'tickets')
        requestfolder = os.path.join(self.path, 'requests')
        pagure.APP.config['GIT_FOLDER'] = gitfolder

        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        # Create a new project
        msg = pagure.lib.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            namespace='foonamespace',
            blacklist=[],
            allowed_prefix=['foonamespace'],
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
            description='description for testproject',
            parent_id=None,
        )
        self.session.commit()
        self.assertEqual(msg, 'Project "foonamespace/testproject" created')

        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        repo = pagure.lib._get_project(self.session, 'testproject', namespace='foonamespace')
        gitrepo = os.path.join(gitfolder, repo.path)
        docrepo = os.path.join(docfolder, repo.path)
        ticketrepo = os.path.join(ticketfolder, repo.path)
        requestrepo = os.path.join(requestfolder, repo.path)

        self.assertTrue(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))
        self.assertTrue(os.path.exists(requestrepo))

        # Git repo exists
        grepo = '%s.git' % os.path.join(
            gitfolder, 'forks', 'foo', 'foonamespace', 'testproject')
        os.makedirs(grepo)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.fork_project,
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )
        self.session.rollback()
        shutil.rmtree(grepo)

        # Doc repo exists
        grepo = '%s.git' % os.path.join(
            docfolder, 'forks', 'foo', 'foonamespace', 'testproject')
        os.makedirs(grepo)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.fork_project,
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )
        self.session.rollback()
        shutil.rmtree(grepo)

        # Ticket repo exists
        grepo = '%s.git' % os.path.join(
            ticketfolder, 'forks', 'foo', 'foonamespace', 'testproject')
        os.makedirs(grepo)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.fork_project,
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )
        self.session.rollback()
        shutil.rmtree(grepo)

        # Request repo exists
        grepo = '%s.git' % os.path.join(
            requestfolder, 'forks', 'foo', 'foonamespace', 'testproject')
        os.makedirs(grepo)
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.fork_project,
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )
        self.session.rollback()
        shutil.rmtree(grepo)

        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        # Fork worked

        msg = pagure.lib.fork_project(
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )
        self.session.commit()
        self.assertEqual(
            msg,
            'Repo "foonamespace/testproject" cloned to '
            '"foo/foonamespace/testproject"')

        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 2)

        # Fork a fork

        repo = pagure.lib._get_project(self.session, 'testproject', user='foo', namespace='foonamespace')

        msg = pagure.lib.fork_project(
            session=self.session,
            user='pingou',
            repo=repo,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )
        self.session.commit()
        self.assertEqual(
            msg,
            'Repo "foonamespace/testproject" cloned to '
            '"pingou/foonamespace/testproject"')

        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 3)

    @patch('pagure.lib.notify.send_email')
    def test_new_pull_request(self, mockemail):
        """ test new_pull_request of pagure.lib. """
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
        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(repo.open_requests, 0)

        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        repo = pagure.lib._get_project(self.session, 'test')
        forked_repo = pagure.lib._get_project(
            self.session, 'test', user='pingou')

        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')
        self.assertEqual(repo.open_requests, 1)

    @patch('pagure.lib.notify.send_email')
    def test_add_pull_request_comment(self, mockemail):
        """ Test add_pull_request_comment of pagure.lib. """
        mockemail.return_value = True

        self.test_new_pull_request()

        request = pagure.lib.search_pull_requests(self.session, requestid=1)

        msg = pagure.lib.add_pull_request_comment(
            session=self.session,
            request=request,
            commit='commithash',
            tree_id=None,
            filename='file',
            row=None,
            comment='This is awesome, I got to remember it!',
            user='foo',
            requestfolder=None,
        )
        self.assertEqual(msg, 'Comment added')
        self.session.commit()

        self.assertEqual(len(request.discussion), 0)
        self.assertEqual(len(request.comments), 1)
        self.assertEqual(request.score, 0)

    @patch('pagure.lib.notify.send_email')
    def test_add_pull_request_flag(self, mockemail):
        """ Test add_pull_request_flag of pagure.lib. """
        mockemail.return_value = True

        self.test_new_pull_request()
        tests.create_tokens(self.session)

        request = pagure.lib.search_pull_requests(self.session, requestid=1)
        self.assertEqual(len(request.flags), 0)

        msg = pagure.lib.add_pull_request_flag(
            session=self.session,
            request=request,
            username="jenkins",
            percent=100,
            comment="Build passes",
            url="http://jenkins.cloud.fedoraproject.org",
            uid="jenkins_build_pagure_34",
            user='foo',
            token='aaabbbcccddd',
            requestfolder=None,
        )
        self.assertEqual(msg, 'Flag added')
        self.session.commit()

        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].token_id, 'aaabbbcccddd')

    @patch('pagure.lib.notify.send_email')
    def test_add_pull_request_flag_no_token(self, mockemail):
        """ Test add_pull_request_flag of pagure.lib. """
        mockemail.return_value = True

        self.test_new_pull_request()
        tests.create_tokens(self.session)

        request = pagure.lib.search_pull_requests(self.session, requestid=1)
        self.assertEqual(len(request.flags), 0)

        self.assertRaises(
            ValueError,
            pagure.lib.add_pull_request_flag,
            session=self.session,
            request=request,
            username="jenkins",
            percent=100,
            comment="Build passes",
            url="http://jenkins.cloud.fedoraproject.org",
            uid="jenkins_build_pagure_34",
            user='foo',
            token=None,
            requestfolder=None,
        )

        request = pagure.lib.search_pull_requests(self.session, requestid=1)
        self.assertEqual(len(request.flags), 0)

    def test_search_pull_requests(self):
        """ Test search_pull_requests of pagure.lib. """

        self.test_new_pull_request()

        prs = pagure.lib.search_pull_requests(
            session=self.session
        )
        self.assertEqual(len(prs), 1)

        prs = pagure.lib.search_pull_requests(
            session=self.session,
            project_id=1
        )
        self.assertEqual(len(prs), 1)

        prs = pagure.lib.search_pull_requests(
            session=self.session,
            project_id_from=4
        )
        self.assertEqual(len(prs), 1)

        prs = pagure.lib.search_pull_requests(
            session=self.session,
            status=False
        )
        self.assertEqual(len(prs), 0)

        # All non-assigned PR
        prs = pagure.lib.search_pull_requests(
            session=self.session,
            assignee=False
        )
        self.assertEqual(len(prs), 1)

        prs[0].assignee_id = 1
        self.session.add(prs[0])
        self.session.commit()

        # All the PR assigned
        prs = pagure.lib.search_pull_requests(
            session=self.session,
            assignee=True
        )
        self.assertEqual(len(prs), 1)

        # Basically the same as above but then for a specific user
        prs = pagure.lib.search_pull_requests(
            session=self.session,
            assignee='pingou'
        )
        self.assertEqual(len(prs), 1)

        # All PR except those assigned to pingou
        prs = pagure.lib.search_pull_requests(
            session=self.session,
            assignee='!pingou'
        )
        self.assertEqual(len(prs), 0)

        # All PR created by the specified author
        prs = pagure.lib.search_pull_requests(
            session=self.session,
            author='pingou'
        )
        self.assertEqual(len(prs), 1)

        # Count the PR instead of listing them
        prs = pagure.lib.search_pull_requests(
            session=self.session,
            author='pingou',
            count=True
        )
        self.assertEqual(prs, 1)

    @patch('pagure.lib.notify.send_email')
    def test_close_pull_request(self, send_email):
        """ Test close_pull_request of pagure.lib. """
        send_email.return_value = True

        self.test_new_pull_request()

        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(repo.open_requests, 1)
        request = pagure.lib.search_pull_requests(self.session, requestid=1)

        pagure.lib.close_pull_request(
            session=self.session,
            request=request,
            user='pingou',
            requestfolder=None,
            merged=True,
        )
        self.session.commit()
        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(repo.open_requests, 0)

        prs = pagure.lib.search_pull_requests(
            session=self.session,
            status=False
        )
        self.assertEqual(len(prs), 1)

        # Does not change much, just the notification sent

        pagure.lib.close_pull_request(
            session=self.session,
            request=request,
            user='pingou',
            requestfolder=None,
            merged=False,
        )
        self.session.commit()

        prs = pagure.lib.search_pull_requests(
            session=self.session,
            status=False
        )
        self.assertEqual(len(prs), 1)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_remove_issue_dependency(self, p_send_email, p_ugt):
        """ Test remove_issue_dependency of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_add_issue_dependency()
        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        issue_blocked = pagure.lib.search_issues(
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
            pagure.lib.remove_issue_dependency,
            session=self.session,
            issue=issue,
            issue_blocked=issue,
            user='pingou',
            ticketfolder=None)

        # Wrong order of issues
        msg = pagure.lib.remove_issue_dependency(
            session=self.session,
            issue=issue,
            issue_blocked=issue_blocked,
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, None)

        # Drop deps
        msg = pagure.lib.remove_issue_dependency(
            session=self.session,
            issue=issue_blocked,
            issue_blocked=issue,
            user='pingou',
            ticketfolder=None)
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
        """ Test the get_issue_comment of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_add_issue_comment()

        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)

        self.assertEqual(
            pagure.lib.get_issue_comment(self.session, issue.uid, 10),
            None
        )

        comment = pagure.lib.get_issue_comment(self.session, issue.uid, 1)
        self.assertEqual(comment.comment, 'Hey look a comment!')

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_get_issue_by_uid(self, p_send_email, p_ugt):
        """ Test the get_issue_by_uid of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()

        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)

        self.assertEqual(
            pagure.lib.get_issue_by_uid(self.session, 'foobar'),
            None
        )

        new_issue = pagure.lib.get_issue_by_uid(self.session, issue.uid)
        self.assertEqual(issue, new_issue)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_update_tags(self, p_send_email, p_ugt):
        """ Test the update_tags of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()
        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)

        # before
        self.assertEqual(repo.tags_colored, [])
        self.assertEqual(issue.tags_text, [])

        messages = pagure.lib.update_tags(
            self.session, issue, 'tag', 'pingou', ticketfolder=None)
        self.assertEqual(messages, ['Issue tagged with: tag'])

        # after
        repo = pagure.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)

        self.assertEqual(
            [t.tag for t in repo.tags_colored], ['tag'])
        self.assertEqual(issue.tags_text, ['tag'])

        # Replace the tag by two others
        messages = pagure.lib.update_tags(
            self.session, issue, ['tag2', 'tag3'], 'pingou',
            ticketfolder=None)
        self.assertEqual(
            messages, [
                'Issue tagged with: tag2, tag3',
                'Issue **un**tagged with: tag'
            ]
        )

        # after
        repo = pagure.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)

        self.assertEqual(
            sorted([t.tag for t in repo.tags_colored]),
            ['tag', 'tag2', 'tag3'])
        self.assertEqual(issue.tags_text, ['tag2', 'tag3'])


    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_update_dependency_issue(self, p_send_email, p_ugt):
        """ Test the update_dependency_issue of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()
        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)

        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

        # Create issues to play with
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #3',
            content='We should work on this (3rd time!)',
            user='pingou',
            ticketfolder=None,
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

        messages = pagure.lib.update_dependency_issue(
            self.session, repo, issue, '2', 'pingou', ticketfolder=None)
        self.assertEqual(messages, ['Issue marked as depending on: #2'])
        messages = pagure.lib.update_dependency_issue(
            self.session, repo, issue, ['3', '4', 5], 'pingou',
            ticketfolder=None)
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
        """ Test the update_blocked_issue of pagure.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()
        repo = pagure.lib._get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)

        # Create issues to play with
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #3',
            content='We should work on this (3rd time!)',
            user='pingou',
            ticketfolder=None,
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #3')

        # before
        self.assertEqual(issue.tags_text, [])
        self.assertEqual(issue.depending_text, [])
        self.assertEqual(issue.blocking_text, [])

        messages = pagure.lib.update_blocked_issue(
            self.session, repo, issue, '2', 'pingou', ticketfolder=None)
        self.assertEqual(messages, ['Issue marked as blocking: #2'])
        messages = pagure.lib.update_blocked_issue(
            self.session, repo, issue, ['3', '4', 5], 'pingou',
            ticketfolder=None)
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
        """ Test add_pull_request_assignee of pagure.lib. """
        mockemail.return_value = True

        self.test_new_pull_request()

        request = pagure.lib.search_pull_requests(self.session, requestid=1)

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_pull_request_assignee,
            session=self.session,
            request=request,
            assignee='bar',
            user='foo',
            requestfolder=None,
        )

        # Assign
        msg = pagure.lib.add_pull_request_assignee(
            session=self.session,
            request=request,
            assignee='pingou',
            user='foo',
            requestfolder=None,
        )
        self.assertEqual(msg, 'Request assigned')

        # Reset
        msg = pagure.lib.add_pull_request_assignee(
            session=self.session,
            request=request,
            assignee=None,
            user='foo',
            requestfolder=None,
        )
        self.assertEqual(msg, 'Request reset')

        # Try resetting again
        msg = pagure.lib.add_pull_request_assignee(
            session=self.session,
            request=request,
            assignee=None,
            user='foo',
            requestfolder=None,
        )
        self.assertEqual(msg, None)

    def test_search_pending_email(self):
        """ Test search_pending_email of pagure.lib. """

        self.assertEqual(
            pagure.lib.search_pending_email(self.session), None)

        user = pagure.lib.search_user(self.session, username='pingou')

        email_pend = pagure.lib.model.UserEmailPending(
            user_id=user.id,
            email='foo@fp.o',
            token='abcdef',
        )
        self.session.add(email_pend)
        self.session.commit()

        self.assertNotEqual(
            pagure.lib.search_pending_email(self.session), None)
        self.assertNotEqual(
            pagure.lib.search_pending_email(self.session, token='abcdef'),
            None)

        pend = pagure.lib.search_pending_email(self.session, token='abcdef')
        self.assertEqual(pend.user.username, 'pingou')
        self.assertEqual(pend.email, 'foo@fp.o')
        self.assertEqual(pend.token, 'abcdef')

        pend = pagure.lib.search_pending_email(self.session, email='foo@fp.o')
        self.assertEqual(pend.user.username, 'pingou')
        self.assertEqual(pend.email, 'foo@fp.o')
        self.assertEqual(pend.token, 'abcdef')

    def test_generate_hook_token(self):
        """ Test generate_hook_token of pagure.lib. """

        tests.create_projects(self.session)

        projects = pagure.lib.search_projects(self.session)
        for proj in projects:
            self.assertIn(proj.hook_token, ['aaabbbccc', 'aaabbbddd', 'aaabbbeee'])

        pagure.lib.generate_hook_token(self.session)

        projects = pagure.lib.search_projects(self.session)
        for proj in projects:
            self.assertNotIn(proj.hook_token, ['aaabbbccc', 'aaabbbddd', 'aaabbbeee'])

    @patch('pagure.lib.notify.send_email')
    def test_pull_request_score(self, mockemail):
        """ Test PullRequest.score of pagure.lib.model. """
        mockemail.return_value = True

        self.test_new_pull_request()

        request = pagure.lib.search_pull_requests(self.session, requestid=1)

        msg = pagure.lib.add_pull_request_comment(
            session=self.session,
            request=request,
            commit=None,
            tree_id=None,
            filename=None,
            row=None,
            comment='This looks great :thumbsup:',
            user='foo',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        msg = pagure.lib.add_pull_request_comment(
            session=self.session,
            request=request,
            commit=None,
            tree_id=None,
            filename=None,
            row=None,
            comment='I disagree -1',
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        msg = pagure.lib.add_pull_request_comment(
            session=self.session,
            request=request,
            commit=None,
            tree_id=None,
            filename=None,
            row=None,
            comment='NM this looks great now +1000',
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        self.assertEqual(len(request.discussion), 3)
        self.assertEqual(request.score, 1)

    def test_add_group(self):
        """ Test the add_group method of pagure.lib. """
        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 0)
        self.assertEqual(groups, [])

        # Invalid type
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_group,
            self.session,
            group_name='foo',
            display_name='foo group',
            description=None,
            group_type='bar',
            user='pingou',
            is_admin=True,
            blacklist=[],
        )
        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 0)
        self.assertEqual(groups, [])

        # Invalid user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_group,
            self.session,
            group_name='foo',
            display_name='foo group',
            description=None,
            group_type='user',
            user='test',
            is_admin=False,
            blacklist=[],
        )
        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 0)
        self.assertEqual(groups, [])

        msg = pagure.lib.add_group(
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

        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_name, 'foo')

        # Group with this name already exists
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_group,
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
            pagure.lib.add_group,
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
            pagure.lib.add_group,
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
        """ Test the add_user_to_group method of pagure.lib. """
        self.test_add_group()
        group = pagure.lib.search_groups(self.session, group_name='foo')
        self.assertNotEqual(group, None)
        self.assertEqual(group.group_name, 'foo')

        # Invalid new user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_user_to_group,
            self.session,
            username='foobar',
            group=group,
            user='foo',
            is_admin=False,
        )

        # Invalid user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_user_to_group,
            self.session,
            username='foo',
            group=group,
            user='foobar',
            is_admin=False,
        )

        # User not allowed
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_user_to_group,
            self.session,
            username='foo',
            group=group,
            user='foo',
            is_admin=False,
        )

        msg = pagure.lib.add_user_to_group(
            self.session,
            username='foo',
            group=group,
            user='pingou',
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, 'User `foo` added to the group `foo`.')

        msg = pagure.lib.add_user_to_group(
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
        """ Test the is_group_member method of pagure.lib. """
        self.test_add_group()

        self.assertFalse(
            pagure.lib.is_group_member(self.session, None, 'foo'))

        self.assertFalse(
            pagure.lib.is_group_member(self.session, 'bar', 'foo'))

        self.assertFalse(
            pagure.lib.is_group_member(self.session, 'foo', 'foo'))

        self.assertTrue(
            pagure.lib.is_group_member(self.session, 'pingou', 'foo'))

    def test_get_user_group(self):
        """ Test the get_user_group method of pagure.lib. """

        self.test_add_group()

        item = pagure.lib.get_user_group(self.session, 1, 1)
        self.assertEqual(item.user_id, 1)
        self.assertEqual(item.group_id, 1)

        item = pagure.lib.get_user_group(self.session, 1, 2)
        self.assertEqual(item, None)

        item = pagure.lib.get_user_group(self.session, 2, 1)
        self.assertEqual(item, None)

    def test_get_group_types(self):
        """ Test the get_group_types method of pagure.lib. """

        self.test_add_group()

        groups = pagure.lib.get_group_types(self.session, 'user')
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_type, 'user')

        groups = pagure.lib.get_group_types(self.session)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].group_type, 'admin')
        self.assertEqual(groups[1].group_type, 'user')

    def test_search_groups(self):
        """ Test the search_groups method of pagure.lib. """

        self.assertEqual(pagure.lib.search_groups(self.session), [])

        msg = pagure.lib.add_group(
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

        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_name, 'foo')

        msg = pagure.lib.add_group(
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

        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].group_name, 'bar')
        self.assertEqual(groups[1].group_name, 'foo')

        groups = pagure.lib.search_groups(self.session, group_type='user')
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_name, 'foo')

        groups = pagure.lib.search_groups(self.session, group_type='admin')
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_name, 'bar')

        groups = pagure.lib.search_groups(self.session, group_name='foo')
        self.assertEqual(groups.group_name, 'foo')

    def test_delete_user_of_group(self):
        """ Test the delete_user_of_group method of pagure.lib. """
        self.test_add_user_to_group()

        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_name, 'foo')

        # Invalid username
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.delete_user_of_group,
            self.session,
            username='bar',
            groupname='foo',
            user='pingou',
            is_admin=False,
        )

        # Invalid groupname
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.delete_user_of_group,
            self.session,
            username='foo',
            groupname='bar',
            user='pingou',
            is_admin=False,
        )

        # Invalid user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.delete_user_of_group,
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
            pagure.lib.delete_user_of_group,
            self.session,
            username='bar',
            groupname='foo',
            user='pingou',
            is_admin=False,
        )

        # User is not allowed to remove the username
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.delete_user_of_group,
            self.session,
            username='foo',
            groupname='foo',
            user='bar',
            is_admin=False,
        )

        # Username is the creator of the group
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.delete_user_of_group,
            self.session,
            username='pingou',
            groupname='foo',
            user='pingou',
            is_admin=False,
        )

        # All good
        group = pagure.lib.search_groups(self.session, group_name='foo')
        self.assertEqual(len(group.users), 2)

        pagure.lib.delete_user_of_group(
            self.session,
            username='foo',
            groupname='foo',
            user='pingou',
            is_admin=False,
        )
        self.session.commit()

        group = pagure.lib.search_groups(self.session, group_name='foo')
        self.assertEqual(len(group.users), 1)

    def test_edit_group_info(self):
        """ Test the edit_group_info method of pagure.lib. """
        self.test_add_group()
        group = pagure.lib.search_groups(self.session, group_name='foo')
        self.assertNotEqual(group, None)
        self.assertEqual(group.group_name, 'foo')

        # Invalid new user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.edit_group_info,
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
            pagure.lib.edit_group_info,
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
            pagure.lib.edit_group_info,
            self.session,
            group=group,
            display_name='edited name',
            description=None,
            user='bar',
            is_admin=False,
        )

        msg = pagure.lib.edit_group_info(
            self.session,
            group=group,
            display_name='edited name',
            description=None,
            user='pingou',
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, 'Group "edited name" (foo) edited')

        msg = pagure.lib.edit_group_info(
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
        """ Test the add_group_to_project method of pagure.lib. """
        tests.create_projects(self.session)
        self.test_add_group()

        project = pagure.lib._get_project(self.session, 'test2')

        # Group does not exist
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_group_to_project,
            session=self.session,
            project=project,
            new_group='bar',
            user='foo',
        )

        # User does not exist
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_group_to_project,
            session=self.session,
            project=project,
            new_group='foo',
            user='bar',
        )

        # User not allowed
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_group_to_project,
            session=self.session,
            project=project,
            new_group='foo',
            user='foo',
        )

        # All good
        msg = pagure.lib.add_group_to_project(
            session=self.session,
            project=project,
            new_group='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')
        self.assertEqual(project.groups[0].group_name, 'foo')
        self.assertEqual(project.admin_groups[0].group_name, 'foo')

        # Group already associated with the project
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_group_to_project,
            session=self.session,
            project=project,
            new_group='foo',
            user='pingou',
        )

        # Update the access of group in the project
        msg = pagure.lib.add_group_to_project(
            session=self.session,
            project=project,
            new_group='foo',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')
        self.assertEqual(project.groups[0].group_name, 'foo')
        self.assertEqual(project.committer_groups[0].group_name, 'foo')

        # Update the access of group in the project
        msg = pagure.lib.add_group_to_project(
            session=self.session,
            project=project,
            new_group='foo',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')
        self.assertEqual(project.groups[0].group_name, 'foo')

    def test_update_watch_status(self):
        """ Test the update_watch_status method of pagure.lib. """
        tests.create_projects(self.session)

        project = pagure.lib._get_project(self.session, 'test')

        # User does not exist
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.update_watch_status,
            session=self.session,
            project=project,
            user='aavrug',
            watch=True,
        )

        # All good and when user seleted reset watch option.
        msg = pagure.lib.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch='-1',
        )
        self.session.commit()
        self.assertEqual(msg, 'Watch status is already reset')

        # All good and when user seleted watch option.
        msg = pagure.lib.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch=True,
        )
        self.session.commit()
        self.assertEqual(msg, 'You are now watching this repo.')

        # All good and when user selected unwatch option.
        msg = pagure.lib.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch=False,
        )
        self.session.commit()
        self.assertEqual(msg, 'You are no longer watching this repo.')

        # All good and when user seleted reset watch option.
        msg = pagure.lib.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch='-1',
        )
        self.session.commit()
        self.assertEqual(msg, 'Watch status reset')

    def test_is_watching(self):
        """ Test the is_watching method of pagure.lib. """
        tests.create_projects(self.session)
        self.test_add_group()

        project = pagure.lib._get_project(self.session, 'test')

        # If user not logged in
        watch = pagure.lib.is_watching(
            session=self.session,
            user=None,
            reponame='test',
        )
        self.assertFalse(watch)

        # User does not exist
        user = tests.FakeUser()
        user.username = 'aavrug'
        watch = pagure.lib.is_watching(
            session=self.session,
            user=user,
            reponame='test',
        )
        self.assertFalse(watch)

        pagure.lib.add_group_to_project(
            session=self.session,
            project=project,
            new_group='foo',
            user='pingou',
        )
        self.session.commit()

        group = pagure.lib.search_groups(self.session, group_name='foo')
        pagure.lib.add_user_to_group(
            self.session,
            username='foo',
            group=group,
            user='pingou',
            is_admin=False,
        )
        self.session.commit()
        group = pagure.lib.search_groups(self.session, group_name='foo')

        # If user belongs to any group of that project
        user.username = 'foo'
        watch = pagure.lib.is_watching(
            session=self.session,
            user=user,
            reponame='test',
        )
        self.assertTrue(watch)

        # If user is the creator
        user.username = 'pingou'
        watch = pagure.lib.is_watching(
            session=self.session,
            user=user,
            reponame='test',
        )
        self.assertTrue(watch)

        # Entry into watchers table
        pagure.lib.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch=True,
        )
        self.session.commit()

        # From watchers table
        watch = pagure.lib.is_watching(
            session=self.session,
            user=user,
            reponame='test',
        )
        self.assertTrue(watch)

        # Entry into watchers table
        msg = pagure.lib.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch=False,
        )
        self.session.commit()
        self.assertEqual(msg, 'You are no longer watching this repo.')

        # From watchers table
        watch = pagure.lib.is_watching(
            session=self.session,
            user=user,
            reponame='test',
        )
        self.assertFalse(watch)

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
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=project,
            new_user='bar',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # Check if the new contributor is watching
        user.username = 'bar'
        watch = pagure.lib.is_watching(
            session=self.session,
            user=user,
            reponame='test',
        )
        self.assertTrue(watch)

    def test_user_watch_list(self):
        ''' test user watch list method of pagure.lib '''

        tests.create_projects(self.session)

        # He should be watching
        user = tests.FakeUser()
        user.username = 'pingou'
        watch_list_objs = pagure.lib.user_watch_list(
            session=self.session,
            user='pingou',
        )
        watch_list = [obj.name for obj in watch_list_objs]
        self.assertEqual(watch_list, ['test', 'test2', 'test3'])

        # He isn't in the db, thus not watching anything
        user.username = 'vivek'
        watch_list_objs = pagure.lib.user_watch_list(
            session=self.session,
            user='vivek',
        )
        watch_list = [obj.name for obj in watch_list_objs]
        self.assertEqual(watch_list, [])

        # He shouldn't be watching anything
        user.username = 'foo'
        watch_list_objs = pagure.lib.user_watch_list(
            session=self.session,
            user='foo',
        )
        watch_list = [obj.name for obj in watch_list_objs]
        self.assertEqual(watch_list, [])

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_text2markdown(self):
        ''' Test the test2markdown method in pagure.lib. '''
        pagure.APP.config['TESTING'] = True
        pagure.APP.config['SERVER_NAME'] = 'pagure.org'
        pagure.SESSION = self.session
        pagure.lib.SESSION = self.session
        self.app = pagure.APP.test_client()

        # This creates:
        # project: test
        # fork: pingou/test
        # PR#1 to project test
        self.test_new_pull_request()

        # create PR#2 to project pingou/test
        repo = pagure.lib._get_project(self.session, 'test')
        forked_repo = pagure.lib._get_project(self.session, 'test', user='pingou')
        req = pagure.lib.new_pull_request(
            requestid=2,
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=forked_repo,
            branch_to='master',
            title='test pull-request in fork',
            user='pingou',
            requestfolder=None,
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

        iss = pagure.lib.new_issue(
            issue_id=4,
            session=self.session,
            repo=item,
            title='test issue',
            content='content test issue',
            user='pingou',
            ticketfolder=None,
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

        iss = pagure.lib.new_issue(
            issue_id=7,
            session=self.session,
            repo=item,
            title='test issue #7',
            content='content test issue #7 in forked repo',
            user='pingou',
            ticketfolder=None,
        )
        self.session.commit()
        self.assertEqual(iss.id, 7)
        self.assertEqual(iss.title, 'test issue #7')

        iss = pagure.lib.new_issue(
            issue_id=8,
            session=self.session,
            repo=item,
            title='private issue #8',
            content='Private content test issue #8 in forked repo',
            user='pingou',
            private=True,
            ticketfolder=None,
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
            'pingou committed on test#9364354a4555ba17aa60f0dc844d70b74eb1aecd',
            'irc://pagure.io',
            'ircs://pagure.io',
            'http://pagure.io',
            'https://pagure.io',
            '~~foo~~',
            '~~foo bar~~',
            '~~[BZ#1435310](https://bugzilla.redhat.com/1435310)~~',
            "~~[BZ#1435310](https://bugzilla.redhat.com/1435310) avc denial "
            "during F26AH boot 'error_name=org.freedesktop.systemd1."
            "NoSuchDynamicUser'~~",
            '``~~foo bar~~``',
            '~~foo bar~~ and ~~another ~~',
        ]
        expected = [
            # 'foo bar test#1 see?',
            '<p>foo bar <a href="http://pagure.org/test/pull-request/1"'
            ' title="test pull-request">test#1</a> see?</p>',
            # 'foo bar pingou/test#2 I mean, really', -- unknown namespace
            '<p>foo bar pingou/test#2 I mean, really</p>',
            # 'foo bar fork/pingou/test#2 bouza!',
            '<p>foo bar <a href="http://pagure.org/fork/'
            'pingou/test/pull-request/2" title="test pull-request in fork">'
            'pingou/test#2</a> bouza!</p>',
            # 'foo bar forks/pingou/test#2 bouza!',  -- the 's' doesn't matter
            '<p>foo bar <a href="http://pagure.org/fork/'
            'pingou/test/pull-request/2" title="test pull-request in fork">'
            'pingou/test#2</a> bouza!</p>',
            # 'foo bar ns/test3#4 bouza!',
            '<p>foo bar <a href="http://pagure.org/ns/test3/issue/4"'
            ' title="test issue">ns/test3#4</a> bouza!</p>',
            # 'foo bar fork/user/ns/test#5 bouza!', -- unknown fork
            '<p>foo bar user/ns/test#5 bouza!</p>',
            # 'foo bar fork/pingou/ns/test#7 bouza!',
            '<p>foo bar <a href="http://pagure.org/'
            'fork/pingou/ns/test/issue/7" title="test issue #7">'
            'pingou/ns/test#7</a> bouza!</p>',
            # 'test#1 bazinga!',
            '<p><a href="http://pagure.org/test/pull-request/1" '
            'title="test pull-request">test#1</a> bazinga!</p>',
            # 'pingou opened the PR forks/pingou/test#2'
            '<p>pingou opened the PR <a href="http://pagure.org/'
            'fork/pingou/test/pull-request/2" '
            'title="test pull-request in fork">pingou/test#2</a></p>',
            # 'fork/pingou/ns/test#8 is private',
            '<p><a href="http://pagure.org/fork/pingou/ns/test/issue/8" '
            'title="Private issue">pingou/ns/test#8</a> is private</p>',
            # 'pingou committed on test#9364354a4555ba17aa60f0dc844d70b74eb1aecd',
            '<p>pingou committed on <a href="http://pagure.org/'
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
        ]

        with pagure.APP.app_context():
            for idx, text in enumerate(texts):
                html = pagure.lib.text2markdown(text)
                self.assertEqual(html, expected[idx])

    def test_get_access_levels(self):
        ''' Test the get_access_levels method in pagure.lib '''

        acls = pagure.lib.get_access_levels(self.session)
        self.assertEqual(
            sorted(['admin', 'commit', 'ticket']),
            sorted(acls)
        )

    def test_get_project_users(self):
        ''' Test the get_project_users method when combine is True
        '''

        tests.create_projects(self.session)
        project = pagure.lib.get_project(self.session, name='test')

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
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou'
        )
        self.session.commit()
        # since, he is an admin, the msg should be 'User added'
        self.assertEqual(msg, 'User added')

        project = pagure.lib.get_project(self.session, name='test')
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
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')

        project = pagure.lib.get_project(self.session, name='test')
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
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')

        project = pagure.lib.get_project(self.session, name='test')
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
        project = pagure.lib.get_project(self.session, name='test')

        # Let's add a new user to the project, 'foo'
        # By default, if no access is specified, he becomes an admin
        msg = pagure.lib.add_user_to_project(
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
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')

        # He is just a committer
        project = pagure.lib.get_project(self.session, name='test')
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
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')

        # He is just a ticketer
        project = pagure.lib.get_project(self.session, name='test')
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
        msg = pagure.lib.add_group(
            self.session,
            group_name='JL',
            display_name='Justice League',
            description='Nope, it\'s not JLA anymore',
            group_type='user',
            user='foo',
            is_admin=False,
            blacklist=pagure.APP.config.get('BLACKLISTED_PROJECTS')
        )

        self.assertEqual(
            msg,
            'User `foo` added to the group `JL`.'
        )

        # Add the group to project we just created, test
        # First add it as an admin
        project = pagure.lib.get_project(self.session, name='test')
        msg = pagure.lib.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

        # Now, the group is an admin in the project
        # so, it must have access to everything
        project = pagure.lib.get_project(self.session, name='test')
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
        project = pagure.lib.get_project(self.session, name='test')
        msg = pagure.lib.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')

        # It shouldn't be an admin
        project = pagure.lib.get_project(self.session, name='test')
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
        msg = pagure.lib.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')

        # It is not an admin
        project = pagure.lib.get_project(self.session, name='test')
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
        msg = pagure.lib.add_group(
            self.session,
            group_name='JL',
            display_name='Justice League',
            description='Nope, it\'s not JLA anymore',
            group_type='user',
            user='foo',
            is_admin=False,
            blacklist=pagure.APP.config.get('BLACKLISTED_PROJECTS')
        )

        self.assertEqual(
            msg,
            'User `foo` added to the group `JL`.'
        )

        # Add the group to project we just created, test
        # First add it as an admin
        project = pagure.lib.get_project(self.session, name='test')
        msg = pagure.lib.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

        # Now, the group is an admin in the project
        # so, it must have access to everything
        project = pagure.lib.get_project(self.session, name='test')
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
        project = pagure.lib.get_project(self.session, name='test')
        msg = pagure.lib.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')

        # It shouldn't be an admin
        project = pagure.lib.get_project(self.session, name='test')
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
        msg = pagure.lib.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')

        # It is not an admin
        project = pagure.lib.get_project(self.session, name='test')
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
        project = pagure.lib.get_project(self.session, name='test')
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou'
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        user = pagure.lib.get_user(self.session, key='foo')
        # He should be an admin
        access_obj = pagure.lib.get_obj_access(
            self.session,
            project_obj=project,
            obj=user
        )
        self.assertEqual(access_obj.access, 'admin')

        # Update and check for commit access
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')
        project = pagure.lib.get_project(self.session, name='test')

        # He should be a committer
        access_obj = pagure.lib.get_obj_access(
            self.session,
            project_obj=project,
            obj=user
        )
        self.assertEqual(access_obj.access, 'commit')

        # Update and check for ticket access
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')
        project = pagure.lib.get_project(self.session, name='test')

        # He should be a ticketer
        access_obj = pagure.lib.get_obj_access(
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
        msg = pagure.lib.add_group(
            self.session,
            group_name='JL',
            display_name='Justice League',
            description='Nope, it\'s not JLA anymore',
            group_type='user',
            user='foo',
            is_admin=False,
            blacklist=pagure.APP.config.get('BLACKLISTED_PROJECTS')
        )

        self.assertEqual(
            msg,
            'User `foo` added to the group `JL`.'
        )

        # Add a group object - make him an admin first
        project = pagure.lib.get_project(self.session, name='test')
        msg = pagure.lib.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

        group = pagure.lib.search_groups(self.session, group_name='JL')
        # He should be an admin
        access_obj = pagure.lib.get_obj_access(
            self.session,
            project_obj=project,
            obj=group
        )
        self.assertEqual(access_obj.access, 'admin')

        # Update and check for commit access
        msg = pagure.lib.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')

        project = pagure.lib.get_project(self.session, name='test')
        # He should be a committer
        access_obj = pagure.lib.get_obj_access(
            self.session,
            project_obj=project,
            obj=group,
        )
        self.assertEqual(access_obj.access, 'commit')

        # Update and check for ticket access
        msg = pagure.lib.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group access updated')
        project = pagure.lib.get_project(self.session, name='test')

        # He should be a ticketer
        access_obj = pagure.lib.get_obj_access(
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
        iss = pagure.lib.new_issue(
            issue_id=4,
            session=self.session,
            repo=item,
            title='test issue',
            content='content test issue',
            user='pingou',
            ticketfolder=None,
        )
        self.session.commit()
        self.assertEqual(iss.id, 4)
        self.assertEqual(iss.title, 'test issue')

        # Unknown user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.set_watch_obj,
            self.session, 'unknown', iss, True
        )

        # Invalid object to watch - project
        self.assertRaises(
            pagure.exceptions.InvalidObjectException,
            pagure.lib.set_watch_obj,
            self.session, 'foo', iss.project, True
        )

        # Invalid object to watch - string
        self.assertRaises(
            AttributeError,
            pagure.lib.set_watch_obj,
            self.session, 'foo', 'ticket', True
        )

        # Watch the ticket
        out = pagure.lib.set_watch_obj(self.session, 'foo', iss, True)
        self.assertEqual(out, 'You are now watching this issue')

        # Un-watch the ticket
        out = pagure.lib.set_watch_obj(self.session, 'foo', iss, False)
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
            self.assertEqual(pagure.lib.tokenize_search_string(inp),
                             (flds, rem))

    def test_save_report(self):
        """ Test the save_report function. """
        # Create the projects
        tests.create_projects(self.session)

        project = pagure.lib.get_project(self.session, name='test')
        self.assertEqual(project.reports, {})

        name = 'test report'
        url = '?foo=bar&baz=biz'

        pagure.lib.save_report(
            self.session,
            repo=project,
            name=name,
            url=url,
            username=None
        )

        project = pagure.lib.get_project(self.session, name='test')
        self.assertEqual(
            project.reports,
            {'test report': {'baz': 'biz', 'foo': 'bar'}}
        )

        name = 'test report #2'
        url = '?foo=bar&foo=none&foo=baz'

        pagure.lib.save_report(
            self.session,
            repo=project,
            name=name,
            url=url,
            username=None
        )

        project = pagure.lib.get_project(self.session, name='test')
        self.assertEqual(
            project.reports,
            {
                'test report': {'baz': 'biz', 'foo': 'bar'},
                'test report #2': {'foo': ['bar', 'none', 'baz']}
            }
        )

    def test_text2markdown_table(self):
        """ Test the text2markdown function with a markdown table. """

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

        with pagure.APP.app_context():
            html = pagure.lib.text2markdown(text)
            self.assertEqual(html, expected)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagureLibtests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
