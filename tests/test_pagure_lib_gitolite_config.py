# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

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
from io import open

import pygit2
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.git
import pagure.lib.query
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
    """Tests for pagure.lib.git"""

    maxDiff = None

    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureLibGitoliteConfigtests, self).setUp()

        tests.create_projects(self.session)

        self.outputconf = os.path.join(self.path, "test_gitolite.conf")

        self.preconf = os.path.join(self.path, "header_gitolite")
        with open(self.preconf, "w") as stream:
            stream.write("# this is a header that is manually added\n")
            stream.write("\n")
            stream.write("@group1 = foo bar baz\n")
            stream.write("@group2 = threebean puiterwijk kevin pingou\n")

        self.postconf = os.path.join(self.path, "footer_gitolite")
        with open(self.postconf, "w", encoding="utf-8") as stream:
            stream.write("# end of generated configuration\n")
            stream.write(r"# \ó/")
            stream.write("\n# end of footer\n")

    def tearDown(self):
        """Tearn down the environnment, ran before every tests."""
        super(PagureLibGitoliteConfigtests, self).tearDown()

        if os.path.exists(self.outputconf):
            os.unlink(self.outputconf)
        self.assertFalse(os.path.exists(self.outputconf))

    def test_write_gitolite_pre_post_projectNone(self):
        """Test the write_gitolite_acls function of pagure.lib.git with
        a postconf set"""

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=None,
            preconf=self.preconf,
            postconf=self.postconf,
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf, "r") as stream:
            data = stream.read()

        exp = (
            r"""# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou

# end of header
%s

# end of body
# end of generated configuration
# \ó/
# end of footer

"""
            % CORE_CONFIG
        )
        # print data
        self.assertEqual(data, exp)

    def test_write_gitolite_pre_post_projectNone_to_existing_file(self):
        """Test the write_gitolite_acls function of pagure.lib.git with
        a postconf set with existing output file"""

        with open(self.outputconf, "w") as stream:
            pass

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=None,
            preconf=self.preconf,
            postconf=self.postconf,
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()
        self.assertEqual(data, "")

    def test_write_gitolite_pre_post_project_1(self):
        """Test the write_gitolite_acls function of pagure.lib.git with
        a postconf set"""

        with open(self.outputconf, "w") as stream:
            pass

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=-1,
            preconf=self.preconf,
            postconf=self.postconf,
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = (
            r"""# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou

# end of header
%s

# end of body
# end of generated configuration
# \ó/
# end of footer

"""
            % CORE_CONFIG
        )

        # print data
        self.assertEqual(data, exp)

    def test_write_gitolite_pre_post_project_test(self):
        """Test the write_gitolite_acls function of pagure.lib.git with
        a postconf set"""

        with open(self.outputconf, "w") as stream:
            pass

        project = pagure.lib.query._get_project(self.session, "test")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=project,
            preconf=self.preconf,
            postconf=self.postconf,
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = r"""# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou

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

# end of body
# end of generated configuration
# \ó/
# end of footer

"""
        # print data
        self.assertEqual(data, exp)

    def test_write_gitolite_pre_post_project_test_full_file(self):
        """Test the write_gitolite_acls function of pagure.lib.git with
        a postconf set"""

        # Re-generate the gitolite config for all the projects
        self.test_write_gitolite_pre_post_project_1()
        self.assertTrue(os.path.exists(self.outputconf))

        project = pagure.lib.query._get_project(self.session, "test")
        project.user_id = 2
        self.session.add(project)
        self.session.commit()

        project = pagure.lib.query._get_project(self.session, "test")
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user="pingou",
            user="foo",
            access="commit",
        )
        self.assertEqual(msg, "User added")
        self.session.commit()

        project = pagure.lib.query._get_project(self.session, "test")
        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=project,
            preconf=self.preconf,
            postconf=self.postconf,
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = r"""# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou

# end of header
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

# end of body
# end of generated configuration
# \ó/
# end of footer

"""
        # print data
        self.assertEqual(data, exp)

    @patch.dict(
        "pagure.config.config", {"ENABLE_DOCS": False, "ENABLE_TICKETS": False}
    )
    def test_write_gitolite_disabled_docs_tickets(self):
        """Test the write_gitolite_acls function when docs and tickets
        are disabled"""

        # Re-generate the gitolite config for all the projects
        project = pagure.lib.query._get_project(self.session, "test")
        project.user_id = 2
        self.session.add(project)
        self.session.commit()

        project = pagure.lib.query._get_project(self.session, "test")
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user="pingou",
            user="foo",
            access="commit",
        )
        self.assertEqual(msg, "User added")
        self.session.commit()

        project = pagure.lib.query._get_project(self.session, "test")
        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session, self.outputconf, project=project
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = """repo test
  R   = @all
  RW+ = foo
  RW+ = pingou

repo requests/test
  RW+ = foo
  RW+ = pingou

repo test2
  R   = @all
  RW+ = pingou

repo requests/test2
  RW+ = pingou

repo somenamespace/test3
  R   = @all
  RW+ = pingou

repo requests/somenamespace/test3
  RW+ = pingou

# end of body
"""
        self.assertEqual(data, exp)


class PagureLibGitoliteGroupConfigtests(tests.Modeltests):
    """Tests for generating the gitolite configuration file for a group
    change

    """

    maxDiff = None

    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureLibGitoliteGroupConfigtests, self).setUp()

        tests.create_projects(self.session)

        pagure.lib.query.add_group(
            self.session,
            group_name="grp",
            display_name="grp group",
            description=None,
            group_type="user",
            user="pingou",
            is_admin=False,
            blacklist=[],
        )
        pagure.lib.query.add_group(
            self.session,
            group_name="grp2",
            display_name="grp2 group",
            description=None,
            group_type="user",
            user="foo",
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()

        self.outputconf = os.path.join(self.path, "test_gitolite.conf")

        self.preconf = os.path.join(self.path, "header_gitolite")
        with open(self.preconf, "w") as stream:
            stream.write("# this is a header that is manually added\n")
            stream.write("\n")
            stream.write("@group1 = foo bar baz\n")
            stream.write("@group2 = threebean puiterwijk kevin pingou\n")

        self.postconf = os.path.join(self.path, "footer_gitolite")
        with open(self.postconf, "w") as stream:
            stream.write("# end of generated configuration\n")
            stream.write(r"# \ó/")
            stream.write("\n# end of footer\n")

    def tearDown(self):
        """Tearn down the environnment, ran before every tests."""
        super(PagureLibGitoliteGroupConfigtests, self).tearDown()

        if os.path.exists(self.outputconf):
            os.unlink(self.outputconf)
        self.assertFalse(os.path.exists(self.outputconf))

    def test_write_gitolite_project_test_group(self):
        """Test the write_gitolite_acls when updating a single group."""

        with open(self.outputconf, "w") as stream:
            pass

        project = pagure.lib.query._get_project(self.session, "test")
        group = pagure.lib.query.search_groups(self.session, group_name="grp")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=project,
            preconf=self.preconf,
            postconf=self.postconf,
            group=group,
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = r"""# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou

# end of header
@grp  = pingou

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

# end of body
# end of generated configuration
# \ó/
# end of footer

"""
        # print data
        self.assertEqual(data, exp)

    def test_write_gitolite_project_test_all_groups(self):
        """Test the write_gitolite_acls when updating all groups."""

        with open(self.outputconf, "w") as stream:
            pass

        project = pagure.lib.query._get_project(self.session, "test")

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=project,
            preconf=self.preconf,
            postconf=self.postconf,
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = r"""# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou

# end of header
@grp  = pingou
@grp2  = foo
# end of groups

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

# end of body
# end of generated configuration
# \ó/
# end of footer

"""
        # print data
        self.assertEqual(data, exp)

    def test_write_gitolite_project_all_projects_groups(self):
        """Test the generating the entire gitolite config."""

        with open(self.outputconf, "w") as stream:
            pass

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=-1,
            preconf=self.preconf,
            postconf=self.postconf,
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = (
            r"""# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou

# end of header
@grp  = pingou
@grp2  = foo
# end of groups

%s

# end of body
# end of generated configuration
# \ó/
# end of footer

"""
            % CORE_CONFIG
        )
        # print data
        self.assertEqual(data, exp)

    def test_write_gitolite_project_all_projects_one_group(self):
        """Test the generating the entire gitolite config."""

        # Generate the full gitolite config that we will update
        self.test_write_gitolite_project_all_projects_groups()

        project = pagure.lib.query._get_project(self.session, "test")
        group = pagure.lib.query.search_groups(self.session, group_name="grp")

        # Let's add `foo` to `grp` so something changes
        msg = pagure.lib.query.add_user_to_group(
            self.session,
            username="foo",
            group=group,
            user="pingou",
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, "User `foo` added to the group `grp`.")

        # Let's add `foo` to `test` so the project changes as well
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="commit",
        )
        self.assertEqual(msg, "User added")
        self.session.commit()

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=project,
            group=group,
            preconf=self.preconf,
            postconf=self.postconf,
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = r"""# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou

# end of header
@grp  = foo pingou
@grp2  = foo
# end of groups

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

# end of body
# end of generated configuration
# \ó/
# end of footer

"""
        # print data
        self.assertEqual(data, exp)

    def test_write_gitolite_delete_group(self):
        """Test the updating the gitolite config after having
        deleted a group.
        """

        # Generate the full gitolite config that we will update
        self.test_write_gitolite_project_all_projects_groups()

        # Delete the group `grp`
        self.assertEqual(len(pagure.lib.query.search_groups(self.session)), 2)
        group = pagure.lib.query.search_groups(self.session, group_name="grp")
        self.session.delete(group)
        self.session.commit()
        self.assertEqual(len(pagure.lib.query.search_groups(self.session)), 1)

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(
            self.session,
            self.outputconf,
            project=None,
            preconf=self.preconf,
            postconf=self.postconf,
        )
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = (
            r"""# this is a header that is manually added

@group1 = foo bar baz
@group2 = threebean puiterwijk kevin pingou

# end of header
@grp2  = foo
# end of groups

%s

# end of body
# end of generated configuration
# \ó/
# end of footer

"""
            % CORE_CONFIG
        )
        # print data
        self.assertEqual(data, exp)

    @patch("pagure.lib.git_auth.get_git_auth_helper")
    def test_task_generate_gitolite_acls_one_group(self, get_helper):
        """Test the generate_gitolite_acls task to ensure if group is None
        then None is passed to the helper."""
        helper = MagicMock()
        get_helper.return_value = helper
        pagure.lib.query.SESSIONMAKER = self.session.session_factory

        pagure.lib.tasks.generate_gitolite_acls(
            namespace=None, name="test", user=None, group=None
        )

        get_helper.assert_called_with()
        args = helper.generate_acls.call_args
        self.assertIsNone(args[1].get("group"))
        self.assertIsNotNone(args[1].get("project"))

    def test_write_gitolite_project_test_private(self):
        """Test the write_gitolite_acls function of pagure.lib.git with
        a postconf set"""

        # Make the test project private
        project = pagure.lib.query._get_project(self.session, "test")
        project.private = True
        self.session.add(project)
        self.session.commit()

        # Re-generate the gitolite config just for this project
        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(self.session, self.outputconf, project=None)
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = """@grp  = pingou
@grp2  = foo
# end of groups

repo test
  RW+ = pingou

repo docs/test
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
        self.assertEqual(data, exp)

    def test_remove_acls(self):
        """Test the remove_acls function of pagure.lib.git when deleting
        a project"""
        pagure.config.config["GITOLITE_CONFIG"] = self.outputconf

        with open(self.outputconf, "w") as stream:
            pass

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(self.session, self.outputconf, project=-1)
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = (
            """@grp  = pingou
@grp2  = foo
# end of groups

%s

# end of body
"""
            % CORE_CONFIG
        )

        # print data
        self.assertEqual(data, exp)

        # Test removing a project from the existing config
        project = pagure.lib.query.get_authorized_project(
            self.session, project_name="test"
        )

        helper.remove_acls(self.session, project=project)

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = """@grp  = pingou
@grp2  = foo
# end of groups

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
        self.assertEqual(data, exp)

    def test_remove_acls_no_project(self):
        """Test the remove_acls function of pagure.lib.git when no project
        is specified"""
        pagure.config.config["GITOLITE_CONFIG"] = self.outputconf

        with open(self.outputconf, "w") as stream:
            pass

        helper = pagure.lib.git_auth.get_git_auth_helper("gitolite3")
        helper.write_gitolite_acls(self.session, self.outputconf, project=-1)
        self.assertTrue(os.path.exists(self.outputconf))

        with open(self.outputconf) as stream:
            data = stream.read()

        exp = (
            """@grp  = pingou
@grp2  = foo
# end of groups

%s

# end of body
"""
            % CORE_CONFIG
        )

        # print data
        self.assertEqual(data, exp)

        # Test nothing changes if no project is specified

        self.assertRaises(
            RuntimeError, helper.remove_acls, self.session, project=None
        )

        with open(self.outputconf) as stream:
            data = stream.read()

        self.assertEqual(data, exp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
