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
import tempfile
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskForktests(tests.Modeltests):
    """ Tests for flask fork controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskForktests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.lib.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.filters.SESSION = self.session
        pagure.ui.fork.SESSION = self.session
        pagure.ui.repo.SESSION = self.session
        pagure.ui.issues.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = os.path.join(tests.HERE, 'repos')
        pagure.APP.config['FORK_FOLDER'] = os.path.join(tests.HERE, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            tests.HERE, 'requests')
        self.app = pagure.APP.test_client()

    def set_up_git_repo(
            self, new_project=None, branch_from='feature', mtype='FF'):
        """ Set up the git repo and create the corresponding PullRequest
        object.
        """

        # Create a git repo to play with
        gitrepo = os.path.join(tests.HERE, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

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

        first_commit = repo.revparse_single('HEAD')

        if mtype == 'merge':
            with open(os.path.join(repopath, '.gitignore'), 'w') as stream:
                stream.write('*~')
            clone_repo.index.add('.gitignore')
            clone_repo.index.write()

            # Commits the files added
            tree = clone_repo.index.write_tree()
            author = pygit2.Signature(
                'Alice Author', 'alice@authors.tld')
            committer = pygit2.Signature(
                'Cecil Committer', 'cecil@committers.tld')
            clone_repo.create_commit(
                'refs/heads/master',
                author,
                committer,
                'Add .gitignore file for testing',
                # binary string representing the tree object ID
                tree,
                # list of binary strings representing parents of the new commit
                [first_commit.oid.hex]
            )
            refname = 'refs/heads/master:refs/heads/master'
            ori_remote = clone_repo.remotes[0]
            PagureRepo.push(ori_remote, refname)

        if mtype == 'conflicts':
            with open(os.path.join(repopath, 'sources'), 'w') as stream:
                stream.write('foo\n bar\nbaz')
            clone_repo.index.add('sources')
            clone_repo.index.write()

            # Commits the files added
            tree = clone_repo.index.write_tree()
            author = pygit2.Signature(
                'Alice Author', 'alice@authors.tld')
            committer = pygit2.Signature(
                'Cecil Committer', 'cecil@committers.tld')
            clone_repo.create_commit(
                'refs/heads/master',
                author,
                committer,
                'Add sources conflicting',
                # binary string representing the tree object ID
                tree,
                # list of binary strings representing parents of the new commit
                [first_commit.oid.hex]
            )
            refname = 'refs/heads/master:refs/heads/master'
            ori_remote = clone_repo.remotes[0]
            PagureRepo.push(ori_remote, refname)

        # Set the second repo

        new_gitrepo = repopath
        if new_project:
            # Create a new git repo to play with
            new_gitrepo = os.path.join(newpath, new_project.fullname)
            if not os.path.exists(new_gitrepo):
                os.makedirs(new_gitrepo)
                new_repo = pygit2.clone_repository(gitrepo, new_gitrepo)

        repo = pygit2.Repository(new_gitrepo)

        if mtype != 'nochanges':
            # Edit the sources file again
            with open(os.path.join(new_gitrepo, 'sources'), 'w') as stream:
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
                'refs/heads/%s' % branch_from,
                author,
                committer,
                'A commit on branch %s' % branch_from,
                tree,
                [first_commit.oid.hex]
            )
            refname = 'refs/heads/%s' % (branch_from)
            ori_remote = repo.remotes[0]
            PagureRepo.push(ori_remote, refname)

        # Create a PR for these changes
        project = pagure.lib.get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from=branch_from,
            repo_to=project,
            branch_to='master',
            title='PR from the %s branch' % branch_from,
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the %s branch' % branch_from)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull(self, send_email):
        """ Test the request_pull endpoint. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)

        # Non-existant project
        output = self.app.get('/foobar/pull-request/1')
        self.assertEqual(output.status_code, 404)

        # Project has no PR
        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo(new_project=None, branch_from='feature')

        project = pagure.lib.get_project(self.session, 'test')
        self.assertEqual(len(project.requests), 1)

        # View the pull-request
        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
        self.assertIn(
            'title="View file as of 2a552b">View</a>', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_merge_request_pull_FF(self, send_email):
        """ Test the merge_request_pull endpoint with a FF PR. """
        send_email.return_value = True

        self.test_request_pull()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # No CSRF
            output = self.app.post(
                '/test/pull-request/1/merge', data={}, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                'title="View file as of 2a552b">View</a>', output.data)

            # Wrong project
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/foobar/pull-request/100/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Wrong project
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            # Wrong request id
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/pull-request/100/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Project w/o pull-request
            repo = pagure.lib.get_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            # Pull-request disabled
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Project w pull-request but only assignee can merge
            settings['pull_requests'] = True
            settings['Only_assignee_can_merge_pull-request'] = True
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<li class="error">This request must be assigned to be merged</li>',
                output.data)

            # PR assigned but not to this user
            repo = pagure.lib.get_project(self.session, 'test')
            req = repo.requests[0]
            req.assignee_id = 2
            self.session.add(req)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<li class="error">Only the assignee can merge this review</li>',
                output.data)

            # Project w/ minimal PR score
            settings['Only_assignee_can_merge_pull-request'] = False
            settings['Minimum_score_to_merge_pull-request'] = 2
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<li class="error">This request does not have the minimum '
                'review score necessary to be merged</li>', output.data)

            # Merge
            settings['Minimum_score_to_merge_pull-request'] = -1
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output.data)
            self.assertIn(
                '<li class="message">Changes merged!</li>', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_merge_request_pull_merge(self, send_email):
        """ Test the merge_request_pull endpoint with a merge PR. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)
        self.set_up_git_repo(
            new_project=None, branch_from='feature', mtype='merge')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token': csrf_token,
            }

            # Merge
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output.data)
            self.assertIn(
                '<li class="message">Changes merged!</li>', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_merge_request_pull_conflicts(self, send_email):
        """ Test the merge_request_pull endpoint with a conflicting PR. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)
        self.set_up_git_repo(
            new_project=None, branch_from='feature', mtype='conflicts')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token': csrf_token,
            }

            # Merge conflicts
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<li class="error">Merge conflicts!</li>', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_merge_request_pull_nochange(self, send_email):
        """ Test the merge_request_pull endpoint. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)
        self.set_up_git_repo(
            new_project=None, branch_from='master', mtype='nochanges')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token': csrf_token,
            }

            # Nothing to merge
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the master branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<li class="error">Nothing to do, changes were already '
                'merged</li>', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_close(self, send_email):
        """ Test the request_pull endpoint with a closed PR. """
        send_email.return_value = True

        self.test_merge_request_pull_FF()

        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
        self.assertIn(
            '<span>Merged by', output.data)
        self.assertIn(
            'title="View file as of 2a552b">View</a>', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_disabled(self, send_email):
        """ Test the request_pull endpoint with PR disabled. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)
        self.set_up_git_repo(new_project=None, branch_from='feature')

        # Project w/o pull-request
        repo = pagure.lib.get_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_empty_repo(self, send_email):
        """ Test the request_pull endpoint against an empty repo. """
        send_email.return_value = True

        tests.create_projects(self.session)
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            description='test project #1',
            hook_token='aaabbb',
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'forks', 'foo'), bare=True)

        # Create a git repo to play with
        gitrepo = os.path.join(tests.HERE, 'repos', 'test.git')
        self.assertFalse(os.path.exists(gitrepo))
        os.makedirs(gitrepo)
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(tests.HERE, 'forks', 'foo', 'test.git')
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        # Edit the sources file again
        with open(os.path.join(newpath, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        new_repo.index.add('sources')
        new_repo.index.write()

        # Commits the files added
        tree = new_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        new_repo.create_commit(
            'refs/heads/feature',
            author,
            committer,
            'A commit on branch feature',
            tree,
            []
        )
        refname = 'refs/heads/feature:refs/heads/feature'
        ori_remote = new_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create a PR for these changes
        project = pagure.lib.get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=item,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
            requestfolder=None,

        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
        self.assertTrue(output.data.count('<td class="commitid">'), 1)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_empty_fork(self, send_email):
        """ Test the request_pull endpoint from an empty fork. """
        send_email.return_value = True

        tests.create_projects(self.session)
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            description='test project #1',
            hook_token='aaabbb',
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'forks', 'foo'), bare=True)

        # Create a git repo to play with
        gitrepo = os.path.join(tests.HERE, 'repos', 'test.git')
        self.assertFalse(os.path.exists(gitrepo))
        os.makedirs(gitrepo)
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(tests.HERE, 'forks', 'foo', 'test.git')
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        # Create a PR for these "changes" (there are none, both repos are
        # empty)
        project = pagure.lib.get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=item,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
            requestfolder=None,

        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        output = self.app.get('/test/pull-request/1', follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<title>Overview - test - Pagure</title>', output.data)
        self.assertIn(
            '<li class="error">Fork is empty, there are no commits to '
            'request pulling</li>', output.data)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_request_pulls(self, send_email):
        """ Test the request_pulls endpoint. """
        send_email.return_value = True

        # No such project
        output = self.app.get('/test/pull-requests')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/pull-requests')
        self.assertEqual(output.status_code, 200)
        self.assertIn('Pull-requests (0)', output.data)
        self.assertIn('(0 Closed)</a>', output.data)

        self.set_up_git_repo(new_project=None, branch_from='feature')

        output = self.app.get('/test/pull-requests')
        self.assertEqual(output.status_code, 200)
        self.assertIn('Pull-requests (1)', output.data)
        self.assertIn('(0 Closed)</a>', output.data)

        output = self.app.get('/test/pull-requests?status=Closed')
        self.assertEqual(output.status_code, 200)
        self.assertIn('Closed Pull-requests (0)', output.data)
        self.assertIn('(1 Open)</a>', output.data)

        output = self.app.get('/test/pull-requests?status=0')
        self.assertEqual(output.status_code, 200)
        self.assertIn('Closed/Merged Pull-requests (0)', output.data)
        self.assertIn('(1 Open)</a>', output.data)

        # Project w/o pull-request
        repo = pagure.lib.get_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/pull-requests')
        self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_patch(self, send_email):
        """ Test the request_pull_patch endpoint. """
        send_email.return_value = True

        output = self.app.get('/test/pull-request/1.patch')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)
        self.set_up_git_repo(
            new_project=None, branch_from='feature', mtype='merge')

        output = self.app.get('/test/pull-request/100.patch')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/test/pull-request/1.patch')
        self.assertEqual(output.status_code, 200)

        npatch = []
        for row in output.data.split('\n'):
            if row.startswith('Date:'):
                continue
            if row.startswith('From '):
                row = row.split(' ', 2)[2]
            npatch.append(row)

        exp = """Mon Sep 17 00:00:00 2001
From: Alice Author <alice@authors.tld>
Subject: A commit on branch feature


---

diff --git a/.gitignore b/.gitignore
new file mode 100644
index 0000000..e4e5f6c
--- /dev/null
+++ b/.gitignore
@@ -0,0 +1 @@
+*~
\ No newline at end of file
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

        patch = '\n'.join(npatch)
        #print patch
        self.assertEqual(patch, exp)

        # Project w/o pull-request
        repo = pagure.lib.get_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/pull-request/1.patch')
        self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_patch_close(self, send_email):
        """ Test the request_pull_patch endpoint with a closed PR. """
        send_email.return_value = True

        self.test_merge_request_pull_FF()

        output = self.app.get('/test/pull-request/1.patch')
        self.assertEqual(output.status_code, 200)

        npatch = []
        for row in output.data.split('\n'):
            if row.startswith('Date:'):
                continue
            if row.startswith('From '):
                row = row.split(' ', 2)[2]
            npatch.append(row)

        exp = """Mon Sep 17 00:00:00 2001
From: Alice Author <alice@authors.tld>
Subject: A commit on branch feature


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

        patch = '\n'.join(npatch)
        #print patch
        self.assertEqual(patch, exp)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_patch_empty_repo(self, send_email):
        """ Test the request_pull_patch endpoint against an empty repo. """
        send_email.return_value = True

        tests.create_projects(self.session)
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            description='test project #1',
            hook_token='aaabbb',
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'forks', 'foo'), bare=True)

        # Create a git repo to play with
        gitrepo = os.path.join(tests.HERE, 'repos', 'test.git')
        self.assertFalse(os.path.exists(gitrepo))
        os.makedirs(gitrepo)
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(tests.HERE, 'forks', 'foo', 'test.git')
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        # Edit the sources file again
        with open(os.path.join(newpath, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        new_repo.index.add('sources')
        new_repo.index.write()

        # Commits the files added
        tree = new_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        new_repo.create_commit(
            'refs/heads/feature',
            author,
            committer,
            'A commit on branch feature',
            tree,
            []
        )
        refname = 'refs/heads/feature:refs/heads/feature'
        ori_remote = new_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create a PR for these "changes" (there are none, both repos are
        # empty)
        project = pagure.lib.get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=item,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
            requestfolder=None,

        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        output = self.app.get('/test/pull-request/1.patch', follow_redirects=True)
        self.assertEqual(output.status_code, 200)

        npatch = []
        for row in output.data.split('\n'):
            if row.startswith('Date:'):
                continue
            if row.startswith('From '):
                row = row.split(' ', 2)[2]
            npatch.append(row)

        exp = """Mon Sep 17 00:00:00 2001
From: Alice Author <alice@authors.tld>
Subject: A commit on branch feature


---

diff --git a/sources b/sources
new file mode 100644
index 0000000..2a552bb
--- /dev/null
+++ b/sources
@@ -0,0 +1,4 @@
+foo
+ bar
+baz
+ boose
\ No newline at end of file

"""

        patch = '\n'.join(npatch)
        #print patch
        self.assertEqual(patch, exp)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_patch_empty_fork(self, send_email):
        """ Test the request_pull_patch endpoint from an empty fork. """
        send_email.return_value = True

        tests.create_projects(self.session)
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            description='test project #1',
            hook_token='aaabbb',
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'forks', 'foo'), bare=True)

        # Create a git repo to play with
        gitrepo = os.path.join(tests.HERE, 'repos', 'test.git')
        self.assertFalse(os.path.exists(gitrepo))
        os.makedirs(gitrepo)
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(tests.HERE, 'forks', 'foo', 'test.git')
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        # Create a PR for these "changes" (there are none, both repos are
        # empty)
        project = pagure.lib.get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=item,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
            requestfolder=None,

        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        output = self.app.get('/test/pull-request/1.patch', follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<title>Overview - test - Pagure</title>', output.data)
        self.assertIn(
            '<li class="error">Fork is empty, there are no commits to '
            'request pulling</li>', output.data)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_cancel_request_pull(self, send_email):
        """ Test the cancel_request_pull endpoint. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)
        self.set_up_git_repo(
            new_project=None, branch_from='feature', mtype='merge')

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/pull-request/cancel/1')
            self.assertEqual(output.status_code, 302)

            output = self.app.post(
                '/test/pull-request/cancel/1', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output.data)
            self.assertIn(
                '<li class="error">Invalid input submitted</li>', output.data)

            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token': csrf_token,
            }

            # Invalid project
            output = self.app.post(
                '/foo/pull-request/cancel/1', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Invalid PR id
            output = self.app.post(
                '/test/pull-request/cancel/100', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Invalid user for this project
            output = self.app.post(
                '/test/pull-request/cancel/1', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            # Project w/o pull-request
            repo = pagure.lib.get_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/cancel/1', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Project w/o pull-request
            repo = pagure.lib.get_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = True
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/cancel/1', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output.data)
            self.assertIn(
                '<li class="message">Request pull canceled!</li>',
                output.data)

    @patch('pagure.lib.notify.send_email')
    def test_set_assignee_requests(self, send_email):
        """ Test the set_assignee_requests endpoint. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)
        self.set_up_git_repo(new_project=None, branch_from='feature')

        # No such project
        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/pull-request/1/assign')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/pull-request/100/assign')
            self.assertEqual(output.status_code, 404)

            # Invalid input
            output = self.app.post(
                '/test/pull-request/1/assign', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<h2>Pull Request: PR from the feature branch</h2>',
                output.data)
            self.assertNotIn(
                '<li class="message">Request assigned</li>', output.data)

            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'user': 'pingou',
            }

            # No CSRF
            output = self.app.post(
                '/test/pull-request/1/assign', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<h2>Pull Request: PR from the feature branch</h2>',
                output.data)
            self.assertNotIn(
                '<li class="message">Request assigned</li>', output.data)

            # Invalid assignee
            data = {
                'csrf_token': csrf_token,
                'user': 'bar',
            }

            output = self.app.post(
                '/test/pull-request/1/assign', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<h2>Pull Request: PR from the feature branch</h2>',
                output.data)
            self.assertIn(
                '<li class="error">No user &#34;bar&#34; found</li>',
                output.data)

            # Assign the PR
            data = {
                'csrf_token': csrf_token,
                'user': 'pingou',
            }

            output = self.app.post(
                '/test/pull-request/1/assign', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<h2>Pull Request: PR from the feature branch</h2>',
                output.data)
            self.assertIn(
                '<li class="message">Request assigned</li>', output.data)

            # Pull-Request closed
            repo = pagure.lib.get_project(self.session, 'test')
            req = repo.requests[0]
            req.status = 'Closed'
            req.closed_by_in = 1
            self.session.add(req)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/assign', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 403)

            # Project w/o pull-request
            repo = pagure.lib.get_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/assign', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.notify.send_email')
    def test_fork_project(self, send_email):
        """ Test the fork_project endpoint. """
        send_email.return_value = True

        tests.create_projects(self.session)
        for folder in ['docs', 'tickets', 'requests', 'repos']:
            tests.create_projects_git(
                os.path.join(tests.HERE, folder), bare=True)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/do_fork/test')
            self.assertEqual(output.status_code, 400)

            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New project</h2>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/do_fork/foo', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            output = self.app.post(
                '/do_fork/test', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="error">You may not fork your own repo</li>',
                output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/do_fork/test')
            self.assertEqual(output.status_code, 400)

            data = {
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/do_fork/test', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="message">Repo &#34;test&#34; cloned to '
                '&#34;foo/test&#34;</li>', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull(self, send_email):
        """ Test the new_request_pull endpoint. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)

        repo = pagure.lib.get_project(self.session, 'test')
        fork = pagure.lib.get_project(self.session, 'test', user='foo')

        self.set_up_git_repo(
            new_project=fork, branch_from='feature', mtype='FF')

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/foo/diff/master..feature')
            self.assertEqual(output.status_code, 404)

            output = self.app.get('/test/diff/master..foo')
            self.assertEqual(output.status_code, 400)

            output = self.app.get('/test/diff/foo..master')
            self.assertEqual(output.status_code, 400)

            output = self.app.get('/test/diff/feature..master')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Diff from master to feature - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<td class="error"> No commits found </td>', output.data)

            output = self.app.get('/test/diff/master..feature')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Diff from feature to master - test - Pagure</title>',
                output.data)
            self.assertNotIn(
                '<input type="submit" class="submit positive button" '
                'value="Create">', output.data)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/diff/master..feature')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Diff from feature to master - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<input type="submit" class="submit positive button" '
                'value="Create">', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token': csrf_token,
                'title': 'foo bar PR',
            }

            output = self.app.post(
                '/test/diff/master..feature', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#2: foo bar PR - test - Pagure</title>',
                output.data)
            self.assertIn(
                '<li class="message">Request created</li>', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_empty_repo(self, send_email):
        """ Test the new_request_pull endpoint against an empty repo. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)

        repo = pagure.lib.get_project(self.session, 'test')
        fork = pagure.lib.get_project(self.session, 'test', user='foo')

        # Create a git repo to play with
        gitrepo = os.path.join(tests.HERE, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(tests.HERE, 'forks', 'foo', 'test.git')
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get(
                '/fork/foo/test/diff/master..feature',
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output.data)
            self.assertIn(
                '<li class="error">Fork is empty, there are no commits to '
                'request pulling</li>', output.data)

            output = self.app.get('/test/new_issue')
            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token': csrf_token,
                'title': 'foo bar PR',
            }

            output = self.app.post(
                '/test/diff/master..feature', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output.data)
            self.assertIn(
                '<li class="error">Fork is empty, there are no commits to '
                'request pulling</li>', output.data)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_empty_fork(self, send_email):
        """ Test the new_request_pull endpoint against an empty repo. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)

        repo = pagure.lib.get_project(self.session, 'test')
        fork = pagure.lib.get_project(self.session, 'test', user='foo')

        # Create a git repo to play with
        gitrepo = os.path.join(tests.HERE, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(tests.HERE, 'forks', 'foo', 'test.git')
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get(
                '/fork/foo/test/diff/master..master', follow_redirects=True)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output.data)
            self.assertIn(
                '<li class="error">Fork is empty, there are no commits to '
                'request pulling</li>', output.data)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_pull_request_add_comment(self, send_email):
        """ Test the pull_request_add_comment endpoint. """
        send_email.return_value = True

        self.test_request_pull()

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/pull-request/1/comment')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/pull-request/100/comment')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/pull-request/1/comment')
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                output.data.startswith('<section class="add_comment">'))

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token': csrf_token,
                'comment': 'This look alright but we can do better',
            }
            output = self.app.post(
                '/test/pull-request/1/comment', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<li class="message">Comment added</li>', output.data)

            # Project w/o pull-request
            repo = pagure.lib.get_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/comment', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.notify.send_email')
    def test_pull_request_drop_comment(self, send_email):
        """ Test the pull_request_drop_comment endpoint. """
        send_email.return_value = True

        self.test_pull_request_add_comment()
        # Project w/ pull-request
        repo = pagure.lib.get_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/pull-request/1/comment/drop')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/pull-request/100/comment/drop')
            self.assertEqual(output.status_code, 404)

            output = self.app.post(
                '/test/pull-request/1/comment/drop', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn('href="#comment-1">¶</a>', output.data)
            self.assertIn(
                '<p>This look alright but we can do better</p>',
                output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Invalid comment id
            data = {
                'csrf_token': csrf_token,
                'drop_comment': '10',
            }
            output = self.app.post(
                '/test/pull-request/1/comment/drop', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            data['drop_comment'] = '1'
            output = self.app.post(
                '/test/pull-request/1/comment/drop', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            # Drop comment
            output = self.app.post(
                '/test/pull-request/1/comment/drop', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<li class="message">Comment removed</li>', output.data)

            # Project w/o pull-request
            repo = pagure.lib.get_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/comment/drop', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.notify.send_email')
    def test_pull_request_edit_comment(self, send_email):
        """ Test the pull request edit comment endpoint """
        send_email.return_value = True

        self.test_request_pull()

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            # Repo 'foo' does not exist so it is verifying that condition
            output = self.app.post('/foo/pull-request/1/comment/1/edit')
            self.assertEqual(output.status_code, 404)

            # Here no comment is present in the PR so its verifying that condition
            output = self.app.post('/test/pull-request/100/comment/100/edit')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/pull-request/1/comment')
            self.assertEqual(output.status_code, 200)
            # Creating comment to play with
            self.assertTrue(
                output.data.startswith('<section class="add_comment">'))

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token': csrf_token,
                'comment': 'This look alright but we can do better',
            }
            output = self.app.post(
                '/test/pull-request/1/comment', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<li class="message">Comment added</li>', output.data)
            # Check if the comment is there
            self.assertIn(
                '<p>This look alright but we can do better</p>', output.data)
            output = self.app.get('/test/pull-request/1/comment/1/edit')
            self.assertEqual(output.status_code, 200)

            self.assertIn('<section class="request_comment add_comment">', output.data)
            # Checking if the comment is there in the update page
            self.assertIn(
                'This look alright but we can do better</textarea>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token': csrf_token,
                'update_comment': 'This look alright but we can do better than this.',
            }
            output = self.app.post(
                '/test/pull-request/1/comment/1/edit', data=data,
                follow_redirects=True)
            # Checking if the comment is updated in the main page
            self.assertIn(
                '<p>This look alright but we can do better than this.</p>', output.data)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test - '
                'Pagure</title>', output.data)
            # Checking if Edited by User is there or not
            self.assertIn(
                '<span title="">Edited by pingou just now</span>', output.data)
            self.assertIn(
                '<li class="message">Comment updated</li>', output.data)


            #  Project w/o pull-request
            repo = pagure.lib.get_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/comment/edit/1', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)

if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagureFlaskForktests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
