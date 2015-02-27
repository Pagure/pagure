#-*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib
import tests


class ProgitLibtests(tests.Modeltests):
    """ Tests for progit.lib """

    def test_get_next_id(self):
        """ Test the get_next_id function of progit.lib. """
        tests.create_projects(self.session)
        self.assertEqual(1, progit.lib.get_next_id(self.session, 1))

    def test_search_user_all(self):
        """ Test the search_user of progit.lib. """

        # Retrieve all users
        items = progit.lib.search_user(self.session)
        self.assertEqual(2, len(items))
        self.assertEqual(1, items[0].id)
        self.assertEqual('pingou', items[0].user)
        self.assertEqual('pingou', items[0].username)
        self.assertEqual([], items[0].groups)
        self.assertEqual(2, items[1].id)
        self.assertEqual('foo', items[1].user)
        self.assertEqual('foo', items[1].username)
        self.assertEqual([], items[1].groups)

    def test_search_user_username(self):
        """ Test the search_user of progit.lib. """

        # Retrieve user by username
        item = progit.lib.search_user(self.session, username='foo')
        self.assertEqual('foo', item.user)
        self.assertEqual('foo', item.username)
        self.assertEqual([], item.groups)

        item = progit.lib.search_user(self.session, username='bar')
        self.assertEqual(None, item)

    def test_search_user_email(self):
        """ Test the search_user of progit.lib. """

        # Retrieve user by email
        item = progit.lib.search_user(self.session, email='foo@foo.com')
        self.assertEqual(None, item)

        item = progit.lib.search_user(self.session, email='foo@bar.com')
        self.assertEqual('foo', item.user)
        self.assertEqual('foo', item.username)
        self.assertEqual([], item.groups)
        self.assertEqual(
            ['foo@bar.com'], [email.email for email in item.emails])

        item = progit.lib.search_user(self.session, email='foo@pingou.com')
        self.assertEqual('pingou', item.user)
        self.assertEqual(
            ['bar@pingou.com', 'foo@pingou.com'],
            [email.email for email in item.emails])

    def test_search_user_token(self):
        """ Test the search_user of progit.lib. """

        # Retrieve user by token
        item = progit.lib.search_user(self.session, token='aaa')
        self.assertEqual(None, item)

        item = progit.lib.model.User(
            user='pingou2',
            fullname='PY C',
            token='aaabbb',
        )
        self.session.add(item)
        self.session.commit()

        item = progit.lib.search_user(self.session, token='aaabbb')
        self.assertEqual('pingou2', item.user)
        self.assertEqual('PY C', item.fullname)

    def test_search_user_pattern(self):
        """ Test the search_user of progit.lib. """

        # Retrieve user by pattern
        item = progit.lib.search_user(self.session, pattern='a*')
        self.assertEqual([], item)

        item = progit.lib.model.User(
            user='pingou2',
            fullname='PY C',
            token='aaabbb',
        )
        self.session.add(item)
        self.session.commit()

        items = progit.lib.search_user(self.session, pattern='p*')
        self.assertEqual(2, len(items))
        self.assertEqual(1, items[0].id)
        self.assertEqual('pingou', items[0].user)
        self.assertEqual('pingou', items[0].username)
        self.assertEqual([], items[0].groups)
        self.assertEqual(
            ['bar@pingou.com', 'foo@pingou.com'],
            [email.email for email in items[0].emails])
        self.assertEqual(3, items[1].id)
        self.assertEqual('pingou2', items[1].user)
        self.assertEqual('pingou2', items[1].username)
        self.assertEqual([], items[1].groups)
        self.assertEqual(
            [], [email.email for email in items[1].emails])

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_new_issue(self, p_send_email, p_ugt):
        """ Test the new_issue of progit.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        repo = progit.lib.get_project(self.session, 'test')

        # Before
        issues = progit.lib.search_issues(self.session, repo)
        self.assertEqual(len(issues), 0)

        # See where it fails
        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.new_issue,
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='blah',
            ticketfolder=None
        )

        # Create issues to play with
        msg = progit.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue created')

        msg = progit.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this for the second time',
            user='foo',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue created')

        # After
        issues = progit.lib.search_issues(self.session, repo)
        self.assertEqual(len(issues), 2)

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_edit_issue(self, p_send_email, p_ugt):
        """ Test the edit_issue of progit.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()
        repo = progit.lib.get_project(self.session, 'test')
        issue = progit.lib.search_issues(self.session, repo, issueid=2)

        # Edit the issue
        msg = progit.lib.edit_issue(
            session=self.session,
            issue=issue,
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'No changes to edit')

        msg = progit.lib.edit_issue(
            session=self.session,
            issue=issue,
            ticketfolder=None,
            title='Test issue #2',
            content='We should work on this for the second time',
            status='Open',
        )
        self.session.commit()
        self.assertEqual(msg, 'No changes to edit')

        msg = progit.lib.edit_issue(
            session=self.session,
            issue=issue,
            ticketfolder=None,
            title='Foo issue #2',
            content='We should work on this period',
            status='Invalid')
        self.session.commit()
        self.assertEqual(msg, 'Edited successfully issue #2')

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_add_issue_tag(self, p_send_email, p_ugt):
        """ Test the add_issue_tag of progit.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_edit_issue()
        repo = progit.lib.get_project(self.session, 'test')
        issue = progit.lib.search_issues(self.session, repo, issueid=1)

        # Add a tag to the issue
        msg = progit.lib.add_issue_tag(
            session=self.session,
            issue=issue,
            tag='tag1',
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Tag added')

        # Try a second time
        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.add_issue_tag,
            session=self.session,
            issue=issue,
            tag='tag1',
            user='pingou',
            ticketfolder=None)

        issues = progit.lib.search_issues(self.session, repo, tags='tag1')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 1)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual([tag.tag for tag in issues[0].tags], ['tag1'])

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_remove_issue_tags(self, p_send_email, p_ugt):
        """ Test the remove_issue_tags of progit.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_add_issue_tag()
        repo = progit.lib.get_project(self.session, 'test')
        issue = progit.lib.search_issues(self.session, repo, issueid=1)

        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.remove_issue_tags,
            session=self.session,
            project=repo,
            tags='foo')

        msgs = progit.lib.remove_issue_tags(
            session=self.session,
            project=repo,
            tags='tag1')

        self.assertEqual(msgs, [u'Removed tag: tag1'])

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_edit_issue_tags(self, p_send_email, p_ugt):
        """ Test the edit_issue_tags of progit.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_add_issue_tag()
        repo = progit.lib.get_project(self.session, 'test')
        issue = progit.lib.search_issues(self.session, repo, issueid=1)

        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.edit_issue_tags,
            session=self.session,
            project=repo,
            old_tag='foo',
            new_tag='bar')

        msgs = progit.lib.edit_issue_tags(
            session=self.session,
            project=repo,
            old_tag='tag1',
            new_tag='tag2')
        self.session.commit()
        self.assertEqual(msgs, ['Edited tag: tag1 to tag2'])

        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.edit_issue_tags,
            session=self.session,
            project=repo,
            old_tag='tag2',
            new_tag='tag2')

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_search_issues(self, p_send_email, p_ugt):
        """ Test the search_issues of progit.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_edit_issue()
        repo = progit.lib.get_project(self.session, 'test')

        # All issues
        issues = progit.lib.search_issues(self.session, repo)
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].id, 1)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual(issues[0].tags, [])
        self.assertEqual(issues[1].id, 2)
        self.assertEqual(issues[1].project_id, 1)
        self.assertEqual(issues[1].status, 'Invalid')
        self.assertEqual(issues[1].tags, [])

        # Issues by status
        issues = progit.lib.search_issues(
            self.session, repo, status='Invalid')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Invalid')
        self.assertEqual(issues[0].tags, [])

        # Issues closed
        issues = progit.lib.search_issues(
            self.session, repo, closed=True)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Invalid')
        self.assertEqual(issues[0].tags, [])

        # Issues by tag
        issues = progit.lib.search_issues(self.session, repo, tags='foo')
        self.assertEqual(len(issues), 0)

        # Issue by id
        issue = progit.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.title, 'Test issue')
        self.assertEqual(issue.user.user, 'pingou')
        self.assertEqual(issue.tags, [])

        # Issues by authors
        issues = progit.lib.search_issues(self.session, repo, author='foo')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Invalid')
        self.assertEqual(issues[0].tags, [])

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_add_issue_assignee(self, p_send_email, p_ugt):
        """ Test the add_issue_assignee of progit.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_new_issue()
        repo = progit.lib.get_project(self.session, 'test')
        issue = progit.lib.search_issues(self.session, repo, issueid=2)

        # Before
        issues = progit.lib.search_issues(
            self.session, repo, assignee='pingou')
        self.assertEqual(len(issues), 0)

        # Test when it fails
        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.add_issue_assignee,
            session=self.session,
            issue=issue,
            assignee='foo@foobar.com',
            user='foo@pingou.com',
            ticketfolder=None
        )

        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.add_issue_assignee,
            session=self.session,
            issue=issue,
            assignee='foo@bar.com',
            user='foo@foopingou.com',
            ticketfolder=None
        )

        # Set the assignee by its email
        msg = progit.lib.add_issue_assignee(
            session=self.session,
            issue=issue,
            assignee='foo@bar.com',
            user='foo@pingou.com',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Issue assigned')

        # Change the assignee to someone else by its username
        msg = progit.lib.add_issue_assignee(
            session=self.session,
            issue=issue,
            assignee='pingou',
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Issue assigned')

        # After  -- Searches by assignee
        issues = progit.lib.search_issues(
            self.session, repo, assignee='pingou')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual(issues[0].tags, [])

        issues = progit.lib.search_issues(
            self.session, repo, assignee=True)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 2)
        self.assertEqual(issues[0].title, 'Test issue #2')
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual(issues[0].tags, [])

        issues = progit.lib.search_issues(
            self.session, repo, assignee=False)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, 1)
        self.assertEqual(issues[0].title, 'Test issue')
        self.assertEqual(issues[0].project_id, 1)
        self.assertEqual(issues[0].status, 'Open')
        self.assertEqual(issues[0].tags, [])

        # Reset the assignee to no-one
        msg = progit.lib.add_issue_assignee(
            session=self.session,
            issue=issue,
            assignee=None,
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Assignee reset')

        issues = progit.lib.search_issues(
            self.session, repo, assignee=False)
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].id, 1)
        self.assertEqual(issues[1].id, 2)

        issues = progit.lib.search_issues(
            self.session, repo, assignee=True)
        self.assertEqual(len(issues), 0)

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_add_issue_comment(self, p_send_email, p_ugt):
        """ Test the add_issue_comment of progit.lib. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        self.test_new_issue()
        repo = progit.lib.get_project(self.session, 'test')

        # Before
        issue = progit.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        # Add a comment to that issue
        msg = progit.lib.add_issue_comment(
            session=self.session,
            issue=issue,
            comment='Hey look a comment!',
            user='foo',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        # After
        issue = progit.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)
        self.assertEqual(issue.comments[0].comment, 'Hey look a comment!')
        self.assertEqual(issue.comments[0].user.user, 'foo')

    @patch('progit.lib.notify.send_email')
    def test_add_user_to_project(self, p_send_email):
        """ Test the add_user_to_project of progit.lib. """
        p_send_email.return_value = True

        tests.create_projects(self.session)

        # Before
        repo = progit.lib.get_project(self.session, 'test')
        self.assertEqual(len(repo.users), 0)

        # Add an user to a project
        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.add_user_to_project,
            session=self.session,
            project=repo,
            user='foobar',
        )

        msg = progit.lib.add_user_to_project(
            session=self.session,
            project=repo,
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # After
        repo = progit.lib.get_project(self.session, 'test')
        self.assertEqual(len(repo.users), 1)
        self.assertEqual(repo.users[0].user, 'foo')

    def test_new_project(self):
        """ Test the new_project of progit.lib. """
        gitfolder = os.path.join(self.path, 'repos')
        docfolder = os.path.join(self.path, 'docs')
        ticketfolder = os.path.join(self.path, 'tickets')

        os.mkdir(gitfolder)
        os.mkdir(docfolder)
        os.mkdir(ticketfolder)

        # Create a new project
        msg = progit.lib.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            description='description for testproject',
            parent_id=None
        )
        self.session.commit()
        self.assertEqual(msg, 'Project "testproject" created')

        repo = progit.lib.get_project(self.session, 'testproject')
        self.assertEqual(repo.path, 'testproject.git')

        gitrepo = os.path.join(gitfolder, repo.path)
        docrepo = os.path.join(docfolder, repo.path)
        ticketrepo = os.path.join(ticketfolder, repo.path)

        self.assertTrue(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))

        # Try re-creating it but all repos are existing
        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.new_project,
            session=self.session,
            user='pingou',
            name='testproject',
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            description='description for testproject',
            parent_id=None
        )
        self.session.rollback()

        self.assertTrue(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))

        # Drop the main git repo and try again
        shutil.rmtree(gitrepo)
        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.new_project,
            session=self.session,
            user='pingou',
            name='testproject',
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            description='description for testproject',
            parent_id=None
        )
        self.session.rollback()

        self.assertFalse(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))

        # Drop the doc repo and try again
        shutil.rmtree(docrepo)
        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.new_project,
            session=self.session,
            user='pingou',
            name='testproject',
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            description='description for testproject',
            parent_id=None
        )
        self.session.rollback()
        self.assertFalse(os.path.exists(gitrepo))
        self.assertFalse(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))

    def test_update_project_settings(self):
        """ Test the update_project_settings of progit.lib. """

        tests.create_projects(self.session)

        # Before
        repo = progit.lib.get_project(self.session, 'test2')
        self.assertTrue(repo.issue_tracker)
        self.assertTrue(repo.project_docs)

        msg = progit.lib.update_project_settings(
            session=self.session,
            repo=repo,
            issue_tracker=True,
            project_docs=True
        )
        self.assertEqual(msg, 'No settings to change')

        msg = progit.lib.update_project_settings(
            session=self.session,
            repo=repo,
            issue_tracker=False,
            project_docs=False
        )
        self.assertEqual(msg, 'Edited successfully settings of repo: test2')

        # After
        repo = progit.lib.get_project(self.session, 'test2')
        self.assertFalse(repo.issue_tracker)
        self.assertFalse(repo.project_docs)

    def test_search_projects(self):
        """ Test the search_projects of progit.lib. """
        tests.create_projects(self.session)

        projects = progit.lib.search_projects(self.session)
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0].id, 1)
        self.assertEqual(projects[1].id, 2)

        projects = progit.lib.search_projects(self.session, username='foo')
        self.assertEqual(len(projects), 0)

        projects = progit.lib.search_projects(self.session, username='pingou')
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0].id, 1)
        self.assertEqual(projects[1].id, 2)

        projects = progit.lib.search_projects(self.session, start=1)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].id, 2)

        projects = progit.lib.search_projects(self.session, limit=1)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].id, 1)

        projects = progit.lib.search_projects(self.session, count=True)
        self.assertEqual(projects, 2)

    def test_search_project_forked(self):
        """ Test the search_project for forked projects in progit.lib. """
        tests.create_projects(self.session)

        # Create two forked repo
        item = progit.lib.model.Project(
            user_id=2,  # foo
            name='test',
            description='test project #1',
            parent_id=1,
        )
        self.session.add(item)

        item = progit.lib.model.Project(
            user_id=2,  # foo
            name='test2',
            description='test project #2',
            parent_id=2,
        )
        self.session.add(item)

        # Since we have two forks, let's search them
        projects = progit.lib.search_projects(self.session, fork=True)
        self.assertEqual(len(projects), 2)
        projects = progit.lib.search_projects(self.session, fork=False)
        self.assertEqual(len(projects), 2)

    def test_get_tags_of_project(self):
        """ Test the get_tags_of_project of progit.lib. """

        self.test_add_issue_tag()
        repo = progit.lib.get_project(self.session, 'test')

        tags = progit.lib.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ['tag1'])

        tags = progit.lib.get_tags_of_project(
            self.session, repo, pattern='T*')
        self.assertEqual([tag.tag for tag in tags], ['tag1'])

        repo = progit.lib.get_project(self.session, 'test2')

        tags = progit.lib.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], [])

    def test_get_issue_statuses(self):
        """ Test the get_issue_statuses of progit.lib. """
        statuses = progit.lib.get_issue_statuses(self.session)
        self.assertEqual(
            statuses, ['Open', 'Invalid', 'Insufficient data', 'Fixed'])

    def test_set_up_user(self):
        """ Test the set_up_user of progit.lib. """

        items = progit.lib.search_user(self.session)
        self.assertEqual(2, len(items))
        self.assertEqual(1, items[0].id)
        self.assertEqual('pingou', items[0].user)
        self.assertEqual(2, items[1].id)
        self.assertEqual('foo', items[1].user)

        progit.lib.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth',
            user_email='skvidal@fp.o'
        )
        self.session.commit()

        items = progit.lib.search_user(self.session)
        self.assertEqual(3, len(items))
        self.assertEqual(1, items[0].id)
        self.assertEqual('pingou', items[0].user)
        self.assertEqual(2, items[1].id)
        self.assertEqual('foo', items[1].user)
        self.assertEqual(3, items[2].id)
        self.assertEqual('skvidal', items[2].user)
        self.assertEqual('Seth', items[2].fullname)
        self.assertEqual(
            ['skvidal@fp.o'], [email.email for email in items[2].emails])

        # Add the user a second time
        progit.lib.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth V',
            user_email='skvidal@fp.o'
        )
        self.session.commit()
        # Nothing changed
        items = progit.lib.search_user(self.session)
        self.assertEqual(3, len(items))
        self.assertEqual('skvidal', items[2].user)
        self.assertEqual('Seth V', items[2].fullname)
        self.assertEqual(
            ['skvidal@fp.o'], [email.email for email in items[2].emails])

        # Add the user a third time with a different email
        progit.lib.set_up_user(
            session=self.session,
            username='skvidal',
            fullname='Seth',
            user_email='svidal@fp.o'
        )
        self.session.commit()
        # Email added
        items = progit.lib.search_user(self.session)
        self.assertEqual(3, len(items))
        self.assertEqual('skvidal', items[2].user)
        self.assertEqual(
            ['skvidal@fp.o', 'svidal@fp.o'],
            [email.email for email in items[2].emails])

    def test_update_user_ssh(self):
        """ Test the update_user_ssh of progit.lib. """

        # Before
        user = progit.lib.search_user(self.session, username='foo')
        self.assertEqual(user.public_ssh_key, None)

        msg = progit.lib.update_user_ssh(self.session, user, 'blah')
        self.assertEqual(msg, 'Public ssh key updated')

        msg = progit.lib.update_user_ssh(self.session, user, 'blah')
        self.assertEqual(msg, 'Nothing to update')

        msg = progit.lib.update_user_ssh(self.session, 'foo', None)
        self.assertEqual(msg, 'Public ssh key updated')

    def test_avatar_url(self):
        """ Test the avatar_url of progit.lib. """
        output = progit.lib.avatar_url('pingou')
        self.assertEqual(
            output,
            'https://seccdn.libravatar.org/avatar/'
            '01fe73d687f4db328da1183f2a1b5b22962ca9d9c50f0728aafeac974856311c'
            '?s=64&d=retro')

    def test_fork_project(self):
        """ Test the fork_project of progit.lib. """
        gitfolder = os.path.join(self.path, 'repos')
        docfolder = os.path.join(self.path, 'docs')
        ticketfolder = os.path.join(self.path, 'tickets')
        forkfolder = os.path.join(self.path, 'forks')

        os.mkdir(gitfolder)
        os.mkdir(docfolder)
        os.mkdir(ticketfolder)

        projects = progit.lib.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        # Create a new project
        msg = progit.lib.new_project(
            session=self.session,
            user='pingou',
            name='testproject',
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            description='description for testproject',
            parent_id=None
        )
        self.session.commit()
        self.assertEqual(msg, 'Project "testproject" created')

        projects = progit.lib.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        repo = progit.lib.get_project(self.session, 'testproject')
        gitrepo = os.path.join(gitfolder, repo.path)
        docrepo = os.path.join(docfolder, repo.path)
        ticketrepo = os.path.join(ticketfolder, repo.path)

        self.assertTrue(os.path.exists(gitrepo))
        self.assertTrue(os.path.exists(docrepo))
        self.assertTrue(os.path.exists(ticketrepo))

        # Fail to fork

        # Cannot fail your own project
        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.fork_project,
            session=self.session,
            user='pingou',
            repo=repo,
            gitfolder=gitfolder,
            forkfolder=forkfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
        )
        self.session.rollback()

        # Git repo exists
        grepo = '%s.git' % os.path.join(forkfolder, 'foo', 'testproject')
        os.makedirs(grepo)
        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.fork_project,
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            forkfolder=forkfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
        )
        self.session.rollback()
        shutil.rmtree(grepo)

        # Doc repo exists
        grepo = '%s.git' % os.path.join(docfolder, 'foo', 'testproject')
        os.makedirs(grepo)
        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.fork_project,
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            forkfolder=forkfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
        )
        self.session.rollback()
        shutil.rmtree(grepo)

        # Ticket repo exists
        grepo = '%s.git' % os.path.join(ticketfolder, 'foo', 'testproject')
        os.makedirs(grepo)
        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.fork_project,
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            forkfolder=forkfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
        )
        self.session.rollback()
        shutil.rmtree(grepo)

        projects = progit.lib.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        # Fork worked

        msg = progit.lib.fork_project(
            session=self.session,
            user='foo',
            repo=repo,
            gitfolder=gitfolder,
            forkfolder=forkfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
        )
        self.session.commit()
        self.assertEqual(
            msg, 'Repo "testproject" cloned to "foo/testproject"')

        projects = progit.lib.search_projects(self.session)
        self.assertEqual(len(projects), 2)

        # Fork a fork

        repo = progit.lib.get_project(
            self.session, 'testproject', user='foo')

        msg = progit.lib.fork_project(
            session=self.session,
            user='pingou',
            repo=repo,
            gitfolder=gitfolder,
            forkfolder=forkfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
        )
        self.session.commit()
        self.assertEqual(
            msg, 'Repo "testproject" cloned to "pingou/testproject"')

        projects = progit.lib.search_projects(self.session)
        self.assertEqual(len(projects), 3)

    def test_new_pull_request(self):
        """ test new_pull_request of progit.lib. """
        tests.create_projects(self.session)

        # Create a forked repo
        item = progit.lib.model.Project(
            user_id=1,  # pingou
            name='test',
            description='test project #1',
            parent_id=1,
        )
        self.session.commit()
        self.session.add(item)

        repo = progit.lib.get_project(self.session, 'test')
        forked_repo = progit.lib.get_project(
            self.session, 'test', user='pingou')

        msg = progit.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou'
        )
        self.assertEqual(msg, 'Request created')

    def test_add_pull_request_comment(self):
        """ Test add_pull_request_comment of progit.lib. """

        self.test_new_pull_request()

        request = progit.lib.search_pull_requests(self.session, requestid=1)

        msg = progit.lib.add_pull_request_comment(
            session=self.session,
            request=request,
            commit='commithash',
            filename='file',
            row=None,
            comment='This is awesome, I got to remember it!',
            user='foo'
        )
        self.assertEqual(msg, 'Comment added')

    def test_search_pull_requests(self):
        """ Test search_pull_requests of progit.lib. """

        self.test_new_pull_request()

        prs = progit.lib.search_pull_requests(
            session=self.session
        )
        self.assertEqual(len(prs), 1)

        prs = progit.lib.search_pull_requests(
            session=self.session,
            project_id=1
        )
        self.assertEqual(len(prs), 1)

        prs = progit.lib.search_pull_requests(
            session=self.session,
            project_id_from=3
        )
        self.assertEqual(len(prs), 1)

        prs = progit.lib.search_pull_requests(
            session=self.session,
            status=False
        )
        self.assertEqual(len(prs), 0)

    @patch('progit.lib.notify.notify_merge_pull_request')
    @patch('progit.lib.notify.notify_cancelled_pull_request')
    def test_close_pull_request(self, mpr, cpr):
        """ Test close_pull_request of progit.lib. """
        mpr.return_value = True
        cpr.return_value = True

        self.test_new_pull_request()

        request = progit.lib.search_pull_requests(self.session, requestid=1)

        progit.lib.close_pull_request(
            session=self.session,
            request=request,
            user='pingou',
            merged=True)
        self.session.commit()

        prs = progit.lib.search_pull_requests(
            session=self.session,
            status=False
        )
        self.assertEqual(len(prs), 1)

        # Does not change much, just the notification sent

        progit.lib.close_pull_request(
            session=self.session,
            request=request,
            user='pingou',
            merged=False)
        self.session.commit()

        prs = progit.lib.search_pull_requests(
            session=self.session,
            status=False
        )
        self.assertEqual(len(prs), 1)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitLibtests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
