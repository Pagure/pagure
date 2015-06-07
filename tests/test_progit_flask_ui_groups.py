# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

import json
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskGroupstests(tests.Modeltests):
    """ Tests for flask groups controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskGroupstests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.groups.SESSION = self.session
        pagure.ui.repo.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = tests.HERE
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            tests.HERE, 'requests')
        self.app = pagure.APP.test_client()

    def test_group_lists(self):
        """ Test the group_lists endpoint. """
        output = self.app.get('/groups')
        self.assertIn('<h2>Groups</h2>', output.data)
        self.assertIn('<p>0 groups.</p>', output.data)

    def test_add_group(self):
        """ Test the add_group endpoint. """
        output = self.app.get('/group/add')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/group/add')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/group/add')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<h2>Create group</h2>', output.data)
            self.assertNotIn(
                '<option value="admin">admin</option>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
            }

            # Insufficient input
            output = self.app.post('/group/add', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<h2>Create group</h2>', output.data)
            self.assertEqual(output.data.count(
                'This field is required.'), 1)

            data = {
                'group_name': 'test group',
            }

            # Missing CSRF
            output = self.app.post('/group/add', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<h2>Create group</h2>', output.data)
            self.assertEqual(output.data.count(
                'This field is required.'), 0)

            data['csrf_token'] = csrf_token

            # Space in the group
            output = self.app.post(
                '/group/add', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<h2>Create group</h2>', output.data)
            self.assertIn(
                '<li class="error">Spaces are not allowed in group names: '
                'test group</li>' , output.data)

            # All good
            data['group_name'] = 'test_group'
            output = self.app.post(
                '/group/add', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="message">User `pingou` added to the group '
                '`test_group`.</li>', output.data)
            self.assertIn(
                '<li class="message">Group `test_group` created.</li>',
                output.data)
            self.assertIn('<h2>Groups</h2>', output.data)
            self.assertIn('<p>1 groups.</p>', output.data)

        user = tests.FakeUser(
            username='pingou',
            groups=pagure.APP.config['ADMIN_GROUP'])
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/group/add')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<h2>Create group</h2>', output.data)
            self.assertIn('<option value="admin">admin</option>', output.data)

            data = {
                'group_name': 'test_admin_group',
                'group_type': 'admin',
                'csrf_token': csrf_token,
            }

            # All good
            output = self.app.post(
                '/group/add', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="message">User `pingou` added to the group '
                '`test_admin_group`.</li>', output.data)
            self.assertIn(
                '<li class="message">Group `test_admin_group` created.</li>',
                output.data)
            self.assertIn('<h2>Groups</h2>', output.data)
            self.assertIn('<p>2 groups.</p>', output.data)

    def test_group_delete(self):
        """ Test the group_delete endpoint. """
        output = self.app.post('/group/foo/delete')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/group/foo/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<p>No groups have been created on this pagure instance '
                'yet</p>', output.data)
            self.assertIn('<p>0 groups.</p>', output.data)

        self.test_add_group()

        with tests.user_set(pagure.APP, user):
            output = self.app.post('/group/foo/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<p>1 groups.</p>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):

            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/group/bar/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="error">No group `bar` found</li>', output.data)
            self.assertIn('<p>1 groups.</p>', output.data)

            output = self.app.post(
                '/group/test_group/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="error">You are not allowed to delete the group '
                'test_group</li>', output.data)
            self.assertIn('<p>1 groups.</p>', output.data)

        user.username = 'bar'
        with tests.user_set(pagure.APP, user):

            output = self.app.post(
                '/group/test_group/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            output = self.app.post(
                '/group/test_group/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="message">Group `test_group` has been deleted'
                '</li>', output.data)
            self.assertIn('<p>0 groups.</p>', output.data)

    def test_view_group(self):
        """ Test the view_group endpoint. """
        output = self.app.get('/group/foo')
        self.assertEqual(output.status_code, 404)

        self.test_add_group()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/group/test_group')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<h2>Group: test_group</h2>', output.data)

            output = self.app.get('/group/test_admin_group')
            self.assertEqual(output.status_code, 404)

        user = tests.FakeUser(
            username='pingou',
            groups=pagure.APP.config['ADMIN_GROUP'])
        with tests.user_set(pagure.APP, user):
            # Admin can see group of type admins
            output = self.app.get('/group/test_admin_group')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<h2>Group: test_admin_group</h2>', output.data)
            self.assertEqual(output.data.count('<a href="/user/'), 2)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # No CSRF
            data = {
                'user': 'bar'
            }

            output = self.app.post('/group/test_admin_group', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<h2>Group: test_admin_group</h2>', output.data)
            self.assertEqual(output.data.count('<a href="/user/'), 2)

            # Invalid user
            data = {
                'user': 'bar',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/group/test_admin_group', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="error">No user `bar` found</li>', output.data)
            self.assertIn('<h2>Group: test_admin_group</h2>', output.data)
            self.assertEqual(output.data.count('<a href="/user/'), 2)

            # All good
            data = {
                'user': 'foo',
                'csrf_token': csrf_token,
            }
            output = self.app.post('/group/test_admin_group', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="message">User `foo` added to the group '
                '`test_admin_group`.</li>', output.data)
            self.assertIn('<h2>Group: test_admin_group</h2>', output.data)
            self.assertEqual(output.data.count('<a href="/user/'), 3)

    def test_group_user_delete(self):
        """ Test the group_user_delete endpoint. """
        output = self.app.post('/group/foo/bar/delete')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post(
                '/group/foo/bar/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        self.test_add_group()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post(
                '/group/test_group/bar/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<h2>Group: test_group</h2>', output.data)
            self.assertEqual(output.data.count('<a href="/user/'), 2)

            output = self.app.get('/new/')
            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'csrf_token': csrf_token}

            output = self.app.post(
                '/group/test_group/bar/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="error">No user `bar` found</li>', output.data)
            self.assertIn('<h2>Group: test_group</h2>', output.data)
            self.assertEqual(output.data.count('<a href="/user/'), 2)

            output = self.app.post(
                '/group/test_group/foo/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="error">Could not find user username</li>',
                output.data)
            self.assertIn('<h2>Group: test_group</h2>', output.data)
            self.assertEqual(output.data.count('<a href="/user/'), 2)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            # User not in the group
            output = self.app.post(
                '/group/test_group/foo/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="error">User `foo` could not be found in the '
                'group `test_group`</li>', output.data)
            self.assertIn('<h2>Group: test_group</h2>', output.data)
            self.assertEqual(output.data.count('<a href="/user/'), 2)

            # Cannot delete creator
            output = self.app.post(
                '/group/test_group/foo/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="error">User `foo` could not be found in the '
                'group `test_group`</li>', output.data)
            self.assertIn('<h2>Group: test_group</h2>', output.data)
            self.assertEqual(output.data.count('<a href="/user/'), 2)

            # Add user foo
            data = {
                'user': 'foo',
                'csrf_token': csrf_token,
            }
            output = self.app.post('/group/test_group', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="message">User `foo` added to the group '
                '`test_group`.</li>', output.data)
            self.assertIn('<h2>Group: test_group</h2>', output.data)
            self.assertEqual(output.data.count('<a href="/user/'), 3)

            output = self.app.post(
                '/group/test_group/foo/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="message">User `foo` removed from the group '
                '`test_group`</li>', output.data)
            self.assertIn('<h2>Group: test_group</h2>', output.data)
            self.assertEqual(output.data.count('<a href="/user/'), 2)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskGroupstests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
