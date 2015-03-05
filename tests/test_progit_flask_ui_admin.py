# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
import unittest
import shutil
import sys
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib
import tests


class ProgitFlaskAdmintests(tests.Modeltests):
    """ Tests for flask admin controller of progit """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(ProgitFlaskAdmintests, self).setUp()

        progit.APP.config['TESTING'] = True
        progit.SESSION = self.session
        progit.ui.SESSION = self.session
        progit.ui.app.SESSION = self.session
        progit.ui.admin.SESSION = self.session

        progit.APP.config['GIT_FOLDER'] = tests.HERE
        progit.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        progit.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        progit.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = progit.APP.test_client()

    def test_admin_index(self):
        """ Test the admin_index endpoint. """

        output = self.app.get('/admin')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/admin', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="error">Access restricted</li>' in output.data)

        user.username = 'pingou'
        user.groups.append(progit.APP.config['ADMIN_GROUP'])
        with tests.user_set(progit.APP, user):
            output = self.app.get('/admin', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Admin section</h2>' in output.data)
            self.assertTrue('Re-generate gitolite ACLs file' in output.data)
            self.assertTrue(
                'Re-generate ssh authorized_key file' in output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitFlaskAdmintests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
