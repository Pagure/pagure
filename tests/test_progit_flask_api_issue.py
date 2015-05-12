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

import json
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskApiIssuetests(tests.Modeltests):
    """ Tests for the flask API of pagure for issue """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiIssuetests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.api.SESSION = self.session
        pagure.api.issue.SESSION = self.session
        pagure.lib.SESSION = self.session

        pagure.APP.config['TICKETS_FOLDER'] = None

        self.app = pagure.APP.test_client()

    def test_api_new_issue(self):
        """ Test the api_new_issue method of the flask api. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(tests.HERE, 'tickets'))
        tests.create_tokens(self.session)
        tests.create_acls(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Valid token, wrong project
        output = self.app.post('/api/0/test2/new_issue', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or expired token. Please visit " \
                  "https://pagure.org/ get or renew your API token.",
              "error_code": 5
            }
        )

        # No input
        output = self.app.post('/api/0/test/new_issue', headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": 4
            }
        )

        data = {
            'title': 'test issue',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": 4
            }
        )

        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'status': 'Open',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'issue created'}
        )

    def test_api_view_issue(self):
        """ Test the api_view_issue method of the flask api. """
        self.test_api_new_issue()

        # Invalid repo
        output = self.app.get('/api/0/foo/issue/1')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Project not found",
              "error_code": 1
            }
        )

        # Invalid issue for this repo
        output = self.app.get('/api/0/test2/issue/1')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Issue not found",
              "error_code": 6
            }
        )

        # Valid issue
        output = self.app.get('/api/0/test/issue/1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['date_created'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "assignee": None,
              "blocks": [],
              "comments": [],
              "content": "This issue needs attention",
              "date_created": "1431414800",
              "depends": [],
              "id": 1,
              "private": False,
              "status": "Open",
              "tags": [],
              "title": "test issue",
              "user": {
                "default_email": "bar@pingou.com",
                "emails": [
                  "bar@pingou.com",
                  "foo@pingou.com"
                ],
                "fullname": "PY C",
                "name": "pingou"
              }
            }
        )

        # Create private issue
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Access private issue un-authenticated
        output = self.app.get('/api/0/test/issue/2')
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "You are not allowed to view this issue",
              "error_code": 7
            }
        )

        headers = {'Authorization': 'token aaabbbccc'}

        # Access private issue authenticated but wrong token
        output = self.app.get('/api/0/test/issue/2', headers=headers)
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "You are not allowed to view this issue",
              "error_code": 7
            }
        )

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Access private issue authenticated correctly
        output = self.app.get('/api/0/test/issue/2', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['date_created'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "assignee": None,
              "blocks": [],
              "comments": [],
              "content": "We should work on this",
              "date_created": "1431414800",
              "depends": [],
              "id": 2,
              "private": True,
              "status": "Open",
              "tags": [],
              "title": "Test issue",
              "user": {
                "default_email": "bar@pingou.com",
                "emails": [
                  "bar@pingou.com",
                  "foo@pingou.com"
                ],
                "fullname": "PY C",
                "name": "pingou"
              }
            }
        )


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskApiIssuetests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
