# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
import unittest
import shutil
import sys
import tempfile
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskSlashInNametests(tests.Modeltests):
    """ Tests for flask application when the project contains a '/'.
    """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskSlashInNametests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.lib.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.filters.SESSION = self.session
        pagure.ui.fork.SESSION = self.session
        pagure.ui.repo.SESSION = self.session
        pagure.ui.issues.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = os.path.join(tests.HERE, 'repos')
        pagure.APP.config['FORK_FOLDER'] = os.path.join(tests.HERE, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            tests.HERE, 'requests')
        self.app = pagure.APP.test_client()

    @patch('pagure.lib.notify.send_email')
    def test_view_repo(self, send_email):
        """ Test the view_repo endpoint when the project has a slash in its
        name.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test')
        self.assertEqual(output.status_code, 404)

        # Create a git repo to play with
        gitrepo = os.path.join(tests.HERE, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        # With git repo
        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<div class="card-block">\n            '
            '<h5><strong>Owners</strong></h5>', output.data)
        self.assertIn(
            '<p>The Project Creator has not pushed any code yet</p>',
            output.data)

        # Create the project `forks/test`
        message = pagure.lib.new_project(
            self.session,
            name='forks/test',
            description='test project forks/test',
            url='',
            avatar_email='',
            user='pingou',
            blacklist=pagure.APP.config['BLACKLISTED_PROJECTS'],
            gitfolder=pagure.APP.config['GIT_FOLDER'],
            docfolder=pagure.APP.config['DOCS_FOLDER'],
            ticketfolder=pagure.APP.config['TICKETS_FOLDER'],
            requestfolder=pagure.APP.config['REQUESTS_FOLDER'],
        )
        self.session.commit()
        self.assertEqual(message, 'Project "forks/test" created')

        output = self.app.get('/forks/test')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<div class="card-block">\n            '
            '<h5><strong>Owners</strong></h5>', output.data)
        self.assertIn(
            '<p>The Project Creator has not pushed any code yet</p>',
            output.data)

        output = self.app.get('/forks/test/issues')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<title>Issues - forks/test - Pagure</title>', output.data)
        self.assertIn(
            '<td colspan="5" class="noresult">No issues found</td>',
            output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskSlashInNametests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
