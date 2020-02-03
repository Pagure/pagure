# -*- coding: utf-8 -*-

"""
 (c) 2020 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import json
import unittest
import shutil
import sys
import tempfile
import os

import pygit2
from celery.result import EagerResult
from mock import patch, Mock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.api
import pagure.flask_app
import pagure.lib.query
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskApiProjectDeleteProjecttests(tests.Modeltests):
    """ Tests for the flask API of pagure for deleting projects """

    maxDiff = None

    def setUp(self):
        super(PagureFlaskApiProjectDeleteProjecttests, self).setUp()
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, "repos", "docs"), bare=True
        )
        tests.create_projects_git(
            os.path.join(self.path, "repos", "tickets"), bare=True
        )
        tests.create_projects_git(
            os.path.join(self.path, "repos", "requests"), bare=True
        )
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        tests.create_tokens(self.session, project_id=2, suffix="_test2")
        tests.create_tokens_acl(self.session, token_id="aaabbbcccddd_test2")
        tests.create_tokens(self.session, user_id=2, suffix="_foo")
        tests.create_tokens_acl(self.session, token_id="aaabbbcccddd_foo")

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        project.read_only = False
        self.session.add(project)
        self.session.commit()

    def test_delete_project_no_header(self):
        output = self.app.post("/api/0/invalid/delete")
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])

    def test_delete_project_invalid_project(self):
        headers = {"Authorization": "token aaabbbcccddd"}

        output = self.app.post("/api/0/invalid/delete", headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.ENOPROJECT.name, data["error_code"]
        )
        self.assertEqual(pagure.api.APIERROR.ENOPROJECT.value, data["error"])

    def test_delete_project_invalid_token_project(self):
        headers = {"Authorization": "token aaabbbcccddd"}

        output = self.app.post("/api/0/test2/delete", headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])

    def test_delete_project_read_only_project(self):
        headers = {"Authorization": "token aaabbbcccddd_test2"}

        output = self.app.post("/api/0/test2/delete", headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(pagure.api.APIERROR.ENOCODE.name, data["error_code"])
        error = "The ACLs of this project are being refreshed in the backend this prevents the project from being deleted. Please wait for this task to finish before trying again. Thanks!"
        self.assertEqual(data["error"], error)

    def test_delete_project_not_allowed(self):
        headers = {"Authorization": "token aaabbbcccddd_foo"}

        output = self.app.post("/api/0/test/delete", headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.ENOTHIGHENOUGH.name, data["error_code"]
        )
        self.assertEqual(
            pagure.api.APIERROR.ENOTHIGHENOUGH.value, data["error"]
        )

    @patch.dict("pagure.config.config", {"ENABLE_DEL_PROJECTS": False})
    def test_delete_project_not_allowed_by_config(self):
        headers = {"Authorization": "token aaabbbcccddd_test2"}

        output = self.app.post("/api/0/test2/delete", headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.ENOPROJECT.name, data["error_code"]
        )
        self.assertEqual(pagure.api.APIERROR.ENOPROJECT.value, data["error"])

    def test_delete_project(self):
        headers = {"Authorization": "token aaabbbcccddd"}

        projects = pagure.lib.query.search_projects(session=self.session)
        self.assertEqual(len(projects), 3)
        for frag in [".", "docs", "tickets", "requests"]:
            self.assertTrue(
                os.path.exists(
                    os.path.join(self.path, "repos", frag, "test.git")
                )
            )

        output = self.app.post("/api/0/test/delete", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for key in ["date_created", "date_modified"]:
            data["project"][key] = "1595341690"
        self.assertEqual(
            data,
            {
                "message": "Project deleted",
                "project": {
                    "access_groups": {
                        "admin": [],
                        "collaborator": [],
                        "commit": [],
                        "ticket": [],
                    },
                    "access_users": {
                        "admin": [],
                        "collaborator": [],
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
                    "date_created": "1595341690",
                    "date_modified": "1595341690",
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
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                },
            },
        )

        projects = pagure.lib.query.search_projects(session=self.session)
        self.assertEqual(len(projects), 2)
        for frag in [".", "docs", "tickets", "requests"]:
            self.assertFalse(
                os.path.exists(
                    os.path.join(self.path, "repos", frag, "test.git")
                )
            )
