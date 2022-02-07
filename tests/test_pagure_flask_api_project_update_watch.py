# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import copy
import datetime
import unittest
import shutil
import sys
import time
import os

import json
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests


class PagureFlaskApiProjectUpdateWatchTests(tests.Modeltests):
    """Tests for the flask API of pagure for changing the watch status on
    a project via the API
    """

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureFlaskApiProjectUpdateWatchTests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        tests.create_tokens(
            self.session, user_id=1, project_id=None, suffix="_project_less"
        )
        tests.create_tokens_acl(
            self.session,
            token_id="aaabbbcccddd_project_less",
            acl_name="modify_project",
        )

        # Create normal issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #1",
            content="We should work on this",
            user="pingou",
            private=False,
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #1")

        # Create project-less token for user foo
        item = pagure.lib.model.Token(
            id="project-less-foo",
            user_id=1,
            project_id=None,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30),
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session, token_id="project-less-foo")

    def test_api_update_project_watchers_invalid_project(self):
        """Test the api_update_project_watchers method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd"}

        # Invalid project
        output = self.app.post(
            "/api/0/foobar/watchers/update", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_api_change_status_issue_token_not_for_project(self):
        """Test the api_update_project_watchers method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid token, wrong project
        output = self.app.post("/api/0/test2/watchers/update", headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])

    def test_api_update_project_watchers_no_user_watching(self):
        """Test the api_update_project_watchers method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"status": "42"}

        output = self.app.post(
            "/api/0/test/watchers/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
            },
        )

    def test_api_update_project_watchers_no_watch_status(self):
        """Test the api_update_project_watchers method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"watcher": "pingou"}

        output = self.app.post(
            "/api/0/test/watchers/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": 'The watch value of "None" is invalid',
                "error_code": "ENOCODE",
            },
        )

    def test_api_update_project_watchers_invalid_status(self):
        """Test the api_update_project_watchers method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"watcher": "pingou", "status": "42"}

        output = self.app.post(
            "/api/0/test/watchers/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": 'The watch value of "42" is invalid',
                "error_code": "ENOCODE",
            },
        )

    def test_api_update_project_watchers_invalid_user(self):
        """Test the api_update_project_watchers method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"watcher": "example", "status": "2"}

        output = self.app.post(
            "/api/0/test/watchers/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "You are not allowed to modify this project",
                "error_code": "EMODIFYPROJECTNOTALLOWED",
            },
        )

    def test_api_update_project_watchers_other_user(self):
        """Test the api_update_project_watchers method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"watcher": "foo", "status": "2"}

        output = self.app.post(
            "/api/0/test/watchers/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "You are not allowed to modify this project",
                "error_code": "EMODIFYPROJECTNOTALLOWED",
            },
        )

    def test_api_update_project_watchers_all_good(self):
        """Test the api_update_project_watchers method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"watcher": "pingou", "status": 1}

        output = self.app.post(
            "/api/0/test/watchers/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "message": "You are now watching issues and PRs on this project",
                "status": "ok",
            },
        )

    @patch("pagure.utils.is_admin", MagicMock(return_value=True))
    def test_api_update_project_watchers_other_user_admin(self):
        """Test the api_update_project_watchers method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"watcher": "foo", "status": "2"}

        output = self.app.post(
            "/api/0/test/watchers/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "message": "You are now watching commits on this project",
                "status": "ok",
            },
        )

    @patch("pagure.utils.is_admin", MagicMock(return_value=True))
    def test_api_update_project_watchers_set_then_reset(self):
        """Test the api_update_project_watchers method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd_project_less"}
        data = {"watcher": "foo", "status": "2"}

        output = self.app.post(
            "/api/0/test/watchers/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "message": "You are now watching commits on this project",
                "status": "ok",
            },
        )

        data = {"watcher": "foo", "status": "-1"}

        output = self.app.post(
            "/api/0/test/watchers/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {"message": "Watch status reset", "status": "ok"},
        )

    @patch("pagure.utils.is_admin", MagicMock(return_value=True))
    def test_api_update_project_watchers_invalid_user_admin(self):
        """Test the api_update_project_watchers method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"watcher": "example", "status": "2"}

        output = self.app.post(
            "/api/0/test/watchers/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
            },
        )

    @patch("pagure.utils.is_admin", MagicMock(return_value=True))
    def test_api_update_project_watchers_missing_user_admin(self):
        """Test the api_update_project_watchers method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"status": "2"}

        output = self.app.post(
            "/api/0/test/watchers/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
