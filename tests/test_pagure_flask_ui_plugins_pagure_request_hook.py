# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import shutil
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import tests


class PagureFlaskPluginPagureRequestHooktests(tests.SimplePagureTest):
    """ Tests for pagure_hook plugin of pagure """

    def test_plugin_pagure_request(self):
        """ Test the pagure_request plugin on/off endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/settings/Pagure requests')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Pagure requests - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post('/test/settings/Pagure requests', data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Pagure requests - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            data['csrf_token'] = csrf_token

            # Create the requests repo
            tests.create_projects_git(os.path.join(self.path, 'repos', 'requests'))

            output = self.app.post(
                '/test/settings/Pagure requests', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook Pagure requests deactivated',
                output_text)

            output = self.app.get('/test/settings/Pagure requests')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Pagure requests - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'requests', 'test.git', 'hooks',
                'post-receive.pagure')))

            # Activate hook
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
            }

            output = self.app.post(
                '/test/settings/Pagure requests', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook Pagure requests activated',
                output_text)

            output = self.app.get('/test/settings/Pagure requests')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Pagure requests - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<input checked class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            # De-Activate hook
            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings/Pagure requests', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook Pagure requests deactivated',
                output_text)

            output = self.app.get('/test/settings/Pagure requests')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Pagure requests - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'requests', 'test.git', 'hooks',
                'post-receive.pagure-requests')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
