# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import sys
import os

from mock import patch

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.utils
import tests


class PagureFlaskPluginMirrortests(tests.Modeltests):
    """ Tests for mirror plugin of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskPluginMirrortests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

    def test_valid_ssh_url_pattern(self):
        """Check a number of valide ssh target that the pattern should let
        through.
        """
        entries = [
            "ssh://user@host.lcl:/path/to/repo.git",
            "git@github.com:user/project.git",
            "ssh://user@host.org/target",
            "git+ssh://user@host.org/target",
            "git+ssh://user@host.lcl:/path/to/repo.git",
        ]
        for el in entries:
            print(el)
            self.assertIsNotNone(pagure.utils.ssh_urlpattern.match(el))

    def test_plugin_mirror_no_csrf(self):
        """ Test setting up the mirror plugin with no csrf. """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/settings/Mirroring")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mirroring - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )

            data = {}

            output = self.app.post("/test/settings/Mirroring", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mirroring - test - Pagure</title>",
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
                        "post-receive.mirror",
                    )
                )
            )

    def test_plugin_mirror_no_data(self):
        """Test the setting up the mirror plugin when there are no data
        provided in the request.
        """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            data = {"csrf_token": csrf_token}

            # With the git repo
            output = self.app.post(
                "/test/settings/Mirroring", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn("</i> Hook Mirroring deactivated</div>", output_text)

            output = self.app.get("/test/settings/Mirroring", data=data)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mirroring - test - Pagure</title>",
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
                        "post-receive.mirror",
                    )
                )
            )

    def test_plugin_mirror_invalid_target(self):
        """Test the setting up the mirror plugin when there are the target
        provided is invalid.
        """

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            data = {
                "csrf_token": csrf_token,
                "active": True,
                "target": "https://host.org/target",
            }

            # With the git repo
            output = self.app.post(
                "/test/settings/Mirroring", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mirroring - test - Pagure</title>",
                output_text,
            )
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<div class="col-sm-10">\n        '
                    '<input class="form-control pl-0" id="target" name="target" '
                    'required type="text" value="https://host.org/target">\n'
                    "    </div>\n  "
                    '</div>\n      <div class="alert alert-danger">Invalid '
                    "input.</div>",
                    output_text,
                )
            else:
                self.assertIn(
                    '<div class="col-sm-10">\n        '
                    '<input class="form-control pl-0" id="target" name="target" '
                    'type="text" value="https://host.org/target">\n    </div>\n  '
                    '</div>\n      <div class="alert alert-danger">Invalid '
                    "input.</div>",
                    output_text,
                )

            output = self.app.get("/test/settings/Mirroring", data=data)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mirroring - test - Pagure</title>",
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
                        "post-receive.mirror",
                    )
                )
            )

    def test_setting_up_mirror(self):
        """Test the setting up the mirror plugin."""

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            data = {
                "csrf_token": csrf_token,
                "active": True,
                "target": "ssh://user@host.org/target",
            }

            # With the git repo
            output = self.app.post(
                "/test/settings/Mirroring", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn("</i> Hook Mirroring activated</div>", output_text)

            output = self.app.get("/test/settings/Mirroring", data=data)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mirroring - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<input checked class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )

            self.assertTrue(
                os.path.exists(
                    os.path.join(
                        self.path, "repos", "test.git", "hooks", "post-receive"
                    )
                )
            )

    def test_plugin_mirror_deactivate(self):
        """Test the deactivating the mirror plugin."""
        self.test_setting_up_mirror()

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            # De-Activate hook
            data = {"csrf_token": csrf_token}
            output = self.app.post(
                "/test/settings/Mirroring", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings - test - Pagure</title>", output_text
            )
            self.assertIn("</i> Hook Mirroring deactivated</div>", output_text)

            output = self.app.get("/test/settings/Mirroring", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mirroring - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output.get_data(as_text=True),
            )

            self.assertFalse(
                os.path.exists(
                    os.path.join(
                        self.path,
                        "repos",
                        "test.git",
                        "hooks",
                        "post-receive.mirror",
                    )
                )
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
