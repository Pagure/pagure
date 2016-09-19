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
import tempfile
import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib.git
import tests

from pagure.lib.repo import PagureRepo


class PagureLibGittests(tests.Modeltests):
    """ Tests for pagure.lib.git """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureLibGittests, self).setUp()

        pagure.lib.git.SESSION = self.session
        pagure.APP.config['GIT_FOLDER'] = os.path.join(
            tests.HERE, 'repos')
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            tests.HERE, 'requests')

    def test_write_gitolite_acls(self):
        """ Test the write_gitolite_acls function of pagure.lib.git. """
        tests.create_projects(self.session)

        repo = pagure.lib.get_project(self.session, 'test')
        # Add an user to a project
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')
        # Add a forked project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #2',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbvvv',
        )
        self.session.add(item)
        self.session.commit()

        outputconf = os.path.join(tests.HERE, 'test_gitolite.conf')

        pagure.lib.git.write_gitolite_acls(self.session, outputconf)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """
repo test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo docs/test
  R   = @all
  RW+ = pingou
  RW+ = foo

repo tickets/test
  RW+ = pingou
  RW+ = foo

repo requests/test
  RW+ = pingou
  RW+ = foo

repo test2
  R   = @all
  RW+ = pingou

repo docs/test2
  R   = @all
  RW+ = pingou

repo tickets/test2
  RW+ = pingou

repo requests/test2
  RW+ = pingou

repo forks/pingou/test3
  R   = @all
  RW+ = pingou

repo docs/forks/pingou/test3
  R   = @all
  RW+ = pingou

repo tickets/forks/pingou/test3
  RW+ = pingou

repo requests/forks/pingou/test3
  RW+ = pingou

"""
        #print data
        self.assertEqual(data, exp)

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_write_gitolite_acls_groups(self):
        """ Test the write_gitolite_acls function of pagure.lib.git with
        groups.
        """
        tests.create_projects(self.session)

        repo = pagure.lib.get_project(self.session, 'test')

        # Add a couple of groups
        msg = pagure.lib.add_group(
            self.session,
            group_name='sysadmin',
            display_name='sysadmin group',
            description=None,
            group_type='user',
            user='pingou',
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, 'User `pingou` added to the group `sysadmin`.')
        msg = pagure.lib.add_group(
            self.session,
            group_name='devs',
            display_name='devs group',
            description=None,
            group_type='user',
            user='pingou',
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()
        self.assertEqual(msg, 'User `pingou` added to the group `devs`.')

        # Associate these groups to a project
        msg = pagure.lib.add_group_to_project(
            session=self.session,
            project=repo,
            new_group='sysadmin',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')
        msg = pagure.lib.add_group_to_project(
            session=self.session,
            project=repo,
            new_group='devs',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'Group added')

        # Add an user to a project
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')
        # Add a forked project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test2',
            description='test project #2',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbvvv',
        )
        self.session.add(item)
        self.session.commit()

        outputconf = os.path.join(tests.HERE, 'test_gitolite.conf')

        pagure.lib.git.write_gitolite_acls(self.session, outputconf)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        exp = """@sysadmin   = pingou
@devs   = pingou

repo test
  R   = @all
  RW+ = @sysadmin @devs
  RW+ = pingou
  RW+ = foo

repo docs/test
  R   = @all
  RW+ = @sysadmin @devs
  RW+ = pingou
  RW+ = foo

repo tickets/test
  RW+ = @sysadmin @devs
  RW+ = pingou
  RW+ = foo

repo requests/test
  RW+ = @sysadmin @devs
  RW+ = pingou
  RW+ = foo

repo test2
  R   = @all
  RW+ = pingou

repo docs/test2
  R   = @all
  RW+ = pingou

repo tickets/test2
  RW+ = pingou

repo requests/test2
  RW+ = pingou

repo forks/pingou/test2
  R   = @all
  RW+ = pingou

repo docs/forks/pingou/test2
  R   = @all
  RW+ = pingou

repo tickets/forks/pingou/test2
  RW+ = pingou

repo requests/forks/pingou/test2
  RW+ = pingou

"""
        #print data
        self.assertEqual(data.split('\n'), exp.split('\n'))

        os.unlink(outputconf)
        self.assertFalse(os.path.exists(outputconf))

    def test_commit_to_patch(self):
        """ Test the commit_to_patch function of pagure.lib.git. """
        # Create a git repo to play with
        self.gitrepo = os.path.join(tests.HERE, 'test_repo.git')
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
        patch = pagure.lib.git.commit_to_patch(
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
        patch = pagure.lib.git.commit_to_patch(repo, second_commit)
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

    @patch('pagure.lib.notify.send_email')
    def test_update_git(self, email_f):
        """ Test the update_git of pagure.lib.git. """
        email_f.return_value = True

        # Create project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test_ticket_repo',
            description='test project for ticket',
            hook_token='aaabbbwww',
        )
        self.session.add(item)
        self.session.commit()

        # Create repo
        self.gitrepo = os.path.join(tests.HERE, 'test_ticket_repo.git')
        os.makedirs(self.gitrepo)
        repo_obj = pygit2.init_repository(self.gitrepo, bare=True)

        repo = pagure.lib.get_project(self.session, 'test_ticket_repo')
        # Create an issue to play with
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=tests.HERE
        )
        self.assertEqual(msg.title, 'Test issue')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        pagure.lib.git.update_git(issue, repo, tests.HERE)

        repo = pygit2.Repository(self.gitrepo)
        commit = repo.revparse_single('HEAD')

        # Use patch to validate the repo
        patch = pagure.lib.git.commit_to_patch(repo, commit)
        exp = """Mon Sep 17 00:00:00 2001
From: pagure <pagure>
Subject: Updated issue <hash>: Test issue


---

diff --git a/123 b/456
new file mode 100644
index 0000000..60f7480
--- /dev/null
+++ b/456
@@ -0,0 +1,25 @@
+{
+    "assignee": null,
+    "blocks": [],
+    "closed_at": null,
+    "comments": [],
+    "content": "We should work on this",
+    "date_created": null,
+    "depends": [],
+    "id": 1,
+    "milestone": null,
+    "priority": null,
+    "private": false,
+    "status": "Open",
+    "tags": [],
+    "title": "Test issue",
+    "user": {
+        "default_email": "bar@pingou.com",
+        "emails": [
+            "bar@pingou.com",
+            "foo@pingou.com"
+        ],
+        "fullname": "PY C",
+        "name": "pingou"
+    }
+}
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
            elif 'Updated issue' in row:
                row = row.split()
                row[3] = '<hash>:'
                row = ' '.join(row)
            elif 'date_created' in row:
                t = row.split(': ')[0]
                row = '%s: null,' % t
            elif 'closed_at' in row:
                t = row.split(': ')[0]
                row = '%s: null,' % t
            elif row.startswith('index 00'):
                row = 'index 0000000..60f7480'
            elif row.startswith('+++ b/'):
                row = '+++ b/456'
            npatch.append(row)
        patch = '\n'.join(npatch)
        #print patch
        self.assertEqual(patch, exp)

        # Test again after adding a comment
        msg = pagure.lib.add_issue_comment(
            session=self.session,
            issue=issue,
            comment='Hey look a comment!',
            user='foo',
            ticketfolder=tests.HERE
        )
        self.session.commit()
        self.assertEqual(msg, 'Comment added')

        # Use patch to validate the repo
        repo = pygit2.Repository(self.gitrepo)
        commit = repo.revparse_single('HEAD')
        patch = pagure.lib.git.commit_to_patch(repo, commit)
        exp = """Mon Sep 17 00:00:00 2001
From: pagure <pagure>
Subject: Updated issue <hash>: Test issue


---

diff --git a/123 b/456
index 458821a..77674a8
--- a/123
+++ b/456
@@ -2,7 +2,25 @@
     "assignee": null,
     "blocks": [],
     "closed_at": null,
-    "comments": [],
+    "comments": [
+        {
+            "comment": "Hey look a comment!",
+            "date_created": null,
+            "edited_on": null,
+            "editor": null,
+            "id": 1,
+            "notification": false,
+            "parent": null,
+            "user": {
+                "default_email": "foo@bar.com",
+                "emails": [
+                    "foo@bar.com"
+                ],
+                "fullname": "foo bar",
+                "name": "foo"
+            }
+        }
+    ],
     "content": "We should work on this",
     "date_created": null,
     "depends": [],

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
            elif 'Updated issue' in row:
                row = row.split()
                row[3] = '<hash>:'
                row = ' '.join(row)
            elif 'date_created' in row:
                t = row.split(': ')[0]
                row = '%s: null,' % t
            elif 'closed_at' in row:
                t = row.split(': ')[0]
                row = '%s: null,' % t
            elif row.startswith('index'):
                row = 'index 458821a..77674a8'
            elif row.startswith('--- a/'):
                row = '--- a/123'
            elif row.startswith('+++ b/'):
                row = '+++ b/456'
            npatch.append(row)
        patch = '\n'.join(npatch)
        #print patch
        self.assertEqual(patch, exp)

    def test_clean_git(self):
        """ Test the clean_git method of pagure.lib.git. """
        pagure.lib.git.clean_git(None, None, None)

        self.test_update_git()

        gitpath = os.path.join(tests.HERE, 'test_ticket_repo.git')
        gitrepo = pygit2.init_repository(gitpath, bare=True)

        # Get the uid of the ticket created
        commit = gitrepo.revparse_single('HEAD')
        patch = pagure.lib.git.commit_to_patch(gitrepo, commit)
        hash_file = None
        for row in patch.split('\n'):
            if row.startswith('+++ b/'):
                hash_file = row.split('+++ b/')[-1]
                break

        # The only file in git is the one of that ticket
        files = [entry.name for entry in commit.tree]
        self.assertEqual(files, [hash_file])

        repo = pagure.lib.get_project(self.session, 'test_ticket_repo')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        pagure.lib.git.clean_git(issue, repo, tests.HERE)

        # No more files in the git repo
        commit = gitrepo.revparse_single('HEAD')
        files = [entry.name for entry in commit.tree]
        self.assertEqual(files, [])

    @patch('pagure.lib.notify.send_email')
    def test_update_git_requests(self, email_f):
        """ Test the update_git of pagure.lib.git for pull-requests. """
        email_f.return_value = True

        # Create project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test_ticket_repo',
            description='test project for ticket',
            hook_token='aaabbbxxx',
        )
        self.session.add(item)
        self.session.commit()

        # Create repo
        self.gitrepo = os.path.join(tests.HERE, 'test_ticket_repo.git')
        os.makedirs(self.gitrepo)
        repo_obj = pygit2.init_repository(self.gitrepo, bare=True)

        repo = pagure.lib.get_project(self.session, 'test_ticket_repo')
        # Create an issue to play with
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='feature',
            repo_to=repo,
            branch_to='master',
            title='test PR',
            user='pingou',
            requestfolder=tests.HERE,
            requestuid='foobar',
            requestid=None,
            status='Open',
            notify=True
        )
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test PR')

        request = repo.requests[0]
        self.assertEqual(request.title, 'test PR')
        pagure.lib.git.update_git(request, request.project, tests.HERE)

        repo = pygit2.Repository(self.gitrepo)
        commit = repo.revparse_single('HEAD')

        # Use patch to validate the repo
        patch = pagure.lib.git.commit_to_patch(repo, commit)
        exp = """Mon Sep 17 00:00:00 2001
From: pagure <pagure>
Subject: Updated pull-request <hash>: test PR


---

diff --git a/123 b/456
new file mode 100644
index 0000000..60f7480
--- /dev/null
+++ b/456
@@ -0,0 +1,87 @@
+{
+    "assignee": null,
+    "branch": "master",
+    "branch_from": "feature",
+    "closed_at": null,
+    "closed_by": null,
+    "comments": [],
+    "commit_start": null,
+    "commit_stop": null,
+    "date_created": null,
+    "id": 1,
+    "initial_comment": null,
+    "project": {
+        "date_created": null,
+        "description": "test project for ticket",
+        "id": 1,
+        "name": "test_ticket_repo",
+        "namespace": null,
+        "parent": null,
+        "priorities": {},
+        "settings": {
+            "Enforce_signed-off_commits_in_pull-request": false,
+            "Minimum_score_to_merge_pull-request": -1,
+            "Only_assignee_can_merge_pull-request": false,
+            "Web-hooks": null,
+            "always_merge": false,
+            "issue_tracker": true,
+            "issues_default_to_private": false,
+            "project_documentation": false,
+            "pull_requests": true
+        },
+        "tags": [],
+        "user": {
+            "default_email": "bar@pingou.com",
+            "emails": [
+                "bar@pingou.com",
+                "foo@pingou.com"
+            ],
+            "fullname": "PY C",
+            "name": "pingou"
+        }
+    },
+    "remote_git": null,
+    "repo_from": {
+        "date_created": null,
+        "description": "test project for ticket",
+        "id": 1,
+        "name": "test_ticket_repo",
+        "namespace": null,
+        "parent": null,
+        "priorities": {},
+        "settings": {
+            "Enforce_signed-off_commits_in_pull-request": false,
+            "Minimum_score_to_merge_pull-request": -1,
+            "Only_assignee_can_merge_pull-request": false,
+            "Web-hooks": null,
+            "always_merge": false,
+            "issue_tracker": true,
+            "issues_default_to_private": false,
+            "project_documentation": false,
+            "pull_requests": true
+        },
+        "tags": [],
+        "user": {
+            "default_email": "bar@pingou.com",
+            "emails": [
+                "bar@pingou.com",
+                "foo@pingou.com"
+            ],
+            "fullname": "PY C",
+            "name": "pingou"
+        }
+    },
+    "status": "Open",
+    "title": "test PR",
+    "uid": "foobar",
+    "updated_on": null,
+    "user": {
+        "default_email": "bar@pingou.com",
+        "emails": [
+            "bar@pingou.com",
+            "foo@pingou.com"
+        ],
+        "fullname": "PY C",
+        "name": "pingou"
+    }
+}
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
            elif 'Updated pull-request' in row:
                row = row.split()
                row[3] = '<hash>:'
                row = ' '.join(row)
            elif 'date_created' in row:
                t = row.split(': ')[0]
                row = '%s: null,' % t
            elif 'updated_on' in row:
                t = row.split(': ')[0]
                row = '%s: null,' % t
            elif row.startswith('index 00'):
                row = 'index 0000000..60f7480'
            elif row.startswith('+++ b/'):
                row = '+++ b/456'
            npatch.append(row)
        patch = '\n'.join(npatch)
        #print patch
        self.assertEqual(patch, exp)

    def test_update_ticket_from_git(self):
        """ Test the update_ticket_from_git method from pagure.lib.git. """
        tests.create_projects(self.session)

        repo = pagure.lib.get_project(self.session, 'test')

        # Before
        self.assertEqual(len(repo.issues), 0)
        self.assertEqual(repo.issues, [])

        data = {
            "status": "Open", "title": "foo", "comments": [],
            "content": "bar", "date_created": "1426500263",
            "user": {
                "name": "pingou", "emails": ["pingou@fedoraproject.org"]},
        }

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.git.update_ticket_from_git,
            self.session,
            reponame='foobar',
            namespace=None,
            username=None,
            issue_uid='foobar',
            json_data=data
        )

        pagure.lib.git.update_ticket_from_git(
            self.session, reponame='test', namespace=None, username=None,
            issue_uid='foobar', json_data=data
        )
        self.session.commit()

        # After 1 insertion
        self.assertEqual(len(repo.issues), 1)
        self.assertEqual(repo.issues[0].id, 1)
        self.assertEqual(repo.issues[0].uid, 'foobar')
        self.assertEqual(repo.issues[0].title, 'foo')
        self.assertEqual(repo.issues[0].depends_text, [])
        self.assertEqual(repo.issues[0].blocks_text, [])

        data["title"] = "fake issue for tests"
        pagure.lib.git.update_ticket_from_git(
            self.session, reponame='test', namespace=None, username=None,
            issue_uid='foobar', json_data=data
        )
        self.session.commit()

        # After edit
        self.assertEqual(len(repo.issues), 1)
        self.assertEqual(repo.issues[0].id, 1)
        self.assertEqual(repo.issues[0].uid, 'foobar')
        self.assertEqual(repo.issues[0].title, 'fake issue for tests')
        self.assertEqual(repo.issues[0].depends_text, [])
        self.assertEqual(repo.issues[0].blocks_text, [])

        data = {
            "status": "Open", "title": "Rename pagure", "private": False,
            "content": "This is too much of a conflict with the book",
            "user": {
                "fullname": "Pierre-YvesChibon",
                "name": "pingou",
                "default_email": "pingou@fedoraproject.org",
                "emails": ["pingou@fedoraproject.org"]
            },
            "id": 20,
            "blocks": [1],
            "depends": [3, 4],
            "date_created": "1426595224",
            "comments": [
                {
                    "comment": "Nirik:\r\n\r\n- sourceforge++ \r\n- "
                    "gitmaker\r\n- mastergit \r\n- hostomatic\r\n- "
                    "gitcorp\r\n- git-keiretsu \r\n- gitbuffet\r\n- "
                    "cogitator\r\n- cogitate\r\n\r\nrandomuser:\r\n\r\n- "
                    "COLLABORATRON5000\r\n- git-sm\u00f6rg\u00e5sbord\r\n- "
                    "thislittlegittywenttomarket\r\n- git-o-rama\r\n- "
                    "gitsundheit",
                    "date_created": "1426595224", "id": 250, "parent": None,
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": ["pingou@fedoraproject.org"]
                    }
                },
                {
                    "comment": "Nirik:\r\n\r\n- sourceforge++ \r\n- "
                    "gitmaker\r\n- mastergit \r\n- hostomatic\r\n- "
                    "gitcorp\r\n- git-keiretsu \r\n- gitbuffet\r\n- "
                    "cogitator\r\n- cogitate\r\n\r\nrandomuser:\r\n\r\n- "
                    "COLLABORATRON5000\r\n- git-sm\u00f6rg\u00e5sbord\r\n- "
                    "thislittlegittywenttomarket\r\n- git-o-rama\r\n- "
                    "gitsundheit",
                    "date_created": "1426595340", "id": 324, "parent": None,
                    "user": {
                        "fullname": "Ralph Bean",
                        "name": "ralph",
                        "default_email": "ralph@fedoraproject.org",
                        "emails": ["ralph@fedoraproject.org"]
                    }
                }
            ]
        }

        pagure.lib.git.update_ticket_from_git(
            self.session, reponame='test', namespace=None, username=None,
            issue_uid='foobar2', json_data=data
        )

        # After second insertion
        self.assertEqual(len(repo.issues), 2)
        self.assertEqual(repo.issues[0].uid, 'foobar')
        self.assertEqual(repo.issues[0].title, 'fake issue for tests')
        self.assertEqual(repo.issues[0].depends_text, [20])
        self.assertEqual(repo.issues[0].blocks_text, [])
        # New one
        self.assertEqual(repo.issues[1].uid, 'foobar2')
        self.assertEqual(repo.issues[1].title, 'Rename pagure')
        self.assertEqual(repo.issues[1].depends_text, [])
        self.assertEqual(repo.issues[1].blocks_text, [1])

    def test_update_request_from_git(self):
        """ Test the update_request_from_git method from pagure.lib.git. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(tests.HERE, 'repos'))

        repo = pagure.lib.get_project(self.session, 'test')

        # Before
        self.assertEqual(len(repo.requests), 0)
        self.assertEqual(repo.requests, [])

        data = {
            "status": True,
            "uid": "d4182a2ac2d541d884742d3037c26e56",
            "project": {
                "parent": None,
                "settings": {
                    "issue_tracker": True,
                    "project_documentation": True,
                    "pull_requests": True,
                },
                "name": "test",
                "date_created": "1426500194",
                "tags": [],
                "user": {
                    "fullname": "Pierre-YvesChibon",
                    "name": "pingou",
                    "default_email": "pingou@fedoraproject.org",
                    "emails": [
                        "pingou@fedoraproject.org"
                    ]
                },
                "id": 1,
                "description": "test project"
            },
            "commit_stop": "eface8e13bc2a08a3fb22af9a72a8c90e36b8b89",
            "user": {
                "fullname": "Pierre-YvesChibon",
                "name": "pingou",
                "default_email": "pingou@fedoraproject.org",
                "emails": ["pingou@fedoraproject.org"]
            },
            "id": 7,
            "comments": [
                {
                    "comment": "really?",
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": ["pingou@fedoraproject.org"]
                    },
                    "parent": None,
                    "date_created": "1426843778",
                    "commit": "fa72f315373ec5f98f2b08c8ffae3645c97aaad2",
                    "line": 5,
                    "id": 1,
                    "filename": "test"
                },
                {
                    "comment": "Again ?",
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": [
                            "pingou@fedoraproject.org"
                        ]
                    },
                    "parent": None,
                    "date_created": "1426866781",
                    "commit": "94ebaf900161394059478fd88aec30e59092a1d7",
                    "line": 5,
                    "id": 2,
                    "filename": "test2"
                },
                {
                    "comment": "Should be fine in fact",
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": [
                            "pingou@fedoraproject.org"
                        ]
                    },
                    "parent": None,
                    "date_created": "1426866950",
                    "commit": "94ebaf900161394059478fd88aec30e59092a1d7",
                    "line": 5,
                    "id": 3,
                    "filename": "test2"
                }
            ],
            "branch_from": "master",
            "title": "test request",
            "commit_start": "788efeaaf86bde8618f594a8181abb402e1dd904",
            "repo_from": {
                "parent": {
                    "parent": None,
                    "name": "test",
                    "date_created": "1426500194",
                    "tags": [],
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": [
                            "pingou@fedoraproject.org"
                        ]
                    },
                    "settings": {
                        "issue_tracker": True,
                        "project_documentation": True,
                        "pull_requests": True,
                    },
                    "id": 1,
                    "description": "test project"
                },
                "settings": {
                    "issue_tracker": True,
                    "project_documentation": True,
                    "pull_requests": True,
                },
                "name": "test",
                "date_created": "1426843440",
                "tags": [],
                "user": {
                    "fullname": "fake user",
                    "name": "fake",
                    "default_email": "fake@fedoraproject.org",
                    "emails": [
                        "fake@fedoraproject.org"
                    ]
                },
                "id": 6,
                "description": "test project"
            },
            "branch": "master",
            "date_created": "1426843732"
        }

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.git.update_request_from_git,
            self.session,
            reponame='foobar',
            namespace=None,
            username=None,
            request_uid='d4182a2ac2d541d884742d3037c26e56',
            json_data=data,
            gitfolder=tests.HERE,
            docfolder=os.path.join(tests.HERE, 'docs'),
            ticketfolder=os.path.join(tests.HERE, 'tickets'),
            requestfolder=os.path.join(tests.HERE, 'requests')
        )

        pagure.lib.git.update_request_from_git(
            self.session,
            reponame='test',
            namespace=None,
            username=None,
            request_uid='d4182a2ac2d541d884742d3037c26e56',
            json_data=data,
            gitfolder=tests.HERE,
            docfolder=os.path.join(tests.HERE, 'docs'),
            ticketfolder=os.path.join(tests.HERE, 'tickets'),
            requestfolder=os.path.join(tests.HERE, 'requests')
        )
        self.session.commit()

        # After 1 st insertion
        self.assertEqual(len(repo.requests), 1)
        self.assertEqual(repo.requests[0].id, 7)
        self.assertEqual(
            repo.requests[0].uid, 'd4182a2ac2d541d884742d3037c26e56')
        self.assertEqual(repo.requests[0].title, 'test request')
        self.assertEqual(len(repo.requests[0].comments), 3)

        data = {
            "status": True,
            "uid": "d4182a2ac2d541d884742d3037c26e57",
            "project": {
                "parent": None,
                "name": "test",
                "date_created": "1426500194",
                "tags": [],
                "user": {
                    "fullname": "Pierre-YvesChibon",
                    "name": "pingou",
                    "default_email": "pingou@fedoraproject.org",
                    "emails": [
                        "pingou@fedoraproject.org"
                    ]
                },
                "settings": {
                    "issue_tracker": True,
                    "project_documentation": True,
                    "pull_requests": True,
                },
                "id": 1,
                "description": "test project"
            },
            "commit_stop": "eface8e13bc2a08a3fb22af9a72a8c90e36b8b89",
            "user": {
                "fullname": "Pierre-YvesChibon",
                "name": "pingou",
                "default_email": "pingou@fedoraproject.org",
                "emails": ["pingou@fedoraproject.org"]
            },
            "id": 4,
            "comments": [],
            "branch_from": "master",
            "title": "test request #2",
            "commit_start": "788efeaaf86bde8618f594a8181abb402e1dd904",
            "repo_from": {
                "parent": {
                    "parent": None,
                    "name": "test",
                    "date_created": "1426500194",
                    "tags": [],
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
                        "default_email": "pingou@fedoraproject.org",
                        "emails": [
                            "pingou@fedoraproject.org"
                        ]
                    },
                    "settings": {
                        "issue_tracker": True,
                        "project_documentation": True,
                        "pull_requests": True,
                    },
                    "id": 1,
                    "description": "test project"
                },
                "settings": {
                    "issue_tracker": True,
                    "project_documentation": True,
                    "pull_requests": True,
                },
                "name": "test",
                "date_created": "1426843440",
                "tags": [],
                "user": {
                    "fullname": "fake user",
                    "name": "fake",
                    "default_email": "fake@fedoraproject.org",
                    "emails": [
                        "fake@fedoraproject.org"
                    ]
                },
                "project_docs": True,
                "id": 6,
                "description": "test project"
            },
            "branch": "master",
            "date_created": "1426843745"
        }

        pagure.lib.git.update_request_from_git(
            self.session,
            reponame='test',
            namespace=None,
            username=None,
            request_uid='d4182a2ac2d541d884742d3037c26e57',
            json_data=data,
            gitfolder=tests.HERE,
            docfolder=os.path.join(tests.HERE, 'docs'),
            ticketfolder=os.path.join(tests.HERE, 'tickets'),
            requestfolder=os.path.join(tests.HERE, 'requests')
        )
        self.session.commit()

        # After 2 nd insertion
        self.assertEqual(len(repo.requests), 2)
        self.assertEqual(repo.requests[0].id, 7)
        self.assertEqual(
            repo.requests[0].uid, 'd4182a2ac2d541d884742d3037c26e56')
        self.assertEqual(repo.requests[0].title, 'test request')
        self.assertEqual(len(repo.requests[0].comments), 3)
        # 2 entry
        self.assertEqual(repo.requests[1].id, 4)
        self.assertEqual(
            repo.requests[1].uid, 'd4182a2ac2d541d884742d3037c26e57')
        self.assertEqual(repo.requests[1].title, 'test request #2')
        self.assertEqual(len(repo.requests[1].comments), 0)

    def test_read_git_lines(self):
        """ Test the read_git_lines method of pagure.lib.git. """
        self.test_update_git()

        gitrepo = os.path.join(tests.HERE, 'test_ticket_repo.git')
        output = pagure.lib.git.read_git_lines(
            ['log', '-1', "--pretty='%s'"], gitrepo)
        self.assertEqual(len(output), 1)
        self.assertTrue(
            output[0].startswith("'Updated issue ")
        )
        self.assertTrue(
            output[0].endswith(": Test issue'")
        )

        # Keeping the new line symbol
        output = pagure.lib.git.read_git_lines(
            ['log', '-1', "--pretty='%s'"], gitrepo, keepends=True)
        self.assertEqual(len(output), 1)
        self.assertTrue(
            output[0].endswith(": Test issue'\n")
        )

    def test_get_revs_between(self):
        """ Test the get_revs_between method of pagure.lib.git. """

        self.test_update_git()

        gitrepo = os.path.join(tests.HERE, 'test_ticket_repo.git')
        output = pagure.lib.git.read_git_lines(
            ['log', '-3', "--pretty='%H'"], gitrepo)
        self.assertEqual(len(output), 2)
        from_hash = output[1].replace("'", '')

        # Case 1, repo BASE is null and HEAD is equal to from_hash
        to_hash = '0'
        output1 = pagure.lib.git.get_revs_between(
            to_hash, from_hash, gitrepo, 'refs/heads/master')
        self.assertEqual(output1, [from_hash])

        # Case 2, get revs between two commits (to_hash, from_hash)
        to_hash = output[0].replace("'", '')
        output2 = pagure.lib.git.get_revs_between(
            to_hash, from_hash, gitrepo, 'refs/heads/master')
        self.assertEqual(output2, [to_hash])

        # Case 3, get revs between two commits (from_hash, to_hash)
        output3 = pagure.lib.git.get_revs_between(
            from_hash, to_hash, gitrepo, 'refs/heads/master')
        self.assertEqual(output3, [to_hash])

        # Case 4, get revs between two commits on two different branches
        newgitrepo = tempfile.mkdtemp(prefix='pagure-')
        newrepo = pygit2.clone_repository(gitrepo, newgitrepo)
        newrepo.create_branch('feature', newrepo.head.get_object())

        with open(os.path.join(newgitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        newrepo.index.add('sources')
        newrepo.index.write()

        # Commits the files added
        tree = newrepo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        newrepo.create_commit(
            'refs/heads/feature',  # the name of the reference to update
            author,
            committer,
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [to_hash]
        )
        branch_commit = newrepo.revparse_single('refs/heads/feature')

        # Push to origin
        ori_remote = newrepo.remotes[0]
        PagureRepo.push(ori_remote, 'refs/heads/feature')

        # Remove the clone
        shutil.rmtree(newgitrepo)

        output4 = pagure.lib.git.get_revs_between(
            '0', branch_commit.oid.hex, gitrepo, 'refs/heads/feature')
        self.assertEqual(output4, [branch_commit.oid.hex])

    def test_get_author(self):
        """ Test the get_author method of pagure.lib.git. """

        self.test_update_git()

        gitrepo = os.path.join(tests.HERE, 'test_ticket_repo.git')
        output = pagure.lib.git.read_git_lines(
            ['log', '-3', "--pretty='%H'"], gitrepo)
        self.assertEqual(len(output), 2)
        for githash in output:
            githash = githash.replace("'", '')
            output = pagure.lib.git.get_author(githash, gitrepo)
            self.assertEqual(output, 'pagure')

    def get_author_email(self):
        """ Test the get_author_email method of pagure.lib.git. """

        self.test_update_git()

        gitrepo = os.path.join(tests.HERE, 'test_ticket_repo.git')
        output = pagure.lib.git.read_git_lines(
            ['log', '-3', "--pretty='%H'"], gitrepo)
        self.assertEqual(len(output), 2)
        for githash in output:
            githash = githash.replace("'", '')
            output = pagure.lib.git.get_author_email(githash, gitrepo)
            self.assertEqual(output, 'pagure')

    def test_get_repo_name(self):
        """ Test the get_repo_name method of pagure.lib.git. """
        gitrepo = os.path.join(tests.HERE, 'test_ticket_repo.git')
        repo_name = pagure.lib.git.get_repo_name(gitrepo)
        self.assertEqual(repo_name, 'test_ticket_repo')

        repo_name = pagure.lib.git.get_repo_name('foo/bar/baz/test.git')
        self.assertEqual(repo_name, 'test')

        repo_name = pagure.lib.git.get_repo_name('foo.test.git')
        self.assertEqual(repo_name, 'foo.test')

    def test_get_username(self):
        """ Test the get_username method of pagure.lib.git. """
        gitrepo = os.path.join(tests.HERE, 'test_ticket_repo.git')
        repo_name = pagure.lib.git.get_username(gitrepo)
        self.assertEqual(repo_name, None)

        repo_name = pagure.lib.git.get_username('foo/bar/baz/test.git')
        self.assertEqual(repo_name, None)

        repo_name = pagure.lib.git.get_username('foo.test.git')
        self.assertEqual(repo_name, None)

        repo_name = pagure.lib.git.get_username(
            os.path.join(tests.HERE, 'forks', 'pingou', 'foo.test.git'))
        self.assertEqual(repo_name, 'pingou')

        repo_name = pagure.lib.git.get_username(
            os.path.join(tests.HERE, 'forks', 'pingou', 'bar/foo.test.git'))
        self.assertEqual(repo_name, 'pingou')

        repo_name = pagure.lib.git.get_username(os.path.join(
            tests.HERE, 'forks', 'pingou', 'fooo/bar/foo.test.git'))
        self.assertEqual(repo_name, 'pingou')

    def test_get_repo_namespace(self):
        """ Test the get_repo_namespace method of pagure.lib.git. """
        repo_name = pagure.lib.git.get_repo_namespace(
            os.path.join(tests.HERE, 'repos', 'test_ticket_repo.git'))
        self.assertEqual(repo_name, None)

        repo_name = pagure.lib.git.get_repo_namespace(
            os.path.join(tests.HERE, 'repos', 'foo/bar/baz/test.git'))
        self.assertEqual(repo_name, 'foo/bar/baz')

        repo_name = pagure.lib.git.get_repo_namespace(
            os.path.join(tests.HERE, 'repos', 'foo.test.git'))
        self.assertEqual(repo_name, None)

        repo_name = pagure.lib.git.get_repo_namespace(os.path.join(
            tests.HERE, 'repos', 'forks', 'user', 'foo.test.git'))
        self.assertEqual(repo_name, None)

        repo_name = pagure.lib.git.get_repo_namespace(os.path.join(
            tests.HERE, 'repos', 'forks', 'user', 'bar/foo.test.git'))
        self.assertEqual(repo_name, 'bar')

        repo_name = pagure.lib.git.get_repo_namespace(os.path.join(
            tests.HERE, 'repos', 'forks', 'user', 'ns/bar/foo.test.git'))
        self.assertEqual(repo_name, 'ns/bar')

        repo_name = pagure.lib.git.get_repo_namespace(os.path.join(
            tests.HERE, 'repos', 'forks', 'user', '/bar/foo.test.git'))
        self.assertEqual(repo_name, 'bar')



if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagureLibGittests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
