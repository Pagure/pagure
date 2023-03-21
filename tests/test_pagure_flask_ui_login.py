# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Farhaan Bukhsh <farhaan.bukhsh@gmail.com>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import hashlib
import json
import unittest
import shutil
import sys
import tempfile
import os

import flask
import pygit2
import six
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests
from pagure.lib.repo import PagureRepo

import pagure.ui.login


class PagureFlaskLogintests(tests.SimplePagureTest):
    """Tests for flask app controller of pagure"""

    def setUp(self):
        """Create the application with PAGURE_AUTH being local."""
        super(PagureFlaskLogintests, self).setUp()

        app = pagure.flask_app.create_app(
            {"DB_URL": self.dbpath, "PAGURE_AUTH": "local"}
        )
        # Remove the log handlers for the tests
        app.logger.handlers = []

        self.app = app.test_client()

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    def test_front_page(self):
        """Test the front page."""
        # First access the front page
        output = self.app.get("/")
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Home - Pagure</title>", output.get_data(as_text=True)
        )

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_new_user(self):
        """Test the new_user endpoint."""

        # Check before:
        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(2, len(items))

        # First access the new user page
        output = self.app.get("/user/new")
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>New user - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            '<form action="/user/new" method="post">',
            output.get_data(as_text=True),
        )

        # Create the form to send there

        # This has all the data needed
        data = {
            "user": "foo",
            "fullname": "user foo",
            "email_address": "foo@bar.com",
            "password": "barpass",
            "confirm_password": "barpass",
        }

        # Submit this form  -  Doesn't work since there is no csrf token
        output = self.app.post("/user/new", data=data)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>New user - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            '<form action="/user/new" method="post">',
            output.get_data(as_text=True),
        )

        csrf_token = (
            output.get_data(as_text=True)
            .split('name="csrf_token" type="hidden" value="')[1]
            .split('">')[0]
        )

        # Submit the form with the csrf token
        data["csrf_token"] = csrf_token
        output = self.app.post("/user/new", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>New user - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            '<form action="/user/new" method="post">',
            output.get_data(as_text=True),
        )
        self.assertIn("Username already taken.", output.get_data(as_text=True))

        # Submit the form with another username
        data["user"] = "foouser"
        output = self.app.post("/user/new", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>New user - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            "Email address already taken.", output.get_data(as_text=True)
        )

        # Submit the form with proper data
        data["email_address"] = "foo@example.com"
        output = self.app.post("/user/new", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            "User created, please check your email to activate the account",
            output.get_data(as_text=True),
        )

        # Check after:
        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(3, len(items))

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    @patch.dict("pagure.config.config", {"ALLOW_USER_REGISTRATION": False})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_new_user_disabled(self):
        """Test the disabling of the new_user endpoint."""

        # Check before:
        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(2, len(items))

        # Attempt to access the new user page
        output = self.app.get("/user/new", follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            "User registration is disabled.", output.get_data(as_text=True)
        )

        # Check after:
        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(2, len(items))

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    @patch.dict("pagure.config.config", {"CHECK_SESSION_IP": False})
    def test_do_login(self):
        """Test the do_login endpoint."""

        output = self.app.get("/login/")
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            '<form action="/dologin" method="post">',
            output.get_data(as_text=True),
        )

        # This has all the data needed
        data = {"username": "foouser", "password": "barpass"}

        # Submit this form  -  Doesn't work since there is no csrf token
        output = self.app.post("/dologin", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            '<form action="/dologin" method="post">',
            output.get_data(as_text=True),
        )
        self.assertIn(
            "Insufficient information provided", output.get_data(as_text=True)
        )

        csrf_token = (
            output.get_data(as_text=True)
            .split('name="csrf_token" type="hidden" value="')[1]
            .split('">')[0]
        )

        # Submit the form with the csrf token  -  but invalid user
        data["csrf_token"] = csrf_token
        output = self.app.post("/dologin", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            '<form action="/dologin" method="post">',
            output.get_data(as_text=True),
        )
        self.assertIn(
            "Username or password invalid.", output.get_data(as_text=True)
        )

        # Create a local user
        self.test_new_user()

        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(3, len(items))

        # Submit the form with the csrf token  -  but user not confirmed
        data["csrf_token"] = csrf_token
        output = self.app.post("/dologin", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            '<form action="/dologin" method="post">',
            output.get_data(as_text=True),
        )
        self.assertIn(
            "Invalid user, did you confirm the creation with the url "
            "provided by email?",
            output.get_data(as_text=True),
        )

        # User in the DB, csrf provided  -  but wrong password submitted
        data["password"] = "password"
        output = self.app.post("/dologin", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            '<form action="/dologin" method="post">',
            output.get_data(as_text=True),
        )
        self.assertIn(
            "Username or password invalid.", output.get_data(as_text=True)
        )

        # When account is not confirmed i.e user_obj != None
        data["password"] = "barpass"
        output = self.app.post("/dologin", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            '<form action="/dologin" method="post">',
            output.get_data(as_text=True),
        )
        self.assertIn(
            "Invalid user, did you confirm the creation with the url "
            "provided by email?",
            output.get_data(as_text=True),
        )

        # Confirm the user so that we can log in
        self.session.commit()
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertNotEqual(item.token, None)

        # Remove the token
        item.token = None
        self.session.add(item)
        self.session.commit()

        # Check the user
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertEqual(item.token, None)

        # Login works but cannot save the session to the DB due to the missing
        # IP address in the flask request
        data["password"] = "barpass"
        output = self.app.post("/dologin", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Home - Pagure</title>", output_text)

        # I'm not sure if the change was in flask or werkzeug, but in older
        # version flask.request.remote_addr was returning None, while it
        # now returns 127.0.0.1 making our logic pass where it used to
        # partly fail
        if hasattr(flask, "__version__"):
            flask_v = tuple(int(el) for el in flask.__version__.split("."))
            if flask_v < (0, 12, 0):
                self.assertIn(
                    '<a class="btn btn-primary" '
                    'href="/login/?next=http://localhost/">',
                    output_text,
                )
                self.assertIn(
                    "Could not set the session in the db, please report "
                    "this error to an admin",
                    output_text,
                )
            else:
                self.assertIn(
                    '<a class="dropdown-item" '
                    'href="/logout/?next=http://localhost/dashboard/projects">',
                    output_text,
                )

        # Make the password invalid
        self.session.commit()
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertTrue(item.password.startswith("$2$"))

        # Remove the $2$
        item.password = item.password[3:]
        self.session.add(item)
        self.session.commit()

        # Check the password
        self.session.commit()
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertFalse(item.password.startswith("$2$"))

        # Try login again
        output = self.app.post(
            "/dologin",
            data=data,
            follow_redirects=True,
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            '<form action="/dologin" method="post">',
            output.get_data(as_text=True),
        )
        self.assertIn(
            "Username or password invalid.",
            output.get_data(as_text=True),
        )

        # Check the password is still not of a known version
        self.session.commit()
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertFalse(item.password.startswith("$1$"))
        self.assertFalse(item.password.startswith("$2$"))

        # V1 password
        password = "%s%s" % ("barpass", None)
        if isinstance(password, six.text_type):
            password = password.encode("utf-8")
        password = hashlib.sha512(password).hexdigest().encode("utf-8")
        item.token = None
        item.password = b"$1$" + password
        self.session.add(item)
        self.session.commit()

        # Check the password
        self.session.commit()
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertTrue(item.password.startswith(b"$1$"))

        # Log in with a v1 password
        output = self.app.post(
            "/dologin",
            data=data,
            follow_redirects=True,
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Home - Pagure</title>", output_text)
        self.assertIn("Welcome foouser", output_text)
        self.assertIn("Activity", output_text)

        # Check the password got upgraded to version 2
        self.session.commit()
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertTrue(item.password.startswith("$2$"))

        # We have set the REMOTE_ADDR in the request, so this works with all
        # versions of Flask.
        self.assertIn(
            '<a class="dropdown-item" '
            'href="/logout/?next=http://localhost/dashboard/projects">',
            output_text,
        )

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    @patch.dict("pagure.config.config", {"CHECK_SESSION_IP": False})
    def test_do_login_and_redirect(self):
        """Test the do_login endpoint with a non-default redirect."""
        # This has all the data needed
        data = {
            "username": "foouser",
            "password": "barpass",
            "csrf_token": self.get_csrf(url="/login/"),
            "next_url": "http://localhost/test/",
        }

        # Create a local user
        self.test_new_user()
        self.session.commit()

        # Confirm the user so that we can log in
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertNotEqual(item.token, None)

        # Remove the token
        item.token = None
        self.session.add(item)
        self.session.commit()

        # Check the user
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertEqual(item.token, None)

        # Add a test project to the user
        tests.create_projects(self.session, user_id=3)
        tests.create_projects_git(os.path.join(self.path, "repos"))
        output = self.app.get("/test")
        output_text = output.get_data(as_text=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn("<title>Overview - test - Pagure</title>", output_text)

        # Login and redirect to the test project
        output = self.app.post(
            "/dologin",
            data=data,
            follow_redirects=True,
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Overview - test - Pagure</title>", output_text)
        self.assertIn(
            '<a class="dropdown-item" '
            'href="/logout/?next=http://localhost/test/">',
            output_text,
        )
        self.assertIn(
            '<span class="d-none d-md-inline">Settings</span>', output_text
        )

        output = self.app.get("/login/?next=%2f%2f%09%2fgoogle.fr")
        self.assertEqual(output.status_code, 302)
        self.assertEqual(output.location, "http://localhost/google.fr")

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    @patch.dict("pagure.config.config", {"CHECK_SESSION_IP": False})
    def test_has_settings(self):
        """Test that user can see the Settings button when they are logged
        in."""
        # Create a local user
        self.test_new_user()
        self.session.commit()

        # Remove the token
        item = pagure.lib.query.search_user(self.session, username="foouser")
        item.token = None
        self.session.add(item)
        self.session.commit()

        # Check the user
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertEqual(item.token, None)

        # Add a test project to the user
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))
        output = self.app.get("/test")
        output_text = output.get_data(as_text=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn("<title>Overview - test - Pagure</title>", output_text)

        # Login and redirect to the test project
        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Overview - test - Pagure</title>", output_text
            )
            self.assertIn(
                '<span class="d-none d-md-inline">Settings</span>', output_text
            )

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_non_ascii_password(self):
        """Test login and user creation functionality when the password is
        non-ascii.
        """

        # Check before:
        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(2, len(items))

        # First access the new user page
        output = self.app.get("/user/new")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>New user - Pagure</title>", output_text)
        self.assertIn('<form action="/user/new" method="post">', output_text)

        # Create the form to send there
        # This has all the data needed

        data = {
            "user": "foo",
            "fullname": "user foo",
            "email_address": "foo@bar.com",
            "password": "ö",
            "confirm_password": "ö",
        }

        # Submit this form  -  Doesn't work since there is no csrf token
        output = self.app.post("/user/new", data=data)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>New user - Pagure</title>", output_text)
        self.assertIn('<form action="/user/new" method="post">', output_text)

        csrf_token = output_text.split(
            'name="csrf_token" type="hidden" value="'
        )[1].split('">')[0]

        # Submit the form with the csrf token
        data["csrf_token"] = csrf_token
        output = self.app.post("/user/new", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>New user - Pagure</title>", output_text)
        self.assertIn('<form action="/user/new" method="post">', output_text)
        self.assertIn("Username already taken.", output_text)

        # Submit the form with another username
        data["user"] = "foobar"
        output = self.app.post("/user/new", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>New user - Pagure</title>", output_text)
        self.assertIn("Email address already taken.", output_text)

        # Submit the form with proper data
        data["email_address"] = "foobar@foobar.com"
        output = self.app.post("/user/new", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Login - Pagure</title>", output_text)
        self.assertIn(
            "User created, please check your email to activate the account",
            output_text,
        )

        # Check after:
        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(3, len(items))

        # Checking for the /login page
        output = self.app.get("/login/")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Login - Pagure</title>", output_text)
        self.assertIn('<form action="/dologin" method="post">', output_text)

        # This has all the data needed
        data = {"username": "foob_bar", "password": "ö"}

        # Submit this form  -  Doesn't work since there is no csrf token
        output = self.app.post("/dologin", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Login - Pagure</title>", output_text)
        self.assertIn('<form action="/dologin" method="post">', output_text)
        self.assertIn("Insufficient information provided", output_text)

        # Submit the form with the csrf token  -  but invalid user
        data["csrf_token"] = csrf_token
        output = self.app.post("/dologin", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Login - Pagure</title>", output_text)
        self.assertIn('<form action="/dologin" method="post">', output_text)
        self.assertIn("Username or password invalid.", output_text)

        # Submit the form with the csrf token  -  but user not confirmed
        data["username"] = "foobar"
        output = self.app.post("/dologin", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Login - Pagure</title>", output_text)
        self.assertIn('<form action="/dologin" method="post">', output_text)
        self.assertIn(
            "Invalid user, did you confirm the creation with the url "
            "provided by email?",
            output_text,
        )

        # User in the DB, csrf provided  -  but wrong password submitted
        data["password"] = "öö"
        output = self.app.post("/dologin", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Login - Pagure</title>", output_text)
        self.assertIn('<form action="/dologin" method="post">', output_text)
        self.assertIn("Username or password invalid.", output_text)

        # When account is not confirmed i.e user_obj != None
        data["password"] = "ö"
        output = self.app.post("/dologin", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Login - Pagure</title>", output_text)
        self.assertIn('<form action="/dologin" method="post">', output_text)
        self.assertIn(
            "Invalid user, did you confirm the creation with the url "
            "provided by email?",
            output_text,
        )

        # Confirm the user so that we can log in
        item = pagure.lib.query.search_user(self.session, username="foobar")
        self.assertEqual(item.user, "foobar")
        self.assertNotEqual(item.token, None)

        # Remove the token
        item.token = None
        self.session.add(item)
        self.session.commit()

        # Login but cannot save the session to the DB due to the missing IP
        # address in the flask request
        data["password"] = "ö"
        output = self.app.post("/dologin", data=data, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>Home - Pagure</title>", output_text)

        # I'm not sure if the change was in flask or werkzeug, but in older
        # version flask.request.remote_addr was returning None, while it
        # now returns 127.0.0.1 making our logic pass where it used to
        # partly fail
        if hasattr(flask, "__version__"):
            flask_v = tuple(int(el) for el in flask.__version__.split("."))
            if flask_v <= (0, 12, 0):
                self.assertIn(
                    '<a class="btn btn-primary" '
                    'href="/login/?next=http://localhost/">',
                    output_text,
                )
                self.assertIn(
                    "Could not set the session in the db, please report "
                    "this error to an admin",
                    output_text,
                )
            else:
                self.assertIn(
                    '<a class="dropdown-item" '
                    'href="/logout/?next=http://localhost/dashboard/projects">',
                    output_text,
                )

        # Check the user
        item = pagure.lib.query.search_user(self.session, username="foobar")
        self.assertEqual(item.user, "foobar")
        self.assertEqual(item.token, None)

    def test_confirm_user(self):
        """Test the confirm_user endpoint."""

        output = self.app.get("/confirm/foo", follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Home - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            "No user associated with this token.",
            output.get_data(as_text=True),
        )

        # Create a local user
        self.test_new_user()

        items = pagure.lib.query.search_user(self.session)
        self.assertEqual(3, len(items))
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertTrue(item.password.startswith("$2$"))
        self.assertNotEqual(item.token, None)

        output = self.app.get(
            "/confirm/%s" % item.token, follow_redirects=True
        )
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            "Email confirmed, account activated", output.get_data(as_text=True)
        )

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_lost_password(self):
        """Test the lost_password endpoint."""

        output = self.app.get("/password/lost")
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Lost password - Pagure</title>",
            output.get_data(as_text=True),
        )
        self.assertIn(
            '<form action="/password/lost" method="post">',
            output.get_data(as_text=True),
        )

        # Prepare the data to send
        data = {"username": "foouser"}

        # Missing CSRF
        output = self.app.post("/password/lost", data=data)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Lost password - Pagure</title>",
            output.get_data(as_text=True),
        )
        self.assertIn(
            '<form action="/password/lost" method="post">',
            output.get_data(as_text=True),
        )

        csrf_token = (
            output.get_data(as_text=True)
            .split('name="csrf_token" type="hidden" value="')[1]
            .split('">')[0]
        )

        # With the CSRF  -  But invalid user
        data["csrf_token"] = csrf_token
        output = self.app.post(
            "/password/lost", data=data, follow_redirects=True
        )
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn("Username invalid.", output.get_data(as_text=True))

        # With the CSRF and a valid user
        data["username"] = "foo"
        output = self.app.post(
            "/password/lost", data=data, follow_redirects=True
        )
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            "Check your email to finish changing your password",
            output.get_data(as_text=True),
        )

        # With the CSRF and a valid user  -  but too quick after the last one
        data["username"] = "foo"
        output = self.app.post(
            "/password/lost", data=data, follow_redirects=True
        )
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            "An email was sent to you less than 3 minutes ago, did you "
            "check your spam folder? Otherwise, try again after some time.",
            output.get_data(as_text=True),
        )

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_reset_password(self):
        """Test the reset_password endpoint."""

        output = self.app.get("/password/reset/foo", follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            "No user associated with this token.",
            output.get_data(as_text=True),
        )
        self.assertIn(
            '<form action="/dologin" method="post">',
            output.get_data(as_text=True),
        )

        self.test_lost_password()
        self.test_new_user()

        # Check the password
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertNotEqual(item.token, None)
        self.assertTrue(item.password.startswith("$2$"))

        old_password = item.password
        token = item.token

        output = self.app.get(
            "/password/reset/%s" % token, follow_redirects=True
        )
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Change password - Pagure</title>",
            output.get_data(as_text=True),
        )
        self.assertIn(
            '<form action="/password/reset/', output.get_data(as_text=True)
        )

        data = {"password": "passwd", "confirm_password": "passwd"}

        # Missing CSRF
        output = self.app.post(
            "/password/reset/%s" % token, data=data, follow_redirects=True
        )
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Change password - Pagure</title>",
            output.get_data(as_text=True),
        )
        self.assertIn(
            '<form action="/password/reset/', output.get_data(as_text=True)
        )

        csrf_token = (
            output.get_data(as_text=True)
            .split('name="csrf_token" type="hidden" value="')[1]
            .split('">')[0]
        )

        # With CSRF
        data["csrf_token"] = csrf_token
        output = self.app.post(
            "/password/reset/%s" % token, data=data, follow_redirects=True
        )
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn("Password changed", output.get_data(as_text=True))

    @patch(
        "pagure.ui.login._check_session_cookie", MagicMock(return_value=True)
    )
    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    def test_change_password(self):
        """Test the change_password endpoint."""

        # Not logged in, redirects
        output = self.app.get("/password/change", follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Login - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertIn(
            '<form action="/dologin" method="post">',
            output.get_data(as_text=True),
        )

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get("/password/change")
            self.assertEqual(output.status_code, 404)
            self.assertIn("User not found", output.get_data(as_text=True))

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/password/change")
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<title>Change password - Pagure</title>",
                output.get_data(as_text=True),
            )
            self.assertIn(
                '<form action="/password/change" method="post">',
                output.get_data(as_text=True),
            )

            data = {
                "old_password": "bfoo",
                "password": "foo",
                "confirm_password": "foo",
            }

            # No CSRF token
            output = self.app.post("/password/change", data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<title>Change password - Pagure</title>",
                output.get_data(as_text=True),
            )
            self.assertIn(
                '<form action="/password/change" method="post">',
                output.get_data(as_text=True),
            )

            csrf_token = (
                output.get_data(as_text=True)
                .split('name="csrf_token" type="hidden" value="')[1]
                .split('">')[0]
            )

            # With CSRF  -  Invalid password format
            data["csrf_token"] = csrf_token
            output = self.app.post(
                "/password/change", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<title>Home - Pagure</title>", output.get_data(as_text=True)
            )
            self.assertIn(
                "Could not update your password, either user or password "
                "could not be checked",
                output.get_data(as_text=True),
            )

        self.test_new_user()

        # Remove token of foouser
        item = pagure.lib.query.search_user(self.session, username="foouser")
        self.assertEqual(item.user, "foouser")
        self.assertNotEqual(item.token, None)
        self.assertTrue(item.password.startswith("$2$"))
        item.token = None
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser(username="foouser")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/password/change")
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<title>Change password - Pagure</title>",
                output.get_data(as_text=True),
            )
            self.assertIn(
                '<form action="/password/change" method="post">',
                output.get_data(as_text=True),
            )

            data = {
                "old_password": "bfoo",
                "password": "foo",
                "confirm_password": "foo",
            }

            # No CSRF token
            output = self.app.post("/password/change", data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<title>Change password - Pagure</title>",
                output.get_data(as_text=True),
            )
            self.assertIn(
                '<form action="/password/change" method="post">',
                output.get_data(as_text=True),
            )

            csrf_token = (
                output.get_data(as_text=True)
                .split('name="csrf_token" type="hidden" value="')[1]
                .split('">')[0]
            )

            # With CSRF  -  Incorrect password
            data["csrf_token"] = csrf_token
            output = self.app.post(
                "/password/change", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<title>Home - Pagure</title>", output.get_data(as_text=True)
            )
            self.assertIn(
                "Could not update your password, either user or password "
                "could not be checked",
                output.get_data(as_text=True),
            )

            # With CSRF  -  Correct password
            data["old_password"] = "barpass"
            output = self.app.post(
                "/password/change", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<title>Home - Pagure</title>", output.get_data(as_text=True)
            )
            self.assertIn("Password changed", output.get_data(as_text=True))

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    def test_logout(self):
        """Test the auth_logout endpoint for local login."""

        output = self.app.get("/logout/", follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            "<title>Home - Pagure</title>", output.get_data(as_text=True)
        )
        self.assertNotIn(
            "You have been logged out", output.get_data(as_text=True)
        )
        self.assertIn(
            '<a class="btn btn-primary" '
            'href="/login/?next=http://localhost/">',
            output.get_data(as_text=True),
        )

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/logout/", follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<title>Home - Pagure</title>", output.get_data(as_text=True)
            )
            self.assertIn(
                "You have been logged out", output.get_data(as_text=True)
            )
            # Due to the way the tests are running we do not actually
            # log out
            self.assertIn(
                '<a class="dropdown-item" href="/logout/?next='
                'http://localhost/dashboard/projects">Log Out</a>',
                output.get_data(as_text=True),
            )

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/logout/?next=%2f%2f%09%2fgoogle.fr")
            self.assertEqual(output.status_code, 302)
            self.assertTrue(
                output.headers["location"] in ("http://localhost/google.fr",)
            )

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    def test_settings_admin_session_timedout(self):
        """Test the admin_session_timedout with settings endpoint."""
        lifetime = pagure.config.config.get(
            "ADMIN_SESSION_LIFETIME", datetime.timedelta(minutes=15)
        )
        td1 = datetime.timedelta(minutes=1)
        # session already expired
        user = tests.FakeUser(username="foo")
        user.login_time = datetime.datetime.utcnow() - lifetime - td1
        with tests.user_set(self.app.application, user):
            # not following the redirect because user_set contextmanager
            # will run again for the login page and set back the user
            # which results in a loop, since admin_session_timedout will
            # redirect again for the login page
            output = self.app.get("/settings/")
            self.assertEqual(output.status_code, 302)
            self.assertTrue(
                output.location
                in (
                    "http://localhost/login/",
                    "/login/?next=http%3A%2F%2Flocalhost%2Fsettings%2F",
                    "http://localhost/login/?next=http%3A%2F%2Flocalhost%2Fsettings%2F",
                )
            )
        # session did not expire
        user.login_time = datetime.datetime.utcnow() - lifetime + td1
        with tests.user_set(self.app.application, user):
            output = self.app.get("/settings/")
            self.assertEqual(output.status_code, 200)

    @patch("flask.flash")
    def test_admin_session_timedout(self, flash):
        """Test the call to admin_session_timedout."""
        lifetime = pagure.config.config.get(
            "ADMIN_SESSION_LIFETIME", datetime.timedelta(minutes=15)
        )
        td1 = datetime.timedelta(minutes=1)
        # session already expired
        user = tests.FakeUser(username="foo")
        user.login_time = datetime.datetime.utcnow() - lifetime - td1
        with self.app.application.app_context() as ctx:
            ctx.g.session = self.session
            ctx.g.fas_user = user
            self.assertTrue(pagure.flask_app.admin_session_timedout())

        # session did not expire
        user.login_time = datetime.datetime.utcnow() - lifetime + td1
        with self.app.application.app_context() as ctx:
            ctx.g.session = self.session
            ctx.g.fas_user = user
            self.assertFalse(pagure.flask_app.admin_session_timedout())

    @patch.dict("pagure.config.config", {"PAGURE_AUTH": "local"})
    def test_force_logout(self):
        """Test forcing logout."""
        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user, keep_get_user=True):
            # Test that accessing settings works
            output = self.app.get("/settings")
            self.assertEqual(output.status_code, 200)

            # Now logout everywhere
            data = {"csrf_token": self.get_csrf()}
            output = self.app.post("/settings/forcelogout/", data=data)
            self.assertEqual(output.status_code, 302)
            self.assertTrue(
                output.headers["Location"]
                in ("http://localhost/settings", "/settings")
            )

            # We should now get redirected to index, because our session became
            # invalid
            output = self.app.get("/settings")
            self.assertTrue(
                output.headers["Location"] in ("http://localhost/", "/")
            )

            # After changing the login_time to now, the session should again be
            # valid
            user.login_time = datetime.datetime.utcnow()
            output = self.app.get("/")
            self.assertEqual(output.status_code, 302)


if __name__ == "__main__":
    unittest.main(verbosity=2)
