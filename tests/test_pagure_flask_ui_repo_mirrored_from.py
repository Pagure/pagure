# -*- coding: utf-8 -*-

"""
 (c) 2020 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import os
import shutil
import sys
import tempfile
import time
import unittest

import pygit2
import six
from mock import patch, MagicMock, ANY, call

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.git
import tests

from pagure.lib.repo import PagureRepo


class PagureUiRepoMirroredFromTests(tests.Modeltests):
    """Tests for pagure project that are mirrored from a remote location"""

    maxDiff = None

    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureUiRepoMirroredFromTests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Make the test project mirrored from elsewhere
        self.project = pagure.lib.query.get_authorized_project(
            self.session, "test"
        )
        self.project.mirrored_from = "https://example.com/foo/bar.git"
        self.session.add(self.project)
        self.session.commit()

    def test_custom_projecticon(self):
        """Ensure that the customized project icon is shown the main page of
        the project.
        """
        output = self.app.get("/test")
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<i class="fa fa-cloud-download text-muted" title="Mirrored from '
            'https://example.com/foo/bar.git"></i>',
            output_text,
        )

    def test_regular_projecticon(self):
        """Ensure that the customized project icon is shown the main page of
        the project.
        """
        output = self.app.get("/test2")
        output_text = output.get_data(as_text=True)
        self.assertNotIn(
            '<i class="fa fa-cloud-download text-muted" title="Mirrored from ',
            output_text,
        )

    def test_settings_shows(self):
        """Ensure that the box to edit the mirrored from value shows up
        in the settings.
        """
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<input class="form-control" name="mirrored_from" '
                'value="https://example.com/foo/bar.git" />',
                output_text,
            )
            self.assertIn(
                "The (public) url from which this repository is mirrored.",
                output_text,
            )

    def test_settings_not_show(self):
        """Ensure that the box to edit the mirrored from value does not
        show up in the settings when it shouldn't.
        """
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test2/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn(
                '<input class="form-control" name="mirrored_from" ',
                output_text,
            )
            self.assertNotIn(
                "The (public) url from which this repository is mirrored.",
                output_text,
            )

    def test_edit_mirrored_from(self):
        """Ensure that we can successfully edit the content of the
        mirrored_from field.
        """
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<input class="form-control" name="mirrored_from" '
                'value="https://example.com/foo/bar.git" />',
                output_text,
            )

            csrf_token = self.get_csrf(output=output)

            data = {
                "csrf_token": csrf_token,
                "description": "test repo",
                "mirrored_from": "https://example2.com/bar.git",
            }
            output = self.app.post(
                "/test/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<input class="form-control" name="mirrored_from" '
                'value="https://example2.com/bar.git" />',
                output_text,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
