# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

import mock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import pagure.lib.model
import tests

@mock.patch(
        'pagure.lib.git.update_git', mock.MagicMock(return_value=True))
@mock.patch(
    'pagure.lib.notify.send_email', mock.MagicMock(return_value=True))
class PagureLibGetWatchListtests(tests.Modeltests):
    """ Tests for pagure.lib.get_watch_list """

    def test_get_watch_list_invalid_object(self):
        """ Test get_watch_list when given an invalid object """
        # Create a project ns/test
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        self.assertRaises(
            pagure.exceptions.InvalidObjectException,
            pagure.lib.get_watch_list,
            self.session,
            item
        )

    def test_get_watch_list_simple(self):
        """ Test get_watch_list when the creator of the ticket is the
        creator of the project """
        # Create a project ns/test
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Create the ticket
        iss = pagure.lib.new_issue(
            issue_id=4,
            session=self.session,
            repo=item,
            title='test issue',
            content='content test issue',
            user='pingou',
            ticketfolder=None,
        )
        self.session.commit()
        self.assertEqual(iss.id, 4)
        self.assertEqual(iss.title, 'test issue')

        self.assertEqual(
            pagure.lib.get_watch_list(self.session, iss),
            set(['pingou'])
        )

    def test_get_watch_list_different_creator(self):
        """ Test get_watch_list when the creator of the ticket is not the
        creator of the project """
        # Create a project ns/test
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Create the ticket
        iss = pagure.lib.new_issue(
            issue_id=4,
            session=self.session,
            repo=item,
            title='test issue',
            content='content test issue',
            user='foo',
            ticketfolder=None,
        )
        self.session.commit()
        self.assertEqual(iss.id, 4)
        self.assertEqual(iss.title, 'test issue')

        self.assertEqual(
            pagure.lib.get_watch_list(self.session, iss),
            set(['pingou', 'foo'])
        )

    def test_get_watch_list_project_w_contributor(self):
        """ Test get_watch_list when the project has more than one
        contributor """
        # Create a project ns/test3
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Add a contributor to the project
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar foo',
            password='foo',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)

        project = pagure.lib._get_project(
            self.session, 'test3', namespace='ns')
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=project,
            new_user='bar',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # Create the ticket
        iss = pagure.lib.new_issue(
            issue_id=4,
            session=self.session,
            repo=project,
            title='test issue',
            content='content test issue',
            user='foo',
            ticketfolder=None,
        )
        self.session.commit()
        self.assertEqual(iss.id, 4)
        self.assertEqual(iss.title, 'test issue')

        self.assertEqual(
            pagure.lib.get_watch_list(self.session, iss),
            set(['pingou', 'foo', 'bar'])
        )

    def test_get_watch_list_user_in_group(self):
        """ Test get_watch_list when the project has groups of contributors
        """
        # Create a project ns/test3
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Create a third user
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar foo',
            password='foo',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)

        # Create a group
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

        # Add user to group
        group = pagure.lib.search_groups(self.session, group_name='foo')
        msg = pagure.lib.add_user_to_group(
            self.session,
            username='bar',
            group=group,
            user='pingou',
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, 'User `bar` added to the group `foo`.')

        project = pagure.lib._get_project(
            self.session, 'test3', namespace='ns')

        # Add group to project
        msg = pagure.lib.add_group_to_project(
            session=self.session,
            project=project,
            new_group='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

        # Create the ticket
        iss = pagure.lib.new_issue(
            issue_id=4,
            session=self.session,
            repo=project,
            title='test issue',
            content='content test issue',
            user='foo',
            ticketfolder=None,
        )
        self.session.commit()
        self.assertEqual(iss.id, 4)
        self.assertEqual(iss.title, 'test issue')

        self.assertEqual(
            pagure.lib.get_watch_list(self.session, iss),
            set(['pingou', 'foo', 'bar'])
        )

    def test_get_watch_list_project_w_contributor_out(self):
        """ Test get_watch_list when the project has one contributor not
        watching the project """
        # Create a project ns/test3
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Add a contributor to the project
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar foo',
            password='foo',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)

        project = pagure.lib._get_project(
            self.session, 'test3', namespace='ns')
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=project,
            new_user='bar',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # Set the user `pingou` to not watch the project
        msg = pagure.lib.update_watch_status(
            session=self.session,
            project=project,
            user='pingou',
            watch='0',
        )
        self.session.commit()
        self.assertEqual(msg, 'You are no longer watching this project')

        # Create the ticket
        iss = pagure.lib.new_issue(
            issue_id=4,
            session=self.session,
            repo=project,
            title='test issue',
            content='content test issue',
            user='foo',
            ticketfolder=None,
        )
        self.session.commit()
        self.assertEqual(iss.id, 4)
        self.assertEqual(iss.title, 'test issue')

        self.assertEqual(
            pagure.lib.get_watch_list(self.session, iss),
            set(['foo', 'bar'])
        )

    def test_get_watch_list_project_w_contributor_out_pr(self):
        """ Test get_watch_list when the project has one contributor not
        watching the pull-request """
        # Create a project ns/test3
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Add a contributor to the project
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar foo',
            password='foo',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)

        project = pagure.lib._get_project(
            self.session, 'test3', namespace='ns')
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=project,
            new_user='bar',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # Create the pull-request
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='dev',
            repo_to=project,
            branch_to='master',
            title='test pull-request',
            user='foo',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Set the user `pingou` to not watch the pull-request
        out = pagure.lib.set_watch_obj(self.session, 'pingou', req, False)
        self.assertEqual(
            out, 'You are no longer watching this pull-request')

        self.assertEqual(
            pagure.lib.get_watch_list(self.session, req),
            set(['foo', 'bar'])
        )

    def test_get_watch_list_project_w_contributor_watching_project(self):
        """ Test get_watch_list when the project has one contributor watching
        the project """
        # Create a project ns/test3
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Add a new user
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar foo',
            password='foo',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)

        # Set the user `bar` to watch the project
        project = pagure.lib._get_project(
            self.session, 'test3', namespace='ns')
        msg = pagure.lib.update_watch_status(
            session=self.session,
            project=project,
            user='bar',
            watch='1',
        )
        self.session.commit()
        self.assertEqual(
            msg, 'You are now watching issues and PRs on this project')

        # Create the pull-request
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='dev',
            repo_to=project,
            branch_to='master',
            title='test pull-request',
            user='foo',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        self.assertEqual(
            pagure.lib.get_watch_list(self.session, req),
            set(['foo', 'bar', 'pingou'])
        )

    def test_get_watch_list_project_w_private_issue(self):
        """ Test get_watch_list when the project has one contributor watching
        the project and the issue is private """
        # Create a project ns/test3
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Add a new user
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar foo',
            password='foo',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)

        # Set the user `bar` to watch the project
        project = pagure.lib.get_authorized_project(
            self.session, 'test3', namespace='ns')
        msg = pagure.lib.update_watch_status(
            session=self.session,
            project=project,
            user='bar',
            watch='1',
        )
        self.session.commit()
        self.assertEqual(
            msg, 'You are now watching issues and PRs on this project')

        # Create the ticket
        iss = pagure.lib.new_issue(
            issue_id=4,
            session=self.session,
            repo=project,
            title='test issue',
            content='content test issue',
            user='pingou',
            private=True,
            ticketfolder=None,
        )
        self.session.commit()
        self.assertEqual(iss.id, 4)
        self.assertEqual(iss.title, 'test issue')

        self.assertEqual(
            pagure.lib.get_watch_list(self.session, iss),
            set(['pingou'])
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
