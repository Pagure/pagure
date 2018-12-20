# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

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

import pagure.lib.query
import tests


class PagureFlaskApiForktests(tests.Modeltests):
    """ Tests for the flask API of pagure for issue """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiForktests, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_views_pr_disabled(self):
        """ Test the api_pull_request_views method of the flask api when PR
        are disabled. """

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(
            self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/api/0/test/pull-requests')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'Pull-Request have been deactivated for this project',
                u'error_code': u'EPULLREQUESTSDISABLED'
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_views_pr_closed(self):
        """ Test the api_pull_request_views method of the flask api to list
        the closed PRs. """

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(
            self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        output = self.app.get('/api/0/test/pull-requests?status=closed')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for k in ['first', 'last']:
            self.assertIsNotNone(data['pagination'][k])
            data['pagination'][k] = 'http://localhost...'
        self.assertDictEqual(
            data,
            {
                u'args': {
                    u'assignee': None,
                    u'author': None,
                    u'page': 1,
                    u'per_page': 20,
                    u'status': u'closed'
                },
                u'pagination': {
                    u'first': u'http://localhost...',
                    u'last': u'http://localhost...',
                    u'next': None,
                    u'page': 1,
                    u'pages': 0,
                    u'per_page': 20,
                    u'prev': None
                },
                u'requests': [],
                u'total_requests': 0
            }
        )

        # Close the PR and try again
        pagure.lib.query.close_pull_request(
            self.session, request=req, user='pingou',
            merged=False)

        output = self.app.get('/api/0/test/pull-requests?status=closed')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()),
            ['args', 'pagination', 'requests', 'total_requests'])
        self.assertDictEqual(
            data['args'],
            {
                u'assignee': None,
                u'author': None,
                u'page': 1,
                u'per_page': 20,
                u'status': u'closed'
            }
        )
        self.assertEqual(data['total_requests'], 1)

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_views_all_pr(self):
        """ Test the api_pull_request_views method of the flask api to list
        all PRs. """

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(
            self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        output = self.app.get('/api/0/test/pull-requests?status=all')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()),
            ['args', 'pagination', 'requests', 'total_requests'])
        self.assertDictEqual(
            data['args'],
            {
                u'assignee': None,
                u'author': None,
                u'page': 1,
                u'per_page': 20,
                u'status': u'all'
            }
        )
        self.assertEqual(data['total_requests'], 1)

        # Close the PR and try again
        pagure.lib.query.close_pull_request(
            self.session, request=req, user='pingou',
            merged=False)

        output = self.app.get('/api/0/test/pull-requests?status=all')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()),
            ['args', 'pagination', 'requests', 'total_requests'])
        self.assertDictEqual(
            data['args'],
            {
                u'assignee': None,
                u'author': None,
                u'page': 1,
                u'per_page': 20,
                u'status': u'all'
            }
        )
        self.assertEqual(data['total_requests'], 1)

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_views(self, send_email):
        """ Test the api_pull_request_views method of the flask api. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(
            self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Invalid repo
        output = self.app.get('/api/0/foo/pull-requests')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
        data['requests'][0]['date_created'] = '1431414800'
        data['requests'][0]['updated_on'] = '1431414800'
        data['requests'][0]['project']['date_created'] = '1431414800'
        data['requests'][0]['project']['date_modified'] = '1431414800'
        data['requests'][0]['repo_from']['date_created'] = '1431414800'
        data['requests'][0]['repo_from']['date_modified'] = '1431414800'
        data['requests'][0]['uid'] = '1431414800'
        data['requests'][0]['last_updated'] = '1431414800'
        for k in ['first', 'last']:
            self.assertIsNotNone(data['pagination'][k])
            data['pagination'][k] = 'http://localhost...'
        expected_data = {
            "args": {
                "assignee": None,
                "author": None,
                "page": 1,
                "per_page": 20,
                "status": True
            },
            'pagination': {
              "first": 'http://localhost...',
              "last": 'http://localhost...',
              "next": None,
              "page": 1,
              "pages": 1,
              "per_page": 20,
              "prev": None
            },
            "requests": [{
                "assignee": None,
                "branch": "master",
                "branch_from": "master",
                "cached_merge_status": "unknown",
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
                "threshold_reached": None,
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
        data2 = json.loads(output.get_data(as_text=True))
        data2['requests'][0]['date_created'] = '1431414800'
        data2['requests'][0]['updated_on'] = '1431414800'
        data2['requests'][0]['project']['date_created'] = '1431414800'
        data2['requests'][0]['project']['date_modified'] = '1431414800'
        data2['requests'][0]['repo_from']['date_created'] = '1431414800'
        data2['requests'][0]['repo_from']['date_modified'] = '1431414800'
        data2['requests'][0]['uid'] = '1431414800'
        data2['requests'][0]['last_updated'] = '1431414800'
        for k in ['first', 'last']:
            self.assertIsNotNone(data['pagination'][k])
            data2['pagination'][k] = 'http://localhost...'
        self.assertDictEqual(data, data2)

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_view_pr_disabled(self, send_email):
        """ Test the api_pull_request_view method of the flask api. """
        send_email.return_value = True
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/api/0/test/pull-request/1')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'Pull-Request have been deactivated for this project',
                u'error_code': u'EPULLREQUESTSDISABLED'
            }
        )

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_view(self, send_email):
        """ Test the api_pull_request_view method of the flask api. """
        send_email.return_value = True
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Invalid repo
        output = self.app.get('/api/0/foo/pull-request/1')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
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
            "cached_merge_status": "unknown",
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
            "threshold_reached": None,
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
        data2 = json.loads(output.get_data(as_text=True))
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
    def test_api_pull_request_by_uid_view(self, send_email):
        """ Test the api_pull_request_by_uid_view method of the flask api. """
        send_email.return_value = True
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')
        uid = req.uid

        # Invalid request
        output = self.app.get('/api/0/pull-requests/{}'.format(uid + 'aaa'))
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
              "error": "Pull-Request not found",
              "error_code": "ENOREQ",
            }
        )

        # Valid issue
        output = self.app.get('/api/0/pull-requests/{}'.format(uid))
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['date_created'] = '1431414800'
        data['updated_on'] = '1431414800'
        data['project']['date_created'] = '1431414800'
        data['project']['date_modified'] = '1431414800'
        data['repo_from']['date_created'] = '1431414800'
        data['repo_from']['date_modified'] = '1431414800'
        data['last_updated'] = '1431414800'
        expected_data = {
            "assignee": None,
            "branch": "master",
            "branch_from": "master",
            "cached_merge_status": "unknown",
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
            "threshold_reached": None,
            "title": "test pull-request",
            "uid": uid,
            "updated_on": "1431414800",
            "user": {
                "fullname": "PY C",
                "name": "pingou"
            }
        }
        self.assertDictEqual(data, expected_data)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Access Pull-Request authenticated
        output = self.app.get('/api/0/pull-requests/{}'.format(uid), headers=headers)
        self.assertEqual(output.status_code, 200)
        data2 = json.loads(output.get_data(as_text=True))
        data2['date_created'] = '1431414800'
        data2['project']['date_created'] = '1431414800'
        data2['project']['date_modified'] = '1431414800'
        data2['repo_from']['date_created'] = '1431414800'
        data2['repo_from']['date_modified'] = '1431414800'
        data2['date_created'] = '1431414800'
        data2['updated_on'] = '1431414800'
        data2['last_updated'] = '1431414800'
        self.assertDictEqual(data, data2)

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_close_pr_disabled(self, send_email):
        """ Test the api_pull_request_close method of the flask api. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create the pull-request to close
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}

        output = self.app.post(
            '/api/0/test/pull-request/1/close', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'Pull-Request have been deactivated for this project',
                u'error_code': u'EPULLREQUESTSDISABLED'
            }
        )

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_close(self, send_email):
        """ Test the api_pull_request_close method of the flask api. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create the pull-request to close
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/close', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # Invalid PR
        output = self.app.post(
            '/api/0/test/pull-request/2/close', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
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
        acls = pagure.lib.query.get_acls(self.session)
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
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {"message": "Pull-request closed!"}
        )

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_merge_pr_disabled(self, send_email):
        """ Test the api_pull_request_merge method of the flask api when PR
        are disabled. """
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
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='test',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}

        output = self.app.post(
            '/api/0/test/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'Pull-Request have been deactivated for this project',
                u'error_code': u'EPULLREQUESTSDISABLED'
            }
        )

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_merge_only_assigned(self, send_email):
        """ Test the api_pull_request_merge method of the flask api when
        only assignee can merge the PR and the PR isn't assigned. """
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
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='test',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['Only_assignee_can_merge_pull-request'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}

        output = self.app.post(
            '/api/0/test/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'This request must be assigned to be merged',
                u'error_code': u'ENOTASSIGNED'
            }
        )

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_merge_only_assigned_not_assignee(
            self, send_email):
        """ Test the api_pull_request_merge method of the flask api when
        only assignee can merge the PR and the PR isn't assigned to the
        user asking to merge. """
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
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='test',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')
        req.assignee = pagure.lib.query.search_user(self.session, 'foo')
        self.session.add(req)
        self.session.commit()

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['Only_assignee_can_merge_pull-request'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}

        output = self.app.post(
            '/api/0/test/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'Only the assignee can merge this review',
                u'error_code': u'ENOTASSIGNEE'
            }
        )

    @patch('pagure.lib.notify.send_email')
    def test_api_pull_request_merge_minimal_score(self, send_email):
        """ Test the api_pull_request_merge method of the flask api when
        a PR requires a certain minimal score to be merged. """
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
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='test',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['Minimum_score_to_merge_pull-request'] = 2
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}

        output = self.app.post(
            '/api/0/test/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'This request does not have the minimum review '
                'score necessary to be merged',
                u'error_code': u'EPRSCORE'
            }
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
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='test',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # Invalid PR
        output = self.app.post(
            '/api/0/test/pull-request/2/merge', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
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
        acls = pagure.lib.query.get_acls(self.session)
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
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
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
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='test',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'error': 'Pull-Request not found', 'error_code': "ENOREQ"}
        )

        # Valid token, invalid PR - other project
        output = self.app.post(
            '/api/0/test/pull-request/2/merge', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
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
        acls = pagure.lib.query.get_acls(self.session)
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
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No input
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
              "error": "Pull-Request not found",
              "error_code": "ENOREQ",
            }
        )

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Check comments before
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 0)

        data = {
            'title': 'test issue',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submitted",
              "error_code": "EINVALIDREQ",
              "errors": {"comment": ["This field is required."]}
            }
        )

        # No change
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 0)

        data = {
            'comment': 'This is a very interesting question',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        # One comment added
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 1)

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_add_comment_wrong_user(self):
        """ Test the api_pull_request_add_comment method of the flask api
        when the user is not found in the DB. """

        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        data = {
            'comment': 'This is a very interesting question',
        }

        # Valid request
        with patch('pagure.lib.query.add_pull_request_comment',
                   side_effect=pagure.exceptions.PagureException('error')):
            output = self.app.post(
                '/api/0/test/pull-request/1/comment', data=data, headers=headers)
            self.assertEqual(output.status_code, 400)
            data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(
                data,
                {u'error': u'error', u'error_code': u'ENOCODE'}
            )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_add_comment_pr_disabled(self):
        """ Test the api_pull_request_add_comment method of the flask api
        when PRs are disabled. """

        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        data = {
            'comment': 'This is a very interesting question',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'Pull-Request have been deactivated for this project',
                u'error_code': u'EPULLREQUESTSDISABLED'
            }
        )

        # no comment added
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 0)

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
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
              "error": "Pull-Request not found",
              "error_code": "ENOREQ",
            }
        )

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Check comments before
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 0)

        data = {
            'title': 'test issue',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submitted",
              "error_code": "EINVALIDREQ",
              "errors": {"comment": ["This field is required."]}
            }
        )

        # No change
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 0)

        data = {
            'comment': 'This is a very interesting question',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        # One comment added
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 1)

    @patch('pagure.lib.notify.send_email')
    def test_api_subscribe_pull_request_pr_disabled(self, p_send_email):
        """ Test the api_subscribe_pull_request method of the flask api. """
        p_send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'Pull-Request have been deactivated for this project',
                u'error_code': u'EPULLREQUESTSDISABLED'
            }
        )

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_subscribe_pull_request_invalid_token(self, p_send_email, p_ugt):
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
        tests.create_tokens(self.session, user_id=3, project_id=2)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Create pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='feature',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Check subscribtion before
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(
            pagure.lib.query.get_watch_list(self.session, request),
            set(['pingou']))

        data = {}
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe',
            data=data, headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'Invalid or expired token. Please visit '
                'http://localhost.localdomain/settings#api-keys to get or '
                'renew your API token.',
                u'error_code': u'EINVALIDTOK'
            }
        )

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
        data = json.loads(output.get_data(as_text=True))
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
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No input
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                'error': 'Pull-Request not found',
                'error_code': 'ENOREQ'
            }
        )

        # Create pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='feature',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Check subscribtion before
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(
            pagure.lib.query.get_watch_list(self.session, request),
            set(['pingou']))

        # Unsubscribe - no changes
        data = {}
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe',
            data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {'message': 'You are no longer watching this pull-request',
            'avatar_url': 'https://seccdn.libravatar.org/avatar/...',
            'user': 'bar',
            }
        )

        data = {}
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe',
            data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {'message': 'You are no longer watching this pull-request',
            'avatar_url': 'https://seccdn.libravatar.org/avatar/...',
            'user': 'bar',
            }
        )

        # No change
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(
            pagure.lib.query.get_watch_list(self.session, request),
            set(['pingou']))

        # Subscribe
        data = {'status': True}
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe',
            data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {'message': 'You are now watching this pull-request',
            'avatar_url': 'https://seccdn.libravatar.org/avatar/...',
            'user': 'bar',
            }
        )

        # Subscribe - no changes
        data = {'status': True}
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe',
            data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {'message': 'You are now watching this pull-request',
            'avatar_url': 'https://seccdn.libravatar.org/avatar/...',
            'user': 'bar',
            }
        )

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(
            pagure.lib.query.get_watch_list(self.session, request),
            set(['pingou', 'bar']))

        # Unsubscribe
        data = {}
        output = self.app.post(
            '/api/0/test/pull-request/1/subscribe',
            data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {'message': 'You are no longer watching this pull-request',
            'avatar_url': 'https://seccdn.libravatar.org/avatar/...',
            'user': 'bar',
            }
        )

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(
            pagure.lib.query.get_watch_list(self.session, request),
            set(['pingou']))

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_subscribe_pull_request_logged_in(self, p_send_email, p_ugt):
        """ Test the api_subscribe_pull_request method of the flask api
        when the user is logged in via the UI. """
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

        # Create pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='feature',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Check subscribtion before
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(
            pagure.lib.query.get_watch_list(self.session, request),
            set(['pingou']))

        # Subscribe
        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            data = {'status': True}
            output = self.app.post(
                '/api/0/test/pull-request/1/subscribe', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
            self.assertDictEqual(
                data,
                {'message': 'You are now watching this pull-request',
                'avatar_url': 'https://seccdn.libravatar.org/avatar/...',
                'user': 'foo',
                }
            )

        # Check subscribtions after
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(
            pagure.lib.query.get_watch_list(self.session, request),
            set(['pingou', 'foo']))

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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'error': 'Project not found', 'error_code': 'ENOPROJECT'}
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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                'error': 'Invalid or incomplete input submitted',
                'error_code': 'EINVALIDREQ',
                'errors': {'title': ['This field is required.']}
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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                'error': 'Invalid or incomplete input submitted',
                'error_code': 'EINVALIDREQ',
                'errors': {'branch_to': ['This field is required.']}
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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                'error': 'Invalid or incomplete input submitted',
                'error_code': 'EINVALIDREQ',
                'errors': {'branch_from': ['This field is required.']}
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
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                'error': 'Pull-Request have been deactivated for this project',
                'error_code': 'EPULLREQUESTSDISABLED'
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
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                'error': 'This repo enforces that all commits are signed '
                   'off by their author.',
                'error_code': 'ENOSIGNEDOFF'
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
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                'error': 'Invalid or incomplete input submitted',
                'error_code': 'EINVALIDREQ',
                'errors': 'Branch foobarbaz does not exist'
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_open_invalid_token(self):
        """ Test the api_pull_request_create method of the flask api when
        queried with an invalid token.
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
            'branch_from': 'foobarbaz',
        }

        output = self.app.post(
            '/api/0/test2/pull-request/new', headers=headers, data=data)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'Invalid or expired token. Please visit '
                'http://localhost.localdomain/settings#api-keys to get or '
                'renew your API token.',
                u'error_code': u'EINVALIDTOK',
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_open_invalid_access(self):
        """ Test the api_pull_request_create method of the flask api when
        the user opening the PR doesn't have commit access.
        """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session, user_id=2)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'title': 'Test PR',
            'initial_comment': 'Nothing much, the changes speak for themselves',
            'branch_to': 'master',
            'branch_from': 'foobarbaz',
        }

        output = self.app.post(
            '/api/0/test/pull-request/new', headers=headers, data=data)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'You do not have sufficient permissions to '
                u'perform this action',
                u'error_code': u'ENOTHIGHENOUGH'
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
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                'error': 'Invalid or incomplete input submitted',
                'error_code': 'EINVALIDREQ',
                'errors': 'Branch foobarbaz could not be found in the '
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
        data = json.loads(output.get_data(as_text=True))
        data['project']['date_created'] = '1516348115'
        data['project']['date_modified'] = '1516348115'
        data['repo_from']['date_created'] = '1516348115'
        data['repo_from']['date_modified'] = '1516348115'
        data['uid'] = 'e8b68df8711648deac67c3afed15a798'
        data['commit_start'] = '114f1b468a5f05e635fcb6394273f3f907386eab'
        data['commit_stop'] = '114f1b468a5f05e635fcb6394273f3f907386eab'
        data['date_created'] = '1516348115'
        data['last_updated'] = '1516348115'
        data['updated_on'] = '1516348115'
        self.assertDictEqual(
            data,
            {
                'assignee': None,
                'branch': 'master',
                'branch_from': 'test',
                'cached_merge_status': 'unknown',
                'closed_at': None,
                'closed_by': None,
                'comments': [],
                'commit_start': '114f1b468a5f05e635fcb6394273f3f907386eab',
                'commit_stop': '114f1b468a5f05e635fcb6394273f3f907386eab',
                'date_created': '1516348115',
                'id': 1,
                'initial_comment': 'Nothing much, the changes speak for themselves',
                'last_updated': '1516348115',
                'project': {'access_groups': {'admin': [],
                                                'commit': [],
                                                'ticket':[]},
                             'access_users': {'admin': [],
                                               'commit': [],
                                               'owner': ['pingou'],
                                               'ticket': []},
                             'close_status': ['Invalid',
                                               'Insufficient data',
                                               'Fixed',
                                               'Duplicate'],
                             'custom_keys': [],
                             'date_created': '1516348115',
                             'date_modified': '1516348115',
                             'description': 'test project #1',
                             'fullname': 'test',
                             'id': 1,
                             'milestones': {},
                             'name': 'test',
                             'namespace': None,
                             'parent': None,
                             'priorities': {},
                             'tags': [],
                             'url_path': 'test',
                             'user': {'fullname': 'PY C', 'name': 'pingou'}},
                'remote_git': None,
                'repo_from': {'access_groups': {'admin': [],
                                                  'commit': [],
                                                  'ticket': []},
                               'access_users': {'admin': [],
                                                 'commit': [],
                                                 'owner': ['pingou'],
                                                 'ticket': []},
                               'close_status': ['Invalid',
                                                 'Insufficient data',
                                                 'Fixed',
                                                 'Duplicate'],
                               'custom_keys': [],
                               'date_created': '1516348115',
                               'date_modified': '1516348115',
                               'description': 'test project #1',
                               'fullname': 'test',
                               'id': 1,
                               'milestones': {},
                               'name': 'test',
                               'namespace': None,
                               'parent': None,
                               'priorities': {},
                               'tags': [],
                               'url_path': 'test',
                               'user': {'fullname': 'PY C', 'name': 'pingou'}},
                'status': 'Open',
                'threshold_reached': None,
                'title': 'Test PR',
                'uid': 'e8b68df8711648deac67c3afed15a798',
                'updated_on': '1516348115',
                'user': {'fullname': 'PY C', 'name': 'pingou'}
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
        data = json.loads(output.get_data(as_text=True))
        data['project']['date_created'] = '1516348115'
        data['project']['date_modified'] = '1516348115'
        data['repo_from']['date_created'] = '1516348115'
        data['repo_from']['date_modified'] = '1516348115'
        data['uid'] = 'e8b68df8711648deac67c3afed15a798'
        data['commit_start'] = '114f1b468a5f05e635fcb6394273f3f907386eab'
        data['commit_stop'] = '114f1b468a5f05e635fcb6394273f3f907386eab'
        data['date_created'] = '1516348115'
        data['last_updated'] = '1516348115'
        data['updated_on'] = '1516348115'
        self.assertDictEqual(
            data,
            {
                'assignee': None,
                'branch': 'master',
                'branch_from': 'test',
                'cached_merge_status': 'unknown',
                'closed_at': None,
                'closed_by': None,
                'comments': [],
                'commit_start': '114f1b468a5f05e635fcb6394273f3f907386eab',
                'commit_stop': '114f1b468a5f05e635fcb6394273f3f907386eab',
                'date_created': '1516348115',
                'id': 1,
                'initial_comment': None,
                'last_updated': '1516348115',
                'project': {'access_groups': {'admin': [],
                                                'commit': [],
                                                'ticket':[]},
                             'access_users': {'admin': [],
                                               'commit': [],
                                               'owner': ['pingou'],
                                               'ticket': []},
                             'close_status': ['Invalid',
                                               'Insufficient data',
                                               'Fixed',
                                               'Duplicate'],
                             'custom_keys': [],
                             'date_created': '1516348115',
                             'date_modified': '1516348115',
                             'description': 'test project #1',
                             'fullname': 'test',
                             'id': 1,
                             'milestones': {},
                             'name': 'test',
                             'namespace': None,
                             'parent': None,
                             'priorities': {},
                             'tags': [],
                             'url_path': 'test',
                             'user': {'fullname': 'PY C', 'name': 'pingou'}},
                'remote_git': None,
                'repo_from': {'access_groups': {'admin': [],
                                                  'commit': [],
                                                  'ticket': []},
                               'access_users': {'admin': [],
                                                 'commit': [],
                                                 'owner': ['pingou'],
                                                 'ticket': []},
                               'close_status': ['Invalid',
                                                 'Insufficient data',
                                                 'Fixed',
                                                 'Duplicate'],
                               'custom_keys': [],
                               'date_created': '1516348115',
                               'date_modified': '1516348115',
                               'description': 'test project #1',
                               'fullname': 'test',
                               'id': 1,
                               'milestones': {},
                               'name': 'test',
                               'namespace': None,
                               'parent': None,
                               'priorities': {},
                               'tags': [],
                               'url_path': 'test',
                               'user': {'fullname': 'PY C', 'name': 'pingou'}},
                'status': 'Open',
                'threshold_reached': None,
                'title': 'Test PR',
                'uid': 'e8b68df8711648deac67c3afed15a798',
                'updated_on': '1516348115',
                'user': {'fullname': 'PY C', 'name': 'pingou'}
            }
        )

class PagureFlaskApiForkPRDiffStatstests(tests.Modeltests):
    """ Tests for the flask API of pagure for the diff stats endpoint of PRs
    """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiForkPRDiffStatstests, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), ncommits=5)
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), branch='test')

        # Create the pull-request to close
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='test',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_diffstats_no_repo(self):
        """ Test the api_pull_request_merge method of the flask api. """
        output = self.app.get('/api/0/invalid/pull-request/404/diffstats')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {'error': 'Project not found', 'error_code': 'ENOPROJECT'}
        )

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_diffstats_no_pr(self):
        """ Test the api_pull_request_merge method of the flask api. """
        output = self.app.get('/api/0/test/pull-request/404/diffstats')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {'error': 'Pull-Request not found', 'error_code': 'ENOREQ'}
        )

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_diffstats_file_modified(self):
        """ Test the api_pull_request_merge method of the flask api. """
        output = self.app.get('/api/0/test/pull-request/1/diffstats')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                'sources': {
                    'lines_added': 10,
                    'lines_removed': 0,
                    "new_id": "540916fbd3d825d14cc0c0b2397606fda69379ce",
                    "old_id": "265f133a7c94ede4cb183dd808219c5bf9e08f87",
                    'old_path': 'sources',
                    'status': 'M'
                }
            }
        )

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_diffstats_file_added_mofidied(self):
        """ Test the api_pull_request_merge method of the flask api. """
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), ncommits=5)
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'test.git'),
            readme_name='README.md', branch='test')

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        self.assertEqual(len(repo.requests), 1)

        output = self.app.get('/api/0/test/pull-request/1/diffstats')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertTrue(
            data in
            [
                {
                  "README.md": {
                    "lines_added": 5,
                    "lines_removed": 0,
                    "new_id": "bd913ea153650b94f33f53e5164c36a28b761bf4",
                    "old_id": "0000000000000000000000000000000000000000",
                    "old_path": "README.md",
                    "status": "A"
                  },
                  "sources": {
                    "lines_added": 5,
                    "lines_removed": 0,
                    "new_id": "540916fbd3d825d14cc0c0b2397606fda69379ce",
                    "old_id": "293500070b9dfc6ab66e31383f8f7fccf6a95fe2",
                    "old_path": "sources",
                    "status": "M"
                  }
                },
                {
                  "README.md": {
                    "lines_added": 5,
                    "lines_removed": 0,
                    "new_id": "bd913ea153650b94f33f53e5164c36a28b761bf4",
                    "old_id": "0000000000000000000000000000000000000000",
                    "old_path": "README.md",
                    "status": "A"
                  },
                  "sources": {
                    "lines_added": 10,
                    "lines_removed": 0,
                    "new_id": "540916fbd3d825d14cc0c0b2397606fda69379ce",
                    "old_id": "265f133a7c94ede4cb183dd808219c5bf9e08f87",
                    "old_path": "sources",
                    "status": "M"
                  }
                }
            ]
        )

    @patch('pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_pull_request_diffstats_file_modified_deleted(self):
        """ Test the api_pull_request_merge method of the flask api. """
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        self.assertEqual(len(repo.requests), 1)
        pagure.lib.tasks.update_pull_request(repo.requests[0].uid)

        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'test.git'),
            readme_name='README.md', branch='test')
        tests.remove_file_git_repo(
            os.path.join(self.path, 'repos', 'test.git'),
            filename='sources', branch='test')

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        self.assertEqual(len(repo.requests), 1)
        pagure.lib.tasks.update_pull_request(repo.requests[0].uid)

        output = self.app.get('/api/0/test/pull-request/1/diffstats')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
              "README.md": {
                "lines_added": 5,
                "lines_removed": 0,
                "new_id": "bd913ea153650b94f33f53e5164c36a28b761bf4",
                "old_id": "0000000000000000000000000000000000000000",
                "old_path": "README.md",
                "status": "A"
              },
              "sources": {
                "lines_added": 0,
                "lines_removed": 5,
                "new_id": "0000000000000000000000000000000000000000",
                "old_id": "265f133a7c94ede4cb183dd808219c5bf9e08f87",
                "old_path": "sources",
                "status": "D"
              }
            }
        )

class PagureApiThresholdReachedTests(tests.Modeltests):
    """ Test the behavior of the threshold_reached value returned by the API.
    """
    maxDiff = None

    def _clean_data(self, data):
        data['project']['date_created'] = '1516348115'
        data['project']['date_modified'] = '1516348115'
        data['repo_from']['date_created'] = '1516348115'
        data['repo_from']['date_modified'] = '1516348115'
        data['uid'] = 'e8b68df8711648deac67c3afed15a798'
        data['commit_start'] = '114f1b468a5f05e635fcb6394273f3f907386eab'
        data['commit_stop'] = '114f1b468a5f05e635fcb6394273f3f907386eab'
        data['date_created'] = '1516348115'
        data['last_updated'] = '1516348115'
        data['updated_on'] = '1516348115'
        data['comments'] = []  # Let's not check the comments
        return data

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environment for the tests. """
        super(PagureApiThresholdReachedTests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos', 'test.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Add a token for user `foo`
        item = pagure.lib.model.Token(
            id='aaabbbcccddd_foo',
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow()
                + datetime.timedelta(days=30)
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session, token_id="aaabbbcccddd_foo")

        # Add a minimal required score:
        repo = pagure.lib.query._get_project(self.session, 'test')
        settings = repo.settings
        settings['Minimum_score_to_merge_pull-request'] = 2
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
        self.assertEqual(output.status_code, 200)

        self.expected_data = {
            'assignee': None,
            'branch': 'master',
            'branch_from': 'test',
            'cached_merge_status': 'unknown',
            'closed_at': None,
            'closed_by': None,
            'comments': [],
            'commit_start': '114f1b468a5f05e635fcb6394273f3f907386eab',
            'commit_stop': '114f1b468a5f05e635fcb6394273f3f907386eab',
            'date_created': '1516348115',
            'id': 1,
            'initial_comment': 'Nothing much, the changes speak for themselves',
            'last_updated': '1516348115',
            'project': {'access_groups': {'admin': [],
                                            'commit': [],
                                            'ticket':[]},
                         'access_users': {'admin': [],
                                           'commit': [],
                                           'owner': ['pingou'],
                                           'ticket': []},
                         'close_status': ['Invalid',
                                           'Insufficient data',
                                           'Fixed',
                                           'Duplicate'],
                         'custom_keys': [],
                         'date_created': '1516348115',
                         'date_modified': '1516348115',
                         'description': 'test project #1',
                         'fullname': 'test',
                         'id': 1,
                         'milestones': {},
                         'name': 'test',
                         'namespace': None,
                         'parent': None,
                         'priorities': {},
                         'tags': [],
                         'url_path': 'test',
                         'user': {'fullname': 'PY C', 'name': 'pingou'}},
            'remote_git': None,
            'repo_from': {'access_groups': {'admin': [],
                                              'commit': [],
                                              'ticket': []},
                           'access_users': {'admin': [],
                                             'commit': [],
                                             'owner': ['pingou'],
                                             'ticket': []},
                           'close_status': ['Invalid',
                                             'Insufficient data',
                                             'Fixed',
                                             'Duplicate'],
                           'custom_keys': [],
                           'date_created': '1516348115',
                           'date_modified': '1516348115',
                           'description': 'test project #1',
                           'fullname': 'test',
                           'id': 1,
                           'milestones': {},
                           'name': 'test',
                           'namespace': None,
                           'parent': None,
                           'priorities': {},
                           'tags': [],
                           'url_path': 'test',
                           'user': {'fullname': 'PY C', 'name': 'pingou'}},
            'status': 'Open',
            'threshold_reached': None,
            'title': 'Test PR',
            'uid': 'e8b68df8711648deac67c3afed15a798',
            'updated_on': '1516348115',
            'user': {'fullname': 'PY C', 'name': 'pingou'}
        }

    def test_api_pull_request_no_comments(self):
        """ Check the value of threshold_reach when the PR has no comments.
        """

        # Check the PR with 0 comment:
        output = self.app.get('/api/0/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data = self._clean_data(data)
        self.expected_data["threshold_reached"] = False
        self.assertDictEqual(data, self.expected_data)

    def test_api_pull_request_one_comments(self):
        """ Check the value of threshold_reach when the PR has one comment.
        """
        # Check the PR with 1 comment:
        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'comment': 'This is a very interesting solution :thumbsup:',
        }
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        output = self.app.get('/api/0/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data = self._clean_data(data)
        self.expected_data["threshold_reached"] = False
        self.assertDictEqual(data, self.expected_data)

    def test_api_pull_request_two_comments_one_person(self):
        """ Check the value of threshold_reach when the PR has two comments
        but from the same person.
        """
        # Add two comments from the same user:
        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'comment': 'This is a very interesting solution :thumbsup:',
        }
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'comment': 'Indeed it is :thumbsup:',
        }
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        output = self.app.get('/api/0/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data = self._clean_data(data)
        self.expected_data["threshold_reached"] = False
        self.assertDictEqual(data, self.expected_data)

    def test_api_pull_request_two_comments_two_persons(self):
        """ Check the value of threshold_reach when the PR has two comments
        from two different persons.
        """
        # Add two comments from two users:
        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'comment': 'This is a very interesting solution :thumbsup:',
        }
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        headers = {'Authorization': 'token aaabbbcccddd_foo'}
        data = {
            'comment': 'Indeed it is :thumbsup:',
        }
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        output = self.app.get('/api/0/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data = self._clean_data(data)
        data['comments'] = []  # Let's not check the comments
        self.expected_data["threshold_reached"] = True
        self.assertDictEqual(data, self.expected_data)

    def test_api_pull_request_three_comments_two_persons_changed_to_no(self):
        """ Check the value of threshold_reach when the PR has three
        comments from two person among which one changed their mind from
        +1 to -1.
        """
        # Add three comments from two users:
        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'comment': 'This is a very interesting solution :thumbsup:',
        }
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        headers = {'Authorization': 'token aaabbbcccddd_foo'}
        data = {
            'comment': 'Indeed it is :thumbsup:',
        }
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        data = {
            'comment': 'Nevermind the bug is elsewhere in fact :thumbsdown:',
        }
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        output = self.app.get('/api/0/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data = self._clean_data(data)
        data['comments'] = []  # Let's not check the comments
        self.expected_data["threshold_reached"] = False
        self.assertDictEqual(data, self.expected_data)

    def test_api_pull_request_three_comments_two_persons_changed_to_yes(self):
        """ Check the value of threshold_reach when the PR has three
        comments from two person among which one changed their mind from
        -1 to +1
        """
        # Add three comments from two users:
        headers = {'Authorization': 'token aaabbbcccddd'}
        data = {
            'comment': 'This is a very interesting solution :thumbsup:',
        }
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        headers = {'Authorization': 'token aaabbbcccddd_foo'}
        data = {
            'comment': 'I think the bug is elsewhere :thumbsdown:',
        }
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        data = {
            'comment': 'Nevermind it is here :thumbsup:',
        }
        output = self.app.post(
            '/api/0/test/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        output = self.app.get('/api/0/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data = self._clean_data(data)
        data['comments'] = []  # Let's not check the comments
        self.expected_data["threshold_reached"] = True
        self.assertDictEqual(data, self.expected_data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
