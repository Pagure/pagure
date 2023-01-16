# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

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
import pagure_messages
import json
import munch

from fedora_messaging import api, testing
from mock import ANY, patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.config
import pagure.lib.query
import tests

FULL_ISSUE_LIST = [
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "We should work on this",
        "custom_fields": [],
        "full_url": "http://localhost.localdomain/test/issue/2",
        "date_created": "1431414800",
        "depends": [],
        "id": 2,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": True,
        "related_prs": [],
        "status": "Closed",
        "tags": [],
        "title": "Test issue",
        "user": {
            "fullname": "PY C",
            "full_url": "http://localhost.localdomain/user/pingou",
            "name": "pingou",
            "url_path": "user/pingou",
        },
    },
    {
        "assignee": {
            "fullname": "foo bar",
            "full_url": "http://localhost.localdomain/user/foo",
            "name": "foo",
            "url_path": "user/foo",
        },
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "full_url": "http://localhost.localdomain/test/issue/8",
        "date_created": "1431414800",
        "depends": [],
        "id": 8,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": True,
        "related_prs": [],
        "status": "Open",
        "tags": [],
        "title": "test issue1",
        "user": {
            "fullname": "PY C",
            "full_url": "http://localhost.localdomain/user/pingou",
            "name": "pingou",
            "url_path": "user/pingou",
        },
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "full_url": "http://localhost.localdomain/test/issue/7",
        "date_created": "1431414800",
        "depends": [],
        "id": 7,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": True,
        "related_prs": [],
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "full_url": "http://localhost.localdomain/user/pingou",
            "name": "pingou",
            "url_path": "user/pingou",
        },
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "full_url": "http://localhost.localdomain/test/issue/6",
        "date_created": "1431414800",
        "depends": [],
        "id": 6,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": False,
        "related_prs": [],
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "full_url": "http://localhost.localdomain/user/pingou",
            "name": "pingou",
            "url_path": "user/pingou",
        },
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "full_url": "http://localhost.localdomain/test/issue/5",
        "date_created": "1431414800",
        "depends": [],
        "id": 5,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": False,
        "related_prs": [],
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "full_url": "http://localhost.localdomain/user/pingou",
            "name": "pingou",
            "url_path": "user/pingou",
        },
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "full_url": "http://localhost.localdomain/test/issue/4",
        "date_created": "1431414800",
        "depends": [],
        "id": 4,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": False,
        "related_prs": [],
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "full_url": "http://localhost.localdomain/user/pingou",
            "name": "pingou",
            "url_path": "user/pingou",
        },
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "full_url": "http://localhost.localdomain/test/issue/3",
        "date_created": "1431414800",
        "depends": [],
        "id": 3,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": False,
        "related_prs": [],
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "full_url": "http://localhost.localdomain/user/pingou",
            "name": "pingou",
            "url_path": "user/pingou",
        },
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "full_url": "http://localhost.localdomain/test/issue/2",
        "date_created": "1431414800",
        "depends": [],
        "id": 2,
        "last_updated": "1431414800",
        "milestone": "milestone-1.0",
        "priority": None,
        "private": False,
        "related_prs": [],
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "full_url": "http://localhost.localdomain/user/pingou",
            "name": "pingou",
            "url_path": "user/pingou",
        },
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "full_url": "http://localhost.localdomain/test/issue/1",
        "date_created": "1431414800",
        "depends": [],
        "id": 1,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": False,
        "related_prs": [],
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "full_url": "http://localhost.localdomain/user/pingou",
            "name": "pingou",
            "url_path": "user/pingou",
        },
    },
]


LCL_ISSUES = [
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "Description",
        "custom_fields": [],
        "full_url": "http://localhost.localdomain/test/issue/2",
        "date_created": "1431414800",
        "depends": [],
        "id": 2,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": False,
        "related_prs": [],
        "status": "Open",
        "tags": [],
        "title": "Issue #2",
        "user": {
            "fullname": "PY C",
            "full_url": "http://localhost.localdomain/user/pingou",
            "name": "pingou",
            "url_path": "user/pingou",
        },
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "Description",
        "custom_fields": [],
        "full_url": "http://localhost.localdomain/test/issue/1",
        "date_created": "1431414800",
        "depends": [],
        "id": 1,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": False,
        "related_prs": [],
        "status": "Open",
        "tags": [],
        "title": "Issue #1",
        "user": {
            "fullname": "PY C",
            "full_url": "http://localhost.localdomain/user/pingou",
            "name": "pingou",
            "url_path": "user/pingou",
        },
    },
]


class PagureFlaskApiIssuetests(tests.SimplePagureTest):
    """Tests for the flask API of pagure for issue"""

    maxDiff = None

    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureFlaskApiIssuetests, self).setUp()
        pagure.config.config["TICKETS_FOLDER"] = None

    def test_api_new_issue_wrong_token(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid token, wrong project
        output = self.app.post("/api/0/test2/new_issue", headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["error", "error_code"])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )

    @patch.dict(
        "pagure.config.config", {"ENABLE_TICKETS_NAMESPACE": ["foobar"]}
    )
    def test_api_new_issue_wrong_namespace(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid token, wrong project
        output = self.app.post(
            "/api/0/somenamespace/test3/new_issue", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["error", "error_code"])
        self.assertEqual(
            pagure.api.APIERROR.ETRACKERDISABLED.value, data["error"]
        )
        self.assertEqual(
            pagure.api.APIERROR.ETRACKERDISABLED.name, data["error_code"]
        )

    def test_api_new_issue_no_input(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # No input
        output = self.app.post("/api/0/test/new_issue", headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "issue_content": ["This field is required."],
                    "title": ["This field is required."],
                },
            },
        )

    def test_api_new_issue_invalid_repo(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        data = {"title": "test issue"}

        # Invalid repo
        output = self.app.post(
            "/api/0/foo/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_api_new_issue_invalid_request(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Incomplete request
        output = self.app.post(
            "/api/0/test/new_issue", data={}, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "issue_content": ["This field is required."],
                    "title": ["This field is required."],
                },
            },
        )

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    def test_api_new_issue(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
        }

        # Valid request
        with testing.mock_sends(
            pagure_messages.IssueNewV1(
                topic="pagure.issue.new",
                body={
                    "issue": {
                        "id": 1,
                        "title": "test issue",
                        "content": "This issue needs attention",
                        "status": "Open",
                        "close_status": None,
                        "date_created": ANY,
                        "last_updated": ANY,
                        "closed_at": None,
                        "user": {
                            "name": "pingou",
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "fullname": "PY C",
                            "url_path": "user/pingou",
                        },
                        "private": False,
                        "tags": [],
                        "depends": [],
                        "blocks": [],
                        "assignee": None,
                        "priority": None,
                        "milestone": None,
                        "custom_fields": [],
                        "full_url": "http://localhost.localdomain/test/issue/1",
                        "closed_by": None,
                        "related_prs": [],
                        "comments": [],
                    },
                    "project": {
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
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "fullname": "PY C",
                            "url_path": "user/pingou",
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
                    "agent": "pingou",
                },
            )
        ):
            output = self.app.post(
                "/api/0/test/new_issue", data=data, headers=headers
            )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"
        self.assertDictEqual(
            data, {"issue": FULL_ISSUE_LIST[8], "message": "Issue created"}
        )

    def test_api_new_issue_img(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        with open(os.path.join(tests.HERE, "placebo.png"), "rb") as stream:
            data = {
                "title": "test issue",
                "issue_content": "This issue needs attention <!!image>",
                "filestream": stream,
            }

            # Valid request
            output = self.app.post(
                "/api/0/test/new_issue", data=data, headers=headers
            )
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            data["issue"]["date_created"] = "1431414800"
            data["issue"]["last_updated"] = "1431414800"

            issue = copy.deepcopy(FULL_ISSUE_LIST[8])
            issue["id"] = 1
            self.assertIn(
                "_tests_placebo.png)](/test/issue/raw/files/"
                "8a06845923010b27bfd8e7e75acff7badc40d1021b4994e01f5e11ca"
                "40bc3abe",
                data["issue"]["content"],
            )
            data["issue"]["content"] = "This issue needs attention"

            self.assertDictEqual(
                data, {"issue": issue, "message": "Issue created"}
            )

    def test_api_new_issue_invalid_milestone(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid request but invalid milestone
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "milestone": ["milestone-1.0"],
        }
        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {"milestone": ["Not a valid choice"]},
        }
        if self.get_wtforms_version() >= (3, 0):
            expected_output["errors"]["milestone"] = ["Not a valid choice."]
        self.assertDictEqual(data, expected_output)

    def test_api_new_issue_milestone(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Set some milestones
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestones = {"milestone-1.0": "", "milestone-2.0": "Tomorrow!"}
        self.session.add(repo)
        self.session.commit()

        # Valid request with milestone
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "milestone": ["milestone-1.0"],
        }
        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[7])
        issue["id"] = 1
        issue["full_url"] = "http://localhost.localdomain/test/issue/1"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

    def test_api_new_issue_public(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid request, with private='false'
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "private": "false",
        }

        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[6])
        issue["id"] = 1
        issue["full_url"] = "http://localhost.localdomain/test/issue/1"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

        # Valid request, with private=False
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "private": False,
        }

        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[5])
        issue["id"] = 2
        issue["full_url"] = "http://localhost.localdomain/test/issue/2"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

        # Valid request, with private='False'
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "private": "False",
        }

        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[4])
        issue["id"] = 3
        issue["full_url"] = "http://localhost.localdomain/test/issue/3"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

        # Valid request, with private=0
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "private": 0,
        }

        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[3])
        issue["id"] = 4
        issue["full_url"] = "http://localhost.localdomain/test/issue/4"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

    def test_api_new_issue_private(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Private issue: True
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "private": True,
        }
        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[2])
        issue["id"] = 1
        issue["full_url"] = "http://localhost.localdomain/test/issue/1"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

        # Private issue: 1
        data = {
            "title": "test issue1",
            "issue_content": "This issue needs attention",
            "private": 1,
            "assignee": "foo",
        }
        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        exp = copy.deepcopy(FULL_ISSUE_LIST[1])
        exp["id"] = 2
        exp["full_url"] = "http://localhost.localdomain/test/issue/2"

        self.assertDictEqual(data, {"issue": exp, "message": "Issue created"})

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    def test_api_new_issue_private_no_fedora_messaging_notifs(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Private issue: True
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "private": True,
        }
        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[2])
        issue["id"] = 1
        issue["full_url"] = "http://localhost.localdomain/test/issue/1"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

        # Private issue: 1
        data = {
            "title": "test issue1",
            "issue_content": "This issue needs attention",
            "private": 1,
            "assignee": "foo",
        }
        with self.assertRaises(AssertionError) as cm:
            with testing.mock_sends(api.Message()):
                output = self.app.post(
                    "/api/0/test/new_issue", data=data, headers=headers
                )
        self.assertEqual(
            cm.exception.args[0],
            "Expected 1 messages to be sent, but 0 were sent",
        )

    @patch("pagure.utils.check_api_acls", MagicMock(return_value=None))
    def test_api_new_issue_raise_db_error(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
        }

        with self._app.test_request_context("/") as ctx:
            flask.g.session = self.session
            flask.g.fas_user = tests.FakeUser(username="foo")

            with patch(
                "flask.g.session.commit",
                MagicMock(side_effect=SQLAlchemyError("DB error")),
            ):
                output = self.app.post(
                    "/api/0/test/new_issue", data=data, headers=headers
                )
                self.assertEqual(output.status_code, 400)
                data = json.loads(output.get_data(as_text=True))
                self.assertDictEqual(
                    data,
                    {
                        "error": "An error occurred at the database "
                        "level and prevent the action from reaching "
                        "completion",
                        "error_code": "EDBERROR",
                    },
                )

    def test_api_new_issue_user_token_no_input(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid token, invalid request - No input
        output = self.app.post("/api/0/test2/new_issue", headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "issue_content": ["This field is required."],
                    "title": ["This field is required."],
                },
            },
        )

    def test_api_new_issue_user_token_invalid_user(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Another project, still an invalid request - No input
        output = self.app.post("/api/0/test/new_issue", headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "issue_content": ["This field is required."],
                    "title": ["This field is required."],
                },
            },
        )

    def test_api_new_issue_user_token_invalid_repo(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"title": "test issue"}

        # Invalid repo
        output = self.app.post(
            "/api/0/foo/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_api_new_issue_user_token_invalid_request(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        # Incomplete request
        output = self.app.post(
            "/api/0/test/new_issue", data={}, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "issue_content": ["This field is required."],
                    "title": ["This field is required."],
                },
            },
        )

    def test_api_new_issue_user_token(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
        }

        # Valid request
        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        self.assertDictEqual(
            data, {"issue": FULL_ISSUE_LIST[8], "message": "Issue created"}
        )

    def test_api_new_issue_user_token_milestone(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Set some milestones
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestones = {"milestone-1.0": "", "milestone-2.0": "Tomorrow!"}
        self.session.add(repo)
        self.session.commit()

        # Valid request with milestone
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "milestone": ["milestone-1.0"],
        }
        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[7])
        issue["id"] = 1
        issue["full_url"] = "http://localhost.localdomain/test/issue/1"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

    def test_api_new_issue_user_token_public(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid request, with private='false'
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "private": "false",
        }

        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[6])
        issue["id"] = 1
        issue["full_url"] = "http://localhost.localdomain/test/issue/1"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

        # Valid request, with private=False
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "private": False,
        }

        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[5])
        issue["id"] = 2
        issue["full_url"] = "http://localhost.localdomain/test/issue/2"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

        # Valid request, with private='False'
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "private": "False",
        }

        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[4])
        issue["id"] = 3
        issue["full_url"] = "http://localhost.localdomain/test/issue/3"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

        # Valid request, with private=0
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "private": 0,
        }

        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[4])
        issue["id"] = 4
        issue["full_url"] = "http://localhost.localdomain/test/issue/4"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

    def test_api_new_issue_user_token_private(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Private issue: True
        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "private": True,
        }
        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[2])
        issue["id"] = 1
        issue["full_url"] = "http://localhost.localdomain/test/issue/1"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

        # Private issue: 1
        data = {
            "title": "test issue1",
            "issue_content": "This issue needs attention",
            "private": 1,
            "assignee": "foo",
        }
        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        issue = copy.deepcopy(FULL_ISSUE_LIST[1])
        issue["id"] = 2
        issue["full_url"] = "http://localhost.localdomain/test/issue/2"

        self.assertDictEqual(
            data, {"issue": issue, "message": "Issue created"}
        )

        # Private issue: 'true'
        data = {
            "title": "test issue1",
            "issue_content": "This issue needs attention",
            "private": "true",
        }
        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"

        exp = copy.deepcopy(FULL_ISSUE_LIST[1])
        exp["id"] = 3
        exp["full_url"] = "http://localhost.localdomain/test/issue/3"
        exp["assignee"] = None

        self.assertDictEqual(data, {"issue": exp, "message": "Issue created"})

    def test_api_view_issues(self):
        """Test the api_view_issues method of the flask api."""
        self.test_api_new_issue()

        # Invalid repo
        output = self.app.get("/api/0/foo/issues")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

        # List all opened issues
        output = self.app.get("/api/0/test/issues")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [FULL_ISSUE_LIST[8]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
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
            status="Closed",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        # Access issues un-authenticated
        output = self.app.get("/api/0/test/issues")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [FULL_ISSUE_LIST[8]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )
        headers = {"Authorization": "token aaabbbccc"}

        # Access issues authenticated but non-existing token
        output = self.app.get("/api/0/test/issues", headers=headers)
        self.assertEqual(output.status_code, 401)

        # Create a new token for another user
        item = pagure.lib.model.Token(
            id="bar_token",
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30),
        )
        self.session.add(item)
        self.session.commit()

        headers = {"Authorization": "token bar_token"}

        # Access issues authenticated but wrong token
        output = self.app.get("/api/0/test/issues", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [FULL_ISSUE_LIST[8]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

        headers = {"Authorization": "token aaabbbcccddd"}

        # Access issues authenticated correctly
        output = self.app.get("/api/0/test/issues", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [FULL_ISSUE_LIST[8]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )
        headers = {"Authorization": "token aaabbbccc"}

        # Access issues authenticated but non-existing token
        output = self.app.get("/api/0/test/issues", headers=headers)
        self.assertEqual(output.status_code, 401)

        # Create a new token for another user
        item = pagure.lib.model.Token(
            id="bar_token_foo",
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30),
        )
        self.session.add(item)
        self.session.commit()

        headers = {"Authorization": "token bar_token_foo"}

        # Access issues authenticated but wrong token
        output = self.app.get("/api/0/test/issues", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [FULL_ISSUE_LIST[8]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

        headers = {"Authorization": "token aaabbbcccddd"}

        # Access issues authenticated correctly
        output = self.app.get("/api/0/test/issues", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [FULL_ISSUE_LIST[8]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

        # List closed issue
        output = self.app.get(
            "/api/0/test/issues?status=Closed", headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issues"][0]["date_created"] = "1431414800"
        data["issues"][0]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": "Closed",
                    "tags": [],
                },
                "issues": [FULL_ISSUE_LIST[0]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

        # List closed issue
        output = self.app.get(
            "/api/0/test/issues?status=Invalid", headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": "Invalid",
                    "tags": [],
                },
                "issues": [],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 0,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 0,
            },
        )

        # List all issues
        output = self.app.get("/api/0/test/issues?status=All", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["last_updated"] = "1431414800"
            data["issues"][idx]["date_created"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": "All",
                    "tags": [],
                },
                "issues": [FULL_ISSUE_LIST[0], FULL_ISSUE_LIST[8]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 2,
            },
        )

    def test_api_view_issues_user_token(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
        }

        # Create an issue
        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"
        self.assertDictEqual(
            data, {"issue": FULL_ISSUE_LIST[8], "message": "Issue created"}
        )

        # List all opened issues
        output = self.app.get("/api/0/test/issues")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [FULL_ISSUE_LIST[8]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

    def test_api_view_issues_private_user_token(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "title": "test issue",
            "issue_content": "This issue needs attention",
            "private": True,
        }

        # Create an issue
        output = self.app.post(
            "/api/0/test/new_issue", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        lcl_issue = copy.deepcopy(FULL_ISSUE_LIST[8])
        lcl_issue["private"] = True
        data["issue"]["date_created"] = "1431414800"
        data["issue"]["last_updated"] = "1431414800"
        self.assertDictEqual(
            data, {"issue": lcl_issue, "message": "Issue created"}
        )

        # List all opened issues - unauth
        output = self.app.get("/api/0/test/issues")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 0,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 0,
            },
        )

        # List all opened issues - auth
        output = self.app.get("/api/0/test/issues", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [lcl_issue],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

    def test_api_view_issues_since_invalid_format(self):
        """Test the api_view_issues method of the flask api."""
        self.test_api_new_issue()

        # Invalid repo
        output = self.app.get("/api/0/test/issues?since=12-13")
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {"error": "Invalid datetime format", "error_code": "EDATETIME"},
        )

    def test_api_view_issues_since_invalid_timestamp(self):
        """Test the api_view_issues method of the flask api."""
        self.test_api_new_issue()

        # Invalid repo
        output = self.app.get(
            "/api/0/test/issues?since=10000000000000000000000"
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {"error": "Invalid timestamp format", "error_code": "ETIMESTAMP"},
        )

    def test_api_view_issues_reversed(self):
        """Test the api_view_issues method of the flask api. in reversed
        order.

        """
        self.test_api_new_issue()

        headers = {"Authorization": "token aaabbbcccddd"}

        # List issues in reverse order
        output = self.app.get("/api/0/test/issues?order=asc", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["last_updated"] = "1431414800"
            data["issues"][idx]["date_created"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        expected = {
            "args": {
                "assignee": None,
                "author": None,
                "milestones": [],
                "no_stones": None,
                "order": "asc",
                "priority": None,
                "since": None,
                "status": None,
                "tags": [],
            },
            "issues": [FULL_ISSUE_LIST[8]],
            "pagination": {
                "first": "http://localhost...",
                "last": "http://localhost...",
                "next": None,
                "page": 1,
                "pages": 1,
                "per_page": 20,
                "prev": None,
            },
            "total_issues": 1,
        }
        self.assertDictEqual(data, expected)

    def test_api_view_issues_milestone(self):
        """Test the api_view_issues method of the flask api when filtering
        for a milestone.
        """
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Create 2 tickets but only 1 has a milestone
        start = arrow.utcnow().timestamp
        issue = pagure.lib.model.Issue(
            id=pagure.lib.query.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title="Issue #1",
            content="Description",
            user_id=1,  # pingou
            uid="issue#1",
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        issue = pagure.lib.model.Issue(
            id=pagure.lib.query.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title="Issue #2",
            content="Description",
            user_id=1,  # pingou
            uid="issue#2",
            private=False,
            milestone="v1.0",
        )
        self.session.add(issue)
        self.session.commit()

        # List all opened issues
        output = self.app.get("/api/0/test/issues")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        lcl_issues = copy.deepcopy(LCL_ISSUES)
        lcl_issues[0]["milestone"] = "v1.0"
        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": lcl_issues,
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 2,
            },
        )

        # List all issues of the milestone v1.0
        output = self.app.get("/api/0/test/issues?milestones=v1.0")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": ["v1.0"],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [lcl_issues[0]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

    def test_api_view_issues_priority(self):
        """Test the api_view_issues method of the flask api when filtering
        for a priority.
        """
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Create 2 tickets but only 1 has a priority
        start = arrow.utcnow().timestamp
        issue = pagure.lib.model.Issue(
            id=pagure.lib.query.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title="Issue #1",
            content="Description",
            user_id=1,  # pingou
            uid="issue#1",
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        issue = pagure.lib.model.Issue(
            id=pagure.lib.query.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title="Issue #2",
            content="Description",
            user_id=1,  # pingou
            uid="issue#2",
            private=False,
            priority=1,
        )
        self.session.add(issue)
        self.session.commit()

        # Set some priorities to the project
        repo.priorities = {"1": "High", "2": "Normal"}
        self.session.add(repo)
        self.session.commit()

        # List all opened issues
        output = self.app.get("/api/0/test/issues")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        lcl_issues = copy.deepcopy(LCL_ISSUES)
        lcl_issues[0]["priority"] = 1
        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": lcl_issues,
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 2,
            },
        )

        # List all issues of the priority high (ie: 1)
        output = self.app.get("/api/0/test/issues?priority=high")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": "high",
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [lcl_issues[0]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

        output = self.app.get("/api/0/test/issues?priority=1")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": "1",
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [lcl_issues[0]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

    def test_api_view_issues_priority_invalid(self):
        """Test the api_view_issues method of the flask api when filtering
        for an invalid priority.
        """
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Try getting issues with an invalid priority
        output = self.app.get("/api/0/test/issues?priority=foobar")
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid priority submitted",
                "error_code": "EINVALIDPRIORITY",
            },
        )

    def test_api_view_issues_no_stones(self):
        """Test the api_view_issues method of the flask api when filtering
        with no_stones.
        """
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Create 2 tickets but only 1 has a milestone
        start = arrow.utcnow().timestamp
        issue = pagure.lib.model.Issue(
            id=pagure.lib.query.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title="Issue #1",
            content="Description",
            user_id=1,  # pingou
            uid="issue#1",
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        issue = pagure.lib.model.Issue(
            id=pagure.lib.query.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title="Issue #2",
            content="Description",
            user_id=1,  # pingou
            uid="issue#2",
            private=False,
            milestone="v1.0",
        )
        self.session.add(issue)
        self.session.commit()

        # List all opened issues
        output = self.app.get("/api/0/test/issues")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        lcl_issues = copy.deepcopy(LCL_ISSUES)
        lcl_issues[0]["milestone"] = "v1.0"
        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": lcl_issues,
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 2,
            },
        )

        # List all issues with no milestone
        output = self.app.get("/api/0/test/issues?no_stones=1")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": True,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [lcl_issues[1]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

        # List all issues with a milestone
        output = self.app.get("/api/0/test/issues?no_stones=0")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": False,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": [lcl_issues[0]],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

    def test_api_view_issues_since(self):
        """Test the api_view_issues method of the flask api for since option"""

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets"), bare=True
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Create 1st tickets
        start = int(arrow.utcnow().float_timestamp)
        issue = pagure.lib.model.Issue(
            id=pagure.lib.query.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title="Issue #1",
            content="Description",
            user_id=1,  # pingou
            uid="issue#1",
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        time.sleep(1)
        middle = int(arrow.utcnow().float_timestamp)

        # Create 2nd tickets
        issue = pagure.lib.model.Issue(
            id=pagure.lib.query.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title="Issue #2",
            content="Description",
            user_id=1,  # pingou
            uid="issue#2",
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        time.sleep(1)
        final = int(arrow.utcnow().float_timestamp)

        # Create private issue
        issue = pagure.lib.model.Issue(
            id=pagure.lib.query.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title="Issue #3",
            content="Description",
            user_id=1,  # pingou
            uid="issue#3",
            private=True,
        )
        self.session.add(issue)
        self.session.commit()

        # Invalid repo
        output = self.app.get("/api/0/foo/issues")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

        # List all opened issues
        output = self.app.get("/api/0/test/issues")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": None,
                    "tags": [],
                },
                "issues": LCL_ISSUES,
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 2,
            },
        )

        time.sleep(1)

        # List all opened issues from the start
        output = self.app.get("/api/0/test/issues?since=%s" % start)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": str(start),
                    "status": None,
                    "tags": [],
                },
                "issues": LCL_ISSUES,
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 2,
            },
        )

        # List all opened issues from the middle
        output = self.app.get("/api/0/test/issues?since=%s" % middle)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": str(middle),
                    "status": None,
                    "tags": [],
                },
                "issues": LCL_ISSUES[:1],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

        # List all opened issues at the end
        output = self.app.get("/api/0/test/issues?since=%s" % final)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["date_created"] = "1431414800"
            data["issues"][idx]["last_updated"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": str(final),
                    "status": None,
                    "tags": [],
                },
                "issues": [],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 0,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 0,
            },
        )

        headers = {"Authorization": "token aaabbbcccddd"}

        # Test since for a value before creation of issues
        output = self.app.get(
            "/api/0/test/issues?since=%s" % final, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for idx in range(len(data["issues"])):
            data["issues"][idx]["last_updated"] = "1431414800"
            data["issues"][idx]["date_created"] = "1431414800"
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": str(final),
                    "status": None,
                    "tags": [],
                },
                "issues": [
                    {
                        "assignee": None,
                        "blocks": [],
                        "close_status": None,
                        "closed_at": None,
                        "closed_by": None,
                        "comments": [],
                        "content": "Description",
                        "custom_fields": [],
                        "date_created": "1431414800",
                        "depends": [],
                        "full_url": "http://localhost.localdomain/test/issue/3",
                        "id": 3,
                        "last_updated": "1431414800",
                        "milestone": None,
                        "priority": None,
                        "private": True,
                        "related_prs": [],
                        "status": "Open",
                        "tags": [],
                        "title": "Issue #3",
                        "user": {
                            "fullname": "PY C",
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "name": "pingou",
                            "url_path": "user/pingou",
                        },
                    }
                ],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_issues": 1,
            },
        )

    def test_api_view_issue(self):
        """Test the api_view_issue method of the flask api."""
        self.test_api_new_issue()

        # Invalid repo
        output = self.app.get("/api/0/foo/issue/1")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

        # Invalid issue for this repo
        output = self.app.get("/api/0/test2/issue/1")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Issue not found", "error_code": "ENOISSUE"}
        )

        # Valid issue
        output = self.app.get("/api/0/test/issue/1")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1431414800"
        data["last_updated"] = "1431414800"
        self.assertDictEqual(
            data,
            {
                "assignee": None,
                "blocks": [],
                "comments": [],
                "content": "This issue needs attention",
                "custom_fields": [],
                "full_url": "http://localhost.localdomain/test/issue/1",
                "date_created": "1431414800",
                "close_status": None,
                "closed_at": None,
                "closed_by": None,
                "depends": [],
                "id": 1,
                "last_updated": "1431414800",
                "milestone": None,
                "priority": None,
                "private": False,
                "related_prs": [],
                "status": "Open",
                "tags": [],
                "title": "test issue",
                "user": {
                    "fullname": "PY C",
                    "full_url": "http://localhost.localdomain/user/pingou",
                    "name": "pingou",
                    "url_path": "user/pingou",
                },
            },
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
            issue_uid="aaabbbccc",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        # Access private issue un-authenticated
        output = self.app.get("/api/0/test/issue/2")
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "You are not allowed to view this issue",
                "error_code": "EISSUENOTALLOWED",
            },
        )

        headers = {"Authorization": "token aaabbbccc"}

        # Access private issue authenticated but non-existing token
        output = self.app.get("/api/0/test/issue/2", headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["error", "error_code", "errors"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(data["errors"], "Invalid token")

        # Create a new token for another user
        item = pagure.lib.model.Token(
            id="bar_token",
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30),
        )
        self.session.add(item)
        self.session.commit()

        headers = {"Authorization": "token bar_token"}

        # Access private issue authenticated but wrong token
        output = self.app.get("/api/0/test/issue/2", headers=headers)
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "You are not allowed to view this issue",
                "error_code": "EISSUENOTALLOWED",
            },
        )

        headers = {"Authorization": "token aaabbbcccddd"}

        # Access private issue authenticated correctly
        output = self.app.get("/api/0/test/issue/2", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1431414800"
        data["last_updated"] = "1431414800"
        self.assertDictEqual(
            data,
            {
                "assignee": None,
                "blocks": [],
                "comments": [],
                "content": "We should work on this",
                "custom_fields": [],
                "full_url": "http://localhost.localdomain/test/issue/2",
                "date_created": "1431414800",
                "close_status": None,
                "closed_at": None,
                "closed_by": None,
                "depends": [],
                "id": 2,
                "last_updated": "1431414800",
                "milestone": None,
                "priority": None,
                "private": True,
                "related_prs": [],
                "status": "Open",
                "tags": [],
                "title": "Test issue",
                "user": {
                    "fullname": "PY C",
                    "full_url": "http://localhost.localdomain/user/pingou",
                    "name": "pingou",
                    "url_path": "user/pingou",
                },
            },
        )

        # Access private issue authenticated correctly using the issue's uid
        output = self.app.get("/api/0/test/issue/aaabbbccc", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1431414800"
        data["last_updated"] = "1431414800"
        self.assertDictEqual(
            data,
            {
                "assignee": None,
                "blocks": [],
                "comments": [],
                "content": "We should work on this",
                "custom_fields": [],
                "full_url": "http://localhost.localdomain/test/issue/2",
                "date_created": "1431414800",
                "close_status": None,
                "closed_at": None,
                "closed_by": None,
                "depends": [],
                "id": 2,
                "last_updated": "1431414800",
                "milestone": None,
                "priority": None,
                "private": True,
                "related_prs": [],
                "status": "Open",
                "tags": [],
                "title": "Test issue",
                "user": {
                    "fullname": "PY C",
                    "full_url": "http://localhost.localdomain/user/pingou",
                    "name": "pingou",
                    "url_path": "user/pingou",
                },
            },
        )

    def test_api_change_milestone_issue_invalid_project(self):
        """Test the api_change_milestone_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestones = {"v1.0": None, "v2.0": "Soon"}
        self.session.add(repo)
        self.session.commit()

        headers = {"Authorization": "token aaabbbcccddd"}

        # Invalid project
        output = self.app.post("/api/0/foo/issue/1/milestone", headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    @patch.dict(
        "pagure.config.config", {"ENABLE_TICKETS_NAMESPACE": ["foobar"]}
    )
    def test_api_change_milestone_issue_wrong_namespace(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.query.get_authorized_project(
            self.session, "test3", namespace="somenamespace"
        )
        repo.milestones = {"v1.0": None, "v2.0": "Soon"}
        self.session.add(repo)
        self.session.commit()

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

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid token, wrong project
        output = self.app.post(
            "/api/0/somenamespace/test3/issue/1/milestone", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["error", "error_code"])
        self.assertEqual(
            pagure.api.APIERROR.ETRACKERDISABLED.value, data["error"]
        )
        self.assertEqual(
            pagure.api.APIERROR.ETRACKERDISABLED.name, data["error_code"]
        )

    def test_api_change_milestone_issue_wrong_token(self):
        """Test the api_change_milestone_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestones = {"v1.0": None, "v2.0": "Soon"}
        self.session.add(repo)
        self.session.commit()

        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid token, wrong project
        output = self.app.post(
            "/api/0/test2/issue/1/milestone", headers=headers
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["error", "error_code"])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )

    def test_api_change_milestone_issue_no_issue(self):
        """Test the api_change_milestone_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestones = {"v1.0": None, "v2.0": "Soon"}
        self.session.add(repo)
        self.session.commit()

        headers = {"Authorization": "token aaabbbcccddd"}

        # No issue
        output = self.app.post(
            "/api/0/test/issue/1/milestone", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Issue not found", "error_code": "ENOISSUE"}
        )

    def test_api_change_milestone_issue_no_milestone(self):
        """Test the api_change_milestone_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestones = {"v1.0": None, "v2.0": "Soon"}
        self.session.add(repo)
        self.session.commit()

        headers = {"Authorization": "token aaabbbcccddd"}
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

        # Check milestone before
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.milestone, None)

        data = {"milestone": ""}

        # Valid request but no milestone specified
        output = self.app.post(
            "/api/0/test/issue/1/milestone", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "No changes"})

        # No change
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.milestone, None)

    def test_api_change_milestone_issue_invalid_milestone(self):
        """Test the api_change_milestone_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestones = {"v1.0": None, "v2.0": "Soon"}
        self.session.add(repo)
        self.session.commit()

        headers = {"Authorization": "token aaabbbcccddd"}
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

        # Check milestone before
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.milestone, None)

        data = {"milestone": "milestone-1-0"}

        # Invalid milestone specified
        output = self.app.post(
            "/api/0/test/issue/1/milestone", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {"milestone": ["Not a valid choice"]},
        }
        if self.get_wtforms_version() >= (3, 0):
            expected_output["errors"]["milestone"] = ["Not a valid choice."]
        self.assertDictEqual(data, expected_output)

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    def test_api_change_milestone_issue(self):
        """Test the api_change_milestone_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestones = {"v1.0": None, "v2.0": "Soon"}
        self.session.add(repo)
        self.session.commit()

        headers = {"Authorization": "token aaabbbcccddd"}
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

        # Check milestone before
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.milestone, None)

        data = {"milestone": "v1.0"}

        # Valid requests
        with testing.mock_sends(
            pagure_messages.IssueEditV1(
                topic="pagure.issue.edit",
                body={
                    "issue": {
                        "id": 1,
                        "title": "Test issue #1",
                        "content": "We should work on this",
                        "status": "Open",
                        "close_status": None,
                        "date_created": ANY,
                        "last_updated": ANY,
                        "closed_at": None,
                        "user": {
                            "name": "pingou",
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "fullname": "PY C",
                            "url_path": "user/pingou",
                        },
                        "private": False,
                        "tags": [],
                        "depends": [],
                        "blocks": [],
                        "assignee": None,
                        "priority": None,
                        "milestone": "v1.0",
                        "custom_fields": [],
                        "full_url": "http://localhost.localdomain/test/issue/1",
                        "closed_by": None,
                        "related_prs": [],
                        "comments": [],
                    },
                    "project": {
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
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "fullname": "PY C",
                            "url_path": "user/pingou",
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
                        "milestones": {
                            "v1.0": {"date": None, "active": True},
                            "v2.0": {"date": "Soon", "active": True},
                        },
                    },
                    "fields": ["milestone"],
                    "agent": "pingou",
                },
            )
        ):
            output = self.app.post(
                "/api/0/test/issue/1/milestone", data=data, headers=headers
            )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": ["Issue set to the milestone: v1.0"]}
        )

    def test_api_change_milestone_issue_remove_milestone(self):
        """Test the api_change_milestone_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestones = {"v1.0": None, "v2.0": "Soon"}
        self.session.add(repo)
        self.session.commit()

        headers = {"Authorization": "token aaabbbcccddd"}
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

        # Check milestone before
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.milestone, None)

        data = {"milestone": "v1.0"}

        # Valid requests
        output = self.app.post(
            "/api/0/test/issue/1/milestone", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": ["Issue set to the milestone: v1.0"]}
        )

        # remove milestone
        data = {"milestone": ""}

        # Valid requests
        output = self.app.post(
            "/api/0/test/issue/1/milestone", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": ["Issue set to the milestone: None (was: v1.0)"]}
        )

        # Change recorded
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.milestone, None)

    def test_api_change_milestone_issue_remove_milestone2(self):
        """Test the api_change_milestone_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestones = {"v1.0": None, "v2.0": "Soon"}
        self.session.add(repo)
        self.session.commit()

        headers = {"Authorization": "token aaabbbcccddd"}
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

        # Check milestone before
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.milestone, None)

        data = {"milestone": "v1.0"}

        # Valid requests
        output = self.app.post(
            "/api/0/test/issue/1/milestone", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": ["Issue set to the milestone: v1.0"]}
        )

        # remove milestone by using no milestone in JSON
        data = {}

        # Valid requests
        output = self.app.post(
            "/api/0/test/issue/1/milestone", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": ["Issue set to the milestone: None (was: v1.0)"]}
        )

        # Change recorded
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.milestone, None)

    def test_api_change_milestone_issue_unauthorized(self):
        """Test the api_change_milestone_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestones = {"v1.0": None, "v2.0": "Soon"}
        self.session.add(repo)
        self.session.commit()

        headers = {"Authorization": "token aaabbbcccddd"}
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

        headers = {"Authorization": "token pingou_foo"}
        data = {"milestone": "v1.0"}

        # Un-authorized issue
        output = self.app.post(
            "/api/0/foo/issue/1/milestone", data={}, headers=headers
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["error", "error_code", "errors"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(data["errors"], "Invalid token")

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch(
        "pagure.lib.query.add_metadata_update_notif",
        MagicMock(side_effect=pagure.exceptions.PagureException("error")),
    )
    def test_api_change_milestone_issue_raises_exception(self):
        """Test the api_change_milestone_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestones = {"v1.0": None, "v2.0": "Soon"}
        self.session.add(repo)
        self.session.commit()

        headers = {"Authorization": "token aaabbbcccddd"}
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

        data = {"milestone": "v1.0"}

        # Valid requests
        output = self.app.post(
            "/api/0/test/issue/1/milestone", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"error": "error", "error_code": "ENOCODE"})

    def test_api_view_issue_related_prs(self):
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #1",
            content="We should work on this",
            user="pingou",
            private=False,
            issue_uid="aaabbbccc1",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #1")
        self.assertEqual(msg.related_prs, [])
        self.assertEqual(msg.id, 1)

        # Create pull request
        repo_to = pagure.lib.query.get_authorized_project(self.session, "test")
        repo_from = pagure.lib.query.get_authorized_project(
            self.session, "test"
        )

        msg = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=repo_from,
            repo_to=repo_to,
            branch_from="master",
            branch_to="master",
            title="New shiny feature",
            user="pingou",
            initial_comment="Fixes #1",
        )
        self.session.commit()
        self.assertEqual(msg.id, 2)
        self.assertEqual(msg.title, "New shiny feature")

        output = self.app.get("/api/0/test/pull-request/2")
        self.assertEqual(
            json.loads(output.get_data(as_text=True)).get("initial_comment"),
            "Fixes #1",
        )

        output = self.app.get("/api/0/test/issue/1")
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data.get("related_prs"), [{"id": 2, "title": "New shiny feature"}]
        )

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_api_view_issue_comment(self, p_send_email, p_ugt):
        """Test the api_view_issue_comment endpoint."""
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create normal issue in test
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #1",
            content="We should work on this",
            user="pingou",
            private=False,
            issue_uid="aaabbbccc1",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #1")

        headers = {"Authorization": "token aaabbbcccddd"}

        data = {"comment": "This is a very interesting question"}

        # Valid request
        output = self.app.post(
            "/api/0/test/issue/1/comment", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "message": "Comment added",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "pingou",
            },
        )

        # One comment added
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)

        # View a comment that does not exist
        output = self.app.get("/api/0/foo/issue/100/comment/2")
        self.assertEqual(output.status_code, 404)

        # Issue exists but not the comment
        output = self.app.get("/api/0/test/issue/1/comment/2")
        self.assertEqual(output.status_code, 404)

        # Issue and comment exists
        output = self.app.get("/api/0/test/issue/1/comment/1")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1435821770"
        data["comment_date"] = "2015-07-02 09:22"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "comment": "This is a very interesting question",
                "comment_date": "2015-07-02 09:22",
                "date_created": "1435821770",
                "edited_on": None,
                "editor": None,
                "notification": False,
                "id": 1,
                "parent": None,
                "reactions": {},
                "user": {
                    "fullname": "PY C",
                    "full_url": "http://localhost.localdomain/user/pingou",
                    "name": "pingou",
                    "url_path": "user/pingou",
                },
            },
        )

        # Issue and comment exists, using UID
        output = self.app.get("/api/0/test/issue/aaabbbccc1/comment/1")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1435821770"
        data["comment_date"] = "2015-07-02 09:22"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "comment": "This is a very interesting question",
                "comment_date": "2015-07-02 09:22",
                "date_created": "1435821770",
                "edited_on": None,
                "editor": None,
                "notification": False,
                "id": 1,
                "parent": None,
                "reactions": {},
                "user": {
                    "fullname": "PY C",
                    "full_url": "http://localhost.localdomain/user/pingou",
                    "name": "pingou",
                    "url_path": "user/pingou",
                },
            },
        )

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_api_view_issue_comment_private(self, p_send_email, p_ugt):
        """Test the api_view_issue_comment endpoint."""
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create normal issue in test
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #1",
            content="We should work on this",
            user="foo",
            private=True,
            issue_uid="aaabbbccc1",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #1")

        # Create a token for another user
        item = pagure.lib.model.Token(
            id="foo_token_2",
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30),
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session, token_id="foo_token_2")

        # Add a comment to that issue
        data = {"comment": "This is a very interesting question"}
        headers = {"Authorization": "token foo_token_2"}
        output = self.app.post(
            "/api/0/test/issue/1/comment", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "message": "Comment added",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "foo",
            },
        )

        # Private issue - no auth
        output = self.app.get("/api/0/test/issue/1/comment/2")
        self.assertEqual(output.status_code, 403)

        # Private issue - Auth - Invalid token
        headers = {"Authorization": "token aaabbbcccdddee"}
        output = self.app.get("/api/0/test/issue/1/comment/2", headers=headers)
        self.assertEqual(output.status_code, 401)

        # Private issue - Auth - valid token - unknown comment
        headers = {"Authorization": "token foo_token_2"}
        output = self.app.get("/api/0/test/issue/1/comment/3", headers=headers)
        self.assertEqual(output.status_code, 404)

        # Private issue - Auth - valid token - known comment
        headers = {"Authorization": "token foo_token_2"}
        output = self.app.get("/api/0/test/issue/1/comment/1", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1435821770"
        data["comment_date"] = "2015-07-02 09:22"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "comment": "This is a very interesting question",
                "comment_date": "2015-07-02 09:22",
                "date_created": "1435821770",
                "edited_on": None,
                "editor": None,
                "notification": False,
                "id": 1,
                "parent": None,
                "reactions": {},
                "user": {
                    "fullname": "foo bar",
                    "full_url": "http://localhost.localdomain/user/foo",
                    "name": "foo",
                    "url_path": "user/foo",
                },
            },
        )

    @patch.dict(
        "pagure.config.config", {"ENABLE_TICKETS_NAMESPACE": ["foobar"]}
    )
    def test_api_assign_issue_wrong_namespace(self):
        """Test the api_new_issue method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.query.get_authorized_project(
            self.session, "test3", namespace="somenamespace"
        )
        repo.milestones = {"v1.0": None, "v2.0": "Soon"}
        self.session.add(repo)
        self.session.commit()

        # Create normal issue
        repo = pagure.lib.query.get_authorized_project(
            self.session, "test3", namespace="somenamespace"
        )
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

        # Valid token, wrong project
        output = self.app.post(
            "/api/0/somenamespace/test3/issue/1/assign", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["error", "error_code"])
        self.assertEqual(
            pagure.api.APIERROR.ETRACKERDISABLED.value, data["error"]
        )
        self.assertEqual(
            pagure.api.APIERROR.ETRACKERDISABLED.name, data["error_code"]
        )

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_api_assign_issue(self, p_send_email, p_ugt):
        """Test the api_assign_issue method of the flask api."""
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Invalid project
        output = self.app.post("/api/0/foo/issue/1/assign", headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

        # Valid token, wrong project
        output = self.app.post("/api/0/test2/issue/1/assign", headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["error", "error_code"])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )

        # No input
        output = self.app.post("/api/0/test/issue/1/assign", headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Issue not found", "error_code": "ENOISSUE"}
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
            issue_uid="aaabbbccc1",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #1")

        # Check comments before
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        # No change
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.status, "Open")

        data = {"assignee": "pingou"}

        # Valid request
        with testing.mock_sends(
            pagure_messages.IssueAssignedAddedV1(
                topic="pagure.issue.assigned.added",
                body={
                    "issue": {
                        "id": 1,
                        "title": "Test issue #1",
                        "content": "We should work on this",
                        "status": "Open",
                        "close_status": None,
                        "date_created": ANY,
                        "last_updated": ANY,
                        "closed_at": None,
                        "user": {
                            "name": "pingou",
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "fullname": "PY C",
                            "url_path": "user/pingou",
                        },
                        "private": False,
                        "tags": [],
                        "depends": [],
                        "blocks": [],
                        "assignee": {
                            "name": "pingou",
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "fullname": "PY C",
                            "url_path": "user/pingou",
                        },
                        "priority": None,
                        "milestone": None,
                        "custom_fields": [],
                        "full_url": "http://localhost.localdomain/test/issue/1",
                        "closed_by": None,
                        "related_prs": [],
                        "comments": [],
                    },
                    "project": {
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
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "fullname": "PY C",
                            "url_path": "user/pingou",
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
                    "agent": "pingou",
                },
            )
        ):
            output = self.app.post(
                "/api/0/test/issue/1/assign", data=data, headers=headers
            )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Issue assigned to pingou"})

        # Un-assign
        with testing.mock_sends(
            pagure_messages.IssueAssignedResetV1(
                topic="pagure.issue.assigned.reset",
                body={
                    "issue": {
                        "id": 1,
                        "title": "Test issue #1",
                        "content": "We should work on this",
                        "status": "Open",
                        "close_status": None,
                        "date_created": ANY,
                        "last_updated": ANY,
                        "closed_at": None,
                        "user": {
                            "name": "pingou",
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "fullname": "PY C",
                            "url_path": "user/pingou",
                        },
                        "private": False,
                        "tags": [],
                        "depends": [],
                        "blocks": [],
                        "assignee": None,
                        "priority": None,
                        "milestone": None,
                        "custom_fields": [],
                        "full_url": "http://localhost.localdomain/test/issue/1",
                        "closed_by": None,
                        "related_prs": [],
                        "comments": [
                            {
                                "id": 1,
                                "comment": "**Metadata Update from @pingou**:"
                                "\n- Issue assigned to pingou",
                                "parent": None,
                                "date_created": ANY,
                                "user": {
                                    "name": "pingou",
                                    "full_url": "http://localhost.localdomain/user/pingou",
                                    "fullname": "PY C",
                                    "url_path": "user/pingou",
                                },
                                "edited_on": None,
                                "editor": None,
                                "notification": True,
                                "reactions": {},
                            }
                        ],
                    },
                    "project": {
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
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "fullname": "PY C",
                            "url_path": "user/pingou",
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
                    "agent": "pingou",
                },
            )
        ):
            output = self.app.post(
                "/api/0/test/issue/1/assign", data=data, headers=headers
            )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Assignee reset"})
        # No change
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.assignee, None)

        # Un-assign
        data = {"assignee": None}
        output = self.app.post(
            "/api/0/test/issue/1/assign", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Nothing to change"})
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.assignee, None)

        # Re-assign for the rest of the tests
        data = {"assignee": "pingou"}
        output = self.app.post(
            "/api/0/test/issue/1/assign", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Issue assigned to pingou"})

        # Un-assign
        data = {"assignee": ""}
        output = self.app.post(
            "/api/0/test/issue/1/assign", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Assignee reset"})

        # Re-assign for the rest of the tests
        data = {"assignee": "pingou"}
        output = self.app.post(
            "/api/0/test/issue/1/assign", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Issue assigned to pingou"})

        # One comment added
        self.session.commit()
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.assignee.user, "pingou")

        # Create another project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name="foo",
            description="test project #3",
            hook_token="aaabbbdddeee",
        )
        self.session.add(item)
        self.session.commit()

        # Create a token for pingou for this project
        item = pagure.lib.model.Token(
            id="pingou_foo",
            user_id=1,
            project_id=4,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30),
        )
        self.session.add(item)
        self.session.commit()

        # Give `issue_change_status` to this token when `issue_comment`
        # is required
        acl_id = (
            sorted(pagure.config.config["ACLS"]).index("issue_comment") + 1
        )
        item = pagure.lib.model.TokenAcl(token_id="pingou_foo", acl_id=acl_id)
        self.session.add(item)
        self.session.commit()

        repo = pagure.lib.query.get_authorized_project(self.session, "foo")
        # Create private issue
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="foo",
            private=True,
            issue_uid="aaabbbccc#2",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        # Check before
        repo = pagure.lib.query.get_authorized_project(self.session, "foo")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        data = {"assignee": "pingou"}
        headers = {"Authorization": "token pingou_foo"}

        # Valid request but un-authorized
        output = self.app.post(
            "/api/0/foo/issue/1/assign", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["error", "error_code", "errors"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(
            data["errors"], "Missing ACLs: issue_assign, issue_update"
        )

        # No comment added
        repo = pagure.lib.query.get_authorized_project(self.session, "foo")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        # Create token for user foo
        item = pagure.lib.model.Token(
            id="foo_token2",
            user_id=2,
            project_id=4,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30),
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session, token_id="foo_token2")

        data = {"assignee": "pingou"}
        headers = {"Authorization": "token foo_token2"}

        # Valid request and authorized
        output = self.app.post(
            "/api/0/foo/issue/1/assign", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Issue assigned to pingou"})

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_api_assign_issue_issuer(self, p_send_email, p_ugt):
        """Test the api_assign_issue method of the flask api."""
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session, user_id=2)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Create normal issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #1",
            content="We should work on this",
            user="pingou",
            private=False,
            issue_uid="aaabbbccc1",
            assignee="foo",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #1")

        # Check comments before
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        # Un-assign
        data = {"assignee": None}
        output = self.app.post(
            "/api/0/test/issue/1/assign", data={}, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Assignee reset"})

        # No longer allowed to self-assign since no access
        data = {"assignee": "foo"}
        output = self.app.post(
            "/api/0/test/issue/1/assign", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "You are not allowed to view this issue",
                "error_code": "EISSUENOTALLOWED",
            },
        )

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_api_subscribe_issue(self, p_send_email, p_ugt):
        """Test the api_subscribe_issue method of the flask api."""
        p_send_email.return_value = True
        p_ugt.return_value = True

        item = pagure.lib.model.User(
            user="bar",
            fullname="bar foo",
            password="foo",
            default_email="bar@bar.com",
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(user_id=3, email="bar@bar.com")
        self.session.add(item)

        self.session.commit()

        tests.create_projects(self.session)
        tests.create_tokens(self.session, user_id=3)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Invalid project
        output = self.app.post("/api/0/foo/issue/1/subscribe", headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

        # Valid token, wrong project
        output = self.app.post(
            "/api/0/test2/issue/1/subscribe", headers=headers
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["error", "error_code"])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )

        # No input
        output = self.app.post(
            "/api/0/test/issue/1/subscribe", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Issue not found", "error_code": "ENOISSUE"}
        )

        # Create normal issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #1",
            content="We should work on this",
            user="foo",
            private=False,
            issue_uid="aaabbbccc1",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #1")

        # Check subscribtion before
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(
            pagure.lib.query.get_watch_list(self.session, issue),
            set(["pingou", "foo"]),
        )

        # Unsubscribe - no changes
        data = {}
        output = self.app.post(
            "/api/0/test/issue/1/subscribe", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "message": "You are no longer watching this issue",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "bar",
            },
        )

        data = {}
        output = self.app.post(
            "/api/0/test/issue/1/subscribe", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "message": "You are no longer watching this issue",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "bar",
            },
        )

        # No change
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(
            pagure.lib.query.get_watch_list(self.session, issue),
            set(["pingou", "foo"]),
        )

        # Subscribe
        data = {"status": True}
        output = self.app.post(
            "/api/0/test/issue/1/subscribe", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "message": "You are now watching this issue",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "bar",
            },
        )

        # Subscribe - no changes
        data = {"status": True}
        output = self.app.post(
            "/api/0/test/issue/1/subscribe", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "message": "You are now watching this issue",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "bar",
            },
        )

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(
            pagure.lib.query.get_watch_list(self.session, issue),
            set(["pingou", "foo", "bar"]),
        )

        # Unsubscribe
        data = {}
        output = self.app.post(
            "/api/0/test/issue/1/subscribe", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "message": "You are no longer watching this issue",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "bar",
            },
        )

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(
            pagure.lib.query.get_watch_list(self.session, issue),
            set(["pingou", "foo"]),
        )

    def test_api_update_custom_field(self):
        """Test the api_update_custom_field method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Invalid project
        output = self.app.post(
            "/api/0/foo/issue/1/custom/bugzilla", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

        # Valid token, wrong project
        output = self.app.post(
            "/api/0/test2/issue/1/custom/bugzilla", headers=headers
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["error", "error_code"])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )

        # No issue
        output = self.app.post(
            "/api/0/test/issue/1/custom/bugzilla", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Issue not found", "error_code": "ENOISSUE"}
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

        # Project does not have this custom field
        output = self.app.post(
            "/api/0/test/issue/1/custom/bugzilla", headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid custom field submitted",
                "error_code": "EINVALIDISSUEFIELD",
            },
        )

        # Check the behavior if the project disabled the issue tracker
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        settings = repo.settings
        settings["issue_tracker"] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.post(
            "/api/0/test/issue/1/custom/bugzilla", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Issue tracker disabled",
                "error_code": "ETRACKERDISABLED",
            },
        )

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        settings = repo.settings
        settings["issue_tracker"] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        # Invalid API token
        headers = {"Authorization": "token foobar"}

        output = self.app.post(
            "/api/0/test/issue/1/custom/bugzilla", headers=headers
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["error", "error_code", "errors"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(data["errors"], "Invalid token")

        headers = {"Authorization": "token aaabbbcccddd"}

        # Set some custom fields
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.set_custom_key_fields(
            self.session,
            repo,
            ["bugzilla", "upstream", "reviewstatus", "duedate"],
            ["link", "boolean", "list", "date"],
            ["", "", "ack, nack ,  needs review", "2018-10-10"],
            [None, None, None, None],
        )
        self.session.commit()
        self.assertEqual(msg, "List of custom fields updated")

        # Check the project custom fields were correctly set
        for key in repo.issue_keys:
            # Check that the bugzilla field correctly had its data removed
            if key.name == "bugzilla":
                self.assertIsNone(key.data)

            # Check that the reviewstatus list field still has its list
            if key.name == "reviewstatus":
                self.assertEqual(
                    sorted(key.data), ["ack", "nack", "needs review"]
                )

            # Check that the duedate date field still has its date
            if key.name == "duedate":
                self.assertEqual(key.data, "2018-10-10")

        # Check that not setting the value on a non-existing custom field
        # changes nothing
        output = self.app.post(
            "/api/0/test/issue/1/custom/bugzilla", headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "No changes"})

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.other_fields, [])
        self.assertEqual(len(issue.other_fields), 0)

        # Invalid value
        output = self.app.post(
            "/api/0/test/issue/1/custom/bugzilla",
            headers=headers,
            data={"value": "foobar"},
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid custom field submitted, the value is not "
                "a link",
                "error_code": "EINVALIDISSUEFIELD_LINK",
            },
        )

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.other_fields, [])
        self.assertEqual(len(issue.other_fields), 0)

        # All good
        output = self.app.post(
            "/api/0/test/issue/1/custom/bugzilla",
            headers=headers,
            data={"value": "https://bugzilla.redhat.com/1234"},
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "message": "Custom field bugzilla adjusted to "
                "https://bugzilla.redhat.com/1234"
            },
        )

        self.session.commit()
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.other_fields), 1)
        self.assertEqual(issue.other_fields[0].key.name, "bugzilla")
        self.assertEqual(
            issue.other_fields[0].value, "https://bugzilla.redhat.com/1234"
        )

        # Reset the value
        output = self.app.post(
            "/api/0/test/issue/1/custom/bugzilla",
            headers=headers,
            data={"value": ""},
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "message": "Custom field bugzilla reset "
                "(from https://bugzilla.redhat.com/1234)"
            },
        )

        self.session.commit()
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.other_fields), 0)

    @patch(
        "pagure.lib.query.set_custom_key_value",
        MagicMock(side_effect=pagure.exceptions.PagureException("error")),
    )
    def test_api_update_custom_field_raises_error(self):
        """Test the api_update_custom_field method of the flask api."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

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

        # Set some custom fields
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.set_custom_key_fields(
            self.session,
            repo,
            ["bugzilla", "upstream", "reviewstatus"],
            ["link", "boolean", "list"],
            ["unused data for non-list type", "", "ack, nack ,  needs review"],
            [None, None, None],
        )
        self.session.commit()
        self.assertEqual(msg, "List of custom fields updated")

        # Check the project custom fields were correctly set
        for key in repo.issue_keys:
            # Check that the bugzilla field correctly had its data removed
            if key.name == "bugzilla":
                self.assertIsNone(key.data)

            # Check that the reviewstatus list field still has its list
            elif key.name == "reviewstatus":
                self.assertEqual(
                    sorted(key.data), ["ack", "nack", "needs review"]
                )

        # Should work but raises an exception
        output = self.app.post(
            "/api/0/test/issue/1/custom/bugzilla",
            headers=headers,
            data={"value": "https://bugzilla.redhat.com/1234"},
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"error": "error", "error_code": "ENOCODE"})

    def test_api_view_issues_history_stats(self):
        """Test the api_view_issues_history_stats method of the flask api."""
        self.test_api_new_issue()

        # Create private issue, closed and without a closed_at date
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
            private=True,
            status="Closed",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        output = self.app.get("/api/0/test/issues/history/stats")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data), 1)
        self.assertEqual(len(data["stats"]), 53)
        last_key = sorted(data["stats"].keys())[-1]
        self.assertEqual(data["stats"][last_key], 0)
        for k in sorted(data["stats"].keys())[:-1]:
            self.assertEqual(data["stats"][k], 0)

    def test_api_view_issues_history_stats_detailed(self):
        """Test the api_view_issues_history_stats method of the flask api."""
        self.test_api_new_issue()

        output = self.app.get("/api/0/test/issues/history/detailed_stats")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(list(data.keys()), ["stats"])
        self.assertEqual(len(data["stats"]), 53)
        last_key = sorted(data["stats"].keys())[-1]
        self.assertEqual(
            data["stats"][last_key],
            {"closed_ticket": 0, "count": 0, "open_ticket": 1},
        )
        for k in sorted(data["stats"].keys())[:-1]:
            self.assertEqual(
                data["stats"][k],
                {"closed_ticket": 0, "count": 0, "open_ticket": 0},
            )

    def test_api_view_issues_history_stats_detailed_invalid_range(self):
        """Test the api_view_issues_history_stats method of the flask api."""
        self.test_api_new_issue()

        output = self.app.get(
            "/api/0/test/issues/history/detailed_stats?weeks_range=abc"
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(list(data.keys()), ["stats"])
        self.assertEqual(len(data["stats"]), 53)
        last_key = sorted(data["stats"].keys())[-1]
        self.assertEqual(
            data["stats"][last_key],
            {"closed_ticket": 0, "count": 0, "open_ticket": 1},
        )
        for k in sorted(data["stats"].keys())[:-1]:
            self.assertEqual(
                data["stats"][k],
                {"closed_ticket": 0, "count": 0, "open_ticket": 0},
            )

    def test_api_view_issues_history_stats_detailed_one_week(self):
        """Test the api_view_issues_history_stats method of the flask api."""
        self.test_api_new_issue()

        output = self.app.get(
            "/api/0/test/issues/history/detailed_stats?weeks_range=1"
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(list(data.keys()), ["stats"])
        self.assertEqual(len(data["stats"]), 1)
        last_key = sorted(data["stats"].keys())[-1]
        self.assertEqual(
            data["stats"][last_key],
            {"closed_ticket": 0, "count": 0, "open_ticket": 1},
        )
        for k in sorted(data["stats"].keys())[:-1]:
            self.assertEqual(
                data["stats"][k],
                {"closed_ticket": 0, "count": 0, "open_ticket": 0},
            )

    def test_api_view_user_issues_pingou(self):
        """Test the api_view_user_issues method of the flask api for pingou."""
        self.test_api_new_issue()

        # Create private issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
            private=True,
            status="Closed",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        output = self.app.get("/api/0/user/pingou/issues")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        args = {
            "assignee": True,
            "author": True,
            "closed": None,
            "created": None,
            "milestones": [],
            "no_stones": None,
            "order": None,
            "order_key": None,
            "page": 1,
            "since": None,
            "status": None,
            "tags": [],
            "updated": None,
        }

        self.assertEqual(data["args"], args)
        self.assertEqual(data["issues_assigned"], [])
        self.assertEqual(len(data["issues_created"]), 1)
        self.assertEqual(data["total_issues_assigned"], 0)
        self.assertEqual(data["total_issues_created"], 1)
        self.assertEqual(data["total_issues_assigned_pages"], 1)
        self.assertEqual(data["total_issues_created_pages"], 1)

        # Restrict to a certain, fake milestone
        output = self.app.get("/api/0/user/pingou/issues?milestones=v1.0")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        args = {
            "assignee": True,
            "author": True,
            "closed": None,
            "created": None,
            "milestones": ["v1.0"],
            "no_stones": None,
            "order": None,
            "order_key": None,
            "page": 1,
            "since": None,
            "status": None,
            "tags": [],
            "updated": None,
        }

        self.assertEqual(data["args"], args)
        self.assertEqual(data["issues_assigned"], [])
        self.assertEqual(data["issues_created"], [])
        self.assertEqual(data["total_issues_assigned"], 0)
        self.assertEqual(data["total_issues_created"], 0)
        self.assertEqual(data["total_issues_assigned_pages"], 1)
        self.assertEqual(data["total_issues_created_pages"], 1)

        # Restrict to a certain status
        output = self.app.get("/api/0/user/pingou/issues?status=closed")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        args = {
            "assignee": True,
            "author": True,
            "closed": None,
            "created": None,
            "milestones": [],
            "no_stones": None,
            "order": None,
            "order_key": None,
            "page": 1,
            "since": None,
            "status": "closed",
            "tags": [],
            "updated": None,
        }

        self.assertEqual(data["args"], args)
        self.assertEqual(data["issues_assigned"], [])
        self.assertEqual(len(data["issues_created"]), 1)
        self.assertEqual(data["total_issues_assigned"], 0)
        self.assertEqual(data["total_issues_created"], 1)
        self.assertEqual(data["total_issues_assigned_pages"], 1)
        self.assertEqual(data["total_issues_created_pages"], 1)

        # Restrict to a certain status
        output = self.app.get("/api/0/user/pingou/issues?status=all")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        args = {
            "assignee": True,
            "author": True,
            "closed": None,
            "created": None,
            "milestones": [],
            "no_stones": None,
            "order": None,
            "order_key": None,
            "page": 1,
            "since": None,
            "status": "all",
            "tags": [],
            "updated": None,
        }

        self.assertEqual(data["args"], args)
        self.assertEqual(data["issues_assigned"], [])
        self.assertEqual(len(data["issues_created"]), 2)
        self.assertEqual(data["total_issues_assigned"], 0)
        self.assertEqual(data["total_issues_created"], 2)
        self.assertEqual(data["total_issues_assigned_pages"], 1)
        self.assertEqual(data["total_issues_created_pages"], 1)

    def test_api_view_user_issues_foo(self):
        """Test the api_view_user_issues method of the flask api for foo."""
        self.test_api_new_issue()

        # Create private issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
            private=True,
            status="Closed",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue")

        output = self.app.get("/api/0/user/foo/issues")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        args = {
            "assignee": True,
            "author": True,
            "closed": None,
            "created": None,
            "milestones": [],
            "no_stones": None,
            "order": None,
            "order_key": None,
            "page": 1,
            "since": None,
            "status": None,
            "tags": [],
            "updated": None,
        }

        self.assertEqual(data["args"], args)
        self.assertEqual(len(data["issues_assigned"]), 0)
        self.assertEqual(data["issues_created"], [])
        self.assertEqual(data["total_issues_assigned"], 0)
        self.assertEqual(data["total_issues_created"], 0)
        self.assertEqual(data["total_issues_assigned_pages"], 1)
        self.assertEqual(data["total_issues_created_pages"], 1)

    def test_api_view_user_issues_foo_invalid_page(self):
        """Test the api_view_user_issues method of the flask api for foo."""
        self.test_api_new_issue()

        output = self.app.get("/api/0/user/foo/issues?page=0")
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
            },
        )

        output = self.app.get("/api/0/user/foo/issues?page=abc")
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
            },
        )

    def test_api_view_user_issues_foo_no_assignee(self):
        """Test the api_view_user_issues method of the flask api for foo."""
        self.test_api_new_issue()

        output = self.app.get("/api/0/user/foo/issues?assignee=0")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        args = {
            "assignee": False,
            "author": True,
            "closed": None,
            "created": None,
            "milestones": [],
            "no_stones": None,
            "order": None,
            "order_key": None,
            "page": 1,
            "since": None,
            "status": None,
            "tags": [],
            "updated": None,
        }

        self.assertEqual(data["args"], args)
        self.assertEqual(data["issues_assigned"], [])
        self.assertEqual(data["issues_created"], [])
        self.assertEqual(data["total_issues_assigned"], 0)
        self.assertEqual(data["total_issues_created"], 0)
        self.assertEqual(data["total_issues_assigned_pages"], 1)
        self.assertEqual(data["total_issues_created_pages"], 1)

    def test_api_view_user_issues_pingou_no_author(self):
        """Test the api_view_user_issues method of the flask api for pingou."""
        self.test_api_new_issue()

        output = self.app.get("/api/0/user/pingou/issues?author=0")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        args = {
            "assignee": True,
            "author": False,
            "closed": None,
            "created": None,
            "milestones": [],
            "no_stones": None,
            "order": None,
            "order_key": None,
            "page": 1,
            "since": None,
            "status": None,
            "tags": [],
            "updated": None,
        }

        self.assertEqual(data["args"], args)
        self.assertEqual(data["issues_assigned"], [])
        self.assertEqual(data["issues_created"], [])
        self.assertEqual(data["total_issues_assigned"], 0)
        self.assertEqual(data["total_issues_created"], 0)
        self.assertEqual(data["total_issues_assigned_pages"], 1)
        self.assertEqual(data["total_issues_created_pages"], 1)

    def api_api_view_issue_user_token(self):
        """Testhe the api view issues of the flask api with valid user token"""
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "tickets", bare=True)
        )
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        # Create issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #1",
            content="We should work on this",
            user="pingou",
            private=False,
            issue_uid="aaabbbccc1",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #1")
        self.assertEqual(msg.related_prs, [])
        self.assertEqual(msg.id, 1)

        # Check issue
        output = self.app.get("/api/0/test/issue/1")
        self.assertEqual(output.status_code, 200)


if __name__ == "__main__":
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskApiIssuetests
    )
    unittest.TextTestRunner(verbosity=2).run(SUITE)
