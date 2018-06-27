# -*- coding: utf-8 -*-

"""
 (c) 2016-2018 - Copyright Red Hat Inc

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
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Block Un-Signed commits - test - '
                'Pagure</title>', output_text)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post(
                '/test/settings/Block Un-Signed commits', data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Block Un-Signed commits - test - '
                'Pagure</title>', output_text)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output_text)

            data['csrf_token'] = csrf_token

            # With the git repo
            output = self.app.post(
                '/test/settings/Block Un-Signed commits',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertTrue(
                'Hook Block Un-Signed '
                'commits deactivated' in output_text)

            output = self.app.get(
                '/test/settings/Block Un-Signed commits')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Block Un-Signed commits - test - '
                'Pagure</title>', output_text)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'pre-receive.pagureunsignedcommit')))

            # Activate the hook
            data = {'csrf_token': csrf_token, 'active': 'y'}

            output = self.app.post(
                '/test/settings/Block Un-Signed commits',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertNotIn(
                'Hook activated',
                output_text)

            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'pre-receive.pagureunsignedcommit')))

            # De-Activate hook
            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings/Block Un-Signed commits',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertTrue(
                'Hook Block Un-Signed '
                'commits deactivated' in output_text)

            output = self.app.get(
                '/test/settings/Block Un-Signed commits')
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Block Un-Signed commits - test - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'pre-receive.pagureunsignedcommit')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
