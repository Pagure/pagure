# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

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
import pagure.config
import pagure.lib
import pagure.lib.model as model
import tests


class PagureFlaskApiUSertests(tests.Modeltests):
    """ Tests for the flask API of pagure for issue """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiUSertests, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None


    def test_api_users(self):
        """ Test the api_users function.  """

        output = self.app.get('/api/0/users')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data['users']), ['foo', 'pingou'])
        self.assertEqual(sorted(data.keys()), ['mention', 'total_users', 'users'])
        self.assertEqual(data['total_users'], 2)

        output = self.app.get('/api/0/users?pattern=p')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(data['users'], ['pingou'])
        self.assertEqual(sorted(data.keys()), ['mention', 'total_users', 'users'])
        self.assertEqual(data['total_users'], 1)

    def test_api_view_user(self):
        """
            Test the api_view_user method of the flask api
            The tested user has no project or forks.
        """
        output = self.app.get('/api/0/user/pingou')
        self.assertEqual(output.status_code, 200)
        exp = {
            "forks": [],
            'forks_pagination': {
              'first': 'http://localhost...',
              'last': 'http://localhost...',
              'next': None,
              'forkpage': 1,
              'pages': 0,
              'per_page': 20,
              'prev': None},
            "repos": [],
            'repos_pagination': {
              'first': 'http://localhost...',
              'last': 'http://localhost...',
              'next': None,
              'repopage': 1,
              'pages': 0,
              'per_page': 20,
              'prev': None},
            "user": { "fullname": "PY C", "name": "pingou"}}
        data = json.loads(output.get_data(as_text=True))
        for k in ['forks_pagination', 'repos_pagination']:
            for k2 in ['first', 'last']:
                self.assertIsNotNone(data[k][k2])
                data[k][k2] = 'http://localhost...'
        self.assertEqual(data, exp)

    def test_api_view_user_with_project(self):
        """
            Test the api_view_user method of the flask api,
            this time the user has some project defined.
        """
        tests.create_projects(self.session)

        output = self.app.get('/api/0/user/pingou')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['repos'][0]['date_created'] = "1490272832"
        data['repos'][0]['date_modified'] = "1490272832"
        data['repos'][1]['date_created'] = "1490272832"
        data['repos'][1]['date_modified'] = "1490272832"
        data['repos'][2]['date_created'] = "1490272832"
        data['repos'][2]['date_modified'] = "1490272832"
        for k in ['forks_pagination', 'repos_pagination']:
            for k2 in ['first', 'last']:
                self.assertIsNotNone(data[k][k2])
                data[k][k2] = 'http://localhost...'
        expected_data = {
            "forks": [],
            'forks_pagination': {
              'first': 'http://localhost...',
              'last': 'http://localhost...',
              'next': None,
              'forkpage': 1,
              'pages': 0,
              'per_page': 20,
              'prev': None},
            "repos": [
                {
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
                    "date_created": "1490272832",
                    "date_modified": "1490272832",
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
                {
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
                    "date_created": "1490272832",
                    "date_modified": "1490272832",
                    "description": "test project #2",
                    "fullname": "test2",
                    "url_path": "test2",
                    "id": 2,
                    "milestones": {},
                    "name": "test2",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou"
                    }
                },
                {
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
                    "date_created": "1490272832",
                    "date_modified": "1490272832",
                    "description": "namespaced test project",
                    "fullname": "somenamespace/test3",
                    "url_path": "somenamespace/test3",
                    "id": 3,
                    "milestones": {},
                    "name": "test3",
                    "namespace": "somenamespace",
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou"
                    }
                }
            ],
            'repos_pagination': {
              'first': 'http://localhost...',
              'last': 'http://localhost...',
              'next': None,
              'repopage': 1,
              'pages': 1,
              'per_page': 20,
              'prev': None},
            "user": {
                "fullname": "PY C",
                "name": "pingou"
            }
        }
        self.assertEqual(data, expected_data)

    @patch('pagure.lib.notify.send_email')
    def test_api_view_user_activity_stats(self, mockemail):
        """ Test the api_view_user_activity_stats method of the flask user
        api. """
        mockemail.return_value = True

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Create a pull-request
        repo = pagure.lib._get_project(self.session, 'test')
        forked_repo = pagure.lib._get_project(self.session, 'test')
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
        self.session.commit()
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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        # One comment added
        self.session.commit()
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 1)

        # Close PR
        output = self.app.post(
            '/api/0/test/pull-request/1/close', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {"message": "Pull-request closed!"}
        )

        # PR closed
        self.session.commit()
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(request.status, 'Closed')

        # Finally retrieve the user's logs
        output = self.app.get('/api/0/user/pingou/activity/stats')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        date = datetime.datetime.utcnow().date().strftime('%Y-%m-%d')
        self.assertDictEqual(data, {date: 4})

    @patch('pagure.lib.notify.send_email')
    def test_api_view_user_activity_date(self, mockemail):
        """ Test the api_view_user_activity_date method of the flask user
        api. """

        self.test_api_view_user_activity_stats()

        # Invalid date
        output = self.app.get('/api/0/user/pingou/activity/AABB')
        self.assertEqual(output.status_code, 400)

        # Invalid date
        output = self.app.get('/api/0/user/pingou/activity/2016asd')
        self.assertEqual(output.status_code, 200)
        exp = {
          "activities": [],
          "date": "2016-01-01"
        }
        self.assertEqual(json.loads(output.get_data(as_text=True)), exp)

        # Date parsed, just not really as expected
        output = self.app.get('/api/0/user/pingou/activity/20161245')
        self.assertEqual(output.status_code, 200)
        exp = {
          "activities": [],
          "date": "1970-08-22"
        }
        self.assertEqual(json.loads(output.get_data(as_text=True)), exp)

        date = datetime.datetime.utcnow().date().strftime('%Y-%m-%d')
        # Retrieve the user's logs for today
        output = self.app.get('/api/0/user/pingou/activity/%s' % date)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        exp = {
          "activities": [
            {
              "date": date,
              "date_created": "1477558752",
              "type": "pull-request",
              "description_mk": "<p>pingou created PR <a href=\"/test/pull-request/1\" title=\"[Closed] test pull-request\">test#1</a></p>",
              "id": 1,
              "ref_id": "1",
              "type": "created",
              "user": {
                "fullname": "PY C",
                "name": "pingou"
              }
            },
            {
              "date": date,
              "date_created": "1477558752",
              "type": "pull-request",
              "description_mk": "<p>pingou commented on PR <a href=\"/test/pull-request/1\" title=\"[Closed] test pull-request\">test#1</a></p>",
              "id": 2,
              "ref_id": "1",
              "type": "commented",
              "user": {
                "fullname": "PY C",
                "name": "pingou"
              }
            },
            {
              "date": date,
              "date_created": "1477558752",
              "type": "pull-request",
              "description_mk": "<p>pingou closed PR <a href=\"/test/pull-request/1\" title=\"[Closed] test pull-request\">test#1</a></p>",
              "id": 3,
              "ref_id": "1",
              "type": "closed",
              "user": {
                "fullname": "PY C",
                "name": "pingou"
              }
            },
            {
              "date": date,
              "date_created": "1477558752",
              "type": "pull-request",
              "description_mk": "<p>pingou commented on PR <a href=\"/test/pull-request/1\" title=\"[Closed] test pull-request\">test#1</a></p>",
              "id": 4,
              "ref_id": "1",
              "type": "commented",
              "user": {
                "fullname": "PY C",
                "name": "pingou"
              }
            }
          ],
          "date": date,
        }
        for idx, act in enumerate(data['activities']):
            act['date_created'] = '1477558752'
            data['activities'][idx] = act

        self.assertEqual(data, exp)

    @patch('pagure.lib.notify.send_email')
    def test_api_view_user_activity_date_1_activity(self, mockemail):
        """ Test the api_view_user_activity_date method of the flask user
        api when the user only did one action. """

        tests.create_projects(self.session)
        repo = pagure.lib._get_project(self.session, 'test')

        now = datetime.datetime.utcnow()
        date = now.date().strftime('%Y-%m-%d')
        # Create a single commit log
        log = model.PagureLog(
            user_id=1,
            user_email='foo@bar.com',
            project_id=1,
            log_type='committed',
            ref_id='githash',
            date=now.date(),
            date_created=now
        )
        self.session.add(log)
        self.session.commit()

        # Retrieve the user's logs for today
        output = self.app.get(
            '/api/0/user/pingou/activity/%s?grouped=1' % date)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        exp = {
          "activities": [
            {
              "description_mk": "<p>pingou committed on test#githash</p>"
            }
          ],
          "date": date,
        }
        self.assertEqual(data, exp)

    @patch('pagure.lib.notify.send_email')
    def test_api_view_user_activity_timezone_negative(self, mockemail):
        """Test api_view_user_activity{_stats,_date} with the America/
        New York timezone, which is 5 hours behind UTC in winter and
        4 hours behind UTC in summer (daylight savings). The events
        will occur on 2018-02-15 in UTC, but on 2018-02-14 local.
        """
        tests.create_projects(self.session)
        repo = pagure.lib._get_project(self.session, 'test')

        dateobj = datetime.datetime(2018, 2, 15, 3, 30)
        utcdate = '2018-02-15'
        # the Unix timestamp for 2018-02-15 12:00 UTC
        utcts = '1518696000'
        localdate = '2018-02-14'
        # the Unix timestamp for 2018-02-14 12:00 America/New_York
        localts = '1518627600'
        # Create a single commit log
        log = model.PagureLog(
            user_id=1,
            user_email='foo@bar.com',
            project_id=1,
            log_type='committed',
            ref_id='githash',
            date=dateobj.date(),
            date_created=dateobj
        )
        self.session.add(log)
        self.session.commit()

        # Retrieve the user's stats with no timezone specified (==UTC)
        output = self.app.get('/api/0/user/pingou/activity/stats')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        # date in output should be UTC date
        self.assertDictEqual(data, {utcdate: 1})
        # Now in timestamp format...
        output = self.app.get('/api/0/user/pingou/activity/stats?format=timestamp')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        # timestamp in output should be UTC ts
        self.assertDictEqual(data, {utcts: 1})

        # Retrieve the user's stats with local timezone specified
        output = self.app.get('/api/0/user/pingou/activity/stats?tz=America/New_York')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        # date in output should be local date
        self.assertDictEqual(data, {localdate: 1})
        # Now in timestamp format...
        output = self.app.get('/api/0/user/pingou/activity/stats?format=timestamp&tz=America/New_York')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        # timestamp in output should be local ts
        self.assertDictEqual(data, {localts: 1})

        # Retrieve the user's logs for 2018-02-15 with no timezone
        output = self.app.get(
            '/api/0/user/pingou/activity/%s?grouped=1' % utcdate)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        exp = {
          "activities": [
            {
              "description_mk": "<p>pingou committed on test#githash</p>"
            }
          ],
          "date": utcdate,
        }
        self.assertEqual(data, exp)

        # Now retrieve the user's logs for 2018-02-14 with local time
        output = self.app.get(
            '/api/0/user/pingou/activity/%s?grouped=1&tz=America/New_York' % localdate)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        exp['date'] = localdate
        self.assertEqual(data, exp)

    @patch('pagure.lib.notify.send_email')
    def test_api_view_user_activity_timezone_positive(self, mockemail):
        """Test api_view_user_activity{_stats,_date} with the Asia/
        Dubai timezone, which is 4 hours ahead of UTC. The events will
        occur on 2018-02-15 in UTC, but on 2018-02-16 in local time.
        """
        tests.create_projects(self.session)
        repo = pagure.lib._get_project(self.session, 'test')

        dateobj = datetime.datetime(2018, 2, 15, 22, 30)
        utcdate = '2018-02-15'
        # the Unix timestamp for 2018-02-15 12:00 UTC
        utcts = '1518696000'
        localdate = '2018-02-16'
        # the Unix timestamp for 2018-02-16 12:00 Asia/Dubai
        localts = '1518768000'
        # Create a single commit log
        log = model.PagureLog(
            user_id=1,
            user_email='foo@bar.com',
            project_id=1,
            log_type='committed',
            ref_id='githash',
            date=dateobj.date(),
            date_created=dateobj
        )
        self.session.add(log)
        self.session.commit()

        # Retrieve the user's stats with no timezone specified (==UTC)
        output = self.app.get('/api/0/user/pingou/activity/stats')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        # date in output should be UTC date
        self.assertDictEqual(data, {utcdate: 1})
        # Now in timestamp format...
        output = self.app.get('/api/0/user/pingou/activity/stats?format=timestamp')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        # timestamp in output should be UTC ts
        self.assertDictEqual(data, {utcts: 1})

        # Retrieve the user's stats with local timezone specified
        output = self.app.get('/api/0/user/pingou/activity/stats?tz=Asia/Dubai')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        # date in output should be local date
        self.assertDictEqual(data, {localdate: 1})
        # Now in timestamp format...
        output = self.app.get('/api/0/user/pingou/activity/stats?format=timestamp&tz=Asia/Dubai')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        # timestamp in output should be local ts
        self.assertDictEqual(data, {localts: 1})

        # Retrieve the user's logs for 2018-02-15 with no timezone
        output = self.app.get(
            '/api/0/user/pingou/activity/%s?grouped=1' % utcdate)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        exp = {
          "activities": [
            {
              "description_mk": "<p>pingou committed on test#githash</p>"
            }
          ],
          "date": utcdate,
        }
        self.assertEqual(data, exp)

        # Now retrieve the user's logs for 2018-02-16 with local time
        output = self.app.get(
            '/api/0/user/pingou/activity/%s?grouped=1&tz=Asia/Dubai' % localdate)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        exp['date'] = localdate
        self.assertEqual(data, exp)


class PagureFlaskApiUsertestrequests(tests.Modeltests):
    """ Tests for the user requests endpoints """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiUsertestrequests, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None

        tests.create_projects(self.session)

        # Create few pull-requests
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
        pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='open pullrequest by user foo on repo test',
            user='foo',
            requestfolder=None,
        )

        repo = pagure.lib.get_authorized_project(self.session, 'test2')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test2')
        pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='open pullrequest by user foo on repo test2',
            user='foo',
            requestfolder=None,
        )
        self.session.commit()

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
        pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='closed pullrequest by user foo on repo test',
            user='foo',
            status='Closed',
            requestfolder=None,
        )

        repo = pagure.lib.get_authorized_project(self.session, 'test2')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test2')
        pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='closed pullrequest by user foo on repo test2',
            user='foo',
            status='Closed',
            requestfolder=None,
        )
        self.session.commit()

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
        pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='merged pullrequest by user foo on repo test',
            user='foo',
            status='Merged',
            requestfolder=None,
        )

        repo = pagure.lib.get_authorized_project(self.session, 'test2')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test2')
        pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='merged pullrequest by user foo on repo test2',
            user='foo',
            status='Merged',
            requestfolder=None,
        )
        self.session.commit()

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
        pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='open pullrequest by user pingou on repo test',
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()

        repo = pagure.lib.get_authorized_project(self.session, 'test2')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test2')
        pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='open pullrequest by user pingou on repo test2',
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
        pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='closed pullrequest by user pingou on repo test',
            user='pingou',
            status="Closed",
            requestfolder=None,
        )
        self.session.commit()

        repo = pagure.lib.get_authorized_project(self.session, 'test2')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test2')
        pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='closed pullrequest by user pingou on repo test2',
            user='pingou',
            status="Closed",
            requestfolder=None,
        )
        self.session.commit()

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test')
        pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='merged pullrequest by user pingou on repo test',
            user='pingou',
            status="Merged",
            requestfolder=None,
        )
        self.session.commit()

        repo = pagure.lib.get_authorized_project(self.session, 'test2')
        forked_repo = pagure.lib.get_authorized_project(self.session, 'test2')
        pagure.lib.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='merged pullrequest by user pingou on repo test2',
            user='pingou',
            status="Merged",
            requestfolder=None,
        )
        self.session.commit()

    @patch('pagure.lib.notify.send_email')
    def test_api_view_user_requests_filed(self, mockemail):
        """ Test the api_view_user_requests_filed method of the flask user
        api """

        # First we test without the status parameter. It should default to `open`
        output = self.app.get(
            '/api/0/user/pingou/requests/filed')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data['requests']), 2)
        self.assertEqual(
            sorted(data.keys()),
            [u'args', u'pagination', u'requests', u'total_requests'])
        self.assertEqual(data['requests'][0]['user']['name'], "pingou")
        self.assertEqual(data['requests'][1]['user']['name'], "pingou")
        self.assertEqual(data['requests'][0]['status'], "Open")
        self.assertEqual(data['requests'][1]['status'], "Open")
        self.assertEqual(data['requests'][0]['title'], "open pullrequest by user pingou on repo test2")
        self.assertEqual(data['requests'][1]['title'], "open pullrequest by user pingou on repo test")
        self.assertEqual(data['args']['status'], "open")
        self.assertEqual(data['args']['page'], 1)

        # Next test with the status parameter set to `open`.
        output = self.app.get(
            '/api/0/user/pingou/requests/filed?status=open')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data['requests']), 2)
        self.assertEqual(
            sorted(data.keys()),
            [u'args', u'pagination', u'requests', u'total_requests'])
        self.assertEqual(data['requests'][0]['user']['name'], "pingou")
        self.assertEqual(data['requests'][1]['user']['name'], "pingou")
        self.assertEqual(data['requests'][0]['status'], "Open")
        self.assertEqual(data['requests'][1]['status'], "Open")
        self.assertEqual(data['requests'][0]['title'], "open pullrequest by user pingou on repo test2")
        self.assertEqual(data['requests'][1]['title'], "open pullrequest by user pingou on repo test")
        self.assertEqual(data['args']['status'], "open")
        self.assertEqual(data['args']['page'], 1)

        # Next test with the status parameter set to `closed`.
        output = self.app.get(
            '/api/0/user/pingou/requests/filed?status=closed')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data['requests']), 2)
        self.assertEqual(
            sorted(data.keys()),
            [u'args', u'pagination', u'requests', u'total_requests'])
        self.assertEqual(data['requests'][0]['user']['name'], "pingou")
        self.assertEqual(data['requests'][1]['user']['name'], "pingou")
        self.assertEqual(data['requests'][0]['status'], "Closed")
        self.assertEqual(data['requests'][1]['status'], "Closed")
        self.assertEqual(data['requests'][0]['title'], "closed pullrequest by user pingou on repo test2")
        self.assertEqual(data['requests'][1]['title'], "closed pullrequest by user pingou on repo test")
        self.assertEqual(data['args']['status'], "closed")
        self.assertEqual(data['args']['page'], 1)

        # Next test with the status parameter set to `merged`.
        output = self.app.get(
            '/api/0/user/pingou/requests/filed?status=merged')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data['requests']), 2)
        self.assertEqual(
            sorted(data.keys()),
            [u'args', u'pagination', u'requests', u'total_requests'])
        self.assertEqual(data['requests'][0]['user']['name'], "pingou")
        self.assertEqual(data['requests'][1]['user']['name'], "pingou")
        self.assertEqual(data['requests'][0]['status'], "Merged")
        self.assertEqual(data['requests'][1]['status'], "Merged")
        self.assertEqual(data['requests'][0]['title'], "merged pullrequest by user pingou on repo test2")
        self.assertEqual(data['requests'][1]['title'], "merged pullrequest by user pingou on repo test")
        self.assertEqual(data['args']['status'], "merged")
        self.assertEqual(data['args']['page'], 1)

        # Finally, test with the status parameter set to `all`.
        output = self.app.get(
            '/api/0/user/pingou/requests/filed?status=all')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data['requests']), 6)
        self.assertEqual(
            sorted(data.keys()),
            [u'args', u'pagination', u'requests', u'total_requests'])
        self.assertEqual(data['requests'][0]['user']['name'], "pingou")
        self.assertEqual(data['requests'][1]['user']['name'], "pingou")
        self.assertEqual(data['requests'][2]['user']['name'], "pingou")
        self.assertEqual(data['requests'][3]['user']['name'], "pingou")
        self.assertEqual(data['requests'][4]['user']['name'], "pingou")
        self.assertEqual(data['requests'][5]['user']['name'], "pingou")
        self.assertEqual(data['requests'][0]['status'], "Merged")
        self.assertEqual(data['requests'][1]['status'], "Merged")
        self.assertEqual(data['requests'][2]['status'], "Closed")
        self.assertEqual(data['requests'][3]['status'], "Closed")
        self.assertEqual(data['requests'][4]['status'], "Open")
        self.assertEqual(data['requests'][5]['status'], "Open")
        self.assertEqual(data['requests'][0]['title'], "merged pullrequest by user pingou on repo test2")
        self.assertEqual(data['requests'][1]['title'], "merged pullrequest by user pingou on repo test")
        self.assertEqual(data['requests'][2]['title'], "closed pullrequest by user pingou on repo test2")
        self.assertEqual(data['requests'][3]['title'], "closed pullrequest by user pingou on repo test")
        self.assertEqual(data['requests'][4]['title'], "open pullrequest by user pingou on repo test2")
        self.assertEqual(data['requests'][5]['title'], "open pullrequest by user pingou on repo test")
        self.assertEqual(data['args']['status'], "all")
        self.assertEqual(data['args']['page'], 1)

        # Test page 2 with the status parameter set to `all`.
        output = self.app.get(
            '/api/0/user/pingou/requests/filed?status=all&page=2')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data['requests']), 0)
        self.assertEqual(
            sorted(data.keys()),
            [u'args', u'pagination', u'requests', u'total_requests'])
        self.assertEqual(data['args']['page'], 2)

    @patch('pagure.lib.notify.send_email')
    def test_api_view_user_requests_actionable(self, mockemail):
        """ Test the api_view_user_requests_actionable method of the flask user
        api """

        # First we test without the status parameter. It should default to `open`
        output = self.app.get(
            '/api/0/user/pingou/requests/actionable')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data['requests']), 2)
        self.assertEqual(
            sorted(data.keys()),
            [u'args', u'pagination', u'requests', u'total_requests'])
        self.assertEqual(data['requests'][0]['user']['name'], "foo")
        self.assertEqual(data['requests'][1]['user']['name'], "foo")
        self.assertEqual(data['requests'][0]['status'], "Open")
        self.assertEqual(data['requests'][1]['status'], "Open")
        self.assertEqual(data['requests'][0]['title'], "open pullrequest by user foo on repo test2")
        self.assertEqual(data['requests'][1]['title'], "open pullrequest by user foo on repo test")
        self.assertEqual(data['args']['status'], "open")
        self.assertEqual(data['args']['page'], 1)

        # Next test with the status parameter set to `open`.
        output = self.app.get(
            '/api/0/user/pingou/requests/actionable?status=open')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data['requests']), 2)
        self.assertEqual(
            sorted(data.keys()),
            [u'args', u'pagination', u'requests', u'total_requests'])
        self.assertEqual(data['requests'][0]['user']['name'], "foo")
        self.assertEqual(data['requests'][1]['user']['name'], "foo")
        self.assertEqual(data['requests'][0]['status'], "Open")
        self.assertEqual(data['requests'][1]['status'], "Open")
        self.assertEqual(data['requests'][0]['title'], "open pullrequest by user foo on repo test2")
        self.assertEqual(data['requests'][1]['title'], "open pullrequest by user foo on repo test")
        self.assertEqual(data['args']['status'], "open")
        self.assertEqual(data['args']['page'], 1)

        # Next test with the status parameter set to `closed`.
        output = self.app.get(
            '/api/0/user/pingou/requests/actionable?status=closed')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data['requests']), 2)
        self.assertEqual(
            sorted(data.keys()),
            [u'args', u'pagination', u'requests', u'total_requests'])
        self.assertEqual(data['requests'][0]['user']['name'], "foo")
        self.assertEqual(data['requests'][1]['user']['name'], "foo")
        self.assertEqual(data['requests'][0]['status'], "Closed")
        self.assertEqual(data['requests'][1]['status'], "Closed")
        self.assertEqual(data['requests'][0]['title'], "closed pullrequest by user foo on repo test2")
        self.assertEqual(data['requests'][1]['title'], "closed pullrequest by user foo on repo test")
        self.assertEqual(data['args']['status'], "closed")
        self.assertEqual(data['args']['page'], 1)

        # Next test with the status parameter set to `merged`.
        output = self.app.get(
            '/api/0/user/pingou/requests/actionable?status=merged')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data['requests']), 2)
        self.assertEqual(
            sorted(data.keys()),
            [u'args', u'pagination', u'requests', u'total_requests'])
        self.assertEqual(data['requests'][0]['user']['name'], "foo")
        self.assertEqual(data['requests'][1]['user']['name'], "foo")
        self.assertEqual(data['requests'][0]['status'], "Merged")
        self.assertEqual(data['requests'][1]['status'], "Merged")
        self.assertEqual(data['requests'][0]['title'], "merged pullrequest by user foo on repo test2")
        self.assertEqual(data['requests'][1]['title'], "merged pullrequest by user foo on repo test")
        self.assertEqual(data['args']['status'], "merged")
        self.assertEqual(data['args']['page'], 1)

        # Finally, test with the status parameter set to `all`.
        output = self.app.get(
            '/api/0/user/pingou/requests/actionable?status=all')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data['requests']), 6)
        self.assertEqual(
            sorted(data.keys()),
            [u'args', u'pagination', u'requests', u'total_requests'])
        self.assertEqual(data['requests'][0]['user']['name'], "foo")
        self.assertEqual(data['requests'][1]['user']['name'], "foo")
        self.assertEqual(data['requests'][2]['user']['name'], "foo")
        self.assertEqual(data['requests'][3]['user']['name'], "foo")
        self.assertEqual(data['requests'][4]['user']['name'], "foo")
        self.assertEqual(data['requests'][5]['user']['name'], "foo")
        self.assertEqual(data['requests'][0]['status'], "Merged")
        self.assertEqual(data['requests'][1]['status'], "Merged")
        self.assertEqual(data['requests'][2]['status'], "Closed")
        self.assertEqual(data['requests'][3]['status'], "Closed")
        self.assertEqual(data['requests'][4]['status'], "Open")
        self.assertEqual(data['requests'][5]['status'], "Open")
        self.assertEqual(data['requests'][0]['title'], "merged pullrequest by user foo on repo test2")
        self.assertEqual(data['requests'][1]['title'], "merged pullrequest by user foo on repo test")
        self.assertEqual(data['requests'][2]['title'], "closed pullrequest by user foo on repo test2")
        self.assertEqual(data['requests'][3]['title'], "closed pullrequest by user foo on repo test")
        self.assertEqual(data['requests'][4]['title'], "open pullrequest by user foo on repo test2")
        self.assertEqual(data['requests'][5]['title'], "open pullrequest by user foo on repo test")
        self.assertEqual(data['args']['status'], "all")
        self.assertEqual(data['args']['page'], 1)

        # Test page 2 with the status parameter set to `all`.
        output = self.app.get(
            '/api/0/user/pingou/requests/actionable?status=all&page=2')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.assertEqual(len(data['requests']), 0)
        self.assertEqual(
            sorted(data.keys()),
            [u'args', u'pagination', u'requests', u'total_requests'])
        self.assertEqual(data['args']['page'], 2)


class PagureFlaskApiUsertestissues(tests.Modeltests):
    """ Tests for the user issues endpoints """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiUsertestissues, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None

        tests.create_projects(self.session)

        repo = pagure.lib._get_project(self.session, 'test')

        # Create issues to play with
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

    def test_user_issues_empty(self):
        """ Return the list of issues associated with the specified user. """

        output = self.app.get('/api/0/user/foo/issues')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for k in ['pagination_issues_assigned', 'pagination_issues_created']:
            for k2 in ['first', 'last']:
                self.assertIsNotNone(data[k][k2])
                data[k][k2] = None
        self.assertEqual(
            data,
            {
              "args": {
                "assignee": True,
                "author": True,
                "milestones": [],
                "no_stones": None,
                "order": None,
                "order_key": None,
                "page": 1,
                "since": None,
                "status": None,
                "tags": []
              },
              "issues_assigned": [],
              "issues_created": [],
              'pagination_issues_assigned': {
                'first': None,
                'last': None,
                'next': None,
                'page': 1,
                'pages': 0,
                'per_page': 20,
                'prev': None},
              'pagination_issues_created': {
                'first': None,
                'last': None,
                'next': None,
                'page': 1,
                'pages': 0,
                'per_page': 20,
                'prev': None},
              "total_issues_assigned": 0,
              "total_issues_assigned_pages": 1,
              "total_issues_created": 0,
              "total_issues_created_pages": 1
            }
        )

    def test_user_issues(self):
        """ Return the list of issues associated with the specified user. """

        output = self.app.get('/api/0/user/pingou/issues')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        issues = []
        for issue in data['issues_created']:
            issue['date_created'] = '1513111778'
            issue['last_updated'] = '1513111778'
            issue['project']['date_created'] = '1513111778'
            issue['project']['date_modified'] = '1513111778'
            issues.append(issue)
        data['issues_created'] = issues
        for k in ['pagination_issues_assigned', 'pagination_issues_created']:
            for k2 in ['first', 'last']:
                self.assertIsNotNone(data[k][k2])
                data[k][k2] = None
        self.assertEqual(
            data,
            {
              "args": {
                "assignee": True,
                "author": True,
                "milestones": [],
                "no_stones": None,
                "order": None,
                "order_key": None,
                "page": 1,
                "since": None,
                "status": None,
                "tags": []
              },
              "issues_assigned": [],
              "issues_created": [
                {
                  "assignee": None,
                  "blocks": [],
                  "close_status": None,
                  "closed_at": None,
                  "comments": [],
                  "content": "We should work on this",
                  "custom_fields": [],
                  "date_created": "1513111778",
                  "depends": [],
                  "id": 1,
                  "last_updated": "1513111778",
                  "milestone": None,
                  "priority": None,
                  "private": False,
                  "project": {
                    "access_groups": {
                      "admin": [],
                      "commit": [],
                      "ticket": []
                    },
                    "access_users": {
                      "admin": [],
                      "commit": [],
                      "owner": [
                        "pingou"
                      ],
                      "ticket": []
                    },
                    "close_status": [
                      "Invalid",
                      "Insufficient data",
                      "Fixed",
                      "Duplicate"
                    ],
                    "custom_keys": [],
                    "date_created": "1513111778",
                    "date_modified": "1513111778",
                    "description": "test project #1",
                    "fullname": "test",
                    "id": 1,
                    "milestones": {},
                    "name": "test",
                    "namespace": None,
                    "parent": None,
                    "priorities": {},
                    "tags": [],
                    "url_path": "test",
                    "user": {
                      "fullname": "PY C",
                      "name": "pingou"
                    }
                  },
                  "status": "Open",
                  "tags": [],
                  "title": "Test issue",
                  "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ],
              'pagination_issues_assigned': {
                'first': None,
                'last': None,
                'next': None,
                'page': 1,
                'pages': 0,
                'per_page': 20,
                'prev': None},
              'pagination_issues_created': {
                'first': None,
                'last': None,
                'next': None,
                'page': 1,
                'pages': 1,
                'per_page': 20,
                'prev': None},
              "total_issues_assigned": 0,
              "total_issues_assigned_pages": 1,
              "total_issues_created": 1,
              "total_issues_created_pages": 1
            }
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
