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

        pagure.APP.config['GIT_FOLDER'] = tests.HERE
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = pagure.APP.test_client()

    def test_plugin_pagure_ci(self):
        """ Test the pagure ci plugin on/off endpoint. """

        tests.create_projects(self.session)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/settings/Pagure CI')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>Pagure CI settings</h3>' in output.data)
            self.assertTrue(
                '<td><label for="pagure_name">Name of project in Pagure</label></td>'
                in output.data)
            self.assertTrue(
                '<td><label for="jenkins_name">Name of project in Jenkins</label></td>'
                in output.data)
            self.assertTrue(
                '<td><label for="jenkins_url">Jenkins URL</label></td>'
                in output.data)
            self.assertTrue(
                '<td><label for="jenkins_token">Jenkins token</label></td>'
                in output.data)
            self.assertTrue(
                '<input id="active" name="active" type="checkbox" value="y">'
                in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post('/test/settings/Pagure CI', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>Pagure CI settings</h3>' in output.data)
            self.assertTrue(
                '<td><label for="pagure_name">Name of project in Pagure</label></td>'
                in output.data)
            self.assertTrue(
                '<td><label for="jenkins_name">Name of project in Jenkins</label></td>'
                in output.data)
            self.assertTrue(
                '<td><label for="jenkins_url">Jenkins URL</label></td>'
                in output.data)
            self.assertTrue(
                '<td><label for="jenkins_token">Jenkins token</label></td>'
                in output.data)
            self.assertTrue(
                '<input id="active" name="active" type="checkbox" value="y">'
                in output.data)

            # Activate hook
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
                'pagure_name': 'test',
                'jenkins_name': 'jenkins_test',
                'jenkins_url': 'https://jenkins.fedoraproject.org',
                'jenkins_token': 'BEEFCAFE'
            }
            # No git found
            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            tests.create_projects_git(tests.HERE)

            data = {'csrf_token': csrf_token}
            # With the git repo
            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>Pagure CI settings</h3>' in output.data)
            self.assertFalse(
                '</button>\n                      Hook activated' in output.data)
            self.assertTrue(
                '<td><input id="pagure_name" name="pagure_name" type="text" value=""></td>'
                '\n<td class="errors">This field is required.</td>'
                in output.data)
            self.assertTrue(
                '<input id="active" name="active" type="checkbox" value="y">' in output.data)

            output = self.app.get('/test/settings/Pagure CI')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>Pagure CI settings</h3>' in output.data)
            self.assertTrue(
                '<td><label for="pagure_name">Name of project in Pagure</label></td>'
                in output.data)
            self.assertTrue(
                '<td><label for="jenkins_name">Name of project in Jenkins</label></td>'
                in output.data)
            self.assertTrue(
                '<td><label for="jenkins_url">Jenkins URL</label></td>'
                in output.data)
            self.assertTrue(
                '<td><label for="jenkins_token">Jenkins token</label></td>'
                in output.data)
            self.assertTrue(
                '<input checked id="active" name="active" type="checkbox" value="y">'
                in output.data)

            # Missing the required
            data = {'csrf_token': csrf_token, 'active': 'y'}

            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>Pagure CI settings</h3>' in output.data)
            self.assertFalse(
                '</button>\n                      Hook activated' in output.data)
            self.assertTrue(
                '<td><input id="pagure_name" name="pagure_name" type="text" value=""></td>'
                '\n<td class="errors">This field is required.</td>'
                in output.data)
            self.assertTrue(
                '<input checked id="active" name="active" type="checkbox" '
                'value="y">' in output.data)

            # Activate hook
            data = {
                'csrf_token': csrf_token,
                'active': 'y',
                'pagure_name': 'test',
                'jenkins_name': 'jenkins_test',
                'jenkins_url': 'https://jenkins.fedoraproject.org',
                'jenkins_token': 'BEEFCAFE'
            }

            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output.data)
            self.assertTrue(
                '</button>\n                      Hook Pagure CI activated' in output.data)

            output = self.app.get('/test/settings/Pagure CI')
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertTrue('<h3>Pagure CI settings</h3>' in output.data)
            self.assertTrue(
                '<td><label for="pagure_name">Name of project in Pagure</label></td>'
                in output.data)
            self.assertTrue(
                '<td><input id="pagure_name" name="pagure_name" type="text" value="test"></td>'
                in output.data)
            self.assertTrue(
                '<td><label for="jenkins_name">Name of project in Jenkins</label></td>'
                in output.data)
            self.assertTrue(
                '<td><input id="jenkins_name" name="jenkins_name" type="text" value="jenkins_test"></td>'
                in output.data)
            self.assertTrue(
                '<input checked id="active" name="active" type="checkbox" value="y">'
                in output.data)

            # De-Activate hook
            data = {
                'csrf_token': csrf_token,
                'pagure_name': 'test',
                'jenkins_name': 'jenkins_test',
                'jenkins_url': 'https://jenkins.fedoraproject.org',
                'jenkins_token': 'BEEFCAFE'
            }
            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '</button>\n                      Hook Pagure CI inactived' in output.data)

            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskPluginPagureCItests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
