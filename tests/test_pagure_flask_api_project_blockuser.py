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

    def tearDown(self):
        """ Tears down the environment at the end of the tests. """
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(project.block_users, [])

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
                "http://localhost.localdomain/settings#api-keys to "
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
                "http://localhost.localdomain/settings#api-keys to "
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


class PagureFlaskApiProjectBlockuserFilledTests(tests.SimplePagureTest):
    """ Tests for the flask API of pagure for assigning a PR """

    maxDiff = None

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectBlockuserFilledTests, self).setUp()

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(project.block_users, [])

    def tearDown(self):
        """ Tears down the environment at the end of the tests. """
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(project.block_users, ["foo"])

        super(PagureFlaskApiProjectBlockuserFilledTests, self).tearDown()

    def test_api_blockuser_with_data(self):
        """ Test api_project_block_user method to block users.
        """

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"username": ["foo"]}

        # No user blocked
        output = self.app.post(
            "/api/0/test/blockuser", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "User(s) blocked"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
