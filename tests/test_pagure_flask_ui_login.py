# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

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

import pagure.ui.login


class PagureFlaskLogintests(tests.Modeltests):
    """ Tests for flask app controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskLogintests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.APP.config['EMAIL_SEND'] = True
        pagure.APP.config['PAGURE_AUTH'] = 'local'
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.login.SESSION = self.session

        self.app = pagure.APP.test_client()

    def test_new_user(self):
        """ Test the new_user endpoint. """

        # Check before:
        items = pagure.lib.search_user(self.session)
        self.assertEqual(2, len(items))

        # First access the new user page
        output = self.app.get('/user/new')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>New user - Pagure</title>', output.data)
        self.assertIn(
            '<form action="/user/new" method="post">', output.data)

        # Create the form to send there

        # This has all the data needed
        data = {
            'user': 'foo',
            'fullname': 'user foo',
            'email_address': 'foo@bar.com',
            'password': 'barpass',
            'confirm_password': 'barpass',
        }

        # Submit this form  -  Doesn't work since there is no csrf token
        output = self.app.post('/user/new', data=data)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>New user - Pagure</title>', output.data)
        self.assertIn(
            '<form action="/user/new" method="post">', output.data)

        csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

        # Submit the form with the csrf token
        data['csrf_token'] = csrf_token
        output = self.app.post('/user/new', data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>New user - Pagure</title>', output.data)
        self.assertIn(
            '<form action="/user/new" method="post">', output.data)
        self.assertIn('Username already taken.', output.data)

        # Submit the form with another username
        data['user'] = 'foouser'
        output = self.app.post('/user/new', data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>New user - Pagure</title>', output.data)
        self.assertIn('Email address already taken.', output.data)

        # Submit the form with proper data
        data['email_address'] = 'foo@example.com'
        output = self.app.post('/user/new', data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Login - Pagure</title>', output.data)
        self.assertIn(
            'User created, please check your email to activate the account',
            output.data)

        # Check after:
        items = pagure.lib.search_user(self.session)
        self.assertEqual(3, len(items))

    def test_do_login(self):
        """ Test the do_login endpoint. """

        output = self.app.get('/login/')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Login - Pagure</title>', output.data)
        self.assertIn(
            '<form action="/dologin" method="post">', output.data)

        # This has all the data needed
        data = {
            'username': 'foouser',
            'password': 'barpass',
        }

        # Submit this form  -  Doesn't work since there is no csrf token
        output = self.app.post('/dologin', data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Login - Pagure</title>', output.data)
        self.assertIn(
            '<form action="/dologin" method="post">', output.data)
        self.assertIn('Insufficient information provided', output.data)

        csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

        # Submit the form with the csrf token  -  but invalid user
        data['csrf_token'] = csrf_token
        output = self.app.post('/dologin', data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Login - Pagure</title>', output.data)
        self.assertIn(
            '<form action="/dologin" method="post">', output.data)
        self.assertIn('Username or password invalid.', output.data)

        # Create a local user
        self.test_new_user()

        items = pagure.lib.search_user(self.session)
        self.assertEqual(3, len(items))

        # Submit the form with the csrf token  -  but user not confirmed
        data['csrf_token'] = csrf_token
        output = self.app.post('/dologin', data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Login - Pagure</title>', output.data)
        self.assertIn(
            '<form action="/dologin" method="post">', output.data)
        self.assertIn(
            'Invalid user, did you confirm the creation with the url '
            'provided by email?', output.data)

        # User in the DB, csrf provided  -  but wrong password submitted
        data['password'] = 'password'
        output = self.app.post('/dologin', data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Login - Pagure</title>', output.data)
        self.assertIn(
            '<form action="/dologin" method="post">', output.data)
        self.assertIn('Username or password invalid.', output.data)

        # When account is not confirmed i.e user_obj != None
        data['password'] = 'barpass'
        output = self.app.post('/dologin', data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Login - Pagure</title>', output.data)
        self.assertIn(
            '<form action="/dologin" method="post">', output.data)
        self.assertIn(
            'Invalid user, did you confirm the creation with the url '
            'provided by email?', output.data)

        # Wrong password submitted
        data['password'] = 'password'
        output = self.app.post('/dologin', data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Login - Pagure</title>', output.data)
        self.assertIn(
            '<form action="/dologin" method="post">', output.data)
        self.assertIn('Username or password invalid.', output.data)

        # When account is not confirmed i.e user_obj != None
        data['password'] = 'barpass'
        output = self.app.post('/dologin', data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Login - Pagure</title>', output.data)
        self.assertIn(
            '<form action="/dologin" method="post">', output.data)
        self.assertIn(
            'Invalid user, did you confirm the creation with the url '
            'provided by email?', output.data)

        # Confirm the user so that we can log in
        item = pagure.lib.search_user(self.session, username='foouser')
        self.assertEqual(item.user, 'foouser')
        self.assertNotEqual(item.token, None)

        # Remove the token
        item.token = None
        self.session.add(item)
        self.session.commit

        # Check the user
        item = pagure.lib.search_user(self.session, username='foouser')
        self.assertEqual(item.user, 'foouser')
        self.assertEqual(item.token, None)

        # Login but cannot save the session to the DB due to the missing IP
        # address in the flask request
        data['password'] = 'barpass'
        output = self.app.post('/dologin', data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Home - Pagure</title>', output.data)
        self.assertIn(
            '<a class="nav-link" href="/login/?next=http://localhost/">',
            output.data)
        self.assertIn(
            'Could not set the session in the db, please report this error '
            'to an admin', output.data)

        # Make the password invalid
        item = pagure.lib.search_user(self.session, username='foouser')
        self.assertEqual(item.user, 'foouser')
        self.assertTrue(item.password.startswith('$2$'))

        # Remove the $2$
        item.password = item.password[3:]
        self.session.add(item)
        self.session.commit

        # Check the password
        item = pagure.lib.search_user(self.session, username='foouser')
        self.assertEqual(item.user, 'foouser')
        self.assertFalse(item.password.startswith('$2$'))

        # Try login again
        output = self.app.post('/dologin', data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Login - Pagure</title>', output.data)
        self.assertIn(
            '<form action="/dologin" method="post">', output.data)
        self.assertIn('Username or password of invalid format.', output.data)



if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagureFlaskLogintests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
