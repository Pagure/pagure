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
import time
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


def _get_commits(output):
    ''' Returns the commits message in the output. All commits must have
    been made by `Alice Author` or `PY C` to be found.
    '''
    commits = []
    save = False
    cnt = 0
    for row in output.split('\n'):
        if row.strip() in ['Alice Author', 'Alice Äuthòr', 'PY C']:
            save = True
        if save:
            cnt += 1
        if cnt == 7:
            commits.append(row.strip())
            save = False
            cnt = 0
    return commits


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


    def set_up_git_repo(
            self, new_project=None, branch_from='feature', mtype='FF'):
        """ Set up the git repo and create the corresponding PullRequest
        object.
        """

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
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
                'Alice Äuthòr', 'alice@äuthòrs.tld')
            committer = pygit2.Signature(
                'Cecil Cõmmîttër', 'cecil@cõmmîttërs.tld')
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
        project = pagure.get_authorized_project(self.session, 'test')
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

    def test_request_pull_reference(self):
        """ Test if there is a reference created for a new PR. """

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        self.set_up_git_repo(new_project=None, branch_from='feature')

        project = pagure.get_authorized_project(self.session, 'test')
        self.assertEqual(len(project.requests), 1)

        # View the pull-request
        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 200)

        # Give time to the worker to process the task
        time.sleep(1)

        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        repo = pygit2.Repository(gitrepo)
        self.assertEqual(
            list(repo.listall_references()),
            ['refs/heads/feature', 'refs/heads/master', 'refs/pull/1/head']
        )

    @patch('pagure.lib.notify.send_email')
    def test_request_pull(self, send_email):
        """ Test the request_pull endpoint. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        # Non-existant project
        output = self.app.get('/foobar/pull-request/1')
        self.assertEqual(output.status_code, 404)

        # Project has no PR
        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo(new_project=None, branch_from='feature')

        project = pagure.get_authorized_project(self.session, 'test')
        self.assertEqual(len(project.requests), 1)

        # View the pull-request
        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h3><span class="label label-default">PR#1</span>\n'
            '  PR from the feature branch\n</h3>', output.data)
        self.assertIn(
            'title="View file as of 2a552b">sources</a>', output.data)

        # Test if the `open changed file icon` is displayed.
        self.assertIn(
            'class="open_changed_file_icon_wrap"><span '
            'class="oi open_changed_file_icon" data-glyph="eye" '
            'alt="Open changed file" title="Open changed file"></span>'
            '</a>', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_merge_request_pull_FF(self, send_email):
        """ Test the merge_request_pull endpoint with a FF PR. """
        send_email.return_value = True

        self.test_request_pull()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            # No CSRF
            output = self.app.post(
                '/test/pull-request/1/merge', data={}, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n</h3>', output.data)
            self.assertIn(
                'title="View file as of 2a552b">sources</a>', output.data)

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
            repo = pagure.get_authorized_project(self.session, 'test')
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
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n     <span class="pull-xs-right">',
                output.data)
            self.assertIn(
                '</button>\n                      This request must be '
                'assigned to be merged', output.data)

            # PR assigned but not to this user
            repo = pagure.get_authorized_project(self.session, 'test')
            req = repo.requests[0]
            req.assignee_id = 2
            self.session.add(req)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n     <span class="pull-xs-right">',
                output.data)
            self.assertIn(
                '</button>\n                      Only the assignee can '
                'merge this review', output.data)

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
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n     <span class="pull-xs-right">',
                output.data)
            self.assertIn(
                '</button>\n                      This request does not '
                'have the minimum review score necessary to be merged',
                output.data)

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
                'A commit on branch feature', output.data)
            self.assertNotIn(
                'Merge #1 `PR from the feature branch`', output.data)
            # Ensure we have the new commit
            commits = _get_commits(output.data)
            self.assertEqual(
                commits,
                [
                    'A commit on branch feature',
                    'Add sources file for testing'
                ]
            )

            # Check if the closing notification was added
            output = self.app.get('/test/pull-request/1')
            self.assertIn(
                '<small><p>Pull-Request has been merged by pingou</p></small>',
                output.data)

    @patch('pagure.lib.notify.send_email')
    def test_merge_request_pull_merge(self, send_email):
        """ Test the merge_request_pull endpoint with a merge PR. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(
            new_project=None, branch_from='feature', mtype='merge')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
            }

            # Merge
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output.data)

            # Check if the closing notification was added
            output = self.app.get('/test/pull-request/1')
            self.assertIn(
                '<small><p>Pull-Request has been merged by pingou</p></small>',
                output.data)

    @patch('pagure.lib.notify.send_email')
    def test_merge_request_pull_conflicts(self, send_email):
        """ Test the merge_request_pull endpoint with a conflicting PR. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(
            new_project=None, branch_from='feature', mtype='conflicts')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
            }

            # Merge conflicts
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n     <span class="pull-xs-right">',
                output.data)
            self.assertIn('Merge conflicts!', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_merge_request_pull_nochange(self, send_email):
        """ Test the merge_request_pull endpoint. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(
            new_project=None, branch_from='master', mtype='nochanges')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
            }

            # Nothing to merge
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<h3><span class="label label-default">PR#1</span>\n'
                '  <span class="label label-success">Merged</span>',
                output.data)
            self.assertIn('Nothing to do, changes were already merged',
                          output.data)

            # Check if the closing notification was added
            output = self.app.get('/test/pull-request/1')
            self.assertIn(
                '<small><p>Pull-Request has been merged by pingou</p></small>',
                output.data)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_close(self, send_email):
        """ Test the request_pull endpoint with a closed PR. """
        send_email.return_value = True

        self.test_merge_request_pull_FF()

        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h3><span class="label label-default">PR#1</span>\n'
            '  <span class="label label-success">', output.data)
        self.assertIn('<div>Merged by\n', output.data)
        self.assertIn(
            'title="View file as of 2a552b">sources</a>', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_disabled(self, send_email):
        """ Test the request_pull endpoint with PR disabled. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(new_project=None, branch_from='feature')

        # Project w/o pull-request
        repo = pagure.get_authorized_project(self.session, 'test')
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
            is_fork=True,
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, 'repos', 'forks', 'foo'), bare=True)

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(gitrepo))
        os.makedirs(gitrepo)
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(self.path, 'repos', 'forks', 'foo', 'test.git')
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
        project = pagure.get_authorized_project(self.session, 'test')
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
            '<h3><span class="label label-default">PR#1</span>\n'
            '  PR from the feature branch\n</h3>', output.data)
        self.assertTrue(
            output.data.count('<span class="commitdate" title='), 1)

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
            is_fork=True,
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, 'repos', 'forks', 'foo'), bare=True)

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(gitrepo))
        os.makedirs(gitrepo)
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(
            self.path, 'repos', 'forks', 'foo', 'test.git')
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        # Create a PR for these "changes" (there are none, both repos are
        # empty)
        project = pagure.get_authorized_project(self.session, 'test')
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
            '</button>\n                      No branch from which to pull '
            'or local PR reference were found', output.data)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_request_pulls(self, send_email):
        """ Test the request_pulls endpoint. """
        send_email.return_value = True

        # No such project
        output = self.app.get('/test/pull-requests')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/pull-requests')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h2 class="p-b-1">\n    0 Pull Requests (of 0)\n  </h2>',
            output.data)
        # Open is primary
        self.assertIn(
            '<a class="btn btn-primary btn-sm" '
            'href="/test/pull-requests">Open</a>', output.data)
        self.assertIn(
            '<a class="btn btn-secondary btn-sm" '
            'href="/test/pull-requests?status=0">Closed</a>', output.data)

        self.set_up_git_repo(new_project=None, branch_from='feature')

        output = self.app.get('/test/pull-requests')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h2 class="p-b-1">\n    1 Pull Requests (of 1)\n  </h2>',
            output.data)
        # Open is primary
        self.assertIn(
            '<a class="btn btn-primary btn-sm" '
            'href="/test/pull-requests">Open</a>', output.data)
        self.assertIn(
            '<a class="btn btn-secondary btn-sm" '
            'href="/test/pull-requests?status=0">Closed</a>', output.data)

        output = self.app.get('/test/pull-requests?status=Closed')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h2 class="p-b-1">\n    0 Closed Pull Requests (of 0)\n  </h2>',
            output.data)
        # Close is primary
        self.assertIn(
            '<a class="btn btn-secondary btn-sm" '
            'href="/test/pull-requests">Open</a>', output.data)
        self.assertIn(
            '<a class="btn btn-primary btn-sm" '
            'href="/test/pull-requests?status=0">Closed</a>', output.data)

        output = self.app.get('/test/pull-requests?status=0')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h2 class="p-b-1">\n    0 Closed/Merged Pull Requests (of 0)\n  </h2>',
            output.data)
        # Close is primary
        self.assertIn(
            '<a class="btn btn-secondary btn-sm" '
            'href="/test/pull-requests">Open</a>', output.data)
        self.assertIn(
            '<a class="btn btn-primary btn-sm" '
            'href="/test/pull-requests?status=0">Closed</a>', output.data)

        # Project w/o pull-request
        repo = pagure.get_authorized_project(self.session, 'test')
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
            os.path.join(self.path, 'requests'), bare=True)
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
        repo = pagure.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/pull-request/1.patch')
        self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_diff(self, send_email):
        """ Test the request_pull_patch endpoint. """
        send_email.return_value = True

        output = self.app.get('/test/pull-request/1.diff')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(
            new_project=None, branch_from='feature', mtype='merge')

        output = self.app.get('/test/pull-request/100.diff')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/test/pull-request/1.diff')
        self.assertEqual(output.status_code, 200)

        exp = """diff --git a/.gitignore b/.gitignore
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

        self.assertEqual(output.data, exp)

        # Project w/o pull-request
        repo = pagure.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/pull-request/1.diff')
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
            is_fork=True,
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, 'repos', 'forks', 'foo'), bare=True)

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(gitrepo))
        os.makedirs(gitrepo)
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(
            self.path, 'repos', 'forks', 'foo', 'test.git')
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
        project = pagure.get_authorized_project(self.session, 'test')
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

        output = self.app.get(
            '/test/pull-request/1.patch', follow_redirects=True)
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
            is_fork=True,
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, 'repos', 'forks', 'foo'), bare=True)

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(gitrepo))
        os.makedirs(gitrepo)
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(
            self.path, 'repos', 'forks', 'foo', 'test.git')
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        # Create a PR for these "changes" (there are none, both repos are
        # empty)
        project = pagure.get_authorized_project(self.session, 'test')
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
            '</button>\n                      No branch from which to pull '
            'or local PR reference were found', output.data)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_cancel_request_pull(self, send_email):
        """ Test the cancel_request_pull endpoint. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
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
                '</button>\n                      Invalid input submitted',
                output.data)

            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
            }

            # Invalid project
            output = self.app.post(
                '/foo/pull-request/cancel/1', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Invalid PR id
            output = self.app.post(
                '/test/pull-request/cancel/100', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Invalid user for this project
            output = self.app.post(
                '/test/pull-request/cancel/1', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            # Project w/o pull-request
            repo = pagure.get_authorized_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/cancel/1', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Project w/ pull-request
            repo = pagure.get_authorized_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = True
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/cancel/1', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output.data)
            self.assertIn(
                '</button>\n                      Pull request canceled!',
                output.data)

    @patch('pagure.lib.notify.send_email')
    def test_set_assignee_requests(self, send_email):
        """ Test the set_assignee_requests endpoint. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(new_project=None, branch_from='feature')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            # No such project
            output = self.app.post('/foo/pull-request/1/assign')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/pull-request/100/assign')
            self.assertEqual(output.status_code, 404)

            # Invalid input
            output = self.app.post(
                '/test/pull-request/1/assign', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n', output.data)
            self.assertNotIn(
                '</button>\n                      Request assigned',
                output.data)

            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            data = {
                'user': 'pingou',
            }

            # No CSRF
            output = self.app.post(
                '/test/pull-request/1/assign', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n', output.data)
            self.assertNotIn(
                '</button>\n                      Request assigned',
                output.data)

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
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n', output.data)
            self.assertIn(
                '</button>\n                      No user &#34;bar&#34; found',
                output.data)

            # Assign the PR
            data = {
                'csrf_token': csrf_token,
                'user': 'pingou',
            }

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.post(
                '/test/pull-request/1/assign', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post(
                '/test/pull-request/1/assign', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n', output.data)
            self.assertIn(
                '</button>\n                      Request assigned',
                output.data)

            # Pull-Request closed
            repo = pagure.get_authorized_project(self.session, 'test')
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
            repo = pagure.get_authorized_project(self.session, 'test')
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
                os.path.join(self.path, folder), bare=True)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/do_fork/test')
            self.assertEqual(output.status_code, 400)

            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/do_fork/foo', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

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

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull(self, send_email):
        """ Test the new_request_pull endpoint. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        repo = pagure.get_authorized_project(self.session, 'test')
        fork = pagure.get_authorized_project(self.session, 'test', user='foo')

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
                '<title>Diff from master to feature - test\n - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<p class="error"> No commits found </p>', output.data)

            output = self.app.get('/test/diff/master..feature')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Diff from feature to master - test\n - '
                'Pagure</title>', output.data)
            self.assertNotIn(
                '<input type="submit" class="submit positive button" '
                'value="Create">', output.data)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/diff/master..feature')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Create new Pull Request for master - test\n - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<input type="submit" class="btn btn-primary" value="Create">',
                output.data)

            csrf_token = self.get_csrf(output=output)

            # Case 1 - Add an initial comment
            data = {
                'csrf_token': csrf_token,
                'title': 'foo bar PR',
                'initial_comment': 'Test Initial Comment',
            }

            output = self.app.post(
                '/test/diff/master..feature', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#2: foo bar PR - test\n - Pagure</title>',
                output.data)
            self.assertIn('<p>Test Initial Comment</p>', output.data)
            self.assertEqual(output.data.count('title="PY C (pingou)"'), 1)

            # Test if the `open changed file icon` is displayed.
            self.assertIn(
                'class="open_changed_file_icon_wrap"><span '
                'class="oi open_changed_file_icon" data-glyph="eye" '
                'alt="Open changed file" title="Open changed file"></span>'
                '</a>', output.data)

            # Case 2 - Add an empty initial comment
            data = {
                'csrf_token': csrf_token,
                'title': 'foo bar PR',
                'initial_comment': '',
            }

            output = self.app.post(
                '/test/diff/master..feature', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#3: foo bar PR - test\n - Pagure</title>',
                output.data)
            self.assertNotIn('<div id="comment-', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_commit_start_stop(self, send_email):
        """ Test the the commit start and stop of brand new PR. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        repo = pagure.get_authorized_project(self.session, 'test')
        fork = pagure.get_authorized_project(self.session, 'test', user='foo')

        self.set_up_git_repo(
            new_project=fork, branch_from='feature', mtype='FF')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/diff/master..feature')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Create new Pull Request for master - test\n - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<input type="submit" class="btn btn-primary" value="Create">',
                output.data)

            csrf_token = self.get_csrf(output=output)

            # Case 1 - Add an initial comment
            data = {
                'csrf_token': csrf_token,
                'title': 'foo bar PR',
                'initial_comment': 'Test Initial Comment',
            }

            output = self.app.post(
                '/test/diff/master..feature', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#2: foo bar PR - test\n - Pagure</title>',
                output.data)
            self.assertIn('<p>Test Initial Comment</p>', output.data)

        # Check if commit start and stop have been set for PR#2
        request = pagure.lib.search_pull_requests(
            self.session, project_id=1, requestid=2)
        self.assertIsNotNone(request.commit_start)
        self.assertIsNotNone(request.commit_stop)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_empty_repo(self, send_email):
        """ Test the new_request_pull endpoint against an empty repo. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        repo = pagure.get_authorized_project(self.session, 'test')
        fork = pagure.get_authorized_project(self.session, 'test', user='foo')

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(self.path, 'repos', 'forks', 'foo', 'test.git')
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get(
                '/fork/foo/test/diff/master..feature',
                follow_redirects=True)
            self.assertEqual(output.status_code, 400)
            self.assertIn(
                '<p>No branch from which to pull or local PR reference '
                'were found</p>', output.data)

            output = self.app.get('/test/new_issue')
            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
                'title': 'foo bar PR',
            }

            output = self.app.post(
                '/test/diff/master..feature', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 400)
            self.assertIn(
                '<p>No branch from which to pull or local PR reference '
                'were found</p>', output.data)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_empty_fork(self, send_email):
        """ Test the new_request_pull endpoint against an empty repo. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        repo = pagure.get_authorized_project(self.session, 'test')
        fork = pagure.get_authorized_project(self.session, 'test', user='foo')

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(
            self.path, 'repos', 'forks', 'foo', 'test.git')
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get(
                '/fork/foo/test/diff/master..master', follow_redirects=True)
            self.assertEqual(output.status_code, 400)
            self.assertIn(
                '<p>No branch from which to pull or local PR reference '
                'were found</p>', output.data)

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
                output.data.startswith('\n<section class="add_comment">'))

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
                'comment': 'This look alright but we can do better',
            }
            output = self.app.post(
                '/test/pull-request/1/comment', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output.data)
            self.assertIn(
                '</button>\n                      Comment added',
                output.data)
            self.assertEqual(output.data.count('title="PY C (pingou)"'), 2)

            # Project w/o pull-request
            repo = pagure.get_authorized_project(self.session, 'test')
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
        repo = pagure.get_authorized_project(self.session, 'test')
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
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n</h3>', output.data)
            #self.assertIn('href="#comment-1">¶</a>', output.data)
            self.assertIn(
                '<p>This look alright but we can do better</p>',
                output.data)

            csrf_token = self.get_csrf(output=output)

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
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n     <span class="pull-xs-right">',
                output.data)
            self.assertIn(
                '</button>\n                      Comment removed',
                output.data)

            # Project w/o pull-request
            repo = pagure.get_authorized_project(self.session, 'test')
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
                output.data.startswith('\n<section class="add_comment">'))

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
                'comment': 'This look alright but we can do better',
            }
            output = self.app.post(
                '/test/pull-request/1/comment', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            self.assertIn(
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n     <span class="pull-xs-right">',
                output.data)
            self.assertIn(
                '</button>\n                      Comment added',
                output.data)
            # Check if the comment is there
            self.assertIn(
                '<p>This look alright but we can do better</p>', output.data)
            output = self.app.get('/test/pull-request/1/comment/1/edit')
            self.assertEqual(output.status_code, 200)

            self.assertIn('<section class="edit_comment">', output.data)
            # Checking if the comment is there in the update page
            self.assertIn(
                'This look alright but we can do better</textarea>', output.data)

            csrf_token = self.get_csrf(output=output)

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
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n     <span class="pull-xs-right">',
                output.data)
            # Checking if Edited by User is there or not
            self.assertTrue(
                '<small class="text-muted">Edited just now by pingou </small>'
                in output.data
                or
                '<small class="text-muted">Edited seconds ago by pingou </small>'
                in output.data)
            self.assertIn(
                '</button>\n                      Comment updated', output.data)

            #  Project w/o pull-request
            repo = pagure.get_authorized_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/comment/edit/1', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.notify.send_email')
    def test_merge_request_pull_FF_w_merge_commit(self, send_email):
        """ Test the merge_request_pull endpoint with a FF PR but with a
        merge commit.
        """
        send_email.return_value = True

        self.test_request_pull()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            # No CSRF
            output = self.app.post(
                '/test/pull-request/1/merge', data={}, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output.data)
            self.assertIn(
                '<h3><span class="label label-default">PR#1</span>\n'
                '  PR from the feature branch\n</h3>', output.data)
            self.assertIn(
                'title="View file as of 2a552b">sources</a>', output.data)

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

            # Project requiring a merge commit
            repo = pagure.get_authorized_project(self.session, 'test')
            settings = repo.settings
            settings['always_merge'] = True
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            # Merge
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output.data)
            self.assertIn(
                'Merge #1 `PR from the feature branch`', output.data)
            self.assertIn(
                'A commit on branch feature', output.data)
            # Ensure we have the merge commit
            commits = _get_commits(output.data)
            self.assertEqual(commits, [
                'Merge #1 `PR from the feature branch`',
                'Add sources file for testing',
                'A commit on branch feature',
            ])

            # Check if the closing notification was added
            output = self.app.get('/test/pull-request/1')
            self.assertIn(
                '<small><p>Pull-Request has been merged by pingou</p></small>',
                output.data)

    @patch('pagure.lib.notify.send_email')
    def test_internal_endpoint_main_ahead(self, send_email):
        """ Test the new_request_pull endpoint when the main repo is ahead
        of the fork.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        self.set_up_git_repo(
            new_project=None,
            branch_from='feature')

        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Make the main repo be ahead of the fork

        # First commit
        newpath = tempfile.mkdtemp(prefix='pagure-test')
        repopath = os.path.join(newpath, 'test')
        clone_repo = pygit2.clone_repository(gitrepo, repopath)

        # Create a file in that git repo
        with open(os.path.join(repopath, 'testfile'), 'w') as stream:
            stream.write('foo\n bar')
        clone_repo.index.add('testfile')
        clone_repo.index.write()

        # Commits the files added
        last_commit = clone_repo.revparse_single('HEAD')
        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        clone_repo.create_commit(
            'refs/heads/master',  # the name of the reference to update
            author,
            committer,
            'Add testfile file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [last_commit.oid.hex]
        )

        # Second commit
        with open(os.path.join(repopath, 'testfile'), 'a') as stream:
            stream.write('\nfoo2\n bar2')
        clone_repo.index.add('testfile')
        clone_repo.index.write()

        # Commits the files added
        last_commit = clone_repo.revparse_single('HEAD')
        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        clone_repo.create_commit(
            'refs/heads/master',  # the name of the reference to update
            author,
            committer,
            'Add a second commit to testfile for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [last_commit.oid.hex]
        )

        # Third commit
        with open(os.path.join(repopath, 'testfile'), 'a') as stream:
            stream.write('\nfoo3\n bar3')
        clone_repo.index.add('testfile')
        clone_repo.index.write()

        # Commits the files added
        last_commit = clone_repo.revparse_single('HEAD')
        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        clone_repo.create_commit(
            'refs/heads/master',  # the name of the reference to update
            author,
            committer,
            'Add a third commit to testfile for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [last_commit.oid.hex]
        )

        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        shutil.rmtree(newpath)

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):

            output = self.app.get('/new')
            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            output = self.app.post(
                '/pv/pull-request/ready',
                data={'repo': 'test', 'csrf_token': csrf_token}
            )
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                  "code": "OK",
                  "message": {
                    "branch_w_pr": {
                      "feature": 1
                    },
                    "new_branch": {}
                  }
                }
            )

    @patch('pagure.lib.notify.send_email')
    def test_fork_edit_file(self, send_email):
        """ Test the fork_edit file endpoint. """

        send_email.return_value = True

        # Git repo not found
        output = self.app.post('fork_edit/test/edit/master/f/sources')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        for folder in ['docs', 'tickets', 'requests', 'repos']:
            tests.create_projects_git(
                os.path.join(self.path, folder), bare=True)

        # User not logged in
        output = self.app.post('fork_edit/test/edit/master/f/sources')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            # Invalid request
            output = self.app.post('fork_edit/test/edit/master/f/source')
            self.assertEqual(output.status_code, 400)

            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
            }

            # No files can be found since they are not added
            output = self.app.post('fork_edit/test/edit/master/f/sources',
                        data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):

            data = {
                'csrf_token': csrf_token,
            }

            # Invalid request
            output = self.app.post('fork_edit/test/edit/master/f/sources',
                            follow_redirects=True)
            self.assertEqual(output.status_code, 400)

            # Add content to the repo
            tests.add_content_git_repo(os.path.join(
                pagure.APP.config['GIT_FOLDER'], 'test.git'))

            tests.add_readme_git_repo(os.path.join(
                pagure.APP.config['GIT_FOLDER'], 'test.git'))

            tests.add_binary_git_repo(
                os.path.join(
                    pagure.APP.config['GIT_FOLDER'], 'test.git'), 'test.jpg')

            # Check if button exists
            output = self.app.get('/test/blob/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'Fork and Edit\n                    </button>\n',
                output.data)

            # Check fork-edit doesn't show for binary files
            output = self.app.get('/test/blob/master/f/test.jpg')
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                'Fork and Edit\n                    </button>\n',
                output.data)

            # Check for edit panel
            output = self.app.post('fork_edit/test/edit/master/f/sources',
                            data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li><a href="/fork/foo/test/tree/master">'
                '<span class="oi" data-glyph="random"></span>&nbsp; master</a>'
                '</li><li class="active"><span class="oi" data-glyph="file">'
                '</span>&nbsp; sources</li>',
                output.data)
            self.assertIn(
                '<textarea id="textareaCode" name="content">foo\n bar</textarea>',
                output.data)

            # View what's supposed to be an image
            output = self.app.post('fork_edit/test/edit/master/f/test.jpg',
                        data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 400)
            self.assertIn('<p>Cannot edit binary files</p>', output.data)

        # Check fork-edit shows when user is not logged in
        output = self.app.get('/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'Fork and Edit\n                    </button>\n',
            output.data)

        # Check if fork-edit shows for different user
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            # Check if button exists
            output = self.app.get('/test/blob/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'Fork and Edit\n                    </button>\n',
                output.data)

            # Check fork-edit doesn't show for binary
            output = self.app.get('/test/blob/master/f/test.jpg')
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                'Fork and Edit\n                    </button>\n',
                output.data)

    @patch('pagure.lib.notify.send_email')
    def test_fork_without_main_repo(self, send_email):
        """ Test the fork without the main repo. """
        send_email.return_value = True

        tests.create_projects(self.session)

        # Create a fork with no parent i.e parent_id = None
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            description='test project #1',
            hook_token='aaabbb',
            is_fork=True,
            parent_id=None,
        )
        self.session.add(item)
        self.session.commit()

        # Get fork project
        project = pagure.lib._get_project(self.session, 'test', 'foo')

        # Pull-requests and issue-trackers are off for forks
        # lib function is not used here so mannually turning them off
        project_settings = project.settings
        project_settings['pull_requests'] = False
        project_settings['issue_tracker'] = False
        project.settings = project_settings
        self.session.add(project)
        self.session.commit()

        tests.create_projects_git(
            os.path.join(self.path, 'repos', 'forks', 'foo'), bare=True)

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(gitrepo))
        os.makedirs(gitrepo)
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(self.path, 'repos', 'forks', 'foo', 'test.git')
        new_repo = pygit2.clone_repository(gitrepo, newpath)
        tests.add_content_git_repo(gitrepo)

        # UI test for deleted main
        output = self.app.get('/fork/foo/test')
        self.assertEqual(output.status_code, 200)
        print output.data
        self.assertIn('Fork from a deleted repository\n', output.data)

        # Testing commit endpoint
        output = self.app.get('/fork/foo/test/commits/master')
        self.assertEqual(output.status_code, 200)
        self.assertIn('Commits <span class="label label-default"> 2</span>\n    </h3>\n', output.data)

        # Test pull-request endpoint
        output = self.app.get('/fork/foo/test/pull-requests')
        self.assertEqual(output.status_code, 404)

        # Test issue-tracker endpoint
        output = self.app.get('/fork/foo/test/issues')
        self.assertEqual(output.status_code, 404)

        shutil.rmtree(newpath)

if __name__ == '__main__':
    unittest.main(verbosity=2)
