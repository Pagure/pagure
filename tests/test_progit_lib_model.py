# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib
import tests


class ProgitLibModeltests(tests.Modeltests):
    """ Tests for progit.lib.model """

    def test_user__repr__(self):
        """ Test the User.__repr__ function of progit.lib.model. """
        item = progit.lib.search_user(self.session, email='foo@bar.com')
        self.assertEqual(str(item), 'User: 2 - name foo')
        self.assertEqual('foo', item.user)
        self.assertEqual('foo', item.username)
        self.assertEqual([], item.groups)

    @patch('progit.lib.git.update_git')
    @patch('progit.lib.notify.send_email')
    def test_issue__repr__(self, p_send_email, p_ugt):
        """ Test the Issue.__repr__ function of progit.lib.model. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        repo = progit.lib.get_project(self.session, 'test')

        # Create an issue
        msg = progit.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.assertEqual(msg, 'Issue created')

        issues = progit.lib.search_issues(self.session, repo)
        self.assertEqual(len(issues), 1)
        self.assertEqual(
            str(issues[0]),
            'Issue(1, project:test, user:pingou, title:Test issue)')

    @patch('progit.lib.git.update_git')
    @patch('progit.lib.notify.send_email')
    def test_pullrequest__repr__(self, p_send_email, p_ugt):
        """ Test the PullRequest.__repr__ function of progit.lib.model. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        # Create a forked repo
        item = progit.lib.model.Project(
            user_id=1,  # pingou
            name='test',
            description='test project #1',
            parent_id=1,
        )
        self.session.commit()
        self.session.add(item)

        repo = progit.lib.get_project(self.session, 'test')
        forked_repo = progit.lib.get_project(
            self.session, 'test', user='pingou')

        # Create an pull-request
        msg = progit.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
            requestfolder=None,
        )
        self.assertEqual(msg, 'Request created')

        request = progit.lib.search_pull_requests(self.session, requestid=1)
        self.assertEqual(
            str(request),
            'PullRequest(1, project:test, user:pingou, '
            'title:test pull-request)')

    def test_progitgroup__repr__(self):
        """ Test the ProgitGroup.__repr__ function of progit.lib.model. """
        item = progit.lib.model.ProgitGroup(
            group_name='admin',
        )
        self.session.add(item)
        self.session.commit()

        self.assertEqual(str(item), 'Group: 1 - name admin')

if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitLibModeltests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
