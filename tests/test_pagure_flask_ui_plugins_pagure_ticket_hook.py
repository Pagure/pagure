# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

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


class PagureFlaskPluginPagureTicketHooktests(tests.SimplePagureTest):
    """ Tests for pagure_hook plugin of pagure """

    def test_plugin_pagure_ticket(self):
        """ Test the pagure_ticket plugin on/off endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/settings/Pagure tickets')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Pagure tickets - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post('/test/settings/Pagure tickets', data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Pagure tickets - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            data['csrf_token'] = csrf_token

            # Create the tickets repo
            tests.create_projects_git(os.path.join(self.path, 'repos', 'tickets'))

            output = self.app.post(
                '/test/settings/Pagure tickets', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook Pagure tickets deactivated',
                output_text)

            output = self.app.get('/test/settings/Pagure tickets')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Pagure tickets - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'tickets', 'test.git', 'hooks',
                'post-receive.pagure')))

            # Activate hook
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
            }

            output = self.app.post(
                '/test/settings/Pagure tickets', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook Pagure tickets activated',
                output_text)

            output = self.app.get('/test/settings/Pagure tickets')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Pagure tickets - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<input checked class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            # De-Activate hook
            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings/Pagure tickets', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook Pagure tickets deactivated',
                output_text)

            output = self.app.get('/test/settings/Pagure tickets')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Pagure tickets - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'tickets', 'test.git', 'hooks',
                'post-receive.pagure-ticket')))

            # Try re-activate hook w/o the git repo
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
            }
            shutil.rmtree(os.path.join(self.path, 'repos', 'tickets', 'test.git'))

            output = self.app.post('/test/settings/Pagure tickets', data=data)
            self.assertEqual(output.status_code, 404)


if __name__ == '__main__':
    unittest.main(verbosity=2)
