# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']

import unittest
import sys
import os

from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskPluginPagureHooktests(tests.SimplePagureTest):
    """ Tests for pagure_hook plugin of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskPluginPagureHooktests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))
        tests.create_projects_git(os.path.join(self.path, 'repos', 'docs'))

    def tearDown(self):
        """ Tear Down the environment after the tests. """
        super(PagureFlaskPluginPagureHooktests, self).tearDown()
        pagure.config.config['DOCS_FOLDER'] = None

    def test_plugin_mail_page(self):
        """ Test the default page of the pagure hook plugin. """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/settings/Pagure')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Pagure settings</h3>', output_text)
            self.assertIn(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

    def test_plugin_mail_no_data(self):
        """ Test the pagure hook plugin endpoint when no data is sent. """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):

            data = {}

            output = self.app.post('/test/settings/Pagure', data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Pagure settings</h3>', output_text)
            self.assertIn(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive')))
            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'docs', 'test.git', 'hooks',
                'post-receive')))

    def test_plugin_mail_no_data_csrf(self):
        """ Test the pagure hook plugin endpoint when no data is sent but
        the csrf token.
        """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            data = {'csrf_token': csrf_token}

            tests.create_projects_git(os.path.join(self.path, 'repos', 'docs'))
            tests.create_projects_git(os.path.join(self.path, 'repos', 'requests'))

            # With the git repo
            output = self.app.post(
                '/test/settings/Pagure', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output_text)
            self.assertIn(
                '</button>\n                      Hook Pagure deactivated',
                output_text)

            output = self.app.get('/test/settings/Pagure')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Pagure settings</h3>', output_text)
            self.assertIn(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.pagure')))
            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive')))
            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'docs', 'test.git', 'hooks',
                'post-receive')))

    def test_plugin_mail_activate_hook(self):
        """ Test the pagure hook plugin endpoint when activating the hook.
        """
        pagure.config.config['DOCS_FOLDER'] = os.path.join(
            self.path, 'repos', 'docs')

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            # Activate hook
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
            }

            output = self.app.post(
                '/test/settings/Pagure', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output.get_data(as_text=True))
            self.assertIn(
                '</button>\n                      Hook Pagure activated',
                output_text)

            output = self.app.get('/test/settings/Pagure')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Pagure settings</h3>', output_text)
            self.assertIn(
                '<input checked class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.pagure')))
            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive')))
            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'docs', 'test.git', 'hooks',
                'post-receive')))

    def test_plugin_mail_deactivate_hook(self):
        """ Test the pagure hook plugin endpoint when activating the hook.
        """
        self.test_plugin_mail_activate_hook()

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            # De-Activate hook
            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings/Pagure', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output_text)
            self.assertIn(
                '</button>\n                      Hook Pagure deactivated',
                output_text)

            output = self.app.get('/test/settings/Pagure')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Pagure settings</h3>', output_text)
            self.assertIn(
                '<input class="form-control" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.pagure')))
            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive')))
            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'docs', 'test.git', 'hooks',
                'post-receive')))

    @patch.dict('pagure.config.config', {'DOCS_FOLDER': None})
    def test_plugin_mail_activate_hook_no_doc(self):
        """ Test the pagure hook plugin endpoint when activating the hook
        on a pagure instance that de-activated the doc repos.
        """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            # Activate hook
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
            }

            output = self.app.post(
                '/test/settings/Pagure', data=data, follow_redirects=True)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '</button>\n                      Hook Pagure activated',
                output_text)

            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.pagure')))
            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive')))
            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'docs', 'test.git', 'hooks',
                'post-receive')))

    @patch.dict('pagure.config.config', {'DOCS_FOLDER': None})
    def test_plugin_mail_deactivate_hook_no_doc(self):
        """ Test the pagure hook plugin endpoint when activating then
        deactivating the hook on a pagure instance that de-activated the
        doc repos.
        """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            # Activate hook
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
            }

            output = self.app.post(
                '/test/settings/Pagure', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output_text)
            self.assertIn(
                '</button>\n                      Hook Pagure activated',
                output_text)

            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.pagure')))
            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive')))
            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'docs', 'test.git', 'hooks',
                'post-receive')))

            # Deactivate hook
            data = {
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/test/settings/Pagure', data=data, follow_redirects=True)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '</button>\n                      Hook Pagure deactivated',
                output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.pagure')))
            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive')))
            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'docs', 'test.git', 'hooks',
                'post-receive')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
