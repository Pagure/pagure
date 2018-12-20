# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

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
import pagure.lib.query
import tests


class PagureFlaskGiveRepotests(tests.SimplePagureTest):
    """ Tests for give a project on pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskGiveRepotests, self).setUp()

        pagure.config.config['VIRUS_SCAN_ATTACHMENTS'] = False
        pagure.config.config['UPLOAD_FOLDER_URL'] = '/releases/'
        pagure.config.config['UPLOAD_FOLDER_PATH'] = os.path.join(
            self.path, 'releases')

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        self._check_user(user='pingou')

    def _check_user(self, user='pingou'):
        self.session.commit()
        project = pagure.lib.query.get_authorized_project(
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
        with tests.user_set(self.app.application, user):

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
                output.get_data(as_text=True))

            self._check_user()

    def test_give_project_invalid_user(self):
        """ Test the give_project endpoint. """

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
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
                output.get_data(as_text=True))

            self._check_user()

    def test_give_project_no_user(self):
        """ Test the give_project endpoint. """

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            self._check_user()

            # No user
            data = {
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/test/give', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)
            self.assertIn('<p>No user specified</p>', output.get_data(as_text=True))

            self._check_user()

    def test_give_project_not_owner(self):
        """ Test the give_project endpoint. """

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(self.app.application, user):
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
                'project</p>', output.get_data(as_text=True))

            self._check_user()

    def test_give_project_not_admin(self):
        """ Test the give_project endpoint. """

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(self.app.application, user):
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
                'project</p>', output.get_data(as_text=True))

            self._check_user()

    def test_give_project_not_owner_but_is_admin(self):
        """ Test the give_project endpoint. """
        project = pagure.lib.query.get_authorized_project(
            self.session, project_name='test')

        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user='foo',
            user='pingou',
            access='admin')
        self.session.commit()
        self.assertEqual(msg, 'User added')

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(self.app.application, user):
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
                output.get_data(as_text=True))

            self._check_user()

    @patch.dict('pagure.config.config', {'PAGURE_ADMIN_USERS': 'foo'})
    @patch('pagure.lib.git.generate_gitolite_acls', MagicMock())
    def test_give_project_not_owner_but_admin(self):
        """ Test the give_project endpoint.

        Test giving a project when the person giving the project is a pagure
        admin (instance wide admin) but not a project admin.
        """

        user = tests.FakeUser()
        user.username = 'foo'
        user.cla_done = True
        user.groups = ['foo']
        with tests.user_set(self.app.application, user):
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
                'The project has been '
                'transferred to foo',
                output.get_data(as_text=True))

            self._check_user('foo')

    @patch.dict('pagure.config.config', {'PAGURE_ADMIN_USERS': 'foo'})
    @patch('pagure.lib.git.generate_gitolite_acls', MagicMock())
    def test_give_project(self):
        """ Test the give_project endpoint. """

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
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
                'The project has been '
                'transferred to foo',
                output.get_data(as_text=True))

            self._check_user('foo')
            # Make sure that the user giving the project is still an admin
            project = pagure.lib.query.get_authorized_project(
                self.session, project_name='test')
            self.assertEqual(len(project.users), 1)
            self.assertEqual(project.users[0].user, 'pingou')

    @patch.dict('pagure.config.config', {'PAGURE_ADMIN_USERS': 'foo'})
    @patch('pagure.lib.git.generate_gitolite_acls', MagicMock())
    def test_give_project_already_user(self):
        """ Test the give_project endpoint when the new main_admin is already
        a committer on the project. """

        project = pagure.lib.query._get_project(self.session, 'test')
        pagure.lib.query.add_user_to_project(
            self.session, project,
            new_user='foo',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
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
                'The project has been '
                'transferred to foo',
                output.get_data(as_text=True))

            self._check_user('foo')
            # Make sure that the user giving the project is still an admin
            project = pagure.lib.query.get_authorized_project(
                self.session, project_name='test')
            self.assertEqual(len(project.users), 1)
            self.assertEqual(project.users[0].user, 'pingou')

    @patch.dict('pagure.config.config', {'REQUIRED_GROUPS': {'*': ['packager']}})
    @patch.dict('pagure.config.config', {'PAGURE_ADMIN_USERS': 'foo'})
    @patch('pagure.lib.git.generate_gitolite_acls', MagicMock())
    def test_give_project_not_in_required_group(self):
        """ Test the give_project endpoint. """

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            self._check_user()

            # User not a packager
            data = {
                'user': 'foo',
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/test/give', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</i> This user must be in one of the following groups to '
                'be allowed to be added to this project: packager</div>',
                output.get_data(as_text=True))

            self._check_user(user='pingou')

    @patch.dict('pagure.config.config', {'REQUIRED_GROUPS': {'*': ['packager']}})
    @patch.dict('pagure.config.config', {'PAGURE_ADMIN_USERS': 'foo'})
    @patch('pagure.lib.git.generate_gitolite_acls', MagicMock())
    def test_give_project_in_required_group(self):
        """ Test the give_project endpoint. """

        # Create the packager group
        msg = pagure.lib.query.add_group(
            self.session,
            group_name='packager',
            display_name='packager group',
            description=None,
            group_type='user',
            user='pingou',
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, 'User `pingou` added to the group `packager`.')

        # Add foo to the packager group
        group = pagure.lib.query.search_groups(self.session, group_name='packager')
        msg = pagure.lib.query.add_user_to_group(
            self.session,
            username='foo',
            group=group,
            user='pingou',
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, 'User `foo` added to the group `packager`.')

        # pingou transferts test to foo
        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            self._check_user()

            # User not a packager
            data = {
                'user': 'foo',
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/test/give', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</i> The project has been transferred to foo</div>',
                output.get_data(as_text=True))

            self._check_user('foo')
            # Make sure that the user giving the project is still an admin
            project = pagure.lib.query.get_authorized_project(
                self.session, project_name='test')
            self.assertEqual(len(project.users), 1)
            self.assertEqual(project.users[0].user, 'pingou')


if __name__ == '__main__':
    unittest.main(verbosity=2)
