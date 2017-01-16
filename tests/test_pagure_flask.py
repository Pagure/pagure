# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

import mock
import pygit2
import werkzeug

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import pagure.lib.model
import tests

class PagureGetRemoteRepoPath(tests.Modeltests):
    """ Tests for pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureGetRemoteRepoPath, self).setUp()

        pagure.APP.config['GIT_FOLDER'] = os.path.join(self.path, 'repos')
        pagure.APP.config['REMOTE_GIT_FOLDER'] = os.path.join(
            self.path, 'remotes')
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.add_content_git_repo(os.path.join(self.path, 'repos', 'test2.git'))

    def test_failed_clone(self):
        """ Test get_remote_repo_path in pagure. """
        with self.assertRaises(werkzeug.exceptions.InternalServerError) as cm:
            pagure.get_remote_repo_path('remote_repo', 'branch')

        self.assertEqual(
            cm.exception.get_description(),
            '<p>The following error was raised when trying to clone the '
            'remote repo: Unsupported URL protocol</p>')

    @mock.patch(
        'pagure.lib.repo.PagureRepo.pull',
        mock.MagicMock(side_effect=pygit2.GitError))
    def test_failed_pull(self):
        """ Test get_remote_repo_path in pagure. """
        pagure.get_remote_repo_path(
            os.path.join(self.path, 'repos', 'test2.git'), 'master')

        with self.assertRaises(werkzeug.exceptions.InternalServerError) as cm:
            pagure.get_remote_repo_path(
                os.path.join(self.path, 'repos', 'test2.git'), 'master')

        self.assertEqual(
            cm.exception.get_description(),
            '<p>The following error was raised when trying to pull the '
            'changes from the remote: </p>')

    @mock.patch(
        'pagure.lib.repo.PagureRepo.pull',
        mock.MagicMock(side_effect=pygit2.GitError))
    def test_passing(self):
        """ Test get_remote_repo_path in pagure. """
        output = pagure.get_remote_repo_path(
            os.path.join(self.path, 'repos', 'test2.git'), 'master')

        self.assertTrue(output.endswith('repos_test2.git_master'))


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureGetRemoteRepoPath)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
