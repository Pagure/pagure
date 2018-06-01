# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import datetime
import unittest
import shutil
import sys
import os

import six
import json
import pygit2
from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskAppIndextests(tests.Modeltests):
    """ Tests for the index page of flask app controller of pagure """

    @patch.dict('pagure.config.config', {'HTML_TITLE': 'Pagure HTML title set'})
    def test_index_html_title(self):
        """ Test the index endpoint with a set html title. """

        output = self.app.get('/')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<title>Home - Pagure HTML title set</title>',
            output.get_data(as_text=True))

    def test_index_logged_out(self):
        """ Test the index endpoint when logged out. """

        output = self.app.get('/')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<title>Home - Pagure</title>', output_text)
        self.assertIn(
            '<h3 class="m-0 font-weight-bold">All Projects '
            '<span class="badge badge-secondary">0</span></h3>',
            output_text)

        tests.create_projects(self.session)

        output = self.app.get('/?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h3 class="m-0 font-weight-bold">All Projects '
            '<span class="badge badge-secondary">3</span></h3>',
            output.get_data(as_text=True))

    def test_index_logged_in(self):
        """ Test the index endpoint when logged in. """
        tests.create_projects(self.session)

        # Add a 3rd project with a long description
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project #3 with a very long description',
            hook_token='aaabbbeeefff',
        )
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/?repopage=abc&forkpage=def')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">1</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

    def test_index_commit_access_while_admin(self):
        """ Test the index endpoint filter for commit access only when user
        is an admin. """
        tests.create_projects(self.session)

        # Add a 3rd project just for foo
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project #3 with a very long description',
            hook_token='aaabbbeeefff',
        )
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            # Before
            output = self.app.get('/?acl=commit')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">1</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

            # Add foo to test with admin level
            project = pagure.lib._get_project(self.session, 'test')
            msg = pagure.lib.add_user_to_project(
                self.session,
                project=project,
                new_user='foo',
                user='pingou',
                access='admin')
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # After
            output = self.app.get('/?acl=commit')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">2</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

    def test_index_commit_access_while_commit(self):
        """ Test the index endpoint filter for commit access only when user
        is an committer. """
        tests.create_projects(self.session)

        # Add a 3rd project just for foo
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project #3 with a very long description',
            hook_token='aaabbbeeefff',
        )
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            # Before
            output = self.app.get('/?acl=commit')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">1</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

            # Add foo to test with commit level
            project = pagure.lib._get_project(self.session, 'test')
            msg = pagure.lib.add_user_to_project(
                self.session,
                project=project,
                new_user='foo',
                user='pingou',
                access='commit')
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # After
            output = self.app.get('/?acl=commit')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">2</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

    def test_index_commit_access_while_ticket(self):
        """ Test the index endpoint filter for commit access only when user
        is has ticket access. """
        tests.create_projects(self.session)

        # Add a 3rd project just for foo
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project #3 with a very long description',
            hook_token='aaabbbeeefff',
        )
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            # Before
            output = self.app.get('/?acl=ticket')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">1</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

            # Add foo to test with ticket level
            project = pagure.lib._get_project(self.session, 'test')
            msg = pagure.lib.add_user_to_project(
                self.session,
                project=project,
                new_user='foo',
                user='pingou',
                access='ticket')
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # After  -  projects with ticket access aren't shown
            output = self.app.get('/?acl=ticket')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">1</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

    def test_index_admin_access_while_admin(self):
        """ Test the index endpoint filter for admin access only when user
        is an admin. """
        tests.create_projects(self.session)

        # Add a 3rd project just for foo
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project #3 with a very long description',
            hook_token='aaabbbeeefff',
        )
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            # Before
            output = self.app.get('/?acl=admin')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">1</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

            # Add foo to test with commit level
            project = pagure.lib._get_project(self.session, 'test')
            msg = pagure.lib.add_user_to_project(
                self.session,
                project=project,
                new_user='foo',
                user='pingou',
                access='admin')
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # After
            output = self.app.get('/?acl=admin')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">2</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

    def test_index_admin_access_while_commit(self):
        """ Test the index endpoint filter for admin access only when user
        is an committer. """
        tests.create_projects(self.session)

        # Add a 3rd project just for foo
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project #3 with a very long description',
            hook_token='aaabbbeeefff',
        )
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            # Before
            output = self.app.get('/?acl=admin')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">1</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

            # Add foo to test with commit level
            project = pagure.lib._get_project(self.session, 'test')
            msg = pagure.lib.add_user_to_project(
                self.session,
                project=project,
                new_user='foo',
                user='pingou',
                access='commit')
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # After
            output = self.app.get('/?acl=admin')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">1</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

    def test_index_main_admin_access_while_commit(self):
        """ Test the index endpoint filter for main admin access only when
        user is an committer. """
        tests.create_projects(self.session)

        # Add a 3rd project just for foo
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project #3 with a very long description',
            hook_token='aaabbbeeefff',
        )
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            # Before
            output = self.app.get('/?acl=main admin')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">1</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

            # Add foo to test with commit level
            project = pagure.lib._get_project(self.session, 'test')
            msg = pagure.lib.add_user_to_project(
                self.session,
                project=project,
                new_user='foo',
                user='pingou',
                access='commit')
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # After
            output = self.app.get('/?acl=main admin')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'Projects <span class="badge badge-secondary">1</span>',
                output_text)
            self.assertIn(
                'Forks <span class="badge badge-secondary">0</span>',
                output_text)
            self.assertEqual(
                output_text.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output_text.count('<div class="card-header">'), 6)

    def test_index_fork_without_parent(self):
        """ Test the index view: forks should display either their parent
        project or mention that it was deleted. """
        tests.create_projects(self.session)

        # Add a 3rd project just for foo
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project #3',
            hook_token='aaabbbeeefff',
            is_fork=True,
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            # Before
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'My Forks <span class="badge badge-secondary">1</span>',
                output_text)
            segment = output_text.split('My Forks')[1].split('My Groups')[0]
            six.assertRegex(
                self,
                segment,
                r'foo/test3(\s*<[^>]+?>\s*)*?forked from(\s*<[^>]+?>\s*)*?test'
            )

            # Delete the parent (or fake it)
            proj = pagure.lib._get_project(self.session, 'test3', user='foo')
            proj.parent_id = None
            self.session.add(proj)
            self.session.commit()

            # Check page again
            output = self.app.get('/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                'My Forks <span class="badge badge-secondary">1</span>',
                output_text)
            segment = output_text.split('My Forks')[1].split('My Groups')[0]
            six.assertRegex(
                self,
                segment,
                r'foo/test3(\s*<[^>]+?>\s*)*?forked from a deleted repository'
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
