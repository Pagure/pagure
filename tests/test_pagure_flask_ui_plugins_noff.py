# -*- coding: utf-8 -*-

"""
 (c) 2016-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

__requires__ = ['SQLAlchemy >= 0.8']

import unittest
import sys
import os


sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

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
                '<title>Settings Block non fast-forward pushes - test - '
                'Pagure</title>', output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control pl-0" id="branches" name="branches" '
                    'required type="text" value="">', output_text)
            else:
                self.assertIn(
                    '<input class="form-control pl-0" id="branches" name="branches" '
                    'type="text" value="">', output_text)
            self.assertTrue(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">' in output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post(
                '/test/settings/Block non fast-forward pushes', data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Block non fast-forward pushes - test - '
                'Pagure</title>', output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control pl-0" id="branches" name="branches" '
                    'required type="text" value="">', output_text)
            else:
                self.assertIn(
                    '<input class="form-control pl-0" id="branches" name="branches" '
                    'type="text" value="">', output_text)
            self.assertTrue(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">' in output_text)

            data['csrf_token'] = csrf_token

            # With the git repo
            output = self.app.post(
                '/test/settings/Block non fast-forward pushes',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertTrue(
                'Hook Block non '
                'fast-forward pushes deactivated' in output_text)

            output = self.app.get(
                '/test/settings/Block non fast-forward pushes')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Block non fast-forward pushes - test - '
                'Pagure</title>', output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control pl-0" id="branches" name="branches" '
                    'required type="text" value="">', output_text)
            else:
                self.assertIn(
                    '<input class="form-control pl-0" id="branches" name="branches" '
                    'type="text" value="">', output_text)
            self.assertTrue(
                '<input class="form-check-input mt-2" id="active" name="active" '
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
                '<title>Settings Block non fast-forward pushes - test - '
                'Pagure</title>', output_text)
            self.assertNotIn(
                'Hook activated',
                output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control pl-0" id="branches" name="branches" '
                    'required type="text" value="">', output_text)
            else:
                self.assertIn(
                    '<input class="form-control pl-0" id="branches" name="branches" '
                    'type="text" value="">', output_text)
            self.assertTrue(
                '<input checked class="form-check-input mt-2" id="active" name="active" '
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
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook Block non '
                'fast-forward pushes activated', output_text)

            output = self.app.get(
                '/test/settings/Block non fast-forward pushes')
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Block non fast-forward pushes - test - '
                'Pagure</title>', output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control pl-0" id="branches" name="branches" '
                    'required type="text" value="master">', output_text)
            else:
                self.assertIn(
                    '<input class="form-control pl-0" id="branches" name="branches" '
                    'type="text" value="master">', output_text)
            self.assertIn(
                '<input checked class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            # De-Activate hook
            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings/Block non fast-forward pushes',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook Block non '
                'fast-forward pushes deactivated', output_text)

            output = self.app.get(
                '/test/settings/Block non fast-forward pushes')
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Block non fast-forward pushes - test - '
                'Pagure</title>', output_text)
            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<input class="form-control pl-0" id="branches" name="branches" '
                    'required type="text" value="">', output_text)
            else:
                self.assertIn(
                    '<input class="form-control pl-0" id="branches" name="branches" '
                    'type="text" value="">', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'pre-receive.pagureforcecommit')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
