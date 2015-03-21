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

        outputconf = os.path.join(tests.HERE, 'test_gitolite.conf')

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
    def test_update_git(self, email_f):
        """ Test the update_git of progit.lib.git. """
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
        self.gitrepo = os.path.join(tests.HERE, 'test_ticket_repo.git')
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
            ticketfolder=tests.HERE
        )
        self.assertEqual(msg, 'Issue created')
        issue = progit.lib.search_issues(self.session, repo, issueid=1)
        progit.lib.git.update_git(issue, repo, tests.HERE)

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
+{"status": "Open", "blocks": "", "tags": "", "title": "Test issue", "private": false, "content": "We should work on this", "depends": "", "user": {"fullname": "PY C", "name": "pingou", "emails": ["bar@pingou.com", "foo@pingou.com"]}, "date_created": null, "id": 1, "comments": []}
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
            ticketfolder=tests.HERE
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
-{"status": "Open", "blocks": "", "tags": "", "title": "Test issue", "private": false, "content": "We should work on this", "depends": "", "user": {"fullname": "PY C", "name": "pingou", "emails": ["bar@pingou.com", "foo@pingou.com"]}, "date_created": null, "id": 1, "comments": []}
\ No newline at end of file
+{"status": "Open", "blocks": "", "tags": "", "title": "Test issue", "private": false, "content": "We should work on this", "depends": "", "user": {"fullname": "PY C", "name": "pingou", "emails": ["bar@pingou.com", "foo@pingou.com"]}, "date_created": null, "id": 1, "comments": [{"comment": "Hey look a comment!", "date_created": null, "id": 1, "parent": null, "user": {"fullname": "foo bar", "name": "foo", "emails": ["foo@bar.com"]}}]}
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

    def test_update_ticket_from_git(self):
        """ Test the update_ticket_from_git method from progit.lib.git. """
        tests.create_projects(self.session)

        repo = progit.lib.get_project(self.session, 'test')

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
            progit.exceptions.ProgitException,
            progit.lib.git.update_ticket_from_git,
            self.session,
            reponame='foobar',
            username=None,
            issue_uid='foobar',
            json_data=data
        )

        progit.lib.git.update_ticket_from_git(
            self.session, reponame='test', username=None,
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
        progit.lib.git.update_ticket_from_git(
            self.session, reponame='test', username=None,
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
            "status": "Open", "title": "Rename progit", "private": False,
            "content": "This is too much of a conflict with the book",
            "user": {
                "fullname": "Pierre-YvesChibon", "name": "pingou",
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
                        "emails": ["ralph@fedoraproject.org"]
                    }
                }
            ]
        }

        progit.lib.git.update_ticket_from_git(
            self.session, reponame='test', username=None,
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
        self.assertEqual(repo.issues[1].title, 'Rename progit')
        self.assertEqual(repo.issues[1].depends_text, [])
        self.assertEqual(repo.issues[1].blocks_text, [1])

    def test_update_request_from_git(self):
        """ Test the update_request_from_git method from progit.lib.git. """
        tests.create_projects(self.session)

        repo = progit.lib.get_project(self.session, 'test')

        # Before
        self.assertEqual(len(repo.requests), 0)
        self.assertEqual(repo.requests, [])

        data = {
            "status": True,
            "uid": "d4182a2ac2d541d884742d3037c26e56",
            "repo": {
                "parent": None,
                "issue_tracker": True,
                "name": "test",
                "date_created": "1426500194",
                "user": {
                    "fullname": "fake user",
                    "name": "fake",
                    "emails": ["fake@fedoraproject.org"]
                },
                "project_docs": True,
                "id": 1,
                "description": "test project"
            },
            "commit_stop": "eface8e13bc2a08a3fb22af9a72a8c90e36b8b89",
            "user": {
                "fullname": "Pierre-YvesChibon",
                "name": "pingou",
                "emails": ["pingou@fedoraproject.org"]
            },
            "id": 7,
            "comments": [
                {
                    "comment": "really?",
                    "user": {
                        "fullname": "Pierre-YvesChibon",
                        "name": "pingou",
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
                    "issue_tracker": True,
                    "name": "test",
                    "date_created": "1426500194",
                    "user": {
                        "fullname": "fake user",
                        "name": "fake",
                        "emails": [
                            "py@pingoured.fr"
                        ]
                    },
                    "project_docs": True,
                    "id": 1,
                    "description": "test project"
                },
                "issue_tracker": True,
                "name": "test",
                "date_created": "1426843440",
                "user": {
                    "fullname": "Pierre-YvesChibon",
                    "name": "pingou",
                    "emails": [
                        "pingou@fedoraproject.org"
                    ]
                },
                "project_docs": True,
                "id": 6,
                "description": "test project"
            },
            "branch": "master",
            "date_created": "1426843732"
        }

        self.assertRaises(
            progit.exceptions.ProgitException,
            progit.lib.git.update_request_from_git,
            self.session,
            reponame='foobar',
            username=None,
            request_uid='d4182a2ac2d541d884742d3037c26e56',
            json_data=data,
            gitfolder=tests.HERE,
            docfolder=os.path.join(tests.HERE, 'docs'),
            ticketfolder=os.path.join(tests.HERE, 'tickets'),
            requestfolder=os.path.join(tests.HERE, 'requests')
        )

        progit.lib.git.update_request_from_git(
            self.session,
            reponame='test',
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
            "repo": {
                "parent": None,
                "issue_tracker": True,
                "name": "test",
                "date_created": "1426500194",
                "user": {
                    "fullname": "fake user",
                    "name": "fake",
                    "emails": ["fake@fedoraproject.org"]
                },
                "project_docs": True,
                "id": 1,
                "description": "test project"
            },
            "commit_stop": "eface8e13bc2a08a3fb22af9a72a8c90e36b8b89",
            "user": {
                "fullname": "Pierre-YvesChibon",
                "name": "pingou",
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
                    "issue_tracker": True,
                    "name": "test",
                    "date_created": "1426500194",
                    "user": {
                        "fullname": "fake user",
                        "name": "fake",
                        "emails": [
                            "py@pingoured.fr"
                        ]
                    },
                    "project_docs": True,
                    "id": 1,
                    "description": "test project"
                },
                "issue_tracker": True,
                "name": "test",
                "date_created": "1426843440",
                "user": {
                    "fullname": "Pierre-YvesChibon",
                    "name": "pingou",
                    "emails": [
                        "pingou@fedoraproject.org"
                    ]
                },
                "project_docs": True,
                "id": 6,
                "description": "test project"
            },
            "branch": "master",
            "date_created": "1426843745"
        }

        progit.lib.git.update_request_from_git(
            self.session,
            reponame='test',
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


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitLibGittests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
