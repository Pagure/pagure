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
from mock import patch

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskRoadmaptests(tests.Modeltests):
    """ Tests for the pagure's roadmap """

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_ticket_with_no_roadmap(self, p_send_email, p_ugt):
        """ Test creating a ticket without roadmap. """
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

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_ticket_with_roadmap(self, p_send_email, p_ugt):
        """ Test creating a ticket with roadmap. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Set some milestone
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        repo.milestone = {"v1.0": "", "v2.0": "Tomorrow!"}
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

            # Mark the ticket for the roadmap
            data = {"tag": "roadmap", "csrf_token": csrf_token}
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

    def test_update_milestones(self):
        """ Test updating milestones of a repo. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Set some milestones
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.milestones, {})

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

            data = {
                "milestones": 1,
                "milestone_1_name": "1",
                "milestone_1_date": "Tomorrow",
            }
            output = self.app.post(
                "/test/update/milestones", data=data, follow_redirects=True
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
            self.assertEqual(repo.milestones, {})

            data = {
                "milestones": 1,
                "milestone_1_name": "1",
                "milestone_date": "",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/milestones", data=data, follow_redirects=True
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
            self.assertIn("Milestones updated", output_text)

            # Check the result of the action -- Milestones recorded
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.milestones, {"1": {"active": False, "date": None}}
            )

            data = {
                "milestones": [1, 2],
                "milestone_1_name": "v1.0",
                "milestone_2_name": "v2.0",
                "milestone_1_date": "Tomorrow",
                "milestone_2_date": "",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/milestones", data=data, follow_redirects=True
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
            self.assertIn("Milestones updated", output_text)
            # Check the result of the action -- Milestones recorded
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.milestones,
                {
                    "v1.0": {"active": False, "date": "Tomorrow"},
                    "v2.0": {"active": False, "date": None},
                },
            )

            # Check error - less milestones than dates
            data = {
                "milestones": [1, 2],
                "milestone_1_name": "v1.0",
                "milestone_2_name": "v2.0",
                "milestone_1_date": "Tomorrow",
                "milestone_2_date": "Next week",
                "milestone_3_date": "Next Year",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/milestones", data=data, follow_redirects=True
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
            # Check the result of the action -- Milestones un-changed
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.milestones,
                {
                    "v1.0": {"active": False, "date": "Tomorrow"},
                    "v2.0": {"active": False, "date": "Next week"},
                },
            )

            # Check error - Twice the same milestone
            data = {
                "milestones": [1, 2, 3],
                "milestone_1_name": "v1.0",
                "milestone_2_name": "v2.0",
                "milestone_3_name": "v2.0",
                "milestone_1_date": "Tomorrow",
                "milestone_2_date": "Next week",
                "milestone_3_date": "Next Year",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/milestones", data=data, follow_redirects=True
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
                "Milestone v2.0 is present multiple times",
                "Milestone v2.0 is present multiple times",
                output_text,
            )
            # Check the result of the action -- Milestones un-changed
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.milestones,
                {
                    "v1.0": {"active": False, "date": "Tomorrow"},
                    "v2.0": {"active": False, "date": "Next week"},
                },
            )

            # Check error - Twice the same date
            data = {
                "milestones": [1, 2, 3],
                "milestone_1_name": "v1.0",
                "milestone_2_name": "v2.0",
                "milestone_3_name": "v3.0",
                "milestone_1_date": "Tomorrow",
                "milestone_2_date": "Next week",
                "milestone_3_date": "Next week",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/milestones", data=data, follow_redirects=True
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
            self.assertIn("Milestones updated", output_text)
            # Check the result of the action -- Milestones updated
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.milestones,
                {
                    "v1.0": {"active": False, "date": "Tomorrow"},
                    "v2.0": {"active": False, "date": "Next week"},
                    "v3.0": {"active": False, "date": "Next week"},
                },
            )

            # Check for an invalid project
            output = self.app.post("/foo/update/milestones", data=data)
            self.assertEqual(output.status_code, 404)

            # Check the behavior if the project disabled the issue tracker
            settings = repo.settings
            settings["issue_tracker"] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post("/test/update/milestones", data=data)
            self.assertEqual(output.status_code, 404)

        # Check for a non-admin user
        settings = repo.settings
        settings["issue_tracker"] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        user.username = "ralph"
        with tests.user_set(self.app.application, user):
            output = self.app.post("/test/update/milestones", data=data)
            self.assertEqual(output.status_code, 403)

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_milestones_without_dates(self, p_send_email, p_ugt):
        """ Test creating two milestones with no dates. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            # Get the CSRF token
            output = self.app.get("/test/settings")
            output_text = output.get_data(as_text=True)
            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {
                "milestones": [1, 2],
                "milestone_1_name": "v1.0",
                "milestone_2_name": "v2.0",
                "milestone_1_date": "",
                "milestone_2_date": "",
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/milestones", data=data, follow_redirects=True
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
            self.assertIn("Milestones updated", output_text)
            # Check the result of the action -- Milestones recorded
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(
                self.session, "test"
            )
            self.assertEqual(
                repo.milestones,
                {
                    "v1.0": {"active": False, "date": None},
                    "v2.0": {"active": False, "date": None},
                },
            )

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_roadmap_ui(self, p_send_email, p_ugt):
        """ Test viewing the roadmap of a repo. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_update_milestones()

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

            # Create an unplanned milestone
            data = {
                "milestones": [1, 2, 3],
                "milestone_1_name": "v1.0",
                "milestone_2_name": "v2.0",
                "milestone_3_name": "unplanned",
                "milestone_1_date": "Tomorrow",
                "milestone_2_date": "",
                "milestone_3_date": "",
                "milestone_1_active": True,
                "milestone_2_active": True,
                "milestone_3_active": True,
                "csrf_token": csrf_token,
            }
            output = self.app.post(
                "/test/update/milestones", data=data, follow_redirects=True
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
            self.assertIn("Milestones updated", output_text)

            # Check the result of the action -- Milestones recorded
            self.session.commit()
            repo = pagure.lib.query._get_project(self.session, "test")
            self.assertEqual(
                repo.milestones,
                {
                    "unplanned": {"active": True, "date": None},
                    "v1.0": {"active": True, "date": "Tomorrow"},
                    "v2.0": {"active": True, "date": None},
                },
            )

            # Create the issues
            for cnt in range(6):
                cnt += 1
                data = {
                    "title": "Test issue %s" % cnt,
                    "issue_content": "We really should improve on this "
                    "issue %s" % cnt,
                    "csrf_token": csrf_token,
                }

                output = self.app.post(
                    "/test/new_issue", data=data, follow_redirects=True
                )
                self.assertEqual(output.status_code, 200)
                output_text = output.get_data(as_text=True)
                self.assertIn(
                    "<title>Issue #{0}: Test issue {0} - test - "
                    "Pagure</title>".format(cnt),
                    output_text,
                )
                self.assertIn(
                    '<a class="btn btn-outline-secondary btn-sm border-0" '
                    'href="/test/issue/%s/edit" title="Edit this issue">'
                    % cnt,
                    output_text,
                )

                # Mark the ticket for the roadmap
                mstone = "v%s.0" % cnt
                if cnt >= 3:
                    if (cnt % 3) == 0:
                        mstone = "unplanned"
                    else:
                        mstone = "v%s.0" % (cnt % 3)
                data = {"milestone": mstone, "csrf_token": csrf_token}
                output = self.app.post(
                    "/test/issue/%s/update" % cnt,
                    data=data,
                    follow_redirects=True,
                )
                self.assertEqual(output.status_code, 200)
                output_text = output.get_data(as_text=True)
                self.assertIn(
                    "<title>Issue #{0}: Test issue {0} - test - "
                    "Pagure</title>".format(cnt),
                    output_text,
                )
                self.assertIn(
                    '<a class="btn btn-outline-secondary btn-sm border-0" '
                    'href="/test/issue/%s/edit" title="Edit this issue">'
                    % cnt,
                    output_text,
                )
                self.assertIn(
                    "Issue set to the milestone: %s" % mstone, output_text
                )
                self.assertIn(
                    '<div class="ml-2" id="milestone_plain">', output_text
                )
                self.assertIn(
                    '<a href="/test/roadmap/%s/">' % mstone, output_text
                )

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Mark ticket #1 as Fixed
        for iid in [1, 4]:
            ticket = pagure.lib.query.search_issues(
                self.session, repo, issueid=iid
            )
            ticket.status = "Closed"
            ticket.close_status = "Fixed"
            self.session.add(ticket)
            self.session.commit()

        # test the roadmap view
        output = self.app.get("/test/roadmap")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<span class="fa fa-fw fa-map-signs"></span>\n'
            '                            <span class="font'
            '-weight-bold">v1.0</span>',
            output_text,
        )
        self.assertIn(
            '<span class="fa fa-fw fa-map-signs"></span>\n'
            '                            <span class="font'
            '-weight-bold">unplanned</span>',
            output_text,
        )
        self.assertIn(
            'title="100% Completed | 2 Closed Issues | 0 Open Issues"\n',
            output_text,
        )
        self.assertIn(
            'title="0% Completed | 0 Closed Issues | 2 Open Issues"\n',
            output_text,
        )
        self.assertIn(
            'title="0% Completed | 0 Closed Issues | 2 Open Issues"\n',
            output_text,
        )

        # test the roadmap view for a specific milestone
        output = self.app.get("/test/roadmap/v2.0/")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<span class="fa fa-fw fa-exclamation-circle"></span> 2 Open\n',
            output_text,
        )
        self.assertIn(
            '<span class="fa fa-fw fa-exclamation-circle"></span> 0 Closed\n',
            output_text,
        )
        self.assertIn('<a class="notblue" href="/test/issue/2">', output_text)
        self.assertEquals(
            output_text.count('<a class="notblue" href="/test/issue/2">'), 1
        )

        # test the roadmap view for errors
        output = self.app.get("/foo/roadmap")
        self.assertEqual(output.status_code, 404)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        settings = repo.settings
        settings["issue_tracker"] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.get("/test/roadmap", data=data)
        self.assertEqual(output.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
