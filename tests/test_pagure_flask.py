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
import munch
import pygit2
import werkzeug

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import pagure.lib.model
import pagure.utils
import tests


class PagureGetRemoteRepoPath(tests.SimplePagureTest):
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
        output = pagure.utils.get_remote_repo_path(
            os.path.join(self.path, 'repos', 'test2.git'), 'master',
            ignore_non_exist=True)

        self.assertTrue(output.endswith('repos_test2.git_master'))

    def test_is_repo_committer_logged_out(self):
        """ Test is_repo_committer in pagure when there is no logged in user.
        """
        repo = pagure.lib._get_project(self.session, 'test')
        output = pagure.utils.is_repo_committer(repo)
        self.assertFalse(output)

    def test_is_repo_committer_logged_in(self):
        """ Test is_repo_committer in pagure with the appropriate user logged
        in. """
        repo = pagure.lib._get_project(self.session, 'test')

        g = munch.Munch()
        g.fas_user = tests.FakeUser(username='pingou')
        g.authenticated = True
        with mock.patch('pagure.flask_app.flask.g', g):
            output = pagure.utils.is_repo_committer(repo)
            self.assertTrue(output)

    def test_is_repo_committer_logged_in_wrong_user(self):
        """ Test is_repo_committer in pagure with the wrong user logged in.
        """
        repo = pagure.lib._get_project(self.session, 'test')

        g = munch.Munch()
        g.fas_user = tests.FakeUser()
        g.authenticated = True
        with mock.patch('pagure.flask_app.flask.g', g):
            output = pagure.utils.is_repo_committer(repo)
            self.assertFalse(output)

    # Mocked config
    config = {
        'provenpackager': {}
    }

    @mock.patch.dict('pagure.config.config', {'EXTERNAL_COMMITTER': config})
    def test_is_repo_committer_external_committer_generic_no_member(self):
        """ Test is_repo_committer in pagure with EXTERNAL_COMMITTER
        configured to give access to all the provenpackager, but the user
        is not one.
        """
        repo = pagure.lib._get_project(self.session, 'test')

        user = tests.FakeUser()
        g = munch.Munch()
        g.fas_user = user
        g.authenticated = True
        with mock.patch('pagure.flask_app.flask.g', g):
            output = pagure.utils.is_repo_committer(repo)
            self.assertFalse(output)

    @mock.patch.dict('pagure.config.config', {'EXTERNAL_COMMITTER': config})
    def test_is_repo_committer_external_committer_generic_member(self):
        """ Test is_repo_committer in pagure with EXTERNAL_COMMITTER
        configured to give access to all the provenpackager, and the user
        is one
        """
        repo = pagure.lib._get_project(self.session, 'test')

        g = munch.Munch()
        g.fas_user = tests.FakeUser()
        g.fas_user.groups.append('provenpackager')
        g.authenticated = True
        with mock.patch('pagure.flask_app.flask.g', g):
            output = pagure.utils.is_repo_committer(repo)
            self.assertTrue(output)

    config = {
        'provenpackager': {
            'exclude': ['test']
        }
    }

    @mock.patch.dict('pagure.config.config', {'EXTERNAL_COMMITTER': config})
    def test_is_repo_committer_external_committer_excluding_one(self):
        """ Test is_repo_committer in pagure with EXTERNAL_COMMITTER
        configured to give access to all the provenpackager but for this
        one repo
        """
        repo = pagure.lib._get_project(self.session, 'test')

        g = munch.Munch()
        g.fas_user = tests.FakeUser()
        g.fas_user.groups.append('provenpackager')
        g.authenticated = True
        with mock.patch('pagure.flask_app.flask.g', g):
            output = pagure.utils.is_repo_committer(repo)
            self.assertFalse(output)

    config = {
        'provenpackager': {
            'restrict': ['test']
        }
    }

    @mock.patch.dict('pagure.config.config', {'EXTERNAL_COMMITTER': config})
    def test_is_repo_committer_external_committer_restricted_not_member(self):
        """ Test is_repo_committer in pagure with EXTERNAL_COMMITTER
        configured to give access the provenpackager just for one repo
        """
        repo = pagure.lib._get_project(self.session, 'test')

        g = munch.Munch()
        g.fas_user = tests.FakeUser()
        g.authenticated = True
        with mock.patch('pagure.flask_app.flask.g', g):
            output = pagure.utils.is_repo_committer(repo)
            self.assertFalse(output)

    @mock.patch.dict('pagure.config.config', {'EXTERNAL_COMMITTER': config})
    def test_is_repo_committer_external_committer_restricting_to_one(self):
        """ Test is_repo_committer in pagure with EXTERNAL_COMMITTER
        configured to give access the provenpackager just for one repo
        """
        repo = pagure.lib._get_project(self.session, 'test')

        g = munch.Munch()
        g.fas_user = tests.FakeUser()
        g.authenticated = True
        g.fas_user.groups.append('provenpackager')
        with mock.patch('pagure.flask_app.flask.g', g):
            output = pagure.utils.is_repo_committer(repo)
            self.assertTrue(output)

    @mock.patch.dict('pagure.config.config', {'EXTERNAL_COMMITTER': config})
    def test_is_repo_committer_external_committer_restricting_another_one(self):
        """ Test is_repo_committer in pagure with EXTERNAL_COMMITTER
        configured to give access the provenpackager just for one repo not
        this one
        """
        repo = pagure.lib._get_project(self.session, 'test2')

        g = munch.Munch()
        g.fas_user = tests.FakeUser()
        g.authenticated = True
        g.fas_user.groups.append('provenpackager')
        with mock.patch('pagure.flask_app.flask.g', g):
            output = pagure.utils.is_repo_committer(repo)
            self.assertFalse(output)


if __name__ == '__main__':
    unittest.main(verbosity=2)
