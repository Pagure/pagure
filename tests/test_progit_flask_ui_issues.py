# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
import unittest
import shutil
import sys
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib
import tests


class ProgitFlaskIssuestests(tests.Modeltests):
    """ Tests for flask issues controller of progit """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(ProgitFlaskIssuestests, self).setUp()

        progit.APP.config['TESTING'] = True
        progit.SESSION = self.session
        progit.ui.SESSION = self.session
        progit.ui.app.SESSION = self.session
        progit.ui.issues.SESSION = self.session
        progit.ui.repo.SESSION = self.session

        progit.APP.config['GIT_FOLDER'] = tests.HERE
        progit.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        progit.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        progit.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = progit.APP.test_client()

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_new_issue(self, p_send_email, p_ugt):
        """ Test the new_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/new_issue')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/foo/new_issue')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.get('/test/new_issue')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New issue</h2>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
            }

            # Insufficient input
            output = self.app.post('/test/new_issue', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New issue</h2>' in output.data)
            self.assertEqual(output.data.count(
                '<td class="errors">This field is required.</td>'), 2)

            data['title'] = 'Test issue'
            output = self.app.post('/test/new_issue', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New issue</h2>' in output.data)
            self.assertEqual(output.data.count(
                '<td class="errors">This field is required.</td>'), 1)

            data['issue_content'] = 'We really should improve on this issue'
            data['status'] = 'Open'
            output = self.app.post('/test/new_issue', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New issue</h2>' in output.data)
            self.assertEqual(output.data.count(
                '<td class="errors">This field is required.</td>'), 0)

            # Invalid user
            data['csrf_token'] = csrf_token
            output = self.app.post('/test/new_issue', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New issue</h2>' in output.data)
            self.assertEqual(output.data.count(
                '<td class="errors">This field is required.</td>'), 0)
            self.assertTrue(
                '<li class="error">No user &#34;username&#34; found</li>'
                in output.data)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.post(
                '/test/new_issue', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="message">Issue created</li>' in output.data)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue('<h2>\n    Issues (1)\n  </h2>' in output.data)

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_view_issues(self, p_send_email, p_ugt):
        """ Test the view_issues endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/issues')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/issues')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue('<h2>\n    Issues (0)\n  </h2>' in output.data)

        # Create issues to play with
        repo = progit.lib.get_project(self.session, 'test')
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

        # Whole list
        output = self.app.get('/test/issues')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue('<h2>\n    Issues (1)\n  </h2>' in output.data)

        # Status = closed
        output = self.app.get('/test/issues?status=cloSED')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue(
            '<h2>\n    Closed\n    Issues (0)\n  </h2>' in output.data)

        # Status = fixed
        output = self.app.get('/test/issues?status=fixed')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue(
            '<h2>\n    Closed\n    Issues (0)\n  </h2>' in output.data)

        # Project w/o issue tracker
        repo = progit.lib.get_project(self.session, 'test')
        repo.issue_tracker = False
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/issues')
        self.assertEqual(output.status_code, 404)

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_view_issue(self, p_send_email, p_ugt):
        """ Test the view_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/issue/1')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = progit.lib.get_project(self.session, 'test')
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

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue(
            '<p><a href="/login/">Login</a> to comment on this ticket.</p>'
            in output.data)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertFalse(
                '<p><a href="/login/">Login</a> to comment on this ticket.</p>'
                in output.data)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

        # Create private issue
        repo = progit.lib.get_project(self.session, 'test')
        msg = progit.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue created')

        # Not logged in
        output = self.app.get('/test/issue/2')
        self.assertEqual(output.status_code, 403)

        # Wrong user
        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/issue/2')
            self.assertEqual(output.status_code, 403)

        # reporter
        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/issue/2')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)

        # Project w/o issue tracker
        repo = progit.lib.get_project(self.session, 'test')
        repo.issue_tracker = False
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_update_issue(self, p_send_email, p_ugt):
        """ Test the update_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/issue/1/update')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/issue/1/update')
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = progit.lib.get_project(self.session, 'test')
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

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'status': 'fixed'
            }

            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertFalse(
                '<option selected value="Fixed">Fixed</option>'
                in output.data)

            data['status'] = 'Fixed'
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertFalse(
                '<option selected value="Fixed">Fixed</option>'
                in output.data)

            data['csrf_token'] = csrf_token
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue(
                '<li class="message">Edited successfully issue #1</li>'
                in output.data)
            self.assertTrue(
                '<option selected value="Fixed">Fixed</option>'
                in output.data)

            # Add new comment
            data = {
                'csrf_token': csrf_token,
                'status': 'Fixed',
                'comment': 'Woohoo a second comment !',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue(
                '<li class="message">Comment added</li>' in output.data)
            self.assertFalse(
                'li class="message">No changes to edit</li>' in output.data)
            self.assertTrue(
                '<p>Woohoo a second comment !</p>' in output.data)
            self.assertEqual(
                output.data.count('<div class="comment_body">'), 2)
            self.assertTrue(
                '<option selected value="Fixed">Fixed</option>'
                in output.data)

            # Add new tag
            data = {
                'csrf_token': csrf_token,
                'status': 'Fixed',
                'tag': 'tag#2',
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue(
                '<li class="message">Tag added</li>' in output.data)
            self.assertFalse(
                'li class="message">No changes to edit</li>' in output.data)
            self.assertTrue(
                '<p>Woohoo a second comment !</p>' in output.data)
            self.assertEqual(
                output.data.count('<div class="comment_body">'), 2)
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
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue(
                '<li class="error">No user &#34;ralph&#34; found</li>'
                in output.data)
            self.assertTrue(
                '<p>Woohoo a second comment !</p>' in output.data)
            self.assertEqual(
                output.data.count('<div class="comment_body">'), 2)
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
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue(
                '<li class="message">Issue assigned</li>' in output.data)
            self.assertTrue(
                '<a href="/test/issues?assignee=pingou">' in output.data)
            self.assertTrue(
                '<p>Woohoo a second comment !</p>' in output.data)
            self.assertEqual(
                output.data.count('<div class="comment_body">'), 2)
            self.assertTrue(
                '<option selected value="Fixed">Fixed</option>'
                in output.data)

        # Create another issue with a dependency
        repo = progit.lib.get_project(self.session, 'test')
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
        # Reset the status of the first issue
        parent_issue = progit.lib.search_issues(
            self.session, repo, issueid=2)
        parent_issue.status = 'Open'
        # Add the dependency relationship
        self.session.add(parent_issue)
        issue = progit.lib.search_issues(self.session, repo, issueid=2)
        issue.parents.append(parent_issue)
        self.session.add(issue)
        self.session.commit()

        with tests.user_set(progit.APP, user):

            data['csrf_token'] = csrf_token
            output = self.app.post(
                '/test/issue/2/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue(
                '<li class="error">You cannot close a ticket that has ticket '
                'depending that are still open.</li>' in output.data)
            self.assertTrue(
                '<option selected value="Open">Open</option>'
                in output.data)

        # Create private issue
        repo = progit.lib.get_project(self.session, 'test')
        msg = progit.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue created')

        # Wrong user
        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.post(
                '/test/issue/3/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        # Project w/o issue tracker
        repo = progit.lib.get_project(self.session, 'test')
        repo.issue_tracker = False
        self.session.add(repo)
        self.session.commit()

        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/issue/1/update')
            self.assertEqual(output.status_code, 404)

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_edit_issue(self, p_send_email, p_ugt):
        """ Test the edit_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/issue/1/edit')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/foo/issue/1/edit')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.get('/test/issue/1/edit')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/issue/1/edit')
            self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = progit.lib.get_project(self.session, 'test')
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

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/issue/1/edit')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/issue/1/edit')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Edit issue #1</h2>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'issue_content': 'We should work on this!'
            }

            output = self.app.post('/test/issue/1/edit', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Edit issue #1</h2>' in output.data)
            self.assertEqual(output.data.count(
                '<td class="errors">This field is required.</td>'), 1)
            self.assertEqual(output.data.count(
                '<td class="errors">Not a valid choice</td>'), 1)

            data['status'] = 'Open'
            data['title'] = 'Test issue #1'
            output = self.app.post('/test/issue/1/edit', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Edit issue #1</h2>' in output.data)
            self.assertEqual(output.data.count(
                '<td class="errors">This field is required.</td>'), 0)
            self.assertEqual(output.data.count(
                '<td class="errors">Not a valid choice</td>'), 0)

            data['csrf_token'] = csrf_token
            output = self.app.post(
                '/test/issue/1/edit', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<span class="issueid">#1</span> Test issue #1'
                in output.data)
            self.assertEqual(output.data.count(
                '<option selected value="Open">Open</option>'), 1)
            self.assertEqual(output.data.count(
                '<div class="comment_body">\n        '
                '<p>We should work on this!</p>'), 1)

        # Project w/o issue tracker
        repo = progit.lib.get_project(self.session, 'test')
        repo.issue_tracker = False
        self.session.add(repo)
        self.session.commit()

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.post('/test/issue/1/edit', data=data)
            self.assertEqual(output.status_code, 404)

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_edit_tag(self, p_send_email, p_ugt):
        """ Test the edit_tag endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/tag/foo/edit')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/foo/tag/foo/edit')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.get('/test/tag/foo/edit')
            self.assertEqual(output.status_code, 403)

        # Create issues to play with
        repo = progit.lib.get_project(self.session, 'test')
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

        # Add a tag to the issue
        issue = progit.lib.search_issues(self.session, repo, issueid=1)
        msg = progit.lib.add_issue_tag(
            session=self.session,
            issue=issue,
            tag='tag1',
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Tag added')

        # Before edit, list tags
        tags = progit.lib.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ['tag1'])

        # Edit tag
        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
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
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue(
                '<li class="message">Edited tag: tag1 to tag2</li>'
                in output.data)

        # After edit, list tags
        tags = progit.lib.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ['tag2'])

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_remove_tag(self, p_send_email, p_ugt):
        """ Test the remove_tag endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.post('/foo/droptag/')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.post('/foo/droptag/')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.post('/test/droptag/')
            self.assertEqual(output.status_code, 403)

        # Create issues to play with
        repo = progit.lib.get_project(self.session, 'test')
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

        # Add a tag to the issue
        issue = progit.lib.search_issues(self.session, repo, issueid=1)
        msg = progit.lib.add_issue_tag(
            session=self.session,
            issue=issue,
            tag='tag1',
            user='pingou',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Tag added')

        # Before edit, list tags
        tags = progit.lib.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ['tag1'])

        # Edit tag
        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.post(
                '/test/droptag/', data={}, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'tag': 'tag1'}

            output = self.app.post(
                '/test/droptag/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            data['csrf_token'] = csrf_token
            output = self.app.post(
                '/test/droptag/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="message">Removed tag: tag1</li>' in output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitFlaskIssuestests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
