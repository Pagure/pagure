# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import sys
import os

import json
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.config
import pagure.lib.query
import pagure.lib.tasks
import tests


class PagureMergePrNoForkTest(tests.Modeltests):
    """Tests merging a PR in pagure when the fork no longer exists"""

    maxDiff = None

    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureMergePrNoForkTest, self).setUp()

        tests.create_projects(self.session)
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )

        # Fork
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        task = pagure.lib.query.fork_project(
            session=self.session, user="pingou", repo=project
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {
                "endpoint": "ui_ns.view_repo",
                "repo": "test",
                "namespace": None,
                "username": "pingou",
            },
        )

        tests.add_readme_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test.git")
        )
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        fork = pagure.lib.query.get_authorized_project(
            self.session, "test", user="pingou"
        )

        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=fork,
            branch_from="master",
            repo_to=project,
            branch_to="master",
            title="test pull-request",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "test pull-request")

        # Assert the PR is open
        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(project.requests), 1)
        self.assertEqual(project.requests[0].status, "Open")
        # Check how the PR renders in the API and the UI
        output = self.app.get("/api/0/test/pull-request/1")
        self.assertEqual(output.status_code, 200)
        output = self.app.get("/test/pull-request/1")
        self.assertEqual(output.status_code, 200)

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_api_pull_request_diffstats(self):
        """Test the api_pull_request_merge method of the flask api."""

        # Check the PR stats in the API
        output = self.app.get("/api/0/test/pull-request/1/diffstats")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "README.rst": {
                    "lines_added": 16,
                    "lines_removed": 0,
                    "new_id": "fb7093d2ba1cf8f80d10b45e4f15b10240727db5",
                    "old_id": "0000000000000000000000000000000000000000",
                    "old_path": "README.rst",
                    "status": "A",
                }
            },
        )

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_api_pull_request_diffstats_no_fork(self):
        """Test the api_pull_request_merge method of the flask api."""

        pagure.lib.tasks.delete_project(
            namespace=None, name="test", user="pingou", action_user="pingou"
        )

        # Check the PR stats in the API
        output = self.app.get("/api/0/test/pull-request/1/diffstats")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "README.rst": {
                    "lines_added": 16,
                    "lines_removed": 0,
                    "new_id": "fb7093d2ba1cf8f80d10b45e4f15b10240727db5",
                    "old_id": "0000000000000000000000000000000000000000",
                    "old_path": "README.rst",
                    "status": "A",
                }
            },
        )

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_api_pull_request_merge(self):
        """Test the api_pull_request_merge method of the flask api."""

        headers = {"Authorization": "token aaabbbcccddd"}

        # Merge PR
        output = self.app.post(
            "/api/0/test/pull-request/1/merge", headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Changes merged!"})

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_api_pull_request_merge_no_fork(self):
        """Test the api_pull_request_merge method of the flask api."""

        pagure.lib.tasks.delete_project(
            namespace=None, name="test", user="pingou", action_user="pingou"
        )

        headers = {"Authorization": "token aaabbbcccddd"}

        # Merge PR
        output = self.app.post(
            "/api/0/test/pull-request/1/merge", headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"message": "Changes merged!"})

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_ui_pull_request_merge(self):
        """Test the api_pull_request_merge method of the flask UI."""

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {"csrf_token": self.get_csrf()}

            # Merge PR
            output = self.app.post(
                "/test/pull-request/1/merge", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>PR#1: test pull-request - test\n - Pagure</title>",
                output_text,
            )

        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(project.requests[0].status, "Merged")

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_ui_pull_request_merge_no_fork(self):
        """Test the api_pull_request_merge method of the flask UI."""

        pagure.lib.tasks.delete_project(
            namespace=None, name="test", user="pingou", action_user="pingou"
        )

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {"csrf_token": self.get_csrf()}
            # Check the PR view on UI
            output = self.app.get("/test/pull-request/1")
            self.assertEqual(output.status_code, 200)
            # Merge PR
            output = self.app.post(
                "/test/pull-request/1/merge", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>PR#1: test pull-request - test\n - Pagure</title>",
                output_text,
            )

        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(project.requests[0].status, "Merged")

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_internal_merge_status(self):
        """Test the api_pull_request_merge method of the flask UI."""

        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query.get_authorized_project(self.session, "test")

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {
                "csrf_token": self.get_csrf(),
                "requestid": project.requests[0].uid,
            }

            # Merge PR
            output = self.app.post("/pv/pull-request/merge", data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(
                data,
                {
                    "code": "FFORWARD",
                    "message": "The pull-request can be merged and "
                    "fast-forwarded",
                    "short_code": "Ok",
                },
            )

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_internal_merge_status_no_fork(self):
        """Test the api_pull_request_merge method of the flask UI."""

        pagure.lib.tasks.delete_project(
            namespace=None, name="test", user="pingou", action_user="pingou"
        )

        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query.get_authorized_project(self.session, "test")

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {
                "csrf_token": self.get_csrf(),
                "requestid": project.requests[0].uid,
            }

            # Merge PR
            output = self.app.post("/pv/pull-request/merge", data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(
                data,
                {
                    "code": "FFORWARD",
                    "message": "The pull-request can be merged and "
                    "fast-forwarded",
                    "short_code": "Ok",
                },
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
