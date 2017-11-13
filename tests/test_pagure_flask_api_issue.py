# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

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
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests

FULL_ISSUE_LIST = [
  {
    "assignee": None,
    "blocks": [],
    "close_status": None,
    "closed_at": None,
    "comments": [],
    "content": "We should work on this",
    "custom_fields": [],
    "date_created": "1431414800",
    "depends": [],
    "id": 9,
    "last_updated": "1431414800",
    "milestone": None,
    "priority": None,
    "private": True,
    "status": "Closed",
    "tags": [],
    "title": "Test issue",
    "user": {
      "fullname": "PY C",
      "name": "pingou"
    }
  },
  {
    "assignee": {'fullname': 'foo bar', 'name': 'foo'},
    "blocks": [],
    "close_status": None,
    "closed_at": None,
    "comments": [],
    "content": "This issue needs attention",
    "custom_fields": [],
    "date_created": "1431414800",
    "depends": [],
    "id": 8,
    "last_updated": "1431414800",
    "milestone": None,
    "priority": None,
    "private": True,
    "status": "Open",
    "tags": [],
    "title": "test issue1",
    "user": {
      "fullname": "PY C",
      "name": "pingou"
    }
  },
  {
    "assignee": None,
    "blocks": [],
    "close_status": None,
    "closed_at": None,
    "comments": [],
    "content": "This issue needs attention",
    "custom_fields": [],
    "date_created": "1431414800",
    "depends": [],
    "id": 7,
    "last_updated": "1431414800",
    "milestone": None,
    "priority": None,
    "private": True,
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
    "close_status": None,
    "closed_at": None,
    "comments": [],
    "content": "This issue needs attention",
    "custom_fields": [],
    "date_created": "1431414800",
    "depends": [],
    "id": 6,
    "last_updated": "1431414800",
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
  },
  {
    "assignee": None,
    "blocks": [],
    "close_status": None,
    "closed_at": None,
    "comments": [],
    "content": "This issue needs attention",
    "custom_fields": [],
    "date_created": "1431414800",
    "depends": [],
    "id": 5,
    "last_updated": "1431414800",
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
  },
  {
    "assignee": None,
    "blocks": [],
    "close_status": None,
    "closed_at": None,
    "comments": [],
    "content": "This issue needs attention",
    "custom_fields": [],
    "date_created": "1431414800",
    "depends": [],
    "id": 4,
    "last_updated": "1431414800",
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
  },
  {
    "assignee": None,
    "blocks": [],
    "close_status": None,
    "closed_at": None,
    "comments": [],
    "content": "This issue needs attention",
    "custom_fields": [],
    "date_created": "1431414800",
    "depends": [],
    "id": 3,
    "last_updated": "1431414800",
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
  },
  {
    "assignee": None,
    "blocks": [],
    "close_status": None,
    "closed_at": None,
    "comments": [],
    "content": "This issue needs attention",
    "custom_fields": [],
    "date_created": "1431414800",
    "depends": [],
    "id": 2,
    "last_updated": "1431414800",
    "milestone": "milestone-1.0",
    "priority": None,
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
    "close_status": None,
    "closed_at": None,
    "comments": [],
    "content": "This issue needs attention",
    "custom_fields": [],
    "date_created": "1431414800",
    "depends": [],
    "id": 1,
    "last_updated": "1431414800",
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


LCL_ISSUES = [
  {
    'assignee': None,
    'blocks': [],
    'close_status': None,
    'closed_at': None,
    'comments': [],
    'content': 'Description',
    'custom_fields': [],
    'date_created': '1431414800',
    'depends': [],
    'id': 2,
    'last_updated': '1431414800',
    'milestone': None,
    'priority': None,
    'private': False,
    'status': 'Open',
    'tags': [],
    'title': 'Issue #2',
    'user': {'fullname': 'PY C', 'name': 'pingou'}
  },
  {
    'assignee': None,
    'blocks': [],
    'close_status': None,
    'closed_at': None,
    'comments': [],
    'content': 'Description',
    'custom_fields': [],
    'date_created': '1431414800',
    'depends': [],
    'id': 1,
    'last_updated': '1431414800',
    'milestone': None,
    'priority': None,
    'private': False,
    'status': 'Open',
    'tags': [],
    'title': 'Issue #1',
    'user': {'fullname': 'PY C', 'name': 'pingou'}
   }
]


class PagureFlaskApiIssuetests(tests.SimplePagureTest):
    """ Tests for the flask API of pagure for issue """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiIssuetests, self).setUp()
        pagure.config.config['TICKETS_FOLDER'] = None

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
              "error": "Invalid or incomplete input submitted",
              "error_code": "EINVALIDREQ",
              "errors": {
                "issue_content": ["This field is required."],
                "title": ["This field is required."],
              }
            }
        )

        data = {
            'title': 'test issue'
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
              "error": "Invalid or incomplete input submitted",
              "error_code": "EINVALIDREQ",
              "errors": {
                "issue_content": ["This field is required."],
                "title": ["This field is required."]
              }
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
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[8],
              "message": "Issue created"
            }
        )

        # Valid request but invalid milestone
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'milestone': ['milestone-1.0'],
        }
        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submitted",
              "error_code": "EINVALIDREQ",
              "errors": {
                "milestone": [
                  "Not a valid choice"
                ]
              }
            }
        )

        # Set some milestones
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        repo.milestones = {'milestone-1.0': '', 'milestone-2.0': 'Tomorrow!'}
        self.session.add(repo)
        self.session.commit()

        # Valid request with milestone
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'milestone': ['milestone-1.0'],
        }
        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'

        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[7],
              "message": "Issue created"
            }
        )

        # Valid request, with private='false'
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'private': 'false',
        }

        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[6],
              "message": "Issue created"
            }
        )

        # Valid request, with private=False
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'private': False
        }

        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[5],
              "message": "Issue created"
            }
        )

        # Valid request, with private='False'
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'private': 'False'
        }

        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[4],
              "message": "Issue created"
            }
        )

        # Valid request, with private=0
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'private': 0
        }

        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[3],
              "message": "Issue created"
            }
        )

        # Private issue: True
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'private': True,
        }
        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[2],
              "message": "Issue created"
            }
        )

        # Private issue: 1
        data = {
            'title': 'test issue1',
            'issue_content': 'This issue needs attention',
            'private': 1,
            'assignee': 'foo'
        }
        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        exp = copy.deepcopy(FULL_ISSUE_LIST[1])
        exp['id'] = 8
        self.assertDictEqual(
            data,
            {
              "issue": exp,
              "message": "Issue created"
            }
        )

    def test_api_new_issue_user_token(self):
        """ Test the api_new_issue method of the flask api. """
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'tickets'), bare=True)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Valid token, invalid request - No input
        output = self.app.post('/api/0/test2/new_issue', headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submitted",
              "error_code": "EINVALIDREQ",
              "errors": {
                "issue_content": ["This field is required."],
                "title": ["This field is required."],
              }
            }
        )

        # Another project, still an invalid request - No input
        output = self.app.post('/api/0/test/new_issue', headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submitted",
              "error_code": "EINVALIDREQ",
              "errors": {
                "issue_content": ["This field is required."],
                "title": ["This field is required."],
              }
            }
        )

        data = {
            'title': 'test issue'
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
              "error": "Invalid or incomplete input submitted",
              "error_code": "EINVALIDREQ",
              "errors": {
                "issue_content": ["This field is required."],
                "title": ["This field is required."]
              }
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
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[8],
              "message": "Issue created"
            }
        )

        # Set some milestones
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        repo.milestones = {'milestone-1.0': '', 'milestone-2.0': 'Tomorrow!'}
        self.session.add(repo)
        self.session.commit()

        # Valid request with milestone
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'milestone': ['milestone-1.0'],
        }
        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'

        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[7],
              "message": "Issue created"
            }
        )

        # Valid request, with private='false'
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'private': 'false',
        }

        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[6],
              "message": "Issue created"
            }
        )

        # Valid request, with private=False
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'private': False
        }

        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[5],
              "message": "Issue created"
            }
        )

        # Valid request, with private='False'
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'private': 'False'
        }

        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[4],
              "message": "Issue created"
            }
        )

        # Valid request, with private=0
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'private': 0
        }

        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[3],
              "message": "Issue created"
            }
        )

        # Private issue: True
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
            'private': True,
        }
        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[2],
              "message": "Issue created"
            }
        )

        # Private issue: 1
        data = {
            'title': 'test issue1',
            'issue_content': 'This issue needs attention',
            'private': 1,
            'assignee': 'foo'
        }
        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "issue": FULL_ISSUE_LIST[1],
              "message": "Issue created"
            }
        )

        # Private issue: 'true'
        data = {
            'title': 'test issue1',
            'issue_content': 'This issue needs attention',
            'private': 'true',
        }
        output = self.app.post(
            '/api/0/test/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        exp = copy.deepcopy(FULL_ISSUE_LIST[1])
        exp['id'] = 9
        exp['assignee'] = None
        self.assertDictEqual(
            data,
            {
              "issue": exp,
              "message": "Issue created"
            }
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
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": [],
              },
              "issues": FULL_ISSUE_LIST[3:],
              "total_issues": 6
            }
        )

        # Create private issue
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=True,
            status="Closed"
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Access issues un-authenticated
        output = self.app.get('/api/0/test/issues')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": []
              },
              "issues": FULL_ISSUE_LIST[3:],
              "total_issues": 6
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
        self.session.commit()

        headers = {'Authorization': 'token bar_token'}

        # Access issues authenticated but wrong token
        output = self.app.get('/api/0/test/issues', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": []
              },
              "issues": FULL_ISSUE_LIST[3:],
              "total_issues": 6
            }
        )

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Access issues authenticated correctly
        output = self.app.get('/api/0/test/issues', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'

        exp = FULL_ISSUE_LIST[1]
        exp['id'] = 8

        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": []
              },
              "issues": FULL_ISSUE_LIST[1:],
              "total_issues": 8
            }
        )
        headers = {'Authorization': 'token aaabbbccc'}

        # Access issues authenticated but non-existing token
        output = self.app.get('/api/0/test/issues', headers=headers)
        self.assertEqual(output.status_code, 401)

        # Create a new token for another user
        item = pagure.lib.model.Token(
            id='bar_token_foo',
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)
        self.session.commit()

        headers = {'Authorization': 'token bar_token_foo'}

        # Access issues authenticated but wrong token
        output = self.app.get('/api/0/test/issues', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": []
              },
              "issues": FULL_ISSUE_LIST[3:],
              "total_issues": 6
            }
        )

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Access issues authenticated correctly
        output = self.app.get('/api/0/test/issues', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": []
              },
              "issues": FULL_ISSUE_LIST[1:],
              "total_issues": 8
            }
        )

        # List closed issue
        output = self.app.get('/api/0/test/issues?status=Closed', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['issues'][0]['date_created'] = '1431414800'
        data['issues'][0]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                "milestones": [],
                "no_stones": None,
                'order': None,
                "priority": None,
                "since": None,
                "status": "Closed",
                "tags": []
              },
              "issues": [FULL_ISSUE_LIST[0]],
              "total_issues": 1,
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
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
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
        for idx in range(len(data['issues'])):
            data['issues'][idx]['last_updated'] = '1431414800'
            data['issues'][idx]['date_created'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
                "status": "All",
                "tags": []
              },
              "issues": FULL_ISSUE_LIST,
              "total_issues": 9
            }
        )

    def test_api_view_issues_reversed(self):
        """ Test the api_view_issues method of the flask api. in reversed
        order.

        """
        self.test_api_new_issue()

        headers = {'Authorization': 'token aaabbbcccddd'}

        # List issues in reverse order
        output = self.app.get('/api/0/test/issues?order=asc', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['last_updated'] = '1431414800'
            data['issues'][idx]['date_created'] = '1431414800'
        expected = {
            "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': 'asc',
                'priority': None,
                "since": None,
                "status": None,
                "tags": []
            },
            "issues": FULL_ISSUE_LIST[1:][::-1],
            "total_issues": 8
        }
        self.assertDictEqual(data, expected)

    def test_api_view_issues_milestone(self):
        """ Test the api_view_issues method of the flask api when filtering
        for a milestone.
        """
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'tickets'), bare=True)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        repo = pagure.lib.get_authorized_project(self.session, 'test')

        # Create 2 tickets but only 1 has a milestone
        start = datetime.datetime.utcnow().strftime('%s')
        issue = pagure.lib.model.Issue(
            id=pagure.lib.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title='Issue #1',
            content='Description',
            user_id=1,  # pingou
            uid='issue#1',
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        issue = pagure.lib.model.Issue(
            id=pagure.lib.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title='Issue #2',
            content='Description',
            user_id=1,  # pingou
            uid='issue#2',
            private=False,
            milestone='v1.0',
        )
        self.session.add(issue)
        self.session.commit()

        # List all opened issues
        output = self.app.get('/api/0/test/issues')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        lcl_issues = copy.deepcopy(LCL_ISSUES)
        lcl_issues[0]['milestone'] = 'v1.0'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": [],
              },
              "issues": lcl_issues,
              "total_issues": 2
            }
        )

        # List all issues of the milestone v1.0
        output = self.app.get('/api/0/test/issues?milestones=v1.0')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': ['v1.0'],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": [],
              },
              "issues": [lcl_issues[0]],
              "total_issues": 1
            }
        )

    def test_api_view_issues_priority(self):
        """ Test the api_view_issues method of the flask api when filtering
        for a priority.
        """
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'tickets'), bare=True)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        repo = pagure.lib.get_authorized_project(self.session, 'test')

        # Create 2 tickets but only 1 has a priority
        start = datetime.datetime.utcnow().strftime('%s')
        issue = pagure.lib.model.Issue(
            id=pagure.lib.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title='Issue #1',
            content='Description',
            user_id=1,  # pingou
            uid='issue#1',
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        issue = pagure.lib.model.Issue(
            id=pagure.lib.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title='Issue #2',
            content='Description',
            user_id=1,  # pingou
            uid='issue#2',
            private=False,
            priority=1,
        )
        self.session.add(issue)
        self.session.commit()

        # Set some priorities to the project
        repo.priorities = {'1': 'High', '2': 'Normal'}
        self.session.add(repo)
        self.session.commit()

        # List all opened issues
        output = self.app.get('/api/0/test/issues')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        lcl_issues = copy.deepcopy(LCL_ISSUES)
        lcl_issues[0]['priority'] = 1
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": [],
              },
              "issues": lcl_issues,
              "total_issues": 2
            }
        )

        # List all issues of the priority high (ie: 1)
        output = self.app.get('/api/0/test/issues?priority=high')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': 'high',
                "since": None,
                "status": None,
                "tags": [],
              },
              "issues": [lcl_issues[0]],
              "total_issues": 1
            }
        )

        output = self.app.get('/api/0/test/issues?priority=1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': '1',
                "since": None,
                "status": None,
                "tags": [],
              },
              "issues": [lcl_issues[0]],
              "total_issues": 1
            }
        )

    def test_api_view_issues_priority_invalid(self):
        """ Test the api_view_issues method of the flask api when filtering
        for an invalid priority.
        """
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'tickets'), bare=True)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Try getting issues with an invalid priority
        output = self.app.get('/api/0/test/issues?priority=foobar')
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid priority submitted",
              "error_code": "EINVALIDPRIORITY"
            }
        )

    def test_api_view_issues_no_stones(self):
        """ Test the api_view_issues method of the flask api when filtering
        with no_stones.
        """
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'tickets'), bare=True)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        repo = pagure.lib.get_authorized_project(self.session, 'test')

        # Create 2 tickets but only 1 has a milestone
        start = datetime.datetime.utcnow().strftime('%s')
        issue = pagure.lib.model.Issue(
            id=pagure.lib.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title='Issue #1',
            content='Description',
            user_id=1,  # pingou
            uid='issue#1',
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        issue = pagure.lib.model.Issue(
            id=pagure.lib.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title='Issue #2',
            content='Description',
            user_id=1,  # pingou
            uid='issue#2',
            private=False,
            milestone='v1.0',
        )
        self.session.add(issue)
        self.session.commit()

        # List all opened issues
        output = self.app.get('/api/0/test/issues')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        lcl_issues = copy.deepcopy(LCL_ISSUES)
        lcl_issues[0]['milestone'] = 'v1.0'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": [],
              },
              "issues": lcl_issues,
              "total_issues": 2
            }
        )

        # List all issues with no milestone
        output = self.app.get('/api/0/test/issues?no_stones=1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': True,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": [],
              },
              "issues": [lcl_issues[1]],
              "total_issues": 1
            }
        )

        # List all issues with a milestone
        output = self.app.get('/api/0/test/issues?no_stones=0')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': False,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": [],
              },
              "issues": [lcl_issues[0]],
              "total_issues": 1
            }
        )

    def test_api_view_issues_since(self):
        """ Test the api_view_issues method of the flask api for since option """

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'tickets'), bare=True)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        repo = pagure.lib.get_authorized_project(self.session, 'test')

        # Create 1st tickets
        start = datetime.datetime.utcnow().strftime('%s')
        issue = pagure.lib.model.Issue(
            id=pagure.lib.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title='Issue #1',
            content='Description',
            user_id=1,  # pingou
            uid='issue#1',
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        time.sleep(1)
        middle = datetime.datetime.utcnow().strftime('%s')

        # Create 2nd tickets
        issue = pagure.lib.model.Issue(
            id=pagure.lib.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title='Issue #2',
            content='Description',
            user_id=1,  # pingou
            uid='issue#2',
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        time.sleep(1)
        final = datetime.datetime.utcnow().strftime('%s')

        # Create private issue
        issue = pagure.lib.model.Issue(
            id=pagure.lib.get_next_id(self.session, repo.id),
            project_id=repo.id,
            title='Issue #3',
            content='Description',
            user_id=1,  # pingou
            uid='issue#3',
            private=True,
        )
        self.session.add(issue)
        self.session.commit()

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
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": None,
                "status": None,
                "tags": []
              },
              "issues": LCL_ISSUES,
              "total_issues": 2
            }
        )

        time.sleep(1)
        late = datetime.datetime.utcnow().strftime('%s')

        # List all opened issues from the start
        output = self.app.get('/api/0/test/issues?since=%s' % start)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": start,
                "status": None,
                "tags": []
              },
              "issues": LCL_ISSUES,
              "total_issues": 2
            }
        )

        # List all opened issues from the middle
        output = self.app.get('/api/0/test/issues?since=%s' % middle)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": middle,
                "status": None,
                "tags": []
              },
              "issues": LCL_ISSUES[:1],
              "total_issues": 1
            }
        )

        # List all opened issues at the end
        output = self.app.get('/api/0/test/issues?since=%s' % final)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['date_created'] = '1431414800'
            data['issues'][idx]['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": final,
                "status": None,
                "tags": []
              },
              "issues": [],
              "total_issues": 0
            }
        )

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Test since for a value before creation of issues
        output = self.app.get(
            '/api/0/test/issues?since=%s' % final, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for idx in range(len(data['issues'])):
            data['issues'][idx]['last_updated'] = '1431414800'
            data['issues'][idx]['date_created'] = '1431414800'
        self.assertDictEqual(
            data,
            {
              "args": {
                "assignee": None,
                "author": None,
                'milestones': [],
                'no_stones': None,
                'order': None,
                'priority': None,
                "since": final,
                "status": None,
                "tags": []
              },
              "issues": [{
                'assignee': None,
                'blocks': [],
                'close_status': None,
                'closed_at': None,
                'comments': [],
                'content': 'Description',
                'custom_fields': [],
                'date_created': '1431414800',
                'depends': [],
                'id': 3,
                'last_updated': '1431414800',
                'milestone': None,
                'priority': None,
                'private': True,
                'status': 'Open',
                'tags': [],
                'title': 'Issue #3',
                'user': {'fullname': 'PY C', 'name': 'pingou'}}
              ],
              "total_issues": 1
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
        data['last_updated'] = '1431414800'
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
              "last_updated": "1431414800",
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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
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
        output = self.app.get('/api/0/test/issue/7')
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
        output = self.app.get('/api/0/test/issue/6', headers=headers)
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
        self.session.commit()

        headers = {'Authorization': 'token bar_token'}

        # Access private issue authenticated but wrong token
        output = self.app.get('/api/0/test/issue/7', headers=headers)
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
        output = self.app.get('/api/0/test/issue/6', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['date_created'] = '1431414800'
        data['last_updated'] = '1431414800'
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
              "id": 6,
              "last_updated": "1431414800",
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

        # Access private issue authenticated correctly using the issue's uid
        output = self.app.get('/api/0/test/issue/aaabbbccc', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['date_created'] = '1431414800'
        data['last_updated'] = '1431414800'
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
              "id": 9,
              "last_updated": "1431414800",
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

    def test_api_change_milestone_issue(self):
        """ Test the api_change_milestone_issue method of the flask api. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'tickets'))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Set some milestones to the project
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        repo.milestones = {'v1.0': None, 'v2.0': 'Soon'}
        self.session.add(repo)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post('/api/0/foo/issue/1/milestone', headers=headers)
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
        output = self.app.post('/api/0/test2/issue/1/milestone', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No issue
        output = self.app.post('/api/0/test/issue/1/milestone', headers=headers)
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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
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

        # Check milestone before
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.milestone, None)

        data = {
            'milestone': '',
        }

        # Valid request but no milestone specified
        output = self.app.post(
            '/api/0/test/issue/1/milestone', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'No changes'}
        )

        # No change
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.milestone, None)

        data = {
            'milestone': 'milestone-1-0',
        }

        # Invalid milestone specified
        output = self.app.post(
            '/api/0/test/issue/1/milestone', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "milestone": [
                        "Not a valid choice"
                    ]
                }
            }
        )

        data = {
            'milestone': 'v1.0',
        }

        # Valid requests
        output = self.app.post(
            '/api/0/test/issue/1/milestone', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "message": [
                    "Issue set to the milestone: v1.0"
                ]
            }
        )

        # remove milestone
        data = {
            'milestone': '',
        }

        # Valid requests
        output = self.app.post(
            '/api/0/test/issue/1/milestone', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "message": [
                    "Issue set to the milestone: None (was: v1.0)"
                ]
            }
        )

        # Change recorded
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.milestone, None)

        data = {
            'milestone': 'v1.0',
        }

        # Valid requests
        output = self.app.post(
            '/api/0/test/issue/1/milestone', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "message": [
                    "Issue set to the milestone: v1.0"
                ]
            }
        )

        # remove milestone by using no milestone in JSON
        data = {}

        # Valid requests
        output = self.app.post(
            '/api/0/test/issue/1/milestone', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "message": [
                    "Issue set to the milestone: None (was: v1.0)"
                ]
            }
        )

        # Change recorded
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.milestone, None)

        headers = {'Authorization': 'token pingou_foo'}

        # Un-authorized issue
        output = self.app.post(
            '/api/0/foo/issue/1/milestone', data=data, headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_view_issue_comment(self, p_send_email, p_ugt):
        """ Test the api_view_issue_comment endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'tickets'))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create normal issue in test
        repo = pagure.lib.get_authorized_project(self.session, 'test')
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


        headers = {'Authorization': 'token aaabbbcccddd'}

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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)

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

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_view_issue_comment_private(self, p_send_email, p_ugt):
        """ Test the api_view_issue_comment endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'tickets'))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create normal issue in test
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this',
            user='foo',
            ticketfolder=None,
            private=True,
            issue_uid='aaabbbccc#1',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')

        # Create a token for another user
        item = pagure.lib.model.Token(
            id='foo_token_2',
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30)
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session, token_id='foo_token_2')

        # Add a comment to that issue
        data = {
            'comment': 'This is a very interesting question',
        }
        headers = {'Authorization': 'token foo_token_2'}
        output = self.app.post(
            '/api/0/test/issue/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        # Private issue - no auth
        output = self.app.get('/api/0/test/issue/1/comment/2')
        self.assertEqual(output.status_code, 403)

        # Private issue - Auth - Invalid token
        headers = {'Authorization': 'token aaabbbcccdddee'}
        output = self.app.get('/api/0/test/issue/1/comment/2', headers=headers)
        self.assertEqual(output.status_code, 401)

        # Private issue - Auth - valid token - unknown comment
        headers = {'Authorization': 'token foo_token_2'}
        output = self.app.get('/api/0/test/issue/1/comment/3', headers=headers)
        self.assertEqual(output.status_code, 404)

        # Private issue - Auth - valid token - known comment
        headers = {'Authorization': 'token foo_token_2'}
        output = self.app.get('/api/0/test/issue/1/comment/1', headers=headers)
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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        # No change
        repo = pagure.lib.get_authorized_project(self.session, 'test')
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
            {'message': 'Issue assigned to pingou'}
        )

        # Un-assign
        output = self.app.post(
            '/api/0/test/issue/1/assign', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Assignee reset'}
        )
        # No change
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.assignee, None)

        # Un-assign
        data = {'assignee': None}
        output = self.app.post(
            '/api/0/test/issue/1/assign', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Nothing to change'}
        )
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.assignee, None)

        # Re-assign for the rest of the tests
        data = {'assignee': 'pingou'}
        output = self.app.post(
            '/api/0/test/issue/1/assign', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Issue assigned to pingou'}
        )

        # Un-assign
        data = {'assignee': ''}
        output = self.app.post(
            '/api/0/test/issue/1/assign', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Assignee reset'}
        )

        # Re-assign for the rest of the tests
        data = {'assignee': 'pingou'}
        output = self.app.post(
            '/api/0/test/issue/1/assign', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Issue assigned to pingou'}
        )

        # One comment added
        self.session = pagure.lib.create_session(self.dbpath)
        repo = pagure.lib.get_authorized_project(self.session, 'test')
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
            acl_id=6,
        )
        self.session.add(item)
        self.session.commit()

        repo = pagure.lib.get_authorized_project(self.session, 'foo')
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
        repo = pagure.lib.get_authorized_project(self.session, 'foo')
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
        repo = pagure.lib.get_authorized_project(self.session, 'foo')
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
            {'message': 'Issue assigned to pingou'}
        )

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_assign_issue_issuer(self, p_send_email, p_ugt):
        """ Test the api_assign_issue method of the flask api. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session, user_id=2)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Create normal issue
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=False,
            issue_uid='aaabbbccc#1',
            assignee='foo',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')

        # Check comments before
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        # Un-assign
        data = {'assignee': None}
        output = self.app.post(
            '/api/0/test/issue/1/assign', data={}, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Assignee reset'}
        )

        # No longer allowed to self-assign since no access
        data = {
            'assignee': 'foo',
        }
        output = self.app.post(
            '/api/0/test/issue/1/assign', data=data, headers=headers)
        self.assertEqual(output.status_code, 403)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                u'error': u'You are not allowed to view this issue',
                u'error_code': u'EISSUENOTALLOWED'
            }
        )

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_subscribe_issue(self, p_send_email, p_ugt):
        """ Test the api_subscribe_issue method of the flask api. """
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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(
            pagure.lib.get_watch_list(self.session, issue),
            set(['pingou', 'foo']))


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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(
            pagure.lib.get_watch_list(self.session, issue),
            set(['pingou', 'foo']))

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

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(
            pagure.lib.get_watch_list(self.session, issue),
            set(['pingou', 'foo', 'bar']))

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

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(
            pagure.lib.get_watch_list(self.session, issue),
            set(['pingou', 'foo']))

    def test_api_update_custom_field(self):
        """ Test the api_update_custom_field method of the flask api. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'tickets'))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/issue/1/custom/bugzilla', headers=headers)
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
            '/api/0/test2/issue/1/custom/bugzilla', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No issue
        output = self.app.post(
            '/api/0/test/issue/1/custom/bugzilla', headers=headers)
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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
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

        # Project does not have this custom field
        output = self.app.post(
            '/api/0/test/issue/1/custom/bugzilla', headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid custom field submitted",
              "error_code": "EINVALIDISSUEFIELD",
            }
        )

        # Check the behavior if the project disabled the issue tracker
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['issue_tracker'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.post(
            '/api/0/test/issue/1/custom/bugzilla', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Issue tracker disabled for this project",
              "error_code": "ETRACKERDISABLED",
            }
        )

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['issue_tracker'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        # Invalid API token
        headers = {'Authorization': 'token foobar'}

        output = self.app.post(
            '/api/0/test/issue/1/custom/bugzilla', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or expired token. Please visit "
                  "https://pagure.org/ to get or renew your API token.",
              "error_code": "EINVALIDTOK",
            }
        )

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Set some custom fields
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.set_custom_key_fields(
            self.session, repo,
            ['bugzilla', 'upstream', 'reviewstatus'],
            ['link', 'boolean', 'list'],
            ['unused data for non-list type', '', 'ack, nack ,  needs review'],
            [None, None, None])
        self.session.commit()
        self.assertEqual(msg, 'List of custom fields updated')

        # Check the project custom fields were correctly set
        for key in repo.issue_keys:
            # Check that the bugzilla field correctly had its data removed
            if key.name == "bugzilla":
                self.assertIsNone(key.data)

            # Check that the reviewstatus list field still has its list
            if key.name == "reviewstatus":
                self.assertEqual(
                    sorted(key.data), ['ack', 'nack', 'needs review'])

        # Check that not setting the value on a non-existing custom field
        # changes nothing
        output = self.app.post(
            '/api/0/test/issue/1/custom/bugzilla', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              'message': 'No changes'
            }
        )

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.other_fields, [])
        self.assertEqual(len(issue.other_fields), 0)

        # Invalid value
        output = self.app.post(
            '/api/0/test/issue/1/custom/bugzilla', headers=headers,
            data={'value': 'foobar'})
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid custom field submitted, the value is not "
                  "a link",
              "error_code": "EINVALIDISSUEFIELD_LINK",
            }
        )

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.other_fields, [])
        self.assertEqual(len(issue.other_fields), 0)

        # All good
        output = self.app.post(
            '/api/0/test/issue/1/custom/bugzilla', headers=headers,
            data={'value': 'https://bugzilla.redhat.com/1234'})
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "message": "Custom field bugzilla adjusted to "
                "https://bugzilla.redhat.com/1234"
            }
        )

        self.session = pagure.lib.create_session(self.dbpath)
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.other_fields), 1)
        self.assertEqual(issue.other_fields[0].key.name, 'bugzilla')
        self.assertEqual(
            issue.other_fields[0].value,
            'https://bugzilla.redhat.com/1234')

        # Reset the value
        output = self.app.post(
            '/api/0/test/issue/1/custom/bugzilla', headers=headers,
            data={'value': ''})
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "message": "Custom field bugzilla reset "
                  "(from https://bugzilla.redhat.com/1234)"
            }
        )

        self.session = pagure.lib.create_session(self.dbpath)
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.other_fields), 0)

    def test_api_view_issues_history_stats(self):
        """ Test the api_view_issues_history_stats method of the flask api. """
        self.test_api_new_issue()

        # Create private issue
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=True,
            status="Closed"
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        output = self.app.get('/api/0/test/issues/history/stats')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)

        self.assertEqual(len(data), 1)
        self.assertEqual(len(data['stats']), 53)
        last_key = sorted(data['stats'].keys())[-1]
        self.assertEqual(data['stats'][last_key], 7)
        for k in sorted(data['stats'].keys())[:-1]:
            self.assertEqual(data['stats'][k], 0)

    def test_api_view_user_issues_pingou(self):
        """ Test the api_view_user_issues method of the flask api for pingou.
        """
        self.test_api_new_issue()

        # Create private issue
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=True,
            status="Closed"
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        output = self.app.get('/api/0/user/pingou/issues')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        args = {
            u"assignee": True,
            u"author": True,
            "milestones": [],
            "no_stones": None,
            "order": None,
            "order_key": None,
            "page": 1,
            "since": None,
            "status": None,
            "tags": []
        }

        self.assertEqual(data['args'], args)
        self.assertEqual(data['issues_assigned'], [])
        self.assertEqual(len(data['issues_created']), 8)
        self.assertEqual(data['total_issues_assigned'], 0)
        self.assertEqual(data['total_issues_created'], 8)
        self.assertEqual(data['total_issues_assigned_pages'], 1)
        self.assertEqual(data['total_issues_created_pages'], 1)

        # Restrict to a certain, fake milestone
        output = self.app.get('/api/0/user/pingou/issues?milestones=v1.0')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        args = {
            u"assignee": True,
            u"author": True,
            "milestones": ['v1.0'],
            "no_stones": None,
            "order": None,
            "order_key": None,
            "page": 1,
            "since": None,
            "status": None,
            "tags": []
        }

        self.assertEqual(data['args'], args)
        self.assertEqual(data['issues_assigned'], [])
        self.assertEqual(data['issues_created'], [])
        self.assertEqual(data['total_issues_assigned'], 0)
        self.assertEqual(data['total_issues_created'], 0)
        self.assertEqual(data['total_issues_assigned_pages'], 1)
        self.assertEqual(data['total_issues_created_pages'], 1)

        # Restrict to a certain status
        output = self.app.get('/api/0/user/pingou/issues?status=closed')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        args = {
            u"assignee": True,
            u"author": True,
            "milestones": [],
            "no_stones": None,
            "order": None,
            "order_key": None,
            "page": 1,
            "since": None,
            "status": 'closed',
            "tags": []
        }

        self.assertEqual(data['args'], args)
        self.assertEqual(data['issues_assigned'], [])
        self.assertEqual(len(data['issues_created']), 1)
        self.assertEqual(data['total_issues_assigned'], 0)
        self.assertEqual(data['total_issues_created'], 1)
        self.assertEqual(data['total_issues_assigned_pages'], 1)
        self.assertEqual(data['total_issues_created_pages'], 1)

        # Restrict to a certain status
        output = self.app.get('/api/0/user/pingou/issues?status=all')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        args = {
            u"assignee": True,
            u"author": True,
            "milestones": [],
            "no_stones": None,
            "order": None,
            "order_key": None,
            "page": 1,
            "since": None,
            "status": 'all',
            "tags": []
        }

        self.assertEqual(data['args'], args)
        self.assertEqual(data['issues_assigned'], [])
        self.assertEqual(len(data['issues_created']), 9)
        self.assertEqual(data['total_issues_assigned'], 0)
        self.assertEqual(data['total_issues_created'], 9)
        self.assertEqual(data['total_issues_assigned_pages'], 1)
        self.assertEqual(data['total_issues_created_pages'], 1)

    def test_api_view_user_issues_foo(self):
        """ Test the api_view_user_issues method of the flask api for foo.
        """
        self.test_api_new_issue()

        # Create private issue
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=True,
            status="Closed"
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        output = self.app.get('/api/0/user/foo/issues')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        args = {
            u"assignee": True,
            u"author": True,
            u"milestones": [],
            u"no_stones": None,
            u"order": None,
            u"order_key": None,
            u"page": 1,
            u"since": None,
            u"status": None,
            u"tags": [],
        }

        self.assertEqual(data['args'], args)
        self.assertEqual(len(data['issues_assigned']), 1)
        self.assertEqual(data['issues_created'], [])
        self.assertEqual(data['total_issues_assigned'], 1)
        self.assertEqual(data['total_issues_created'], 0)
        self.assertEqual(data['total_issues_assigned_pages'], 1)
        self.assertEqual(data['total_issues_created_pages'], 1)

    def test_api_view_user_issues_foo_invalid_page(self):
        """ Test the api_view_user_issues method of the flask api for foo.
        """
        self.test_api_new_issue()

        output = self.app.get('/api/0/user/foo/issues?page=0')
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)

        self.assertEqual(
            data,
            {
                u'error': u'Invalid page requested',
                u'error_code': u'ENOCODE'
            }
        )

        output = self.app.get('/api/0/user/foo/issues?page=abc')
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)

        self.assertEqual(
            data,
            {
                u'error': u'Invalid page requested',
                u'error_code': u'ENOCODE'
            }
        )

    def test_api_view_user_issues_foo_no_assignee(self):
        """ Test the api_view_user_issues method of the flask api for foo.
        """
        self.test_api_new_issue()

        output = self.app.get('/api/0/user/foo/issues?assignee=0')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        args = {
            u"assignee": False,
            u"author": True,
            u"milestones": [],
            u"no_stones": None,
            u"order": None,
            u"order_key": None,
            u"page": 1,
            u"since": None,
            u"status": None,
            u"tags": [],
        }

        self.assertEqual(data['args'], args)
        self.assertEqual(data['issues_assigned'], [])
        self.assertEqual(data['issues_created'], [])
        self.assertEqual(data['total_issues_assigned'], 0)
        self.assertEqual(data['total_issues_created'], 0)
        self.assertEqual(data['total_issues_assigned_pages'], 1)
        self.assertEqual(data['total_issues_created_pages'], 1)

    def test_api_view_user_issues_pingou_no_author(self):
        """ Test the api_view_user_issues method of the flask api for pingou.
        """
        self.test_api_new_issue()

        output = self.app.get('/api/0/user/pingou/issues?author=0')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        args = {
            u"assignee": True,
            u"author": False,
            "milestones": [],
            "no_stones": None,
            "order": None,
            "order_key": None,
            "page": 1,
            "since": None,
            "status": None,
            "tags": []
        }

        self.assertEqual(data['args'], args)
        self.assertEqual(data['issues_assigned'], [])
        self.assertEqual(data['issues_created'], [])
        self.assertEqual(data['total_issues_assigned'], 0)
        self.assertEqual(data['total_issues_created'], 0)
        self.assertEqual(data['total_issues_assigned_pages'], 1)
        self.assertEqual(data['total_issues_created_pages'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
