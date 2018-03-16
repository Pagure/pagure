# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

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
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>IRC settings</h3>' in output.data)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post('/test/settings/IRC', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>IRC settings</h3>' in output.data)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output.data)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks', 'post-receive.irc')))

            data['csrf_token'] = csrf_token

            # With the git repo
            output = self.app.post(
                '/test/settings/IRC', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output.data)
            self.assertTrue(
                '</button>\n                      Hook IRC deactivated' in output.data)

            output = self.app.get('/test/settings/IRC')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>IRC settings</h3>' in output.data)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output.data)

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
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output.data)
            self.assertTrue(
                '</button>\n                      Hook IRC activated' in output.data)

            output = self.app.get('/test/settings/IRC')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>IRC settings</h3>' in output.data)
            self.assertTrue(
                '<input checked class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output.data)

            # TODO: Fix this
            #self.assertTrue(os.path.exists(os.path.join(
                #self.path, 'repos', 'test.git', 'hooks', 'post-receive.irc')))

            # De-Activate hook
            data = {'csrf_token': csrf_token}
            output = self.app.post('/test/settings/IRC', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output.data)
            self.assertTrue(
                '</button>\n                      Hook IRC deactivated' in output.data)

            output = self.app.get('/test/settings/IRC')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>IRC settings</h3>' in output.data)
            self.assertTrue(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">' in output.data)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks', 'post-receive.irc')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
