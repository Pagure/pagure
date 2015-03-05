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

import progit.lib
import tests


class ProgitFlaskApitests(tests.Modeltests):
    """ Tests for flask API controller of progit """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(ProgitFlaskApitests, self).setUp()

        progit.APP.config['TESTING'] = True
        progit.SESSION = self.session
        progit.api.SESSION = self.session
        self.app = progit.APP.test_client()

    def test_api_version(self):
        """ Test the api_version function.  """

        output = self.app.get('/api/0/version')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data['version'], progit.__api_version__)
        self.assertEqual(data.keys(), ['version'])

    def test_api_users(self):
        """ Test the api_users function.  """

        output = self.app.get('/api/0/users')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data['users'], ['pingou', 'foo'])
        self.assertEqual(data.keys(), ['users'])

        output = self.app.get('/api/0/users?pattern=p')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data['users'], ['pingou'])
        self.assertEqual(data.keys(), ['users'])

    def test_api_project_tags(self):
        """ Test the api_project_tags function.  """
        tests.create_projects(self.session)

        output = self.app.get('/api/0/foo/tags/')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertEqual(data.keys(), ['output', 'error'])
        self.assertEqual(data['output'], 'notok')
        self.assertEqual(data['error'], 'Project not found')

        output = self.app.get('/api/0/test/tags/')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data.keys(), ['tags'])
        self.assertEqual(data['tags'], [])

        # Add an issue and tag it so that we can list them
        item = progit.lib.model.Issue(
            id=1,
            uid='foobar',
            project_id=1,
            title='issue',
            content='a bug report',
            user_id=1,  # pingou
        )
        self.session.add(item)
        self.session.commit()
        item = progit.lib.model.Tag(
            tag='tag1',
        )
        self.session.add(item)
        self.session.commit()
        item = progit.lib.model.TagIssue(
            tag='tag1',
            issue_uid='foobar',
        )
        self.session.add(item)
        self.session.commit()

        output = self.app.get('/api/0/test/tags/')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data.keys(), ['tags'])
        self.assertEqual(data['tags'], ['tag1'])

        output = self.app.get('/api/0/test/tags/?pattern=t')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data.keys(), ['tags'])
        self.assertEqual(data['tags'], ['tag1'])

        output = self.app.get('/api/0/test/tags/?pattern=p')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data.keys(), ['tags'])
        self.assertEqual(data['tags'], [])


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitFlaskApitests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
