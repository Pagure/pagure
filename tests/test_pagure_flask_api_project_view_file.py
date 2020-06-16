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

import pagure.flask_app
import pagure.lib.query
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskApiProjectViewFiletests(tests.Modeltests):
    """ Tests for the flask API of pagure for issue """

    maxDiff = None

    def setUp(self):
        super(PagureFlaskApiProjectViewFiletests, self).setUp()
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))

    def test_view_file_invalid_project(self):
        output = self.app.get("/api/0/invalid/tree")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_view_file_invalid_ref_and_path(self):
        output = self.app.get("/api/0/test/tree/branchname/f/foldername")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "File not found in this git repository",
                "error_code": "EFILENOTFOUND",
            },
        )

    def test_view_file_empty_project(self):
        output = self.app.get("/api/0/test2/tree")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "This git repository is empty",
                "error_code": "EEMPTYGIT",
            },
        )

    def test_view_file_basic(self):
        output = self.app.get("/api/0/test/tree")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "content": [
                    {
                        "content_url": "http://localhost/test/raw/master/"
                        "f/README.rst",
                        "name": "README.rst",
                        "path": "README.rst",
                        "type": "file",
                    }
                ],
                "name": None,
                "type": "folder",
            },
        )

    def test_view_file_with_folder(self):
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        output = self.app.get("/api/0/test/tree")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "content": [
                    {
                        "content_url": "http://localhost/api/0/test/tree/"
                        "master/f/folder1",
                        "name": "folder1",
                        "path": "folder1",
                        "type": "folder",
                    },
                    {
                        "content_url": "http://localhost/test/raw/master/f/"
                        "README.rst",
                        "name": "README.rst",
                        "path": "README.rst",
                        "type": "file",
                    },
                    {
                        "content_url": "http://localhost/test/raw/master/f/"
                        "sources",
                        "name": "sources",
                        "path": "sources",
                        "type": "file",
                    },
                ],
                "name": None,
                "type": "folder",
            },
        )

    def test_view_file_specific_file(self):
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        output = self.app.get("/api/0/test/tree/master/f/README.rst")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "content_url": "http://localhost/test/raw/master/f/README.rst",
                "name": "README.rst",
                "type": "file",
            },
        )

    def test_view_file_invalid_ref(self):
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        output = self.app.get("/api/0/test/tree/invalid/f/folder1")
        print(output.data)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "File not found in this git repository",
                "error_code": "EFILENOTFOUND",
            },
        )

    def test_view_file_invalid_folder(self):
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        output = self.app.get("/api/0/test/tree/master/f/inv/invalid")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "File not found in this git repository",
                "error_code": "EFILENOTFOUND",
            },
        )

    def test_view_file_valid_branch(self):
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        output = self.app.get("/api/0/test/tree/master/f/folder1")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "content": [
                    {
                        "content_url": "http://localhost/api/0/test/tree/"
                        "master/f/folder1/folder2",
                        "name": "folder2",
                        "path": "folder1/folder2",
                        "type": "folder",
                    }
                ],
                "name": "folder1",
                "type": "folder",
            },
        )

    def test_view_file_non_ascii_name(self):
        # View file with a non-ascii name
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "test.git"),
            ncommits=1,
            filename="Šource",
        )
        output = self.app.get("/api/0/test/tree")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True).encode("utf-8"))
        self.assertDictEqual(
            data,
            {
                "content": [
                    {
                        "content_url": "http://localhost/test/raw/master/f/"
                        "README.rst",
                        "name": "README.rst",
                        "path": "README.rst",
                        "type": "file",
                    },
                    {
                        "content_url": "http://localhost/test/raw/master/f/%C5%A0ource",
                        "name": "Šource",
                        "path": "Šource",
                        "type": "file",
                    },
                ],
                "name": None,
                "type": "folder",
            },
        )

    def test_view_file_from_commit(self):
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")

        output = self.app.get("/api/0/test/tree/%s" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "content": [
                    {
                        "content_url": "http://localhost/test/raw/"
                        "%s/f/README.rst" % commit.oid.hex,
                        "name": "README.rst",
                        "path": "README.rst",
                        "type": "file",
                    }
                ],
                "name": None,
                "type": "folder",
            },
        )

    def test_view_file_from_tree(self):
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")

        output = self.app.get(
            "/api/0/test/tree/%s/f/folder1" % commit.tree.oid.hex
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "content": [
                    {
                        "content_url": "http://localhost/api/0/test/tree/"
                        "%s/f/folder1/folder2" % commit.tree.oid.hex,
                        "name": "folder2",
                        "path": "folder1/folder2",
                        "type": "folder",
                    }
                ],
                "name": "folder1",
                "type": "folder",
            },
        )

    def test_view_file_from_tag_hex(self):
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")
        tagger = pygit2.Signature("Alice Doe", "adoe@example.com", 12347, 0)
        tag = repo.create_tag(
            "v1.0_tag",
            commit.oid.hex,
            pygit2.GIT_OBJ_COMMIT,
            tagger,
            "Release v1.0",
        )

        output = self.app.get("/api/0/test/tree/%s" % tag.hex)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "content": [
                    {
                        "content_url": "http://localhost/test/raw/"
                        "%s/f/README.rst" % tag.hex,
                        "name": "README.rst",
                        "path": "README.rst",
                        "type": "file",
                    }
                ],
                "name": None,
                "type": "folder",
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
