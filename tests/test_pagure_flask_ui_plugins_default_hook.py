# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
import unittest
import shutil
import sys
import os

import flask
import pygit2
from mock import patch, MagicMock

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

    def test_plugin_default_remove(self):
        """ Check that the default plugin can be correctly removed if
        somehow managed.
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

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        plugin = pagure.lib.plugins.get_plugin('default')
        dbobj = plugin.db_object()

        plugin.remove(repo)

        self.assertFalse(os.path.exists(os.path.join(
            self.path, 'repos', 'test.git', 'hooks', 'post-receive.default')))
        self.assertTrue(os.path.exists(os.path.join(
            self.path, 'repos', 'test.git', 'hooks', 'post-receive')))

    def test_plugin_default_form(self):
        """ Check that the default plugin's form.
        """
        with self._app.test_request_context('/') as ctx:
            flask.g.session = self.session
            flask.g.fas_user = tests.FakeUser(username='foo')

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

            repo = pagure.lib.get_authorized_project(self.session, 'test')
            plugin = pagure.lib.plugins.get_plugin('default')
            dbobj = plugin.db_object()
            form = plugin.form(obj=dbobj)
            self.assertEqual(
                str(form.active),
                '<input id="active" name="active" type="checkbox" value="y">'
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
