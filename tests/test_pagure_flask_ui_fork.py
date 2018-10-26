# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

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
import re

import pygit2
import six
from mock import patch, MagicMock
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib.query
import pagure.lib.tasks
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

    def set_up_git_repo(
            self, new_project=None, branch_from='feature', mtype='FF',
            prid=1, name_from='test'):
        """ Set up the git repo and create the corresponding PullRequest
        object.
        """

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', '%s.git' % name_from)
        repo = pygit2.init_repository(gitrepo, bare=True)

        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        repopath = os.path.join(newpath, 'test')
        clone_repo = pygit2.clone_repository(gitrepo, repopath)

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
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            prev_commit
        )
        time.sleep(1)
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        first_commit = repo.revparse_single('HEAD')

        def compatible_signature(name, email):
            if six.PY2:
                name = name.encode("utf-8")
                email = email.encode("utf-8")
            return pygit2.Signature(name, email)

        if mtype == 'merge':
            with open(os.path.join(repopath, '.gitignore'), 'w') as stream:
                stream.write('*~')
            clone_repo.index.add('.gitignore')
            clone_repo.index.write()

            # Commits the files added
            tree = clone_repo.index.write_tree()
            author = compatible_signature(
                'Alice Äuthòr', 'alice@äuthòrs.tld')
            comitter = compatible_signature(
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
                'A commit on branch %s\n\nMore information' % branch_from,
                tree,
                [first_commit.oid.hex]
            )
            refname = 'refs/heads/%s' % (branch_from)
            ori_remote = repo.remotes[0]
            PagureRepo.push(ori_remote, refname)

        # Create a PR for these changes
        project = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from=branch_from,
            repo_to=project,
            branch_to='master',
            title='PR from the %s branch' % branch_from,
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, prid)
        self.assertEqual(req.title, 'PR from the %s branch' % branch_from)

        shutil.rmtree(newpath)

    def test_request_pull_reference(self):
        """ Test if there is a reference created for a new PR. """

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        self.set_up_git_repo(new_project=None, branch_from='feature')

        project = pagure.lib.query.get_authorized_project(self.session, 'test')
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

        project = pagure.lib.query.get_authorized_project(self.session, 'test')
        self.assertEqual(len(project.requests), 1)

        # View the pull-request
        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        #self.assertIn(
            #'<h3><span class="label label-default">PR#1</span>\n'
            #'  PR from the feature branch\n</h3>',
            #output_text)
        self.assertIn(
            'title="View file as of 2a552b">sources</a>', output_text)

        # Test if the `open changed file icon` is displayed.
        self.assertIn(
            'class="open_changed_file_icon_wrap"><span '
            'class="fa fa-file-code-o fa-fw" '
            'alt="Open changed file" title="Open changed file"></span>'
            '</a>', output_text)

        self.assertIn(
            '<span class="btn btn-success btn-sm font-weight-bold disabled opacity-100">+3</span>', output_text)
        self.assertIn(
            '<span class="btn btn-danger btn-sm font-weight-bold disabled opacity-100">-1</span>',
            output_text)

    @patch('pagure.lib.notify.send_email')
    def test_task_update_request_pull(self, send_email):
        """ Test the task update_pull_request endpoint. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        self.set_up_git_repo(new_project=None, branch_from='feature')

        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query.get_authorized_project(self.session, 'test')
        self.assertEqual(len(project.requests), 1)

        request = project.requests[0]
        self.assertEqual(len(request.comments), 0)
        start_commit = request.commit_start
        stop_commit = request.commit_stop

        # View the pull-request
        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>PR#1: PR from the feature branch - test\n - Pagure</title>',
            output_text)
        self.assertIn(
            'title="View file as of 2a552b">sources</a>', output_text)

        # Add a new commit on the repo from
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        repopath = os.path.join(newpath, 'test')
        clone_repo = pygit2.clone_repository(
            gitrepo, repopath, checkout_branch='feature')

        def compatible_signature(name, email):
            if six.PY2:
                name = name.encode("utf-8")
                email = email.encode("utf-8")
            return pygit2.Signature(name, email)

        with open(os.path.join(repopath, '.gitignore'), 'w') as stream:
                stream.write('*~')
        clone_repo.index.add('.gitignore')
        clone_repo.index.write()

        com = clone_repo.revparse_single('HEAD')
        prev_commit = [com.oid.hex]

        # Commits the files added
        tree = clone_repo.index.write_tree()
        author = compatible_signature(
            'Alice Äuthòr', 'alice@äuthòrs.tld')
        comitter = compatible_signature(
            'Cecil Cõmmîttër', 'cecil@cõmmîttërs.tld')
        clone_repo.create_commit(
            'refs/heads/feature',
            author,
            comitter,
            'Add .gitignore file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            prev_commit
        )
        refname = 'refs/heads/feature:refs/heads/feature'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)
        shutil.rmtree(newpath)

        pagure.lib.tasks.update_pull_request(request.uid)

        self.session = pagure.lib.query.create_session(self.dbpath)
        project = pagure.lib.query.get_authorized_project(self.session, 'test')
        self.assertEqual(len(project.requests), 1)
        request = project.requests[0]
        self.assertEqual(len(request.comments), 1)
        self.assertIsNotNone(request.commit_start)
        self.assertIsNotNone(request.commit_stop)
        self.assertNotEqual(start_commit, request.commit_start)
        self.assertNotEqual(stop_commit, request.commit_stop)

    @patch('pagure.lib.notify.send_email')
    def test_merge_request_pull_FF(self, send_email):
        """ Test the merge_request_pull endpoint with a FF PR. """
        send_email.return_value = True

        self.test_request_pull()

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            # No CSRF
            output = self.app.post(
                '/test/pull-request/1/merge', data={}, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output_text)
            #self.assertIn(
                #'<h3><span class="label label-default">PR#1</span>\n'
                #'  PR from the feature branch\n</h3>',
                #output_text)
            self.assertIn(
                'title="View file as of 2a552b">sources</a>', output_text)

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
        with tests.user_set(self.app.application, user):

            # Wrong request id
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/pull-request/100/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Project w/o pull-request
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
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
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            settings['pull_requests'] = True
            settings['Only_assignee_can_merge_pull-request'] = True
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n',
                output_text)
            self.assertIn(
                'This request must be '
                'assigned to be merged', output_text)

            # PR assigned but not to this user
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            req = repo.requests[0]
            req.assignee_id = 2
            self.session.add(req)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n',
                output_text)
            self.assertIn(
                'Only the assignee can '
                'merge this review', output_text)

            # Project w/ minimal PR score
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            settings['Only_assignee_can_merge_pull-request'] = False
            settings['Minimum_score_to_merge_pull-request'] = 2
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n',
                output_text)
            self.assertIn(
                'This request does not '
                'have the minimum review score necessary to be merged',
                output_text)

            # Merge
            self.session.commit()
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            settings['Minimum_score_to_merge_pull-request'] = -1
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            output = self.app.get('/test/commits')
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Commits - test - Pagure</title>', output_text)
            self.assertIn(
                'A commit on branch feature', output_text)
            self.assertNotIn(
                'Merge #1 `PR from the feature branch`', output_text)

            # Check if the closing notification was added
            output = self.app.get('/test/pull-request/1')
            self.assertIn(
                '<span class="text-info font-weight-bold">Merged</span> just now\n'
                '            </span>\n            by\n'
                '            <span title="PY C (pingou)">pingou.</span>\n',
                output.get_data(as_text=True))

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
        with tests.user_set(self.app.application, user):
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
                '<title>Overview - test - Pagure</title>', output.get_data(as_text=True))

            # Check if the closing notification was added
            output = self.app.get('/test/pull-request/1')
            self.assertIn(
                '<span class="text-info font-weight-bold">Merged</span> just now\n'
                '            </span>\n            by\n'
                '            <span title="PY C (pingou)">pingou.</span>\n',
                output.get_data(as_text=True))

    @patch('pagure.lib.notify.send_email')
    def test_merge_request_pull_merge_with_delete_branch(self, send_email):
        """ Test the merge_request_pull endpoint with a merge PR and delete source branch. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(
            new_project=None, branch_from='feature-branch', mtype='merge')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            data = {
                'csrf_token': self.get_csrf(output=output),
                'delete_branch': True,
            }

            # Merge
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output_text)
            # Check the branch is not mentioned
            self.assertNotIn(
                '<a class="" href="/test/branch/feature-branch"', output_text)

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
        with tests.user_set(self.app.application, user):
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
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n',
                output_text)
            self.assertIn('Merge conflicts!', output_text)

    @patch('pagure.lib.notify.send_email')
    def test_merge_request_pull_conflicts_with_delete_branch(self, send_email):
        """ Test the merge_request_pull endpoint with a conflicting PR and request deletion of branch. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(
            new_project=None, branch_from='feature-branch', mtype='conflicts')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            data = {
                'csrf_token': self.get_csrf(output=output),
                'delete_branch': True,
            }

            # Merge conflicts
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n'
                '              <span class="text-success font-weight-bold">#1</span>\n'
                '            <span class="font-weight-bold">\n'
                '                  PR from the feature-branch branch\n',
                output_text)
            self.assertIn('Merge conflicts!', output_text)

            # Check the branch still exists
            output = self.app.get('/test/branches')
            self.assertIn('feature-branch', output.get_data(as_text=True))

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
        with tests.user_set(self.app.application, user):
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
            output_text = output.get_data(as_text=True)

            self.assertIn('Nothing to do, changes were already merged',
                          output_text)

            # Check if the closing notification was added
            output = self.app.get('/test/pull-request/1')
            self.assertIn(
                '<span class="text-info font-weight-bold">Merged</span> just now\n'
                '            </span>\n            by\n'
                '            <span title="PY C (pingou)">pingou.</span>\n',
                output.get_data(as_text=True))

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_close(self, send_email):
        """ Test the request_pull endpoint with a closed PR. """
        send_email.return_value = True

        self.test_merge_request_pull_FF()

        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)

        self.assertIn('<span class="text-info font-weight-bold">Merged</span> '
            'just now\n            </span>\n            by\n', output_text)
        self.assertIn(
            'title="View file as of 2a552b">sources</a>', output_text)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_disabled(self, send_email):
        """ Test the request_pull endpoint with PR disabled. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(new_project=None, branch_from='feature')

        # Project w/o pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 404)

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.lib.git.update_pull_ref')
    def test_request_pull_empty_repo(self, send_email, update_pull_ref):
        """ Test the request_pull endpoint against an empty repo. """
        # Mock update_pull_ref or the repo won't be empty anymore
        # (the PR will have been pushed to refs/pull)
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
        project = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=item,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n', output_text)
        self.assertTrue(
            output_text.count(
                '<span class="commitdate"'), 1)
        self.assertTrue(update_pull_ref.called)

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
        project = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=item,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        output = self.app.get('/test/pull-request/1', follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>PR#1: PR from the feature branch - test\n - Pagure</title>',
            output_text)
        self.assertIn(
            'Fork is empty, there are no '
            'commits to create a pull request with',
            output_text)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_request_pulls_order(self, send_email):
        """Test the request_pulls

        i.e Make sure that the results are displayed
        in the order required by the user"""
        send_email.return_value = True

        #Initially no project
        output = self.app.get('/test/pull-requests')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        item = pagure.lib.model.Project(
            user_id=2,
            name='test',
            description='test project #1',
            hook_token='aaabbb',
            is_fork=True,
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        # create PR's to play with
        # PR-1
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_to=repo,
            repo_from=item,
            branch_from='feature',
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
            status='Open',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        # PR-2
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_to=repo,
            branch_to='master',
            branch_from='feature',
            repo_from=item,
            title='test PR',
            user='pingou',
            status='Open',
        )
        self.session.commit()
        self.assertEqual(req.title, 'test PR')

        # PR-3
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_to=repo,
            branch_from='feature',
            branch_to='master',
            repo_from=item,
            title='test Invalid PR',
            user='pingou',
            status='Closed',
        )
        self.session.commit()
        self.assertEqual(req.title, 'test Invalid PR')

        # PR-4
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_to=repo,
            branch_from='feature',
            title='test PR for sort',
            repo_from=item,
            user='pingou',
            branch_to='master',
            status='Open',
        )
        self.session.commit()
        self.assertEqual(req.title, 'test PR for sort')

        # sort by last_updated
        output = self.app.get('/test/pull-requests?order_key=last_updated')
        output_text = output.get_data(as_text=True)
        tr_elements = re.findall('<div class="request-row list-group-item list-group-item-action ">(.*?)</div><!--end request-row-->', output_text, re.M | re.S)
        self.assertEqual(output.status_code, 200)
        # Make sure that issue four is first since it was modified last
        self.assertIn('href="/test/pull-request/4"', tr_elements[0])
        self.assertIn('href="/test/pull-request/2"', tr_elements[1])
        self.assertIn('href="/test/pull-request/1"', tr_elements[2])

        pr_one = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        pr_one.last_updated = datetime.utcnow() + timedelta(seconds=2)
        self.session.add(pr_one)
        self.session.commit()

        # sort by last_updated
        output = self.app.get('/test/pull-requests?order_key=last_updated')
        output_text = output.get_data(as_text=True)
        tr_elements = re.findall('<div class="request-row list-group-item list-group-item-action ">(.*?)</div><!--end request-row-->', output_text, re.M | re.S)
        self.assertEqual(output.status_code, 200)
        # Make sure that PR four is first since it was modified last
        self.assertIn('href="/test/pull-request/1"', tr_elements[0])
        # Make sure that PR two is second since it was modified second
        self.assertIn('href="/test/pull-request/4"', tr_elements[1])
        # Make sure that PR one is last since it was modified first
        self.assertIn('href="/test/pull-request/2"', tr_elements[2])


        # Now query so that the results are ascending
        output = self.app.get('/test/pull-requests?'
                'order_key=last_updated&order=asc')
        output_text = output.get_data(as_text=True)
        tr_elements = re.findall('<div class="request-row list-group-item list-group-item-action ">(.*?)</div><!--end request-row-->', output_text, re.M | re.S)
        self.assertIn('href="/test/pull-request/2"', tr_elements[0])
        self.assertIn('href="/test/pull-request/4"', tr_elements[1])
        self.assertIn('href="/test/pull-request/1"', tr_elements[2])

        #check that search_pattern argument works
        output = self.app.get('/test/pull-requests?search_pattern=feature')
        output_text = output.get_data(as_text=True)
        tr_elements = re.findall('<div class="request-row list-group-item list-group-item-action ">(.*?)</div><!--end request-row-->', output_text, re.M | re.S)
        self.assertIn('href="/test/pull-request/1"', tr_elements[0])
        self.assertEqual(len(tr_elements), 1)

        output = self.app.get('/test/pull-requests?search_pattern=PR')
        output_text = output.get_data(as_text=True)
        tr_elements = re.findall('<div class="request-row list-group-item list-group-item-action ">(.*?)</div><!--end request-row-->', output_text, re.M | re.S)
        self.assertIn('href="/test/pull-request/4"', tr_elements[0])
        self.assertIn('href="/test/pull-request/2"', tr_elements[1])
        self.assertIn('href="/test/pull-request/1"', tr_elements[2])
        self.assertEqual(len(tr_elements), 3)

        output = self.app.get('/test/pull-requests?search_pattern=*PR')
        output_text = output.get_data(as_text=True)
        tr_elements = re.findall('<div class="request-row list-group-item list-group-item-action ">(.*?)</div><!--end request-row-->', output_text, re.M | re.S)
        self.assertEqual(len(tr_elements), 1)
        self.assertIn('href="/test/pull-request/2"', tr_elements[0])

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
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<span class="fa fa-fw fa-arrow-circle-down"></span> 0 Open PRs\n',
            output_text)

        self.set_up_git_repo(new_project=None, branch_from='feature')

        output = self.app.get('/test/pull-requests')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<span class="fa fa-fw fa-arrow-circle-down"></span> 1 Open PRs\n',
            output_text)

        output = self.app.get('/test/pull-requests?status=1')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<span class="fa fa-fw fa-arrow-circle-down"></span> 1 Open PRs\n',
            output_text)

        output = self.app.get('/test/pull-requests?status=true')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<span class="fa fa-fw fa-arrow-circle-down"></span> 1 Open PRs\n',
            output_text)

        output = self.app.get('/test/pull-requests?status=Merged')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<span class="fa fa-fw fa-arrow-circle-down"></span> 0 Merged PRs\n',
            output_text)

        output = self.app.get('/test/pull-requests?status=0')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<span class="fa fa-fw fa-arrow-circle-down"></span> 0 Merged PRs\n',
            output_text)

        output = self.app.get('/test/pull-requests?status=Closed')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<span class="fa fa-fw fa-arrow-circle-down"></span> 0 Cancelled PRs\n',
            output_text)


        # Project w/o pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
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
        for row in output.get_data(as_text=True).split('\n'):
            if row.startswith('Date:'):
                continue
            if row.startswith('From '):
                row = row.split(' ', 2)[2]
            npatch.append(row)

        exp = r"""Mon Sep 17 00:00:00 2001
From: Alice Author <alice@authors.tld>
Subject: A commit on branch feature


More information
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
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
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

        exp = r"""diff --git a/.gitignore b/.gitignore
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

        self.assertEqual(output.get_data(as_text=True), exp)

        # Project w/o pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
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
        for row in output.get_data(as_text=True).split('\n'):
            if row.startswith('Date:'):
                continue
            if row.startswith('From '):
                row = row.split(' ', 2)[2]
            npatch.append(row)

        exp = r"""Mon Sep 17 00:00:00 2001
From: Alice Author <alice@authors.tld>
Subject: A commit on branch feature


More information
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
    @patch('pagure.lib.git.update_pull_ref')
    def test_request_pull_patch_empty_repo(self, send_email, update_pull_ref):
        """ Test the request_pull_patch endpoint against an empty repo. """
        # Mock update_pull_ref or the repo won't be empty anymore
        # (the PR will have been pushed to refs/pull)
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
        project = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=item,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',

        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        output = self.app.get(
            '/test/pull-request/1.patch', follow_redirects=True)
        self.assertEqual(output.status_code, 200)

        npatch = []
        for row in output.get_data(as_text=True).split('\n'):
            if row.startswith('Date:'):
                continue
            if row.startswith('From '):
                row = row.split(' ', 2)[2]
            npatch.append(row)

        exp = r"""Mon Sep 17 00:00:00 2001
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
        project = pagure.lib.query.get_authorized_project(self.session, 'test')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=item,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',

        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        output = self.app.get('/test/pull-request/1.patch',
                              follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>Overview - test - Pagure</title>',
            output_text)
        self.assertIn(
            'Fork is empty, there are no '
            'commits to create a pull request with',
            output_text)

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
        with tests.user_set(self.app.application, user):
            output = self.app.post('/test/pull-request/cancel/1')
            self.assertEqual(output.status_code, 302)

            output = self.app.post(
                '/test/pull-request/cancel/1', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output_text)
            self.assertIn(
                'Invalid input submitted',
                output_text)

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
        with tests.user_set(self.app.application, user):
            # Project w/o pull-request
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
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
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = True
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/cancel/1', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Overview - test - Pagure</title>', output_text)
            self.assertIn(
                'Pull request canceled!',
                output_text)

    @patch('pagure.lib.notify.send_email')
    def test_reopen_request_pull(self, send_email):
        """ Test the reopen_request_pull endpoint. """
        send_email.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(
            new_project=None, branch_from='feature', mtype='merge')

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.post('/test/pull-request/1/reopen')
            self.assertEqual(output.status_code, 302)

            output = self.app.post(
                '/test/pull-request/1/reopen', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - Pagure</title>', output_text)
            self.assertIn(
                #'Pull request reopened!',
                'return window.confirm("Are you sure you want to reopen this requested pull?")',
                output_text)

            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
            }

            # Invalid project
            output = self.app.post(
                '/foo/pull-request/1/reopen', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Invalid PR id
            output = self.app.post(
                '/test/pull-request/100/reopen', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Invalid user for this project
            output = self.app.post(
                '/test/pull-request/1/reopen', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            # Project w/o pull-request
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/reopen', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Project w/ pull-request
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = True
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/cancel/1', data=data,
                follow_redirects=True)
            output = self.app.post(
                '/test/pull-request/1/reopen', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                'return window.confirm("Are you sure you want to reopen this requested pull?")',
                output_text)

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_update_pull_requests_assign(self):
        """ Test the update_pull_requests endpoint when assigning a PR.
        """

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(new_project=None, branch_from='feature')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            # No such project
            output = self.app.post('/foo/pull-request/1/update')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/pull-request/100/update')
            self.assertEqual(output.status_code, 404)

            # Invalid input
            output = self.app.post(
                '/test/pull-request/1/update', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n', output_text)
            self.assertNotIn(
                'Request assigned',
                output_text)

            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            data = {
                'user': 'pingou',
            }

            # No CSRF
            output = self.app.post(
                '/test/pull-request/1/update', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n', output_text)
            self.assertNotIn(
                'Request assigned',
                output_text)

            # Invalid assignee
            data = {
                'csrf_token': csrf_token,
                'user': 'bar',
            }

            output = self.app.post(
                '/test/pull-request/1/update', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n', output_text)
            self.assertIn(
                'No user &#34;bar&#34; found',
                output_text)

            # Assign the PR
            data = {
                'csrf_token': csrf_token,
                'user': 'pingou',
            }

        user.username = 'foo'
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                '/test/pull-request/1/update', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                '/test/pull-request/1/update', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n', output_text)
            self.assertIn(
                'Request assigned',
                output_text)

            # Pull-Request closed
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            req = repo.requests[0]
            req.status = 'Closed'
            req.closed_by_in = 1
            self.session.add(req)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/update', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            # Project w/o pull-request
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/update', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 404)


    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_update_pull_requests_tag(self):
        """ Test the update_pull_requests endpoint when tagging a PR.
        """

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(new_project=None, branch_from='feature')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            data = {
                'tag': 'black',
            }

            # No CSRF
            output = self.app.post(
                '/test/pull-request/1/update', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n', output_text)
            self.assertNotIn(
                'Request assigned',
                output_text)

            # Tag the PR
            data = {
                'csrf_token': csrf_token,
                'tag': 'black',
            }

            output = self.app.post(
                '/test/pull-request/1/update', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n', output_text)
            self.assertIn(
                'Pull-request tagged with: black',
                output_text)
            self.assertIn(
                'title="comma separated list of tags"\n              '
                'value="black" />', output_text)

        # Try as another user
        user.username = 'foo'
        with tests.user_set(self.app.application, user):
            # Tag the PR
            data = {
                'csrf_token': csrf_token,
                'tag': 'blue, yellow',
            }

            output = self.app.post(
                '/test/pull-request/1/update', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 403)

            # Make the PR be from foo
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            req = repo.requests[0]
            req.user_id = 2
            self.session.add(req)
            self.session.commit()

            # Re-try to tag the PR
            data = {
                'csrf_token': csrf_token,
                'tag': 'blue, yellow',
            }

            output = self.app.post(
                '/test/pull-request/1/update', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            soup = BeautifulSoup(output.get_data(as_text=True), "html.parser")
            self.assertEqual(
                soup.find("title").string,
                'PR#1: PR from the feature branch - test\n - Pagure'
            )

            self.assertIn('Pull-request **un**tagged with: black', output.get_data(as_text=True))
            self.assertIn('Pull-request tagged with: blue, yellow', output.get_data(as_text=True))


        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            # Pull-Request closed
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            req = repo.requests[0]
            req.status = 'Closed'
            req.closed_by_in = 1
            self.session.add(req)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/update', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            # Project w/o pull-request
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            settings = repo.settings
            settings['pull_requests'] = False
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            output = self.app.post(
                '/test/pull-request/1/update', data=data,
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
        with tests.user_set(self.app.application, user):
            output = self.app.post('/do_fork/test')
            self.assertEqual(output.status_code, 400)

            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.get_data(as_text=True))

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/do_fork/foo', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        user.username = 'foo'
        with tests.user_set(self.app.application, user):
            output = self.app.post('/do_fork/test')
            self.assertEqual(output.status_code, 400)

            data = {
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/do_fork/test', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_branch_space(self, send_email):
        """ Test the new_request_pull endpoint. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        fork = pagure.lib.query.get_authorized_project(self.session, 'test', user='foo')

        self.set_up_git_repo(
            new_project=fork, branch_from='feature', mtype='FF')

        user = tests.FakeUser(username = 'pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/diff/master..foo bar')
            self.assertEqual(output.status_code, 400)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<p>Branch foo bar does not exist</p>', output_text)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull(self, send_email):
        """ Test the new_request_pull endpoint. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        fork = pagure.lib.query.get_authorized_project(self.session, 'test', user='foo')

        self.set_up_git_repo(
            new_project=fork, branch_from='feature', mtype='FF')

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/foo/diff/master..feature')
            self.assertEqual(output.status_code, 404)

            output = self.app.get('/test/diff/master..foo')
            self.assertEqual(output.status_code, 400)

            output = self.app.get('/test/diff/foo..master')
            self.assertEqual(output.status_code, 400)

            output = self.app.get('/test/diff/feature..master')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Diff from master to feature - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<p class="error"> No commits found </p>', output_text)

            output = self.app.get('/test/diff/master..feature')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Diff from feature to master - test\n - '
                'Pagure</title>', output_text)
            self.assertNotIn(
                '<input type="submit" class="submit positive button" '
                'value="Create">', output_text)

        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/diff/master..feature')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Create new Pull Request for master - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<input type="submit" class="btn btn-primary" value="Create Pull Request">\n',
                output_text)
            # Check that we prefilled the input fields as expected:
            self.assertIn(
                '<input class="form-control" id="title" name="title" '
                'placeholder="Pull Request Title" required="required" '
                'type="text" value="A commit on branch feature">',
                output_text)
            self.assertIn(
                '''<textarea class="form-control" rows=8 id="initial_comment" name="initial_comment"
            placeholder="Describe your changes" tabindex=1>
More information</textarea>
            <div id="preview" class="p-1">''', output_text)

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
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#2: foo bar PR - test\n - Pagure</title>',
                output_text)
            self.assertIn('<p>Test Initial Comment</p>',
                          output_text)
            self.assertEqual(
                output_text.count('title="PY C (pingou)"'),
                2)

            # Test if the `open changed file icon` is displayed.
            self.assertIn(
                'class="open_changed_file_icon_wrap"><span '
                'class="fa fa-file-code-o fa-fw" '
                'alt="Open changed file" title="Open changed file"></span>'
                '</a>', output_text)

            # Case 2 - Add an empty initial comment
            data = {
                'csrf_token': csrf_token,
                'title': 'foo bar PR',
                'initial_comment': '',
            }

            output = self.app.post(
                '/test/diff/master..feature', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#3: foo bar PR - test\n - Pagure</title>',
                output_text)
            self.assertNotIn('<div id="comment-', output_text)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_req_sign_off_view(self, send_email):
        """ Test the new_request_pull endpoint. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        fork = pagure.lib.query.get_authorized_project(self.session, 'test', user='foo')

        # Enforce Signed-of-by in the repo
        settings = repo.settings
        settings['Enforce_signed-off_commits_in_pull-request'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        self.set_up_git_repo(
            new_project=fork, branch_from='feature', mtype='FF')

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(self.app.application, user):

            output = self.app.get('/test/diff/master..feature')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Diff from feature to master - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                'This project enforces the '
                'Signed-off-by statement on all commits', output_text)
            self.assertNotIn(
                '<input type="submit" class="btn btn-primary" value="Create Pull Request">\n',
                output_text)
            self.assertNotIn(
                'This repo enforces that '
                'all commits are signed off by their author.', output_text)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_req_sign_off_submit(self, send_email):
        """ Test the new_request_pull endpoint. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        fork = pagure.lib.query.get_authorized_project(self.session, 'test', user='foo')

        # Enforce Signed-of-by in the repo
        settings = repo.settings
        settings['Enforce_signed-off_commits_in_pull-request'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        self.set_up_git_repo(
            new_project=fork, branch_from='feature', mtype='FF')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):

            output = self.app.get('/test/diff/master..feature')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Create new Pull Request for master - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                'This project enforces the '
                'Signed-off-by statement on all commits', output_text)
            self.assertIn(
                '<input type="submit" class="btn btn-primary" value="Create Pull Request">\n',
                output_text)

            csrf_token = self.get_csrf(output=output)

            # Try to create the PR
            data = {
                'csrf_token': csrf_token,
                'title': 'foo bar PR',
                'initial_comment': 'Test Initial Comment',
            }

            output = self.app.post(
                '/test/diff/master..feature', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Create new Pull Request for master - test\n - '
                'Pagure</title>', output_text)
            # Flashed information message
            self.assertIn(
                'This project enforces the '
                'Signed-off-by statement on all commits', output_text)
            # Flashed error message
            self.assertIn(
                'This repo enforces that '
                'all commits are signed off by their author.', output_text)
            self.assertIn(
                '<input type="submit" class="btn btn-primary" value="Create Pull Request">\n',
                output_text)

    @patch('pagure.lib.notify.send_email')
    def test_request_pull_commit_start_stop(self, send_email):
        """ Test the the commit start and stop of brand new PR. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        fork = pagure.lib.query.get_authorized_project(self.session, 'test', user='foo')

        self.set_up_git_repo(
            new_project=fork, branch_from='feature', mtype='FF')

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/diff/master..feature')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Create new Pull Request for master - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<input type="submit" class="btn btn-primary" value="Create Pull Request">\n',
                output_text)

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
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#2: foo bar PR - test\n - Pagure</title>',
                output_text)
            self.assertIn('<p>Test Initial Comment</p>', output_text)

        # Check if commit start and stop have been set for PR#2
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=2)
        self.assertIsNotNone(request.commit_start)
        self.assertIsNotNone(request.commit_stop)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_fork_to_fork_pr_disabled(self, send_email):
        """ Test creating a fork to fork PR. """
        send_email.return_value = True

        self.test_fork_project()

        # Create a 3rd user
        item = pagure.lib.model.User(
            user='ralph',
            fullname='Ralph bar',
            password='ralph_foo',
            default_email='ralph@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='ralph@bar.com')
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser()
        user.username = 'ralph'
        with tests.user_set(self.app.application, user):
            # Have Ralph fork, foo's fork of test
            output = self.app.get('/fork/foo/test')
            self.assertEqual(output.status_code, 200)

            output = self.app.post('/do_fork/fork/foo/test')
            self.assertEqual(output.status_code, 400)

            csrf_token = self.get_csrf()
            data = {
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/do_fork/fork/foo/test', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            # Check that Ralph's fork do exist
            output = self.app.get('/fork/ralph/test')
            self.assertEqual(output.status_code, 200)

            tests.create_projects_git(
                os.path.join(self.path, 'requests'), bare=True)

            fork = pagure.lib.query.get_authorized_project(
                self.session, 'test', user='ralph')

            self.set_up_git_repo(
                new_project=fork, branch_from='feature', mtype='FF')

            # Try opening a pull-request
            output = self.app.get(
                '/fork/ralph/test/diff/master..feature')
            self.assertEqual(output.status_code, 404)
            self.assertIn(
                '<p>No pull-request allowed on this project</p>',
                output.get_data(as_text=True))

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_fork_to_fork(self, send_email):
        """ Test creating a fork to fork PR. """
        send_email.return_value = True

        self.test_fork_project()

        # Create a 3rd user
        item = pagure.lib.model.User(
            user='ralph',
            fullname='Ralph bar',
            password='ralph_foo',
            default_email='ralph@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='ralph@bar.com')
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser()
        user.username = 'ralph'
        with tests.user_set(self.app.application, user):
            # Have Ralph fork, foo's fork of test
            output = self.app.get('/fork/foo/test')
            self.assertEqual(output.status_code, 200)

            output = self.app.post('/do_fork/fork/foo/test')
            self.assertEqual(output.status_code, 400)

            csrf_token = self.get_csrf()
            data = {
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/do_fork/fork/foo/test', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            # Check that Ralph's fork do exist
            output = self.app.get('/fork/ralph/test')
            self.assertEqual(output.status_code, 200)

            tests.create_projects_git(
                os.path.join(self.path, 'requests'), bare=True)

            # Turn on pull-request on the fork
            repo = pagure.lib.query.get_authorized_project(
                self.session, 'test', user='foo')
            settings = repo.settings
            settings['pull_requests'] = True
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            # Add some content to the parent
            self.set_up_git_repo(
                new_project=repo, branch_from='master', mtype='FF',
                name_from=repo.fullname)

            fork = pagure.lib.query.get_authorized_project(
                self.session, 'test', user='ralph')

            self.set_up_git_repo(
                new_project=fork, branch_from='feature', mtype='FF',
                prid=2, name_from=fork.fullname)

            # Try opening a pull-request
            output = self.app.get(
                '/fork/ralph/test/diff/master..feature')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Create new Pull Request for master - fork/ralph/test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<input type="submit" class="btn btn-primary" value="Create Pull Request">\n',
                output_text)

            csrf_token = self.get_csrf(output=output)

            # Case 1 - Add an initial comment
            data = {
                'csrf_token': csrf_token,
                'title': 'foo bar PR',
                'initial_comment': 'Test Initial Comment',
            }

            output = self.app.post(
                '/fork/ralph/test/diff/master..feature',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: foo bar PR - fork/foo/test\n - Pagure</title>',
                output_text)
            self.assertIn('<p>Test Initial Comment</p>', output_text)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_fork_to_other_fork(self, send_email):
        """ Test creating a PR from fork to a fork of the same family. """
        send_email.return_value = True

        self.test_fork_project()

        # Create a 3rd user
        item = pagure.lib.model.User(
            user='ralph',
            fullname='Ralph bar',
            password='ralph_foo',
            default_email='ralph@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='ralph@bar.com')
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser()
        user.username = 'ralph'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()
            data = {
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/do_fork/test', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            # Check that Ralph's fork do exist
            output = self.app.get('/fork/ralph/test')
            self.assertEqual(output.status_code, 200)

            tests.create_projects_git(
                os.path.join(self.path, 'requests'), bare=True)

            # Turn on pull-request on the fork
            repo = pagure.lib.query.get_authorized_project(
                self.session, 'test', user='foo')
            settings = repo.settings
            settings['pull_requests'] = True
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            # Add some content to the parents
            self.set_up_git_repo(
                new_project=repo, branch_from='master', mtype='FF')
            self.set_up_git_repo(
                new_project=repo, branch_from='master', mtype='FF',
                name_from=repo.fullname, prid=2)

            fork = pagure.lib.query.get_authorized_project(
                self.session, 'test', user='ralph')

            self.set_up_git_repo(
                new_project=fork, branch_from='feature', mtype='FF',
                prid=3, name_from=fork.fullname)

            # Try opening a pull-request
            output = self.app.get(
                '/fork/ralph/test/diff/master..feature?project_to=fork/foo/test')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Create new Pull Request for master - fork/ralph/test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<input type="submit" class="btn btn-primary" value="Create Pull Request">\n',
                output_text)

            csrf_token = self.get_csrf(output=output)

            # Case 1 - Opening PR to fork/foo/test
            data = {
                'csrf_token': csrf_token,
                'title': 'foo bar PR',
                'initial_comment': 'Test Initial Comment',
            }

            output = self.app.post(
                '/fork/ralph/test/diff/master..feature?project_to=fork/foo/test',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: foo bar PR - fork/foo/test\n - Pagure</title>',
                output_text)
            self.assertIn('<p>Test Initial Comment</p>', output_text)

            # Case 1 - Opening PR to parent repo, shows project_to works
            output = self.app.post(
                '/fork/ralph/test/diff/master..feature',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#4: foo bar PR - test\n - Pagure</title>',
                output_text)
            self.assertIn('<p>Test Initial Comment</p>', output_text)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_fork_to_other_unrelated_fork(self, send_email):
        """ Test creating a PR from  fork to fork that isn't from the same
        family.
        """
        send_email.return_value = True

        self.test_fork_project()

        # Create a 3rd user
        item = pagure.lib.model.User(
            user='ralph',
            fullname='Ralph bar',
            password='ralph_foo',
            default_email='ralph@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='ralph@bar.com')
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser()
        user.username = 'ralph'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()
            data = {
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/do_fork/test2', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            # Check that Ralph's fork do exist
            output = self.app.get('/fork/ralph/test2')
            self.assertEqual(output.status_code, 200)

            tests.create_projects_git(
                os.path.join(self.path, 'requests'), bare=True)

            # Turn on pull-request on the fork
            repo = pagure.lib.query.get_authorized_project(
                self.session, 'test', user='foo')
            settings = repo.settings
            settings['pull_requests'] = True
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            # Add some content to the parent
            self.set_up_git_repo(
                new_project=repo, branch_from='master', mtype='FF',
                name_from=repo.fullname)

            fork = pagure.lib.query.get_authorized_project(
                self.session, 'test2', user='ralph')

            self.set_up_git_repo(
                new_project=fork, branch_from='feature', mtype='FF',
                prid=2, name_from=fork.fullname)

            # Case 1 - Opening PR to fork/foo/test
            data = {
                'csrf_token': csrf_token,
                'title': 'foo bar PR',
                'initial_comment': 'Test Initial Comment',
            }

            output = self.app.post(
                '/fork/ralph/test2/diff/master..feature?project_to=fork/foo/test',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 400)
            self.assertIn(
                "<p>fork/foo/test is not part of fork/ralph/test2's "
                "family</p>", output.get_data(as_text=True))

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_empty_repo(self, send_email):
        """ Test the new_request_pull endpoint against an empty repo. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        fork = pagure.lib.query.get_authorized_project(self.session, 'test', user='foo')

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        gitrepo = os.path.join(self.path, 'repos', 'forks', 'foo', 'test.git')
        new_repo = pygit2.clone_repository(gitrepo, newpath)

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(self.app.application, user):
            output = self.app.get(
                '/fork/foo/test/diff/master..feature',
                follow_redirects=True)
            self.assertEqual(output.status_code, 400)
            self.assertIn(
                '<p>Fork is empty, there are no commits to create a pull '
                'request with</p>', output.get_data(as_text=True))

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
                '<p>Fork is empty, there are no commits to create a pull '
                'request with</p>', output.get_data(as_text=True))

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull_empty_fork(self, send_email):
        """ Test the new_request_pull endpoint against an empty repo. """
        send_email.return_value = True

        self.test_fork_project()

        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        fork = pagure.lib.query.get_authorized_project(self.session, 'test', user='foo')

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
        with tests.user_set(self.app.application, user):
            output = self.app.get(
                '/fork/foo/test/diff/master..master', follow_redirects=True)
            self.assertEqual(output.status_code, 400)
            self.assertIn(
                '<p>Fork is empty, there are no commits to create a pull '
                'request with</p>', output.get_data(as_text=True))

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_pull_request_add_comment(self, send_email):
        """ Test the pull_request_add_comment endpoint. """
        send_email.return_value = True

        self.test_request_pull()

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.post('/foo/pull-request/1/comment')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/pull-request/100/comment')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/pull-request/1/comment')
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                output.get_data(as_text=True).startswith('\n<section class="add_comment">'))

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
                'comment': 'This look alright but we can do better',
            }
            output = self.app.post(
                '/test/pull-request/1/comment', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                'Comment added',
                output_text)
            self.assertEqual(output_text.count('title="PY C (pingou)"'), 2)

            # Project w/o pull-request
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
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
        repo = pagure.lib.query.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['pull_requests'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(self.app.application, user):
            output = self.app.post('/foo/pull-request/1/comment/drop')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/pull-request/100/comment/drop')
            self.assertEqual(output.status_code, 404)

            output = self.app.post(
                '/test/pull-request/1/comment/drop', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n', output_text)
            #self.assertIn('href="#comment-1">¶</a>', output_text)
            self.assertIn(
                '<p>This look alright but we can do better</p>',
                output_text)

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
        with tests.user_set(self.app.application, user):
            # Drop comment
            output = self.app.post(
                '/test/pull-request/1/comment/drop', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n',
                output_text)
            self.assertIn(
                'Comment removed',
                output_text)

            # Project w/o pull-request
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
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
        with tests.user_set(self.app.application, user):
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
                output.get_data(as_text=True).startswith('\n<section class="add_comment">'))

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
                'comment': 'This look alright but we can do better',
            }
            output = self.app.post(
                '/test/pull-request/1/comment', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n',
                output_text)
            self.assertIn(
                'Comment added',
                output_text)
            # Check if the comment is there
            self.assertIn(
                '<p>This look alright but we can do better</p>', output_text)
            output = self.app.get('/test/pull-request/1/comment/1/edit')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)

            self.assertIn('<section class="edit_comment">', output_text)
            # Checking if the comment is there in the update page
            self.assertIn(
                'This look alright but we can do better</textarea>', output_text)

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
                'update_comment': 'This look alright but we can do better than this.',
            }
            output = self.app.post(
                '/test/pull-request/1/comment/1/edit', data=data,
                follow_redirects=True)
            output_text = output.get_data(as_text=True)
            # Checking if the comment is updated in the main page
            self.assertIn(
                '<p>This look alright but we can do better than this.</p>', output_text)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n',
                output_text)
            # Checking if Edited by User is there or not
            self.assertTrue(
                '<small>Edited just now by pingou </small>'
                in output_text
                or
                '<small>Edited seconds ago by pingou </small>'
                in output_text)
            self.assertIn(
                'Comment updated', output_text)

            #  Project w/o pull-request
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
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
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            csrf_token = self.get_csrf(output=output)

            # No CSRF
            output = self.app.post(
                '/test/pull-request/1/merge', data={}, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>PR#1: PR from the feature branch - test\n - '
                'Pagure</title>', output_text)
            self.assertIn(
                '<h4 class="ml-1">\n        <div>\n              '
                '<span class="fa fa-fw text-success fa-arrow-circle-down pt-1"></span>\n              '
                '<span class="text-success '
                'font-weight-bold">#1</span>\n            '
                '<span class="font-weight-bold">\n                  '
                'PR from the feature branch\n', output_text)
            self.assertIn(
                'title="View file as of 2a552b">sources</a>', output_text)

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
        with tests.user_set(self.app.application, user):

            # Wrong request id
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/pull-request/100/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

            # Project requiring a merge commit
            repo = pagure.lib.query.get_authorized_project(self.session, 'test')
            settings = repo.settings
            settings['always_merge'] = True
            repo.settings = settings
            self.session.add(repo)
            self.session.commit()

            # Merge
            output = self.app.post(
                '/test/pull-request/1/merge', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)

            output = self.app.get('/test/commits')
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Commits - test - Pagure</title>', output_text)
            self.assertIn(
                'Merge #1 `PR from the feature branch`', output_text)
            self.assertIn(
                'A commit on branch feature', output_text)

            # Check if the closing notification was added
            output = self.app.get('/test/pull-request/1')
            self.assertIn(
                '<span class="text-info font-weight-bold">Merged</span> just now\n'
                '            </span>\n            by\n'
                '            <span title="PY C (pingou)">pingou.</span>\n',
                output.get_data(as_text=True))

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
        with tests.user_set(self.app.application, user):

            csrf_token = self.get_csrf()

            output = self.app.post(
                '/pv/pull-request/ready',
                data={'repo': 'test', 'csrf_token': csrf_token}
            )
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertEqual(sorted(data.keys()), ['code', 'task'])
            self.assertEqual(data['code'], 'OK')

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
        with tests.user_set(self.app.application, user):
            # Invalid request
            output = self.app.post('fork_edit/test/edit/master/f/source')
            self.assertEqual(output.status_code, 400)

            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.get_data(as_text=True))

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
        with tests.user_set(self.app.application, user):

            data = {
                'csrf_token': csrf_token,
            }

            # Invalid request
            output = self.app.post('fork_edit/test/edit/master/f/sources',
                            follow_redirects=True)
            self.assertEqual(output.status_code, 400)

            # Add content to the repo
            tests.add_content_git_repo(os.path.join(
                pagure.config.config['GIT_FOLDER'], 'test.git'))

            tests.add_readme_git_repo(os.path.join(
                pagure.config.config['GIT_FOLDER'], 'test.git'))

            tests.add_binary_git_repo(
                os.path.join(
                    pagure.config.config['GIT_FOLDER'], 'test.git'), 'test.jpg')

            # Check if button exists
            output = self.app.get('/test/blob/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'Fork and Edit\n                    </button>\n',
                output.get_data(as_text=True))

            # Check fork-edit doesn't show for binary files
            output = self.app.get('/test/blob/master/f/test.jpg')
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                'Fork and Edit\n                    </button>\n',
                output.get_data(as_text=True))

            # Check for edit panel
            output = self.app.post('fork_edit/test/edit/master/f/sources',
                            data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<li><a href="/fork/foo/test/tree/master">'
                '<span class="fa fa-random"></span>&nbsp; master</a>'
                '</li><li class="active"><span class="fa fa-file">'
                '</span>&nbsp; sources</li>',
                output_text)
            self.assertIn(
                '<textarea id="textareaCode" name="content">foo\n bar</textarea>',
                output_text)

             # Check for edit panel- Fork already done
            output = self.app.post('fork_edit/test/edit/master/f/sources',
                            data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Edit - test - Pagure</title>',
                output_text)
            self.assertIn(
                'You had already forked '
                'this project', output_text)
            self.assertIn(
                '<i class="fa fa-code-fork fa-fw"></i> View Upstream',
                output_text)
            self.assertIn(
                '<li><a href="/fork/foo/test/tree/master">'
                '<span class="fa fa-random"></span>&nbsp; master</a>'
                '</li><li class="active"><span class="fa fa-file">'
                '</span>&nbsp; sources</li>',
                output_text)
            self.assertIn(
                '<textarea id="textareaCode" name="content">foo\n bar</textarea>',
                output_text)

            # View what's supposed to be an image
            output = self.app.post('fork_edit/test/edit/master/f/test.jpg',
                        data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 400)
            self.assertIn('<p>Cannot edit binary files</p>', output.get_data(as_text=True))

        # Check fork-edit shows when user is not logged in
        output = self.app.get('/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'Fork and Edit\n                    </button>\n',
            output.get_data(as_text=True))

        # Check if fork-edit shows for different user
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):

            # Check if button exists
            output = self.app.get('/test/blob/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'Edit in your fork\n                    </button>\n',
                output.get_data(as_text=True))

            # Check fork-edit doesn't show for binary
            output = self.app.get('/test/blob/master/f/test.jpg')
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                'Edit in your fork\n                    </button>\n',
                output.get_data(as_text=True))

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_fork_edit_file_namespace(self):
        """ Test the fork_edit file endpoint on a namespaced project. """

        tests.create_projects(self.session)
        for folder in ['docs', 'tickets', 'requests', 'repos']:
            tests.create_projects_git(
                os.path.join(self.path, folder), bare=True)

        # User not logged in
        output = self.app.post(
            'fork_edit/somenamespace/test3/edit/master/f/sources')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            # Invalid request
            output = self.app.post(
                'fork_edit/somenamespace/test3/edit/master/f/sources')
            self.assertEqual(output.status_code, 400)

            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.get_data(as_text=True))

            csrf_token = self.get_csrf(output=output)

            data = {
                'csrf_token': csrf_token,
            }

            # No files can be found since they are not added
            output = self.app.post(
                'fork_edit/somenamespace/test3/edit/master/f/sources',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(self.app.application, user):

            data = {
                'csrf_token': csrf_token,
            }

            # Invalid request
            output = self.app.post(
                'fork_edit/somenamespace/test3/edit/master/f/sources',
                follow_redirects=True)
            self.assertEqual(output.status_code, 400)

            # Add content to the repo
            tests.add_content_git_repo(os.path.join(
                pagure.config.config['GIT_FOLDER'],
                'somenamespace', 'test3.git'))

            tests.add_readme_git_repo(os.path.join(
                pagure.config.config['GIT_FOLDER'],
                'somenamespace', 'test3.git'))

            tests.add_binary_git_repo(
                os.path.join(
                    pagure.config.config['GIT_FOLDER'],
                    'somenamespace', 'test3.git'), 'test.jpg')

            # Check if button exists
            output = self.app.get('/somenamespace/test3/blob/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'Fork and Edit\n                    </button>\n',
                output.get_data(as_text=True))

            # Check fork-edit doesn't show for binary files
            output = self.app.get('/somenamespace/test3/blob/master/f/test.jpg')
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                'Fork and Edit\n                    </button>\n',
                output.get_data(as_text=True))

            # Check for edit panel
            output = self.app.post(
                'fork_edit/somenamespace/test3/edit/master/f/sources',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Edit - somenamespace/test3 - Pagure</title>',
                output_text)
            self.assertIn(
                '<i class="fa fa-code-fork fa-fw"></i> View Upstream',
                output_text)
            self.assertIn(
                '<li><a href="/fork/foo/somenamespace/test3/tree/master">'
                '<span class="fa fa-random"></span>&nbsp; master</a>'
                '</li><li class="active"><span class="fa fa-file">'
                '</span>&nbsp; sources</li>',
                output_text)
            self.assertIn(
                '<textarea id="textareaCode" name="content">foo\n bar</textarea>',
                output_text)

            # Check for edit panel - while the project was already forked
            output = self.app.post(
                'fork_edit/somenamespace/test3/edit/master/f/sources',
                data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<title>Edit - somenamespace/test3 - Pagure</title>',
                output_text)
            self.assertIn(
                'You had already forked '
                'this project', output_text)
            self.assertIn(
                '<i class="fa fa-code-fork fa-fw"></i> View Upstream',
                output_text)
            self.assertIn(
                '<li><a href="/fork/foo/somenamespace/test3/tree/master">'
                '<span class="fa fa-random"></span>&nbsp; master</a>'
                '</li><li class="active"><span class="fa fa-file">'
                '</span>&nbsp; sources</li>',
                output_text)
            self.assertIn(
                '<textarea id="textareaCode" name="content">foo\n bar</textarea>',
                output_text)

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
        project = pagure.lib.query._get_project(self.session, 'test', 'foo')

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
        self.assertIn('Forked from a deleted repository', output.get_data(as_text=True))

        # Testing commit endpoint
        output = self.app.get('/fork/foo/test/commits/master')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'Commits <span class="badge badge-secondary"> 2</span>\n',
            output.get_data(as_text=True))

        # Test pull-request endpoint
        output = self.app.get('/fork/foo/test/pull-requests')
        self.assertEqual(output.status_code, 404)

        # Test issue-tracker endpoint
        output = self.app.get('/fork/foo/test/issues')
        self.assertEqual(output.status_code, 404)

        shutil.rmtree(newpath)

    def _set_up_for_reaction_test(self):
        self.session.add(pagure.lib.model.User(
            user='jdoe',
            fullname='John Doe',
            password=b'password',
            default_email='jdoe@example.com',
        ))
        self.session.commit()
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)
        self.set_up_git_repo(new_project=None, branch_from='feature')
        pagure.lib.query.get_authorized_project(self.session, 'test')
        request = pagure.lib.query.search_pull_requests(
            self.session, requestid=1, project_id=1,
        )
        pagure.lib.query.add_pull_request_comment(
            self.session,
            request=request,
            commit=None,
            tree_id=None,
            filename=None,
            row=None,
            comment='Hello',
            user='jdoe',
        )
        self.session.commit()

    @patch('pagure.lib.notify.send_email')
    def test_add_reaction(self, send_email):
        """ Test the request_pull endpoint. """
        send_email.return_value = True

        self._set_up_for_reaction_test()

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)

            data = {
                'csrf_token': self.get_csrf(output=output),
                'reaction': 'Thumbs up',
            }

            output = self.app.post(
                '/test/pull-request/1/comment/1/react',
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)

            # Load the page and check reaction is added.
            output = self.app.get('/test/pull-request/1')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'Thumbs up sent by pingou',
                output.get_data(as_text=True)
            )

    @patch('pagure.lib.notify.send_email')
    def test_add_reaction_unauthenticated(self, send_email):
        """ Test the request_pull endpoint. """
        send_email.return_value = True

        self._set_up_for_reaction_test()

        output = self.app.get('/test/pull-request/1')
        self.assertEqual(output.status_code, 200)

        data = {
            'csrf_token': self.get_csrf(output=output),
            'reaction': 'Thumbs down',
        }

        output = self.app.post(
            '/test/pull-request/1/comment/1/react',
            data=data,
            follow_redirects=False,
        )
        # Redirect to login page
        self.assertEqual(output.status_code, 302)
        self.assertIn('/login/', output.headers['Location'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
