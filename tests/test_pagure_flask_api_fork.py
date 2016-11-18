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

import pagure.api
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

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_views(self, send_email):
        """ Test the api_pull_request_views method of the flask api. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.get_project(self.session, 'test')
        forked_repo = pagure.lib.get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
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
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Invalid repo
        output = self.app.get('/api/0/foo/pull-requests')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Project not found",
              "error_code": "ENOPROJECT",
            }
        )

        # List pull-requests
        output = self.app.get('/api/0/test/pull-requests')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['requests'][0]['date_created'] = '1431414800'
        data['requests'][0]['updated_on'] = '1431414800'
        data['requests'][0]['project']['date_created'] = '1431414800'
        data['requests'][0]['repo_from']['date_created'] = '1431414800'
        data['requests'][0]['uid'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                "status": True
              },
              "total_requests": 1,
              "requests": [
                {
                  "assignee": None,
                  "branch": "master",
                  "branch_from": "master",
                  "closed_at": None,
                  "closed_by": None,
                  "comments": [],
                  "commit_start": None,
                  "commit_stop": None,
                  "date_created": "1431414800",
                  "id": 1,
                  "initial_comment": None,
                  "project": {
                    "close_status": [
                      "Invalid",
                      "Insufficient data",
                      "Fixed",
                      "Duplicate"
                    ],
                    "custom_keys": [],
                    "date_created": "1431414800",
                    "description": "test project #1",
                    "id": 1,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                      "fullname": "PY C",
                      "name": "pingou"
                    }
                  },
                  "remote_git": None,
                  "repo_from": {
                    "close_status": [
                      "Invalid",
                      "Insufficient data",
                      "Fixed",
                      "Duplicate"
                    ],
                    "custom_keys": [],
                    "date_created": "1431414800",
                    "description": "test project #1",
                    "id": 1,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                      "fullname": "PY C",
                      "name": "pingou"
                    }
                  },
                  "status": 'Open',
                  "title": "test pull-request",
                  "uid": "1431414800",
                  "updated_on": "1431414800",
                  "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ]
            }
        )

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Access Pull-Request authenticated
        output = self.app.get('/api/0/test/pull-requests', headers=headers)
        self.assertEqual(output.status_code, 200)
        data2 = json.loads(output.data)
        data2['requests'][0]['date_created'] = '1431414800'
        data2['requests'][0]['updated_on'] = '1431414800'
        data2['requests'][0]['project']['date_created'] = '1431414800'
        data2['requests'][0]['repo_from']['date_created'] = '1431414800'
        data2['requests'][0]['uid'] = '1431414800'
        self.assertDictEqual(data, data2)

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_view(self, send_email):
        """ Test the api_pull_request_view method of the flask api. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.get_project(self.session, 'test')
        forked_repo = pagure.lib.get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
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
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Invalid repo
        output = self.app.get('/api/0/foo/pull-request/1')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Project not found",
              "error_code": "ENOPROJECT",
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
              "error_code": "ENOREQ",
            }
        )

        # Valid issue
        output = self.app.get('/api/0/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['date_created'] = '1431414800'
        data['updated_on'] = '1431414800'
        data['project']['date_created'] = '1431414800'
        data['repo_from']['date_created'] = '1431414800'
        data['uid'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "assignee": None,
              "branch": "master",
              "branch_from": "master",
              "closed_at": None,
              "closed_by": None,
              "comments": [],
              "commit_start": None,
              "commit_stop": None,
              "date_created": "1431414800",
              "id": 1,
              "initial_comment": None,
              "project": {
                "close_status": [
                  "Invalid",
                  "Insufficient data",
                  "Fixed",
                  "Duplicate"
                ],
                "custom_keys": [],
                "date_created": "1431414800",
                "description": "test project #1",
                "id": 1,
                "milestones": {},
                "name": "test",
                "namespace": None,
                "parent": None,
                "priorities": {},
                "tags": [],
                "user": {
                  "fullname": "PY C",
                  "name": "pingou"
                }
              },
              "remote_git": None,
              "repo_from": {
                "close_status": [
                  "Invalid",
                  "Insufficient data",
                  "Fixed",
                  "Duplicate"
                ],
                "custom_keys": [],
                "date_created": "1431414800",
                "description": "test project #1",
                "id": 1,
                "milestones": {},
                "name": "test",
                "namespace": None,
                "parent": None,
                "priorities": {},
                "tags": [],
                "user": {
                  "fullname": "PY C",
                  "name": "pingou"
                }
              },
              "status": 'Open',
              "title": "test pull-request",
              "uid": "1431414800",
              "updated_on": "1431414800",
              "user": {
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
        data2['updated_on'] = '1431414800'
        self.assertDictEqual(data, data2)

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_close(self, send_email):
        """ Test the api_pull_request_close method of the flask api. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create the pull-request to close
        repo = pagure.lib.get_project(self.session, 'test')
        forked_repo = pagure.lib.get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
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
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/close', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Project not found",
              "error_code": "ENOPROJECT",
            }
        )

        # Valid token, wrong project
        output = self.app.post(
            '/api/0/test2/pull-request/1/close', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # Invalid PR
        output = self.app.post(
            '/api/0/test/pull-request/2/close', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'error': 'Pull-Request not found', 'error_code': "ENOREQ"}
        )

        # Create a token for foo for this project
        item = pagure.lib.model.Token(
            id='foobar_token',
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)
        self.session.commit()

        # Allow the token to close PR
        acls = pagure.lib.get_acls(self.session)
        acl = None
        for acl in acls:
            if acl.name == 'pull_request_close':
                break
        item = pagure.lib.model.TokenAcl(
            token_id='foobar_token',
            acl_id=acl.id,
        )
        self.session.add(item)
        self.session.commit()

        headers = {'Authorization': 'token foobar_token'}

        # User not admin
        output = self.app.post(
            '/api/0/test/pull-request/1/close', headers=headers)
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                'error': 'You are not allowed to merge/close pull-request '
                    'for this project',
                'error_code': "ENOPRCLOSE",
            }
        )

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Close PR
        output = self.app.post(
            '/api/0/test/pull-request/1/close', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {"message": "Pull-request closed!"}
        )

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.lib.git.merge_pull_request')
    def test_api_pull_request_merge(self, mpr, send_email):
        """ Test the api_pull_request_merge method of the flask api. """
        mpr.return_value = 'Changes merged!'
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create the pull-request to close
        repo = pagure.lib.get_project(self.session, 'test')
        forked_repo = pagure.lib.get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
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
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Project not found",
              "error_code": "ENOPROJECT",
            }
        )

        # Valid token, wrong project
        output = self.app.post(
            '/api/0/test2/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # Invalid PR
        output = self.app.post(
            '/api/0/test/pull-request/2/merge', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'error': 'Pull-Request not found', 'error_code': "ENOREQ"}
        )

        # Create a token for foo for this project
        item = pagure.lib.model.Token(
            id='foobar_token',
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)
        self.session.commit()

        # Allow the token to merge PR
        acls = pagure.lib.get_acls(self.session)
        acl = None
        for acl in acls:
            if acl.name == 'pull_request_merge':
                break
        item = pagure.lib.model.TokenAcl(
            token_id='foobar_token',
            acl_id=acl.id,
        )
        self.session.add(item)
        self.session.commit()

        headers = {'Authorization': 'token foobar_token'}

        # User not admin
        output = self.app.post(
            '/api/0/test/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                'error': 'You are not allowed to merge/close pull-request '
                    'for this project',
                'error_code': "ENOPRCLOSE",
            }
        )

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Merge PR
        output = self.app.post(
            '/api/0/test/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {"message": "Changes merged!"}
        )

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_add_comment(self, mockemail):
        """ Test the api_pull_request_add_comment method of the flask api. """
        mockemail.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/comment', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Project not found",
              "error_code": "ENOPROJECT",
            }
        )

        # Valid token, wrong project
        output = self.app.post(
            '/api/0/test2/pull-request/1/comment', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No input
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Pull-Request not found",
              "error_code": "ENOREQ",
            }
        )

        # Create a pull-request
        repo = pagure.lib.get_project(self.session, 'test')
        forked_repo = pagure.lib.get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
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
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Check comments before
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 0)

        data = {
            'title': 'test issue',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": "EINVALIDREQ",
              "errors": {"comment": ["This field is required."]}
            }
        )

        # No change
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 0)

        data = {
            'comment': 'This is a very interesting question',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        # One comment added
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 1)

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_add_flag(self, mockemail):
        """ Test the api_pull_request_add_flag method of the flask api. """
        mockemail.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Project not found",
              "error_code": "ENOPROJECT",
            }
        )

        # Valid token, wrong project
        output = self.app.post(
            '/api/0/test2/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No input
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Pull-Request not found",
              "error_code": "ENOREQ",
            }
        )

        # Create a pull-request
        repo = pagure.lib.get_project(self.session, 'test')
        forked_repo = pagure.lib.get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
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
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Check comments before
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 0)

        data = {
            'username': 'Jenkins',
            'percent': 100,
            'url': 'http://jenkins.cloud.fedoraproject.org/',
            'uid': 'jenkins_build_pagure_100+seed',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": "EINVALIDREQ",
              "errors": {"comment": ["This field is required."]}
            }
        )

        # No change
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 0)

        data = {
            'username': 'Jenkins',
            'percent': 0,
            'comment': 'Tests failed',
            'url': 'http://jenkins.cloud.fedoraproject.org/',
            'uid': 'jenkins_build_pagure_100+seed',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Flag added'}
        )

        # One flag added
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].comment, 'Tests failed')
        self.assertEqual(request.flags[0].percent, 0)

        # Update flag
        data = {
            'username': 'Jenkins',
            'percent': 100,
            'comment': 'Tests passed',
            'url': 'http://jenkins.cloud.fedoraproject.org/',
            'uid': 'jenkins_build_pagure_100+seed',
        }

        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Flag updated'}
        )

        # One flag added
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].comment, 'Tests passed')
        self.assertEqual(request.flags[0].percent, 100)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskApiForktests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
