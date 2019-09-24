# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import json
import unittest
import shutil
import sys
import tempfile
import time
import os

import pygit2
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskPrNoSourcestests(tests.Modeltests):
    """ Tests PR in pagure when the source is gone """

    maxDiff = None

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch("pagure.lib.notify.fedmsg_publish", MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskPrNoSourcestests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Create foo's fork of pingou's test project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name="test",
            description="test project #1",
            hook_token="aaabbb",
            is_fork=True,
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()
        # Create the fork's git repo
        repo_path = os.path.join(self.path, "repos", item.path)
        pygit2.init_repository(repo_path, bare=True)

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        fork = pagure.lib.query.get_authorized_project(
            self.session, "test", user="foo"
        )

        self.set_up_git_repo(repo=project, fork=fork)

        # Ensure things got setup straight
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(project.requests), 1)

        # wait for the worker to process the task
        path = os.path.join(
            self.path, "repos", "test.git", "refs", "pull", "1", "head"
        )
        self.assertTrue(os.path.exists(path))

    def set_up_git_repo(self, repo, fork, branch_from="feature"):
        """ Set up the git repo and create the corresponding PullRequest
        object.
        """

        req = tests.add_pull_request_git_repo(
            self.path, self.session, repo, fork, branch_from
        )

        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "PR from the %s branch" % branch_from)

        tests.clean_pull_requests_path()

    def test_request_pull_reference(self):
        """ Test if there is a reference created for a new PR. """

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(project.requests), 1)

        gitrepo = os.path.join(self.path, "repos", "test.git")
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(
            list(repo.listall_references()),
            ["refs/heads/master", "refs/pull/1/head"],
        )

    def test_request_pull_fork_reference(self):
        """ Test if there the references created on the fork. """

        project = pagure.lib.query.get_authorized_project(
            self.session, "test", user="foo"
        )
        self.assertEqual(len(project.requests), 0)

        gitrepo = os.path.join(self.path, "repos", project.path)
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(
            list(repo.listall_references()), ["refs/heads/feature"]
        )

    def test_accessing_pr_fork_deleted(self):
        """ Test accessing the PR if the fork has been deleted. """

        # Delete fork on disk
        project = pagure.lib.query.get_authorized_project(
            self.session, "test", user="foo"
        )
        repo_path = os.path.join(self.path, "repos", project.path)
        self.assertTrue(os.path.exists(repo_path))
        shutil.rmtree(repo_path)
        self.assertFalse(os.path.exists(repo_path))

        # Delete fork in the DB
        self.session.delete(project)
        self.session.commit()

        # View the pull-request
        output2 = self.app.get("/test/pull-request/1")
        self.assertEqual(output2.status_code, 200)

    def test_accessing_pr_patch_fork_deleted(self):
        """ Test accessing the PR's patch if the fork has been deleted. """

        # Delete fork on disk
        project = pagure.lib.query.get_authorized_project(
            self.session, "test", user="foo"
        )
        repo_path = os.path.join(self.path, "repos", project.path)
        self.assertTrue(os.path.exists(repo_path))
        shutil.rmtree(repo_path)
        self.assertFalse(os.path.exists(repo_path))

        # Delete fork in the DB
        self.session.delete(project)
        self.session.commit()

        # View the pull-request
        output = self.app.get("/test/pull-request/1.patch")
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "--- a/sources\n+++ b/sources\n@@ -1,2 +1,4 @@",
            output.get_data(as_text=True),
        )

    def test_accessing_pr_branch_deleted(self):
        """ Test accessing the PR if branch it originates from has been
        deleted. """
        project = pagure.lib.query.get_authorized_project(
            self.session, "test", user="foo"
        )

        # Check the branches before
        gitrepo = os.path.join(self.path, "repos", project.path)
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(
            list(repo.listall_references()), ["refs/heads/feature"]
        )

        # Delete branch of the fork
        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                "/fork/foo/test/b/feature/delete", follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)

        # Check the branches after
        gitrepo = os.path.join(self.path, "repos", project.path)
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(list(repo.listall_references()), [])

        # View the pull-request
        output2 = self.app.get("/test/pull-request/1")
        self.assertEqual(output2.status_code, 200)

    def test_accessing_pr_patch_branch_deleted(self):
        """ Test accessing the PR's patch if branch it originates from has
        been deleted. """
        project = pagure.lib.query.get_authorized_project(
            self.session, "test", user="foo"
        )

        # Check the branches before
        gitrepo = os.path.join(self.path, "repos", project.path)
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(
            list(repo.listall_references()), ["refs/heads/feature"]
        )

        # Delete branch of the fork
        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                "/fork/foo/test/b/feature/delete", follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)

        # Check the branches after
        gitrepo = os.path.join(self.path, "repos", project.path)
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(list(repo.listall_references()), [])

        # View the pull-request
        output = self.app.get("/test/pull-request/1.patch")
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "--- a/sources\n+++ b/sources\n@@ -1,2 +1,4 @@",
            output.get_data(as_text=True),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
