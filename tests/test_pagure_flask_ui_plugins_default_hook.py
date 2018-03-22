# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
import unittest
import shutil
import sys
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskPluginDefaultHooktests(tests.Modeltests):
    """ Tests for default_hook plugin of pagure """

    def test_plugin_default_ui(self):
        """ Test the default hook plugin on/off endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/settings/default')
            self.assertEqual(output.status_code, 403)

    def test_plugin_default_install(self):
        """ Check that the default plugin is correctly installed when a
        project is created.
        """

        task = pagure.lib.new_project(
            self.session,
            user='pingou',
            name='test',
            blacklist=[],
            allowed_prefix=[],
            gitfolder=os.path.join(self.path, 'repos'),
            docfolder=os.path.join(self.path, 'docs'),
            ticketfolder=os.path.join(self.path, 'tickets'),
            requestfolder=os.path.join(self.path, 'requests'),
            description=None,
            url=None, avatar_email=None,
            parent_id=None,
            add_readme=False,
            userobj=None,
            prevent_40_chars=False,
            namespace=None
        )
        self.assertEqual(task.get(),
                         {'endpoint': 'ui_ns.view_repo',
                          'repo': 'test',
                          'namespace': None})

        self.assertTrue(os.path.exists(os.path.join(
            self.path, 'repos', 'test.git', 'hooks', 'post-receive.default')))
        self.assertTrue(os.path.exists(os.path.join(
            self.path, 'repos', 'test.git', 'hooks', 'post-receive')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
