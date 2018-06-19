# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

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


class PagureFlaskSlashInBranchtests(tests.SimplePagureTest):
    """ Tests for flask application when the branch name contains a '/'.
    """

    def set_up_git_repo(self):
        """ Set up the git repo to play with. """

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        newpath = tempfile.mkdtemp(prefix='pagure-other-test')
        repopath = os.path.join(newpath, 'test')
        clone_repo = pygit2.clone_repository(gitrepo, repopath)

        # Create a file in that git repo
        with open(os.path.join(repopath, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        clone_repo.index.add('sources')
        clone_repo.index.write()

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
            []
        )
        refname = 'refs/heads/master'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        master_branch = clone_repo.lookup_branch('master')
        first_commit = master_branch.get_object().hex

        # Second commit
        with open(os.path.join(repopath, '.gitignore'), 'w') as stream:
            stream.write('*~')
        clone_repo.index.add('.gitignore')
        clone_repo.index.write()

        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        clone_repo.create_commit(
            'refs/heads/maxamilion/feature',
            author,
            committer,
            'Add .gitignore file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit]
        )

        refname = 'refs/heads/maxamilion/feature'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_view_repo(self, send_email):
        """ Test the view_repo endpoint when the git repo has no master
        branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<input class="form-control bg-white" type="text" '
            'value="git://localhost.localdomain/test.git" readonly>',
            output_text)

    '''
    @patch('pagure.lib.notify.send_email')
    def test_view_repo_branch(self, send_email):
        """ Test the view_repo_branch endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test/branch/maxamilion/feature')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<input class="form-control bg-white" type="text" '
            'value="git://localhost.localdomain/test.git" readonly>', output_text)
    '''

    @patch('pagure.lib.notify.send_email')
    def test_view_commits(self, send_email):
        """ Test the view_commits endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.get_data(as_text=True).count('<span class="commitdate"'), 1)

        output = self.app.get('/test/commits/maxamilion/feature')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<title>Commits - test - Pagure</title>', output_text)
        self.assertIn('Add sources file for testing', output_text)
        self.assertIn('Add .gitignore file for testing', output_text)
        self.assertEqual(output_text.count('<span class="commitdate"'), 3)

    @patch('pagure.lib.notify.send_email')
    def test_view_file(self, send_email):
        """ Test the view_file endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '''<ol class="breadcrumb">
          <li class="breadcrumb-item">
            <a href="/test/tree/master">
              <span class="fa fa-random">
              </span>&nbsp; master
            </a>
          </li>
          <li class="active breadcrumb-item">
            <span class="fa fa-file" data-glyph="">
            </span>&nbsp; sources
          </li>
        </ol>''', output.get_data(as_text=True))

        output = self.app.get('/test/blob/master/f/.gitignore')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/test/blob/maxamilion/feature/f/.gitignore')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '''<ol class="breadcrumb">
          <li class="breadcrumb-item">
            <a href="/test/tree/maxamilion/feature">
              <span class="fa fa-random">
              </span>&nbsp; maxamilion/feature
            </a>
          </li>
          <li class="active breadcrumb-item">
            <span class="fa fa-file" data-glyph="">
            </span>&nbsp; .gitignore
          </li>
        </ol>''', output_text)
        self.assertTrue(
            # new version of pygments
            '<td class="cell2"><pre><span></span>*~</pre></td>' in output_text
            or
            # old version of pygments
            '<td class="cell2"><pre>*~</pre></td>' in output_text)

    @patch('pagure.lib.notify.send_email')
    def test_view_raw_file(self, send_email):
        """ Test the view_raw_file endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/raw/master')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/raw/master/f/sources')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test/raw/master')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('diff --git a/sources b/sources', output_text)
        self.assertIn('+foo\n+ bar', output_text)
        output = self.app.get('/test/raw/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.get_data(as_text=True), 'foo\n bar')

        output = self.app.get('/test/raw/maxamilion/feature')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('diff --git a/.gitignore b/.gitignore', output_text)
        self.assertIn('+*~', output_text)

        output = self.app.get('/test/raw/maxamilion/feature/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertEqual('foo\n bar', output.get_data(as_text=True))

    @patch('pagure.lib.notify.send_email')
    def test_view_tree(self, send_email):
        """ Test the view_tree endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/tree/')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/tree/master')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test/tree/master')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<a href="/test/blob/master/f/sources">', output_text)
        self.assertEqual(
            output_text.count('<span class="oi red-icon" data-glyph="file"'), 1)

        output = self.app.get('/test/tree/master/sources')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<a href="/test/blob/master/f/sources">', output_text)
        self.assertEqual(
            output_text.count('<span class="oi red-icon" data-glyph="file"'), 1)

        output = self.app.get('/test/tree/feature')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<a href="/test/blob/master/f/sources">', output_text)
        self.assertEqual(
            output_text.count('<span class="oi red-icon" data-glyph="file"'), 1)

        output = self.app.get('/test/tree/maxamilion/feature')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<a href="/test/blob/maxamilion/feature/f/sources">',
            output_text)
        self.assertEqual(
            output_text.count('<span class="oi red-icon" data-glyph="file"'), 1)

        # Wrong identifier, back onto master
        output = self.app.get('/test/tree/maxamilion/feature/f/.gitignore')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<a href="/test/blob/master/f/sources">', output_text)
        self.assertEqual(
            output_text.count('<span class="oi red-icon" data-glyph="file"'), 1)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull(self, send_email):
        """ Test the new_request_pull endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/diff/master..maxamilion/feature')
        # (used to be 302 but seeing a diff is allowed even logged out)
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/diff/master..maxamilion/feature')
            self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        output = self.app.get('/test/diff/master..maxamilion/feature')
        # (used to be 302 but seeing a diff is allowed even logged out)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertEqual(
            output_text.count('<span class="commitdate"'), 1)
        self.assertIn(
            '<span class="badge badge-success pull-xs-right text-mono">'
            '+1</span>', output_text)
        self.assertIn(
            '<div><small>file added</small></div></h5>', output_text)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/diff/master..maxamilion/feature')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(
                output_text.count('<span class="commitdate"'), 1)
            self.assertIn(
                '<span class="badge badge-success pull-xs-right text-mono">'
                '+1</span>', output_text)
            self.assertIn(
                '<div><small>file added</small></div></h5>', output_text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
