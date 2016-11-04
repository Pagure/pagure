# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

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


class PagureFlaskApiUSertests(tests.Modeltests):
    """ Tests for the flask API of pagure for issue """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiUSertests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.api.SESSION = self.session
        pagure.api.fork.SESSION = self.session
        pagure.api.user.SESSION = self.session
        pagure.lib.SESSION = self.session

        pagure.APP.config['REQUESTS_FOLDER'] = None

        self.app = pagure.APP.test_client()

    def test_api_users(self):
        """ Test the api_users function.  """

        output = self.app.get('/api/0/users')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(sorted(data['users']), ['foo', 'pingou'])
        self.assertEqual(sorted(data.keys()), ['mention', 'total_users', 'users'])
        self.assertEqual(data['total_users'], 2)

        output = self.app.get('/api/0/users?pattern=p')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data['users'], ['pingou'])
        self.assertEqual(sorted(data.keys()), ['mention', 'total_users', 'users'])
        self.assertEqual(data['total_users'], 1)


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

        # Close PR
        output = self.app.post(
            '/api/0/test/pull-request/1/close', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {"message": "Pull-request closed!"}
        )

        # PR closed
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(request.status, 'Closed')

        # Finally retrieve the user's logs
        output = self.app.get('/api/0/user/pingou/activity/stats')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        date = datetime.datetime.utcnow().date().strftime('%Y-%m-%d')
        # There seems to be a difference in the JSON generated between
        # flask-0.10.1 (F23) and 0.11.1 (jenkins)
            data == {date: 4}
            or
            data == [[date, 4]]
        )

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
        self.assertEqual(json.loads(output.data), exp)

        # Date parsed, just not really as expected
        output = self.app.get('/api/0/user/pingou/activity/20161245')
        self.assertEqual(output.status_code, 200)
        exp = {
          "activities": [],
          "date": "1970-08-22"
        }
        self.assertEqual(json.loads(output.data), exp)

        date = datetime.datetime.utcnow().date().strftime('%Y-%m-%d')
        # Retrieve the user's logs for today
        output = self.app.get('/api/0/user/pingou/activity/%s' % date)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        exp = {
          "activities": [
            {
              "date": date,
              "date_created": "1477558752",
              "type": "pull-request",
              "description_mk": "<p>pingou created PR <a href=\"/test/pull-request/1\" title=\"test pull-request\">test#1</a></p>",
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
              "description_mk": "<p>pingou comment on PR <a href=\"/test/pull-request/1\" title=\"test pull-request\">test#1</a></p>",
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
              "description_mk": "<p>pingou closed PR <a href=\"/test/pull-request/1\" title=\"test pull-request\">test#1</a></p>",
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
              "description_mk": "<p>pingou comment on PR <a href=\"/test/pull-request/1\" title=\"test pull-request\">test#1</a></p>",
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


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskApiUSertests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
