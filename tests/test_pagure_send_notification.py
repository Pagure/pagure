# -*- coding: utf-8 -*-

"""
 (c) 2019 - Copyright Red Hat Inc

 Authors:
   Fabien Boucher <fboucher@redhat.com>

"""

import unittest
import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import mock
import pygit2

import pagure.hooks.default
import tests


class PagureHooksDefault(tests.SimplePagureTest):
    """ Tests for pagure.hooks.default """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureHooksDefault, self).setUp()
        tests.create_projects(self.session)
        self.projects = tests.create_projects_git(
            os.path.join(self.path, "repos"), bare=True
        )
        self.folder = os.path.join(self.path, "repos", "test.git")

    def init_test_repo(self):
        tests.add_content_git_repo(self.projects[0])
        repo = pygit2.Repository(self.projects[0])
        commit = repo.references["refs/heads/master"].peel()
        sha = commit.hex
        oldsha = commit.parents[0].hex
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        return project, sha, oldsha

    @mock.patch("pagure.hooks.default.send_fedmsg_notifications")
    def test_send_action_notification(self, fedmsg):
        project, sha, _ = self.init_test_repo()
        pagure.hooks.default.send_action_notification(
            self.session,
            "tag",
            "bar",
            project,
            self.folder,
            "pingou",
            "master",
            sha,
        )
        (_, args, kwargs) = fedmsg.mock_calls[0]
        self.assertEqual(args[1], "git.tag.bar")
        self.assertEqual(args[2]["repo"]["name"], "test")
        self.assertEqual(args[2]["rev"], sha)

    @mock.patch("pagure.hooks.default.send_fedmsg_notifications")
    def test_send_notifications(self, fedmsg):
        project, sha, oldsha = self.init_test_repo()
        pagure.hooks.default.send_notifications(
            self.session,
            project,
            self.folder,
            "pingou",
            "master",
            [sha],
            False,
            oldsha,
        )
        (_, args, kwargs) = fedmsg.mock_calls[0]
        self.assertEqual(args[1], "git.receive")
        self.assertEqual(args[2]["repo"]["name"], "test")
        self.assertEqual(args[2]["start_commit"], sha)
        self.assertEqual(args[2]["forced"], False)
        self.assertEqual(args[2]["old_commit"], oldsha)
        self.assertEqual(
            args[2]["changed_files"],
            {
                "folder1/folder2/file": "A",
                "folder1/folder2/fileŠ": "A",
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
