# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

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


class PagureFlaskPluginIRCtests(tests.SimplePagureTest):
    """ Tests for pagure_hook plugin of pagure """

    def test_plugin_mail(self):
        """ Test the irc plugin on/off endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/settings/IRC')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings IRC - test - Pagure</title>', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post('/test/settings/IRC', data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings IRC - test - Pagure</title>', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks', 'post-receive.irc')))

            data['csrf_token'] = csrf_token

            # With the git repo
            output = self.app.post(
                '/test/settings/IRC', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook IRC deactivated', output_text)

            output = self.app.get('/test/settings/IRC')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings IRC - test - Pagure</title>', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks', 'post-receive.irc')))

            # Activate hook
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
                'server': 'irc.freenode.net',
                'port': 6667,
                'room': '#fedora-apps',
            }

            output = self.app.post(
                '/test/settings/IRC', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook IRC activated', output_text)

            output = self.app.get('/test/settings/IRC')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings IRC - test - Pagure</title>', output_text)
            self.assertIn(
                '<input checked class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            # TODO: Fix this
            #self.assertTrue(os.path.exists(os.path.join(
                #self.path, 'repos', 'test.git', 'hooks', 'post-receive.irc')))

            # De-Activate hook
            data = {'csrf_token': csrf_token}
            output = self.app.post('/test/settings/IRC', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook IRC deactivated', output_text)

            output = self.app.get('/test/settings/IRC')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings IRC - test - Pagure</title>', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks', 'post-receive.irc')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
