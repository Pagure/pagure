# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
import unittest
import shutil
import sys
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskPluginFedmsgtests(tests.Modeltests):
    """ Tests for fedmsg plugin of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskPluginFedmsgtests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.plugins.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = tests.HERE
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = pagure.APP.test_client()

    def test_plugin_mail(self):
        """ Test the mail plugin on/off endpoint. """

        tests.create_projects(self.session)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/settings/Fedmsg')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue('<h3>Fedmsg</h3>' in output.data)
            self.assertTrue(
                '<input id="active" name="active" type="checkbox" value="y">'
                in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post('/test/settings/Fedmsg', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue('<h3>Fedmsg</h3>' in output.data)
            self.assertTrue(
                '<input id="active" name="active" type="checkbox" value="y">'
                in output.data)

            self.assertFalse(os.path.exists(os.path.join(
                tests.HERE, 'test.git', 'hooks', 'post-receive.fedmsg')))

            data['csrf_token'] = csrf_token
            # No git found
            output = self.app.post('/test/settings/Fedmsg', data=data)
            self.assertEqual(output.status_code, 404)

            tests.create_projects_git(tests.HERE)

            # With the git repo
            output = self.app.post(
                '/test/settings/Fedmsg', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertIn(
                '<li class="message">Hook Fedmsg inactived</li>',
                output.data)
            output = self.app.get('/test/settings/Fedmsg', data=data)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertIn('<h3>Fedmsg</h3>', output.data)
            self.assertIn(
                '<input id="active" name="active" type="checkbox" value="y">',
                output.data)

            self.assertFalse(os.path.exists(os.path.join(
                tests.HERE, 'test.git', 'hooks', 'post-receive.fedmsg')))

            # Activate hook
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
            }

            output = self.app.post(
                '/test/settings/Fedmsg', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertIn(
                '<li class="message">Hook Fedmsg activated</li>',
                output.data)
            output = self.app.get('/test/settings/Fedmsg', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue('<h3>Fedmsg</h3>' in output.data)
            self.assertTrue(
                '<input checked id="active" name="active" type="checkbox" '
                'value="y">' in output.data)

            self.assertTrue(os.path.exists(os.path.join(
                tests.HERE, 'test.git', 'hooks', 'post-receive.fedmsg')))

            # De-Activate hook
            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings/Fedmsg', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertIn(
                '<li class="message">Hook Fedmsg inactived</li>',
                output.data)
            output = self.app.get('/test/settings/Fedmsg', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue('<h3>Fedmsg</h3>' in output.data)
            self.assertTrue(
                '<input id="active" name="active" type="checkbox" '
                'value="y">' in output.data)

            self.assertFalse(os.path.exists(os.path.join(
                tests.HERE, 'test.git', 'hooks', 'post-receive.fedmsg')))


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskPluginFedmsgtests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
