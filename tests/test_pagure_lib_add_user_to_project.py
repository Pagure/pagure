# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

import unittest
import sys
import os

from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureLibAddUserToProjecttests(tests.Modeltests):
    """ Tests for pagure.lib.add_user_to_project """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureLibAddUserToProjecttests, self).setUp()

        tests.create_projects(self.session)

        item = pagure.lib.model.User(
            user='bar',
            fullname='bar baz',
            password='foo',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)

        self.session.commit()

        # Before
        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(len(repo.users), 0)

        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # After
        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(len(repo.users), 1)
        self.assertEqual(repo.users[0].user, 'foo')
        self.assertEqual(repo.admins[0].user, 'foo')

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_re_add_user_to_project_default(self):
        """ Update an existing user but to the same access level. """
        repo = pagure.lib._get_project(self.session, 'test')

        # Try adding the same user with the same access
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_user_to_project,
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='admin'
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_update_user_to_project_default(self):
        """ Update an existing user without any required group membership.
        """
        repo = pagure.lib._get_project(self.session, 'test')

        # Update the access of the user
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')
        self.assertEqual(len(repo.users), 1)
        self.assertEqual(repo.users[0].user, 'foo')
        self.assertEqual(repo.committers[0].user, 'foo')

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_update_user_to_project_require_packager_on_all(self):
        """
        Update an existing user but required group membership on all
        projects.
        """
        repo = pagure.lib._get_project(self.session, 'test')
        config = {
            '*': ['packager']
        }

        # Update the access of the user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_user_to_project,
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='admin',
            required_groups=config
        )
        self.session.commit()
        self.assertEqual(len(repo.users), 1)
        self.assertEqual(repo.users[0].user, 'foo')
        self.assertEqual(repo.committers[0].user, 'foo')

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_update_user_to_project_require_packager_on_st(self):
        """
        Update an existing user but required group membership on all
        projects match *st.
        """
        repo = pagure.lib._get_project(self.session, 'test')
        config = {
            '*st': ['packager']
        }

        # Update the access of the user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_user_to_project,
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='admin',
            required_groups=config
        )
        self.session.commit()
        self.assertEqual(len(repo.users), 1)
        self.assertEqual(repo.users[0].user, 'foo')
        self.assertEqual(repo.committers[0].user, 'foo')

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_update_user_to_project_require_packager_on_te(self):
        """
        Update an existing user but required group membership on all
        projects match te*.
        """
        repo = pagure.lib._get_project(self.session, 'test')
        config = {
            'te*': ['packager']
        }

        # Update the access of the user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_user_to_project,
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='admin',
            required_groups=config
        )
        self.session.commit()
        self.assertEqual(len(repo.users), 1)
        self.assertEqual(repo.users[0].user, 'foo')
        self.assertEqual(repo.committers[0].user, 'foo')

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_update_user_to_project_require_packager_on_test(self):
        """
        Update an existing user but required group membership on a specific
        project: test.
        """
        repo = pagure.lib._get_project(self.session, 'test')
        config = {
            'test': ['packager']
        }

        # Update the access of the user
        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.add_user_to_project,
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='admin',
            required_groups=config
        )
        self.session.commit()
        self.assertEqual(len(repo.users), 1)
        self.assertEqual(repo.users[0].user, 'foo')
        self.assertEqual(repo.committers[0].user, 'foo')

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_add_user_to_test2_require_packager_on_test(self):
        """
        Add user to project test2 while the configuration requires group
        membership on the project test.
        """
        repo = pagure.lib._get_project(self.session, 'test2')
        self.assertEqual(len(repo.users), 0)

        config = {
            'test': ['packager']
        }

        # Add the user
        pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='admin',
            required_groups=config
        )
        self.session.commit()
        self.assertEqual(len(repo.users), 1)
        self.assertEqual(repo.users[0].user, 'foo')
        self.assertEqual(repo.committers[0].user, 'foo')

class PagureLibAddUserToProjectWithGrouptests(
        PagureLibAddUserToProjecttests):
    """ Tests for pagure.lib.add_user_to_project """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureLibAddUserToProjectWithGrouptests, self).setUp()

        # Create group
        msg = pagure.lib.add_group(
            self.session,
            group_name='packager',
            display_name='packager',
            description='The Fedora packager groups',
            group_type='user',
            user='pingou',
            is_admin=False,
            blacklist=[])
        self.session.commit()
        self.assertEqual(msg, 'User `pingou` added to the group `packager`.')

        # Add user to group
        group = pagure.lib.search_groups(self.session, group_name='packager')
        msg = pagure.lib.add_user_to_group(
            self.session,
            username='bar',
            group=group,
            user='pingou',
            is_admin=True)
        self.session.commit()
        self.assertEqual(msg, 'User `bar` added to the group `packager`.')

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_add_user_to_test_require_packager_on_test(self):
        """
        Add user to project test while the configuration requires group
        membership on the project test.
        """
        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(len(repo.users), 1)

        config = {
            'test': ['packager']
        }

        # Add the user to the project
        pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='bar',
            user='pingou',
            access='commit',
            required_groups=config
        )
        self.session.commit()

        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(len(repo.users), 2)
        self.assertEqual(repo.users[0].user, 'foo')
        self.assertEqual(repo.committers[0].user, 'foo')
        self.assertEqual(repo.users[1].user, 'bar')
        self.assertEqual(repo.committers[1].user, 'bar')

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_add_user_to_test_require_packager(self):
        """
        Add user to project test while the configuration requires group
        membership on all the projects.
        """
        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(len(repo.users), 1)

        config = {
            '*': ['packager']
        }

        # Add the user to the project
        pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='bar',
            user='pingou',
            access='commit',
            required_groups=config
        )
        self.session.commit()

        repo = pagure.lib._get_project(self.session, 'test')
        self.assertEqual(len(repo.users), 2)
        self.assertEqual(repo.users[0].user, 'foo')
        self.assertEqual(repo.committers[0].user, 'foo')
        self.assertEqual(repo.users[1].user, 'bar')
        self.assertEqual(repo.committers[1].user, 'bar')


if __name__ == '__main__':
    unittest.main(verbosity=2)
