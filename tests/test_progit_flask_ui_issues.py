# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
import unittest
import shutil
import sys
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib
import tests


class ProgitFlaskIssuestests(tests.Modeltests):
    """ Tests for flask docs of progit """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(ProgitFlaskIssuestests, self).setUp()

        progit.APP.config['TESTING'] = True
        progit.SESSION = self.session
        progit.ui.SESSION = self.session
        progit.ui.app.SESSION = self.session
        progit.ui.issues.SESSION = self.session
        progit.ui.repo.SESSION = self.session

        progit.APP.config['GIT_FOLDER'] = tests.HERE
        progit.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        progit.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        progit.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = progit.APP.test_client()

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_new_issue(self, p_send_email, p_ugt):
        """ Test the new_issue endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/new_issue')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/foo/new_issue')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.get('/test/new_issue')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New issue</h2>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
            }

            # Insufficient input
            output = self.app.post('/test/new_issue', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New issue</h2>' in output.data)
            self.assertEqual(output.data.count(
                '<td class="errors">This field is required.</td>'), 2)

            data['title'] = 'Test issue'
            output = self.app.post('/test/new_issue', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New issue</h2>' in output.data)
            self.assertEqual(output.data.count(
                '<td class="errors">This field is required.</td>'), 1)

            data['issue_content'] = 'We really should improve on this issue'
            data['status'] = 'Open'
            output = self.app.post('/test/new_issue', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New issue</h2>' in output.data)
            self.assertEqual(output.data.count(
                '<td class="errors">This field is required.</td>'), 0)

            # Invalid user
            data['csrf_token'] = csrf_token
            output = self.app.post('/test/new_issue', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New issue</h2>' in output.data)
            self.assertEqual(output.data.count(
                '<td class="errors">This field is required.</td>'), 0)
            self.assertTrue(
                '<li class="error">No user &#34;username&#34; found</li>'
                in output.data)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.post(
                '/test/new_issue', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="message">Issue created</li>' in output.data)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue('<h2>\n    Issues (1)\n  </h2>' in output.data)

    @patch('progit.lib.git.update_git_ticket')
    @patch('progit.lib.notify.send_email')
    def test_view_issues(self, p_send_email, p_ugt):
        """ Test the view_issues endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        output = self.app.get('/foo/issues')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/issues')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue('<h2>\n    Issues (0)\n  </h2>' in output.data)

        # Create issues to play with
        repo = progit.lib.get_project(self.session, 'test')
        msg = progit.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg, 'Issue created')

        # Whole list
        output = self.app.get('/test/issues')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue('<h2>\n    Issues (1)\n  </h2>' in output.data)

        # Status = closed
        output = self.app.get('/test/issues?status=cloSED')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue(
            '<h2>\n    Closed\n    Issues (0)\n  </h2>' in output.data)

        # Status = fixed
        output = self.app.get('/test/issues?status=fixed')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue(
            '<h2>\n    Closed\n    Issues (0)\n  </h2>' in output.data)

        # Project w/o issue tracker
        repo = progit.lib.get_project(self.session, 'test')
        repo.issue_tracker = False
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/issues')
        self.assertEqual(output.status_code, 404)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitFlaskIssuestests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
