# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources  # noqa

import unittest  # noqa
import shutil  # noqa
import subprocess  # noqa
import sys  # noqa
import os  # noqa

import munch  # noqa
from mock import patch, MagicMock  # noqa

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

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

    def test_parse_arguments(self):
        """ Test the parse_arguments function of pagure-admin, empty. """
        if 'BUILD_ID' in os.environ:
            raise unittest.case.SkipTest('Skipping on jenkins/el7')

        cmd = ['python', PAGURE_ADMIN]
        output = _get_ouput(cmd)
        self.assertEqual(output[0], '')
        self.assertEqual(output[1], '''usage: admin.py [-h] [--debug]
                {refresh-gitolite,refresh-ssh,clear-hook-token,admin-token}
                ...
admin.py: error: too few arguments
''')

    def test_parse_arguments_help(self):
        """ Test the parse_arguments function of pagure-admin. """
        cmd = ['python', PAGURE_ADMIN, '--help']
        self.assertEqual(
            _get_ouput(cmd)[0],
            '''usage: admin.py [-h] [--debug]
                {refresh-gitolite,refresh-ssh,clear-hook-token,admin-token}
                ...

The admin CLI for this pagure instance

optional arguments:
  -h, --help            show this help message and exit
  --debug               Increase the verbosity of the information displayed

actions:
  {refresh-gitolite,refresh-ssh,clear-hook-token,admin-token}
    refresh-gitolite    Re-generate the gitolite config file
    refresh-ssh         Re-write to disk every user's ssh key stored in the
                        database
    clear-hook-token    Generate a new hook token for every project in this
                        instance
    admin-token         Manages the admin tokens for this instance
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
            '''usage: admin.py admin-token [-h] {list,info,expire,create} ...

optional arguments:
  -h, --help            show this help message and exit

actions:
  {list,info,expire,create}
    list                List the API admin token
    info                Provide some information about a specific API token
    expire              Expire a specific API token
    create              Create a new API token
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
            '''usage: admin.py admin-token [-h] {list,info,expire,create} ...
admin.py admin-token: error: invalid choice: 'foo' (choose from 'list', 'info', 'expire', 'create')
''')  # noqa


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
            self.dbpath, acls=pagure.APP.config.get('ACLS', {}))

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
        pagure.cli.admin.SESSION = self.session

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
            self.dbpath, acls=pagure.APP.config.get('ACLS', {}))

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
        pagure.cli.admin.SESSION = self.session

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
