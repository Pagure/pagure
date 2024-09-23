# -*- coding: utf-8 -*-

"""
 (c) 2020 - Copyright Red Hat Inc

 Authors:
   Aurelien Bompard <abompard@fedoraproject.org>

"""

from __future__ import unicode_literals

__requires__ = ["SQLAlchemy >= 0.8"]
import pkg_resources

import unittest
import json
import sys
import os

import flask
from mock import patch, Mock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib
import tests

from pagure.ui.oidc_login import fas_user_from_oidc, oidc


CLIENT_SECRETS = {
    "web": {
        "client_id": "dummy",
        "client_secret": "dummy",
        "auth_uri": "dummy-uri://",
        "token_uri": "dummy-uri://",
        "userinfo_uri": "dummy-uri://",
        "redirect_uris": ["http://localhost:5000/oidc"],
        "issuer": "http://localhost:5000/oidc/",  # Additional field, required since flask-oidc v2.0.0
    }
}


class PagureFlaskOIDCLogintests(tests.SimplePagureTest):
    """Tests for OIDC login in the flask app controller of pagure"""

    populate_db = False

    def setUp(self):
        """Create the application with PAGURE_AUTH being local."""
        super(PagureFlaskOIDCLogintests, self).setUp()

        self.app = pagure.flask_app.create_app(
            {"DB_URL": self.dbpath, "PAGURE_AUTH": "local"}
        )
        # Remove the log handlers for the tests
        self.app.logger.handlers = []

        secrets_path = os.path.join(self.path, "client_secrets.json")
        self.config_patcher = patch.dict(
            "pagure.config.config",
            {
                "OIDC_PAGURE_EMAIL": "email",
                "OIDC_PAGURE_FULLNAME": "name",
                "OIDC_PAGURE_USERNAME": "preferred_username",
                "OIDC_PAGURE_SSH_KEY": "ssh_key",
                "OIDC_PAGURE_GROUPS": "groups",
                "OIDC_CLIENT_SECRETS": secrets_path,
            },
        )
        self.config_patcher.start()

        with open(secrets_path, "w") as secrets:
            secrets.write(json.dumps(CLIENT_SECRETS))

        self.request_context = self.app.test_request_context("/")
        self.request_context.push()
        flask.session["oidc_logintime"] = "dummy-logintime"
        flask.g.session = Mock()  # the DB session should be here

        flask.g.oidc_id_token = {"sub": "dummy"}  # Used in flask-oidc < 2.0.0
        flask.session["oidc_auth_token"] = {
            "sub": "dummy"
        }  # Used in flask-oidc >= 2.0.0

        self.user_info = {
            "email": "dummy@example.com",
            "name": "Dummy User",
            "preferred_username": "dummy",
        }

        oidc.init_app(self.app)

    def tearDown(self):
        self.request_context.pop()
        self.config_patcher.stop()

    def test_fas_user_from_oidc(self):
        """Test the user creation function."""
        user_info = self.user_info.copy()

        flask.g._oidc_userinfo = user_info  # Used in flask-oidc < 2.0.0
        flask.session["oidc_auth_profile"] = (
            user_info  # Used in flask-oidc >= 2.0.0
        )

        fas_user_from_oidc()
        self.assertIsNotNone(getattr(flask.g, "fas_user", None))
        self.assertEqual(flask.g.fas_user.username, "dummy")
        self.assertEqual(flask.g.fas_user.fullname, "Dummy User")
        self.assertIsNone(flask.g.fas_user.ssh_key)
        self.assertEqual(flask.g.fas_user.groups, [])

    def test_fas_user_from_oidc_groups(self):
        """Test the user creation function."""
        user_info = self.user_info.copy()
        user_info["groups"] = ["group1", "group2"]

        flask.g._oidc_userinfo = user_info  # Used in flask-oidc < 2.0.0
        flask.session["oidc_auth_profile"] = (
            user_info  # Used in flask-oidc >= 2.0.0
        )

        fas_user_from_oidc()
        self.assertEqual(flask.g.fas_user.groups, ["group1", "group2"])

    def test_fas_user_from_oidc_ssh(self):
        """Test the user creation function."""
        user_info = self.user_info.copy()
        user_info["ssh_key"] = "dummy ssh key"

        flask.g._oidc_userinfo = user_info  # Used in flask-oidc < 2.0.0
        flask.session["oidc_auth_profile"] = (
            user_info  # Used in flask-oidc >= 2.0.0
        )

        fas_user_from_oidc()
        self.assertEqual(flask.g.fas_user.ssh_key, "dummy ssh key")

    def test_fas_user_from_oidc_ssh_b64(self):
        """The SSH key may be base64-encoded"""
        user_info = self.user_info.copy()
        user_info["ssh_key"] = "ZHVtbXkgc3NoIGtleQ=="

        flask.g._oidc_userinfo = user_info  # Used in flask-oidc < 2.0.0
        flask.session["oidc_auth_profile"] = (
            user_info  # Used in flask-oidc >= 2.0.0
        )

        fas_user_from_oidc()
        self.assertEqual(flask.g.fas_user.ssh_key, "dummy ssh key")


if __name__ == "__main__":
    unittest.main(verbosity=2)
