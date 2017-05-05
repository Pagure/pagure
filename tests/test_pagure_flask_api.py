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

import pagure.lib
import tests


class PagureFlaskApitests(tests.Modeltests):
    """ Tests for flask API controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApitests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.api.SESSION = self.session
        self.app = pagure.APP.test_client()

    def test_api_version(self):
        """ Test the api_version function.  """

        output = self.app.get('/api/0/version')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data['version'], pagure.__api_version__)
        self.assertEqual(data.keys(), ['version'])

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
        self.assertEqual(sorted(data.keys()), ['tags', 'total_tags'])
        self.assertEqual(data['tags'], [])
        self.assertEqual(data['total_tags'], 0)

        # Add an issue and tag it so that we can list them
        item = pagure.lib.model.Issue(
            id=1,
            uid='foobar',
            project_id=1,
            title='issue',
            content='a bug report',
            user_id=1,  # pingou
        )
        self.session.add(item)
        self.session.commit()
        item = pagure.lib.model.TagColored(
            tag='tag1', tag_color='DeepBlueSky', project_id=1,
        )
        self.session.add(item)
        self.session.commit()
        item = pagure.lib.model.TagIssueColored(
            issue_uid='foobar',
            tag_id=item.id
        )
        self.session.add(item)
        self.session.commit()

        output = self.app.get('/api/0/test/tags/')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(sorted(data.keys()), ['tags', 'total_tags'])
        self.assertEqual(data['tags'], ['tag1'])
        self.assertEqual(data['total_tags'], 1)

        output = self.app.get('/api/0/test/tags/?pattern=t')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(sorted(data.keys()), ['tags', 'total_tags'])
        self.assertEqual(data['tags'], ['tag1'])
        self.assertEqual(data['total_tags'], 1)

        output = self.app.get('/api/0/test/tags/?pattern=p')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(sorted(data.keys()), ['tags', 'total_tags'])
        self.assertEqual(data['tags'], [])
        self.assertEqual(data['total_tags'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
