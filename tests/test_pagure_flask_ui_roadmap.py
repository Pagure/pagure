# -*- coding: utf-8 -*-

"""
 (c) 2016-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import datetime
import json
import unittest
import shutil
import sys
import tempfile
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskRoadmaptests(tests.Modeltests):
    """ Tests for the pagure's roadmap """

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_ticket_with_no_roadmap(self, p_send_email, p_ugt):
        """ Test creating a ticket without roadmap. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):

            # Get the CSRF token
            output = self.app.get('/test/new_issue')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertTrue(
                '<div class="card-header">\n        New issue'
                in output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'title': 'Test issue',
                'issue_content': 'We really should improve on this issue',
                'status': 'Open',
                'csrf_token': csrf_token,
            }

            # Create the issue
            output = self.app.post(
                '/test/new_issue', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_ticket_with_roadmap(self, p_send_email, p_ugt):
        """ Test creating a ticket with roadmap. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        # Set some milestone
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        repo.milestone = {'v1.0': '', 'v2.0': 'Tomorrow!'}
        self.session.add(repo)
        self.session.commit()

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):

            # Get the CSRF token
            output = self.app.get('/test/new_issue')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertTrue(
                '<div class="card-header">\n        New issue'
                in output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'title': 'Test issue',
                'issue_content': 'We really should improve on this issue',
                'status': 'Open',
                'csrf_token': csrf_token,
            }

            # Create the issue
            output = self.app.post(
                '/test/new_issue', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text)

            # Mark the ticket for the roadmap
            data = {
                'tag': 'roadmap',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Issue #1: Test issue - test - Pagure</title>',
                output_text)
            self.assertIn(
                '<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output_text)

    def test_update_milestones(self):
        """ Test updating milestones of a repo. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        # Set some milestones
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertEqual(repo.milestones, {})

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):

            # Get the CSRF token
            output = self.app.get('/test/settings')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output_text)
            self.assertIn('<h3>Settings for test</h3>', output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'milestones': 1,
                'milestone_dates': 'Tomorrow',
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output_text)
            self.assertIn('<h3>Settings for test</h3>', output_text)
            # Check the result of the action -- None, no CSRF
            repo = pagure.lib.get_authorized_project(self.session, 'test')
            self.assertEqual(repo.milestones, {})

            data = {
                'milestones': 1,
                'milestone_dates': 'Tomorrow',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output_text)
            self.assertIn('<h3>Settings for test</h3>', output_text)
            self.assertIn('Milestones updated', output_text)
            # Check the result of the action -- Milestones recorded
            self.session.commit()
            repo = pagure.lib.get_authorized_project(self.session, 'test')
            self.assertEqual(repo.milestones, {'1': {'active': False, 'date': None}})

            data = {
                'milestones': ['v1.0', 'v2.0'],
                'milestone_dates_1': 'Tomorrow',
                'milestone_dates_2': '',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output_text)
            self.assertIn('<h3>Settings for test</h3>', output_text)
            self.assertIn('Milestones updated', output_text)
            # Check the result of the action -- Milestones recorded
            self.session.commit()
            repo = pagure.lib.get_authorized_project(self.session, 'test')
            self.assertEqual(
                repo.milestones,
                {
                    'v1.0': {'active': False, 'date': None},
                    'v2.0': {'active': False, 'date': None}
                }
            )

            # Check error - less milestones than dates
            data = {
                'milestones': ['v1.0', 'v2.0'],
                'milestone_date_1': 'Tomorrow',
                'milestone_date_2': 'Next week',
                'milestone_date_3': 'Next Year',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output_text)
            self.assertIn('<h3>Settings for test</h3>', output_text)
            # Check the result of the action -- Milestones un-changed
            self.session.commit()
            repo = pagure.lib.get_authorized_project(self.session, 'test')
            self.assertEqual(
                repo.milestones,
                {
                    'v1.0': {'active': False, 'date': 'Tomorrow'},
                    'v2.0': {'active': False, 'date': 'Next week'}
                }
            )

            # Check error - Twice the same milestone
            data = {
                'milestones': ['v1.0', 'v2.0', 'v2.0'],
                'milestone_date_1': 'Tomorrow',
                'milestone_date_2': 'Next week',
                'milestone_date_3': 'Next Year',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output_text)
            self.assertIn('<h3>Settings for test</h3>', output_text)
            self.assertIn(
                '</button>\n'
                '                      Milestone v2.0 is present 2 times',
                output_text)
            # Check the result of the action -- Milestones un-changed
            self.session.commit()
            repo = pagure.lib.get_authorized_project(self.session, 'test')
            self.assertEqual(
                repo.milestones,
                {
                    'v1.0': {'active': False, 'date': 'Tomorrow'},
                    'v2.0': {'active': False, 'date': 'Next week'}
                }
            )

            # Check error - Twice the same date
            data = {
                'milestones': ['v1.0', 'v2.0', 'v3.0'],
                'milestone_date_1': 'Tomorrow',
                'milestone_date_2': 'Next week',
                'milestone_date_3': 'Next week',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output_text)
            self.assertIn('<h3>Settings for test</h3>', output_text)
            self.assertIn(
                '</button>\n'
                '                      Milestones updated',
                output_text)
            # Check the result of the action -- Milestones updated
            self.session.commit()
            repo = pagure.lib.get_authorized_project(self.session, 'test')
            self.assertEqual(
                repo.milestones,
                {
                    'v1.0': {'active': False, 'date': 'Tomorrow'},
                    'v2.0': {'active': False, 'date': 'Next week'},
                    'v3.0': {'active': False, 'date': 'Next week'},
                }
            )

            # Check for an invalid project
            output = self.app.post(
                '/foo/update/milestones', data=data)
            self.assertEqual(output.status_code, 404)

            # Check the behavior if the project disabled the issue tracker
            settings = repo.settings
            settings['issue_tracker'] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/update/milestones', data=data)
            self.assertEqual(output.status_code, 404)

        # Check for a non-admin user
        settings = repo.settings
        settings['issue_tracker'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        user.username = 'ralph'
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                '/test/update/milestones', data=data)
            self.assertEqual(output.status_code, 403)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_milestones_without_dates(self, p_send_email, p_ugt):
        """ Test creating two milestones with no dates. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            # Get the CSRF token
            output = self.app.get('/test/settings')
            output_text = output.get_data(as_text=True)
            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'milestones': ['v1.0', 'v2.0'],
                'milestone_dates': ['', ''],
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output_text)
            self.assertIn('<h3>Settings for test</h3>', output_text)
            self.assertIn('Milestones updated', output_text)
            # Check the result of the action -- Milestones recorded
            self.session.commit()
            repo = pagure.lib.get_authorized_project(self.session, 'test')
            self.assertEqual(
                repo.milestones,
                {
                    'v1.0': {'active': False, 'date': None},
                    'v2.0': {'active': False, 'date': None}
                }
            )

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_roadmap_ui(self, p_send_email, p_ugt):
        """ Test viewing the roadmap of a repo. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_update_milestones()

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):

            # Get the CSRF token
            output = self.app.get('/test/new_issue')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertTrue(
                '<div class="card-header">\n        New issue'
                in output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Create an unplanned milestone
            data = {
                'milestones': ['v1.0', 'v2.0', 'unplanned'],
                'milestone_date_1': 'Tomorrow',
                'milestone_date_2': '',
                'milestone_date_3': '',
                'active_milestone_1': True,
                'active_milestone_2': True,
                'active_milestone_3': True,
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # Check the redirect
            self.assertIn(
                '<title>Settings - test - Pagure</title>', output_text)
            self.assertIn('<h3>Settings for test</h3>', output_text)
            self.assertIn('Milestones updated', output_text)
            # Check the result of the action -- Milestones recorded
            self.session.commit()
            repo = pagure.lib._get_project(self.session, 'test')
            self.assertEqual(
                repo.milestones,
                {
                    'unplanned': {'active': True, 'date': None},
                    'v1.0': {'active': True, 'date': 'Tomorrow'},
                    'v2.0': {'active': True, 'date': None}
                }
            )

            # Create the issues
            for cnt in range(6):
                cnt += 1
                data = {
                    'title': 'Test issue %s' % cnt,
                    'issue_content': 'We really should improve on this '
                    'issue %s' % cnt,
                    'csrf_token': csrf_token,
                }

                output = self.app.post(
                    '/test/new_issue', data=data, follow_redirects=True)
                self.assertEqual(output.status_code, 200)
                output_text = output.get_data(as_text=True)
                self.assertIn(
                    '<title>Issue #{0}: Test issue {0} - test - '
                    'Pagure</title>'.format(cnt),
                    output_text)
                self.assertIn(
                    '<a class="btn btn-primary btn-sm" '
                    'href="/test/issue/%s/edit" title="Edit this '
                    'issue">' % cnt,
                    output_text)

                # Mark the ticket for the roadmap
                mstone = 'v%s.0' % cnt
                if cnt >= 3:
                    if (cnt % 3) == 0:
                        mstone = 'unplanned'
                    else:
                        mstone = 'v%s.0' % (cnt % 3)
                data = {
                    'milestone': mstone,
                    'csrf_token': csrf_token,
                }
                output = self.app.post(
                    '/test/issue/%s/update' % cnt, data=data,
                    follow_redirects=True)
                self.assertEqual(output.status_code, 200)
                output_text = output.get_data(as_text=True)
                self.assertIn(
                    '<title>Issue #{0}: Test issue {0} - test - '
                    'Pagure</title>'.format(cnt),
                    output_text)
                self.assertIn(
                    '<a class="btn btn-primary btn-sm" '
                    'href="/test/issue/%s/edit" title="Edit this '
                    'issue">' % cnt,
                    output_text)
                self.assertIn(
                    '</button>\n                      '
                    'Issue set to the milestone: %s\n' % mstone,
                    output_text)

        repo = pagure.lib.get_authorized_project(self.session, 'test')

        # Mark ticket #1 as Fixed
        for iid in [1, 4]:
            ticket = pagure.lib.search_issues(
                self.session,
                repo,
                issueid=iid
            )
            ticket.status = 'Closed'
            ticket.close_status = 'Fixed'
            self.session.add(ticket)
            self.session.commit()

        # test the roadmap view
        output = self.app.get('/test/roadmap')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<th>v2.0', output_text)
        self.assertIn('<th>unplanned', output_text)
        self.assertEqual(
            output_text.count('<span class="label label-default">#'), 4)

        # test the roadmap view for all milestones
        output = self.app.get('/test/roadmap?all_stones=True&status=All')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<th>v1.0', output_text)
        self.assertIn('<th>v2.0', output_text)
        self.assertIn('<th>unplanned', output_text)
        self.assertEqual(
            output_text.count('<span class="label label-default">#'), 6)

        # test the roadmap view for a specific milestone
        output = self.app.get('/test/roadmap?milestone=v2.0')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<th>v2.0', output_text)
        self.assertEqual(
            output_text.count('<span class="label label-default">#'), 2)

        # test the roadmap view for a specific milestone - open
        output = self.app.get('/test/roadmap?milestone=v1.0')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('No issues found', output_text)
        self.assertEqual(
            output_text.count('<span class="label label-default">#'), 0)

        # test the roadmap view for a specific milestone - closed
        output = self.app.get(
            '/test/roadmap?milestone=v1.0&status=All&all_stones=True')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<th>v1.0', output_text)
        self.assertEqual(
            output_text.count('<span class="label label-default">#'), 2)

        # test the roadmap view for a specific tag
        output = self.app.get('/test/roadmap?milestone=v2.0&tag=unknown')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('No issues found', output_text)
        self.assertEqual(
            output_text.count('<span class="label label-default">#'), 0)

        # test the roadmap view for errors
        output = self.app.get('/foo/roadmap')
        self.assertEqual(output.status_code, 404)

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['issue_tracker'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/roadmap', data=data)
        self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_show_ban_lock_unlock_in_roadmap_ui(self, send_email, update_git):
        send_email.return_value = True
        update_git.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        repo.milestones = {'0.1': ''}

        issue_1 = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            milestone='0.1',
        )

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue_2 = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this again',
            user='foo',
            ticketfolder=None,
            milestone='0.1',
        )

        issue_1.children.append(issue_2)
        self.session.commit()

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/roadmap')
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="oi" data-glyph="ban" '
                'title="Issue blocked by one or more issue(s)"></span>',
                output_text)
            self.assertEqual(1, output_text.count(
                'title="Issue blocked by one or more issue(s)'))
            self.assertIn(
                '<span class="oi" data-glyph="lock-unlocked" '
                'title="Issue blocking one or more issue(s)"></span>',
                output_text)
            self.assertEqual(1, output_text.count(
                'title="Issue blocking one or more issue(s)'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
