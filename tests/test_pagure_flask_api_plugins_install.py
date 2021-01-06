# -*- coding: utf-8 -*-

"""
 (c) 2019 - Copyright Red Hat Inc

 Authors:
   Michal Konecny <mkonecny@redhat.com>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import unittest
import sys
import os
import json

from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query  # noqa: E402
import tests  # noqa: E402


class PagureFlaskApiPluginInstalltests(tests.Modeltests):
    """Tests for the flask API of pagure for installing a plugin"""

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiPluginInstalltests, self).setUp()

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create project-less token for user foo
        item = pagure.lib.model.Token(
            id="project-less-foo",
            user_id=2,
            project_id=None,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30),
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session, token_id="project-less-foo")

        # Create project-specific token for user foo
        item = pagure.lib.model.Token(
            id="project-specific-foo",
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30),
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session, token_id="project-specific-foo")

    def test_install_plugin_own_project_no_data(self):
        """Test installing a new plugin on a project for which you're the
        main maintainer.
        """

        # pingou's token with all the ACLs
        headers = {"Authorization": "token aaabbbcccddd"}

        # Install a plugin on /test/ where pingou is the main admin
        output = self.app.post(
            "/api/0/test/settings/Mail/install", headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDREQ.name, data["error_code"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDREQ.value, data["error"])
        self.assertEqual(
            data["errors"], {"mail_to": ["This field is required."]}
        )

    def test_install_plugin_own_project(self):
        """Test installing a new plugin on a project for which you're the
        main maintainer.
        """

        # pingou's token with all the ACLs
        headers = {"Authorization": "token aaabbbcccddd"}

        # complete data set
        data = {"mail_to": "serg@wh40k.com"}

        # Create an issue on /test/ where pingou is the main admin
        output = self.app.post(
            "/api/0/test/settings/Mail/install", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "plugin": {"mail_to": "serg@wh40k.com"},
                "message": "Hook 'Mail' activated",
            },
        )

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_install_plugin_someone_else_project_project_less_token(self):
        """Test installing a new plugin on a project with which you have
        nothing to do.
        """

        # pingou's token with all the ACLs
        headers = {"Authorization": "token project-less-foo"}

        # Install a plugin on /test/ where pingou is the main admin
        output = self.app.post(
            "/api/0/test/settings/Prevent creating new branches by git push/"
            "install",
            headers=headers,
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "plugin": {},
                "message": "Hook 'Prevent creating new branches by git push' "
                "activated",
            },
        )

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_install_plugin_project_specific_token(self):
        """Test installing a new plugin on a project with a regular
        project-specific token.
        """

        # pingou's token with all the ACLs
        headers = {"Authorization": "token project-specific-foo"}

        # complete data set
        data = {"mail_to": "serg@wh40k.com"}

        # Create an issue on /test/ where pingou is the main admin
        output = self.app.post(
            "/api/0/test/settings/Mail/install", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "plugin": {"mail_to": "serg@wh40k.com"},
                "message": "Hook 'Mail' activated",
            },
        )

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_install_plugin_invalid_project_specific_token(self):
        """Test installing a new plugin on a project with a regular
        project-specific token but for another project.
        """

        # pingou's token with all the ACLs
        headers = {"Authorization": "token project-specific-foo"}

        # complete data set
        data = {"mail_to": "serg@wh40k.com"}

        # Create an issue on /test/ where pingou is the main admin
        output = self.app.post(
            "/api/0/test2/settings/Mail/install", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
