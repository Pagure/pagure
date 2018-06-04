# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Lubomír Sedlář <lsedlar@redhat.com>

"""

from __future__ import unicode_literals

import mock
import os
import sys
import unittest

import six

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import pagure.lib.plugins
import pagure.lib.model
import pagure.hooks
import tests


class PagureFlaskQuickReplytest(tests.Modeltests):
    """ Tests for configuring and displaying quick replies. """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskQuickReplytest, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        self.admin = tests.FakeUser(username='pingou')
        self.user = tests.FakeUser(username='ralph')
        self.repo = pagure.lib._get_project(self.session, 'test')

    def disable_issues_and_pull_requests(self):
        """Disable both issues and pull requests."""
        # This can not use direct access as repo.settings is a property that
        # serializes data into JSON. Direct modification is not preserved.
        settings = self.repo.settings
        settings['issue_tracker'] = False
        settings['pull_requests'] = False
        self.repo.settings = settings
        self.session.add(self.repo)
        self.session.commit()

    def setup_quick_replies(self):
        """Create some quick replies.

        The full replies are stored as r1 and r2 attributes, with shortened
        versions in sr1 and sr2.
        """
        self.r1 = 'Ship it!'
        self.r2 = ('Nah. I would prefer if you did not submit this, as there '
                   'are problems.')
        self.sr1 = self.r1
        self.sr2 = 'Nah. I would prefer if you did not submit this, as...'

        # Set some quick replies
        self.repo.quick_replies = [self.r1, self.r2]
        self.session.add(self.repo)

    def assertRedirectToSettings(self, output, project='test', notice=None):
        """
        Check that user was redirected to settings page of a given project
        and that a given notice was printed.
        """
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>Settings - %s - Pagure</title>' % project,
            output_text)
        self.assertIn(
                '<h5 class="pl-2 font-weight-bold text-muted">'
                'Project Settings</h5>\n', output_text)
        if notice:
            self.assertIn(notice, output_text)

    def assertQuickReplies(self, quick_replies, project='test'):
        self.session.commit()
        repo = pagure.lib._get_project(self.session, project)
        self.assertEqual(repo.quick_replies, quick_replies)

    def assertQuickReplyLinks(self, output):
        """Assert reply links created by setup_quick_replies are present."""
        link = 'data-qr="%s">\s*%s\s*</a>'
        six.assertRegex(
            self,
            output.get_data(as_text=True),
            link % (self.r1, self.sr1))
        six.assertRegex(
            self,
            output.get_data(as_text=True),
            link % (self.r2, self.sr2))

    def test_new_project_has_none(self):
        self.assertQuickReplies([])

    def test_update_quick_reply_without_csrf(self):
        with tests.user_set(self.app.application, self.admin):
            output = self.app.get('/test/settings')
            self.assertEqual(output.status_code, 200)

            data = {
                'quick_reply': 'Ship it!',
            }
            output = self.app.post(
                '/test/update/quick_replies', data=data, follow_redirects=True)
            self.assertRedirectToSettings(output)
            self.assertQuickReplies([])

    def test_update_quick_replies_single(self):
        with tests.user_set(self.app.application, self.admin):
            data = {
                'quick_reply': 'Ship it!',
                'csrf_token': self.get_csrf(),
            }
            output = self.app.post(
                '/test/update/quick_replies', data=data, follow_redirects=True)
            self.assertRedirectToSettings(
                output, notice='quick replies updated')
            self.assertQuickReplies(['Ship it!'])
            self.assertIn('>Ship it!</textarea>', output.get_data(as_text=True))

    def test_update_quick_replies_multiple(self):
        with tests.user_set(self.app.application, self.admin):
            data = {
                'quick_reply': ['Ship it!', 'Nah.'],
                'csrf_token': self.get_csrf(),
            }
            output = self.app.post(
                '/test/update/quick_replies', data=data, follow_redirects=True)
            self.assertRedirectToSettings(
                output, notice='quick replies updated')
            self.assertQuickReplies(['Ship it!', 'Nah.'])
            # Check page has filled in textarea.
            self.assertIn('>Ship it!</textarea>', output.get_data(as_text=True))
            self.assertIn('>Nah.</textarea>', output.get_data(as_text=True))

    def test_update_quick_replies_empty_to_reset(self):
        # Set some quick replies
        repo = pagure.lib._get_project(self.session, 'test')
        repo.quick_replies = ['Ship it!', 'Nah.']
        self.session.add(repo)
        self.session.commit()

        with tests.user_set(self.app.application, self.admin):
            data = {
                'quick_reply': [],
                'csrf_token': self.get_csrf(),
            }
            output = self.app.post(
                '/test/update/quick_replies', data=data, follow_redirects=True)
            self.assertRedirectToSettings(
                output, notice='quick replies updated')
            self.assertQuickReplies([])

    def test_update_quick_replies_unprivileged(self):
        with tests.user_set(self.app.application, self.user):
            data = {
                'quick_reply': 'Ship it!',
                'csrf_token': 'a guess',
            }
            output = self.app.post(
                '/test/update/quick_replies', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 403)
            self.assertQuickReplies([])

    def test_no_form_with_disabled_issues_and_pull_requests(self):
        self.disable_issues_and_pull_requests()

        with tests.user_set(self.app.application, self.admin):
            output = self.app.get('/test/settings')
            self.assertNotIn('Quick replies', output.get_data(as_text=True))

    def test_no_submit_with_disabled_issues_and_pull_requests(self):
        self.disable_issues_and_pull_requests()

        with tests.user_set(self.app.application, self.admin):
            data = {
                'quick_reply': 'Ship it!',
                'csrf_token': 'a guess',
            }
            output = self.app.post(
                '/test/update/quick_replies', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)
            self.assertQuickReplies([])

    def test_submit_for_bad_project(self):
        with tests.user_set(self.app.application, self.admin):
            data = {
                'quick_reply': 'Ship it!',
                'csrf_token': 'a guess',
            }
            output = self.app.post(
                '/boom/update/quick_replies', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

    @mock.patch('pagure.lib.git.update_git')
    def test_issue_page_has_quick_replies(self, p_ugt):
        self.setup_quick_replies()

        issue = pagure.lib.new_issue(
            self.session,
            self.repo,
            'Dummy issue',
            'Just a lonely issue.',
            'pingou',
            None,
            notify=False
        )

        with tests.user_set(self.app.application, self.user):
            output = self.app.get('/test/issue/%s' % issue.id)
            self.assertEqual(output.status_code, 200)
            self.assertQuickReplyLinks(output)

    @mock.patch('pagure.lib.git.update_git')
    @mock.patch('pagure.lib.git.diff_pull_request')
    def test_pull_request_page_has_quick_replies(self, diff, p_ugt):
        diff.return_value = ([], [])

        self.setup_quick_replies()

        pr = pagure.lib.new_pull_request(
            self.session,
            'pr',
            self.repo,
            'master',
            'Dummy PR', 'pingou',
            None,
            repo_from=self.repo,
            notify=False,
        )

        with tests.user_set(self.app.application, self.user):
            output = self.app.get('/test/pull-request/%s' % pr.id)
            self.assertEqual(output.status_code, 200)
            self.assertQuickReplyLinks(output)


if __name__ == '__main__':
    unittest.main(verbosity=2)
