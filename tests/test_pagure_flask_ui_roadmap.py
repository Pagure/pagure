# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

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

import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskRoadmaptests(tests.Modeltests):
    """ Tests for the pagure's roadmap """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskRoadmaptests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.filters.SESSION = self.session
        pagure.ui.repo.SESSION = self.session
        pagure.ui.issues.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = tests.HERE
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            tests.HERE, 'requests')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = pagure.APP.test_client()

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_ticket_with_no_roadmap(self, p_send_email, p_ugt):
        """ Test creating a ticket without roadmap. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(tests.HERE), bare=True)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            # Get the CSRF token
            output = self.app.get('/test/new_issue')
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                u'<div class="card-header">\n        New issue'
                in output.data)

            csrf_token = output.data.split(
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
            self.assertIn(
                u'<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                u'<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_ticket_with_roadmap(self, p_send_email, p_ugt):
        """ Test creating a ticket with roadmap. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(tests.HERE), bare=True)

        # Set some milestone
        repo = pagure.lib.get_project(self.session, 'test')
        repo.milestone = {'v1.0': '', 'v2.0': 'Tomorrow!'}
        self.session.add(repo)
        self.session.commit()

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            # Get the CSRF token
            output = self.app.get('/test/new_issue')
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                u'<div class="card-header">\n        New issue'
                in output.data)

            csrf_token = output.data.split(
                u'name="csrf_token" type="hidden" value="')[1].split(u'">')[0]

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
            self.assertIn(
                u'<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                u'<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)

            # Mark the ticket for the roadmap
            data = {
                'tag': 'roadmap',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/issue/1/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                u'<title>Issue #1: Test issue - test - Pagure</title>',
                output.data)
            self.assertIn(
                u'<a class="btn btn-primary btn-sm" '
                'href="/test/issue/1/edit" title="Edit this issue">',
                output.data)


    def test_update_milestones(self):
        """ Test updating milestones of a repo. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(tests.HERE), bare=True)

        # Set some milestones
        repo = pagure.lib.get_project(self.session, 'test')
        self.assertEqual(repo.milestones, {})

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            # Get the CSRF token
            output = self.app.get('/test/settings')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                u'<title>Settings - test - Pagure</title>', output.data)
            self.assertIn(u'<h3>Settings for test</h3>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'milestones': 1,
                'milestone_dates': 'Tomorrow',
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            # Check the redirect
            self.assertIn(
                u'<title>Settings - test - Pagure</title>', output.data)
            self.assertIn('<h3>Settings for test</h3>', output.data)
            # Check the result of the action -- None, no CSRF
            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(repo.milestones, {})

            data = {
                'milestones': 1,
                'milestone_dates': 'Tomorrow',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            # Check the redirect
            self.assertIn(
                u'<title>Settings - test - Pagure</title>', output.data)
            self.assertIn(u'<h3>Settings for test</h3>', output.data)
            self.assertIn(u'Milestones updated', output.data)
            # Check the result of the action -- Milestones recorded
            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(repo.milestones, {u'1': u'Tomorrow'})

            data = {
                'milestones': ['v1.0', 'v2.0'],
                'milestone_dates': ['Tomorrow', ''],
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            # Check the redirect
            self.assertIn(
                u'<title>Settings - test - Pagure</title>', output.data)
            self.assertIn(u'<h3>Settings for test</h3>', output.data)
            self.assertIn(u'Milestones updated', output.data)
            # Check the result of the action -- Milestones recorded
            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(
                repo.milestones, {u'v1.0': u'Tomorrow', u'v2.0': u''}
            )

            # Check error - less milestones than dates
            data = {
                'milestones': ['v1.0', 'v2.0'],
                'milestone_dates': ['Tomorrow', 'Next week', 'Next Year'],
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            # Check the redirect
            self.assertIn(
                u'<title>Settings - test - Pagure</title>', output.data)
            self.assertIn(u'<h3>Settings for test</h3>', output.data)
            self.assertIn(
                u'</button>\n'
                '                      Milestones and dates are not of the '
                'same length', output.data)
            # Check the result of the action -- Milestones un-changed
            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(
                repo.milestones, {u'v1.0': u'Tomorrow', u'v2.0': u''}
            )

            # Check error - Twice the same milestone
            data = {
                'milestones': ['v1.0', 'v2.0', 'v2.0'],
                'milestone_dates': ['Tomorrow', 'Next week', 'Next Year'],
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            # Check the redirect
            self.assertIn(
                u'<title>Settings - test - Pagure</title>', output.data)
            self.assertIn(u'<h3>Settings for test</h3>', output.data)
            self.assertIn(
                u'</button>\n'
                '                      Milestone v2.0 is present 2 times',
                output.data)
            # Check the result of the action -- Milestones un-changed
            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(
                repo.milestones, {u'v1.0': u'Tomorrow', u'v2.0': u''}
            )

            # Check error - Twice the same date
            data = {
                'milestones': ['v1.0', 'v2.0', 'v3.0'],
                'milestone_dates': ['Tomorrow', 'Next week', 'Next week'],
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            # Check the redirect
            self.assertIn(
                u'<title>Settings - test - Pagure</title>', output.data)
            self.assertIn(u'<h3>Settings for test</h3>', output.data)
            self.assertIn(
                u'</button>\n'
                '                      Date Next week is present 2 times',
                output.data)
            # Check the result of the action -- Milestones un-changed
            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(
                repo.milestones, {u'v1.0': u'Tomorrow', u'v2.0': u''}
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
        with tests.user_set(pagure.APP, user):
            output = self.app.post(
                '/test/update/milestones', data=data)
            self.assertEqual(output.status_code, 403)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_milestones_without_dates(self, p_send_email, p_ugt):
        """ Test creating two milestones with no dates. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(tests.HERE), bare=True)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            # Get the CSRF token
            output = self.app.get('/test/settings')
            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'milestones': ['v1.0', 'v2.0'],
                'milestone_dates': ['', ''],
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            # Check the redirect
            self.assertIn(
                u'<title>Settings - test - Pagure</title>', output.data)
            self.assertIn(u'<h3>Settings for test</h3>', output.data)
            self.assertIn(u'Milestones updated', output.data)
            # Check the result of the action -- Milestones recorded
            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(repo.milestones, {u'v1.0': u'', u'v2.0': u''})

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_roadmap_ui(self, p_send_email, p_ugt):
        """ Test viewing the roadmap of a repo. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_update_milestones()

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            # Get the CSRF token
            output = self.app.get('/test/new_issue')
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                u'<div class="card-header">\n        New issue'
                in output.data)

            csrf_token = output.data.split(
                u'name="csrf_token" type="hidden" value="')[1].split(u'">')[0]

            # Create an unplanned milestone
            data = {
                'milestones': ['v1.0', 'v2.0', 'unplanned'],
                'milestone_dates': ['Tomorrow', '', ''],
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update/milestones', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            # Check the redirect
            self.assertIn(
                u'<title>Settings - test - Pagure</title>', output.data)
            self.assertIn(u'<h3>Settings for test</h3>', output.data)
            self.assertIn(u'Milestones updated', output.data)
            # Check the result of the action -- Milestones recorded
            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(
                repo.milestones,
                {
                    u'v1.0': u'Tomorrow', u'v2.0': u'', u'unplanned': u''
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
                self.assertIn(
                    u'<title>Issue #{0}: Test issue {0} - test - '
                    'Pagure</title>'.format(cnt),
                    output.data)
                self.assertIn(
                    u'<a class="btn btn-primary btn-sm" '
                    'href="/test/issue/%s/edit" title="Edit this '
                    'issue">' % cnt,
                    output.data)

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
                self.assertIn(
                    u'<title>Issue #{0}: Test issue {0} - test - '
                    'Pagure</title>'.format(cnt),
                    output.data)
                self.assertIn(
                    u'<a class="btn btn-primary btn-sm" '
                    'href="/test/issue/%s/edit" title="Edit this '
                    'issue">' % cnt,
                    output.data)
                self.assertIn(
                    u'</button>\n                      '
                    u'Successfully edited issue #%s' % cnt,
                    output.data)

        repo = pagure.lib.get_project(self.session, 'test')

        # Mark ticket #1 as Fixed
        for iid in [1, 4]:
            ticket = pagure.lib.search_issues(
                self.session,
                repo,
                issueid=iid
            )
            ticket.status = 'Fixed'
            self.session.add(ticket)
            self.session.commit()

        # test the roadmap view
        output = self.app.get('/test/roadmap')
        self.assertEqual(output.status_code, 200)
        self.assertIn(u'2 Milestones', output.data)
        self.assertIn(u'Milestone: v2.0', output.data)
        self.assertIn(u'Milestone: unplanned', output.data)
        self.assertEqual(
            output.data.count(u'<span class="label label-default">#'), 4)

        # test the roadmap view for all milestones
        output = self.app.get('/test/roadmap?status=All')
        self.assertEqual(output.status_code, 200)
        self.assertIn(u'3 Milestones', output.data)
        self.assertIn(u'Milestone: v1.0', output.data)
        self.assertIn(u'Milestone: v2.0', output.data)
        self.assertIn(u'Milestone: unplanned', output.data)
        self.assertEqual(
            output.data.count(u'<span class="label label-default">#'), 6)

        # test the roadmap view for a specific milestone
        output = self.app.get('/test/roadmap?milestone=v2.0')
        self.assertEqual(output.status_code, 200)
        self.assertIn(u'1 Milestones', output.data)
        self.assertIn(u'Milestone: v2.0', output.data)
        self.assertEqual(
            output.data.count(u'<span class="label label-default">#'), 2)

        # test the roadmap view for a specific milestone - closed
        output = self.app.get('/test/roadmap?milestone=v1.0')
        self.assertEqual(output.status_code, 200)
        self.assertIn(u'1 Milestones', output.data)
        self.assertIn(u'Milestone: v1.0', output.data)
        self.assertEqual(
            output.data.count(u'<span class="label label-default">#'), 0)

        # test the roadmap view for a specific milestone - closed
        output = self.app.get('/test/roadmap?milestone=v1.0&status=All')
        self.assertEqual(output.status_code, 200)
        self.assertIn(u'1 Milestones', output.data)
        self.assertIn(u'Milestone: v1.0', output.data)
        self.assertEqual(
            output.data.count(u'<span class="label label-default">#'), 2)

        # test the roadmap view for errors
        output = self.app.get('/foo/roadmap')
        self.assertEqual(output.status_code, 404)

        repo = pagure.lib.get_project(self.session, 'test')
        settings = repo.settings
        settings['issue_tracker'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/roadmap', data=data)
        self.assertEqual(output.status_code, 404)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskRoadmaptests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
