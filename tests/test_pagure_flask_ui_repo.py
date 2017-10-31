# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import datetime
import json
import unittest
import re
import shutil
import sys
import tempfile
import time
import os

import pygit2
from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
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
        pagure.APP.config['UPLOAD_FOLDER_URL'] = '/releases/'
        pagure.APP.config['UPLOAD_FOLDER_PATH'] = os.path.join(
            self.path, 'releases')

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
        tests.create_projects_git(os.path.join(self.path, 'repos'))

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
            tests.create_projects_git(os.path.join(self.path, 'repos'))
            output = self.app.post(
                '/test/adduser', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        pagure.APP.config['ENABLE_USER_MNGT'] = True


    @patch('pagure.ui.repo.admin_session_timedout')
    def test_add_deploykey(self, ast):
        """ Test the add_deploykey endpoint. """
        ast.return_value = False

        # No git repo
        output = self.app.get('/foo/adddeploykey')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        # User not logged in
        output = self.app.get('/test/adddeploykey')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/adddeploykey')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.get('/test/adddeploykey')
            self.assertEqual(output.status_code, 302)

            # Redirect also happens for POST request
            output = self.app.post('/test/adddeploykey')
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
            output = self.app.get('/test/adddeploykey')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Add deploy key to the', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'ssh_key': 'asdf',
                'pushaccess': 'false'
            }

            # No CSRF token
            output = self.app.post('/test/adddeploykey', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<strong>Add deploy key to the' in output.data)

            data['csrf_token'] = csrf_token

            # First, invalid SSH key
            output = self.app.post('/test/adddeploykey', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Add deploy key to the', output.data)
            self.assertIn('Deploy key invalid', output.data)

            # Next up, multiple SSH keys
            data['ssh_key'] = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q==\nssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q=='
            output = self.app.post(
                '/test/adddeploykey', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn('Deploy key can only be single keys.', output.data)

            # Now, a valid SSH key
            data['ssh_key'] = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q=='
            output = self.app.post(
                '/test/adddeploykey', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn('Deploy key added', output.data)
            self.assertNotIn('PUSH ACCESS', output.data)

            # And now, adding the same key
            output = self.app.post(
                '/test/adddeploykey', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn('Deploy key already exists', output.data)

            # And next, a key with push access
            data['ssh_key'] = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQC9Xwc2RDzPBhlEDARfHldGjudIVoa04tqT1JVKGQmyllTFz7Rb8CngQL3e7zyNzotnhwYKHdoiLlPkVEiDee4dWMUe48ilqId+FJZQGhyv8fu4BoFdE1AJUVylzmltbLg14VqG5gjTpXgtlrEva9arKwBMHJjRYc8ScaSn3OgyQw=='
            data['pushaccess'] = 'true'
            output = self.app.post(
                '/test/adddeploykey', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn('Deploy key added', output.data)
            self.assertIn('PUSH ACCESS', output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    @patch.dict('pagure.APP.config', {'DEPLOY_KEY': False})
    def test_add_deploykey_disabled(self, ast):
        """ Test the add_deploykey endpoint when it's disabled in the config.
        """
        ast.return_value = False
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/adddeploykey')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/adddeploykey')
            self.assertEqual(output.status_code, 404)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_add_user(self, ast):
        """ Test the add_user endpoint. """
        ast.return_value = False

        # No git repo
        output = self.app.get('/foo/adduser')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

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

            # Missing access and no CSRF
            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Add user - test - Pagure</title>', output.data)
            self.assertTrue('<strong>Add user to the' in output.data)

            # No CSRF
            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Add user - test - Pagure</title>', output.data)

            # Missing access
            data['csrf_token'] = csrf_token
            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Add user - test - Pagure</title>', output.data)
            self.assertIn('<strong>Add user to the', output.data)

            # Unknown user
            data['access'] = 'commit'
            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Add user - test - Pagure</title>', output.data)
            self.assertIn('<strong>Add user to the', output.data)
            self.assertIn(
                '</button>\n                      No user &#34;ralph&#34; found\n',
                output.data)

            # All correct
            data['user'] = 'foo'
            output = self.app.post(
                '/test/adduser', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
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
        tests.create_projects_git(os.path.join(self.path, 'repos'))

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
        tests.create_projects_git(os.path.join(self.path, 'repos'))

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

            # Missing CSRF
            output = self.app.post('/test/addgroup', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Add group - test - Pagure</title>', output.data)
            self.assertIn('<strong>Add group to the', output.data)

            # Missing access
            data['csrf_token'] = csrf_token
            output = self.app.post('/test/addgroup', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Add group - test - Pagure</title>', output.data)
            self.assertIn('<strong>Add group to the', output.data)

            # Unknown group
            data['access'] = 'ticket'
            output = self.app.post('/test/addgroup', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Add group - test - Pagure</title>', output.data)
            self.assertIn('<strong>Add group to the', output.data)
            self.assertIn(
                '</button>\n                      No group ralph found.',
                output.data)

            # All good
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
            tests.create_projects_git(os.path.join(self.path, 'repos'))

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
        repo = pagure.get_authorized_project(self.session, 'test')
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
    def test_remove_deploykey(self, ast):
        """ Test the remove_deploykey endpoint. """
        ast.return_value = False

        # Git repo not found
        output = self.app.post('/foo/dropdeploykey/1')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/dropdeploykey/1')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(os.path.join(self.path, 'repos'))

            output = self.app.post('/test/dropdeploykey/1')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.post('/test/dropdeploykey/1')
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

        # User not logged in
        output = self.app.post('/test/dropdeploykey/1')
        self.assertEqual(output.status_code, 302)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/settings')

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'csrf_token': csrf_token}

            output = self.app.post(
                '/test/dropdeploykey/1', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn('Deploy key does not exist in project', output.data)

        # Add a deploy key to a project
        repo = pagure.get_authorized_project(self.session, 'test')
        msg = pagure.lib.add_deploykey_to_project(
            session=self.session,
            project=repo,
            ssh_key='ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q==',
            pushaccess=True,
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Deploy key added')

        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/dropdeploykey/1', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertNotIn('Deploy key removed', output.data)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/dropdeploykey/1', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn('Deploy key removed', output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    @patch.dict('pagure.APP.config', {'DEPLOY_KEY': False})
    def test_remove_deploykey_disabled(self, ast):
        """ Test the remove_deploykey endpoint when it's disabled in the
        config.
        """
        ast.return_value = False
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/dropdeploykey/1')
            self.assertEqual(output.status_code, 404)

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
            tests.create_projects_git(os.path.join(self.path, 'repos'))

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
                '</button>\n                      User does not have any '
                'access on the repo', output.data)

        # Add an user to a project
        repo = pagure.get_authorized_project(self.session, 'test')
        self.assertEqual(len(repo.users), 0)
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')
        self.assertEqual(len(repo.users), 1)

        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/dropuser/2', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertNotIn(
                '</button>\n                      User removed', output.data)
            self.assertIn('action="/test/dropuser/2">', output.data)
            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertEqual(len(repo.users), 1)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/dropuser/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '</button>\n                      User removed', output.data)
            self.assertNotIn('action="/test/dropuser/2">', output.data)
            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertEqual(len(repo.users), 0)


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
        tests.create_projects_git(os.path.join(self.path, 'repos'))

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

        repo = pagure.get_authorized_project(self.session, 'test')
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
            tests.create_projects_git(os.path.join(self.path, 'repos'))

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

        repo = pagure.get_authorized_project(self.session, 'test')
        # Add the group to a project
        msg = pagure.lib.add_group_to_project(
            session=self.session,
            project=repo,
            new_group='testgrp',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

        repo = pagure.get_authorized_project(self.session, 'test')
        self.assertEqual(len(repo.groups), 1)

        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/dropgroup/1', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn('action="/test/dropgroup/1">', output.data)
            self.assertNotIn(
                '</button>\n                      Group removed',
                output.data)
            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertEqual(len(repo.groups), 1)

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
            self.assertNotIn('action="/test/dropgroup/1">', output.data)
            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertEqual(len(repo.groups), 0)

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
            tests.create_projects_git(os.path.join(self.path, 'repos'))

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
    def test_update_project_update_tag(self, ast):
        """ Test the view_settings endpoint when updating the project's tags.

        We had an issue where when you add an existing tag to a project we
        were querying the wrong table in the database. It would thus not find
        the tag, would try to add it, and (rightfully) complain about duplicated
        content.
        This test ensure we are behaving properly.
        """
        ast.return_value = False

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):

            output = self.app.get('/test/settings')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Add tag to a project so that they are added to the database
            data = {
                'csrf_token': csrf_token,
                'description': 'Test project',
                'tags': 'test,pagure,tag',
            }
            output = self.app.post(
                '/test/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '</button>\n                      Project updated',
                output.data)

            # Remove two of the tags of the project, they will still be in
            # the DB but not associated to this project
            data = {
                'csrf_token': csrf_token,
                'description': 'Test project',
                'tags': 'tag',
            }
            output = self.app.post(
                '/test/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn(
                '</button>\n                      Project updated',
                output.data)

            # Try re-adding the two tags, this used to fail before we fixed
            # it
            data = {
                'csrf_token': csrf_token,
                'description': 'Test project',
                'tags': 'test,pagure,tag',
            }
            output = self.app.post(
                '/test/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
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
            tests.create_projects_git(os.path.join(self.path, 'repos'))

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

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_fields_in_view_settings(self, ast):
        """ Test the default fields in view_settings endpoint. """
        ast.return_value = False

        # No Git repo
        output = self.app.get('/foo/settings')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/foo/settings')
            self.assertEqual(output.status_code, 404)

            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbccc',
            )
            self.session.add(item)
            self.session.commit()
            tests.create_projects_git(os.path.join(self.path, 'repos'))

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
            # Check that the priorities have their empty fields
            self.assertIn(
            '''<div id="priorities">
              <div class="row p-t-1">
                <div class="col-sm-2 p-r-0">
                  <input type="text" name="priority_weigth"
                    value="" size="3" class="form-control"/>
                </div>
                <div class="col-sm-9 p-r-0">
                  <input type="text" name="priority_title"
                    value="" class="form-control"/>
                </div>
              </div>
          </div>''', output.data)

            # Check that the milestones have their empty fields
            self.assertIn(
            '''<div id="milestones">
              <div class="row p-t-1">
                <div class="col-sm-6 p-r-0">
                  <input type="text" name="milestones"
                    value="" size="3" class="form-control"/>
                </div>
                <div class="col-sm-6 p-r-0">
                  <input type="text" name="milestone_dates"
                    value="" class="form-control"/>
                </div>
              </div>''', output.data)

            # Check that the close_status have its empty field
            self.assertIn(
            '''<div id="close_sstatus">
              <div class="row p-t-1">
                <div class="col-sm-12 p-r-0">
                  <input type="text" name="close_status"
                    value="" class="form-control"/>
                </div>
              </div>''', output.data)

            # Check that the custom fields have their empty fields
            self.assertIn(
            '''<div id="custom_fields">
              <div class="row p-t-1">
                <div class="col-sm-3 p-r-0">
                  <input type="text" name="custom_keys"
                    value="" class="form-control"/>
                </div>
                <div class="col-sm-2 p-r-0">
                  <select name="custom_keys_type" class="form-control">
                    <option value="text" >Text</option>
                    <option value="boolean" >Boolean</option>
                    <option value="link" >Link</option>
                    <option value="list" >List</option>
                  </select>
                </div>
                <div class="col-sm-6 p-r-0">
                    <input title="Comma separated list items" type="text" name="custom_keys_data"
                      value="" class="form-control"/>
                </div>
                <div class="col-sm-1 p-r-0">
                  <input type="checkbox" name="custom_keys_notify-1" title="Trigger email notification when updated"
                  class="form-control"/>
                </div>
              </div>''', output.data)

    def test_view_forks(self):
        """ Test the view_forks endpoint. """

        output = self.app.get('/foo/forks', follow_redirects=True)
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/forks', follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertTrue('This project has not been forked.' in output.data)

    @patch.dict('pagure.APP.config', {'CASE_SENSITIVE': True})
    def test_view_repo_case_sensitive(self):
        """ Test the view_repo endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>This repo is brand new!</p>' in output.data)

        output = self.app.get('/TEST')
        self.assertEqual(output.status_code, 404)

    def test_view_repo(self):
        """ Test the view_repo endpoint. """

        output = self.app.get('/foo')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test')
        # No git repo associated
        self.assertEqual(output.status_code, 404)
        self.perfMaxWalks(0, 0)
        self.perfReset()

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>This repo is brand new!</p>' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)
        self.perfMaxWalks(0, 0)
        self.perfReset()

        output = self.app.get('/test/')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>This repo is brand new!</p>' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)
        self.perfMaxWalks(0, 0)
        self.perfReset()

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'repos',
                                                'test.git'))
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        self.perfReset()

        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)
        self.perfMaxWalks(3, 8)  # Target: (1, 3)
        self.perfReset()

        # Turn that repo into a fork
        repo = pagure.get_authorized_project(self.session, 'test')
        repo.parent_id = 2
        repo.is_fork = True
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get('/test')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test.git'))

        output = self.app.get('/fork/pingou/test')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)
        self.assertTrue('Forked from' in output.data)
        self.perfMaxWalks(1, 3)
        self.perfReset()

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
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #3        </div>', output.data)
        self.assertTrue('Forked from' in output.data)
        self.perfMaxWalks(3, 18)  # Ideal: (1, 3)
        self.perfReset()

    def test_view_repo_empty(self):
        """ Test the view_repo endpoint on a repo w/o master branch. """

        tests.create_projects(self.session)
        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
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

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'repos',
                                                'test.git'))
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))

        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)

        # Turn that repo into a fork
        repo = pagure.get_authorized_project(self.session, 'test')
        repo.parent_id = 2
        repo.is_fork = True
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test.git'))

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
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'),
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

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<p>This repo is brand new!</p>', output.data)
        self.assertIn(
            '<div class="projectinfo m-t-1 m-b-1">\n'
            'test project #1        </div>', output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'repos',
                                                'test.git'))
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))

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
        repo = pagure.get_authorized_project(self.session, 'test')
        repo.parent_id = 2
        repo.is_fork = True
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test.git'))

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
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'),
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
                '<span>Commits&nbsp;</span>\n      ' +
                '<span ' +
                'class="label label-default label-pill">' +
                '\n        2\n      </span>',
                output.data)
            self.assertIn(
                '<span style="color: #a40000; background-color: #ffdddd">- ' +
                'Row 0', output.data)
            # View inverse commits comparison
            output = self.app.get('/test/c/%s..%s' % (c1.oid.hex, c2.oid.hex))
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Diff from %s to %s - test\n - Pagure</title>' %
                (c1.oid.hex, c2.oid.hex),
                output.data)
            self.assertIn(
                '<span>Commits&nbsp;</span>\n      ' +
                '<span ' +
                'class="label label-default label-pill">' +
                '\n        2\n      </span>',
                output.data)
            self.assertIn(
                '<h5 class="text-muted">%s .. %s</h5>' %
                (c1.oid.hex, c2.oid.hex),
                output.data)
            self.assertIn(
                '<span style="color: #00A000; background-color: #ddffdd">' +
                '+ Row 0', output.data)

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
                '<span style="color: #00A000; background-color: ' +
                '#ddffdd">+ Row 0</span>', output.data)
            self.assertEqual(
                output.data.count(
                '<span style="color: #00A000; background-color: ' +
                '#ddffdd">+ Row 0'), 2)
            self.assertIn(
                '<span>Commits&nbsp;</span>\n      ' +
                '<span ' +
                'class="label label-default label-pill">' +
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
                '<span style="color: #800080; font-weight: bold">@@ -1,2 +1,1' +
                ' @@', output.data)
            self.assertIn(
                '<span style="color: #a40000; background-color: #ffdddd">- ' +
                'Row 0</span>', output.data)
            self.assertIn(
                '<span>Commits&nbsp;</span>\n      ' +
                '<span ' +
                'class="label label-default label-pill">' +
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

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/bar')
        self.assertEqual(output.status_code, 404)

        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))

        # Add one commit to git repo
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), ncommits=1)
        c1 = repo.revparse_single('HEAD')

        # Add another commit to git repo
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), ncommits=1)
        c2 = repo.revparse_single('HEAD')

        # Add one more commit to git repo
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'test.git'),
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

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/blob/foo/f/sources')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'repos',
                                                'test.git'))
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_binary_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), 'test.jpg')
        tests.add_binary_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), 'test_binary')

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

        # Empty files should also be displayed
        tests.add_content_to_git(
            os.path.join(self.path, 'repos', 'test.git'),
            filename="emptyfile.md",
            content="")
        output = self.app.get('/test/blob/master/f/emptyfile.md')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<a class="btn btn-secondary btn-sm" '
            'href="/test/raw/master/f/emptyfile.md" '
            'title="View as raw">Raw</a>', output.data)
        self.assertIn(
            '<div class="m-a-2">\n'
            '        \n      </div>', output.data)

        # View what's supposed to be an image
        output = self.app.get('/test/blob/master/f/test.jpg')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'Binary files cannot be rendered.<br/>', output.data)
        self.assertIn(
            '<a href="/test/raw/master/f/test.jpg">view the raw version',
            output.data)

        # View by commit id
        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
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

        # Verify the nav links correctly when viewing a nested folder/file.
        output = self.app.get('/test/blob/master/f/folder1/folder2/file')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<li><a href="/test/blob/master/f/folder1/folder2">\n'
            '            <span class="oi" data-glyph="folder">'
            '</span>&nbsp; folder2</a>\n'
            '          </li>', output.data)

        # View by image name -- with a non-existant file
        output = self.app.get('/test/blob/sources/f/testfoo.jpg')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/blob/master/f/folder1/testfoo.jpg')
        self.assertEqual(output.status_code, 404)

        # View file with a non-ascii name
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'test.git'),
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
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        # Verify the nav links correctly when viewing a file/folder in a fork.
        output = self.app.get(
            '/fork/pingou/test3/blob/master/f/folder1/folder2/file')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<li><a href="/fork/pingou/test3/blob/master/f/folder1/folder2">\n'
            '            <span class="oi" data-glyph="folder"></span>&nbsp; '
            'folder2</a>\n          </li>', output.data)


        output = self.app.get('/fork/pingou/test3/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<table class="code_table">', output.data)
        self.assertIn(
            '<tr><td class="cell1"><a id="_1" href="#_1" data-line-number="1"></a></td>',
            output.data)
        self.assertIn(
            '<td class="cell2"><pre> barRow 0</pre></td>', output.data)

    @patch(
        'pagure.lib.encoding_utils.decode',
        MagicMock(side_effect=pagure.exceptions.PagureException))
    def test_view_file_with_wrong_encoding(self):
        """ Test the view_file endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'repos',
                                                'test.git'))
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_binary_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), 'test.jpg')
        tests.add_binary_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), 'test_binary')

        # View file
        output = self.app.get('/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertIn('Binary files cannot be rendered.<br/>', output.data)

    def test_view_raw_file(self):
        """ Test the view_raw_file endpoint. """
        output = self.app.get('/foo/raw/foo/sources')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/raw/foo/sources')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/raw/foo/sources')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))

        # View first commit
        output = self.app.get('/test/raw/master')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.headers['Content-Type'].lower(),
                         'text/plain; charset=ascii')
        self.assertTrue(':Author: Pierre-Yves Chibon' in output.data)

        # Add some more content to the repo
        tests.add_content_git_repo(os.path.join(self.path, 'repos',
                                                'test.git'))
        tests.add_binary_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), 'test.jpg')
        tests.add_binary_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), 'test_binary')

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
        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
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
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'),
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

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/blame/sources')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'repos',
                                                'test.git'))
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos','test.git'),
            branch='feature')
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_binary_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), 'test.jpg')
        tests.add_binary_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), 'test_binary')

        output = self.app.get('/test/blame/foofile')
        self.assertEqual(output.status_code, 404)
        regex = re.compile('>(\w+)</a></td>\n<td class="cell2">')

        # View in master branch
        output = self.app.get('/test/blame/sources')
        self.assertEqual(output.status_code, 200)
        self.assertIn(b'<table class="code_table">', output.data)
        self.assertIn(
            b'<tr><td class="cell1"><a id="1" href="#1" '
            b'data-line-number="1"></a></td>', output.data)
        self.assertIn(
            b'<td class="cell2"><pre> bar</pre></td>', output.data)
        data = regex.findall(output.data)
        self.assertEqual(len(data), 2)

        # View in feature branch
        output = self.app.get('/test/blame/sources?identifier=feature')
        self.assertEqual(output.status_code, 200)
        self.assertIn(b'<table class="code_table">', output.data)
        self.assertIn(
            b'<tr><td class="cell1"><a id="1" href="#1" '
            b'data-line-number="1"></a></td>', output.data)
        self.assertIn(
            b'<td class="cell2"><pre> bar</pre></td>', output.data)
        data2 = regex.findall(output.data)
        self.assertEqual(len(data2), 2)
        self.assertNotEqual(data, data2)

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
            os.path.join(self.path, 'repos', 'test.git'),
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
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'),
            ncommits=10)
        tests.add_content_to_git(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'),
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

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/c/bar')
        self.assertEqual(output.status_code, 404)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View first commit
        output = self.app.get('/test/c/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.data)
        self.assertTrue('  Merged by Alice Author\n' in output.data)
        self.assertTrue('  Committed by Cecil Committer\n' in output.data)

        # View first commit - with the old URL scheme disabled - default
        output = self.app.get(
            '/test/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 404)
        self.assertIn('<p>Project not found</p>', output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'repos',
                                                'test.git'))

        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
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
            '<span style="background-color: #f0f0f0' in
            output.data)

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
            self.path, 'repos', 'forks', 'pingou', 'test3.git')

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
            '<span style="background-color: #f0f0f0; padding: 0 5px 0 5px"> 2' +
            ' </span><span style="color: #00A000; background-color: #ddffdd">' +
            '+ Pagure</span>' in output.data)
        self.assertTrue(
            '<span style="background-color: #f0f0f0; padding: 0 5px 0 5px"> 3' +
            ' </span><span style="color: #00A000; background-color: #ddffdd">' +
            '+ ======</span>' in output.data)

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

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/c/bar.patch')
        self.assertEqual(output.status_code, 404)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
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
        tests.add_content_git_repo(os.path.join(self.path, 'repos',
                                                'test.git'))

        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
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
        forkedgit = os.path.join(self.path, 'repos', 'forks', 'pingou',
                                 'test3.git')

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

    def test_view_commit_diff(self):
        """ Test the view_commit_diff endpoint. """

        # No project registered in the DB
        output = self.app.get('/foo/c/bar.diff')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/c/bar.diff')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/c/bar.diff')
        self.assertEqual(output.status_code, 404)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View first commit
        output = self.app.get('/test/c/%s.diff' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertEqual('''diff --git a/README.rst b/README.rst
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
''', output.data)

    def test_view_tree(self):
        """ Test the view_tree endpoint. """
        output = self.app.get('/foo/tree/')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/tree/')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

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
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
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
        forkedgit = os.path.join(self.path, 'repos', 'forks', 'pingou',
                                 'test3.git')

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

    @patch.dict('pagure.APP.config', {'ENABLE_DEL_PROJECTS': False})
    @patch('pagure.lib.notify.send_email')
    @patch('pagure.ui.repo.admin_session_timedout')
    def test_delete_repo_when_turned_off(self, ast, send_email):
        """ Test the delete_repo endpoint when deletion of a repo is
        turned off in the pagure instance """
        ast.return_value = False
        send_email.return_value = True

        # No Git repo
        output = self.app.post('/foo/delete')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            tests.create_projects(self.session)
            tests.create_projects_git(os.path.join(self.path, 'repos'))

            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        # User not logged in
        output = self.app.post('/test/delete')
        self.assertEqual(output.status_code, 302)

        # Ensure the project isn't read-only
        repo = pagure.get_authorized_project(self.session, 'test')
        repo.read_only = False
        self.session.add(repo)
        self.session.commit()

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
            tests.create_projects_git(os.path.join(self.path, 'repos'))
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
            tests.create_projects_git(os.path.join(self.path, 'repos'))
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
            repo = pagure.get_authorized_project(self.session, 'test')
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

            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertNotEqual(repo, None)
            repo = pagure.get_authorized_project(self.session, 'test2')
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
                os.path.join(self.path, 'repos', 'forks', 'pingou',
                             'test3.git'))
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

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.ui.repo.admin_session_timedout')
    def test_delete_read_only_repo(self, ast, send_email):
        """ Test the delete_repo endpoint when the repo is read_only """
        ast.return_value = False
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

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
        tests.create_projects_git(os.path.join(self.path, 'repos'))
        tests.create_projects_git(os.path.join(self.path, 'docs'))
        tests.create_projects_git(
            os.path.join(self.path, 'tickets'), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):

            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertNotEqual(repo, None)
            repo.read_only = True
            self.session.add(repo)
            self.session.commit()

            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                u'<title>Settings - test - Pagure</title>', output.data)
            self.assertIn(
                u'The ACLs of this project are being refreshed in the '
                u'backend this prevents the project from being deleted. '
                u'Please wait for this task to finish before trying again. '
                u'Thanks!', output.data)
            self.assertIn(
                u'title="Action disabled while project\'s ACLs are being refreshed">',
                output.data)

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
            tests.create_projects_git(os.path.join(self.path, 'repos'))

            # No project registered in the DB (no git repo)
            output = self.app.post('/foo/delete')
            self.assertEqual(output.status_code, 404)

            # User not allowed
            output = self.app.post('/test/delete')
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.post('/test/delete')
        self.assertEqual(output.status_code, 302)

        # Ensure the project isn't read-only
        repo = pagure.get_authorized_project(self.session, 'test')
        repo.read_only = False
        self.session.add(repo)
        self.session.commit()

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            tests.create_projects_git(os.path.join(self.path, 'repos'))

            ast.return_value = True
            output = self.app.post('/test/delete')
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
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
                read_only=False,
            )
            self.session.add(item)
            self.session.commit()
            tests.create_projects_git(os.path.join(self.path, 'repos'))

            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
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
                read_only=False,
            )
            self.session.add(item)
            self.session.commit()
            tests.create_projects_git(os.path.join(self.path, 'repos'))
            tests.create_projects_git(os.path.join(self.path, 'docs'))
            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            Projects <span '
                'class="label label-default">2</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            # All repo there
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbiii',
                read_only=False,
            )
            self.session.add(item)
            self.session.commit()

            # Create all the git repos
            tests.create_projects_git(os.path.join(self.path, 'repos'))
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
            repo = pagure.get_authorized_project(self.session, 'test')
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

            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertEqual(repo, None)
            repo = pagure.get_authorized_project(self.session, 'test2')
            self.assertNotEqual(repo, None)

            # Add a fork of a fork
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test3',
                description='test project #3',
                is_fork=True,
                parent_id=2,
                hook_token='aaabbbjjj',
                read_only=False,
            )
            self.session.add(item)
            self.session.commit()
            tests.add_content_git_repo(
                os.path.join(self.path, 'repos', 'forks', 'pingou',
                             'test3.git'))
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

    @patch.dict('pagure.APP.config', {'TICKETS_FOLDER': None})
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    @patch('pagure.ui.repo.admin_session_timedout', MagicMock(return_value=False))
    def test_delete_repo_no_ticket(self):
        """ Test the delete_repo endpoint when tickets aren't enabled in
        this pagure instance. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        # Ensure the project isn't read-only
        repo = pagure.get_authorized_project(self.session, 'test')
        repo.read_only = False
        self.session.add(repo)
        self.session.commit()

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            # Check before deleting the project
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">3</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            # Delete the project
            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            # Check deletion worked
            self.assertIn(
                '<div class="card-header">\n            Projects <span '
                'class="label label-default">2</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.ui.repo.admin_session_timedout')
    def test_delete_repo_with_users(self, ast, send_email):
        """ Test the delete_repo endpoint. """
        ast.return_value = False
        send_email.return_value = True

        user = tests.FakeUser()
        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            # Create new project
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbiii',
                read_only=False,
            )
            self.session.add(item)
            self.session.commit()

            # Create all the git repos
            tests.create_projects_git(os.path.join(self.path, 'repos'))
            tests.create_projects_git(
                os.path.join(self.path, 'docs'), bare=True)
            tests.create_projects_git(
                os.path.join(self.path, 'tickets'), bare=True)
            tests.create_projects_git(
                os.path.join(self.path, 'requests'), bare=True)

            # Check repo was created
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">1</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            # add user
            repo = pagure.get_authorized_project(self.session, 'test')
            msg = pagure.lib.add_user_to_project(
                session=self.session,
                project=repo,
                new_user='foo',
                user='pingou',
            )
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # Ensure the project isn't read-only (because adding an user
            # will trigger an ACL refresh, thus read-only)
            repo = pagure.get_authorized_project(self.session, 'test')
            repo.read_only = False
            self.session.add(repo)
            self.session.commit()

            # Check before deleting the project
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">1</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)
            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertNotEqual(repo, None)
            repo = pagure.get_authorized_project(self.session, 'test2')
            self.assertEqual(repo, None)

            # Delete the project
            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            Projects <span '
                'class="label label-default">0</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            # Check after
            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertEqual(repo, None)
            repo = pagure.get_authorized_project(self.session, 'test2')
            self.assertEqual(repo, None)

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.ui.repo.admin_session_timedout')
    def test_delete_repo_with_group(self, ast, send_email):
        """ Test the delete_repo endpoint. """
        ast.return_value = False
        send_email.return_value = True

        user = tests.FakeUser()
        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            # Create new project
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbiii',
                read_only=False,
            )
            self.session.add(item)
            self.session.commit()

            # Create all the git repos
            tests.create_projects_git(os.path.join(self.path, 'repos'))
            tests.create_projects_git(
                os.path.join(self.path, 'docs'), bare=True)
            tests.create_projects_git(
                os.path.join(self.path, 'tickets'), bare=True)
            tests.create_projects_git(
                os.path.join(self.path, 'requests'), bare=True)

            # Check repo was created
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">1</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            # Create group
            msg = pagure.lib.add_group(
                self.session,
                group_name='foo',
                display_name='foo group',
                description=None,
                group_type='bar',
                user='pingou',
                is_admin=False,
                blacklist=[],
            )
            self.session.commit()
            self.assertEqual(msg, 'User `pingou` added to the group `foo`.')

            # Add group to the project
            repo = pagure.get_authorized_project(self.session, 'test')
            msg = pagure.lib.add_group_to_project(
                session=self.session,
                project=repo,
                new_group='foo',
                user='pingou',
            )
            self.session.commit()
            self.assertEqual(msg, 'Group added')

            # Ensure the project isn't read-only (because adding a group
            # will trigger an ACL refresh, thus read-only)
            repo = pagure.get_authorized_project(self.session, 'test')
            repo.read_only = False
            self.session.add(repo)
            self.session.commit()

            # check if group where we expect it
            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertEqual(len(repo.projects_groups), 1)

            # Check before deleting the project
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">1</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)
            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertNotEqual(repo, None)

            # Delete the project
            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            Projects <span '
                'class="label label-default">0</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            # Check after
            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertEqual(repo, None)

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.ui.repo.admin_session_timedout')
    def test_delete_repo_with_coloredtag(self, ast, send_email):
        """ Test the delete_repo endpoint. """
        ast.return_value = False
        send_email.return_value = True

        user = tests.FakeUser()
        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            # Create new project
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbiii',
                read_only=False,
            )
            self.session.add(item)
            self.session.commit()

            # Create all the git repos
            tests.create_projects_git(os.path.join(self.path, 'repos'))
            tests.create_projects_git(
                os.path.join(self.path, 'docs'), bare=True)
            tests.create_projects_git(
                os.path.join(self.path, 'tickets'), bare=True)
            tests.create_projects_git(
                os.path.join(self.path, 'requests'), bare=True)

            # Check repo was created
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">1</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            # Create the issue
            repo = pagure.get_authorized_project(self.session, 'test')
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

            # Add a tag to the issue
            repo = pagure.get_authorized_project(self.session, 'test')
            issue = pagure.lib.search_issues(self.session, repo, issueid=1)
            msg = pagure.lib.add_tag_obj(
                session=self.session,
                obj=issue,
                tags='tag1',
                user='pingou',
                ticketfolder=None)
            self.session.commit()
            self.assertEqual(msg, 'Issue tagged with: tag1')

            # Check before deleting the project
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            My Projects <span '
                'class="label label-default">1</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)
            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertNotEqual(repo, None)
            repo = pagure.get_authorized_project(self.session, 'test2')
            self.assertEqual(repo, None)

            # Delete the project
            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            Projects <span '
                'class="label label-default">0</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            # Check after
            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertEqual(repo, None)
            repo = pagure.get_authorized_project(self.session, 'test2')
            self.assertEqual(repo, None)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_new_repo_hook_token(self, ast):
        """ Test the new_repo_hook_token endpoint. """
        ast.return_value = False
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        repo = pagure.get_authorized_project(self.session, 'test')
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

        repo = pagure.get_authorized_project(self.session, 'test')
        self.assertEqual(repo.hook_token, 'aaabbbccc')

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            pagure.APP.config['WEBHOOK'] = True
            output = self.app.post('/test/hook_token')
            self.assertEqual(output.status_code, 400)

            data = {'csrf_token': csrf_token}

            repo = pagure.get_authorized_project(self.session, 'test')
            self.assertEqual(repo.hook_token, 'aaabbbccc')

            output = self.app.post(
                '/test/hook_token', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      New hook token generated',
                output.data)
            pagure.APP.config['WEBHOOK'] = False

        repo = pagure.get_authorized_project(self.session, 'test')
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
        tests.create_projects_git(os.path.join(self.path, 'repos'))

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
            repo = pagure.get_authorized_project(self.session, 'test')
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
            repo = pagure.get_authorized_project(self.session, 'test')
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

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/releases')
        self.assertEqual(output.status_code, 200)
        self.assertIn('This project has not been tagged.', output.data)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
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
            tests.create_projects_git(os.path.join(self.path, 'repos'),
                                      bare=True)

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
            tests.add_content_git_repo(os.path.join(self.path, 'repos',
                                                    'test.git'))
            tests.add_readme_git_repo(os.path.join(self.path, 'repos',
                                                   'test.git'))
            tests.add_binary_git_repo(
                os.path.join(self.path, 'repos', 'test.git'), 'test.jpg')
            tests.add_binary_git_repo(
                os.path.join(self.path, 'repos', 'test.git'), 'test_binary')

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

            # Verify the nav links correctly when editing a file.
            output = self.app.get('/test/blob/master/f/folder1/folder2/file')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li><a href="/test/blob/master/f/folder1/folder2">\n'
                '            <span class="oi" data-glyph="folder">'
                '</span>&nbsp; folder2</a>\n'
                '          </li>', output.data)

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
            self.assertIn('test commit', output.data)

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
                os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
            tests.add_readme_git_repo(
                os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'))
            tests.add_commit_git_repo(
                os.path.join(self.path, 'repos', 'forks', 'pingou', 'test3.git'),
                ncommits=10)

            # Verify the nav links correctly when editing a file in a fork.
            output = self.app.get(
                '/fork/pingou/test3/edit/master/f/folder1/folder2/file')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li><a\n      '
                'href="/fork/pingou/test3/blob/master/f/folder1/folder2"\n'
                '        ><span class="oi" data-glyph="folder"></span>&nbsp; '
                'folder2</a>\n        </li>', output.data)

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
            self.assertIn('test commit', output.data)

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
            repos = tests.create_projects_git(os.path.join(self.path, 'repos'))

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
            repo = tests.create_projects_git(os.path.join(self.path, 'repos'))

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

            upload_dir = os.path.join(self.path, 'releases')
            self.assertEqual(os.listdir(upload_dir), [])

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

            self.assertEqual(os.listdir(upload_dir), ['test'])
            folder = os.path.join(upload_dir, 'test')
            checksum_file = os.path.join(folder, 'CHECKSUMS')

            # Wait for the worker to create the checksums file
            cnt = 0
            while not os.path.exists(checksum_file):
                print os.listdir(os.path.join(upload_dir, 'test'))
                cnt += 1
                if cnt == 40:
                    raise ValueError(
                        'The worker did not create the checksums file '
                        'in a timely manner')
                time.sleep(0.5)

            self.assertEqual(len(os.listdir(folder)), 2)

            self.assertTrue(os.path.exists(checksum_file))

            # Check the content of the checksums file
            with open(checksum_file) as stream:
                data = stream.readlines()
            self.assertEqual(len(data), 3)
            self.assertEqual(data[0], '# Generated and updated by pagure\n')
            self.assertTrue(data[1].startswith('SHA256 ('))
            self.assertTrue(data[1].endswith(
                'tests_placebo.png) = 8a06845923010b27bfd8e7e75acff'
                '7badc40d1021b4994e01f5e11ca40bc3abe\n'))
            self.assertTrue(data[2].startswith('SHA512 ('))
            self.assertTrue(data[2].endswith(
                'tests_placebo.png) = 65a4458df0acb29dc3c5ad4a3620e'
                '98841d1fcf3f8df358f5348fdeddd1a86706491ac6e416768e'
                '9f218aae8147d6ac524a59d3eb91fb925fdcb5c489e55ccbb\n'))

            # Try uploading the same file -- fails
            with open(img, mode='rb') as stream:
                data = {'filestream': stream, 'csrf_token': csrf_token}
                output = self.app.post(
                    '/test/upload/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      This tarball has already '
                'been uploaded', output.data)
            self.assertIn('This project has not been tagged.', output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_add_token_all_tokens(self, ast):
        """ Test the add_token endpoint. """
        ast.return_value = False
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/token/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create a new token</strong>', output.data)
            self.assertEqual(
                output.data.count('<label class="c-input c-checkbox">'),
                len(pagure.APP.config['ACLS'].keys()) - 1
            )

    @patch.dict('pagure.APP.config', {'USER_ACLS': ['create_project']})
    @patch('pagure.ui.repo.admin_session_timedout')
    def test_add_token_one_token(self, ast):
        """ Test the add_token endpoint. """
        ast.return_value = False
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/token/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create a new token</strong>', output.data)
            self.assertEqual(
                output.data.count('<label class="c-input c-checkbox">'),
                1
            )

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
            tests.create_projects_git(os.path.join(self.path, 'repos'),
                                      bare=True)

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
            self.assertIn(
                    '</button>\n                      You must select at least '
                    'one permission.', output.data)

            data = {
                'csrf_token': csrf_token,
                'acls': ['issue_create'],
                'description': 'Test token',
            }

            # New token created
            output = self.app.post(
                '/test/token/new/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Token created', output.data)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            self.assertIn('<strong>Test token</strong>', output.data)
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
            tests.create_projects_git(os.path.join(self.path, 'repos'),
                                      bare=True)

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
            repo = pagure.get_authorized_project(self.session, 'test')
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
            repo = pagure.get_authorized_project(self.session, 'test')
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
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

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
            self.assertIn('<p>Branch not found</p>', output.data)

            # Add a branch that we can delete
            path = os.path.join(self.path, 'repos', 'test.git')
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
            path = os.path.join(self.path, 'repos', 'test.git')
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
                '<form id="delete_branch_form-feature__foo"', output.data)
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
                '<form id="delete_branch_form-feature__foo"', output.data)
            self.assertIn(
                '<strong title="Currently viewing branch master"',
                output.data)

    @patch.dict('pagure.APP.config', {'ALLOW_DELETE_BRANCH': False})
    def test_delete_branch_disabled_in_ui(self):
        """ Test that the delete branch button doesn't show when the feature
        is turned off. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        # Add a branch that we can delete
        path = os.path.join(self.path, 'repos', 'test.git')
        tests.add_content_git_repo(path)
        repo = pygit2.Repository(path)
        repo.create_branch('foo', repo.head.get_object())

        user = tests.FakeUser(username = 'pingou')
        with tests.user_set(pagure.APP, user):
            # Check that the UI doesn't offer the button
            output = self.app.get('/test')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'data-toggle="tooltip">foo',
                output.data)
            self.assertNotIn('<form id="delete_branch_form-foo"', output.data)
            self.assertNotIn(
                'Are you sure you want to remove the branch',
                output.data)

    @patch.dict('pagure.APP.config', {'ALLOW_DELETE_BRANCH': False})
    def test_delete_branch_disabled(self):
        """ Test the delete_branch endpoint when it's disabled in the entire
        instance. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        # Add a branch that we can delete
        path = os.path.join(self.path, 'repos', 'test.git')
        tests.add_content_git_repo(path)
        repo = pygit2.Repository(path)
        repo.create_branch('foo', repo.head.get_object())

        user = tests.FakeUser(username = 'pingou')
        with tests.user_set(pagure.APP, user):
            # Delete the branch
            output = self.app.post('/test/b/foo/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 404)

    def test_view_docs(self):
        """ Test the view_docs endpoint. """
        output = self.app.get('/docs/foo/')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/docs/test/')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/docs/test/')
        self.assertEqual(output.status_code, 404)

    def test_view_project_activity(self):
        """ Test the view_project_activity endpoint. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

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
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
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
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

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
                '/foo/watch/settings/1', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            output = self.app.post(
                '/test/watch/settings/8', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 400)

            output = self.app.post(
                '/test/watch/settings/0', data=data, follow_redirects=True)
            self.assertIn(
                '</button>\n                      You are no longer'
                ' watching this project', output.data)

            output = self.app.post(
                '/test/watch/settings/1', data=data, follow_redirects=True)
            self.assertIn(
                '</button>\n                      You are now'
                ' watching issues and PRs on this project', output.data)

            output = self.app.post(
                '/test/watch/settings/2', data=data, follow_redirects=True)
            self.assertIn(
                '</button>\n                      You are now'
                ' watching commits on this project', output.data)

            output = self.app.post(
                '/test/watch/settings/3', data=data, follow_redirects=True)
            self.assertIn(
                ('</button>\n                      You are now'
                 ' watching issues, PRs, and commits on this project'),
                output.data)

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
            gitrepo = os.path.join(self.path, 'repos', 'forks', 'foo',
                                   'test.git')
            pygit2.init_repository(gitrepo, bare=True)

            output = self.app.post(
                '/fork/foo/test/watch/settings/-1', data=data,
                follow_redirects=True)
            self.assertIn(
                '</button>\n                      Watch status is already reset',
                output.data)

            output = self.app.post(
                '/fork/foo/test/watch/settings/0', data=data,
                follow_redirects=True)
            self.assertIn(
                '</button>\n                      You are no longer'
                ' watching this project', output.data)

            output = self.app.post(
                '/fork/foo/test/watch/settings/1', data=data,
                follow_redirects=True)
            self.assertIn(
                '</button>\n                      You are now'
                ' watching issues and PRs on this project', output.data)

            output = self.app.post(
                '/fork/foo/test/watch/settings/2', data=data,
                follow_redirects=True)
            self.assertIn(
                '</button>\n                      You are now'
                ' watching commits on this project', output.data)

            output = self.app.post(
                '/fork/foo/test/watch/settings/3', data=data,
                follow_redirects=True)
            self.assertIn(
                ('</button>\n                      You are now'
                 ' watching issues, PRs, and commits on this project'),
                output.data)

            output = self.app.post(
                '/fork/foo/test/watch/settings/-1', data=data,
                follow_redirects=True)
            self.assertIn(
                '</button>\n                      Watch status reset',
                output.data)

    def test_delete_report(self):
        """ Test the  delete_report endpoint. """

        output = self.app.post('/test/delete/report')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # No report specified
            data = {
                'csrf_token':csrf_token
            }
            output = self.app.post(
                '/test/delete/report', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Unknown report: None',
                output.data)

            # Report specified not in the project's reports
            data = {
                'csrf_token':csrf_token,
                'report': 'foo'
            }
            output = self.app.post(
                '/test/delete/report', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Unknown report: foo',
                output.data)

            # Create a report
            project = pagure.get_authorized_project(self.session, project_name='test')
            self.assertEqual(project.reports, {})
            name = 'test report'
            url = '?foo=bar&baz=biz'
            pagure.lib.save_report(
                self.session,
                repo=project,
                name=name,
                url=url,
                username=None
            )
            self.session.commit()
            project = pagure.get_authorized_project(self.session, project_name='test')
            self.assertEqual(
                project.reports,
                {'test report': {'baz': 'biz', 'foo': 'bar'}}
            )

            # Missing CSRF
            data = {
                'report': 'test report'
            }
            output = self.app.post(
                '/test/delete/report', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - test - Pagure</title>',
                output.data)

            project = pagure.get_authorized_project(self.session, project_name='test')
            self.assertEqual(
                project.reports,
                {'test report': {'baz': 'biz', 'foo': 'bar'}}
            )

            # Delete the report
            data = {
                'csrf_token':csrf_token,
                'report': 'test report'
            }
            output = self.app.post(
                '/test/delete/report', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      List of reports updated',
                output.data)
            project = pagure.get_authorized_project(self.session, project_name='test')
            self.assertEqual(project.reports, {})

    def test_delete_report_ns_project(self):
        """ Test the  delete_report endpoint on a namespaced project. """

        output = self.app.post('/foo/test/delete/report')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                namespace='foo',
                name='test',
                description='foo project #2',
                hook_token='aaabbb',
            )
            self.session.add(item)
            self.session.commit()
            gitrepo = os.path.join(self.path, 'repos', 'foo', 'test.git')
            pygit2.init_repository(gitrepo, bare=True)

            # No report specified
            data = {
                'csrf_token':csrf_token
            }
            output = self.app.post(
                '/foo/test/delete/report', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Unknown report: None',
                output.data)

            # Report specified not in the project's reports
            data = {
                'csrf_token':csrf_token,
                'report': 'foo'
            }
            output = self.app.post(
                '/foo/test/delete/report', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      Unknown report: foo',
                output.data)

            # Create a report
            project = pagure.get_authorized_project(
                self.session, project_name='test', namespace='foo')
            self.assertEqual(project.reports, {})
            name = 'test report'
            url = '?foo=bar&baz=biz'
            pagure.lib.save_report(
                self.session,
                repo=project,
                name=name,
                url=url,
                username=None
            )
            self.session.commit()
            project = pagure.get_authorized_project(
                self.session, project_name='test', namespace='foo')
            self.assertEqual(
                project.reports,
                {'test report': {'baz': 'biz', 'foo': 'bar'}}
            )

            # Missing CSRF
            data = {
                'report': 'test report'
            }
            output = self.app.post(
                '/foo/test/delete/report', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Settings - foo/test - Pagure</title>',
                output.data)

            project = pagure.get_authorized_project(
                self.session, project_name='test', namespace='foo')
            self.assertEqual(
                project.reports,
                {'test report': {'baz': 'biz', 'foo': 'bar'}}
            )

            # Delete the report
            data = {
                'csrf_token':csrf_token,
                'report': 'test report'
            }
            output = self.app.post(
                '/foo/test/delete/report', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '</button>\n                      List of reports updated',
                output.data)

            project = pagure.get_authorized_project(
                self.session, project_name='test', namespace='foo')
            self.assertEqual(project.reports, {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
