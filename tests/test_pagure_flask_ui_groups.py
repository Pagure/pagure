# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

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

import pagure.config
import tests


class PagureFlaskGroupstests(tests.Modeltests):
    """ Tests for flask groups controller of pagure """

    def test_group_lists(self):
        """ Test the group_lists endpoint. """
        output = self.app.get('/groups')
        self.assertIn(
            '<h3 class="font-weight-bold">\n'
            '      Groups <span class="badge badge-secondary">0</span>',
            output.get_data(as_text=True))

    def test_add_group(self):
        """ Test the add_group endpoint. """
        output = self.app.get('/group/add')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/group/add')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/group/add')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new group</strong>', output.get_data(as_text=True))
            self.assertNotIn(
                '<option value="admin">admin</option>', output.get_data(as_text=True))

            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
            }

            # Insufficient input
            output = self.app.post('/group/add', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new group</strong>', output.get_data(as_text=True))
            self.assertEqual(output.get_data(as_text=True).count(
                'This field is required.'), 3)

            data = {
                'group_name': 'test_group',
                'display_name': 'Test Group',
                'description': 'This is a group for the tests',
            }

            # Missing CSRF
            output = self.app.post('/group/add', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new group</strong>', output.get_data(as_text=True))
            self.assertEqual(output.get_data(as_text=True).count(
                'This field is required.'), 0)

            data['csrf_token'] = csrf_token

            # All good
            output = self.app.post(
                '/group/add', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'User `pingou` added to '
                'the group `test_group`.', output.get_data(as_text=True))
            self.assertIn(
                'Group `test_group` created.',
                output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="font-weight-bold">\n'
                '      Groups <span class="badge badge-secondary">1</span>',
                output.get_data(as_text=True))

        user = tests.FakeUser(
            username='pingou',
            groups=pagure.config.config['ADMIN_GROUP'])
        with tests.user_set(self.app.application, user):
            output = self.app.get('/group/add')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new group</strong>', output.get_data(as_text=True))
            self.assertIn('<option value="admin">admin</option>', output.get_data(as_text=True))

            data = {
                'group_name': 'test_admin_group',
                'group_type': 'admin',
                'display_name': 'Test Admin Group',
                'description': 'This is another group for the tests',
                'csrf_token': csrf_token,
            }

            # All good
            output = self.app.post(
                '/group/add', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'User `pingou` added to '
                'the group `test_admin_group`.', output.get_data(as_text=True))
            self.assertIn(
                'Group `test_admin_group` '
                'created.',output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="font-weight-bold">\n'
                '      Groups <span class="badge badge-secondary">2</span>',
                output.get_data(as_text=True))

    def test_edit_group(self):
        """ Test the edit_group endpoint. """

        output = self.app.get('/group/test_group/edit')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/group/test_group/edit')
            self.assertEqual(output.status_code, 404)
            self.assertIn('<p>Group not found</p>', output.get_data(as_text=True))

        self.test_add_group()

        user.username = 'foo'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/group/foo/edit')
            self.assertEqual(output.status_code, 404)
            self.assertIn('<p>Group not found</p>', output.get_data(as_text=True))

            output = self.app.get('/group/test_group/edit')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Edit group: test_group - Pagure</title>',
                output.get_data(as_text=True))
            self.assertIn(
                '<form action="/group/test_group/edit" method="post">',
                output.get_data(as_text=True))
            self.assertIn(
                '<strong><label for="description">Description'
                '</label></strong>', output.get_data(as_text=True))

            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Missing CSRF
            data = {
                'group_name': 'test_group',
                'display_name': 'Test Group edited',
                'description': 'This is a group for the tests edited',
            }

            output = self.app.post(
                '/group/test_group/edit', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Edit group: test_group - Pagure</title>',
                output.get_data(as_text=True))
            self.assertIn(
                '<form action="/group/test_group/edit" method="post">',
                output.get_data(as_text=True))
            self.assertIn(
                '<strong><label for="description">Description'
                '</label></strong>', output.get_data(as_text=True))

            # User not allowed
            data['csrf_token'] = csrf_token

            output = self.app.post(
                '/group/test_group/edit', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Group test_group - Pagure</title>',
                output.get_data(as_text=True))
            self.assertIn(
                'You are not '
                'allowed to edit this group', output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Group</h3>',
                output.get_data(as_text=True))

        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            # Invalid repo
            output = self.app.post(
                '/group/bar/edit', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)
            self.assertIn('<p>Group not found</p>', output.get_data(as_text=True))

            output = self.app.post(
                '/group/test_group/edit', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Group test_group - Pagure</title>', output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Group edited</h3>',
                output.get_data(as_text=True))
            self.assertIn(
                'Group &#34;Test Group edited&#34; (test_group) edited',
                output.get_data(as_text=True))

    def test_group_delete(self):
        """ Test the group_delete endpoint. """
        output = self.app.post('/group/foo/delete')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post('/group/foo/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<p>No groups have been created on this pagure instance '
                'yet</p>', output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="font-weight-bold">\n'
                '      Groups <span class="badge badge-secondary">0</span>',
                output.get_data(as_text=True))

        self.test_add_group()

        with tests.user_set(self.app.application, user):
            output = self.app.post('/group/foo/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<h3 class="font-weight-bold">\n'
                '      Groups <span class="badge badge-secondary">1</span>',
                output.get_data(as_text=True))

            output = self.app.get('/new/')
            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

        user.username = 'foo'
        with tests.user_set(self.app.application, user):

            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/group/bar/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'No group `bar` found',
                output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="font-weight-bold">\n'
                '      Groups <span class="badge badge-secondary">1</span>',
                output.get_data(as_text=True))

            output = self.app.post(
                '/group/test_group/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'You are not allowed to '
                'delete the group test_group', output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="font-weight-bold">\n'
                '      Groups <span class="badge badge-secondary">1</span>',
                output.get_data(as_text=True))

        user.username = 'bar'
        with tests.user_set(self.app.application, user):

            output = self.app.post(
                '/group/test_group/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        user.username = 'pingou'
        with tests.user_set(self.app.application, user):

            output = self.app.post(
                '/group/test_group/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'Group `test_group` has '
                'been deleted', output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="font-weight-bold">\n'
                '      Groups <span class="badge badge-secondary">0</span>',
                output.get_data(as_text=True))

    def test_view_group(self):
        """ Test the view_group endpoint. """
        output = self.app.get('/group/foo')
        self.assertEqual(output.status_code, 404)

        self.test_add_group()

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/group/test_group')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Group</h3>',
                output.get_data(as_text=True))

            output = self.app.get('/group/test_admin_group')
            self.assertEqual(output.status_code, 404)

        user = tests.FakeUser(
            username='pingou',
            groups=pagure.config.config['ADMIN_GROUP'])
        with tests.user_set(self.app.application, user):
            # Admin can see group of type admins
            output = self.app.get('/group/test_admin_group')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Admin Group</h3>',
                output.get_data(as_text=True))
            self.assertEqual(
                output.get_data(as_text=True).count('<a href="/user/'), 2)

            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # No CSRF
            data = {
                'user': 'bar'
            }

            output = self.app.post('/group/test_admin_group', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Admin Group</h3>',
                output.get_data(as_text=True))
            self.assertEqual(
                output.get_data(as_text=True).count('<a href="/user/'), 2)

            # Invalid user
            data = {
                'user': 'bar',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/group/test_admin_group', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'No user `bar` found',
                output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Admin Group</h3>',
                output.get_data(as_text=True))
            self.assertEqual(
                output.get_data(as_text=True).count('<a href="/user/'), 2)

            # All good
            data = {
                'user': 'foo',
                'csrf_token': csrf_token,
            }
            output = self.app.post('/group/test_admin_group', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'User `foo` added to the '
                'group `test_admin_group`.', output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Admin Group</h3>',
                output.get_data(as_text=True))
            self.assertEqual(
                output.get_data(as_text=True).count('<a href="/user/'), 3)

    def test_group_user_delete(self):
        """ Test the group_user_delete endpoint. """
        output = self.app.post('/group/foo/bar/delete')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                '/group/foo/bar/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        self.test_add_group()

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                '/group/test_group/bar/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Group</h3>',
                output.get_data(as_text=True))
            self.assertEqual(
                output.get_data(as_text=True).count('<a href="/user/'), 2)

            output = self.app.get('/new/')
            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'csrf_token': csrf_token}

            output = self.app.post(
                '/group/test_group/bar/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'No user `bar` found',
                output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Group</h3>',
                output.get_data(as_text=True))
            self.assertEqual(
                output.get_data(as_text=True).count('<a href="/user/'), 2)

            output = self.app.post(
                '/group/test_group/foo/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'Could not find user '
                'username', output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Group</h3>',
                output.get_data(as_text=True))
            self.assertEqual(
                output.get_data(as_text=True).count('<a href="/user/'), 2)

        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            # User not in the group
            output = self.app.post(
                '/group/test_group/foo/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'User `foo` could not be '
                'found in the group `test_group`', output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Group</h3>',
                output.get_data(as_text=True))
            self.assertEqual(
                output.get_data(as_text=True).count('<a href="/user/'), 2)

            # Cannot delete creator
            output = self.app.post(
                '/group/test_group/foo/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'User `foo` could not be '
                'found in the group `test_group`', output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Group</h3>',
                output.get_data(as_text=True))
            self.assertEqual(
                output.get_data(as_text=True).count('<a href="/user/'), 2)

            # Add user foo
            data = {
                'user': 'foo',
                'csrf_token': csrf_token,
            }
            output = self.app.post('/group/test_group', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'User `foo` added to the '
                'group `test_group`.', output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Group</h3>',
                output.get_data(as_text=True))
            self.assertEqual(
                output.get_data(as_text=True).count('<a href="/user/'), 3)

            output = self.app.post(
                '/group/test_group/foo/delete', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'User `foo` removed from '
                'the group `test_group`', output.get_data(as_text=True))
            self.assertIn(
                '<h3 class="mb-0 font-weight-bold">Test Group</h3>',
                output.get_data(as_text=True))
            self.assertEqual(
                output.get_data(as_text=True).count('<a href="/user/'), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
