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


class PagureFlaskApiProjectBlockuserTests(tests.SimplePagureTest):
    """ Tests for the flask API of pagure for assigning a PR """

    maxDiff = None

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectBlockuserTests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        item = pagure.lib.model.Token(
            id="aaabbbcccdddeee",
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30),
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session, token_id="aaabbbcccdddeee")

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(project.block_users, [])
        self.blocked_users = []

        project = pagure.lib.query.get_authorized_project(
            self.session, "test2"
        )
        project.block_users = ["foo"]
        self.session.add(project)
        self.session.commit()

    def tearDown(self):
        """ Tears down the environment at the end of the tests. """
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(project.block_users, self.blocked_users)

        super(PagureFlaskApiProjectBlockuserTests, self).tearDown()

    def test_api_blockuser_no_token(self):
        """ Test api_project_block_user method when no token is provided.
        """

        # No token
        output = self.app.post("/api/0/test/blockuser")
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or expired token. Please visit "
                "http://localhost.localdomain/settings#nav-api-tab to "
                "get or renew your API token.",
                "error_code": "EINVALIDTOK",
                "errors": "Invalid token",
            },
        )

    def test_api_blockuser_invalid_token(self):
        """ Test api_project_block_user method when the token provided is invalid.
        """

        headers = {"Authorization": "token aaabbbcccd"}

        # Invalid token
        output = self.app.post("/api/0/test/blockuser", headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or expired token. Please visit "
                "http://localhost.localdomain/settings#nav-api-tab to "
                "get or renew your API token.",
                "error_code": "EINVALIDTOK",
                "errors": "Invalid token",
            },
        )

    def test_api_blockuser_no_data(self):
        """ Test api_project_block_user method when no data is provided.
        """

        headers = {"Authorization": "token aaabbbcccddd"}

        # No user blocked
        output = self.app.post("/api/0/test/blockuser", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "User(s) blocked"})

    def test_api_blockuser_invalid_user(self):
        """ Test api_project_block_user method when the data provided includes
        an invalid username.
        """

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"username": ["invalid"]}

        # No user blocked
        output = self.app.post(
            "/api/0/test/blockuser", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": 'No user "invalid" found', "error_code": "ENOCODE"}
        )

    def test_api_blockuser_insufficient_rights(self):
        """ Test api_project_block_user method when the user doing the action
        does not have admin priviledges.
        """

        headers = {"Authorization": "token aaabbbcccdddeee"}
        data = {"username": ["invalid"]}

        # No user blocked
        output = self.app.post(
            "/api/0/test/blockuser", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "You do not have sufficient permissions to perform "
                "this action",
                "error_code": "ENOTHIGHENOUGH",
            },
        )

    def test_api_blockuser_with_data(self):
        """ Test api_pull_request_assign method when the project doesn't exist.
        """
        self.blocked_users = ["foo"]

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"username": ["foo"]}

        # user blocked
        output = self.app.post(
            "/api/0/test/blockuser", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "User(s) blocked"})

        # Second request, no changes
        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"username": ["foo"]}

        output = self.app.post(
            "/api/0/test/blockuser", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "User(s) blocked"})

    def test_api_blockeduser_api(self):
        """ Test doing a POST request to the API when the user is blocked.
        """
        self.blocked_users = ["pingou"]

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"username": ["pingou"]}

        # user blocked
        output = self.app.post(
            "/api/0/test/blockuser", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "User(s) blocked"})

        # Second request, but user is blocked
        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"username": ["foo"]}

        output = self.app.post(
            "/api/0/test/blockuser", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "You have been blocked from this project",
                "error_code": "EUBLOCKED",
            },
        )

    def test_ui_new_issue_user_blocked(self):
        """ Test doing a POST request to the UI when the user is blocked.
        """

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):

            output = self.app.get("/test2/new_issue")
            self.assertEqual(output.status_code, 200)
            self.assertIn("New Issue", output.get_data(as_text=True))

            csrf_token = self.get_csrf(output=output)

            data = {
                "title": "Test issue",
                "issue_content": "We really should improve on this issue",
                "status": "Open",
                "csrf_token": csrf_token,
            }

            output = self.app.post("/test2/new_issue", data=data)
            self.assertEqual(output.status_code, 403)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<p>You have been blocked from this project</p>", output_text
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
