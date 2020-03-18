# -*- coding: utf-8 -*-

"""
 Authors:
  Pierre-Yves Chibon <pingou@pingoured.fr>
"""

from __future__ import unicode_literals, absolute_import

import json
import sys
import os

import pygit2

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import tests
import pagure.lib.query


class PagureFlaskApiProjectGitTagstests(tests.Modeltests):
    """ Tests for the flask API of pagure for creating new git tags """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectGitTagstests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        tests.add_commit_git_repo(
            folder=os.path.join(self.path, "repos", "test.git")
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        # token for user = pingou (user_id = 1)
        self.headers = {"Authorization": "token aaabbbcccddd"}

    def test_api_new_git_tags_no_project(self):
        """ Test the api_new_git_tags function.  """
        output = self.app.post("/api/0/foo/git/tags", headers=self.headers)
        self.assertEqual(output.status_code, 404)
        expected_rv = {
            "error": "Project not found",
            "error_code": "ENOPROJECT",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_new_git_tags_invalid_auth(self):
        """ Test the api_new_git_tags function.  """
        headers = self.headers
        headers["Authorization"] += "foo"
        output = self.app.post("/api/0/foo/git/tags", headers=headers)
        self.assertEqual(output.status_code, 401)
        expected_rv = {
            "error": "Project not found",
            "error_code": "EINVALIDTOK",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["error", "error_code", "errors"]
        )
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual("Invalid token", data["errors"])

    def test_api_new_git_tag(self):
        """ Test the api_new_git_tags function.  """

        # Before
        output = self.app.get("/api/0/test/git/tags")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["tags", "total_tags"])
        self.assertEqual(data["tags"], [])
        self.assertEqual(data["total_tags"], 0)

        # Add a tag so that we can list it
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        latest_commit = repo.revparse_single("HEAD")
        data = {
            "tagname": "test-tag-no-message",
            "commit_hash": latest_commit.oid.hex,
            "message": None,
        }

        output = self.app.post(
            "/api/0/test/git/tags", headers=self.headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["tag_created", "tags", "total_tags"]
        )
        self.assertEqual(data["tags"], ["test-tag-no-message"])
        self.assertEqual(data["total_tags"], 1)
        self.assertEqual(data["tag_created"], True)

        output = self.app.get("/api/0/test/git/tags?with_commits=t")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["tags", "total_tags"])
        self.assertEqual(
            data["tags"], {"test-tag-no-message": latest_commit.oid.hex}
        )
        self.assertEqual(data["total_tags"], 1)

    def test_api_new_git_tag_with_commits(self):
        """ Test the api_new_git_tags function.  """

        # Before
        output = self.app.get("/api/0/test/git/tags")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["tags", "total_tags"])
        self.assertEqual(data["tags"], [])
        self.assertEqual(data["total_tags"], 0)

        # Add a tag so that we can list it
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        latest_commit = repo.revparse_single("HEAD")
        data = {
            "tagname": "test-tag-no-message",
            "commit_hash": latest_commit.oid.hex,
            "message": None,
            "with_commits": True,
        }

        output = self.app.post(
            "/api/0/test/git/tags", headers=self.headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["tag_created", "tags", "total_tags"]
        )
        self.assertEqual(
            data["tags"], {"test-tag-no-message": latest_commit.oid.hex}
        )
        self.assertEqual(data["total_tags"], 1)
        self.assertEqual(data["tag_created"], True)

    def test_api_new_git_tag_with_message(self):
        """ Test the api_new_git_tags function.  """

        # Before
        output = self.app.get("/api/0/test/git/tags")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["tags", "total_tags"])
        self.assertEqual(data["tags"], [])
        self.assertEqual(data["total_tags"], 0)

        # Add a tag so that we can list it
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        latest_commit = repo.revparse_single("HEAD")
        data = {
            "tagname": "test-tag-no-message",
            "commit_hash": latest_commit.oid.hex,
            "message": "This is a long annotation\nover multiple lines\n for testing",
        }

        output = self.app.post(
            "/api/0/test/git/tags", headers=self.headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["tag_created", "tags", "total_tags"]
        )
        self.assertEqual(data["tags"], ["test-tag-no-message"])
        self.assertEqual(data["total_tags"], 1)
        self.assertEqual(data["tag_created"], True)

    def test_api_new_git_tag_with_message_twice(self):
        """ Test the api_new_git_tags function.  """

        # Before
        output = self.app.get("/api/0/test/git/tags")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["tags", "total_tags"])
        self.assertEqual(data["tags"], [])
        self.assertEqual(data["total_tags"], 0)

        # Add a tag so that we can list it
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        latest_commit = repo.revparse_single("HEAD")
        data = {
            "tagname": "test-tag-no-message",
            "commit_hash": latest_commit.oid.hex,
            "message": "This is a long annotation\nover multiple lines\n for testing",
        }

        output = self.app.post(
            "/api/0/test/git/tags", headers=self.headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["tag_created", "tags", "total_tags"]
        )
        self.assertEqual(data["tags"], ["test-tag-no-message"])
        self.assertEqual(data["total_tags"], 1)
        self.assertEqual(data["tag_created"], True)

        # Submit the same request/tag a second time to the same commit
        data = {
            "tagname": "test-tag-no-message",
            "commit_hash": latest_commit.oid.hex,
            "message": "This is a long annotation\nover multiple lines\n for testing",
        }

        output = self.app.post(
            "/api/0/test/git/tags", headers=self.headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["tag_created", "tags", "total_tags"]
        )
        self.assertEqual(data["tags"], ["test-tag-no-message"])
        self.assertEqual(data["total_tags"], 1)
        self.assertEqual(data["tag_created"], False)

    def test_api_new_git_tag_user_no_access(self):
        """ Test the api_new_git_tags function.  """

        tests.create_tokens(
            self.session, user_id=2, project_id=2, suffix="foo"
        )
        tests.create_tokens_acl(self.session, token_id="aaabbbcccdddfoo")
        # token for user = foo (user_id = 2)
        headers = {"Authorization": "token aaabbbcccdddfoo"}

        # Before
        output = self.app.get("/api/0/test/git/tags")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["tags", "total_tags"])
        self.assertEqual(data["tags"], [])
        self.assertEqual(data["total_tags"], 0)

        # Add a tag so that we can list it
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        latest_commit = repo.revparse_single("HEAD")
        data = {
            "tagname": "test-tag-no-message",
            "commit_hash": latest_commit.oid.hex,
            "message": "This is a long annotation\nover multiple lines\n for testing",
        }

        output = self.app.post(
            "/api/0/test/git/tags", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["error", "error_code"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])

    def test_api_new_git_tag_user_global_token(self):
        """ Test the api_new_git_tags function.  """

        tests.create_tokens(
            self.session, user_id=2, project_id=None, suffix="foo"
        )
        tests.create_tokens_acl(self.session, token_id="aaabbbcccdddfoo")
        # token for user = foo (user_id = 2)
        headers = {"Authorization": "token aaabbbcccdddfoo"}

        # Before
        output = self.app.get("/api/0/test/git/tags")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["tags", "total_tags"])
        self.assertEqual(data["tags"], [])
        self.assertEqual(data["total_tags"], 0)

        # Add a tag so that we can list it
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        latest_commit = repo.revparse_single("HEAD")
        data = {
            "tagname": "test-tag-no-message",
            "commit_hash": latest_commit.oid.hex,
            "message": "This is a long annotation\nover multiple lines\n for testing",
        }

        output = self.app.post(
            "/api/0/test/git/tags", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["tag_created", "tags", "total_tags"]
        )
        self.assertEqual(data["tags"], ["test-tag-no-message"])
        self.assertEqual(data["total_tags"], 1)
        self.assertEqual(data["tag_created"], True)

    def test_api_new_git_tag_forced(self):
        """ Test the api_new_git_tags function.  """

        # Before
        output = self.app.get("/api/0/test/git/tags")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["tags", "total_tags"])
        self.assertEqual(data["tags"], [])
        self.assertEqual(data["total_tags"], 0)

        # Add a tag so that we can list it
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        latest_commit = repo.revparse_single("HEAD")
        prev_commit = latest_commit.parents[0].oid.hex
        data = {
            "tagname": "test-tag-no-message",
            "commit_hash": prev_commit,
            "message": "This is a long annotation\nover multiple lines\n for testing",
            "with_commits": True,
        }

        output = self.app.post(
            "/api/0/test/git/tags", headers=self.headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["tag_created", "tags", "total_tags"]
        )
        self.assertEqual(data["tags"], {"test-tag-no-message": prev_commit})
        self.assertEqual(data["total_tags"], 1)
        self.assertEqual(data["tag_created"], True)

        # Submit the same request/tag a second time to the same commit
        data = {
            "tagname": "test-tag-no-message",
            "commit_hash": latest_commit.oid.hex,
            "message": "This is a long annotation\nover multiple lines\n for testing",
            "with_commits": True,
            "force": True,
        }

        output = self.app.post(
            "/api/0/test/git/tags", headers=self.headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["tag_created", "tags", "total_tags"]
        )
        self.assertEqual(
            data["tags"], {"test-tag-no-message": latest_commit.oid.hex}
        )
        self.assertEqual(data["total_tags"], 1)
        self.assertEqual(data["tag_created"], True)
