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


class ProgitFlaskDocstests(tests.Modeltests):
    """ Tests for flask docs of progit """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(ProgitFlaskDocstests, self).setUp()

        progit.APP.config['TESTING'] = True
        progit.SESSION = self.session
        progit.ui.SESSION = self.session
        progit.ui.app.SESSION = self.session
        progit.ui.docs.SESSION = self.session

        progit.APP.config['GIT_FOLDER'] = tests.HERE
        progit.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        progit.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        progit.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = progit.APP.test_client()

    def test_view_docs_no_project(self):
        """ Test the view_docs endpoint with no project. """

        output = self.app.get('/foo/docs')
        self.assertEqual(output.status_code, 404)

    def test_view_docs_project_no_git(self):
        """ Test the view_docs endpoint with a project that has no
        corresponding git repo.
        """
        tests.create_projects(self.session)

        output = self.app.get('/test/docs', follow_redirects=True)
        self.assertEqual(output.status_code, 404)
        self.assertTrue(
            '<li class="error">No docs repository could be found, please '
            'contact an admin</li>' in output.data)

    def test_view_docs_project_no_docs(self):
        """ Test the view_docs endpoint with a project that disabled the
        docs.
        """
        tests.create_projects(self.session)
        repo = progit.lib.get_project(self.session, 'test')
        tests.create_projects_git(os.path.join(tests.HERE, 'docs'))

        output = self.app.get('/test/docs')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<h2>Docs</h2>' in output.data)
        self.assertTrue('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue(
            'git clone git@progit.fedorahosted.org:docs/test.git'
            in output.data)

        repo.project_docs = False
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/docs', follow_redirects=True)
        self.assertEqual(output.status_code, 404)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitFlaskDocstests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
