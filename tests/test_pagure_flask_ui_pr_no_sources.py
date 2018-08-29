# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

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
import time
import os

import pygit2
from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskPrNoSourcestests(tests.Modeltests):
    """ Tests PR in pagure when the source is gone """

    maxDiff = None

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    @patch('pagure.lib.notify.fedmsg_publish', MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskPrNoSourcestests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        # Create foo's fork of pingou's test project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            description='test project #1',
            hook_token='aaabbb',
            is_fork=True,
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()
        # Create the fork's git repo
        repo_path = os.path.join(self.path, 'repos', item.path)
        pygit2.init_repository(repo_path, bare=True)

        project = pagure.lib.get_authorized_project(self.session, 'test')
        fork = pagure.lib.get_authorized_project(
            self.session, 'test', user='foo')

        self.set_up_git_repo(repo=project, fork=fork)

        # Ensure things got setup straight
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertEqual(len(project.requests), 1)

        # wait for the worker to process the task
        path = os.path.join(
            self.path, 'repos', 'test.git',
            'refs', 'pull', '1', 'head')
        cnt = 0
        while not os.path.exists(path):
            time.sleep(0.1)
            cnt += 1
            if cnt == 100:
                # We're about 10 seconds in, let's bail
                raise Exception('Sorry, worker took too long')

    def set_up_git_repo(self, repo, fork, branch_from='feature'):
        """ Set up the git repo and create the corresponding PullRequest
        object.
        """

        # Clone the main repo
        gitrepo = os.path.join(self.path, 'repos', repo.path)
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
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
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        first_commit = clone_repo.revparse_single('HEAD')

        # Set the second repo
        repopath = os.path.join(self.path, 'repos', fork.path)
        new_gitrepo = os.path.join(newpath, 'fork_test')
        clone_repo = pygit2.clone_repository(repopath, new_gitrepo)

        # Add the main project as remote repo
        upstream_path = os.path.join(self.path, 'repos', repo.path)
        remote = clone_repo.create_remote('upstream', upstream_path)
        remote.fetch()

        # Edit the sources file again
        with open(os.path.join(new_gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        clone_repo.index.add('sources')
        clone_repo.index.write()

        # Commits the files added
        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        clone_repo.create_commit(
            'refs/heads/%s' % branch_from,
            author,
            committer,
            'A commit on branch %s' % branch_from,
            tree,
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/%s' % (branch_from)
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create a PR for these changes
        project = pagure.lib.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=fork,
            branch_from=branch_from,
            repo_to=project,
            branch_to='master',
            title='PR from the %s branch' % branch_from,
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the %s branch' % branch_from)

        shutil.rmtree(newpath)

    def test_request_pull_reference(self):
        """ Test if there is a reference created for a new PR. """

        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertEqual(len(project.requests), 1)

        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(
            list(repo.listall_references()),
            ['refs/heads/master', 'refs/pull/1/head']
        )

    def test_request_pull_fork_reference(self):
        """ Test if there the references created on the fork. """

        project = pagure.lib.get_authorized_project(
            self.session, 'test', user='foo')
        self.assertEqual(len(project.requests), 0)

        gitrepo = os.path.join(self.path, 'repos', project.path)
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(
            list(repo.listall_references()),
            ['refs/heads/feature']
        )

    def test_accessing_pr_fork_deleted(self):
        """ Test accessing the PR if the fork has been deleted. """

        # Delete fork on disk
        project = pagure.lib.get_authorized_project(
            self.session, 'test', user='foo')
        repo_path = os.path.join(self.path, 'repos', project.path)
        self.assertTrue(os.path.exists(repo_path))
        shutil.rmtree(repo_path)
        self.assertFalse(os.path.exists(repo_path))

        # Delete fork in the DB
        self.session.delete(project)
        self.session.commit()

        # View the pull-request
        output2 = self.app.get('/test/pull-request/1')
        self.assertEqual(output2.status_code, 200)

    def test_accessing_pr_patch_fork_deleted(self):
        """ Test accessing the PR's patch if the fork has been deleted. """

        # Delete fork on disk
        project = pagure.lib.get_authorized_project(
            self.session, 'test', user='foo')
        repo_path = os.path.join(self.path, 'repos', project.path)
        self.assertTrue(os.path.exists(repo_path))
        shutil.rmtree(repo_path)
        self.assertFalse(os.path.exists(repo_path))

        # Delete fork in the DB
        self.session.delete(project)
        self.session.commit()

        # View the pull-request
        output = self.app.get('/test/pull-request/1.patch')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '--- a/sources\n+++ b/sources\n@@ -1,2 +1,4 @@',
            output.get_data(as_text=True))

    def test_accessing_pr_branch_deleted(self):
        """ Test accessing the PR if branch it originates from has been
        deleted. """
        project = pagure.lib.get_authorized_project(
            self.session, 'test', user='foo')

        # Check the branches before
        gitrepo = os.path.join(self.path, 'repos', project.path)
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(
            list(repo.listall_references()),
            ['refs/heads/feature']
        )

        # Delete branch of the fork
        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                '/fork/foo/test/b/feature/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)

        # Check the branches after
        gitrepo = os.path.join(self.path, 'repos', project.path)
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(
            list(repo.listall_references()),
            []
        )

        # View the pull-request
        output2 = self.app.get('/test/pull-request/1')
        self.assertEqual(output2.status_code, 200)

    def test_accessing_pr_patch_branch_deleted(self):
        """ Test accessing the PR's patch if branch it originates from has
        been deleted. """
        project = pagure.lib.get_authorized_project(
            self.session, 'test', user='foo')

        # Check the branches before
        gitrepo = os.path.join(self.path, 'repos', project.path)
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(
            list(repo.listall_references()),
            ['refs/heads/feature']
        )

        # Delete branch of the fork
        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                '/fork/foo/test/b/feature/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)

        # Check the branches after
        gitrepo = os.path.join(self.path, 'repos', project.path)
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(
            list(repo.listall_references()),
            []
        )

        # View the pull-request
        output = self.app.get('/test/pull-request/1.patch')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '--- a/sources\n+++ b/sources\n@@ -1,2 +1,4 @@',
            output.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main(verbosity=2)
