# -*- coding: utf-8 -*-

"""
 (c) 2021 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import arrow
import copy
import datetime
import unittest
import shutil
import sys
import time
import os

import flask
import json
import munch
from mock import ANY, patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests


class PagureFlaskApiProjectHascommitTests(tests.SimplePagureTest):
    """Tests for the flask API of pagure for listing contributors of a project"""

    maxDiff = None

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureFlaskApiProjectHascommitTests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

    def test_private_project(self):
        project = pagure.lib.query.get_authorized_project(self.session, "test")
        project.private = True
        self.session.add(project)
        self.session.commit()

        output = self.app.get("/api/0/test/hascommit?user=pingou")
        self.assertEqual(output.status_code, 404)
        expected_rv = {
            "error": "Project not found",
            "error_code": "ENOPROJECT",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_missing_branch(self):

        output = self.app.get("/api/0/test/hascommit?user=pingou")
        self.assertEqual(output.status_code, 400)
        expected_rv = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_missing_user(self):

        output = self.app.get("/api/0/test/hascommit?branch=user")
        self.assertEqual(output.status_code, 400)
        expected_rv = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_just_main_admin(self):

        output = self.app.get("/api/0/test/hascommit?user=pingou&branch=main")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "args": {
                "branch": "main",
                "project": {
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
                    "date_created": ANY,
                    "date_modified": ANY,
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
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                },
                "user": "pingou",
            },
            "hascommit": True,
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_admin_user(self):

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="admin",
            branches=None,
            required_groups=None,
        )
        self.session.commit()
        self.assertEqual(msg, "User added")

        output = self.app.get("/api/0/test/hascommit?user=foo&branch=main")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "args": {
                "branch": "main",
                "project": {
                    "access_groups": {
                        "admin": [],
                        "collaborator": [],
                        "commit": [],
                        "ticket": [],
                    },
                    "access_users": {
                        "admin": ["foo"],
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
                    "date_created": ANY,
                    "date_modified": ANY,
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
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                },
                "user": "foo",
            },
            "hascommit": True,
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_admin_user_and_commit(self):

        tests.create_user(self.session, "baz", "foo baz", ["baz@bar.com"])

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="admin",
            branches=None,
            required_groups=None,
        )
        self.session.commit()
        self.assertEqual(msg, "User added")

        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=project,
            new_user="baz",
            user="pingou",
            access="commit",
            branches=None,
            required_groups=None,
        )
        self.session.commit()
        self.assertEqual(msg, "User added")

        output = self.app.get("/api/0/test/hascommit?user=baz&branch=main")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "args": {
                "branch": "main",
                "project": {
                    "access_groups": {
                        "admin": [],
                        "collaborator": [],
                        "commit": [],
                        "ticket": [],
                    },
                    "access_users": {
                        "admin": ["foo"],
                        "collaborator": [],
                        "commit": ["baz"],
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
                    "date_created": ANY,
                    "date_modified": ANY,
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
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                },
                "user": "baz",
            },
            "hascommit": True,
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_admin_user_and_commit_and_ticket(self):

        tests.create_user(self.session, "baz", "foo baz", ["baz@bar.com"])
        tests.create_user(
            self.session, "alex", "Alex Ander", ["alex@ander.com"]
        )

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="admin",
            branches=None,
            required_groups=None,
        )
        self.session.commit()
        self.assertEqual(msg, "User added")

        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=project,
            new_user="baz",
            user="pingou",
            access="commit",
            branches=None,
            required_groups=None,
        )
        self.session.commit()
        self.assertEqual(msg, "User added")

        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=project,
            new_user="alex",
            user="pingou",
            access="ticket",
            branches=None,
            required_groups=None,
        )
        self.session.commit()
        self.assertEqual(msg, "User added")

        output = self.app.get("/api/0/test/hascommit?user=alex&branch=main")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "args": {
                "branch": "main",
                "project": {
                    "access_groups": {
                        "admin": [],
                        "collaborator": [],
                        "commit": [],
                        "ticket": [],
                    },
                    "access_users": {
                        "admin": ["foo"],
                        "collaborator": [],
                        "commit": ["baz"],
                        "owner": ["pingou"],
                        "ticket": ["alex"],
                    },
                    "close_status": [
                        "Invalid",
                        "Insufficient data",
                        "Fixed",
                        "Duplicate",
                    ],
                    "custom_keys": [],
                    "date_created": ANY,
                    "date_modified": ANY,
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
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                },
                "user": "alex",
            },
            "hascommit": False,
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_admin_user_and_commit_and_ticket_and_contributors(self):

        tests.create_user(self.session, "baz", "foo baz", ["baz@bar.com"])
        tests.create_user(
            self.session, "alex", "Alex Ander", ["alex@ander.com"]
        )
        tests.create_user(self.session, "ralph", "Ralph B.", ["ralph@b.com"])
        tests.create_user(self.session, "kevin", "Kevin F.", ["kevin@f.com"])

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="admin",
            branches=None,
            required_groups=None,
        )
        self.session.commit()
        self.assertEqual(msg, "User added")

        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=project,
            new_user="baz",
            user="pingou",
            access="commit",
            branches=None,
            required_groups=None,
        )
        self.session.commit()
        self.assertEqual(msg, "User added")

        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=project,
            new_user="alex",
            user="pingou",
            access="ticket",
            branches=None,
            required_groups=None,
        )
        self.session.commit()
        self.assertEqual(msg, "User added")

        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=project,
            new_user="ralph",
            user="pingou",
            access="collaborator",
            branches="epel*",
            required_groups=None,
        )
        self.session.commit()
        self.assertEqual(msg, "User added")

        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=project,
            new_user="kevin",
            user="pingou",
            access="collaborator",
            branches="f*",
            required_groups=None,
        )
        self.session.commit()
        self.assertEqual(msg, "User added")

        output = self.app.get("/api/0/test/hascommit?user=kevin&branch=main")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "args": {
                "branch": "main",
                "project": {
                    "access_groups": {
                        "admin": [],
                        "collaborator": [],
                        "commit": [],
                        "ticket": [],
                    },
                    "access_users": {
                        "admin": ["foo"],
                        "collaborator": ["kevin", "ralph"],
                        "commit": ["baz"],
                        "owner": ["pingou"],
                        "ticket": ["alex"],
                    },
                    "close_status": [
                        "Invalid",
                        "Insufficient data",
                        "Fixed",
                        "Duplicate",
                    ],
                    "custom_keys": [],
                    "date_created": ANY,
                    "date_modified": ANY,
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
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                },
                "user": "kevin",
            },
            "hascommit": False,
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

        output = self.app.get("/api/0/test/hascommit?user=kevin&branch=f33")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "args": {
                "branch": "f33",
                "project": {
                    "access_groups": {
                        "admin": [],
                        "collaborator": [],
                        "commit": [],
                        "ticket": [],
                    },
                    "access_users": {
                        "admin": ["foo"],
                        "collaborator": ["kevin", "ralph"],
                        "commit": ["baz"],
                        "owner": ["pingou"],
                        "ticket": ["alex"],
                    },
                    "close_status": [
                        "Invalid",
                        "Insufficient data",
                        "Fixed",
                        "Duplicate",
                    ],
                    "custom_keys": [],
                    "date_created": ANY,
                    "date_modified": ANY,
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
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                },
                "user": "kevin",
            },
            "hascommit": True,
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)
