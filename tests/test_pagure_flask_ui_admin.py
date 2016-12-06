# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

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


class PagureFlaskAdmintests(tests.Modeltests):
    """ Tests for flask admin controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskAdmintests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.filters.SESSION = self.session
        pagure.ui.repo.SESSION = self.session
        pagure.ui.admin.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = self.path
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            self.path, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            self.path, 'docs')
        self.app = pagure.APP.test_client()

    def test_admin_index(self):
        """ Test the admin_index endpoint. """

        output = self.app.get('/admin')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/admin', follow_redirects=True)
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                '</button>\n                      Access restricted',
                 output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/admin', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Access restricted',
                 output.data)

        user = tests.FakeUser(
            username='pingou',
            groups=pagure.APP.config['ADMIN_GROUP'])
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/admin', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Admin section</h2>' in output.data)
            self.assertTrue('Re-generate gitolite ACLs file' in output.data)
            self.assertTrue(
                'Re-generate user ssh key files' in output.data)

    @patch('pagure.lib.git.write_gitolite_acls')
    def test_admin_generate_acl(self, wga):
        """ Test the admin_generate_acl endpoint. """
        wga.return_value = True

        output = self.app.get('/admin/gitolite')
        self.assertEqual(output.status_code, 404)

        output = self.app.post('/admin/gitolite')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/admin/gitolite', follow_redirects=True)
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                '</button>\n                      Access restricted',
                 output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/admin/gitolite', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Access restricted',
                 output.data)

        user = tests.FakeUser(
            username='pingou',
            groups=pagure.APP.config['ADMIN_GROUP'])
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/admin/gitolite', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Admin section</h2>' in output.data)
            self.assertTrue('Re-generate gitolite ACLs file' in output.data)
            self.assertTrue(
                'Re-generate user ssh key files' in output.data)
            self.assertFalse(
                '<li class="message">Gitolite ACLs updated</li>'
                in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/admin/gitolite', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Admin section</h2>' in output.data)
            self.assertTrue('Re-generate gitolite ACLs file' in output.data)
            self.assertTrue(
                'Re-generate user ssh key files' in output.data)
            self.assertTrue(
                '</button>\n                      Gitolite ACLs updated'
                in output.data)

    @patch('pagure.generate_user_key_files')
    def test_admin_refresh_ssh(self, gakf):
        """ Test the admin_refresh_ssh endpoint. """
        gakf.return_value = True

        output = self.app.get('/admin/ssh')
        self.assertEqual(output.status_code, 404)

        output = self.app.post('/admin/ssh')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/admin/ssh', follow_redirects=True)
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                '</button>\n                      Access restricted',
                 output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/admin/ssh', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Access restricted',
                 output.data)

        user = tests.FakeUser(
            username='pingou',
            groups=pagure.APP.config['ADMIN_GROUP'])
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/admin/ssh', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Admin section</h2>' in output.data)
            self.assertTrue('Re-generate gitolite ACLs file' in output.data)
            self.assertTrue(
                'Re-generate user ssh key files' in output.data)
            self.assertFalse(
                '<li class="message">Authorized file updated</li>'
                in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/admin/ssh', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Admin section</h2>' in output.data)
            self.assertTrue('Re-generate gitolite ACLs file' in output.data)
            self.assertTrue(
                'Re-generate user ssh key files' in output.data)
            self.assertTrue(
                '</button>\n                      User key files regenerated'
                in output.data)

    def test_admin_generate_hook_token(self):
        """ Test the admin_generate_hook_token endpoint. """

        output = self.app.get('/admin/hook_token')
        self.assertEqual(output.status_code, 404)

        output = self.app.post('/admin/hook_token')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/admin/hook_token', follow_redirects=True)
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                '</button>\n                      Access restricted',
                 output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/admin/hook_token', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Access restricted',
                 output.data)

        user = tests.FakeUser(
            username='pingou',
            groups=pagure.APP.config['ADMIN_GROUP'])
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/admin/hook_token', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Admin section</h2>' in output.data)
            self.assertTrue('Re-generate gitolite ACLs file' in output.data)
            self.assertTrue(
                'Re-generate user ssh key files' in output.data)
            self.assertTrue(
                'Re-generate hook-token for every projects' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]
            data = {'csrf_token': csrf_token}

            output = self.app.post(
                '/admin/hook_token', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Admin section</h2>' in output.data)
            self.assertTrue('Re-generate gitolite ACLs file' in output.data)
            self.assertTrue(
                'Re-generate user ssh key files' in output.data)
            self.assertTrue(
                'Re-generate hook-token for every projects' in output.data)
            self.assertTrue(
                '</button>\n                      Hook token all re-generated'
                in output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagureFlaskAdmintests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
