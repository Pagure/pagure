# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import sys
import os

import pagure_messages
from mock import ANY, patch, MagicMock
from fedora_messaging import testing

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests


class PagureFlaskDeleteRepotests(tests.Modeltests):
    """ Tests for deleting a project in pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskDeleteRepotests, self).setUp()

        # Create some projects
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))
        self.session.commit()

        # Create all the git repos
        tests.create_projects_git(os.path.join(self.path, "repos"))
        tests.create_projects_git(os.path.join(self.path, "repos", "docs"))
        tests.create_projects_git(
            os.path.join(self.path, "repos", "tickets"), bare=True
        )
        tests.create_projects_git(
            os.path.join(self.path, "repos", "requests"), bare=True
        )

        project = pagure.lib.query.get_authorized_project(
            self.session, project_name="test"
        )
        self.assertIsNotNone(project)
        # Ensure the project isn't read-only
        project.read_only = False
        self.session.add(project)
        self.session.commit()

        # Create a fork
        task = pagure.lib.query.fork_project(
            session=self.session, user="pingou", repo=project
        )
        task.get()

        # Ensure everything was correctly created
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 4)

    @patch.dict("pagure.config.config", {"ENABLE_DEL_PROJECTS": False})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_delete_repo_when_turned_off(self):
        """ Test the delete_repo endpoint for a fork when only deleting main
        project is forbidden.
        """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/delete", follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 4)

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_delete_button_present(self):
        """ Test that the delete button is present when deletions are
        allowed.
        """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<form action="/test/delete"', output.get_data(as_text=True)
            )
            self.assertIn(
                "&nbsp; Delete the test project", output.get_data(as_text=True)
            )

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 4)

    @patch.dict("pagure.config.config", {"ENABLE_DEL_PROJECTS": False})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_delete_button_absent(self):
        """ Test that the delete button is absent when deletions are not
        allowed.
        """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                '<form action="/test/delete"', output.get_data(as_text=True)
            )
            self.assertNotIn(
                "&nbsp; Delete the test project", output.get_data(as_text=True)
            )

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 4)

    @patch.dict("pagure.config.config", {"ENABLE_DEL_PROJECTS": False})
    @patch.dict("pagure.config.config", {"ENABLE_DEL_FORKS": True})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_delete_fork_when_project_off_refreshing(self):
        """ Test the delete_repo endpoint for a fork when only deleting main
        project is forbidden but the fork is being refreshed in the backend
        """
        project = pagure.lib.query.get_authorized_project(
            self.session, project_name="test", user="pingou"
        )
        self.assertIsNotNone(project)
        # Ensure the project isn't read-only
        project.read_only = True
        self.session.add(project)
        self.session.commit()

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                "/fork/pingou/test/delete", follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "The ACLs of this project "
                "are being refreshed in the backend this prevents the "
                "project from being deleted. Please wait for this task to "
                "finish before trying again. Thanks!",
                output.get_data(as_text=True),
            )

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 4)

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    @patch.dict("pagure.config.config", {"ENABLE_DEL_PROJECTS": False})
    @patch.dict("pagure.config.config", {"ENABLE_DEL_FORKS": True})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_delete_fork_when_project_off(self):
        """ Test the delete_repo endpoint for a fork when only deleting main
        project is forbidden.
        """
        project = pagure.lib.query.get_authorized_project(
            self.session, project_name="test", user="pingou"
        )
        self.assertIsNotNone(project)
        # Ensure the project isn't read-only
        project.read_only = False
        self.session.add(project)
        self.session.commit()

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            with testing.mock_sends(
                pagure_messages.ProjectDeletedV1(
                    topic="pagure.project.deleted",
                    body={
                        "project": {
                            "id": 4,
                            "name": "test",
                            "fullname": "forks/pingou/test",
                            "url_path": "fork/pingou/test",
                            "description": "test project #1",
                            "namespace": None,
                            "parent": {
                                "id": 1,
                                "name": "test",
                                "fullname": "test",
                                "url_path": "test",
                                "description": "test project #1",
                                "namespace": None,
                                "parent": None,
                                "date_created": ANY,
                                "date_modified": ANY,
                                "user": {
                                    "name": "pingou",
                                    "fullname": "PY C",
                                    "url_path": "user/pingou",
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
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "url_path": "user/pingou",
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
                            "close_status": [],
                            "milestones": {},
                        },
                        "agent": "pingou",
                    },
                )
            ):
                output = self.app.post(
                    "/fork/pingou/test/delete", follow_redirects=True
                )
                self.assertEqual(output.status_code, 200)

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 3)

    @patch.dict("pagure.config.config", {"ENABLE_DEL_PROJECTS": False})
    @patch.dict("pagure.config.config", {"ENABLE_DEL_FORKS": False})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_delete_fork_when_fork_and_project_off(self):
        """ Test the delete_repo endpoint for a fork when deleting fork and
        project is forbidden.
        """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                "/fork/pingou/test/delete", follow_redirects=True
            )
            self.assertEqual(output.status_code, 404)

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 4)

    @patch.dict("pagure.config.config", {"ENABLE_DEL_PROJECTS": False})
    @patch.dict("pagure.config.config", {"ENABLE_DEL_FORKS": False})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_delete_fork_button_absent(self):
        """ Test that the delete button is absent when deletions are not
        allowed.
        """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/fork/pingou/test/settings")
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                '<form action="/fork/pingou/test/delete"',
                output.get_data(as_text=True),
            )
            self.assertNotIn(
                "&nbsp; Delete the forks/pingou/test project",
                output.get_data(as_text=True),
            )

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 4)

    @patch.dict("pagure.config.config", {"ENABLE_DEL_PROJECTS": False})
    @patch.dict("pagure.config.config", {"ENABLE_DEL_FORKS": True})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_delete_fork_button_fork_del_allowed(self):
        """ Test that the delete button is present when deletions of projects
        is not allowed but deletions of forks is.
        """

        project = pagure.lib.query.get_authorized_project(
            self.session, project_name="test", user="pingou"
        )
        self.assertIsNotNone(project)
        # Ensure the project isn't read-only
        project.read_only = False
        self.session.add(project)
        self.session.commit()

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/fork/pingou/test/settings")
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<form action="/fork/pingou/test/delete"',
                output.get_data(as_text=True),
            )
            self.assertIn(
                "&nbsp; Delete the forks/pingou/test project",
                output.get_data(as_text=True),
            )

        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 4)

    @patch.dict("pagure.config.config", {"ENABLE_DEL_PROJECTS": False})
    @patch.dict("pagure.config.config", {"ENABLE_DEL_FORKS": True})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_delete_fork_button_fork_del_allowed_read_only(self):
        """ Test that the delete button is absent when deletions of projects
        is not allowed but deletions of forks is but fork is still being
        processed.
        """

        project = pagure.lib.query.get_authorized_project(
            self.session, project_name="test", user="pingou"
        )
        self.assertIsNotNone(project)
        # Ensure the project is read-only
        project.read_only = True
        self.session.add(project)
        self.session.commit()

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/fork/pingou/test/settings")
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                '<form action="/fork/pingou/test/delete"',
                output.get_data(as_text=True),
            )
            self.assertIn(
                "title=\"Action disabled while project's ACLs are being "
                'refreshed">',
                output.get_data(as_text=True),
            )
            self.assertIn(
                "&nbsp; Delete the forks/pingou/test project",
                output.get_data(as_text=True),
            )
