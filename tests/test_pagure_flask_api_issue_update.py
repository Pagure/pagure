# -*- coding: utf-8 -*-

"""
 Authors:
   Julen Landa Alustiza <jlanda@fedoraproject.org>
"""

from __future__ import unicode_literals, absolute_import

import datetime
import unittest
import sys
import os
import json

from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query  # noqa: E402
import tests  # noqa: E402


class PagureFlaskApiIssueUpdatetests(tests.Modeltests):
    """Tests for the flask API of pagure for updating an issue"""

    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureFlaskApiIssueUpdatetests, self).setUp()

        pagure.config.config["TICKETS_FOLDER"] = None
        tests.create_projects(self.session)
        tests.create_tokens(self.session)

    def test_api_issue_update_wrong_token(self):
        """Test the api_issue_update method of flask API"""
        tests.create_tokens_acl(self.session)
        headers = {"Authorization": "token aaa"}
        output = self.app.post("/api/0/foo/issue/1", headers=headers)
        self.assertEqual(output.status_code, 401)
        expected_rv = {
            "error": "Invalid or expired token. Please visit "
            "http://localhost.localdomain/settings#nav-api-tab to get or renew "
            "your API token.",
            "error_code": "EINVALIDTOK",
            "errors": "Invalid token",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_issue_update_wrong_project(self):
        """Test the api_issue_update method of flask API"""
        tests.create_tokens_acl(self.session)
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.post("/api/0/foo/issue/1", headers=headers)
        self.assertEqual(output.status_code, 404)
        expected_rv = {
            "error": "Project not found",
            "error_code": "ENOPROJECT",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_issue_update_wrong_acls(self):
        """Test the api_issue_update method of flask API"""
        tests.create_tokens_acl(self.session, acl_name="issue_create")
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.post("/api/0/test/issue/1", headers=headers)
        self.assertEqual(output.status_code, 401)
        expected_rv = {
            "error": "Invalid or expired token. Please visit "
            "http://localhost.localdomain/settings#nav-api-tab to get or renew "
            "your API token.",
            "error_code": "EINVALIDTOK",
            "errors": "Missing ACLs: issue_update",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    @patch.dict("pagure.config.config", {"ENABLE_TICKETS": False})
    def test_api_issue_update_instance_tickets_disabled(self):
        """Test the api_issue_update method of flask API"""
        tests.create_tokens_acl(self.session)
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.post("/api/0/test/issue/1", headers=headers)
        self.assertEqual(output.status_code, 404)
        expected_rv = {
            "error": "Issue tracker disabled",
            "error_code": "ETRACKERDISABLED",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_issue_update_project_tickets_disabled(self):
        """Test the api_issue_update method of flask API"""
        tests.create_tokens_acl(self.session)
        # disable tickets on this repo
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        settings = repo.settings
        settings["issue_tracker"] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.post("/api/0/test/issue/1", headers=headers)
        self.assertEqual(output.status_code, 404)
        expected_rv = {
            "error": "Issue tracker disabled",
            "error_code": "ETRACKERDISABLED",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_issue_update_project_read_only_issue_tracker(self):
        """Test the api_issue_update method of flask API"""
        tests.create_tokens_acl(self.session)
        # set read only issue tracke on this repo
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        settings = repo.settings
        settings["issue_tracker_read_only"] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.post("/api/0/test/issue/1", headers=headers)
        self.assertEqual(output.status_code, 401)
        expected_rv = {
            "error": "The issue tracker of this project is read-only",
            "error_code": "ETRACKERREADONLY",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_issue_update_wrong_issue(self):
        """Test the api_issue_update method of flask API"""
        tests.create_tokens_acl(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.post("/api/0/test/issue/1", headers=headers)
        self.assertEqual(output.status_code, 404)
        expected_rv = {"error": "Issue not found", "error_code": "ENOISSUE"}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_issue_update_no_input(self):
        """Test the api_issue_update method of flask API"""
        tests.create_tokens_acl(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        headers = {"Authorization": "token aaabbbcccddd"}

        # Create an issue
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
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.post("/api/0/test/issue/1", headers=headers)
        self.assertEqual(output.status_code, 400)
        expected_rv = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {
                "issue_content": ["This field is required."],
                "title": ["This field is required."],
            },
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_issue_update_partial_input(self):
        """Test the api_issue_update method of flask API"""
        tests.create_tokens_acl(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        headers = {"Authorization": "token aaabbbcccddd"}

        # Create an issue
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
        headers = {"Authorization": "token aaabbbcccddd"}
        # missing issue_content
        data = {"title": "New title"}
        output = self.app.post(
            "/api/0/test/issue/1", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        expected_rv = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {"issue_content": ["This field is required."]},
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)
        # missing title
        data = {"issue_content": "New content"}
        output = self.app.post(
            "/api/0/test/issue/1", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        expected_rv = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {"title": ["This field is required."]},
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_issue_update(self):
        """Test the api_issue_update method of flask API"""
        tests.create_tokens_acl(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        headers = {"Authorization": "token aaabbbcccddd"}

        # Create an issue
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
        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"title": "New title", "issue_content": "New content"}
        output = self.app.post(
            "/api/0/test/issue/1", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(data["message"], "Issue edited")
        self.assertEqual(data["issue"]["title"], "New title")
        self.assertEqual(data["issue"]["content"], "New content")
        output = self.app.get("/api/0/test/issue/1", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(data["title"], "New title")
        self.assertEqual(data["content"], "New content")
