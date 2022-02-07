# -*- coding: utf-8 -*-

"""
 (c) 2016-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import json
import unittest
import shutil
import sys
import tempfile
import os

import pygit2
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskPrioritiestests(tests.Modeltests):
    """Tests for the behavior of priorities in pagure"""

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_ticket_with_no_priority(self, p_send_email, p_ugt):
        """Test creating a ticket without priority."""
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            # Get the CSRF token
            output = self.app.get("/test/new_issue")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertTrue(
                '<h4 class="font-weight-bold mb-4">New Issue</h4>\n'
                in output_text
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {
                "title": "Test issue",
                "issue_content": "We really should improve on this issue",
                "status": "Open",
                "csrf_token": csrf_token,
            }

            # Create the issue
            output = self.app.post(
                "/test/new_issue", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertNotIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertNotIn('<option value="1">High</option>', output_text)

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_ticket_with_priorities(self, p_send_email, p_ugt):
        """Test creating a ticket with priorities."""
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Set some priorities
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.priorities = {"1": "High", "2": "Normal"}
        self.session.add(repo)
        self.session.commit()

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            # Get the CSRF token
            output = self.app.get("/test/new_issue")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertTrue(
                '<h4 class="font-weight-bold mb-4">New Issue</h4>\n'
                in output_text
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {
                "title": "Test issue",
                "issue_content": "We really should improve on this issue",
                "status": "Open",
                "csrf_token": csrf_token,
            }

            # Create the issue
            output = self.app.post(
                "/test/new_issue", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn('<option value="1">High</option>', output_text)

    def test_update_priorities(self):
        """Test updating priorities of a repo."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Set some priorities
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.priorities, {})

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            # Get the CSRF token
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"priority_weigth": 1, "priority_title": "High"}
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            # Check the result of the action -- None, no CSRF
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(repo.priorities, {})

            data = {
                "priority_weigth": 1,
                "priority_title": "High",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            # Check the result of the action -- Priority recorded
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(repo.priorities, {"": "", "1": "High"})

            data = {
                "priority_weigth": [1, 2, 3],
                "priority_title": ["High", "Normal", "Low"],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            # Check the ordering
            self.assertTrue(
                output_text.find("High") < output_text.find("Normal")
            )
            self.assertTrue(
                output_text.find("Normal") < output_text.find("Low")
            )
            # Check the result of the action -- Priority recorded
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.priorities,
                {"": "", "1": "High", "2": "Normal", "3": "Low"},
            )

            # Check error - less weigths than titles
            data = {
                "priority_weigth": [1, 2],
                "priority_title": ["High", "Normal", "Low"],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn(
                "Priorities weights and titles are " "not of the same length",
                output_text,
            )
            # Check the result of the action -- Priorities un-changed
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.priorities,
                {"": "", "1": "High", "2": "Normal", "3": "Low"},
            )

            # Check error - weigths must be integer
            data = {
                "priority_weigth": [1, 2, "c"],
                "priority_title": ["High", "Normal", "Low"],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn("Priorities weights must be numbers", output_text)
            # Check the result of the action -- Priorities un-changed
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.priorities,
                {"": "", "1": "High", "2": "Normal", "3": "Low"},
            )

            # Check error - Twice the same priority weigth
            data = {
                "priority_weigth": [1, 2, 2],
                "priority_title": ["High", "Normal", "Low"],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn("Priority weight 2 is present 2 times", output_text)
            # Check the result of the action -- Priorities un-changed
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.priorities,
                {"": "", "1": "High", "2": "Normal", "3": "Low"},
            )

            # Check error - Twice the same priority title
            data = {
                "priority_weigth": [1, 2, 3],
                "priority_title": ["High", "Normal", "Normal"],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn("Priority Normal is present 2 times", output_text)
            # Check the result of the action -- Priorities un-changed
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.priorities,
                {"": "", "1": "High", "2": "Normal", "3": "Low"},
            )

            # Check the behavior if the project disabled the issue tracker
            settings = repo.settings
            settings["issue_tracker"] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post("/test/update/priorities", data=data)
            self.assertEqual(output.status_code, 404)

            # Check for an invalid project
            output = self.app.post("/foo/update/priorities", data=data)
            self.assertEqual(output.status_code, 404)

        # Check for a non-admin user
        settings = repo.settings
        settings["issue_tracker"] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        user.username = "ralph"
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/update/priorities", data=data)
            self.assertEqual(output.status_code, 403)

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_reset_priorities(self, p_send_email, p_ugt):
        """Test resetting the priorities of a repo."""
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Start from scrach on priorities
        repo = pagure.lib.query._get_project(self.session, "test")
        self.assertEqual(repo.priorities, {})

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            # Get the CSRF token
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            # Set some priorities
            data = {
                "priority_weigth": [1, 2, 3],
                "priority_title": ["High", "Normal", "Low"],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            # Check the result of the action -- Priority recorded
            self.session.commit()
            repo = pagure.lib.query._get_project(self.session, "test")
            self.assertEqual(
                repo.priorities,
                {"": "", "1": "High", "2": "Normal", "3": "Low"},
            )

            # Create an issue
            data = {
                "title": "Test issue",
                "issue_content": "We really should improve on this issue",
                "status": "Open",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/new_issue", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn('<option value="1">High</option>', output_text)

            # Check that the ticket *does* have priorities
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn('<option value="1">High</option>', output_text)

            # Reset the priorities
            data = {"csrf_token": csrf_token}
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            # Check that the issue list renders fine
            output = self.app.get("/test/issues")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)

            # Check that the ticket *does not* have priorities
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertNotIn('<option value="1">High</option>', output_text)

            # Check the result of the action -- Priority reset
            self.session.commit()
            repo = pagure.lib.query._get_project(self.session, "test")
            self.assertEqual(repo.priorities, {})

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_reset_priorities_None(self, p_send_email, p_ugt):
        """Test resetting the priorities of a repo."""
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Start from scrach on priorities
        repo = pagure.lib.query._get_project(self.session, "test")
        self.assertEqual(repo.priorities, {})

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            # Get the CSRF token
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            # Set some priorities
            data = {
                "priority_weigth": [1, 2, 3],
                "priority_title": ["High", "Normal", "Low"],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            # Check the result of the action -- Priority recorded
            self.session.commit()
            repo = pagure.lib.query._get_project(self.session, "test")
            self.assertEqual(
                repo.priorities,
                {"": "", "1": "High", "2": "Normal", "3": "Low"},
            )

            # Create an issue
            data = {
                "title": "Test issue",
                "issue_content": "We really should improve on this issue",
                "status": "Open",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/new_issue", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn('<option value="1">High</option>', output_text)

            # Check that the ticket *does* have priorities
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn('<option value="1">High</option>', output_text)

            # Reset the priorities
            data = {"priority": None, "csrf_token": csrf_token}
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            # Check that the issue list renders fine
            output = self.app.get("/test/issues")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)

            # Check that the ticket *does not* have priorities
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertNotIn('<option value="1">High</option>', output_text)

            # Check the result of the action -- Priority recorded
            self.session.commit()
            repo = pagure.lib.query._get_project(self.session, "test")
            self.assertEqual(repo.priorities, {})

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_set_priority_1_and_back(self):
        """Test setting the priority of a ticket to 1."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Start from scrach on priorities
        repo = pagure.lib.query._get_project(self.session, "test")
        self.assertEqual(repo.priorities, {})

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            # Get the CSRF token
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            # Set some priorities
            data = {
                "priority_weigth": [-1, 0, 1, 2, 3],
                "priority_title": [
                    "Sky Falling",
                    "Urgent",
                    "High",
                    "Normal",
                    "Low",
                ],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            # Check the result of the action -- Priority recorded
            self.session.commit()
            repo = pagure.lib.query._get_project(self.session, "test")
            self.assertEqual(
                repo.priorities,
                {
                    "": "",
                    "-1": "Sky Falling",
                    "0": "Urgent",
                    "1": "High",
                    "2": "Normal",
                    "3": "Low",
                },
            )

            # Create an issue
            data = {
                "title": "Test issue",
                "issue_content": "We really should improve on this issue",
                "status": "Open",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/new_issue", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn('<option value="1">High</option>', output_text)

            # Check that the ticket *does* have priorities
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn(
                '<option value="-1">Sky Falling</option>', output_text
            )
            self.assertIn('<option value="0">Urgent</option>', output_text)
            self.assertIn('<option value="1">High</option>', output_text)

            # Set the priority to High

            data = {"priority": "1", "csrf_token": csrf_token}

            output = self.app.post(
                "/test/issue/1/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn(
                '<option value="-1">Sky Falling</option>', output_text
            )
            self.assertIn('<option value="0">Urgent</option>', output_text)
            self.assertIn(
                '<option selected value="1">High</option>', output_text
            )

            # Reset the priority
            data = {"priority": "", "csrf_token": csrf_token}

            output = self.app.post(
                "/test/issue/1/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn(
                '<option value="-1">Sky Falling</option>', output_text
            )
            self.assertIn('<option value="0">Urgent</option>', output_text)
            self.assertIn('<option value="1">High</option>', output_text)

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_set_priority_0(self):
        """Test setting the priority of a ticket to 0."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Start from scrach on priorities
        repo = pagure.lib.query._get_project(self.session, "test")
        self.assertEqual(repo.priorities, {})

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            # Get the CSRF token
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            # Set some priorities
            data = {
                "priority_weigth": [-1, 0, 1, 2, 3],
                "priority_title": [
                    "Sky Falling",
                    "Urgent",
                    "High",
                    "Normal",
                    "Low",
                ],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            # Check the result of the action -- Priority recorded
            self.session.commit()
            repo = pagure.lib.query._get_project(self.session, "test")
            self.assertEqual(
                repo.priorities,
                {
                    "": "",
                    "-1": "Sky Falling",
                    "0": "Urgent",
                    "1": "High",
                    "2": "Normal",
                    "3": "Low",
                },
            )

            # Create an issue
            data = {
                "title": "Test issue",
                "issue_content": "We really should improve on this issue",
                "status": "Open",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/new_issue", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn('<option value="1">High</option>', output_text)

            # Check that the ticket *does* have priorities
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn(
                '<option value="-1">Sky Falling</option>', output_text
            )
            self.assertIn('<option value="0">Urgent</option>', output_text)
            self.assertIn('<option value="1">High</option>', output_text)

            # Set the priority to Urgent

            data = {"priority": "0", "csrf_token": csrf_token}

            output = self.app.post(
                "/test/issue/1/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn(
                '<option value="-1">Sky Falling</option>', output_text
            )
            self.assertIn(
                '<option selected value="0">Urgent</option>', output_text
            )
            self.assertIn('<option value="1">High</option>', output_text)

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_set_priority_minus1(self):
        """Test setting the priority of a ticket to -1."""

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Start from scrach on priorities
        repo = pagure.lib.query._get_project(self.session, "test")
        self.assertEqual(repo.priorities, {})

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            # Get the CSRF token
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            # Set some priorities
            data = {
                "priority_weigth": [-1, 0, 1, 2, 3],
                "priority_title": [
                    "Sky Falling",
                    "Urgent",
                    "High",
                    "Normal",
                    "Low",
                ],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )

            # Check the result of the action -- Priority recorded
            self.session.commit()
            repo = pagure.lib.query._get_project(self.session, "test")
            self.assertEqual(
                repo.priorities,
                {
                    "": "",
                    "-1": "Sky Falling",
                    "0": "Urgent",
                    "1": "High",
                    "2": "Normal",
                    "3": "Low",
                },
            )

            # Create an issue
            data = {
                "title": "Test issue",
                "issue_content": "We really should improve on this issue",
                "status": "Open",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/new_issue", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn('<option value="1">High</option>', output_text)

            # Check that the ticket *does* have priorities
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn(
                '<option value="-1">Sky Falling</option>', output_text
            )
            self.assertIn('<option value="0">Urgent</option>', output_text)
            self.assertIn('<option value="1">High</option>', output_text)

            # Set the priority to Sky Falling

            data = {"priority": "-1", "csrf_token": csrf_token}

            output = self.app.post(
                "/test/issue/1/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn(
                '<div class="ml-2" id="priority_plain">', output_text
            )
            self.assertIn(
                '<option selected value="-1">Sky Falling</option>', output_text
            )
            self.assertIn('<option value="0">Urgent</option>', output_text)
            self.assertIn('<option value="1">High</option>', output_text)

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_default_priority(self):
        """Test updating the default priority of a repo."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Check the default priorities
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.priorities, {})
        self.assertEqual(repo.default_priority, None)

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            csrf_token = self.get_csrf()

            # Set some priorities
            data = {
                "priority_weigth": [1, 2, 3],
                "priority_title": ["High", "Normal", "Low"],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            # Check the ordering
            self.assertTrue(
                output_text.find("High") < output_text.find("Normal")
            )
            self.assertTrue(
                output_text.find("Normal") < output_text.find("Low")
            )
            # Check the result of the action -- Priority recorded
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.priorities,
                {"": "", "1": "High", "2": "Normal", "3": "Low"},
            )

            # Try setting the default priority  --  no csrf
            data = {"priority": "High"}
            output = self.app.post(
                "/test/update/default_priority",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            # Check the result of the action -- default_priority no change
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(repo.default_priority, None)

            # Try setting the default priority
            data = {"priority": "High", "csrf_token": csrf_token}
            output = self.app.post(
                "/test/update/default_priority",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn("Default priority set " "to High", output_text)
            # Check the result of the action -- default_priority no change
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(repo.default_priority, "High")

            # Try setting a wrong default priority
            data = {"priority": "Smooth", "csrf_token": csrf_token}
            output = self.app.post(
                "/test/update/default_priority",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            # Check the result of the action -- default_priority no change
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(repo.default_priority, "High")

            # reset the default priority
            data = {"csrf_token": csrf_token, "priority": ""}
            output = self.app.post(
                "/test/update/default_priority",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn("Default priority reset", output_text)
            # Check the result of the action -- default_priority no change
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(repo.default_priority, None)

            # Check the behavior if the project disabled the issue tracker
            settings = repo.settings
            settings["issue_tracker"] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post("/test/update/default_priority", data=data)
            self.assertEqual(output.status_code, 404)

            # Check for an invalid project
            output = self.app.post("/foo/update/default_priority", data=data)
            self.assertEqual(output.status_code, 404)

        # Check for a non-admin user
        settings = repo.settings
        settings["issue_tracker"] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        user.username = "ralph"
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/update/default_priority", data=data)
            self.assertEqual(output.status_code, 403)

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_default_priority_reset_when_updating_priorities(self):
        """Test updating the default priority of a repo when updating the
        priorities.
        """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Check the default priorities
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.priorities, {})
        self.assertEqual(repo.default_priority, None)

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            csrf_token = self.get_csrf()

            # Set some priorities
            data = {
                "priority_weigth": [1, 2, 3],
                "priority_title": ["High", "Normal", "Low"],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            # Check the ordering
            self.assertTrue(
                output_text.find("High") < output_text.find("Normal")
            )
            self.assertTrue(
                output_text.find("Normal") < output_text.find("Low")
            )
            # Check the result of the action -- Priority recorded
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.priorities,
                {"": "", "1": "High", "2": "Normal", "3": "Low"},
            )

            # Try setting the default priority
            data = {"priority": "High", "csrf_token": csrf_token}
            output = self.app.post(
                "/test/update/default_priority",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn("Default priority set " "to High", output_text)
            # Check the result of the action -- default_priority no change
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(repo.default_priority, "High")

            # Remove the Hight priority
            data = {
                "priority_weigth": [1, 2],
                "priority_title": ["Normal", "Low"],
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/priorities", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn("Priorities updated", output_text)
            self.assertIn(
                "Default priority reset "
                "as it is no longer one of set priorities.",
                output_text,
            )
            # Check the ordering
            self.assertTrue(
                output_text.find("Normal") < output_text.find("Low")
            )
            # Check the result of the action -- Priority recorded
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.priorities, {"": "", "1": "Normal", "2": "Low"}
            )
            # Default priority is now None
            self.assertIsNone(repo.default_priority)

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_default_priority_on_new_ticket(self):
        """Test updating the default priority of a repo."""
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Set some priority and the default one
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.priorities = {"1": "High", "2": "Normal"}
        repo.default_priority = "Normal"
        self.session.add(repo)
        self.session.commit()

        # Check the default priorities
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.priorities, {"1": "High", "2": "Normal"})
        self.assertEqual(repo.default_priority, "Normal")

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):

            csrf_token = self.get_csrf()

            data = {
                "title": "Test issue",
                "issue_content": "We really should improve on this issue",
                "status": "Open",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/new_issue", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.issues), 1)
        self.assertEqual(repo.issues[0].priority, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
