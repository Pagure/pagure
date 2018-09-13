# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

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


class PagureFlaskPluginFedmsgtests(tests.SimplePagureTest):
    """ Tests for fedmsg plugin of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskPluginFedmsgtests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))
        tests.create_projects_git(os.path.join(self.path, 'docs'))

    def tearDown(self):
        """ Tear Down the environment after the tests. """
        super(PagureFlaskPluginFedmsgtests, self).tearDown()
        pagure.config.config['DOCS_FOLDER'] = None

    def test_plugin_fedmsg_defaul_page(self):
        """ Test the fedmsg plugin endpoint's default page. """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/settings/Fedmsg')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Fedmsg - test - Pagure</title>', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            csrf_token = self.get_csrf(output=output)

            data = {}

            output = self.app.post('/test/settings/Fedmsg', data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Fedmsg - test - Pagure</title>', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.fedmsg')))
            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'docs', 'test.git', 'hooks',
                'post-receive')))

    def test_plugin_fedmsg_no_data(self):
        """ Test the setting up the fedmsg plugin when there are no Docs
        folder.
        """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            data = {'csrf_token': csrf_token}

            # With the git repo
            output = self.app.post(
                '/test/settings/Fedmsg', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook Fedmsg deactivated',
                output_text)

            output = self.app.get('/test/settings/Fedmsg', data=data)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Fedmsg - test - Pagure</title>', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.fedmsg')))
            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'docs', 'test.git', 'hooks',
                'post-receive')))

    def test_plugin_fedmsg_activate(self):
        """ Test the setting up the fedmsg plugin when there are no Docs
        folder.
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
                '/test/settings/Fedmsg', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook Fedmsg activated',
                output_text)

            output = self.app.get('/test/settings/Fedmsg', data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Fedmsg - test - Pagure</title>', output_text)
            self.assertIn(
                '<input checked class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output_text)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.fedmsg')))
            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'docs', 'test.git', 'hooks',
                'post-receive')))

    def test_plugin_fedmsg_deactivate(self):
        """ Test the setting up the fedmsg plugin when there are no Docs
        folder.
        """
        self.test_plugin_fedmsg_activate()

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            # De-Activate hook
            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings/Fedmsg', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
            self.assertIn(
                'Hook Fedmsg deactivated',
                output_text)

            output = self.app.get('/test/settings/Fedmsg', data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings Fedmsg - test - Pagure</title>', output_text)
            self.assertIn(
                '<input class="form-check-input mt-2" id="active" name="active" '
                'type="checkbox" value="y">', output.get_data(as_text=True))

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.fedmsg')))
            self.assertTrue(os.path.exists(os.path.join(
                self.path, 'repos', 'docs', 'test.git', 'hooks',
                'post-receive')))

    @patch.dict('pagure.config.config', {'DOCS_FOLDER': None})
    def test_plugin_fedmsg_no_docs(self):
        """ Test the setting up the fedmsg plugin when there are no Docs
        folder.
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
                '/test/settings/Fedmsg', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'repos', 'test.git', 'hooks',
                'post-receive.fedmsg')))
            self.assertFalse(os.path.exists(os.path.join(
                self.path, 'docs', 'test.git', 'hooks',
                'post-receive')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
