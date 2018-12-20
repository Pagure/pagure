# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Ryan Lerch <rlerch@redhat.com>
"""

from __future__ import unicode_literals, absolute_import

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

import pagure.lib.query
import tests


class PagureFlaskAppUserdashTests(tests.Modeltests):
    """ Tests for the index page of flask app controller of pagure """

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
            output = self.app.get('/dashboard/projects?acl=commit')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="btn btn-outline-secondary disabled opacity-100'
                ' border-0 ml-auto font-weight-bold">1 Projects</span>',
                output_text)
            self.assertIn(
                '<div class="text-center">No Projects match this filter</div>',
                output_text)



            # Add foo to test with admin level
            project = pagure.lib.query._get_project(self.session, 'test')
            msg = pagure.lib.query.add_user_to_project(
                self.session,
                project=project,
                new_user='foo',
                user='pingou',
                access='admin')
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # After
            self.assertIn(
                '<span class="btn btn-outline-secondary disabled opacity-100'
                ' border-0 ml-auto font-weight-bold">1 Projects</span>',
                output_text)
            self.assertIn(
                '<div class="text-center">No Projects match this filter</div>',
                output_text)

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
            output = self.app.get('/dashboard/projects?acl=commit')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>\n'
                '          <span class="btn btn-outline-secondary disabled'
                ' opacity-100 border-0 ml-auto font-weight-bold">1 Projects</span>\n',
                output_text)

            # Add foo to test with commit level
            project = pagure.lib.query._get_project(self.session, 'test')
            msg = pagure.lib.query.add_user_to_project(
                self.session,
                project=project,
                new_user='foo',
                user='pingou',
                access='commit')
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # After
            output = self.app.get('/dashboard/projects?acl=commit')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>\n'
                '          <span class="btn btn-outline-secondary disabled'
                ' opacity-100 border-0 ml-auto font-weight-bold">2 Projects</span>\n',
                output_text)

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
            output = self.app.get('/dashboard/projects?acl=ticket')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>\n'
                '          <span class="btn btn-outline-secondary disabled'
                ' opacity-100 border-0 ml-auto font-weight-bold">1 Projects</span>\n',
                output_text)

            # Add foo to test with ticket level
            project = pagure.lib.query._get_project(self.session, 'test')
            msg = pagure.lib.query.add_user_to_project(
                self.session,
                project=project,
                new_user='foo',
                user='pingou',
                access='ticket')
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # After  -  projects with ticket access aren't shown
            output = self.app.get('/dashboard/projects?acl=ticket')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>\n'
                '          <span class="btn btn-outline-secondary disabled'
                ' opacity-100 border-0 ml-auto font-weight-bold">2 Projects</span>\n',
                output_text)

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
            output = self.app.get('/dashboard/projects?acl=admin')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>\n'
                '          <span class="btn btn-outline-secondary disabled'
                ' opacity-100 border-0 ml-auto font-weight-bold">1 Projects</span>\n',
                output_text)

            # Add foo to test with admin level
            project = pagure.lib.query._get_project(self.session, 'test')
            msg = pagure.lib.query.add_user_to_project(
                self.session,
                project=project,
                new_user='foo',
                user='pingou',
                access='admin')
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # After
            output = self.app.get('/dashboard/projects?acl=admin')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>\n'
                '          <span class="btn btn-outline-secondary disabled'
                ' opacity-100 border-0 ml-auto font-weight-bold">2 Projects</span>\n',
                output_text)

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
            output = self.app.get('/dashboard/projects?acl=commit')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>\n'
                '          <span class="btn btn-outline-secondary disabled'
                ' opacity-100 border-0 ml-auto font-weight-bold">1 Projects</span>\n',
                output_text)

            # Add foo to test with commit level
            project = pagure.lib.query._get_project(self.session, 'test')
            msg = pagure.lib.query.add_user_to_project(
                self.session,
                project=project,
                new_user='foo',
                user='pingou',
                access='commit')
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # After
            output = self.app.get('/dashboard/projects?acl=commit')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # The total number no longer changes
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>\n'
                '          <span class="btn btn-outline-secondary disabled'
                ' opacity-100 border-0 ml-auto font-weight-bold">2 Projects</span>\n',
                output_text)

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
            output = self.app.get('/dashboard/projects?acl=main admin')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>\n'
                '          <span class="btn btn-outline-secondary disabled'
                ' opacity-100 border-0 ml-auto font-weight-bold">1 Projects</span>\n',
                output_text)

            # Add foo to test with commit level
            project = pagure.lib.query._get_project(self.session, 'test')
            msg = pagure.lib.query.add_user_to_project(
                self.session,
                project=project,
                new_user='foo',
                user='pingou',
                access='commit')
            self.session.commit()
            self.assertEqual(msg, 'User added')

            # After
            output = self.app.get('/dashboard/projects?acl=main admin')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>\n'
                '          <span class="btn btn-outline-secondary disabled'
                ' opacity-100 border-0 ml-auto font-weight-bold">2 Projects</span>\n',
                output_text)


    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_index_logged_in_private_project(self):
        """ Test the index endpoint when logged in with a private project. """
        tests.create_projects(self.session)

        # Add a 3rd project with a long description
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project #3 with a very long description',
            hook_token='aaabbbeeefff',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/dashboard/projects')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>\n'
                '          <span class="btn btn-outline-secondary disabled'
                ' opacity-100 border-0 ml-auto font-weight-bold">1 Projects</span>\n',
                output_text)
            self.assertIn(
                '<span title="Private project" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text)
            self.assertEqual(output_text.count('title="Private project"'), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
