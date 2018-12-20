# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import json
import unittest
import re
import shutil
import sys
import tempfile
import time
import os

import pygit2
from mock import ANY, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib.query
import pagure.lib.tasks
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskPrIssueLinkTest(tests.Modeltests):
    """ Tests pagure when linking PRs to tickets """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskPrIssueLinkTest, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects(
            self.session, is_fork=True, user_id=2, hook_token_suffix='bar')
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(
            self.path, 'repos', 'forks', 'foo'), bare=True)

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')

        # Create issues to play with
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='tést íssüé',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'tést íssüé')

        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='tést íssüé #2',
            content='We should still work on this',
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'tést íssüé #2')

        # Add a commit to the fork

        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        repopath = os.path.join(newpath, 'test')
        clone_repo = pygit2.clone_repository(os.path.join(
            self.path, 'repos', 'forks', 'foo', 'test.git'), repopath)

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
            'Add sources file for testing\n\n Relates to #2',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            prev_commit
        )
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create the corresponding PR

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        fork_repo = pagure.lib.query.get_authorized_project(
            self.session, 'test', user='foo')

        request = pagure.lib.query.new_pull_request(
            self.session,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test PR',
            user='foo',
            initial_comment=None,
            repo_from=fork_repo,
        )
        self.session.commit()

        pagure.lib.tasks.link_pr_to_ticket(request.uid)
        self.assertEqual(request.id, 3)

    def test_ticket_no_link(self):
        """ Test that no Related PR(s) block is showing in the issue page.
        """
        output = self.app.get('/test/issue/1')
        self.assertEqual(output.status_code, 200)
        self.assertNotIn(
            'Related Pull Requests',
            output.get_data(as_text=True))

    def test_ticket_link(self):
        """ Test that a Related PR(s) block is showing in the issue page.
        """
        output = self.app.get('/test/issue/2')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'Related Pull Requests',
            output.get_data(as_text=True))

    def test_pr_link_issue_list(self):
        """ Test that the related PR(s) shows in the page listing issues
        """
        output = self.app.get('/test/issues')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<span title="Related to PR#3" class="badge font-weight-bold '
            'text-muted font-size-09" data-toggle="tooltip">\n'
            '                            <i class="fa fa-link"></i>\n'
            '                            <a href="/test/pull-request/3" '
            'class="notblue">PR#3</a>\n                          </span>',
            output.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main(verbosity=2)
