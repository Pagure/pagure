# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
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

        repo = progit.lib.get_project(self.session, 'test')
        # Add an user to a project
        msg = progit.lib.add_user_to_project(
            session=self.session,
            project=repo,
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')
        # Add a forked project
        item = progit.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #2',
            parent_id=1
        )
        self.session.add(item)
        self.session.commit()

        outputconf = os.path.join(HERE, 'test_gitolite.conf')

        progit.lib.git.write_gitolite_acls(self.session, outputconf)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """repo test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo docs/test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo tickets/test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo test2
  R   = @all
  RW+ = pingou

repo docs/test2
  R   = @all
  RW+ = pingou

repo tickets/test2
  R   = @all
  RW+ = pingou

repo forks/pingou/test3
  R   = @all
  RW+ = pingou

repo docs/pingou/test3
  R   = @all
  RW+ = pingou

repo tickets/pingou/test3
  R   = @all
  RW+ = pingou

"""
        self.assertEqual(data, exp)

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

    @patch('progit.lib.notify.send_email')
    def test_update_git_ticket(self, email_f):
        """ Test the update_git_ticket of progit.lib.git. """
        email_f.return_value = True

        # Create project
        item = progit.lib.model.Project(
            user_id=1,  # pingou
            name='test_ticket_repo',
            description='test project for ticket',
        )
        self.session.add(item)
        self.session.commit()

        # Create repo
        self.gitrepo = os.path.join(HERE, 'test_ticket_repo.git')
        os.makedirs(self.gitrepo)
        repo_obj = pygit2.init_repository(self.gitrepo, bare=True)

        repo = progit.lib.get_project(self.session, 'test_ticket_repo')
        # Create an issue to play with
        msg = progit.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=HERE
        )
        self.assertEqual(msg, 'Issue created')
        issue = progit.lib.search_issues(self.session, repo, issueid=1)
        progit.lib.git.update_git_ticket(issue, repo, HERE)

        repo = pygit2.Repository(self.gitrepo)
        commit = repo.revparse_single('HEAD')

        # Use patch to validate the repo
        patch = progit.lib.git.commit_to_patch(repo, commit)
        exp = """Mon Sep 17 00:00:00 2001
From: progit <progit>
Subject: Updated ticket <hash>: Test issue


---

diff --git a/123 b/456
new file mode 100644
index 0000000..60f7480
--- /dev/null
+++ b/456
@@ -0,0 +1 @@
+{"status": "Open", "title": "Test issue", "comments": [], "content": "We should work on this", "user": {"name": "pingou", "emails": ["bar@pingou.com", "foo@pingou.com"]}, "date_created": null}
\ No newline at end of file

"""
        npatch = []
        for row in patch.split('\n'):
            if row.startswith('Date:'):
                continue
            elif row.startswith('From '):
                row = row.split(' ', 2)[2]
            elif row.startswith('diff --git '):
                row = row.split(' ')
                row[2] = 'a/123'
                row[3] = 'b/456'
                row = ' '.join(row)
            elif 'Updated ticket' in row:
                row = row.split()
                row[3] = '<hash>:'
                row = ' '.join(row)
            elif 'date_created' in row:
                data = json.loads(row[1:])
                data['date_created'] = None
                row = '+' + json.dumps(data)
            elif row.startswith('index 00'):
                row = 'index 0000000..60f7480'
            elif row.startswith('+++ b/'):
                row = '+++ b/456'
            npatch.append(row)
        patch = '\n'.join(npatch)
        self.assertEqual(patch, exp)

        # Test again after adding a comment
        msg = progit.lib.add_issue_comment(
            session=self.session,
            issue=issue,
            comment='Hey look a comment!',
            user='foo',
            ticketfolder=HERE
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        # Use patch to validate the repo
        repo = pygit2.Repository(self.gitrepo)
        commit = repo.revparse_single('HEAD')
        patch = progit.lib.git.commit_to_patch(repo, commit)
        exp = """Mon Sep 17 00:00:00 2001
From: progit <progit>
Subject: Updated ticket <hash>: Test issue


---

diff --git a/123 b/456
index 458821a..77674a8
--- a/123
+++ b/456
@@ -1 +1 @@
-{"status": "Open", "title": "Test issue", "comments": [], "content": "We should work on this", "user": {"name": "pingou", "emails": ["bar@pingou.com", "foo@pingou.com"]}, "date_created": null}
\ No newline at end of file
+{"status": "Open", "title": "Test issue", "comments": [{"comment": "Hey look a comment!", "date_created": null, "id": 1, "parent": null, "user": {"name": "foo", "emails": ["foo@bar.com"]}}], "content": "We should work on this", "user": {"name": "pingou", "emails": ["bar@pingou.com", "foo@pingou.com"]}, "date_created": null}
\ No newline at end of file

"""
        npatch = []
        for row in patch.split('\n'):
            if row.startswith('Date:'):
                continue
            elif row.startswith('From '):
                row = row.split(' ', 2)[2]
            elif row.startswith('diff --git '):
                row = row.split(' ')
                row[2] = 'a/123'
                row[3] = 'b/456'
                row = ' '.join(row)
            elif 'Updated ticket' in row:
                row = row.split()
                row[3] = '<hash>:'
                row = ' '.join(row)
            elif 'date_created' in row:
                data = json.loads(row[1:])
                data['date_created'] = None
                comments = []
                for comment in data['comments']:
                    comment['date_created'] = None
                    comments.append(comment)
                data['comments'] = comments
                row = row[0] + json.dumps(data)
            elif row.startswith('index'):
                row = 'index 458821a..77674a8'
            elif row.startswith('--- a/'):
                row = '--- a/123'
            elif row.startswith('+++ b/'):
                row = '+++ b/456'
            npatch.append(row)
        patch = '\n'.join(npatch)
        self.assertEqual(patch, exp)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitLibGittests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
