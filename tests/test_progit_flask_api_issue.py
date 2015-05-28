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
                  "https://pagure.org/ to get or renew your API token.",
              "error_code": "EINVALIDTOK",
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
            'status': 'Open',
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
              "assignee": None,
              "author": None,
              "issues": [
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
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ],
              "status": None,
              "tags": []
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
              "assignee": None,
              "author": None,
              "issues": [
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
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ],
              "status": None,
              "tags": []
            }
        )
        headers = {'Authorization': 'token aaabbbccc'}

        # Access issues authenticated but wrong token
        output = self.app.get('/api/0/test/issues', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issues'][0]['date_created'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "assignee": None,
              "author": None,
              "issues": [
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
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ],
              "status": None,
              "tags": []
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
              "assignee": None,
              "author": None,
              "issues": [
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
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                },
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
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ],
              "status": None,
              "tags": []
            }
        )

        # List closed issue
        output = self.app.get('/api/0/test/issues?status=Closed', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "assignee": None,
              "author": None,
              "issues": [],
              "status": "Closed",
              "tags": []
            }
        )

        # List closed issue
        output = self.app.get('/api/0/test/issues?status=Invalid', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "assignee": None,
              "author": None,
              "issues": [],
              "status": "Invalid",
              "tags": []
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
              "date_created": "1431414800",
              "depends": [],
              "id": 1,
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
              "date_created": "1431414800",
              "depends": [],
              "id": 2,
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
        tests.create_projects_git(os.path.join(tests.HERE, 'tickets'))
        tests.create_tokens(self.session)
        tests.create_acls(self.session)
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
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or expired token. Please visit " \
                  "https://pagure.org/ to get or renew your API token.",
              "error_code": "EINVALIDTOK",
            }
        )

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
            project_id=3,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)
        self.session.commit()

        # Give `change_status_issue` to this token
        item = pagure.lib.model.TokenAcl(
            token_id='pingou_foo',
            acl_id=4,
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
            {'message': 'Edited successfully issue #1'}
        )

        headers = {'Authorization': 'token pingou_foo'}

        # Un-authorized issue
        output = self.app.post(
            '/api/0/foo/issue/1/status', data=data, headers=headers)
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "You are not allowed to view this issue",
              "error_code": "EISSUENOTALLOWED",
            }
        )

    def test_api_comment_issue(self):
        """ Test the api_comment_issue method of the flask api. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_acls(self.session)
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
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or expired token. Please visit " \
                  "https://pagure.org/ to get or renew your API token.",
              "error_code": "EINVALIDTOK",
            }
        )

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
            project_id=3,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)
        self.session.commit()

        # Give `change_status_issue` to this token
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
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "You are not allowed to view this issue",
              "error_code": "EISSUENOTALLOWED",
            }
        )

        # No comment added
        repo = pagure.lib.get_project(self.session, 'foo')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskApiIssuetests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
