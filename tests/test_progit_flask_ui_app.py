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


class ProgitFlaskApptests(tests.Modeltests):
    """ Tests for flask app of progit """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(ProgitFlaskApptests, self).setUp()

        progit.APP.config['TESTING'] = True
        progit.SESSION = self.session
        progit.ui.SESSION = self.session
        self.app = progit.APP.test_client()

    def test_index(self):
        """ Test the index endpoint.  """

        output = self.app.get('/')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<h2>All Projects (2)</h2>' in output.data)

        output = self.app.get('/?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<h2>All Projects (2)</h2>' in output.data)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/?repopage=abc&forkpage=def')
            self.assertTrue(
                '<section class="project_list" id="repos">' in output.data)
            self.assertTrue('<h3>My Forks (0)</h3>' in output.data)
            self.assertTrue(
                '<section class="project_list" id="myforks">' in output.data)
            self.assertTrue('<h3>My Projects (0)</h3>' in output.data)
            self.assertTrue(
                '<section class="project_list" id="myrepos">' in output.data)
            self.assertTrue('<h3>All Projects (2)</h3>' in output.data)

    def test_view_users(self):
        """ Test the view_users endpoint.  """

        output = self.app.get('/users/?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>2 users registered.</p>' in output.data)
        self.assertTrue('<a href="/user/pingou">' in output.data)
        self.assertTrue('<a href="/user/foo">' in output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitFlaskApptests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
