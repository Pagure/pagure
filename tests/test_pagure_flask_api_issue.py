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
        tests.create_projects_git(
            os.path.join(self.path, 'tickets'), bare=True)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Valid token, wrong project
        output = self.app.post('/api/0/test2/new_issue', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No input
        output = self.app.post('/api/0/test/new_issue', headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": "EINVALIDREQ",
            }
        )

        data = {
            'title': 'test issue',
        }

        # Invalid repo
        output = self.app.post(
            '/api/0/foo/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Project not found",
              "error_code": "ENOPROJECT",
            }
        )

        # Incomplete request
        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": "EINVALIDREQ",
            }
        )

        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Issue created'}
        )

    def test_api_view_issues(self):
        """ Test the api_view_issues method of the flask api. """
        self.test_api_new_issue()

        # Invalid repo
        output = self.app.get('/api/0/foo/issues')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Project not found",
              "error_code": "ENOPROJECT",
            }
        )

        # List all opened issues
        output = self.app.get('/api/0/test/issues')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issues'][0]['date_created'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                "status": None,
                "tags": []
              },
              "total_issues": 1,
              "issues": [
                {
                  "assignee": None,
                  "blocks": [],
                  "comments": [],
                  "content": "This issue needs attention",
                  "custom_fields": [],
                  "date_created": "1431414800",
                  "close_status": None,
                  "closed_at": None,
                  "depends": [],
                  "id": 1,
                  "milestone": None,
                  "priority": None,
                  "private": False,
                  "status": "Open",
                  "tags": [],
                  "title": "test issue",
                  "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ]
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

        # Access issues un-authenticated
        output = self.app.get('/api/0/test/issues')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issues'][0]['date_created'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                "status": None,
                "tags": []
              },
              "total_issues": 1,
              "issues": [
                {
                  "assignee": None,
                  "blocks": [],
                  "comments": [],
                  "content": "This issue needs attention",
                  "custom_fields": [],
                  "date_created": "1431414800",
                  "close_status": None,
                  "closed_at": None,
                  "depends": [],
                  "id": 1,
                  "milestone": None,
                  "priority": None,
                  "private": False,
                  "status": "Open",
                  "tags": [],
                  "title": "test issue",
                  "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ]
            }
        )
        headers = {'Authorization': 'token aaabbbccc'}

        # Access issues authenticated but non-existing token
        output = self.app.get('/api/0/test/issues', headers=headers)
        self.assertEqual(output.status_code, 401)

        # Create a new token for another user
        item = pagure.lib.model.Token(
            id='bar_token',
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)

        headers = {'Authorization': 'token bar_token'}

        # Access issues authenticated but wrong token
        output = self.app.get('/api/0/test/issues', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issues'][0]['date_created'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                "status": None,
                "tags": []
              },
              "total_issues": 1,
              "issues": [
                {
                  "assignee": None,
                  "blocks": [],
                  "comments": [],
                  "content": "This issue needs attention",
                  "custom_fields": [],
                  "date_created": "1431414800",
                  "close_status": None,
                  "closed_at": None,
                  "depends": [],
                  "id": 1,
                  "milestone": None,
                  "priority": None,
                  "private": False,
                  "status": "Open",
                  "tags": [],
                  "title": "test issue",
                  "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ]
            }
        )

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Access issues authenticated correctly
        output = self.app.get('/api/0/test/issues', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issues'][0]['date_created'] = '1431414800'
        data['issues'][1]['date_created'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                "status": None,
                "tags": []
              },
              "total_issues": 2,
              "issues": [
                {
                  "assignee": None,
                  "blocks": [],
                  "comments": [],
                  "content": "We should work on this",
                  "custom_fields": [],
                  "date_created": "1431414800",
                  "close_status": None,
                  "closed_at": None,
                  "depends": [],
                  "id": 2,
                  "milestone": None,
                  "priority": None,
                  "private": True,
                  "status": "Open",
                  "tags": [],
                  "title": "Test issue",
                  "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                },
                {
                  "assignee": None,
                  "blocks": [],
                  "comments": [],
                  "content": "This issue needs attention",
                  "custom_fields": [],
                  "date_created": "1431414800",
                  "close_status": None,
                  "closed_at": None,
                  "depends": [],
                  "id": 1,
                  "milestone": None,
                  "priority": None,
                  "private": False,
                  "status": "Open",
                  "tags": [],
                  "title": "test issue",
                  "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ]
            }
        )

        # List closed issue
        output = self.app.get('/api/0/test/issues?status=Closed', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                "status": "Closed",
                "tags": []
              },
              "total_issues": 0,
              "issues": []
            }
        )

        # List closed issue
        output = self.app.get('/api/0/test/issues?status=Invalid', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                "status": "Invalid",
                "tags": []
              },
              "total_issues": 0,
              "issues": []
            }
        )

        # List all issues
        output = self.app.get('/api/0/test/issues?status=All', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issues'][0]['date_created'] = '1431414800'
        data['issues'][1]['date_created'] = '1431414800'
        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "status": "All",
                    "tags": []
                },
                "total_issues": 2,
                "issues": [
                    {
                        "assignee": None,
                        "blocks": [],
                        "comments": [],
                        "content": "We should work on this",
                        "custom_fields": [],
                        "date_created": "1431414800",
                        "close_status": None,
                        "closed_at": None,
                        "depends": [],
                        "id": 2,
                        "milestone": None,
                        "priority": None,
                        "private": True,
                        "status": "Open",
                        "tags": [],
                        "title": "Test issue",
                        "user": {
                            "fullname": "PY C",
                            "name": "pingou"
                        }
                    },
                    {
                        "assignee": None,
                        "blocks": [],
                        "comments": [],
                        "content": "This issue needs attention",
                        "custom_fields": [],
                        "date_created": "1431414800",
                        "close_status": None,
                        "closed_at": None,
                        "depends": [],
                        "id": 1,
                        "milestone": None,
                        "priority": None,
                        "private": False,
                        "status": "Open",
                        "tags": [],
                        "title": "test issue",
                        "user": {
                            "fullname": "PY C",
                            "name": "pingou"
                        }
                    }
                ],
            }
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
              "error_code": "ENOPROJECT",
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
              "error_code": "ENOISSUE",
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
              "custom_fields": [],
              "date_created": "1431414800",
              "close_status": None,
              "closed_at": None,
              "depends": [],
              "id": 1,
              "milestone": None,
              "priority": None,
              "private": False,
              "status": "Open",
              "tags": [],
              "title": "test issue",
              "user": {
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
            issue_uid='aaabbbccc',
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
              "error_code": "EISSUENOTALLOWED",
            }
        )

        headers = {'Authorization': 'token aaabbbccc'}

        # Access private issue authenticated but non-existing token
        output = self.app.get('/api/0/test/issue/2', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # Create a new token for another user
        item = pagure.lib.model.Token(
            id='bar_token',
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)

        headers = {'Authorization': 'token bar_token'}

        # Access private issue authenticated but wrong token
        output = self.app.get('/api/0/test/issue/2', headers=headers)
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "You are not allowed to view this issue",
              "error_code": "EISSUENOTALLOWED",
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
              "custom_fields": [],
              "date_created": "1431414800",
              "close_status": None,
              "closed_at": None,
              "depends": [],
              "id": 2,
              "milestone": None,
              "priority": None,
              "private": True,
              "status": "Open",
              "tags": [],
              "title": "Test issue",
              "user": {
                "fullname": "PY C",
                "name": "pingou"
              }
            }
        )

        # Access private issue authenticated correctly using the issue's uid
        output = self.app.get('/api/0/test/issue/aaabbbccc', headers=headers)
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
              "custom_fields": [],
              "date_created": "1431414800",
              "close_status": None,
              "closed_at": None,
              "depends": [],
              "id": 2,
              "milestone": None,
              "priority": None,
              "private": True,
              "status": "Open",
              "tags": [],
              "title": "Test issue",
              "user": {
                "fullname": "PY C",
                "name": "pingou"
              }
            }
        )

    def test_api_change_status_issue(self):
        """ Test the api_change_status_issue method of the flask api. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'tickets'))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post('/api/0/foo/issue/1/status', headers=headers)
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
        output = self.app.post('/api/0/test2/issue/1/status', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No input
        output = self.app.post('/api/0/test/issue/1/status', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Issue not found",
              "error_code": "ENOISSUE",
            }
        )

        # Create normal issue
        repo = pagure.lib.get_project(self.session, 'test')
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

        # Create another project
        item = pagure.lib.model.Project(
            user_id=2,  # pingou
            name='foo',
            description='test project #3',
            hook_token='aaabbbdddeee',
        )
        self.session.add(item)
        self.session.commit()

        # Create a token for pingou for this project
        item = pagure.lib.model.Token(
            id='pingou_foo',
            user_id=1,
            project_id=4,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)
        self.session.commit()

        # Give `change_status_issue` to this token
        item = pagure.lib.model.TokenAcl(
            token_id='pingou_foo',
            acl_id=6,
        )
        self.session.add(item)
        self.session.commit()

        repo = pagure.lib.get_project(self.session, 'foo')
        # Create private issue
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='foo',
            ticketfolder=None,
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Check status before
        repo = pagure.lib.get_project(self.session, 'test')
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
            }
        )

        # No change
        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.status, 'Open')

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
        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.status, 'Open')

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
            {'message': 'Successfully edited issue #1'}
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

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_comment_issue(self, p_send_email, p_ugt):
        """ Test the api_comment_issue method of the flask api. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post('/api/0/foo/issue/1/comment', headers=headers)
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
        output = self.app.post('/api/0/test2/issue/1/comment', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No input
        output = self.app.post('/api/0/test/issue/1/comment', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Issue not found",
              "error_code": "ENOISSUE",
            }
        )

        # Create normal issue
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=False,
            issue_uid='aaabbbccc#1',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')

        # Check comments before
        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        data = {
            'title': 'test issue',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test/issue/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": "EINVALIDREQ",
            }
        )

        # No change
        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.status, 'Open')

        data = {
            'comment': 'This is a very interesting question',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/issue/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        # One comment added
        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)

        # Create another project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='foo',
            description='test project #3',
            hook_token='aaabbbdddeee',
        )
        self.session.add(item)
        self.session.commit()

        # Create a token for pingou for this project
        item = pagure.lib.model.Token(
            id='pingou_foo',
            user_id=1,
            project_id=4,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)
        self.session.commit()

        # Give `issue_change_status` to this token when `issue_comment`
        # is required
        item = pagure.lib.model.TokenAcl(
            token_id='pingou_foo',
            acl_id=2,
        )
        self.session.add(item)
        self.session.commit()

        repo = pagure.lib.get_project(self.session, 'foo')
        # Create private issue
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='foo',
            ticketfolder=None,
            private=True,
            issue_uid='aaabbbccc#2',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Check before
        repo = pagure.lib.get_project(self.session, 'foo')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        data = {
            'comment': 'This is a very interesting question',
        }
        headers = {'Authorization': 'token pingou_foo'}

        # Valid request but un-authorized
        output = self.app.post(
            '/api/0/foo/issue/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No comment added
        repo = pagure.lib.get_project(self.session, 'foo')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        # Create token for user foo
        item = pagure.lib.model.Token(
            id='foo_token2',
            user_id=2,
            project_id=4,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(days=30)
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session, token_id='foo_token2')

        data = {
            'comment': 'This is a very interesting question',
        }
        headers = {'Authorization': 'token foo_token2'}

        # Valid request and authorized
        output = self.app.post(
            '/api/0/foo/issue/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_view_issue_comment(self, p_send_email, p_ugt):
        """ Test the api_view_issue_comment endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_api_comment_issue()

        # View a comment that does not exist
        output = self.app.get('/api/0/foo/issue/100/comment/2')
        self.assertEqual(output.status_code, 404)

        # Issue exists but not the comment
        output = self.app.get('/api/0/test/issue/1/comment/2')
        self.assertEqual(output.status_code, 404)

        # Issue and comment exists
        output = self.app.get('/api/0/test/issue/1/comment/1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['date_created'] = '1435821770'
        data["comment_date"] = "2015-07-02 09:22"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
              "avatar_url": "https://seccdn.libravatar.org/avatar/...",
              "comment": "This is a very interesting question",
              "comment_date": "2015-07-02 09:22",
              "date_created": "1435821770",
              "edited_on": None,
              "editor": None,
              "notification": False,
              "id": 1,
              "parent": None,
              "user": {
                "fullname": "PY C",
                "name": "pingou"
              }
            }
        )

        # Issue and comment exists, using UID
        output = self.app.get('/api/0/test/issue/aaabbbccc#1/comment/1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['date_created'] = '1435821770'
        data["comment_date"] = "2015-07-02 09:22"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
              "avatar_url": "https://seccdn.libravatar.org/avatar/...",
              "comment": "This is a very interesting question",
              "comment_date": "2015-07-02 09:22",
              "date_created": "1435821770",
              "edited_on": None,
              "editor": None,
              "notification": False,
              "id": 1,
              "parent": None,
              "user": {
                "fullname": "PY C",
                "name": "pingou"
              }
            }
        )

        # Private issue
        output = self.app.get('/api/0/foo/issue/1/comment/2')
        self.assertEqual(output.status_code, 403)

        # Private issue - Auth - wrong token
        headers = {'Authorization': 'token pingou_foo'}
        output = self.app.get('/api/0/foo/issue/1/comment/2', headers=headers)
        self.assertEqual(output.status_code, 403)

        # Private issue - Auth - Invalid token
        headers = {'Authorization': 'token aaabbbcccddd'}
        output = self.app.get('/api/0/foo/issue/1/comment/2', headers=headers)
        self.assertEqual(output.status_code, 401)

        # Private issue - Auth - valid token - unknown comment
        headers = {'Authorization': 'token foo_token2'}
        output = self.app.get('/api/0/foo/issue/1/comment/3', headers=headers)
        self.assertEqual(output.status_code, 404)

        # Private issue - Auth - valid token - known comment
        headers = {'Authorization': 'token foo_token2'}
        output = self.app.get('/api/0/foo/issue/1/comment/2', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['date_created'] = '1435821770'
        data["comment_date"] = "2015-07-02 09:22"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
              "avatar_url": "https://seccdn.libravatar.org/avatar/...",
              "comment": "This is a very interesting question",
              "comment_date": "2015-07-02 09:22",
              "date_created": "1435821770",
              "edited_on": None,
              "editor": None,
              "notification": False,
              "id": 2,
              "parent": None,
              "user": {
                "fullname": "foo bar",
                "name": "foo"
              }
            }
        )

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_assign_issue(self, p_send_email, p_ugt):
        """ Test the api_assign_issue method of the flask api. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post('/api/0/foo/issue/1/assign', headers=headers)
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
        output = self.app.post('/api/0/test2/issue/1/assign', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No input
        output = self.app.post('/api/0/test/issue/1/assign', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Issue not found",
              "error_code": "ENOISSUE",
            }
        )

        # Create normal issue
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=False,
            issue_uid='aaabbbccc#1',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')

        # Check comments before
        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        data = {
            'title': 'test issue',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test/issue/1/assign', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": "EINVALIDREQ",
            }
        )

        # No change
        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.status, 'Open')

        data = {
            'assignee': 'pingou',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/issue/1/assign', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Issue assigned'}
        )

        # One comment added
        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.assignee.user, 'pingou')

        # Create another project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='foo',
            description='test project #3',
            hook_token='aaabbbdddeee',
        )
        self.session.add(item)
        self.session.commit()

        # Create a token for pingou for this project
        item = pagure.lib.model.Token(
            id='pingou_foo',
            user_id=1,
            project_id=4,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)
        self.session.commit()

        # Give `issue_change_status` to this token when `issue_comment`
        # is required
        item = pagure.lib.model.TokenAcl(
            token_id='pingou_foo',
            acl_id=5,
        )
        self.session.add(item)
        self.session.commit()

        repo = pagure.lib.get_project(self.session, 'foo')
        # Create private issue
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='foo',
            ticketfolder=None,
            private=True,
            issue_uid='aaabbbccc#2',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Check before
        repo = pagure.lib.get_project(self.session, 'foo')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        data = {
            'assignee': 'pingou',
        }
        headers = {'Authorization': 'token pingou_foo'}

        # Valid request but un-authorized
        output = self.app.post(
            '/api/0/foo/issue/1/assign', data=data, headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No comment added
        repo = pagure.lib.get_project(self.session, 'foo')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        # Create token for user foo
        item = pagure.lib.model.Token(
            id='foo_token2',
            user_id=2,
            project_id=4,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(days=30)
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session, token_id='foo_token2')

        data = {
            'assignee': 'pingou',
        }
        headers = {'Authorization': 'token foo_token2'}

        # Valid request and authorized
        output = self.app.post(
            '/api/0/foo/issue/1/assign', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Issue assigned'}
        )

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_subscribe_issue(self, p_send_email, p_ugt):
        """ Test the api_subscribe_issue method of the flask api. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/issue/1/subscribe', headers=headers)
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
            '/api/0/test2/issue/1/subscribe', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No input
        output = self.app.post(
            '/api/0/test/issue/1/subscribe', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Issue not found",
              "error_code": "ENOISSUE",
            }
        )

        # Create normal issue
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this',
            user='foo',
            ticketfolder=None,
            private=False,
            issue_uid='aaabbbccc#1',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')

        # Check subscribtion before
        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertFalse(
            pagure.lib.is_watching_obj(self.session, 'pingou', issue))


        # Unsubscribe - no changes
        data = {}
        output = self.app.post(
            '/api/0/test/issue/1/subscribe', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'You are no longer watching this issue'}
        )

        data = {}
        output = self.app.post(
            '/api/0/test/issue/1/subscribe', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'You are no longer watching this issue'}
        )

        # No change
        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertFalse(
            pagure.lib.is_watching_obj(self.session, 'pingou', issue))

        # Subscribe
        data = {'status': True}
        output = self.app.post(
            '/api/0/test/issue/1/subscribe', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'You are now watching this issue'}
        )

        # Subscribe - no changes
        data = {'status': True}
        output = self.app.post(
            '/api/0/test/issue/1/subscribe', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'You are now watching this issue'}
        )

        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertTrue(
            pagure.lib.is_watching_obj(self.session, 'pingou', issue))

        # Unsubscribe
        data = {}
        output = self.app.post(
            '/api/0/test/issue/1/subscribe', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'You are no longer watching this issue'}
        )

        repo = pagure.lib.get_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertFalse(
            pagure.lib.is_watching_obj(self.session, 'pingou', issue))


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskApiIssuetests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
