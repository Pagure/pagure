# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources  # noqa

import json  # noqa
import unittest  # noqa
import shutil  # noqa
import sys  # noqa
import tempfile  # noqa
import os  # noqa

import pygit2  # noqa
from mock import patch  # noqa

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib  # noqa
import tests  # noqa
from pagure.lib.repo import PagureRepo  # noqa


class PagureFlaskForkPrtests(tests.Modeltests):
    """ Tests for flask fork controller of pagure regarding diffing PRs """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskForkPrtests, self).setUp()

        pagure.APP.config['GIT_FOLDER'] = os.path.join(self.path, 'repos')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            self.path, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            self.path, 'docs')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            self.path, 'requests')

        # Create two git repos, one has 6 commits, the other 4 of which only
        # 1 isn't present in the first repo
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        pygit2.init_repository(gitrepo, bare=True)

        gitrepo2 = os.path.join(
            self.path, 'repos', 'forks', 'pingou', 'test.git')
        pygit2.init_repository(gitrepo2, bare=True)

        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        repopath = os.path.join(newpath, 'test')
        clone_repo = pygit2.clone_repository(gitrepo, repopath)

        # Do 3 commits to the main repo
        for i in range(3):
            with open(os.path.join(repopath, 'sources'), 'w') as stream:
                stream.write('foo%s\n bar%s\n' % (i, i))
            clone_repo.index.add('sources')
            clone_repo.index.write()

            parents = []
            try:
                last_commit = clone_repo.revparse_single('HEAD')
                parents = [last_commit.oid.hex]
            except KeyError:
                pass

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
                'Editing the file sources for testing #%s' % i,
                # binary string representing the tree object ID
                tree,
                # list of binary strings representing parents of the new commit
                parents
            )

        # Push to the main repo
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Push to the fork repo
        remote = clone_repo.create_remote('pingou_fork', gitrepo2)
        PagureRepo.push(remote, refname)

        # Do another 3 commits to the main repo
        for i in range(3, 6):
            with open(os.path.join(repopath, 'sources'), 'w') as stream:
                stream.write('foo%s\n bar%s\n' % (i, i))
            clone_repo.index.add('sources')
            clone_repo.index.write()

            last_commit = clone_repo.revparse_single('HEAD')

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
                'Editing the file sources for testing #%s' % i,
                # binary string representing the tree object ID
                tree,
                # list of binary strings representing parents of the new commit
                [last_commit.oid.hex]
            )
        # Push to the main repo
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Add one commit to the fork repo
        repopath = os.path.join(newpath, 'pingou_test')
        clone_repo = pygit2.clone_repository(gitrepo2, repopath)

        with open(os.path.join(repopath, 'sources'), 'w') as stream:
                stream.write('foo\n bar\n')
        clone_repo.index.add('sources')
        clone_repo.index.write()

        last_commit = clone_repo.revparse_single('HEAD')

        # Commits the files added
        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        clone_repo.create_commit(
            'refs/heads/feature_foo',  # the name of the reference to update
            author,
            committer,
            'New edition on side branch of the file sources for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [last_commit.oid.hex]
        )

        # Push to the fork repo
        ori_remote = clone_repo.remotes[0]
        refname = 'refs/heads/feature_foo:refs/heads/feature_foo'
        PagureRepo.push(ori_remote, refname)

    def test_get_pr_info(self):
        """ Test pagure.ui.fork._get_pr_info """

        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        gitrepo2 = os.path.join(
            self.path, 'repos', 'forks', 'pingou', 'test.git')

        diff, diff_commits, orig_commit = pagure.ui.fork._get_pr_info(
            repo_obj=PagureRepo(gitrepo2),
            orig_repo=PagureRepo(gitrepo),
            branch_from='feature_foo',
            branch_to='master'
        )
        self.assertEqual(len(diff_commits), 1)
        self.assertEqual(
            diff_commits[0].message,
            'New edition on side branch of the file sources for testing'
        )
        self.assertEqual(
            orig_commit.message,
            'Editing the file sources for testing #5'
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
