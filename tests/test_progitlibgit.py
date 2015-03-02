# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib.git
import tests

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class ProgitLibGittests(tests.Modeltests):
    """ Tests for progit.lib.git """

    def test_write_gitolite_acls(self):
        """ Test the write_gitolite_acls function of progit.lib.git. """
        tests.create_projects(self.session)

        outputconf = os.path.join(HERE, 'test_gitolite.conf')

        progit.lib.git.write_gitolite_acls(self.session, outputconf)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        self.assertEqual(
            data,
            'repo test\n  R   = @all\n  RW+ = pingou\n\n'
            'repo docs/test\n  R   = @all\n  RW+ = pingou\n\n'
            'repo tickets/test\n  R   = @all\n  RW+ = pingou\n\n'
            'repo test2\n  R   = @all\n  RW+ = pingou\n\n'
            'repo docs/test2\n  R   = @all\n  RW+ = pingou\n\n'
            'repo tickets/test2\n  R   = @all\n  RW+ = pingou\n\n')

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_commit_to_patch(self):
        """ Test the commit_to_patch function of progit.lib.git. """
        # Create a git repo to play with
        self.gitrepo = os.path.join(HERE, 'test_repo.git')
        os.makedirs(self.gitrepo)
        repo = pygit2.init_repository(self.gitrepo)

        # Create a file in that git repo
        with open(os.path.join(self.gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        repo.create_commit(
            'refs/heads/master',  # the name of the reference to update
            author,
            committer,
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        first_commit = repo.revparse_single('HEAD')

        # Edit the sources file again
        with open(os.path.join(self.gitrepo, 'sources'), 'w') as stream:
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
            'refs/heads/master',  # the name of the reference to update
            author,
            committer,
            'Add baz and boose to the sources\n\n There are more objects to '
            'consider',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )

        second_commit = repo.revparse_single('HEAD')

        # Generate a patch for 2 commits
        patch = progit.lib.git.commit_to_patch(
            repo, [first_commit, second_commit])
        exp = """Mon Sep 17 00:00:00 2001
From: Alice Author <alice@authors.tld>
Subject: [PATCH 1/2] Add sources file for testing


---

diff --git a/sources b/sources
new file mode 100644
index 0000000..9f44358
--- /dev/null
+++ b/sources
@@ -0,0 +1,2 @@
+foo
+ bar
\ No newline at end of file

Mon Sep 17 00:00:00 2001
From: Alice Author <alice@authors.tld>
Subject: [PATCH 2/2] Add baz and boose to the sources


 There are more objects to consider
---

diff --git a/sources b/sources
index 9f44358..2a552bb 100644
--- a/sources
+++ b/sources
@@ -1,2 +1,4 @@
 foo
- bar
\ No newline at end of file
+ bar
+baz
+ boose
\ No newline at end of file

"""
        npatch = []
        for row in patch.split('\n'):
            if row.startswith('Date:'):
                continue
            if row.startswith('From '):
                row = row.split(' ', 2)[2]
            npatch.append(row)

        patch = '\n'.join(npatch)
        self.assertEqual(patch, exp)

        # Generate a patch for a single commit
        patch = progit.lib.git.commit_to_patch(repo, second_commit)
        exp = """Mon Sep 17 00:00:00 2001
From: Alice Author <alice@authors.tld>
Subject: Add baz and boose to the sources


 There are more objects to consider
---

diff --git a/sources b/sources
index 9f44358..2a552bb 100644
--- a/sources
+++ b/sources
@@ -1,2 +1,4 @@
 foo
- bar
\ No newline at end of file
+ bar
+baz
+ boose
\ No newline at end of file

"""
        npatch = []
        for row in patch.split('\n'):
            if row.startswith('Date:'):
                continue
            if row.startswith('From '):
                row = row.split(' ', 2)[2]
            npatch.append(row)

        patch = '\n'.join(npatch)
        self.assertEqual(patch, exp)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitLibGittests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
