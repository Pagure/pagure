#!/usr/bin/env python
# coding=utf-8

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Vivek Anand <vivekanand1101@gmail.com>

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


class PagureFlaskIssuesACLtests(tests.Modeltests):
    """ Tests for flask issues controller of pagure for acls """

    def setUp(self):
        """ Set up the environnment, run before every tests. """
        super(PagureFlaskIssuesACLtests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.issues.SESSION = self.session
        pagure.ui.repo.SESSION = self.session
        pagure.ui.filters.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = self.path
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            self.path, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            self.path, 'docs')
        self.app = pagure.APP.test_client()

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_view_issue_no_access(self, p_send_email, p_ugt):
        """ Test the view_issue endpoint. when a user has no access on repo """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/issue/1')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path), bare=True)

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

        # Add milestone
        repo.milestones = {'77': None}
        self.session.add(repo)
        issue = pagure.lib.search_issues(
            self.session,
            repo=repo,
            issueid=1
        )

        pagure.lib.edit_issue(
            self.session,
            issue,
            pagure.APP.config.get('TICKETS_FOLDER'),
            user='pingou',
            milestone='77'
        )
        self.session.add(repo)
        self.session.add(issue)

        msg = pagure.lib.set_custom_key_fields(
            self.session,
            project=repo,
            fields=['abc', 'xyz'],
            types=['boolean', 'boolean'],
            data=[None, None],
        )
        self.assertEqual(msg, 'List of custom fields updated')
        self.session.add(repo)

        msg = pagure.lib.set_custom_key_value(
            self.session,
            issue=issue,
            key=pagure.lib.get_custom_key(self.session, repo, 'abc'),
            value=1
        )
        self.session.add(issue)
        self.session.commit()


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

            # no edit metadata
            self.assertNotIn(
                '<a class="btn btn-secondary issue-metadata-display'
                ' editmetadatatoggle">',
                output.data)
            self.assertFalse(
                '<a href="/login/">Login</a> to comment on this ticket.'
                in output.data)

            # can view the milestone
            self.assertIn(
                '<label><strong>Milestone</strong></label>',
                output.data)
            self.assertIn(
                '<span >77</span>',
                output.data)
            # but can't edit them
            self.assertNotIn(
                '<select class="form-control c-select" id="milestone" '
                ' name="milestone"><option value=""></option><option '
                'selected value="77">77</option></select>',
                output.data)

            # can view depends on
            self.assertIn(
                '<label><strong>Depends on</strong></label>',
                output.data)

            # can't edit depends on
            self.assertNotIn(
                '<input class="form-control" id="depends" type="text"\n\
                                placeholder="issue depending" name="depends"\n\
                                value="" />',
                output.data)

            # no toggle option for custom fields
            self.assertNotIn(
                '<a class="btn btn-secondary '
                'issue-custom-display edit_custom_toggle">',
                output.data)

            # no checkbox for private
            self.assertNotIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertNotIn(
                '<button class="btn btn-danger btn-sm" type="submit"',
                output.data)
            self.assertNotIn('title="Delete this ticket">', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # no edit metadata
            self.assertNotIn(
                '<a class="btn btn-secondary issue-metadata-display'
                ' editmetadatatoggle">',
                output.data)
            self.assertFalse(
                '<a href="/login/">Login</a> to comment on this ticket.'
                in output.data)

            # no toggle option for custom fields
            self.assertNotIn(
                '<a class="btn btn-secondary '
                'issue-custom-display edit_custom_toggle">',
                output.data)

            # can't see the custom field as a checkbox
            self.assertNotIn(
                '<input type="checkbox"                   '
                'class="form-control" name="abc" id="abc"checked/>',
                output.data)

            # can view the milestone
            self.assertIn(
                '<label><strong>Milestone</strong></label>',
                output.data)
            self.assertIn(
                '<span >77</span>',
                output.data)

            # but can't edit them
            self.assertNotIn(
                '<select class="form-control c-select" id="milestone" '
                ' name="milestone"><option value=""></option><option '
                'selected value="77">77</option></select>',
                output.data)

            # can view depends on
            self.assertIn(
                '<label><strong>Depends on</strong></label>',
                output.data)

            # can't edit depends on
            self.assertNotIn(
                '<input class="form-control" id="depends" type="text"\n\
                                placeholder="issue depending" name="depends"\n\
                                value="" />',
                output.data)

            # no checkbox for private
            self.assertNotIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output.data)

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

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_view_issue_ticket_access(self, p_send_email, p_ugt):
        """ Test the view_issue endpoint. when a user has ticket access on repo """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/issue/1')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path), bare=True)

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')

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

        # Add milestone
        repo.milestones = {'77': None}
        self.session.add(repo)
        issue = pagure.lib.search_issues(
            self.session,
            repo=repo,
            issueid=1
        )

        pagure.lib.edit_issue(
            self.session,
            issue,
            pagure.APP.config.get('TICKETS_FOLDER'),
            user='pingou',
            milestone='77'
        )
        self.session.add(repo)
        self.session.add(issue)

        msg = pagure.lib.set_custom_key_fields(
            self.session,
            project=repo,
            fields=['abc', 'xyz'],
            types=['boolean', 'boolean'],
            data=[None, None],
        )
        self.assertEqual(msg, 'List of custom fields updated')
        self.session.add(repo)

        msg = pagure.lib.set_custom_key_value(
            self.session,
            issue=issue,
            key=pagure.lib.get_custom_key(self.session, repo, 'abc'),
            value=1
        )
        self.session.add(issue)
        self.session.commit()


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

            # no edit metadata
            self.assertNotIn(
                '<a class="btn btn-secondary issue-metadata-display'
                ' editmetadatatoggle">',
                output.data)
            self.assertFalse(
                '<a href="/login/">Login</a> to comment on this ticket.'
                in output.data)

            # can view the milestone
            self.assertIn(
                '<label><strong>Milestone</strong></label>',
                output.data)
            self.assertIn(
                '<span >77</span>',
                output.data)
            # but can't edit them
            self.assertNotIn(
                '<select class="form-control c-select" id="milestone" '
                ' name="milestone"><option value=""></option><option '
                'selected value="77">77</option></select>',
                output.data)

            # can view depends on
            self.assertIn(
                '<label><strong>Depends on</strong></label>',
                output.data)

            # can't edit depends on
            self.assertNotIn(
                '<input class="form-control" id="depends" type="text"\n\
                                placeholder="issue depending" name="depends"\n\
                                value="" />',
                output.data)

            # no toggle option for custom fields
            self.assertNotIn(
                '<a class="btn btn-secondary '
                'issue-custom-display edit_custom_toggle">',
                output.data)

            # no checkbox for private
            self.assertNotIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)

            # the user can't edit the issue
            self.assertNotIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertNotIn(
                '<button class="btn btn-danger btn-sm" type="submit"',
                output.data)

            # the user still can't delete the ticket
            self.assertNotIn('title="Delete this ticket">', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # the user can do the following things
            # edit metadata
            self.assertIn(
                '<a class="btn btn-secondary issue-metadata-display'
                ' editmetadatatoggle">',
                output.data)

            # toggle option for custom fields
            self.assertIn(
                '<a class="btn btn-secondary '
                'issue-custom-display edit_custom_toggle">',
                output.data)

            # can view the milestone
            self.assertIn(
                '<label><strong>Milestone</strong></label>',
                output.data)
            self.assertIn(
                '<span >77</span>',
                output.data)

            # can edit them
            self.assertIn(
                '<select class="form-control c-select" id="milestone" '
                'name="milestone"><option value=""></option><option selected '
                'value="77">77</option></select>\n      <div>\n',
                output.data)

            # can view depends on
            self.assertIn(
                '<label><strong>Depends on</strong></label>',
                output.data)

            # can edit depends on
            self.assertIn(
                '<input class="form-control" id="depends" type="text"'
                '\n                placeholder="issue depending" name="depends"\n',
                output.data)

            # the user should be able to do public -> private
            # the other way round won't be possible since GET and POST
            # to this endpoint for this user will be blocked

            # checkbox for private
            self.assertIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output.data)

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

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_view_issue_commit_access(self, p_send_email, p_ugt):
        """ Test the view_issue endpoint. when a user has commit access on repo """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/issue/1')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path), bare=True)

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')

        # Add user 'foo' with ticket access on repo
        msg = pagure.lib.add_user_to_project(
            self.session,
            repo,
            new_user='foo',
            user='pingou',
            access='commit',
        )
        self.assertEqual(msg, 'User added')
        self.session.commit()

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

        # Add milestone
        repo.milestones = {'77': None}
        self.session.add(repo)
        issue = pagure.lib.search_issues(
            self.session,
            repo=repo,
            issueid=1
        )

        pagure.lib.edit_issue(
            self.session,
            issue,
            pagure.APP.config.get('TICKETS_FOLDER'),
            user='pingou',
            milestone='77'
        )
        self.session.add(repo)
        self.session.add(issue)

        msg = pagure.lib.set_custom_key_fields(
            self.session,
            project=repo,
            fields=['abc', 'xyz'],
            types=['boolean', 'boolean'],
            data=[None, None],
        )
        self.assertEqual(msg, 'List of custom fields updated')
        self.session.add(repo)

        msg = pagure.lib.set_custom_key_value(
            self.session,
            issue=issue,
            key=pagure.lib.get_custom_key(self.session, repo, 'abc'),
            value=1
        )
        self.session.add(issue)
        self.session.commit()


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

            # no edit metadata
            self.assertNotIn(
                '<a class="btn btn-secondary issue-metadata-display'
                ' editmetadatatoggle">',
                output.data)
            self.assertFalse(
                '<a href="/login/">Login</a> to comment on this ticket.'
                in output.data)

            # can view the milestone
            self.assertIn(
                '<label><strong>Milestone</strong></label>',
                output.data)
            self.assertIn(
                '<span >77</span>',
                output.data)
            # but can't edit them
            self.assertNotIn(
                '<select class="form-control c-select" id="milestone" '
                ' name="milestone"><option value=""></option><option '
                'selected value="77">77</option></select>',
                output.data)

            # can view depends on
            self.assertIn(
                '<label><strong>Depends on</strong></label>',
                output.data)

            # can't edit depends on
            self.assertNotIn(
                '<input class="form-control" id="depends" type="text"\n\
                                placeholder="issue depending" name="depends"\n\
                                value="" />',
                output.data)

            # no toggle option for custom fields
            self.assertNotIn(
                '<a class="btn btn-secondary '
                'issue-custom-display edit_custom_toggle">',
                output.data)

            # no checkbox for private
            self.assertNotIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)

            # the user can edit the issue
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '<button class="btn btn-danger btn-sm" type="submit"',
                output.data)

            # the user can delete the ticket
            self.assertIn('title="Delete this ticket">', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # the user can do the following things
            # edit metadata
            self.assertIn(
                '<a class="btn btn-secondary issue-metadata-display'
                ' editmetadatatoggle">',
                output.data)

            # toggle option for custom fields
            self.assertIn(
                '<a class="btn btn-secondary '
                'issue-custom-display edit_custom_toggle">',
                output.data)

            # can view the milestone
            self.assertIn(
                '<label><strong>Milestone</strong></label>',
                output.data)
            self.assertIn(
                '<span >77</span>',
                output.data)

            # can edit them
            self.assertIn(
                '<select class="form-control c-select" id="milestone" '
                'name="milestone"><option value=""></option><option selected '
                'value="77">77</option></select>\n      <div>\n',
                output.data)
            # can view depends on
            self.assertIn(
                '<label><strong>Depends on</strong></label>',
                output.data)

            # can edit depends on
            self.assertIn(
                '<input class="form-control" id="depends" type="text"'
                '\n                placeholder="issue depending" name="depends"\n',
                output.data)

            # the user should be able to do public -> private
            # the other way round won't be possible since GET and POST
            # to this endpoint for this user will be blocked

            # checkbox for private
            self.assertIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output.data)

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

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_view_issue_admin_access(self, p_send_email, p_ugt):
        """ Test the view_issue endpoint. when a user has admin access on repo """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/issue/1')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path), bare=True)

        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')

        # Add user 'foo' with ticket access on repo
        msg = pagure.lib.add_user_to_project(
            self.session,
            repo,
            new_user='foo',
            user='pingou',
            access='admin',
        )
        self.assertEqual(msg, 'User added')
        self.session.commit()

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

        # Add milestone
        repo.milestones = {'77': None}
        self.session.add(repo)
        issue = pagure.lib.search_issues(
            self.session,
            repo=repo,
            issueid=1
        )

        pagure.lib.edit_issue(
            self.session,
            issue,
            pagure.APP.config.get('TICKETS_FOLDER'),
            user='pingou',
            milestone='77'
        )
        self.session.add(repo)
        self.session.add(issue)

        msg = pagure.lib.set_custom_key_fields(
            self.session,
            project=repo,
            fields=['abc', 'xyz'],
            types=['boolean', 'boolean'],
            data=[None, None],
        )
        self.assertEqual(msg, 'List of custom fields updated')
        self.session.add(repo)

        msg = pagure.lib.set_custom_key_value(
            self.session,
            issue=issue,
            key=pagure.lib.get_custom_key(self.session, repo, 'abc'),
            value=1
        )
        self.session.add(issue)
        self.session.commit()


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

            # no edit metadata
            self.assertNotIn(
                '<a class="btn btn-secondary issue-metadata-display'
                ' editmetadatatoggle">',
                output.data)
            self.assertFalse(
                '<a href="/login/">Login</a> to comment on this ticket.'
                in output.data)

            # can view the milestone
            self.assertIn(
                '<label><strong>Milestone</strong></label>',
                output.data)
            self.assertIn(
                '<span >77</span>',
                output.data)
            # but can't edit them
            self.assertNotIn(
                '<select class="form-control c-select" id="milestone" '
                ' name="milestone"><option value=""></option><option '
                'selected value="77">77</option></select>',
                output.data)

            # can view depends on
            self.assertIn(
                '<label><strong>Depends on</strong></label>',
                output.data)

            # can't edit depends on
            self.assertNotIn(
                '<input class="form-control" id="depends" type="text"\n\
                                placeholder="issue depending" name="depends"\n\
                                value="" />',
                output.data)

            # no toggle option for custom fields
            self.assertNotIn(
                '<a class="btn btn-secondary '
                'issue-custom-display edit_custom_toggle">',
                output.data)

            # no checkbox for private
            self.assertNotIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/issue/1')
            self.assertEqual(output.status_code, 200)

            # the user can edit the issue
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)
            self.assertIn(
                '<button class="btn btn-danger btn-sm" type="submit"',
                output.data)

            # the user still can delete the ticket
            self.assertIn('title="Delete this ticket">', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # the user can do the following things
            # edit metadata
            self.assertIn(
                '<a class="btn btn-secondary issue-metadata-display'
                ' editmetadatatoggle">',
                output.data)

            # toggle option for custom fields
            self.assertIn(
                '<a class="btn btn-secondary '
                'issue-custom-display edit_custom_toggle">',
                output.data)

            # can view the milestone
            self.assertIn(
                '<label><strong>Milestone</strong></label>',
                output.data)
            self.assertIn(
                '<span >77</span>',
                output.data)

            # can edit them
            self.assertIn(
                '<select class="form-control c-select" id="milestone" '
                'name="milestone"><option value=""></option><option selected '
                'value="77">77</option></select>\n      <div>\n',
                output.data)

            # can view depends on
            self.assertIn(
                '<label><strong>Depends on</strong></label>',
                output.data)

            # can edit depends on
            self.assertIn(
                '<input class="form-control" id="depends" type="text"'
                '\n                placeholder="issue depending" name="depends"\n',
                output.data)

            # the user should be able to do public -> private
            # the other way round won't be possible since GET and POST
            # to this endpoint for this user will be blocked

            # checkbox for private
            self.assertIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output.data)

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


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskIssuesACLtests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
