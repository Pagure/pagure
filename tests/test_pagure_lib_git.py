# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import os
import shutil
import sys
import tempfile
import time
import unittest

import pygit2
import six
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.git
import tests

from pagure.lib.repo import PagureRepo


class PagureLibGittests(tests.Modeltests):
    """ Tests for pagure.lib.git """

    def test_write_gitolite_acls(self):
        """ Test the write_gitolite_acls function of pagure.lib.git.
        when the new uesr is an made an admin """
        tests.create_projects(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        # Add an user to a project
        # The user will be an admin of the project
        msg = pagure.lib.query.add_user_to_project(
            session=self.session, project=repo, new_user="foo", user="pingou"
        )
        self.session.commit()
        self.assertEqual(msg, "User added")
        # Add a forked project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #2",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbvvv",
        )
        self.session.add(item)
        self.session.commit()

        outputconf = os.path.join(self.path, "test_gitolite.conf")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session, configfile=outputconf, project=-1
        )

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """repo test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo docs/test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo tickets/test
  RW+ = pingou
  RW+ = foo

repo requests/test
  RW+ = pingou
  RW+ = foo

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

repo forks/pingou/test3
  R   = @all
  RW+ = pingou

repo docs/forks/pingou/test3
  R   = @all
  RW+ = pingou

repo tickets/forks/pingou/test3
  RW+ = pingou

repo requests/forks/pingou/test3
  RW+ = pingou

# end of body
"""
        # print data
        self.assertEqual(data, exp)

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_write_gitolite_acls_preconf(self):
        """ Test the write_gitolite_acls function of pagure.lib.git with
        a preconf set """
        tests.create_projects(self.session)

        outputconf = os.path.join(self.path, "test_gitolite.conf")
        preconf = os.path.join(self.path, "header_gitolite")
        with open(preconf, "w") as stream:
            stream.write("# this is a header that is manually added")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session, outputconf, project=-1, preconf=preconf
        )
        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """# this is a header that is manually added
# end of header
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

# end of body
"""
        # print data
        self.assertEqual(data.split("\n"), exp.split("\n"))

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_write_gitolite_acls_preconf_postconf(self):
        """ Test the write_gitolite_acls function of pagure.lib.git with
        a postconf set """
        tests.create_projects(self.session)

        outputconf = os.path.join(self.path, "test_gitolite.conf")

        preconf = os.path.join(self.path, "header_gitolite")
        with open(preconf, "w") as stream:
            stream.write("# this is a header that is manually added")

        postconf = os.path.join(self.path, "footer_gitolite")
        with open(postconf, "w") as stream:
            stream.write("# end of generated configuration")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session,
            outputconf,
            project=-1,
            preconf=preconf,
            postconf=postconf,
        )
        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """# this is a header that is manually added
# end of header
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

# end of body
# end of generated configuration
"""
        # print data
        self.assertEqual(data, exp)

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_write_gitolite_acls_postconf(self):
        """ Test the write_gitolite_acls function of pagure.lib.git with
        a preconf and a postconf set """
        tests.create_projects(self.session)

        outputconf = os.path.join(self.path, "test_gitolite.conf")
        postconf = os.path.join(self.path, "footer_gitolite")
        with open(postconf, "w") as stream:
            stream.write("# end of generated configuration")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session, outputconf, project=-1, postconf=postconf
        )
        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """repo test
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
  RW+ = pingou

# end of body
# end of generated configuration
"""
        # print data
        self.assertEqual(data, exp)

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_write_gitolite_acls_deploykeys(self):
        """ Test write_gitolite_acls function to add deploy keys. """
        tests.create_projects(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        # Add two deploy keys (one readonly one push)
        pingou = pagure.lib.query.get_user(self.session, "pingou")
        msg1 = pagure.lib.query.add_sshkey_to_project_or_user(
            session=self.session,
            project=repo,
            ssh_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDAzBMSIlvPRaEiLOTVInErkRIw9CzQQcnslDekAn1jFnGf+SNa1acvbTiATbCX71AA03giKrPxPH79dxcC7aDXerc6zRcKjJs6MAL9PrCjnbyxCKXRNNZU5U9X/DLaaL1b3caB+WD6OoorhS3LTEtKPX8xyjOzhf3OQSzNjhJp5Q==",
            pushaccess=False,
            creator=pingou,
        )
        msg2 = pagure.lib.query.add_sshkey_to_project_or_user(
            session=self.session,
            project=repo,
            ssh_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQC9Xwc2RDzPBhlEDARfHldGjudIVoa04tqT1JVKGQmyllTFz7Rb8CngQL3e7zyNzotnhwYKHdoiLlPkVEiDee4dWMUe48ilqId+FJZQGhyv8fu4BoFdE1AJUVylzmltbLg14VqG5gjTpXgtlrEva9arKwBMHJjRYc8ScaSn3OgyQw==",
            pushaccess=True,
            creator=pingou,
        )
        self.session.commit()
        self.assertEqual(msg1, "SSH key added")
        self.assertEqual(msg2, "SSH key added")
        # Add a forked project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #2",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbvvv",
        )
        self.session.add(item)
        self.session.commit()

        outputconf = os.path.join(self.path, "test_gitolite.conf")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(self.session, outputconf, project=-1)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """repo test
  R   = @all
  RW+ = pingou
  R = deploykey_test_1
  RW+ = deploykey_test_2

repo docs/test
  R   = @all
  RW+ = pingou
  R = deploykey_test_1
  RW+ = deploykey_test_2

repo tickets/test
  RW+ = pingou
  R = deploykey_test_1
  RW+ = deploykey_test_2

repo requests/test
  RW+ = pingou
  R = deploykey_test_1
  RW+ = deploykey_test_2

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

repo forks/pingou/test3
  R   = @all
  RW+ = pingou

repo docs/forks/pingou/test3
  R   = @all
  RW+ = pingou

repo tickets/forks/pingou/test3
  RW+ = pingou

repo requests/forks/pingou/test3
  RW+ = pingou

# end of body
"""
        # print data
        self.assertEqual(data, exp)

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_write_gitolite_acls_ticket(self):
        """ Test the write_gitolite_acls function of pagure.lib.git.
        when the new uesr is just a ticketer """
        tests.create_projects(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        # Add an user to a project
        # The user will be an admin of the project
        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=repo,
            new_user="foo",
            user="pingou",
            access="ticket",
        )
        self.session.commit()
        self.assertEqual(msg, "User added")
        # Add a forked project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #2",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbvvv",
        )
        self.session.add(item)
        self.session.commit()

        outputconf = os.path.join(self.path, "test_gitolite.conf")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(self.session, outputconf, project=-1)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """repo test
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
  RW+ = pingou

repo forks/pingou/test3
  R   = @all
  RW+ = pingou

repo docs/forks/pingou/test3
  R   = @all
  RW+ = pingou

repo tickets/forks/pingou/test3
  RW+ = pingou

repo requests/forks/pingou/test3
  RW+ = pingou

# end of body
"""
        # print data
        self.assertEqual(data, exp)

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_write_gitolite_acls_commit(self):
        """ Test the write_gitolite_acls function of pagure.lib.git.
        when the new uesr is just a committer """
        tests.create_projects(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        # Add an user to a project
        # The user will be an admin of the project
        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=repo,
            new_user="foo",
            user="pingou",
            access="commit",
        )
        self.session.commit()
        self.assertEqual(msg, "User added")
        # Add a forked project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #2",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbvvv",
        )
        self.session.add(item)
        self.session.commit()

        outputconf = os.path.join(self.path, "test_gitolite.conf")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(self.session, outputconf, project=-1)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """repo test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo docs/test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo tickets/test
  RW+ = pingou
  RW+ = foo

repo requests/test
  RW+ = pingou
  RW+ = foo

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

repo forks/pingou/test3
  R   = @all
  RW+ = pingou

repo docs/forks/pingou/test3
  R   = @all
  RW+ = pingou

repo tickets/forks/pingou/test3
  RW+ = pingou

repo requests/forks/pingou/test3
  RW+ = pingou

# end of body
"""
        # print data
        self.assertEqual(data, exp)

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_write_gitolite_acls_groups(self):
        """ Test the write_gitolite_acls function of pagure.lib.git with
        groups as admin
        """
        tests.create_projects(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Add a couple of groups
        # They would be admins
        msg = pagure.lib.query.add_group(
            self.session,
            group_name="sysadmin",
            display_name="sysadmin group",
            description=None,
            group_type="user",
            user="pingou",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, "User `pingou` added to the group `sysadmin`.")
        msg = pagure.lib.query.add_group(
            self.session,
            group_name="devs",
            display_name="devs group",
            description=None,
            group_type="user",
            user="pingou",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, "User `pingou` added to the group `devs`.")

        # Associate these groups to a project
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=repo,
            new_group="sysadmin",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")
        msg = pagure.lib.query.add_group_to_project(
            session=self.session, project=repo, new_group="devs", user="pingou"
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        # Add an user to a project
        msg = pagure.lib.query.add_user_to_project(
            session=self.session, project=repo, new_user="foo", user="pingou"
        )
        self.session.commit()
        self.assertEqual(msg, "User added")
        # Add a forked project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test2",
            description="test project #2",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbvvv",
        )
        self.session.add(item)
        self.session.commit()

        outputconf = os.path.join(self.path, "test_gitolite.conf")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(self.session, outputconf, project=-1)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """@devs  = pingou
@sysadmin  = pingou
# end of groups

repo test
  R   = @all
  RW+ = @devs @sysadmin
  RW+ = pingou
  RW+ = foo

repo docs/test
  R   = @all
  RW+ = @devs @sysadmin
  RW+ = pingou
  RW+ = foo

repo tickets/test
  RW+ = @devs @sysadmin
  RW+ = pingou
  RW+ = foo

repo requests/test
  RW+ = @devs @sysadmin
  RW+ = pingou
  RW+ = foo

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

repo forks/pingou/test2
  R   = @all
  RW+ = pingou

repo docs/forks/pingou/test2
  R   = @all
  RW+ = pingou

repo tickets/forks/pingou/test2
  RW+ = pingou

repo requests/forks/pingou/test2
  RW+ = pingou

# end of body
"""
        # print data
        self.assertEqual(data.split("\n"), exp.split("\n"))

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_write_gitolite_acls_groups_ticket(self):
        """ Test the write_gitolite_acls function of pagure.lib.git with
        groups as ticketers
        """
        tests.create_projects(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Add a couple of groups
        # They would be ticketers
        msg = pagure.lib.query.add_group(
            self.session,
            group_name="sysadmin",
            display_name="sysadmin group",
            description=None,
            group_type="user",
            user="pingou",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, "User `pingou` added to the group `sysadmin`.")
        msg = pagure.lib.query.add_group(
            self.session,
            group_name="devs",
            display_name="devs group",
            description=None,
            group_type="user",
            user="pingou",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, "User `pingou` added to the group `devs`.")

        # Associate these groups to a project
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=repo,
            new_group="sysadmin",
            user="pingou",
            access="ticket",
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=repo,
            new_group="devs",
            user="pingou",
            access="ticket",
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        # Add an user to a project
        msg = pagure.lib.query.add_user_to_project(
            session=self.session, project=repo, new_user="foo", user="pingou"
        )
        self.session.commit()
        self.assertEqual(msg, "User added")
        # Add a forked project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test2",
            description="test project #2",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbvvv",
        )
        self.session.add(item)
        self.session.commit()

        outputconf = os.path.join(self.path, "test_gitolite.conf")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(self.session, outputconf, project=-1)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """@devs  = pingou
@sysadmin  = pingou
# end of groups

repo test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo docs/test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo tickets/test
  RW+ = pingou
  RW+ = foo

repo requests/test
  RW+ = pingou
  RW+ = foo

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

repo forks/pingou/test2
  R   = @all
  RW+ = pingou

repo docs/forks/pingou/test2
  R   = @all
  RW+ = pingou

repo tickets/forks/pingou/test2
  RW+ = pingou

repo requests/forks/pingou/test2
  RW+ = pingou

# end of body
"""
        # print data
        self.assertEqual(data.split("\n"), exp.split("\n"))

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_write_gitolite_acls_groups_commit(self):
        """ Test the write_gitolite_acls function of pagure.lib.git with
        groups as committers
        """
        tests.create_projects(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Add a couple of groups
        # They would be committers
        msg = pagure.lib.query.add_group(
            self.session,
            group_name="sysadmin",
            display_name="sysadmin group",
            description=None,
            group_type="user",
            user="pingou",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, "User `pingou` added to the group `sysadmin`.")
        msg = pagure.lib.query.add_group(
            self.session,
            group_name="devs",
            display_name="devs group",
            description=None,
            group_type="user",
            user="pingou",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, "User `pingou` added to the group `devs`.")

        # Associate these groups to a project
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=repo,
            new_group="sysadmin",
            user="pingou",
            access="commit",
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")
        msg = pagure.lib.query.add_group_to_project(
            session=self.session,
            project=repo,
            new_group="devs",
            user="pingou",
            access="commit",
        )
        self.session.commit()
        self.assertEqual(msg, "Group added")

        # Add an user to a project
        msg = pagure.lib.query.add_user_to_project(
            session=self.session, project=repo, new_user="foo", user="pingou"
        )
        self.session.commit()
        self.assertEqual(msg, "User added")
        # Add a forked project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test2",
            description="test project #2",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbvvv",
        )
        self.session.add(item)
        self.session.commit()

        outputconf = os.path.join(self.path, "test_gitolite.conf")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(self.session, outputconf, project=-1)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """@devs  = pingou
@sysadmin  = pingou
# end of groups

repo test
  R   = @all
  RW+ = @devs @sysadmin
  RW+ = pingou
  RW+ = foo

repo docs/test
  R   = @all
  RW+ = @devs @sysadmin
  RW+ = pingou
  RW+ = foo

repo tickets/test
  RW+ = @devs @sysadmin
  RW+ = pingou
  RW+ = foo

repo requests/test
  RW+ = @devs @sysadmin
  RW+ = pingou
  RW+ = foo

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

repo forks/pingou/test2
  R   = @all
  RW+ = pingou

repo docs/forks/pingou/test2
  R   = @all
  RW+ = pingou

repo tickets/forks/pingou/test2
  RW+ = pingou

repo requests/forks/pingou/test2
  RW+ = pingou

# end of body
"""
        # print data
        self.assertEqual(data.split("\n"), exp.split("\n"))

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_write_gitolite_project_pr_only(self):
        """ Test the write_gitolite_acls function of pagure.lib.git.
        when the project enforces the PR approach.
        """
        tests.create_projects(self.session)

        repo = pagure.lib.query._get_project(self.session, "test")
        # Make the project enforce the PR workflow
        settings = repo.settings
        settings["pull_request_access_only"] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        # Add an user to a project
        # The user will be an admin of the project
        msg = pagure.lib.query.add_user_to_project(
            session=self.session, project=repo, new_user="foo", user="pingou"
        )
        self.session.commit()
        self.assertEqual(msg, "User added")
        # Add a forked project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #2",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbvvv",
        )
        self.session.add(item)
        self.session.commit()

        outputconf = os.path.join(self.path, "test_gitolite.conf")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(self.session, outputconf, project=-1)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """repo docs/test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo tickets/test
  RW+ = pingou
  RW+ = foo

repo requests/test
  RW+ = pingou
  RW+ = foo

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

repo forks/pingou/test3
  R   = @all
  RW+ = pingou

repo docs/forks/pingou/test3
  R   = @all
  RW+ = pingou

repo tickets/forks/pingou/test3
  RW+ = pingou

repo requests/forks/pingou/test3
  RW+ = pingou

# end of body
"""
        # print data
        self.assertEqual(data, exp)

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    @patch.dict("pagure.config.config", {"PR_ONLY": True})
    def test_write_gitolite_global_pr_only(self):
        """ Test the write_gitolite_acls function of pagure.lib.git.
        when the pagure instance enforces the PR approach.
        """
        tests.create_projects(self.session)

        repo = pagure.lib.query._get_project(self.session, "test")
        self.assertFalse(repo.settings["pull_request_access_only"])

        # Add an user to a project
        # The user will be an admin of the project
        msg = pagure.lib.query.add_user_to_project(
            session=self.session, project=repo, new_user="foo", user="pingou"
        )
        self.session.commit()
        self.assertEqual(msg, "User added")
        # Add a forked project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #2",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbvvv",
        )
        self.session.add(item)
        self.session.commit()

        outputconf = os.path.join(self.path, "test_gitolite.conf")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(self.session, outputconf, project=-1)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """repo docs/test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo tickets/test
  RW+ = pingou
  RW+ = foo

repo requests/test
  RW+ = pingou
  RW+ = foo

repo docs/test2
  R   = @all
  RW+ = pingou

repo tickets/test2
  RW+ = pingou

repo requests/test2
  RW+ = pingou

repo docs/somenamespace/test3
  R   = @all
  RW+ = pingou

repo tickets/somenamespace/test3
  RW+ = pingou

repo requests/somenamespace/test3
  RW+ = pingou

repo forks/pingou/test3
  R   = @all
  RW+ = pingou

repo docs/forks/pingou/test3
  R   = @all
  RW+ = pingou

repo tickets/forks/pingou/test3
  RW+ = pingou

repo requests/forks/pingou/test3
  RW+ = pingou

# end of body
"""
        # print data
        self.assertEqual(data, exp)

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    @patch("pagure.lib.notify.send_email")
    def test_update_git(self, email_f):
        """ Test the update_git of pagure.lib.git. """
        email_f.return_value = True

        # Create project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test_ticket_repo",
            description="test project for ticket",
            hook_token="aaabbbwww",
        )
        self.session.add(item)
        self.session.commit()

        # Create repo
        self.gitrepo = os.path.join(
            self.path, "repos", "tickets", "test_ticket_repo.git"
        )
        pygit2.init_repository(self.gitrepo, bare=True)

        repo = pagure.lib.query.get_authorized_project(
            self.session, "test_ticket_repo"
        )
        # Create an issue to play with
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
        )
        self.assertEqual(msg.title, "Test issue")
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        pagure.lib.git.update_git(issue, repo).get()

        repo = pygit2.Repository(self.gitrepo)
        commit = repo.revparse_single("HEAD")

        # Use patch to validate the repo
        commit_patch = pagure.lib.git.commit_to_patch(repo, commit)
        exp = r"""Mon Sep 17 00:00:00 2001
From: pagure <pagure>
Subject: Updated issue <hash>: Test issue


---

diff --git a/123 b/456
new file mode 100644
index 0000000..60f7480
--- /dev/null
+++ b/456
@@ -0,0 +1,30 @@
+{
+    "assignee": null,
+    "blocks": [],
+    "close_status": null,
+    "closed_at": null,
+    "comments": [],
+    "content": "We should work on this",
+    "custom_fields": [],
+    "date_created": null,
+    "depends": [],
+    "id": 1,
+    "last_updated": null,
+    "milestone": null,
+    "priority": null,
+    "private": false,
+    "related_prs": [],
+    "status": "Open",
+    "tags": [],
+    "title": "Test issue",
+    "user": {
+        "default_email": "bar@pingou.com",
+        "emails": [
+            "bar@pingou.com",
+            "foo@pingou.com"
+        ],
+        "fullname": "PY C",
+        "name": "pingou"
+    }
+}
\ No newline at end of file

"""
        npatch = []
        for row in commit_patch.split("\n"):
            if row.startswith("Date:"):
                continue
            elif row.startswith("From "):
                row = row.split(" ", 2)[2]
            elif row.startswith("diff --git "):
                row = row.split(" ")
                row[2] = "a/123"
                row[3] = "b/456"
                row = " ".join(row)
            elif "Updated issue" in row:
                row = row.split()
                row[3] = "<hash>:"
                row = " ".join(row)
            elif "date_created" in row:
                t = row.split(": ")[0]
                row = "%s: null," % t
            elif "last_updated" in row:
                t = row.split(": ")[0]
                row = "%s: null," % t
            elif "closed_at" in row:
                t = row.split(": ")[0]
                row = "%s: null," % t
            elif "closed_by" in row:
                continue
            elif row.startswith("index 00"):
                row = "index 0000000..60f7480"
            elif row.startswith("+++ b/"):
                row = "+++ b/456"
            npatch.append(row)
        commit_patch = "\n".join(npatch)
        # print commit_patch
        self.assertEqual(commit_patch, exp)

        # Enforce having a different last_updated field
        # This is required as the test run fine and fast with sqlite but is
        # much slower with postgresql so we end-up with an updated
        # last_updated in postgresql but not with sqlite
        time.sleep(1)

        # Test again after adding a comment
        # We need to make sure we wait for worker to commit the comment
        with patch("pagure.lib.git._maybe_wait", tests.definitely_wait):
            msg = pagure.lib.query.add_issue_comment(
                session=self.session,
                issue=issue,
                comment="Hey look a comment!",
                user="foo",
            )
        self.session.commit()
        self.assertEqual(msg, "Comment added")

        # Use patch to validate the repo
        repo = pygit2.Repository(self.gitrepo)
        commit = repo.revparse_single("HEAD")
        commit_patch = pagure.lib.git.commit_to_patch(repo, commit)
        exp = r"""Mon Sep 17 00:00:00 2001
From: pagure <pagure>
Subject: Updated issue <hash>: Test issue


---

diff --git a/123 b/456
index 458821a..77674a8
--- a/123
+++ b/456
@@ -4,13 +4,32 @@
     "close_status": null,
     "closed_at": null,
-    "comments": [],
+    "comments": [
+        {
+            "comment": "Hey look a comment!",
+            "date_created": null,
+            "edited_on": null,
+            "editor": null,
+            "id": 1,
+            "notification": false,
+            "parent": null,
+            "reactions": {},
+            "user": {
+                "default_email": "foo@bar.com",
+                "emails": [
+                    "foo@bar.com"
+                ],
+                "fullname": "foo bar",
+                "name": "foo"
+            }
+        }
+    ],
     "content": "We should work on this",
     "custom_fields": [],
     "date_created": null,
     "depends": [],
     "id": 1,
-    "last_updated": "<date>",
+    "last_updated": "<date>",
     "milestone": null,
     "priority": null,
     "private": false,

"""
        npatch = []
        for row in commit_patch.split("\n"):
            if row.startswith("Date:"):
                continue
            elif row.startswith("From "):
                row = row.split(" ", 2)[2]
            elif row.startswith("diff --git "):
                row = row.split(" ")
                row[2] = "a/123"
                row[3] = "b/456"
                row = " ".join(row)
            elif "Updated issue" in row:
                row = row.split()
                row[3] = "<hash>:"
                row = " ".join(row)
            elif "date_created" in row:
                t = row.split(": ")[0]
                row = "%s: null," % t
            elif "closed_at" in row:
                t = row.split(": ")[0]
                row = "%s: null," % t
            elif "closed_by" in row:
                continue
            elif row.startswith("index"):
                row = "index 458821a..77674a8"
            elif row.startswith("--- a/"):
                row = "--- a/123"
            elif row.startswith("+++ b/"):
                row = "+++ b/456"
            elif "last_updated" in row:
                t = row.split(": ")[0]
                row = '%s: "<date>",' % t
            npatch.append(row)
        commit_patch = "\n".join(npatch)
        # print commit_patch
        self.assertEqual(commit_patch, exp)

    def test_clean_git(self):
        """ Test the clean_git method of pagure.lib.git. """
        self.test_update_git()

        gitpath = os.path.join(
            self.path, "repos", "tickets", "test_ticket_repo.git"
        )
        gitrepo = pygit2.init_repository(gitpath, bare=True)

        # Get the uid of the ticket created
        commit = gitrepo.revparse_single("HEAD")
        patch = pagure.lib.git.commit_to_patch(gitrepo, commit)
        hash_file = None
        for row in patch.split("\n"):
            if row.startswith("+++ b/"):
                hash_file = row.split("+++ b/")[-1]
                break

        # The only file in git is the one of that ticket
        files = [entry.name for entry in commit.tree]
        self.assertEqual(files, [hash_file])

        repo = pagure.lib.query.get_authorized_project(
            self.session, "test_ticket_repo"
        )
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        pagure.lib.git.clean_git(repo, issue.repotype, issue.uid).get()

        # No more files in the git repo
        commit = gitrepo.revparse_single("HEAD")
        files = [entry.name for entry in commit.tree]
        self.assertEqual(files, [])

    @patch("pagure.lib.notify.send_email")
    def test_update_git_requests(self, email_f):
        """ Test the update_git of pagure.lib.git for pull-requests. """
        email_f.return_value = True

        # Create project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test_ticket_repo",
            description="test project for ticket",
            hook_token="aaabbbxxx",
        )
        self.session.add(item)
        self.session.commit()

        # Create repo
        self.gitrepo = os.path.join(
            self.path, "repos", "requests", "test_ticket_repo.git"
        )
        pygit2.init_repository(self.gitrepo, bare=True)

        # Create a PR to play with
        repo = pagure.lib.query.get_authorized_project(
            self.session, "test_ticket_repo"
        )
        # Create an issue to play with
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from="feature",
            repo_to=repo,
            branch_to="master",
            title="test PR",
            user="pingou",
            requestuid="foobar",
            requestid=None,
            status="Open",
            notify=True,
        )
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "test PR")

        request = repo.requests[0]
        self.assertEqual(request.title, "test PR")
        pagure.lib.git.update_git(request, request.project).get()

        repo = pygit2.Repository(self.gitrepo)
        commit = repo.revparse_single("HEAD")

        # Use patch to validate the repo
        patch = pagure.lib.git.commit_to_patch(repo, commit)
        exp = r"""Mon Sep 17 00:00:00 2001
From: pagure <pagure>
Subject: Updated pull-request <hash>: test PR


---

diff --git a/123 b/456
new file mode 100644
index 0000000..60f7480
--- /dev/null
+++ b/456
@@ -0,0 +1,147 @@
+{
+    "assignee": null,
+    "branch": "master",
+    "branch_from": "feature",
+    "cached_merge_status": "unknown",
+    "closed_at": null,
+    "closed_by": null,
+    "comments": [],
+    "commit_start": null,
+    "commit_stop": null,
+    "date_created": null,
+    "id": 1,
+    "initial_comment": null,
+    "last_updated": null,
+    "project": {
+        "access_groups": {
+            "admin": [],
+            "commit": [],
+            "ticket": []
+        },
+        "access_users": {
+            "admin": [],
+            "commit": [],
+            "owner": [
+                "pingou"
+            ],
+            "ticket": []
+        },
+        "close_status": [],
+        "custom_keys": [],
+        "date_created": null,
+        "date_modified": null,
+        "description": "test project for ticket",
+        "fullname": "test_ticket_repo",
+        "id": 1,
+        "milestones": {},
+        "name": "test_ticket_repo",
+        "namespace": null,
+        "parent": null,
+        "priorities": {},
+        "settings": {
+            "Enforce_signed-off_commits_in_pull-request": false,
+            "Minimum_score_to_merge_pull-request": -1,
+            "Only_assignee_can_merge_pull-request": false,
+            "Web-hooks": null,
+            "always_merge": false,
+            "disable_non_fast-forward_merges": false,
+            "fedmsg_notifications": true,
+            "issue_tracker": true,
+            "issue_tracker_read_only": false,
+            "issues_default_to_private": false,
+            "mqtt_notifications": true,
+            "notify_on_commit_flag": false,
+            "notify_on_pull-request_flag": false,
+            "open_metadata_access_to_all": false,
+            "project_documentation": false,
+            "pull_request_access_only": false,
+            "pull_requests": true,
+            "stomp_notifications": true
+        },
+        "tags": [],
+        "url_path": "test_ticket_repo",
+        "user": {
+            "default_email": "bar@pingou.com",
+            "emails": [
+                "bar@pingou.com",
+                "foo@pingou.com"
+            ],
+            "fullname": "PY C",
+            "name": "pingou"
+        }
+    },
+    "remote_git": null,
+    "repo_from": {
+        "access_groups": {
+            "admin": [],
+            "commit": [],
+            "ticket": []
+        },
+        "access_users": {
+            "admin": [],
+            "commit": [],
+            "owner": [
+                "pingou"
+            ],
+            "ticket": []
+        },
+        "close_status": [],
+        "custom_keys": [],
+        "date_created": null,
+        "date_modified": null,
+        "description": "test project for ticket",
+        "fullname": "test_ticket_repo",
+        "id": 1,
+        "milestones": {},
+        "name": "test_ticket_repo",
+        "namespace": null,
+        "parent": null,
+        "priorities": {},
+        "settings": {
+            "Enforce_signed-off_commits_in_pull-request": false,
+            "Minimum_score_to_merge_pull-request": -1,
+            "Only_assignee_can_merge_pull-request": false,
+            "Web-hooks": null,
+            "always_merge": false,
+            "disable_non_fast-forward_merges": false,
+            "fedmsg_notifications": true,
+            "issue_tracker": true,
+            "issue_tracker_read_only": false,
+            "issues_default_to_private": false,
+            "mqtt_notifications": true,
+            "notify_on_commit_flag": false,
+            "notify_on_pull-request_flag": false,
+            "open_metadata_access_to_all": false,
+            "project_documentation": false,
+            "pull_request_access_only": false,
+            "pull_requests": true,
+            "stomp_notifications": true
+        },
+        "tags": [],
+        "url_path": "test_ticket_repo",
+        "user": {
+            "default_email": "bar@pingou.com",
+            "emails": [
+                "bar@pingou.com",
+                "foo@pingou.com"
+            ],
+            "fullname": "PY C",
+            "name": "pingou"
+        }
+    },
+    "status": "Open",
+    "tags": [],
+    "threshold_reached": null,
+    "title": "test PR",
+    "uid": "foobar",
+    "updated_on": null,
+    "user": {
+        "default_email": "bar@pingou.com",
+        "emails": [
+            "bar@pingou.com",
+            "foo@pingou.com"
+        ],
+        "fullname": "PY C",
+        "name": "pingou"
+    }
+}
\ No newline at end of file

"""
        npatch = []
        for row in patch.split("\n"):
            if row.startswith("Date:"):
                continue
            elif row.startswith("From "):
                row = row.split(" ", 2)[2]
            elif row.startswith("diff --git "):
                row = row.split(" ")
                row[2] = "a/123"
                row[3] = "b/456"
                row = " ".join(row)
            elif "Updated pull-request" in row:
                row = row.split()
                row[3] = "<hash>:"
                row = " ".join(row)
            elif "date_created" in row:
                t = row.split(": ")[0]
                row = "%s: null," % t
            elif "date_modified" in row:
                t = row.split(": ")[0]
                row = "%s: null," % t
            elif "last_updated" in row:
                t = row.split(": ")[0]
                row = "%s: null," % t
            elif "updated_on" in row:
                t = row.split(": ")[0]
                row = "%s: null," % t
            elif row.startswith("index 00"):
                row = "index 0000000..60f7480"
            elif row.startswith("+++ b/"):
                row = "+++ b/456"
            npatch.append(row)
        patch = "\n".join(npatch)
        print(patch)
        self.assertEqual(patch, exp)

    def test_update_ticket_from_git_no_priority(self):
        """ Test the update_ticket_from_git method from pagure.lib.git. """
        tests.create_projects(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Before
        self.assertEqual(len(repo.issues), 0)
        self.assertEqual(repo.issues, [])

        data = {
            "status": "Open",
            "title": "foo",
            "comments": [],
            "content": "bar",
            "date_created": "1426500263",
            "user": {"name": "pingou", "emails": ["pingou@fedoraproject.org"]},
            "milestone": "Next Release",
            "priority": 1,
        }

        # Invalid project
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.git.update_ticket_from_git,
            self.session,
            reponame="foobar",
            namespace=None,
            username=None,
            issue_uid="foobar",
            json_data=data,
            agent="pingou",
        )

        # Create the issue
        data = {
            "status": "Open",
            "title": "foo",
            "comments": [],
            "content": "bar",
            "date_created": "1426500263",
            "user": {"name": "pingou", "emails": ["pingou@fedoraproject.org"]},
            "milestone": "Next Release",
        }

        pagure.lib.git.update_ticket_from_git(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            issue_uid="foobar",
            json_data=data,
            agent="pingou",
        )
        self.session.commit()

        # Edit the issue
        data = {
            "status": "Open",
            "title": "foo",
            "comments": [],
            "content": "bar",
            "date_created": "1426500263",
            "user": {"name": "pingou", "emails": ["pingou@fedoraproject.org"]},
            "milestone": "Next Release",
            "priority": 1,
        }

        pagure.lib.git.update_ticket_from_git(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            issue_uid="foobar",
            json_data=data,
            agent="pingou",
        )
        self.session.commit()

        # Data contained a priority but not the project, so bailing
        self.assertEqual(len(repo.issues), 1)
        self.assertEqual(repo.issues[0].id, 1)
        self.assertEqual(repo.issues[0].uid, "foobar")
        self.assertEqual(repo.issues[0].title, "foo")
        self.assertEqual(repo.issues[0].depending_text, [])
        self.assertEqual(repo.issues[0].blocking_text, [])
        self.assertEqual(repo.issues[0].milestone, "Next Release")
        self.assertEqual(repo.issues[0].priority, None)
        self.assertEqual(
            repo.milestones, {"Next Release": {"active": True, "date": None}}
        )

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_update_ticket_from_git_close_ticket(self):
        """ Test the update_ticket_from_git method from pagure.lib.git. """
        tests.create_projects(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Before
        self.assertEqual(len(repo.issues), 0)
        self.assertEqual(repo.issues, [])

        # Create the issue
        data = {
            "status": "Open",
            "title": "foo",
            "comments": [],
            "content": "bar",
            "date_created": "1426500263",
            "user": {"name": "foo", "emails": ["foo@fedoraproject.org"]},
            "milestone": "Next Release",
        }

        pagure.lib.git.update_ticket_from_git(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            issue_uid="foobar",
            json_data=data,
            agent="pingou",
        )
        self.session.commit()

        # Edit the issue
        data = {
            "status": "Closed",
            "close_status": "Fixed",
            "title": "foo",
            "comments": [],
            "content": "bar",
            "date_created": "1426500263",
            "user": {"name": "foo", "emails": ["foo@fedoraproject.org"]},
            "milestone": "Next Release",
        }

        pagure.lib.git.update_ticket_from_git(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            issue_uid="foobar",
            json_data=data,
            agent="pingou",
        )
        self.session.commit()

        self.assertEqual(len(repo.issues), 1)
        self.assertEqual(repo.issues[0].id, 1)
        self.assertEqual(repo.issues[0].uid, "foobar")
        self.assertEqual(repo.issues[0].title, "foo")
        self.assertEqual(repo.issues[0].depending_text, [])
        self.assertEqual(repo.issues[0].blocking_text, [])
        self.assertEqual(repo.issues[0].milestone, "Next Release")
        self.assertEqual(repo.issues[0].priority, None)
        self.assertEqual(
            repo.milestones, {"Next Release": {"active": True, "date": None}}
        )
        self.assertEqual(repo.issues[0].status, "Closed")
        self.assertEqual(repo.issues[0].close_status, "Fixed")
        self.assertIsNotNone(repo.issues[0].closed_at)
        self.assertEqual(
            repo.issues[0].comments[-1].comment,
            "**Metadata Update from @pingou**:\n"
            "- Issue close_status updated to: Fixed\n"
            "- Issue status updated to: Closed (was: Open)",
        )

    def test_update_ticket_from_git(self):
        """ Test the update_ticket_from_git method from pagure.lib.git. """
        tests.create_projects(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        # Set some priorities to the project
        repo.priorities = {"1": "High", "2": "Normal"}
        self.session.add(repo)
        self.session.commit()

        # Before
        self.assertEqual(len(repo.issues), 0)
        self.assertEqual(repo.issues, [])

        data = {
            "status": "Open",
            "title": "foo",
            "comments": [],
            "content": "bar",
            "date_created": "1426500263",
            "user": {"name": "pingou", "emails": ["pingou@fedoraproject.org"]},
            "milestone": "Next Release",
            "priority": 1,
        }

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.git.update_ticket_from_git,
            self.session,
            reponame="foobar",
            namespace=None,
            username=None,
            issue_uid="foobar",
            json_data=data,
            agent="pingou",
        )

        pagure.lib.git.update_ticket_from_git(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            issue_uid="foobar",
            json_data=data,
            agent="pingou",
        )
        self.session.commit()

        # After 1 insertion
        self.assertEqual(len(repo.issues), 1)
        self.assertEqual(repo.issues[0].id, 1)
        self.assertEqual(repo.issues[0].uid, "foobar")
        self.assertEqual(repo.issues[0].title, "foo")
        self.assertEqual(repo.issues[0].depending_text, [])
        self.assertEqual(repo.issues[0].blocking_text, [])
        self.assertEqual(repo.issues[0].milestone, "Next Release")
        self.assertEqual(repo.issues[0].priority, 1)
        self.assertIsNone(repo.issues[0].closed_at)
        self.assertEqual(
            repo.milestones, {"Next Release": {"active": True, "date": None}}
        )

        data["title"] = "fake issue for tests"
        pagure.lib.git.update_ticket_from_git(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            issue_uid="foobar",
            json_data=data,
            agent="pingou",
        )
        self.session.commit()

        # After edit
        self.assertEqual(len(repo.issues), 1)
        self.assertEqual(repo.issues[0].id, 1)
        self.assertEqual(repo.issues[0].uid, "foobar")
        self.assertEqual(repo.issues[0].title, "fake issue for tests")
        self.assertEqual(repo.issues[0].depending_text, [])
        self.assertEqual(repo.issues[0].blocking_text, [])
        self.assertEqual(repo.issues[0].priority, 1)
        self.assertIsNone(repo.issues[0].closed_at)

        data = {
            "status": "Open",
            "title": "Rename pagure",
            "private": False,
            "content": "This is too much of a conflict with the book",
            "user": {
                "fullname": "Pierre-YvesChibon",
                "name": "pingou",
                "default_email": "pingou@fedoraproject.org",
                "emails": ["pingou@fedoraproject.org"],
            },
            "id": 20,
            "blocks": [1],
            "depends": [3, 4],
            "date_created": "1426595224",
            "milestone": "Future",
            "priority": 1,
            "comments": [
                {
                    "comment": "Nirik:\r\n\r\n- sourceforge++ \r\n- "
                    "gitmaker\r\n- mastergit \r\n- hostomatic\r\n- "
                    "gitcorp\r\n- git-keiretsu \r\n- gitbuffet\r\n- "
                    "cogitator\r\n- cogitate\r\n\r\nrandomuser:\r\n\r\n- "
                    "COLLABORATRON5000\r\n- git-sm\\u00f6rg\\u00e5sbord\r\n- "
                    "thislittlegittywenttomarket\r\n- git-o-rama\r\n- "
                    "gitsundheit",
                    "date_created": "1426595224",
                    "id": 250,
                    "parent": None,
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": ["pingou@fedoraproject.org"],
                    },
                },
                {
                    "comment": "Nirik:\r\n\r\n- sourceforge++ \r\n- "
                    "gitmaker\r\n- mastergit \r\n- hostomatic\r\n- "
                    "gitcorp\r\n- git-keiretsu \r\n- gitbuffet\r\n- "
                    "cogitator\r\n- cogitate\r\n\r\nrandomuser:\r\n\r\n- "
                    "COLLABORATRON5000\r\n- git-sm\\u00f6rg\\u00e5sbord\r\n- "
                    "thislittlegittywenttomarket\r\n- git-o-rama\r\n- "
                    "gitsundheit",
                    "date_created": "1426595340",
                    "id": 324,
                    "parent": None,
                    "user": {
                        "fullname": "Ralph Bean",
                        "name": "ralph",
                        "default_email": "ralph@fedoraproject.org",
                        "emails": ["ralph@fedoraproject.org"],
                    },
                },
            ],
        }

        pagure.lib.git.update_ticket_from_git(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            issue_uid="foobar2",
            json_data=data,
            agent="pingou",
        )

        # After second insertion
        self.assertEqual(len(repo.issues), 2)
        self.assertEqual(repo.issues[0].uid, "foobar")
        self.assertEqual(repo.issues[0].title, "fake issue for tests")
        self.assertEqual(repo.issues[0].depending_text, [20])
        self.assertEqual(repo.issues[0].blocking_text, [])
        self.assertIsNone(repo.issues[0].closed_at)
        # New one
        self.assertEqual(repo.issues[1].uid, "foobar2")
        self.assertEqual(repo.issues[1].title, "Rename pagure")
        self.assertEqual(repo.issues[1].depending_text, [])
        self.assertEqual(repo.issues[1].blocking_text, [1])
        self.assertEqual(repo.issues[1].milestone, "Future")
        self.assertIsNone(repo.issues[1].closed_at)
        self.assertDictEqual(
            repo.milestones,
            {
                "Future": {"active": True, "date": None},
                "Next Release": {"active": True, "date": None},
            },
        )

    def test_update_request_from_git(self):
        """ Test the update_request_from_git method from pagure.lib.git. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        repo = pagure.lib.query._get_project(self.session, "test")
        namespaced_repo = pagure.lib.query._get_project(
            self.session, "test3", namespace="somenamespace"
        )

        # Before
        self.assertEqual(len(repo.requests), 0)
        self.assertEqual(repo.requests, [])
        self.assertEqual(len(namespaced_repo.requests), 0)
        self.assertEqual(namespaced_repo.requests, [])

        data = {
            "status": True,
            "uid": "d4182a2ac2d541d884742d3037c26e56",
            "project": {
                "custom_keys": [],
                "parent": None,
                "settings": {
                    "issue_tracker": True,
                    "project_documentation": True,
                    "pull_requests": True,
                },
                "name": "test",
                "date_created": "1426500194",
                "tags": [],
                "user": {
                    "fullname": "Pierre-YvesChibon",
                    "name": "pingou",
                    "default_email": "pingou@fedoraproject.org",
                    "emails": ["pingou@fedoraproject.org"],
                },
                "id": 1,
                "description": "test project",
            },
            "commit_stop": "eface8e13bc2a08a3fb22af9a72a8c90e36b8b89",
            "user": {
                "fullname": "Pierre-YvesChibon",
                "name": "pingou",
                "default_email": "pingou@fedoraproject.org",
                "emails": ["pingou@fedoraproject.org"],
            },
            "id": 7,
            "comments": [
                {
                    "comment": "really?",
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": ["pingou@fedoraproject.org"],
                    },
                    "parent": None,
                    "date_created": "1426843778",
                    "commit": "fa72f315373ec5f98f2b08c8ffae3645c97aaad2",
                    "line": 5,
                    "id": 1,
                    "filename": "test",
                },
                {
                    "comment": "Again ?",
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": ["pingou@fedoraproject.org"],
                    },
                    "parent": None,
                    "date_created": "1426866781",
                    "commit": "94ebaf900161394059478fd88aec30e59092a1d7",
                    "line": 5,
                    "id": 2,
                    "filename": "test2",
                },
                {
                    "comment": "Should be fine in fact",
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": ["pingou@fedoraproject.org"],
                    },
                    "parent": None,
                    "date_created": "1426866950",
                    "commit": "94ebaf900161394059478fd88aec30e59092a1d7",
                    "line": 5,
                    "id": 3,
                    "filename": "test2",
                },
            ],
            "branch_from": "master",
            "title": "test request",
            "commit_start": "788efeaaf86bde8618f594a8181abb402e1dd904",
            "repo_from": {
                "parent": {
                    "custom_keys": [],
                    "parent": None,
                    "name": "test",
                    "date_created": "1426500194",
                    "tags": [],
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": ["pingou@fedoraproject.org"],
                    },
                    "settings": {
                        "issue_tracker": True,
                        "project_documentation": True,
                        "pull_requests": True,
                    },
                    "id": 1,
                    "description": "test project",
                },
                "settings": {
                    "issue_tracker": True,
                    "project_documentation": True,
                    "pull_requests": True,
                },
                "name": "test",
                "date_created": "1426843440",
                "custom_keys": [],
                "tags": [],
                "user": {
                    "fullname": "fake user",
                    "name": "fake",
                    "default_email": "fake@fedoraproject.org",
                    "emails": ["fake@fedoraproject.org"],
                },
                "id": 6,
                "description": "test project",
            },
            "branch": "master",
            "date_created": "1426843732",
        }

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.git.update_request_from_git,
            self.session,
            reponame="foobar",
            namespace=None,
            username=None,
            request_uid="d4182a2ac2d541d884742d3037c26e56",
            json_data=data,
        )

        pagure.lib.git.update_request_from_git(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            request_uid="d4182a2ac2d541d884742d3037c26e56",
            json_data=data,
        )
        self.session.commit()

        # After 1 st insertion
        self.assertEqual(len(repo.requests), 1)
        self.assertEqual(repo.requests[0].id, 7)
        self.assertEqual(
            repo.requests[0].uid, "d4182a2ac2d541d884742d3037c26e56"
        )
        self.assertEqual(repo.requests[0].title, "test request")
        self.assertEqual(len(repo.requests[0].comments), 3)

        data = {
            "status": True,
            "uid": "d4182a2ac2d541d884742d3037c26e57",
            "project": {
                "parent": None,
                "name": "test",
                "custom_keys": [],
                "date_created": "1426500194",
                "tags": [],
                "user": {
                    "fullname": "Pierre-YvesChibon",
                    "name": "pingou",
                    "default_email": "pingou@fedoraproject.org",
                    "emails": ["pingou@fedoraproject.org"],
                },
                "settings": {
                    "issue_tracker": True,
                    "project_documentation": True,
                    "pull_requests": True,
                },
                "id": 1,
                "description": "test project",
            },
            "commit_stop": "eface8e13bc2a08a3fb22af9a72a8c90e36b8b89",
            "user": {
                "fullname": "Pierre-YvesChibon",
                "name": "pingou",
                "default_email": "pingou@fedoraproject.org",
                "emails": ["pingou@fedoraproject.org"],
            },
            "id": 4,
            "comments": [],
            "branch_from": "master",
            "title": "test request #2",
            "commit_start": "788efeaaf86bde8618f594a8181abb402e1dd904",
            "repo_from": {
                "parent": {
                    "parent": None,
                    "name": "test",
                    "custom_keys": [],
                    "date_created": "1426500194",
                    "tags": [],
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": ["pingou@fedoraproject.org"],
                    },
                    "settings": {
                        "issue_tracker": True,
                        "project_documentation": True,
                        "pull_requests": True,
                    },
                    "id": 1,
                    "description": "test project",
                },
                "settings": {
                    "issue_tracker": True,
                    "project_documentation": True,
                    "pull_requests": True,
                },
                "name": "test",
                "date_created": "1426843440",
                "custom_keys": [],
                "tags": [],
                "user": {
                    "fullname": "fake user",
                    "name": "fake",
                    "default_email": "fake@fedoraproject.org",
                    "emails": ["fake@fedoraproject.org"],
                },
                "project_docs": True,
                "id": 6,
                "description": "test project",
            },
            "branch": "master",
            "date_created": "1426843745",
        }

        pagure.lib.git.update_request_from_git(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            request_uid="d4182a2ac2d541d884742d3037c26e57",
            json_data=data,
        )
        self.session.commit()

        # After 2 nd insertion
        self.assertEqual(len(repo.requests), 2)
        self.assertEqual(repo.requests[0].id, 7)
        self.assertEqual(
            repo.requests[0].uid, "d4182a2ac2d541d884742d3037c26e56"
        )
        self.assertEqual(repo.requests[0].title, "test request")
        self.assertEqual(len(repo.requests[0].comments), 3)
        # 2 entry
        self.assertEqual(repo.requests[1].id, 4)
        self.assertEqual(
            repo.requests[1].uid, "d4182a2ac2d541d884742d3037c26e57"
        )
        self.assertEqual(repo.requests[1].title, "test request #2")
        self.assertEqual(len(repo.requests[1].comments), 0)

        data = {
            "status": True,
            "uid": "d4182a2ac2d541d884742d3037c26e58",
            "project": {
                "parent": None,
                "name": "test3",
                "custom_keys": [],
                "namespace": "somenamespace",
                "date_created": "1426500194",
                "tags": [],
                "user": {
                    "fullname": "Pierre-YvesChibon",
                    "name": "pingou",
                    "default_email": "pingou@fedoraproject.org",
                    "emails": ["pingou@fedoraproject.org"],
                },
                "settings": {
                    "issue_tracker": True,
                    "project_documentation": True,
                    "pull_requests": True,
                },
                "id": 3,
                "description": "namespaced test project",
            },
            "commit_stop": "eface8e13bc2a08a3fb22af9a72a8c90e36b8b89",
            "user": {
                "fullname": "Pierre-YvesChibon",
                "name": "pingou",
                "default_email": "pingou@fedoraproject.org",
                "emails": ["pingou@fedoraproject.org"],
            },
            "id": 5,
            "comments": [],
            "branch_from": "master",
            "title": "test request to namespaced repo",
            "commit_start": "788efeaaf86bde8618f594a8181abb402e1dd904",
            "repo_from": {
                "parent": {
                    "parent": None,
                    "name": "test",
                    "custom_keys": [],
                    "date_created": "1426500194",
                    "tags": [],
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": ["pingou@fedoraproject.org"],
                    },
                    "settings": {
                        "issue_tracker": True,
                        "project_documentation": True,
                        "pull_requests": True,
                    },
                    "id": 1,
                    "description": "test project",
                },
                "settings": {
                    "issue_tracker": True,
                    "project_documentation": True,
                    "pull_requests": True,
                },
                "name": "test",
                "date_created": "1426843440",
                "custom_keys": [],
                "tags": [],
                "user": {
                    "fullname": "fake user",
                    "name": "fake",
                    "default_email": "fake@fedoraproject.org",
                    "emails": ["fake@fedoraproject.org"],
                },
                "project_docs": True,
                "id": 6,
                "description": "test project",
            },
            "branch": "master",
            "date_created": "1426843745",
        }
        pagure.lib.git.update_request_from_git(
            self.session,
            reponame="test3",
            namespace="somenamespace",
            username=None,
            request_uid="d4182a2ac2d541d884742d3037c26e58",
            json_data=data,
        )
        self.session.commit()

        self.assertEqual(len(namespaced_repo.requests), 1)
        self.assertEqual(namespaced_repo.requests[0].id, 5)
        self.assertEqual(
            namespaced_repo.requests[0].uid, "d4182a2ac2d541d884742d3037c26e58"
        )
        self.assertEqual(
            namespaced_repo.requests[0].title,
            "test request to namespaced repo",
        )

    def test_update_request_from_git(self):
        """ Test the update_request_from_git method from pagure.lib.git. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        repo = pagure.lib.query._get_project(self.session, "test")
        namespaced_repo = pagure.lib.query._get_project(
            self.session, "test3", namespace="somenamespace"
        )

        # Before
        self.assertEqual(len(repo.requests), 0)
        self.assertEqual(repo.requests, [])
        self.assertEqual(len(namespaced_repo.requests), 0)
        self.assertEqual(namespaced_repo.requests, [])

        data = {
            "status": True,
            "uid": "d4182a2ac2d541d884742d3037c26e57",
            "project": {
                "parent": None,
                "name": "test",
                "custom_keys": [],
                "date_created": "1426500194",
                "tags": [],
                "user": {
                    "fullname": "Pierre-YvesChibon",
                    "name": "pingou",
                    "default_email": "pingou@fedoraproject.org",
                    "emails": ["pingou@fedoraproject.org"],
                },
                "settings": {
                    "issue_tracker": True,
                    "project_documentation": True,
                    "pull_requests": True,
                },
                "id": 1,
                "description": "test project",
            },
            "commit_stop": "eface8e13bc2a08a3fb22af9a72a8c90e36b8b89",
            "user": {
                "fullname": "Pierre-YvesChibon",
                "name": "pingou",
                "default_email": "pingou@fedoraproject.org",
                "emails": ["pingou@fedoraproject.org"],
            },
            "id": 4,
            "comments": [],
            "branch_from": "master",
            "title": "test request #2",
            "commit_start": "788efeaaf86bde8618f594a8181abb402e1dd904",
            "repo_from": {
                "parent": {
                    "parent": None,
                    "name": "test",
                    "custom_keys": [],
                    "date_created": "1426500194",
                    "tags": [],
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": ["pingou@fedoraproject.org"],
                    },
                    "settings": {
                        "issue_tracker": True,
                        "project_documentation": True,
                        "pull_requests": True,
                    },
                    "id": 1,
                    "description": "test project",
                },
                "settings": {
                    "issue_tracker": True,
                    "project_documentation": True,
                    "pull_requests": True,
                },
                "name": "test",
                "date_created": "1426843440",
                "custom_keys": [],
                "tags": [],
                "user": {
                    "fullname": "fake user",
                    "name": "fake",
                    "default_email": "fake@fedoraproject.org",
                    "emails": ["fake@fedoraproject.org"],
                },
                "project_docs": True,
                "id": 6,
                "description": "test project",
            },
            "branch": "master",
            "date_created": "1426843745",
            "tags": ["WIP", "core"],
        }

        pagure.lib.git.update_request_from_git(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            request_uid="d4182a2ac2d541d884742d3037c26e57",
            json_data=data,
        )
        self.session.commit()

        # After insertion
        self.assertEqual(repo.requests[0].id, 4)
        self.assertEqual(
            repo.requests[0].uid, "d4182a2ac2d541d884742d3037c26e57"
        )
        self.assertEqual(repo.requests[0].title, "test request #2")
        self.assertEqual(len(repo.requests[0].comments), 0)
        self.assertEqual(repo.requests[0].tags_text, ["WIP", "core"])

    def test_read_git_lines(self):
        """ Test the read_git_lines method of pagure.lib.git. """
        self.test_update_git()

        gitrepo = os.path.join(
            self.path, "repos", "tickets", "test_ticket_repo.git"
        )
        output = pagure.lib.git.read_git_lines(
            ["log", "-1", "--pretty='%s'"], gitrepo
        )
        self.assertEqual(len(output), 1)
        self.assertTrue(output[0].startswith("'Updated issue "))
        self.assertTrue(output[0].endswith(": Test issue'"))

        # Keeping the new line symbol
        output = pagure.lib.git.read_git_lines(
            ["log", "-1", "--pretty='%s'"], gitrepo, keepends=True
        )
        self.assertEqual(len(output), 1)
        self.assertTrue(output[0].endswith(": Test issue'\n"))

    def test_get_revs_between(self):
        """ Test the get_revs_between method of pagure.lib.git. """

        self.test_update_git()

        gitrepo = os.path.join(
            self.path, "repos", "tickets", "test_ticket_repo.git"
        )
        output = pagure.lib.git.read_git_lines(
            ["log", "-3", "--pretty='%H'"], gitrepo
        )
        self.assertEqual(len(output), 2)
        from_hash = output[1].replace("'", "")

        # Case 1, repo BASE is null and HEAD is equal to from_hash
        to_hash = "0"
        output1 = pagure.lib.git.get_revs_between(
            to_hash, from_hash, gitrepo, "refs/heads/master"
        )
        self.assertEqual(output1, [from_hash])

        # Case 2, get revs between two commits (to_hash, from_hash)
        to_hash = output[0].replace("'", "")
        output2 = pagure.lib.git.get_revs_between(
            to_hash, from_hash, gitrepo, "refs/heads/master"
        )
        self.assertEqual(output2, [to_hash])

        # Case 3, get revs between two commits (from_hash, to_hash)
        output3 = pagure.lib.git.get_revs_between(
            from_hash, to_hash, gitrepo, "refs/heads/master"
        )
        self.assertEqual(output3, [to_hash])

        # Case 4, get revs between two commits on two different branches
        newgitrepo = tempfile.mkdtemp(prefix="pagure-")
        newrepo = pygit2.clone_repository(gitrepo, newgitrepo)
        newrepo.create_branch("feature", newrepo.head.peel())

        with open(os.path.join(newgitrepo, "sources"), "w") as stream:
            stream.write("foo\n bar")
        newrepo.index.add("sources")
        newrepo.index.write()

        # Commits the files added
        tree = newrepo.index.write_tree()
        author = pygit2.Signature("Alice Author", "alice@authors.tld")
        committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
        newrepo.create_commit(
            "refs/heads/feature",  # the name of the reference to update
            author,
            committer,
            "Add sources file for testing",
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [to_hash],
        )
        branch_commit = newrepo.revparse_single("refs/heads/feature")

        # Push to origin
        ori_remote = newrepo.remotes[0]
        PagureRepo.push(ori_remote, "refs/heads/feature")

        # Remove the clone
        shutil.rmtree(newgitrepo)

        output4 = pagure.lib.git.get_revs_between(
            "0", branch_commit.oid.hex, gitrepo, "refs/heads/feature"
        )
        self.assertEqual(output4, [branch_commit.oid.hex])

    def test_get_author(self):
        """ Test the get_author method of pagure.lib.git. """

        self.test_update_git()

        gitrepo = os.path.join(
            self.path, "repos", "tickets", "test_ticket_repo.git"
        )
        output = pagure.lib.git.read_git_lines(
            ["log", "-3", "--pretty='%H'"], gitrepo
        )
        self.assertEqual(len(output), 2)
        for githash in output:
            githash = githash.replace("'", "")
            output = pagure.lib.git.get_author(githash, gitrepo)
            self.assertEqual(output, "pagure")

    def get_author_email(self):
        """ Test the get_author_email method of pagure.lib.git. """

        self.test_update_git()

        gitrepo = os.path.join(self.path, "tickets", "test_ticket_repo.git")
        output = pagure.lib.git.read_git_lines(
            ["log", "-3", "--pretty='%H'"], gitrepo
        )
        self.assertEqual(len(output), 2)
        for githash in output:
            githash = githash.replace("'", "")
            output = pagure.lib.git.get_author_email(githash, gitrepo)
            self.assertEqual(output, "pagure")

    def test_get_repo_name(self):
        """ Test the get_repo_name method of pagure.lib.git. """

        def runtest(reponame, *path):
            gitrepo = os.path.join(self.path, "repos", *path)
            os.makedirs(gitrepo)
            repo_name = pagure.lib.git.get_repo_name(gitrepo)
            self.assertEqual(repo_name, reponame)

        runtest("test_ticket_repo", "tickets", "test_ticket_repo.git")
        runtest("test", "test.git")
        runtest("foo.test", "foo.test.git")

    def test_get_username(self):
        """ Test the get_username method of pagure.lib.git. """

        def runtest(username, *path):
            gitrepo = os.path.join(self.path, "repos", *path)
            os.makedirs(gitrepo)
            repo_username = pagure.lib.git.get_username(gitrepo)
            self.assertEqual(repo_username, username)

        runtest(None, "tickets", "test_ticket_repo.git")
        runtest(None, "test.git")
        runtest(None, "foo.test.git")
        runtest("pingou", "forks", "pingou", "foo.test.git")
        runtest("pingou", "forks", "pingou", "bar/foo.test.git")

    def test_get_repo_namespace(self):
        """ Test the get_repo_namespace method of pagure.lib.git. """

        def runtest(namespace, *path):
            gitrepo = os.path.join(self.path, "repos", *path)
            if not os.path.exists(gitrepo):
                os.makedirs(gitrepo)
            repo_namespace = pagure.lib.git.get_repo_namespace(gitrepo)
            self.assertEqual(repo_namespace, namespace)

        runtest(None, "test_ticket_repo.git")
        runtest("foo/bar/baz", "foo", "bar", "baz", "test.git")
        runtest(None, "foo.test.git")
        runtest(None, "forks", "user", "foo.test.git")
        runtest("bar", "forks", "user", "bar", "foo.test.git")
        runtest("ns/bar", "forks", "user", "ns", "bar", "foo.test.git")
        runtest("bar", "forks", "user", "bar", "foo.test.git")

    def test_update_custom_fields_from_json(self):
        """ Test the update_custom_fields_from_json method of lib.git """

        tests.create_projects(self.session)
        repo = pagure.lib.query._get_project(self.session, "test")

        # Create issues to play with
        pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
            issue_uid="someuid",
        )
        self.session.commit()

        issue = pagure.lib.query.get_issue_by_uid(self.session, "someuid")

        # Fake json data, currently without custom_fields
        # This should bring no new custom_fields to the issue
        json_data = {
            "status": "Open",
            "title": "Test issue",
            "private": False,
            "content": "We should work on this",
            "user": {
                "fullname": "PY C",
                "name": "pingou",
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com"],
            },
            "id": 1,
            "blocks": [],
            "depends": [],
            "date_created": "1234567",
            "comments": [],
        }

        pagure.lib.git.update_custom_field_from_json(
            self.session, repo, issue, json_data
        )

        updated_issue = pagure.lib.query.get_issue_by_uid(
            self.session, "someuid"
        )

        self.assertEqual(updated_issue.to_json().get("custom_fields"), [])
        custom_fields = [
            {
                "name": "custom1",
                "key_type": "text",
                "value": "value1",
                "key_data": None,
            },
            {
                "name": "custom2",
                "key_type": "text",
                "value": "value2",
                "key_data": None,
            },
        ]

        # Again, Fake the json data but, with custom_fields in it
        # The updated issue should have the custom_fields as
        # was in the json_data
        json_data = {
            "status": "Open",
            "title": "Test issue",
            "private": False,
            "content": "We should work on this",
            "user": {
                "fullname": "PY C",
                "name": "pingou",
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com"],
            },
            "id": 1,
            "blocks": [],
            "depends": [],
            "date_created": "1234567",
            "comments": [],
            "custom_fields": custom_fields,
        }

        pagure.lib.git.update_custom_field_from_json(
            self.session, repo, issue, json_data
        )

        updated_issue = pagure.lib.query.get_issue_by_uid(
            self.session, "someuid"
        )

        custom_fields_of_issue = updated_issue.to_json().get("custom_fields")
        self.assertEqual(custom_fields_of_issue, custom_fields)

    @patch("pagure.lib.notify.send_email")
    @patch("pagure.lib.git.update_git")
    def test_merge_pull_request_no_master(self, email_f, up_git):
        """ Test the merge_pull_request function when there are no master
        branch in the repo. """
        email_f.return_value = True
        up_git.return_value = True

        gitfolder = os.path.join(self.path, "repos")
        docfolder = os.path.join(self.path, "docs")
        ticketfolder = os.path.join(self.path, "tickets")
        requestfolder = os.path.join(self.path, "requests")

        # Create project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test",
            description="test project",
            hook_token="aaabbbwww",
        )
        self.session.add(item)
        self.session.commit()

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        gitrepo = os.path.join(gitfolder, repo.path)
        docrepo = os.path.join(docfolder, repo.path)
        ticketrepo = os.path.join(ticketfolder, repo.path)
        requestrepo = os.path.join(requestfolder, repo.path)
        os.makedirs(os.path.join(self.path, "repos", "forks", "foo"))

        self.gitrepo = os.path.join(self.path, "repos", "test.git")
        os.makedirs(self.gitrepo)
        repo_obj = pygit2.init_repository(self.gitrepo, bare=True)

        # Fork the project
        task = pagure.lib.query.fork_project(
            session=self.session, user="foo", repo=repo
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {
                "endpoint": "ui_ns.view_repo",
                "repo": "test",
                "username": "foo",
                "namespace": None,
            },
        )

        # Create repo, with some content
        self.gitrepo = os.path.join(
            self.path, "repos", "forks", "foo", "test.git"
        )
        tests.add_content_git_repo(self.gitrepo, branch="feature")

        fork_repo = pagure.lib.query.get_authorized_project(
            self.session, "test", user="foo"
        )
        # Create a PR to play with
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=fork_repo,
            branch_from="feature",
            repo_to=repo,
            branch_to="master",
            title="test PR",
            user="pingou",
            requestuid="foobar",
            requestid=None,
            status="Open",
            notify=True,
        )
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "test PR")

        # `master` branch not found
        msg = pagure.lib.git.merge_pull_request(
            self.session, request=req, username="pingou", domerge=False
        )
        self.assertEqual(msg, "FFORWARD")

    @patch("pagure.lib.notify.send_email")
    @patch("pagure.lib.git.update_git")
    def test_merge_pull_request_closed(self, email_f, up_git):
        """ Test the merge_pull_request function when the PR was already
        closed/merged. """
        email_f.return_value = True
        up_git.return_value = True

        gitfolder = os.path.join(self.path, "repos")
        docfolder = os.path.join(self.path, "docs")
        ticketfolder = os.path.join(self.path, "tickets")
        requestfolder = os.path.join(self.path, "requests")

        # Create project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test",
            description="test project",
            hook_token="aaabbbwww",
        )
        self.session.add(item)
        self.session.commit()

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        os.makedirs(os.path.join(self.path, "repos", "forks", "foo"))

        self.gitrepo = os.path.join(self.path, "repos", "test.git")
        os.makedirs(self.gitrepo)
        repo_obj = pygit2.init_repository(self.gitrepo, bare=True)
        tests.add_content_git_repo(self.gitrepo, branch="master")

        # Fork the project
        task = pagure.lib.query.fork_project(
            session=self.session, user="foo", repo=repo
        )
        self.session.commit()
        self.assertEqual(
            task.get(),
            {
                "endpoint": "ui_ns.view_repo",
                "repo": "test",
                "username": "foo",
                "namespace": None,
            },
        )

        # Create repo, with some content
        self.gitrepo = os.path.join(
            self.path, "repos", "forks", "foo", "test.git"
        )
        tests.add_content_git_repo(self.gitrepo, branch="feature")

        fork_repo = pagure.lib.query.get_authorized_project(
            self.session, "test", user="foo"
        )
        # Create a PR to play with
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=fork_repo,
            branch_from="feature",
            repo_to=repo,
            branch_to="master",
            title="test PR",
            user="pingou",
            requestuid="foobar",
            requestid=None,
            status="Open",
            notify=True,
        )
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "test PR")

        # Close the PR before we ask to merge it
        req.status = "Closed"
        req.closed_by_id = 2  # id:2 == foo
        req.closed_at = datetime.datetime(2017, 10, 20, 12, 32, 10)
        self.session.add(req)
        self.session.commit()

        # PR already closed
        six.assertRaisesRegex(
            self,
            pagure.exceptions.PagureException,
            "This pull-request was merged or closed by foo",
            pagure.lib.git.merge_pull_request,
            self.session,
            request=req,
            username="pingou",
            domerge=False,
        )

    @patch("subprocess.Popen")
    def test_generate_gitolite_acls(self, popen):
        """ Test calling generate_gitolite_acls. """
        pagure.SESSION = self.session
        pagure.lib.git.SESSION = self.session
        pagure.config.config["GITOLITE_HOME"] = "/tmp"

        proc = MagicMock()
        proc.communicate.return_value = (1, 2)
        proc.returncode = 0
        popen.return_value = proc
        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.generate_acls(project=None)
        popen.assert_called_with(
            "HOME=/tmp gitolite compile && "
            "HOME=/tmp gitolite trigger POST_COMPILE",
            cwd="/tmp",
            shell=True,
            stderr=-1,
            stdout=-1,
        )

    def test_is_forced_push_new_branch(self):
        self.assertFalse(
            pagure.lib.git.is_forced_push(
                "0000000000000000000000000000000000000000",
                "^0e6e0b6c931d65ee22f67205a53933d841c6eeff",
                "path/is/not/important",
            )
        )

    @patch("pagure.utils.get_repo_path")
    def test_update_pull_ref(self, get_repo_path):
        fake_pr = MagicMock()
        fake_pr.uid = "1234567"
        fake_pr.branch_from = "master"
        fake_pr.id = 6
        fake_pr.user = MagicMock()
        fake_pr.user.user = "pingou"
        fake_pr.project = "doesnt_matter_mocked_out"
        projects = tests.create_projects_git(
            os.path.join(self.path, "repos"), bare=True
        )
        tests.add_content_git_repo(projects[0])
        tests.add_content_git_repo(projects[1])
        orig = pygit2.Repository(projects[0])
        fork = pygit2.Repository(projects[1])
        get_repo_path.return_value = projects[0]

        # make sure that creating works the first time
        pagure.lib.git.update_pull_ref(fake_pr, fork)
        oldhex = fork.references["refs/heads/master"].peel().hex
        self.assertEqual(
            orig.references["refs/pull/6/head"].peel().hex, oldhex
        )

        # make sure that updating works correctly
        tests.add_content_git_repo(projects[1], append="foobar")
        newhex = fork.references["refs/heads/master"].peel().hex
        self.assertNotEqual(oldhex, newhex)
        pagure.lib.git.update_pull_ref(fake_pr, fork)
        self.assertEqual(
            orig.references["refs/pull/6/head"].peel().hex, newhex
        )

        # make sure the function works fine even if there's a leftover
        # ref from previous failed run of the function
        with patch("pygit2.remote.RemoteCollection.delete"):
            pagure.lib.git.update_pull_ref(fake_pr, fork)
        self.assertIsNotNone(fork.remotes["pingou_1234567"])
        tests.add_content_git_repo(projects[1], append="foobarbaz")
        newesthex = fork.references["refs/heads/master"].peel().hex
        self.assertNotEqual(newhex, newesthex)
        pagure.lib.git.update_pull_ref(fake_pr, fork)
        self.assertEqual(
            orig.references["refs/pull/6/head"].peel().hex, newesthex
        )


class PagureLibGitCommitToPatchtests(tests.Modeltests):
    """ Tests for pagure.lib.git """

    maxDiff = None

    def setUp(self):
        """ Set up the environment for the tests. """
        super(PagureLibGitCommitToPatchtests, self).setUp()

        # Create a git repo to play with
        self.gitrepo = os.path.join(self.path, "repos", "test_repo.git")
        os.makedirs(self.gitrepo)
        repo = pygit2.init_repository(self.gitrepo)

        # Create a file in that git repo
        with open(os.path.join(self.gitrepo, "sources"), "w") as stream:
            stream.write("foo\n bar")
        repo.index.add("sources")
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature("Alice Author", "alice@authors.tld")
        committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
        repo.create_commit(
            "refs/heads/master",  # the name of the reference to update
            author,
            committer,
            "Add sources file for testing",
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [],
        )

        self.first_commit = repo.revparse_single("HEAD")

        # Edit the sources file again
        with open(os.path.join(self.gitrepo, "sources"), "w") as stream:
            stream.write("foo\n bar\nbaz\n boose")
        repo.index.add("sources")
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature("Alice Author", "alice@authors.tld")
        committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
        repo.create_commit(
            "refs/heads/master",  # the name of the reference to update
            author,
            committer,
            "Add baz and boose to the sources\n\n There are more objects to "
            "consider",
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [self.first_commit.oid.hex],
        )

        self.second_commit = repo.revparse_single("HEAD")

        # Add empty commit
        repo.create_commit(
            "refs/heads/master",  # the name of the reference to update
            author,
            committer,
            "Empty commit",
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [self.second_commit.oid.hex],
        )

        self.third_commit = repo.revparse_single("HEAD")

    def test_commit_to_patch_first_commit(self):
        """ Test the commit_to_patch function of pagure.lib.git. """
        repo = pygit2.init_repository(self.gitrepo)

        patch = pagure.lib.git.commit_to_patch(repo, self.first_commit)
        exp = r"""Mon Sep 17 00:00:00 2001
From: Alice Author <alice@authors.tld>
Subject: Add sources file for testing


---

diff --git a/sources b/sources
new file mode 100644
index 0000000..9f44358
--- /dev/null
+++ b/sources
@@ -0,0 +1,2 @@
+foo
+ bar
\ No newline at end of file

"""
        npatch = []
        for row in patch.split("\n"):
            if row.startswith("Date:"):
                continue
            if row.startswith("From "):
                row = row.split(" ", 2)[2]
            npatch.append(row)

        patch = "\n".join(npatch)
        self.assertEqual(patch, exp)

    def test_commit_to_patch_single_commit(self):
        """ Test the commit_to_patch function of pagure.lib.git. """
        repo = pygit2.init_repository(self.gitrepo)

        patch = pagure.lib.git.commit_to_patch(repo, self.second_commit)
        exp = r"""Mon Sep 17 00:00:00 2001
From: Alice Author <alice@authors.tld>
Subject: Add baz and boose to the sources


 There are more objects to consider
---

diff --git a/sources b/sources
index 9f44358..2a552bb 100644
--- a/sources
+++ b/sources
@@ -1,2 +1,4 @@
 foo
- bar
\ No newline at end of file
+ bar
+baz
+ boose
\ No newline at end of file

"""
        npatch = []
        for row in patch.split("\n"):
            if row.startswith("Date:"):
                continue
            if row.startswith("From "):
                row = row.split(" ", 2)[2]
            npatch.append(row)

        patch = "\n".join(npatch)
        self.assertEqual(patch, exp)

    def test_commit_to_patch_2_commits(self):
        """ Test the commit_to_patch function of pagure.lib.git. """
        repo = pygit2.init_repository(self.gitrepo)

        patch = pagure.lib.git.commit_to_patch(
            repo, [self.first_commit, self.second_commit]
        )
        exp = r"""Mon Sep 17 00:00:00 2001
From: Alice Author <alice@authors.tld>
Subject: [PATCH 1/2] Add sources file for testing


---

diff --git a/sources b/sources
new file mode 100644
index 0000000..9f44358
--- /dev/null
+++ b/sources
@@ -0,0 +1,2 @@
+foo
+ bar
\ No newline at end of file

Mon Sep 17 00:00:00 2001
From: Alice Author <alice@authors.tld>
Subject: [PATCH 2/2] Add baz and boose to the sources


 There are more objects to consider
---

diff --git a/sources b/sources
index 9f44358..2a552bb 100644
--- a/sources
+++ b/sources
@@ -1,2 +1,4 @@
 foo
- bar
\ No newline at end of file
+ bar
+baz
+ boose
\ No newline at end of file

"""
        npatch = []
        for row in patch.split("\n"):
            if row.startswith("Date:"):
                continue
            if row.startswith("From "):
                row = row.split(" ", 2)[2]
            npatch.append(row)

        patch = "\n".join(npatch)
        self.assertEqual(patch, exp)

    def test_commit_to_patch_first_commit_diff(self):
        """ Test the commit_to_patch function of pagure.lib.git. """
        repo = pygit2.init_repository(self.gitrepo)

        patch = pagure.lib.git.commit_to_patch(
            repo, self.first_commit, diff_view=True
        )
        exp = r"""diff --git a/sources b/sources
new file mode 100644
index 0000000..9f44358
--- /dev/null
+++ b/sources
@@ -0,0 +1,2 @@
+foo
+ bar
\ No newline at end of file
"""
        npatch = []
        for row in patch.split("\n"):
            if row.startswith("Date:"):
                continue
            if row.startswith("From "):
                row = row.split(" ", 2)[2]
            npatch.append(row)

        patch = "\n".join(npatch)
        self.assertEqual(patch, exp)

    def test_commit_to_patch_single_commit_diff(self):
        """ Test the commit_to_patch function of pagure.lib.git. """
        repo = pygit2.init_repository(self.gitrepo)

        patch = pagure.lib.git.commit_to_patch(
            repo, self.second_commit, diff_view=True
        )
        exp = r"""diff --git a/sources b/sources
index 9f44358..2a552bb 100644
--- a/sources
+++ b/sources
@@ -1,2 +1,4 @@
 foo
- bar
\ No newline at end of file
+ bar
+baz
+ boose
\ No newline at end of file
"""
        npatch = []
        for row in patch.split("\n"):
            if row.startswith("Date:"):
                continue
            if row.startswith("From "):
                row = row.split(" ", 2)[2]
            npatch.append(row)

        patch = "\n".join(npatch)
        self.assertEqual(patch, exp)

    def test_commit_to_patch_two_commits_diff(self):
        """ Test the commit_to_patch function of pagure.lib.git. """
        repo = pygit2.init_repository(self.gitrepo)

        patch = pagure.lib.git.commit_to_patch(
            repo, [self.first_commit, self.second_commit], diff_view=True
        )
        exp = r"""diff --git a/sources b/sources
new file mode 100644
index 0000000..9f44358
--- /dev/null
+++ b/sources
@@ -0,0 +1,2 @@
+foo
+ bar
\ No newline at end of file
diff --git a/sources b/sources
index 9f44358..2a552bb 100644
--- a/sources
+++ b/sources
@@ -1,2 +1,4 @@
 foo
- bar
\ No newline at end of file
+ bar
+baz
+ boose
\ No newline at end of file
"""
        npatch = []
        for row in patch.split("\n"):
            if row.startswith("Date:"):
                continue
            if row.startswith("From "):
                row = row.split(" ", 2)[2]
            npatch.append(row)

        patch = "\n".join(npatch)
        self.assertEqual(patch, exp)

    def test_commit_to_patch_first_commit_diff_separated(self):
        """ Test the commit_to_patch function of pagure.lib.git. """
        repo = pygit2.init_repository(self.gitrepo)

        patches = pagure.lib.git.commit_to_patch(
            repo, self.first_commit, diff_view=True, separated=True
        )
        exp = r"""diff --git a/sources b/sources
new file mode 100644
index 0000000..9f44358
--- /dev/null
+++ b/sources
@@ -0,0 +1,2 @@
+foo
+ bar
\ No newline at end of file
"""
        output = []
        for patch in patches:
            npatch = []
            for row in patch.split("\n"):
                if row.startswith("Date:"):
                    continue
                if row.startswith("From "):
                    row = row.split(" ", 2)[2]
                npatch.append(row)

            patch = "\n".join(npatch)
            output.append(patch)

        self.assertEqual(output, [exp])

    def test_commit_to_patch_single_commit_diff_separated(self):
        """ Test the commit_to_patch function of pagure.lib.git. """
        repo = pygit2.init_repository(self.gitrepo)

        patches = pagure.lib.git.commit_to_patch(
            repo, self.second_commit, diff_view=True, separated=True
        )
        exp = r"""diff --git a/sources b/sources
index 9f44358..2a552bb 100644
--- a/sources
+++ b/sources
@@ -1,2 +1,4 @@
 foo
- bar
\ No newline at end of file
+ bar
+baz
+ boose
\ No newline at end of file
"""
        output = []
        for patch in patches:
            npatch = []
            for row in patch.split("\n"):
                if row.startswith("Date:"):
                    continue
                if row.startswith("From "):
                    row = row.split(" ", 2)[2]
                npatch.append(row)

            patch = "\n".join(npatch)
            output.append(patch)

        self.assertEqual(output, [exp])

    def test_commit_to_patch_two_commits_diff_separated(self):
        """ Test the commit_to_patch function of pagure.lib.git. """
        repo = pygit2.init_repository(self.gitrepo)

        patches = pagure.lib.git.commit_to_patch(
            repo,
            [self.first_commit, self.second_commit],
            diff_view=True,
            separated=True,
        )
        exp = [
            r"""diff --git a/sources b/sources
new file mode 100644
index 0000000..9f44358
--- /dev/null
+++ b/sources
@@ -0,0 +1,2 @@
+foo
+ bar
\ No newline at end of file
""",
            r"""diff --git a/sources b/sources
index 9f44358..2a552bb 100644
--- a/sources
+++ b/sources
@@ -1,2 +1,4 @@
 foo
- bar
\ No newline at end of file
+ bar
+baz
+ boose
\ No newline at end of file
""",
        ]
        output = []
        for patch in patches:
            npatch = []
            for row in patch.split("\n"):
                if row.startswith("Date:"):
                    continue
                if row.startswith("From "):
                    row = row.split(" ", 2)[2]
                npatch.append(row)

            patch = "\n".join(npatch)
            output.append(patch)

        self.assertEqual(output, exp)

    def test_commit_to_patch_empty_commit(self):
        """ Test the commit_to_path function of pagure.lib.git. """
        repo = pygit2.init_repository(self.gitrepo)

        patch = pagure.lib.git.commit_to_patch(repo, self.third_commit)
        exp = ""
        self.assertEqual(patch, exp)

    def test_commit_to_patch_empty_commit_diff(self):
        """ Test the commit_to_patch function of pagure.lib.git. """
        repo = pygit2.init_repository(self.gitrepo)

        patch = pagure.lib.git.commit_to_patch(
            repo, self.third_commit, diff_view=True
        )
        exp = ""
        self.assertEqual(patch, exp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
