# -*- coding: utf-8 -*-

"""
 (c) 2017-2018 - Copyright Red Hat Inc

 Authors:
   Matt Prahl <mprahl@redhat.com>
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import sys
import os
import json
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.api
import pagure.lib.query
from pagure.exceptions import PagureException
import tests


class PagureFlaskApiGroupTests(tests.SimplePagureTest):
    """Tests for the flask API of pagure for issue"""

    maxDiff = None

    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureFlaskApiGroupTests, self).setUp()

        pagure.config.config["REQUESTS_FOLDER"] = None

        msg = pagure.lib.query.add_group(
            self.session,
            group_name="some_group",
            display_name="Some Group",
            description=None,
            group_type="bar",
            user="pingou",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()

        tests.create_projects(self.session)

        project = pagure.lib.query._get_project(self.session, "test2")
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="some_group",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

    def test_api_groups(self):
        """Test the api_groups function."""

        # Add a couple of groups so that we can list them
        item = pagure.lib.model.PagureGroup(
            group_name="group1",
            group_type="user",
            display_name="User group",
            user_id=1,  # pingou
        )
        self.session.add(item)

        item = pagure.lib.model.PagureGroup(
            group_name="rel-eng",
            group_type="user",
            display_name="Release engineering group",
            user_id=1,  # pingou
        )
        self.session.add(item)
        self.session.commit()

        output = self.app.get("/api/0/groups")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(data["groups"], ["group1", "rel-eng", "some_group"])
        self.assertEqual(
            sorted(data.keys()), ["groups", "pagination", "total_groups"]
        )
        self.assertEqual(data["total_groups"], 3)

        output = self.app.get("/api/0/groups?pattern=re")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(data["groups"], ["rel-eng"])
        self.assertEqual(
            sorted(data.keys()), ["groups", "pagination", "total_groups"]
        )
        self.assertEqual(data["total_groups"], 1)

    def test_api_groups_extended(self):
        """Test the api_groups function."""

        # Add a couple of groups so that we can list them
        item = pagure.lib.model.PagureGroup(
            group_name="group1",
            group_type="user",
            display_name="User group",
            user_id=1,  # pingou
        )
        self.session.add(item)

        item = pagure.lib.model.PagureGroup(
            group_name="rel-eng",
            group_type="user",
            display_name="Release engineering group",
            user_id=1,  # pingou
        )
        self.session.add(item)
        self.session.commit()

        output = self.app.get("/api/0/groups?extended=1")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for k in ["first", "last"]:
            self.assertIsNotNone(data["pagination"][k])
            data["pagination"][k] = "http://localhost..."
        self.assertEqual(
            data,
            {
                "groups": [
                    {"description": None, "name": "group1"},
                    {"description": None, "name": "rel-eng"},
                    {"description": None, "name": "some_group"},
                ],
                "pagination": {
                    "first": "http://localhost...",
                    "last": "http://localhost...",
                    "next": None,
                    "page": 1,
                    "pages": 1,
                    "per_page": 20,
                    "prev": None,
                },
                "total_groups": 3,
            },
        )

    def test_api_view_group_authenticated(self):
        """
        Test the api_view_group method of the flask api with an
        authenticated user. The tested group has one member.
        """
        tests.create_tokens(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/group/some_group", headers=headers)
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "full_url": "http://localhost.localdomain/group/some_group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "full_url": "http://localhost.localdomain/user/pingou",
                "url_path": "user/pingou",
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com", "foo@pingou.com"],
                "name": "pingou",
            },
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertDictEqual(data, exp)

    def test_api_view_group_unauthenticated(self):
        """
        Test the api_view_group method of the flask api with an
        unauthenticated user. The tested group has one member.
        """
        output = self.app.get("/api/0/group/some_group")
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "full_url": "http://localhost.localdomain/group/some_group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "full_url": "http://localhost.localdomain/user/pingou",
                "name": "pingou",
                "url_path": "user/pingou",
            },
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertDictEqual(data, exp)

    def test_api_view_group_two_members_authenticated(self):
        """
        Test the api_view_group method of the flask api with an
        authenticated user. The tested group has two members.
        """
        user = pagure.lib.model.User(
            user="mprahl",
            fullname="Matt Prahl",
            password="foo",
            default_email="mprahl@redhat.com",
        )
        self.session.add(user)
        self.session.commit()
        group = pagure.lib.query.search_groups(
            self.session, group_name="some_group"
        )
        result = pagure.lib.query.add_user_to_group(
            self.session, user.username, group, user.username, True
        )
        self.assertEqual(
            result, "User `mprahl` added to the group `some_group`."
        )
        self.session.commit()

        tests.create_tokens(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/group/some_group", headers=headers)
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "full_url": "http://localhost.localdomain/group/some_group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "full_url": "http://localhost.localdomain/user/pingou",
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com", "foo@pingou.com"],
                "name": "pingou",
                "url_path": "user/pingou",
            },
            "members": ["pingou", "mprahl"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
        }
        self.maxDiff = None
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertDictEqual(data, exp)

    def test_api_view_group_no_group_error(self):
        """
        Test the api_view_group method of the flask api
        The tested group has one member.
        """
        output = self.app.get("/api/0/group/some_group3")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(data["error"], "Group not found")
        self.assertEqual(data["error_code"], "ENOGROUP")

    def test_api_view_group_w_projects_and_acl(self):
        """
        Test the api_view_group method with project info and restricted
        to the admin ACL
        """
        tests.create_tokens(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get(
            "/api/0/group/some_group?projects=1", headers=headers
        )
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "full_url": "http://localhost.localdomain/group/some_group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "full_url": "http://localhost.localdomain/user/pingou",
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com", "foo@pingou.com"],
                "name": "pingou",
                "url_path": "user/pingou",
            },
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
            "pagination": {
                "first": "http://localhost...",
                "last": "http://localhost...",
                "next": None,
                "page": 1,
                "pages": 1,
                "per_page": 20,
                "prev": None,
            },
            "projects": [
                {
                    "access_groups": {
                        "admin": ["some_group"],
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
                    "date_created": "1492020239",
                    "date_modified": "1492020239",
                    "description": "test project #2",
                    "full_url": "http://localhost.localdomain/test2",
                    "fullname": "test2",
                    "id": 2,
                    "milestones": {},
                    "name": "test2",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "url_path": "test2",
                    "user": {
                        "fullname": "PY C",
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                }
            ],
            "total_projects": 1,
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertIsNotNone(data["pagination"]["first"])
        data["pagination"]["first"] = "http://localhost..."
        self.assertIsNotNone(data["pagination"]["last"])
        data["pagination"]["last"] = "http://localhost..."
        projects = []
        for p in data["projects"]:
            p["date_created"] = "1492020239"
            p["date_modified"] = "1492020239"
            projects.append(p)
        data["projects"] = projects
        self.assertDictEqual(data, exp)

        output = self.app.get(
            "/api/0/group/some_group?projects=1&acl=admin", headers=headers
        )
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertIsNotNone(data["pagination"]["first"])
        data["pagination"]["first"] = "http://localhost..."
        self.assertIsNotNone(data["pagination"]["last"])
        data["pagination"]["last"] = "http://localhost..."
        projects = []
        for p in data["projects"]:
            p["date_created"] = "1492020239"
            p["date_modified"] = "1492020239"
            projects.append(p)
        data["projects"] = projects
        self.assertDictEqual(data, exp)

    def test_api_view_group_w_projects_and_acl_commit(self):
        """
        Test the api_view_group method with project info and restricted
        to the commit ACL
        """

        output = self.app.get("/api/0/group/some_group?projects=1&acl=commit")
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "full_url": "http://localhost.localdomain/group/some_group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "full_url": "http://localhost.localdomain/user/pingou",
                "name": "pingou",
                "url_path": "user/pingou",
            },
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
            "pagination": {
                "first": "http://localhost...",
                "last": "http://localhost...",
                "next": None,
                "page": 1,
                "pages": 1,
                "per_page": 20,
                "prev": None,
            },
            "projects": [
                {
                    "access_groups": {
                        "admin": ["some_group"],
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
                    "date_created": "1492020239",
                    "date_modified": "1492020239",
                    "description": "test project #2",
                    "full_url": "http://localhost.localdomain/test2",
                    "fullname": "test2",
                    "id": 2,
                    "milestones": {},
                    "name": "test2",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "url_path": "test2",
                    "user": {
                        "fullname": "PY C",
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                }
            ],
            "total_projects": 1,
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertIsNotNone(data["pagination"]["first"])
        data["pagination"]["first"] = "http://localhost..."
        self.assertIsNotNone(data["pagination"]["last"])
        data["pagination"]["last"] = "http://localhost..."
        projects = []
        for p in data["projects"]:
            p["date_created"] = "1492020239"
            p["date_modified"] = "1492020239"
            projects.append(p)
        data["projects"] = projects
        self.assertDictEqual(data, exp)

    def test_api_view_group_w_projects_and_acl_ticket(self):
        """
        Test the api_view_group method with project info and restricted
        to the ticket ACL
        """

        output = self.app.get("/api/0/group/some_group?projects=1&acl=ticket")
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "full_url": "http://localhost.localdomain/group/some_group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "full_url": "http://localhost.localdomain/user/pingou",
                "name": "pingou",
                "url_path": "user/pingou",
            },
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
            "pagination": {
                "first": "http://localhost...",
                "last": "http://localhost...",
                "next": None,
                "page": 1,
                "pages": 1,
                "per_page": 20,
                "prev": None,
            },
            "projects": [
                {
                    "access_groups": {
                        "admin": ["some_group"],
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
                    "date_created": "1492020239",
                    "date_modified": "1492020239",
                    "description": "test project #2",
                    "full_url": "http://localhost.localdomain/test2",
                    "fullname": "test2",
                    "id": 2,
                    "milestones": {},
                    "name": "test2",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "url_path": "test2",
                    "user": {
                        "fullname": "PY C",
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                }
            ],
            "total_projects": 1,
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertIsNotNone(data["pagination"]["first"])
        data["pagination"]["first"] = "http://localhost..."
        self.assertIsNotNone(data["pagination"]["last"])
        data["pagination"]["last"] = "http://localhost..."
        projects = []
        for p in data["projects"]:
            p["date_created"] = "1492020239"
            p["date_modified"] = "1492020239"
            projects.append(p)
        data["projects"] = projects
        self.assertDictEqual(data, exp)

    def test_api_view_group_w_projects_and_acl_admin_no_project(self):
        """
        Test the api_view_group method with project info and restricted
        to the admin ACL
        """

        # Make the group having only commit access
        project = pagure.lib.query._get_project(self.session, "test2")
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="some_group",
            user="pingou",
            access="commit",
        )
        self.session.commit()
        self.assertEqual(msg, "Group access updated")

        output = self.app.get("/api/0/group/some_group?projects=1&acl=admin")
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "full_url": "http://localhost.localdomain/group/some_group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "full_url": "http://localhost.localdomain/user/pingou",
                "name": "pingou",
                "url_path": "user/pingou",
            },
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
            "pagination": {
                "first": "http://localhost...",
                "last": "http://localhost...",
                "next": None,
                "page": 1,
                "pages": 0,
                "per_page": 20,
                "prev": None,
            },
            "projects": [],
            "total_projects": 0,
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertIsNotNone(data["pagination"]["first"])
        data["pagination"]["first"] = "http://localhost..."
        self.assertIsNotNone(data["pagination"]["last"])
        data["pagination"]["last"] = "http://localhost..."
        self.assertDictEqual(data, exp)

    def test_api_view_group_w_projects_and_acl_commit_no_project(self):
        """
        Test the api_view_group method with project info and restricted
        to the commit ACL
        """

        # Make the group having only ticket access
        project = pagure.lib.query._get_project(self.session, "test2")
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="some_group",
            user="pingou",
            access="ticket",
        )
        self.session.commit()
        self.assertEqual(msg, "Group access updated")

        output = self.app.get("/api/0/group/some_group?projects=1&acl=commit")
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "full_url": "http://localhost.localdomain/group/some_group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "full_url": "http://localhost.localdomain/user/pingou",
                "name": "pingou",
                "url_path": "user/pingou",
            },
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
            "pagination": {
                "first": "http://localhost...",
                "last": "http://localhost...",
                "next": None,
                "page": 1,
                "pages": 0,
                "per_page": 20,
                "prev": None,
            },
            "projects": [],
            "total_projects": 0,
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertIsNotNone(data["pagination"]["first"])
        data["pagination"]["first"] = "http://localhost..."
        self.assertIsNotNone(data["pagination"]["last"])
        data["pagination"]["last"] = "http://localhost..."
        self.assertDictEqual(data, exp)

    def test_api_view_group_w_projects_and_acl_ticket_no_project(self):
        """
        Test the api_view_group method with project info and restricted
        to the ticket ACL
        """

        # Create a group not linked to any project
        item = pagure.lib.model.PagureGroup(
            group_name="rel-eng",
            group_type="user",
            display_name="Release engineering group",
            user_id=1,  # pingou
        )
        self.session.add(item)
        self.session.commit()

        output = self.app.get("/api/0/group/rel-eng?projects=1&acl=ticket")
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Release engineering group",
            "full_url": "http://localhost.localdomain/group/rel-eng",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "full_url": "http://localhost.localdomain/user/pingou",
                "name": "pingou",
                "url_path": "user/pingou",
            },
            "members": [],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "rel-eng",
            "pagination": {
                "first": "http://localhost...",
                "last": "http://localhost...",
                "next": None,
                "page": 1,
                "pages": 0,
                "per_page": 20,
                "prev": None,
            },
            "projects": [],
            "total_projects": 0,
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertIsNotNone(data["pagination"]["first"])
        data["pagination"]["first"] = "http://localhost..."
        self.assertIsNotNone(data["pagination"]["last"])
        data["pagination"]["last"] = "http://localhost..."
        self.assertDictEqual(data, exp)

    def test_api_view_group_w_projects_and_acl_pagination(self):
        """
        Tests the pagination for the api_view_group method
        """

        project = pagure.lib.query._get_project(self.session, "test2")
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project,
            new_group="some_group",
            user="pingou",
            access="commit",
        )
        self.session.commit()
        self.assertEqual(msg, "Group access updated")

        project_another = pagure.lib.query._get_project(self.session, "test")
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=project_another,
            new_group="some_group",
            user="pingou",
            access="commit",
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        tests.create_tokens(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get(
            "/api/0/group/some_group?per_page=1&projects=1", headers=headers
        )
        self.assertEqual(output.status_code, 200)

        data = json.loads(output.get_data(as_text=True))
        projects = [project["name"] for project in data["projects"]]

        # Test the result we've got from the first page out of two
        assert projects == ["test"]

        output_last = self.app.get(
            data["pagination"]["next"].replace("http://localhost", ""),
            headers=headers,
        )
        self.assertEqual(output_last.status_code, 200)
        data_last = json.loads(output_last.get_data(as_text=True))

        projects.extend([project["name"] for project in data_last["projects"]])

        # Note that pagure sorts projects alphabetically, so we're comparing
        # a different order that was the order of requests
        assert projects == ["test", "test2"]

    def test_api_group_add_member_authenticated(self):
        """
        Test the api_group_add_member method of the flask api with an
        authenticated user.
        """
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"user": "foo"}
        output = self.app.post(
            "/api/0/group/some_group/add", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "full_url": "http://localhost.localdomain/group/some_group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "full_url": "http://localhost.localdomain/user/pingou",
                "url_path": "user/pingou",
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com", "foo@pingou.com"],
                "name": "pingou",
            },
            "members": ["pingou", "foo"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertDictEqual(data, exp)

    def test_api_group_add_member_unauthenticated(self):
        """
        Assert that api_group_add_member method will fail with
        unauthenticated user.
        """
        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"user": "foo"}
        output = self.app.post(
            "/api/0/group/some_group/add", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 401)
        exp = {
            "error": (
                "Invalid or expired token. "
                "Please visit "
                "http://localhost.localdomain/settings#nav-api-tab "
                "to get or renew your API token."
            ),
            "error_code": "EINVALIDTOK",
            "errors": "Invalid token",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, exp)

    def test_api_group_add_member_no_permission(self):
        """
        Assert that api_group_add_member method will fail with
        user that don't have permissions to add member to group.
        """
        # Create tokens for foo user
        tests.create_tokens(self.session, user_id=2)
        tests.create_tokens_acl(self.session)
        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"user": "foo"}
        output = self.app.post(
            "/api/0/group/some_group/add", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        exp = {
            "error": (
                "An error occurred at the database level "
                "and prevent the action from reaching completion"
            ),
            "error_code": "EDBERROR",
            "errors": ["You are not allowed to add user to this group"],
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, exp)

    def test_api_group_add_member_no_group(self):
        """
        Assert that api_group_add_member method will fail when group doesn't
        exist.
        """
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"user": "foo"}
        output = self.app.post(
            "/api/0/group/no_group/add", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 404)
        exp = {"error": "Group not found", "error_code": "ENOGROUP"}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, exp)

    def test_api_group_add_member_invalid_request(self):
        """
        Assert that api_group_add_member method will fail when request
        is invalid.
        """
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"dummy": "foo"}
        output = self.app.post(
            "/api/0/group/some_group/add", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        exp = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {"user": ["This field is required."]},
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, exp)

    @patch("pagure.lib.query.add_user_to_group")
    def test_api_group_add_member_pagure_error(self, mock_add_user):
        """
        Assert that api_group_add_member method will fail when pagure
        throws exception.
        """
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        mock_add_user.side_effect = PagureException("Error")

        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"user": "foo"}
        output = self.app.post(
            "/api/0/group/some_group/add", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        exp = {
            "error": (
                "An error occurred at the database level "
                "and prevent the action from reaching completion"
            ),
            "error_code": "EDBERROR",
            "errors": ["Error"],
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, exp)

    @patch("pagure.lib.query.add_user_to_group")
    def test_api_group_add_member_sqlalchemy_error(self, mock_add_user):
        """
        Assert that api_group_add_member method will fail when SQLAlchemy
        throws exception.
        """
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        mock_add_user.side_effect = SQLAlchemyError("Error")

        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"user": "foo"}
        output = self.app.post(
            "/api/0/group/some_group/add", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        exp = {
            "error": (
                "An error occurred at the database level "
                "and prevent the action from reaching completion"
            ),
            "error_code": "EDBERROR",
            "errors": ["Error"],
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, exp)

    def test_api_group_remove_member_authenticated(self):
        """
        Test the api_group_remove_member method of the flask api with an
        authenticated user.
        """
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"user": "foo"}
        # Add user first
        output = self.app.post(
            "/api/0/group/some_group/add", data=payload, headers=headers
        )
        exp = {
            "display_name": "Some Group",
            "full_url": "http://localhost.localdomain/group/some_group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "full_url": "http://localhost.localdomain/user/pingou",
                "url_path": "user/pingou",
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com", "foo@pingou.com"],
                "name": "pingou",
            },
            "members": ["pingou", "foo"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertDictEqual(data, exp)

        # Then remove it
        output = self.app.post(
            "/api/0/group/some_group/remove", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "full_url": "http://localhost.localdomain/group/some_group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "full_url": "http://localhost.localdomain/user/pingou",
                "url_path": "user/pingou",
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com", "foo@pingou.com"],
                "name": "pingou",
            },
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertDictEqual(data, exp)

    def test_api_group_remove_member_unauthenticated(self):
        """
        Assert that api_group_remove_member method will fail with
        unauthenticated user.
        """
        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"user": "foo"}
        output = self.app.post(
            "/api/0/group/some_group/remove", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 401)
        exp = {
            "error": (
                "Invalid or expired token. "
                "Please visit "
                "http://localhost.localdomain/settings#nav-api-tab "
                "to get or renew your API token."
            ),
            "error_code": "EINVALIDTOK",
            "errors": "Invalid token",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, exp)

    def test_api_group_remove_member_no_permission(self):
        """
        Assert that api_group_remove_member method will fail with
        user that don't have permissions to remove member to group.
        """
        # Create tokens for foo user
        tests.create_tokens(self.session, user_id=2)
        tests.create_tokens_acl(self.session)
        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"user": "foo"}
        output = self.app.post(
            "/api/0/group/some_group/remove", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        exp = {
            "error": (
                "An error occurred at the database level "
                "and prevent the action from reaching completion"
            ),
            "error_code": "EDBERROR",
            "errors": ["You are not allowed to remove user from this group"],
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, exp)

    def test_api_group_remove_member_no_group(self):
        """
        Assert that api_group_remove_member method will fail when group doesn't
        exist.
        """
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"user": "foo"}
        output = self.app.post(
            "/api/0/group/no_group/remove", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 404)
        exp = {"error": "Group not found", "error_code": "ENOGROUP"}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, exp)

    def test_api_group_remove_member_invalid_request(self):
        """
        Assert that api_group_remove_member method will fail when request
        is invalid.
        """
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"dummy": "foo"}
        output = self.app.post(
            "/api/0/group/some_group/remove", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        exp = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {"user": ["This field is required."]},
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, exp)

    @patch("pagure.lib.query.delete_user_of_group")
    def test_api_group_remove_member_pagure_error(self, mock_remove_user):
        """
        Assert that api_group_remove_member method will fail when pagure
        throws exception.
        """
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        mock_remove_user.side_effect = PagureException("Error")

        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"user": "foo"}
        output = self.app.post(
            "/api/0/group/some_group/remove", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        exp = {
            "error": (
                "An error occurred at the database level "
                "and prevent the action from reaching completion"
            ),
            "error_code": "EDBERROR",
            "errors": ["Error"],
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, exp)

    @patch("pagure.lib.query.delete_user_of_group")
    def test_api_group_remove_member_sqlalchemy_error(self, mock_remove_user):
        """
        Assert that api_group_remove_member method will fail when SQLAlchemy
        throws exception.
        """
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        mock_remove_user.side_effect = SQLAlchemyError("Error")

        headers = {"Authorization": "token aaabbbcccddd"}
        payload = {"user": "foo"}
        output = self.app.post(
            "/api/0/group/some_group/remove", data=payload, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        exp = {
            "error": (
                "An error occurred at the database level "
                "and prevent the action from reaching completion"
            ),
            "error_code": "EDBERROR",
            "errors": ["Error"],
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, exp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
