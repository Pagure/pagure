# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import sys
import os


sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import tests


class PagureFlaskPluginMailtests(tests.SimplePagureTest):
    """ Tests for flask plugins controller of pagure """

    def test_plugin_mail(self):
        """ Test the mail plugin on/off endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/settings/Mail")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mail - test - Pagure</title>", output_text
            )
            self.assertIn('<label for="mail_to">Mail to</label>', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

            data = {}

            output = self.app.post("/test/settings/Mail", data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mail - test - Pagure</title>", output_text
            )
            self.assertIn('<label for="mail_to">Mail to</label>', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )

            data["csrf_token"] = csrf_token

            # With the git repo
            output = self.app.post(
                "/test/settings/Mail", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn("Hook Mail deactivated", output_text)

            output = self.app.get("/test/settings/Mail")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mail - test - Pagure</title>", output_text
            )
            self.assertIn('<label for="mail_to">Mail to</label>', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )

            # Missing the required mail_to
            data = {"csrf_token": csrf_token, "active": "y"}

            output = self.app.post(
                "/test/settings/Mail", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mail - test - Pagure</title>", output_text
            )
            self.assertNotIn("Hook activated", output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<div class="col-sm-10">\n        '
                    '<input class="form-control pl-0" id="mail_to" name="mail_to" '
                    'required type="text" value="">\n    </div>\n  </div>\n      '
                    '<div class="alert alert-danger">This field is required.</div>',
                    output_text,
                )
            else:
                self.assertIn(
                    '<div class="col-sm-10">\n        '
                    '<input class="form-control pl-0" id="mail_to" name="mail_to" '
                    'type="text" value="">\n    </div>\n  </div>\n      '
                    '<div class="alert alert-danger">This field is required.</div>',
                    output_text,
                )
            self.assertIn(
                '<input checked class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )

            # Activate hook
            data = {
                "csrf_token": csrf_token,
                "active": "y",
                "mail_to": "foo@bar",
            }

            output = self.app.post(
                "/test/settings/Mail", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn("Hook Mail activated", output_text)

            output = self.app.get("/test/settings/Mail")
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mail - test - Pagure</title>", output_text
            )
            self.assertIn('<label for="mail_to">Mail to</label>', output_text)
            self.assertIn(
                '<input checked class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )

            # De-Activate hook
            data = {"csrf_token": csrf_token}
            output = self.app.post(
                "/test/settings/Mail", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                "Project Settings</h5>\n",
                output_text,
            )
            self.assertIn("Hook Mail deactivated", output_text)

            output = self.app.get("/test/settings/Mail")
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Settings Mail - test - Pagure</title>", output_text
            )
            self.assertIn('<label for="mail_to">Mail to</label>', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">',
                output_text,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
