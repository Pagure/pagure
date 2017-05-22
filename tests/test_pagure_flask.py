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

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.add_content_git_repo(os.path.join(self.path, 'repos', 'test2.git'))

    @mock.patch(
        'pagure.lib.repo.PagureRepo.pull',
        mock.MagicMock(side_effect=pygit2.GitError))
    def test_passing(self):
        """ Test get_remote_repo_path in pagure. """
        output = pagure.get_remote_repo_path(
            os.path.join(self.path, 'repos', 'test2.git'), 'master',
            ignore_non_exist=True)

        self.assertTrue(output.endswith('repos_test2.git_master'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
