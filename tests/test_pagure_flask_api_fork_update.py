# -*- coding: utf-8 -*-

"""
 (c) 2019 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import arrow
import copy
import datetime
import unittest
import shutil
import sys
import time
import os

import flask
import json
import munch
from mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests


class PagureFlaskApiForkUpdatetests(tests.SimplePagureTest):
    """ Tests for the flask API of pagure for updating a PR """

    maxDiff = None

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiForkUpdatetests, self).setUp()

        tests.create_projects(self.session)
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )

        # Fork
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        task = pagure.lib.query.fork_project(
            session=self.session, user="pingou", repo=project
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {
                "endpoint": "ui_ns.view_repo",
                "repo": "test",
                "namespace": None,
                "username": "pingou",
            },
        )

        tests.add_readme_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test.git")
        )
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        fork = pagure.lib.query.get_authorized_project(
            self.session, "test", user="pingou"
        )

        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=fork,
            branch_from="master",
            repo_to=project,
            branch_to="master",
            title="test pull-request",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "test pull-request")

        # Assert the PR is open
        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(project.requests), 1)
        self.assertEqual(project.requests[0].status, "Open")
        # Check how the PR renders in the API and the UI
        output = self.app.get("/api/0/test/pull-request/1")
        self.assertEqual(output.status_code, 200)
        output = self.app.get("/test/pull-request/1")
        self.assertEqual(output.status_code, 200)

    def test_api_pull_request_update_invalid_project_namespace(self):
        """ Test api_pull_request_update method when the project doesn't exist.
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid token, wrong project
        output = self.app.post(
            "/api/0/somenamespace/test3/pull-request/1", headers=headers
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or expired token. Please visit "
                "http://localhost.localdomain/settings#api-keys to get or renew your "
                "API token.",
                "error_code": "EINVALIDTOK",
            },
        )

    def test_api_pull_request_update_invalid_project(self):
        """ Test api_pull_request_update method when the project doesn't exist.
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        # Invalid project
        output = self.app.post("/api/0/foo/pull-request/1", headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_api_pull_request_update_invalid_project_token(self):
        """ Test api_pull_request_update method when the token doesn't correspond
        to the project.
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid token, wrong project
        output = self.app.post("/api/0/test2/pull-request/1", headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["error", "error_code"])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )

    def test_api_pull_request_update_invalid_pr(self):
        """ Test api_assign_pull_request method when asking for an invalid PR
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        # Invalid PR id
        output = self.app.post("/api/0/test/pull-request/404", headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Pull-Request not found", "error_code": "ENOREQ"}
        )

    def test_api_pull_request_update_no_input(self):
        """ Test api_assign_pull_request method when no input is specified
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        # No input
        output = self.app.post("/api/0/test/pull-request/1", headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"title": ["This field is required."]},
            },
        )

    def test_api_pull_request_update_insufficient_input(self):
        """ Test api_assign_pull_request method when no input is specified
        """

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"initial_comment": "will not work"}

        # Missing the required title field
        output = self.app.post(
            "/api/0/test/pull-request/1", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"title": ["This field is required."]},
            },
        )

    def test_api_pull_request_update_edited(self):
        """ Test api_assign_pull_request method when with valid input
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "title": "edited test PR",
            "initial_comment": "Edited initial comment",
        }

        # Valid request
        output = self.app.post(
            "/api/0/test/pull-request/1", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        # Hard-code all the values that will change from a test to another
        # because either random or time-based
        data["date_created"] = "1551276260"
        data["last_updated"] = "1551276261"
        data["updated_on"] = "1551276260"
        data["commit_start"] = "5f5d609db65d447f77ba00e25afd17ba5053344b"
        data["commit_stop"] = "5f5d609db65d447f77ba00e25afd17ba5053344b"
        data["project"]["date_created"] = "1551276259"
        data["project"]["date_modified"] = "1551276259"
        data["repo_from"]["date_created"] = "1551276259"
        data["repo_from"]["date_modified"] = "1551276259"
        data["repo_from"]["parent"]["date_created"] = "1551276259"
        data["repo_from"]["parent"]["date_modified"] = "1551276259"
        data["uid"] = "a2bddecc8ea548e88c22a0df77670092"
        self.assertDictEqual(
            data,
            {
                "assignee": None,
                "branch": "master",
                "branch_from": "master",
                "cached_merge_status": "unknown",
                "closed_at": None,
                "closed_by": None,
                "comments": [],
                "commit_start": "5f5d609db65d447f77ba00e25afd17ba5053344b",
                "commit_stop": "5f5d609db65d447f77ba00e25afd17ba5053344b",
                "date_created": "1551276260",
                "id": 1,
                "initial_comment": "Edited initial comment",
                "last_updated": "1551276261",
                "project": {
                    "access_groups": {"admin": [], "commit": [], "ticket": []},
                    "access_users": {
                        "admin": [],
                        "commit": [],
                        "owner": ["pingou"],
                        "ticket": [],
                    },
                    "close_status": [
                        "Invalid",
                        "Insufficient data",
                        "Fixed",
                        "Duplicate",
                    ],
                    "custom_keys": [],
                    "date_created": "1551276259",
                    "date_modified": "1551276259",
                    "description": "test project #1",
                    "fullname": "test",
                    "id": 1,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "url_path": "test",
                    "user": {"fullname": "PY C", "name": "pingou"},
                },
                "remote_git": None,
                "repo_from": {
                    "access_groups": {"admin": [], "commit": [], "ticket": []},
                    "access_users": {
                        "admin": [],
                        "commit": [],
                        "owner": ["pingou"],
                        "ticket": [],
                    },
                    "close_status": [],
                    "custom_keys": [],
                    "date_created": "1551276259",
                    "date_modified": "1551276259",
                    "description": "test project #1",
                    "fullname": "forks/pingou/test",
                    "id": 4,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": {
                        "access_groups": {
                            "admin": [],
                            "commit": [],
                            "ticket": [],
                        },
                        "access_users": {
                            "admin": [],
                            "commit": [],
                            "owner": ["pingou"],
                            "ticket": [],
                        },
                        "close_status": [
                            "Invalid",
                            "Insufficient data",
                            "Fixed",
                            "Duplicate",
                        ],
                        "custom_keys": [],
                        "date_created": "1551276259",
                        "date_modified": "1551276259",
                        "description": "test project #1",
                        "fullname": "test",
                        "id": 1,
                        "milestones": {},
                        "name": "test",
                        "namespace": None,
                        "parent": None,
                        "priorities": {},
                        "tags": [],
                        "url_path": "test",
                        "user": {"fullname": "PY C", "name": "pingou"},
                    },
                    "priorities": {},
                    "tags": [],
                    "url_path": "fork/pingou/test",
                    "user": {"fullname": "PY C", "name": "pingou"},
                },
                "status": "Open",
                "tags": [],
                "threshold_reached": None,
                "title": "edited test PR",
                "uid": "a2bddecc8ea548e88c22a0df77670092",
                "updated_on": "1551276260",
                "user": {"fullname": "PY C", "name": "pingou"},
            },
        )

    def test_api_pull_request_update_edited_no_comment(self):
        """ Test api_assign_pull_request method when with valid input
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        data = {"title": "edited test PR"}

        # Valid request
        output = self.app.post(
            "/api/0/test/pull-request/1", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        # Hard-code all the values that will change from a test to another
        # because either random or time-based
        data["date_created"] = "1551276260"
        data["last_updated"] = "1551276261"
        data["updated_on"] = "1551276260"
        data["commit_start"] = "5f5d609db65d447f77ba00e25afd17ba5053344b"
        data["commit_stop"] = "5f5d609db65d447f77ba00e25afd17ba5053344b"
        data["project"]["date_created"] = "1551276259"
        data["project"]["date_modified"] = "1551276259"
        data["repo_from"]["date_created"] = "1551276259"
        data["repo_from"]["date_modified"] = "1551276259"
        data["repo_from"]["parent"]["date_created"] = "1551276259"
        data["repo_from"]["parent"]["date_modified"] = "1551276259"
        data["uid"] = "a2bddecc8ea548e88c22a0df77670092"
        self.assertDictEqual(
            data,
            {
                "assignee": None,
                "branch": "master",
                "branch_from": "master",
                "cached_merge_status": "unknown",
                "closed_at": None,
                "closed_by": None,
                "comments": [],
                "commit_start": "5f5d609db65d447f77ba00e25afd17ba5053344b",
                "commit_stop": "5f5d609db65d447f77ba00e25afd17ba5053344b",
                "date_created": "1551276260",
                "id": 1,
                "initial_comment": "",
                "last_updated": "1551276261",
                "project": {
                    "access_groups": {"admin": [], "commit": [], "ticket": []},
                    "access_users": {
                        "admin": [],
                        "commit": [],
                        "owner": ["pingou"],
                        "ticket": [],
                    },
                    "close_status": [
                        "Invalid",
                        "Insufficient data",
                        "Fixed",
                        "Duplicate",
                    ],
                    "custom_keys": [],
                    "date_created": "1551276259",
                    "date_modified": "1551276259",
                    "description": "test project #1",
                    "fullname": "test",
                    "id": 1,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "url_path": "test",
                    "user": {"fullname": "PY C", "name": "pingou"},
                },
                "remote_git": None,
                "repo_from": {
                    "access_groups": {"admin": [], "commit": [], "ticket": []},
                    "access_users": {
                        "admin": [],
                        "commit": [],
                        "owner": ["pingou"],
                        "ticket": [],
                    },
                    "close_status": [],
                    "custom_keys": [],
                    "date_created": "1551276259",
                    "date_modified": "1551276259",
                    "description": "test project #1",
                    "fullname": "forks/pingou/test",
                    "id": 4,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": {
                        "access_groups": {
                            "admin": [],
                            "commit": [],
                            "ticket": [],
                        },
                        "access_users": {
                            "admin": [],
                            "commit": [],
                            "owner": ["pingou"],
                            "ticket": [],
                        },
                        "close_status": [
                            "Invalid",
                            "Insufficient data",
                            "Fixed",
                            "Duplicate",
                        ],
                        "custom_keys": [],
                        "date_created": "1551276259",
                        "date_modified": "1551276259",
                        "description": "test project #1",
                        "fullname": "test",
                        "id": 1,
                        "milestones": {},
                        "name": "test",
                        "namespace": None,
                        "parent": None,
                        "priorities": {},
                        "tags": [],
                        "url_path": "test",
                        "user": {"fullname": "PY C", "name": "pingou"},
                    },
                    "priorities": {},
                    "tags": [],
                    "url_path": "fork/pingou/test",
                    "user": {"fullname": "PY C", "name": "pingou"},
                },
                "status": "Open",
                "tags": [],
                "threshold_reached": None,
                "title": "edited test PR",
                "uid": "a2bddecc8ea548e88c22a0df77670092",
                "updated_on": "1551276260",
                "user": {"fullname": "PY C", "name": "pingou"},
            },
        )

    def test_api_pull_request_update_edited_linked(self):
        """ Test api_assign_pull_request method when with valid input
        """
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(project.requests), 1)
        self.assertEqual(len(project.requests[0].related_issues), 0)
        self.assertEqual(len(project.issues), 0)

        # Create issues to link to
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=project,
            title="tést íssüé",
            content="We should work on this",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(msg.title, "tést íssüé")

        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "title": "edited test PR",
            "initial_comment": "Edited initial comment\n\n"
            "this PR fixes #2 \n\nThanks",
        }

        # Valid request
        output = self.app.post(
            "/api/0/test/pull-request/1", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        # Hard-code all the values that will change from a test to another
        # because either random or time-based
        data["date_created"] = "1551276260"
        data["last_updated"] = "1551276261"
        data["updated_on"] = "1551276260"
        data["commit_start"] = "5f5d609db65d447f77ba00e25afd17ba5053344b"
        data["commit_stop"] = "5f5d609db65d447f77ba00e25afd17ba5053344b"
        data["project"]["date_created"] = "1551276259"
        data["project"]["date_modified"] = "1551276259"
        data["repo_from"]["date_created"] = "1551276259"
        data["repo_from"]["date_modified"] = "1551276259"
        data["repo_from"]["parent"]["date_created"] = "1551276259"
        data["repo_from"]["parent"]["date_modified"] = "1551276259"
        data["uid"] = "a2bddecc8ea548e88c22a0df77670092"
        self.assertDictEqual(
            data,
            {
                "assignee": None,
                "branch": "master",
                "branch_from": "master",
                "cached_merge_status": "unknown",
                "closed_at": None,
                "closed_by": None,
                "comments": [],
                "commit_start": "5f5d609db65d447f77ba00e25afd17ba5053344b",
                "commit_stop": "5f5d609db65d447f77ba00e25afd17ba5053344b",
                "date_created": "1551276260",
                "id": 1,
                "initial_comment": "Edited initial comment\n\nthis PR "
                "fixes #2 \n\nThanks",
                "last_updated": "1551276261",
                "project": {
                    "access_groups": {"admin": [], "commit": [], "ticket": []},
                    "access_users": {
                        "admin": [],
                        "commit": [],
                        "owner": ["pingou"],
                        "ticket": [],
                    },
                    "close_status": [
                        "Invalid",
                        "Insufficient data",
                        "Fixed",
                        "Duplicate",
                    ],
                    "custom_keys": [],
                    "date_created": "1551276259",
                    "date_modified": "1551276259",
                    "description": "test project #1",
                    "fullname": "test",
                    "id": 1,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "url_path": "test",
                    "user": {"fullname": "PY C", "name": "pingou"},
                },
                "remote_git": None,
                "repo_from": {
                    "access_groups": {"admin": [], "commit": [], "ticket": []},
                    "access_users": {
                        "admin": [],
                        "commit": [],
                        "owner": ["pingou"],
                        "ticket": [],
                    },
                    "close_status": [],
                    "custom_keys": [],
                    "date_created": "1551276259",
                    "date_modified": "1551276259",
                    "description": "test project #1",
                    "fullname": "forks/pingou/test",
                    "id": 4,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": {
                        "access_groups": {
                            "admin": [],
                            "commit": [],
                            "ticket": [],
                        },
                        "access_users": {
                            "admin": [],
                            "commit": [],
                            "owner": ["pingou"],
                            "ticket": [],
                        },
                        "close_status": [
                            "Invalid",
                            "Insufficient data",
                            "Fixed",
                            "Duplicate",
                        ],
                        "custom_keys": [],
                        "date_created": "1551276259",
                        "date_modified": "1551276259",
                        "description": "test project #1",
                        "fullname": "test",
                        "id": 1,
                        "milestones": {},
                        "name": "test",
                        "namespace": None,
                        "parent": None,
                        "priorities": {},
                        "tags": [],
                        "url_path": "test",
                        "user": {"fullname": "PY C", "name": "pingou"},
                    },
                    "priorities": {},
                    "tags": [],
                    "url_path": "fork/pingou/test",
                    "user": {"fullname": "PY C", "name": "pingou"},
                },
                "status": "Open",
                "tags": [],
                "threshold_reached": None,
                "title": "edited test PR",
                "uid": "a2bddecc8ea548e88c22a0df77670092",
                "updated_on": "1551276260",
                "user": {"fullname": "PY C", "name": "pingou"},
            },
        )

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(project.requests), 1)
        self.assertEqual(len(project.requests[0].related_issues), 1)
        self.assertEqual(len(project.issues), 1)
        self.assertEqual(len(project.issues[0].related_prs), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
