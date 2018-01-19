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
from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests


class PagureFlaskApiForktests(tests.Modeltests):
    """ Tests for the flask API of pagure for issue """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiForktests, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_views(self, send_email):
        """ Test the api_pull_request_views method of the flask api. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(
            self.session, 'test')
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
        data['requests'][0]['project']['date_modified'] = '1431414800'
        data['requests'][0]['repo_from']['date_created'] = '1431414800'
        data['requests'][0]['repo_from']['date_modified'] = '1431414800'
        data['requests'][0]['uid'] = '1431414800'
        data['requests'][0]['last_updated'] = '1431414800'
        expected_data = {
            "args": {
                "assignee": None,
                "author": None,
                "status": True
            },
            "requests": [{
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
                "last_updated": "1431414800",
                "project": {
                    "access_groups": {
                        "admin": [],
                        "commit": [],
                        "ticket": []
                    },
                    "access_users": {
                        "admin": [],
                        "commit": [],
                        "owner": ["pingou"],
                        "ticket": []
                    },
                    "close_status": [
                        "Invalid",
                        "Insufficient data",
                        "Fixed",
                        "Duplicate"
                    ],
                    "custom_keys": [],
                    "date_created": "1431414800",
                    "date_modified": "1431414800",
                    "description": "test project #1",
                    "fullname": "test",
                    "url_path": "test",
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
                    "access_groups": {
                        "admin": [],
                        "commit": [],
                        "ticket": []},
                    "access_users": {
                        "admin": [],
                        "commit": [],
                        "owner": ["pingou"],
                        "ticket": []
                    },
                    "close_status": [
                        "Invalid",
                        "Insufficient data",
                        "Fixed",
                        "Duplicate"
                    ],
                    "custom_keys": [],
                    "date_created": "1431414800",
                    "date_modified": "1431414800",
                    "description": "test project #1",
                    "fullname": "test",
                    "url_path": "test",
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
                "status": "Open",
                "title": "test pull-request",
                "uid": "1431414800",
                "updated_on": "1431414800",
                "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                }
            }],
            "total_requests": 1
        }
        self.assertDictEqual(data, expected_data)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Access Pull-Request authenticated
        output = self.app.get('/api/0/test/pull-requests', headers=headers)
        self.assertEqual(output.status_code, 200)
        data2 = json.loads(output.data)
        data2['requests'][0]['date_created'] = '1431414800'
        data2['requests'][0]['updated_on'] = '1431414800'
        data2['requests'][0]['project']['date_created'] = '1431414800'
        data2['requests'][0]['project']['date_modified'] = '1431414800'
        data2['requests'][0]['repo_from']['date_created'] = '1431414800'
        data2['requests'][0]['repo_from']['date_modified'] = '1431414800'
        data2['requests'][0]['uid'] = '1431414800'
        data2['requests'][0]['last_updated'] = '1431414800'
        self.assertDictEqual(data, data2)

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_view(self, send_email):
        """ Test the api_pull_request_view method of the flask api. """
        send_email.return_value = True
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
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
        data['project']['date_modified'] = '1431414800'
        data['repo_from']['date_created'] = '1431414800'
        data['repo_from']['date_modified'] = '1431414800'
        data['uid'] = '1431414800'
        data['last_updated'] = '1431414800'
        expected_data = {
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
            "last_updated": "1431414800",
            "project": {
                "access_groups": {
                    "admin": [],
                    "commit": [],
                    "ticket": []
                },
                "access_users": {
                    "admin": [],
                    "commit": [],
                    "owner": ["pingou"],
                    "ticket": []
                },
                "close_status": [
                    "Invalid",
                    "Insufficient data",
                    "Fixed",
                    "Duplicate"
                ],
                "custom_keys": [],
                "date_created": "1431414800",
                "date_modified": "1431414800",
                "description": "test project #1",
                "fullname": "test",
                "url_path": "test",
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
                "access_groups": {
                    "admin": [],
                    "commit": [],
                    "ticket": []},
                "access_users": {
                    "admin": [],
                    "commit": [],
                    "owner": ["pingou"],
                    "ticket": []},
                "close_status": [
                    "Invalid",
                    "Insufficient data",
                    "Fixed",
                    "Duplicate"],
                    "custom_keys": [],
                    "date_created": "1431414800",
                    "date_modified": "1431414800",
                    "description": "test project #1",
                    "fullname": "test",
                    "url_path": "test",
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
            "status": "Open",
            "title": "test pull-request",
            "uid": "1431414800",
            "updated_on": "1431414800",
            "user": {
                "fullname": "PY C",
                "name": "pingou"
            }
        }
        self.assertDictEqual(data, expected_data)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Access Pull-Request authenticated
        output = self.app.get('/api/0/test/pull-request/1', headers=headers)
        self.assertEqual(output.status_code, 200)
        data2 = json.loads(output.data)
        data2['date_created'] = '1431414800'
        data2['project']['date_created'] = '1431414800'
        data2['project']['date_modified'] = '1431414800'
        data2['repo_from']['date_created'] = '1431414800'
        data2['repo_from']['date_modified'] = '1431414800'
        data2['uid'] = '1431414800'
        data2['date_created'] = '1431414800'
        data2['updated_on'] = '1431414800'
        data2['last_updated'] = '1431414800'
        self.assertDictEqual(data, data2)

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_close(self, send_email):
        """ Test the api_pull_request_close method of the flask api. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create the pull-request to close
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
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
    def test_api_pull_request_merge(self, send_email):
        """ Test the api_pull_request_merge method of the flask api. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create the pull-request to close
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='test',
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
    def test_api_pull_request_merge_user_token(self, send_email):
        """ Test the api_pull_request_merge method of the flask api. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        # Create the pull-request to close
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='test',
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

        # Valid token, invalid PR
        output = self.app.post(
            '/api/0/test2/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'error': 'Pull-Request not found', 'error_code': "ENOREQ"}
        )

        # Valid token, invalid PR - other project
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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
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
        self.session = pagure.lib.create_session(self.dbpath)
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
              "error": "Invalid or incomplete input submitted",
              "error_code": "EINVALIDREQ",
              "errors": {"comment": ["This field is required."]}
            }
        )

        # No change
        self.session = pagure.lib.create_session(self.dbpath)
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
        self.session = pagure.lib.create_session(self.dbpath)
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 1)

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_add_comment_user_token(self, mockemail):
        """ Test the api_pull_request_add_comment method of the flask api. """
        mockemail.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
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

        # Valid token, invalid request
        output = self.app.post(
            '/api/0/test2/pull-request/1/comment', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Pull-Request not found",
              "error_code": "ENOREQ",
            }
        )

        # Valid token, invalid request in another project
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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
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
        self.session = pagure.lib.create_session(self.dbpath)
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
              "error": "Invalid or incomplete input submitted",
              "error_code": "EINVALIDREQ",
              "errors": {"comment": ["This field is required."]}
            }
        )

        # No change
        self.session = pagure.lib.create_session(self.dbpath)
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
        self.session = pagure.lib.create_session(self.dbpath)
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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
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
        self.session = pagure.lib.create_session(self.dbpath)
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
              "error": "Invalid or incomplete input submitted",
              "error_code": "EINVALIDREQ",
              "errors": {"comment": ["This field is required."]}
            }
        )

        # No change
        self.session = pagure.lib.create_session(self.dbpath)
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 0)

        data = {
            'username': 'Jenkins',
            'comment': 'Tests running',
            'url': 'http://jenkins.cloud.fedoraproject.org/',
            'uid': 'jenkins_build_pagure_100+seed',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['flag']['date_created'] = u'1510742565'
        data['flag']['pull_request_uid'] = u'62b49f00d489452994de5010565fab81'
        self.assertDictEqual(
            data,
            {
                u'flag': {
                    u'comment': u'Tests running',
                    u'date_created': u'1510742565',
                    u'percent': None,
                    u'pull_request_uid': u'62b49f00d489452994de5010565fab81',
                    u'status': u'pending',
                    u'url': u'http://jenkins.cloud.fedoraproject.org/',
                    u'user': {
                        u'default_email': u'bar@pingou.com',
                        u'emails': [u'bar@pingou.com', u'foo@pingou.com'],
                         u'fullname': u'PY C',
                         u'name': u'pingou'},
                    u'username': u'Jenkins'},
                u'message': u'Flag added',
                u'uid': u'jenkins_build_pagure_100+seed'
            }
        )

        # One flag added
        self.session = pagure.lib.create_session(self.dbpath)
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].comment, 'Tests running')
        self.assertEqual(request.flags[0].percent, None)

        # Update flag  -  w/o providing the status
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
        data['flag']['date_created'] = u'1510742565'
        data['flag']['pull_request_uid'] = u'62b49f00d489452994de5010565fab81'
        self.assertDictEqual(
            data,
            {
                u'flag': {
                    u'comment': u'Tests passed',
                    u'date_created': u'1510742565',
                    u'percent': 100,
                    u'pull_request_uid': u'62b49f00d489452994de5010565fab81',
                    u'status': u'success',
                    u'url': u'http://jenkins.cloud.fedoraproject.org/',
                    u'user': {
                        u'default_email': u'bar@pingou.com',
                        u'emails': [u'bar@pingou.com', u'foo@pingou.com'],
                         u'fullname': u'PY C',
                         u'name': u'pingou'},
                    u'username': u'Jenkins'},
                u'message': u'Flag updated',
                u'uid': u'jenkins_build_pagure_100+seed'
            }
        )

        # One flag added
        self.session = pagure.lib.create_session(self.dbpath)
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].comment, 'Tests passed')
        self.assertEqual(request.flags[0].percent, 100)

        data = {
            'username': 'Jenkins',
            'comment': 'Tests running again',
            'url': 'http://jenkins.cloud.fedoraproject.org/',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['flag']['date_created'] = u'1510742565'
        data['flag']['pull_request_uid'] = u'62b49f00d489452994de5010565fab81'
        self.assertNotEqual(
            data['uid'], 'jenkins_build_pagure_100+seed')
        data['uid'] = 'jenkins_build_pagure_100+seed'
        self.assertDictEqual(
            data,
            {
                u'flag': {
                    u'comment': u'Tests running again',
                    u'date_created': u'1510742565',
                    u'percent': None,
                    u'pull_request_uid': u'62b49f00d489452994de5010565fab81',
                    u'status': u'pending',
                    u'url': u'http://jenkins.cloud.fedoraproject.org/',
                    u'user': {
                        u'default_email': u'bar@pingou.com',
                        u'emails': [u'bar@pingou.com', u'foo@pingou.com'],
                         u'fullname': u'PY C',
                         u'name': u'pingou'},
                    u'username': u'Jenkins'},
                u'message': u'Flag added',
                u'uid': u'jenkins_build_pagure_100+seed'
            }
        )

        # Two flag added
        self.session = pagure.lib.create_session(self.dbpath)
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 2)
        self.assertEqual(request.flags[0].comment, 'Tests passed')
        self.assertEqual(request.flags[0].percent, 100)
        self.assertEqual(request.flags[1].comment, 'Tests running again')
        self.assertEqual(request.flags[1].percent, None)

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_add_flag_user_token(self, mockemail):
        """ Test the api_pull_request_add_flag method of the flask api. """
        mockemail.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
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
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Pull-Request not found",
              "error_code": "ENOREQ",
            }
        )

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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
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
        self.session = pagure.lib.create_session(self.dbpath)
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
              "error": "Invalid or incomplete input submitted",
              "error_code": "EINVALIDREQ",
              "errors": {"comment": ["This field is required."]}
            }
        )

        # No change
        self.session = pagure.lib.create_session(self.dbpath)
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

        # Valid request  -  w/o providing the status
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['flag']['date_created'] = u'1510742565'
        data['flag']['pull_request_uid'] = u'62b49f00d489452994de5010565fab81'
        self.assertDictEqual(
            data,
            {
                u'flag': {
                    u'comment': u'Tests failed',
                    u'date_created': u'1510742565',
                    u'percent': 0,
                    u'pull_request_uid': u'62b49f00d489452994de5010565fab81',
                    u'status': u'failure',
                    u'url': u'http://jenkins.cloud.fedoraproject.org/',
                    u'user': {
                        u'default_email': u'bar@pingou.com',
                        u'emails': [u'bar@pingou.com', u'foo@pingou.com'],
                         u'fullname': u'PY C',
                         u'name': u'pingou'},
                    u'username': u'Jenkins'},
                u'message': u'Flag added',
                u'uid': u'jenkins_build_pagure_100+seed'
            }
        )

        # One flag added
        self.session = pagure.lib.create_session(self.dbpath)
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
            'status': 'success',
        }

        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['flag']['date_created'] = u'1510742565'
        data['flag']['pull_request_uid'] = u'62b49f00d489452994de5010565fab81'
        self.assertDictEqual(
            data,
            {
                u'flag': {
                    u'comment': u'Tests passed',
                    u'date_created': u'1510742565',
                    u'percent': 100,
                    u'pull_request_uid': u'62b49f00d489452994de5010565fab81',
                    u'status': u'success',
                    u'url': u'http://jenkins.cloud.fedoraproject.org/',
                    u'user': {
                        u'default_email': u'bar@pingou.com',
                        u'emails': [u'bar@pingou.com', u'foo@pingou.com'],
                         u'fullname': u'PY C',
                         u'name': u'pingou'},
                    u'username': u'Jenkins'},
                u'message': u'Flag updated',
                u'uid': u'jenkins_build_pagure_100+seed'
            }
        )

        # One flag added
        self.session = pagure.lib.create_session(self.dbpath)
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].comment, 'Tests passed')
        self.assertEqual(request.flags[0].percent, 100)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_subscribe_pull_request(self, p_send_email, p_ugt):
        """ Test the api_subscribe_pull_request method of the flask api. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        item = pagure.lib.model.User(
            user='bar',
            fullname='bar foo',
            password='foo',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)

        self.session.commit()

        tests.create_projects(self.session)
        tests.create_tokens(self.session, user_id=3)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/subscribe', headers=headers)
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
            '/api/0/test2/pull-request/1/subscribe', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No input
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                u'error': u'Pull-Request not found',
                u'error_code': u'ENOREQ'
            }
        )

        # Create pull-request
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='feature',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Check subscribtion before
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(
            pagure.lib.get_watch_list(self.session, request),
            set(['pingou']))

        # Unsubscribe - no changes
        data = {}
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe',
            data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'You are no longer watching this pull-request'}
        )

        data = {}
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe',
            data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'You are no longer watching this pull-request'}
        )

        # No change
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(
            pagure.lib.get_watch_list(self.session, request),
            set(['pingou']))

        # Subscribe
        data = {'status': True}
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe',
            data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'You are now watching this pull-request'}
        )

        # Subscribe - no changes
        data = {'status': True}
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe',
            data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'You are now watching this pull-request'}
        )

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(
            pagure.lib.get_watch_list(self.session, request),
            set(['pingou', 'bar']))

        # Unsubscribe
        data = {}
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe',
            data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'You are no longer watching this pull-request'}
        )

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(
            pagure.lib.get_watch_list(self.session, request),
            set(['pingou']))

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_open_invalid_project(self):
        """ Test the api_pull_request_create method of the flask api when
        not the project doesn't exist.
        """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'initial_comment': 'Nothing much, the changes speak for themselves',
            'branch_to': 'master',
            'branch_from': 'test',
        }

        output = self.app.post(
            '/api/0/foobar/pull-request/new', headers=headers, data=data)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {u'error': u'Project not found', u'error_code': u'ENOPROJECT'}
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_open_missing_title(self):
        """ Test the api_pull_request_create method of the flask api when
        not title is submitted.
        """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'initial_comment': 'Nothing much, the changes speak for themselves',
            'branch_to': 'master',
            'branch_from': 'test',
        }

        output = self.app.post(
            '/api/0/test/pull-request/new', headers=headers, data=data)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                u'error': u'Invalid or incomplete input submitted',
                u'error_code': u'EINVALIDREQ',
                u'errors': {u'title': [u'This field is required.']}
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_open_missing_branch_to(self):
        """ Test the api_pull_request_create method of the flask api when
        not branch to is submitted.
        """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'title': 'Test PR',
            'initial_comment': 'Nothing much, the changes speak for themselves',
            'branch_from': 'test',
        }

        output = self.app.post(
            '/api/0/test/pull-request/new', headers=headers, data=data)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                u'error': u'Invalid or incomplete input submitted',
                u'error_code': u'EINVALIDREQ',
                u'errors': {u'branch_to': [u'This field is required.']}
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_open_missing_branch_from(self):
        """ Test the api_pull_request_create method of the flask api when
        not branch from is submitted.
        """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'title': 'Test PR',
            'initial_comment': 'Nothing much, the changes speak for themselves',
            'branch_to': 'master',
        }

        output = self.app.post(
            '/api/0/test/pull-request/new', headers=headers, data=data)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                u'error': u'Invalid or incomplete input submitted',
                u'error_code': u'EINVALIDREQ',
                u'errors': {u'branch_from': [u'This field is required.']}
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_open_pr_disabled(self):
        """ Test the api_pull_request_create method of the flask api when
        the parent repo disabled pull-requests.
        """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Check the behavior if the project disabled the issue tracker
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'title': 'Test PR',
            'initial_comment': 'Nothing much, the changes speak for themselves',
            'branch_to': 'master',
            'branch_from': 'test',
        }

        output = self.app.post(
            '/api/0/test/pull-request/new', headers=headers, data=data)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                u'error': u'Pull-Request have been deactivated for this project',
                u'error_code': u'EPULLREQUESTSDISABLED'
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_open_signed_pr(self):
        """ Test the api_pull_request_create method of the flask api when
        the parent repo enforces signed-off pull-requests.
        """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Check the behavior if the project disabled the issue tracker
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['Enforce_signed-off_commits_in_pull-request'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'title': 'Test PR',
            'initial_comment': 'Nothing much, the changes speak for themselves',
            'branch_to': 'master',
            'branch_from': 'test',
        }

        output = self.app.post(
            '/api/0/test/pull-request/new', headers=headers, data=data)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                u'error': u'This repo enforces that all commits are signed '
                   'off by their author.',
                u'error_code': u'ENOSIGNEDOFF'
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_open_invalid_branch_from(self):
        """ Test the api_pull_request_create method of the flask api when
        the branch from does not exist.
        """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Check the behavior if the project disabled the issue tracker
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['Enforce_signed-off_commits_in_pull-request'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'title': 'Test PR',
            'initial_comment': 'Nothing much, the changes speak for themselves',
            'branch_to': 'master',
            'branch_from': 'foobarbaz',
        }

        output = self.app.post(
            '/api/0/test/pull-request/new', headers=headers, data=data)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                u'error': u'Invalid or incomplete input submitted',
                u'error_code': u'EINVALIDREQ',
                u'errors': u'Branch foobarbaz does not exist'
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_open_invalid_branch_to(self):
        """ Test the api_pull_request_create method of the flask api when
        the branch to does not exist.
        """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Check the behavior if the project disabled the issue tracker
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['Enforce_signed-off_commits_in_pull-request'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'title': 'Test PR',
            'initial_comment': 'Nothing much, the changes speak for themselves',
            'branch_to': 'foobarbaz',
            'branch_from': 'test',
        }

        output = self.app.post(
            '/api/0/test/pull-request/new', headers=headers, data=data)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                u'error': u'Invalid or incomplete input submitted',
                u'error_code': u'EINVALIDREQ',
                u'errors': u'Branch foobarbaz could not be found in the '
                    'target repo'
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_open(self):
        """ Test the api_pull_request_create method of the flask api. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'title': 'Test PR',
            'initial_comment': 'Nothing much, the changes speak for themselves',
            'branch_to': 'master',
            'branch_from': 'test',
        }

        output = self.app.post(
            '/api/0/test/pull-request/new', headers=headers, data=data)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['project']['date_created'] = u'1516348115'
        data['project']['date_modified'] = u'1516348115'
        data['repo_from']['date_created'] = u'1516348115'
        data['repo_from']['date_modified'] = u'1516348115'
        data['uid'] = u'e8b68df8711648deac67c3afed15a798'
        data['commit_start'] = u'114f1b468a5f05e635fcb6394273f3f907386eab'
        data['commit_stop'] = u'114f1b468a5f05e635fcb6394273f3f907386eab'
        data['date_created'] = u'1516348115'
        data['last_updated'] = u'1516348115'
        data['updated_on'] = u'1516348115'
        self.assertDictEqual(
            data,
            {
                u'assignee': None,
                u'branch': u'master',
                u'branch_from': u'test',
                u'closed_at': None,
                u'closed_by': None,
                u'comments': [],
                u'commit_start': u'114f1b468a5f05e635fcb6394273f3f907386eab',
                u'commit_stop': u'114f1b468a5f05e635fcb6394273f3f907386eab',
                u'date_created': u'1516348115',
                u'id': 1,
                u'initial_comment': u'Nothing much, the changes speak for themselves',
                u'last_updated': u'1516348115',
                u'project': {u'access_groups': {u'admin': [],
                                                u'commit': [],
                                                u'ticket':[]},
                             u'access_users': {u'admin': [],
                                               u'commit': [],
                                               u'owner': [u'pingou'],
                                               u'ticket': []},
                             u'close_status': [u'Invalid',
                                               u'Insufficient data',
                                               u'Fixed',
                                               u'Duplicate'],
                             u'custom_keys': [],
                             u'date_created': u'1516348115',
                             u'date_modified': u'1516348115',
                             u'description': u'test project #1',
                             u'fullname': u'test',
                             u'id': 1,
                             u'milestones': {},
                             u'name': u'test',
                             u'namespace': None,
                             u'parent': None,
                             u'priorities': {},
                             u'tags': [],
                             u'url_path': u'test',
                             u'user': {u'fullname': u'PY C', u'name': u'pingou'}},
                u'remote_git': None,
                u'repo_from': {u'access_groups': {u'admin': [],
                                                  u'commit': [],
                                                  u'ticket': []},
                               u'access_users': {u'admin': [],
                                                 u'commit': [],
                                                 u'owner': [u'pingou'],
                                                 u'ticket': []},
                               u'close_status': [u'Invalid',
                                                 u'Insufficient data',
                                                 u'Fixed',
                                                 u'Duplicate'],
                               u'custom_keys': [],
                               u'date_created': u'1516348115',
                               u'date_modified': u'1516348115',
                               u'description': u'test project #1',
                               u'fullname': u'test',
                               u'id': 1,
                               u'milestones': {},
                               u'name': u'test',
                               u'namespace': None,
                               u'parent': None,
                               u'priorities': {},
                               u'tags': [],
                               u'url_path': u'test',
                               u'user': {u'fullname': u'PY C', u'name': u'pingou'}},
                u'status': u'Open',
                u'title': u'Test PR',
                u'uid': u'e8b68df8711648deac67c3afed15a798',
                u'updated_on': u'1516348115',
                u'user': {u'fullname': u'PY C', u'name': u'pingou'}
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_open_missing_initial_comment(self):
        """ Test the api_pull_request_create method of the flask api when
        not initial comment is submitted.
        """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'title': 'Test PR',
            'branch_to': 'master',
            'branch_from': 'test',
        }

        output = self.app.post(
            '/api/0/test/pull-request/new', headers=headers, data=data)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['project']['date_created'] = u'1516348115'
        data['project']['date_modified'] = u'1516348115'
        data['repo_from']['date_created'] = u'1516348115'
        data['repo_from']['date_modified'] = u'1516348115'
        data['uid'] = u'e8b68df8711648deac67c3afed15a798'
        data['commit_start'] = u'114f1b468a5f05e635fcb6394273f3f907386eab'
        data['commit_stop'] = u'114f1b468a5f05e635fcb6394273f3f907386eab'
        data['date_created'] = u'1516348115'
        data['last_updated'] = u'1516348115'
        data['updated_on'] = u'1516348115'
        self.assertDictEqual(
            data,
            {
                u'assignee': None,
                u'branch': u'master',
                u'branch_from': u'test',
                u'closed_at': None,
                u'closed_by': None,
                u'comments': [],
                u'commit_start': u'114f1b468a5f05e635fcb6394273f3f907386eab',
                u'commit_stop': u'114f1b468a5f05e635fcb6394273f3f907386eab',
                u'date_created': u'1516348115',
                u'id': 1,
                u'initial_comment': None,
                u'last_updated': u'1516348115',
                u'project': {u'access_groups': {u'admin': [],
                                                u'commit': [],
                                                u'ticket':[]},
                             u'access_users': {u'admin': [],
                                               u'commit': [],
                                               u'owner': [u'pingou'],
                                               u'ticket': []},
                             u'close_status': [u'Invalid',
                                               u'Insufficient data',
                                               u'Fixed',
                                               u'Duplicate'],
                             u'custom_keys': [],
                             u'date_created': u'1516348115',
                             u'date_modified': u'1516348115',
                             u'description': u'test project #1',
                             u'fullname': u'test',
                             u'id': 1,
                             u'milestones': {},
                             u'name': u'test',
                             u'namespace': None,
                             u'parent': None,
                             u'priorities': {},
                             u'tags': [],
                             u'url_path': u'test',
                             u'user': {u'fullname': u'PY C', u'name': u'pingou'}},
                u'remote_git': None,
                u'repo_from': {u'access_groups': {u'admin': [],
                                                  u'commit': [],
                                                  u'ticket': []},
                               u'access_users': {u'admin': [],
                                                 u'commit': [],
                                                 u'owner': [u'pingou'],
                                                 u'ticket': []},
                               u'close_status': [u'Invalid',
                                                 u'Insufficient data',
                                                 u'Fixed',
                                                 u'Duplicate'],
                               u'custom_keys': [],
                               u'date_created': u'1516348115',
                               u'date_modified': u'1516348115',
                               u'description': u'test project #1',
                               u'fullname': u'test',
                               u'id': 1,
                               u'milestones': {},
                               u'name': u'test',
                               u'namespace': None,
                               u'parent': None,
                               u'priorities': {},
                               u'tags': [],
                               u'url_path': u'test',
                               u'user': {u'fullname': u'PY C', u'name': u'pingou'}},
                u'status': u'Open',
                u'title': u'Test PR',
                u'uid': u'e8b68df8711648deac67c3afed15a798',
                u'updated_on': u'1516348115',
                u'user': {u'fullname': u'PY C', u'name': u'pingou'}
            }
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
