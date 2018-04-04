# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


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


class PagureFlaskApiIssueCommenttests(tests.Modeltests):
    """ Tests for the flask API of pagure for changing the status of an
    issue
    """

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiIssueCommenttests, self).setUp()

        pagure.config.config['TICKETS_FOLDER'] = None

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'tickets'))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

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

    def test_api_comment_issue_invalid_project(self):
        """ Test the api_comment_issue method of the flask api. """

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post('/api/0/foo/issue/1/comment', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

    def test_api_comment_issue_invalid_project_token(self):
        """ Test the api_comment_issue method of the flask api. """

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Valid token, wrong project
        output = self.app.post('/api/0/test2/issue/1/comment', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

    def test_api_comment_issue_invalid_issue(self):
        """ Test the api_comment_issue method of the flask api. """

        headers = {'Authorization': 'token aaabbbcccddd'}
        # Invalid issue
        output = self.app.post('/api/0/test/issue/10/comment', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Issue not found",
                "error_code": "ENOISSUE",
            }
        )

    def test_api_comment_issue_incomplete_request(self):
        """ Test the api_comment_issue method of the flask api. """

        headers = {'Authorization': 'token aaabbbcccddd'}
        # Check comments before
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        data = {
            'title': 'test issue',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test/issue/1/comment', data=data, headers=headers)
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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.status, 'Open')

    def test_api_comment_issue(self):
        """ Test the api_comment_issue method of the flask api. """

        headers = {'Authorization': 'token aaabbbcccddd'}

        data = {
            'comment': 'This is a very interesting question',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/issue/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        # One comment added
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)

    def test_api_comment_issue_private_un_authorized(self):
        """ Test the api_comment_issue method of the flask api. """

        # Check before
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=2)
        self.assertEqual(len(issue.comments), 0)

        data = {
            'comment': 'This is a very interesting question',
        }
        headers = {'Authorization': 'token pingou_foo'}

        # Valid request but un-authorized
        output = self.app.post(
            '/api/0/test/issue/2/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No comment added
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=2)
        self.assertEqual(len(issue.comments), 0)

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_comment_issue_private(self):
        """ Test the api_comment_issue method of the flask api. """

        # Create token for user foo
        item = pagure.lib.model.Token(
            id='foo_token2',
            user_id=2,
            project_id=1,
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
            '/api/0/test/issue/2/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

    def test_api_comment_issue_invalid_project_project_less(self):
        """ Test the api_comment_issue method of the flask api. """

        headers = {'Authorization': 'token project-less-foo'}

        # Invalid project
        output = self.app.post('/api/0/foo/issue/1/comment', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

    def test_api_comment_issue_invalid_project_token_project_less(self):
        """ Test the api_comment_issue method of the flask api. """

        headers = {'Authorization': 'token project-less-foo'}

        # Valid token, no such issue, project-less token so different failure
        output = self.app.post('/api/0/test2/issue/1/comment', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Issue not found",
                "error_code": "ENOISSUE",
            }
        )

    def test_api_comment_issue_invalid_issue_project_less(self):
        """ Test the api_comment_issue method of the flask api. """

        headers = {'Authorization': 'token project-less-foo'}
        # Invalid issue
        output = self.app.post('/api/0/test/issue/10/comment', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Issue not found",
                "error_code": "ENOISSUE",
            }
        )

    def test_api_comment_issue_incomplete_request_project_less(self):
        """ Test the api_comment_issue method of the flask api. """

        headers = {'Authorization': 'token project-less-foo'}
        # Check comments before
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        data = {
            'title': 'test issue',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test/issue/1/comment', data=data, headers=headers)
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
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.status, 'Open')

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_comment_issue_project_less(self):
        """ Test the api_comment_issue method of the flask api. """

        headers = {'Authorization': 'token project-less-foo'}

        data = {
            'comment': 'This is a very interesting question',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/issue/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        # One comment added
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)

    def test_api_comment_issue_private_un_authorized_project_less(self):
        """ Test the api_comment_issue method of the flask api. """

        # Check before
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=2)
        self.assertEqual(len(issue.comments), 0)

        data = {
            'comment': 'This is a very interesting question',
        }
        headers = {'Authorization': 'token pingou_foo'}

        # Valid request but un-authorized
        output = self.app.post(
            '/api/0/test/issue/2/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        # No comment added
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=2)
        self.assertEqual(len(issue.comments), 0)

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_comment_issue_private_project_less(self):
        """ Test the api_comment_issue method of the flask api. """

        # Create token for user foo
        item = pagure.lib.model.Token(
            id='foo_token2',
            user_id=2,
            project_id=None,
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
            '/api/0/test/issue/2/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
