# -*- coding: utf-8 -*-

"""
 Authors:
   Julen Landa Alustiza <jlanda@fedoraproject.org>
"""

from __future__ import unicode_literals, absolute_import

import sys
import os

import pagure_messages
from fedora_messaging import api, testing
from mock import ANY, patch

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import tests
import pagure.lib.query
import pygit2


class PagureFlaskPrEditSimpletests(tests.Modeltests):
    def test_pr_edit_no_project(self):
        """ Test the edit pull request endpoint """
        output = self.app.get("/foo/pull-request/1/edit")
        self.assertEqual(output.status_code, 404)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            "<title>Page not found :'( - Pagure</title>", output_text
        )
        self.assertIn("<h2>Page not found (404)</h2>", output_text)

    def test_pr_edit_no_git_repo(self):
        """ Test the edit pull request endpoint """
        tests.create_projects(self.session)
        output = self.app.get("/test/pull-request/1/edit")
        self.assertEqual(output.status_code, 404)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            "<title>Page not found :'( - Pagure</title>", output_text
        )
        self.assertIn("<p>No git repo found</p>", output_text)

    def test_pr_edit_no_pull_requests_no_login(self):
        """ Test the edit pull request endpoint """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        output = self.app.get("/test/pull-request/1/edit")
        self.assertEqual(output.status_code, 302)

    def test_pr_edit_no_pull_requests(self):
        """ Test the edit pull request endpoint """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/pull-request/1/edit")
            self.assertEqual(output.status_code, 404)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Page not found :'( - Pagure</title>", output_text
            )
            self.assertIn("<p>Pull-request not found</p>", output_text)


class PagureFlaskPrEdittests(tests.Modeltests):
    def setUp(self):
        super(PagureFlaskPrEdittests, self).setUp()
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Create foo's fork of pingou's test project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name="test",
            description="test project #1",
            hook_token="aaabbb",
            is_fork=True,
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()
        # Create the fork's git repo
        repo_path = os.path.join(self.path, "repos", item.path)
        pygit2.init_repository(repo_path, bare=True)

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        fork = pagure.lib.query.get_authorized_project(
            self.session, "test", user="foo"
        )
        tests.add_pull_request_git_repo(
            self.path,
            self.session,
            project,
            fork,
            user="foo",
            allow_rebase=True,
        )

        # Create a "main" branch in addition to the default "master" one
        repo_obj = pygit2.Repository(
            os.path.join(self.path, "repos", "test.git")
        )
        repo_obj.branches.local.create("main", repo_obj.head.peel())

    def tearDown(self):
        try:
            tests.clean_pull_requests_path()
        except:
            pass
        super(PagureFlaskPrEdittests, self).tearDown()

    def test_pr_edit_pull_request_unauthenticated(self):
        output = self.app.get("/test/pull-request/1/edit")
        self.assertEqual(output.status_code, 302)

    def test_pr_edit_pull_request_unauthorized(self):
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/pull-request/1/edit")
            self.assertEqual(output.status_code, 403)
            output_text = output.get_data(as_text=True)
            self.assertIn("<title>403 Forbidden</title>", output_text)
            self.assertIn(
                "<p>You are not allowed to edit this pull-request</p>",
                output_text,
            )

    def test_pr_edit_pull_request_view_author(self):
        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/pull-request/1/edit")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Author is editing PR #1
            self.assertIn(
                "<title>Edit PR#1: PR from the feature branch - test - "
                "Pagure</title>",
                output_text,
            )
            # Author has a title input
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control" id="title" name="title" '
                    'required type="text" value="PR from the feature branch">',
                    output_text,
                )
            else:
                self.assertIn(
                    '<input class="form-control" id="title" name="title" '
                    'type="text" value="PR from the feature branch">',
                    output_text,
                )
            # Author has an initial_commit textarea
            self.assertIn(
                '<textarea class="form-control width-100per" '
                'id="initial_comment"\n                    '
                'name="initial_comment"></textarea>',
                output_text,
            )
            # Author has an non-disabled allow_rebase input
            self.assertIn(
                '<input id="allow_rebase" name="allow_rebase" '
                'type="checkbox" value="y" checked>',
                output_text,
            )

    def test_pr_edit_pull_request_post_author_no_csrf_token(self):
        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            data = {
                "title": "New title",
                "initial_comment": "New initial comment",
                "branch_to": "master",
                "allow_rebase": False,
            }
            output = self.app.post(
                "/test/pull-request/1/edit", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Without CSRF token, we finish again on the form with new
            # values.
            self.assertIn(
                "<title>Edit PR#1: PR from the feature branch - test - "
                "Pagure</title>",
                output_text,
            )
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control" id="title" name="title" '
                    'required type="text" value="New title">',
                    output_text,
                )
            else:
                self.assertIn(
                    '<input class="form-control" id="title" name="title" '
                    'type="text" value="New title">',
                    output_text,
                )
            self.assertIn(
                '<textarea class="form-control width-100per" '
                'id="initial_comment"\n                    '
                'name="initial_comment">New initial comment</textarea>',
                output_text,
            )
            self.assertIn(
                '<input id="allow_rebase" name="allow_rebase" type="checkbox"'
                ' value="y" checked>',
                output_text,
            )
            request = pagure.lib.query.search_pull_requests(
                self.session, project_id=1, requestid=1
            )
            # DB model has not been changed
            self.assertEqual("PR from the feature branch", request.title)
            self.assertEqual(None, request.initial_comment)
            self.assertEqual(True, request.allow_rebase)

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    def test_pr_edit_pull_request_post_author(self):
        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            data = {
                "title": "New title",
                "initial_comment": "New initial comment",
                "allow_rebase": False,
                "branch_to": "master",
                "csrf_token": self.get_csrf(),
            }
            with testing.mock_sends(
                pagure_messages.PullRequestInitialCommentEditedV1(
                    topic="pagure.pull-request.initial_comment.edited",
                    body={
                        "pullrequest": {
                            "id": 1,
                            "uid": ANY,
                            "title": "New title",
                            "full_url": "http://localhost.localdomain/test/pull-request/1",
                            "branch": "master",
                            "project": {
                                "id": 1,
                                "name": "test",
                                "fullname": "test",
                                "url_path": "test",
                                "full_url": "http://localhost.localdomain/test",
                                "description": "test project #1",
                                "namespace": None,
                                "parent": None,
                                "date_created": ANY,
                                "date_modified": ANY,
                                "user": {
                                    "name": "pingou",
                                    "fullname": "PY C",
                                    "url_path": "user/pingou",
                                    "full_url": "http://localhost.localdomain/user/pingou",
                                },
                                "access_users": {
                                    "owner": ["pingou"],
                                    "admin": [],
                                    "commit": [],
                                    "collaborator": [],
                                    "ticket": [],
                                },
                                "access_groups": {
                                    "admin": [],
                                    "commit": [],
                                    "collaborator": [],
                                    "ticket": [],
                                },
                                "tags": [],
                                "priorities": {},
                                "custom_keys": [],
                                "close_status": [
                                    "Invalid",
                                    "Insufficient data",
                                    "Fixed",
                                    "Duplicate",
                                ],
                                "milestones": {},
                            },
                            "branch_from": "feature",
                            "repo_from": {
                                "id": 4,
                                "name": "test",
                                "fullname": "forks/foo/test",
                                "url_path": "fork/foo/test",
                                "full_url": "http://localhost.localdomain/fork/foo/test",
                                "description": "test project #1",
                                "namespace": None,
                                "parent": {
                                    "id": 1,
                                    "name": "test",
                                    "fullname": "test",
                                    "url_path": "test",
                                    "description": "test project #1",
                                    "full_url": "http://localhost.localdomain/test",
                                    "namespace": None,
                                    "parent": None,
                                    "date_created": ANY,
                                    "date_modified": ANY,
                                    "user": {
                                        "name": "pingou",
                                        "fullname": "PY C",
                                        "url_path": "user/pingou",
                                        "full_url": "http://localhost.localdomain/user/pingou",
                                    },
                                    "access_users": {
                                        "owner": ["pingou"],
                                        "admin": [],
                                        "commit": [],
                                        "collaborator": [],
                                        "ticket": [],
                                    },
                                    "access_groups": {
                                        "admin": [],
                                        "commit": [],
                                        "collaborator": [],
                                        "ticket": [],
                                    },
                                    "tags": [],
                                    "priorities": {},
                                    "custom_keys": [],
                                    "close_status": [
                                        "Invalid",
                                        "Insufficient data",
                                        "Fixed",
                                        "Duplicate",
                                    ],
                                    "milestones": {},
                                },
                                "date_created": ANY,
                                "date_modified": ANY,
                                "user": {
                                    "name": "foo",
                                    "fullname": "foo bar",
                                    "full_url": "http://localhost.localdomain/user/foo",
                                    "url_path": "user/foo",
                                },
                                "access_users": {
                                    "owner": ["foo"],
                                    "admin": [],
                                    "commit": [],
                                    "collaborator": [],
                                    "ticket": [],
                                },
                                "access_groups": {
                                    "admin": [],
                                    "commit": [],
                                    "collaborator": [],
                                    "ticket": [],
                                },
                                "tags": [],
                                "priorities": {},
                                "custom_keys": [],
                                "close_status": [],
                                "milestones": {},
                            },
                            "remote_git": None,
                            "date_created": ANY,
                            "updated_on": ANY,
                            "last_updated": ANY,
                            "closed_at": None,
                            "user": {
                                "name": "foo",
                                "fullname": "foo bar",
                                "url_path": "user/foo",
                                "full_url": "http://localhost.localdomain/user/foo",
                            },
                            "assignee": None,
                            "status": "Open",
                            "commit_start": None,
                            "commit_stop": None,
                            "closed_by": None,
                            "initial_comment": "New initial comment",
                            "cached_merge_status": "unknown",
                            "threshold_reached": None,
                            "tags": [],
                            "comments": [],
                        },
                        "project": {
                            "id": 1,
                            "name": "test",
                            "fullname": "test",
                            "full_url": "http://localhost.localdomain/test",
                            "url_path": "test",
                            "description": "test project #1",
                            "namespace": None,
                            "parent": None,
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "url_path": "user/pingou",
                                "full_url": "http://localhost.localdomain/user/pingou",
                            },
                            "access_users": {
                                "owner": ["pingou"],
                                "admin": [],
                                "commit": [],
                                "collaborator": [],
                                "ticket": [],
                            },
                            "access_groups": {
                                "admin": [],
                                "commit": [],
                                "collaborator": [],
                                "ticket": [],
                            },
                            "tags": [],
                            "priorities": {},
                            "custom_keys": [],
                            "close_status": [
                                "Invalid",
                                "Insufficient data",
                                "Fixed",
                                "Duplicate",
                            ],
                            "milestones": {},
                        },
                        "agent": "foo",
                    },
                )
            ):
                output = self.app.post(
                    "/test/pull-request/1/edit",
                    data=data,
                    follow_redirects=True,
                )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # After successful edit, we end on pull_request view with new data
            self.assertIn(
                "<title>PR#1: New title - test\n - Pagure</title>", output_text
            )
            self.assertIn(
                '<span class="font-weight-bold">\n'
                "                  New title\n"
                "            </span>",
                output_text,
            )
            self.assertIn("<p>New initial comment</p>", output_text)
            request = pagure.lib.query.search_pull_requests(
                self.session, project_id=1, requestid=1
            )
            # DB model has been changed
            self.assertEqual("New title", request.title)
            self.assertEqual("New initial comment", request.initial_comment)
            self.assertEqual(False, request.allow_rebase)

    def test_pr_edit_pull_request_view_committer(self):
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/pull-request/1/edit")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Committer is editing PR #1
            self.assertIn(
                "<title>Edit PR#1: PR from the feature branch - test - "
                "Pagure</title>",
                output_text,
            )
            # Committer has a title input
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control" id="title" name="title" '
                    'required type="text" value="PR from the feature branch">',
                    output_text,
                )
            else:
                self.assertIn(
                    '<input class="form-control" id="title" name="title" '
                    'type="text" value="PR from the feature branch">',
                    output_text,
                )
            # Committer has an initial_commit textarea
            self.assertIn(
                '<textarea class="form-control width-100per" '
                'id="initial_comment"\n'
                '                    name="initial_comment"></textarea>',
                output_text,
            )
            # Committer has an disabled allow_rebase input
            self.assertIn(
                '<input id="allow_rebase" name="allow_rebase" type="checkbox"'
                ' value="y" checked disabled>',
                output_text,
            )

    def test_pr_edit_pull_request_post_committer(self):
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {
                "title": "New title",
                "initial_comment": "New initial comment",
                "allow_rebase": False,
                "branch_to": "master",
                "csrf_token": self.get_csrf(),
            }
            output = self.app.post(
                "/test/pull-request/1/edit", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # After successful edit, we end on pull_request view with new data
            self.assertIn(
                "<title>PR#1: New title - test\n - Pagure</title>", output_text
            )
            self.assertIn(
                '<span class="font-weight-bold">\n'
                "                  New title\n"
                "            </span>",
                output_text,
            )
            self.assertIn("<p>New initial comment</p>", output_text)
            request = pagure.lib.query.search_pull_requests(
                self.session, project_id=1, requestid=1
            )
            # DB model has been changed
            self.assertEqual("New title", request.title)
            self.assertEqual("New initial comment", request.initial_comment)
            # But allow_rebase remains unchanged
            self.assertEqual(True, request.allow_rebase)

    def test_pr_edit_pull_request_invalid_branch_to(self):
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {
                "title": "New title",
                "initial_comment": "New initial comment",
                "allow_rebase": False,
                "branch_to": "invalid",
                "csrf_token": self.get_csrf(),
            }
            output = self.app.post(
                "/test/pull-request/1/edit", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Edit failed - we're back on the same page
            self.assertIn(
                "<title>Edit PR#1: PR from the feature branch - test - Pagure"
                "</title>",
                output_text,
            )
            self.assertIn("Not a valid choice", output_text)
            request = pagure.lib.query.search_pull_requests(
                self.session, project_id=1, requestid=1
            )
            # DB model has not been changed
            self.assertEqual("PR from the feature branch", request.title)
            self.assertEqual(None, request.initial_comment)
            self.assertEqual("master", request.branch)
            # But allow_rebase remains unchanged
            self.assertEqual(True, request.allow_rebase)

    def test_pr_edit_pull_request_valid_branch_to(self):
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {
                "title": "New title",
                "initial_comment": "New initial comment",
                "allow_rebase": False,
                "branch_to": "main",
                "csrf_token": self.get_csrf(),
            }
            output = self.app.post(
                "/test/pull-request/1/edit", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # After successful edit, we end on pull_request view with new data
            self.assertIn(
                "<title>PR#1: New title - test\n - Pagure</title>", output_text
            )
            self.assertIn(
                '<span class="font-weight-bold">\n'
                "                  New title\n"
                "            </span>",
                output_text,
            )
            self.assertIn("<p>New initial comment</p>", output_text)
            request = pagure.lib.query.search_pull_requests(
                self.session, project_id=1, requestid=1
            )
            # DB model has been changed
            self.assertEqual("New title", request.title)
            self.assertEqual("New initial comment", request.initial_comment)
            self.assertEqual("main", request.branch)
            # But allow_rebase remains unchanged
            self.assertEqual(True, request.allow_rebase)
