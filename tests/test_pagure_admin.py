# -*- coding: utf-8 -*-

"""
 (c) 2017-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime  # noqa
import os  # noqa
import platform  # noqa
import shutil  # noqa
import subprocess  # noqa
import sys  # noqa
import unittest  # noqa

import pygit2
import munch  # noqa
from mock import patch, MagicMock  # noqa
from six import StringIO  # noqa

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.config  # noqa
import pagure.exceptions  # noqa: E402
import pagure.cli.admin  # noqa
import pagure.lib.model  # noqa
import tests  # noqa


class PagureAdminAdminTokenEmptytests(tests.Modeltests):
    """ Tests for pagure-admin admin-token when there is nothing in the DB
    """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminAdminTokenEmptytests, self).setUp()
        pagure.cli.admin.session = self.session

    def test_do_create_admin_token_no_user(self):
        """ Test the do_create_admin_token function of pagure-admin without
        user.
        """
        args = munch.Munch({"user": "pingou"})
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_create_admin_token(args)
        self.assertEqual(cm.exception.args[0], 'No user "pingou" found')

    def test_do_list_admin_token_empty(self):
        """ Test the do_list_admin_token function of pagure-admin when there
        are not tokens in the db.
        """
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertEqual(output, "No admin tokens found\n")


class PagureAdminAdminRefreshGitolitetests(tests.Modeltests):
    """ Tests for pagure-admin refresh-gitolite """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminAdminRefreshGitolitetests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user="pingou",
            fullname="PY C",
            password="foo",
            default_email="bar@pingou.com",
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(user_id=1, email="bar@pingou.com")
        self.session.add(item)
        self.session.commit()

        # Create a couple of projects
        tests.create_projects(self.session)

        # Add a group
        msg = pagure.lib.query.add_group(
            self.session,
            group_name="foo",
            display_name="foo group",
            description=None,
            group_type="bar",
            user="pingou",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, "User `pingou` added to the group `foo`.")

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

    @patch("pagure.cli.admin._ask_confirmation")
    @patch("pagure.lib.git_auth.get_git_auth_helper")
    def test_do_refresh_gitolite_no_args(self, get_helper, conf):
        """ Test the do_generate_acl function with no special args. """
        conf.return_value = True
        helper = MagicMock()
        get_helper.return_value = helper

        args = munch.Munch(
            {"group": None, "project": None, "all_": False, "user": None}
        )
        pagure.cli.admin.do_generate_acl(args)

        get_helper.assert_called_with()
        args = helper.generate_acls.call_args
        self.assertIsNone(args[1].get("group"))
        self.assertIsNone(args[1].get("project"))

    @patch("pagure.cli.admin._ask_confirmation")
    @patch("pagure.lib.git_auth.get_git_auth_helper")
    def test_do_refresh_gitolite_all_project(self, get_helper, conf):
        """ Test the do_generate_acl function for all projects. """
        conf.return_value = True
        helper = MagicMock()
        get_helper.return_value = helper

        args = munch.Munch(
            {"group": None, "project": None, "all_": True, "user": None}
        )
        pagure.cli.admin.do_generate_acl(args)

        get_helper.assert_called_with()
        args = helper.generate_acls.call_args
        self.assertIsNone(args[1].get("group"))
        self.assertEqual(args[1].get("project"), -1)

    @patch("pagure.cli.admin._ask_confirmation")
    @patch("pagure.lib.git_auth.get_git_auth_helper")
    def test_do_refresh_gitolite_one_project(self, get_helper, conf):
        """ Test the do_generate_acl function for a certain project. """
        conf.return_value = True
        helper = MagicMock()
        get_helper.return_value = helper

        args = munch.Munch(
            {"group": None, "project": "test", "all_": False, "user": None}
        )
        pagure.cli.admin.do_generate_acl(args)

        get_helper.assert_called_with()
        args = helper.generate_acls.call_args
        self.assertIsNone(args[1].get("group"))
        self.assertEqual(args[1].get("project").fullname, "test")

    @patch("pagure.cli.admin._ask_confirmation")
    @patch("pagure.lib.git_auth.get_git_auth_helper")
    def test_do_refresh_gitolite_one_project_and_all(self, get_helper, conf):
        """ Test the do_generate_acl function for a certain project and all.
        """
        conf.return_value = True
        helper = MagicMock()
        get_helper.return_value = helper

        args = munch.Munch(
            {"group": None, "project": "test", "all_": True, "user": None}
        )
        pagure.cli.admin.do_generate_acl(args)

        get_helper.assert_called_with()
        args = helper.generate_acls.call_args
        self.assertIsNone(args[1].get("group"))
        self.assertEqual(args[1].get("project"), -1)

    @patch("pagure.cli.admin._ask_confirmation")
    @patch("pagure.lib.git_auth.get_git_auth_helper")
    def test_do_refresh_gitolite_one_group(self, get_helper, conf):
        """ Test the do_generate_acl function for a certain group. """
        conf.return_value = True
        helper = MagicMock()
        get_helper.return_value = helper

        args = munch.Munch(
            {"group": "foo", "project": None, "all_": False, "user": None}
        )
        pagure.cli.admin.do_generate_acl(args)

        get_helper.assert_called_with()
        args = helper.generate_acls.call_args
        self.assertEqual(args[1].get("group").group_name, "foo")
        self.assertIsNone(args[1].get("project"))


class PagureAdminAdminTokentests(tests.Modeltests):
    """ Tests for pagure-admin admin-token """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminAdminTokentests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user="pingou",
            fullname="PY C",
            password="foo",
            default_email="bar@pingou.com",
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(user_id=1, email="bar@pingou.com")
        self.session.add(item)
        self.session.commit()

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

    @patch("pagure.cli.admin._get_input")
    @patch("pagure.cli.admin._ask_confirmation")
    def test_do_create_admin_token(self, conf, rinp):
        """ Test the do_create_admin_token function of pagure-admin. """
        conf.return_value = True
        rinp.return_value = "1,2,3"

        args = munch.Munch({"user": "pingou"})
        pagure.cli.admin.do_create_admin_token(args)

        # Check the outcome
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

    @patch("pagure.cli.admin._get_input")
    @patch("pagure.cli.admin._ask_confirmation")
    def test_do_list_admin_token(self, conf, rinp):
        """ Test the do_list_admin_token function of pagure-admin. """
        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = "1,2,3"

        args = munch.Munch({"user": "pingou"})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve all tokens
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

        # Retrieve pfrields's tokens
        list_args = munch.Munch(
            {
                "user": "pfrields",
                "token": None,
                "active": False,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertEqual(output, "No admin tokens found\n")

    def test_do_list_admin_token_non_admin_acls(self):
        """ Test the do_list_admin_token function of pagure-admin for a token
        without any admin ACL. """
        pagure.lib.query.add_token_to_user(
            self.session,
            project=None,
            acls=["issue_assign", "pull_request_subscribe"],
            username="pingou",
        )

        # Retrieve all admin tokens
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertEqual(output, "No admin tokens found\n")

        # Retrieve all tokens
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": True,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

    @patch("pagure.cli.admin._get_input")
    @patch("pagure.cli.admin._ask_confirmation")
    def test_do_info_admin_token(self, conf, rinp):
        """ Test the do_info_admin_token function of pagure-admin. """
        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = "2,4,5"

        args = munch.Munch({"user": "pingou"})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve the token
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

        token = output.split(" ", 1)[0]

        args = munch.Munch({"token": token})
        with tests.capture_output() as output:
            pagure.cli.admin.do_info_admin_token(args)
        output = output.getvalue()
        self.assertIn(" -- pingou -- ", output.split("\n", 1)[0])
        self.assertEqual(
            output.split("\n", 1)[1],
            """ACLs:
  - issue_create
  - pull_request_comment
  - pull_request_flag
""",
        )

    def test_do_info_admin_token_non_admin_acl(self):
        """ Test the do_info_admin_token function of pagure-admin for a
        token not having any admin ACL. """
        pagure.lib.query.add_token_to_user(
            self.session,
            project=None,
            acls=["issue_assign", "pull_request_subscribe"],
            username="pingou",
        )

        # Retrieve the token
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": True,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

        token = output.split(" ", 1)[0]

        args = munch.Munch({"token": token})
        with tests.capture_output() as output:
            pagure.cli.admin.do_info_admin_token(args)
        output = output.getvalue()
        self.assertIn(" -- pingou -- ", output.split("\n", 1)[0])
        self.assertEqual(
            output.split("\n", 1)[1],
            """ACLs:
  - issue_assign
  - pull_request_subscribe
""",
        )

    @patch("pagure.cli.admin._get_input")
    @patch("pagure.cli.admin._ask_confirmation")
    def test_do_expire_admin_token(self, conf, rinp):
        """ Test the do_expire_admin_token function of pagure-admin. """
        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = "1,2,3"

        args = munch.Munch({"user": "pingou"})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve the token
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

        token = output.split(" ", 1)[0]

        # Before
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": True,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, "No admin tokens found\n")
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

        # Expire the token
        args = munch.Munch({"token": token, "all": False})
        pagure.cli.admin.do_expire_admin_token(args)

        # After
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": True,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertEqual(output, "No admin tokens found\n")

    @patch("pagure.cli.admin._get_input")
    @patch("pagure.cli.admin._ask_confirmation")
    def test_do_expire_admin_token_non_admin_acls(self, conf, rinp):
        """ Test the do_expire_admin_token function of pagure-admin for a token
        without any admin ACL. """

        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = "1,2,3"

        pagure.lib.query.add_token_to_user(
            self.session,
            project=None,
            acls=["issue_assign", "pull_request_subscribe"],
            username="pingou",
        )

        # Retrieve all tokens to get the one of interest
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": True,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

        token = output.split(" ", 1)[0]

        # Expire the token
        args = munch.Munch({"token": token, "all": True})
        pagure.cli.admin.do_expire_admin_token(args)

        # After
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": True,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertEqual(output, "No admin tokens found\n")

    @patch("pagure.cli.admin._get_input")
    @patch("pagure.cli.admin._ask_confirmation")
    def test_do_update_admin_token_invalid_date(self, conf, rinp):
        """ Test the do_update_admin_token function of pagure-admin with
        an invalid date. """

        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = "1,2,3"

        args = munch.Munch({"user": "pingou"})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve the token
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

        token = output.split(" ", 1)[0]
        current_expiration = output.split(" ", 1)[1]

        # Set the expiration date to the token
        args = munch.Munch({"token": token, "date": "aa-bb-cc", "all": False})
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.cli.admin.do_update_admin_token,
            args,
        )

    @patch("pagure.cli.admin._get_input")
    @patch("pagure.cli.admin._ask_confirmation")
    def test_do_update_admin_token_invalid_date2(self, conf, rinp):
        """ Test the do_update_admin_token function of pagure-admin with
        an invalid date. """

        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = "1,2,3"

        args = munch.Munch({"user": "pingou"})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve the token
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

        token = output.split(" ", 1)[0]
        current_expiration = output.split(" ", 1)[1]

        # Set the expiration date to the token
        args = munch.Munch(
            {"token": token, "date": "2017-18-01", "all": False}
        )
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.cli.admin.do_update_admin_token,
            args,
        )

    @patch("pagure.cli.admin._get_input")
    @patch("pagure.cli.admin._ask_confirmation")
    def test_do_update_admin_token_invalid_date3(self, conf, rinp):
        """ Test the do_update_admin_token function of pagure-admin with
        an invalid date (is today). """

        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = "1,2,3"

        args = munch.Munch({"user": "pingou"})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve the token
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

        token = output.split(" ", 1)[0]
        current_expiration = output.split(" ", 1)[1]

        # Set the expiration date to the token
        args = munch.Munch(
            {
                "token": token,
                "date": datetime.datetime.utcnow().date(),
                "all": False,
            }
        )
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.cli.admin.do_update_admin_token,
            args,
        )

    @patch("pagure.cli.admin._get_input")
    @patch("pagure.cli.admin._ask_confirmation")
    def test_do_update_admin_token(self, conf, rinp):
        """ Test the do_update_admin_token function of pagure-admin. """

        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = "1,2,3"

        args = munch.Munch({"user": "pingou"})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve the token
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

        token = output.split(" ", 1)[0]
        current_expiration = output.strip().split(" -- ", 2)[-1]

        # Before
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": True,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, "No admin tokens found\n")
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

        deadline = datetime.datetime.utcnow().date() + datetime.timedelta(
            days=3
        )

        # Set the expiration date to the token
        args = munch.Munch(
            {
                "token": token,
                "date": deadline.strftime("%Y-%m-%d"),
                "all": False,
            }
        )
        pagure.cli.admin.do_update_admin_token(args)

        # After
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": True,
                "expired": False,
                "all": False,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertEqual(output.split(" ", 1)[0], token)
        self.assertNotEqual(
            output.strip().split(" -- ", 2)[-1], current_expiration
        )

    @patch("pagure.cli.admin._get_input")
    @patch("pagure.cli.admin._ask_confirmation")
    def test_do_update_admin_token_non_admin_acls(self, conf, rinp):
        """ Test the do_update_admin_token function of pagure-admin for a token
        without any admin ACL. """

        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = "1,2,3"

        pagure.lib.query.add_token_to_user(
            self.session,
            project=None,
            acls=["issue_assign", "pull_request_subscribe"],
            username="pingou",
        )

        # Retrieve all tokens to get the one of interest
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": False,
                "expired": False,
                "all": True,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split("\n")), 2)
        self.assertIn(" -- pingou -- ", output)

        token = output.split(" ", 1)[0]
        current_expiration = output.strip().split(" -- ", 2)[-1]
        deadline = datetime.datetime.utcnow().date() + datetime.timedelta(
            days=3
        )

        # Set the expiration date to the token
        args = munch.Munch(
            {
                "token": token,
                "date": deadline.strftime("%Y-%m-%d"),
                "all": True,
            }
        )
        pagure.cli.admin.do_update_admin_token(args)

        # After
        list_args = munch.Munch(
            {
                "user": None,
                "token": None,
                "active": True,
                "expired": False,
                "all": True,
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertEqual(output.split(" ", 1)[0], token)
        self.assertNotEqual(
            output.strip().split(" -- ", 2)[-1], current_expiration
        )


class PagureAdminGetWatchTests(tests.Modeltests):
    """ Tests for pagure-admin get-watch """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminGetWatchTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user="pingou",
            fullname="PY C",
            password="foo",
            default_email="bar@pingou.com",
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(user_id=1, email="bar@pingou.com")
        self.session.add(item)

        # Create the user foo
        item = pagure.lib.model.User(
            user="foo",
            fullname="foo B.",
            password="foob",
            default_email="foo@pingou.com",
        )
        self.session.add(item)

        # Create two projects for the user pingou
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test",
            description="namespaced test project",
            hook_token="aaabbbeee",
            namespace="somenamespace",
        )
        self.session.add(item)

        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test",
            description="Test project",
            hook_token="aaabbbccc",
            namespace=None,
        )
        self.session.add(item)

        self.session.commit()

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

    def test_get_watch_get_project_unknown_project(self):
        """ Test the get-watch function of pagure-admin with an unknown
        project.
        """
        args = munch.Munch({"project": "foobar", "user": "pingou"})
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_get_watch_status(args)
        self.assertEqual(
            cm.exception.args[0], "No project found with: project=foobar"
        )

    def test_get_watch_get_project_invalid_project(self):
        """ Test the get-watch function of pagure-admin with an invalid
        project.
        """
        args = munch.Munch({"project": "fo/o/bar", "user": "pingou"})
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_get_watch_status(args)
        self.assertEqual(
            cm.exception.args[0],
            'Invalid project name, has more than one "/": fo/o/bar',
        )

    def test_get_watch_get_project_invalid_user(self):
        """ Test the get-watch function of pagure-admin on a invalid user.
        """
        args = munch.Munch({"project": "test", "user": "beebop"})
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_get_watch_status(args)
        self.assertEqual(cm.exception.args[0], 'No user "beebop" found')

    def test_get_watch_get_project(self):
        """ Test the get-watch function of pagure-admin on a regular project.
        """
        args = munch.Munch({"project": "test", "user": "pingou"})
        with tests.capture_output() as output:
            pagure.cli.admin.do_get_watch_status(args)
        output = output.getvalue()
        self.assertEqual(
            "On test user: pingou is watching the following items: "
            "issues, pull-requests\n",
            output,
        )

    def test_get_watch_get_project_not_watching(self):
        """ Test the get-watch function of pagure-admin on a regular project.
        """

        args = munch.Munch({"project": "test", "user": "foo"})
        with tests.capture_output() as output:
            pagure.cli.admin.do_get_watch_status(args)
        output = output.getvalue()
        self.assertEqual(
            "On test user: foo is watching the following items: None\n", output
        )

    def test_get_watch_get_project_namespaced(self):
        """ Test the get-watch function of pagure-admin on a namespaced project.
        """

        args = munch.Munch({"project": "somenamespace/test", "user": "pingou"})
        with tests.capture_output() as output:
            pagure.cli.admin.do_get_watch_status(args)
        output = output.getvalue()
        self.assertEqual(
            "On somenamespace/test user: pingou is watching the following "
            "items: issues, pull-requests\n",
            output,
        )

    def test_get_watch_get_project_namespaced_not_watching(self):
        """ Test the get-watch function of pagure-admin on a namespaced project.
        """

        args = munch.Munch({"project": "somenamespace/test", "user": "foo"})
        with tests.capture_output() as output:
            pagure.cli.admin.do_get_watch_status(args)
        output = output.getvalue()
        with tests.capture_output() as _discarded:
            pagure.cli.admin.do_get_watch_status(args)
        self.assertEqual(
            "On somenamespace/test user: foo is watching the following "
            "items: None\n",
            output,
        )


class PagureAdminUpdateWatchTests(tests.Modeltests):
    """ Tests for pagure-admin update-watch """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminUpdateWatchTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user="pingou",
            fullname="PY C",
            password="foo",
            default_email="bar@pingou.com",
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(user_id=1, email="bar@pingou.com")
        self.session.add(item)

        # Create the user foo
        item = pagure.lib.model.User(
            user="foo",
            fullname="foo B.",
            password="foob",
            default_email="foo@pingou.com",
        )
        self.session.add(item)

        # Create two projects for the user pingou
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test",
            description="namespaced test project",
            hook_token="aaabbbeee",
            namespace="somenamespace",
        )
        self.session.add(item)

        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test",
            description="Test project",
            hook_token="aaabbbccc",
            namespace=None,
        )
        self.session.add(item)

        self.session.commit()

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

    def test_get_watch_update_project_unknown_project(self):
        """ Test the update-watch function of pagure-admin on an unknown
        project.
        """
        args = munch.Munch(
            {"project": "foob", "user": "pingou", "status": "1"}
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_update_watch_status(args)
        self.assertEqual(
            cm.exception.args[0], "No project found with: project=foob"
        )

    def test_get_watch_update_project_invalid_project(self):
        """ Test the update-watch function of pagure-admin on an invalid
        project.
        """
        args = munch.Munch(
            {"project": "fo/o/b", "user": "pingou", "status": "1"}
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_update_watch_status(args)
        self.assertEqual(
            cm.exception.args[0],
            'Invalid project name, has more than one "/": fo/o/b',
        )

    def test_get_watch_update_project_invalid_user(self):
        """ Test the update-watch function of pagure-admin on an invalid user.
        """
        args = munch.Munch({"project": "test", "user": "foob", "status": "1"})
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_update_watch_status(args)
        self.assertEqual(cm.exception.args[0], 'No user "foob" found')

    def test_get_watch_update_project_invalid_status(self):
        """ Test the update-watch function of pagure-admin with an invalid
        status.
        """
        args = munch.Munch(
            {"project": "test", "user": "pingou", "status": "10"}
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_update_watch_status(args)
        self.assertEqual(
            cm.exception.args[0],
            "Invalid status provided: 10 not in -1, 0, 1, 2, 3",
        )

    def test_get_watch_update_project_no_effect(self):
        """ Test the update-watch function of pagure-admin with a regular
        project - nothing changed.
        """

        args = munch.Munch({"project": "test", "user": "pingou"})
        with tests.capture_output() as output:
            pagure.cli.admin.do_get_watch_status(args)
        output = output.getvalue()
        self.assertEqual(
            "On test user: pingou is watching the following items: "
            "issues, pull-requests\n",
            output,
        )

        args = munch.Munch(
            {"project": "test", "user": "pingou", "status": "1"}
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_update_watch_status(args)
        output = output.getvalue()
        self.assertEqual(
            "Updating watch status of pingou to 1 (watch issues and PRs) "
            "on test\n",
            output,
        )

        args = munch.Munch({"project": "test", "user": "pingou"})
        with tests.capture_output() as output:
            pagure.cli.admin.do_get_watch_status(args)
        output = output.getvalue()
        self.assertEqual(
            "On test user: pingou is watching the following items: "
            "issues, pull-requests\n",
            output,
        )


class PagureAdminReadOnlyTests(tests.Modeltests):
    """ Tests for pagure-admin read-only """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminReadOnlyTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user="pingou",
            fullname="PY C",
            password="foo",
            default_email="bar@pingou.com",
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(user_id=1, email="bar@pingou.com")
        self.session.add(item)

        # Create two projects for the user pingou
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test",
            description="namespaced test project",
            hook_token="aaabbbeee",
            namespace="somenamespace",
        )
        self.session.add(item)

        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test",
            description="Test project",
            hook_token="aaabbbccc",
            namespace=None,
        )
        self.session.add(item)

        self.session.commit()

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

    def test_read_only_unknown_project(self):
        """ Test the read-only function of pagure-admin on an unknown
        project.
        """

        args = munch.Munch({"project": "foob", "user": None, "ro": None})
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_read_only(args)
        self.assertEqual(
            cm.exception.args[0], "No project found with: project=foob"
        )

    def test_read_only_invalid_project(self):
        """ Test the read-only function of pagure-admin on an invalid
        project.
        """

        args = munch.Munch({"project": "fo/o/b", "user": None, "ro": None})
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_read_only(args)
        self.assertEqual(
            cm.exception.args[0],
            'Invalid project name, has more than one "/": fo/o/b',
        )

    def test_read_only(self):
        """ Test the read-only function of pagure-admin to get status of
        a non-namespaced project.
        """

        args = munch.Munch({"project": "test", "user": None, "ro": None})
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            "The current read-only flag of the project test is set to True\n",
            output,
        )

    def test_read_only_namespace(self):
        """ Test the read-only function of pagure-admin to get status of
        a namespaced project.
        """

        args = munch.Munch(
            {"project": "somenamespace/test", "user": None, "ro": None}
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            "The current read-only flag of the project somenamespace/test "
            "is set to True\n",
            output,
        )

    def test_read_only_namespace_changed(self):
        """ Test the read-only function of pagure-admin to set the status of
        a namespaced project.
        """

        # Before
        args = munch.Munch(
            {"project": "somenamespace/test", "user": None, "ro": None}
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            "The current read-only flag of the project somenamespace/test "
            "is set to True\n",
            output,
        )

        args = munch.Munch(
            {"project": "somenamespace/test", "user": None, "ro": "false"}
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            "The read-only flag of the project somenamespace/test has been "
            "set to False\n",
            output,
        )

        # After
        args = munch.Munch(
            {"project": "somenamespace/test", "user": None, "ro": None}
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            "The current read-only flag of the project somenamespace/test "
            "is set to False\n",
            output,
        )

    def test_read_only_no_change(self):
        """ Test the read-only function of pagure-admin to set the status of
        a namespaced project.
        """

        # Before
        args = munch.Munch({"project": "test", "user": None, "ro": None})
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            "The current read-only flag of the project test "
            "is set to True\n",
            output,
        )

        args = munch.Munch({"project": "test", "user": None, "ro": "true"})
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            "The read-only flag of the project test has been " "set to True\n",
            output,
        )

        # After
        args = munch.Munch({"project": "test", "user": None, "ro": None})
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            "The current read-only flag of the project test "
            "is set to True\n",
            output,
        )


class PagureNewGroupTests(tests.Modeltests):
    """ Tests for pagure-admin new-group """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureNewGroupTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user="pingou",
            fullname="PY C",
            password="foo",
            default_email="bar@pingou.com",
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(user_id=1, email="bar@pingou.com")
        self.session.add(item)

        self.session.commit()

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 0)

    def test_missing_display_name(self):
        """ Test the new-group function of pagure-admin when the display name
        is missing from the args.
        """

        args = munch.Munch(
            {
                "group_name": "foob",
                "display": None,
                "description": None,
                "username": "pingou",
            }
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_new_group(args)
        self.assertEqual(
            cm.exception.args[0],
            "A display name must be provided for the group",
        )

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 0)

    def test_missing_username(self):
        """ Test the new-group function of pagure-admin when the username
        is missing from the args.
        """

        args = munch.Munch(
            {
                "group_name": "foob",
                "display": "foo group",
                "description": None,
                "username": None,
            }
        )

        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_new_group(args)

        self.assertEqual(
            cm.exception.args[0],
            "An username must be provided to associate with the group",
        )

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 0)

    def test_new_group(self):
        """ Test the new-group function of pagure-admin when all arguments
        are provided.
        """

        args = munch.Munch(
            {
                "group_name": "foob",
                "display": "foo group",
                "description": None,
                "username": "pingou",
            }
        )

        pagure.cli.admin.do_new_group(args)

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 1)

    @patch.dict("pagure.config.config", {"ENABLE_GROUP_MNGT": False})
    @patch("pagure.cli.admin._ask_confirmation")
    def test_new_group_grp_mngt_off_no(self, conf):
        """ Test the new-group function of pagure-admin when all arguments
        are provided and ENABLE_GROUP_MNGT if off in the config and the user
        replies no to the question.
        """
        conf.return_value = False

        args = munch.Munch(
            {
                "group_name": "foob",
                "display": "foo group",
                "description": None,
                "username": "pingou",
            }
        )

        pagure.cli.admin.do_new_group(args)

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 0)

    @patch.dict("pagure.config.config", {"ENABLE_GROUP_MNGT": False})
    @patch("pagure.cli.admin._ask_confirmation")
    def test_new_group_grp_mngt_off_yes(self, conf):
        """ Test the new-group function of pagure-admin when all arguments
        are provided and ENABLE_GROUP_MNGT if off in the config and the user
        replies yes to the question.
        """
        conf.return_value = True

        args = munch.Munch(
            {
                "group_name": "foob",
                "display": "foo group",
                "description": None,
                "username": "pingou",
            }
        )

        pagure.cli.admin.do_new_group(args)

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 1)

    @patch.dict("pagure.config.config", {"BLACKLISTED_GROUPS": ["foob"]})
    def test_new_group_grp_mngt_off_yes(self):
        """ Test the new-group function of pagure-admin when all arguments
        are provided but the group is black listed.
        """

        args = munch.Munch(
            {
                "group_name": "foob",
                "display": "foo group",
                "description": None,
                "username": "pingou",
            }
        )

        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_new_group(args)

        self.assertEqual(
            cm.exception.args[0],
            "This group name has been blacklisted, please choose another one",
        )

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 0)


class PagureListGroupEmptyTests(tests.Modeltests):
    """ Tests for pagure-admin list-groups """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureListGroupEmptyTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user="pingou",
            fullname="PY C",
            password="foo",
            default_email="bar@pingou.com",
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(user_id=1, email="bar@pingou.com")
        self.session.add(item)

        self.session.commit()

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 0)

    @patch("sys.stdout", new_callable=StringIO)
    def test_no_groups(self, mock_stdout):
        """ Test the list-groups function of pagure-admin when there are no
        groups in the database
        """

        args = munch.Munch()
        pagure.cli.admin.do_list_groups(args)

        self.assertEqual(
            mock_stdout.getvalue(),
            "No groups found in this pagure instance.\n",
        )

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 0)


class PagureListGroupTests(tests.Modeltests):
    """ Tests for pagure-admin list-groups """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureListGroupTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user="pingou",
            fullname="PY C",
            password="foo",
            default_email="bar@pingou.com",
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(user_id=1, email="bar@pingou.com")
        self.session.add(item)

        # Create a group
        pagure.lib.query.add_group(
            self.session,
            group_name="JL",
            display_name="Justice League",
            description="Nope, it's not JLA anymore",
            group_type="user",
            user="pingou",
            is_admin=False,
            blacklist=[],
        )

        self.session.commit()

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 1)

    @patch("sys.stdout", new_callable=StringIO)
    def test_list_groups(self, mock_stdout):
        """ Test the list-groups function of pagure-admin when there is one
        group in the database
        """

        args = munch.Munch()
        pagure.cli.admin.do_list_groups(args)

        self.assertEqual(
            mock_stdout.getvalue(),
            "List of groups on this Pagure instance:\n" "Group: 1 - name JL\n",
        )

        groups = pagure.lib.query.search_groups(self.session)
        self.assertEqual(len(groups), 1)


class PagureBlockUserTests(tests.Modeltests):
    """ Tests for pagure-admin block-user """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureBlockUserTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user="pingou",
            fullname="PY C",
            password="foo",
            default_email="bar@pingou.com",
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(user_id=1, email="bar@pingou.com")
        self.session.add(item)

        self.session.commit()

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

        user = pagure.lib.query.get_user(self.session, "pingou")
        self.assertIsNone(user.refuse_sessions_before)

    def test_missing_date(self):
        """ Test the block-user function of pagure-admin when the no date is
        provided.
        """

        args = munch.Munch({"username": "pingou", "date": None, "list": False})
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_block_user(args)
        self.assertEqual(
            cm.exception.args[0],
            "Invalid date submitted: None, not of the format YYYY-MM-DD",
        )

        user = pagure.lib.query.get_user(self.session, "pingou")
        self.assertIsNone(user.refuse_sessions_before)

    def test_missing_username(self):
        """ Test the block-user function of pagure-admin when the username
        is missing from the args.
        """

        args = munch.Munch(
            {"date": "2018-06-11", "username": None, "list": False}
        )

        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_block_user(args)

        self.assertEqual(cm.exception.args[0], "An username must be specified")

        user = pagure.lib.query.get_user(self.session, "pingou")
        self.assertIsNone(user.refuse_sessions_before)

    def test_invalid_username(self):
        """ Test the block-user function of pagure-admin when the username
        provided does correspond to any user in the DB.
        """

        args = munch.Munch(
            {"date": "2018-06-11", "username": "invalid", "list": False}
        )

        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_block_user(args)

        self.assertEqual(cm.exception.args[0], 'No user "invalid" found')

        user = pagure.lib.query.get_user(self.session, "pingou")
        self.assertIsNone(user.refuse_sessions_before)

    def test_invalide_date(self):
        """ Test the block-user function of pagure-admin when the provided
        date is incorrect.
        """

        args = munch.Munch(
            {"date": "2018-14-05", "username": "pingou", "list": False}
        )

        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_block_user(args)

        self.assertEqual(
            cm.exception.args[0],
            "Invalid date submitted: 2018-14-05, not of the format YYYY-MM-DD",
        )

        user = pagure.lib.query.get_user(self.session, "pingou")
        self.assertIsNone(user.refuse_sessions_before)

    @patch("pagure.cli.admin._ask_confirmation", MagicMock(return_value=True))
    def test_block_user(self):
        """ Test the block-user function of pagure-admin when all arguments
        are provided correctly.
        """

        args = munch.Munch(
            {"date": "2050-12-31", "username": "pingou", "list": False}
        )

        pagure.cli.admin.do_block_user(args)

        user = pagure.lib.query.get_user(self.session, "pingou")
        self.assertIsNotNone(user.refuse_sessions_before)

    def test_list_blocked_user(self):
        """ Test the block-user function of pagure-admin when all arguments
        are provided correctly.
        """

        args = munch.Munch({"list": True, "username": None, "date": None})

        with tests.capture_output() as output:
            pagure.cli.admin.do_block_user(args)

        output = output.getvalue()
        self.assertEqual("No users are currently blocked\n", output)

    @patch("pagure.cli.admin._ask_confirmation", MagicMock(return_value=True))
    def test_list_blocked_user_with_data(self):
        """ Test the block-user function of pagure-admin when all arguments
        are provided correctly.
        """
        args = munch.Munch(
            {"date": "2050-12-31", "username": "pingou", "list": False}
        )
        pagure.cli.admin.do_block_user(args)

        args = munch.Munch({"list": True, "username": None, "date": None})

        with tests.capture_output() as output:
            pagure.cli.admin.do_block_user(args)

        output = output.getvalue()
        self.assertEqual(
            "Users blocked:\n"
            " pingou                -  2050-12-31T00:00:00\n",
            output,
        )

    @patch("pagure.cli.admin._ask_confirmation", MagicMock(return_value=True))
    def test_list_blocked_user_with_username_data(self):
        """ Test the block-user function of pagure-admin when all arguments
        are provided correctly.
        """
        args = munch.Munch(
            {"date": "2050-12-31", "username": "pingou", "list": False}
        )
        pagure.cli.admin.do_block_user(args)

        args = munch.Munch({"list": True, "username": "ralph", "date": None})

        with tests.capture_output() as output:
            pagure.cli.admin.do_block_user(args)

        output = output.getvalue()
        self.assertEqual("No users are currently blocked\n", output)

        args = munch.Munch({"list": True, "username": "pin*", "date": None})

        with tests.capture_output() as output:
            pagure.cli.admin.do_block_user(args)
        output = output.getvalue()
        self.assertEqual(
            "Users blocked:\n"
            " pingou                -  2050-12-31T00:00:00\n",
            output,
        )

    @patch("pagure.cli.admin._ask_confirmation", MagicMock(return_value=True))
    def test_list_blocked_user_with_date(self):
        """ Test the block-user function of pagure-admin when all arguments
        are provided correctly.
        """
        args = munch.Munch(
            {"list": True, "username": None, "date": "2050-12-31"}
        )

        with tests.capture_output() as output:
            pagure.cli.admin.do_block_user(args)

        output = output.getvalue()
        self.assertIn("No users are currently blocked\n", output)

    @patch("pagure.cli.admin._ask_confirmation", MagicMock(return_value=True))
    def test_list_blocked_user_with_date_and_data(self):
        """ Test the block-user function of pagure-admin when all arguments
        are provided correctly.
        """
        args = munch.Munch(
            {"date": "2050-12-31", "username": "pingou", "list": False}
        )
        pagure.cli.admin.do_block_user(args)

        args = munch.Munch(
            {"list": True, "username": None, "date": "2050-12-31"}
        )

        with tests.capture_output() as output:
            pagure.cli.admin.do_block_user(args)

        output = output.getvalue()
        self.assertIn(
            "Users blocked:\n"
            " pingou                -  2050-12-31T00:00:00\n",
            output,
        )

        args = munch.Munch(
            {"list": True, "username": None, "date": "2051-01-01"}
        )

        with tests.capture_output() as output:
            pagure.cli.admin.do_block_user(args)

        output = output.getvalue()
        self.assertIn("No users are currently blocked\n", output)


class PagureAdminDeleteProjectTests(tests.Modeltests):
    """ Tests for pagure-admin delete-project """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminDeleteProjectTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user="pingou",
            fullname="PY C",
            password="foo",
            default_email="bar@pingou.com",
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(user_id=1, email="bar@pingou.com")
        self.session.add(item)

        # Create two projects for the user pingou
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test",
            description="namespaced test project",
            hook_token="aaabbbeee",
            namespace="somenamespace",
        )
        self.session.add(item)

        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test",
            description="Test project",
            hook_token="aaabbbccc",
            namespace=None,
        )
        self.session.add(item)

        self.session.commit()

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

    def test_delete_project_unknown_project(self):
        """ Test the read-only function of pagure-admin on an unknown
        project.
        """

        args = munch.Munch(
            {"project": "foob", "user": None, "action_user": "pingou"}
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_delete_project(args)
        self.assertEqual(
            cm.exception.args[0],
            "No project found with: project=foob, user=None",
        )

    def test_delete_project_invalid_project(self):
        """ Test the read-only function of pagure-admin on an invalid
        project.
        """

        args = munch.Munch(
            {"project": "fo/o/b", "user": None, "action_user": "pingou"}
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_delete_project(args)
        self.assertEqual(
            cm.exception.args[0],
            'Invalid project name, has more than one "/": fo/o/b',
        )

    @patch("pagure.cli.admin._ask_confirmation", MagicMock(return_value=True))
    def test_delete_project(self):
        """ Test the read-only function of pagure-admin to get status of
        a non-namespaced project.
        """

        args = munch.Munch(
            {"project": "test", "user": None, "action_user": "pingou"}
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_delete_project(args)
        output = output.getvalue()
        self.assertEqual(
            "Are you sure you want to delete: test?\n"
            "  This cannot be undone!\n"
            "Project deleted\n",
            output,
        )

    @patch("pagure.cli.admin._ask_confirmation", MagicMock(return_value=True))
    def test_delete_project_namespace(self):
        """ Test the read-only function of pagure-admin to get status of
        a namespaced project.
        """

        args = munch.Munch(
            {
                "project": "somenamespace/test",
                "user": None,
                "action_user": "pingou",
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_delete_project(args)
        output = output.getvalue()
        self.assertEqual(
            "Are you sure you want to delete: somenamespace/test?\n"
            "  This cannot be undone!\n"
            "Project deleted\n",
            output,
        )

    @patch("pagure.cli.admin._ask_confirmation", MagicMock(return_value=True))
    def test_delete_project_namespace_changed(self):
        """ Test the read-only function of pagure-admin to set the status of
        a namespaced project.
        """

        # Before
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 2)

        args = munch.Munch(
            {
                "project": "somenamespace/test",
                "user": None,
                "action_user": "pingou",
            }
        )
        with tests.capture_output() as output:
            pagure.cli.admin.do_delete_project(args)
        output = output.getvalue()
        self.assertEqual(
            "Are you sure you want to delete: somenamespace/test?\n"
            "  This cannot be undone!\n"
            "Project deleted\n",
            output,
        )

        # After
        projects = pagure.lib.query.search_projects(self.session)
        self.assertEqual(len(projects), 1)


class PagureCreateBranchTests(tests.Modeltests):
    """ Tests for pagure-admin create-branch """

    populate_db = True

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureCreateBranchTests, self).setUp()

        # Create a couple of projects
        tests.create_projects(self.session)
        # Create their git repo
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

    def test_create_branch_unknown_project(self):
        """ Test the read-only function of pagure-admin on an unknown
        project.
        """

        args = munch.Munch(
            {
                "project": "foob",
                "user": None,
                "new_branch": "new_branch",
                "from_branch": "master",
                "from_commit": None,
                "action_user": "pingou",
            }
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_create_branch(args)
        self.assertEqual(
            cm.exception.args[0],
            "No project found with: project=foob, user=None",
        )

    def test_create_branch_invalid_project(self):
        """ Test the read-only function of pagure-admin on an invalid
        project.
        """

        args = munch.Munch(
            {
                "project": "f/o/o/b",
                "user": None,
                "new_branch": "new_branch",
                "from_branch": "master",
                "from_commit": None,
                "action_user": "pingou",
            }
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_create_branch(args)
        self.assertEqual(
            cm.exception.args[0],
            'Invalid project name, has more than one "/": f/o/o/b',
        )

    def test_create_branch_commit_and_branch_from(self):
        """ Test the read-only function of pagure-admin to get status of
        a non-namespaced project.
        """

        args = munch.Munch(
            {
                "project": "test",
                "user": None,
                "new_branch": "new_branch",
                "from_branch": "master",
                "from_commit": "foobar",
                "action_user": "pingou",
            }
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_create_branch(args)
        self.assertEqual(
            cm.exception.args[0],
            "You must create the branch from something, either a commit "
            "or another branch, not from both",
        )

    def test_create_branch_no_branch_from(self):
        """ Test the read-only function of pagure-admin to get status of
        a non-namespaced project.
        """

        args = munch.Munch(
            {
                "project": "test",
                "user": None,
                "new_branch": "new_branch",
                "from_branch": "master",
                "from_commit": None,
                "action_user": "pingou",
            }
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_create_branch(args)
        self.assertEqual(
            cm.exception.args[0], 'The "master" branch does not exist'
        )

    def test_create_branch_no_commit_from(self):
        """ Test the read-only function of pagure-admin to get status of
        a non-namespaced project.
        """

        args = munch.Munch(
            {
                "project": "test",
                "user": None,
                "new_branch": "new_branch",
                "from_branch": None,
                "from_commit": "foobar",
                "action_user": "pingou",
            }
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_create_branch(args)
        self.assertEqual(
            cm.exception.args[0], "No commit foobar found from which to branch"
        )

    def test_create_branch_from_branch(self):
        """ Test the do_create_admin_token function of pagure-admin. """

        gitrepo_path = os.path.join(self.path, "repos", "test.git")
        tests.add_content_git_repo(gitrepo_path)

        # Check branch before:
        gitrepo = pygit2.Repository(gitrepo_path)
        self.assertEqual(gitrepo.listall_branches(), ["master"])

        args = munch.Munch(
            {
                "project": "test",
                "user": None,
                "new_branch": "new_branch",
                "from_branch": "master",
                "from_commit": None,
                "action_user": "pingou",
            }
        )

        with tests.capture_output() as output:
            pagure.cli.admin.do_create_branch(args)
        output = output.getvalue()
        self.assertEqual("Branch created\n", output)

        # Check branch after:
        gitrepo = pygit2.Repository(gitrepo_path)
        self.assertEqual(
            sorted(gitrepo.listall_branches()), ["master", "new_branch"]
        )


class PagureSetDefaultBranchTests(tests.Modeltests):
    """ Tests for pagure-admin set-default-branch """

    populate_db = True

    def setUp(self):
        """ Set up the environment, run before every tests. """
        super(PagureSetDefaultBranchTests, self).setUp()

        # Create a couple of projects
        tests.create_projects(self.session)
        # Create their git repo
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

    def test_set_default_branch_unknown_project(self):
        """ Test the set-default-branch function of pagure-admin on an unknown
        project.
        """

        args = munch.Munch(
            {"project": "foob", "user": None, "branch": "master"}
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_set_default_branch(args)
        self.assertEqual(
            cm.exception.args[0],
            "No project found with: project=foob, user=None",
        )

    def test_set_default_branch_invalid_project(self):
        """ Test the set-default-branch function of pagure-admin on an invalid
        project.
        """

        args = munch.Munch(
            {"project": "f/o/o/b", "user": None, "branch": "master"}
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_set_default_branch(args)
        self.assertEqual(
            cm.exception.args[0],
            'Invalid project name, has more than one "/": f/o/o/b',
        )

    def test_set_default_branch_unknown_branch(self):
        """ Test the set-default-branch function of pagure-admin on an unknown
        branch.
        """

        args = munch.Munch({"project": "test", "user": None, "branch": "foob"})
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_set_default_branch(args)
        self.assertEqual(
            cm.exception.args[0], "No foob branch found on project: test"
        )

    def test_set_default_branch_invalid_branch(self):
        """ Test the set-default-branch function of pagure-admin on an invalid branch.
        """

        args = munch.Munch(
            {"project": "test", "user": None, "branch": "~invalid~"}
        )
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_set_default_branch(args)
        self.assertEqual(
            cm.exception.args[0], "No ~invalid~ branch found on project: test"
        )

    def test_set_default_branch(self):
        """ Test the set-default-branch funcion of pagure-admin. """

        gitrepo_path = os.path.join(self.path, "repos", "test.git")
        tests.add_content_git_repo(gitrepo_path)
        tests.add_commit_git_repo(gitrepo_path, branch="dev")

        # Check default branch before:
        gitrepo = pygit2.Repository(gitrepo_path)
        self.assertEqual(gitrepo.head.shorthand, "master")

        args = munch.Munch({"project": "test", "user": None, "branch": "dev"})

        with tests.capture_output() as output:
            pagure.cli.admin.do_set_default_branch(args)
        output = output.getvalue()
        self.assertEqual("Branch dev set as default\n", output)

        # Check default branch after:
        self.assertEqual(gitrepo.head.shorthand, "dev")


if __name__ == "__main__":
    unittest.main(verbosity=2)
