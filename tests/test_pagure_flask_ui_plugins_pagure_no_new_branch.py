# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import shutil
import sys
import os


sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import tests
import pagure.config


class PagureFlaskPluginPagureNoNewBranchHooktests(tests.SimplePagureTest):
    """ Tests for pagure_no_new_branches plugin of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskPluginPagureNoNewBranchHooktests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        pagure.config.config["GIT_FOLDER"] = os.path.join(self.path, "repos")

        with tests.user_set(self.app.application, tests.FakeUser()):
            self.csrf_token = self.get_csrf()

    def test_plugin_pagure_ticket_no_data(self):
        """ Test the pagure_ticket plugin on/off endpoint. """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get(
                "/test/settings/Prevent creating new branches by git push"
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Prevent creating new branches by git "
                "push - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )

            data = {}

            output = self.app.post(
                "/test/settings/Prevent creating new branches by git push",
                data=data,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Prevent creating new branches by git push "
                "- test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )

    def test_plugin_pagure_ticket_deactivate(self):
        """ Test the pagure_ticket plugin on/off endpoint. """
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            data = {"csrf_token": self.csrf_token}

            output = self.app.post(
                "/test/settings/Prevent creating new branches by git push",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn(
                "Hook Prevent creating new branches by git push deactivated",
                output_text,
            )

            output = self.app.get(
                "/test/settings/Prevent creating new branches by git push"
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Prevent creating new branches by git push "
                "- test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )

            self.assertFalse(
                os.path.exists(
                    os.path.join(
                        self.path,
                        "repos",
                        "test.git",
                        "hooks",
                        "post-receive.pagure",
                    )
                )
            )

    def test_plugin_pagure_ticket_activate(self):
        """ Test the pagure_ticket plugin on/off endpoint. """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            # Activate hook
            data = {"csrf_token": self.csrf_token, "active": "y"}

            output = self.app.post(
                "/test/settings/Prevent creating new branches by git push",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn(
                "Hook Prevent creating new branches by git push activated",
                output_text,
            )

            output = self.app.get(
                "/test/settings/Prevent creating new branches by git push"
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Prevent creating new branches by git push "
                "- test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<input checked class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )

            # De-Activate hook
            data = {"csrf_token": self.csrf_token}
            output = self.app.post(
                "/test/settings/Prevent creating new branches by git push",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn(
                "Hook Prevent creating new branches by git push deactivated",
                output_text,
            )

            output = self.app.get(
                "/test/settings/Prevent creating new branches by git push"
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Prevent creating new branches by git push "
                "- test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )

            self.assertFalse(
                os.path.exists(
                    os.path.join(
                        self.path,
                        "repos",
                        "test.git",
                        "hooks",
                        "pre-receive.pagure_no_new_branches",
                    )
                )
            )

    def test_plugin_pagure_ticket_activate_w_no_repo(self):
        """ Test the pagure_ticket plugin on/off endpoint. """
        shutil.rmtree(os.path.join(self.path, "repos", "test.git"))

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            # Try re-activate hook w/o the git repo
            data = {"csrf_token": self.csrf_token, "active": "y"}

            output = self.app.post(
                "/test/settings/Prevent creating new branches by git push",
                data=data,
            )
            self.assertEqual(output.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
