# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import datetime
import json
import unittest
import shutil
import sys
import tempfile
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskRepotests(tests.Modeltests):
    """ Tests for flask app controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskRepotests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.filters.SESSION = self.session
        pagure.ui.repo.SESSION = self.session

        pagure.APP.config['VIRUS_SCAN_ATTACHMENTS'] = False
        pagure.APP.config['GIT_FOLDER'] = self.path
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            self.path, 'forks')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            self.path, 'requests')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            self.path, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            self.path, 'docs')
        pagure.APP.config['UPLOAD_FOLDER_URL'] = '/releases/'
        pagure.APP.config['UPLOAD_FOLDER_PATH'] = os.path.join(
            self.path, 'releases')
        self.app = pagure.APP.test_client()

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_add_user_when_user_mngt_off(self, ast):
        """ Test the add_user endpoint when user management is turned off
        in the pagure instance """
        pagure.APP.config['ENABLE_USER_MNGT'] = False
        ast.return_value = False

        # No Git repo
        output = self.app.get('/foo/adduser')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(self.path)

        # User not logged in
        output = self.app.get('/test/adduser')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):

            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 404)

            #just get the csrf token
            pagure.APP.config['ENABLE_USER_MNGT'] = True
            output = self.app.get('/test/adduser')
            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            pagure.APP.config['ENABLE_USER_MNGT'] = False

            data = {
                'user': 'ralph',
            }

            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 404)

            data['csrf_token'] = csrf_token
            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 404)

            data['user'] = 'foo'
            tests.create_projects_git(self.path)
            output = self.app.post(
                '/test/adduser', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        pagure.APP.config['ENABLE_USER_MNGT'] = True


    @patch('pagure.ui.repo.admin_session_timedout')
    def test_add_user(self, ast):
        """ Test the add_user endpoint. """
        ast.return_value = False

        # No git repo
        output = self.app.get('/foo/adduser')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(self.path)

        # User not logged in
        output = self.app.get('/test/adduser')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 302)

            # Redirect also happens for POST request
            output = self.app.post('/test/adduser')
            self.assertEqual(output.status_code, 302)

        # Need to do this un-authentified since our fake user isn't in the DB
        # Check the message flashed during the redirect
        output = self.app.get('/')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '</button>\n                      Action canceled, try it '
            'again',output.data)

        ast.return_value = False

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Add user to the', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'user': 'ralph',
            }

            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<strong>Add user to the' in output.data)

            data['csrf_token'] = csrf_token
            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Add user to the', output.data)
            self.assertIn(
                '</button>\n                      No user &#34;ralph&#34; '
                'found', output.data)

            data['user'] = 'foo'
            output = self.app.post(
                '/test/adduser', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '</button>\n                      User added', output.data)


    @patch('pagure.ui.repo.admin_session_timedout')
    def test_add_group_project_when_user_mngt_off(self, ast):
        """ Test the add_group_project endpoint  when user management is
        turned off in the pagure instance"""
        pagure.APP.config['ENABLE_USER_MNGT'] = False
        ast.return_value = False

        # No Git repo
        output = self.app.get('/foo/addgroup')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(self.path)

        # User not logged in
        output = self.app.get('/test/addgroup')
        self.assertEqual(output.status_code, 302)

        msg = pagure.lib.add_group(
            self.session,
            group_name='foo',
            group_type='bar',
            display_name='foo group',
            description=None,
            user='pingou',
            is_admin=False,
            blacklist=pagure.APP.config['BLACKLISTED_GROUPS'],
        )
        self.session.commit()
        self.assertEqual(msg, 'User `pingou` added to the group `foo`.')

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            #just get the csrf token
            pagure.APP.config['ENABLE_USER_MNGT'] = True

            output = self.app.get('/test/addgroup')
            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]
            pagure.APP.config['ENABLE_USER_MNGT'] = False

            data = {
                'group': 'ralph',
            }

            output = self.app.post('/test/addgroup', data=data)
            self.assertEqual(output.status_code, 404)

            data['csrf_token'] = csrf_token
            output = self.app.post('/test/addgroup', data=data)
            self.assertEqual(output.status_code, 404)

            data['group'] = 'foo'
            output = self.app.post(
                '/test/addgroup', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        pagure.APP.config['ENABLE_USER_MNGT'] = True


    @patch('pagure.ui.repo.admin_session_timedout')
    def test_add_group_project(self, ast):
        """ Test the add_group_project endpoint. """
        ast.return_value = False

        # No Git repo
        output = self.app.get('/foo/addgroup')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(self.path)

        # User not logged in
        output = self.app.get('/test/addgroup')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/addgroup')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.get('/test/addgroup')
            self.assertEqual(output.status_code, 302)

            # Redirect also happens for POST request
            output = self.app.post('/test/addgroup')
            self.assertEqual(output.status_code, 302)

        # Need to do this un-authentified since our fake user isn't in the DB
        # Check the message flashed during the redirect
        output = self.app.get('/')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '</button>\n                      Action canceled, try it '
            'again', output.data)

        ast.return_value = False

        msg = pagure.lib.add_group(
            self.session,
            group_name='foo',
            display_name='foo group',
            description=None,
            group_type='bar',
            user='pingou',
            is_admin=False,
            blacklist=pagure.APP.config['BLACKLISTED_GROUPS'],
        )
        self.session.commit()
        self.assertEqual(msg, 'User `pingou` added to the group `foo`.')

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/addgroup')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<strong>Add group to the' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'group': 'ralph',
            }

            output = self.app.post('/test/addgroup', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<strong>Add group to the' in output.data)

            data['csrf_token'] = csrf_token
            output = self.app.post('/test/addgroup', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<strong>Add group to the' in output.data)
            self.assertIn(
                '</button>\n                      No group ralph found.',
                output.data)

            data['group'] = 'foo'
            output = self.app.post(
                '/test/addgroup', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '</button>\n                      Group added', output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_remove_user_when_user_mngt_off(self, ast):
        """ Test the remove_user endpoint when user management is turned
        off in the pagure instance"""
        pagure.APP.config['ENABLE_USER_MNGT'] = False
        ast.return_value = False

        # Git repo not found
        output = self.app.post('/foo/dropuser/1')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            tests.create_projects(self.session)
            tests.create_projects_git(self.path)

            output = self.app.post('/test/settings')

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'csrf_token': csrf_token}

            output = self.app.post(
                '/test/dropuser/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        # User not logged in
        output = self.app.post('/test/dropuser/1')
        self.assertEqual(output.status_code, 302)

        # Add an user to a project
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/dropuser/2', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/dropuser/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        pagure.APP.config['ENABLE_USER_MNGT'] = True


    @patch('pagure.ui.repo.admin_session_timedout')
    def test_remove_user(self, ast):
        """ Test the remove_user endpoint. """
        ast.return_value = False

        # Git repo not found
        output = self.app.post('/foo/dropuser/1')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/dropuser/1')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(self.path)

            output = self.app.post('/test/dropuser/1')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.post('/test/dropuser/1')
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

        # User not logged in
        output = self.app.post('/test/dropuser/1')
        self.assertEqual(output.status_code, 302)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/settings')

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'csrf_token': csrf_token}

            output = self.app.post(
                '/test/dropuser/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '</button>\n                      User does not have commit rights, '
                'or cannot have them removed', output.data)

        # Add an user to a project
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/dropuser/2', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertNotIn(
                '</button>\n                      User removed', output.data)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/dropuser/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '</button>\n                      User removed', output.data)


    @patch('pagure.ui.repo.admin_session_timedout')
    def test_remove_group_project_when_user_mngt_off(self, ast):
        """ Test the remove_group_project endpoint when user management is
        turned off in the pagure instance"""
        pagure.APP.config['ENABLE_USER_MNGT'] = False
        ast.return_value = False

        # No Git repo
        output = self.app.post('/foo/dropgroup/1')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(self.path)

        # User not logged in
        output = self.app.post('/test/dropgroup/1')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/settings')

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'csrf_token': csrf_token}

            output = self.app.post(
                '/test/dropgroup/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        # Create the new group
        msg = pagure.lib.add_group(
            session=self.session,
            group_name='testgrp',
            group_type='user',
            display_name='testgrp group',
            description=None,
            user='pingou',
            is_admin=False,
            blacklist=[],
        )
        self.assertEqual(msg, 'User `pingou` added to the group `testgrp`.')
        self.session.commit()

        repo = pagure.lib.get_project(self.session, 'test')
        # Add the group to a project
        msg = pagure.lib.add_group_to_project(
            session=self.session,
            project=repo,
            new_group='testgrp',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/dropgroup/1', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/dropgroup/1', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        pagure.APP.config['ENABLE_USER_MNGT'] = True


    @patch('pagure.ui.repo.admin_session_timedout')
    def test_remove_group_project(self, ast):
        """ Test the remove_group_project endpoint. """
        ast.return_value = False

        # No Git repo
        output = self.app.post('/foo/dropgroup/1')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/dropgroup/1')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(self.path)

            output = self.app.post('/test/dropgroup/1')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.post('/test/dropgroup/1')
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

        # User not logged in
        output = self.app.post('/test/dropgroup/1')
        self.assertEqual(output.status_code, 302)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/settings')

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'csrf_token': csrf_token}

            output = self.app.post(
                '/test/dropgroup/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '</button>\n                      '
                'Group does not seem to be part of this project',
                output.data)

        # Create the new group
        msg = pagure.lib.add_group(
            session=self.session,
            group_name='testgrp',
            group_type='user',
            display_name='testgrp group',
            description=None,
            user='pingou',
            is_admin=False,
            blacklist=[],
        )
        self.assertEqual(msg, 'User `pingou` added to the group `testgrp`.')
        self.session.commit()

        repo = pagure.lib.get_project(self.session, 'test')
        # Add the group to a project
        msg = pagure.lib.add_group_to_project(
            session=self.session,
            project=repo,
            new_group='testgrp',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/dropgroup/1', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertNotIn(
                '</button>\n                      Group removed',
                output.data)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/dropgroup/1', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '</button>\n                      Group removed',
                output.data)


    @patch('pagure.ui.repo.admin_session_timedout')
    def test_update_project(self, ast):
        """ Test the update_project endpoint. """
        ast.return_value = True

        # Git repo not found
        output = self.app.post('/foo/update')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            # Project does not exist
            output = self.app.post('/foo/update')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(self.path)

            # Session timed-out
            output = self.app.post('/test/update')
            self.assertEqual(output.status_code, 302)

            ast.return_value = False

            # Not allowed
            output = self.app.post('/test/update')
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.post('/test/update')
        self.assertEqual(output.status_code, 302)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/update', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'description': 'new description for test project #1',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '<input class="form-control" name="avatar_email" value="" />', output.data)
            self.assertIn(
                '</button>\n                      Project updated',
                output.data)

            # Edit the avatar_email
            data = {
                'description': 'new description for test project #1',
                'avatar_email': 'pingou@fp.o',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '<input class="form-control" name="avatar_email" value="pingou@fp.o" />',
                output.data)
            self.assertIn(
                '</button>\n                      Project updated',
                output.data)

            # Reset the avatar_email
            data = {
                'description': 'new description for test project #1',
                'avatar_email': '',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '<input class="form-control" name="avatar_email" value="" />', output.data)
            self.assertIn(
                '</button>\n                      Project updated',
                output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_view_settings(self, ast):
        """ Test the view_settings endpoint. """
        ast.return_value = False

        # No Git repo
        output = self.app.get('/foo/settings')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/foo/settings')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(self.path)

            output = self.app.get('/test/settings')
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.get('/test/settings')
        self.assertEqual(output.status_code, 302)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            ast.return_value = True
            output = self.app.get('/test/settings')
            self.assertEqual(output.status_code, 302)

            ast.return_value = False
            output = self.app.get('/test/settings')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)

            # Both checkbox checked before
            self.assertIn(
                '<input id="pull_requests" type="checkbox" value="y" '
                'name="pull_requests" checked=""/>', output.data)
            self.assertIn(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" checked=""/>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}
            output = self.app.post(
                '/test/settings', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)

            # Both checkbox are still checked
            output = self.app.get('/test/settings', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '<input id="pull_requests" type="checkbox" value="y" '
                'name="pull_requests" checked=""/>', output.data)
            self.assertIn(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" checked=""/>', output.data)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output.data)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertIn(
                '</button>\n                      Edited successfully '
                'settings of repo: test', output.data)

            # Both checkbox are now un-checked
            output = self.app.get('/test/settings', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '<input id="pull_requests" type="checkbox" value="y" '
                'name="pull_requests" />', output.data)
            self.assertIn(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" />', output.data)

            data = {
                'csrf_token': csrf_token,
                'pull_requests': 'y',
                'issue_tracker': 'y',
            }
            output = self.app.post(
                '/test/settings', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output.data)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\n'
                'test project #1        </div>', output.data)
            self.assertIn(
                '</button>\n                      Edited successfully '
                'settings of repo: test', output.data)

            # Both checkbox are again checked
            output = self.app.get('/test/settings', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '<input id="pull_requests" type="checkbox" value="y" '
                'name="pull_requests" checked=""/>', output.data)
            self.assertIn(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" checked=""/>', output.data)

    def test_view_forks(self):
        """ Test the view_forks endpoint. """

        output = self.app.get('/foo/forks', follow_redirects=True)
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/test/forks', follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertTrue('This project has not been forked.' in output.data)

    def test_view_repo(self):
        """ Test the view_repo endpoint. """

        output = self.app.get('/foo')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>This repo is brand new!</p>' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)

        output = self.app.get('/test/')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>This repo is brand new!</p>' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'test.git'))
        tests.add_readme_git_repo(os.path.join(self.path, 'test.git'))

        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)

        # Turn that repo into a fork
        repo = pagure.lib.get_project(self.session, 'test')
        repo.parent_id = 2
        repo.is_fork = True
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get('/test')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test.git'))

        output = self.app.get('/fork/pingou/test')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)
        self.assertTrue('Forked from' in output.data)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbmmm',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #3        </div>', output.data)
        self.assertTrue('Forked from' in output.data)

    def test_view_repo_empty(self):
        """ Test the view_repo endpoint on a repo w/o master branch. """

        tests.create_projects(self.session)
        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'test.git')
        pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-viewrepo-test')
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        # Edit the sources file again
        with open(os.path.join(newpath, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        new_repo.index.add('sources')
        new_repo.index.write()

        # Commits the files added
        tree = new_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        new_repo.create_commit(
            'refs/heads/feature',
            author,
            committer,
            'A commit on branch feature',
            tree,
            []
        )
        refname = 'refs/heads/feature'
        ori_remote = new_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 0)

        shutil.rmtree(newpath)

    def test_view_repo_branch(self):
        """ Test the view_repo_branch endpoint. """

        output = self.app.get('/foo/branch/master')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/branch/master')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'test.git'))
        tests.add_readme_git_repo(os.path.join(self.path, 'test.git'))

        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)

        # Turn that repo into a fork
        repo = pagure.lib.get_project(self.session, 'test')
        repo.parent_id = 2
        repo.is_fork = True
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test.git'))

        output = self.app.get('/fork/pingou/test/branch/master')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)
        self.assertTrue('Forked from' in output.data)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbnnn',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3/branch/master')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #3        </div>', output.data)
        self.assertTrue('Forked from' in output.data)

    def test_view_commits(self):
        """ Test the view_commits endpoint. """
        output = self.app.get('/foo/commits')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/commits')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<p>This repo is brand new!</p>', output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'test.git'))
        tests.add_readme_git_repo(os.path.join(self.path, 'test.git'))

        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 200)
        self.assertNotIn('<p>This repo is brand new!</p>', output.data)
        self.assertNotIn('Forked from', output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)
        self.assertIn('<title>Commits - test - Pagure</title>', output.data)

        output = self.app.get('/test/commits/master')
        self.assertEqual(output.status_code, 200)
        self.assertNotIn('<p>This repo is brand new!</p>', output.data)
        self.assertNotIn('Forked from', output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)

        # Turn that repo into a fork
        repo = pagure.lib.get_project(self.session, 'test')
        repo.parent_id = 2
        repo.is_fork = True
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test.git'))

        output = self.app.get('/fork/pingou/test/commits?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertNotIn('<p>This repo is brand new!</p>', output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)
        self.assertIn('Forked from', output.data)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbooo',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3/commits/fobranch')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/fork/pingou/test3/commits')
        self.assertEqual(output.status_code, 200)
        self.assertNotIn('<p>This repo is brand new!</p>', output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #3        </div>', output.data)
        self.assertIn('Forked from', output.data)

    def test_compare_commits(self):
        """ Test the compare_commits endpoint. """

        # First two commits comparison
        def compare_first_two(c1, c2):
            # View commits comparison
            output = self.app.get('/test/c/%s..%s' % (c2.oid.hex, c1.oid.hex))
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Diff from %s to %s - test\n - Pagure</title>'
                % (c2.oid.hex, c1.oid.hex),
                output.data)
            self.assertIn(
                '<h5 class="text-muted">%s .. %s</h5>'
                % (c2.oid.hex, c1.oid.hex),
                output.data)
            self.assertIn(
                '<span class="hidden-sm-down">Commits&nbsp;</span>\n      ' +
                '<span ' +
                'class="label label-default label-pill hidden-sm-down">' +
                '\n        2\n      </span>',
                output.data)
            self.assertIn(
                '<span style="color: #800080; font-weight: bold">' +
                '@@ -1,2 +1,1 @@</span>',
                output.data)
            self.assertIn(
                '<span style="color: #a40000">- Row 0</span>', output.data)
            # View inverse commits comparison
            output = self.app.get('/test/c/%s..%s' % (c1.oid.hex, c2.oid.hex))
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Diff from %s to %s - test\n - Pagure</title>' %
                (c1.oid.hex, c2.oid.hex),
                output.data)
            self.assertIn(
                '<span class="hidden-sm-down">Commits&nbsp;</span>\n      ' +
                '<span ' +
                'class="label label-default label-pill hidden-sm-down">' +
                '\n        2\n      </span>',
                output.data)
            self.assertIn(
                '<h5 class="text-muted">%s .. %s</h5>' %
                (c1.oid.hex, c2.oid.hex),
                output.data)
            self.assertIn(
                '<span style="color: #800080; font-weight: bold">' +
                '@@ -1,1 +1,2 @@</span>',
                output.data)
            self.assertIn(
                '<span style="color: #00A000">+ Row 0</span>',
                output.data)

        def compare_all(c1, c3):
            # View commits comparison
            output = self.app.get('/test/c/%s..%s' % (c1.oid.hex, c3.oid.hex))
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Diff from %s to %s - test\n - Pagure</title>' %
                (c1.oid.hex, c3.oid.hex), output.data)
            self.assertIn(
                '<h5 class="text-muted">%s .. %s</h5>' %
                (c1.oid.hex, c3.oid.hex),
                output.data)
            self.assertIn(
                '<span style="color: #800080; font-weight: bold">' +
                '@@ -1,1 +1,2 @@</span>',
                output.data)
            self.assertIn(
                '<span style="color: #00A000">+ Row 0</span>', output.data)
            self.assertEqual(
                output.data.count(
                    '<span style="color: #00A000">+ Row 0</span>'), 2)
            self.assertIn(
                '<span class="hidden-sm-down">Commits&nbsp;</span>\n      ' +
                '<span ' +
                'class="label label-default label-pill hidden-sm-down">' +
                '\n        3\n      </span>',
                output.data)
            self.assertIn(
                'title="View file as of 4829cf">Šource</a>', output.data)
            self.assertIn(
                '<div><small>file added</small></div></h5>', output.data)

            # View inverse commits comparison
            output = self.app.get(
                '/test/c/%s..%s' % (c3.oid.hex, c1.oid.hex))
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Diff from %s to %s - test\n - Pagure</title>' %
                (c3.oid.hex, c1.oid.hex), output.data)
            self.assertIn(
                '<h5 class="text-muted">%s .. %s</h5>' %
                (c3.oid.hex, c1.oid.hex),
                output.data)
            self.assertIn(
                '<span style="color: #800080; font-weight: bold">' +
                '@@ -1,2 +1,1 @@</span>',
                output.data)
            self.assertIn(
                '<span style="color: #a40000">- Row 0</span>',
                output.data)
            self.assertEqual(
                output.data.count(
                    '<span style="color: #a40000">- Row 0</span>'), 1)
            self.assertIn(
                '<span class="hidden-sm-down">Commits&nbsp;</span>\n      ' +
                '<span ' +
                'class="label label-default label-pill hidden-sm-down">' +
                '\n        3\n      </span>',
                output.data)
            self.assertIn(
                'title="View file as of 000000">Šource</a>', output.data)
            self.assertIn(
                '<div><small>file removed</small></div></h5>', output.data)

        output = self.app.get('/foo/bar')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/bar')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/test/bar')
        self.assertEqual(output.status_code, 404)

        repo = pygit2.Repository(os.path.join(self.path, 'test.git'))

        # Add one commit to git repo
        tests.add_commit_git_repo(
            os.path.join(self.path, 'test.git'), ncommits=1)
        c1 = repo.revparse_single('HEAD')

        # Add another commit to git repo
        tests.add_commit_git_repo(
            os.path.join(self.path, 'test.git'), ncommits=1)
        c2 = repo.revparse_single('HEAD')

        # Add one more commit to git repo
        tests.add_commit_git_repo(
            os.path.join(self.path, 'test.git'),
            ncommits=1, filename='Šource')
        c3 = repo.revparse_single('HEAD')

        compare_first_two(c1, c2)
        compare_all(c1, c3)

        user = tests.FakeUser()
        # Set user logged in
        with tests.user_set(pagure.APP, user):
            compare_first_two(c1, c2)
            compare_all(c1, c3)

    def test_view_file(self):
        """ Test the view_file endpoint. """
        output = self.app.get('/foo/blob/foo/f/sources')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/blob/foo/f/sources')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/test/blob/foo/f/sources')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'test.git'))
        tests.add_readme_git_repo(os.path.join(self.path, 'test.git'))
        tests.add_binary_git_repo(
            os.path.join(self.path, 'test.git'), 'test.jpg')
        tests.add_binary_git_repo(
            os.path.join(self.path, 'test.git'), 'test_binary')

        output = self.app.get('/test/blob/master/foofile')
        self.assertEqual(output.status_code, 404)

        # View in a branch
        output = self.app.get('/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<table class="code_table">' in output.data)
        self.assertTrue(
            '<tr><td class="cell1"><a id="_1" href="#_1" data-line-number="1"></a></td>'
            in output.data)
        self.assertTrue(
            '<td class="cell2"><pre> bar</pre></td>' in output.data)

        # View what's supposed to be an image
        output = self.app.get('/test/blob/master/f/test.jpg')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'Binary files cannot be rendered.<br/>', output.data)
        self.assertIn(
            '<a href="/test/raw/master/f/test.jpg">view the raw version',
            output.data)

        # View by commit id
        repo = pygit2.Repository(os.path.join(self.path, 'test.git'))
        commit = repo.revparse_single('HEAD')

        output = self.app.get('/test/blob/%s/f/test.jpg' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'Binary files cannot be rendered.<br/>', output.data)
        self.assertIn('/f/test.jpg">view the raw version', output.data)

        # View by image name -- somehow we support this
        output = self.app.get('/test/blob/sources/f/test.jpg')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'Binary files cannot be rendered.<br/>', output.data)
        self.assertIn('/f/test.jpg">view the raw version', output.data)

        # View binary file
        output = self.app.get('/test/blob/sources/f/test_binary')
        self.assertEqual(output.status_code, 200)
        self.assertIn('/f/test_binary">view the raw version', output.data)
        self.assertTrue(
            'Binary files cannot be rendered.<br/>'
            in output.data)

        # View folder
        output = self.app.get('/test/blob/master/f/folder1')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<span class="oi text-muted" data-glyph="folder"></span>',
            output.data)
        self.assertIn('<title>Tree - test - Pagure</title>', output.data)
        self.assertIn(
            '<a href="/test/blob/master/f/folder1/folder2">', output.data)

        # View by image name -- with a non-existant file
        output = self.app.get('/test/blob/sources/f/testfoo.jpg')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/blob/master/f/folder1/testfoo.jpg')
        self.assertEqual(output.status_code, 404)

        # View file with a non-ascii name
        tests.add_commit_git_repo(
            os.path.join(self.path, 'test.git'),
            ncommits=1, filename='Šource')
        output = self.app.get('/test/blob/master/f/Šource')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.headers['Content-Type'].lower(),
                         'text/html; charset=utf-8')
        self.assertIn('</span>&nbsp; Šource', output.data)
        self.assertIn('<table class="code_table">', output.data)
        self.assertIn(
            '<tr><td class="cell1"><a id="_1" href="#_1" '
            'data-line-number="1"></a></td>', output.data)
        self.assertTrue(
            '<td class="cell2"><pre><span></span>Row 0</pre></td>'
            in output.data
            or
            '<td class="cell2"><pre>Row 0</pre></td>' in output.data
        )

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbppp',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<table class="code_table">', output.data)
        self.assertIn(
            '<tr><td class="cell1"><a id="_1" href="#_1" data-line-number="1"></a></td>',
            output.data)
        self.assertIn(
            '<td class="cell2"><pre> barRow 0</pre></td>', output.data)

    def test_view_raw_file(self):
        """ Test the view_raw_file endpoint. """
        output = self.app.get('/foo/raw/foo/sources')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/raw/foo/sources')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/test/raw/foo/sources')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_readme_git_repo(os.path.join(self.path, 'test.git'))

        # View first commit
        output = self.app.get('/test/raw/master')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.headers['Content-Type'].lower(),
                         'text/plain; charset=ascii')
        self.assertTrue(':Author: Pierre-Yves Chibon' in output.data)

        # Add some more content to the repo
        tests.add_content_git_repo(os.path.join(self.path, 'test.git'))
        tests.add_binary_git_repo(
            os.path.join(self.path, 'test.git'), 'test.jpg')
        tests.add_binary_git_repo(
            os.path.join(self.path, 'test.git'), 'test_binary')

        output = self.app.get('/test/raw/master/f/foofile')
        self.assertEqual(output.status_code, 404)

        # View in a branch
        output = self.app.get('/test/raw/master/f/sources')
        self.assertEqual(output.headers['Content-Type'].lower(),
                         'text/plain; charset=ascii')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('foo\n bar' in output.data)

        # View what's supposed to be an image
        output = self.app.get('/test/raw/master/f/test.jpg')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(output.data.startswith('\x00\x00\x01\x00'))

        # View by commit id
        repo = pygit2.Repository(os.path.join(self.path, 'test.git'))
        commit = repo.revparse_single('HEAD')

        output = self.app.get('/test/raw/%s/f/test.jpg' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(output.data.startswith('\x00\x00\x01\x00'))

        # View by image name -- somehow we support this
        output = self.app.get('/test/raw/sources/f/test.jpg')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(output.data.startswith('\x00\x00\x01\x00'))

        # View binary file
        output = self.app.get('/test/raw/sources/f/test_binary')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.headers['Content-Type'].lower(),
                         'application/octet-stream')
        self.assertTrue(output.data.startswith('\x00\x00\x01\x00'))

        # View folder
        output = self.app.get('/test/raw/master/f/folder1')
        self.assertEqual(output.status_code, 404)

        # View by image name -- with a non-existant file
        output = self.app.get('/test/raw/sources/f/testfoo.jpg')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/raw/master/f/folder1/testfoo.jpg')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/test/raw/master/f/')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/test/raw/master')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.headers['Content-Type'].lower(),
                         'text/plain; charset=ascii')
        self.assertTrue(output.data.startswith(
            'diff --git a/test_binary b/test_binary\n'))

        output = self.app.get('/test/raw/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(output.data.startswith(
            'diff --git a/test_binary b/test_binary\n'))

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbqqq',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3/raw/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.headers['Content-Type'].lower(),
                         'text/plain; charset=ascii')
        self.assertTrue('foo\n bar' in output.data)

    def test_view_blame_file(self):
        """ Test the view_blame_file endpoint. """
        output = self.app.get('/foo/blame/sources')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/blame/sources')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/test/blame/sources')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'test.git'))
        tests.add_readme_git_repo(os.path.join(self.path, 'test.git'))
        tests.add_binary_git_repo(
            os.path.join(self.path, 'test.git'), 'test.jpg')
        tests.add_binary_git_repo(
            os.path.join(self.path, 'test.git'), 'test_binary')

        output = self.app.get('/test/blame/foofile')
        self.assertEqual(output.status_code, 404)

        # View in a branch
        output = self.app.get('/test/blame/sources')
        self.assertEqual(output.status_code, 200)
        self.assertIn(b'<table class="code_table">', output.data)
        self.assertIn(
            b'<tr><td class="cell1"><a id="1" href="#1" '
            b'data-line-number="1"></a></td>', output.data)
        self.assertIn(
            b'<td class="cell2"><pre> bar</pre></td>', output.data)

        # View what's supposed to be an image
        output = self.app.get('/test/blame/test.jpg')
        self.assertEqual(output.status_code, 400)
        self.assertIn(
            b'<title>400 Bad Request</title>', output.data)
        self.assertIn(
            b'<p>Binary files cannot be blamed</p>', output.data)

        # View folder
        output = self.app.get('/test/blame/folder1')
        self.assertEqual(output.status_code, 404)
        self.assertIn("<title>Page not found :'( - Pagure</title>", output.data)
        self.assertIn(
            '<h2>Page not found (404)</h2>', output.data)

        # View by image name -- with a non-existant file
        output = self.app.get('/test/blame/testfoo.jpg')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/blame/folder1/testfoo.jpg')
        self.assertEqual(output.status_code, 404)

        # View file with a non-ascii name
        tests.add_commit_git_repo(
            os.path.join(self.path, 'test.git'),
            ncommits=1, filename='Šource')
        output = self.app.get('/test/blame/Šource')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.headers['Content-Type'].lower(),
                         'text/html; charset=utf-8')
        self.assertIn('</span>&nbsp; Šource', output.data)
        self.assertIn('<table class="code_table">', output.data)
        self.assertIn(
            '<tr><td class="cell1"><a id="1" href="#1" '
            'data-line-number="1"></a></td>', output.data)
        self.assertTrue(
            '<td class="cell2"><pre><span></span>Row 0</pre></td>'
            in output.data
            or
            '<td class="cell2"><pre>Row 0</pre></td>' in output.data
        )

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbppp',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'),
            ncommits=10)
        tests.add_content_to_git(
            os.path.join(self.path, 'forks', 'pingou', 'test3.git'),
            content=u'✨☃🍰☃✨'.encode('utf-8'))

        output = self.app.get('/fork/pingou/test3/blame/sources')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<table class="code_table">', output.data)
        self.assertIn(
            '<tr><td class="cell1"><a id="1" href="#1" '
            'data-line-number="1"></a></td>', output.data)
        self.assertIn(
            '<td class="cell2"><pre> barRow 0</pre></td>', output.data)

    def test_view_commit(self):
        """ Test the view_commit endpoint. """
        output = self.app.get('/foo/c/bar')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/c/bar')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/test/c/bar')
        self.assertEqual(output.status_code, 404)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, 'test.git'))
        repo = pygit2.Repository(os.path.join(self.path, 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View first commit
        output = self.app.get('/test/c/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.data)
        self.assertTrue('  Authored by Alice Author\n' in output.data)
        self.assertTrue('  Committed by Cecil Committer\n' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ Pagure</span>' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ ======</span>' in output.data)

        # View first commit - with the old URL scheme disabled - default
        output = self.app.get(
            '/test/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 404)
        self.assertIn('<p>Project not found</p>', output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'test.git'))

        repo = pygit2.Repository(os.path.join(self.path, 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View another commit
        output = self.app.get('/test/c/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.data)
        self.assertTrue('  Authored by Alice Author\n' in output.data)
        self.assertTrue('  Committed by Cecil Committer\n' in output.data)
        self.assertTrue(
            # new version of pygments
            '<div class="highlight" style="background: #f8f8f8">'
            '<pre style="line-height: 125%">'
            '<span></span>'
            '<span style="color: #800080; font-weight: bold">'
            '@@ -0,0 +1,3 @@</span>' in output.data
            or
            # old version of pygments
            '<div class="highlight" style="background: #f8f8f8">'
            '<pre style="line-height: 125%">'
            '<span style="color: #800080; font-weight: bold">'
            '@@ -0,0 +1,3 @@</span>' in output.data)

        #View the commit when branch name is provided
        output = self.app.get('/test/c/%s?branch=master' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<a class="active nav-link" href="/test/commits/master">'
            in output.data)

        #View the commit when branch name is wrong, show the commit
        output = self.app.get('/test/c/%s?branch=abcxyz' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<a class="active nav-link" href="/test/commits">'
            in output.data)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbkkk',
        )
        self.session.add(item)
        self.session.commit()
        forkedgit = os.path.join(
            self.path, 'forks', 'pingou', 'test3.git')

        tests.add_content_git_repo(forkedgit)
        tests.add_readme_git_repo(forkedgit)

        repo = pygit2.Repository(forkedgit)
        commit = repo.revparse_single('HEAD')

        # Commit does not exist in anothe repo :)
        output = self.app.get('/test/c/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 404)

        # View commit of fork
        output = self.app.get(
            '/fork/pingou/test3/c/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.data)
        self.assertTrue('  Authored by Alice Author\n' in output.data)
        self.assertTrue('  Committed by Cecil Committer\n' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ Pagure</span>' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ ======</span>' in output.data)

        # Try the old URL scheme with a short hash
        output = self.app.get(
            '/fork/pingou/test3/%s' % commit.oid.hex[:10],
            follow_redirects=True)
        self.assertEqual(output.status_code, 404)
        self.assertIn('<p>Project not found</p>', output.data)

        #View the commit of the fork when branch name is provided
        output = self.app.get('/fork/pingou/test3/c/%s?branch=master' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<a class="active nav-link" href="/fork/pingou/test3/commits/master">'
            in output.data)

        #View the commit of the fork when branch name is wrong
        output = self.app.get('/fork/pingou/test3/c/%s?branch=abcxyz' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<a class="active nav-link" href="/fork/pingou/test3/commits">'
            in output.data)


    def test_view_commit_patch(self):
        """ Test the view_commit_patch endpoint. """

        # No project registered in the DB
        output = self.app.get('/foo/c/bar.patch')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/c/bar.patch')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/test/c/bar.patch')
        self.assertEqual(output.status_code, 404)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, 'test.git'))
        repo = pygit2.Repository(os.path.join(self.path, 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View first commit
        output = self.app.get('/test/c/%s.patch' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue('''diff --git a/README.rst b/README.rst
new file mode 100644
index 0000000..fb7093d
--- /dev/null
+++ b/README.rst
@@ -0,0 +1,16 @@
+Pagure
+======
+
+:Author: Pierre-Yves Chibon <pingou@pingoured.fr>
+
+
+Pagure is a light-weight git-centered forge based on pygit2.
+
+Currently, Pagure offers a web-interface for git repositories, a ticket
+system and possibilities to create new projects, fork existing ones and
+create/merge pull-requests across or within projects.
+
+
+Homepage: https://github.com/pypingou/pagure
+
+Dev instance: http://209.132.184.222/ (/!\ May change unexpectedly, it's a dev instance ;-))
''' in output.data)
        self.assertTrue('Subject: Add a README file' in output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'test.git'))

        repo = pygit2.Repository(os.path.join(self.path, 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View another commit
        output = self.app.get('/test/c/%s.patch' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            'Subject: Add some directory and a file for more testing'
            in output.data)
        self.assertTrue('''diff --git a/folder1/folder2/file b/folder1/folder2/file
new file mode 100644
index 0000000..11980b1
--- /dev/null
+++ b/folder1/folder2/file
@@ -0,0 +1,3 @@
+foo
+ bar
+baz
\ No newline at end of file
''' in output.data)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbblll',
        )
        self.session.add(item)
        self.session.commit()
        forkedgit = os.path.join(self.path, 'forks', 'pingou', 'test3.git')

        tests.add_content_git_repo(forkedgit)
        tests.add_readme_git_repo(forkedgit)

        repo = pygit2.Repository(forkedgit)
        commit = repo.revparse_single('HEAD')

        # Commit does not exist in anothe repo :)
        output = self.app.get('/test/c/%s.patch' % commit.oid.hex)
        self.assertEqual(output.status_code, 404)

        # View commit of fork
        output = self.app.get(
            '/fork/pingou/test3/c/%s.patch' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue('''diff --git a/README.rst b/README.rst
new file mode 100644
index 0000000..fb7093d
--- /dev/null
+++ b/README.rst
@@ -0,0 +1,16 @@
+Pagure
+======
+
+:Author: Pierre-Yves Chibon <pingou@pingoured.fr>
+
+
+Pagure is a light-weight git-centered forge based on pygit2.
+
+Currently, Pagure offers a web-interface for git repositories, a ticket
+system and possibilities to create new projects, fork existing ones and
+create/merge pull-requests across or within projects.
+
+
+Homepage: https://github.com/pypingou/pagure
+
+Dev instance: http://209.132.184.222/ (/!\ May change unexpectedly, it's a dev instance ;-))
''' in output.data)

    def test_view_tree(self):
        """ Test the view_tree endpoint. """
        output = self.app.get('/foo/tree/')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/tree/')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/test/tree/')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '''
        <ol class="breadcrumb">
          <li>
            <a href="/test/tree">
              <span class="oi" data-glyph="random">
              </span>&nbsp; None
            </a>
          </li>
        </ol>''', output.data)
        self.assertTrue(
            'No content found in this repository' in output.data)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, 'test.git'))
        repo = pygit2.Repository(os.path.join(self.path, 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View first commit
        output = self.app.get('/test/tree/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)
        self.assertIn('<title>Tree - test - Pagure</title>', output.data)
        self.assertTrue('README.rst' in output.data)
        self.assertFalse(
            'No content found in this repository' in output.data)

        # View tree by branch
        output = self.app.get('/test/tree/master')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)
        self.assertIn('<title>Tree - test - Pagure</title>', output.data)
        self.assertTrue('README.rst' in output.data)
        self.assertFalse(
            'No content found in this repository' in output.data)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbfff',
        )
        self.session.add(item)
        self.session.commit()
        forkedgit = os.path.join(self.path, 'forks', 'pingou', 'test3.git')

        tests.add_content_git_repo(forkedgit)

        output = self.app.get('/fork/pingou/test3/tree/')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #3        </div>', output.data)
        self.assertIn('<title>Tree - test3 - Pagure</title>', output.data)
        self.assertTrue(
            '<a href="/fork/pingou/test3/blob/master/f/folder1">'
            in output.data)
        self.assertTrue(
            '<a href="/fork/pingou/test3/blob/master/f/sources">'
            in output.data)
        self.assertFalse(
            'No content found in this repository' in output.data)

        output = self.app.get(
            '/fork/pingou/test3/blob/master/f/folder1/folder2')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<a href="/fork/pingou/test3/blob/master/'
            'f/folder1/folder2/file%C5%A0">' in output.data)


    @patch('pagure.lib.notify.send_email')
    @patch('pagure.ui.repo.admin_session_timedout')
    def test_delete_repo_when_turned_off(self, ast, send_email):
        """ Test the delete_repo endpoint when deletion of a repo is
        turned off in the pagure instance """
        ast.return_value = False
        send_email.return_value = True
        pagure.APP.config['ENABLE_DEL_PROJECTS'] = False

        # No Git repo
        output = self.app.post('/foo/delete')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            tests.create_projects(self.session)
            tests.create_projects_git(self.path)

            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        # User not logged in
        output = self.app.post('/test/delete')
        self.assertEqual(output.status_code, 302)

        with tests.user_set(pagure.APP, user):
            # Only git repo
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbggg',
            )
            self.session.add(item)
            self.session.commit()
            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Only git and doc repo
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbhhh',
            )
            self.session.add(item)
            self.session.commit()
            tests.create_projects_git(self.path)
            tests.create_projects_git(os.path.join(self.path, 'docs'))
            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # All repo there
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbiii',
            )
            self.session.add(item)
            self.session.commit()

            # Create all the git repos
            tests.create_projects_git(self.path)
            tests.create_projects_git(os.path.join(self.path, 'docs'))
            tests.create_projects_git(
                os.path.join(self.path, 'tickets'), bare=True)
            tests.create_projects_git(
                os.path.join(self.path, 'requests'), bare=True)

            # Check repo was created
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">6</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            # add issues
            repo = pagure.lib.get_project(self.session, 'test')
            msg = pagure.lib.new_issue(
                session=self.session,
                repo=repo,
                title='Test issue',
                content='We should work on this',
                user='pingou',
                ticketfolder=os.path.join(self.path, 'tickets')
            )
            self.session.commit()
            self.assertEqual(msg.title, 'Test issue')

            msg = pagure.lib.new_issue(
                session=self.session,
                repo=repo,
                title='Test issue #2',
                content='We should work on this, really',
                user='pingou',
                ticketfolder=os.path.join(self.path, 'tickets')
            )
            self.session.commit()
            self.assertEqual(msg.title, 'Test issue #2')

            # Add a comment to an issue
            issue = pagure.lib.search_issues(self.session, repo, issueid=1)
            msg = pagure.lib.add_issue_comment(
                session=self.session,
                issue=issue,
                comment='Hey look a comment!',
                user='foo',
                ticketfolder=None
            )
            self.session.commit()
            self.assertEqual(msg, 'Comment added')

            # add pull-requests
            req = pagure.lib.new_pull_request(
                session=self.session,
                repo_from=repo,
                branch_from='feature',
                repo_to=repo,
                branch_to='master',
                title='test pull-request',
                user='pingou',
                requestfolder=os.path.join(self.path, 'requests'),
            )
            self.session.commit()
            self.assertEqual(req.id, 3)
            self.assertEqual(req.title, 'test pull-request')

            req = pagure.lib.new_pull_request(
                session=self.session,
                repo_from=repo,
                branch_from='feature2',
                repo_to=repo,
                branch_to='master',
                title='test pull-request',
                user='pingou',
                requestfolder=os.path.join(self.path, 'requests'),
            )
            self.session.commit()
            self.assertEqual(req.id, 4)
            self.assertEqual(req.title, 'test pull-request')

            # Add comment on a pull-request
            request = pagure.lib.search_pull_requests(
                self.session, requestid=3)

            msg = pagure.lib.add_pull_request_comment(
                session=self.session,
                request=request,
                commit='commithash',
                tree_id=None,
                filename='file',
                row=None,
                comment='This is awesome, I got to remember it!',
                user='foo',
                requestfolder=None,
            )
            self.assertEqual(msg, 'Comment added')

            # Check before deleting the project
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">6</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            repo = pagure.lib.get_project(self.session, 'test')
            self.assertNotEqual(repo, None)
            repo = pagure.lib.get_project(self.session, 'test2')
            self.assertNotEqual(repo, None)

            # Add a fork of a fork
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test3',
                description='test project #3',
                is_fork=True,
                parent_id=2,
                hook_token='aaabbbjjj',
            )
            self.session.add(item)
            self.session.commit()
            tests.add_content_git_repo(
                os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
            tests.add_content_git_repo(
                os.path.join(self.path, 'docs', 'pingou', 'test3.git'))
            tests.add_content_git_repo(
                os.path.join(self.path, 'tickets', 'pingou', 'test3.git'))

            # Check before deleting the fork
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">6</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">1</span>',
                output.data)

            output = self.app.post(
                '/fork/pingou/test3/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        pagure.APP.config['ENABLE_DEL_PROJECTS'] = True


    @patch('pagure.lib.notify.send_email')
    @patch('pagure.ui.repo.admin_session_timedout')
    def test_delete_repo(self, ast, send_email):
        """ Test the delete_repo endpoint. """
        ast.return_value = False
        send_email.return_value = True

        # No Git repo
        output = self.app.post('/foo/delete')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            tests.create_projects(self.session)
            tests.create_projects_git(self.path)

            # No project registered in the DB (no git repo)
            output = self.app.post('/foo/delete')
            self.assertEqual(output.status_code, 404)

            # User not allowed
            output = self.app.post('/test/delete')
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.post('/test/delete')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            tests.create_projects_git(self.path)

            ast.return_value = True
            output = self.app.post('/test/delete')
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Could not delete all the '
                'repos from the system', output.data)
            self.assertIn(
                '<div class="card-header">\n            Projects <span '
                'class="label label-default">2</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            # Only git repo
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbggg',
            )
            self.session.add(item)
            self.session.commit()
            tests.create_projects_git(self.path)

            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '</button>\n                      Could not delete all the '
                'repos from the system' in output.data)
            self.assertIn(
                '<div class="card-header">\n            Projects <span '
                'class="label label-default">2</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            # Only git and doc repo
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbhhh',
            )
            self.session.add(item)
            self.session.commit()
            tests.create_projects_git(self.path)
            tests.create_projects_git(os.path.join(self.path, 'docs'))
            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '</button>\n                      Could not delete all the '
                'repos from the system' in output.data)

            # All repo there
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbiii',
            )
            self.session.add(item)
            self.session.commit()

            # Create all the git repos
            tests.create_projects_git(self.path)
            tests.create_projects_git(os.path.join(self.path, 'docs'))
            tests.create_projects_git(
                os.path.join(self.path, 'tickets'), bare=True)
            tests.create_projects_git(
                os.path.join(self.path, 'requests'), bare=True)

            # Check repo was created
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">3</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            # add issues
            repo = pagure.lib.get_project(self.session, 'test')
            msg = pagure.lib.new_issue(
                session=self.session,
                repo=repo,
                title='Test issue',
                content='We should work on this',
                user='pingou',
                ticketfolder=os.path.join(self.path, 'tickets')
            )
            self.session.commit()
            self.assertEqual(msg.title, 'Test issue')

            msg = pagure.lib.new_issue(
                session=self.session,
                repo=repo,
                title='Test issue #2',
                content='We should work on this, really',
                user='pingou',
                ticketfolder=os.path.join(self.path, 'tickets')
            )
            self.session.commit()
            self.assertEqual(msg.title, 'Test issue #2')

            # Add a comment to an issue
            issue = pagure.lib.search_issues(self.session, repo, issueid=1)
            msg = pagure.lib.add_issue_comment(
                session=self.session,
                issue=issue,
                comment='Hey look a comment!',
                user='foo',
                ticketfolder=None
            )
            self.session.commit()
            self.assertEqual(msg, 'Comment added')

            # add pull-requests
            req = pagure.lib.new_pull_request(
                session=self.session,
                repo_from=repo,
                branch_from='feature',
                repo_to=repo,
                branch_to='master',
                title='test pull-request',
                user='pingou',
                requestfolder=os.path.join(self.path, 'requests'),
            )
            self.session.commit()
            self.assertEqual(req.id, 3)
            self.assertEqual(req.title, 'test pull-request')

            req = pagure.lib.new_pull_request(
                session=self.session,
                repo_from=repo,
                branch_from='feature2',
                repo_to=repo,
                branch_to='master',
                title='test pull-request',
                user='pingou',
                requestfolder=os.path.join(self.path, 'requests'),
            )
            self.session.commit()
            self.assertEqual(req.id, 4)
            self.assertEqual(req.title, 'test pull-request')

            # Add comment on a pull-request
            request = pagure.lib.search_pull_requests(
                self.session, requestid=3)

            msg = pagure.lib.add_pull_request_comment(
                session=self.session,
                request=request,
                commit='commithash',
                tree_id=None,
                filename='file',
                row=None,
                comment='This is awesome, I got to remember it!',
                user='foo',
                requestfolder=None,
            )
            self.assertEqual(msg, 'Comment added')

            # Check before deleting the project
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">3</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            Projects <span '
                'class="label label-default">2</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(repo, None)
            repo = pagure.lib.get_project(self.session, 'test2')
            self.assertNotEqual(repo, None)

            # Add a fork of a fork
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test3',
                description='test project #3',
                is_fork=True,
                parent_id=2,
                hook_token='aaabbbjjj',
            )
            self.session.add(item)
            self.session.commit()
            tests.add_content_git_repo(
                os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
            tests.add_content_git_repo(
                os.path.join(self.path, 'docs', 'pingou', 'test3.git'))
            tests.add_content_git_repo(
                os.path.join(self.path, 'tickets', 'pingou', 'test3.git'))

            # Check before deleting the fork
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">2</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">1</span>',
                output.data)

            output = self.app.post(
                '/fork/pingou/test3/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            Projects <span '
                'class="label label-default">2</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_new_repo_hook_token(self, ast):
        """ Test the new_repo_hook_token endpoint. """
        ast.return_value = False
        tests.create_projects(self.session)
        tests.create_projects_git(self.path)

        repo = pagure.lib.get_project(self.session, 'test')
        self.assertEqual(repo.hook_token, 'aaabbbccc')

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            pagure.APP.config['WEBHOOK'] = True
            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            output = self.app.post('/foo/hook_token')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/hook_token')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.post('/test/hook_token')
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

            pagure.APP.config['WEBHOOK'] = False

        repo = pagure.lib.get_project(self.session, 'test')
        self.assertEqual(repo.hook_token, 'aaabbbccc')

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            pagure.APP.config['WEBHOOK'] = True
            output = self.app.post('/test/hook_token')
            self.assertEqual(output.status_code, 400)

            data = {'csrf_token': csrf_token}

            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(repo.hook_token, 'aaabbbccc')

            output = self.app.post(
                '/test/hook_token', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      New hook token generated',
                output.data)
            pagure.APP.config['WEBHOOK'] = False

        repo = pagure.lib.get_project(self.session, 'test')
        self.assertNotEqual(repo.hook_token, 'aaabbbccc')

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.ui.repo.admin_session_timedout')
    @patch('pagure.lib.git.update_git')
    def test_regenerate_git(self, upgit, ast, sendmail):
        """ Test the regenerate_git endpoint. """
        ast.return_value = False
        upgit.return_value = True
        sendmail.return_value = True
        tests.create_projects(self.session)
        tests.create_projects_git(self.path)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            output = self.app.post('/foo/regenerate')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/regenerate')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.post('/test/regenerate')
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/regenerate')
            self.assertEqual(output.status_code, 400)

            data = {'csrf_token': csrf_token}

            output = self.app.post('/test/regenerate', data=data)
            self.assertEqual(output.status_code, 400)

            data['regenerate'] = 'ticket'
            output = self.app.post('/test/regenerate', data=data)
            self.assertEqual(output.status_code, 400)

            # Create an issue to play with
            repo = pagure.lib.get_project(self.session, 'test')
            msg = pagure.lib.new_issue(
                session=self.session,
                repo=repo,
                title='Test issue',
                content='We should work on this',
                user='pingou',
                ticketfolder=None
            )
            self.session.commit()
            self.assertEqual(msg.title, 'Test issue')

            data['regenerate'] = 'tickets'
            output = self.app.post(
                '/test/regenerate', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Tickets git repo updated',
                output.data)

            # Create a request to play with
            repo = pagure.lib.get_project(self.session, 'test')
            msg = pagure.lib.new_pull_request(
                session=self.session,
                repo_from=repo,
                branch_from='branch',
                repo_to=repo,
                branch_to='master',
                title='Test pull-request',
                user='pingou',
                requestfolder=None,
            )
            self.session.commit()
            self.assertEqual(msg.title, 'Test pull-request')

            data['regenerate'] = 'requests'
            output = self.app.post(
                '/test/regenerate', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Requests git repo updated',
                output.data)

    def test_view_tags(self):
        """ Test the view_tags endpoint. """
        output = self.app.get('/foo/releases')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/releases')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/test/releases')
        self.assertEqual(output.status_code, 200)
        self.assertIn('This project has not been tagged.', output.data)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, 'test.git'))
        repo = pygit2.Repository(os.path.join(self.path, 'test.git'))
        first_commit = repo.revparse_single('HEAD')
        tagger = pygit2.Signature('Alice Doe', 'adoe@example.com', 12347, 0)
        repo.create_tag(
            "0.0.1", first_commit.oid.hex, pygit2.GIT_OBJ_COMMIT, tagger,
            "Release 0.0.1")

        output = self.app.get('/test/releases')
        self.assertEqual(output.status_code, 200)
        self.assertIn('0.0.1', output.data)
        self.assertIn('<span id="tagid" class="label label-default">', output.data)
        self.assertTrue(output.data.count('tagid'), 1)

    def test_edit_file(self):
        """ Test the edit_file endpoint. """

        # No Git repo
        output = self.app.get('/foo/edit/foo/f/sources')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            # No project registered in the DB
            output = self.app.get('/foo/edit/foo/f/sources')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(self.path, bare=True)

            # No a repo admin
            output = self.app.get('/test/edit/foo/f/sources')
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.get('/test/edit/foo/f/sources')
        self.assertEqual(output.status_code, 302)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            # No such file
            output = self.app.get('/test/edit/foo/f/sources')
            self.assertEqual(output.status_code, 404)

            # Add some content to the git repo
            tests.add_content_git_repo(os.path.join(self.path, 'test.git'))
            tests.add_readme_git_repo(os.path.join(self.path, 'test.git'))
            tests.add_binary_git_repo(
                os.path.join(self.path, 'test.git'), 'test.jpg')
            tests.add_binary_git_repo(
                os.path.join(self.path, 'test.git'), 'test_binary')

            output = self.app.get('/test/edit/master/foofile')
            self.assertEqual(output.status_code, 404)

            # Edit page
            output = self.app.get('/test/edit/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li><a href="/test/tree/master">'
                '<span class="oi" data-glyph="random"></span>&nbsp; master'
                '</a></li><li class="active">'
                '<span class="oi" data-glyph="file"></span>&nbsp; sources</li>',
                output.data)
            self.assertIn(
                '<textarea id="textareaCode" name="content">foo\n bar</textarea>',
                output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # View what's supposed to be an image
            output = self.app.get('/test/edit/master/f/test.jpg')
            self.assertEqual(output.status_code, 400)
            self.assertIn('<p>Cannot edit binary files</p>', output.data)

            # Check file before the commit:
            output = self.app.get('/test/raw/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertEqual(output.data, 'foo\n bar')

            # No CSRF Token
            data = {
                'content': 'foo\n bar\n  baz',
                'commit_title': 'test commit',
                'commit_message': 'Online commits from the tests',
            }
            output = self.app.post('/test/edit/master/f/sources', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Edit - test - Pagure</title>', output.data)

            # Check that nothing changed
            output = self.app.get('/test/raw/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertEqual(output.data, 'foo\n bar')

            # Missing email
            data['csrf_token'] = csrf_token
            output = self.app.post('/test/edit/master/f/sources', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Edit - test - Pagure</title>', output.data)

            # Invalid email
            data['email'] = 'pingou@fp.o'
            output = self.app.post('/test/edit/master/f/sources', data=data)
            self.assertIn(
                '<title>Edit - test - Pagure</title>', output.data)

            # Works
            data['email'] = 'bar@pingou.com'
            data['branch'] = 'master'
            output = self.app.post(
                '/test/edit/master/f/sources', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Commits - test - Pagure</title>', output.data)
            self.assertIn(
                '</button>\n                      Changes committed',
                output.data)

            # Check file after the commit:
            output = self.app.get('/test/raw/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertEqual(output.data, 'foo\n bar\n  baz')

            # Add a fork of a fork
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test3',
                description='test project #3',
                is_fork=True,
                parent_id=1,
                hook_token='aaabbbppp',
            )
            self.session.add(item)
            self.session.commit()

            tests.add_content_git_repo(
                os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
            tests.add_readme_git_repo(
                os.path.join(self.path, 'forks', 'pingou', 'test3.git'))
            tests.add_commit_git_repo(
                os.path.join(self.path, 'forks', 'pingou', 'test3.git'),
                ncommits=10)

            output = self.app.get('/fork/pingou/test3/edit/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li><a href="/fork/pingou/test3/tree/master">'
                '<span class="oi" data-glyph="random"></span>&nbsp; master'
                '</a></li><li class="active">'
                '<span class="oi" data-glyph="file"></span>&nbsp; sources'
                '</li>', output.data)
            self.assertIn(
                '<textarea id="textareaCode" name="content">foo\n barRow 0\n',
                output.data)

            # Empty the file - no `content` provided
            data = {
                'commit_title': 'test commit',
                'commit_message': 'Online commits from the tests',
                'csrf_token': csrf_token,
                'email': 'bar@pingou.com',
                'branch': 'master',
            }
            output = self.app.post(
                '/test/edit/master/f/sources', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Commits - test - Pagure</title>', output.data)
            self.assertIn(
                '</button>\n                      Changes committed',
                output.data)

            # Check file after the commit:
            output = self.app.get('/test/raw/master/f/sources')
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                '<p>No content found</p>', output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_change_ref_head(self,ast):
        """ Test the change_ref_head endpoint. """
        ast.return_value = True

        # No Git repo
        output = self.app.post('/foo/default/branch/')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/default/branch/')
            self.assertEqual(output.status_code, 404)

            ast.return_value = False

            output = self.app.post('/foo/default/branch/')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            repos = tests.create_projects_git(self.path)

            output = self.app.post('/test/default/branch/')
            self.assertEqual(output.status_code, 403)

        # User no logged in
        output = self.app.post('/test/default/branch/')
        self.assertEqual(output.status_code, 302)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/default/branch/',
                                    follow_redirects=True) # without git branch
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '<select class="c-select" id="branches" name="branches">'
                '</select>', output.data)
            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            repo_obj = pygit2.Repository(repos[0])
            tree = repo_obj.index.write_tree()
            author = pygit2.Signature(
                'Alice Author', 'alice@authors.tld')
            committer = pygit2.Signature(
                'Cecil Committer', 'cecil@committers.tld')
            repo_obj.create_commit(
                'refs/heads/master',  # the name of the reference to update
                author,
                committer,
                'Add sources file for testing',
                # binary string representing the tree object ID
                tree,
                # list of binary strings representing parents of the new commit
                []
            )
            repo_obj.create_branch("feature",repo_obj.head.get_object())

            data = {
                'branches': 'feature',
                'csrf_token': csrf_token,
            }

            output = self.app.post('/test/default/branch/',     # changing head to feature branch
                                    data=data,
                                    follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '<select class="c-select" id="branches" name="branches">'
                '<option selected value="feature">feature</option>'
                '<option value="master">master</option>'
                '</select>', output.data)
            self.assertIn(
                '</button>\n                      Default branch updated '
                'to feature', output.data)

            data = {
                'branches': 'master',
                'csrf_token': csrf_token,
            }

            output = self.app.post('/test/default/branch/',     # changing head to master branch
                                    data=data,
                                    follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '<select class="c-select" id="branches" name="branches">'
                '<option value="feature">feature</option>'
                '<option selected value="master">master</option>'
                '</select>', output.data)
            self.assertIn(
                '</button>\n                      Default branch updated '
                'to master', output.data)

    def test_new_release(self):
        """ Test the new_release endpoint. """

        # No Git repo
        output = self.app.post('/foo/upload/')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/upload/')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            repo = tests.create_projects_git(self.path)

            output = self.app.post('/test/upload/')
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.post('/test/upload/')
        self.assertEqual(output.status_code, 302)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            img = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                               'placebo.png')

            # Missing CSRF Token
            with open(img, mode='rb') as stream:
                data = {'filestream': stream}
                output = self.app.post('/test/upload/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<h2>Upload a new release</h2>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Upload successful
            with open(img, mode='rb') as stream:
                data = {'filestream': stream, 'csrf_token': csrf_token}
                output = self.app.post(
                    '/test/upload/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      File', output.data)
            self.assertIn(
                'uploaded\n                    </div>', output.data)
            self.assertIn('This project has not been tagged.', output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_add_token(self, ast):
        """ Test the add_token endpoint. """
        ast.return_value = False

        # No Git repo
        output = self.app.get('/foo/token/new/')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/foo/token/new/')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(self.path, bare=True)

            output = self.app.get('/test/token/new/')
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.get('/test/token/new/')
        self.assertEqual(output.status_code, 302)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/token/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create a new token</strong>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]
            data = {'csrf_token': csrf_token}

            ast.return_value = True
            # Test when the session timed-out
            output = self.app.post('/test/token/new/', data=data)
            self.assertEqual(output.status_code, 302)
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Action canceled, try it '
                'again', output.data)
            ast.return_value = False

            # Missing acls
            output = self.app.post('/test/token/new/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create a new token</strong>', output.data)

            data = {'csrf_token': csrf_token, 'acls': ['issue_create']}

            # Upload successful
            data = {'csrf_token': csrf_token, 'acls': ['issue_create']}
            output = self.app.post(
                '/test/token/new/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Token created', output.data)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '<span class="text-success btn-align"><strong>Valid</strong> until: ',
                output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_revoke_api_token(self, ast):
        """ Test the revoke_api_token endpoint. """
        ast.return_value = False

        # No Git repo
        output = self.app.post('/foo/token/revoke/123')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/token/revoke/123')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(self.path, bare=True)

            output = self.app.post('/test/token/revoke/123')
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.post('/test/token/revoke/123')
        self.assertEqual(output.status_code, 302)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/token/new')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create a new token</strong>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]
            data = {'csrf_token': csrf_token}

            ast.return_value = True
            # Test when the session timed-out
            output = self.app.post('/test/token/revoke/123', data=data)
            self.assertEqual(output.status_code, 302)
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Action canceled, try it again',
                output.data)
            ast.return_value = False

            output = self.app.post('/test/token/revoke/123', data=data)
            self.assertEqual(output.status_code, 404)
            self.assertIn('<p>Token not found</p>', output.data)

            # Create a token to revoke
            data = {'csrf_token': csrf_token, 'acls': ['issue_create']}
            output = self.app.post(
                '/test/token/new/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Token created',
                output.data)

            # Existing token will expire in 60 days
            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(
                repo.tokens[0].expiration.date(),
                datetime.datetime.utcnow().date() + datetime.timedelta(days=60))

            token = repo.tokens[0].id
            output = self.app.post(
                '/test/token/revoke/%s' % token,
                data=data,
                follow_redirects=True)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn(
                '</button>\n                      Token revoked',
                output.data)

            # Existing token has been expired
            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(
                repo.tokens[0].expiration.date(),
                repo.tokens[0].created.date())
            self.assertEqual(
                repo.tokens[0].expiration.date(),
                datetime.datetime.utcnow().date())

    def test_delete_branch(self):
        """ Test the delete_branch endpoint. """
        # No Git repo
        output = self.app.post('/foo/b/master/delete')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(self.path, bare=True)

        # User not logged in
        output = self.app.post('/test/b/master/delete')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            # Unknown repo
            output = self.app.post('/foo/b/master/delete')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/b/master/delete')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/b/master/delete')
            self.assertEqual(output.status_code, 403)
            self.assertIn(
                '<p>You are not allowed to delete the master branch</p>',
                output.data)

            output = self.app.post('/test/b/bar/delete')
            self.assertEqual(output.status_code, 404)
            self.assertIn('<p>Branch no found</p>', output.data)

            # Add a branch that we can delete
            path = os.path.join(self.path, 'test.git')
            tests.add_content_git_repo(path)
            repo = pygit2.Repository(path)
            repo.create_branch('foo', repo.head.get_object())

            # Check before deletion
            output = self.app.get('/test')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'data-toggle="tooltip">foo',
                output.data)
            self.assertIn('<form id="delete_branch_form-foo"', output.data)
            self.assertIn(
                '<strong title="Currently viewing branch master"',
                output.data)

            # Delete the branch
            output = self.app.post('/test/b/foo/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                'data-toggle="tooltip">foo',
                output.data)
            self.assertNotIn(
                '<form id="delete_branch_form-foo"', output.data)
            self.assertIn(
                '<strong title="Currently viewing branch master"',
                output.data)

            # Add a branch with a '/' in its name that we can delete
            path = os.path.join(self.path, 'test.git')
            tests.add_content_git_repo(path)
            repo = pygit2.Repository(path)
            repo.create_branch('feature/foo', repo.head.get_object())

            # Check before deletion
            output = self.app.get('/test')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'data-toggle="tooltip">feature/foo',
                output.data)
            self.assertIn(
                '<form id="delete_branch_form-feature_foo"', output.data)
            self.assertIn(
                '<strong title="Currently viewing branch master"',
                output.data)

            # Delete the branch
            output = self.app.post('/test/b/feature/foo/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                'data-toggle="tooltip">feature/foo',
                output.data)
            self.assertNotIn(
                '<form id="delete_branch_form-feature_foo"', output.data)
            self.assertIn(
                '<strong title="Currently viewing branch master"',
                output.data)

    def test_view_docs(self):
        """ Test the view_docs endpoint. """
        output = self.app.get('/docs/foo/')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/docs/test/')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(self.path, bare=True)

        output = self.app.get('/docs/test/')
        self.assertEqual(output.status_code, 404)

    def test_view_project_activity(self):
        """ Test the view_project_activity endpoint. """
        tests.create_projects(self.session)
        tests.create_projects_git(self.path, bare=True)

        # Project Exists, but No DATAGREPPER_URL set
        output = self.app.get('/test/activity/')
        self.assertEqual(output.status_code, 404)

        # Project Exists, and DATAGREPPER_URL set
        pagure.APP.config['DATAGREPPER_URL'] = 'foo'
        output = self.app.get('/test/activity/')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<title>Activity - test - Pagure</title>', output.data)
        self.assertIn(
            'No activity reported on the test project', output.data)

        # project doesnt exist
        output = self.app.get('/foo/activity/')
        self.assertEqual(output.status_code, 404)

    def test_goimport(self):
        """ Test the go-import tag. """
        tests.create_projects(self.session)
        tests.create_projects_git(self.path, bare=True)
        output = self.app.get('/test/')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<meta name="go-import" '
                      'content="pagure.org/test git git://pagure.org/test.git"'
                      '>',
                      output.data)

    def test_watch_repo(self):
        """ Test the  watch_repo endpoint. """

        output = self.app.post('/watch/')
        self.assertEqual(output.status_code, 405)

        tests.create_projects(self.session)
        tests.create_projects_git(self.path, bare=True)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token':csrf_token
            }
            output = self.app.post(
                '/watch', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            output = self.app.post(
                '/foo/watch/settings', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            output = self.app.post(
                '/test/watch/settings/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 400)

            output = self.app.post(
                '/test/watch/settings/0', data=data, follow_redirects=True)
            self.assertIn(
                '</button>\n                      You are no longer'
                ' watching this repo.', output.data)

            output = self.app.post(
                '/test/watch/settings/1', data=data, follow_redirects=True)
            self.assertIn(
                '</button>\n                      You are now'
                ' watching this repo.', output.data)

            item = pagure.lib.model.Project(
                user_id=2,  # foo
                name='test',
                description='foo project #1',
                hook_token='aaabbb',
                is_fork=True,
                parent_id=1,
            )
            self.session.add(item)
            self.session.commit()
            gitrepo = os.path.join(self.path, 'forks', 'foo', 'test.git')
            pygit2.init_repository(gitrepo, bare=True)

            output = self.app.post(
                '/fork/foo/test/watch/settings/0', data=data,
                follow_redirects=True)
            self.assertIn(
                '</button>\n                      You are no longer'
                ' watching this repo.', output.data)

            output = self.app.post(
                '/fork/foo/test/watch/settings/1', data=data,
                follow_redirects=True)
            self.assertIn(
                '</button>\n                      You are now'
                ' watching this repo.', output.data)

if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagureFlaskRepotests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
