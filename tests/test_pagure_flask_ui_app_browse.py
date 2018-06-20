# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import sys
import os

from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskAppBrowsetests(tests.Modeltests):
    """ Tests for the browse pages of flask app controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskAppBrowsetests, self).setUp()

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

    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_browse_project_logged_in_private_project(self):
        """ Test the browse project endpoint when logged in with a private
        project. """

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/browse/projects/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Home - Pagure</title>\n',
                output_text)
            self.assertIn(
                '<h3 class="m-0 font-weight-bold">All Projects '
                '<span class="badge badge-secondary">4</span></h3>',
                output_text)
            self.assertIn(
                '<span title="Private project" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text)
            self.assertEqual(output_text.count('title="Private project"'), 1)

    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_browse_project_unauth_private_project(self):
        """ Test the browse project endpoint when logged out with a private
        project. """

        output = self.app.get('/browse/projects/')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>Home - Pagure</title>\n',
            output_text)
        self.assertIn(
            '<h3 class="m-0 font-weight-bold">All Projects '
            '<span class="badge badge-secondary">3</span></h3>',
            output_text)
        self.assertNotIn(
            '<span title="Private project" class="text-danger '
            'fa fa-fw fa-lock"></span>',
            output_text)
        self.assertEqual(output_text.count('title="Private project"'), 0)

    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_browse_project_logged_in_no_access_private_project(self):
        """ Test the browse project endpoint when logged in as an user that
        has no access to the private project. """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/browse/projects/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Home - Pagure</title>\n',
                output_text)
            self.assertIn(
                '<h3 class="m-0 font-weight-bold">All Projects '
                '<span class="badge badge-secondary">3</span></h3>',
                output_text)
            self.assertNotIn(
                '<span title="Private project" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text)
            self.assertEqual(output_text.count('title="Private project"'), 0)

    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_browse_project_logged_in_ticket_private_project(self):
        """ Test the browse project endpoint when logged in as an user that
        has no access to the private project. """

        # Add user 'pingou' with ticket access on repo
        repo = pagure.lib._get_project(self.session, 'test3')
        msg = pagure.lib.add_user_to_project(
            self.session,
            repo,
            new_user='pingou',
            user='foo',
            access='ticket',
        )
        self.assertEqual(msg, 'User added')
        self.session.commit()

        # Ticket access level isn't sufficient to access private projects
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/browse/projects/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Home - Pagure</title>\n',
                output_text)
            self.assertIn(
                '<h3 class="m-0 font-weight-bold">All Projects '
                '<span class="badge badge-secondary">3</span></h3>',
                output_text)
            self.assertNotIn(
                '<span title="Private project" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text)
            self.assertEqual(output_text.count('title="Private project"'), 0)

    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_browse_project_logged_in_commit_private_project(self):
        """ Test the browse project endpoint when logged in as an user that
        has no access to the private project. """

        # Add user 'pingou' with commit access on repo
        repo = pagure.lib._get_project(self.session, 'test3')
        msg = pagure.lib.add_user_to_project(
            self.session,
            repo,
            new_user='pingou',
            user='foo',
            access='commit',
        )
        self.assertEqual(msg, 'User added')
        self.session.commit()

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/browse/projects/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Home - Pagure</title>\n',
                output_text)
            self.assertIn(
                '<h3 class="m-0 font-weight-bold">All Projects '
                '<span class="badge badge-secondary">4</span></h3>',
                output_text)
            self.assertIn(
                '<span title="Private project" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text)
            self.assertEqual(output_text.count('title="Private project"'), 1)

    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_browse_project_logged_in_admin_private_project(self):
        """ Test the browse project endpoint when logged in as an user that
        has no access to the private project. """

        # Add user 'pingou' with admin access on repo
        repo = pagure.lib._get_project(self.session, 'test3')
        msg = pagure.lib.add_user_to_project(
            self.session,
            repo,
            new_user='pingou',
            user='foo',
            access='admin',
        )
        self.assertEqual(msg, 'User added')
        self.session.commit()

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/browse/projects/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Home - Pagure</title>\n',
                output_text)
            self.assertIn(
                '<h3 class="m-0 font-weight-bold">All Projects '
                '<span class="badge badge-secondary">4</span></h3>',
                output_text)
            self.assertIn(
                '<span title="Private project" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text)
            self.assertEqual(output_text.count('title="Private project"'), 1)

class PagureFlaskAppBrowseGroupAdmintests(tests.Modeltests):
    """ Tests for the browse pages of flask app controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskAppBrowseGroupAdmintests, self).setUp()

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

        # Create a group
        msg = pagure.lib.add_group(
            self.session,
            group_name='JL',
            display_name='Justice League',
            description='Nope, it\'s not JLA anymore',
            group_type='user',
            user='foo',
            is_admin=False,
            blacklist=pagure.config.config.get('BLACKLISTED_PROJECTS')
        )

        self.assertEqual(msg, 'User `foo` added to the group `JL`.')

        # Add the group to project we just created, test3
        # Add it with admin ACL
        project = pagure.lib._get_project(self.session, 'test3')
        msg = pagure.lib.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='foo',
            access='admin'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_browse_project_user_not_in_group(self):
        """ Test the browse project endpoint when logged in as an user that
        has no access to the private project via a group as admin. """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/browse/projects/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Home - Pagure</title>\n',
                output_text)
            self.assertIn(
                '<h3 class="m-0 font-weight-bold">All Projects '
                '<span class="badge badge-secondary">3</span></h3>',
                output_text)
            self.assertNotIn(
                '<span title="Private project" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text)
            self.assertEqual(output_text.count('title="Private project"'), 0)

    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_browse_project_user_in_group(self):
        """ Test the browse project endpoint when logged in as an user that
        has no access to the private project via a group as admin. """
        group = pagure.lib.search_groups(
            self.session, group_name='JL')

        pagure.lib.add_user_to_group(
            session=self.session,
            username='pingou',
            group=group,
            user='foo',
            is_admin=False,
        )
        self.session.commit()

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/browse/projects/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Home - Pagure</title>\n',
                output_text)
            self.assertIn(
                '<h3 class="m-0 font-weight-bold">All Projects '
                '<span class="badge badge-secondary">4</span></h3>',
                output_text)
            self.assertIn(
                '<span title="Private project" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text)
            self.assertEqual(output_text.count('title="Private project"'), 1)


class PagureFlaskAppBrowseGroupCommittests(tests.Modeltests):
    """ Tests for the browse pages of flask app controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskAppBrowseGroupCommittests, self).setUp()

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

        # Create a group
        msg = pagure.lib.add_group(
            self.session,
            group_name='JL',
            display_name='Justice League',
            description='Nope, it\'s not JLA anymore',
            group_type='user',
            user='foo',
            is_admin=False,
            blacklist=pagure.config.config.get('BLACKLISTED_PROJECTS')
        )

        self.assertEqual(msg, 'User `foo` added to the group `JL`.')

        # Add the group to project we just created, test3
        # Add it with commit ACL
        project = pagure.lib._get_project(self.session, 'test3')
        msg = pagure.lib.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='foo',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_browse_project_user_not_in_group(self):
        """ Test the browse project endpoint when logged in as an user that
        has no access to the private project via a group as admin. """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/browse/projects/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Home - Pagure</title>\n',
                output_text)
            self.assertIn(
                '<h3 class="m-0 font-weight-bold">All Projects '
                '<span class="badge badge-secondary">3</span></h3>',
                output_text)
            self.assertNotIn(
                '<span title="Private project" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text)
            self.assertEqual(output_text.count('title="Private project"'), 0)

    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_browse_project_user_in_group(self):
        """ Test the browse project endpoint when logged in as an user that
        has no access to the private project via a group as admin. """
        group = pagure.lib.search_groups(
            self.session, group_name='JL')

        pagure.lib.add_user_to_group(
            session=self.session,
            username='pingou',
            group=group,
            user='foo',
            is_admin=False,
        )
        self.session.commit()

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/browse/projects/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Home - Pagure</title>\n',
                output_text)
            self.assertIn(
                '<h3 class="m-0 font-weight-bold">All Projects '
                '<span class="badge badge-secondary">4</span></h3>',
                output_text)
            self.assertIn(
                '<span title="Private project" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text)
            self.assertEqual(output_text.count('title="Private project"'), 1)


class PagureFlaskAppBrowseGroupTickettests(tests.Modeltests):
    """ Tests for the browse pages of flask app controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskAppBrowseGroupTickettests, self).setUp()

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

        # Create a group
        msg = pagure.lib.add_group(
            self.session,
            group_name='JL',
            display_name='Justice League',
            description='Nope, it\'s not JLA anymore',
            group_type='user',
            user='foo',
            is_admin=False,
            blacklist=pagure.config.config.get('BLACKLISTED_PROJECTS')
        )

        self.assertEqual(msg, 'User `foo` added to the group `JL`.')

        # Add the group to project we just created, test3
        # Add it with ticket ACL
        project = pagure.lib._get_project(self.session, 'test3')
        msg = pagure.lib.add_group_to_project(
            self.session,
            project=project,
            new_group='JL',
            user='foo',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_browse_project_user_not_in_group(self):
        """ Test the browse project endpoint when logged in as an user that
        has no access to the private project via a group as admin. """

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/browse/projects/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Home - Pagure</title>\n',
                output_text)
            self.assertIn(
                '<h3 class="m-0 font-weight-bold">All Projects '
                '<span class="badge badge-secondary">3</span></h3>',
                output_text)
            self.assertNotIn(
                '<span title="Private project" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text)
            self.assertEqual(output_text.count('title="Private project"'), 0)

    @patch.dict('pagure.config.config', {'PRIVATE_PROJECTS': True})
    def test_browse_project_user_in_group(self):
        """ Test the browse project endpoint when logged in as an user that
        has no access to the private project via a group as admin. """
        group = pagure.lib.search_groups(
            self.session, group_name='JL')

        pagure.lib.add_user_to_group(
            session=self.session,
            username='pingou',
            group=group,
            user='foo',
            is_admin=False,
        )
        self.session.commit()

        # Ticket ACL isn't enough to grant you access
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/browse/projects/')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Home - Pagure</title>\n',
                output_text)
            self.assertIn(
                '<h3 class="m-0 font-weight-bold">All Projects '
                '<span class="badge badge-secondary">3</span></h3>',
                output_text)
            self.assertNotIn(
                '<span title="Private project" class="text-danger '
                'fa fa-fw fa-lock"></span>',
                output_text)
            self.assertEqual(output_text.count('title="Private project"'), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
