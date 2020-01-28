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

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.api
import pagure.lib.query
import tests


class PagureFlaskApiGroupTests(tests.SimplePagureTest):
    """ Tests for the flask API of pagure for issue """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
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
        """ Test the api_groups function.  """

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
        """ Test the api_groups function.  """

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
            "description": None,
            "creator": {
                "fullname": "PY C",
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
            "description": None,
            "creator": {"fullname": "PY C", "name": "pingou"},
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
            "description": None,
            "creator": {
                "fullname": "PY C",
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com", "foo@pingou.com"],
                "name": "pingou",
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
            "description": None,
            "creator": {
                "fullname": "PY C",
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com", "foo@pingou.com"],
                "name": "pingou",
            },
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
            "projects": [
                {
                    "access_groups": {
                        "admin": ["some_group"],
                        "commit": [],
                        "ticket": [],
                    },
                    "access_users": {
                        "admin": [],
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
                    "fullname": "test2",
                    "id": 2,
                    "milestones": {},
                    "name": "test2",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "url_path": "test2",
                    "user": {"fullname": "PY C", "name": "pingou"},
                }
            ],
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        projects = []
        for p in data["projects"]:
            p["date_created"] = "1492020239"
            p["date_modified"] = "1492020239"
            projects.append(p)
        data["projects"] = projects
        self.assertDictEqual(data, exp)

        output2 = self.app.get(
            "/api/0/group/some_group?projects=1&acl=admin", headers=headers
        )
        self.assertListEqual(
            output.get_data(as_text=True).split("\n"),
            output2.get_data(as_text=True).split("\n"),
        )

    def test_api_view_group_w_projects_and_acl_commit(self):
        """
            Test the api_view_group method with project info and restricted
            to the commit ACL
        """

        output = self.app.get("/api/0/group/some_group?projects=1&acl=commit")
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "description": None,
            "creator": {"fullname": "PY C", "name": "pingou"},
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
            "projects": [
                {
                    "access_groups": {
                        "admin": ["some_group"],
                        "commit": [],
                        "ticket": [],
                    },
                    "access_users": {
                        "admin": [],
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
                    "fullname": "test2",
                    "id": 2,
                    "milestones": {},
                    "name": "test2",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "url_path": "test2",
                    "user": {"fullname": "PY C", "name": "pingou"},
                }
            ],
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
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
            "description": None,
            "creator": {"fullname": "PY C", "name": "pingou"},
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
            "projects": [
                {
                    "access_groups": {
                        "admin": ["some_group"],
                        "commit": [],
                        "ticket": [],
                    },
                    "access_users": {
                        "admin": [],
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
                    "fullname": "test2",
                    "id": 2,
                    "milestones": {},
                    "name": "test2",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "url_path": "test2",
                    "user": {"fullname": "PY C", "name": "pingou"},
                }
            ],
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
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
            "description": None,
            "creator": {"fullname": "PY C", "name": "pingou"},
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
            "projects": [],
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
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
            "description": None,
            "creator": {"fullname": "PY C", "name": "pingou"},
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group",
            "projects": [],
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
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
            "description": None,
            "creator": {"fullname": "PY C", "name": "pingou"},
            "members": [],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "rel-eng",
            "projects": [],
        }
        data = json.loads(output.get_data(as_text=True))
        data["date_created"] = "1492020239"
        self.assertDictEqual(data, exp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
