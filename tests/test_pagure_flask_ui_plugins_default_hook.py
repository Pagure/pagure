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

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskPluginDefaultHooktests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.plugins.SESSION = self.session
        pagure.ui.repo.SESSION = self.session
        pagure.ui.filters.SESSION = self.session


    def test_plugin_default_ui(self):
        """ Test the default hook plugin on/off endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/settings/default')
            self.assertEqual(output.status_code, 403)

    def test_plugin_default_install(self):
        """ Check that the default plugin is correctly installed when a
        project is created.
        """

        taskid = pagure.lib.new_project(
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
        result = pagure.lib.tasks.get_result(taskid).get()
        self.assertEqual(result,
                         {'endpoint': 'view_repo',
                          'repo': 'test',
                          'namespace': None})

        self.assertTrue(os.path.exists(os.path.join(
            self.path, 'repos', 'test.git', 'hooks', 'post-receive.default')))
        self.assertTrue(os.path.exists(os.path.join(
            self.path, 'repos', 'test.git', 'hooks', 'post-receive')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
