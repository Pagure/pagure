# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Adam Williamson <awilliam@redhat.com>

"""

import unittest
import sys
import os

import mock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib           # pylint: disable=wrong-import-position
import pagure.lib.model     # pylint: disable=wrong-import-position
import pagure.lib.notify    # pylint: disable=wrong-import-position
import tests                # pylint: disable=wrong-import-position


class PagureLibNotifyEmailtests(tests.Modeltests):
    """ Some tests for the various email construction functions. In
    their own class so they can have some shared fixtures.
    """

    def setUp(self):
        """ Override setUp to add more fixtures used for many tests. """
        super(PagureLibNotifyEmailtests, self).setUp()
        pagure.SESSION = self.session
        tests.create_projects(self.session)

        # we don't want to send any mails while setting up
        patcher = mock.patch('pagure.lib.notify.send_email')
        patcher.start()

        self.user1 = pagure.lib.get_user(self.session, 'pingou')
        self.user2 = pagure.lib.get_user(self.session, 'foo')
        self.project1 = pagure.lib._get_project(self.session, 'test')
        self.project2 = pagure.lib._get_project(self.session, 'test2')
        self.project3 = pagure.lib._get_project(self.session, 'test3', namespace='somenamespace')

        # Create a forked repo, should be project #4
        # Not using fork_project as it tries to do a git clone
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            description='test project #1',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbyyy',
        )
        self.session.add(item)
        self.session.commit()
        self.forkedproject = pagure.lib._get_project(self.session, 'test', user='foo')

        # Report an issue on project #1
        self.issue1 = pagure.lib.new_issue(
            session=self.session,
            repo=self.project1,
            title='issue',
            content='a bug report',
            user='pingou',
            ticketfolder=None,
        )

        # Add a comment on the issue
        pagure.lib.add_issue_comment(
            self.session,
            self.issue1,
            comment='Test comment',
            user='pingou',
            ticketfolder=None,
        )
        self.comment1 = pagure.lib.get_issue_comment(self.session, self.issue1.uid, 1)

        # Report an issue on project #3 (namespaced)
        self.issue2 = pagure.lib.new_issue(
            session=self.session,
            repo=self.project3,
            title='namespaced project issue',
            content='a bug report on a namespaced project',
            user='pingou',
            ticketfolder=None,
        )

        # report an issue on foo's fork of project #1
        self.issue3 = pagure.lib.new_issue(
            session=self.session,
            repo=self.forkedproject,
            title='forked project issue',
            content='a bug report on a forked project',
            user='pingou',
            ticketfolder=None,
        )

        patcher.stop()

    @mock.patch('pagure.lib.notify.send_email')
    def test_notify_new_comment(self, fakemail):
        """Simple test for notification about new comment."""
        exptext = u"""
pingou added a new comment to an issue you are following:
``
Test comment
``

To reply, visit the link below
https://pagure.org/test/issue/1
"""
        pagure.lib.notify.notify_new_comment(self.comment1)
        (_, args, kwargs) = fakemail.mock_calls[0]

        # Mail text should be as expected.
        self.assertEqual(args[0], exptext)

        # Mail subject should be as expected.
        self.assertEqual(args[1], u'Issue #1: issue')

        # Mail should be sent to user #1.
        self.assertEqual(args[2], self.user1.default_email)

        # Mail ID should be comment #1's mail ID...
        self.assertEqual(kwargs['mail_id'], self.comment1.mail_id)

        # In reply to issue #1's mail ID.
        self.assertEqual(kwargs['in_reply_to'], self.issue1.mail_id)

        # Project name should be...project (full) name.
        self.assertEqual(kwargs['project_name'], self.project1.fullname)

        # Mail should be from user1 (who wrote the comment).
        self.assertEqual(kwargs['user_from'], self.user1.fullname)

    @mock.patch('pagure.lib.notify.send_email')
    def test_notify_new_issue_namespaced(self, fakemail):   # pylint: disable=invalid-name
        """Test for notifying of a new issue, namespaced project."""
        exptext = u"""
pingou reported a new issue against the project: `test3` that you are following:
``
a bug report on a namespaced project
``

To reply, visit the link below
https://pagure.org/somenamespace/test3/issue/1
"""
        pagure.lib.notify.notify_new_issue(self.issue2)
        (_, args, kwargs) = fakemail.mock_calls[0]

        # Mail text should be as expected.
        self.assertEqual(args[0], exptext)

        # Mail subject should be as expected.
        self.assertEqual(args[1], u'Issue #1: namespaced project issue')

        # Mail should be sent to user #1.
        self.assertEqual(args[2], self.user1.default_email)

        # Mail ID should be issue's mail ID.
        self.assertEqual(kwargs['mail_id'], self.issue2.mail_id)

        # Project name should be...project (full) name.
        self.assertEqual(kwargs['project_name'], self.project3.fullname)

        # Mail should be from user1 (who submitted the issue).
        self.assertEqual(kwargs['user_from'], self.user1.fullname)

    @mock.patch('pagure.lib.notify.send_email')
    def test_notify_assigned_issue_forked(self, fakemail):  # pylint: disable=invalid-name
        """Test for notifying re-assignment of issue on forked project.
        'foo' reassigns issue on his fork of 'test' to 'pingou'.
        """
        exptext = u"""
The issue: `forked project issue` of project: `test` has been assigned to `pingou` by foo.

https://pagure.org/fork/foo/test/issue/1
"""
        pagure.lib.notify.notify_assigned_issue(self.issue3, self.user1, self.user2)
        (_, args, kwargs) = fakemail.mock_calls[0]

        # Mail text should be as expected.
        self.assertEqual(args[0], exptext)

        # Mail subject should be as expected.
        self.assertEqual(args[1], u'Issue #1: forked project issue')

        # Mail should be sent to user #1.
        # NOTE: Not sent to user #2...
        self.assertEqual(args[2], self.user1.default_email)

        # Mail ID should contain issue's mail ID and '/assigned/'
        self.assertIn("{0}/assigned/".format(self.issue3.mail_id), kwargs['mail_id'])

        # Project name should be...project (full) name.
        self.assertEqual(kwargs['project_name'], self.forkedproject.fullname)

        # Mail should be from user1 (who submitted the issue).
        self.assertEqual(kwargs['user_from'], self.user2.fullname)

# Add more tests to verify that correct mails are sent to correct people here

if __name__ == '__main__':
    unittest.main(verbosity=2)
