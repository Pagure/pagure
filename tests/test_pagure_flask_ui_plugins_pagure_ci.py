# -*- coding: utf-8 -*-

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']

import unittest
import sys
import os

import pagure.lib
import tests


class PagureFlaskPluginPagureCItests(tests.SimplePagureTest):
    """ Tests for flask plugins controller of pagure """

    def test_plugin_pagure_ci(self):
        """ Test the pagure ci plugin on/off endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/settings/Pagure CI')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Pagure CI settings</h3>', output_text)
            self.assertIn(
                '<label for="ci_url">URL to the project on the CI '
                'service</label>', output_text)
            self.assertIn(
                '<label for="ci_job">Name of the job to trigger'
                '</label>', output_text)
            self.assertIn(
                '<input class="form-control" id="active_commit" '
                'name="active_commit" type="checkbox" value="y">', output_text)
            self.assertIn(
                '<input class="form-control" id="active_pr" '
                'name="active_pr" type="checkbox" value="y">', output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}

            output = self.app.post('/test/settings/Pagure CI', data=data)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Pagure CI settings</h3>', output_text)
            self.assertIn(
                '<label for="ci_url">URL to the project on the CI '
                'service</label>', output_text)
            self.assertIn(
                '<label for="ci_job">Name of the job to trigger'
                '</label>', output_text)
            self.assertIn(
                '<input class="form-control" id="active_commit" '
                'name="active_commit" type="checkbox" value="y">', output_text)
            self.assertIn(
                '<input class="form-control" id="active_pr" '
                'name="active_pr" type="checkbox" value="y">', output_text)

            # Activate hook
            data = {
                'active_commit': 'y',
                'ci_url': 'https://jenkins.fedoraproject.org',
                'ci_type': 'jenkins',
                'ci_job': 'test/job'
            }
            # CSRF Token missing
            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Pagure CI settings</h3>', output_text)
            self.assertIn(
                '<label for="ci_url">URL to the project on the CI '
                'service</label>', output_text)
            self.assertIn(
                '<label for="ci_job">Name of the job to trigger'
                '</label>', output_text)
            self.assertIn(
                '<input checked class="form-control" id="active_commit" '
                'name="active_commit" type="checkbox" value="y">', output_text)
            self.assertIn(
                '<input class="form-control" id="active_pr" '
                'name="active_pr" type="checkbox" value="y">', output_text)

            data['csrf_token'] = csrf_token

            # Activate hook
            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output_text)
            self.assertIn('<h3>Settings for test</h3>', output_text)
            self.assertIn(
                '</button>\n                      Hook Pagure CI activated',
                output_text)

            output = self.app.get('/test/settings/Pagure CI')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Pagure CI settings</h3>', output_text)
            self.assertIn(
                '<label for="ci_url">URL to the project on the CI '
                'service</label>', output_text)
            self.assertIn(
                '<label for="ci_job">Name of the job to trigger'
                '</label>', output_text)
            self.assertIn(
                '<input checked class="form-control" id="active_commit" '
                'name="active_commit" type="checkbox" value="y">', output_text)
            self.assertIn(
                '<pre>\nhttp://localhost.localdomain/api/0/ci/jenkins/test/',
                output_text)

            # De-activate the hook
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '</button>\n                      Hook Pagure CI deactivated',
                output_text)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output_text)

            output = self.app.get('/test/settings/Pagure CI')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Pagure CI settings</h3>', output_text)
            self.assertIn(
                '<label for="ci_url">URL to the project on the CI '
                'service</label>', output_text)
            self.assertIn(
                '<label for="ci_job">Name of the job to trigger'
                '</label>', output_text)
            self.assertIn(
                '<input class="form-control" id="active_commit" '
                'name="active_commit" type="checkbox" value="y">', output_text)

            # Missing the required ci_url
            data = {'csrf_token': csrf_token, 'active_commit': 'y'}

            output = self.app.post(
                '/test/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1      </div>', output_text)
            self.assertIn('<h3>Pagure CI settings</h3>', output_text)
            self.assertFalse(
                '</button>\n                      Hook activated' in output_text)

            if self.get_wtforms_version() >= (2, 2):
                self.assertIn(
                    '<td><input class="form-control" id="ci_url" '
                    'name="ci_url" required type="text" value="">'
                    '</td>\n<td class="errors">This field is required.</td>',
                    output_text)
                self.assertIn(
                    '<td><input class="form-control" id="ci_job" '
                    'name="ci_job" required type="text" value="">'
                    '</td>\n<td class="errors">This field is required.</td>',
                    output_text)
            else:
                self.assertIn(
                    '<td><input class="form-control" id="ci_url" '
                    'name="ci_url" type="text" value="">'
                    '</td>\n<td class="errors">This field is required.</td>',
                    output_text)
                self.assertIn(
                    '<td><input class="form-control" id="ci_job" '
                    'name="ci_job" type="text" value="">'
                    '</td>\n<td class="errors">This field is required.</td>',
                    output_text)
            self.assertIn(
                '<input checked class="form-control" id="active_commit" '
                'name="active_commit" type="checkbox" value="y">', output_text)

    def test_plugin_pagure_ci_namespaced(self):
        """ Test the pagure ci plugin on/off endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/somenamespace/test3/settings/Pagure CI')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'namespaced test project      </div>', output_text)
            self.assertIn('<h3>Pagure CI settings</h3>', output_text)
            self.assertIn(
                '<label for="ci_url">URL to the project on the CI '
                'service</label>', output_text)
            self.assertIn(
                '<label for="ci_job">Name of the job to trigger'
                '</label>', output_text)
            self.assertIn(
                '<input class="form-control" id="active_pr" name="active_pr" '
                'type="checkbox" value="y">', output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Activate hook
            data = {
                'active_pr': 'y',
                'ci_url': 'https://jenkins.fedoraproject.org',
                'ci_job': 'test/job',
                'ci_type': 'jenkins',
                'csrf_token': csrf_token,
            }

            # Activate hook
            output = self.app.post(
                '/somenamespace/test3/settings/Pagure CI', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'namespaced test project      </div>', output_text)
            self.assertIn(
                '<title>Settings - somenamespace/test3 - Pagure</title>',
                output_text)
            self.assertIn(
                '<h3>Settings for somenamespace/test3</h3>',
                output_text)
            self.assertIn(
                '</button>\n                      Hook Pagure CI activated',
                output_text)

            output = self.app.get('/somenamespace/test3/settings/Pagure CI')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'namespaced test project      </div>', output_text)
            self.assertIn('<h3>Pagure CI settings</h3>', output_text)
            self.assertIn(
                '<label for="ci_url">URL to the project on the CI '
                'service</label>', output_text)
            self.assertIn(
                '<label for="ci_job">Name of the job to trigger'
                '</label>', output_text)
            self.assertIn(
                '<input checked class="form-control" id="active_pr" name="active_pr" '
                'type="checkbox" value="y">', output_text)
            self.assertIn(
                '<pre>\nhttp://localhost.localdomain/api/0/ci/jenkins/somenamespace/test3/',
                output_text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
