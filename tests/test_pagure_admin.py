# -*- coding: utf-8 -*-

"""
 (c) 2017-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources  # noqa

import datetime  # noqa
import os  # noqa
import platform  # noqa
import shutil  # noqa
import subprocess  # noqa
import sys  # noqa
import unittest  # noqa

import munch  # noqa
from mock import patch, MagicMock  # noqa

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

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
        args = munch.Munch({'user': "pingou"})
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_create_admin_token(args)
        self.assertEqual(
            cm.exception.args[0],
            'No user "pingou" found'
        )

    def test_do_list_admin_token_empty(self):
        """ Test the do_list_admin_token function of pagure-admin when there
        are not tokens in the db.
        """
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': False,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertEqual(output, 'No admin tokens found\n')


class PagureAdminAdminRefreshGitolitetests(tests.Modeltests):
    """ Tests for pagure-admin refresh-gitolite """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminAdminRefreshGitolitetests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user='pingou',
            fullname='PY C',
            password='foo',
            default_email='bar@pingou.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=1,
            email='bar@pingou.com')
        self.session.add(item)
        self.session.commit()

        # Create a couple of projects
        tests.create_projects(self.session)

        # Add a group
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

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

    @patch('pagure.cli.admin._ask_confirmation')
    @patch('pagure.lib.git_auth.get_git_auth_helper')
    def test_do_refresh_gitolite_no_args(self, get_helper, conf):
        """ Test the do_generate_acl function with no special args. """
        conf.return_value = True
        helper = MagicMock()
        get_helper.return_value = helper

        args = munch.Munch(
            {'group': None, 'project': None, 'all_': False, 'user': None})
        pagure.cli.admin.do_generate_acl(args)

        get_helper.assert_called_with('gitolite3')
        args = helper.generate_acls.call_args
        self.assertIsNone(args[1].get('group'))
        self.assertIsNone(args[1].get('project'))

    @patch('pagure.cli.admin._ask_confirmation')
    @patch('pagure.lib.git_auth.get_git_auth_helper')
    def test_do_refresh_gitolite_all_project(self, get_helper, conf):
        """ Test the do_generate_acl function for all projects. """
        conf.return_value = True
        helper = MagicMock()
        get_helper.return_value = helper

        args = munch.Munch(
            {'group': None, 'project': None, 'all_': True, 'user': None})
        pagure.cli.admin.do_generate_acl(args)

        get_helper.assert_called_with('gitolite3')
        args = helper.generate_acls.call_args
        self.assertIsNone(args[1].get('group'))
        self.assertEqual(args[1].get('project'), -1)

    @patch('pagure.cli.admin._ask_confirmation')
    @patch('pagure.lib.git_auth.get_git_auth_helper')
    def test_do_refresh_gitolite_one_project(self, get_helper, conf):
        """ Test the do_generate_acl function for a certain project. """
        conf.return_value = True
        helper = MagicMock()
        get_helper.return_value = helper

        args = munch.Munch(
            {'group': None, 'project': 'test', 'all_': False, 'user': None})
        pagure.cli.admin.do_generate_acl(args)

        get_helper.assert_called_with('gitolite3')
        args = helper.generate_acls.call_args
        self.assertIsNone(args[1].get('group'))
        self.assertEqual(args[1].get('project').fullname, 'test')

    @patch('pagure.cli.admin._ask_confirmation')
    @patch('pagure.lib.git_auth.get_git_auth_helper')
    def test_do_refresh_gitolite_one_project_and_all(self, get_helper, conf):
        """ Test the do_generate_acl function for a certain project and all.
        """
        conf.return_value = True
        helper = MagicMock()
        get_helper.return_value = helper

        args = munch.Munch(
            {'group': None, 'project': 'test', 'all_': True, 'user': None})
        pagure.cli.admin.do_generate_acl(args)

        get_helper.assert_called_with('gitolite3')
        args = helper.generate_acls.call_args
        self.assertIsNone(args[1].get('group'))
        self.assertEqual(args[1].get('project'), -1)

    @patch('pagure.cli.admin._ask_confirmation')
    @patch('pagure.lib.git_auth.get_git_auth_helper')
    def test_do_refresh_gitolite_one_group(self, get_helper, conf):
        """ Test the do_generate_acl function for a certain group. """
        conf.return_value = True
        helper = MagicMock()
        get_helper.return_value = helper

        args = munch.Munch(
            {'group': 'foo', 'project': None, 'all_': False, 'user': None})
        pagure.cli.admin.do_generate_acl(args)

        get_helper.assert_called_with('gitolite3')
        args = helper.generate_acls.call_args
        self.assertEqual(args[1].get('group').group_name, 'foo')
        self.assertIsNone(args[1].get('project'))


class PagureAdminAdminTokentests(tests.Modeltests):
    """ Tests for pagure-admin admin-token """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminAdminTokentests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user='pingou',
            fullname='PY C',
            password='foo',
            default_email='bar@pingou.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=1,
            email='bar@pingou.com')
        self.session.add(item)
        self.session.commit()

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

    @patch('pagure.cli.admin._get_input')
    @patch('pagure.cli.admin._ask_confirmation')
    def test_do_create_admin_token(self, conf, rinp):
        """ Test the do_create_admin_token function of pagure-admin. """
        conf.return_value = True
        rinp.return_value = '1,2,3'

        args = munch.Munch({'user': 'pingou'})
        pagure.cli.admin.do_create_admin_token(args)

        # Check the outcome
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': False,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

    @patch('pagure.cli.admin._get_input')
    @patch('pagure.cli.admin._ask_confirmation')
    def test_do_list_admin_token(self, conf, rinp):
        """ Test the do_list_admin_token function of pagure-admin. """
        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = '1,2,3'

        args = munch.Munch({'user': 'pingou'})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve all tokens
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': False,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        # Retrieve pfrields's tokens
        list_args = munch.Munch({
            'user': 'pfrields',
            'token': None,
            'active': False,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertEqual(output, 'No admin tokens found\n')

    def test_do_list_admin_token_non_admin_acls(self):
        """ Test the do_list_admin_token function of pagure-admin for a token
        without any admin ACL. """
        pagure.lib.add_token_to_user(
            self.session,
            project=None,
            acls=['issue_assign', 'pull_request_subscribe'],
            username='pingou')

        # Retrieve all admin tokens
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': False,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertEqual(output, 'No admin tokens found\n')

        # Retrieve all tokens
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': False,
            'expired': False,
            'all': True,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

    @patch('pagure.cli.admin._get_input')
    @patch('pagure.cli.admin._ask_confirmation')
    def test_do_info_admin_token(self, conf, rinp):
        """ Test the do_info_admin_token function of pagure-admin. """
        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = '1,3,4'

        args = munch.Munch({'user': 'pingou'})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve the token
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': False,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        token = output.split(' ', 1)[0]

        args = munch.Munch({'token': token})
        with tests.capture_output() as output:
            pagure.cli.admin.do_info_admin_token(args)
        output = output.getvalue()
        self.assertIn(' -- pingou -- ', output.split('\n', 1)[0])
        self.assertEqual(
            output.split('\n', 1)[1], '''ACLs:
  - issue_create
  - pull_request_comment
  - pull_request_flag
''')

    def test_do_info_admin_token_non_admin_acl(self):
        """ Test the do_info_admin_token function of pagure-admin for a
        token not having any admin ACL. """
        pagure.lib.add_token_to_user(
            self.session,
            project=None,
            acls=['issue_assign', 'pull_request_subscribe'],
            username='pingou')

        # Retrieve the token
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': False,
            'expired': False,
            'all': True,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        token = output.split(' ', 1)[0]

        args = munch.Munch({'token': token})
        with tests.capture_output() as output:
            pagure.cli.admin.do_info_admin_token(args)
        output = output.getvalue()
        self.assertIn(' -- pingou -- ', output.split('\n', 1)[0])
        self.assertEqual(
            output.split('\n', 1)[1], '''ACLs:
  - issue_assign
  - pull_request_subscribe
''')

    @patch('pagure.cli.admin._get_input')
    @patch('pagure.cli.admin._ask_confirmation')
    def test_do_expire_admin_token(self, conf, rinp):
        """ Test the do_expire_admin_token function of pagure-admin. """
        if 'BUILD_ID' in os.environ:
            raise unittest.case.SkipTest('Skipping on jenkins/el7')

        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = '1,2,3'

        args = munch.Munch({'user': 'pingou'})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve the token
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': False,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        token = output.split(' ', 1)[0]

        # Before
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': True,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No admin tokens found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        # Expire the token
        args = munch.Munch({'token': token})
        pagure.cli.admin.do_expire_admin_token(args)

        # After
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': True,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertEqual(output, 'No admin tokens found\n')

    @patch('pagure.cli.admin._get_input')
    @patch('pagure.cli.admin._ask_confirmation')
    def test_do_update_admin_token_invalid_date(self, conf, rinp):
        """ Test the do_update_admin_token function of pagure-admin with
        an invalid date. """
        if 'BUILD_ID' in os.environ:
            raise unittest.case.SkipTest('Skipping on jenkins/el7')

        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = '1,2,3'

        args = munch.Munch({'user': 'pingou'})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve the token
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': False,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        token = output.split(' ', 1)[0]
        current_expiration = output.split(' ', 1)[1]

        # Set the expiration date to the token
        args = munch.Munch({'token': token, 'date': 'aa-bb-cc'})
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.cli.admin.do_update_admin_token,
            args
        )

    @patch('pagure.cli.admin._get_input')
    @patch('pagure.cli.admin._ask_confirmation')
    def test_do_update_admin_token_invalid_date2(self, conf, rinp):
        """ Test the do_update_admin_token function of pagure-admin with
        an invalid date. """
        if 'BUILD_ID' in os.environ:
            raise unittest.case.SkipTest('Skipping on jenkins/el7')

        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = '1,2,3'

        args = munch.Munch({'user': 'pingou'})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve the token
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': False,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        token = output.split(' ', 1)[0]
        current_expiration = output.split(' ', 1)[1]

        # Set the expiration date to the token
        args = munch.Munch({'token': token, 'date': '2017-18-01'})
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.cli.admin.do_update_admin_token,
            args
        )

    @patch('pagure.cli.admin._get_input')
    @patch('pagure.cli.admin._ask_confirmation')
    def test_do_update_admin_token_invalid_date3(self, conf, rinp):
        """ Test the do_update_admin_token function of pagure-admin with
        an invalid date (is today). """
        if 'BUILD_ID' in os.environ:
            raise unittest.case.SkipTest('Skipping on jenkins/el7')

        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = '1,2,3'

        args = munch.Munch({'user': 'pingou'})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve the token
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': False,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        token = output.split(' ', 1)[0]
        current_expiration = output.split(' ', 1)[1]

        # Set the expiration date to the token
        args = munch.Munch({
            'token': token, 'date': datetime.datetime.utcnow().date()
        })
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.cli.admin.do_update_admin_token,
            args
        )

    @patch('pagure.cli.admin._get_input')
    @patch('pagure.cli.admin._ask_confirmation')
    def test_do_update_admin_token(self, conf, rinp):
        """ Test the do_update_admin_token function of pagure-admin. """
        if 'BUILD_ID' in os.environ:
            raise unittest.case.SkipTest('Skipping on jenkins/el7')

        # Create an admin token to use
        conf.return_value = True
        rinp.return_value = '1,2,3'

        args = munch.Munch({'user': 'pingou'})
        pagure.cli.admin.do_create_admin_token(args)

        # Retrieve the token
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': False,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        token = output.split(' ', 1)[0]
        current_expiration = output.strip().split(' -- ', 2)[-1]

        # Before
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': True,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertNotEqual(output, 'No admin tokens found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        deadline = datetime.datetime.utcnow().date() \
            + datetime.timedelta(days=3)

        # Set the expiration date to the token
        args = munch.Munch({
            'token': token,
            'date': deadline.strftime('%Y-%m-%d')
        })
        pagure.cli.admin.do_update_admin_token(args)

        # After
        list_args = munch.Munch({
            'user': None,
            'token': None,
            'active': True,
            'expired': False,
            'all': False,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_list_admin_token(list_args)
        output = output.getvalue()
        self.assertEqual(output.split(' ', 1)[0], token)
        self.assertNotEqual(
            output.strip().split(' -- ', 2)[-1],
            current_expiration)


class PagureAdminGetWatchTests(tests.Modeltests):
    """ Tests for pagure-admin get-watch """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminGetWatchTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user='pingou',
            fullname='PY C',
            password='foo',
            default_email='bar@pingou.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=1,
            email='bar@pingou.com')
        self.session.add(item)

        # Create the user foo
        item = pagure.lib.model.User(
            user='foo',
            fullname='foo B.',
            password='foob',
            default_email='foo@pingou.com',
        )
        self.session.add(item)

        # Create two projects for the user pingou
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test',
            description='namespaced test project',
            hook_token='aaabbbeee',
            namespace='somenamespace',
        )
        self.session.add(item)

        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test',
            description='Test project',
            hook_token='aaabbbccc',
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
        args = munch.Munch({
            'project': 'foobar',
            'user': 'pingou',
        })
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_get_watch_status(args)
        self.assertEqual(
            cm.exception.args[0],
            'No project found with: foobar'
        )

    def test_get_watch_get_project_invalid_project(self):
        """ Test the get-watch function of pagure-admin with an invalid
        project.
        """
        args = munch.Munch({
            'project': 'fo/o/bar',
            'user': 'pingou',
        })
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_get_watch_status(args)
        self.assertEqual(
            cm.exception.args[0],
            'Invalid project name, has more than one "/": fo/o/bar',
        )

    def test_get_watch_get_project_invalid_user(self):
        """ Test the get-watch function of pagure-admin on a invalid user.
        """
        args = munch.Munch({
            'project': 'test',
            'user': 'beebop',
        })
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_get_watch_status(args)
        self.assertEqual(
            cm.exception.args[0],
            'No user "beebop" found'
        )

    def test_get_watch_get_project(self):
        """ Test the get-watch function of pagure-admin on a regular project.
        """
        args = munch.Munch({
            'project': 'test',
            'user': 'pingou',
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_get_watch_status(args)
        output = output.getvalue()
        self.assertEqual(
            'On test user: pingou is watching the following items: '
            'issues, pull-requests\n', output)

    def test_get_watch_get_project_not_watching(self):
        """ Test the get-watch function of pagure-admin on a regular project.
        """

        args = munch.Munch({
            'project': 'test',
            'user': 'foo',
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_get_watch_status(args)
        output = output.getvalue()
        self.assertEqual(
            'On test user: foo is watching the following items: None\n',
            output)

    def test_get_watch_get_project_namespaced(self):
        """ Test the get-watch function of pagure-admin on a namespaced project.
        """

        args = munch.Munch({
            'project': 'somenamespace/test',
            'user': 'pingou',
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_get_watch_status(args)
        output = output.getvalue()
        self.assertEqual(
            'On somenamespace/test user: pingou is watching the following '
            'items: issues, pull-requests\n', output)

    def test_get_watch_get_project_namespaced_not_watching(self):
        """ Test the get-watch function of pagure-admin on a namespaced project.
        """

        args = munch.Munch({
            'project': 'somenamespace/test',
            'user': 'foo',
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_get_watch_status(args)
        output = output.getvalue()
        with tests.capture_output() as _discarded:
            pagure.cli.admin.do_get_watch_status(args)
        self.assertEqual(
            'On somenamespace/test user: foo is watching the following '
            'items: None\n', output)


class PagureAdminUpdateWatchTests(tests.Modeltests):
    """ Tests for pagure-admin update-watch """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminUpdateWatchTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user='pingou',
            fullname='PY C',
            password='foo',
            default_email='bar@pingou.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=1,
            email='bar@pingou.com')
        self.session.add(item)

        # Create the user foo
        item = pagure.lib.model.User(
            user='foo',
            fullname='foo B.',
            password='foob',
            default_email='foo@pingou.com',
        )
        self.session.add(item)

        # Create two projects for the user pingou
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test',
            description='namespaced test project',
            hook_token='aaabbbeee',
            namespace='somenamespace',
        )
        self.session.add(item)

        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test',
            description='Test project',
            hook_token='aaabbbccc',
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
        args = munch.Munch({
            'project': 'foob',
            'user': 'pingou',
            'status': '1'
        })
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_update_watch_status(args)
        self.assertEqual(
            cm.exception.args[0],
            'No project found with: foob'
        )

    def test_get_watch_update_project_invalid_project(self):
        """ Test the update-watch function of pagure-admin on an invalid
        project.
        """
        args = munch.Munch({
            'project': 'fo/o/b',
            'user': 'pingou',
            'status': '1'
        })
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_update_watch_status(args)
        self.assertEqual(
            cm.exception.args[0],
            'Invalid project name, has more than one "/": fo/o/b',
        )

    def test_get_watch_update_project_invalid_user(self):
        """ Test the update-watch function of pagure-admin on an invalid user.
        """
        args = munch.Munch({
            'project': 'test',
            'user': 'foob',
            'status': '1'
        })
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_update_watch_status(args)
        self.assertEqual(
            cm.exception.args[0],
            'No user "foob" found'
        )

    def test_get_watch_update_project_invalid_status(self):
        """ Test the update-watch function of pagure-admin with an invalid
        status.
        """
        args = munch.Munch({
            'project': 'test',
            'user': 'pingou',
            'status': '10'
        })
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_update_watch_status(args)
        self.assertEqual(
            cm.exception.args[0],
            'Invalid status provided: 10 not in -1, 0, 1, 2, 3'
        )

    def test_get_watch_update_project_no_effect(self):
        """ Test the update-watch function of pagure-admin with a regular
        project - nothing changed.
        """

        args = munch.Munch({
            'project': 'test',
            'user': 'pingou',
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_get_watch_status(args)
        output = output.getvalue()
        self.assertEqual(
            'On test user: pingou is watching the following items: '
            'issues, pull-requests\n', output)

        args = munch.Munch({
            'project': 'test',
            'user': 'pingou',
            'status': '1'
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_update_watch_status(args)
        output = output.getvalue()
        self.assertEqual(
            'Updating watch status of pingou to 1 (watch issues and PRs) '
            'on test\n', output)

        args = munch.Munch({
            'project': 'test',
            'user': 'pingou',
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_get_watch_status(args)
        output = output.getvalue()
        self.assertEqual(
            'On test user: pingou is watching the following items: '
            'issues, pull-requests\n', output)


class PagureAdminReadOnlyTests(tests.Modeltests):
    """ Tests for pagure-admin read-only """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminReadOnlyTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user='pingou',
            fullname='PY C',
            password='foo',
            default_email='bar@pingou.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=1,
            email='bar@pingou.com')
        self.session.add(item)

        # Create two projects for the user pingou
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test',
            description='namespaced test project',
            hook_token='aaabbbeee',
            namespace='somenamespace',
        )
        self.session.add(item)

        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test',
            description='Test project',
            hook_token='aaabbbccc',
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

        args = munch.Munch({
            'project': 'foob',
            'user': None,
            'ro': None,
        })
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_read_only(args)
        self.assertEqual(
            cm.exception.args[0],
            'No project found with: foob'
        )

    def test_read_only_invalid_project(self):
        """ Test the read-only function of pagure-admin on an invalid
        project.
        """

        args = munch.Munch({
            'project': 'fo/o/b',
            'user': None,
            'ro': None,
        })
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_read_only(args)
        self.assertEqual(
            cm.exception.args[0],
            'Invalid project name, has more than one "/": fo/o/b'
        )

    def test_read_only(self):
        """ Test the read-only function of pagure-admin to get status of
        a non-namespaced project.
        """

        args = munch.Munch({
            'project': 'test',
            'user': None,
            'ro': None,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            'The current read-only flag of the project test is set to True\n',
            output)

    def test_read_only_namespace(self):
        """ Test the read-only function of pagure-admin to get status of
        a namespaced project.
        """

        args = munch.Munch({
            'project': 'somenamespace/test',
            'user': None,
            'ro': None,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            'The current read-only flag of the project somenamespace/test '\
            'is set to True\n', output)

    def test_read_only_namespace_changed(self):
        """ Test the read-only function of pagure-admin to set the status of
        a namespaced project.
        """

        # Before
        args = munch.Munch({
            'project': 'somenamespace/test',
            'user': None,
            'ro': None,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            'The current read-only flag of the project somenamespace/test '\
            'is set to True\n', output)

        args = munch.Munch({
            'project': 'somenamespace/test',
            'user': None,
            'ro': 'false',
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            'The read-only flag of the project somenamespace/test has been '
            'set to False\n', output)

        # After
        args = munch.Munch({
            'project': 'somenamespace/test',
            'user': None,
            'ro': None,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            'The current read-only flag of the project somenamespace/test '\
            'is set to False\n', output)

    def test_read_only_no_change(self):
        """ Test the read-only function of pagure-admin to set the status of
        a namespaced project.
        """

        # Before
        args = munch.Munch({
            'project': 'test',
            'user': None,
            'ro': None,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            'The current read-only flag of the project test '\
            'is set to True\n', output)

        args = munch.Munch({
            'project': 'test',
            'user': None,
            'ro': 'true',
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            'The read-only flag of the project test has been '
            'set to True\n', output)

        # After
        args = munch.Munch({
            'project': 'test',
            'user': None,
            'ro': None,
        })
        with tests.capture_output() as output:
            pagure.cli.admin.do_read_only(args)
        output = output.getvalue()
        self.assertEqual(
            'The current read-only flag of the project test '\
            'is set to True\n', output)


class PagureNewGroupTests(tests.Modeltests):
    """ Tests for pagure-admin new-group """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureNewGroupTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user='pingou',
            fullname='PY C',
            password='foo',
            default_email='bar@pingou.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=1,
            email='bar@pingou.com')
        self.session.add(item)

        self.session.commit()

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 0)

    def test_missing_display_name(self):
        """ Test the new-group function of pagure-admin when the display name
        is missing from the args.
        """

        args = munch.Munch({
            'group_name': 'foob',
            'display': None,
            'description': None,
            'username': 'pingou',
        })
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_new_group(args)
        self.assertEqual(
            cm.exception.args[0],
            'A display name must be provided for the group'
        )

        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 0)

    def test_missing_username(self):
        """ Test the new-group function of pagure-admin when the username
        is missing from the args.
        """

        args = munch.Munch({
            'group_name': 'foob',
            'display': 'foo group',
            'description': None,
            'username': None,
        })

        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_new_group(args)

        self.assertEqual(
            cm.exception.args[0],
            'An username must be provided to associate with the group'
        )

        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 0)

    def test_new_group(self):
        """ Test the new-group function of pagure-admin when all arguments
        are provided.
        """

        args = munch.Munch({
            'group_name': 'foob',
            'display': 'foo group',
            'description': None,
            'username': 'pingou',
        })

        pagure.cli.admin.do_new_group(args)

        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 1)

    @patch.dict('pagure.config.config', {'ENABLE_GROUP_MNGT': False})
    @patch('pagure.cli.admin._ask_confirmation')
    def test_new_group_grp_mngt_off_no(self, conf):
        """ Test the new-group function of pagure-admin when all arguments
        are provided and ENABLE_GROUP_MNGT if off in the config and the user
        replies no to the question.
        """
        conf.return_value = False

        args = munch.Munch({
            'group_name': 'foob',
            'display': 'foo group',
            'description': None,
            'username': 'pingou',
        })

        pagure.cli.admin.do_new_group(args)

        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 0)

    @patch.dict('pagure.config.config', {'ENABLE_GROUP_MNGT': False})
    @patch('pagure.cli.admin._ask_confirmation')
    def test_new_group_grp_mngt_off_yes(self, conf):
        """ Test the new-group function of pagure-admin when all arguments
        are provided and ENABLE_GROUP_MNGT if off in the config and the user
        replies yes to the question.
        """
        conf.return_value = True

        args = munch.Munch({
            'group_name': 'foob',
            'display': 'foo group',
            'description': None,
            'username': 'pingou',
        })

        pagure.cli.admin.do_new_group(args)

        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 1)

    @patch.dict('pagure.config.config', {'BLACKLISTED_GROUPS': ['foob']})
    def test_new_group_grp_mngt_off_yes(self):
        """ Test the new-group function of pagure-admin when all arguments
        are provided but the group is black listed.
        """

        args = munch.Munch({
            'group_name': 'foob',
            'display': 'foo group',
            'description': None,
            'username': 'pingou',
        })

        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_new_group(args)

        self.assertEqual(
            cm.exception.args[0],
            'This group name has been blacklisted, please choose another one'
        )

        groups = pagure.lib.search_groups(self.session)
        self.assertEqual(len(groups), 0)


class PagureBlockUserTests(tests.Modeltests):
    """ Tests for pagure-admin block-user """

    populate_db = False

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureBlockUserTests, self).setUp()
        pagure.cli.admin.session = self.session

        # Create the user pingou
        item = pagure.lib.model.User(
            user='pingou',
            fullname='PY C',
            password='foo',
            default_email='bar@pingou.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=1,
            email='bar@pingou.com')
        self.session.add(item)

        self.session.commit()

        # Make the imported pagure use the correct db session
        pagure.cli.admin.session = self.session

        user = pagure.lib.get_user(self.session, 'pingou')
        self.assertIsNone(user.refuse_sessions_before)

    def test_missing_date(self):
        """ Test the block-user function of pagure-admin when the no date is
        provided.
        """

        args = munch.Munch({
            'username': 'pingou',
            'date': None,
        })
        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_block_user(args)
        self.assertEqual(
            cm.exception.args[0],
            'Invalid date submitted: None, not of the format YYYY-MM-DD'
        )

        user = pagure.lib.get_user(self.session, 'pingou')
        self.assertIsNone(user.refuse_sessions_before)

    def test_missing_username(self):
        """ Test the block-user function of pagure-admin when the username
        is missing from the args.
        """

        args = munch.Munch({
            'date': '2018-06-11',
            'username': None,
        })

        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_block_user(args)

        self.assertEqual(
            cm.exception.args[0],
            'An username must be specified'
        )

        user = pagure.lib.get_user(self.session, 'pingou')
        self.assertIsNone(user.refuse_sessions_before)

    def test_invalid_username(self):
        """ Test the block-user function of pagure-admin when the username
        provided does correspond to any user in the DB.
        """

        args = munch.Munch({
            'date': '2018-06-11',
            'username': 'invalid'
        })

        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_block_user(args)

        self.assertEqual(
            cm.exception.args[0],
            'No user "invalid" found'
        )

        user = pagure.lib.get_user(self.session, 'pingou')
        self.assertIsNone(user.refuse_sessions_before)

    def test_invalide_date(self):
        """ Test the block-user function of pagure-admin when the provided
        date is incorrect.
        """

        args = munch.Munch({
            'date': '2018-14-05',
            'username': 'pingou',
        })

        with self.assertRaises(pagure.exceptions.PagureException) as cm:
            pagure.cli.admin.do_block_user(args)

        self.assertEqual(
            cm.exception.args[0],
            'Invalid date submitted: 2018-14-05, not of the format YYYY-MM-DD'
        )

        user = pagure.lib.get_user(self.session, 'pingou')
        self.assertIsNone(user.refuse_sessions_before)

    @patch('pagure.cli.admin._ask_confirmation', MagicMock(return_value=True))
    def test_block_user(self):
        """ Test the block-user function of pagure-admin when all arguments
        are provided correctly.
        """

        args = munch.Munch({
            'date': '2050-12-31',
            'username': 'pingou',
        })

        pagure.cli.admin.do_block_user(args)

        user = pagure.lib.get_user(self.session, 'pingou')
        self.assertIsNotNone(user.refuse_sessions_before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
