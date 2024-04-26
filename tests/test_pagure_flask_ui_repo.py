# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import json
import unittest
import re
import shutil
import sys
import tempfile
import time
import os

cchardet = None
try:
    import cchardet
except ImportError:
    pass

import pagure_messages
import pygit2
import six
from fedora_messaging import testing
from mock import ANY, patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests
from pagure.lib.repo import PagureRepo
from pagure.utils import __get_file_in_tree as get_file_in_tree


class PagureFlaskRepotests(tests.Modeltests):
    """Tests for flask app controller of pagure"""

    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureFlaskRepotests, self).setUp()

        pagure.config.config["VIRUS_SCAN_ATTACHMENTS"] = False
        pagure.config.config["UPLOAD_FOLDER_URL"] = "/releases/"
        pagure.config.config["UPLOAD_FOLDER_PATH"] = os.path.join(
            self.path, "releases"
        )

    @patch("pagure.decorators.admin_session_timedout")
    def test_add_user_when_user_mngt_off(self, ast):
        """Test the add_user endpoint when user management is turned off
        in the pagure instance"""
        pagure.config.config["ENABLE_USER_MNGT"] = False
        ast.return_value = False

        # No Git repo
        output = self.app.get("/foo/adduser")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        # User not logged in
        output = self.app.get("/test/adduser")
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):

            output = self.app.get("/test/adduser")
            self.assertEqual(output.status_code, 404)

            # just get the csrf token
            pagure.config.config["ENABLE_USER_MNGT"] = True
            output = self.app.get("/test/adduser")
            output_text = output.get_data(as_text=True)
            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            pagure.config.config["ENABLE_USER_MNGT"] = False

            data = {"user": "ralph"}

            output = self.app.post("/test/adduser", data=data)
            self.assertEqual(output.status_code, 404)

            data["csrf_token"] = csrf_token
            output = self.app.post("/test/adduser", data=data)
            self.assertEqual(output.status_code, 404)

            data["user"] = "foo"
            tests.create_projects_git(os.path.join(self.path, "repos"))
            output = self.app.post(
                "/test/adduser", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 404)

        pagure.config.config["ENABLE_USER_MNGT"] = True

    @patch("pagure.decorators.admin_session_timedout")
    def test_add_deploykey(self, ast):
        """Test the add_deploykey endpoint."""
        ast.return_value = False

        # No git repo
        output = self.app.get("/foo/adddeploykey")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        # User not logged in
        output = self.app.get("/test/adddeploykey")
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/adddeploykey")
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.get("/test/adddeploykey")
            self.assertEqual(output.status_code, 302)

            # Redirect also happens for POST request
            output = self.app.post("/test/adddeploykey")
            self.assertEqual(output.status_code, 302)

        # Need to do this un-authentified since our fake user isn't in the DB
        # Check the message flashed during the redirect
        output = self.app.get("/", follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("Action canceled, try it " "again", output_text)

        ast.return_value = False

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/adddeploykey")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Add deploy key to the", output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"ssh_key": "asdf", "pushaccess": "false"}

            # No CSRF token
            output = self.app.post("/test/adddeploykey", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Add deploy key to the", output_text)

            data["csrf_token"] = csrf_token

            # First, invalid SSH key
            output = self.app.post("/test/adddeploykey", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Add deploy key to the", output_text)
            self.assertIn("SSH key invalid", output_text)

            # Next up, multiple SSH keys
            data[
                "ssh_key"
            ] = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q==\nssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q=="
            output = self.app.post(
                "/test/adddeploykey", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Please add single SSH keys.", output_text)

            # Now, a valid SSH key
            data[
                "ssh_key"
            ] = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q=="
            output = self.app.post(
                "/test/adddeploykey", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("SSH key added", output_text)
            self.assertNotIn("Push Access", output_text)

            # And now, adding the same key
            output = self.app.post(
                "/test/adddeploykey", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("SSH key already exists", output_text)

            # And next, a key with push access
            data[
                "ssh_key"
            ] = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQC9Xwc2RDzPBhlEDARfHldGjudIVoa04tqT1JVKGQmyllTFz7Rb8CngQL3e7zyNzotnhwYKHdoiLlPkVEiDee4dWMUe48ilqId+FJZQGhyv8fu4BoFdE1AJUVylzmltbLg14VqG5gjTpXgtlrEva9arKwBMHJjRYc8ScaSn3OgyQw=="
            data["pushaccess"] = "true"
            output = self.app.post(
                "/test/adddeploykey", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("SSH key added", output_text)
            self.assertIn("Push Access", output_text)

    @patch("pagure.decorators.admin_session_timedout")
    @patch.dict("pagure.config.config", {"DEPLOY_KEY": False})
    def test_add_deploykey_disabled(self, ast):
        """Test the add_deploykey endpoint when it's disabled in the config."""
        ast.return_value = False
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/adddeploykey")
            self.assertEqual(output.status_code, 404)

            output = self.app.post("/test/adddeploykey")
            self.assertEqual(output.status_code, 404)

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    @patch("pagure.decorators.admin_session_timedout")
    def test_add_user(self, ast):
        """Test the add_user endpoint."""
        ast.return_value = False

        # No git repo
        output = self.app.get("/foo/adduser")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        # User not logged in
        output = self.app.get("/test/adduser")
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/adduser")
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.get("/test/adduser")
            self.assertEqual(output.status_code, 302)

            # Redirect also happens for POST request
            output = self.app.post("/test/adduser")
            self.assertEqual(output.status_code, 302)

        # Need to do this un-authentified since our fake user isn't in the DB
        # Check the message flashed during the redirect
        output = self.app.get("/", follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("Action canceled, try it " "again", output_text)

        ast.return_value = False

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/adduser")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Add user to the", output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"user": "ralph"}

            # Missing access and no CSRF
            output = self.app.post("/test/adduser", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Add user - test - Pagure</title>", output_text
            )
            self.assertIn("<strong>Add user to the", output_text)

            # No CSRF
            output = self.app.post("/test/adduser", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Add user - test - Pagure</title>", output_text
            )

            # Missing access
            data["csrf_token"] = csrf_token
            output = self.app.post("/test/adduser", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Add user - test - Pagure</title>", output_text
            )
            self.assertIn("<strong>Add user to the", output_text)

            # Unknown user
            data["access"] = "commit"
            output = self.app.post("/test/adduser", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Add user - test - Pagure</title>", output_text
            )
            self.assertIn("<strong>Add user to the", output_text)
            self.assertIn("No user &#34;ralph&#34; found", output_text)

            # All correct
            data["user"] = "foo"
            with testing.mock_sends(
                pagure_messages.ProjectUserAddedV1(
                    topic="pagure.project.user.added",
                    body={
                        "project": {
                            "id": 1,
                            "name": "test",
                            "fullname": "test",
                            "url_path": "test",
                            "full_url": "http://localhost.localdomain/test",
                            "description": "test project #1",
                            "namespace": None,
                            "parent": None,
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "url_path": "user/pingou",
                                "full_url": "http://localhost.localdomain/user/pingou",
                            },
                            "access_users": {
                                "owner": ["pingou"],
                                "admin": [],
                                "commit": ["foo"],
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
                        "new_user": "foo",
                        "access": "commit",
                        "branches": None,
                        "agent": "pingou",
                    },
                )
            ):
                output = self.app.post(
                    "/test/adduser", data=data, follow_redirects=True
                )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("User added", output_text)

            # Update access
            data["access"] = "ticket"
            data["user"] = "foo"
            with testing.mock_sends(
                pagure_messages.ProjectUserAccessUpdatedV1(
                    topic="pagure.project.user.access.updated",
                    body={
                        "project": {
                            "id": 1,
                            "name": "test",
                            "fullname": "test",
                            "url_path": "test",
                            "full_url": "http://localhost.localdomain/test",
                            "description": "test project #1",
                            "namespace": None,
                            "parent": None,
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "url_path": "user/pingou",
                                "full_url": "http://localhost.localdomain/user/pingou",
                            },
                            "access_users": {
                                "owner": ["pingou"],
                                "admin": [],
                                "commit": [],
                                "collaborator": [],
                                "ticket": ["foo"],
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
                        "new_user": "foo",
                        "new_access": "ticket",
                        "new_branches": None,
                        "agent": "pingou",
                    },
                )
            ):
                output = self.app.post(
                    "/test/adduser", data=data, follow_redirects=True
                )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("User access updated", output_text)

    @patch("pagure.decorators.admin_session_timedout")
    def test_add_group_project_when_user_mngt_off(self, ast):
        """Test the add_group_project endpoint  when user management is
        turned off in the pagure instance"""
        pagure.config.config["ENABLE_USER_MNGT"] = False
        ast.return_value = False

        # No Git repo
        output = self.app.get("/foo/addgroup")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        # User not logged in
        output = self.app.get("/test/addgroup")
        self.assertEqual(output.status_code, 302)

        msg = pagure.lib.query.add_group(
            self.session,
            group_name="foo",
            group_type="bar",
            display_name="foo group",
            description=None,
            user="pingou",
            is_admin=False,
            blacklist=pagure.config.config["BLACKLISTED_GROUPS"],
        )
        self.session.commit()
        self.assertEqual(msg, "User `pingou` added to the group `foo`.")

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            # just get the csrf token
            pagure.config.config["ENABLE_USER_MNGT"] = True

            output = self.app.get("/test/addgroup")
            output_text = output.get_data(as_text=True)
            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]
            pagure.config.config["ENABLE_USER_MNGT"] = False

            data = {"group": "ralph"}

            output = self.app.post("/test/addgroup", data=data)
            self.assertEqual(output.status_code, 404)

            data["csrf_token"] = csrf_token
            output = self.app.post("/test/addgroup", data=data)
            self.assertEqual(output.status_code, 404)

            data["group"] = "foo"
            output = self.app.post(
                "/test/addgroup", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 404)

        pagure.config.config["ENABLE_USER_MNGT"] = True

    @patch.dict("pagure.config.config", {"ENABLE_GROUP_MNGT": False})
    @patch("pagure.decorators.admin_session_timedout")
    def test_add_group_project_grp_mngt_off(self, ast):
        """Test the add_group_project endpoint  when group management is
        turned off in the pagure instance"""
        ast.return_value = False

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):

            data = {
                "group": "ralph",
                "access": "ticket",
                "csrf_token": self.get_csrf(),
            }
            output = self.app.post(
                "/test/addgroup", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Add group - test - Pagure</title>", output_text
            )
            self.assertIn("No group ralph found.", output_text)

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    @patch("pagure.decorators.admin_session_timedout")
    def test_add_group_project(self, ast):
        """Test the add_group_project endpoint."""
        ast.return_value = False

        # No Git repo
        output = self.app.get("/foo/addgroup")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        # User not logged in
        output = self.app.get("/test/addgroup")
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/addgroup")
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.get("/test/addgroup")
            self.assertEqual(output.status_code, 302)

            # Redirect also happens for POST request
            output = self.app.post("/test/addgroup")
            self.assertEqual(output.status_code, 302)

        # Need to do this un-authentified since our fake user isn't in the DB
        # Check the message flashed during the redirect
        output = self.app.get("/", follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("Action canceled, try it " "again", output_text)

        ast.return_value = False

        msg = pagure.lib.query.add_group(
            self.session,
            group_name="foo",
            display_name="foo group",
            description=None,
            group_type="bar",
            user="pingou",
            is_admin=False,
            blacklist=pagure.config.config["BLACKLISTED_GROUPS"],
        )
        self.session.commit()
        self.assertEqual(msg, "User `pingou` added to the group `foo`.")

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/addgroup")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Add group to the", output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"group": "ralph"}

            # Missing CSRF
            output = self.app.post("/test/addgroup", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Add group - test - Pagure</title>", output_text
            )
            self.assertIn("<strong>Add group to the", output_text)

            # Missing access
            data["csrf_token"] = csrf_token
            output = self.app.post("/test/addgroup", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Add group - test - Pagure</title>", output_text
            )
            self.assertIn("<strong>Add group to the", output_text)

            # All good
            data["access"] = "ticket"
            with testing.mock_sends(
                pagure_messages.ProjectGroupAddedV1(
                    topic="pagure.project.group.added",
                    body={
                        "project": {
                            "id": 1,
                            "name": "test",
                            "fullname": "test",
                            "url_path": "test",
                            "full_url": "http://localhost.localdomain/test",
                            "description": "test project #1",
                            "namespace": None,
                            "parent": None,
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "url_path": "user/pingou",
                                "full_url": "http://localhost.localdomain/user/pingou",
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
                                "ticket": ["ralph"],
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
                        "new_group": "ralph",
                        "access": "ticket",
                        "branches": None,
                        "agent": "pingou",
                    },
                )
            ):
                output = self.app.post(
                    "/test/addgroup", data=data, follow_redirects=True
                )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("Group added", output_text)

            # All good -- Update existing group/access
            data["access"] = "commit"
            with testing.mock_sends(
                pagure_messages.ProjectGroupAccessUpdatedV1(
                    topic="pagure.project.group.access.updated",
                    body={
                        "project": {
                            "id": 1,
                            "name": "test",
                            "fullname": "test",
                            "url_path": "test",
                            "full_url": "http://localhost.localdomain/test",
                            "description": "test project #1",
                            "namespace": None,
                            "parent": None,
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "url_path": "user/pingou",
                                "full_url": "http://localhost.localdomain/user/pingou",
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
                                "commit": ["ralph"],
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
                        "new_group": "ralph",
                        "new_access": "commit",
                        "new_branches": None,
                        "agent": "pingou",
                    },
                )
            ):
                output = self.app.post(
                    "/test/addgroup", data=data, follow_redirects=True
                )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("Group access updated", output_text)

    @patch("pagure.decorators.admin_session_timedout")
    def test_remove_user_when_user_mngt_off(self, ast):
        """Test the remove_user endpoint when user management is turned
        off in the pagure instance"""
        pagure.config.config["ENABLE_USER_MNGT"] = False
        ast.return_value = False

        # Git repo not found
        output = self.app.post("/foo/dropuser/1")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            tests.create_projects(self.session)
            tests.create_projects_git(os.path.join(self.path, "repos"))

            output = self.app.post("/test/settings")
            output_text = output.get_data(as_text=True)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"csrf_token": csrf_token}

            output = self.app.post(
                "/test/dropuser/2", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 404)

        # User not logged in
        output = self.app.post("/test/dropuser/1")
        self.assertEqual(output.status_code, 302)

        # Add an user to a project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.add_user_to_project(
            session=self.session, project=repo, new_user="foo", user="pingou"
        )
        self.session.commit()
        self.assertEqual(msg, "User added")

        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/dropuser/2", follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            data = {"csrf_token": csrf_token}

            output = self.app.post(
                "/test/dropuser/2", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 404)

        pagure.config.config["ENABLE_USER_MNGT"] = True

    @patch("pagure.decorators.admin_session_timedout")
    def test_remove_deploykey(self, ast):
        """Test the remove_deploykey endpoint."""
        ast.return_value = False

        # Git repo not found
        output = self.app.post("/foo/dropdeploykey/1")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/foo/dropdeploykey/1")
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(os.path.join(self.path, "repos"))

            output = self.app.post("/test/dropdeploykey/1")
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.post("/test/dropdeploykey/1")
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

        # User not logged in
        output = self.app.post("/test/dropdeploykey/1")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/settings")
            output_text = output.get_data(as_text=True)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"csrf_token": csrf_token}

            output = self.app.post(
                "/test/dropdeploykey/1", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("Deploy key does not exist in project", output_text)

        # Add a deploy key to a project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        pingou = pagure.lib.query.get_user(self.session, "pingou")
        msg = pagure.lib.query.add_sshkey_to_project_or_user(
            session=self.session,
            project=repo,
            ssh_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q==",
            pushaccess=True,
            creator=pingou,
        )
        self.session.commit()
        self.assertEqual(msg, "SSH key added")

        with tests.user_set(self.app.application, user):
            output = self.app.post(
                "/test/dropdeploykey/1", follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertNotIn("Deploy key removed", output_text)

            data = {"csrf_token": csrf_token}
            output = self.app.post(
                "/test/dropdeploykey/1", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("Deploy key removed", output_text)

    @patch("pagure.decorators.admin_session_timedout")
    @patch.dict("pagure.config.config", {"DEPLOY_KEY": False})
    def test_remove_deploykey_disabled(self, ast):
        """Test the remove_deploykey endpoint when it's disabled in the
        config.
        """
        ast.return_value = False
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/dropdeploykey/1")
            self.assertEqual(output.status_code, 404)

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    @patch("pagure.decorators.admin_session_timedout")
    def test_remove_user(self, ast):
        """Test the remove_user endpoint."""
        ast.return_value = False

        # Git repo not found
        output = self.app.post("/foo/dropuser/1")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/foo/dropuser/1")
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(os.path.join(self.path, "repos"))

            output = self.app.post("/test/dropuser/1")
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.post("/test/dropuser/1")
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

        # User not logged in
        output = self.app.post("/test/dropuser/1")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/settings")
            output_text = output.get_data(as_text=True)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"csrf_token": csrf_token}

            output = self.app.post(
                "/test/dropuser/2", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn(
                "User does not have any " "access on the repo", output_text
            )

        # Add an user to a project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.users), 0)
        msg = pagure.lib.query.add_user_to_project(
            session=self.session, project=repo, new_user="foo", user="pingou"
        )
        self.session.commit()
        self.assertEqual(msg, "User added")
        self.assertEqual(len(repo.users), 1)

        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/dropuser/2", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertNotIn("User removed", output_text)
            self.assertIn('action="/test/dropuser/2">', output_text)
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(len(repo.users), 1)

            data = {"csrf_token": csrf_token}

            with testing.mock_sends(
                pagure_messages.ProjectUserRemovedV1(
                    topic="pagure.project.user.removed",
                    body={
                        "project": {
                            "id": 1,
                            "name": "test",
                            "fullname": "test",
                            "url_path": "test",
                            "full_url": "http://localhost.localdomain/test",
                            "description": "test project #1",
                            "namespace": None,
                            "parent": None,
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "url_path": "user/pingou",
                                "full_url": "http://localhost.localdomain/user/pingou",
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
                        "removed_user": "foo",
                        "agent": "pingou",
                    },
                )
            ):
                output = self.app.post(
                    "/test/dropuser/2", data=data, follow_redirects=True
                )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("User removed", output_text)
            self.assertNotIn('action="/test/dropuser/2">', output_text)

            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(len(repo.users), 0)

    @patch("pagure.decorators.admin_session_timedout")
    @patch("pagure.lib.notify.log")
    def test_remove_user_self(self, mock_log, ast):
        """Test the remove_user endpoint when removing themselves."""
        ast.return_value = False

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        # Add an user to a project
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.users), 0)
        msg = pagure.lib.query.add_user_to_project(
            session=self.session, project=repo, new_user="foo", user="pingou"
        )
        self.session.commit()
        self.assertEqual(msg, "User added")
        self.assertEqual(len(repo.users), 1)

        # Let user foo remove themselves
        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()
            data = {"csrf_token": csrf_token}

            output = self.app.post(
                "/test/dropuser/2", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h3 class="mb-0">\n<a href="/test"><strong>test</strong>'
                "</a>\n            </h3>",
                output_text,
            )
            self.assertIn("User removed", output_text)

        self.session.commit()
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.users), 0)

        mock_log.assert_called_with(ANY, topic="project.user.removed", msg=ANY)

    @patch("pagure.decorators.admin_session_timedout")
    def test_remove_group_project_when_user_mngt_off(self, ast):
        """Test the remove_group_project endpoint when user management is
        turned off in the pagure instance"""
        pagure.config.config["ENABLE_USER_MNGT"] = False
        ast.return_value = False

        # No Git repo
        output = self.app.post("/foo/dropgroup/1")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        # User not logged in
        output = self.app.post("/test/dropgroup/1")
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/settings")
            output_text = output.get_data(as_text=True)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"csrf_token": csrf_token}

            output = self.app.post(
                "/test/dropgroup/2", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 404)

        # Create the new group
        msg = pagure.lib.query.add_group(
            session=self.session,
            group_name="testgrp",
            group_type="user",
            display_name="testgrp group",
            description=None,
            user="pingou",
            is_admin=False,
            blacklist=[],
        )
        self.assertEqual(msg, "User `pingou` added to the group `testgrp`.")
        self.session.commit()

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        # Add the group to a project
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=repo,
            new_group="testgrp",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/dropgroup/1", follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            data = {"csrf_token": csrf_token}
            output = self.app.post(
                "/test/dropgroup/1", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 404)

        pagure.config.config["ENABLE_USER_MNGT"] = True

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    @patch("pagure.decorators.admin_session_timedout")
    def test_remove_group_project(self, ast):
        """Test the remove_group_project endpoint."""
        ast.return_value = False

        # No Git repo
        output = self.app.post("/foo/dropgroup/1")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/foo/dropgroup/1")
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(os.path.join(self.path, "repos"))

            output = self.app.post("/test/dropgroup/1")
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.post("/test/dropgroup/1")
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

        # User not logged in
        output = self.app.post("/test/dropgroup/1")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/settings")
            output_text = output.get_data(as_text=True)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"csrf_token": csrf_token}

            output = self.app.post(
                "/test/dropgroup/2", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn(
                "" "Group does not seem to be part of this project",
                output_text,
            )

        # Create the new group
        msg = pagure.lib.query.add_group(
            session=self.session,
            group_name="testgrp",
            group_type="user",
            display_name="testgrp group",
            description=None,
            user="pingou",
            is_admin=False,
            blacklist=[],
        )
        self.assertEqual(msg, "User `pingou` added to the group `testgrp`.")
        self.session.commit()

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        # Add the group to a project
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=repo,
            new_group="testgrp",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.groups), 1)

        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/dropgroup/1", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn('action="/test/dropgroup/1">', output_text)
            self.assertNotIn("Group removed", output_text)
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(len(repo.groups), 1)

            data = {"csrf_token": csrf_token}
            with testing.mock_sends(
                pagure_messages.ProjectGroupRemovedV1(
                    topic="pagure.project.group.removed",
                    body={
                        "project": {
                            "id": 1,
                            "name": "test",
                            "fullname": "test",
                            "url_path": "test",
                            "full_url": "http://localhost.localdomain/test",
                            "description": "test project #1",
                            "namespace": None,
                            "parent": None,
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "url_path": "user/pingou",
                                "full_url": "http://localhost.localdomain/user/pingou",
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
                        "removed_groups": ["testgrp"],
                        "agent": "pingou",
                    },
                )
            ):
                output = self.app.post(
                    "/test/dropgroup/1", data=data, follow_redirects=True
                )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("Group removed", output_text)
            self.assertNotIn('action="/test/dropgroup/1">', output_text)

            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(len(repo.groups), 0)

    @patch("pagure.decorators.admin_session_timedout")
    def test_update_project(self, ast):
        """Test the update_project endpoint."""
        ast.return_value = True

        # Git repo not found
        output = self.app.post("/foo/update")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            # Project does not exist
            output = self.app.post("/foo/update")
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(os.path.join(self.path, "repos"))

            # Session timed-out
            output = self.app.post("/test/update")
            self.assertEqual(output.status_code, 302)

            ast.return_value = False

            # Not allowed
            output = self.app.post("/test/update")
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.post("/test/update")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/update", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {
                "description": "new description for test project #1",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn(
                '<input class="form-control" name="avatar_email" value="" />',
                output_text,
            )
            self.assertIn("Project updated", output_text)

            # Edit the avatar_email
            data = {
                "description": "new description for test project #1",
                "avatar_email": "pingou@fp.o",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn(
                '<input class="form-control" name="avatar_email" value="pingou@fp.o" />',
                output_text,
            )
            self.assertIn("Project updated", output_text)

            # Reset the avatar_email
            data = {
                "description": "new description for test project #1",
                "avatar_email": "",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn(
                '<input class="form-control" name="avatar_email" value="" />',
                output_text,
            )
            self.assertIn("Project updated", output_text)

    @patch("pagure.decorators.admin_session_timedout")
    def test_update_project_update_tag(self, ast):
        """Test the view_settings endpoint when updating the project's tags.

        We had an issue where when you add an existing tag to a project we
        were querying the wrong table in the database. It would thus not find
        the tag, would try to add it, and (rightfully) complain about duplicated
        content.
        This test ensure we are behaving properly.
        """
        ast.return_value = False

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):

            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            # Add tag to a project so that they are added to the database
            data = {
                "csrf_token": csrf_token,
                "description": "Test project",
                "tags": "test,pagure,tag",
            }
            output = self.app.post(
                "/test/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("Project updated", output_text)

            # Remove two of the tags of the project, they will still be in
            # the DB but not associated to this project
            data = {
                "csrf_token": csrf_token,
                "description": "Test project",
                "tags": "tag",
            }
            output = self.app.post(
                "/test/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("Project updated", output_text)

            # Try re-adding the two tags, this used to fail before we fixed
            # it
            data = {
                "csrf_token": csrf_token,
                "description": "Test project",
                "tags": "test,pagure,tag",
            }
            output = self.app.post(
                "/test/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("Project updated", output_text)

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    @patch("pagure.decorators.admin_session_timedout")
    def test_view_settings(self, ast):
        """Test the view_settings endpoint."""
        ast.return_value = False

        # No Git repo
        output = self.app.get("/foo/settings")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/foo/settings")
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(os.path.join(self.path, "repos"))

            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.get("/test/settings")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            ast.return_value = True
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 302)

            ast.return_value = False
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )

            # Both checkbox checked before
            self.assertIn(
                '<input id="pull_requests" type="checkbox" value="y" '
                'name="pull_requests" checked=""/>',
                output_text,
            )
            self.assertIn(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" checked=""/>',
                output_text,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {}

            output = self.app.post(
                "/test/settings", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )

            # Both checkbox are still checked
            output = self.app.get("/test/settings", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn(
                '<input id="pull_requests" type="checkbox" value="y" '
                'name="pull_requests" checked=""/>',
                output_text,
            )
            self.assertIn(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" checked=""/>',
                output_text,
            )

            data = {"csrf_token": csrf_token}

            output = self.app.post(
                "/test/settings", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - test - Pagure</title>", output_text
            )
            self.assertIn(
                "Edited successfully " "settings of repo: test", output_text
            )

            # Both checkbox are now un-checked
            output = self.app.get("/test/settings", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn(
                '<input id="pull_requests" type="checkbox" value="y" '
                'name="pull_requests" />',
                output_text,
            )
            self.assertIn(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" />',
                output_text,
            )

            data = {
                "csrf_token": csrf_token,
                "pull_requests": "y",
                "issue_tracker": "y",
                "fedmsg_notifications": "y",
            }
            with testing.mock_sends(
                pagure_messages.ProjectEditV1(
                    topic="pagure.project.edit",
                    body={
                        "project": {
                            "id": 1,
                            "name": "test",
                            "fullname": "test",
                            "url_path": "test",
                            "full_url": "http://localhost.localdomain/test",
                            "description": "test project #1",
                            "namespace": None,
                            "parent": None,
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "url_path": "user/pingou",
                                "full_url": "http://localhost.localdomain/user/pingou",
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
                        "fields": [
                            "fedmsg_notifications",
                            "issue_tracker",
                            "pull_requests",
                        ],
                        "agent": "pingou",
                    },
                )
            ):
                output = self.app.post(
                    "/test/settings", data=data, follow_redirects=True
                )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - test - Pagure</title>", output_text
            )
            self.assertIn(
                "Edited successfully " "settings of repo: test", output_text
            )

            # Both checkbox are again checked
            output = self.app.get("/test/settings", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn(
                '<input id="pull_requests" type="checkbox" value="y" '
                'name="pull_requests" checked=""/>',
                output_text,
            )
            self.assertIn(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" checked=""/>',
                output_text,
            )

    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_view_settings_custom_fields(self):
        """Test the view_settings endpoint when the project has some custom
        field for issues."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.set_custom_key_fields(
            self.session,
            repo,
            ["bugzilla", "upstream", "reviewstatus"],
            ["link", "boolean", "list"],
            [
                "unused data for non-list type",
                "",
                "ack",
                "nack",
                "needs review",
            ],
            [None, None, None],
        )
        self.session.commit()
        self.assertEqual(msg, "List of custom fields updated")
        self.assertIsNotNone(repo.issue_keys)

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)

    @patch("pagure.decorators.admin_session_timedout")
    def test_view_settings_pr_only(self, ast):
        """Test the view_settings endpoint when turning on PR only."""
        ast.return_value = False
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )

            csrf_token = self.get_csrf(output=output)

            data = {
                "csrf_token": csrf_token,
                "pull_requests": "y",
                "issue_tracker": "y",
                "pull_request_access_only": "y",
            }
            output = self.app.post(
                "/test/settings", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - test - Pagure</title>", output_text
            )
            self.assertIn(
                "Edited successfully " "settings of repo: test", output_text
            )

            # Both checkbox are again checked
            output = self.app.get("/test/settings", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn(
                '<input id="pull_requests" type="checkbox" value="y" '
                'name="pull_requests" checked=""/>',
                output_text,
            )
            self.assertIn(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" checked=""/>',
                output_text,
            )
            self.assertIn(
                '<input id="pull_request_access_only" type="checkbox" '
                'value="y" name="pull_request_access_only" checked=""/>',
                output_text,
            )

    @patch("pagure.decorators.admin_session_timedout")
    def test_fields_in_view_settings(self, ast):
        """Test the default fields in view_settings endpoint."""
        ast.return_value = False

        # No Git repo
        output = self.app.get("/foo/settings")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/foo/settings")
            self.assertEqual(output.status_code, 404)

            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name="test",
                description="test project #1",
                hook_token="aaabbbccc",
            )
            self.session.add(item)
            self.session.commit()
            tests.create_projects_git(os.path.join(self.path, "repos"))

            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.get("/test/settings")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            ast.return_value = True
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 302)

            ast.return_value = False
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            # Check that the priorities have their empty fields
            self.assertIn(
                """<div class="form-group settings-field-rows" id="priorities-list">
                        <div class="row hidden blank-field">
                            <div class="col-sm-2" >
                              <input type="text" name="priority_weigth"
                                     value="" size="3" class="form-control"/>
                            </div>
                            <div class="col-sm-9">
                              <input type="text" name="priority_title"
                                     value="" class="form-control"/>
                            </div>""",
                output_text,
            )

            # Check that the milestones have their empty fields
            self.assertIn(
                """<div id="milestones">
      <div class="row p-t-1 milestone" id="milestone_1">
        <input type="hidden" name="milestones" value="1">
        <div class="col-sm-4 p-r-0">
          <input type="text" name="milestone_1_name"
            value="" size="3" class="form-control"/>
        </div>
        <div class="col-sm-4 p-r-0">
          <input type="text" name="milestone_1_date"
            value="" class="form-control"/>
        </div>
        <div class="col-sm-2 p-r-0" >
            <span class="fa fa-long-arrow-up milestone_order_up"
                data-stone="1"></span>
            <span class="fa fa-long-arrow-down milestone_order_bottom"
                data-stone="1"></span>
        </div>
        <div class="col-sm-1 p-r-0" >
            <input type="checkbox" name="milestone_1_active" />
        </div>
      </div>""",
                output_text,
            )

            # Check that the close_status have its empty field
            self.assertIn(
                """<div class="form-group settings-field-rows" id="status-list">
                        <div class="row hidden blank-field">
                            <div class="col-sm-11" >
                              <input type="text" name="close_status"
                                      value="" class="form-control"/>
                            </div>""",
                output_text,
            )

            # Check that the custom fields have their empty fields
            self.assertIn(
                """<div class="form-group settings-field-rows" id="customfields-list">
                              <div class="row hidden blank-field">
                                  <div class="col-sm-2 pr-0">
                                      <input type="text" name="custom_keys"
                                        value="" class="form-control"/>
                                    </div>
                                    <div class="col-sm-2 pr-0">
                                      <select name="custom_keys_type" class="form-control custom-keys">
                                        <option value="text">Text</option>
                                        <option value="boolean">Boolean</option>
                                        <option value="link">Link</option>
                                        <option value="list">List</option>
                                        <option value="date">Date</option>
                                      </select>
                                    </div>
                                    <div class="col-sm-6 pr-0">
                                      <input title="Comma separated list items" type="text" name="custom_keys_data" value="" class="form-control custom-keys-list hidden" id="custom_keys_list"/>
                                    </div>
                                    <div class="col-sm-1 pr-0">
                                      <input type="checkbox" name="custom_keys_notify" title="Trigger email notification when updated" class="form-control"/>
                                    </div>""",
                output_text,
            )

    def test_view_forks(self):
        """Test the view_forks endpoint."""

        output = self.app.get("/foo/forks", follow_redirects=True)
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/forks", follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("This project has not been forked.", output_text)

    @patch.dict("pagure.config.config", {"CASE_SENSITIVE": True})
    def test_view_repo_case_sensitive(self):
        """Test the view_repo endpoint."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<p>This repo is brand new!</p>", output_text)

        output = self.app.get("/TEST")
        self.assertEqual(output.status_code, 404)

    def test_view_repo_more_button_absent_no_auth(self):
        """Test the view_repo endpoint and check if the "more" button is
        absent when not logged in."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn(
            '<span class="pull-xs-right"><a data-toggle="collapse" '
            'href="#moregiturls"',
            output_text,
        )
        self.assertIn("<p>This repo is brand new!</p>", output_text)
        self.assertIn("<title>Overview - test - Pagure</title>", output_text)
        self.assertIn(
            '<span class="d-none d-md-inline">Stats</span>', output_text
        )
        self.perfMaxWalks(0, 0)
        self.perfReset()

    def test_view_repo_more_button_present(self):
        """Test the view_repo endpoint and check if the "more" button is
        present when it should be."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        pingou = pagure.lib.query.get_user(self.session, "pingou")
        pagure.lib.query.add_sshkey_to_project_or_user(
            session=self.session,
            user=pingou,
            ssh_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q==",
            pushaccess=True,
            creator=pingou,
        )
        self.session.commit()
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<input class="form-control bg-white select-on-focus" type="text" '
                'value="ssh://git@localhost.localdomain/tickets/test.git" readonly>',
                output_text,
            )
            self.assertIn("<p>This repo is brand new!</p>", output_text)
            self.assertIn(
                "<title>Overview - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<span class="d-none d-md-inline">Stats</span>', output_text
            )
            self.perfMaxWalks(0, 0)
            self.perfReset()

    def test_view_repo_more_button_absent_no_access(self):
        """Test the view_repo endpoint and check if the "more" button is
        absent if the user doesn't have access to the project."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn(
                '<input class="form-control bg-white select-on-focus" type="text" '
                'value="ssh://git@localhost.localdomain/tickets/test.git" readonly>',
                output_text,
            )
            self.assertIn("<p>This repo is brand new!</p>", output_text)
            self.assertIn(
                "<title>Overview - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<span class="d-none d-md-inline">Stats</span>', output_text
            )
            self.perfMaxWalks(0, 0)
            self.perfReset()

    def test_view_repo_ssh_key_not_uploaded_no_ssh_url(self):
        """Test viewing repo when user hasn't uploaded SSH key yet
        and thus should see a message instead of url for SSH cloning."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        user = tests.FakeUser(username="pingou")

        with tests.user_set(self.app.application, user):
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "You need to upload SSH key to be able to clone over SSH",
                output_text,
            )

    def test_view_repo(self):
        """Test the view_repo endpoint."""

        output = self.app.get("/foo")
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get("/test")
        # No git repo associated
        self.assertEqual(output.status_code, 404)
        self.perfMaxWalks(0, 0)
        self.perfReset()

        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<p>This repo is brand new!</p>", output_text)
        self.assertIn("<title>Overview - test - Pagure</title>", output_text)
        self.assertIn(
            '<a class="nav-link" href="/test/stats">\n          '
            '<i class="fa fa-line-chart fa-fw text-muted"></i>\n          '
            '<span class="d-none d-md-inline">Stats</span>\n      </a>',
            output_text,
        )
        self.perfMaxWalks(0, 0)
        self.perfReset()

        output = self.app.get("/test/")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<p>This repo is brand new!</p>", output_text)
        self.assertIn("<title>Overview - test - Pagure</title>", output_text)
        self.perfMaxWalks(0, 0)
        self.perfReset()

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        tests.add_readme_git_repo(
            os.path.join(self.path, "repos", "test.git"), "README.txt"
        )
        tests.add_readme_git_repo(
            os.path.join(self.path, "repos", "test.git"), "README.dummy"
        )
        self.perfReset()

        # Authenticated, the Fork button appears
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<i class="fa fa-code-fork fa-fw"></i> Fork</button>',
                output_text,
            )
            self.assertFalse("<p>This repo is brand new!</p>" in output_text)
            self.assertNotIn("Forked from", output_text)
            self.assertNotIn("README.txt", output_text)
            self.assertNotIn("README.dummy", output_text)
            self.assertIn(
                "<title>Overview - test - Pagure</title>", output_text
            )
            self.perfMaxWalks(3, 8)  # Target: (1, 3)
            self.perfReset()

        # Non-authenticated, the Fork button does not appear
        output = self.app.get("/test")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn(
            '<i class="fa fa-code-fork"></i>Fork</button>', output_text
        )
        self.assertNotIn("<p>This repo is brand new!</p>", output_text)
        self.assertNotIn("Forked from", output_text)
        self.assertNotIn("README.txt", output_text)
        self.assertNotIn("README.dummy", output_text)
        self.assertIn("<title>Overview - test - Pagure</title>", output_text)
        self.perfMaxWalks(3, 8)  # Target: (1, 3)
        self.perfReset()

        # Turn that repo into a fork
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.parent_id = 2
        repo.is_fork = True
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get("/test")
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test.git")
        )
        tests.add_readme_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test.git")
        )

        # Authenticated and already have a fork, the View Fork button appears
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/fork/pingou/test")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn("<p>This repo is brand new!</p>", output_text)
            self.assertIn(
                "<title>Overview - test - Pagure</title>", output_text
            )
            self.assertIn("Forked from", output_text)
            self.assertNotIn(
                '<i class="fa fa-code-fork fa-fw"></i> Fork</button>',
                output_text,
            )
            self.assertIn(
                '<i class="fa fa-code-fork fa-fw"></i> View Upstream',
                output_text,
            )
            self.perfMaxWalks(1, 3)
            self.perfReset()

        # Authenticated, the Fork button appears
        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/fork/pingou/test")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn("<p>This repo is brand new!</p>", output_text)
            self.assertIn(
                "<title>Overview - test - Pagure</title>", output_text
            )
            self.assertIn("Forked from", output_text)
            self.assertNotIn(
                '<i class="fa fa-code-fork fa-fw"></i> View Upstream',
                output_text,
            )
            self.assertIn(
                '<i class="fa fa-code-fork fa-fw"></i> Fork</button>',
                output_text,
            )
            self.perfMaxWalks(1, 3)
            self.perfReset()

        # Non-authenticated, the Fork button does not appear
        output = self.app.get("/fork/pingou/test")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn("<p>This repo is brand new!</p>", output_text)
        self.assertIn("<title>Overview - test - Pagure</title>", output_text)
        self.assertIn("Forked from", output_text)
        self.assertNotIn(
            '<i class="fa fa-code-fork"></i> View Fork', output_text
        )
        self.assertNotIn(
            '<i class="fa fa-code-fork"></i>Fork</button>', output_text
        )
        self.perfMaxWalks(1, 3)
        self.perfReset()

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #3",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbmmm",
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git")
        )
        tests.add_readme_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git")
        )
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git"),
            ncommits=10,
        )

        output = self.app.get("/fork/pingou/test3")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn("<p>This repo is brand new!</p>", output_text)
        self.assertIn("<title>Overview - test3 - Pagure</title>", output_text)
        self.assertIn("Forked from", output_text)
        self.perfMaxWalks(3, 18)  # Ideal: (1, 3)
        self.perfReset()

    def test_view_repo_empty(self):
        """Test the view_repo endpoint on a repo w/o master branch."""

        tests.create_projects(self.session)
        # Create a git repo to play with
        gitrepo = os.path.join(self.path, "repos", "test.git")
        pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix="pagure-viewrepo-test")
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        # Edit the sources file again
        with open(os.path.join(newpath, "sources"), "w") as stream:
            stream.write("foo\n bar\nbaz\n boose")
        new_repo.index.add("sources")
        new_repo.index.write()

        # Commits the files added
        tree = new_repo.index.write_tree()
        author = pygit2.Signature("Alice Author", "alice@authors.tld")
        committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
        new_repo.create_commit(
            "refs/heads/feature",
            author,
            committer,
            "A commit on branch feature",
            tree,
            [],
        )
        refname = "refs/heads/feature"
        ori_remote = new_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        output = self.app.get("/test")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<p>This repo is brand new!</p>", output_text)
        self.assertNotIn("Forked from", output_text)
        self.assertIn("<title>Overview - test - Pagure</title>", output_text)
        self.assertEqual(output_text.count('<span class="commitid">'), 0)

        shutil.rmtree(newpath)

    '''
    def test_view_repo_branch(self):
        """ Test the view_repo_branch endpoint. """

        output = self.app.get('/foo/branch/master')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/branch/master')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'repos',
                                                'test.git'))
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))

        # Turn that repo into a fork
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        repo.parent_id = 2
        repo.is_fork = True
        self.session.add(repo)
        self.session.commit()

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test.git'))

        output = self.app.get('/fork/pingou/test/')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn('<p>This repo is brand new!</p>', output_text)
        self.assertIn('Forked from', output_text)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbnnn',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3/')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn('<p>This repo is brand new!</p>', output_text)
        self.assertIn('Forked from', output_text)
    '''

    def test_view_commits(self):
        """Test the view_commits endpoint."""
        output = self.app.get("/foo/commits")
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get("/test/commits")
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/commits")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<p>This repo is brand new!</p>", output_text)
        self.assertIn("<title>Commits - test - Pagure</title>", output_text)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))

        output = self.app.get("/test/commits")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn("<p>This repo is brand new!</p>", output_text)
        self.assertNotIn("Forked from", output_text)
        self.assertIn("<title>Commits - test - Pagure</title>", output_text)

        output = self.app.get("/test/commits/master")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn("<p>This repo is brand new!</p>", output_text)
        self.assertNotIn("Forked from", output_text)
        self.assertIn("<title>Commits - test - Pagure</title>", output_text)

        # Turn that repo into a fork
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.parent_id = 2
        repo.is_fork = True
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get("/test/commits")
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test.git")
        )
        tests.add_readme_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test.git")
        )

        output = self.app.get("/fork/pingou/test/commits?page=abc")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn("<p>This repo is brand new!</p>", output_text)
        self.assertIn("<title>Commits - test - Pagure</title>", output_text)
        self.assertIn("Forked from", output_text)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #3",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbooo",
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git")
        )
        tests.add_readme_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git")
        )
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git"),
            ncommits=10,
        )

        # list is empty
        output = self.app.get("/fork/pingou/test3/commits/fobranch")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<div class="list-group my-2">\n\n\n          </div>', output_text
        )
        self.assertIn(
            'Commits <span class="badge badge-secondary"> 0</span>',
            output_text,
        )

        output = self.app.get("/fork/pingou/test3/commits")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn("<p>This repo is brand new!</p>", output_text)
        self.assertIn("<title>Commits - test3 - Pagure</title>", output_text)
        self.assertIn("Forked from", output_text)

    def test_view_commits_from_tag(self):
        """Test the view_commits endpoint given a tag."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        first_commit = repo.revparse_single("HEAD")
        tagger = pygit2.Signature("Alice Doe", "adoe@example.com", 12347, 0)
        repo.create_tag(
            "0.0.1",
            first_commit.oid.hex,
            pygit2.GIT_OBJ_COMMIT,
            tagger,
            "Release 0.0.1",
        )

        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        latest_commit = repo.revparse_single("HEAD")

        output = self.app.get("/test/commits/0.0.1")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(first_commit.oid.hex, output_text)
        self.assertNotIn(latest_commit.oid.hex, output_text)
        self.assertIn("<title>Commits - test - Pagure</title>", output_text)
        self.assertEqual(output_text.count('<span id="commit-actions">'), 1)

    def test_view_commits_from_blob(self):
        """Test the view_commits endpoint given a blob."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        tests.add_content_to_git(os.path.join(self.path, "repos", "test.git"))

        # Retrieve the blob of the `sources` file in head
        repo_obj = pygit2.Repository(
            os.path.join(self.path, "repos", "test.git")
        )
        commit = repo_obj[repo_obj.head.target]
        content = get_file_in_tree(
            repo_obj, commit.tree, ["sources"], bail_on_tree=True
        )

        output = self.app.get("/test/commits/%s" % content.oid.hex)
        self.assertEqual(output.status_code, 404)
        output_text = output.get_data(as_text=True)
        self.assertIn("Invalid branch/identifier provided", output_text)

    def test_view_commit_from_tag(self):
        """Test the view_commit endpoint given a tag."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        first_commit = repo.revparse_single("HEAD")
        tagger = pygit2.Signature("Alice Doe", "adoe@example.com", 12347, 0)
        repo.create_tag(
            "0.0.1",
            first_commit.oid.hex,
            pygit2.GIT_OBJ_COMMIT,
            tagger,
            "Release 0.0.1",
        )

        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        tags = pagure.lib.git.get_git_tags_objects(project)
        tag_id = tags[0]["object"].oid
        commit_id = tags[0]["object"].peel(pygit2.Commit).hex

        output = self.app.get("/test/c/%s" % tag_id)
        self.assertEqual(output.status_code, 302)

        output = self.app.get("/test/c/%s" % tag_id, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(first_commit.oid.hex, output_text)
        self.assertIn(
            "<title>Commit - test - %s - Pagure</title>" % commit_id,
            output_text,
        )

    def test_compare_commits(self):
        """Test the compare_commits endpoint."""

        # First two commits comparison
        def compare_first_two(c1, c2):
            # View commits comparison
            output = self.app.get("/test/c/%s..%s" % (c2.oid.hex, c1.oid.hex))
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Diff from %s to %s - test\n - Pagure</title>"
                % (c2.oid.hex, c1.oid.hex),
                output_text,
            )
            self.assertIn(
                '        <span class="badge-light border border-secondary badge">%s</span>\n        ..\n        <span class="badge-light border border-secondary badge">%s</span>\n'
                % (c2.oid.hex, c1.oid.hex),
                output_text,
            )
            self.assertNotIn('id="show_hidden_commits"', output_text)
            self.assertIn(
                '<pre class="alert-danger"><code>- Row 0</code></pre>',
                output_text,
            )
            # View inverse commits comparison
            output = self.app.get("/test/c/%s..%s" % (c1.oid.hex, c2.oid.hex))
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Diff from %s to %s - test\n - Pagure</title>"
                % (c1.oid.hex, c2.oid.hex),
                output_text,
            )
            self.assertNotIn('id="show_hidden_commits"', output_text)
            self.assertIn(
                '        <span class="badge-light border border-secondary badge">%s</span>\n        ..\n        <span class="badge-light border border-secondary badge">%s</span>\n'
                % (c1.oid.hex, c2.oid.hex),
                output_text,
            )
            self.assertIn(
                '<pre class="alert-success"><code>+ Row 0</code></pre>',
                output_text,
            )

        def compare_all(c1, c3):
            # View commits comparison
            output = self.app.get("/test/c/%s..%s" % (c1.oid.hex, c3.oid.hex))
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Diff from %s to %s - test\n - Pagure</title>"
                % (c1.oid.hex, c3.oid.hex),
                output_text,
            )
            self.assertIn(
                '        <span class="badge-light border border-secondary badge">%s</span>\n        ..\n        <span class="badge-light border border-secondary badge">%s</span>\n'
                % (c1.oid.hex, c3.oid.hex),
                output_text,
            )
            self.assertIn(
                '<pre class="alert-success"><code>+ Row 0</code></pre>',
                output_text,
            )
            self.assertEqual(
                output_text.count(
                    '<pre class="alert-success"><code>+ Row 0</code></pre>'
                ),
                2,
            )
            self.assertIn('<a class="pointer">1 more commits...', output_text)
            self.assertIn(
                'title="View file as of 4829cfa">Šource</a>', output_text
            )
            self.assertIn(
                '<div class="btn btn-outline-success disabled opacity-100 border-0 font-weight-bold">\n'
                "    file added\n",
                output_text,
            )

            # View inverse commits comparison
            output = self.app.get("/test/c/%s..%s" % (c3.oid.hex, c1.oid.hex))
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Diff from %s to %s - test\n - Pagure</title>"
                % (c3.oid.hex, c1.oid.hex),
                output_text,
            )
            self.assertIn(
                '        <span class="badge-light border border-secondary badge">%s</span>\n        ..\n        <span class="badge-light border border-secondary badge">%s</span>\n'
                % (c3.oid.hex, c1.oid.hex),
                output_text,
            )
            self.assertIn(
                '<pre class="text-muted"><code>@@ -1,2 +1,1 @@</code></pre>',
                output_text,
            )
            self.assertIn(
                '<pre class="alert-danger"><code>- Row 0</code></pre>',
                output_text,
            )
            self.assertIn('<a class="pointer">1 more commits...', output_text)
            self.assertIn(
                'title="View file as of 0000000">Šource</a>', output_text
            )
            self.assertIn(
                '<div class="btn btn-outline-danger disabled opacity-100 border-0 font-weight-bold">\n'
                "    file removed\n",
                output_text,
            )

        def compare_with_symlink(c3, c4):
            # View comparison of commits with symlink
            # we only test that the patch itself renders correctly,
            # the rest of the logic is already tested in the other functions
            output = self.app.get("/test/c/%s..%s" % (c3.oid.hex, c4.oid.hex))
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            print(output_text)
            self.assertIn(
                "<title>Diff from %s to %s - test\n - Pagure</title>"
                % (c3.oid.hex, c4.oid.hex),
                output_text,
            )
            self.assertIn(
                '<pre class="alert-success"><code>+ Source </code></pre>',
                output_text,
            )

        output = self.app.get("/foo/bar")
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get("/test/bar")
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/bar")
        self.assertEqual(output.status_code, 404)

        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))

        # Add one commit to git repo
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "test.git"), ncommits=1
        )
        c1 = repo.revparse_single("HEAD")

        # Add another commit to git repo
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "test.git"), ncommits=1
        )
        c2 = repo.revparse_single("HEAD")

        # Add one more commit to git repo
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "test.git"),
            ncommits=1,
            filename="Šource",
        )
        c3 = repo.revparse_single("HEAD")

        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "test.git"),
            ncommits=1,
            filename="Source-sl",
            symlink_to="Source",
        )
        c4 = repo.revparse_single("HEAD")

        compare_first_two(c1, c2)
        compare_all(c1, c3)
        compare_with_symlink(c3, c4)

        user = tests.FakeUser()
        # Set user logged in
        with tests.user_set(self.app.application, user):
            compare_first_two(c1, c2)
            compare_all(c1, c3)
            compare_with_symlink(c3, c4)

    def test_view_file(self):
        """Test the view_file endpoint."""
        output = self.app.get("/foo/blob/foo/f/sources")
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get("/test/blob/foo/f/sources")
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/blob/foo/f/sources")
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        tests.add_binary_git_repo(
            os.path.join(self.path, "repos", "test.git"), "test.jpg"
        )
        tests.add_binary_git_repo(
            os.path.join(self.path, "repos", "test.git"), "test_binary"
        )

        output = self.app.get("/test/blob/master/foofile")
        self.assertEqual(output.status_code, 404)

        # View in a branch
        output = self.app.get("/test/blob/master/f/sources")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<pre class="syntaxhighlightblock">'
            '<code class="lang-plaintext">foo\n bar</code></pre>',
            output_text,
        )

        # Empty files should also be displayed
        tests.add_content_to_git(
            os.path.join(self.path, "repos", "test.git"),
            filename="emptyfile.md",
            content="",
        )
        output = self.app.get("/test/blob/master/f/emptyfile.md")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<a class="btn btn-secondary btn-sm" '
            'href="/test/raw/master/f/emptyfile.md" '
            'title="View as raw">Raw</a>',
            output_text,
        )
        self.assertIn(
            '<div class="m-2">\n' "        \n      </div>", output_text
        )

        # View what's supposed to be an image
        output = self.app.get("/test/blob/master/f/test.jpg")
        self.assertEqual(output.status_code, 200)
        self.assertNotIn(b"<html", output.data)

        # View by commit id
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")

        output = self.app.get("/test/blob/%s/f/test.jpg" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertNotIn(b"<html", output.data)

        # View by image name -- somehow we support this
        output = self.app.get("/test/blob/master/f/test.jpg")
        self.assertEqual(output.status_code, 200)
        self.assertNotIn(b"<html", output.data)

        # View binary file
        output = self.app.get("/test/blob/master/f/test_binary")
        self.assertEqual(output.status_code, 200)
        self.assertNotIn(b"<html", output.data)

        # View folder
        output = self.app.get("/test/blob/master/f/folder1")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<li class="active breadcrumb-item">\n            '
            '<span class="fa fa-folder" data-glyph="">\n            '
            "</span>&nbsp; folder1\n          </li>",
            output_text,
        )
        self.assertIn("<title>Tree - test - Pagure</title>", output_text)
        self.assertIn(
            '<a href="/test/blob/master/f/folder1/folder2">', output_text
        )

        # Verify the nav links correctly when viewing a nested folder/file.
        output = self.app.get("/test/blob/master/f/folder1/folder2/file")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<li class="breadcrumb-item"><a href="/test/blob/master/f/folder1/folder2">'
            '\n            <span class="fa fa-folder"></span>&nbsp; folder2</a>\n'
            "          </li>",
            output_text,
        )

        # View by image name -- with a non-existant file
        output = self.app.get("/test/blob/sources/f/testfoo.jpg")
        self.assertEqual(output.status_code, 404)
        output = self.app.get("/test/blob/master/f/folder1/testfoo.jpg")
        self.assertEqual(output.status_code, 404)

        # View file with a non-ascii name
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "test.git"),
            ncommits=1,
            filename="Šource",
        )
        output = self.app.get("/test/blob/master/f/Šource")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertEqual(
            output.headers["Content-Type"].lower(), "text/html; charset=utf-8"
        )
        self.assertIn("</span>&nbsp; Šource", output_text)
        self.assertIn(
            '<pre class="syntaxhighlightblock">'
            '<code class="lang-plaintext">Row 0\n</code></pre>',
            output_text,
        )

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #3",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbppp",
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git")
        )
        tests.add_readme_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git")
        )
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git"),
            ncommits=10,
        )

        # Verify the nav links correctly when viewing a file/folder in a fork.
        output = self.app.get(
            "/fork/pingou/test3/blob/master/f/folder1/folder2/file"
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<li class="breadcrumb-item">'
            '<a href="/fork/pingou/test3/blob/master/f/folder1/folder2">'
            '\n            <span class="fa fa-folder"></span>'
            "&nbsp; folder2</a>\n          </li>",
            output_text,
        )

        output = self.app.get("/fork/pingou/test3/blob/master/f/sources")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<pre class="syntaxhighlightblock">'
            '<code class="lang-plaintext">foo\n barRow 0\n'
            "Row 1\nRow 2\nRow 3\nRow 4\nRow 5\nRow 6\nRow 7\nRow 8\n"
            "Row 9\n</code></pre>",
            output_text,
        )

    @patch(
        "pagure.lib.encoding_utils.decode",
        MagicMock(side_effect=pagure.exceptions.PagureException),
    )
    def test_view_file_with_wrong_encoding(self):
        """Test the view_file endpoint."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        tests.add_binary_git_repo(
            os.path.join(self.path, "repos", "test.git"), "test.jpg"
        )
        tests.add_binary_git_repo(
            os.path.join(self.path, "repos", "test.git"), "test_binary"
        )

        # View file
        output = self.app.get("/test/blob/master/f/sources")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertEqual("foo\n bar", output_text)

    def test_view_raw_file(self):
        """Test the view_raw_file endpoint."""
        output = self.app.get("/foo/raw/foo/sources")
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get("/test/raw/foo/sources")
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/raw/foo/sources")
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))

        # View first commit
        output = self.app.get("/test/raw/master")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertEqual(
            output.headers["Content-Type"].lower(),
            "text/plain; charset=ascii",
        )
        self.assertIn(":Author: Pierre-Yves Chibon", output_text)

        # Add some more content to the repo
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        tests.add_binary_git_repo(
            os.path.join(self.path, "repos", "test.git"), "test.jpg"
        )
        tests.add_binary_git_repo(
            os.path.join(self.path, "repos", "test.git"), "test_binary"
        )

        output = self.app.get("/test/raw/master/f/foofile")
        self.assertEqual(output.status_code, 404)

        # View in a branch
        output = self.app.get("/test/raw/master/f/sources")
        self.assertEqual(
            output.headers["Content-Type"].lower(),
            "text/plain; charset=ascii",
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("foo\n bar", output_text)

        # View what's supposed to be an image
        output = self.app.get("/test/raw/master/f/test.jpg")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data()
        self.assertTrue(output_text.startswith(b"\x00\x00\x01\x00"))

        # View by commit id
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")

        output = self.app.get("/test/raw/%s/f/test.jpg" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data()
        self.assertTrue(output_text.startswith(b"\x00\x00\x01\x00"))

        # View by image name -- somehow we support this
        output = self.app.get("/test/raw/master/f/test.jpg")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data()
        self.assertTrue(output_text.startswith(b"\x00\x00\x01\x00"))

        # View binary file
        output = self.app.get("/test/raw/master/f/test_binary")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data()
        self.assertEqual(
            output.headers["Content-Type"].lower(), "application/octet-stream"
        )
        self.assertTrue(output_text.startswith(b"\x00\x00\x01\x00"))

        # View folder
        output = self.app.get("/test/raw/master/f/folder1")
        self.assertEqual(output.status_code, 404)

        # View by image name -- with a non-existant file
        output = self.app.get("/test/raw/master/f/testfoo.jpg")
        self.assertEqual(output.status_code, 404)
        output = self.app.get("/test/raw/master/f/folder1/testfoo.jpg")
        self.assertEqual(output.status_code, 404)

        output = self.app.get("/test/raw/master/f/")
        self.assertEqual(output.status_code, 404)

        output = self.app.get("/test/raw/master")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertEqual(
            output.headers["Content-Type"].lower(),
            "text/plain; charset=ascii",
        )
        self.assertTrue(
            output_text.startswith("diff --git a/test_binary b/test_binary\n")
        )

        output = self.app.get("/test/raw/%s" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertTrue(
            output_text.startswith("diff --git a/test_binary b/test_binary\n")
        )

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #3",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbqqq",
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git")
        )
        tests.add_readme_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git")
        )
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git"),
            ncommits=10,
        )

        output = self.app.get("/fork/pingou/test3/raw/master/f/sources")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertEqual(
            output.headers["Content-Type"].lower(),
            "text/plain; charset=ascii",
        )
        self.assertIn("foo\n bar", output_text)

    def test_view_commit(self):
        """Test the view_commit endpoint."""
        output = self.app.get("/foo/c/bar")
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get("/test/c/bar")
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/c/bar")
        self.assertEqual(output.status_code, 404)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")

        # View first commit
        output = self.app.get("/test/c/%s" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("#commit-overview-collapse", output_text)
        self.assertIn("Merged by Alice Author", output_text)
        self.assertIn("Committed by Cecil Committer", output_text)
        self.assertIn(
            '<div class="btn btn-outline-success disabled opacity-100 '
            'border-0 font-weight-bold">file added</div>',
            output_text,
        )

        # View first commit - with the old URL scheme disabled - default
        output = self.app.get(
            "/test/%s" % commit.oid.hex, follow_redirects=True
        )
        self.assertEqual(output.status_code, 404)
        output_text = output.get_data(as_text=True)
        self.assertIn("<p>Project not found</p>", output_text)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )

        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")
        # Add a symlink to test that it displays correctly
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "test.git"),
            ncommits=1,
            filename="sources-sl",
            symlink_to="sources",
        )
        commit_sl = repo.revparse_single("HEAD")

        # View another commit
        output = self.app.get("/test/c/%s" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("#commit-overview-collapse", output_text)
        self.assertIn("Authored by Alice Author", output_text)
        self.assertIn("Committed by Cecil Committer", output_text)

        # Make sure that diff containing symlink displays the header correctly
        output = self.app.get("/test/c/%s" % commit_sl.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        # check the link to the file
        self.assertIn(">sources-sl</a>", output_text)
        # check that the header contains "file added" and a +1 for one added line
        self.assertIn(">file added</span>", output_text)
        self.assertIn(">+1</span>", output_text)

        # View the commit when branch name is provided
        output = self.app.get("/test/c/%s?branch=master" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<a class=\n    "nav-link nowrap\n active"\n    '
            'href="/test/commits/master">\n    <i class="fa fa-list-alt '
            'text-muted fa-fw" data-glyph="spreadsheet"></i>&nbsp;Commits'
            "\n  </a>",
            output_text,
        )

        # View the commit when branch name is wrong, show the commit
        output = self.app.get("/test/c/%s?branch=abcxyz" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<a class=\n    "nav-link nowrap\n active"\n    '
            'href="/test/commits">\n    <i class="fa fa-list-alt '
            'text-muted fa-fw" data-glyph="spreadsheet"></i>&nbsp;Commits'
            "\n  </a>\n",
            output_text,
        )

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #3",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbkkk",
        )
        self.session.add(item)
        self.session.commit()
        forkedgit = os.path.join(
            self.path, "repos", "forks", "pingou", "test3.git"
        )

        tests.add_content_git_repo(forkedgit)
        tests.add_readme_git_repo(forkedgit)

        repo = pygit2.Repository(forkedgit)
        commit = repo.revparse_single("HEAD")

        # Commit does not exist in anothe repo :)
        output = self.app.get("/test/c/%s" % commit.oid.hex)
        self.assertEqual(output.status_code, 404)

        # View commit of fork
        output = self.app.get("/fork/pingou/test3/c/%s" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("#commit-overview-collapse", output_text)
        self.assertIn("Authored by Alice Author", output_text)
        self.assertIn("Committed by Cecil Committer", output_text)

        # Try the old URL scheme with a short hash
        output = self.app.get(
            "/fork/pingou/test3/%s" % commit.oid.hex[:10],
            follow_redirects=True,
        )
        self.assertEqual(output.status_code, 404)
        output_text = output.get_data(as_text=True)
        self.assertIn("<p>Project not found</p>", output_text)

        # View the commit of the fork when branch name is provided
        output = self.app.get(
            "/fork/pingou/test3/c/%s?branch=master" % commit.oid.hex
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<a class=\n    "nav-link nowrap\n active"\n    '
            'href="/fork/pingou/test3/commits/master">\n    '
            '<i class="fa fa-list-alt '
            'text-muted fa-fw" data-glyph="spreadsheet"></i>&nbsp;Commits'
            "\n  </a>\n",
            output_text,
        )

        # View the commit of the fork when branch name is wrong
        output = self.app.get(
            "/fork/pingou/test3/c/%s?branch=abcxyz" % commit.oid.hex
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<a class=\n    "nav-link nowrap\n active"\n    '
            'href="/fork/pingou/test3/commits">\n    <i class="fa fa-list-alt '
            'text-muted fa-fw" data-glyph="spreadsheet"></i>&nbsp;Commits'
            "\n  </a>",
            output_text,
        )

    def test_view_commit_with_full_link(self):
        """Test the view_commit endpoint when the commit message includes
        an url."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        folder = os.path.join(self.path, "repos", "test.git")

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(folder)
        tests.create_projects_git(folder, bare=True)
        # Add a commit with an url in the commit message
        tests.add_content_to_git(
            folder,
            branch="master",
            filename="sources",
            content="foo",
            message="Test commit message\n\n"
            "Fixes http://example.com/pagure/issue/2",
        )

        # Add a README to the git repo - First commit
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")

        # View first commit
        output = self.app.get("/test/c/%s" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("#commit-overview-collapse", output_text)
        self.assertIn(
            '<pre class="commit_message_body">\n    '
            "Test commit message\n    \n    "
            'Fixes <a href="http://example.com/pagure/issue/2" '
            'rel="nofollow">http://example.com/pagure/issue/2</a>\n        '
            "</pre>",
            output_text,
        )
        self.assertIn(
            '<div class="btn btn-outline-success disabled opacity-100 '
            'border-0 font-weight-bold">file added</div>',
            output_text,
        )

    def test_view_commit_with_short_link(self):
        """Test the view_commit endpoint when the commit message includes
        an url."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        folder = os.path.join(self.path, "repos", "test.git")

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(folder)
        tests.create_projects_git(folder, bare=True)
        # Add a commit with an url in the commit message
        tests.add_content_to_git(
            folder,
            branch="master",
            filename="sources",
            content="foo",
            message="Test commit message\n\nFixes #2",
        )

        # Add a README to the git repo - First commit
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")

        # View first commit
        output = self.app.get("/test/c/%s" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("#commit-overview-collapse", output_text)
        self.assertIn(
            '<pre class="commit_message_body">\n    '
            "Test commit message\n    \n    "
            "Fixes #2\n        </pre>",
            output_text,
        )
        self.assertIn(
            '<div class="btn btn-outline-success disabled opacity-100 '
            'border-0 font-weight-bold">file added</div>',
            output_text,
        )

    def test_view_commit_patch(self):
        """Test the view_commit_patch endpoint."""

        # No project registered in the DB
        output = self.app.get("/foo/c/bar.patch")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get("/test/c/bar.patch")
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/c/bar.patch")
        self.assertEqual(output.status_code, 404)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")

        # View first commit
        output = self.app.get("/test/c/%s.patch" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            r"""diff --git a/README.rst b/README.rst
new file mode 100644
index 0000000..fb7093d
--- /dev/null
+++ b/README.rst
@@ -0,0 +1,16 @@
+Pagure
+======
+
+:Author: Pierre-Yves Chibon <pingou@pingoured.fr>
+
+
+Pagure is a light-weight git-centered forge based on pygit2.
+
+Currently, Pagure offers a web-interface for git repositories, a ticket
+system and possibilities to create new projects, fork existing ones and
+create/merge pull-requests across or within projects.
+
+
+Homepage: https://github.com/pypingou/pagure
+
+Dev instance: http://209.132.184.222/ (/!\ May change unexpectedly, it's a dev instance ;-))
""",
            output_text,
        )
        self.assertIn("Subject: Add a README file", output_text)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )

        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")

        # View another commit
        output = self.app.get("/test/c/%s.patch" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            "Subject: Add some directory and a file for more testing",
            output_text,
        )
        self.assertIn(
            r"""diff --git a/folder1/folder2/file b/folder1/folder2/file
new file mode 100644
index 0000000..11980b1
--- /dev/null
+++ b/folder1/folder2/file
@@ -0,0 +1,3 @@
+foo
+ bar
+baz
\ No newline at end of file
""",
            output_text,
        )

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #3",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbblll",
        )
        self.session.add(item)
        self.session.commit()
        forkedgit = os.path.join(
            self.path, "repos", "forks", "pingou", "test3.git"
        )

        tests.add_content_git_repo(forkedgit)
        tests.add_readme_git_repo(forkedgit)

        repo = pygit2.Repository(forkedgit)
        commit = repo.revparse_single("HEAD")

        # Commit does not exist in anothe repo :)
        output = self.app.get("/test/c/%s.patch" % commit.oid.hex)
        self.assertEqual(output.status_code, 404)

        # View commit of fork
        output = self.app.get("/fork/pingou/test3/c/%s.patch" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            r"""diff --git a/README.rst b/README.rst
new file mode 100644
index 0000000..fb7093d
--- /dev/null
+++ b/README.rst
@@ -0,0 +1,16 @@
+Pagure
+======
+
+:Author: Pierre-Yves Chibon <pingou@pingoured.fr>
+
+
+Pagure is a light-weight git-centered forge based on pygit2.
+
+Currently, Pagure offers a web-interface for git repositories, a ticket
+system and possibilities to create new projects, fork existing ones and
+create/merge pull-requests across or within projects.
+
+
+Homepage: https://github.com/pypingou/pagure
+
+Dev instance: http://209.132.184.222/ (/!\ May change unexpectedly, it's a dev instance ;-))
""",
            output_text,
        )

    def test_view_commit_diff(self):
        """Test the view_commit_diff endpoint."""

        # No project registered in the DB
        output = self.app.get("/foo/c/bar.diff")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get("/test/c/bar.diff")
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/c/bar.diff")
        self.assertEqual(output.status_code, 404)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")

        # View first commit
        output = self.app.get("/test/c/%s.diff" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertEqual(
            r"""diff --git a/README.rst b/README.rst
new file mode 100644
index 0000000..fb7093d
--- /dev/null
+++ b/README.rst
@@ -0,0 +1,16 @@
+Pagure
+======
+
+:Author: Pierre-Yves Chibon <pingou@pingoured.fr>
+
+
+Pagure is a light-weight git-centered forge based on pygit2.
+
+Currently, Pagure offers a web-interface for git repositories, a ticket
+system and possibilities to create new projects, fork existing ones and
+create/merge pull-requests across or within projects.
+
+
+Homepage: https://github.com/pypingou/pagure
+
+Dev instance: http://209.132.184.222/ (/!\ May change unexpectedly, it's a dev instance ;-))
""",
            output_text,
        )

    def test_view_tree(self):
        """Test the view_tree endpoint."""
        output = self.app.get("/foo/tree/")
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get("/test/tree/")
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/tree/")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            """<ol class="breadcrumb p-0 bg-transparent mb-0">
          <li class="breadcrumb-item">
            <a href="/test/tree">
              <span class="fa fa-random">
              </span>&nbsp; None
            </a>
          </li>
        </ol>""",
            output_text,
        )
        self.assertIn("No content found in this repository", output_text)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        commit = repo.revparse_single("HEAD")

        # View first commit
        output = self.app.get("/test/tree/%s" % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Tree - test - Pagure</title>", output_text)
        self.assertIn("README.rst", output_text)
        self.assertFalse("No content found in this repository" in output_text)

        # View tree, no identifier:
        output = self.app.get("/test/tree/")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Tree - test - Pagure</title>", output_text)
        self.assertIn("README.rst", output_text)
        self.assertNotIn("No content found in this repository", output_text)
        self.assertNotIn(
            "&#39;None&#39; not found in the git repository, going back to: "
            "master",
            output_text,
        )

        # View tree, invalid identifier:
        output = self.app.get("/test/tree/invalid")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Tree - test - Pagure</title>", output_text)
        self.assertIn("README.rst", output_text)
        self.assertNotIn("No content found in this repository", output_text)
        self.assertIn(
            "&#39;invalid&#39; not found in the git repository, going back "
            "to: master",
            output_text,
        )

        # View tree by branch
        output = self.app.get("/test/tree/master")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Tree - test - Pagure</title>", output_text)
        self.assertIn("README.rst", output_text)
        self.assertNotIn("No content found in this repository", output_text)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #3",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbfff",
        )
        self.session.add(item)
        self.session.commit()
        forkedgit = os.path.join(
            self.path, "repos", "forks", "pingou", "test3.git"
        )

        tests.add_content_git_repo(forkedgit)

        output = self.app.get("/fork/pingou/test3/tree/")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Tree - test3 - Pagure</title>", output_text)
        self.assertIn(
            '<a href="/fork/pingou/test3/blob/master/f/folder1">', output_text
        )
        self.assertIn(
            '<a href="/fork/pingou/test3/blob/master/f/sources">', output_text
        )
        self.assertNotIn("No content found in this repository", output_text)

        output = self.app.get(
            "/fork/pingou/test3/blob/master/f/folder1/folder2"
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<a href="/fork/pingou/test3/blob/master/'
            'f/folder1/folder2/file%C5%A0">',
            output_text,
        )

    @patch.dict("pagure.config.config", {"ENABLE_DEL_PROJECTS": False})
    @patch("pagure.lib.notify.send_email")
    @patch("pagure.decorators.admin_session_timedout")
    def test_delete_repo_when_turned_off(self, ast, send_email):
        """Test the delete_repo endpoint when deletion of a repo is
        turned off in the pagure instance"""
        ast.return_value = False
        send_email.return_value = True

        # No Git repo
        output = self.app.post("/foo/delete")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            tests.create_projects(self.session)
            tests.create_projects_git(os.path.join(self.path, "repos"))

            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        # User not logged in
        output = self.app.post("/test/delete")
        self.assertEqual(output.status_code, 302)

        with tests.user_set(self.app.application, user):
            # Only git repo
            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Only git and doc repo
            tests.create_projects_git(os.path.join(self.path, "repos"))
            tests.create_projects_git(os.path.join(self.path, "docs"))
            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Create all the git repos
            tests.create_projects_git(os.path.join(self.path, "repos"))
            tests.create_projects_git(os.path.join(self.path, "docs"))
            tests.create_projects_git(
                os.path.join(self.path, "tickets"), bare=True
            )
            tests.create_projects_git(
                os.path.join(self.path, "requests"), bare=True
            )

            # Check repo was created
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="btn btn-outline-secondary disabled opacity-100 '
                'border-0 ml-auto font-weight-bold">3 Projects</span>',
                output_text,
            )
            self.assertNotIn(
                '<span class="d-none d-md-inline">Forks&nbsp;</span>',
                output_text,
            )

            # add issues
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            msg = pagure.lib.query.new_issue(
                session=self.session,
                repo=repo,
                title="Test issue",
                content="We should work on this",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(msg.title, "Test issue")

            msg = pagure.lib.query.new_issue(
                session=self.session,
                repo=repo,
                title="Test issue #2",
                content="We should work on this, really",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(msg.title, "Test issue #2")

            # Add a comment to an issue
            issue = pagure.lib.query.search_issues(
                self.session, repo, issueid=1
            )
            msg = pagure.lib.query.add_issue_comment(
                session=self.session,
                issue=issue,
                comment="Hey look a comment!",
                user="foo",
            )
            self.session.commit()
            self.assertEqual(msg, "Comment added")

            # add pull-requests
            req = pagure.lib.query.new_pull_request(
                session=self.session,
                repo_from=repo,
                branch_from="feature",
                repo_to=repo,
                branch_to="master",
                title="test pull-request",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(req.id, 3)
            self.assertEqual(req.title, "test pull-request")

            req = pagure.lib.query.new_pull_request(
                session=self.session,
                repo_from=repo,
                branch_from="feature2",
                repo_to=repo,
                branch_to="master",
                title="test pull-request",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(req.id, 4)
            self.assertEqual(req.title, "test pull-request")

            # Add comment on a pull-request
            request = pagure.lib.query.search_pull_requests(
                self.session, requestid=3
            )

            msg = pagure.lib.query.add_pull_request_comment(
                session=self.session,
                request=request,
                commit="commithash",
                tree_id=None,
                filename="file",
                row=None,
                comment="This is awesome, I got to remember it!",
                user="foo",
            )
            self.assertEqual(msg, "Comment added")

            # Check before deleting the project
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="btn btn-outline-secondary disabled opacity-100 '
                'border-0 ml-auto font-weight-bold">3 Projects</span>',
                output_text,
            )
            self.assertNotIn(
                '<span class="d-none d-md-inline">Forks&nbsp;</span>',
                output_text,
            )

            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertNotEqual(repo, None)
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test2"
            )
            self.assertNotEqual(repo, None)

            # Add a fork of a fork
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name="test3",
                description="test project #3",
                is_fork=True,
                parent_id=2,
                hook_token="aaabbbjjj",
            )
            self.session.add(item)
            self.session.commit()
            tests.add_content_git_repo(
                os.path.join(
                    self.path, "repos", "forks", "pingou", "test3.git"
                )
            )
            tests.add_content_git_repo(
                os.path.join(self.path, "docs", "pingou", "test3.git")
            )
            tests.add_content_git_repo(
                os.path.join(self.path, "tickets", "pingou", "test3.git")
            )

            # Check before deleting the fork
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="btn btn-outline-secondary disabled opacity-100 '
                'border-0 ml-auto font-weight-bold">3 Projects</span>',
                output_text,
            )
            self.assertIn(
                """<span>
              <i class="fa fa-fw text-muted fa-code-fork"></i>
              <span class="d-none d-md-inline">Forks&nbsp;</span>
            </span>
            <div class="ml-auto">
              <span class="badge badge-secondary">
                1
              </span>
            </div>""",
                output_text,
            )

            output = self.app.post(
                "/fork/pingou/test3/delete", follow_redirects=True
            )
            self.assertEqual(output.status_code, 404)

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch("pagure.decorators.admin_session_timedout")
    def test_delete_repo(self, ast):
        """Test the delete_repo endpoint."""
        ast.return_value = False

        # No Git repo
        output = self.app.post("/foo/delete")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            tests.create_projects(self.session)
            tests.create_projects_git(os.path.join(self.path, "repos"))

            # No project registered in the DB (no git repo)
            output = self.app.post("/foo/delete")
            self.assertEqual(output.status_code, 404)

            # User not allowed
            output = self.app.post("/test/delete")
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.post("/test/delete")
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            tests.create_projects_git(os.path.join(self.path, "repos"))

            ast.return_value = True
            output = self.app.post("/test/delete")
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  2
                </span>
              </div>""",
                output_text,
            )
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""",
                output_text,
            )

            # Only git repo
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name="test",
                description="test project #1",
                hook_token="aaabbbggg",
            )
            self.session.add(item)
            self.session.commit()
            tests.create_projects_git(os.path.join(self.path, "repos"))

            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  2
                </span>
              </div>""",
                output_text,
            )
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""",
                output_text,
            )

            # Only git and doc repo
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name="test",
                description="test project #1",
                hook_token="aaabbbhhh",
            )
            self.session.add(item)
            self.session.commit()
            tests.create_projects_git(os.path.join(self.path, "repos"))
            tests.create_projects_git(os.path.join(self.path, "docs"))
            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  2
                </span>
              </div>""",
                output_text,
            )
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""",
                output_text,
            )

            # All repo there
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name="test",
                description="test project #1",
                hook_token="aaabbbiii",
            )
            self.session.add(item)
            self.session.commit()

            # Create all the git repos
            tests.create_projects_git(os.path.join(self.path, "repos"))
            tests.create_projects_git(os.path.join(self.path, "docs"))
            tests.create_projects_git(
                os.path.join(self.path, "tickets"), bare=True
            )
            tests.create_projects_git(
                os.path.join(self.path, "requests"), bare=True
            )

            # Check repo was created
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
              <i class="fa fa-calendar-o fa-rotate-270 fa-fw text-muted"></i>
              <span class="d-none d-md-inline">Projects&nbsp;</span>
            </span>
            <div class="ml-auto">
              <span class="badge badge-secondary">
                3
              </span>
            </div>""",
                output_text,
            )
            self.assertNotIn(
                """<span class="d-none d-md-inline">Forks&nbsp;</span>""",
                output_text,
            )

            # add issues
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            msg = pagure.lib.query.new_issue(
                session=self.session,
                repo=repo,
                title="Test issue",
                content="We should work on this",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(msg.title, "Test issue")

            msg = pagure.lib.query.new_issue(
                session=self.session,
                repo=repo,
                title="Test issue #2",
                content="We should work on this, really",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(msg.title, "Test issue #2")

            # Add a comment to an issue
            issue = pagure.lib.query.search_issues(
                self.session, repo, issueid=1
            )
            msg = pagure.lib.query.add_issue_comment(
                session=self.session,
                issue=issue,
                comment="Hey look a comment!",
                user="foo",
            )
            self.session.commit()
            self.assertEqual(msg, "Comment added")

            # add pull-requests
            req = pagure.lib.query.new_pull_request(
                session=self.session,
                repo_from=repo,
                branch_from="feature",
                repo_to=repo,
                branch_to="master",
                title="test pull-request",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(req.id, 3)
            self.assertEqual(req.title, "test pull-request")

            req = pagure.lib.query.new_pull_request(
                session=self.session,
                repo_from=repo,
                branch_from="feature2",
                repo_to=repo,
                branch_to="master",
                title="test pull-request",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(req.id, 4)
            self.assertEqual(req.title, "test pull-request")

            # Add comment on a pull-request
            request = pagure.lib.query.search_pull_requests(
                self.session, requestid=3
            )

            msg = pagure.lib.query.add_pull_request_comment(
                session=self.session,
                request=request,
                commit="commithash",
                tree_id=None,
                filename="file",
                row=None,
                comment="This is awesome, I got to remember it!",
                user="foo",
            )
            self.assertEqual(msg, "Comment added")

            # Check before deleting the project
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
              <i class="fa fa-calendar-o fa-rotate-270 fa-fw text-muted"></i>
              <span class="d-none d-md-inline">Projects&nbsp;</span>
            </span>
            <div class="ml-auto">
              <span class="badge badge-secondary">
                3
              </span>
            </div>""",
                output_text,
            )
            self.assertNotIn(
                """<span class="d-none d-md-inline">Forks&nbsp;</span>""",
                output_text,
            )

            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  2
                </span>
              </div>""",
                output_text,
            )
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""",
                output_text,
            )

            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(repo, None)
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test2"
            )
            self.assertNotEqual(repo, None)

            # Add a fork of a fork
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name="test3",
                description="test project #3",
                is_fork=True,
                parent_id=2,
                hook_token="aaabbbjjj",
            )
            self.session.add(item)
            self.session.commit()
            tests.add_content_git_repo(
                os.path.join(
                    self.path, "repos", "forks", "pingou", "test3.git"
                )
            )
            tests.add_content_git_repo(
                os.path.join(self.path, "docs", "pingou", "test3.git")
            )
            tests.add_content_git_repo(
                os.path.join(self.path, "tickets", "pingou", "test3.git")
            )

            # Check before deleting the fork
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
              <i class="fa fa-calendar-o fa-rotate-270 fa-fw text-muted"></i>
              <span class="d-none d-md-inline">Projects&nbsp;</span>
            </span>
            <div class="ml-auto">
              <span class="badge badge-secondary">
                2
              </span>
            </div>""",
                output_text,
            )
            self.assertIn(
                """<span>
              <i class="fa fa-fw text-muted fa-code-fork"></i>
              <span class="d-none d-md-inline">Forks&nbsp;</span>
            </span>
            <div class="ml-auto">
              <span class="badge badge-secondary">
                1
              </span>
            </div>""",
                output_text,
            )

            output = self.app.post(
                "/fork/pingou/test3/delete", follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  2
                </span>
              </div>""",
                output_text,
            )
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""",
                output_text,
            )

    @patch.dict("pagure.config.config", {"TICKETS_FOLDER": None})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_delete_repo_no_ticket(self):
        """Test the delete_repo endpoint when tickets aren't enabled in
        this pagure instance."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            # Check before deleting the project
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
              <i class="fa fa-calendar-o fa-rotate-270 fa-fw text-muted"></i>
              <span class="d-none d-md-inline">Projects&nbsp;</span>
            </span>
            <div class="ml-auto">
              <span class="badge badge-secondary">
                3
              </span>
            </div>""",
                output_text,
            )
            self.assertNotIn(
                """<span class="d-none d-md-inline">Forks&nbsp;</span>""",
                output_text,
            )

            # Delete the project
            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)

            # Check deletion worked
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  2
                </span>
              </div>""",
                output_text,
            )
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""",
                output_text,
            )

    @patch("pagure.lib.notify.send_email")
    @patch("pagure.decorators.admin_session_timedout")
    def test_delete_repo_with_users(self, ast, send_email):
        """Test the delete_repo endpoint."""
        ast.return_value = False
        send_email.return_value = True

        user = tests.FakeUser()
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            # Create new project
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name="test",
                description="test project #1",
                hook_token="aaabbbiii",
            )
            self.session.add(item)
            self.session.commit()

            # Create all the git repos
            tests.create_projects_git(os.path.join(self.path, "repos"))
            tests.create_projects_git(
                os.path.join(self.path, "docs"), bare=True
            )
            tests.create_projects_git(
                os.path.join(self.path, "tickets"), bare=True
            )
            tests.create_projects_git(
                os.path.join(self.path, "requests"), bare=True
            )

            # Check repo was created
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="btn btn-outline-secondary disabled opacity-100 '
                'border-0 ml-auto font-weight-bold">1 Projects</span>',
                output_text,
            )
            self.assertNotIn(
                '<span class="d-none d-md-inline">Forks&nbsp;</span>',
                output_text,
            )

            # add user
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            msg = pagure.lib.query.add_user_to_project(
                session=self.session,
                project=repo,
                new_user="foo",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(msg, "User added")

            # Check before deleting the project
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="btn btn-outline-secondary disabled opacity-100 '
                'border-0 ml-auto font-weight-bold">1 Projects</span>',
                output_text,
            )
            self.assertNotIn(
                '<span class="d-none d-md-inline">Forks&nbsp;</span>',
                output_text,
            )
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertNotEqual(repo, None)
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test2"
            )
            self.assertEqual(repo, None)

            # Delete the project
            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""",
                output_text,
            )
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""",
                output_text,
            )

            # Check after
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(repo, None)
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test2"
            )
            self.assertEqual(repo, None)

    @patch("pagure.lib.notify.send_email")
    @patch("pagure.decorators.admin_session_timedout")
    def test_delete_repo_with_group(self, ast, send_email):
        """Test the delete_repo endpoint."""
        ast.return_value = False
        send_email.return_value = True

        user = tests.FakeUser()
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            # Create new project
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name="test",
                description="test project #1",
                hook_token="aaabbbiii",
            )
            self.session.add(item)
            self.session.commit()

            # Create all the git repos
            tests.create_projects_git(os.path.join(self.path, "repos"))
            tests.create_projects_git(
                os.path.join(self.path, "docs"), bare=True
            )
            tests.create_projects_git(
                os.path.join(self.path, "tickets"), bare=True
            )
            tests.create_projects_git(
                os.path.join(self.path, "requests"), bare=True
            )

            # Check repo was created
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="btn btn-outline-secondary disabled opacity-100 '
                'border-0 ml-auto font-weight-bold">1 Projects</span>',
                output_text,
            )
            self.assertNotIn(
                '<span class="d-none d-md-inline">Forks&nbsp;</span>',
                output_text,
            )

            # Create group
            msg = pagure.lib.query.add_group(
                self.session,
                group_name="foo",
                display_name="foo group",
                description=None,
                group_type="bar",
                user="pingou",
                is_admin=False,
                blacklist=[],
            )
            self.session.commit()
            self.assertEqual(msg, "User `pingou` added to the group `foo`.")

            # Add group to the project
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            msg = pagure.lib.query.add_group_to_project(
                session=self.session,
                project=repo,
                new_group="foo",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(msg, "Group added")

            # check if group where we expect it
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(len(repo.projects_groups), 1)

            # Check before deleting the project
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="btn btn-outline-secondary disabled opacity-100 '
                'border-0 ml-auto font-weight-bold">1 Projects</span>',
                output_text,
            )
            self.assertNotIn(
                '<span class="d-none d-md-inline">Forks&nbsp;</span>',
                output_text,
            )
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertNotEqual(repo, None)

            # Delete the project
            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""",
                output_text,
            )
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""",
                output_text,
            )

            # Check after
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(repo, None)

    @patch("pagure.lib.notify.send_email")
    @patch("pagure.decorators.admin_session_timedout")
    def test_delete_repo_with_coloredtag(self, ast, send_email):
        """Test the delete_repo endpoint."""
        ast.return_value = False
        send_email.return_value = True

        user = tests.FakeUser()
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            # Create new project
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name="test",
                description="test project #1",
                hook_token="aaabbbiii",
            )
            self.session.add(item)
            self.session.commit()

            # Create all the git repos
            tests.create_projects_git(os.path.join(self.path, "repos"))
            tests.create_projects_git(
                os.path.join(self.path, "docs"), bare=True
            )
            tests.create_projects_git(
                os.path.join(self.path, "tickets"), bare=True
            )
            tests.create_projects_git(
                os.path.join(self.path, "requests"), bare=True
            )

            # Check repo was created
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="btn btn-outline-secondary disabled opacity-100 '
                'border-0 ml-auto font-weight-bold">1 Projects</span>',
                output_text,
            )
            self.assertNotIn(
                '<span class="d-none d-md-inline">Forks&nbsp;</span>',
                output_text,
            )

            # Create the issue
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            msg = pagure.lib.query.new_issue(
                session=self.session,
                repo=repo,
                title="Test issue",
                content="We should work on this",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(msg.title, "Test issue")

            # Add a tag to the issue
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            issue = pagure.lib.query.search_issues(
                self.session, repo, issueid=1
            )
            msg = pagure.lib.query.add_tag_obj(
                session=self.session, obj=issue, tags="tag1", user="pingou"
            )
            self.session.commit()
            self.assertEqual(msg, "Issue tagged with: tag1")

            # Check before deleting the project
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="btn btn-outline-secondary disabled opacity-100 '
                'border-0 ml-auto font-weight-bold">1 Projects</span>',
                output_text,
            )
            self.assertNotIn(
                '<span class="d-none d-md-inline">Forks&nbsp;</span>',
                output_text,
            )
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertNotEqual(repo, None)
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test2"
            )
            self.assertEqual(repo, None)

            # Delete the project
            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""",
                output_text,
            )
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""",
                output_text,
            )

            # Check after
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(repo, None)
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test2"
            )
            self.assertEqual(repo, None)

    @patch("pagure.decorators.admin_session_timedout")
    def test_new_repo_hook_token(self, ast):
        """Test the new_repo_hook_token endpoint."""
        ast.return_value = False
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.hook_token, "aaabbbccc")

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            pagure.config.config["WEBHOOK"] = True
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            output = self.app.post("/foo/hook_token")
            self.assertEqual(output.status_code, 404)

            output = self.app.post("/test/hook_token")
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.post("/test/hook_token")
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

            pagure.config.config["WEBHOOK"] = False

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.hook_token, "aaabbbccc")

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            pagure.config.config["WEBHOOK"] = True
            output = self.app.post("/test/hook_token")
            self.assertEqual(output.status_code, 400)

            data = {"csrf_token": csrf_token}

            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(repo.hook_token, "aaabbbccc")

            output = self.app.post(
                "/test/hook_token", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("New hook token generated", output_text)
            pagure.config.config["WEBHOOK"] = False

        self.session.commit()
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertNotEqual(repo.hook_token, "aaabbbccc")

    def test_view_tags(self):
        """Test the view_tags endpoint."""
        output = self.app.get("/foo/releases")
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get("/test/releases")
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/releases")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("This project has not been tagged.", output_text)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        first_commit = repo.revparse_single("HEAD")
        tagger = pygit2.Signature("Alice Doe", "adoe@example.com", 12347, 0)
        repo.create_tag(
            "0.0.1",
            first_commit.oid.hex,
            pygit2.GIT_OBJ_COMMIT,
            tagger,
            "Release 0.0.1",
        )

        output = self.app.get("/test/releases")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("0.0.1", output_text)
        self.assertIn('<section class="tag_list">', output_text)
        self.assertEqual(
            output_text.count(
                '<i class="fa fa-calendar-o fa-rotate-270 text-muted"></i>'
            ),
            1,
        )

    def test_edit_file_no_signed_off(self):
        """Test the edit_file endpoint when signed-off isn't enforced."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "test.git")
            )

            output = self.app.get("/test/edit/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<li><a href="/test/tree/master"><span class="fa fa-random">'
                '</span>&nbsp; master</a></li><li class="active">'
                '<span class="fa fa-file"></span>&nbsp; sources</li>',
                output_text,
            )
            self.assertIn(
                '<textarea id="textareaCode" name="content">foo\n bar</textarea>',
                output_text,
            )
            self.assertIn(
                '<textarea rows="5" class="form-control" type="text" '
                'id="commit_message"\n            name="commit_message" '
                'placeholder="An optional description of the change">'
                "</textarea>",
                output_text,
            )

    def test_edit_file_signed_off(self):
        """Test the edit_file endpoint when signed-off is enforced."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        settings = repo.settings
        settings["Enforce_signed-off_commits_in_pull-request"] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "test.git")
            )

            output = self.app.get("/test/edit/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<li><a href="/test/tree/master"><span class="fa fa-random">'
                '</span>&nbsp; master</a></li><li class="active">'
                '<span class="fa fa-file"></span>&nbsp; sources</li>',
                output_text,
            )
            self.assertIn(
                '<textarea id="textareaCode" name="content">foo\n bar</textarea>',
                output_text,
            )
            self.assertIn(
                '<textarea rows="5" class="form-control" type="text" '
                'id="commit_message"\n            name="commit_message" '
                'placeholder="An optional description of the change">'
                "Signed-off-by: pingou <bar@pingou.com></textarea>",
                output_text,
            )

    def test_edit_file(self):
        """Test the edit_file endpoint."""

        # No Git repo
        output = self.app.get("/foo/edit/foo/f/sources")
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))
        tests.add_binary_git_repo(
            os.path.join(self.path, "repos", "test.git"), "test.jpg"
        )
        tests.add_binary_git_repo(
            os.path.join(self.path, "repos", "test.git"), "test_binary"
        )

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            # No project registered in the DB
            output = self.app.get("/foo/edit/foo/f/sources")
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(
                os.path.join(self.path, "repos"), bare=True
            )

            # No a repo admin
            output = self.app.get("/test/edit/master/f/sources")
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.get("/test/edit/foo/f/sources")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            output = self.app.get("/test/edit/master/foofile")
            self.assertEqual(output.status_code, 404)

            # Edit page
            output = self.app.get("/test/edit/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<li><a href="/test/tree/master"><span class="fa fa-random">'
                '</span>&nbsp; master</a></li><li class="active">'
                '<span class="fa fa-file"></span>&nbsp; sources</li>',
                output_text,
            )
            self.assertIn(
                '<textarea id="textareaCode" name="content">foo\n bar</textarea>',
                output_text,
            )

            # Verify the nav links correctly when editing a file.
            output = self.app.get("/test/blob/master/f/folder1/folder2/file")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<li class="breadcrumb-item"><a href="/test/blob/master/f/folder1/folder2">'
                '\n            <span class="fa fa-folder"></span>&nbsp; folder2</a>\n'
                "          </li>",
                output_text,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            # View what's supposed to be an image
            output = self.app.get("/test/edit/master/f/test.jpg")
            self.assertEqual(output.status_code, 400)
            output_text = output.get_data(as_text=True)
            self.assertIn("<p>Cannot edit binary files</p>", output_text)

            # Check file before the commit:
            output = self.app.get("/test/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar")

            # No CSRF Token
            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
            }
            output = self.app.post("/test/edit/master/f/sources", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<title>Edit - test - Pagure</title>", output_text)

            # Check that nothing changed
            output = self.app.get("/test/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar")

            # Missing email
            data["csrf_token"] = csrf_token
            output = self.app.post("/test/edit/master/f/sources", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<title>Edit - test - Pagure</title>", output_text)

            # Invalid email
            data["email"] = "pingou@fp.o"
            output = self.app.post("/test/edit/master/f/sources", data=data)
            output_text = output.get_data(as_text=True)
            self.assertIn("<title>Edit - test - Pagure</title>", output_text)

            # Works
            data["email"] = "bar@pingou.com"
            data["branch"] = "master"
            output = self.app.post(
                "/test/edit/master/f/sources", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Commits - test - Pagure</title>", output_text
            )
            self.assertIn("test commit", output_text)

            # Check file after the commit:
            output = self.app.get("/test/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar\n  baz")

            # Add a fork of a fork
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name="test3",
                description="test project #3",
                is_fork=True,
                parent_id=1,
                hook_token="aaabbbppp",
            )
            self.session.add(item)
            self.session.commit()

            tests.add_content_git_repo(
                os.path.join(
                    self.path, "repos", "forks", "pingou", "test3.git"
                )
            )
            tests.add_readme_git_repo(
                os.path.join(
                    self.path, "repos", "forks", "pingou", "test3.git"
                )
            )
            tests.add_commit_git_repo(
                os.path.join(
                    self.path, "repos", "forks", "pingou", "test3.git"
                ),
                ncommits=10,
            )

            # Verify the nav links correctly when editing a file in a fork.
            output = self.app.get(
                "/fork/pingou/test3/edit/master/f/folder1/folder2/file"
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<li><a\n      href="/fork/pingou/test3/blob/master/f/folder1/folder2"\n'
                '        ><span class="fa fa-folder"></span>&nbsp; folder2</a>\n'
                "        </li>",
                output_text,
            )

            output = self.app.get("/fork/pingou/test3/edit/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<li><a href="/fork/pingou/test3/tree/master">'
                '<span class="fa fa-random">'
                '</span>&nbsp; master</a></li><li class="active">'
                '<span class="fa fa-file"></span>&nbsp; sources</li>',
                output_text,
            )
            self.assertIn(
                '<textarea id="textareaCode" name="content">foo\n barRow 0\n',
                output_text,
            )

            # Empty the file - no `content` provided
            data = {
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "csrf_token": csrf_token,
                "email": "bar@pingou.com",
                "branch": "master",
            }
            output = self.app.post(
                "/test/edit/master/f/sources", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Commits - test - Pagure</title>", output_text
            )
            self.assertIn("test commit", output_text)

            # Check file after the commit:
            output = self.app.get("/test/raw/master/f/sources")
            self.assertEqual(output.status_code, 404)
            output_text = output.get_data(as_text=True)
            self.assertIn("<p>No content found</p>", output_text)

    def test_edit_file_default_email(self):
        """Test the default email shown by the edit_file endpoint."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )
        tests.add_readme_git_repo(os.path.join(self.path, "repos", "test.git"))

        user = pagure.lib.query.search_user(self.session, username="pingou")
        self.assertEqual(len(user.emails), 2)
        self.assertEqual(user.default_email, "bar@pingou.com")

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):

            # Edit page
            output = self.app.get("/test/edit/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<li><a href="/test/tree/master"><span class="fa fa-random">'
                '</span>&nbsp; master</a></li><li class="active">'
                '<span class="fa fa-file"></span>&nbsp; sources</li>',
                output_text,
            )
            self.assertIn(
                '<textarea id="textareaCode" name="content">foo\n bar</textarea>',
                output_text,
            )
            self.assertIn(
                '<option value="bar@pingou.com" selected>bar@pingou.com'
                "</option>",
                output_text,
            )
            self.assertIn(
                '<option value="foo@pingou.com" >foo@pingou.com</option>',
                output_text,
            )

    @patch("pagure.decorators.admin_session_timedout")
    def test_change_ref_head(self, ast):
        """Test the change_ref_head endpoint."""
        ast.return_value = True

        # No Git repo
        output = self.app.post("/foo/default/branch/")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/foo/default/branch/")
            self.assertEqual(output.status_code, 404)

            ast.return_value = False

            output = self.app.post("/foo/default/branch/")
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            repos = tests.create_projects_git(os.path.join(self.path, "repos"))

            output = self.app.post("/test/default/branch/")
            self.assertEqual(output.status_code, 403)

        # User no logged in
        output = self.app.post("/test/default/branch/")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                "/test/default/branch/", follow_redirects=True
            )  # without git branch
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<select class="c-select" id="branches" name="branches" '
                    "required></select>",
                    output_text,
                )
            else:
                self.assertIn(
                    '<select class="c-select" id="branches" name="branches">'
                    "</select>",
                    output_text,
                )
            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            repo_obj = pygit2.Repository(repos[0])
            tree = repo_obj.index.write_tree()
            author = pygit2.Signature("Alice Author", "alice@authors.tld")
            committer = pygit2.Signature(
                "Cecil Committer", "cecil@committers.tld"
            )
            repo_obj.create_commit(
                "refs/heads/master",  # the name of the reference to update
                author,
                committer,
                "Add sources file for testing",
                # binary string representing the tree object ID
                tree,
                # list of binary strings representing parents of the new commit
                [],
            )
            repo_obj.create_branch("feature", repo_obj.head.peel())

            data = {"branches": "feature", "csrf_token": csrf_token}

            # changing head to feature branch
            output = self.app.post(
                "/test/default/branch/", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<select class="c-select" id="branches" name="branches" '
                    "required>"
                    '<option selected value="feature">feature</option>'
                    '<option value="master">master</option>'
                    "</select>",
                    output_text,
                )
            else:
                self.assertIn(
                    '<select class="c-select" id="branches" name="branches">'
                    '<option selected value="feature">feature</option>'
                    '<option value="master">master</option>'
                    "</select>",
                    output_text,
                )
            self.assertIn("Default branch updated " "to feature", output_text)

            data = {"branches": "master", "csrf_token": csrf_token}

            # changing head to master branch
            output = self.app.post(
                "/test/default/branch/", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<select class="c-select" id="branches" name="branches" '
                    "required>"
                    '<option value="feature">feature</option>'
                    '<option selected value="master">master</option>'
                    "</select>",
                    output_text,
                )
            else:
                self.assertIn(
                    '<select class="c-select" id="branches" name="branches">'
                    '<option value="feature">feature</option>'
                    '<option selected value="master">master</option>'
                    "</select>",
                    output_text,
                )
            self.assertIn("Default branch updated " "to master", output_text)

    def test_new_release(self):
        """Test the new_release endpoint."""

        # No Git repo
        output = self.app.post("/foo/upload/")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/foo/upload/")
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            repo = tests.create_projects_git(os.path.join(self.path, "repos"))

            output = self.app.post("/test/upload/")
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.post("/test/upload/")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            img = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "placebo.png"
            )

            # Missing CSRF Token
            with open(img, mode="rb") as stream:
                data = {"filestream": stream}
                output = self.app.post("/test/upload/", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<h2>Upload a new release</h2>", output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            upload_dir = os.path.join(self.path, "releases")
            self.assertEqual(os.listdir(upload_dir), [])

            # Upload successful
            with open(img, mode="rb") as stream:
                data = {"filestream": stream, "csrf_token": csrf_token}
                output = self.app.post(
                    "/test/upload/", data=data, follow_redirects=True
                )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("File", output_text)
            self.assertIn("uploaded", output_text)
            self.assertIn("This project has not been tagged.", output_text)

            self.assertEqual(os.listdir(upload_dir), ["test"])
            folder = os.path.join(upload_dir, "test")
            checksum_file = os.path.join(folder, "CHECKSUMS")

            # Check the checksums file
            self.assertTrue(os.path.exists(checksum_file))
            self.assertEqual(len(os.listdir(folder)), 2)

            # Check the content of the checksums file
            with open(checksum_file) as stream:
                data = stream.readlines()
            self.assertEqual(len(data), 3)
            self.assertEqual(data[0], "# Generated and updated by pagure\n")
            self.assertTrue(data[1].startswith("SHA256 ("))
            self.assertTrue(
                data[1].endswith(
                    "tests_placebo.png) = 8a06845923010b27bfd8e7e75acff"
                    "7badc40d1021b4994e01f5e11ca40bc3abe\n"
                )
            )
            self.assertTrue(data[2].startswith("SHA512 ("))
            self.assertTrue(
                data[2].endswith(
                    "tests_placebo.png) = 65a4458df0acb29dc3c5ad4a3620e"
                    "98841d1fcf3f8df358f5348fdeddd1a86706491ac6e416768e"
                    "9f218aae8147d6ac524a59d3eb91fb925fdcb5c489e55ccbb\n"
                )
            )

            # Try uploading the same file -- fails
            with open(img, mode="rb") as stream:
                data = {"filestream": stream, "csrf_token": csrf_token}
                output = self.app.post(
                    "/test/upload/", data=data, follow_redirects=True
                )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "This tarball has already " "been uploaded", output_text
            )
            self.assertIn("This project has not been tagged.", output_text)

    def test_new_release_two_files(self):
        """Test the new_release endpoint when uploading two files."""
        tests.create_projects(self.session)
        repo = tests.create_projects_git(os.path.join(self.path, "repos"))

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            img = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "placebo.png"
            )
            img2 = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "pagure.png"
            )

            csrf_token = self.get_csrf()

            upload_dir = os.path.join(self.path, "releases")
            self.assertEqual(os.listdir(upload_dir), [])

            # Upload successful
            with open(img, mode="rb") as stream:
                with open(img2, mode="rb") as stream2:
                    data = {
                        "filestream": [stream, stream2],
                        "csrf_token": csrf_token,
                    }
                    output = self.app.post(
                        "/test/upload/", data=data, follow_redirects=True
                    )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<i class="fa fa-fw fa-info-circle"></i> File', output_text
            )
            self.assertIn("pagure.png&#34; uploaded</div>\n", output_text)
            # self.assertTrue(0)

            self.assertEqual(os.listdir(upload_dir), ["test"])
            folder = os.path.join(upload_dir, "test")
            checksum_file = os.path.join(folder, "CHECKSUMS")

            # Check the checksums file
            self.assertTrue(os.path.exists(checksum_file))
            self.assertEqual(len(os.listdir(folder)), 3)

            # Check the content of the checksums file
            with open(checksum_file) as stream:
                data = stream.readlines()
            self.assertEqual(len(data), 5)
            self.assertEqual(data[0], "# Generated and updated by pagure\n")
            self.assertTrue(data[1].startswith("SHA256 ("))
            self.assertTrue(
                data[1].endswith(
                    "tests_placebo.png) = 8a06845923010b27bfd8e7e75acff"
                    "7badc40d1021b4994e01f5e11ca40bc3abe\n"
                )
            )
            self.assertTrue(data[2].startswith("SHA512 ("))
            self.assertTrue(
                data[2].endswith(
                    "tests_placebo.png) = 65a4458df0acb29dc3c5ad4a3620e"
                    "98841d1fcf3f8df358f5348fdeddd1a86706491ac6e416768e"
                    "9f218aae8147d6ac524a59d3eb91fb925fdcb5c489e55ccbb\n"
                )
            )
            self.assertTrue(data[3].startswith("SHA256 ("))
            self.assertTrue(
                data[3].endswith(
                    "tests_pagure.png) = 6498a2de405546200b6144da56fc25"
                    "d0a3976ae688dbfccaca609c8b4480523e\n"
                )
            )
            self.assertTrue(data[4].startswith("SHA512 ("))
            self.assertTrue(
                data[4].endswith(
                    "tests_pagure.png) = 15458775e5d73cd74de7da7224597f6"
                    "7f8b23d62d3affb8abba4f5db74d33235642a0f744de2265cca7"
                    "d2b5866782c45e1fdeb32dd2822ae33e97995d4879afd\n"
                )
            )

    @patch("pagure.decorators.admin_session_timedout")
    def test_add_token_all_tokens(self, ast):
        """Test the add_token endpoint."""
        ast.return_value = False
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/token/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create a new token</strong>", output_text)
            self.assertEqual(
                output_text.count('<label class="c-input c-checkbox">'),
                len(pagure.config.config["ACLS"].keys()) - 1,
            )

    @patch.dict("pagure.config.config", {"USER_ACLS": ["create_project"]})
    @patch("pagure.decorators.admin_session_timedout")
    def test_add_token_one_token(self, ast):
        """Test the add_token endpoint."""
        ast.return_value = False
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/token/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create a new token</strong>", output_text)
            self.assertEqual(
                output_text.count('<label class="c-input c-checkbox">'), 1
            )

    @patch("pagure.decorators.admin_session_timedout")
    def test_add_token(self, ast):
        """Test the add_token endpoint."""
        ast.return_value = False

        # No Git repo
        output = self.app.get("/foo/token/new/")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/foo/token/new/")
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(
                os.path.join(self.path, "repos"), bare=True
            )

            output = self.app.get("/test/token/new/")
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.get("/test/token/new/")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/token/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create a new token</strong>", output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]
            data = {"csrf_token": csrf_token}

            ast.return_value = True
            # Test when the session timed-out
            output = self.app.post("/test/token/new/", data=data)
            self.assertEqual(output.status_code, 302)
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Action canceled, try it " "again", output_text)
            ast.return_value = False

            # Missing acls
            output = self.app.post("/test/token/new/", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create a new token</strong>", output_text)
            self.assertIn(
                "You must select at least " "one permission.", output_text
            )

            data = {
                "csrf_token": csrf_token,
                "acls": ["issue_create"],
                "description": "Test token",
            }

            # New token created
            output = self.app.post(
                "/test/token/new/", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Token created", output_text)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">Project Settings</h5>',
                output_text,
            )
            self.assertIn("<strong> Test token</strong>", output_text)
            self.assertIn(
                '<small class="font-weight-bold">Active until', output_text
            )

    @patch("pagure.decorators.admin_session_timedout")
    def test_revoke_api_token(self, ast):
        """Test the revoke_api_token endpoint."""
        ast.return_value = False

        # No Git repo
        output = self.app.post("/foo/token/revoke/123")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/foo/token/revoke/123")
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(
                os.path.join(self.path, "repos"), bare=True
            )

            output = self.app.post("/test/token/revoke/123")
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.post("/test/token/revoke/123")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/token/new")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create a new token</strong>", output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]
            data = {"csrf_token": csrf_token}

            ast.return_value = True
            # Test when the session timed-out
            output = self.app.post("/test/token/revoke/123", data=data)
            self.assertEqual(output.status_code, 302)
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Action canceled, try it again", output_text)
            ast.return_value = False

            output = self.app.post("/test/token/revoke/123", data=data)
            self.assertEqual(output.status_code, 404)
            output_text = output.get_data(as_text=True)
            self.assertIn("<p>Token not found</p>", output_text)

            # Create a token to revoke
            data = {"csrf_token": csrf_token, "acls": ["issue_create"]}
            output = self.app.post(
                "/test/token/new/", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Token created", output_text)

            # Existing token will expire in 60 days
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.tokens[0].expiration.date(),
                datetime.datetime.utcnow().date()
                + datetime.timedelta(days=(30 * 6)),
            )

            token = repo.tokens[0].id
            output = self.app.post(
                "/test/token/revoke/%s" % token,
                data=data,
                follow_redirects=True,
            )
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn("Token revoked", output_text)
            self.assertEqual(output_text.count('title="Revoke token">'), 0)
            self.assertEqual(output_text.count('title="Renew token">'), 1)

            # Existing token has been expired
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.tokens[0].expiration.date(), repo.tokens[0].created.date()
            )
            self.assertEqual(
                repo.tokens[0].expiration.date(),
                datetime.datetime.utcnow().date(),
            )

    @patch("pagure.decorators.admin_session_timedout")
    def test_renew_api_token(self, ast):
        """Test the renew_api_token endpoint."""
        ast.return_value = False

        # No Git repo
        output = self.app.post("/foo/token/renew/123")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            # user logged in but still no git repo
            output = self.app.post("/foo/token/renew/123")
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(
                os.path.join(self.path, "repos"), bare=True
            )

            # user logged in, git repo present, but user doesn't have access
            output = self.app.post("/test/token/renew/123")
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.post("/test/token/renew/123")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/token/new")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create a new token</strong>", output_text)

            csrf_token = self.get_csrf(output=output)
            data = {"csrf_token": csrf_token}

            ast.return_value = True
            # Test when the session timed-out
            output = self.app.post("/test/token/renew/123", data=data)
            self.assertEqual(output.status_code, 302)
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Action canceled, try it again", output_text)
            ast.return_value = False

            output = self.app.post("/test/token/renew/123", data=data)
            self.assertEqual(output.status_code, 404)
            output_text = output.get_data(as_text=True)
            self.assertIn("<p>Token not found</p>", output_text)

            # Create a token to renew
            data = {"csrf_token": csrf_token, "acls": ["issue_create"]}
            output = self.app.post(
                "/test/token/new/", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Token created", output_text)

            # 1 token associated with the project, expires in 60 days
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(len(repo.tokens), 1)
            self.assertEqual(
                repo.tokens[0].expiration.date(),
                datetime.datetime.utcnow().date()
                + datetime.timedelta(days=(30 * 6)),
            )

            token = repo.tokens[0].id
            output = self.app.post(
                "/test/token/renew/%s" % token,
                data=data,
                follow_redirects=True,
            )
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn("Token created", output_text)
            self.assertEqual(output_text.count('title="Revoke token">'), 2)
            self.assertEqual(output_text.count('title="Renew token">'), 2)

            # Existing token has been renewed
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(len(repo.tokens), 2)
            self.assertEqual(
                repo.tokens[0].expiration.date(),
                repo.tokens[1].expiration.date(),
            )
            self.assertEqual(
                repo.tokens[0].created.date(), repo.tokens[1].created.date()
            )
            self.assertEqual(repo.tokens[0].acls, repo.tokens[1].acls)
            self.assertEqual(
                repo.tokens[0].description, repo.tokens[1].description
            )

    def test_delete_branch(self):
        """Test the delete_branch endpoint."""
        # No Git repo
        output = self.app.post("/foo/b/master/delete")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # User not logged in
        output = self.app.post("/test/b/master/delete")
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            # Unknown repo
            output = self.app.post("/foo/b/master/delete")
            self.assertEqual(output.status_code, 404)

            output = self.app.post("/test/b/master/delete")
            self.assertEqual(output.status_code, 403)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/b/master/delete")
            self.assertEqual(output.status_code, 403)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<p>You are not allowed to delete the default branch: master</p>",
                output_text,
            )

            output = self.app.post("/test/b/bar/delete")
            self.assertEqual(output.status_code, 404)
            output_text = output.get_data(as_text=True)
            self.assertIn("<p>Branch not found</p>", output_text)

            # Add a branch that we can delete
            path = os.path.join(self.path, "repos", "test.git")
            tests.add_content_git_repo(path)
            repo = pygit2.Repository(path)
            repo.create_branch("foo", repo.head.peel())

            # Check before deletion
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)

            output = self.app.get("/test/branches")
            output_text = output.get_data(as_text=True)
            self.assertIn('<form id="delete_branch_form-foo"', output_text)

            # Delete the branch
            output = self.app.post("/test/b/foo/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            output = self.app.get("/test/branches")
            output_text = output.get_data(as_text=True)
            self.assertNotIn('<form id="delete_branch_form-foo"', output_text)

            # Add a branch with a '/' in its name that we can delete
            path = os.path.join(self.path, "repos", "test.git")
            tests.add_content_git_repo(path)
            repo = pygit2.Repository(path)
            repo.create_branch("feature/foo", repo.head.peel())

            # Check before deletion
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)

            output = self.app.get("/test/branches")
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<form id="delete_branch_form-feature__foo"', output_text
            )

            # Delete the branch
            output = self.app.post(
                "/test/b/feature/foo/delete", follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)

            output = self.app.get("/test/branches")
            output_text = output.get_data(as_text=True)
            self.assertNotIn(
                '<form id="delete_branch_form-feature__foo"', output_text
            )

    def test_delete_branch_unicode(self):
        """Test the delete_branch endpoint with an unicode branch."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):

            # Add a branch that we can delete
            path = os.path.join(self.path, "repos", "test.git")
            tests.add_content_git_repo(path)
            repo = pygit2.Repository(path)
            branchname = "☃️"
            if six.PY2:
                branchname = branchname.encode("utf-8")
            repo.create_branch(branchname, repo.head.peel())

            # Check before deletion
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)

            output = self.app.get("/test/branches")
            output_text = output.get_data(as_text=True)
            self.assertIn('<form id="delete_branch_form-☃️"', output_text)

            # Delete the branch
            output = self.app.post("/test/b/☃️/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            # Check after deletion
            output = self.app.get("/test/branches")
            output_text = output.get_data(as_text=True)
            self.assertNotIn('<form id="delete_branch_form-☃️"', output_text)

    def test_delete_branch_master(self):
        """Test the delete_branch endpoint with the master branch."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        project = pagure.lib.query._get_project(self.session, "test")

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):

            # Add a branch that we can delete
            path = os.path.join(self.path, "repos", "test.git")
            tests.add_content_git_repo(path)
            repo = pygit2.Repository(path)
            branchname = "main"
            repo.create_branch(branchname, repo.head.peel())

            # Make that branch be the default one:
            pagure.lib.git.git_set_ref_head(project=project, branch=branchname)

            # Check before deletion
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)

            output = self.app.get("/test/branches")
            output_text = output.get_data(as_text=True)
            self.assertIn('<form id="delete_branch_form-master"', output_text)
            self.assertNotIn('<form id="delete_branch_form-main"', output_text)

            # Delete the branch
            output = self.app.post(
                "/test/b/master/delete", follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)

            # Check after deletion
            output = self.app.get("/test/branches")
            output_text = output.get_data(as_text=True)
            self.assertNotIn(
                '<form id="delete_branch_form-master"', output_text
            )
            self.assertNotIn('<form id="delete_branch_form-main"', output_text)

    @patch.dict("pagure.config.config", {"ALLOW_DELETE_BRANCH": False})
    def test_delete_branch_disabled_in_ui(self):
        """Test that the delete branch button doesn't show when the feature
        is turned off."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Add a branch that we can delete
        path = os.path.join(self.path, "repos", "test.git")
        tests.add_content_git_repo(path)
        repo = pygit2.Repository(path)
        repo.create_branch("foo", repo.head.peel())

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            # Check that the UI doesn't offer the button
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn('<form id="delete_branch_form-foo"', output_text)
            self.assertNotIn(
                "Are you sure you want to remove the branch", output_text
            )

    @patch.dict("pagure.config.config", {"ALLOW_DELETE_BRANCH": False})
    def test_delete_branch_disabled(self):
        """Test the delete_branch endpoint when it's disabled in the entire
        instance."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Add a branch that we can delete
        path = os.path.join(self.path, "repos", "test.git")
        tests.add_content_git_repo(path)
        repo = pygit2.Repository(path)
        repo.create_branch("foo", repo.head.peel())

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            # Check if the delete branch button does not show
            output = self.app.get("/test/branches")
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                'title="Remove branch foo"', output.get_data(as_text=True)
            )

            # Delete the branch
            output = self.app.post("/test/b/foo/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                "This pagure instance does not allow branch deletion",
                output.get_data(as_text=True),
            )

    @patch.dict("pagure.config.config", {"ALLOW_DELETE_BRANCH": False})
    def test_delete_branch_disabled_fork(self):
        """Test the delete_branch endpoint when it's disabled in the entire
        instance."""
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
        tests.create_projects_git(
            os.path.join(self.path, "repos", "forks", "foo"), bare=True
        )

        # Add a branch that we can delete
        path = os.path.join(self.path, "repos", "forks", "foo", "test.git")
        tests.add_content_git_repo(path)
        repo = pygit2.Repository(path)
        repo.create_branch("foo", repo.head.peel())

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            # Check if the delete branch button shows
            output = self.app.get("/fork/foo/test/branches")
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'title="Remove branch foo"', output.get_data(as_text=True)
            )

            # Delete the branch
            output = self.app.post(
                "/fork/foo/test/b/foo/delete", follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)

            # Check if the delete branch button no longer appears
            output = self.app.get("/fork/foo/test/branches")
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                'title="Remove branch foo"', output.get_data(as_text=True)
            )

    def test_view_docs(self):
        """Test the view_docs endpoint."""
        output = self.app.get("/docs/foo/")
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get("/docs/test/")
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/docs/test/")
        self.assertEqual(output.status_code, 404)

    def test_view_project_activity(self):
        """Test the view_project_activity endpoint."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Project Exists, but No DATAGREPPER_URL set
        output = self.app.get("/test/activity/")
        self.assertEqual(output.status_code, 404)

        # Project Exists, and DATAGREPPER_URL set
        pagure.config.config["DATAGREPPER_URL"] = "foo"
        output = self.app.get("/test/activity/")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Activity - test - Pagure</title>", output_text)
        self.assertIn("No activity reported on the test project", output_text)

        # project doesnt exist
        output = self.app.get("/foo/activity/")
        self.assertEqual(output.status_code, 404)

    def test_goimport(self):
        """Test the go-import tag."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        output = self.app.get("/test/")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<meta name="go-import" '
            'content="localhost.localdomain/test git git://localhost.localdomain/test.git"'
            ">",
            output_text,
        )

    def test_watch_repo(self):
        """Test the  watch_repo endpoint."""

        output = self.app.post("/watch/")
        self.assertEqual(output.status_code, 405)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"csrf_token": csrf_token}

            output = self.app.post(
                "/foo/watch/settings/1", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 404)

            output = self.app.post(
                "/test/watch/settings/8", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 400)

            output = self.app.post(
                "/test/watch/settings/0", data=data, follow_redirects=True
            )
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "You are no longer" " watching this project", output_text
            )

            output = self.app.post(
                "/test/watch/settings/1", data=data, follow_redirects=True
            )
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "You are now" " watching issues and PRs on this project",
                output_text,
            )

            output = self.app.post(
                "/test/watch/settings/2", data=data, follow_redirects=True
            )
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "You are now" " watching commits on this project", output_text
            )

            output = self.app.post(
                "/test/watch/settings/3", data=data, follow_redirects=True
            )
            output_text = output.get_data(as_text=True)
            self.assertIn(
                (
                    "You are now"
                    " watching issues, PRs, and commits on this project"
                ),
                output_text,
            )

            item = pagure.lib.model.Project(
                user_id=2,  # foo
                name="test",
                description="foo project #1",
                hook_token="aaabbb",
                is_fork=True,
                parent_id=1,
            )
            self.session.add(item)
            self.session.commit()
            gitrepo = os.path.join(
                self.path, "repos", "forks", "foo", "test.git"
            )
            pygit2.init_repository(gitrepo, bare=True)

            output = self.app.post(
                "/fork/foo/test/watch/settings/-1",
                data=data,
                follow_redirects=True,
            )
            output_text = output.get_data(as_text=True)
            self.assertIn("Watch status is already reset", output_text)

            output = self.app.post(
                "/fork/foo/test/watch/settings/0",
                data=data,
                follow_redirects=True,
            )
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "You are no longer" " watching this project", output_text
            )

            output = self.app.get("/test", data=data, follow_redirects=True)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                (
                    '<span class="btn btn-sm btn-primary font-weight-bold">1'
                    "</span>\n                    "
                    '<div class="dropdown-menu dropdown-menu-right watch-menu">'
                ),
                output_text,
            )

            output = self.app.post(
                "/fork/foo/test/watch/settings/1",
                data=data,
                follow_redirects=True,
            )
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "You are now" " watching issues and PRs on this project",
                output_text,
            )

            output = self.app.get("/test", data=data, follow_redirects=True)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                (
                    '<span class="btn btn-sm btn-primary font-weight-bold">1'
                    "</span>\n                    "
                    '<div class="dropdown-menu dropdown-menu-right watch-menu">'
                ),
                output_text,
            )

            output = self.app.post(
                "/fork/foo/test/watch/settings/2",
                data=data,
                follow_redirects=True,
            )
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "You are now" " watching commits on this project", output_text
            )

            output = self.app.post(
                "/fork/foo/test/watch/settings/3",
                data=data,
                follow_redirects=True,
            )
            output_text = output.get_data(as_text=True)
            self.assertIn(
                (
                    "You are now"
                    " watching issues, PRs, and commits on this project"
                ),
                output_text,
            )

            output = self.app.get("/test", data=data, follow_redirects=True)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                (
                    '<span class="btn btn-sm btn-primary font-weight-bold">1'
                    "</span>\n                    "
                    '<div class="dropdown-menu dropdown-menu-right watch-menu">'
                ),
                output_text,
            )

            project = pagure.lib.query._get_project(self.session, "test")
            pagure.lib.query.add_user_to_project(
                self.session,
                project,
                new_user="foo",
                user="pingou",
                access="commit",
            )
            self.session.commit()

            output = self.app.get("/test", data=data, follow_redirects=True)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                (
                    '<span class="btn btn-sm btn-primary font-weight-bold">2'
                    "</span>\n                    "
                    '<div class="dropdown-menu dropdown-menu-right watch-menu">'
                ),
                output_text,
            )

            output = self.app.post(
                "/fork/foo/test/watch/settings/-1",
                data=data,
                follow_redirects=True,
            )
            output_text = output.get_data(as_text=True)
            self.assertIn("Watch status reset", output_text)

            output = self.app.get("/test", data=data, follow_redirects=True)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                (
                    '<span class="btn btn-sm btn-primary font-weight-bold">2'
                    "</span>\n                    "
                    '<div class="dropdown-menu dropdown-menu-right watch-menu">'
                ),
                output_text,
            )

    def test_delete_report(self):
        """Test the  delete_report endpoint."""

        output = self.app.post("/test/delete/report")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            # No report specified
            data = {"csrf_token": csrf_token}
            output = self.app.post(
                "/test/delete/report", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Unknown report: None", output_text)

            # Report specified not in the project's reports
            data = {"csrf_token": csrf_token, "report": "foo"}
            output = self.app.post(
                "/test/delete/report", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Unknown report: foo", output_text)

            # Create a report
            project = pagure.lib.query.get_authorized_project(
                self.session, project_name="test"
            )
            self.assertEqual(project.reports, {})
            name = "test report"
            url = "?foo=bar&baz=biz"
            pagure.lib.query.save_report(
                self.session, repo=project, name=name, url=url, username=None
            )
            self.session.commit()
            project = pagure.lib.query.get_authorized_project(
                self.session, project_name="test"
            )
            self.assertEqual(
                project.reports, {"test report": {"baz": "biz", "foo": "bar"}}
            )

            # Missing CSRF
            data = {"report": "test report"}
            output = self.app.post(
                "/test/delete/report", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )

            project = pagure.lib.query.get_authorized_project(
                self.session, project_name="test"
            )
            self.assertEqual(
                project.reports, {"test report": {"baz": "biz", "foo": "bar"}}
            )

            # Delete the report
            data = {"csrf_token": csrf_token, "report": "test report"}
            output = self.app.post(
                "/test/delete/report", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("List of reports updated", output_text)
            self.session.commit()
            project = pagure.lib.query.get_authorized_project(
                self.session, project_name="test"
            )
            self.assertEqual(project.reports, {})

    def test_delete_report_ns_project(self):
        """Test the  delete_report endpoint on a namespaced project."""

        output = self.app.post("/foo/test/delete/report")
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                namespace="foo",
                name="test",
                description="foo project #2",
                hook_token="aaabbb",
            )
            self.session.add(item)
            self.session.commit()
            gitrepo = os.path.join(self.path, "repos", "foo", "test.git")
            pygit2.init_repository(gitrepo, bare=True)

            # No report specified
            data = {"csrf_token": csrf_token}
            output = self.app.post(
                "/foo/test/delete/report", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Unknown report: None", output_text)

            # Report specified not in the project's reports
            data = {"csrf_token": csrf_token, "report": "foo"}
            output = self.app.post(
                "/foo/test/delete/report", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Unknown report: foo", output_text)

            # Create a report
            self.session.commit()
            project = pagure.lib.query.get_authorized_project(
                self.session, project_name="test", namespace="foo"
            )
            self.assertEqual(project.reports, {})
            name = "test report"
            url = "?foo=bar&baz=biz"
            pagure.lib.query.save_report(
                self.session, repo=project, name=name, url=url, username=None
            )
            self.session.commit()
            project = pagure.lib.query.get_authorized_project(
                self.session, project_name="test", namespace="foo"
            )
            self.assertEqual(
                project.reports, {"test report": {"baz": "biz", "foo": "bar"}}
            )

            # Missing CSRF
            data = {"report": "test report"}
            output = self.app.post(
                "/foo/test/delete/report", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - foo/test - Pagure</title>", output_text
            )

            project = pagure.lib.query.get_authorized_project(
                self.session, project_name="test", namespace="foo"
            )
            self.assertEqual(
                project.reports, {"test report": {"baz": "biz", "foo": "bar"}}
            )

            # Delete the report
            data = {"csrf_token": csrf_token, "report": "test report"}
            output = self.app.post(
                "/foo/test/delete/report", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("List of reports updated", output_text)

            self.session.commit()
            project = pagure.lib.query.get_authorized_project(
                self.session, project_name="test", namespace="foo"
            )
            self.assertEqual(project.reports, {})

    def test_open_pr_button_empty_repo(self):
        """Test "Open Pull-Request" button on empty project."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<p>This repo is brand new!</p>", output_text)
        self.assertNotIn(
            'href="/test/diff/master..master">Open Pull-Request', output_text
        )

    @patch.dict(
        "pagure.config.config",
        {"UPLOAD_FOLDER_PATH": None, "UPLOAD_FOLDER_URL": None},
    )
    def test_releases_upload_folder_vars_None(self):
        """Test that /releases/ page of a repo displays correctly with
        UPLOAD_FOLDER_PATH and UPLOAD_FOLDER_URL set to None
        """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/releases")
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "This project has not been tagged.", output.get_data(as_text=True)
        )


class PagureFlaskRepoTestHooktests(tests.Modeltests):
    """Tests for the web hook test function"""

    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureFlaskRepoTestHooktests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_test_hook_no_project(self):
        """Test the test_hook endpoint when the project doesn't exist."""
        # No project
        output = self.app.post("/foo/settings/test_hook")
        self.assertEqual(output.status_code, 404)

    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_test_hook_existing_project(self):
        """Test the test_hook endpoint when the project doesn't exist."""
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/settings/test_hook")
            self.assertEqual(output.status_code, 403)

    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_test_hook_logged_out(self):
        """Test the test_hook endpoint when the project isn't logged in."""
        # User not logged in
        output = self.app.post("/test/settings/test_hook")
        self.assertEqual(output.status_code, 302)

    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_test_hook_logged_in_no_csrf(self):
        """Test the test_hook endpoint when the user is logged in."""
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/settings/test_hook")
            self.assertEqual(output.status_code, 302)
        self.assertEqual(output.status_code, 302)

    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_test_hook_logged_in_csrf(self):
        """Test the test_hook endpoint when the user is logged in."""
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {"csrf_token": self.get_csrf()}
            output = self.app.post("/test/settings/test_hook", data=data)
            self.assertEqual(output.status_code, 302)


class PagureFlaskRepoTestRegenerateGittests(tests.Modeltests):
    """Tests for the regenerate git repo function"""

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureFlaskRepoTestRegenerateGittests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            self.csrf_token = self.get_csrf()

    def test_regenerate_git_invalid_project(self):
        """Test the regenerate_git endpoint."""
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/foo/regenerate")
            self.assertEqual(output.status_code, 404)

    def test_regenerate_git_invalid_user(self):
        """Test the regenerate_git endpoint."""
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/regenerate")
            self.assertEqual(output.status_code, 403)

    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=True),
    )
    def test_regenerate_git_user_session_timeout(self):
        """Test the regenerate_git endpoint."""
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/regenerate")
            self.assertEqual(output.status_code, 302)

    def test_regenerate_git_no_csrf(self):
        """Test the regenerate_git endpoint."""
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/regenerate")
            self.assertEqual(output.status_code, 400)

    def test_regenerate_git_missing_repo_type(self):
        """Test the regenerate_git endpoint."""
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {"csrf_token": self.csrf_token}

            output = self.app.post("/test/regenerate", data=data)
            self.assertEqual(output.status_code, 400)

    def test_regenerate_git_missing_invalid_regenerate(self):
        """Test the regenerate_git endpoint."""
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {"csrf_token": self.csrf_token, "regenerate": "ticket"}
            output = self.app.post("/test/regenerate", data=data)
            self.assertEqual(output.status_code, 400)

    @patch("pagure.lib.git._update_git")
    def test_regenerate_git_tickets(self, upgit):
        """Test the regenerate_git endpoint."""
        upgit.return_value = True

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            # Create an issue to play with
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            msg = pagure.lib.query.new_issue(
                session=self.session,
                repo=repo,
                title="Test issue",
                content="We should work on this",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(msg.title, "Test issue")

            data = {"csrf_token": self.csrf_token, "regenerate": "tickets"}
            output = self.app.post(
                "/test/regenerate", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Tickets git repo updating", output_text)
        self.assertEqual(upgit.call_count, 2)

    @patch("pagure.lib.git._update_git")
    def test_regenerate_git_requests(self, upgit):
        """Test the regenerate_git endpoint."""
        # upgit.return_value = True

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            # Create a request to play with
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            msg = pagure.lib.query.new_pull_request(
                session=self.session,
                repo_from=repo,
                branch_from="branch",
                repo_to=repo,
                branch_to="master",
                title="Test pull-request",
                user="pingou",
            )
            self.session.commit()
            self.assertEqual(msg.title, "Test pull-request")

            data = {"csrf_token": self.csrf_token, "regenerate": "requests"}
            output = self.app.post(
                "/test/regenerate", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Requests git repo updating", output_text)
        self.assertEqual(upgit.call_count, 1)


class PagureFlaskRepoTestGitSSHURL(tests.Modeltests):
    """Tests the display of the SSH url in the UI"""

    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureFlaskRepoTestGitSSHURL, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))
        pingou = pagure.lib.query.get_user(self.session, "pingou")

        # Add a group and make pingou a member of it
        item = pagure.lib.model.PagureGroup(
            group_name="packager",
            group_type="user",
            display_name="User group",
            user_id=1,  # pingou
        )
        self.session.add(item)
        self.session.commit()

        pagure.lib.query.add_user_to_group(
            self.session, pingou.username, item, pingou.username, True
        )

        # Add a SSH key for pingou so that he is allowed to push via ssh
        msg = pagure.lib.query.add_sshkey_to_project_or_user(
            session=self.session,
            user=pingou,
            ssh_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q==",
            pushaccess=True,
            creator=pingou,
        )
        self.session.commit()
        self.assertEqual(msg, "SSH key added")

    def test_logged_out(self):
        """Test the default behavior with the user logged out."""

        output = self.app.get("/test")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<strong>Source Code</strong>", output_text)
        self.assertIn(
            '<div class="input-group-prepend"><span class="input-group-text">'
            "GIT</span></div>",
            output_text,
        )
        self.assertNotIn(
            '<div class="input-group-prepend"><span class="input-group-text">'
            "SSH</span></div>",
            output_text,
        )

    def test_logged_in(self):
        """Test the default behavior with the user logged in."""
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Source Code</strong>", output_text)
            self.assertIn(
                '<div class="input-group-prepend"><span class="input-group-text">'
                "GIT</span></div>",
                output_text,
            )
            self.assertIn(
                '<div class="input-group-prepend"><span class="input-group-text">'
                "SSH</span></div>",
                output_text,
            )

    @patch.dict("pagure.config.config", {"SSH_ACCESS_GROUPS": ["packager"]})
    def test_ssh_restricted_user_member(self):
        """Test when ssh is restricted and the user has access."""
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Source Code</strong>", output_text)
            self.assertIn(
                '<div class="input-group-prepend"><span class="input-group-text">'
                "GIT</span></div>",
                output_text,
            )
            self.assertIn(
                '<div class="input-group-prepend"><span class="input-group-text">'
                "SSH</span></div>",
                output_text,
            )

    @patch.dict("pagure.config.config", {"SSH_ACCESS_GROUPS": ["invalid"]})
    def test_ssh_restricted_user_non_member(self):
        """Test when ssh is restricted and the user does not have access."""
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Source Code</strong>", output_text)
            self.assertIn(
                '<div class="input-group-prepend"><span class="input-group-text">'
                "GIT</span></div>",
                output_text,
            )
            self.assertIn(
                "Only members of the invalid group(s) can clone via ssh",
                output_text,
            )
            self.assertNotIn(
                '<div class="input-group-prepend"><span class="input-group-text">'
                "SSH</span></div>",
                output_text,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
