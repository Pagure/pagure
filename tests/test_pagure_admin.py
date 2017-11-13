# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources  # noqa

import datetime  # noqa
import unittest  # noqa
import shutil  # noqa
import subprocess  # noqa
import sys  # noqa
import os  # noqa

import munch  # noqa
from mock import patch, MagicMock  # noqa

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.config  # noqa
import pagure.cli.admin  # noqa
import pagure.lib.model  # noqa
import tests  # noqa

PAGURE_ADMIN = os.path.abspath(
    os.path.join(tests.HERE, '..', 'pagure', 'cli', 'admin.py'))


def _get_ouput(cmd):
    """ Returns the std-out of the command specified.

    :arg cmd: the command to run provided as a list
    :type cmd: list

    """
    my_env = os.environ.copy()
    my_env["PYTHONPATH"] = os.path.abspath(os.path.join(tests.HERE, '..'))
    output = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=my_env,
    ).communicate()

    return output


class PagureAdminHelptests(tests.Modeltests):
    """ Tests for pagure-admin --help """

    maxDiff = None

    def test_parse_arguments(self):
        """ Test the parse_arguments function of pagure-admin, empty. """
        if 'BUILD_ID' in os.environ:
            raise unittest.case.SkipTest('Skipping on jenkins/el7')

        cmd = ['python', PAGURE_ADMIN]
        output = _get_ouput(cmd)
        self.assertEqual(output[0], '')
        self.assertEqual(output[1], '''usage: admin.py [-h] [-c CONFIG] [--debug]
                {refresh-gitolite,refresh-ssh,clear-hook-token,admin-token,get-watch,update-watch,read-only}
                ...
admin.py: error: too few arguments
''')  # noqa

    def test_parse_arguments_help(self):
        """ Test the parse_arguments function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py [-h] [-c CONFIG] [--debug]
                {refresh-gitolite,refresh-ssh,clear-hook-token,admin-token,get-watch,update-watch,read-only}
                ...

The admin CLI for this pagure instance

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Specify a configuration to use
  --debug               Increase the verbosity of the information displayed

actions:
  {refresh-gitolite,refresh-ssh,clear-hook-token,admin-token,get-watch,update-watch,read-only}
    refresh-gitolite    Re-generate the gitolite config file
    refresh-ssh         Re-write to disk every user's ssh key stored in the
                        database
    clear-hook-token    Generate a new hook token for every project in this
                        instance
    admin-token         Manages the admin tokens for this instance
    get-watch           Get someone's watch status on a project
    update-watch        Update someone's watch status on a project
    read-only           Get or set the read-only flag on a project
''')

    def test_parser_refresh_gitolite_help(self):
        """ Test the parser_refresh_gitolite function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, 'refresh-gitolite', '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py refresh-gitolite [-h] [--user USER] [--project PROJECT]
                                 [--group GROUP] [--all]

optional arguments:
  -h, --help         show this help message and exit
  --user USER        User of the project (to use only on forks)
  --project PROJECT  Project to update (as namespace/project if there is a
                     namespace)
  --group GROUP      Group to refresh
  --all              Refresh all the projects
''')

    def test_parser_refresh_ssh_help(self):
        """ Test the parser_refresh_ssh function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, 'refresh-ssh', '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py refresh-ssh [-h]

optional arguments:
  -h, --help  show this help message and exit
''')

    def test_parser_clear_hook_token_help(self):
        """ Test the parser_clear_hook_token function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, 'clear-hook-token', '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py clear-hook-token [-h]

optional arguments:
  -h, --help  show this help message and exit
''')

    def test_parser_admin_token_help(self):
        """ Test the parser_admin_token function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, 'admin-token', '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py admin-token [-h] {list,info,expire,create,update} ...

optional arguments:
  -h, --help            show this help message and exit

actions:
  {list,info,expire,create,update}
    list                List the API admin token
    info                Provide some information about a specific API token
    expire              Expire a specific API token
    create              Create a new API token
    update              Update the expiration date of an API token
''')

    def test_parser_admin_token_create_help(self):
        """ Test the parser_admin_token_create function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'create', '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py admin-token create [-h] user

positional arguments:
  user        User to associate with the token

optional arguments:
  -h, --help  show this help message and exit
''')

    def test_parser_admin_token_update_help(self):
        """ Test the parser_admin_token_create function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'update', '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py admin-token update [-h] token date

positional arguments:
  token       API token
  date        New expiration date

optional arguments:
  -h, --help  show this help message and exit
''')

    def test_parser_admin_token_list_help(self):
        """ Test the _parser_admin_token_list function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list', '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py admin-token list [-h] [--user USER] [--token TOKEN] [--active]
                                 [--expired]

optional arguments:
  -h, --help     show this help message and exit
  --user USER    User to associate or associated with the token
  --token TOKEN  API token
  --active       Only list active API token
  --expired      Only list expired API token
''')  # noqa

    def test_parser_admin_token_info_help(self):
        """ Test the _parser_admin_token_info function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'info', '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py admin-token info [-h] token

positional arguments:
  token       API token

optional arguments:
  -h, --help  show this help message and exit
''')

    def test_parser_admin_token_expire_help(self):
        """ Test the _parser_admin_token_expire function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'expire', '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py admin-token expire [-h] token

positional arguments:
  token       API token

optional arguments:
  -h, --help  show this help message and exit
''')

    def test_parser_admin_token_invalid_help(self):
        """ Test the _parser_admin_token_expire function of pagure-admin. """
        if 'BUILD_ID' in os.environ:
            raise unittest.case.SkipTest('Skipping on jenkins/el7')

        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'foo', '--help']
        self.assertEqual(
            _get_ouput(cmd)[1],
            '''usage: admin.py admin-token [-h] {list,info,expire,create,update} ...
admin.py admin-token: error: invalid choice: 'foo' (choose from 'list', 'info', 'expire', 'create', 'update')
''')  # noqa

    def test_parser_get_watch(self):
        """ Test the _parser_get_watch function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, 'get-watch', '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py get-watch [-h] project user

positional arguments:
  project     Project (as namespace/project if there is a namespace) -- Fork
              not supported
  user        User to get the watch status of

optional arguments:
  -h, --help  show this help message and exit
''')

    def test_parser_update_watch(self):
        """ Test the _parser_update_watch function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, 'update-watch', '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py update-watch [-h] [-s STATUS] project user

positional arguments:
  project               Project to update (as namespace/project if there is a
                        namespace) -- Fork not supported
  user                  User to update the watch status of

optional arguments:
  -h, --help            show this help message and exit
  -s STATUS, --status STATUS
                        Watch status to update to
''')

    def test_parser_read_only(self):
        """ Test the _parser_update_watch function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, 'read-only', '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py read-only [-h] [--user USER] [--ro RO] project

positional arguments:
  project      Project to update (as namespace/project if there is a
               namespace)

optional arguments:
  -h, --help   show this help message and exit
  --user USER  User of the project (to use only on forks)
  --ro RO      Read-Only status to set (has to be: true or false), do not
               specify to get the current status
''')


class PagureAdminAdminTokenEmptytests(tests.Modeltests):
    """ Tests for pagure-admin admin-token when there is nothing in the DB
    """
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminAdminTokenEmptytests, self).setUp()

        self.configfile = os.path.join(self.path, 'config')
        self.dbpath = "sqlite:///%s/pagure_dev.sqlite" % self.path
        with open(self.configfile, 'w') as stream:
            stream.write('DB_URL="%s"\n' % self.dbpath)

        os.environ['PAGURE_CONFIG'] = self.configfile

        createdb = os.path.abspath(
            os.path.join(tests.HERE, '..', 'createdb.py'))
        cmd = ['python', createdb]
        _get_ouput(cmd)

    def tearDown(self):
        """ Tear down the environnment after running the tests. """
        super(PagureAdminAdminTokenEmptytests, self).tearDown()
        del(os.environ['PAGURE_CONFIG'])

    def test_do_create_admin_token_no_user(self):
        """ Test the do_create_admin_token function of pagure-admin without
        user.
        """
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'create', 'pingou']
        self.assertEqual(_get_ouput(cmd)[0], 'No user "pingou" found\n')

    def test_do_list_admin_token_empty(self):
        """ Test the do_list_admin_token function of pagure-admin when there
        are not tokens in the db.
        """
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list']
        self.assertEqual(_get_ouput(cmd)[0], 'No admin tokens found\n')


class PagureAdminAdminRefreshGitolitetests(tests.Modeltests):
    """ Tests for pagure-admin refresh-gitolite """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminAdminRefreshGitolitetests, self).setUp()

        self.configfile = os.path.join(self.path, 'config')
        self.dbpath = "sqlite:///%s/pagure_dev.sqlite" % self.path
        with open(self.configfile, 'w') as stream:
            stream.write('DB_URL="%s"\n' % self.dbpath)

        os.environ['PAGURE_CONFIG'] = self.configfile

        createdb = os.path.abspath(
            os.path.join(tests.HERE, '..', 'createdb.py'))
        cmd = ['python', createdb]
        _get_ouput(cmd)

        self.session = pagure.lib.model.create_tables(
            self.dbpath, acls=pagure.config.config.get('ACLS', {}))

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

    def tearDown(self):
        """ Tear down the environnment after running the tests. """
        super(PagureAdminAdminRefreshGitolitetests, self).tearDown()
        del(os.environ['PAGURE_CONFIG'])

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

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminAdminTokentests, self).setUp()

        self.configfile = os.path.join(self.path, 'config')
        self.dbpath = "sqlite:///%s/pagure_dev.sqlite" % self.path
        with open(self.configfile, 'w') as stream:
            stream.write('DB_URL="%s"\n' % self.dbpath)

        os.environ['PAGURE_CONFIG'] = self.configfile

        createdb = os.path.abspath(
            os.path.join(tests.HERE, '..', 'createdb.py'))
        cmd = ['python', createdb]
        _get_ouput(cmd)

        self.session = pagure.lib.model.create_tables(
            self.dbpath, acls=pagure.config.config.get('ACLS', {}))

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

    def tearDown(self):
        """ Tear down the environnment after running the tests. """
        super(PagureAdminAdminTokentests, self).tearDown()
        del(os.environ['PAGURE_CONFIG'])

    @patch('pagure.cli.admin._get_input')
    @patch('pagure.cli.admin._ask_confirmation')
    def test_do_create_admin_token(self, conf, rinp):
        """ Test the do_create_admin_token function of pagure-admin. """
        conf.return_value = True
        rinp.return_value = '1,2,3'

        args = munch.Munch({'user': 'pingou'})
        pagure.cli.admin.do_create_admin_token(args)

        # Check the outcome
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list']
        output = _get_ouput(cmd)[0]
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
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list']
        output = _get_ouput(cmd)[0]
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        # Retrieve pfrields's tokens
        cmd = [
            'python', PAGURE_ADMIN,
            'admin-token', 'list', '--user', 'pfrields']
        output = _get_ouput(cmd)[0]
        self.assertEqual(output, 'No admin tokens found\n')

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
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list']
        output = _get_ouput(cmd)[0]
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        token = output.split(' ', 1)[0]

        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'info', token]
        output = _get_ouput(cmd)[0]
        self.assertIn(' -- pingou -- ', output.split('\n', 1)[0])
        self.assertEqual(
            output.split('\n', 1)[1], '''ACLs:
  - issue_create
  - pull_request_comment
  - pull_request_flag
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
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list']
        output = _get_ouput(cmd)[0]
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        token = output.split(' ', 1)[0]

        # Before
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list', '--active']
        output = _get_ouput(cmd)[0]
        self.assertNotEqual(output, 'No admin tokens found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        # Expire the token
        args = munch.Munch({'token': token})
        pagure.cli.admin.do_expire_admin_token(args)

        # After
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list', '--active']
        output = _get_ouput(cmd)[0]
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
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list']
        output = _get_ouput(cmd)[0]
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
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list']
        output = _get_ouput(cmd)[0]
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
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list']
        output = _get_ouput(cmd)[0]
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
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list']
        output = _get_ouput(cmd)[0]
        self.assertNotEqual(output, 'No user "pingou" found\n')
        self.assertEqual(len(output.split('\n')), 2)
        self.assertIn(' -- pingou -- ', output)

        token = output.split(' ', 1)[0]
        current_expiration = output.strip().split(' -- ', 2)[-1]

        # Before
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list', '--active']
        output = _get_ouput(cmd)[0]
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
        cmd = ['python', PAGURE_ADMIN, 'admin-token', 'list', '--active']
        output = _get_ouput(cmd)[0]
        self.assertEqual(output.split(' ', 1)[0], token)
        self.assertNotEqual(
            output.strip().split(' -- ', 2)[-1],
            current_expiration)


class PagureAdminGetWatchTests(tests.Modeltests):
    """ Tests for pagure-admin get-watch """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminGetWatchTests, self).setUp()

        self.configfile = os.path.join(self.path, 'config')
        self.dbpath = "sqlite:///%s/pagure_dev.sqlite" % self.path
        with open(self.configfile, 'w') as stream:
            stream.write('DB_URL="%s"\n' % self.dbpath)

        os.environ['PAGURE_CONFIG'] = self.configfile

        createdb = os.path.abspath(
            os.path.join(tests.HERE, '..', 'createdb.py'))
        cmd = ['python', createdb]
        _get_ouput(cmd)

        self.session = pagure.lib.model.create_tables(
            self.dbpath, acls=pagure.config.config.get('ACLS', {}))

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

    def tearDown(self):
        """ Tear down the environnment after running the tests. """
        super(PagureAdminGetWatchTests, self).tearDown()
        del(os.environ['PAGURE_CONFIG'])

    def test_get_watch_get_project_unknown_project(self):
        """ Test the get-watch function of pagure-admin with an unknown
        project.
        """

        cmd = ['python', PAGURE_ADMIN, 'get-watch', 'foobar', 'pingou']
        output = _get_ouput(cmd)[0]
        self.assertEqual('No project found with: foobar\n', output)

    def test_get_watch_get_project_invalid_project(self):
        """ Test the get-watch function of pagure-admin with an invalid
        project.
        """

        cmd = ['python', PAGURE_ADMIN, 'get-watch', 'fo/o/bar', 'pingou']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'Invalid project name, has more than one "/": fo/o/bar\n',
            output)

    def test_get_watch_get_project_invalid_user(self):
        """ Test the get-watch function of pagure-admin on a invalid user.
        """

        cmd = ['python', PAGURE_ADMIN, 'get-watch', 'test', 'beebop']
        output = _get_ouput(cmd)[0]
        self.assertEqual('No user "beebop" found\n', output)

    def test_get_watch_get_project(self):
        """ Test the get-watch function of pagure-admin on a regular project.
        """

        cmd = ['python', PAGURE_ADMIN, 'get-watch', 'test', 'pingou']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'On test user: pingou is watching the following items: '
            'issues, pull-requests\n', output)

    def test_get_watch_get_project_not_watching(self):
        """ Test the get-watch function of pagure-admin on a regular project.
        """

        cmd = ['python', PAGURE_ADMIN, 'get-watch', 'test', 'foo']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'On test user: foo is watching the following items: None\n',
            output)

    def test_get_watch_get_project_namespaced(self):
        """ Test the get-watch function of pagure-admin on a namespaced project.
        """

        cmd = [
            'python', PAGURE_ADMIN, 'get-watch',
            'somenamespace/test', 'pingou']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'On somenamespace/test user: pingou is watching the following '
            'items: issues, pull-requests\n', output)

    def test_get_watch_get_project_namespaced_not_watching(self):
        """ Test the get-watch function of pagure-admin on a namespaced project.
        """

        cmd = [
            'python', PAGURE_ADMIN, 'get-watch',
            'somenamespace/test', 'foo']
        output = _get_ouput(cmd)[0]
        _get_ouput(cmd)
        self.assertEqual(
            'On somenamespace/test user: foo is watching the following '
            'items: None\n', output)


class PagureAdminUpdateWatchTests(tests.Modeltests):
    """ Tests for pagure-admin update-watch """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminUpdateWatchTests, self).setUp()

        self.configfile = os.path.join(self.path, 'config')
        self.dbpath = "sqlite:///%s/pagure_dev.sqlite" % self.path
        with open(self.configfile, 'w') as stream:
            stream.write('DB_URL="%s"\n' % self.dbpath)

        os.environ['PAGURE_CONFIG'] = self.configfile

        createdb = os.path.abspath(
            os.path.join(tests.HERE, '..', 'createdb.py'))
        cmd = ['python', createdb]
        _get_ouput(cmd)

        self.session = pagure.lib.model.create_tables(
            self.dbpath, acls=pagure.config.config.get('ACLS', {}))

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

    def tearDown(self):
        """ Tear down the environnment after running the tests. """
        super(PagureAdminUpdateWatchTests, self).tearDown()
        del(os.environ['PAGURE_CONFIG'])

    def test_get_watch_update_project_unknown_project(self):
        """ Test the update-watch function of pagure-admin on an unknown
        project.
        """

        cmd = ['python', PAGURE_ADMIN, 'update-watch', 'foob', 'pingou', '-s=1']
        output = _get_ouput(cmd)[0]
        self.assertEqual('No project found with: foob\n', output)

    def test_get_watch_update_project_invalid_project(self):
        """ Test the update-watch function of pagure-admin on an invalid
        project.
        """

        cmd = ['python', PAGURE_ADMIN, 'update-watch', 'fo/o/b', 'pingou', '-s=1']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'Invalid project name, has more than one "/": fo/o/b\n',
            output)

    def test_get_watch_update_project_invalid_user(self):
        """ Test the update-watch function of pagure-admin on an invalid user.
        """

        cmd = ['python', PAGURE_ADMIN, 'update-watch', 'test', 'foob', '-s=1']
        output = _get_ouput(cmd)[0]
        self.assertEqual('No user "foob" found\n', output)

    def test_get_watch_update_project_invalid_status(self):
        """ Test the update-watch function of pagure-admin with an invalid
        status.
        """

        cmd = ['python', PAGURE_ADMIN, 'update-watch', 'test', 'pingou', '-s=10']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'Invalid status provided: 10 not in -1, 0, 1, 2, 3\n', output)

    def test_get_watch_update_project_no_effect(self):
        """ Test the update-watch function of pagure-admin with a regular
        project - nothing changed.
        """

        cmd = ['python', PAGURE_ADMIN, 'get-watch', 'test', 'pingou']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'On test user: pingou is watching the following items: '
            'issues, pull-requests\n', output)

        cmd = ['python', PAGURE_ADMIN, 'update-watch', 'test', 'pingou', '-s=1']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'Updating watch status of pingou to 1 (watch issues and PRs) '
            'on test\n', output)

        cmd = ['python', PAGURE_ADMIN, 'get-watch', 'test', 'pingou']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'On test user: pingou is watching the following items: '
            'issues, pull-requests\n', output)


class PagureAdminReadOnlyTests(tests.Modeltests):
    """ Tests for pagure-admin read-only """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureAdminReadOnlyTests, self).setUp()

        self.configfile = os.path.join(self.path, 'config')
        self.dbpath = "sqlite:///%s/pagure_dev.sqlite" % self.path
        with open(self.configfile, 'w') as stream:
            stream.write('DB_URL="%s"\n' % self.dbpath)

        os.environ['PAGURE_CONFIG'] = self.configfile

        createdb = os.path.abspath(
            os.path.join(tests.HERE, '..', 'createdb.py'))
        cmd = ['python', createdb]
        _get_ouput(cmd)

        self.session = pagure.lib.model.create_tables(
            self.dbpath, acls=pagure.config.config.get('ACLS', {}))

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

    def tearDown(self):
        """ Tear down the environnment after running the tests. """
        super(PagureAdminReadOnlyTests, self).tearDown()
        del(os.environ['PAGURE_CONFIG'])

    def test_read_only_unknown_project(self):
        """ Test the read-only function of pagure-admin on an unknown
        project.
        """

        cmd = ['python', PAGURE_ADMIN, 'read-only', 'foob']
        output = _get_ouput(cmd)[0]
        self.assertEqual('No project found with: foob\n', output)

    def test_read_only_invalid_project(self):
        """ Test the read-only function of pagure-admin on an invalid
        project.
        """

        cmd = ['python', PAGURE_ADMIN, 'read-only', 'fo/o/b']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'Invalid project name, has more than one "/": fo/o/b\n',
            output)

    def test_read_only(self):
        """ Test the read-only function of pagure-admin to get status of
        a non-namespaced project.
        """

        cmd = ['python', PAGURE_ADMIN, 'read-only', 'test']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'The current read-only flag of the project test is set to True\n',
            output)

    def test_read_only_namespace(self):
        """ Test the read-only function of pagure-admin to get status of
        a namespaced project.
        """

        cmd = ['python', PAGURE_ADMIN, 'read-only', 'somenamespace/test']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'The current read-only flag of the project somenamespace/test '\
            'is set to True\n', output)

    def test_read_only_namespace_changed(self):
        """ Test the read-only function of pagure-admin to set the status of
        a namespaced project.
        """

        # Before
        cmd = ['python', PAGURE_ADMIN, 'read-only', 'somenamespace/test']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'The current read-only flag of the project somenamespace/test '\
            'is set to True\n', output)

        cmd = [
            'python', PAGURE_ADMIN, 'read-only',
            'somenamespace/test', '--ro', 'false']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'The read-only flag of the project somenamespace/test has been '
            'set to False\n', output)

        # After
        cmd = ['python', PAGURE_ADMIN, 'read-only', 'somenamespace/test']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'The current read-only flag of the project somenamespace/test '\
            'is set to False\n', output)

    def test_read_only_no_change(self):
        """ Test the read-only function of pagure-admin to set the status of
        a namespaced project.
        """

        # Before
        cmd = ['python', PAGURE_ADMIN, 'read-only', 'test']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'The current read-only flag of the project test '\
            'is set to True\n', output)

        cmd = [
            'python', PAGURE_ADMIN, 'read-only', 'test', '--ro', 'true']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'The read-only flag of the project test has been '
            'set to True\n', output)

        # After
        cmd = ['python', PAGURE_ADMIN, 'read-only', 'test']
        output = _get_ouput(cmd)[0]
        self.assertEqual(
            'The current read-only flag of the project test '\
            'is set to True\n', output)


if __name__ == '__main__':
    unittest.main(verbosity=2)
