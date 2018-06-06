# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']

import unittest
import sys
import os


sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskPluginNoFFtests(tests.SimplePagureTest):
    """ Tests for Block non fast-forward pushes plugin of pagure """

    def test_plugin_noff(self):
        """ Test the noff plugin on/off endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get(
                '/test/settings/Block non fast-forward pushes')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn(
                '<h3>Block non fast-forward pushes settings</h3>',
                output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control" id="branches" name="branches" '
                    'required type="text" value=""></td>', output_text)
            else:
                self.assertIn(
                    '<input class="form-control" id="branches" name="branches" '
                    'type="text" value=""></td>', output_text)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post(
                '/test/settings/Block non fast-forward pushes', data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn(
                '<h3>Block non fast-forward pushes settings</h3>',
                output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control" id="branches" name="branches" '
                    'required type="text" value=""></td>', output_text)
            else:
                self.assertIn(
                    '<input class="form-control" id="branches" name="branches" '
                    'type="text" value=""></td>', output_text)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output_text)

            data['csrf_token'] = csrf_token

            # With the git repo
            output = self.app.post(
                '/test/settings/Block non fast-forward pushes',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output_text)
            self.assertTrue(
                '</button>\n                      Hook Block non '
                'fast-forward pushes deactivated' in output_text)

            output = self.app.get(
                '/test/settings/Block non fast-forward pushes')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn(
                '<h3>Block non fast-forward pushes settings</h3>',
                output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control" id="branches" name="branches" '
                    'required type="text" value=""></td>', output_text)
            else:
                self.assertIn(
                    '<input class="form-control" id="branches" name="branches" '
                    'type="text" value=""></td>', output_text)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks', 'post-receive.mail')))

            # Missing the required mail_to
            data = {'csrf_token': csrf_token, 'active': 'y'}

            output = self.app.post(
                '/test/settings/Block non fast-forward pushes',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn(
                '<h3>Block non fast-forward pushes settings</h3>',
                output_text)
            self.assertNotIn(
                '</button>\n                      Hook activated',
                output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control" id="branches" name="branches" '
                    'required type="text" value=""></td>', output_text)
            else:
                self.assertIn(
                    '<input class="form-control" id="branches" name="branches" '
                    'type="text" value=""></td>', output_text)
            self.assertTrue(
                '<input checked class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'pre-receive.pagureforcecommit')))

            # Activate hook
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
                'branches': 'master',
            }

            output = self.app.post(
                '/test/settings/Block non fast-forward pushes',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h3>Settings for test</h3>',
                output_text)
            self.assertIn(
                '</button>\n                      Hook Block non '
                'fast-forward pushes activated', output_text)

            output = self.app.get(
                '/test/settings/Block non fast-forward pushes')
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn(
                '<h3>Block non fast-forward pushes settings</h3>',
                output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control" id="branches" name="branches" '
                    'required type="text" value="master"></td>', output_text)
            else:
                self.assertIn(
                    '<input class="form-control" id="branches" name="branches" '
                    'type="text" value="master"></td>', output_text)
            self.assertIn(
                '<input checked class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'pre-receive.pagureforcecommit')))

            # De-Activate hook
            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings/Block non fast-forward pushes',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output_text)
            self.assertIn(
                '</button>\n                      Hook Block non '
                'fast-forward pushes deactivated', output_text)

            output = self.app.get(
                '/test/settings/Block non fast-forward pushes')
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn(
                '<h3>Block non fast-forward pushes settings</h3>',
                output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control" id="branches" name="branches" '
                    'required type="text" value=""></td>', output_text)
            else:
                self.assertIn(
                    '<input class="form-control" id="branches" name="branches" '
                    'type="text" value=""></td>', output_text)
            self.assertIn(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'pre-receive.pagureforcecommit')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
