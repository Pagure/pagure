# -*- coding: utf-8 -*-

"""
 (c) 2020 - Copyright Red Hat Inc

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
from mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests


class PagureFlaskApiProjectContributorsTests(tests.SimplePagureTest):
    """ Tests for the flask API of pagure for listing contributors of a project
    """

    maxDiff = None

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjectContributorsTests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

    def test_just_main_admin(self):

        output = self.app.get("/api/0/test/contributors")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "groups": {
                "admin": [],
                "collaborators": [],
                "commit": [],
                "ticket": [],
            },
            "users": {
                "admin": ["pingou"],
                "collaborators": [],
                "commit": [],
                "ticket": [],
            },
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

        output = self.app.get("/api/0/test/contributors")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "groups": {
                "admin": [],
                "collaborators": [],
                "commit": [],
                "ticket": [],
            },
            "users": {
                "admin": ["foo", "pingou"],
                "collaborators": [],
                "commit": [],
                "ticket": [],
            },
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

        output = self.app.get("/api/0/test/contributors")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "groups": {
                "admin": [],
                "collaborators": [],
                "commit": [],
                "ticket": [],
            },
            "users": {
                "admin": ["foo", "pingou"],
                "collaborators": [],
                "commit": ["baz"],
                "ticket": [],
            },
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

        output = self.app.get("/api/0/test/contributors")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "groups": {
                "admin": [],
                "collaborators": [],
                "commit": [],
                "ticket": [],
            },
            "users": {
                "admin": ["foo", "pingou"],
                "collaborators": [],
                "commit": ["baz"],
                "ticket": ["alex"],
            },
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

        output = self.app.get("/api/0/test/contributors")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "groups": {
                "admin": [],
                "collaborators": [],
                "commit": [],
                "ticket": [],
            },
            "users": {
                "admin": ["foo", "pingou"],
                "collaborators": [
                    {"branches": "f*", "user": "kevin"},
                    {"branches": "epel*", "user": "ralph"},
                ],
                "commit": ["baz"],
                "ticket": ["alex"],
            },
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_admin_group(self):

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="admin_groups",
            user="pingou",
            access="admin",
            branches=None,
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        output = self.app.get("/api/0/test/contributors")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "groups": {
                "admin": ["admin_groups"],
                "collaborators": [],
                "commit": [],
                "ticket": [],
            },
            "users": {
                "admin": ["pingou"],
                "collaborators": [],
                "commit": [],
                "ticket": [],
            },
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_admin_and_commit_groups(self):

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="admin_groups",
            user="pingou",
            access="admin",
            branches=None,
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="commit_group",
            user="pingou",
            access="commit",
            branches=None,
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        output = self.app.get("/api/0/test/contributors")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "groups": {
                "admin": ["admin_groups"],
                "collaborators": [],
                "commit": ["commit_group"],
                "ticket": [],
            },
            "users": {
                "admin": ["pingou"],
                "collaborators": [],
                "commit": [],
                "ticket": [],
            },
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_admin_and_commit_and_ticket_groups(self):

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="admin_groups",
            user="pingou",
            access="admin",
            branches=None,
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="commit_group",
            user="pingou",
            access="commit",
            branches=None,
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="ticket_group",
            user="pingou",
            access="ticket",
            branches=None,
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        output = self.app.get("/api/0/test/contributors")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "groups": {
                "admin": ["admin_groups"],
                "collaborators": [],
                "commit": ["commit_group"],
                "ticket": ["ticket_group"],
            },
            "users": {
                "admin": ["pingou"],
                "collaborators": [],
                "commit": [],
                "ticket": [],
            },
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_admin_and_commit_and_ticket_and_collaborators_groups(self):

        project = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="admin_groups",
            user="pingou",
            access="admin",
            branches=None,
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="commit_group",
            user="pingou",
            access="commit",
            branches=None,
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="ticket_group",
            user="pingou",
            access="ticket",
            branches=None,
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="epel_group",
            user="pingou",
            access="collaborator",
            branches="epel*",
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="fedora_group",
            user="pingou",
            access="collaborator",
            branches="f*",
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        output = self.app.get("/api/0/test/contributors")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "groups": {
                "admin": ["admin_groups"],
                "collaborators": [
                    {"branches": "epel*", "user": "epel_group"},
                    {"branches": "f*", "user": "fedora_group"},
                ],
                "commit": ["commit_group"],
                "ticket": ["ticket_group"],
            },
            "users": {
                "admin": ["pingou"],
                "collaborators": [],
                "commit": [],
                "ticket": [],
            },
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_full(self):

        tests.create_user(self.session, "baz", "foo baz", ["baz@bar.com"])
        tests.create_user(
            self.session, "alex", "Alex Ander", ["alex@ander.com"]
        )
        tests.create_user(self.session, "ralph", "Ralph B.", ["ralph@b.com"])
        tests.create_user(self.session, "kevin", "Kevin F.", ["kevin@f.com"])

        project = pagure.lib.query.get_authorized_project(self.session, "test")

        # Add users for all kinds of access
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

        # Create groups for all kinds of access
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="admin_groups",
            user="pingou",
            access="admin",
            branches=None,
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="commit_group",
            user="pingou",
            access="commit",
            branches=None,
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="ticket_group",
            user="pingou",
            access="ticket",
            branches=None,
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="epel_group",
            user="pingou",
            access="collaborator",
            branches="epel*",
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="fedora_group",
            user="pingou",
            access="collaborator",
            branches="f*",
            create=True,
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        output = self.app.get("/api/0/test/contributors")
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "groups": {
                "admin": ["admin_groups"],
                "collaborators": [
                    {"branches": "epel*", "user": "epel_group"},
                    {"branches": "f*", "user": "fedora_group"},
                ],
                "commit": ["commit_group"],
                "ticket": ["ticket_group"],
            },
            "users": {
                "admin": ["foo", "pingou"],
                "collaborators": [
                    {"branches": "f*", "user": "kevin"},
                    {"branches": "epel*", "user": "ralph"},
                ],
                "commit": ["baz"],
                "ticket": ["alex"],
            },
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)


if __name__ == "__main__":
    unittest.main(verbosity=2)
