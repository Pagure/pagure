# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

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


class PagureFlaskApiAuthtests(tests.Modeltests):
    """ Tests for the authentication in the flask API of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiAuthtests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.api.SESSION = self.session
        pagure.api.issue.SESSION = self.session
        pagure.lib.SESSION = self.session
        self.app = pagure.APP.test_client()

    def test_auth_no_data(self):
        """ Test the authentication when there is nothing in the database.
        """

        output = self.app.post('/api/0/foo/new_issue')
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        headers = {'Authorization': 'token aabbbccc'}

        output = self.app.post('/api/0/foo/new_issue', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

    def test_auth_noacl(self):
        """ Test the authentication when the token does not have any ACL.
        """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)

        output = self.app.post('/api/0/test/new_issue')
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        headers = {'Authorization': 'token aaabbbcccddd'}

        output = self.app.post('/api/0/test/new_issue', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

    def test_auth_expired(self):
        """ Test the authentication when the token has expired.
        """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)

        output = self.app.post('/api/0/test/new_issue')
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        headers = {'Authorization': 'token expired_token'}

        output = self.app.post('/api/0/test/new_issue', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

    def test_auth(self):
        """ Test the token based authentication.
        """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        output = self.app.post('/api/0/test/new_issue')
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        headers = {'Authorization': 'token aaabbbcccddd'}

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


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskApiAuthtests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
