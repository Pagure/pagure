# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Karsten Hopp <karsten@redhat.com>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import json
import unittest
import pagure_messages
import shutil
import sys
import tempfile
import os

import pygit2
from celery.result import EagerResult
from fedora_messaging import api, testing
from mock import ANY, patch, Mock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.flask_app
import pagure.lib.query
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskApiProjecttests(tests.Modeltests):
    """ Tests for the flask API of pagure for issue """

    maxDiff = None

    def setUp(self):
        super(PagureFlaskApiProjecttests, self).setUp()
        self.gga_patcher = patch(
            "pagure.lib.tasks.generate_gitolite_acls.delay"
        )
        self.mock_gen_acls = self.gga_patcher.start()
        task_result = EagerResult("abc-1234", True, "SUCCESS")
        self.mock_gen_acls.return_value = task_result

    def tearDown(self):
        self.gga_patcher.stop()
        super(PagureFlaskApiProjecttests, self).tearDown()

    def test_api_git_tags(self):
        """ Test the api_git_tags method of the flask api. """
        tests.create_projects(self.session)

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, "repos", "test.git")
        repo = pygit2.init_repository(gitrepo, bare=True)

        newpath = tempfile.mkdtemp(prefix="pagure-fork-test")
        repopath = os.path.join(newpath, "test")
        clone_repo = pygit2.clone_repository(gitrepo, repopath)

        # Create a file in that git repo
        with open(os.path.join(repopath, "sources"), "w") as stream:
            stream.write("foo\n bar")
        clone_repo.index.add("sources")
        clone_repo.index.write()

        # Commits the files added
        tree = clone_repo.index.write_tree()
        author = pygit2.Signature("Alice Author", "alice@authors.tld")
        committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
        clone_repo.create_commit(
            "refs/heads/master",  # the name of the reference to update
            author,
            committer,
            "Add sources file for testing",
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [],
        )
        refname = "refs/heads/master:refs/heads/master"
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Tag our first commit
        first_commit = repo.revparse_single("HEAD")
        tagger = pygit2.Signature("Alice Doe", "adoe@example.com", 12347, 0)
        repo.create_tag(
            "0.0.1",
            first_commit.oid.hex,
            pygit2.GIT_OBJ_COMMIT,
            tagger,
            "Release 0.0.1",
        )

        # Check tags
        output = self.app.get("/api/0/test/git/tags")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"tags": ["0.0.1"], "total_tags": 1})

        # Check tags with commits
        output = self.app.get("/api/0/test/git/tags?with_commits=True")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["tags"]["0.0.1"] = "bb8fa2aa199da08d6085e1c9badc3d83d188d38c"
        self.assertDictEqual(
            data,
            {
                "tags": {"0.0.1": "bb8fa2aa199da08d6085e1c9badc3d83d188d38c"},
                "total_tags": 1,
            },
        )

        shutil.rmtree(newpath)

    def test_api_git_branches_no_repo(self):
        """ Test the api_git_branches method of the flask api when there is no
        repo on a project.
        """
        tests.create_projects(self.session)
        output = self.app.get("/api/0/test/git/branches")
        self.assertEqual(output.status_code, 404)

    def test_api_git_urls(self):
        """ Test the api_project_git_urls method of the flask api.
        """
        tests.create_projects(self.session)
        output = self.app.get("/api/0/test/git/urls")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "urls": {
                "git": "git://localhost.localdomain/test.git",
                "ssh": "ssh://git@localhost.localdomain/test.git",
            },
            "total_urls": 2,
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_git_urls_no_project(self):
        """ Test the api_project_git_urls method of the flask api when there is
        no project.
        """
        output = self.app.get("/api/0/test1234/git/urls")
        self.assertEqual(output.status_code, 404)
        expected_rv = {
            "error": "Project not found",
            "error_code": "ENOPROJECT",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    @patch.dict("pagure.config.config", {"PRIVATE_PROJECTS": True})
    def test_api_git_urls_private_project(self):
        """ Test the api_project_git_urls method of the flask api when the
        project is private.
        """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session, "aaabbbcccddd")
        headers = {"Authorization": "token aaabbbcccddd"}

        test_project = pagure.lib.query._get_project(self.session, "test")
        test_project.private = True
        self.session.add(test_project)
        self.session.commit()

        output = self.app.get("/api/0/test/git/urls", headers=headers)
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "urls": {
                "git": "git://localhost.localdomain/test.git",
                "ssh": "ssh://git@localhost.localdomain/test.git",
            },
            "total_urls": 2,
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    @patch.dict("pagure.config.config", {"PRIVATE_PROJECTS": True})
    def test_api_git_urls_private_project_no_login(self):
        """ Test the api_project_git_urls method of the flask api when the
        project is private and the user is not logged in.
        """
        tests.create_projects(self.session)
        test_project = pagure.lib.query._get_project(self.session, "test")
        test_project.private = True
        self.session.add(test_project)
        self.session.commit()

        output = self.app.get("/api/0/test/git/urls")
        self.assertEqual(output.status_code, 404)
        expected_rv = {
            "error": "Project not found",
            "error_code": "ENOPROJECT",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_projects_pattern(self):
        """ Test the api_projects method of the flask api. """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/projects?pattern=test")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["projects"][0]["date_created"] = "1436527638"
        data["projects"][0]["date_modified"] = "1436527638"
        del data["pagination"]
        expected_data = {
            "args": {
                "fork": None,
                "namespace": None,
                "owner": None,
                "page": 1,
                "pattern": "test",
                "per_page": 20,
                "short": False,
                "tags": [],
                "username": None,
            },
            "projects": [
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "test project #1",
                    "fullname": "test",
                    "url_path": "test",
                    "full_url": "http://localhost.localdomain/test",
                    "id": 1,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou",
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "url_path": "user/pingou",
                    },
                }
            ],
            "total_projects": 1,
        }
        self.assertDictEqual(data, expected_data)

    def test_api_projects_pattern_short(self):
        """ Test the api_projects method of the flask api. """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/projects?pattern=te*&short=1")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        del data["pagination"]
        expected_data = {
            "args": {
                "fork": None,
                "namespace": None,
                "owner": None,
                "page": 1,
                "pattern": "te*",
                "per_page": 20,
                "short": True,
                "tags": [],
                "username": None,
            },
            "projects": [
                {
                    "description": "test project #1",
                    "fullname": "test",
                    "name": "test",
                    "namespace": None,
                },
                {
                    "description": "test project #2",
                    "fullname": "test2",
                    "name": "test2",
                    "namespace": None,
                },
                {
                    "description": "namespaced test project",
                    "fullname": "somenamespace/test3",
                    "name": "test3",
                    "namespace": "somenamespace",
                },
            ],
            "total_projects": 3,
        }
        self.maxDiff = None
        self.assertDictEqual(data, expected_data)

    def test_api_projects_owner(self):
        """ Test the api_projects method of the flask api. """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/projects?owner=foo")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        del data["pagination"]
        expected_data = {
            "args": {
                "fork": None,
                "namespace": None,
                "owner": "foo",
                "page": 1,
                "pattern": None,
                "per_page": 20,
                "short": False,
                "tags": [],
                "username": None,
            },
            "projects": [],
            "total_projects": 0,
        }
        self.maxDiff = None
        self.assertDictEqual(data, expected_data)

    def test_api_projects_not_owner(self):
        """ Test the api_projects method of the flask api. """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/projects?owner=!foo&short=1")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        del data["pagination"]
        expected_data = {
            "args": {
                "fork": None,
                "namespace": None,
                "owner": "!foo",
                "page": 1,
                "pattern": None,
                "per_page": 20,
                "short": True,
                "tags": [],
                "username": None,
            },
            "projects": [
                {
                    "description": "test project #1",
                    "fullname": "test",
                    "name": "test",
                    "namespace": None,
                },
                {
                    "description": "test project #2",
                    "fullname": "test2",
                    "name": "test2",
                    "namespace": None,
                },
                {
                    "description": "namespaced test project",
                    "fullname": "somenamespace/test3",
                    "name": "test3",
                    "namespace": "somenamespace",
                },
            ],
            "total_projects": 3,
        }
        self.maxDiff = None
        self.assertDictEqual(data, expected_data)

    def test_api_projects(self):
        """ Test the api_projects method of the flask api. """
        tests.create_projects(self.session)

        # Check before adding
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.tags, [])

        # Adding a tag
        output = pagure.lib.query.update_tags(
            self.session, repo, "infra", "pingou"
        )
        self.assertEqual(output, ["Project tagged with: infra"])

        # Check after adding
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.tags), 1)
        self.assertEqual(repo.tags_text, ["infra"])

        # Check the API
        output = self.app.get("/api/0/projects?tags=inf")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        null = None
        del data["pagination"]
        self.assertDictEqual(
            data,
            {
                "total_projects": 0,
                "projects": [],
                "args": {
                    "fork": None,
                    "namespace": None,
                    "owner": None,
                    "page": 1,
                    "pattern": None,
                    "per_page": 20,
                    "short": False,
                    "tags": ["inf"],
                    "username": None,
                },
            },
        )
        output = self.app.get("/api/0/projects?tags=infra")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["projects"][0]["date_created"] = "1436527638"
        data["projects"][0]["date_modified"] = "1436527638"
        del data["pagination"]
        expected_data = {
            "args": {
                "fork": None,
                "namespace": None,
                "owner": None,
                "page": 1,
                "pattern": None,
                "per_page": 20,
                "short": False,
                "tags": ["infra"],
                "username": None,
            },
            "projects": [
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "test project #1",
                    "full_url": "http://localhost.localdomain/test",
                    "fullname": "test",
                    "url_path": "test",
                    "id": 1,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": ["infra"],
                    "user": {
                        "name": "pingou",
                        "fullname": "PY C",
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "url_path": "user/pingou",
                    },
                }
            ],
            "total_projects": 1,
        }
        self.assertDictEqual(data, expected_data)

        output = self.app.get("/api/0/projects?owner=pingou")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["projects"][0]["date_created"] = "1436527638"
        data["projects"][0]["date_modified"] = "1436527638"
        data["projects"][1]["date_created"] = "1436527638"
        data["projects"][1]["date_modified"] = "1436527638"
        data["projects"][2]["date_created"] = "1436527638"
        data["projects"][2]["date_modified"] = "1436527638"
        del data["pagination"]
        expected_data = {
            "args": {
                "fork": None,
                "namespace": None,
                "owner": "pingou",
                "page": 1,
                "pattern": None,
                "per_page": 20,
                "short": False,
                "tags": [],
                "username": None,
            },
            "projects": [
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "test project #1",
                    "full_url": "http://localhost.localdomain/test",
                    "fullname": "test",
                    "url_path": "test",
                    "id": 1,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": ["infra"],
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                        "full_url": "http://localhost.localdomain/user/pingou",
                    },
                },
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "test project #2",
                    "fullname": "test2",
                    "full_url": "http://localhost.localdomain/test2",
                    "url_path": "test2",
                    "id": 2,
                    "milestones": {},
                    "name": "test2",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                        "fullname": "PY C",
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                },
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "namespaced test project",
                    "fullname": "somenamespace/test3",
                    "url_path": "somenamespace/test3",
                    "full_url": "http://localhost.localdomain/somenamespace/test3",
                    "id": 3,
                    "milestones": {},
                    "name": "test3",
                    "namespace": "somenamespace",
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                        "fullname": "PY C",
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                },
            ],
            "total_projects": 3,
        }
        self.assertDictEqual(data, expected_data)

        output = self.app.get("/api/0/projects?username=pingou")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["projects"][0]["date_created"] = "1436527638"
        data["projects"][0]["date_modified"] = "1436527638"
        data["projects"][1]["date_created"] = "1436527638"
        data["projects"][1]["date_modified"] = "1436527638"
        data["projects"][2]["date_created"] = "1436527638"
        data["projects"][2]["date_modified"] = "1436527638"
        del data["pagination"]
        expected_data = {
            "args": {
                "fork": None,
                "namespace": None,
                "owner": None,
                "page": 1,
                "pattern": None,
                "per_page": 20,
                "short": False,
                "tags": [],
                "username": "pingou",
            },
            "projects": [
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "test project #1",
                    "fullname": "test",
                    "url_path": "test",
                    "full_url": "http://localhost.localdomain/test",
                    "id": 1,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": ["infra"],
                    "user": {
                        "fullname": "PY C",
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                },
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "test project #2",
                    "fullname": "test2",
                    "url_path": "test2",
                    "full_url": "http://localhost.localdomain/test2",
                    "id": 2,
                    "milestones": {},
                    "name": "test2",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou",
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "url_path": "user/pingou",
                    },
                },
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "namespaced test project",
                    "fullname": "somenamespace/test3",
                    "url_path": "somenamespace/test3",
                    "full_url": "http://localhost.localdomain/somenamespace/test3",
                    "id": 3,
                    "milestones": {},
                    "name": "test3",
                    "namespace": "somenamespace",
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou",
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "url_path": "user/pingou",
                    },
                },
            ],
            "total_projects": 3,
        }
        self.assertDictEqual(data, expected_data)

        output = self.app.get("/api/0/projects?username=pingou&tags=infra")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["projects"][0]["date_created"] = "1436527638"
        data["projects"][0]["date_modified"] = "1436527638"
        del data["pagination"]
        expected_data = {
            "args": {
                "fork": None,
                "namespace": None,
                "owner": None,
                "page": 1,
                "pattern": None,
                "per_page": 20,
                "short": False,
                "tags": ["infra"],
                "username": "pingou",
            },
            "projects": [
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "test project #1",
                    "fullname": "test",
                    "url_path": "test",
                    "full_url": "http://localhost.localdomain/test",
                    "id": 1,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": ["infra"],
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou",
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "url_path": "user/pingou",
                    },
                }
            ],
            "total_projects": 1,
        }
        self.assertDictEqual(data, expected_data)

        output = self.app.get("/api/0/projects?namespace=somenamespace")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["projects"][0]["date_created"] = "1436527638"
        data["projects"][0]["date_modified"] = "1436527638"
        del data["pagination"]
        expected_data = {
            "args": {
                "fork": None,
                "owner": None,
                "page": 1,
                "namespace": "somenamespace",
                "per_page": 20,
                "pattern": None,
                "short": False,
                "tags": [],
                "username": None,
            },
            "projects": [
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "namespaced test project",
                    "fullname": "somenamespace/test3",
                    "url_path": "somenamespace/test3",
                    "full_url": "http://localhost.localdomain/somenamespace/test3",
                    "id": 3,
                    "milestones": {},
                    "name": "test3",
                    "namespace": "somenamespace",
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou",
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "url_path": "user/pingou",
                    },
                }
            ],
            "total_projects": 1,
        }
        self.assertDictEqual(data, expected_data)

    def test_api_project(self):
        """ Test the api_project method of the flask api. """
        tests.create_projects(self.session)

        # Check before adding
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.tags, [])

        # Adding a tag
        output = pagure.lib.query.update_tags(
            self.session, repo, "infra", "pingou"
        )
        self.assertEqual(output, ["Project tagged with: infra"])

        # Check after adding
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.tags), 1)
        self.assertEqual(repo.tags_text, ["infra"])

        # Check the API

        # Non-existing project
        output = self.app.get("/api/0/random")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error_code": "ENOPROJECT", "error": "Project not found"}
        )

        # Existing project
        output = self.app.get("/api/0/test")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1436527638"
        data["date_modified"] = "1436527638"
        expected_data = {
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
            "date_created": "1436527638",
            "date_modified": "1436527638",
            "description": "test project #1",
            "fullname": "test",
            "url_path": "test",
            "full_url": "http://localhost.localdomain/test",
            "id": 1,
            "milestones": {},
            "name": "test",
            "namespace": None,
            "parent": None,
            "priorities": {},
            "tags": ["infra"],
            "user": {
                "fullname": "PY C",
                "name": "pingou",
                "full_url": "http://localhost.localdomain/user/pingou",
                "url_path": "user/pingou",
            },
        }
        self.assertDictEqual(data, expected_data)

    def test_api_project_collaborators(self):
        """ Test the api_project method of the flask api. """
        tests.create_projects(self.session)
        tests.create_user(self.session, "ralph", "Ralph B", ["ralph@b.org"])
        tests.create_user(self.session, "nils", "Nils P", ["nils@p.net"])

        # Add a couple of collaborators
        project = pagure.lib.query._get_project(self.session, "test")
        pagure.lib.query.add_user_to_project(
            self.session,
            project,
            new_user="ralph",
            user="pingou",
            access="collaborator",
            branches="f*,epel*",
        )
        pagure.lib.query.add_user_to_project(
            self.session,
            project,
            new_user="nils",
            user="pingou",
            access="collaborator",
            branches="epel*",
        )
        self.session.commit()

        # Add a collaborator group
        msg = pagure.lib.query.add_group(
            self.session,
            group_name="some_group",
            display_name="Some Group",
            description=None,
            group_type="bar",
            user="pingou",
            is_admin=False,
            blacklist=[],
        )
        pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="some_group",
            user="pingou",
            access="collaborator",
            branches="features/*",
        )
        self.session.commit()

        # Existing project
        output = self.app.get("/api/0/test")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1436527638"
        data["date_modified"] = "1436527638"
        expected_data = {
            "access_groups": {
                "admin": [],
                "collaborator": ["some_group"],
                "commit": [],
                "ticket": [],
            },
            "access_users": {
                "admin": [],
                "collaborator": ["nils", "ralph"],
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
            "date_created": "1436527638",
            "date_modified": "1436527638",
            "description": "test project #1",
            "full_url": "http://localhost.localdomain/test",
            "fullname": "test",
            "url_path": "test",
            "id": 1,
            "milestones": {},
            "name": "test",
            "namespace": None,
            "parent": None,
            "priorities": {},
            "tags": [],
            "user": {
                "fullname": "PY C",
                "name": "pingou",
                "url_path": "user/pingou",
                "full_url": "http://localhost.localdomain/user/pingou",
            },
        }
        self.assertDictEqual(data, expected_data)

    def test_api_project_group(self):
        """ Test the api_project method of the flask api. """
        tests.create_projects(self.session)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Adding a tag
        output = pagure.lib.query.update_tags(
            self.session, repo, "infra", "pingou"
        )
        self.assertEqual(output, ["Project tagged with: infra"])

        # Check after adding
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.tags), 1)
        self.assertEqual(repo.tags_text, ["infra"])

        # Add a group to the project
        msg = pagure.lib.query.add_group(
            self.session,
            group_name="some_group",
            display_name="Some Group",
            description=None,
            group_type="bar",
            user="foo",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        group = pagure.lib.query.search_groups(
            self.session, group_name="some_group"
        )

        pagure.lib.query.add_group_to_project(
            self.session,
            project,
            new_group="some_group",
            user="pingou",
            access="commit",
            create=False,
            is_admin=True,
        )
        self.session.commit()

        # Check the API

        # Existing project
        output = self.app.get("/api/0/test?expand_group=1")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1436527638"
        data["date_modified"] = "1436527638"
        expected_data = {
            "access_groups": {
                "admin": [],
                "collaborator": [],
                "commit": ["some_group"],
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
            "date_created": "1436527638",
            "date_modified": "1436527638",
            "description": "test project #1",
            "full_url": "http://localhost.localdomain/test",
            "fullname": "test",
            "url_path": "test",
            "group_details": {"some_group": ["foo"]},
            "id": 1,
            "milestones": {},
            "name": "test",
            "namespace": None,
            "parent": None,
            "priorities": {},
            "tags": ["infra"],
            "user": {
                "fullname": "PY C",
                "name": "pingou",
                "url_path": "user/pingou",
                "full_url": "http://localhost.localdomain/user/pingou",
            },
        }
        self.assertDictEqual(data, expected_data)

    def test_api_project_group_but_no_group(self):
        """ Test the api_project method of the flask api when asking for
        group details while there are none associated.
        """
        tests.create_projects(self.session)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Adding a tag
        output = pagure.lib.query.update_tags(
            self.session, repo, "infra", "pingou"
        )
        self.assertEqual(output, ["Project tagged with: infra"])

        # Check after adding
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.tags), 1)
        self.assertEqual(repo.tags_text, ["infra"])

        # Check the API

        # Existing project
        output = self.app.get("/api/0/test?expand_group=0")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1436527638"
        data["date_modified"] = "1436527638"
        expected_data = {
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
            "date_created": "1436527638",
            "date_modified": "1436527638",
            "description": "test project #1",
            "full_url": "http://localhost.localdomain/test",
            "fullname": "test",
            "url_path": "test",
            "id": 1,
            "milestones": {},
            "name": "test",
            "namespace": None,
            "parent": None,
            "priorities": {},
            "tags": ["infra"],
            "user": {
                "fullname": "PY C",
                "name": "pingou",
                "url_path": "user/pingou",
                "full_url": "http://localhost.localdomain/user/pingou",
            },
        }
        self.assertDictEqual(data, expected_data)

    def test_api_projects_pagination(self):
        """ Test the api_projects method of the flask api with pagination. """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/projects?page=1")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for i in range(3):
            data["projects"][i]["date_created"] = "1436527638"
            data["projects"][i]["date_modified"] = "1436527638"
        expected_data = {
            "args": {
                "fork": None,
                "namespace": None,
                "owner": None,
                "page": 1,
                "per_page": 20,
                "pattern": None,
                "short": False,
                "tags": [],
                "username": None,
            },
            "pagination": {
                "next": None,
                "page": 1,
                "pages": 1,
                "per_page": 20,
                "prev": None,
            },
            "projects": [
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "test project #1",
                    "fullname": "test",
                    "url_path": "test",
                    "full_url": "http://localhost.localdomain/test",
                    "id": 1,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                        "full_url": "http://localhost.localdomain/user/pingou",
                    },
                },
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "test project #2",
                    "fullname": "test2",
                    "url_path": "test2",
                    "full_url": "http://localhost.localdomain/test2",
                    "id": 2,
                    "milestones": {},
                    "name": "test2",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                        "full_url": "http://localhost.localdomain/user/pingou",
                    },
                },
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "namespaced test project",
                    "fullname": "somenamespace/test3",
                    "url_path": "somenamespace/test3",
                    "full_url": "http://localhost.localdomain/somenamespace/test3",
                    "id": 3,
                    "milestones": {},
                    "name": "test3",
                    "namespace": "somenamespace",
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                        "full_url": "http://localhost.localdomain/user/pingou",
                    },
                },
            ],
            "total_projects": 3,
        }
        # Test URLs
        self.assertURLEqual(
            data["pagination"].pop("first"),
            "http://localhost/api/0/projects?per_page=20&page=1",
        )
        self.assertURLEqual(
            data["pagination"].pop("last"),
            "http://localhost/api/0/projects?per_page=20&page=1",
        )
        self.assertDictEqual(data, expected_data)

    def test_api_projects_pagination_per_page(self):
        """ Test the api_projects method of the flask api with pagination and
        the `per_page` argument set. """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/projects?page=2&per_page=2")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["projects"][0]["date_created"] = "1436527638"
        data["projects"][0]["date_modified"] = "1436527638"
        expected_data = {
            "args": {
                "fork": None,
                "namespace": None,
                "owner": None,
                "page": 2,
                "per_page": 2,
                "pattern": None,
                "short": False,
                "tags": [],
                "username": None,
            },
            "pagination": {"next": None, "page": 2, "pages": 2, "per_page": 2},
            "projects": [
                {
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
                    "date_created": "1436527638",
                    "date_modified": "1436527638",
                    "description": "namespaced test project",
                    "fullname": "somenamespace/test3",
                    "url_path": "somenamespace/test3",
                    "full_url": "http://localhost.localdomain/somenamespace/test3",
                    "id": 3,
                    "milestones": {},
                    "name": "test3",
                    "namespace": "somenamespace",
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                        "full_url": "http://localhost.localdomain/user/pingou",
                    },
                }
            ],
            "total_projects": 3,
        }
        self.assertURLEqual(
            data["pagination"].pop("first"),
            "http://localhost/api/0/projects?per_page=2&page=1",
        )
        self.assertURLEqual(
            data["pagination"].pop("prev"),
            "http://localhost/api/0/projects?per_page=2&page=1",
        )
        self.assertURLEqual(
            data["pagination"].pop("last"),
            "http://localhost/api/0/projects?per_page=2&page=2",
        )
        self.assertDictEqual(data, expected_data)

    def test_api_projects_pagination_invalid_page(self):
        """ Test the api_projects method of the flask api when an invalid page
        value is entered. """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/projects?page=-3")
        self.assertEqual(output.status_code, 400)

    def test_api_projects_pagination_invalid_page_str(self):
        """ Test the api_projects method of the flask api when an invalid type
        for the page value is entered. """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/projects?page=abcd")
        self.assertEqual(output.status_code, 400)

    def test_api_projects_pagination_invalid_per_page_too_low(self):
        """ Test the api_projects method of the flask api when a per_page
        value is below 1. """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/projects?page=1&per_page=0")
        self.assertEqual(output.status_code, 400)
        error = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            error["error"], "The per_page value must be between 1 and 100"
        )

    def test_api_projects_pagination_invalid_per_page_too_high(self):
        """ Test the api_projects method of the flask api when a per_page
        value is above 100. """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/projects?page=1&per_page=101")
        self.assertEqual(output.status_code, 400)
        error = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            error["error"], "The per_page value must be between 1 and 100"
        )

    def test_api_projects_pagination_invalid_per_page_str(self):
        """ Test the api_projects method of the flask api when an invalid type
        for the per_page value is entered. """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/projects?page=1&per_page=abcd")
        self.assertEqual(output.status_code, 400)

    def test_api_projects_pagination_beyond_last_page(self):
        """ Test the api_projects method of the flask api when a page value
        that is larger than the last page is entered. """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/projects?page=99999")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertURLEqual(
            data["pagination"].pop("first"),
            "http://localhost/api/0/projects?per_page=20&page=1",
        )
        self.assertURLEqual(
            data["pagination"].pop("last"),
            "http://localhost/api/0/projects?per_page=20&page=1",
        )
        self.assertURLEqual(
            data["pagination"].pop("prev"),
            "http://localhost/api/0/projects?per_page=20&page=99998",
        )
        self.assertEqual(
            data,
            {
                "args": {
                    "fork": None,
                    "namespace": None,
                    "owner": None,
                    "page": 99999,
                    "pattern": None,
                    "per_page": 20,
                    "short": False,
                    "tags": [],
                    "username": None,
                },
                "pagination": {
                    "next": None,
                    "page": 99999,
                    "pages": 1,
                    "per_page": 20,
                },
                "projects": [],
                "total_projects": 3,
            },
        )

    def test_api_modify_project_main_admin(self):
        """ Test the api_modify_project method of the flask api when the
        request is to change the main_admin of the project. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")
        headers = {"Authorization": "token aaabbbcccddd"}

        output = self.app.patch(
            "/api/0/test", headers=headers, data={"main_admin": "foo"}
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1496338274"
        data["date_modified"] = "1496338274"
        expected_output = {
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
                "owner": ["foo"],
                "ticket": [],
            },
            "close_status": [
                "Invalid",
                "Insufficient data",
                "Fixed",
                "Duplicate",
            ],
            "custom_keys": [],
            "date_created": "1496338274",
            "date_modified": "1496338274",
            "description": "test project #1",
            "fullname": "test",
            "url_path": "test",
            "full_url": "http://localhost.localdomain/test",
            "id": 1,
            "milestones": {},
            "name": "test",
            "namespace": None,
            "parent": None,
            "priorities": {},
            "tags": [],
            "user": {
                "default_email": "foo@bar.com",
                "emails": ["foo@bar.com"],
                "fullname": "foo bar",
                "name": "foo",
                "url_path": "user/foo",
                "full_url": "http://localhost.localdomain/user/foo",
            },
        }
        self.assertEqual(data, expected_output)

    def test_api_modify_project_main_admin_retain_access(self):
        """ Test the api_modify_project method of the flask api when the
        request is to change the main_admin of the project and retain_access
        is true. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")
        headers = {"Authorization": "token aaabbbcccddd"}

        output = self.app.patch(
            "/api/0/test",
            headers=headers,
            data={"main_admin": "foo", "retain_access": True},
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1496338274"
        data["date_modified"] = "1496338274"
        expected_output = {
            "access_groups": {
                "admin": [],
                "collaborator": [],
                "commit": [],
                "ticket": [],
            },
            "access_users": {
                "admin": ["pingou"],
                "collaborator": [],
                "commit": [],
                "owner": ["foo"],
                "ticket": [],
            },
            "close_status": [
                "Invalid",
                "Insufficient data",
                "Fixed",
                "Duplicate",
            ],
            "custom_keys": [],
            "date_created": "1496338274",
            "date_modified": "1496338274",
            "description": "test project #1",
            "full_url": "http://localhost.localdomain/test",
            "fullname": "test",
            "url_path": "test",
            "id": 1,
            "milestones": {},
            "name": "test",
            "namespace": None,
            "parent": None,
            "priorities": {},
            "tags": [],
            "user": {
                "default_email": "foo@bar.com",
                "emails": ["foo@bar.com"],
                "fullname": "foo bar",
                "name": "foo",
                "url_path": "user/foo",
                "full_url": "http://localhost.localdomain/user/foo",
            },
        }
        self.assertEqual(data, expected_output)

    def test_api_modify_project_main_admin_retain_access_already_user(self):
        """ Test the api_modify_project method of the flask api when the
        request is to change the main_admin of the project and retain_access
        is true and the user becoming the main_admin already has access. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")
        headers = {"Authorization": "token aaabbbcccddd"}

        project = pagure.lib.query._get_project(self.session, "test")
        pagure.lib.query.add_user_to_project(
            self.session,
            project,
            new_user="foo",
            user="pingou",
            access="commit",
        )
        self.session.commit()

        output = self.app.patch(
            "/api/0/test",
            headers=headers,
            data={"main_admin": "foo", "retain_access": True},
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1496338274"
        data["date_modified"] = "1496338274"
        expected_output = {
            "access_groups": {
                "admin": [],
                "collaborator": [],
                "commit": [],
                "ticket": [],
            },
            "access_users": {
                "admin": ["pingou"],
                "collaborator": [],
                "commit": [],
                "owner": ["foo"],
                "ticket": [],
            },
            "close_status": [
                "Invalid",
                "Insufficient data",
                "Fixed",
                "Duplicate",
            ],
            "custom_keys": [],
            "date_created": "1496338274",
            "date_modified": "1496338274",
            "description": "test project #1",
            "full_url": "http://localhost.localdomain/test",
            "fullname": "test",
            "url_path": "test",
            "id": 1,
            "milestones": {},
            "name": "test",
            "namespace": None,
            "parent": None,
            "priorities": {},
            "tags": [],
            "user": {
                "default_email": "foo@bar.com",
                "emails": ["foo@bar.com"],
                "fullname": "foo bar",
                "name": "foo",
                "url_path": "user/foo",
                "full_url": "http://localhost.localdomain/user/foo",
            },
        }
        self.assertEqual(data, expected_output)

    def test_api_modify_project_main_admin_json(self):
        """ Test the api_modify_project method of the flask api when the
        request is to change the main_admin of the project using JSON. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        output = self.app.patch(
            "/api/0/test",
            headers=headers,
            data=json.dumps({"main_admin": "foo"}),
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1496338274"
        data["date_modified"] = "1496338274"
        expected_output = {
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
                "owner": ["foo"],
                "ticket": [],
            },
            "close_status": [
                "Invalid",
                "Insufficient data",
                "Fixed",
                "Duplicate",
            ],
            "custom_keys": [],
            "date_created": "1496338274",
            "date_modified": "1496338274",
            "description": "test project #1",
            "fullname": "test",
            "url_path": "test",
            "full_url": "http://localhost.localdomain/test",
            "id": 1,
            "milestones": {},
            "name": "test",
            "namespace": None,
            "parent": None,
            "priorities": {},
            "tags": [],
            "user": {
                "default_email": "foo@bar.com",
                "emails": ["foo@bar.com"],
                "fullname": "foo bar",
                "name": "foo",
                "url_path": "user/foo",
                "full_url": "http://localhost.localdomain/user/foo",
            },
        }
        self.assertEqual(data, expected_output)

    @patch.dict("pagure.config.config", {"PAGURE_ADMIN_USERS": "foo"})
    def test_api_modify_project_main_admin_as_site_admin(self):
        """ Test the api_modify_project method of the flask api when the
        request is to change the main_admin of the project and the user is a
        Pagure site admin. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, user_id=2, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")
        headers = {"Authorization": "token aaabbbcccddd"}

        # date before:
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        date_before = project.date_modified
        self.assertIsNotNone(date_before)

        output = self.app.patch(
            "/api/0/test", headers=headers, data={"main_admin": "foo"}
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1496338274"
        data["date_modified"] = "1496338274"
        expected_output = {
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
                "owner": ["foo"],
                "ticket": [],
            },
            "close_status": [
                "Invalid",
                "Insufficient data",
                "Fixed",
                "Duplicate",
            ],
            "custom_keys": [],
            "date_created": "1496338274",
            "date_modified": "1496338274",
            "description": "test project #1",
            "full_url": "http://localhost.localdomain/test",
            "fullname": "test",
            "url_path": "test",
            "id": 1,
            "milestones": {},
            "name": "test",
            "namespace": None,
            "parent": None,
            "priorities": {},
            "tags": [],
            "user": {
                "default_email": "foo@bar.com",
                "emails": ["foo@bar.com"],
                "fullname": "foo bar",
                "name": "foo",
                "url_path": "user/foo",
                "full_url": "http://localhost.localdomain/user/foo",
            },
        }
        self.assertEqual(data, expected_output)

        # date after:
        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertNotEqual(date_before, project.date_modified)

    def test_api_modify_project_main_admin_not_main_admin(self):
        """ Test the api_modify_project method of the flask api when the
        requester is not the main_admin of the project and requests to change
        the main_admin.
        """
        tests.create_projects(self.session)
        project_user = pagure.lib.query.model.ProjectUser(
            project_id=1, user_id=2, access="admin"
        )
        self.session.add(project_user)
        self.session.commit()
        tests.create_tokens(self.session, project_id=None, user_id=2)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")
        headers = {"Authorization": "token aaabbbcccddd"}

        output = self.app.patch(
            "/api/0/test", headers=headers, data={"main_admin": "foo"}
        )
        self.assertEqual(output.status_code, 401)
        expected_error = {
            "error": (
                "Only the main admin can set the main admin of a " "project"
            ),
            "error_code": "ENOTMAINADMIN",
        }
        self.assertEqual(
            json.loads(output.get_data(as_text=True)), expected_error
        )

    def test_api_modify_project_not_admin(self):
        """ Test the api_modify_project method of the flask api when the
        requester is not an admin of the project.
        """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None, user_id=2)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")
        headers = {"Authorization": "token aaabbbcccddd"}

        output = self.app.patch(
            "/api/0/test", headers=headers, data={"main_admin": "foo"}
        )
        self.assertEqual(output.status_code, 401)
        expected_error = {
            "error": "You are not allowed to modify this project",
            "error_code": "EMODIFYPROJECTNOTALLOWED",
        }
        self.assertEqual(
            json.loads(output.get_data(as_text=True)), expected_error
        )

    def test_api_modify_project_invalid_request(self):
        """ Test the api_modify_project method of the flask api when the
        request data is invalid.
        """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")
        headers = {"Authorization": "token aaabbbcccddd"}

        output = self.app.patch("/api/0/test", headers=headers, data="invalid")
        self.assertEqual(output.status_code, 400)
        expected_error = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
        }
        self.assertEqual(
            json.loads(output.get_data(as_text=True)), expected_error
        )

    def test_api_modify_project_invalid_keys(self):
        """ Test the api_modify_project method of the flask api when the
        request data contains an invalid key.
        """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")
        headers = {"Authorization": "token aaabbbcccddd"}

        output = self.app.patch(
            "/api/0/test", headers=headers, data={"invalid": "invalid"}
        )
        self.assertEqual(output.status_code, 400)
        expected_error = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
        }
        self.assertEqual(
            json.loads(output.get_data(as_text=True)), expected_error
        )

    def test_api_modify_project_invalid_new_main_admin(self):
        """ Test the api_modify_project method of the flask api when the
        request is to change the main_admin of the project to a main_admin
        that doesn't exist.
        """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")
        headers = {"Authorization": "token aaabbbcccddd"}

        output = self.app.patch(
            "/api/0/test", headers=headers, data={"main_admin": "tbrady"}
        )
        self.assertEqual(output.status_code, 400)
        expected_error = {
            "error": "No such user found",
            "error_code": "ENOUSER",
        }
        self.assertEqual(
            json.loads(output.get_data(as_text=True)), expected_error
        )

    def test_api_project_watchers(self):
        """ Test the api_project_watchers method of the flask api. """
        tests.create_projects(self.session)
        # The user is not logged in and the owner is watching issues implicitly
        output = self.app.get("/api/0/test/watchers")
        self.assertEqual(output.status_code, 200)
        expected_data = {
            "total_watchers": 1,
            "watchers": {"pingou": ["issues"]},
        }
        self.assertDictEqual(
            json.loads(output.get_data(as_text=True)), expected_data
        )

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            # Non-existing project
            output = self.app.get("/api/0/random/watchers")
            self.assertEqual(output.status_code, 404)
            data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(
                data,
                {"error_code": "ENOPROJECT", "error": "Project not found"},
            )

            # The owner is watching issues implicitly
            output = self.app.get("/api/0/test/watchers")
            self.assertEqual(output.status_code, 200)
            expected_data = {
                "total_watchers": 1,
                "watchers": {"pingou": ["issues"]},
            }
            self.assertDictEqual(
                json.loads(output.get_data(as_text=True)), expected_data
            )

            project = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )

            # The owner is watching issues and commits explicitly
            pagure.lib.query.update_watch_status(
                self.session, project, "pingou", "3"
            )
            self.session.commit()
            output = self.app.get("/api/0/test/watchers")
            self.assertEqual(output.status_code, 200)
            expected_data = {
                "total_watchers": 1,
                "watchers": {"pingou": ["issues", "commits"]},
            }
            self.assertDictEqual(
                json.loads(output.get_data(as_text=True)), expected_data
            )

            # The owner is watching issues explicitly
            pagure.lib.query.update_watch_status(
                self.session, project, "pingou", "1"
            )
            self.session.commit()
            output = self.app.get("/api/0/test/watchers")
            self.assertEqual(output.status_code, 200)
            expected_data = {
                "total_watchers": 1,
                "watchers": {"pingou": ["issues"]},
            }
            self.assertDictEqual(
                json.loads(output.get_data(as_text=True)), expected_data
            )

            # The owner is watching commits explicitly
            pagure.lib.query.update_watch_status(
                self.session, project, "pingou", "2"
            )
            self.session.commit()
            output = self.app.get("/api/0/test/watchers")
            self.assertEqual(output.status_code, 200)
            expected_data = {
                "total_watchers": 1,
                "watchers": {"pingou": ["commits"]},
            }
            self.assertDictEqual(
                json.loads(output.get_data(as_text=True)), expected_data
            )

            # The owner is watching commits explicitly and foo is watching
            # issues implicitly
            project_user = pagure.lib.model.ProjectUser(
                project_id=project.id, user_id=2, access="commit"
            )
            pagure.lib.query.update_watch_status(
                self.session, project, "pingou", "2"
            )
            self.session.add(project_user)
            self.session.commit()

            output = self.app.get("/api/0/test/watchers")
            self.assertEqual(output.status_code, 200)
            expected_data = {
                "total_watchers": 2,
                "watchers": {"foo": ["issues"], "pingou": ["commits"]},
            }
            self.assertDictEqual(
                json.loads(output.get_data(as_text=True)), expected_data
            )

            # The owner and foo are watching issues implicitly
            pagure.lib.query.update_watch_status(
                self.session, project, "pingou", "-1"
            )
            self.session.commit()

            output = self.app.get("/api/0/test/watchers")
            self.assertEqual(output.status_code, 200)
            expected_data = {
                "total_watchers": 2,
                "watchers": {"foo": ["issues"], "pingou": ["issues"]},
            }
            self.assertDictEqual(
                json.loads(output.get_data(as_text=True)), expected_data
            )

            # The owner and foo through group membership are watching issues
            # implicitly
            pagure.lib.query.update_watch_status(
                self.session, project, "pingou", "-1"
            )
            project_membership = (
                self.session.query(pagure.lib.model.ProjectUser)
                .filter_by(user_id=2, project_id=project.id)
                .one()
            )
            self.session.delete(project_membership)
            self.session.commit()

            msg = pagure.lib.query.add_group(
                self.session,
                group_name="some_group",
                display_name="Some Group",
                description=None,
                group_type="bar",
                user="pingou",
                is_admin=False,
                blacklist=[],
            )
            self.session.commit()

            project = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            group = pagure.lib.query.search_groups(
                self.session, group_name="some_group"
            )
            pagure.lib.query.add_user_to_group(
                self.session, "foo", group, "pingou", False
            )

            pagure.lib.query.add_group_to_project(
                self.session,
                project,
                new_group="some_group",
                user="pingou",
                access="commit",
                create=False,
                is_admin=True,
            )
            self.session.commit()

            output = self.app.get("/api/0/test/watchers")
            self.assertEqual(output.status_code, 200)
            expected_data = {
                "total_watchers": 2,
                "watchers": {"@some_group": ["issues"], "pingou": ["issues"]},
            }
            self.assertDictEqual(
                json.loads(output.get_data(as_text=True)), expected_data
            )

            # The owner is watching issues implicitly and foo will be watching
            # commits explicitly but is in a group with commit access
            pagure.lib.query.update_watch_status(
                self.session, project, "pingou", "-1"
            )
            pagure.lib.query.update_watch_status(
                self.session, project, "foo", "2"
            )
            self.session.commit()

            output = self.app.get("/api/0/test/watchers")
            self.assertEqual(output.status_code, 200)
            expected_data = {
                "total_watchers": 3,
                "watchers": {
                    "@some_group": ["issues"],
                    "foo": ["commits"],
                    "pingou": ["issues"],
                },
            }
            self.assertDictEqual(
                json.loads(output.get_data(as_text=True)), expected_data
            )

    @patch.dict(
        "pagure.config.config",
        {
            "PAGURE_ADMIN_USERS": ["pingou"],
            "ALLOW_ADMIN_IGNORE_EXISTING_REPOS": True,
        },
    )
    def test_adopt_repos(self):
        """ Test the new_project endpoint with existing git repo. """
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        item = pagure.lib.model.Token(
            id="aaabbbcccddd",
            user_id=1,
            project_id=None,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=10),
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            input_data = {"name": "test", "description": "Project #1"}

            # Valid request
            output = self.app.post(
                "/api/0/new/", data=input_data, headers=headers
            )
            self.assertEqual(output.status_code, 400)
            data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(
                data,
                {
                    "error": "The main repo test.git already exists",
                    "error_code": "ENOCODE",
                },
            )

            input_data["ignore_existing_repos"] = "y"
            # Valid request
            output = self.app.post(
                "/api/0/new/", data=input_data, headers=headers
            )
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(data, {"message": 'Project "test" created'})

    def test_api_fork_project(self):
        """ Test the api_fork_project method of the flask api. """
        tests.create_projects(self.session)
        for folder in ["docs", "tickets", "requests", "repos"]:
            tests.create_projects_git(
                os.path.join(self.path, folder), bare=True
            )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token foo_token"}

        # Invalid token
        output = self.app.post("/api/0/fork", headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["error", "error_code", "errors"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(data["errors"], "Missing ACLs: fork_project")

        headers = {"Authorization": "token aaabbbcccddd"}

        # No input
        output = self.app.post("/api/0/fork", headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"repo": ["This field is required."]},
            },
        )

        data = {"name": "test"}

        # Incomplete request
        output = self.app.post("/api/0/fork", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"repo": ["This field is required."]},
            },
        )

        data = {"repo": "test"}

        # Valid request
        output = self.app.post("/api/0/fork/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": 'Repo "test" cloned to "pingou/test"'}
        )

        data = {"repo": "test"}

        # project already forked
        output = self.app.post("/api/0/fork/", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": 'Repo "forks/pingou/test" already exists',
                "error_code": "ENOCODE",
            },
        )

        data = {"repo": "test", "username": "pingou"}

        # Fork already exists
        output = self.app.post("/api/0/fork/", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": 'Repo "forks/pingou/test" already exists',
                "error_code": "ENOCODE",
            },
        )

        data = {"repo": "test", "namespace": "pingou"}

        # Repo does not exists
        output = self.app.post("/api/0/fork/", data=data, headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_api_fork_project_user_token(self):
        """ Test the api_fork_project method of the flask api. """
        tests.create_projects(self.session)
        for folder in ["docs", "tickets", "requests", "repos"]:
            tests.create_projects_git(
                os.path.join(self.path, folder), bare=True
            )
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token foo_token"}

        # Invalid token
        output = self.app.post("/api/0/fork", headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["error", "error_code", "errors"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(data["errors"], "Missing ACLs: fork_project")

        headers = {"Authorization": "token aaabbbcccddd"}

        # No input
        output = self.app.post("/api/0/fork", headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"repo": ["This field is required."]},
            },
        )

        data = {"name": "test"}

        # Incomplete request
        output = self.app.post("/api/0/fork", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"repo": ["This field is required."]},
            },
        )

        data = {"repo": "test"}

        # Valid request
        output = self.app.post("/api/0/fork/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": 'Repo "test" cloned to "pingou/test"'}
        )

        data = {"repo": "test"}

        # project already forked
        output = self.app.post("/api/0/fork/", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": 'Repo "forks/pingou/test" already exists',
                "error_code": "ENOCODE",
            },
        )

        data = {"repo": "test", "username": "pingou"}

        # Fork already exists
        output = self.app.post("/api/0/fork/", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": 'Repo "forks/pingou/test" already exists',
                "error_code": "ENOCODE",
            },
        )

        data = {"repo": "test", "namespace": "pingou"}

        # Repo does not exists
        output = self.app.post("/api/0/fork/", data=data, headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_api_generate_acls(self):
        """ Test the api_generate_acls method of the flask api """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(
            self.session, "aaabbbcccddd", "generate_acls_project"
        )
        headers = {"Authorization": "token aaabbbcccddd"}

        user = pagure.lib.query.get_user(self.session, "pingou")
        output = self.app.post(
            "/api/0/test/git/generateacls",
            headers=headers,
            data={"wait": False},
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "message": "Project ACL generation queued",
            "taskid": "abc-1234",
        }
        self.assertEqual(data, expected_output)
        self.mock_gen_acls.assert_called_once_with(
            name="test", namespace=None, user=None, group=None
        )

    def test_api_generate_acls_json(self):
        """ Test the api_generate_acls method of the flask api using JSON """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(
            self.session, "aaabbbcccddd", "generate_acls_project"
        )
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        user = pagure.lib.query.get_user(self.session, "pingou")

        output = self.app.post(
            "/api/0/test/git/generateacls",
            headers=headers,
            data=json.dumps({"wait": False}),
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "message": "Project ACL generation queued",
            "taskid": "abc-1234",
        }
        self.assertEqual(data, expected_output)
        self.mock_gen_acls.assert_called_once_with(
            name="test", namespace=None, user=None, group=None
        )

    def test_api_generate_acls_wait_true(self):
        """ Test the api_generate_acls method of the flask api when wait is
        set to True """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(
            self.session, "aaabbbcccddd", "generate_acls_project"
        )
        headers = {"Authorization": "token aaabbbcccddd"}

        task_result = Mock()
        task_result.id = "abc-1234"
        self.mock_gen_acls.return_value = task_result

        user = pagure.lib.query.get_user(self.session, "pingou")
        output = self.app.post(
            "/api/0/test/git/generateacls",
            headers=headers,
            data={"wait": True},
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {"message": "Project ACLs generated"}
        self.assertEqual(data, expected_output)
        self.mock_gen_acls.assert_called_once_with(
            name="test", namespace=None, user=None, group=None
        )
        self.assertTrue(task_result.get.called)

    def test_api_generate_acls_no_project(self):
        """ Test the api_generate_acls method of the flask api when the project
        doesn't exist """
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(
            self.session, "aaabbbcccddd", "generate_acls_project"
        )
        headers = {"Authorization": "token aaabbbcccddd"}

        user = pagure.lib.query.get_user(self.session, "pingou")
        output = self.app.post(
            "/api/0/test12345123/git/generateacls",
            headers=headers,
            data={"wait": False},
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error_code": "ENOPROJECT",
            "error": "Project not found",
        }
        self.assertEqual(data, expected_output)

    def test_api_new_git_branch(self):
        """ Test the api_new_branch method of the flask api """
        tests.create_projects(self.session)
        repo_path = os.path.join(self.path, "repos")
        tests.create_projects_git(repo_path, bare=True)
        tests.add_content_git_repo(os.path.join(repo_path, "test.git"))
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "create_branch")
        headers = {"Authorization": "token aaabbbcccddd"}
        args = {"branch": "test123"}
        output = self.app.post(
            "/api/0/test/git/branch", headers=headers, data=args
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {"message": "Project branch was created"}
        self.assertEqual(data, expected_output)
        git_path = os.path.join(self.path, "repos", "test.git")
        repo_obj = pygit2.Repository(git_path)
        self.assertIn("test123", repo_obj.listall_branches())

    def test_api_new_git_branch_json(self):
        """ Test the api_new_branch method of the flask api """
        tests.create_projects(self.session)
        repo_path = os.path.join(self.path, "repos")
        tests.create_projects_git(repo_path, bare=True)
        tests.add_content_git_repo(os.path.join(repo_path, "test.git"))
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "create_branch")
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        args = {"branch": "test123"}
        output = self.app.post(
            "/api/0/test/git/branch", headers=headers, data=json.dumps(args)
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {"message": "Project branch was created"}
        self.assertEqual(data, expected_output)
        git_path = os.path.join(self.path, "repos", "test.git")
        repo_obj = pygit2.Repository(git_path)
        self.assertIn("test123", repo_obj.listall_branches())

    def test_api_new_git_branch_from_branch(self):
        """ Test the api_new_branch method of the flask api """
        tests.create_projects(self.session)
        repo_path = os.path.join(self.path, "repos")
        tests.create_projects_git(repo_path, bare=True)
        tests.add_content_git_repo(os.path.join(repo_path, "test.git"))
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "create_branch")
        git_path = os.path.join(self.path, "repos", "test.git")
        repo_obj = pygit2.Repository(git_path)
        parent = pagure.lib.git.get_branch_ref(repo_obj, "master").peel()
        repo_obj.create_branch("dev123", parent)
        headers = {"Authorization": "token aaabbbcccddd"}
        args = {"branch": "test123", "from_branch": "dev123"}
        output = self.app.post(
            "/api/0/test/git/branch", headers=headers, data=args
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {"message": "Project branch was created"}
        self.assertEqual(data, expected_output)
        self.assertIn("test123", repo_obj.listall_branches())

    def test_api_new_git_branch_already_exists(self):
        """ Test the api_new_branch method of the flask api when branch already
        exists """
        tests.create_projects(self.session)
        repo_path = os.path.join(self.path, "repos")
        tests.create_projects_git(repo_path, bare=True)
        tests.add_content_git_repo(os.path.join(repo_path, "test.git"))
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "create_branch")
        headers = {"Authorization": "token aaabbbcccddd"}
        args = {"branch": "master"}
        output = self.app.post(
            "/api/0/test/git/branch", headers=headers, data=args
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": 'The branch "master" already exists',
            "error_code": "ENOCODE",
        }
        self.assertEqual(data, expected_output)

    def test_api_new_git_branch_from_commit(self):
        """ Test the api_new_branch method of the flask api """
        tests.create_projects(self.session)
        repos_path = os.path.join(self.path, "repos")
        tests.create_projects_git(repos_path, bare=True)
        git_path = os.path.join(repos_path, "test.git")
        tests.add_content_git_repo(git_path)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "create_branch")
        repo_obj = pygit2.Repository(git_path)
        from_commit = repo_obj.revparse_single("HEAD").oid.hex
        headers = {"Authorization": "token aaabbbcccddd"}
        args = {"branch": "test123", "from_commit": from_commit}
        output = self.app.post(
            "/api/0/test/git/branch", headers=headers, data=args
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {"message": "Project branch was created"}
        self.assertEqual(data, expected_output)
        self.assertIn("test123", repo_obj.listall_branches())


class PagureFlaskApiProjectFlagtests(tests.Modeltests):
    """ Tests for the flask API of pagure for flagging commit in project
    """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectFlagtests, self).setUp()

        tests.create_projects(self.session)
        repo_path = os.path.join(self.path, "repos")
        self.git_path = os.path.join(repo_path, "test.git")
        tests.create_projects_git(repo_path, bare=True)
        tests.add_content_git_repo(self.git_path)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "commit_flag")

    def test_flag_commit_missing_status(self):
        """ Test flagging a commit with missing precentage. """
        repo_obj = pygit2.Repository(self.git_path)
        commit = repo_obj.revparse_single("HEAD")

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "username": "Jenkins",
            "comment": "Tests passed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }
        output = self.app.post(
            "/api/0/test/c/%s/flag" % commit.oid.hex,
            headers=headers,
            data=data,
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {"status": ["Not a valid choice"]},
        }
        if self.get_wtforms_version() >= (2, 3):
            expected_output["errors"]["status"] = ["This field is required."]
        self.assertEqual(data, expected_output)

    def test_flag_commit_missing_username(self):
        """ Test flagging a commit with missing username. """
        repo_obj = pygit2.Repository(self.git_path)
        commit = repo_obj.revparse_single("HEAD")

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "percent": 100,
            "comment": "Tests passed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
            "status": "success",
        }
        output = self.app.post(
            "/api/0/test/c/%s/flag" % commit.oid.hex,
            headers=headers,
            data=data,
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {"username": ["This field is required."]},
        }
        self.assertEqual(data, expected_output)

    def test_flag_commit_missing_comment(self):
        """ Test flagging a commit with missing comment. """
        repo_obj = pygit2.Repository(self.git_path)
        commit = repo_obj.revparse_single("HEAD")

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "username": "Jenkins",
            "percent": 100,
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
            "status": "success",
        }
        output = self.app.post(
            "/api/0/test/c/%s/flag" % commit.oid.hex,
            headers=headers,
            data=data,
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {"comment": ["This field is required."]},
        }
        self.assertEqual(data, expected_output)

    def test_flag_commit_missing_url(self):
        """ Test flagging a commit with missing url. """
        repo_obj = pygit2.Repository(self.git_path)
        commit = repo_obj.revparse_single("HEAD")

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "username": "Jenkins",
            "percent": 100,
            "comment": "Tests passed",
            "uid": "jenkins_build_pagure_100+seed",
            "status": "success",
        }
        output = self.app.post(
            "/api/0/test/c/%s/flag" % commit.oid.hex,
            headers=headers,
            data=data,
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {"url": ["This field is required."]},
        }
        self.assertEqual(data, expected_output)

    def test_flag_commit_invalid_token(self):
        """ Test flagging a commit with missing info. """
        repo_obj = pygit2.Repository(self.git_path)
        commit = repo_obj.revparse_single("HEAD")

        headers = {"Authorization": "token 123"}
        data = {
            "username": "Jenkins",
            "percent": 100,
            "comment": "Tests passed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }
        output = self.app.post(
            "/api/0/test/c/%s/flag" % commit.oid.hex,
            headers=headers,
            data=data,
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

    def test_flag_commit_invalid_status(self):
        """ Test flagging a commit with an invalid status. """
        repo_obj = pygit2.Repository(self.git_path)
        commit = repo_obj.revparse_single("HEAD")

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "username": "Jenkins",
            "percent": 100,
            "comment": "Tests passed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "status": "foobar",
        }
        output = self.app.post(
            "/api/0/test/c/%s/flag" % commit.oid.hex,
            headers=headers,
            data=data,
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "errors": {"status": ["Not a valid choice"]},
                "error_code": "EINVALIDREQ",
                "error": "Invalid or incomplete input submitted",
            },
        )

    def test_flag_commit_with_uid(self):
        """ Test flagging a commit with provided uid. """
        repo_obj = pygit2.Repository(self.git_path)
        commit = repo_obj.revparse_single("HEAD")

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "username": "Jenkins",
            "percent": 100,
            "comment": "Tests passed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
            "status": "success",
        }
        output = self.app.post(
            "/api/0/test/c/%s/flag" % commit.oid.hex,
            headers=headers,
            data=data,
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        data["flag"]["commit_hash"] = "62b49f00d489452994de5010565fab81"
        expected_output = {
            "flag": {
                "comment": "Tests passed",
                "commit_hash": "62b49f00d489452994de5010565fab81",
                "date_created": "1510742565",
                "date_updated": "1510742565",
                "percent": 100,
                "status": "success",
                "url": "http://jenkins.cloud.fedoraproject.org/",
                "user": {
                    "default_email": "bar@pingou.com",
                    "emails": ["bar@pingou.com", "foo@pingou.com"],
                    "full_url": "http://localhost.localdomain/user/pingou",
                    "fullname": "PY C",
                    "name": "pingou",
                    "url_path": "user/pingou",
                },
                "username": "Jenkins",
            },
            "message": "Flag added",
            "uid": "jenkins_build_pagure_100+seed",
        }

        self.assertEqual(data, expected_output)

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    def test_update_flag_commit_with_uid(self):
        """ Test flagging a commit with provided uid. """
        repo_obj = pygit2.Repository(self.git_path)
        commit = repo_obj.revparse_single("HEAD")

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "username": "Jenkins",
            "percent": 0,
            "comment": "Tests running",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
            "status": "pending",
        }
        with testing.mock_sends(
            pagure_messages.CommitFlagAddedV1(
                topic="pagure.commit.flag.added",
                body={
                    "repo": {
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
                    "flag": {
                        "commit_hash": commit.oid.hex,
                        "username": "Jenkins",
                        "percent": "0",
                        "comment": "Tests running",
                        "status": "pending",
                        "url": "http://jenkins.cloud.fedoraproject.org/",
                        "date_created": ANY,
                        "date_updated": ANY,
                        "user": {
                            "name": "pingou",
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "fullname": "PY C",
                            "url_path": "user/pingou",
                        },
                    },
                    "agent": "pingou",
                },
            )
        ):
            output = self.app.post(
                "/api/0/test/c/%s/flag" % commit.oid.hex,
                headers=headers,
                data=data,
            )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        expected_output = {
            "flag": {
                "comment": "Tests running",
                "commit_hash": commit.oid.hex,
                "date_created": "1510742565",
                "date_updated": "1510742565",
                "percent": 0,
                "status": "pending",
                "url": "http://jenkins.cloud.fedoraproject.org/",
                "user": {
                    "default_email": "bar@pingou.com",
                    "emails": ["bar@pingou.com", "foo@pingou.com"],
                    "full_url": "http://localhost.localdomain/user/pingou",
                    "fullname": "PY C",
                    "name": "pingou",
                    "url_path": "user/pingou",
                },
                "username": "Jenkins",
            },
            "message": "Flag added",
            "uid": "jenkins_build_pagure_100+seed",
        }

        self.assertEqual(data, expected_output)

        data = {
            "username": "Jenkins",
            "percent": 100,
            "comment": "Tests passed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
            "status": "success",
        }
        with testing.mock_sends(
            pagure_messages.CommitFlagUpdatedV1(
                topic="pagure.commit.flag.updated",
                body={
                    "repo": {
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
                    "flag": {
                        "commit_hash": commit.oid.hex,
                        "username": "Jenkins",
                        "percent": "100",
                        "comment": "Tests passed",
                        "status": "success",
                        "url": "http://jenkins.cloud.fedoraproject.org/",
                        "date_created": ANY,
                        "date_updated": ANY,
                        "user": {
                            "name": "pingou",
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "fullname": "PY C",
                            "url_path": "user/pingou",
                        },
                    },
                    "agent": "pingou",
                },
            )
        ):
            output = self.app.post(
                "/api/0/test/c/%s/flag" % commit.oid.hex,
                headers=headers,
                data=data,
            )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        expected_output = {
            "flag": {
                "comment": "Tests passed",
                "commit_hash": commit.oid.hex,
                "date_created": "1510742565",
                "date_updated": "1510742565",
                "percent": 100,
                "status": "success",
                "url": "http://jenkins.cloud.fedoraproject.org/",
                "user": {
                    "default_email": "bar@pingou.com",
                    "emails": ["bar@pingou.com", "foo@pingou.com"],
                    "full_url": "http://localhost.localdomain/user/pingou",
                    "fullname": "PY C",
                    "name": "pingou",
                    "url_path": "user/pingou",
                },
                "username": "Jenkins",
            },
            "message": "Flag updated",
            "uid": "jenkins_build_pagure_100+seed",
        }

        self.assertEqual(data, expected_output)

    @patch("pagure.lib.notify.send_email")
    def test_flag_commit_without_uid(self, mock_email):
        """ Test flagging a commit with missing info.

        Also ensure notifications aren't sent when they are not asked for.
        """
        repo_obj = pygit2.Repository(self.git_path)
        commit = repo_obj.revparse_single("HEAD")

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "username": "Jenkins",
            "percent": 100,
            "comment": "Tests passed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "status": "success",
        }
        output = self.app.post(
            "/api/0/test/c/%s/flag" % commit.oid.hex,
            headers=headers,
            data=data,
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertNotEqual(data["uid"], "jenkins_build_pagure_100+seed")
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        data["uid"] = "b1de8f80defd4a81afe2e09f39678087"
        expected_output = {
            "flag": {
                "comment": "Tests passed",
                "commit_hash": commit.oid.hex,
                "date_created": "1510742565",
                "date_updated": "1510742565",
                "percent": 100,
                "status": "success",
                "url": "http://jenkins.cloud.fedoraproject.org/",
                "user": {
                    "default_email": "bar@pingou.com",
                    "emails": ["bar@pingou.com", "foo@pingou.com"],
                    "full_url": "http://localhost.localdomain/user/pingou",
                    "fullname": "PY C",
                    "name": "pingou",
                    "url_path": "user/pingou",
                },
                "username": "Jenkins",
            },
            "message": "Flag added",
            "uid": "b1de8f80defd4a81afe2e09f39678087",
        }
        self.assertEqual(data, expected_output)

        mock_email.assert_not_called()

    @patch("pagure.lib.notify.send_email")
    def test_flag_commit_with_notification(self, mock_email):
        """ Test flagging a commit with notification enabled. """

        # Enable commit notifications
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        settings = repo.settings
        settings["notify_on_commit_flag"] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        repo_obj = pygit2.Repository(self.git_path)
        commit = repo_obj.revparse_single("HEAD")

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "username": "Jenkins",
            "percent": 100,
            "comment": "Tests passed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "status": "success",
        }

        output = self.app.post(
            "/api/0/test/c/%s/flag" % commit.oid.hex,
            headers=headers,
            data=data,
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertNotEqual(data["uid"], "jenkins_build_pagure_100+seed")
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        data["uid"] = "b1de8f80defd4a81afe2e09f39678087"
        expected_output = {
            "flag": {
                "comment": "Tests passed",
                "commit_hash": commit.oid.hex,
                "date_created": "1510742565",
                "date_updated": "1510742565",
                "percent": 100,
                "status": "success",
                "url": "http://jenkins.cloud.fedoraproject.org/",
                "user": {
                    "default_email": "bar@pingou.com",
                    "emails": ["bar@pingou.com", "foo@pingou.com"],
                    "full_url": "http://localhost.localdomain/user/pingou",
                    "fullname": "PY C",
                    "name": "pingou",
                    "url_path": "user/pingou",
                },
                "username": "Jenkins",
            },
            "message": "Flag added",
            "uid": "b1de8f80defd4a81afe2e09f39678087",
        }
        self.assertEqual(data, expected_output)

        mock_email.assert_called_once_with(
            "\nJenkins flagged the commit "
            "`" + commit.oid.hex + "` as success: "
            "Tests passed\n\n"
            "http://localhost.localdomain/test/c/" + commit.oid.hex + "\n",
            "Commit #" + commit.oid.hex + " - Jenkins: success",
            "bar@pingou.com",
            in_reply_to="test-project-1",
            mail_id="test-commit-1-1",
            project_name="test",
            user_from="Jenkins",
        )

    @patch.dict(
        "pagure.config.config",
        {
            "FLAG_STATUSES_LABELS": {
                "pend!": "label-info",
                "succeed!": "label-success",
                "fail!": "label-danger",
                "what?": "label-warning",
            },
            "FLAG_PENDING": "pend!",
            "FLAG_SUCCESS": "succeed!",
            "FLAG_FAILURE": "fail!",
        },
    )
    def test_flag_commit_with_custom_flags(self):
        """ Test flagging when custom flags are set up
        """
        repo_obj = pygit2.Repository(self.git_path)
        commit = repo_obj.revparse_single("HEAD")

        headers = {"Authorization": "token aaabbbcccddd"}
        send_data = {
            "username": "Jenkins",
            "percent": 100,
            "comment": "Tests passed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "status": "succeed!",
        }
        output = self.app.post(
            "/api/0/test/c/%s/flag" % commit.oid.hex,
            headers=headers,
            data=send_data,
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(data["flag"]["status"], "succeed!")

        # Try invalid flag status
        send_data["status"] = "nooooo...."
        output = self.app.post(
            "/api/0/test/c/%s/flag" % commit.oid.hex,
            headers=headers,
            data=send_data,
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "errors": {"status": ["Not a valid choice"]},
                "error_code": "EINVALIDREQ",
                "error": "Invalid or incomplete input submitted",
            },
        )

    def test_commit_flags(self):
        """ Test retrieving commit flags. """
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo_obj = pygit2.Repository(self.git_path)
        commit = repo_obj.revparse_single("HEAD")

        # test with no flags
        output = self.app.get("/api/0/test/c/%s/flag" % commit.oid.hex)
        self.assertEqual(
            json.loads(output.get_data(as_text=True)),
            {"total_flags": 0, "flags": []},
        )
        self.assertEqual(output.status_code, 200)

        # add some flags and retrieve them
        pagure.lib.query.add_commit_flag(
            session=self.session,
            repo=repo,
            commit_hash=commit.oid.hex,
            username="simple-koji-ci",
            status="pending",
            percent=None,
            comment="Build is running",
            url="https://koji.fp.o/koji...",
            uid="uid",
            user="foo",
            token="aaabbbcccddd",
        )

        pagure.lib.query.add_commit_flag(
            session=self.session,
            repo=repo,
            commit_hash=commit.oid.hex,
            username="complex-koji-ci",
            status="success",
            percent=None,
            comment="Build succeeded",
            url="https://koji.fp.o/koji...",
            uid="uid2",
            user="foo",
            token="aaabbbcccddd",
        )
        self.session.commit()

        output = self.app.get("/api/0/test/c/%s/flag" % commit.oid.hex)
        data = json.loads(output.get_data(as_text=True))

        for f in data["flags"]:
            f["date_created"] = "1510742565"
            f["date_updated"] = "1510742565"
            f["commit_hash"] = "62b49f00d489452994de5010565fab81"
        expected_output = {
            "flags": [
                {
                    "comment": "Build is running",
                    "commit_hash": "62b49f00d489452994de5010565fab81",
                    "date_created": "1510742565",
                    "date_updated": "1510742565",
                    "percent": None,
                    "status": "pending",
                    "url": "https://koji.fp.o/koji...",
                    "user": {
                        "fullname": "foo bar",
                        "full_url": "http://localhost.localdomain/user/foo",
                        "name": "foo",
                        "url_path": "user/foo",
                    },
                    "username": "simple-koji-ci",
                },
                {
                    "comment": "Build succeeded",
                    "commit_hash": "62b49f00d489452994de5010565fab81",
                    "date_created": "1510742565",
                    "date_updated": "1510742565",
                    "percent": None,
                    "status": "success",
                    "url": "https://koji.fp.o/koji...",
                    "user": {
                        "fullname": "foo bar",
                        "full_url": "http://localhost.localdomain/user/foo",
                        "name": "foo",
                        "url_path": "user/foo",
                    },
                    "username": "complex-koji-ci",
                },
            ],
            "total_flags": 2,
        }

        self.assertEqual(data, expected_output)


class PagureFlaskApiProjectModifyAclTests(tests.Modeltests):
    """ Tests for the flask API of pagure for modifying ACLs in a project
    """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectModifyAclTests, self).setUp()
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")

        project = pagure.lib.query._get_project(self.session, "test")
        self.assertEquals(
            project.access_users,
            {"admin": [], "collaborator": [], "commit": [], "ticket": []},
        )

    def test_api_modify_acls_no_project(self):
        """ Test the api_modify_acls method of the flask api when the project
        doesn't exist """
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {"user_type": "user", "name": "bar", "acl": "commit"}
        output = self.app.post(
            "/api/0/test12345123/git/modifyacls", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error_code": "ENOPROJECT",
            "error": "Project not found",
        }
        self.assertEqual(data, expected_output)

    def test_api_modify_acls_no_user(self):
        """ Test the api_modify_acls method of the flask api when the user
        doesn't exist """
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {"user_type": "user", "name": "nosuchuser", "acl": "commit"}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "No such user found",
            "error_code": "ENOUSER",
        }
        self.assertEqual(data, expected_output)

    def test_api_modify_acls_no_group(self):
        """ Test the api_modify_acls method of the flask api when the group
        doesn't exist """
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {"user_type": "group", "name": "nosuchgroup", "acl": "commit"}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "Group not found",
            "error_code": "ENOGROUP",
        }
        self.assertEqual(data, expected_output)

    def test_api_modify_acls_no_permission(self):
        """ Test the api_modify_acls method of the flask api when the user
        doesn't have permissions """
        item = pagure.lib.model.Token(
            id="foo_token2",
            user_id=2,
            project_id=None,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30),
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session, "foo_token2", "modify_project")

        headers = {"Authorization": "token foo_token2"}

        data = {"user_type": "user", "name": "foo", "acl": "commit"}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "You are not allowed to modify this project",
            "error_code": "EMODIFYPROJECTNOTALLOWED",
        }
        self.assertEqual(data, expected_output)

    def test_api_modify_acls_neither_user_nor_group(self):
        """ Test the api_modify_acls method of the flask api when neither
        user nor group was set """
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {"acl": "commit"}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {
                "name": ["This field is required."],
                "user_type": ["Not a valid choice"],
            },
        }
        if self.get_wtforms_version() >= (2, 3):
            expected_output["errors"]["user_type"] = [
                "This field is required."
            ]
        self.assertEqual(data, expected_output)

    def test_api_modify_acls_invalid_acl(self):
        """ Test the api_modify_acls method of the flask api when the ACL
        doesn't exist. Must be one of ticket, commit or admin. """
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {"user_type": "user", "name": "bar", "acl": "invalidacl"}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {"acl": ["Not a valid choice"]},
        }
        self.assertEqual(data, expected_output)

    def test_api_modify_acls_user(self):
        """ Test the api_modify_acls method of the flask api for
        setting an ACL for a user. """
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {"user_type": "user", "name": "foo", "acl": "commit"}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1510742565"
        data["date_modified"] = "1510742566"

        expected_output = {
            "access_groups": {
                "admin": [],
                "collaborator": [],
                "commit": [],
                "ticket": [],
            },
            "access_users": {
                "admin": [],
                "collaborator": [],
                "commit": ["foo"],
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
            "date_created": "1510742565",
            "date_modified": "1510742566",
            "description": "test project #1",
            "full_url": "http://localhost.localdomain/test",
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
                "full_url": "http://localhost.localdomain/user/pingou",
                "name": "pingou",
                "url_path": "user/pingou",
            },
        }
        self.assertEqual(data, expected_output)

    def test_api_modify_acls_group(self):
        """ Test the api_modify_acls method of the flask api for
        setting an ACL for a group. """
        headers = {"Authorization": "token aaabbbcccddd"}

        # Create a group
        msg = pagure.lib.query.add_group(
            self.session,
            group_name="baz",
            display_name="baz group",
            description=None,
            group_type="bar",
            user="foo",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, "User `foo` added to the group `baz`.")

        data = {"user_type": "group", "name": "baz", "acl": "ticket"}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )

        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1510742565"
        data["date_modified"] = "1510742566"

        expected_output = {
            "access_groups": {
                "admin": [],
                "collaborator": [],
                "commit": [],
                "ticket": ["baz"],
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
            "date_created": "1510742565",
            "date_modified": "1510742566",
            "description": "test project #1",
            "full_url": "http://localhost.localdomain/test",
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
                "full_url": "http://localhost.localdomain/user/pingou",
                "url_path": "user/pingou",
            },
        }
        self.assertEqual(data, expected_output)

    def test_api_modify_acls_no_acl(self):
        """ Test the api_modify_acls method of the flask api when no ACL
        are specified. """
        headers = {"Authorization": "token aaabbbcccddd"}

        project = pagure.lib.query._get_project(self.session, "test")
        self.assertEquals(
            project.access_users,
            {"admin": [], "collaborator": [], "commit": [], "ticket": []},
        )

        data = {"user_type": "user", "name": "foo"}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": "User does not have any access on the repo",
        }

        self.assertEqual(data, expected_output)

    def test_api_modify_acls_remove_own_acl_no_access(self):
        """ Test the api_modify_acls method of the flask api when no ACL
        are specified, so the user tries to remove their own access but the
        user is the project owner. """
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {"user_type": "user", "name": "pingou"}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": "User does not have any access on the repo",
        }

        self.assertEqual(data, expected_output)

    def test_api_modify_acls_remove_own_acl_(self):
        """ Test the api_modify_acls method of the flask api when no ACL
        are specified, so the user tries to remove their own access but the
        user is the project owner. """
        # Add the user `foo` to the project
        self.test_api_modify_acls_user()

        # Ensure `foo` was properly added:
        project = pagure.lib.query._get_project(self.session, "test")
        user_foo = pagure.lib.query.search_user(self.session, username="foo")
        self.assertEquals(
            project.access_users,
            {
                "admin": [],
                "collaborator": [],
                "commit": [user_foo],
                "ticket": [],
            },
        )

        # Create an API token for `foo` for the project `test`
        item = pagure.lib.model.Token(
            id="foo_test_token",
            user_id=2,  # foo
            project_id=1,  # test
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=10),
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(
            self.session, "foo_test_token", "modify_project"
        )

        headers = {"Authorization": "token foo_test_token"}

        data = {"user_type": "user", "name": "foo"}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1510742565"
        data["date_modified"] = "1510742566"

        expected_output = {
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
            "date_created": "1510742565",
            "date_modified": "1510742566",
            "description": "test project #1",
            "full_url": "http://localhost.localdomain/test",
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
                "full_url": "http://localhost.localdomain/user/pingou",
                "url_path": "user/pingou",
            },
        }

        self.assertEqual(data, expected_output)

        # Ensure `foo` was properly removed
        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query._get_project(self.session, "test")
        self.assertEquals(
            project.access_users,
            {"admin": [], "collaborator": [], "commit": [], "ticket": []},
        )

    def test_api_modify_acls_remove_someone_else_acl(self):
        """ Test the api_modify_acls method of the flask api an admin tries
        to remove access from someone else. """
        # Add the user `foo` to the project
        self.test_api_modify_acls_user()

        # Ensure `foo` was properly added:
        project = pagure.lib.query._get_project(self.session, "test")
        user_foo = pagure.lib.query.search_user(self.session, username="foo")
        self.assertEquals(
            project.access_users,
            {
                "admin": [],
                "collaborator": [],
                "commit": [user_foo],
                "ticket": [],
            },
        )

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"user_type": "user", "name": "foo"}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1510742565"
        data["date_modified"] = "1510742566"

        expected_output = {
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
            "date_created": "1510742565",
            "date_modified": "1510742566",
            "description": "test project #1",
            "full_url": "http://localhost.localdomain/test",
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
                "full_url": "http://localhost.localdomain/user/pingou",
                "url_path": "user/pingou",
            },
        }

        self.assertEqual(data, expected_output)

        # Ensure `foo` was properly removed
        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query._get_project(self.session, "test")
        self.assertEquals(
            project.access_users,
            {"admin": [], "collaborator": [], "commit": [], "ticket": []},
        )

    def test_api_modify_acls_add_remove_group(self):
        """ Test the api_modify_acls method of the flask api for
        setting an ACL for a group. """
        headers = {"Authorization": "token aaabbbcccddd"}

        # Create a group
        msg = pagure.lib.query.add_group(
            self.session,
            group_name="baz",
            display_name="baz group",
            description=None,
            group_type="bar",
            user="foo",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, "User `foo` added to the group `baz`.")

        # Add the group to the project
        data = {"user_type": "group", "name": "baz", "acl": "ticket"}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )

        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1510742565"
        data["date_modified"] = "1510742566"

        expected_output = {
            "access_groups": {
                "admin": [],
                "collaborator": [],
                "commit": [],
                "ticket": ["baz"],
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
            "date_created": "1510742565",
            "date_modified": "1510742566",
            "description": "test project #1",
            "fullname": "test",
            "full_url": "http://localhost.localdomain/test",
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
                "full_url": "http://localhost.localdomain/user/pingou",
                "name": "pingou",
                "url_path": "user/pingou",
            },
        }
        self.assertEqual(data, expected_output)

        # Ensure `baz` was properly added
        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query._get_project(self.session, "test")
        self.assertEquals(
            project.access_users,
            {"admin": [], "collaborator": [], "commit": [], "ticket": []},
        )
        self.assertNotEquals(
            project.access_groups,
            {"admin": [], "collaborator": [], "commit": [], "ticket": []},
        )
        self.assertEquals(len(project.access_groups["ticket"]), 1)

        # Remove the group from the project
        data = {"user_type": "group", "name": "baz", "acl": None}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )

        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1510742565"
        data["date_modified"] = "1510742566"

        expected_output = {
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
            "date_created": "1510742565",
            "date_modified": "1510742566",
            "description": "test project #1",
            "full_url": "http://localhost.localdomain/test",
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
                "full_url": "http://localhost.localdomain/user/pingou",
                "url_path": "user/pingou",
            },
        }
        self.assertEqual(data, expected_output)

        # Ensure `baz` was properly removed
        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query._get_project(self.session, "test")
        self.assertEquals(
            project.access_users,
            {"admin": [], "collaborator": [], "commit": [], "ticket": []},
        )
        self.assertEquals(
            project.access_groups,
            {"admin": [], "collaborator": [], "commit": [], "ticket": []},
        )

    def test_api_modify_acls_remove_group_not_in_project(self):
        """ Test the api_modify_acls method of the flask api for
        setting an ACL for a group. """
        headers = {"Authorization": "token aaabbbcccddd"}

        # Create a group
        msg = pagure.lib.query.add_group(
            self.session,
            group_name="baz",
            display_name="baz group",
            description=None,
            group_type="bar",
            user="foo",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, "User `foo` added to the group `baz`.")

        # Remove the group from the project
        data = {"user_type": "group", "name": "baz", "acl": None}
        output = self.app.post(
            "/api/0/test/git/modifyacls", headers=headers, data=data
        )

        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1510742565"
        data["date_modified"] = "1510742566"

        expected_output = {
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
            "date_created": "1510742565",
            "date_modified": "1510742566",
            "description": "test project #1",
            "full_url": "http://localhost.localdomain/test",
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
                "full_url": "http://localhost.localdomain/user/pingou",
            },
        }
        self.assertEqual(data, expected_output)

        # Ensure `baz` was properly removed
        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query._get_project(self.session, "test")
        self.assertEquals(
            project.access_users,
            {"admin": [], "collaborator": [], "commit": [], "ticket": []},
        )
        self.assertEquals(
            project.access_groups,
            {"admin": [], "collaborator": [], "commit": [], "ticket": []},
        )


class PagureFlaskApiProjectOptionsTests(tests.Modeltests):
    """ Tests for the flask API of pagure for modifying options ofs a project
    """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectOptionsTests, self).setUp()
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")

        project = pagure.lib.query._get_project(self.session, "test")
        self.assertEquals(
            project.access_users,
            {"admin": [], "collaborator": [], "commit": [], "ticket": []},
        )

    def test_api_get_project_options_wrong_project(self):
        """ Test accessing api_get_project_options w/o auth header. """

        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/unknown/options", headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_api_get_project_options_wo_header(self):
        """ Test accessing api_get_project_options w/o auth header. """

        output = self.app.get("/api/0/test/options")
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "error": "Invalid or expired token. Please visit "
                "http://localhost.localdomain/settings#nav-api-tab to get "
                "or renew your API token.",
                "error_code": "EINVALIDTOK",
                "errors": "Invalid token",
            },
        )

    def test_api_get_project_options_w_header(self):
        """ Test accessing api_get_project_options w/ auth header. """

        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/options", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "settings": {
                    "Enforce_signed-off_commits_in_pull-request": False,
                    "Minimum_score_to_merge_pull-request": -1,
                    "Only_assignee_can_merge_pull-request": False,
                    "Web-hooks": None,
                    "always_merge": False,
                    "disable_non_fast-forward_merges": False,
                    "fedmsg_notifications": True,
                    "issue_tracker": True,
                    "issue_tracker_read_only": False,
                    "issues_default_to_private": False,
                    "mqtt_notifications": True,
                    "notify_on_commit_flag": False,
                    "notify_on_pull-request_flag": False,
                    "open_metadata_access_to_all": False,
                    "project_documentation": False,
                    "pull_request_access_only": False,
                    "pull_requests": True,
                    "stomp_notifications": True,
                },
                "status": "ok",
            },
        )

    def test_api_modify_project_options_wrong_project(self):
        """ Test accessing api_modify_project_options w/ an invalid project.
        """

        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.post(
            "/api/0/unknown/options/update", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_api_modify_project_options_wo_header(self):
        """ Test accessing api_modify_project_options w/o auth header. """

        output = self.app.post("/api/0/test/options/update")
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "error": "Invalid or expired token. Please visit "
                "http://localhost.localdomain/settings#nav-api-tab to get "
                "or renew your API token.",
                "error_code": "EINVALIDTOK",
                "errors": "Invalid token",
            },
        )

    def test_api_modify_project_options_no_data(self):
        """ Test accessing api_modify_project_options w/ auth header. """

        # check before
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/options", headers=headers)
        self.assertEqual(output.status_code, 200)
        before = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            before,
            {
                "settings": {
                    "Enforce_signed-off_commits_in_pull-request": False,
                    "Minimum_score_to_merge_pull-request": -1,
                    "Only_assignee_can_merge_pull-request": False,
                    "Web-hooks": None,
                    "always_merge": False,
                    "disable_non_fast-forward_merges": False,
                    "fedmsg_notifications": True,
                    "issue_tracker": True,
                    "issue_tracker_read_only": False,
                    "issues_default_to_private": False,
                    "mqtt_notifications": True,
                    "notify_on_commit_flag": False,
                    "notify_on_pull-request_flag": False,
                    "open_metadata_access_to_all": False,
                    "project_documentation": False,
                    "pull_request_access_only": False,
                    "pull_requests": True,
                    "stomp_notifications": True,
                },
                "status": "ok",
            },
        )

        # Do not update anything
        data = {}
        output = self.app.post(
            "/api/0/test/options/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data, {"message": "No settings to change", "status": "ok"}
        )

        # check after
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/options", headers=headers)
        self.assertEqual(output.status_code, 200)
        after = json.loads(output.get_data(as_text=True))
        self.assertEqual(after, before)

    def test_api_modify_project_options(self):
        """ Test accessing api_modify_project_options w/ auth header. """

        # check before
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/options", headers=headers)
        self.assertEqual(output.status_code, 200)
        before = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            before,
            {
                "settings": {
                    "Enforce_signed-off_commits_in_pull-request": False,
                    "Minimum_score_to_merge_pull-request": -1,
                    "Only_assignee_can_merge_pull-request": False,
                    "Web-hooks": None,
                    "always_merge": False,
                    "disable_non_fast-forward_merges": False,
                    "fedmsg_notifications": True,
                    "issue_tracker": True,
                    "issue_tracker_read_only": False,
                    "issues_default_to_private": False,
                    "mqtt_notifications": True,
                    "notify_on_commit_flag": False,
                    "notify_on_pull-request_flag": False,
                    "open_metadata_access_to_all": False,
                    "project_documentation": False,
                    "pull_request_access_only": False,
                    "pull_requests": True,
                    "stomp_notifications": True,
                },
                "status": "ok",
            },
        )

        # Update: `issues_default_to_private`.
        data = {"issues_default_to_private": True}
        output = self.app.post(
            "/api/0/test/options/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "message": "Edited successfully settings of repo: test",
                "status": "ok",
            },
        )

        # check after
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/options", headers=headers)
        self.assertEqual(output.status_code, 200)
        after = json.loads(output.get_data(as_text=True))
        self.assertNotEqual(before, after)
        before["settings"]["issues_default_to_private"] = True
        self.assertEqual(after, before)

    def test_api_modify_project_options2(self):
        """ Test accessing api_modify_project_options w/ auth header. """

        # check before
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/options", headers=headers)
        self.assertEqual(output.status_code, 200)
        before = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            before,
            {
                "settings": {
                    "Enforce_signed-off_commits_in_pull-request": False,
                    "Minimum_score_to_merge_pull-request": -1,
                    "Only_assignee_can_merge_pull-request": False,
                    "Web-hooks": None,
                    "always_merge": False,
                    "disable_non_fast-forward_merges": False,
                    "fedmsg_notifications": True,
                    "issue_tracker": True,
                    "issue_tracker_read_only": False,
                    "issues_default_to_private": False,
                    "mqtt_notifications": True,
                    "notify_on_commit_flag": False,
                    "notify_on_pull-request_flag": False,
                    "open_metadata_access_to_all": False,
                    "project_documentation": False,
                    "pull_request_access_only": False,
                    "pull_requests": True,
                    "stomp_notifications": True,
                },
                "status": "ok",
            },
        )

        # Update: `issue_tracker`.
        data = {"issue_tracker": False}
        output = self.app.post(
            "/api/0/test/options/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "message": "Edited successfully settings of repo: test",
                "status": "ok",
            },
        )

        # check after
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/options", headers=headers)
        self.assertEqual(output.status_code, 200)
        after = json.loads(output.get_data(as_text=True))
        self.assertNotEqual(before, after)
        before["settings"]["issue_tracker"] = False
        self.assertEqual(after, before)

    def test_api_modify_project_options_json(self):
        """ Test accessing api_modify_project_options w/ auth header and
        input submitted as JSON instead of HTML arguments. """

        # check before
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/options", headers=headers)
        self.assertEqual(output.status_code, 200)
        before = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            before,
            {
                "settings": {
                    "Enforce_signed-off_commits_in_pull-request": False,
                    "Minimum_score_to_merge_pull-request": -1,
                    "Only_assignee_can_merge_pull-request": False,
                    "Web-hooks": None,
                    "always_merge": False,
                    "disable_non_fast-forward_merges": False,
                    "fedmsg_notifications": True,
                    "issue_tracker": True,
                    "issue_tracker_read_only": False,
                    "issues_default_to_private": False,
                    "mqtt_notifications": True,
                    "notify_on_commit_flag": False,
                    "notify_on_pull-request_flag": False,
                    "open_metadata_access_to_all": False,
                    "project_documentation": False,
                    "pull_request_access_only": False,
                    "pull_requests": True,
                    "stomp_notifications": True,
                },
                "status": "ok",
            },
        )

        # Update: `issue_tracker`.
        data = json.dumps({"issue_tracker": False})
        headers["Content-Type"] = "application/json"
        output = self.app.post(
            "/api/0/test/options/update", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "message": "Edited successfully settings of repo: test",
                "status": "ok",
            },
        )

        # check after
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/options", headers=headers)
        self.assertEqual(output.status_code, 200)
        after = json.loads(output.get_data(as_text=True))
        self.assertNotEqual(before, after)
        before["settings"]["issue_tracker"] = False
        self.assertEqual(after, before)


class PagureFlaskApiProjectCreateAPITokenTests(tests.Modeltests):
    """ Tests for the flask API of pagure for creating user project API token
    """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectCreateAPITokenTests, self).setUp()
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")

    def test_api_createapitoken_as_owner(self):
        """ Test accessing api_project_create_token as owner. """

        headers = {"Authorization": "token aaabbbcccddd"}
        project = pagure.lib.query._get_project(self.session, "test")
        tdescription = "my new token"

        # Call the api with pingou user token and verify content
        data = {
            "description": tdescription,
            "acls": ["pull_request_merge", "pull_request_comment"],
        }
        output = self.app.post(
            "/api/0/test/token/new", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        tid = pagure.lib.query.search_token(
            self.session, None, description=tdescription
        )[0].id
        self.assertEqual(
            data, {"token": {"description": tdescription, "id": tid}}
        )
        # Create a second token but with faulty acl
        # Call the api with pingou user token and error code
        data = {"description": tdescription, "acl": ["foo", "bar"]}
        output = self.app.post(
            "/api/0/test/token/new", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)

    def test_api_createapitoken_as_admin(self):
        """ Test accessing api_project_create_token as admin. """

        project = pagure.lib.query._get_project(self.session, "test")

        # Set the foo user as test project admin
        pagure.lib.query.add_user_to_project(
            self.session,
            project,
            new_user="foo",
            user="pingou",
            access="admin",
        )
        self.session.commit()

        # Create modify_project token for foo user
        exp_date = datetime.date.today() + datetime.timedelta(days=300)
        token = pagure.lib.query.add_token_to_user(
            self.session,
            project=None,
            acls=["modify_project"],
            username="foo",
            expiration_date=exp_date,
        )

        # Call the connector with foo user token and verify content
        headers = {"Authorization": "token %s" % token.id}
        tdescription = "my new token"

        # Call the api with pingou user token and verify content
        data = {
            "description": tdescription,
            "acls": ["pull_request_merge", "pull_request_comment"],
        }
        output = self.app.post(
            "/api/0/test/token/new", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        tid = pagure.lib.query.search_token(
            self.session, None, user="foo", description=tdescription
        )[0].id
        self.assertEqual(
            data, {"token": {"description": tdescription, "id": tid}}
        )

    def test_api_createapitoken_as_unauthorized(self):
        """ Test accessing api_project_create_token as project admin
        but with unauthorized token ACL.
        """

        project = pagure.lib.query._get_project(self.session, "test")

        # Set the foo user as test project admin
        pagure.lib.query.add_user_to_project(
            self.session,
            project,
            new_user="foo",
            user="pingou",
            access="admin",
        )
        self.session.commit()

        # Create modify_project token for foo user
        exp_date = datetime.date.today() + datetime.timedelta(days=300)
        pagure.lib.query.add_token_to_user(
            self.session,
            project=None,
            acls=["create_branch"],
            username="foo",
            expiration_date=exp_date,
        )
        mtoken = pagure.lib.query.search_token(
            self.session, ["create_branch"], user="foo"
        )[0]

        # Call the connector with foo user token and verify content
        headers = {"Authorization": "token %s" % mtoken.id}
        tdescription = "my new token"

        # Call the api with pingou user token and verify content
        data = {
            "description": tdescription,
            "acls": ["pull_request_merge", "pull_request_comment"],
        }
        output = self.app.post(
            "/api/0/test/token/new", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 401)

    def test_api_createapitoken_as_unauthorized_2(self):
        """ Test accessing api_project_create_token as project user
        with unauthorized token ACL.
        """

        project = pagure.lib.query._get_project(self.session, "test")

        # Set the foo user as test project admin
        pagure.lib.query.add_user_to_project(
            self.session,
            project,
            new_user="foo",
            user="pingou",
            access="commit",
        )
        self.session.commit()

        # Create modify_project token for foo user
        exp_date = datetime.date.today() + datetime.timedelta(days=300)
        pagure.lib.query.add_token_to_user(
            self.session,
            project=None,
            acls=["modify_project"],
            username="foo",
            expiration_date=exp_date,
        )
        mtoken = pagure.lib.query.search_token(
            self.session, ["modify_project"], user="foo"
        )[0]

        # Call the connector with foo user token and verify content
        headers = {"Authorization": "token %s" % mtoken.id}
        tdescription = "my new token"

        # Call the api with pingou user token and verify content
        data = {
            "description": tdescription,
            "acls": ["pull_request_merge", "pull_request_comment"],
        }
        output = self.app.post(
            "/api/0/test/token/new", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 401)


class PagureFlaskApiProjectConnectorTests(tests.Modeltests):
    """ Tests for the flask API of pagure for getting connector of a project
    """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectConnectorTests, self).setUp()
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "modify_project")

    def test_api_get_project_connector_as_owner(self):
        """ Test accessing api_get_project_connector as project owner. """

        project = pagure.lib.query._get_project(self.session, "test")

        # Create witness project Token for pingou user
        exp_date = datetime.date.today() + datetime.timedelta(days=300)
        pagure.lib.query.add_token_to_user(
            self.session,
            project=project,
            acls=["pull_request_merge"],
            username="pingou",
            expiration_date=exp_date,
        )
        ctokens = pagure.lib.query.search_token(
            self.session, ["pull_request_merge"], user="pingou"
        )
        self.assertEqual(len(ctokens), 1)

        # Call the connector with pingou user token and verify content
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/connector", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "connector": {
                    "hook_token": project.hook_token,
                    "api_tokens": [
                        {
                            "description": t.description,
                            "id": t.id,
                            "expired": False,
                        }
                        for t in ctokens
                    ],
                },
                "status": "ok",
            },
        )

    def test_api_get_project_connector_as_admin(self):
        """ Test accessing api_get_project_connector as project admin """

        project = pagure.lib.query._get_project(self.session, "test")

        # Set the foo user as test project admin
        pagure.lib.query.add_user_to_project(
            self.session,
            project,
            new_user="foo",
            user="pingou",
            access="admin",
        )
        self.session.commit()

        # Create modify_project token for foo user
        exp_date = datetime.date.today() + datetime.timedelta(days=300)
        pagure.lib.query.add_token_to_user(
            self.session,
            project=None,
            acls=["modify_project"],
            username="foo",
            expiration_date=exp_date,
        )
        mtoken = pagure.lib.query.search_token(
            self.session, ["modify_project"], user="foo"
        )[0]

        # Create witness project Token for foo user
        exp_date = datetime.date.today() + datetime.timedelta(days=300)
        pagure.lib.query.add_token_to_user(
            self.session,
            project=project,
            acls=["pull_request_merge"],
            username="foo",
            expiration_date=exp_date,
        )
        ctokens = pagure.lib.query.search_token(
            self.session, ["pull_request_merge"], user="foo"
        )
        self.assertEqual(len(ctokens), 1)

        # Call the connector with foo user token and verify content
        headers = {"Authorization": "token %s" % mtoken.id}
        output = self.app.get("/api/0/test/connector", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "connector": {
                    "hook_token": project.hook_token,
                    "api_tokens": [
                        {
                            "description": t.description,
                            "id": t.id,
                            "expired": False,
                        }
                        for t in ctokens
                    ],
                },
                "status": "ok",
            },
        )

    def test_api_get_project_connector_as_unauthorized(self):
        """ Test accessing api_get_project_connector as project admin
        but with unauthorized token ACL
        """

        project = pagure.lib.query._get_project(self.session, "test")

        # Set the foo user as test project admin
        pagure.lib.query.add_user_to_project(
            self.session,
            project,
            new_user="foo",
            user="pingou",
            access="admin",
        )
        self.session.commit()

        # Create modify_project token for foo user
        exp_date = datetime.date.today() + datetime.timedelta(days=300)
        pagure.lib.query.add_token_to_user(
            self.session,
            project=None,
            acls=["create_project"],
            username="foo",
            expiration_date=exp_date,
        )
        mtoken = pagure.lib.query.search_token(
            self.session, ["create_project"], user="foo"
        )[0]

        # Call the connector with foo user token and verify unauthorized
        headers = {"Authorization": "token %s" % mtoken.id}
        output = self.app.get("/api/0/test/connector", headers=headers)
        self.assertEqual(output.status_code, 401)

    def test_api_get_project_connector_as_unauthorized_2(self):
        """ Test accessing api_get_project_connector as project
        but with unauthorized token ACL
        """

        project = pagure.lib.query._get_project(self.session, "test")

        # Set the foo user as test project admin
        pagure.lib.query.add_user_to_project(
            self.session,
            project,
            new_user="foo",
            user="pingou",
            access="commit",
        )
        self.session.commit()

        # Create modify_project token for foo user
        exp_date = datetime.date.today() + datetime.timedelta(days=300)
        pagure.lib.query.add_token_to_user(
            self.session,
            project=None,
            acls=["modify_project"],
            username="foo",
            expiration_date=exp_date,
        )
        mtoken = pagure.lib.query.search_token(
            self.session, ["modify_project"], user="foo"
        )[0]

        # Call the connector with foo user token and verify unauthorized
        headers = {"Authorization": "token %s" % mtoken.id}
        output = self.app.get("/api/0/test/connector", headers=headers)
        self.assertEqual(output.status_code, 401)


class PagureFlaskApiProjectWebhookTokenTests(tests.Modeltests):
    """ Tests for the flask API of pagure for getting webhook token of a project
    """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectWebhookTokenTests, self).setUp()
        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        # Set a default ACL to avoid get all rights set on
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "issue_assign")

    def test_api_get_project_webhook_token_as_owner(self):
        """ Test accessing webhook token as project owner. """

        project = pagure.lib.query._get_project(self.session, "test")

        # Call the endpoint with pingou user token and verify content
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/webhook/token", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data, {"webhook": {"token": project.hook_token}, "status": "ok"}
        )

    def test_api_get_project_webhook_token_as_collaborator(self):
        """ Test accessing webhook token as project collaborator. """

        project = pagure.lib.query._get_project(self.session, "test")

        # Set the foo user as test project collaborator ticket access level
        pagure.lib.query.add_user_to_project(
            self.session,
            project,
            new_user="foo",
            user="pingou",
            access="collaborator",
        )
        self.session.commit()

        # Create token for foo user with a default ACL
        mtoken = pagure.lib.query.add_token_to_user(
            self.session,
            project=None,
            acls=["issue_assign"],
            username="foo",
            expiration_date=datetime.date.today() + datetime.timedelta(days=1),
        )

        # Call the endpoint with foo user token and verify content
        headers = {"Authorization": "token %s" % mtoken.id}
        output = self.app.get("/api/0/test/webhook/token", headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data, {"webhook": {"token": project.hook_token}, "status": "ok"}
        )

    def test_api_get_project_webhook_token_as_not_collaborator(self):
        """ Test accessing webhook token as not a project collaborator. """

        # Create token for foo user with a default ACL
        mtoken = pagure.lib.query.add_token_to_user(
            self.session,
            project=None,
            acls=["issue_assign"],
            username="foo",
            expiration_date=datetime.date.today() + datetime.timedelta(days=1),
        )

        # Call the endpoint with pingou user token and verify content
        headers = {"Authorization": "token %s" % mtoken.id}
        output = self.app.get("/api/0/test/webhook/token", headers=headers)
        self.assertEqual(output.status_code, 401)


class PagureFlaskApiProjectCommitInfotests(tests.Modeltests):
    """ Tests for the flask API of pagure for commit info
    """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectCommitInfotests, self).setUp()

        tests.create_projects(self.session)
        repo_path = os.path.join(self.path, "repos")
        self.git_path = os.path.join(repo_path, "test.git")
        tests.create_projects_git(repo_path, bare=True)
        tests.add_content_git_repo(self.git_path)

        repo_obj = pygit2.Repository(self.git_path)
        self.commit = repo_obj.revparse_single("HEAD")

    def test_api_commit_info(self):
        """ Test flagging a commit with missing precentage. """

        output = self.app.get("/api/0/test/c/%s/info" % self.commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        expected_output = {
            "author": "Alice Author",
            "commit_time": self.commit.commit_time,
            "commit_time_offset": self.commit.commit_time_offset,
            "committer": "Cecil Committer",
            "hash": self.commit.oid.hex,
            "message": "Add some directory and a file for more testing",
            "parent_ids": [self.commit.parent_ids[0].hex],
            "tree_id": self.commit.tree_id.hex,
        }

        self.assertEqual(data, expected_output)

    def test_api_commit_info_invalid_commit(self):
        """ Test flagging a commit with missing username. """
        output = self.app.get("/api/0/test/c/invalid_commit_hash/info")

        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.ENOCOMMIT.name, data["error_code"]
        )
        self.assertEqual(pagure.api.APIERROR.ENOCOMMIT.value, data["error"])

    def test_api_commit_info_hash_tree(self):
        """ Test flagging a commit with missing username. """
        output = self.app.get(
            "/api/0/test/c/%s/info" % self.commit.tree_id.hex
        )

        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.ENOCOMMIT.name, data["error_code"]
        )
        self.assertEqual(pagure.api.APIERROR.ENOCOMMIT.value, data["error"])


class PagureFlaskApiProjectGitBranchestests(tests.Modeltests):
    """ Tests for the flask API of pagure for git branches
    """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectGitBranchestests, self).setUp()

        tests.create_projects(self.session)
        repo_path = os.path.join(self.path, "repos")
        self.git_path = os.path.join(repo_path, "test.git")
        tests.create_projects_git(repo_path, bare=True)
        tests.add_content_git_repo(self.git_path)

        tests.create_tokens(self.session, project_id=None)
        # Set a default ACL to avoid get all rights set on
        tests.create_tokens_acl(self.session, "foo_token", "modify_project")
        tests.create_tokens_acl(self.session, "aaabbbcccddd", "create_branch")

        # Add a couple of branches to the test project
        repo_obj = pygit2.Repository(self.git_path)
        self.commit = repo_obj.revparse_single("HEAD")

        new_repo_path = os.path.join(self.path, "lcl_forks")
        clone_repo = pygit2.clone_repository(self.git_path, new_repo_path)

        # Create two other branches based on master
        for branch in ["pats-win-49", "pats-win-51"]:
            clone_repo.create_branch(branch, clone_repo.head.peel())
            refname = "refs/heads/{0}:refs/heads/{0}".format(branch)
            PagureRepo.push(clone_repo.remotes[0], refname)

    def test_api_git_branches(self):
        """ Test the api_git_branches method of the flask api. """
        # Check that the branches show up on the API
        output = self.app.get("/api/0/test/git/branches")

        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "branches": ["master", "pats-win-49", "pats-win-51"],
                "default": "master",
                "total_branches": 3,
            },
        )

    def test_api_git_branches_with_commits(self):
        """ Test the api_git_branches method of the flask api with with_commits=True. """
        # Check that the branches show up on the API
        output = self.app.get("/api/0/test/git/branches?with_commits=true")

        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "branches": {
                    "master": self.commit.hex,
                    "pats-win-49": self.commit.hex,
                    "pats-win-51": self.commit.hex,
                },
                "default": {"master": self.commit.hex,},
                "total_branches": 3,
            },
        )

    def test_api_git_branches_empty_repo(self):
        """ Test the api_git_branches method of the flask api when the repo is
        empty.
        """
        # Check that no branches show up on the API
        output = self.app.get("/api/0/test2/git/branches")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"branches": [], "default": None, "total_branches": 0}
        )

    def test_api_set_git_default_branch(self):
        """ Test the api_git_branches method of the flask api. """
        headers = {"Authorization": "token foo_token"}
        data = {"branch_name": "pats-win-49"}
        output = self.app.post(
            "/api/0/test/git/branches", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "branches": ["master", "pats-win-49", "pats-win-51"],
                "default": "pats-win-49",
                "total_branches": 3,
            },
        )

    def test_api_set_git_default_branch_with_commits_form(self):
        """ Test the api_git_branches method of the flask api with with_commits=True. """
        headers = {"Authorization": "token foo_token"}
        data = {"branch_name": "pats-win-49", "with_commits": True}
        output = self.app.post(
            "/api/0/test/git/branches", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "branches": {
                    "master": self.commit.hex,
                    "pats-win-49": self.commit.hex,
                    "pats-win-51": self.commit.hex,
                },
                "default": {"pats-win-49": self.commit.hex,},
                "total_branches": 3,
            },
        )

    def test_api_set_git_default_branch_with_commits_url(self):
        """ Test the api_git_branches method of the flask api with with_commits=True. """
        headers = {"Authorization": "token foo_token"}
        data = {"branch_name": "pats-win-49"}
        output = self.app.post(
            "/api/0/test/git/branches?with_commits=1",
            data=data,
            headers=headers,
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "branches": {
                    "master": self.commit.hex,
                    "pats-win-49": self.commit.hex,
                    "pats-win-51": self.commit.hex,
                },
                "default": {"pats-win-49": self.commit.hex,},
                "total_branches": 3,
            },
        )

    def test_api_set_git_default_branch_invalid_branch(self):
        """ Test the api_git_branches method of the flask api with with_commits=True. """
        headers = {"Authorization": "token foo_token"}
        data = {"branch_name": "main"}
        output = self.app.post(
            "/api/0/test/git/branches?with_commits=1",
            data=data,
            headers=headers,
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "An error occurred during a git operation",
                "error_code": "EGITERROR",
            },
        )

    def test_api_set_git_default_branch_invalid_token(self):
        """ Test the api_git_branches method of the flask api with with_commits=True. """
        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"branch_name": "main"}
        output = self.app.post(
            "/api/0/test/git/branches", data=data, headers=headers,
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or expired token. Please visit "
                "http://localhost.localdomain/settings#nav-api-tab to get or renew "
                "your API token.",
                "error_code": "EINVALIDTOK",
                "errors": "Missing ACLs: modify_project",
            },
        )

    def test_api_set_git_default_branch_empty_repo(self):
        """ Test the api_git_branches method of the flask api when the repo is
        empty.
        """
        headers = {"Authorization": "token foo_token"}
        data = {"branch_name": "main"}
        output = self.app.post(
            "/api/0/test2/git/branches", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "An error occurred during a git operation",
                "error_code": "EGITERROR",
            },
        )


class PagureFlaskApiProjectCreateProjectTests(tests.Modeltests):
    """ Tests for the flask API of pagure for git branches
    """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectCreateProjectTests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "tickets"))
        tests.create_tokens(self.session)
        tests.create_tokens(self.session, suffix="_user", project_id=None)
        tests.create_tokens_acl(self.session)
        tests.create_tokens_acl(self.session, token_id="aaabbbcccddd_user")

    def test_api_new_project_invalid_token(self):

        headers = {"Authorization": "token foo_token"}

        # Invalid token
        output = self.app.post("/api/0/new", headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["error", "error_code", "errors"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(data["errors"], "Missing ACLs: create_project")

    def test_api_new_project_no_input(self):

        headers = {"Authorization": "token aaabbbcccddd"}

        # No input
        output = self.app.post("/api/0/new", headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "name": ["This field is required."],
                    "description": ["This field is required."],
                },
            },
        )

    def test_api_new_project_incomplete_request(self):

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"name": "test"}

        # Incomplete request
        output = self.app.post("/api/0/new", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"description": ["This field is required."]},
            },
        )

    def test_api_new_project_existing_repo(self):

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"name": "test", "description": "Just a small test project"}

        # Valid request but repo already exists
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": 'It is not possible to create the repo "test"',
                "error_code": "ENOCODE",
            },
        )

    def test_api_new_project_invalid_avatar_email_int(self):

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "name": "api1",
            "description": "Mighty mighty description",
            "avatar_email": 123,
        }

        # invalid avatar_email - number
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"avatar_email": ["avatar_email must be an email"]},
            },
        )

    def test_api_new_project_invalid_avatar_email_list(self):

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "name": "api1",
            "description": "Mighty mighty description",
            "avatar_email": [1, 2, 3],
        }

        # invalid avatar_email - list
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"avatar_email": ["avatar_email must be an email"]},
            },
        )

    def test_api_new_project_invalid_avatar_email_bool(self):

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "name": "api1",
            "description": "Mighty mighty description",
            "avatar_email": True,
        }

        # invalid avatar_email - boolean
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"avatar_email": ["avatar_email must be an email"]},
            },
        )

    def test_api_new_project_with_avatar(self):

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "name": "api1",
            "description": "Mighty mighty description",
            "avatar_email": "mighty@email.com",
        }

        # valid avatar_email
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": 'Project "api1" created'})

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    def test_api_new_project(self):

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "name": "test_42",
            "description": "Just another small test project",
        }

        # Valid request
        with testing.mock_sends(
            pagure_messages.ProjectNewV1(
                topic="pagure.project.new",
                body={
                    "project": {
                        "id": 4,
                        "name": "test_42",
                        "fullname": "test_42",
                        "url_path": "test_42",
                        "description": "Just another small test project",
                        "full_url": "http://localhost.localdomain/test_42",
                        "namespace": None,
                        "parent": None,
                        "date_created": ANY,
                        "date_modified": ANY,
                        "user": {
                            "name": "pingou",
                            "fullname": "PY C",
                            "full_url": "http://localhost.localdomain/user/pingou",
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
                        "close_status": [],
                        "milestones": {},
                    },
                    "agent": "pingou",
                },
            )
        ):
            output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": 'Project "test_42" created'})

    def test_api_new_project_mirrored_from(self):

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "name": "test_42",
            "description": "Just another small test project",
            "mirrored_from": "https://pagure.io/pagure/pagure.git",
        }

        # Valid request
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": 'Project "test_42" created'})

        project = pagure.lib.query.get_authorized_project(
            self.session, "test_42"
        )
        self.assertEqual(
            project.mirrored_from, "https://pagure.io/pagure/pagure.git"
        )

    def test_api_new_project_readme(self):

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "name": "test_42",
            "description": "Just another small test project",
            "create_readme": "true",
        }

        # Valid request
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": 'Project "test_42" created'})

        project = pagure.lib.query.get_authorized_project(
            self.session, "test_42"
        )
        repo = pygit2.Repository(project.repopath("main"))
        self.assertEqual(repo.listall_branches(), ["master"])

    def test_api_new_project_readme_default_branch(self):

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "name": "test_42",
            "description": "Just another small test project",
            "create_readme": "true",
            "default_branch": "main",
        }

        # Valid request
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": 'Project "test_42" created'})

        project = pagure.lib.query.get_authorized_project(
            self.session, "test_42"
        )
        repo = pygit2.Repository(project.repopath("main"))
        self.assertEqual(repo.listall_branches(), ["main"])

    @patch.dict("pagure.config.config", {"PRIVATE_PROJECTS": True})
    def test_api_new_project_private(self):
        """ Test the api_new_project method of the flask api to create
        a private project. """

        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "name": "test",
            "description": "Just a small test project",
            "private": True,
        }

        # Valid request
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": 'Project "pingou/test" created'}
        )

    def test_api_new_project_user_token(self):
        """ Test the api_new_project method of the flask api. """

        headers = {"Authorization": "token foo_token_user"}

        # Invalid token
        output = self.app.post("/api/0/new", headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()), ["error", "error_code", "errors"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(data["errors"], "Missing ACLs: create_project")

        headers = {"Authorization": "token aaabbbcccddd_user"}

        # No input
        output = self.app.post("/api/0/new", headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "name": ["This field is required."],
                    "description": ["This field is required."],
                },
            },
        )

        data = {"name": "test"}

        # Incomplete request
        output = self.app.post("/api/0/new", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"description": ["This field is required."]},
            },
        )

        data = {"name": "test", "description": "Just a small test project"}

        # Valid request but repo already exists
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": 'It is not possible to create the repo "test"',
                "error_code": "ENOCODE",
            },
        )

        data = {
            "name": "test_42",
            "description": "Just another small test project",
        }

        # Valid request
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": 'Project "test_42" created'})

        # Project with a namespace
        pagure.config.config["ALLOWED_PREFIX"] = ["rpms"]
        data = {
            "name": "test_42",
            "namespace": "pingou",
            "description": "Just another small test project",
        }

        # Invalid namespace
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"namespace": ["Not a valid choice"]},
            },
        )

        data = {
            "name": "test_42",
            "namespace": "rpms",
            "description": "Just another small test project",
        }

        # All good
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": 'Project "rpms/test_42" created'}
        )

    @patch.dict("pagure.config.config", {"USER_NAMESPACE": True})
    def test_api_new_project_user_ns(self):
        """ Test the api_new_project method of the flask api. """

        headers = {"Authorization": "token aaabbbcccddd"}

        # Create a project with the user namespace feature on
        data = {
            "name": "testproject",
            "description": "Just another small test project",
        }

        # Valid request
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": 'Project "pingou/testproject" created'}
        )

        # Create a project with a namespace and the user namespace feature on
        data = {
            "name": "testproject2",
            "namespace": "testns",
            "description": "Just another small test project",
        }

        # Valid request
        with patch.dict(
            "pagure.config.config", {"ALLOWED_PREFIX": ["testns"]}
        ):
            output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": 'Project "testns/testproject2" created'}
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
