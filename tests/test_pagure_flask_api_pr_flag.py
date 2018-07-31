# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

import unittest
import sys
import os

import json
from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure  # noqa
import pagure.config  # noqa
import pagure.lib  # noqa
import tests  # noqa


class PagureFlaskApiPRFlagtests(tests.Modeltests):
    """ Tests for the flask API of pagure for flagging pull-requests """

    maxDiff = None

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiPRFlagtests, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None

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

        # Check flags before
        self.session.commit()
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 0)

    def test_invalid_project(self):
        """ Test the flagging a PR on an invalid project. """

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

    def test_incorrect_project(self):
        """ Test the flagging a PR on the wrong project. """
        headers = {'Authorization': 'token aaabbbcccddd'}

        # Valid token, wrong project
        output = self.app.post(
            '/api/0/test2/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

    def test_pr_disabled(self):
        """ Test the flagging a PR when PRs are disabled. """

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}

        # PRs disabled
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                u'error': u'Pull-Request have been deactivated for this project',
                u'error_code': u'EPULLREQUESTSDISABLED'
            }
        )

    def test_no_pr(self):
        """ Test the flagging a PR when the PR doesn't exist. """
        headers = {'Authorization': 'token aaabbbcccddd'}

        # No PR
        output = self.app.post(
            '/api/0/test/pull-request/10/flag', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Pull-Request not found",
                "error_code": "ENOREQ",
            }
        )

    def test_no_input(self):
        """ Test the flagging an existing PR but with no data. """
        headers = {'Authorization': 'token aaabbbcccddd'}

        # No input
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                'error': 'Invalid or incomplete input submitted',
                'error_code': 'EINVALIDREQ',
                'errors': {
                    'comment': ['This field is required.'],
                    'url': ['This field is required.'],
                    'username': ['This field is required.']
                }
            }
        )

    def test_no_comment(self):
        """ Test the flagging an existing PR but with incomplete data. """
        headers = {'Authorization': 'token aaabbbcccddd'}

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
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 0)

    @patch('pagure.lib.notify.send_email')
    def test_flagging_a_pul_request_with_notification(self, mock_email):
        """ Test the flagging a PR. """
        headers = {'Authorization': 'token aaabbbcccddd'}

        # Enable PR notifications
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['notify_on_pull-request_flag'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

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
        data = json.loads(output.get_data(as_text=True))
        data['flag']['date_created'] = '1510742565'
        pr_uid = data['flag']['pull_request_uid']
        data['flag']['pull_request_uid'] = '62b49f00d489452994de5010565fab81'
        self.assertDictEqual(
            data,
            {
                'flag': {
                    'comment': 'Tests running',
                    'date_created': '1510742565',
                    'percent': None,
                    'pull_request_uid': '62b49f00d489452994de5010565fab81',
                    'status': 'pending',
                    'url': 'http://jenkins.cloud.fedoraproject.org/',
                    'user': {
                        'default_email': 'bar@pingou.com',
                        'emails': ['bar@pingou.com', 'foo@pingou.com'],
                        'fullname': 'PY C',
                        'name': 'pingou'
                    },
                    'username': 'Jenkins'},
                'message': 'Flag added',
                'uid': 'jenkins_build_pagure_100+seed'
            }
        )

        # One flag added
        self.session.commit()
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].comment, 'Tests running')
        self.assertEqual(request.flags[0].percent, None)

        # Check the notification sent
        mock_email.assert_called_once_with(
            '\nJenkins flagged the pull-request `test pull-request` '
            'as pending: Tests running\n\n'
            'http://localhost.localdomain/test/pull-request/1\n',
            'PR #1 - Jenkins: pending',
            'bar@pingou.com',
            in_reply_to='test-pull-request-' + pr_uid,
            mail_id='test-pull-request-' + pr_uid + '-1',
            project_name='test',
            user_from='Jenkins'
        )

    def test_updating_flag(self):
        """ Test the updating the flag of a PR. """
        headers = {'Authorization': 'token aaabbbcccddd'}

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
        data = json.loads(output.get_data(as_text=True))
        data['flag']['date_created'] = '1510742565'
        data['flag']['pull_request_uid'] = '62b49f00d489452994de5010565fab81'
        self.assertDictEqual(
            data,
            {
                'flag': {
                    'comment': 'Tests running',
                    'date_created': '1510742565',
                    'percent': None,
                    'pull_request_uid': '62b49f00d489452994de5010565fab81',
                    'status': 'pending',
                    'url': 'http://jenkins.cloud.fedoraproject.org/',
                    'user': {
                        'default_email': 'bar@pingou.com',
                        'emails': ['bar@pingou.com', 'foo@pingou.com'],
                        'fullname': 'PY C',
                        'name': 'pingou'
                    },
                    'username': 'Jenkins'},
                'message': 'Flag added',
                'uid': 'jenkins_build_pagure_100+seed'
            }
        )

        # One flag added
        self.session.commit()
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
        data = json.loads(output.get_data(as_text=True))
        data['flag']['date_created'] = '1510742565'
        data['flag']['pull_request_uid'] = '62b49f00d489452994de5010565fab81'
        self.assertDictEqual(
            data,
            {
                'flag': {
                    'comment': 'Tests passed',
                    'date_created': '1510742565',
                    'percent': 100,
                    'pull_request_uid': '62b49f00d489452994de5010565fab81',
                    'status': 'success',
                    'url': 'http://jenkins.cloud.fedoraproject.org/',
                    'user': {
                        'default_email': 'bar@pingou.com',
                        'emails': ['bar@pingou.com', 'foo@pingou.com'],
                        'fullname': 'PY C',
                        'name': 'pingou'
                    },
                    'username': 'Jenkins'},
                'message': 'Flag updated',
                'uid': 'jenkins_build_pagure_100+seed'
            }
        )

        # One flag added
        self.session.commit()
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].comment, 'Tests passed')
        self.assertEqual(request.flags[0].percent, 100)

    def test_adding_two_flags(self):
        """ Test the adding two flags to a PR. """
        headers = {'Authorization': 'token aaabbbcccddd'}

        data = {
            'username': 'Jenkins',
            'comment': 'Tests passed',
            'status': 'success',
            'percent': '100',
            'url': 'http://jenkins.cloud.fedoraproject.org/',
            'uid': 'jenkins_build_pagure_100+seed',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['flag']['date_created'] = '1510742565'
        data['flag']['pull_request_uid'] = '62b49f00d489452994de5010565fab81'
        self.assertDictEqual(
            data,
            {
                'flag': {
                    'comment': 'Tests passed',
                    'date_created': '1510742565',
                    'percent': 100,
                    'pull_request_uid': '62b49f00d489452994de5010565fab81',
                    'status': 'success',
                    'url': 'http://jenkins.cloud.fedoraproject.org/',
                    'user': {
                        'default_email': 'bar@pingou.com',
                        'emails': ['bar@pingou.com', 'foo@pingou.com'],
                        'fullname': 'PY C',
                        'name': 'pingou'
                    },
                    'username': 'Jenkins'},
                'message': 'Flag added',
                'uid': 'jenkins_build_pagure_100+seed'
            }
        )

        # One flag added
        self.session.commit()
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
        data = json.loads(output.get_data(as_text=True))
        data['flag']['date_created'] = '1510742565'
        data['flag']['pull_request_uid'] = '62b49f00d489452994de5010565fab81'
        self.assertNotEqual(
            data['uid'], 'jenkins_build_pagure_100+seed')
        data['uid'] = 'jenkins_build_pagure_100+seed'
        self.assertDictEqual(
            data,
            {
                'flag': {
                    'comment': 'Tests running again',
                    'date_created': '1510742565',
                    'percent': None,
                    'pull_request_uid': '62b49f00d489452994de5010565fab81',
                    'status': 'pending',
                    'url': 'http://jenkins.cloud.fedoraproject.org/',
                    'user': {
                        'default_email': 'bar@pingou.com',
                        'emails': ['bar@pingou.com', 'foo@pingou.com'],
                        'fullname': 'PY C',
                        'name': 'pingou'
                    },
                    'username': 'Jenkins'},
                'message': 'Flag added',
                'uid': 'jenkins_build_pagure_100+seed'
            }
        )

        # Two flag added
        self.session.commit()
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 2)
        self.assertEqual(request.flags[0].comment, 'Tests passed')
        self.assertEqual(request.flags[0].percent, 100)
        self.assertEqual(request.flags[1].comment, 'Tests running again')
        self.assertEqual(request.flags[1].percent, None)

    @patch.dict('pagure.config.config',
                {
                    'FLAG_STATUSES_LABELS':
                        {
                            'pend!': 'label-info',
                            'succeed!': 'label-success',
                            'fail!': 'label-danger',
                            'what?': 'label-warning',
                        },
                    'FLAG_PENDING': 'pend!',
                    'FLAG_SUCCESS': 'succeed!',
                    'FLAG_FAILURE': 'fail!',
                })
    def test_flagging_a_pull_request_while_having_custom_statuses(self):
        """ Test flagging a PR while having custom statuses. """
        headers = {'Authorization': 'token aaabbbcccddd'}

        # No status and no percent => should use FLAG_PENDING
        send_data = {
            'username': 'Jenkins',
            'comment': 'Tests running',
            'url': 'http://jenkins.cloud.fedoraproject.org/',
            'uid': 'jenkins_build_pagure_100+seed',
        }

        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=send_data, headers=headers)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(output.status_code, 200)
        self.assertEqual(data['flag']['status'], 'pend!')

        # No status and 50 % => should use FLAG_SUCCESS
        send_data['percent'] = 50
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=send_data, headers=headers)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(output.status_code, 200)
        self.assertEqual(data['flag']['status'], 'succeed!')

        # No status and 0 % => should use FLAG_FAILURE
        send_data['percent'] = 0
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=send_data, headers=headers)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(output.status_code, 200)
        self.assertEqual(data['flag']['status'], 'fail!')

        # Explicitly set status
        send_data['status'] = 'what?'
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=send_data, headers=headers)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(output.status_code, 200)
        self.assertEqual(data['flag']['status'], 'what?')

        # Explicitly set wrong status
        send_data['status'] = 'nooo.....'
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=send_data, headers=headers)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(output.status_code, 400)
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"status": ["Not a valid choice"]}
            }
        )


class PagureFlaskApiPRFlagUserTokentests(tests.Modeltests):
    """ Tests for the flask API of pagure for flagging pull-requests using
    an user token (ie: not restricted to a specific project).
    """

    maxDiff = None

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiPRFlagUserTokentests, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None

        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
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

        # Check flags before
        self.session.commit()
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 0)

    def test_no_pr(self):
        """ Test flagging a non-existing PR. """
        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

    def test_no_pr_other_project(self):
        """ Test flagging a non-existing PR on a different project. """
        headers = {'Authorization': 'token aaabbbcccddd'}
        # Valid token, wrong project
        output = self.app.post(
            '/api/0/test2/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Pull-Request not found",
                "error_code": "ENOREQ",
            }
        )

    def test_no_input(self):
        """ Test flagging an existing PR but without submitting any data. """
        headers = {'Authorization': 'token aaabbbcccddd'}

        # No input
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                'error': 'Invalid or incomplete input submitted',
                'error_code': 'EINVALIDREQ',
                'errors': {
                    'comment': ['This field is required.'],
                    'url': ['This field is required.'],
                    'username': ['This field is required.']
                }
            }
        )

    def test_no_comment(self):
        """ Test flagging an existing PR but without all the required info.
        """
        headers = {'Authorization': 'token aaabbbcccddd'}

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
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 0)

    def test_invalid_status(self):
        """ Test flagging an existing PR but with an invalid status.
        """
        headers = {'Authorization': 'token aaabbbcccddd'}

        data = {
            'username': 'Jenkins',
            'status': 'failed',
            'comment': 'Failed to run the tests',
            'url': 'http://jenkins.cloud.fedoraproject.org/',
            'uid': 'jenkins_build_pagure_100+seed',
        }

        # Invalid status submitted
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"status": ["Not a valid choice"]}
            }
        )

        # No change
        self.session.commit()
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 0)

    @patch('pagure.lib.notify.send_email')
    def test_flag_pr_no_status(self, mock_email):
        """ Test flagging an existing PR without providing a status.

        Also check that no notifications have been sent.
        """
        headers = {'Authorization': 'token aaabbbcccddd'}

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
        data = json.loads(output.get_data(as_text=True))
        data['flag']['date_created'] = '1510742565'
        data['flag']['pull_request_uid'] = '62b49f00d489452994de5010565fab81'
        self.assertDictEqual(
            data,
            {
                'flag': {
                    'comment': 'Tests failed',
                    'date_created': '1510742565',
                    'percent': 0,
                    'pull_request_uid': '62b49f00d489452994de5010565fab81',
                    'status': 'failure',
                    'url': 'http://jenkins.cloud.fedoraproject.org/',
                    'user': {
                        'default_email': 'bar@pingou.com',
                        'emails': ['bar@pingou.com', 'foo@pingou.com'],
                        'fullname': 'PY C',
                        'name': 'pingou'
                    },
                    'username': 'Jenkins'},
                'message': 'Flag added',
                'uid': 'jenkins_build_pagure_100+seed'
            }
        )

        # One flag added
        self.session.commit()
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].comment, 'Tests failed')
        self.assertEqual(request.flags[0].percent, 0)

        # no notifications sent
        mock_email.assert_not_called()

    def test_editing_flag(self):
        """ Test flagging an existing PR without providing a status.
        """
        headers = {'Authorization': 'token aaabbbcccddd'}

        data = {
            'username': 'Jenkins',
            'status': 'failure',
            'comment': 'Tests failed',
            'url': 'http://jenkins.cloud.fedoraproject.org/',
            'uid': 'jenkins_build_pagure_100+seed',
        }

        # Valid request  -  w/o providing the status
        output = self.app.post(
            '/api/0/test/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['flag']['date_created'] = '1510742565'
        data['flag']['pull_request_uid'] = '62b49f00d489452994de5010565fab81'
        self.assertDictEqual(
            data,
            {
                'flag': {
                    'comment': 'Tests failed',
                    'date_created': '1510742565',
                    'percent': None,
                    'pull_request_uid': '62b49f00d489452994de5010565fab81',
                    'status': 'failure',
                    'url': 'http://jenkins.cloud.fedoraproject.org/',
                    'user': {
                        'default_email': 'bar@pingou.com',
                        'emails': ['bar@pingou.com', 'foo@pingou.com'],
                        'fullname': 'PY C',
                        'name': 'pingou'
                    },
                    'username': 'Jenkins'},
                'message': 'Flag added',
                'uid': 'jenkins_build_pagure_100+seed'
            }
        )

        # One flag added
        self.session.commit()
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].comment, 'Tests failed')
        self.assertEqual(request.flags[0].percent, None)

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
        data = json.loads(output.get_data(as_text=True))
        data['flag']['date_created'] = '1510742565'
        data['flag']['pull_request_uid'] = '62b49f00d489452994de5010565fab81'
        self.assertDictEqual(
            data,
            {
                'flag': {
                    'comment': 'Tests passed',
                    'date_created': '1510742565',
                    'percent': 100,
                    'pull_request_uid': '62b49f00d489452994de5010565fab81',
                    'status': 'success',
                    'url': 'http://jenkins.cloud.fedoraproject.org/',
                    'user': {
                        'default_email': 'bar@pingou.com',
                        'emails': ['bar@pingou.com', 'foo@pingou.com'],
                        'fullname': 'PY C',
                        'name': 'pingou'
                    },
                    'username': 'Jenkins'},
                'message': 'Flag updated',
                'uid': 'jenkins_build_pagure_100+seed'
            }
        )

        # Still only one flag
        self.session.commit()
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].comment, 'Tests passed')
        self.assertEqual(request.flags[0].percent, 100)


if __name__ == '__main__':
    unittest.main(verbosity=2)
