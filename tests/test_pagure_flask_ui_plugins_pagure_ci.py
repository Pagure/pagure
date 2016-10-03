# -*- coding: utf-8 -*-

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


class PagureFlaskPluginPagureCItests(tests.Modeltests):
    """ Tests for flask plugins controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskPluginPagureCItests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.plugins.SESSION = self.session
        pagure.ui.repo.SESSION = self.session
        pagure.ui.filters.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = self.path
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            self.path, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            self.path, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            self.path, 'docs')
        self.app = pagure.APP.test_client()

    def test_plugin_pagure_ci(self):
        """ Test the pagure ci plugin on/off endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(self.path)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/settings/Pagure CI')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>Pagure CI settings</h3>' in output.data)
            self.assertIn(
                '<td><label for="ci_url">URL to the project on the CI '
                'service</label></td>' , output.data)
            self.assertIn(
                '<input id="active" name="active" type="checkbox" value="y">',
                output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post('/test/settings/Pagure CI', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>Pagure CI settings</h3>' in output.data)
            self.assertIn(
                '<td><label for="ci_url">URL to the project on the CI '
                'service</label></td>' , output.data)
            self.assertIn(
                '<input id="active" name="active" type="checkbox" value="y">',
                output.data)

            # Activate hook
            data = {
                'active': 'y',
                'ci_url': 'https://jenkins.fedoraproject.org',
                'ci_type': 'jenkins',
            }
            # CSRF Token missing
            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>Pagure CI settings</h3>' in output.data)
            self.assertIn(
                '<td><label for="ci_url">URL to the project on the CI '
                'service</label></td>' , output.data)
            self.assertIn(
                '<input checked id="active" name="active" type="checkbox" '
                'value="y">', output.data)

            data['csrf_token'] = csrf_token

            if not pagure.APP.config.get('PAGURE_CI_SERVICES'):
                return

            # Activate hook
            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '</button>\n                      Hook Pagure CI activated',
                output.data)

            output = self.app.get('/test/settings/Pagure CI')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>Pagure CI settings</h3>' in output.data)
            self.assertIn(
                '<td><label for="ci_url">URL to the project on the CI '
                'service</label></td>' , output.data)
            self.assertTrue(
                '<input checked id="active" name="active" type="checkbox" value="y">'
                in output.data)

            # De-activate the hook
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Hook Pagure CI inactived',
                output.data)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output.data)

            output = self.app.get('/test/settings/Pagure CI')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>Pagure CI settings</h3>' in output.data)
            self.assertIn(
                '<td><label for="ci_url">URL to the project on the CI '
                'service</label></td>' , output.data)
            self.assertIn(
                '<input id="active" name="active" type="checkbox" '
                'value="y">', output.data)

            # Missing the required ci_url
            data = {'csrf_token': csrf_token, 'active': 'y'}

            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertIn('<h3>Pagure CI settings</h3>', output.data)
            self.assertFalse(
                '</button>\n                      Hook activated' in output.data)
            self.assertIn(
                '<td><input id="ci_url" name="ci_url" type="text" value="">'
                '</td>\n<td class="errors">This field is required.</td>',
                output.data)
            self.assertIn(
                '<input checked id="active" name="active" type="checkbox" '
                'value="y">', output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskPluginPagureCItests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
