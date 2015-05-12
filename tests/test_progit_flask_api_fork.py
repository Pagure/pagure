# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import datetime
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


class PagureFlaskApiForktests(tests.Modeltests):
    """ Tests for the flask API of pagure for issue """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiForktests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.api.SESSION = self.session
        pagure.api.fork.SESSION = self.session
        pagure.lib.SESSION = self.session

        pagure.APP.config['REQUESTS_FOLDER'] = None

        self.app = pagure.APP.test_client()

    def test_api_pull_request_view(self):
        """ Test the api_pull_request_view method of the flask api. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_acls(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.get_project(self.session, 'test')
        forked_repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(msg, 'Request created')

        # Invalid repo
        output = self.app.get('/api/0/foo/pull-request/1')
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
        output = self.app.get('/api/0/test2/pull-request/1')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Pull-Request not found",
              "error_code": 9
            }
        )

        # Valid issue
        output = self.app.get('/api/0/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['date_created'] = '1431414800'
        data['project']['date_created'] = '1431414800'
        data['repo_from']['date_created'] = '1431414800'
        data['uid'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "assignee": None,
              "branch": "master",
              "branch_from": "master",
              "comments": [],
              "commit_start": None,
              "commit_stop": None,
              "date_created": "1431414800",
              "id": 1,
              "project": {
                "date_created": "1431414800",
                "description": "test project #1",
                "id": 1,
                "name": "test",
                "parent": None,
                "settings": {
                  "Minimum_score_to_merge_pull-request": -1,
                  "Only_assignee_can_merge_pull-request": False,
                  "Web-hooks": None,
                  "issue_tracker": True,
                  "project_documentation": True,
                  "pull_requests": True
                },
                "user": {
                  "emails": [
                    "bar@pingou.com",
                    "foo@pingou.com"
                  ],
                  "fullname": "PY C",
                  "name": "pingou"
                }
              },
              "repo_from": {
                "date_created": "1431414800",
                "description": "test project #1",
                "id": 1,
                "name": "test",
                "parent": None,
                "settings": {
                  "Minimum_score_to_merge_pull-request": -1,
                  "Only_assignee_can_merge_pull-request": False,
                  "Web-hooks": None,
                  "issue_tracker": True,
                  "project_documentation": True,
                  "pull_requests": True
                },
                "user": {
                  "emails": [
                    "bar@pingou.com",
                    "foo@pingou.com"
                  ],
                  "fullname": "PY C",
                  "name": "pingou"
                }
              },
              "status": True,
              "title": "test pull-request",
              "uid": "1431414800",
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

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Access Pull-Request authenticated
        output = self.app.get('/api/0/test/pull-request/1', headers=headers)
        self.assertEqual(output.status_code, 200)
        data2 = json.loads(output.data)
        data2['date_created'] = '1431414800'
        data2['project']['date_created'] = '1431414800'
        data2['repo_from']['date_created'] = '1431414800'
        data2['uid'] = '1431414800'
        data2['date_created'] = '1431414800'
        self.assertDictEqual(data, data2)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskApiForktests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
