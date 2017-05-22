# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import tempfile
import os

from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests


class PagureFlaskGiveRepotests(tests.Modeltests):
    """ Tests for give a project on pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskGiveRepotests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.filters.SESSION = self.session
        pagure.ui.repo.SESSION = self.session

        pagure.APP.config['VIRUS_SCAN_ATTACHMENTS'] = False
        pagure.APP.config['UPLOAD_FOLDER_URL'] = '/releases/'
        pagure.APP.config['UPLOAD_FOLDER_PATH'] = os.path.join(
            self.path, 'releases')
        self.app = pagure.APP.test_client()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

    def _check_user(self, user='pingou'):
        project = pagure.get_authorized_project(
            self.session, project_name='test')
        self.assertEqual(project.user.user, user)

    def test_give_project_no_project(self):
        """ Test the give_project endpoint. """

        # No such project
        output = self.app.post('/test42/give')
        self.assertEqual(output.status_code, 404)

    def test_give_project_no_csrf(self):
        """ Test the give_project endpoint. """

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            self._check_user()

            # Missing CSRF
            data = {
                'user': 'foo',
            }

            output = self.app.post(
                '/test/give', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Overview - test - Pagure</title>',
                output.data)

            self._check_user()

    def test_give_project_invalid_user(self):
        """ Test the give_project endpoint. """

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            csrf_token = self.get_csrf()

            self._check_user()

            # Invalid user
            data = {
                'user': 'foobar',
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/test/give', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                '<p>No such user foobar found</p>',
                output.data)

            self._check_user()

    def test_give_project_not_owner(self):
        """ Test the give_project endpoint. """

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            csrf_token = self.get_csrf()

            self._check_user()

            # User isn't the admin
            data = {
                'user': 'foo',
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/test/give', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 403)
            self.assertIn(
                '<p>You are not allowed to change the settings for this '
                'project</p>', output.data)

            self._check_user()

    def test_give_project_not_admin(self):
        """ Test the give_project endpoint. """

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            csrf_token = self.get_csrf()

            self._check_user()

            # User isn't the admin
            data = {
                'user': 'foo',
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/test/give', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 403)
            self.assertIn(
                '<p>You are not allowed to change the settings for this '
                'project</p>', output.data)

            self._check_user()

    def test_give_project_not_owner(self):
        """ Test the give_project endpoint. """
        project = pagure.get_authorized_project(
            self.session, project_name='test')

        msg = pagure.lib.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='admin')
        self.session.commit()
        self.assertEqual(msg, 'User added')

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            csrf_token = self.get_csrf()

            self._check_user()

            # User isn't the owner
            data = {
                'user': 'foo',
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/test/give', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 403)
            self.assertIn(
                '<p>You are not allowed to give this project</p>',
                output.data)

            self._check_user()

    @patch.dict('pagure.APP.config', {'PAGURE_ADMIN_USERS': 'foo'})
    def test_give_project_not_owner_but_admin(self):
        """ Test the give_project endpoint.

        Test giving a project when the person giving the project is a pagure
        admin (instance wide admin) but not a project admin.
        """

        user = tests.FakeUser()
        user.username = 'foo'
        user.cla_done = True
        user.groups = ['foo']
        with tests.user_set(pagure.APP, user):
            csrf_token = self.get_csrf()

            self._check_user()

            # User isn't the owner but is an instance admin
            data = {
                'user': 'foo',
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/test/give', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      The project has been '
                'transferred to foo\n',
                output.data)

            self._check_user('foo')

    @patch.dict('pagure.APP.config', {'PAGURE_ADMIN_USERS': 'foo'})
    def test_give_project(self):
        """ Test the give_project endpoint. """

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            csrf_token = self.get_csrf()

            self._check_user()

            # All good
            data = {
                'user': 'foo',
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/test/give', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      The project has been '
                'transferred to foo\n',
                output.data)

            self._check_user('foo')


if __name__ == '__main__':
    unittest.main(verbosity=2)
