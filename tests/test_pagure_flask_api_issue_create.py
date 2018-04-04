# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

import datetime
import unittest
import sys
import os
import json

from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure  # noqa: E402
import pagure.lib  # noqa: E402
import tests  # noqa: E402


class PagureFlaskApiIssueCreatetests(tests.Modeltests):
    """ Tests for the flask API of pagure for creating an issue
    """

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiIssueCreatetests, self).setUp()

        pagure.config.config['TICKETS_FOLDER'] = None

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'tickets'))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create project-less token for user foo
        item = pagure.lib.model.Token(
            id='project-less-foo',
            user_id=2,
            project_id=None,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30)
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(self.session, token_id='project-less-foo')

        # Create project-specific token for user foo
        item = pagure.lib.model.Token(
            id='project-specific-foo',
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(days=30)
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens_acl(
            self.session, token_id='project-specific-foo')

    def test_create_issue_own_project_no_data(self):
        """ Test creating a new ticket on a project for which you're the
        main maintainer.
        """

        # pingou's token with all the ACLs
        headers = {'Authorization': 'token aaabbbcccddd'}

        # Create an issue on /test/ where pingou is the main admin
        output = self.app.post('/api/0/test/new_issue', headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDREQ.name, data['error_code'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDREQ.value, data['error'])
        self.assertEqual(
            data['errors'],
            {
                'issue_content': ['This field is required.'],
                'title': ['This field is required.']
            }
        )

    def test_create_issue_own_project_incomplete_data(self):
        """ Test creating a new ticket on a project for which you're the
        main maintainer.
        """

        # pingou's token with all the ACLs
        headers = {'Authorization': 'token aaabbbcccddd'}

        # complete data set
        data = {
            'title': 'test issue',
        }

        # Create an issue on /test/ where pingou is the main admin
        output = self.app.post(
            '/api/0/test/new_issue',
            headers=headers,
            data=data)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDREQ.name, data['error_code'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDREQ.value, data['error'])
        self.assertEqual(
            data['errors'],
            {
                'issue_content': ['This field is required.']
            }
        )

    def test_create_issue_own_project(self):
        """ Test creating a new ticket on a project for which you're the
        main maintainer.
        """

        # pingou's token with all the ACLs
        headers = {'Authorization': 'token aaabbbcccddd'}

        # complete data set
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
        }

        # Create an issue on /test/ where pingou is the main admin
        output = self.app.post(
            '/api/0/test/new_issue',
            headers=headers,
            data=data)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertEqual(
            data,
            {
              "issue": {
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
              },
              "message": "Issue created"
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_create_issue_someone_else_project_project_less_token(self):
        """ Test creating a new ticket on a project with which you have
        nothing to do.
        """

        # pingou's token with all the ACLs
        headers = {'Authorization': 'token project-less-foo'}

        # complete data set
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
        }

        # Create an issue on /test/ where pingou is the main admin
        output = self.app.post(
            '/api/0/test/new_issue',
            headers=headers,
            data=data)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertEqual(
            data,
            {
              "issue": {
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
                  "fullname": "foo bar",
                  "name": "foo"
                }
              },
              "message": "Issue created"
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_create_issue_project_specific_token(self):
        """ Test creating a new ticket on a project with a regular
        project-specific token.
        """

        # pingou's token with all the ACLs
        headers = {'Authorization': 'token project-specific-foo'}

        # complete data set
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
        }

        # Create an issue on /test/ where pingou is the main admin
        output = self.app.post(
            '/api/0/test/new_issue',
            headers=headers,
            data=data)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertEqual(
            data,
            {
              "issue": {
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
                  "fullname": "foo bar",
                  "name": "foo"
                }
              },
              "message": "Issue created"
            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_create_issue_invalid_project_specific_token(self):
        """ Test creating a new ticket on a project with a regular
        project-specific token but for another project.
        """

        # pingou's token with all the ACLs
        headers = {'Authorization': 'token project-specific-foo'}

        # complete data set
        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
        }

        # Create an issue on /test/ where pingou is the main admin
        output = self.app.post(
            '/api/0/test2/new_issue',
            headers=headers,
            data=data)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data['error_code'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.value, data['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
