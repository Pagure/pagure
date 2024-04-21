# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

from __future__ import unicode_literals, absolute_import

import base64
import datetime
import unittest
import shutil
import sys
import tempfile
import os

import six
import json
import pygit2
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests


class PagureFlaskAppClonetests(tests.Modeltests):
    """Tests for the clone bridging."""

    def setUp(self):
        super(PagureFlaskAppClonetests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        self.create_project_full("clonetest", {"create_readme": "y"})

    @patch.dict("pagure.config.config", {"ALLOW_HTTP_PULL_PUSH": False})
    def test_http_clone_disabled(self):
        """Test that the HTTP clone endpoint gets correctly closed."""
        output = self.app.get(
            "/clonetest.git/info/refs?service=git-upload-pack"
        )
        self.assertEqual(output.status_code, 403)
        self.assertIn("not allowed", output.get_data(as_text=True))

    @patch.dict("pagure.config.config", {"ALLOW_HTTP_PULL_PUSH": True})
    def test_http_clone_invalid_service(self):
        """Test that the HTTP endpoint refuses invalid services."""
        output = self.app.get("/clonetest.git/info/refs?service=myservice")
        self.assertEqual(output.status_code, 400)
        self.assertIn("Unknown service", output.get_data(as_text=True))

    @patch.dict("pagure.config.config", {"ALLOW_HTTP_PULL_PUSH": True})
    def test_http_clone_invalid_project(self):
        """Test that the HTTP endpoint refuses invalid projects."""
        output = self.app.get(
            "/nosuchrepo.git/info/refs?service=git-upload-pack"
        )
        self.assertEqual(output.status_code, 404)
        self.assertIn("Project not found", output.get_data(as_text=True))

    @patch.dict("pagure.config.config", {"ALLOW_HTTP_PULL_PUSH": True})
    def test_http_clone_dumb(self):
        """Test that the HTTP endpoint refuses dumb service request."""
        output = self.app.get("/clonetest.git/info/refs")
        self.assertEqual(output.status_code, 400)
        self.assertIn("Please switch", output.get_data(as_text=True))

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": False,
        },
    )
    def test_http_push_disabled(self):
        """Test that the HTTP push gets refused."""
        output = self.app.get(
            "/clonetest.git/info/refs?service=git-receive-pack"
        )
        self.assertEqual(output.status_code, 403)
        self.assertIn("pushing disabled", output.get_data(as_text=True))
        output = self.app.post("/clonetest.git/git-receive-pack")
        self.assertEqual(output.status_code, 403)
        self.assertIn("pushing disabled", output.get_data(as_text=True))

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": True,
        },
    )
    def test_http_push_unauthed(self):
        """Test that the HTTP push gets refused unauthed."""
        output = self.app.get(
            "/clonetest.git/info/refs?service=git-receive-pack"
        )
        self.assertEqual(output.status_code, 401)
        self.assertIn("Authorization Required", output.get_data(as_text=True))

    @patch.dict("pagure.config.config", {"ALLOW_HTTP_PULL_PUSH": True})
    def test_http_clone_private_project_unauthed(self):
        """Test that the HTTP endpoint enforced project.private."""
        project = pagure.lib.query._get_project(self.session, "clonetest")
        project.private = True
        self.session.add(project)
        self.session.commit()

        output = self.app.get(
            "/clonetest.git/info/refs?service=git-upload-pack"
        )
        self.assertEqual(output.status_code, 404)
        self.assertIn("Project not found", output.get_data(as_text=True))

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": False,
        },
    )
    def test_http_clone(self):
        """Test that HTTP cloning gives reasonable output."""
        # Unfortunately, actually testing a git clone would need the app to
        # run on a TCP port, which the test environment doesn't do.

        output = self.app.get(
            "/clonetest.git/info/refs?service=git-upload-pack"
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("# service=git-upload-pack", output_text)
        self.assertIn(" refs/heads/master\n0000", output_text)

        output = self.app.post(
            "/clonetest.git/git-upload-pack",
            headers={"Content-Type": "application/x-git-upload-pack-request"},
        )
        # Git 2.17 returns 415, older return 200
        # Either means we didn't fully crash when returning the response
        self.assertIn(output.status_code, (200, 415))

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": False,
        },
    )
    def test_http_clone_private(self):
        """Test that HTTP cloning gives reasonable output with project.private."""
        # Unfortunately, actually testing a git clone would need the app to
        # run on a TCP port, which the test environment doesn't do.
        project = pagure.lib.query._get_project(self.session, "clonetest")
        project.private = True
        self.session.add(project)
        self.session.commit()

        output = self.app.get(
            "/clonetest.git/info/refs?service=git-upload-pack"
        )
        self.assertEqual(output.status_code, 404)
        self.assertIn("Project not found", output.get_data(as_text=True))

        output = self.app.get(
            "/clonetest.git/info/refs?service=git-upload-pack",
            environ_overrides={"REMOTE_USER": "pingou"},
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("# service=git-upload-pack", output_text)
        self.assertIn(" refs/heads/master\n0000", output_text)

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": True,
        },
    )
    def test_http_push(self):
        """Test that the HTTP push gets accepted."""
        output = self.app.get(
            "/clonetest.git/info/refs?service=git-receive-pack",
            environ_overrides={"REMOTE_USER": "pingou"},
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("# service=git-receive-pack", output_text)
        self.assertIn(" refs/heads/master\x00", output_text)

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": True,
        },
    )
    def test_http_push_api_token(self):
        """Test that the HTTP push gets accepted."""

        headers = {
            "Authorization": b"Basic %s"
            % base64.b64encode(b"pingou:aaabbbcccddd")
        }
        output = self.app.get(
            "/test.git/info/refs?service=git-receive-pack",
            headers=headers,
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("# service=git-receive-pack", output_text)
        self.assertIn(" refs/heads/master\x00", output_text)

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": True,
        },
    )
    def test_http_push_projectless_api_token(self):
        """Test that the HTTP push gets accepted."""
        tests.create_tokens(self.session, project_id=None, suffix="2")
        tests.create_tokens_acl(
            self.session, token_id="aaabbbcccddd2", acl_name="commit"
        )

        headers = {
            "Authorization": b"Basic %s"
            % base64.b64encode(b"pingou:aaabbbcccddd2")
        }
        output = self.app.get(
            "/clonetest.git/info/refs?service=git-receive-pack",
            headers=headers,
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("# service=git-receive-pack", output_text)
        self.assertIn(" refs/heads/master\x00", output_text)

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": True,
        },
    )
    def test_http_push__invalid_project_for_api_token(self):
        """Test that the HTTP push gets accepted."""

        headers = {
            "Authorization": b"Basic %s"
            % base64.b64encode(b"pingou:aaabbbcccddd")
        }
        output = self.app.get(
            "/clonetest.git/info/refs?service=git-receive-pack",
            headers=headers,
        )
        self.assertEqual(output.status_code, 401)
        self.assertIn("Authorization Required", output.get_data(as_text=True))

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": True,
        },
    )
    def test_http_push_api_token_invalid_user(self):
        """Test that the HTTP push gets accepted."""

        headers = {
            "Authorization": b"Basic %s"
            % base64.b64encode(b"invalid:aaabbbcccddd")
        }
        output = self.app.get(
            "/clonetest.git/info/refs?service=git-receive-pack",
            headers=headers,
        )
        self.assertEqual(output.status_code, 401)
        self.assertIn("Authorization Required", output.get_data(as_text=True))

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": True,
        },
    )
    def test_http_push_invalid_api_token(self):
        """Test that the HTTP push gets accepted."""

        headers = {
            "Authorization": b"Basic %s"
            % base64.b64encode(b"pingou:invalid_token")
        }
        output = self.app.get(
            "/clonetest.git/info/refs?service=git-receive-pack",
            headers=headers,
        )
        self.assertEqual(output.status_code, 401)
        self.assertIn("Authorization Required", output.get_data(as_text=True))

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": True,
        },
    )
    def test_http_push_invalid_acl_on_token(self):
        """Test that the HTTP push gets accepted."""
        tests.create_tokens(self.session, suffix="2")
        tests.create_tokens_acl(
            self.session, token_id="aaabbbcccddd2", acl_name="commit_flag"
        )

        headers = {
            "Authorization": b"Basic %s"
            % base64.b64encode(b"pingou:aaabbbcccddd2")
        }
        output = self.app.get(
            "/test.git/info/refs?service=git-receive-pack",
            headers=headers,
        )
        self.assertEqual(output.status_code, 401)
        self.assertIn("Authorization Required", output.get_data(as_text=True))

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": True,
            "PAGURE_AUTH": "local",
        },
    )
    def test_http_push_local_auth(self):
        """Test that the HTTP push gets accepted."""

        headers = {
            "Authorization": b"Basic %s" % base64.b64encode(b"pingou:foo")
        }
        output = self.app.get(
            "/clonetest.git/info/refs?service=git-receive-pack",
            headers=headers,
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("# service=git-receive-pack", output_text)
        self.assertIn(" refs/heads/master\x00", output_text)

    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": True,
            "PAGURE_AUTH": "local",
        },
    )
    def test_http_push_local_auth_invalid_username(self):
        """Test that the HTTP push gets accepted."""

        headers = {
            "Authorization": b"Basic %s" % base64.b64encode(b"invalid:foo")
        }
        output = self.app.get(
            "/clonetest.git/info/refs?service=git-receive-pack",
            headers=headers,
        )
        self.assertEqual(output.status_code, 401)
        self.assertIn("Authorization Required", output.get_data(as_text=True))
