# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']

import unittest
import sys
import os


sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskPluginUnsignedtests(tests.SimplePagureTest):
    """ Tests for Block pushes with unsigned commit plugin of pagure """

    def test_plugin_unsigned(self):
        """ Test the noff plugin on/off endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get(
                '/test/settings/Block Un-Signed commits')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output.data)
            self.assertIn(
                '<h3>Block Un-Signed commits settings</h3>',
                output.data)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post(
                '/test/settings/Block Un-Signed commits', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output.data)
            self.assertIn(
                '<h3>Block Un-Signed commits settings</h3>',
                output.data)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output.data)

            data['csrf_token'] = csrf_token

            # With the git repo
            output = self.app.post(
                '/test/settings/Block Un-Signed commits',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output.data)
            self.assertTrue(
                '</button>\n                      Hook Block Un-Signed '
                'commits deactivated' in output.data)

            output = self.app.get(
                '/test/settings/Block Un-Signed commits')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output.data)
            self.assertIn(
                '<h3>Block Un-Signed commits settings</h3>',
                output.data)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output.data)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'pre-receive.pagureunsignedcommit')))

            # Activate the hook
            data = {'csrf_token': csrf_token, 'active': 'y'}

            output = self.app.post(
                '/test/settings/Block Un-Signed commits',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output.data)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output.data)
            self.assertNotIn(
                '</button>\n                      Hook activated',
                output.data)

            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'pre-receive.pagureunsignedcommit')))

            # De-Activate hook
            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings/Block Un-Signed commits',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output.data)
            self.assertTrue(
                '</button>\n                      Hook Block Un-Signed '
                'commits deactivated' in output.data)

            output = self.app.get(
                '/test/settings/Block Un-Signed commits')
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output.data)
            self.assertIn(
                '<h3>Block Un-Signed commits settings</h3>',
                output.data)
            self.assertIn(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output.data)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'pre-receive.pagureunsignedcommit')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
