# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import datetime
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

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(HERE, 'test_config')

os.environ['PAGURE_CONFIG'] = CONFIG

import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskRepoOldUrltests(tests.Modeltests):
    """ Tests for flask app controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskRepoOldUrltests, self).setUp()

        # We need to reload pagure as otherwise the configuration file will
        # not be taken into account
        pagure.APP.view_functions = {}
        os.environ['PAGURE_CONFIG'] = CONFIG

        reload(pagure)
        reload(pagure.lib)
        reload(pagure.lib.model)
        reload(pagure.ui.admin)
        reload(pagure.ui.app)
        reload(pagure.ui.groups)
        reload(pagure.ui.repo)
        reload(pagure.ui.filters)
        reload(pagure.ui.issues)
        reload(pagure.ui.fork)

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.filters.SESSION = self.session
        pagure.ui.repo.SESSION = self.session

        pagure.APP.config['OLD_VIEW_COMMIT_ENABLED'] = True
        pagure.APP.config['EMAIL_SEND'] = False
        pagure.APP.config['GIT_FOLDER'] = tests.HERE
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            tests.HERE, 'requests')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        pagure.APP.config['UPLOAD_FOLDER_PATH'] = os.path.join(
            tests.HERE, 'releases')
        self.app = pagure.APP.test_client()

    def tearDown(self):
        """ Tear down the environnment, after every tests. """
        super(PagureFlaskRepoOldUrltests, self).tearDown()
        if 'PAGURE_CONFIG' in os.environ:
            del os.environ['PAGURE_CONFIG']

        # We need to reload pagure as otherwise the configuration file will
        # remain set for the other tests
        pagure.APP.view_functions = {}

        reload(pagure)
        reload(pagure.lib)
        reload(pagure.lib.model)
        reload(pagure.hooks)
        reload(pagure.hooks.mail)
        reload(pagure.hooks.irc)
        reload(pagure.hooks.fedmsg)
        reload(pagure.hooks.pagure_force_commit)
        reload(pagure.hooks.pagure_hook)
        reload(pagure.hooks.pagure_request_hook)
        reload(pagure.hooks.pagure_ticket_hook)
        reload(pagure.hooks.rtd)
        reload(pagure.ui.admin)
        reload(pagure.ui.app)
        reload(pagure.ui.groups)
        reload(pagure.ui.repo)
        reload(pagure.ui.filters)
        reload(pagure.ui.plugins)
        reload(pagure.ui.issues)
        reload(pagure.ui.fork)

        pagure.APP.config['EMAIL_SEND'] = False
        pagure.LOG.handlers = []


    def test_view_commit_old(self):
        """ Test the view_commit_old endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(tests.HERE, bare=True)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))
        repo = pygit2.Repository(os.path.join(tests.HERE, 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View first commit
        output = self.app.get('/test/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 302)

        output = self.app.get(
            '/test/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.data)
        self.assertTrue('</a> Authored by Alice Author' in output.data)
        self.assertTrue('Committed by Cecil Committer' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ Pagure</span>' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ ======</span>' in output.data)

        self.app = pagure.APP.test_client()
        # View first commit - with the old URL scheme
        output = self.app.get(
            '/test/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.data)
        self.assertTrue('</a> Authored by Alice Author' in output.data)
        self.assertTrue('Committed by Cecil Committer' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ Pagure</span>' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ ======</span>' in output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))

        repo = pygit2.Repository(os.path.join(tests.HERE, 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View another commit
        output = self.app.get(
            '/test/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.data)
        self.assertTrue('</a> Authored by Alice Author' in output.data)
        self.assertTrue('Committed by Cecil Committer' in output.data)
        self.assertTrue(
            # new version of pygments
            '<div class="highlight" style="background: #f8f8f8">'
            '<pre style="line-height: 125%">'
            '<span></span>'
            '<span style="color: #800080; font-weight: bold">'
            '@@ -0,0 +1,3 @@</span>' in output.data
            or
            # old version of pygments
            '<div class="highlight" style="background: #f8f8f8">'
            '<pre style="line-height: 125%">'
            '<span style="color: #800080; font-weight: bold">'
            '@@ -0,0 +1,3 @@</span>' in output.data)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
            hook_token='aaabbbkkk',
        )
        self.session.add(item)
        self.session.commit()
        forkedgit = os.path.join(
            tests.HERE, 'forks', 'pingou', 'test3.git')

        tests.add_content_git_repo(forkedgit)
        tests.add_readme_git_repo(forkedgit)

        repo = pygit2.Repository(forkedgit)
        commit = repo.revparse_single('HEAD')

        # Commit does not exist in anothe repo :)
        output = self.app.get(
            '/test/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 404)

        # View commit of fork
        output = self.app.get(
            '/fork/pingou/test3/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.data)
        self.assertTrue('</a> Authored by Alice Author' in output.data)
        self.assertTrue('Committed by Cecil Committer' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ Pagure</span>' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ ======</span>' in output.data)

        # View commit of fork - With the old URL scheme
        output = self.app.get(
            '/fork/pingou/test3/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.data)
        self.assertTrue('</a> Authored by Alice Author' in output.data)
        self.assertTrue('Committed by Cecil Committer' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ Pagure</span>' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ ======</span>' in output.data)

        # Try the old URL scheme with a short hash
        output = self.app.get(
            '/fork/pingou/test3/%s' % commit.oid.hex[:10],
            follow_redirects=True)
        self.assertEqual(output.status_code, 404)
        self.assertIn('<p>Project not found</p>', output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagureFlaskRepoOldUrltests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
