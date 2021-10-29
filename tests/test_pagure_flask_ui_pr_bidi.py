# -*- coding: utf-8 -*-

"""
 (c) 2021 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import sys
import os

import pygit2
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests


class PagureFlaskPrBiditests(tests.Modeltests):
    """ Tests PR in pagure when the PR has bi-directional characters """

    maxDiff = None

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch("pagure.lib.notify.fedmsg_publish", MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskPrBiditests, self).setUp()

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

    def set_up_git_repo(
        self, repo, fork, branch_from="feature", append_content=None
    ):
        """Set up the git repo and create the corresponding PullRequest
        object.
        """

        req = tests.add_pull_request_git_repo(
            self.path,
            self.session,
            repo,
            fork,
            branch_from,
            append_content=append_content,
        )

        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "PR from the %s branch" % branch_from)

        tests.clean_pull_requests_path()

    def test_accessing_pr_no_bidi(self):
        """ Test accessing the PR which has no bidi characters. """
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

        # View the pull-request -- no bidi characters found
        output = self.app.get("/test/pull-request/1")
        self.assertEqual(output.status_code, 200)
        self.assertNotIn(
            "Special characters such as:", output.get_data(as_text=True)
        )

    def test_accessing_pr_bidi(self):
        """ Test accessing the PR which has no bidi characters. """
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        fork = pagure.lib.query.get_authorized_project(
            self.session, "test", user="foo"
        )
        self.set_up_git_repo(
            repo=project, fork=fork, append_content="ahah %s" % chr(0x2067)
        )

        # Ensure things got setup straight
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(project.requests), 1)

        # wait for the worker to process the task
        path = os.path.join(
            self.path, "repos", "test.git", "refs", "pull", "1", "head"
        )
        self.assertTrue(os.path.exists(path))

        # View the pull-request -- bidi characters found
        output = self.app.get("/test/pull-request/1")
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "Special characters such as:", output.get_data(as_text=True)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
