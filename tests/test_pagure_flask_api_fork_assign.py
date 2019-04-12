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


class PagureFlaskApiForkAssigntests(tests.SimplePagureTest):
    """ Tests for the flask API of pagure for assigning a PR """

    maxDiff = None

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiForkAssigntests, self).setUp()

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

    def test_api_assign_pr_invalid_project_namespace(self):
        """ Test api_pull_request_assign method when the project doesn't exist.
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid token, wrong project
        output = self.app.post(
            "/api/0/somenamespace/test3/pull-request/1/assign", headers=headers
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

    def test_api_assign_pr_invalid_project(self):
        """ Test api_pull_request_assign method when the project doesn't exist.
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        # Invalid project
        output = self.app.post(
            "/api/0/foo/pull-request/1/assign", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_api_assign_pr_invalid_project_token(self):
        """ Test api_pull_request_assign method when the token doesn't correspond
        to the project.
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid token, wrong project
        output = self.app.post(
            "/api/0/test2/pull-request/1/assign", headers=headers
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["error", "error_code"])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )

    def test_api_assign_pr_invalid_pr(self):
        """ Test api_pull_request_assign method when asking for an invalid PR
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        # No input
        output = self.app.post(
            "/api/0/test/pull-request/404/assign", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Pull-Request not found", "error_code": "ENOREQ"}
        )

    def test_api_assign_pr_no_input(self):
        """ Test api_pull_request_assign method when no input is specified
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        # No input
        output = self.app.post(
            "/api/0/test/pull-request/1/assign", headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Nothing to change"})

    def test_api_assign_pr_assigned(self):
        """ Test api_pull_request_assign method when with valid input
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        data = {"assignee": "pingou"}

        # Valid request
        output = self.app.post(
            "/api/0/test/pull-request/1/assign", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Request assigned"})

    def test_api_assign_pr_unassigned(self):
        """ Test api_pull_request_assign method when unassigning
        """
        self.test_api_assign_pr_assigned()

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {}

        # Un-assign
        output = self.app.post(
            "/api/0/test/pull-request/1/assign", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Request assignee reset"})

    def test_api_assign_pr_unassigned_twice(self):
        """ Test api_pull_request_assign method when unassigning
        """
        self.test_api_assign_pr_unassigned()
        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"assignee": None}

        # Un-assign
        output = self.app.post(
            "/api/0/test/pull-request/1/assign", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Nothing to change"})

    def test_api_assign_pr_unassigned_empty_string(self):
        """ Test api_pull_request_assign method when unassigning with an
        empty string
        """
        self.test_api_assign_pr_assigned()

        headers = {"Authorization": "token aaabbbcccddd"}

        # Un-assign
        data = {"assignee": ""}
        output = self.app.post(
            "/api/0/test/pull-request/1/assign", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Request assignee reset"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
