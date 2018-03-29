# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']
import unittest
import shutil
import sys
import os


sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskPluginRtdHooktests(tests.SimplePagureTest):
    """ Tests for rtd_hook plugin of pagure """

    def test_plugin_pagure_request(self):
        """ Test the pagure_request plugin on/off endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/settings/Read the Doc')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Read the Doc settings</h3>', output_text)
            self.assertIn(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post('/test/settings/Read the Doc', data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Read the Doc settings</h3>', output_text)
            self.assertIn(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            data['csrf_token'] = csrf_token

            # Create the requests repo
            tests.create_projects_git(os.path.join(self.path, 'requests'))

            output = self.app.post(
                '/test/settings/Read the Doc', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output_text)
            self.assertIn(
                '</button>\n                      Hook Read the Doc deactivated',
                output_text)

            output = self.app.get('/test/settings/Read the Doc')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Read the Doc settings</h3>', output_text)
            self.assertIn(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'requests', 'test.git', 'hooks',
                'post-receive.pagure')))

            # Activate hook
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
                'project_name': 'foo',
            }

            output = self.app.post(
                '/test/settings/Read the Doc', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output_text)
            self.assertIn(
                '</button>\n                      Hook Read the Doc activated',
                output_text)

            output = self.app.get('/test/settings/Read the Doc')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Read the Doc settings</h3>', output_text)
            self.assertIn(
                '<input checked class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.rtd')))

            # De-Activate hook
            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings/Read the Doc', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output_text)
            self.assertIn(
                '</button>\n                      Hook Read the Doc deactivated',
                output_text)

            output = self.app.get('/test/settings/Read the Doc')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Read the Doc settings</h3>', output_text)
            self.assertIn(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.rtd')))

            # Try re-activate hook w/o the git repo
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
                'project_name': 'foo',
            }
            shutil.rmtree(os.path.join(self.path, 'repos', 'test.git'))

            output = self.app.post('/test/settings/Read the Doc', data=data)
            self.assertEqual(output.status_code, 404)


if __name__ == '__main__':
    unittest.main(verbosity=2)
