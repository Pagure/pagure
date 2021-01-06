# -*- coding: utf-8 -*-

"""
 (c) 2019 - Copyright Red Hat Inc

 Authors:
   Michal Konecny <mkonecny@redhat.com>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import sys
import os
import json

from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.plugins as plugins  # noqa: E402
import pagure.lib.query  # noqa: E402
import tests  # noqa: E402


class PagureFlaskApiPluginViewProjecttests(tests.Modeltests):
    """Tests for the flask API of pagure for viewing enabled plugins on project"""

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiPluginViewProjecttests, self).setUp()

        tests.create_projects(self.session)

    def test_view_plugin_on_project(self):
        """Test viewing plugins on a project."""

        # Install plugin
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        plugin = plugins.get_plugin("Mail")
        plugin.set_up(repo)
        dbobj = plugin.db_object()
        dbobj.active = True
        dbobj.project_id = repo.id
        dbobj.mail_to = "serg@wh40k.com"
        plugin.install(repo, dbobj)
        self.session.add(dbobj)
        self.session.commit()

        # Retrieve all plugins on project
        output = self.app.get("/api/0/test/settings/plugins")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "plugins": [{"Mail": {"mail_to": "serg@wh40k.com"}}],
                "total_plugins": 1,
            },
        )

    def test_viewing_plugin_on_project_no_plugin(self):
        """Test viewing plugins on a project, which doesn't
        have any installed.
        """

        # Retrieve all plugins on project
        output = self.app.get("/api/0/test/settings/plugins")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(data, {"plugins": [], "total_plugins": 0})


if __name__ == "__main__":
    unittest.main(verbosity=2)
