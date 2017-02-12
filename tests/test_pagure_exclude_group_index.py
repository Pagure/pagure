# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

import mock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import pagure.lib.model
import tests

class PagureExcludeGroupIndex(tests.Modeltests):
    """ Tests the EXCLUDE_GROUP_INDEX configuration key in pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureExcludeGroupIndex, self).setUp()

        pagure.APP.config['GIT_FOLDER'] = os.path.join(self.path, 'repos')
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        # Create a ``provenpackger`` group:
        msg = pagure.lib.add_group(
            self.session,
            group_name='provenpackager',
            display_name='Proven Packagers',
            description='Packagers having access to all the repo',
            group_type='user',
            user='pingou',
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(
            msg, 'User `pingou` added to the group `provenpackager`.')

        # Add the `provenpackager` group to the test2 project
        project = pagure.get_authorized_project(self.session, 'test2')
        msg = pagure.lib.add_group_to_project(
            session=self.session,
            project=project,
            new_group='provenpackager',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

    def test_defaults_pingou(self):
        """ Test which repo pingou has by default. """

        repos = pagure.lib.search_projects(
            self.session,
            username='pingou',
            fork=False,
        )

        self.assertEqual(len(repos), 3)
        for idx, name in enumerate(['test', 'test2', 'test3']):
            self.assertEqual(repos[idx].name, name)

    def test_defaults_foo(self):
        """ Test which repo foo has by default. """

        repos = pagure.lib.search_projects(
            self.session,
            username='foo',
            fork=False,
        )

        self.assertEqual(len(repos), 0)


    def test_add_foo_test(self):
        """ Test adding foo to the test project. """

        group = pagure.lib.search_groups(
            self.session, group_name='provenpackager')
        self.assertEqual(group.group_name, 'provenpackager')

        # List all foo's project before (ie: there should be none)
        repos = pagure.lib.search_projects(
            self.session,
            username='foo',
            fork=False,
        )

        self.assertEqual(len(repos), 0)

        # Adding `foo` to the `provenpackager` group
        msg = pagure.lib.add_user_to_group(
            self.session,
            username='foo',
            group=group,
            user='pingou',
            is_admin=False,
        )
        self.assertEqual(
            msg, 'User `foo` added to the group `provenpackager`.')

        # Test that foo has now one project, via the provenpackager group
        repos = pagure.lib.search_projects(
            self.session,
            username='foo',
            fork=False,
        )

        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0].name, 'test2')

    def test_excluding_provenpackager(self):
        """ Test retrieving user's repo with a group excluded. """

        # Add `foo` to `provenpackager`
        group = pagure.lib.search_groups(
            self.session, group_name='provenpackager')
        self.assertEqual(group.group_name, 'provenpackager')

        msg = pagure.lib.add_user_to_group(
            self.session,
            username='foo',
            group=group,
            user='pingou',
            is_admin=False,
        )
        self.assertEqual(
            msg, 'User `foo` added to the group `provenpackager`.')

        # Get foo's project outside of proven packager
        repos = pagure.lib.search_projects(
            self.session,
            username='foo',
            exclude_groups=['provenpackager'],
            fork=False,
        )

        self.assertEqual(len(repos), 0)

        # Get pingou's project outside of proven packager (nothing changes)
        repos = pagure.lib.search_projects(
            self.session,
            username='pingou',
            exclude_groups=['provenpackager'],
            fork=False,
        )
        repos2 = pagure.lib.search_projects(
            self.session,
            username='pingou',
            fork=False,
        )

        self.assertEqual(repos, repos2)
        self.assertEqual(len(repos), 3)
        for idx, name in enumerate(['test', 'test2', 'test3']):
            self.assertEqual(repos[idx].name, name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
