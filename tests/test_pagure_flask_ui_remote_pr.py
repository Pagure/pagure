# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

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
import time
import os

import pygit2
from mock import patch, MagicMock
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagureRemotePRtests(tests.Modeltests):
    """ Tests for remote PRs in pagure """

    def setUp(self):
        """ Set up the environment. """
        super(PagureRemotePRtests, self).setUp()

        self.newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        self.old_value = pagure.config.config['REMOTE_GIT_FOLDER']
        pagure.config.config['REMOTE_GIT_FOLDER'] = os.path.join(
            self.path, 'remotes')

    def tearDown(self):
        """ Clear things up. """
        super(PagureRemotePRtests, self).tearDown()

        pagure.config.config['REMOTE_GIT_FOLDER'] = self.old_value
        shutil.rmtree(self.newpath)

    def set_up_git_repo(self, new_project=None, branch_from='feature'):
        """ Set up the git repo and create the corresponding PullRequest
        object.
        """

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        repopath = os.path.join(self.newpath, 'test')
        clone_repo = pygit2.clone_repository(gitrepo, repopath)

        # Create a file in that git repo
        with open(os.path.join(repopath, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        clone_repo.index.add('sources')
        clone_repo.index.write()

        try:
            com = repo.revparse_single('HEAD')
            prev_commit = [com.oid.hex]
        except:
            prev_commit = []

        # Commits the files added
        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        clone_repo.create_commit(
            'refs/heads/master',  # the name of the reference to update
            author,
            committer,
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            prev_commit
        )
        time.sleep(1)
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        first_commit = repo.revparse_single('HEAD')

        with open(os.path.join(repopath, '.gitignore'), 'w') as stream:
            stream.write('*~')
        clone_repo.index.add('.gitignore')
        clone_repo.index.write()

        # Commits the files added
        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Äuthòr', 'alice@äuthòrs.tld')
        committer = pygit2.Signature(
            'Cecil Cõmmîttër', 'cecil@cõmmîttërs.tld')
        clone_repo.create_commit(
            'refs/heads/master',
            author,
            committer,
            'Add .gitignore file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Set the second repo

        new_gitrepo = repopath
        if new_project:
            # Create a new git repo to play with
            new_gitrepo = os.path.join(self.newpath, new_project.fullname)
            if not os.path.exists(new_gitrepo):
                os.makedirs(new_gitrepo)
                new_repo = pygit2.clone_repository(gitrepo, new_gitrepo)

        repo = pygit2.Repository(new_gitrepo)

        # Edit the sources file again
        with open(os.path.join(new_gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        repo.index.add('sources')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        repo.create_commit(
            'refs/heads/%s' % branch_from,
            author,
            committer,
            'A commit on branch %s' % branch_from,
            tree,
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/%s' % (branch_from)
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

    @patch('pagure.lib.notify.send_email',  MagicMock(return_value=True))
    def test_new_remote_pr_unauth(self):
        """ Test creating a new remote PR un-authenticated. """

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo()

        # Before
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertEqual(len(project.requests), 0)

        # Try creating a remote PR
        output = self.app.get('/test/diff/remote')
        self.assertEqual(output.status_code, 302)
        self.assertIn(
            u'You should be redirected automatically to target URL: '
            u'<a href="/login/?', output.data)

    @patch('pagure.lib.notify.send_email',  MagicMock(return_value=True))
    def test_new_remote_pr_auth(self):
        """ Test creating a new remote PR un-authenticated. """

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo()

        # Before
        self.session = pagure.lib.create_session(self.dbpath)
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertEqual(len(project.requests), 0)

        # Try creating a remote PR
        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/diff/remote')
            self.assertEqual(output.status_code, 200)
            self.assertIn(u'<h2>New remote pull-request</h2>', output.data)

            csrf_token = self.get_csrf(output=output)
            data = {
                'csrf_token': csrf_token,
                'title': 'Remote PR title',
                'branch_from': 'feature',
                'branch_to': 'master',
                'git_repo': os.path.join(self.newpath, 'test'),
            }
            output = self.app.post('/test/diff/remote', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(u'<h2>Create pull request</h2>', output.data)
            self.assertIn(
                u'<div class="card clearfix" id="_1">', output.data)
            self.assertNotIn(
                u'<div class="card clearfix" id="_2">', output.data)

            # Not saved yet
            self.session = pagure.lib.create_session(self.dbpath)
            project = pagure.lib.get_authorized_project(self.session, 'test')
            self.assertEqual(len(project.requests), 0)

            data = {
                'csrf_token': csrf_token,
                'title': 'Remote PR title',
                'branch_from': 'feature',
                'branch_to': 'master',
                'git_repo': os.path.join(self.newpath, 'test'),
                'confirm': 1,
            }
            output = self.app.post(
                '/test/diff/remote', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                u'<h3><span class="label label-default">PR#1</span>',
                output.data)
            self.assertIn(
                u'<div class="card clearfix" id="_1">', output.data)
            self.assertNotIn(
                u'<div class="card clearfix" id="_2">', output.data)

            # Show the filename in the diff view
            self.assertIn(
                u'''<div class="clearfix">
                                        .gitignore
                  <div><small>
                  this is a remote pull-request, so we cannot provide you''',
                output.data)
            self.assertIn(
                u'''<div class="clearfix">
                                        sources
                  <div><small>
                  this is a remote pull-request, so we cannot provide you''',
                output.data)
            # Show the filename in the Changes summary
            self.assertIn(
                u'<a href="#_1">.gitignore</a>', output.data)
            self.assertIn(
                u'<a href="#_1">sources</a>', output.data)

        # Remote PR Created
        self.session = pagure.lib.create_session(self.dbpath)
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertEqual(len(project.requests), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
