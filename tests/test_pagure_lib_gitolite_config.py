# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']

import pkg_resources

import datetime
import os
import shutil
import sys
import tempfile
import time
import unittest

import pygit2
from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib.git
import tests
from pagure.lib.repo import PagureRepo


CORE_CONFIG = """repo test
  R   = @all
  RW+ = pingou

repo docs/test
  R   = @all
  RW+ = pingou

repo tickets/test
  RW+ = pingou

repo requests/test
  RW+ = pingou

repo test2
  R   = @all
  RW+ = pingou

repo docs/test2
  R   = @all
  RW+ = pingou

repo tickets/test2
  RW+ = pingou

repo requests/test2
  RW+ = pingou

repo somenamespace/test3
  R   = @all
  RW+ = pingou

repo docs/somenamespace/test3
  R   = @all
  RW+ = pingou

repo tickets/somenamespace/test3
  RW+ = pingou

repo requests/somenamespace/test3
  RW+ = pingou"""


class PagureLibGitoliteConfigtests(tests.Modeltests):
    """ Tests for pagure.lib.git """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureLibGitoliteConfigtests, self).setUp()

        pagure.lib.git.SESSION = self.session
        tests.create_projects(self.session)

        self.outputconf = os.path.join(self.path, 'test_gitolite.conf')

        self.preconf = os.path.join(self.path, 'header_gitolite')
        with open(self.preconf, 'w') as stream:
            stream.write('# this is a header that is manually added\n')
            stream.write('\n')
            stream.write('@group1 = foo bar baz\n')
            stream.write('@group2 = threebean puiterwijk kevin pingou\n')

        self.postconf = os.path.join(self.path, 'footer_gitolite')
        with open(self.postconf, 'w') as stream:
            stream.write('# end of generated configuration\n')
            stream.write('# \ó/\n')
            stream.write('# end of footer\n')

    def tearDown(self):
        """ Tearn down the environnment, ran before every tests. """
        super(PagureLibGitoliteConfigtests, self).tearDown()

        if os.path.exists(self.outputconf):
            os.unlink(self.outputconf)
        self.assertFalse(os.path.exists(self.outputconf))

    def test_write_gitolite_pre_post_projectNone(self):
        """ Test the write_gitolite_acls function of pagure.lib.git with
        a postconf set """

        helper = pagure.lib.git_auth.get_git_auth_helper('gitolite3')
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=None,
            preconf=self.preconf,
            postconf=self.postconf
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = """# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou


%s

# end of generated configuration
# \ó/
# end of footer

""" % CORE_CONFIG
        #print data
        self.assertEqual(data, exp)

    def test_write_gitolite_pre_post_projectNone(self):
        """ Test the write_gitolite_acls function of pagure.lib.git with
        a postconf set """

        with open(self.outputconf, 'w') as stream:
            pass

        helper = pagure.lib.git_auth.get_git_auth_helper('gitolite3')
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=None,
            preconf=self.preconf,
            postconf=self.postconf
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()
        self.assertEqual(data, '')

    def test_write_gitolite_pre_post_project_1(self):
        """ Test the write_gitolite_acls function of pagure.lib.git with
        a postconf set """

        with open(self.outputconf, 'w') as stream:
            pass

        helper = pagure.lib.git_auth.get_git_auth_helper('gitolite3')
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=-1,
            preconf=self.preconf,
            postconf=self.postconf
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = """# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou


%s

# end of generated configuration
# \ó/
# end of footer

""" % CORE_CONFIG

        #print data
        self.assertEqual(data, exp)

    def test_write_gitolite_pre_post_project_test(self):
        """ Test the write_gitolite_acls function of pagure.lib.git with
        a postconf set """

        with open(self.outputconf, 'w') as stream:
            pass

        project = pagure.lib._get_project(self.session, 'test')

        helper = pagure.lib.git_auth.get_git_auth_helper('gitolite3')
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=project,
            preconf=self.preconf,
            postconf=self.postconf
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = """# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou


repo test
  R   = @all
  RW+ = pingou

repo docs/test
  R   = @all
  RW+ = pingou

repo tickets/test
  RW+ = pingou

repo requests/test
  RW+ = pingou

# end of generated configuration
# \ó/
# end of footer

"""
        #print data
        self.assertEqual(data, exp)

    def test_write_gitolite_pre_post_project_test_full_file(self):
        """ Test the write_gitolite_acls function of pagure.lib.git with
        a postconf set """

        # Re-generate the gitolite config for all the projects
        self.test_write_gitolite_pre_post_project_1()
        self.assertTrue(os.path.exists(self.outputconf))

        project = pagure.lib._get_project(self.session, 'test')
        project.user_id = 2
        self.session.add(project)
        self.session.commit()

        project = pagure.lib._get_project(self.session, 'test')
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=project,
            new_user='pingou',
            user='foo',
            access='commit'
        )
        self.assertEqual(msg, 'User added')
        self.session.commit()

        project = pagure.lib._get_project(self.session, 'test')
        helper = pagure.lib.git_auth.get_git_auth_helper('gitolite3')
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=project,
            preconf=self.preconf,
            postconf=self.postconf
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = """# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou


repo test2
  R   = @all
  RW+ = pingou

repo docs/test2
  R   = @all
  RW+ = pingou

repo tickets/test2
  RW+ = pingou

repo requests/test2
  RW+ = pingou

repo somenamespace/test3
  R   = @all
  RW+ = pingou

repo docs/somenamespace/test3
  R   = @all
  RW+ = pingou

repo tickets/somenamespace/test3
  RW+ = pingou

repo requests/somenamespace/test3
  RW+ = pingou

repo test
  R   = @all
  RW+ = foo
  RW+ = pingou

repo docs/test
  R   = @all
  RW+ = foo
  RW+ = pingou

repo tickets/test
  RW+ = foo
  RW+ = pingou

repo requests/test
  RW+ = foo
  RW+ = pingou

# end of generated configuration
# \ó/
# end of footer

"""
        #print data
        self.assertEqual(data, exp)


if __name__ == '__main__':
    unittest.main(verbosity=2)
