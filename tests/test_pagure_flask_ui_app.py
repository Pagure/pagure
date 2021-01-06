# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import unittest
import shutil
import sys
import tempfile
import os

import six
import json
import pygit2
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests


class PagureFlaskApptests(tests.Modeltests):
    """ Tests for flask app controller of pagure """

    def test_watch_list(self):
        """ Test for watch list of a user """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/", follow_redirects=True)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="text-center">You have no Projects</div>',
                output_text,
            )

            tests.create_projects(self.session)

            output = self.app.get("/", follow_redirects=True)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>',
                output_text,
            )

    def test_view_users(self):
        """ Test the view_users endpoint. """

        output = self.app.get("/users/?page=abc")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<h3 class="mb-3 font-weight-bold">\n      Users '
            '<span class="badge badge-secondary">2</span>',
            output_text,
        )
        self.assertIn(
            '<a href="/user/pingou">\n                  '
            '<div class="nowrap"><strong>pingou</strong>',
            output_text,
        )
        self.assertIn(
            '<a href="/user/foo">\n                  '
            '<div class="nowrap"><strong>foo</strong>',
            output_text,
        )

    @patch.dict("pagure.config.config", {"ITEM_PER_PAGE": 2})
    def test_view_user_repo_cnt(self):
        """ Test the repo counts on the view_user endpoint. """
        tests.create_projects(self.session)
        self.gitrepos = tests.create_projects_git(
            pagure.config.config["GIT_FOLDER"]
        )

        output = self.app.get("/user/pingou")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  3
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

    def test_view_user(self):
        """ Test the view_user endpoint. """

        output = self.app.get("/user/pingou?repopage=abc&forkpage=def")
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

        tests.create_projects(self.session)
        self.gitrepos = tests.create_projects_git(
            pagure.config.config["GIT_FOLDER"]
        )

        output = self.app.get("/user/pingou?repopage=abc&forkpage=def")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  3
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
        self.assertNotIn(
            '<a class="page-link" href="#" tabindex="-1">page 1 of 2</a>',
            output_text,
        )

    @patch.dict(
        "pagure.config.config",
        {
            "PAGURE_ADMIN_USERS": ["pingou"],
            "ALLOW_ADMIN_IGNORE_EXISTING_REPOS": True,
        },
    )
    def test_adopt_repos(self):
        """ Test the new_project endpoint with existing git repo. """
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {
                "csrf_token": self.get_csrf(),
                "name": "test",
                "description": "Project #1",
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("The main repo test.git already exists", output_text)

            data["ignore_existing_repos"] = "y"
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Alice Author", output_text)

    @patch.dict(
        "pagure.config.config",
        {"PAGURE_ADMIN_USERS": [], "USERS_IGNORE_EXISTING_REPOS": ["pingou"]},
    )
    def test_adopt_repos_non_admin(self):
        """ Test the new_project endpoint with existing git repo for non-admins. """
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {
                "csrf_token": self.get_csrf(),
                "name": "test",
                "description": "Project #1",
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("The main repo test.git already exists", output_text)

            data["ignore_existing_repos"] = "y"
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Alice Author", output_text)

    @patch.dict(
        "pagure.config.config",
        {"PAGURE_ADMIN_USERS": [], "USERS_IGNORE_EXISTING_REPOS": []},
    )
    def test_adopt_repos_not_allowed(self):
        """ Test the new_project endpoint with existing git repo for no access. """
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test.git")
        )

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {
                "csrf_token": self.get_csrf(),
                "name": "test",
                "description": "Project #1",
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("The main repo test.git already exists", output_text)

            data["ignore_existing_repos"] = "y"
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("The main repo test.git already exists", output_text)

    @patch.dict("pagure.config.config", {"PROJECT_NAME_REGEX": "^1[a-z]*$"})
    def test_new_project_diff_regex(self):
        """ Test the new_project endpoint with a different regex. """
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)

            csrf_token = self.get_csrf(output=output)

            data = {
                "description": "Project #1",
                "name": "project-1",
                "csrf_token": csrf_token,
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<title>New project - Pagure</title>", output_text)
            self.assertIn("<strong>Create new Project</strong>", output_text)
            self.assertIn(
                "<small>\n            Invalid input.&nbsp;\n"
                "          </small>",
                output_text,
            )

    @patch.dict("pagure.config.config", {"PRIVATE_PROJECTS": True})
    def test_new_project_private(self):
        """ Test the new_project endpoint for a private project. """
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "foo", "project#1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self.path, "repos", "tickets", "foo", "project#1.git"
                )
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self.path, "repos", "docs", "foo", "project#1.git"
                )
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self.path, "repos", "requests", "foo", "project#1.git"
                )
            )
        )

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<strong>Create new Project</strong>",
                output.get_data(as_text=True),
            )

            csrf_token = self.get_csrf(output=output)

            data = {"description": "Project #1", "private": True}

            output = self.app.post("/new/", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)
            self.assertIn(
                "<small>\n            This field is required.&nbsp;\n"
                "          </small>",
                output_text,
            )

            data["name"] = "project-1"
            output = self.app.post("/new/", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)
            self.assertNotIn(
                "<small>\n            This field is required.&nbsp;\n"
                "          </small>",
                output_text,
            )

            data["csrf_token"] = csrf_token
            output = self.app.post("/new/", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)
            self.assertIn("No user " "&#34;username&#34; found", output_text)

        user.username = "foo"
        with tests.user_set(self.app.application, user):
            data["csrf_token"] = csrf_token
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo my-3">\nProject #1', output_text
            )
            self.assertIn("<p>This repo is brand new!</p>", output_text)
            self.assertIn(
                "<title>Overview - foo/project-1 - Pagure</title>", output_text
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        projects = pagure.lib.query.search_projects(self.session, private=True)
        self.assertEqual(len(projects), 1)
        self.assertTrue(
            os.path.exists(
                os.path.join(self.path, "repos", "foo", "project-1.git")
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.path, "repos", "tickets", "foo", "project-1.git"
                )
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.path, "repos", "docs", "foo", "project-1.git"
                )
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.path, "repos", "requests", "foo", "project-1.git"
                )
            )
        )

    def test_non_ascii_new_project(self):
        """ Test the new_project endpoint with a non-ascii project. """
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(
            os.path.exists(os.path.join(self.path, "repos", "project-1.git"))
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "tickets", "project-1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "docs", "project-1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "requests", "project-1.git")
            )
        )

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {
                "description": "Prõjéctö #1",
                "name": "project-1",
                "csrf_token": csrf_token,
                "create_readme": True,
            }
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo my-3">\nPrõjéctö #1', output_text
            )
            self.assertIn(
                """<section class="readme">
              <div class="markdown"><h1>project-1</h1>
<p>Prõjéctö #1</p></div>
            </section>""",
                output_text,
            )

            data = {
                "description": "Мой первый суперский репозиторий",
                "name": "project-2",
                "csrf_token": csrf_token,
                "create_readme": True,
            }
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo my-3">\nМой первый суперский репозиторий',
                output_text,
            )
            self.assertIn(
                """<section class="readme">
              <div class="markdown"><h1>project-2</h1>
<p>Мой первый суперский репозиторий</p></div>
            </section>""",
                output_text,
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 2)
        for project in ["project-1", "project-2"]:
            self.assertTrue(
                os.path.exists(
                    os.path.join(self.path, "repos", "%s.git" % project)
                )
            )
            self.assertTrue(
                os.path.exists(
                    os.path.join(
                        self.path, "repos", "tickets", "%s.git" % project
                    )
                )
            )
            self.assertTrue(
                os.path.exists(
                    os.path.join(
                        self.path, "repos", "docs", "%s.git" % project
                    )
                )
            )
            self.assertTrue(
                os.path.exists(
                    os.path.join(
                        self.path, "repos", "requests", "%s.git" % project
                    )
                )
            )

    @patch("pygit2.init_repository", wraps=pygit2.init_repository)
    def test_new_project_with_template(self, pygit2init):
        """Test the new_project endpoint for a new project with a template set."""
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(
            os.path.exists(os.path.join(self.path, "repos", "project-1.git"))
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "tickets", "project-1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "docs", "project-1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "requests", "project-1.git")
            )
        )

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<strong>Create new Project</strong>",
                output.get_data(as_text=True),
            )

            csrf_token = self.get_csrf(output=output)

            data = {
                "description": "test",
                "name": "project-1",
                "csrf_token": csrf_token,
                "create_readme": True,
            }
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo my-3">\ntest',
                output.get_data(as_text=True),
            )

            self.assertEqual(pygit2init.call_count, 4)
            pygit2init.assert_any_call(
                "%s/repos/project-1.git" % self.path,
                bare=True,
                template_path=None,
            )

            path = os.path.join(self.path, "repos", "project-1.git")
            with patch.dict(
                "pagure.config.config", {"PROJECT_TEMPLATE_PATH": path}
            ):
                data = {
                    "description": "test2",
                    "name": "project-2",
                    "csrf_token": csrf_token,
                    "create_readme": True,
                }
                output = self.app.post(
                    "/new/", data=data, follow_redirects=True
                )
                self.assertEqual(output.status_code, 200)
                self.assertIn(
                    '<div class="projectinfo my-3">\ntest2',
                    output.get_data(as_text=True),
                )

            self.assertEqual(pygit2init.call_count, 8)
            pygit2init.assert_any_call(
                "%s/repos/project-2.git" % self.path,
                bare=True,
                template_path="%s/repos/project-1.git" % self.path,
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 2)
        for project in ["project-1", "project-2"]:
            self.assertTrue(
                os.path.exists(
                    os.path.join(self.path, "repos", "%s.git" % project)
                )
            )
            self.assertTrue(
                os.path.exists(
                    os.path.join(
                        self.path, "repos", "tickets", "%s.git" % project
                    )
                )
            )
            self.assertTrue(
                os.path.exists(
                    os.path.join(
                        self.path, "repos", "docs", "%s.git" % project
                    )
                )
            )
            self.assertTrue(
                os.path.exists(
                    os.path.join(
                        self.path, "repos", "requests", "%s.git" % project
                    )
                )
            )

    @patch("pagure.ui.app.admin_session_timedout")
    def test_user_settings(self, ast):
        """ Test the user_settings endpoint. """
        ast.return_value = False

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/")
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                "<h2>Page not found (404)</h2>", output.get_data(as_text=True)
            )

        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output_text
            )

            ast.return_value = True
            output = self.app.get("/settings/")
            self.assertEqual(output.status_code, 302)

    @patch("pagure.decorators.admin_session_timedout")
    def test_add_user_sshkey(self, ast):
        """ Test the add_user_sshkey endpoint. """
        ast.return_value = False

        # User not logged in
        output = self.app.get("/settings/")
        self.assertEqual(output.status_code, 302)

        ast.return_value = False

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Add SSH key", output_text)

            csrf_token = self.get_csrf(output=output)

            data = {"ssh_key": "asdf"}

            # No CSRF token
            output = self.app.post(
                "/settings/usersettings/addkey",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Add SSH key", output_text)

            data["csrf_token"] = csrf_token

            # First, invalid SSH key
            output = self.app.post(
                "/settings/usersettings/addkey",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Add SSH key", output_text)
            self.assertIn("SSH key invalid", output_text)

            # Next up, multiple SSH keys
            data[
                "ssh_key"
            ] = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q==\nssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q=="
            output = self.app.post(
                "/settings/usersettings/addkey",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Please add single SSH keys.", output_text)

            # Now, a valid SSH key
            data[
                "ssh_key"
            ] = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q=="
            output = self.app.post(
                "/settings/usersettings/addkey",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertIn("SSH key added", output_text)
            self.assertNotIn("Push Access", output_text)

            # And now, adding the same key
            output = self.app.post(
                "/settings/usersettings/addkey",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("SSH key already exists", output_text)

            # And next, a key with push access
            data[
                "ssh_key"
            ] = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQC9Xwc2RDzPBhlEDARfHldGjudIVoa04tqT1JVKGQmyllTFz7Rb8CngQL3e7zyNzotnhwYKHdoiLlPkVEiDee4dWMUe48ilqId+FJZQGhyv8fu4BoFdE1AJUVylzmltbLg14VqG5gjTpXgtlrEva9arKwBMHJjRYc8ScaSn3OgyQw=="
            output = self.app.post(
                "/settings/usersettings/addkey",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertIn("SSH key added", output_text)

    @patch("pagure.decorators.admin_session_timedout")
    def test_remove_user_sshkey(self, ast):
        """ Test the remove_sshkey endpoint. """
        ast.return_value = False

        user = tests.FakeUser()
        # User not logged in
        output = self.app.post("/settings/usersettings/removekey/1")
        self.assertEqual(output.status_code, 302)

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            data = {"csrf_token": self.get_csrf()}

            output = self.app.post(
                "/settings/usersettings/removekey/1",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertIn("SSH key does not exist", output_text)

        # Add a deploy key to a project
        pingou = pagure.lib.query.get_user(self.session, "pingou")
        msg = pagure.lib.query.add_sshkey_to_project_or_user(
            session=self.session,
            ssh_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q==",
            user=pingou,
            pushaccess=True,
            creator=pingou,
        )
        self.session.commit()
        self.assertEqual(msg, "SSH key added")

        with tests.user_set(self.app.application, user):
            output = self.app.post(
                "/settings/usersettings/removekey/1", follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertNotIn("SSH key removed", output_text)

            data = {"csrf_token": self.get_csrf()}
            output = self.app.post(
                "/settings/usersettings/removekey/1",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertIn("SSH key removed", output_text)

    def patched_commit_exists(user, namespace, repo, githash):
        """Patched version of pagure.pfmarkdown._commit_exists to enforce
        returning true on some given hash without having us actually check
        the git repos.
        """
        if githash in [
            "9364354",
            "9364354a",
            "9364354a4555ba17aa60f0dc844d70b74eb1aecd",
        ]:
            return True
        else:
            return False

    @patch(
        "pagure.pfmarkdown._commit_exists",
        MagicMock(side_effect=patched_commit_exists),
    )
    def test_patched_markdown_preview(self):
        """ Test the markdown_preview endpoint. """

        data = {"content": "test\n----\n\n * 1\n * item 2"}

        # CSRF missing
        output = self.app.post("/markdown/", data=data)
        self.assertEqual(output.status_code, 400)

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output_text
            )

            csrf_token = self.get_csrf(output=output)

        # With CSRF
        data["csrf_token"] = csrf_token
        output = self.app.post("/markdown/", data=data)
        self.assertEqual(output.status_code, 200)
        exp = """<div class="markdown"><h2>test</h2>
<ul>
<li>1</li>
<li>item 2</li>
</ul></div>"""
        self.assertEqual(output.get_data(as_text=True), exp)

        tests.create_projects(self.session)
        texts = [
            "pingou committed on test#9364354a4555ba17aa60f0dc844d70b74eb1aecd",
            "Cf commit 936435",  # 6 chars - not long enough
            "Cf commit 9364354",  # 7 chars - long enough
            "Cf commit 9364354a",  # 8 chars - still long enough
            "Cf commit 9364354a4555ba17aa60f0dc844d70b74eb1aecd",  # 40 chars
        ]
        expected = [
            # 'pingou committed on test#9364354a4555ba17aa60f0dc844d70b74eb1aecd',
            '<div class="markdown"><p>pingou committed on <a href="/test/c/9364354a4555ba17aa60f0dc844d70b74eb1aecd" '
            'title="Commit 9364354a4555ba17aa60f0dc844d70b74eb1aecd"'
            ">test#9364354a4555ba17aa60f0dc844d70b74eb1aecd</a></p></div>",
            # 'Cf commit 936435',
            '<div class="markdown"><p>Cf commit 936435</p></div>',
            # 'Cf commit 9364354',
            #'<p>Cf commit 9364354</p>',
            '<div class="markdown"><p>Cf commit <a href="/test/c/9364354" '
            'title="Commit 9364354">9364354</a></p></div>',
            # 'Cf commit 9364354a',
            '<div class="markdown"><p>Cf commit <a href="/test/c/9364354a" '
            'title="Commit 9364354a">9364354</a></p></div>',
            # 'Cf commit 9364354a4555ba17aa60f0dc844d70b74eb1aecd',
            '<div class="markdown"><p>Cf commit <a href="/test/c/9364354a4555ba17aa60f0dc844d70b74eb1aecd" '
            'title="Commit 9364354a4555ba17aa60f0dc844d70b74eb1aecd"'
            ">9364354</a></p></div>",
        ]

        with self.app.application.app_context():
            for idx, text in enumerate(texts):
                data = {"content": text, "csrf_token": csrf_token}
                output = self.app.post("/markdown/?repo=test", data=data)
                self.assertEqual(output.status_code, 200)
                self.assertEqual(expected[idx], output.get_data(as_text=True))

    def test_markdown_preview(self):
        """Test the markdown_preview endpoint with a non-existing commit."""

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output_text
            )

            csrf_token = self.get_csrf(output=output)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        text = "Cf commit 9364354a4555ba17aa60f0d"
        exp = '<div class="markdown"><p>Cf commit 9364354a4555ba17aa60f0d</p></div>'

        with self.app.application.app_context():
            data = {"content": text, "csrf_token": csrf_token}
            output = self.app.post("/markdown/?repo=test", data=data)
            self.assertEqual(output.status_code, 200)
            self.assertEqual(exp, output.get_data(as_text=True))

    def test_markdown_preview_valid_commit(self):
        """ Test the markdown_preview endpoint with an existing commit. """

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output_text
            )

            csrf_token = self.get_csrf(output=output)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        repopath = os.path.join(self.path, "repos", "test.git")
        tests.add_content_git_repo(repopath)

        repo = pygit2.Repository(repopath)
        first_commit = repo.revparse_single("HEAD")

        text = "Cf commit %s" % first_commit.oid.hex
        exp = (
            '<div class="markdown"><p>Cf commit <a href="/test/c/{0}" title="Commit {0}">{1}'
            "</a></p></div>".format(
                first_commit.oid.hex, first_commit.oid.hex[:7]
            )
        )

        with self.app.application.app_context():
            data = {"content": text, "csrf_token": csrf_token}
            output = self.app.post("/markdown/?repo=test", data=data)
            self.assertEqual(output.status_code, 200)
            self.assertEqual(exp, output.get_data(as_text=True))

    @patch("pagure.ui.app.admin_session_timedout")
    def test_remove_user_email(self, ast):
        """ Test the remove_user_email endpoint. """
        ast.return_value = False

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/settings/email/drop")
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                "<h2>Page not found (404)</h2>", output.get_data(as_text=True)
            )

        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output_text
            )

            csrf_token = self.get_csrf(output=output)

            data = {"email": "foo@pingou.com"}

            output = self.app.post(
                "/settings/email/drop", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output_text
            )
            self.assertIn(
                "You must always have at " "least one email", output_text
            )

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )

            csrf_token = self.get_csrf(output=output)

            data = {"email": "foo@pingou.com"}

            output = self.app.post(
                "/settings/email/drop", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertEqual(output_text.count("foo@pingou.com"), 4)

            data = {"csrf_token": csrf_token, "email": "foobar@pingou.com"}

            output = self.app.post(
                "/settings/email/drop", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertIn(
                "You do not have the "
                "email: foobar@pingou.com, nothing to remove",
                output_text,
            )

            data = {"csrf_token": csrf_token, "email": "foo@pingou.com"}

            output = self.app.post(
                "/settings/email/drop", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text.count("foo@pingou.com"), 0)
            self.assertEqual(output_text.count("bar@pingou.com"), 3)

            output = self.app.post(
                "/settings/email/drop", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text.count("foo@pingou.com"), 0)
            self.assertEqual(output_text.count("bar@pingou.com"), 3)

            ast.return_value = True
            output = self.app.post("/settings/email/drop", data=data)
            self.assertEqual(output.status_code, 302)

    @patch("pagure.lib.notify.send_email")
    @patch("pagure.ui.app.admin_session_timedout")
    def test_add_api_user_email(self, ast, send_email):
        """ Test the add_api_user_email endpoint. """
        send_email.return_value = True
        ast.return_value = False

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/settings/email/add")
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                "<h2>Page not found (404)</h2>", output.get_data(as_text=True)
            )

        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.post("/settings/email/add")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Add new email</strong>", output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control form-control-error" id="email" '
                    'name="email" required type="text" value="">',
                    output_text,
                )
            else:
                self.assertIn(
                    '<input class="form-control form-control-error" id="email" '
                    'name="email" type="text" value="">',
                    output_text,
                )

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.post("/settings/email/add")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Add new email</strong>", output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control form-control-error" id="email" '
                    'name="email" required type="text" value="">',
                    output_text,
                )
            else:
                self.assertIn(
                    '<input class="form-control form-control-error" id="email" '
                    'name="email" type="text" value="">',
                    output_text,
                )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"email": "foo2@pingou.com"}

            output = self.app.post(
                "/settings/email/add", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Add new email</strong>", output_text)
            self.assertEqual(output_text.count("foo2@pingou.com"), 1)

            # New email
            data = {"csrf_token": csrf_token, "email": "foðbar@pingou.com"}

            output = self.app.post(
                "/settings/email/add", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertIn("Email pending validation", output_text)
            self.assertEqual(output_text.count("foo@pingou.com"), 4)
            self.assertEqual(output_text.count("bar@pingou.com"), 5)
            self.assertEqual(output_text.count("foðbar@pingou.com"), 2)

            # Email already pending
            output = self.app.post(
                "/settings/email/add", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="card-header">\n      '
                "<strong>Add new email</strong>",
                output_text,
            )
            self.assertIn(
                "This email is already " "pending confirmation", output_text
            )

            # User already has this email
            data = {"csrf_token": csrf_token, "email": "foo@pingou.com"}

            output = self.app.post(
                "/settings/email/add", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertTrue("<strong>Add new email</strong>" in output_text)
            self.assertTrue(
                "Invalid value, can&#39;t be any of: bar@pingou.com, "
                "foo@pingou.com.&nbsp;" in output_text
                or "Invalid value, can&#39;t be any of: foo@pingou.com, "
                "bar@pingou.com.&nbsp;" in output_text
            )
            self.assertEqual(output_text.count("foo@pingou.com"), 6)
            self.assertEqual(output_text.count("bar@pingou.com"), 5)
            self.assertEqual(output_text.count("foðbar@pingou.com"), 0)

            # Email registered by someone else
            data = {"csrf_token": csrf_token, "email": "foo@bar.com"}

            output = self.app.post(
                "/settings/email/add", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertTrue("<strong>Add new email</strong>" in output_text)
            self.assertIn(
                "Invalid value, can&#39;t be any of: foo@bar.com.&nbsp;",
                output_text,
            )

            ast.return_value = True
            output = self.app.post("/settings/email/add", data=data)
            self.assertEqual(output.status_code, 302)

    @patch("pagure.lib.notify.send_email")
    @patch("pagure.ui.app.admin_session_timedout")
    def test_set_default_email(self, ast, send_email):
        """ Test the set_default_email endpoint. """
        send_email.return_value = True
        ast.return_value = False

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/settings/email/default")
            self.assertEqual(output.status_code, 404)
            self.assertTrue(
                "<h2>Page not found (404)</h2>"
                in output.get_data(as_text=True)
            )

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )

            csrf_token = self.get_csrf(output=output)

            data = {"email": "foo@pingou.com"}

            output = self.app.post(
                "/settings/email/default", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertEqual(output_text.count("foo@pingou.com"), 4)

            # Set invalid default email
            data = {"csrf_token": csrf_token, "email": "foobar@pingou.com"}

            output = self.app.post(
                "/settings/email/default", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertEqual(output_text.count("foo@pingou.com"), 4)
            self.assertIn(
                "You do not have the "
                "email: foobar@pingou.com, nothing to set",
                output_text,
            )

            # Set default email
            data = {"csrf_token": csrf_token, "email": "foo@pingou.com"}

            output = self.app.post(
                "/settings/email/default", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertEqual(output_text.count("foo@pingou.com"), 4)
            self.assertIn(
                "Default email set to: " "foo@pingou.com", output_text
            )

            ast.return_value = True
            output = self.app.post("/settings/email/default", data=data)
            self.assertEqual(output.status_code, 302)

    @patch("pagure.lib.notify.send_email")
    @patch("pagure.ui.app.admin_session_timedout")
    def test_reconfirm_email(self, ast, send_email):
        """ Test the reconfirm_email endpoint. """
        send_email.return_value = True
        ast.return_value = False

        # Add a pending email to pingou
        userobj = pagure.lib.query.search_user(self.session, username="pingou")

        self.assertEqual(len(userobj.emails), 2)

        email_pend = pagure.lib.model.UserEmailPending(
            user_id=userobj.id, email="foo@fp.o", token="abcdef"
        )
        self.session.add(email_pend)
        self.session.commit()

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post("/settings/email/resend")
            self.assertEqual(output.status_code, 404)
            self.assertTrue(
                "<h2>Page not found (404)</h2>"
                in output.get_data(as_text=True)
            )

        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )

            csrf_token = self.get_csrf(output=output)

            data = {"email": "foo@pingou.com"}

            output = self.app.post(
                "/settings/email/resend", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertEqual(output_text.count("foo@pingou.com"), 4)

            # Set invalid default email
            data = {"csrf_token": csrf_token, "email": "foobar@pingou.com"}

            output = self.app.post(
                "/settings/email/resend", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertEqual(output_text.count("foo@pingou.com"), 4)
            self.assertIn(
                "This email address has " "already been confirmed", output_text
            )

            # Validate a non-validated email
            data = {"csrf_token": csrf_token, "email": "foo@fp.o"}

            output = self.app.post(
                "/settings/email/resend", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertEqual(output_text.count("foo@pingou.com"), 4)
            self.assertIn("Confirmation email re-sent", output_text)

            ast.return_value = True
            output = self.app.post("/settings/email/resend", data=data)
            self.assertEqual(output.status_code, 302)

    @patch("pagure.ui.app.admin_session_timedout")
    def test_confirm_email(self, ast):
        """ Test the confirm_email endpoint. """
        output = self.app.get("/settings/email/confirm/foobar")
        self.assertEqual(output.status_code, 302)

        ast.return_value = False

        # Add a pending email to pingou
        userobj = pagure.lib.query.search_user(self.session, username="pingou")

        self.assertEqual(len(userobj.emails), 2)

        email_pend = pagure.lib.model.UserEmailPending(
            user_id=userobj.id, email="foo@fp.o", token="abcdef"
        )
        self.session.add(email_pend)
        self.session.commit()

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            # Wrong token
            output = self.app.get(
                "/settings/email/confirm/foobar", follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertIn("No email associated with this token.", output_text)

            # Confirm email
            output = self.app.get(
                "/settings/email/confirm/abcdef", follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertIn("Email validated", output_text)

        userobj = pagure.lib.query.search_user(self.session, username="pingou")
        self.assertEqual(len(userobj.emails), 3)

        ast.return_value = True
        output = self.app.get("/settings/email/confirm/foobar")
        self.assertEqual(output.status_code, 302)

    def test_view_my_requests_no_user(self):
        """Test the view_user_requests endpoint."""
        output = self.app.get("/user/somenonexistentuser/requests")
        self.assertEqual(output.status_code, 404)

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_view_my_requests(self):
        """Test the view_user_requests endpoint. """
        # Create the PR
        tests.create_projects(self.session)
        repo = pagure.lib.query._get_project(self.session, "test")
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from="dev",
            repo_to=repo,
            branch_to="master",
            title="test pull-request #1",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "test pull-request #1")

        output = self.app.get("/user/pingou/requests")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("test pull-request #1", output_text)
        self.assertEqual(output_text.count('pr-status pr-status-open"'), 1)

        # Add a PR in a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test_fork",
            description="test project #1",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbttt",
        )
        self.session.add(item)
        repo = pagure.lib.query._get_project(
            self.session, "test_fork", user="pingou"
        )

        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from="dev",
            repo_to=repo,
            branch_to="master",
            title="tést pull-request #2",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "tést pull-request #2")

        output = self.app.get("/user/pingou/requests")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("test pull-request #1", output_text)
        self.assertIn("tést pull-request #2", output_text)
        self.assertEqual(output_text.count('pr-status pr-status-open"'), 2)

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_view_my_requests_pr_in_another_project(self):
        """Test the view_user_requests endpoint when the user opened a PR
        in another project."""
        # Pingou creates the PR on test
        tests.create_projects(self.session)
        repo = pagure.lib.query._get_project(self.session, "test")
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from="dev",
            repo_to=repo,
            branch_to="master",
            title="test pull-request #1",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "test pull-request #1")

        # foo creates the PR on test
        repo = pagure.lib.query._get_project(self.session, "test")
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from="dev",
            repo_to=repo,
            branch_to="master",
            title="test pull-request #2",
            user="foo",
        )
        self.session.commit()
        self.assertEqual(req.id, 2)
        self.assertEqual(req.title, "test pull-request #2")

        # Check pingou's PR list
        output = self.app.get("/user/pingou/requests?type=filed")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("test pull-request #1", output_text)
        self.assertNotIn("test pull-request #2", output_text)
        self.assertEqual(output_text.count('pr-status pr-status-open"'), 1)

        output = self.app.get("/user/pingou/requests?type=actionable")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn("test pull-request #1", output_text)
        self.assertIn("test pull-request #2", output_text)
        self.assertEqual(output_text.count('pr-status pr-status-open"'), 1)

        # Check foo's PR list
        output = self.app.get("/user/foo/requests")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn("test pull-request #1", output_text)
        self.assertIn("test pull-request #2", output_text)
        self.assertEqual(output_text.count('pr-status pr-status-open"'), 1)

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_view_my_requests_against_another_project(self):
        """Test the view_user_requests endpoint when there is a PR opened
        by me against a project I do not have rights on."""
        # Create the PR
        tests.create_projects(self.session)
        repo = pagure.lib.query._get_project(self.session, "test")
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from="dev",
            repo_to=repo,
            branch_to="master",
            title="test pull-request #1",
            user="foo",
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "test pull-request #1")

        output = self.app.get("/user/foo/requests")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("test pull-request #1", output_text)
        self.assertEqual(output_text.count('pr-status pr-status-open"'), 1)

    def test_view_my_issues_no_user(self):
        """Test the view_user_issues endpoint with a missing user."""
        output = self.app.get("/user/somenonexistentuser/issues")
        self.assertEqual(output.status_code, 404)

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_view_my_issues(self):
        """Test the view_user_issues endpoint when the user exists."""
        # Create the issue
        tests.create_projects(self.session)
        repo = pagure.lib.query._get_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #1",
            content="We should work on this for the second time",
            user="pingou",
            status="Open",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #1")

        output = self.app.get("/user/pingou/issues")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("Test issue #1", output_text)
        self.assertEqual(
            output_text.count("issue-status issue-status-open"), 1
        )

        # Add an issue in a fork
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name="test_fork",
            description="test project #1",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbttt",
        )
        self.session.add(item)
        repo = pagure.lib.query._get_project(
            self.session, "test_fork", user="foo"
        )

        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #2",
            content="We should work on this for the second time",
            user="pingou",
            status="Open",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #2")

        # Test the assigned issue table.  Create issue then set the assignee
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #3",
            content="This issue created by foo, but assigned to pingou",
            user="foo",
            status="Open",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #3")

        msg = pagure.lib.query.add_issue_assignee(
            session=self.session, issue=msg, assignee="pingou", user="foo"
        )
        self.session.commit()
        self.assertEqual(msg, "Issue assigned to pingou")

        output = self.app.get("/user/pingou/issues")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("Test issue #1", output_text)
        self.assertIn("Test issue #2", output_text)
        self.assertIn("Test issue #3", output_text)
        self.assertEqual(
            output_text.count("issue-status issue-status-open"), 3
        )

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_view_my_issues_disabled(self):
        """Test the view_user_issues endpoint when the project disabled issue
        tracking."""
        # Create the issue
        tests.create_projects(self.session)
        repo = pagure.lib.query._get_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #1",
            content="We should work on this for the second time",
            user="pingou",
            status="Open",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #1")

        # Before
        output = self.app.get("/user/pingou/issues")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("Test issue #1", output_text)
        self.assertEqual(
            output_text.count("issue-status issue-status-open"), 1
        )

        # Disable issue tracking
        repo = pagure.lib.query._get_project(self.session, "test")
        settings = repo.settings
        settings["issue_tracker"] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        # After
        output = self.app.get("/user/pingou/issues")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn("Test issue #1", output_text)
        self.assertEqual(
            output_text.count("issue-status issue-status-open"), 0
        )

    def test_view_my_issues_tickets_turned_off(self):
        """Test the view_user_issues endpoint when the user exists and
        and ENABLE_TICKETS is False"""

        # Turn off the tickets instance wide
        pagure.config.config["ENABLE_TICKETS"] = False

        output = self.app.get("/user/pingou/issues")
        self.assertEqual(output.status_code, 404)
        pagure.config.config["ENABLE_TICKETS"] = True

    @patch("pagure.ui.app.admin_session_timedout")
    def test_add_user_token(self, ast):
        """ Test the add_user_token endpoint. """
        ast.return_value = False

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/token/new/")
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                "<h2>Page not found (404)</h2>", output.get_data(as_text=True)
            )

        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/token/new")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="card-header">\n          <strong>'
                "Create a new token</strong>\n",
                output_text,
            )
            self.assertIn(
                '<input type="checkbox" name="acls" value="create_project">',
                output_text,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"acls": ["create_project", "fork_project"]}

            # missing CSRF
            output = self.app.post("/settings/token/new", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<title>Create token - Pagure</title>", output_text)
            self.assertIn(
                '<div class="card-header">\n          <strong>'
                "Create a new token</strong>\n",
                output_text,
            )
            self.assertIn(
                '<input type="checkbox" name="acls" value="create_project">',
                output_text,
            )

            data = {"acls": ["new_project"], "csrf_token": csrf_token}

            # Invalid ACLs
            output = self.app.post("/settings/token/new", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<title>Create token - Pagure</title>", output_text)
            self.assertIn(
                '<div class="card-header">\n          <strong>'
                "Create a new token</strong>\n",
                output_text,
            )
            self.assertIn(
                '<input type="checkbox" name="acls" value="create_project">',
                output_text,
            )

            data = {
                "acls": ["create_project", "fork_project"],
                "csrf_token": csrf_token,
            }

            # All good
            output = self.app.post(
                "/settings/token/new", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output_text
            )
            self.assertIn("Token created", output_text)
            self.assertEqual(
                output_text.count(
                    '<small class="font-weight-bold">Active until'
                ),
                1,
            )

            ast.return_value = True
            output = self.app.get("/settings/token/new")
            self.assertEqual(output.status_code, 302)

    @patch("pagure.ui.app.admin_session_timedout")
    def test_revoke_api_user_token(self, ast):
        """ Test the revoke_api_user_token endpoint. """
        ast.return_value = False

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            # Token doesn't exist
            output = self.app.post("/settings/token/revoke/foobar")
            self.assertEqual(output.status_code, 404)
            self.assertTrue(
                "<h2>Page not found (404)</h2>"
                in output.get_data(as_text=True)
            )

            # Create the foobar API token but associated w/ the user 'foo'
            item = pagure.lib.model.Token(
                id="foobar",
                user_id=2,  # foo
                expiration=datetime.datetime.utcnow()
                + datetime.timedelta(days=30),
            )
            self.session.add(item)
            self.session.commit()

            # Token not associated w/ this user
            output = self.app.post("/settings/token/revoke/foobar")
            self.assertEqual(output.status_code, 404)
            self.assertTrue(
                "<h2>Page not found (404)</h2>"
                in output.get_data(as_text=True)
            )

        user.username = "foo"
        with tests.user_set(self.app.application, user):
            # Missing CSRF token
            output = self.app.post(
                "/settings/token/revoke/foobar", follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output_text
            )
            self.assertEqual(
                output_text.count(
                    '<small class="font-weight-bold">Active until'
                ),
                1,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"csrf_token": csrf_token}

            # All good - token is deleted
            output = self.app.post(
                "/settings/token/revoke/foobar",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output_text
            )
            self.assertEqual(
                output_text.count(
                    '<small class="font-weight-bold">Active until'
                ),
                0,
            )

            user = pagure.lib.query.get_user(self.session, key="foo")
            self.assertEqual(len(user.tokens), 1)
            expiration_dt = user.tokens[0].expiration

            # Token was already deleted - no changes
            output = self.app.post(
                "/settings/token/revoke/foobar",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output_text
            )
            self.assertEqual(
                output_text.count(
                    '<small class="font-weight-bold">Active until'
                ),
                0,
            )

            # Ensure the expiration date did not change
            user = pagure.lib.query.get_user(self.session, key="foo")
            self.assertEqual(len(user.tokens), 1)
            self.assertEqual(expiration_dt, user.tokens[0].expiration)

            ast.return_value = True
            output = self.app.get("/settings/token/new")
            self.assertEqual(output.status_code, 302)

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "fas"})
    @patch.dict("pagure.utils.pagure_config", {"PAGURE_AUTH": "fas"})
    def test_create_project_auth_FAS_no_FPCA(self):
        """Test creating a project when auth is FAS and the user did not
        sign the FPCA."""

        user = tests.FakeUser(username="foo", cla_done=False)
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<title>Home - Pagure</title>", output_text)
            self.assertIn(
                '</i> You must <a href="https://admin.fedoraproject.org/accounts/'
                '">sign the FPCA</a> (Fedora Project Contributor Agreement) '
                "to use pagure</div>",
                output_text,
            )


class PagureFlaskAppAboutPagetests(tests.Modeltests):
    """ Unit-tests for the about page. """

    def test_about_page(self):
        """ Test the about page when an admin_email is set. """
        output = self.app.get("/about/")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>About - Pagure</title>", output_text)
        self.assertIn(
            "by emailing:\n      "
            '<a href="mailto:root@localhost.localdomain">',
            output_text,
        )
        self.assertIn(
            'href="https://pagure.io/pagure/issues">open a ticket</a>',
            output_text,
        )

    @patch.dict("pagure.config.config", {"ADMIN_EMAIL": "admin@fp.o"})
    def test_about_page_admin_email(self):
        """ Test the about page when an admin_email is set. """
        output = self.app.get("/about/")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>About - Pagure</title>", output_text)
        self.assertIn(
            'by emailing:\n      <a href="mailto:admin@fp.o">', output_text
        )
        self.assertIn(
            'href="https://pagure.io/pagure/issues">open a ticket</a>',
            output_text,
        )


class PagureFlaskAppNoDocstests(tests.Modeltests):
    """ Tests for flask app controller of pagure """

    config_values = {"enable_docs": False, "docs_folder": None}

    def test_new_project_no_docs_folder(self):
        """ Test the new_project endpoint with DOCS_FOLDER is None. """
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(
            os.path.exists(os.path.join(self.path, "repos", "project#1.git"))
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "tickets", "project#1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "docs", "project#1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "requests", "project#1.git")
            )
        )

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):

            csrf_token = self.get_csrf()

            data = {
                "description": "Project #1",
                "name": "project-1",
                "csrf_token": csrf_token,
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo my-3">\nProject #1', output_text
            )
            self.assertIn("<p>This repo is brand new!</p>", output_text)
            self.assertIn(
                "<title>Overview - project-1 - Pagure</title>", output_text
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)
        self.assertTrue(
            os.path.exists(os.path.join(self.path, "repos", "project-1.git"))
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(self.path, "repos", "tickets", "project-1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "docs", "project-1.git")
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(self.path, "repos", "requests", "project-1.git")
            )
        )


class PagureFlaskAppNoTicketstests(tests.Modeltests):
    """ Tests for flask app controller of pagure """

    config_values = {"enable_tickets": False, "tickets_folder": None}

    def test_new_project_no_tickets_folder(self):
        """ Test the new_project endpoint with TICKETS_FOLDER is None. """
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(
            os.path.exists(os.path.join(self.path, "repos", "project#1.git"))
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "tickets", "project#1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "docs", "project#1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "requests", "project#1.git")
            )
        )

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):

            csrf_token = self.get_csrf()

            data = {
                "description": "Project #1",
                "name": "project-1",
                "csrf_token": csrf_token,
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo my-3">\nProject #1', output_text
            )
            self.assertIn("<p>This repo is brand new!</p>", output_text)
            self.assertIn(
                "<title>Overview - project-1 - Pagure</title>", output_text
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)
        self.assertTrue(
            os.path.exists(os.path.join(self.path, "repos", "project-1.git"))
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "tickets", "project-1.git")
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(self.path, "repos", "docs", "project-1.git")
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(self.path, "repos", "requests", "project-1.git")
            )
        )


class PagureFlaskAppRenewUserApiTokentests(tests.Modeltests):
    @patch("pagure.decorators.admin_session_timedout")
    def setUp(self, ast):
        """ Constructor """
        super(PagureFlaskAppRenewUserApiTokentests, self).setUp()

        self.ast = ast
        self.ast.return_value = False

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/token/new")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create a new token</strong>", output_text)

            self.csrf_token = self.get_csrf(output=output)

            # Create a token to renew
            data = {"csrf_token": self.csrf_token, "acls": ["modify_project"]}
            output = self.app.post(
                "/settings/token/new/", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Token created", output_text)

        # 1 token associated with the user, expires in 60 days
        userobj = pagure.lib.query.search_user(self.session, username="pingou")
        self.assertEqual(len(userobj.tokens), 1)
        self.assertEqual(
            userobj.tokens[0].expiration.date(),
            datetime.datetime.utcnow().date()
            + datetime.timedelta(days=(30 * 6)),
        )

        self.token = userobj.tokens[0].id

    def test_renew_api_token_not_in(self):
        """ Test the renew_api_token endpoint. """
        # User not logged in
        output = self.app.post("/settings/token/renew/123")
        self.assertEqual(output.status_code, 302)

    @patch("pagure.ui.app.admin_session_timedout")
    def test_renew_api_token_session_old(self, ast):
        """ Test the renew_api_token endpoint. """
        ast.return_value = True

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {"csrf_token": self.csrf_token}

            # Test when the session timed-out
            output = self.app.post("/settings/token/renew/123", data=data)
            self.assertEqual(output.status_code, 302)
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Action canceled, try it again", output_text)

    def test_renew_api_token_invalid_token(self):
        """ Test the renew_api_token endpoint. """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                "/settings/token/renew/123",
                data={"csrf_token": self.csrf_token},
            )
            self.assertEqual(output.status_code, 404)
            output_text = output.get_data(as_text=True)
            self.assertIn("<p>Token not found</p>", output_text)

    def test_renew_api_token(self):
        """ Test the renew_api_token endpoint. """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):

            output = self.app.post(
                "/settings/token/renew/%s" % self.token,
                data={"csrf_token": self.csrf_token},
                follow_redirects=True,
            )
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>pingou's settings - Pagure</title>", output_text
            )
            self.assertIn("Token created", output_text)
            self.assertEqual(output_text.count('title="Revoke token">'), 2)
            self.assertEqual(output_text.count('title="Renew token">'), 2)
            self.session.commit()

            # Existing token has been renewed
            userobj = pagure.lib.query.search_user(
                self.session, username="pingou"
            )
            self.assertEqual(len(userobj.tokens), 2)
            self.assertEqual(
                userobj.tokens[0].expiration.date(),
                userobj.tokens[1].expiration.date(),
            )
            self.assertEqual(
                userobj.tokens[0].created.date(),
                userobj.tokens[1].created.date(),
            )
            self.assertEqual(userobj.tokens[0].acls, userobj.tokens[1].acls)
            self.assertEqual(
                userobj.tokens[0].description, userobj.tokens[1].description
            )


class PagureFlaskAppNewProjecttests(tests.Modeltests):
    """ Tests creating new project via the flask app controller of pagure """

    def setUp(self):
        """ Setup the environment. """
        super(PagureFlaskAppNewProjecttests, self).setUp()

        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(
            os.path.exists(os.path.join(self.path, "repos", "project#1.git"))
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "tickets", "project#1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "docs", "project#1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "requests", "project#1.git")
            )
        )

    @patch.dict("pagure.config.config", {"CASE_SENSITIVE": True})
    def test_new_project_case_sensitive(self):
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test")
        self.assertEqual(output.status_code, 200)

        output = self.app.get("/TEST")
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)
            data = {
                "description": "TEST",
                "name": "TEST",
                "csrf_token": csrf_token,
                "create_readme": True,
            }
            self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            output = self.app.get("/TEST")
            self.assertEqual(output.status_code, 200)

    def test_new_project_readme(self):
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            data = {
                "description": "testproject",
                "name": "testproject",
                "csrf_token": csrf_token,
                "create_readme": True,
            }
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - testproject - Pagure</title>", output_text
            )
            self.assertIn(
                '<a href="/testproject"><strong>testproject</strong></a>',
                output_text,
            )
            self.assertIn(
                '<code class="py-1 px-2 font-weight-bold '
                'commit_branch">master</code>',
                output_text,
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        project = pagure.lib.query._get_project(self.session, "testproject")
        repo = pygit2.Repository(project.repopath("main"))
        self.assertEqual(repo.listall_branches(), ["master"])

    @patch.dict("pagure.config.config", {"ENABLE_UI_NEW_PROJECTS": False})
    def test_new_project_when_turned_off_in_the_ui(self):
        """Test the new_project endpoint when new project creation is
        not allowed in the UI of this pagure instance."""

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 404)

            data = {"description": "Project #1", "name": "project-1"}

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

    @patch.dict("pagure.config.config", {"ENABLE_UI_NEW_PROJECTS": False})
    def test_new_project_button_when_turned_off_in_the_ui_no_project(self):
        """Test the index endpoint when new project creation is
        not allowed in the UI of this pagure instance."""

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>',
                output_text,
            )
            # master template
            self.assertNotIn(
                '<span class="oi" data-glyph="plus" title="Create New"',
                output_text,
            )
            # index_auth template
            self.assertNotIn(
                'title="Create New Project" aria-hidden="true">', output_text
            )

    @patch.dict("pagure.config.config", {"ENABLE_UI_NEW_PROJECTS": False})
    def test_new_project_button_when_turned_off_in_the_ui_w_project(self):
        """Test the index endpoint when new project creation is
        not allowed in the UI of this pagure instance."""
        tests.create_projects(self.session)

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>',
                output_text,
            )
            # master template
            self.assertNotIn(
                '<span class="oi" data-glyph="plus" title="Create New"',
                output_text,
            )
            # index_auth template
            self.assertNotIn(
                'title="Create New Project" aria-hidden="true">', output_text
            )

    def test_new_project_with_dot(self):
        """Test the new_project endpoint when new project contains a dot."""
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            data = {
                "description": "Project #1.",
                "name": "project.1",
                "csrf_token": csrf_token,
            }
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - project.1 - Pagure</title>", output_text
            )
            self.assertIn(
                '<a href="/project.1"><strong>project.1</strong></a>',
                output_text,
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)

    def test_new_project_with_plus(self):
        """Test the new_project endpoint when new project contains a plus sign."""
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            data = {
                "description": "Project #1.",
                "name": "project+1",
                "csrf_token": csrf_token,
            }
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - project+1 - Pagure</title>", output_text
            )
            self.assertTrue(
                '<a href="/project+1"><strong>project+1</strong></a>'
                in output_text
                or '<a href="/project%2B1"><strong>project+1</strong></a>'
                in output_text
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        repo = pygit2.Repository(projects[0].repopath("main"))
        self.assertEqual(repo.listall_branches(), [])

    def test_new_project_with_default_branch(self):
        """Test the new_project endpoint when new project contains a plus sign."""
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            data = {
                "description": "Project #1.",
                "name": "project_main",
                "csrf_token": csrf_token,
                "default_branch": "main",
                "create_readme": True,
            }
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - project_main - Pagure</title>", output_text
            )
            self.assertIn(
                '<a href="/project_main"><strong>project_main</strong></a>',
                output_text,
            )
            self.assertIn(
                '<code class="py-1 px-2 font-weight-bold '
                'commit_branch">main</code>',
                output_text,
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        repo = pygit2.Repository(projects[0].repopath("main"))
        self.assertEqual(repo.listall_branches(), ["main"])

    @patch.dict("pagure.config.config", {"GIT_DEFAULT_BRANCH": "main"})
    def test_new_project_with_default_branch_instance_wide(self):
        """Test the new_project endpoint when new project contains a plus sign."""
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            data = {
                "description": "Project #1.",
                "name": "project_main",
                "csrf_token": csrf_token,
                "create_readme": True,
            }
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - project_main - Pagure</title>", output_text
            )
            self.assertIn(
                '<a href="/project_main"><strong>project_main</strong></a>',
                output_text,
            )
            self.assertIn(
                '<code class="py-1 px-2 font-weight-bold '
                'commit_branch">main</code>',
                output_text,
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        repo = pygit2.Repository(projects[0].repopath("main"))
        self.assertEqual(repo.listall_branches(), ["main"])

    @patch.dict("pagure.config.config", {"GIT_DEFAULT_BRANCH": "main"})
    def test_new_project_with_default_branch_instance_wide_overriden(self):
        """Test the new_project endpoint when new project contains a plus sign."""
        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            data = {
                "description": "Project #1.",
                "name": "project_main",
                "csrf_token": csrf_token,
                "default_branch": "rawhide",
                "create_readme": True,
            }
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - project_main - Pagure</title>", output_text
            )
            self.assertIn(
                '<a href="/project_main"><strong>project_main</strong></a>',
                output_text,
            )
            self.assertIn(
                '<code class="py-1 px-2 font-weight-bold '
                'commit_branch">rawhide</code>',
                output_text,
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)

        repo = pygit2.Repository(projects[0].repopath("main"))
        self.assertEqual(repo.listall_branches(), ["rawhide"])

    def test_new_project_when_turned_off(self):
        """Test the new_project endpoint when new project creation is
        not allowed in the pagure instance."""

        # turn the project creation off
        pagure.config.config["ENABLE_NEW_PROJECTS"] = False

        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(
            os.path.exists(os.path.join(self.path, "repos", "project-1.git"))
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "tickets", "project-1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "docs", "project-1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "requests", "project-1.git")
            )
        )

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 404)

            # just get the csrf token
            pagure.config.config["ENABLE_NEW_PROJECTS"] = True
            output = self.app.get("/new/")
            pagure.config.config["ENABLE_NEW_PROJECTS"] = False

            csrf_token = (
                output.get_data(as_text=True)
                .split('name="csrf_token" type="hidden" value="')[1]
                .split('">')[0]
            )

            data = {"description": "Project #1", "name": "project-1"}

        user.username = "foo"
        with tests.user_set(self.app.application, user):
            data["csrf_token"] = csrf_token
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(
            os.path.exists(os.path.join(self.path, "repos", "project-1.git"))
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "tickets", "project-1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "docs", "project-1.git")
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.path, "repos", "requests", "project-1.git")
            )
        )

        pagure.config.config["ENABLE_NEW_PROJECTS"] = True

    def test_new_project_mirrored_invalid_url(self):
        """ Test the new_project with a mirrored repo but an invalid URL. """

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            data = {
                "description": "Project #1",
                "name": "project-1",
                "mirrored_from": "abcd",
                "csrf_token": csrf_token,
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<title>New project - Pagure</title>", output_text)
            self.assertIn("Invalid input.&nbsp;", output_text)

    def test_new_project_mirrored_invalid_sshurl(self):
        """Test the new_project with a mirrored repo but an invalid
        SSH-like url.
        """

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            data = {
                "description": "Project #1",
                "name": "project-1",
                "mirrored_from": "ssh://git@server.org/foo/bar.git",
                "csrf_token": csrf_token,
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<title>New project - Pagure</title>", output_text)
            self.assertIn("Invalid input.&nbsp;", output_text)

    def test_new_project_mirrored_valid_url(self):
        """ Test the new_project with a mirrored repo with a valid url. """

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<strong><label for="mirrored_from">Mirror from URL'
                "</label> </strong>",
                output_text,
            )

            csrf_token = self.get_csrf(output=output)

            data = {
                "description": "Project #1",
                "name": "project-1",
                "mirrored_from": "https://example.com/foo/bar.git",
                "csrf_token": csrf_token,
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - project-1 - Pagure</title>", output_text
            )
            self.assertIn(
                "<p>This repo is brand new and meant to be mirrored from "
                "https://example.com/foo/bar.git !</p>",
                output_text,
            )

    @patch.dict("pagure.config.config", {"DISABLE_MIRROR_IN": True})
    def test_new_project_mirrored_mirror_disabled(self):
        """Test the new_project with a mirrored repo when that feature is
        disabled.
        """

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn(
                '<strong><label for="mirrored_from">Mirror from URL'
                "</label> </strong>",
                output_text,
            )

            csrf_token = self.get_csrf(output=output)

            data = {
                "description": "Project #1",
                "name": "project-1",
                "mirrored_from": "https://example.com/foo/bar.git",
                "csrf_token": csrf_token,
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<title>New project - Pagure</title>", output_text)
            self.assertIn(
                "</i> Mirroring in projects has been disabled in "
                "this instance</div>",
                output_text,
            )

    def test_new_project(self):
        """ Test the new_project endpoint. """

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {"description": "Project #1"}

            output = self.app.post("/new/", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)
            self.assertIn(
                "<small>\n            This field is required.&nbsp;\n"
                "          </small>",
                output_text,
            )

            data["name"] = "project-1"
            output = self.app.post("/new/", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)
            self.assertNotIn(
                "<small>\n            This field is required.&nbsp;\n"
                "          </small>",
                output_text,
            )

            data["csrf_token"] = csrf_token
            output = self.app.post("/new/", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)
            self.assertIn("No user " "&#34;username&#34; found", output_text)

        user.username = "foo"
        with tests.user_set(self.app.application, user):
            data["csrf_token"] = csrf_token
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo my-3">\nProject #1', output_text
            )
            self.assertIn("<p>This repo is brand new!</p>", output_text)
            self.assertIn(
                "<title>Overview - project-1 - Pagure</title>", output_text
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)
        self.assertTrue(
            os.path.exists(os.path.join(self.path, "repos", "project-1.git"))
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(self.path, "repos", "tickets", "project-1.git")
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(self.path, "repos", "docs", "project-1.git")
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(self.path, "repos", "requests", "project-1.git")
            )
        )

    @patch.dict("pagure.config.config", {"USER_NAMESPACE": True})
    def test_new_project_user_namespaced(self):
        """Test the new_project with a user namespaced enabled."""

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)

            csrf_token = self.get_csrf(output=output)

            data = {
                "description": "Project #1",
                "name": "project-1",
                "csrf_token": csrf_token,
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - foo/project-1 - Pagure</title>", output_text
            )
            self.assertIn(
                '<div class="projectinfo my-3">\nProject #1', output_text
            )
            self.assertIn("<p>This repo is brand new!</p>", output_text)

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)
        self.assertTrue(
            os.path.exists(
                os.path.join(self.path, "repos", "foo", "project-1.git")
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.path, "repos", "tickets", "foo", "project-1.git"
                )
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.path, "repos", "docs", "foo", "project-1.git"
                )
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.path, "repos", "requests", "foo", "project-1.git"
                )
            )
        )

    @patch.dict("pagure.config.config", {"USER_NAMESPACE": True})
    def test_new_project_user_namespaced_invalid_user(self):
        """Test the new_project with a user namespaced enabled."""
        tests.create_user(self.session, "docs", "evil docs", ["docs@bar.com"])

        user = tests.FakeUser(username="docs")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)

            csrf_token = self.get_csrf(output=output)

            data = {
                "description": "Project #1",
                "name": "project-1",
                "csrf_token": csrf_token,
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<title>New project - Pagure</title>", output_text)
            self.assertIn(
                "</i> No project &#34;docs/project-1&#34; are allowed to be "
                "created due to potential conflicts in URLs with pagure "
                "itself</div>",
                output_text,
            )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
