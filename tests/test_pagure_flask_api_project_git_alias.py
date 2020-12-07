# -*- coding: utf-8 -*-

"""
 (c) 2020 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import shutil
import sys
import os

import json
import pygit2
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.api
import pagure.flask_app
import pagure.lib.query
import tests


def set_projects_up(self):
    tests.create_projects(self.session)
    tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
    tests.add_content_git_repo(os.path.join(self.path, "repos", "test.git"))
    tests.create_tokens(self.session)
    tests.create_tokens_acl(self.session)

    self.session.commit()


def set_up_board(self):
    headers = {
        "Authorization": "token aaabbbcccddd",
        "Content-Type": "application/json",
    }

    data = json.dumps({"dev": {"active": True, "tag": "dev"}})
    output = self.app.post("/api/0/test/boards", headers=headers, data=data)
    self.assertEqual(output.status_code, 200)
    data = json.loads(output.get_data(as_text=True))
    self.assertDictEqual(
        data,
        {
            "boards": [
                {
                    "active": True,
                    "full_url": "http://localhost.localdomain/test/boards/dev",
                    "name": "dev",
                    "status": [],
                    "tag": {
                        "tag": "dev",
                        "tag_color": "DeepBlueSky",
                        "tag_description": "",
                    },
                }
            ]
        },
    )


class PagureFlaskApiProjectGitAliastests(tests.SimplePagureTest):
    """ Tests for flask API for branch alias in pagure """

    maxDiff = None

    def setUp(self):
        super(PagureFlaskApiProjectGitAliastests, self).setUp()

        set_projects_up(self)
        self.repo_obj = pygit2.Repository(
            os.path.join(self.path, "repos", "test.git")
        )

    def test_api_git_alias_view_no_project(self):
        output = self.app.get("/api/0/invalid/git/alias")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_api_git_alias_view_empty(self):
        output = self.app.get("/api/0/test/git/alias")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {})

    def test_api_new_git_alias_no_data(self):
        data = "{}"
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        output = self.app.post(
            "/api/0/test/git/alias/new", headers=headers, data=data
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

    def test_api_new_git_alias_invalid_data(self):
        data = json.dumps({"dev": "foobar"})
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        output = self.app.post(
            "/api/0/test/git/alias/new", headers=headers, data=data
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

    def test_api_new_git_alias_missing_data(self):
        data = json.dumps({"alias_from": "mster"})
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        output = self.app.post(
            "/api/0/test/git/alias/new", headers=headers, data=data
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

    def test_api_new_git_alias_no_existant_branch(self):
        data = json.dumps({"alias_from": "master", "alias_to": "main"})
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        output = self.app.post(
            "/api/0/test/git/alias/new", headers=headers, data=data
        )

        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Branch not found in this git repository",
                "error_code": "EBRANCHNOTFOUND",
            },
        )

    def test_api_new_git_alias(self):
        data = json.dumps({"alias_from": "main", "alias_to": "master"})
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        output = self.app.post(
            "/api/0/test/git/alias/new", headers=headers, data=data
        )

        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"refs/heads/main": "refs/heads/master"})

    def test_api_drop_git_alias_no_data(self):
        data = "{}"
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        output = self.app.post(
            "/api/0/test/git/alias/drop", headers=headers, data=data
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

    def test_api_drop_git_alias_invalid_data(self):
        data = json.dumps({"dev": "foobar"})
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        output = self.app.post(
            "/api/0/test/git/alias/drop", headers=headers, data=data
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

    def test_api_drop_git_alias_missing_data(self):
        data = json.dumps({"alias_from": "mster"})
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        output = self.app.post(
            "/api/0/test/git/alias/drop", headers=headers, data=data
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

    def test_api_drop_git_alias_no_existant_branch(self):
        data = json.dumps({"alias_from": "master", "alias_to": "main"})
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        output = self.app.post(
            "/api/0/test/git/alias/drop", headers=headers, data=data
        )

        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Branch not found in this git repository",
                "error_code": "EBRANCHNOTFOUND",
            },
        )

    def test_api_drop_git_alias(self):
        data = json.dumps({"alias_from": "main", "alias_to": "master"})
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        output = self.app.post(
            "/api/0/test/git/alias/drop", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
