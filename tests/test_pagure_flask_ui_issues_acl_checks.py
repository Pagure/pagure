#!/usr/bin/env python
# coding=utf-8

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Vivek Anand <vivekanand1101@gmail.com>

"""

from __future__ import unicode_literals, absolute_import

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
import tempfile

import pygit2
from mock import patch

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.config
import pagure.lib.query
import tests


class PagureFlaskIssuesACLtests(tests.Modeltests):
    """Tests for flask issues controller of pagure for acls"""

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_view_issue_no_access(self, p_send_email, p_ugt):
        """Test the view_issue endpoint. when a user has no access on repo"""
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get("/foo/issue/1")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/issue/1")
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
        )

        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        # Add milestone
        repo.milestones = {"77": None}
        self.session.add(repo)
        issue = pagure.lib.query.search_issues(
            self.session, repo=repo, issueid=1
        )

        pagure.lib.query.edit_issue(
            self.session, issue, user="pingou", milestone="77"
        )
        self.session.add(repo)
        self.session.add(issue)

        msg = pagure.lib.query.set_custom_key_fields(
            self.session,
            project=repo,
            fields=["abc", "xyz"],
            types=["boolean", "boolean"],
            data=[None, None],
        )
        self.assertEqual(msg, "List of custom fields updated")
        self.session.add(repo)

        msg = pagure.lib.query.set_custom_key_value(
            self.session,
            issue=issue,
            key=pagure.lib.query.get_custom_key(self.session, repo, "abc"),
            value=1,
        )
        self.session.add(issue)
        self.session.commit()

        output = self.app.get("/test/issue/1")
        self.assertEqual(output.status_code, 200)
        # Not authentified = No edit
        self.assertNotIn(
            '<a class="btn btn-outline-secondary btn-sm border-0" '
            'href="/test/issue/1/edit" title="Edit this issue">\n',
            output.get_data(as_text=True),
        )
        self.assertTrue(
            '<a href="/login/?next=http%3A%2F%2Flocalhost%2Ftest%2Fissue%2F1">'
            "Log in</a>\n          to comment on this ticket."
            in output.get_data(as_text=True)
        )

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Not author nor admin = No edit
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">\n',
                output_text,
            )
            self.assertNotIn(
                '<a class="dropdown-item text-danger pointer" id="closeticket"\n'
                '                title="Delete this ticket">\n',
                output.get_data(as_text=True),
            )

            # no edit metadata
            self.assertNotIn(
                '<a class="btn btn-outline-primary border-0 btn-sm issue-metadata-display'
                ' editmetadatatoggle pointer inline-block"">'
                '<i class="fa fa-fw fa-pencil">',
                output_text,
            )
            self.assertNotIn(
                '<a href="/login/">Log in</a> to comment on this ticket.',
                output_text,
            )

            # can view the milestone
            self.assertIn("<strong>Milestone</strong>", output_text)
            self.assertIn(
                '\n                <a href="/test/roadmap/77/">'
                "\n                  77\n",
                output_text,
            )
            # but can't edit them
            self.assertNotIn(
                '<select class="form-control c-select" id="milestone" '
                ' name="milestone"><option value=""></option><option '
                'selected value="77">77</option></select>',
                output_text,
            )

            # can view depending
            self.assertIn(
                "<strong>Depending on</strong>", output.get_data(as_text=True)
            )

            # can't edit depending on
            self.assertNotIn(
                '<input class="form-control" id="depending" type="text"\n\
                                placeholder="issue depending" name="depending"\n\
                                value="" />',
                output_text,
            )

            # no checkbox for private
            self.assertNotIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output_text,
            )

        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">\n',
                output_text,
            )
            self.assertNotIn(
                '<a class="dropdown-item text-danger pointer" id="closeticket"\n'
                '                title="Delete this ticket">\n',
                output_text,
            )

            csrf_token = self.get_csrf(output=output)

            # no edit metadata
            self.assertNotIn(
                '<a class="btn btn-outline-primary border-0 btn-sm issue-metadata-display'
                ' editmetadatatoggle pointer inline-block">'
                '<i class="fa fa-fw fa-pencil">',
                output_text,
            )
            self.assertNotIn(
                '<a href="/login/">Log in</a> to comment on this ticket.',
                output_text,
            )

            # can't see the custom field as a checkbox
            self.assertNotIn(
                '<input type="checkbox"                   '
                'class="form-control" name="abc" id="abc"checked/>',
                output_text,
            )

            # can view the milestone
            self.assertIn(
                "<strong>Milestone</strong>", output.get_data(as_text=True)
            )
            self.assertIn(
                '<a href="/test/roadmap/77/">\n                  77',
                output.get_data(as_text=True),
            )

            # but can't edit them
            self.assertNotIn(
                '<select class="form-control c-select" id="milestone" '
                ' name="milestone"><option value=""></option><option '
                'selected value="77">77</option></select>',
                output_text,
            )

            # can view depending
            self.assertIn("<strong>Depending on</strong>", output_text)

            # can't edit depending on
            self.assertNotIn(
                '<input class="form-control" id="depending" type="text"\n\
                                placeholder="issue depending" name="depending"\n\
                                value="" />',
                output_text,
            )

            # no checkbox for private
            self.assertNotIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output_text,
            )

        # Create private issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        # Not logged in
        output = self.app.get("/test/issue/2")
        self.assertEqual(output.status_code, 404)

        # Wrong user
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/2")
            self.assertEqual(output.status_code, 404)

        # reporter
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/2")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #2: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<span title="Private ticket" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/2/edit" title="Edit this issue">\n',
                output_text,
            )

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_view_issue_ticket_access(self, p_send_email, p_ugt):
        """Test the view_issue endpoint. when a user has ticket access on repo"""
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get("/foo/issue/1")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/issue/1")
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Add user 'foo' with ticket access on repo
        msg = pagure.lib.query.add_user_to_project(
            self.session, repo, new_user="foo", user="pingou", access="ticket"
        )
        self.assertEqual(msg, "User added")
        self.session.commit()

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
        )

        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        # Add milestone
        repo.milestones = {"77": None}
        self.session.add(repo)
        issue = pagure.lib.query.search_issues(
            self.session, repo=repo, issueid=1
        )

        pagure.lib.query.edit_issue(
            self.session, issue, user="pingou", milestone="77"
        )
        self.session.add(repo)
        self.session.add(issue)

        msg = pagure.lib.query.set_custom_key_fields(
            self.session,
            project=repo,
            fields=["abc", "xyz"],
            types=["boolean", "boolean"],
            data=[None, None],
        )
        self.assertEqual(msg, "List of custom fields updated")
        self.session.add(repo)

        msg = pagure.lib.query.set_custom_key_value(
            self.session,
            issue=issue,
            key=pagure.lib.query.get_custom_key(self.session, repo, "abc"),
            value=1,
        )
        self.session.add(issue)
        self.session.commit()

        output = self.app.get("/test/issue/1")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        # Not authentified = No edit
        self.assertNotIn(
            '<a class="btn btn-outline-secondary btn-sm border-0" '
            'href="/test/issue/1/edit" title="Edit this issue">\n',
            output_text,
        )
        self.assertTrue(
            '<a href="/login/?next=http%3A%2F%2Flocalhost%2Ftest%2Fissue%2F1">'
            "Log in</a>\n          to comment on this ticket.",
            output_text,
        )

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Not author nor admin = No edit
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">\n',
                output_text,
            )
            self.assertNotIn(
                '<a class="dropdown-item text-danger pointer" id="closeticket"\n'
                '                title="Delete this ticket">\n',
                output_text,
            )

            # no edit metadata
            self.assertNotIn(
                '<a class="btn btn-outline-primary border-0 btn-sm issue-metadata-display'
                ' editmetadatatoggle pointer inline-block">'
                '<i class="fa fa-fw fa-pencil">',
                output_text,
            )
            self.assertNotIn(
                '<a href="/login/">Log in</a> to comment on this ticket.',
                output_text,
            )

            # can view the milestone
            self.assertIn("<strong>Milestone</strong>", output_text)
            self.assertIn(
                '<a href="/test/roadmap/77/">\n                  77',
                output_text,
            )
            # but can't edit them
            self.assertNotIn(
                '<select class="form-control c-select" id="milestone" '
                ' name="milestone"><option value=""></option><option '
                'selected value="77">77</option></select>',
                output_text,
            )

            # can view depending
            self.assertIn("<strong>Depending on</strong>", output_text)

            # can't edit depending on
            self.assertNotIn(
                '<input class="form-control" id="depending" type="text"\n\
                                placeholder="issue depending" name="depending"\n\
                                value="" />',
                output_text,
            )

            # no checkbox for private
            self.assertNotIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output_text,
            )

        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)

            # the user can't edit the issue
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">\n',
                output_text,
            )

            # the user still can't delete the ticket
            self.assertNotIn(
                '<a class="dropdown-item text-danger pointer" id="closeticket"\n'
                '                title="Delete this ticket">\n',
                output_text,
            )

            csrf_token = self.get_csrf(output=output)

            # the user can do the following things
            # edit metadata
            self.assertIn(
                '<a class="btn btn-outline-primary border-0 btn-sm '
                "issue-metadata-display editmetadatatoggle pointer inline-block"
                '"><i class="fa fa-fw fa-pencil"></i></a>',
                output_text,
            )

            # can view the milestone
            self.assertIn("<strong>Milestone</strong>", output_text)
            self.assertIn(
                '<a href="/test/roadmap/77/">\n                  77',
                output_text,
            )

            # can edit them
            self.assertIn(
                '<select class="form-control c-select" id="milestone" '
                'name="milestone"><option value=""></option><option selected '
                'value="77">77</option></select>\n      <div>\n',
                output_text,
            )

            # can view depending
            self.assertIn("<strong>Depending on</strong>", output_text)

            # can edit depending on
            self.assertIn(
                '<input class="form-control" id="depending" type="text"'
                '\n                placeholder="issue depending" name="depending"\n',
                output_text,
            )

            # the user should be able to do public -> private
            # the other way round won't be possible since GET and POST
            # to this endpoint for this user will be blocked

            # checkbox for private
            self.assertIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output_text,
            )

        # Create private issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        # Not logged in
        output = self.app.get("/test/issue/2")
        self.assertEqual(output.status_code, 404)

        # Wrong user
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/2")
            self.assertEqual(output.status_code, 404)

        # reporter
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/2")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #2: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<span title="Private ticket" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/2/edit" title="Edit this issue">\n',
                output_text,
            )

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_view_issue_commit_access(self, p_send_email, p_ugt):
        """Test the view_issue endpoint. when a user has commit access on repo"""
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get("/foo/issue/1")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/issue/1")
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Add user 'foo' with ticket access on repo
        msg = pagure.lib.query.add_user_to_project(
            self.session, repo, new_user="foo", user="pingou", access="commit"
        )
        self.assertEqual(msg, "User added")
        self.session.commit()

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
        )

        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        # Add milestone
        repo.milestones = {"77": None}
        self.session.add(repo)
        issue = pagure.lib.query.search_issues(
            self.session, repo=repo, issueid=1
        )

        pagure.lib.query.edit_issue(
            self.session, issue, user="pingou", milestone="77"
        )
        self.session.add(repo)
        self.session.add(issue)

        msg = pagure.lib.query.set_custom_key_fields(
            self.session,
            project=repo,
            fields=["abc", "xyz"],
            types=["boolean", "boolean"],
            data=[None, None],
        )
        self.assertEqual(msg, "List of custom fields updated")
        self.session.add(repo)

        msg = pagure.lib.query.set_custom_key_value(
            self.session,
            issue=issue,
            key=pagure.lib.query.get_custom_key(self.session, repo, "abc"),
            value=1,
        )
        self.session.add(issue)
        self.session.commit()

        output = self.app.get("/test/issue/1")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        # Not authentified = No edit
        self.assertNotIn(
            '<a class="btn btn-outline-secondary btn-sm border-0" '
            'href="/test/issue/1/edit" title="Edit this issue">\n',
            output_text,
        )
        self.assertTrue(
            '<a href="/login/?next=http%3A%2F%2Flocalhost%2Ftest%2Fissue%2F1">'
            "Log in</a>\n            to comment on this ticket.",
            output_text,
        )

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Not author nor admin = No edit
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">\n',
                output_text,
            )
            self.assertNotIn(
                '<a class="dropdown-item text-danger pointer" id="closeticket"\n'
                '                title="Delete this ticket">\n',
                output_text,
            )

            # no edit metadata
            self.assertNotIn(
                '<a class="btn btn-outline-primary border-0 btn-sm issue-metadata-display'
                ' editmetadatatoggle pointer inline-block">'
                '<i class="fa fa-fw fa-pencil">',
                output_text,
            )
            self.assertNotIn(
                '<a href="/login/">Log in</a> to comment on this ticket.',
                output_text,
            )

            # can view the milestone
            self.assertIn("<strong>Milestone</strong>", output_text)
            self.assertIn(
                '<a href="/test/roadmap/77/">\n                  77',
                output_text,
            )
            # but can't edit them
            self.assertNotIn(
                '<select class="form-control c-select" id="milestone" '
                ' name="milestone"><option value=""></option><option '
                'selected value="77">77</option></select>',
                output_text,
            )

            # can view depending
            self.assertIn("<strong>Depending on</strong>", output_text)

            # can't edit depending on
            self.assertNotIn(
                '<input class="form-control" id="depending" type="text"\n\
                                placeholder="issue depending" name="depending"\n\
                                value="" />',
                output_text,
            )

            # no checkbox for private
            self.assertNotIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output_text,
            )

        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)

            # the user can edit the issue
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">\n',
                output_text,
            )

            # the user can delete the ticket
            self.assertIn(
                '<a class="dropdown-item text-danger pointer" id="closeticket"\n'
                '                title="Delete this ticket">\n',
                output_text,
            )

            csrf_token = self.get_csrf(output=output)

            # the user can do the following things
            # edit metadata
            self.assertIn(
                '<a class="btn btn-outline-primary border-0 btn-sm '
                "issue-metadata-display editmetadatatoggle pointer inline-block"
                '"><i class="fa fa-fw fa-pencil"></i></a>',
                output_text,
            )

            # can view the milestone
            self.assertIn("<strong>Milestone</strong>", output_text)
            self.assertIn(
                '<a href="/test/roadmap/77/">\n                  77',
                output_text,
            )

            # can edit them
            self.assertIn(
                '<select class="form-control c-select" id="milestone" '
                'name="milestone"><option value=""></option><option selected '
                'value="77">77</option></select>\n      <div>\n',
                output_text,
            )
            # can view depending
            self.assertIn("<strong>Depending on</strong>", output_text)

            # can edit depending on
            self.assertIn(
                '<input class="form-control" id="depending" type="text"'
                '\n                placeholder="issue depending" name="depending"\n',
                output_text,
            )

            # the user should be able to do public -> private
            # the other way round won't be possible since GET and POST
            # to this endpoint for this user will be blocked

            # checkbox for private
            self.assertIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output_text,
            )

        # Create private issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        # Not logged in
        output = self.app.get("/test/issue/2")
        self.assertEqual(output.status_code, 404)

        # Wrong user
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/2")
            self.assertEqual(output.status_code, 404)

        # reporter
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/2")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #2: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<span title="Private ticket" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/2/edit" title="Edit this issue">\n',
                output_text,
            )

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_view_issue_admin_access(self, p_send_email, p_ugt):
        """Test the view_issue endpoint. when a user has admin access on repo"""
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get("/foo/issue/1")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/issue/1")
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Add user 'foo' with ticket access on repo
        msg = pagure.lib.query.add_user_to_project(
            self.session, repo, new_user="foo", user="pingou", access="admin"
        )
        self.assertEqual(msg, "User added")
        self.session.commit()

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
        )

        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        # Add milestone
        repo.milestones = {"77": None}
        self.session.add(repo)
        issue = pagure.lib.query.search_issues(
            self.session, repo=repo, issueid=1
        )

        pagure.lib.query.edit_issue(
            self.session, issue, user="pingou", milestone="77"
        )
        self.session.add(repo)
        self.session.add(issue)

        msg = pagure.lib.query.set_custom_key_fields(
            self.session,
            project=repo,
            fields=["abc", "xyz"],
            types=["boolean", "boolean"],
            data=[None, None],
        )
        self.assertEqual(msg, "List of custom fields updated")
        self.session.add(repo)

        msg = pagure.lib.query.set_custom_key_value(
            self.session,
            issue=issue,
            key=pagure.lib.query.get_custom_key(self.session, repo, "abc"),
            value=1,
        )
        self.session.add(issue)
        self.session.commit()

        output = self.app.get("/test/issue/1")
        self.assertEqual(output.status_code, 200)
        # Not authentified = No edit
        self.assertNotIn(
            '<a class="btn btn-outline-secondary btn-sm border-0" '
            'href="/test/issue/1/edit" title="Edit this issue">\n',
            output.get_data(as_text=True),
        )
        self.assertTrue(
            '<a href="/login/?next=http%3A%2F%2Flocalhost%2Ftest%2Fissue%2F1">'
            "Log in</a>\n          to comment on this ticket."
            in output.get_data(as_text=True)
        )

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Not author nor admin = No edit
            self.assertNotIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">\n',
                output_text,
            )
            self.assertNotIn(
                '<a class="dropdown-item text-danger pointer" id="closeticket"\n'
                '                title="Delete this ticket">\n',
                output_text,
            )

            # no edit metadata
            self.assertNotIn(
                '<a class="btn btn-outline-primary border-0 btn-sm issue-metadata-display'
                ' editmetadatatoggle pointer inline-block">'
                '<i class="fa fa-fw fa-pencil">',
                output_text,
            )
            self.assertNotIn(
                '<a href="/login/">Log in</a> to comment on this ticket.',
                output_text,
            )

            # can view the milestone
            self.assertIn("<strong>Milestone</strong>", output_text)
            self.assertIn(
                '<a href="/test/roadmap/77/">\n                  77',
                output_text,
            )
            # but can't edit them
            self.assertNotIn(
                '<select class="form-control c-select" id="milestone" '
                ' name="milestone"><option value=""></option><option '
                'selected value="77">77</option></select>',
                output_text,
            )

            # can view depending
            self.assertIn("<strong>Depending on</strong>", output_text)

            # can't edit depending on
            self.assertNotIn(
                '<input class="form-control" id="depending" type="text"\n\
                                placeholder="issue depending" name="depending"\n\
                                value="" />',
                output_text,
            )

            # no checkbox for private
            self.assertNotIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output_text,
            )

        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)

            # the user can edit the issue
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">\n',
                output_text,
            )
            self.assertIn(
                '<a class="dropdown-item text-danger pointer" id="closeticket"\n'
                '                title="Delete this ticket">\n',
                output_text,
            )

            csrf_token = self.get_csrf(output=output)

            # the user can do the following things
            # edit metadata

            self.assertIn(
                '<a class="btn btn-outline-primary border-0 btn-sm '
                "issue-metadata-display editmetadatatoggle pointer inline-block"
                '"><i class="fa fa-fw fa-pencil"></i></a>',
                output_text,
            )

            # can view the milestone
            self.assertIn("<strong>Milestone</strong>", output_text)
            self.assertIn(
                '<a href="/test/roadmap/77/">\n                  77',
                output_text,
            )

            # can edit them
            self.assertIn(
                '<select class="form-control c-select" id="milestone" '
                'name="milestone"><option value=""></option><option selected '
                'value="77">77</option></select>\n      <div>\n',
                output_text,
            )

            # can view depending
            self.assertIn("<strong>Depending on</strong>", output_text)

            # can edit depending on
            self.assertIn(
                '<input class="form-control" id="depending" type="text"'
                '\n                placeholder="issue depending" name="depending"\n',
                output_text,
            )

            # the user should be able to do public -> private
            # the other way round won't be possible since GET and POST
            # to this endpoint for this user will be blocked

            # checkbox for private
            self.assertIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output_text,
            )

        # Create private issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        # Not logged in
        output = self.app.get("/test/issue/2")
        self.assertEqual(output.status_code, 404)

        # Wrong user
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/2")
            self.assertEqual(output.status_code, 404)

        # reporter
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/2")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #2: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<span title="Private ticket" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/2/edit" title="Edit this issue">\n',
                output_text,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
