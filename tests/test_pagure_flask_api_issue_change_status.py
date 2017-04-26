# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import copy
import datetime
import unittest
import shutil
import sys
import time
import os

import json
from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests


class PagureFlaskApiIssueChangeStatustests(tests.Modeltests):
    """ Tests for the flask API of pagure for changing the status of an
    issue
    """

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiIssueChangeStatustests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.api.SESSION = self.session
        pagure.api.issue.SESSION = self.session
        pagure.lib.SESSION = self.session

        pagure.APP.config['TICKETS_FOLDER'] = None

        self.app = pagure.APP.test_client()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'tickets'))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create normal issue
        repo = pagure.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=False,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')

        # Create private issue
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this',
            user='foo',
            ticketfolder=None,
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')

    def test_api_change_status_issue_invalid_project(self):
        """ Test the api_change_status_issue method of the flask api. """

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foobar/issue/1/status', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Project not found",
              "error_code": "ENOPROJECT",
            }
        )

    def test_api_change_status_issue_token_not_for_project(self):
        """ Test the api_change_status_issue method of the flask api. """

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Valid token, wrong project
        output = self.app.post('/api/0/test2/issue/1/status', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

    def test_api_change_status_issue_invalid_issue(self):
        """ Test the api_change_status_issue method of the flask api. """

        headers = {'Authorization': 'token aaabbbcccddd'}

        # No issue
        output = self.app.post('/api/0/test/issue/42/status', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Issue not found",
              "error_code": "ENOISSUE",
            }
        )

    def test_api_change_status_issue_incomplete(self):
        """ Test the api_change_status_issue method of the flask api. """

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Check status before
        repo = pagure.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.status, 'Open')

        data = {
            'title': 'test issue',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test/issue/1/status', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": "EINVALIDREQ",
              "errors": {"status": ["Not a valid choice"]}
            }
        )

        # No change
        repo = pagure.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.status, 'Open')

    def test_api_change_status_issue_no_change(self):
        """ Test the api_change_status_issue method of the flask api. """

        headers = {'Authorization': 'token aaabbbcccddd'}

        data = {
            'status': 'Open',
        }

        # Valid request but no change
        output = self.app.post(
            '/api/0/test/issue/1/status', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'No changes'}
        )

        # No change
        repo = pagure.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.status, 'Open')

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_change_status_issue(self):
        """ Test the api_change_status_issue method of the flask api. """

        headers = {'Authorization': 'token aaabbbcccddd'}

        data = {
            'status': 'Fixed',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/issue/1/status', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)

        self.assertDictEqual(
            data,
            {'message':[
                'Issue status updated to: Closed (was: Open)',
                'Issue close_status updated to: Fixed'
            ]}
        )

        headers = {'Authorization': 'token pingou_foo'}

        # Un-authorized issue
        output = self.app.post(
            '/api/0/foo/issue/1/status', data=data, headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
