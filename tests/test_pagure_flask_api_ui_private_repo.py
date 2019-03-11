# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import datetime
import unittest
import shutil
import sys
import tempfile
import os

import json
import pygit2
from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib.query
import tests
from pagure.lib.repo import PagureRepo

FULL_ISSUE_LIST = [
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "We should work on this",
        "custom_fields": [],
        "date_created": "1431414800",
        "depends": [],
        "id": 8,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": True,
        "status": "Open",
        "tags": [],
        "title": "Test issue",
        "user": {
            "fullname": "PY C",
            "name": "pingou"
        }
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "date_created": "1431414800",
        "depends": [],
        "id": 7,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": True,
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "name": "pingou"
        }
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "date_created": "1431414800",
        "depends": [],
        "id": 6,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": True,
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "name": "pingou"
        }
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "date_created": "1431414800",
        "depends": [],
        "id": 5,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": False,
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "name": "pingou"
        }
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "date_created": "1431414800",
        "depends": [],
        "id": 4,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": False,
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "name": "pingou"
        }
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "date_created": "1431414800",
        "depends": [],
        "id": 3,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": False,
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "name": "pingou"
        }
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "date_created": "1431414800",
        "depends": [],
        "id": 2,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": False,
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "name": "pingou"
        }
    },
    {
        "assignee": None,
        "blocks": [],
        "close_status": None,
        "closed_at": None,
        "closed_by": None,
        "comments": [],
        "content": "This issue needs attention",
        "custom_fields": [],
        "date_created": "1431414800",
        "depends": [],
        "id": 1,
        "last_updated": "1431414800",
        "milestone": None,
        "priority": None,
        "private": False,
        "status": "Open",
        "tags": [],
        "title": "test issue",
        "user": {
            "fullname": "PY C",
            "name": "pingou"
        }
    }
]


class PagurePrivateRepotest(tests.Modeltests):
    """ Tests for private repo in pagure """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagurePrivateRepotest, self).setUp()

        pagure.config.config['TESTING'] = True
        pagure.config.config['DATAGREPPER_URL'] = None
        pagure.config.config['PRIVATE_PROJECTS'] = True
        pagure.config.config['VIRUS_SCAN_ATTACHMENTS'] = False

    def set_up_git_repo(
            self, new_project=None, branch_from='feature', mtype='FF'):
        """ Set up the git repo and create the corresponding PullRequest
        object.
        """

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'pmc.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        newpath = tempfile.mkdtemp(prefix='pagure-private-test')
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
        project = pagure.lib.query._get_project(self.session, 'pmc')
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
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the %s branch' % branch_from)

        shutil.rmtree(newpath)

    def test_index(self):
        """ Test the index endpoint. """

        output = self.app.get('/')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h3 class="m-0 font-weight-bold">All Projects '
            '<span class="badge badge-secondary">0</span></h3>',
            output.get_data(as_text=True))

        # Add a private project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project description',
            hook_token='aaabbbeee',
            private=True,
        )

        self.session.add(item)

        # Add a public project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeccceee',
        )

        self.session.add(item)
        self.session.commit()

        output = self.app.get('/?page=abc')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<h3 class="m-0 font-weight-bold">All Projects '
            '<span class="badge badge-secondary">1</span></h3>',
            output_text)

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/', follow_redirects=True)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>',
                output_text)
            self.assertIn('2 Projects</span>', output_text)
            self.assertNotIn(
                '<span class="d-none d-md-inline">Forks', output_text)
            self.assertEqual(
                output_text.count('<span class="d-none d-md-inline">Groups'), 0)


    def test_view_user(self):
        """ Test the view_user endpoint. """

        output = self.app.get('/user/foo?repopage=abc&forkpage=def')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""", output_text)
        self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""", output_text)
        self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-users"></i>
                <span class="d-none d-md-inline">Groups&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""", output_text)

        # Add a private project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project description',
            hook_token='aaabbbeee',
            private=True,
        )

        self.session.add(item)

        # Add a public project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeccceee',
        )

        self.session.add(item)
        self.session.commit()

        self.gitrepos = tests.create_projects_git(
            pagure.config.config['GIT_FOLDER'])

        output = self.app.get('/user/foo')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  1
                </span>
              </div>""", output_text)
        self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""", output_text)
        self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-users"></i>
                <span class="d-none d-md-inline">Groups&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""", output_text)

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/user/foo')
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  1
                </span>
              </div>""", output_text)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""", output_text)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-users"></i>
                <span class="d-none d-md-inline">Groups&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""", output_text)

        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/user/foo')
            output_text = output.get_data(as_text=True)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  1
                </span>
              </div>""", output_text)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""", output_text)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-users"></i>
                <span class="d-none d-md-inline">Groups&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""", output_text)

        # Check pingou has 0 projects
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/', follow_redirects=True)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>',
                output_text)
            self.assertIn(
                '0 Projects</span>',
                output_text)
            self.assertNotIn(
                '<span class="d-none d-md-inline">Forks',
                output_text)
            self.assertEqual(
                output_text.count('<span class="d-none d-md-inline">Groups'), 0)

        repo = pagure.lib.query._get_project(self.session, 'test3')

        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='pingou',
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # New user added to private projects
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/', follow_redirects=True)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<h4 class="font-weight-bold mb-0">My Projects</h4>',
                output_text)
            self.assertIn(
                '1 Projects</span>',
                output_text)
            self.assertNotIn(
                '<span class="d-none d-md-inline">Forks',
                output_text)
            self.assertEqual(
                output_text.count('<span class="d-none d-md-inline">Groups'), 0)

    @patch('pagure.decorators.admin_session_timedout')
    def test_private_settings_ui(self, ast):
        """ Test UI for private repo"""
        ast.return_value = False

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        # Add a git repo
        repo_path = os.path.join(
            pagure.config.config.get('GIT_FOLDER'), 'test4.git')
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
        pygit2.init_repository(repo_path)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            tests.create_projects(self.session)
            tests.create_projects_git(pagure.config.config.get('GIT_FOLDER'))

            output = self.app.get('/test/settings')

            # Check for a public repo
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                '<input type="checkbox" value="private" name="private"',
                output.get_data(as_text=True))

            output = self.app.get('/test4/settings')

            # Check for private repo
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<input type="checkbox" value="private" name="private" checked="" />',
                output.get_data(as_text=True))

            # Check the new project form has 'private' checkbox
            output = self.app.get('/new')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<input id="private" name="private" type="checkbox" value="y">',
                output.get_data(as_text=True))

    @patch('pagure.decorators.admin_session_timedout')
    def test_private_settings_ui_update_privacy_false(self, ast):
        """ Test UI for private repo"""
        ast.return_value = False

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        # Add a git repo
        repo_path = os.path.join(
            pagure.config.config.get('GIT_FOLDER'), 'test4.git')
        pygit2.init_repository(repo_path)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):

            # Check for private repo
            output = self.app.get('/test4/settings')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<input type="checkbox" value="private" name="private" checked="" />',
                output.get_data(as_text=True))

            self.session.commit()
            repo = pagure.lib.query._get_project(self.session, 'test4')
            self.assertTrue(repo.private)

            # Make the project public
            data = {
                'description': 'test project description',
                'private': False,
                'csrf_token': self.get_csrf(),
            }
            output = self.app.post(
                '/test4/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'Project updated',
                output.get_data(as_text=True))
            self.assertNotIn(
                '<input type="checkbox" value="private" name="private" checked="" />',
                output.get_data(as_text=True))

            self.session.commit()
            repo = pagure.lib.query._get_project(self.session, 'test4')
            self.assertFalse(repo.private)

    @patch('pagure.decorators.admin_session_timedout')
    def test_private_settings_ui_update_privacy_true(self, ast):
        """ Test UI for private repo"""
        ast.return_value = False

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=False,
        )
        self.session.add(item)
        self.session.commit()

        # Add a git repo
        repo_path = os.path.join(
            pagure.config.config.get('GIT_FOLDER'), 'test4.git')
        pygit2.init_repository(repo_path)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):

            # Check for public repo
            output = self.app.get('/test4/settings')
            self.assertEqual(output.status_code, 200)
            self.assertNotIn(
                '<input type="checkbox" value="private" name="private" checked=""/>',
                output.get_data(as_text=True))

            self.session.commit()
            repo = pagure.lib.query._get_project(self.session, 'test4')
            self.assertFalse(repo.private)

            # Make the project private
            data = {
                'description': 'test project description',
                'private': True,
                'csrf_token': self.get_csrf(),
            }
            output = self.app.post(
                '/test4/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                'Project updated',
                output.get_data(as_text=True))
            self.assertNotIn(
                '<input type="checkbox" value="private" name="private" checked=""/>',
                output.get_data(as_text=True))

            # No change since we can't do public -> private
            self.session.commit()
            repo = pagure.lib.query._get_project(self.session, 'test4')
            self.assertFalse(repo.private)

    @patch('pagure.lib.notify.send_email')
    def test_private_pr(self, send_email):
        """Test pull request made to the private repo"""

        send_email.return_value = True
        # Add a private project
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='pmc',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )

        self.session.add(item)
        self.session.commit()

        repo = pagure.lib.query._get_project(self.session, 'pmc')

        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # Create all the git repos
        tests.create_projects_git(
            os.path.join(self.path, 'requests'), bare=True)

        # Add a git repo
        repo_path = os.path.join(
            pagure.config.config.get('REQUESTS_FOLDER'), 'pmc.git')
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
        pygit2.init_repository(repo_path, bare=True)
        # Check repo was created - Doesn't show on the public page
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/user/pingou/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-calendar-o fa-rotate-270"></i>
                <span class="d-none d-md-inline">Projects&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""", output.get_data(as_text=True))
            self.assertIn(
                """<span>
                <i class="fa fa-fw text-muted fa-code-fork"></i>
                <span class="d-none d-md-inline">Forks&nbsp;</span>
              </span>
              <div class="ml-auto">
                <span class="badge badge-secondary">
                  0
                </span>
              </div>""", output.get_data(as_text=True))

            # Shows on the front page
            output = self.app.get('/dashboard/projects')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                """<span>
              <i class="fa fa-calendar-o fa-rotate-270 fa-fw text-muted"></i>
              <span class="d-none d-md-inline">Projects&nbsp;</span>
            </span>
            <div class="ml-auto">
              <span class="badge badge-secondary">
                1
              </span>
            </div>""", output.get_data(as_text=True))

            self.set_up_git_repo(new_project=None, branch_from='feature')
            project = pagure.lib.query._get_project(self.session, 'pmc')
            self.assertEqual(len(project.requests), 1)

            output = self.app.get('/pmc/pull-request/1')
            self.assertEqual(output.status_code, 200)

        # Check repo was created
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/pmc/pull-requests')
            self.assertEqual(output.status_code, 404)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/pmc/pull-requests')
            self.assertEqual(output.status_code, 200)

        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/pmc/pull-requests')
            self.assertEqual(output.status_code, 200)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_private_repo_issues_ui(self, p_send_email, p_ugt):
        """ Test issues made to private repo"""
        p_send_email.return_value = True
        p_ugt.return_value = True

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        for repo in ['GIT_FOLDER', 'TICKETS_FOLDER']:
            # Add a git repo
            repo_path = os.path.join(
                pagure.config.config.get(repo), 'test4.git')
            if not os.path.exists(repo_path):
                os.makedirs(repo_path)
            pygit2.init_repository(repo_path)

        # Check if the private repo issues are publicly not accesible
        output = self.app.get('/test4/issues')
        self.assertEqual(output.status_code, 404)

        # Create issues to play with
        repo = pagure.lib.query._get_project(self.session, 'test4')
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):

            # Whole list
            output = self.app.get('/test4/issues')
            self.assertEqual(output.status_code, 404)

            # Check single issue
            output = self.app.get('/test4/issue/1')
            self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):

            # Whole list
            output = self.app.get('/test4/issues')
            self.assertEqual(output.status_code, 404)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):

            # Whole list
            output = self.app.get('/test4/issues')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issues - test4 - Pagure</title>', output.get_data(as_text=True))
            self.assertTrue(
                '<span class="fa fa-fw fa-exclamation-circle"></span> 1 Open Issues\n' in output.get_data(as_text=True))

            # Check single issue
            output = self.app.get('/test4/issue/1')
            self.assertEqual(output.status_code, 200)

        repo = pagure.lib.query._get_project(self.session, 'test4')

        msg = pagure.lib.query.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        user.username = 'foo'
        with tests.user_set(self.app.application, user):

            # Whole list
            output = self.app.get('/test4/issues')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Issues - test4 - Pagure</title>', output.get_data(as_text=True))
            self.assertTrue(
                '<span class="fa fa-fw fa-exclamation-circle"></span> 1 Open Issues\n' in output.get_data(as_text=True))

            # Check single issue
            output = self.app.get('/test4/issue/1')
            self.assertEqual(output.status_code, 200)

    @patch('pagure.decorators.admin_session_timedout')
    def test_private_repo_ui_for_different_repo_user(self, ast):
        """ Test the private repo for different ACLS"""
        ast.return_value = False

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        repo = pagure.lib.query._get_project(self.session, "test4")
        # Add a git repo
        repo_path = os.path.join(
            pagure.config.config.get('GIT_FOLDER'), 'test4.git')
        pygit2.init_repository(repo_path)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):

            # Check for private repo
            output = self.app.get('/test4')
            self.assertEqual(output.status_code, 200)

        # Check if the user who doesn't have access to private repo can access it
        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):

            output = self.app.get('/test4')
            self.assertEqual(output.status_code, 404)

        # Add commit access to a user
        pagure.lib.query.add_user_to_project(
            self.session,
            project=repo,
            new_user="foo",
            user="pingou",
            access='commit'
        )
        self.session.commit()


        repo = pagure.lib.query._get_project(self.session, "test4")
        self.assertEqual(len(repo.users), 1)

        # Check if the user can access private repo
        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):

            output = self.app.get('/test4')
            self.assertEqual(output.status_code, 200)

        # Making a new user bar
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar baz',
            password='foo',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)

        self.session.commit()

        # Check that bar shouldn't be able to access the project
        user = tests.FakeUser(username="bar")
        with tests.user_set(self.app.application, user):

            output = self.app.get('/test4')
            self.assertEqual(output.status_code, 404)

        # Adding a ticket level access to bar
        pagure.lib.query.add_user_to_project(
            self.session,
            project=repo,
            new_user="bar",
            user="pingou",
            access='ticket'
        )
        self.session.commit()

        repo = pagure.lib.query._get_project(self.session, "test4")
        self.assertEqual(len(repo.users), 2)

        # Check if the ticket level access user can access the project
        user = tests.FakeUser(username="bar")
        with tests.user_set(self.app.application, user):

            output = self.app.get('/test4')
            self.assertEqual(output.status_code, 200)

    # API checks
    def test_api_private_repo_projects(self):
        """ Test api points for private repo for projects"""

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test4.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        repopath = os.path.join(newpath, 'repos', 'test4')
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

        # Tag our first commit
        first_commit = repo.revparse_single('HEAD')
        tagger = pygit2.Signature('Alice Doe', 'adoe@example.com', 12347, 0)
        repo.create_tag(
            "0.0.1", first_commit.oid.hex, pygit2.GIT_OBJ_COMMIT, tagger,
            "Release 0.0.1")

        # Create a token for foo for this project
        item = pagure.lib.model.Token(
            id='foobar_token',
            user_id=1,
            project_id=1,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)
        self.session.commit()
        item = pagure.lib.model.TokenAcl(
            token_id='foobar_token',
            acl_id=1,
        )
        self.session.add(item)
        self.session.commit()

        # Check if the admin requests
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            # Check tags
            output = self.app.get('/api/0/test4/git/tags')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(
                data,
                {'tags': ['0.0.1'], 'total_tags': 1}
            )

        output = self.app.get('/api/0/test4/git/tags')
        self.assertEqual(output.status_code, 404)

        # Chekc if user is not admin
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/api/0/test4/git/tags')
            self.assertEqual(output.status_code, 404)

        shutil.rmtree(newpath)

        # Check before adding
        repo = pagure.lib.query._get_project(self.session, 'test4')
        self.assertEqual(repo.tags, [])

        # Adding a tag
        output = pagure.lib.query.update_tags(
            self.session, repo, 'infra', 'pingou')
        self.assertEqual(output, ['Project tagged with: infra'])

        # Check after adding
        repo = pagure.lib.query._get_project(self.session, 'test4')
        self.assertEqual(len(repo.tags), 1)
        self.assertEqual(repo.tags_text, ['infra'])

        # Check the API
        output = self.app.get('/api/0/projects?tags=inf')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        del data['pagination']
        self.assertDictEqual(
            data,
            {
                'args': {
                    'fork': None,
                    'namespace': None,
                    'owner': None,
                    'page': 1,
                    'pattern': None,
                    'per_page': 20,
                    'short': False,
                    'tags': ['inf'],
                    'username': None
                },
                'projects': [],
                'total_projects': 0
            }
        )

        # Request by not a loggged in user
        output = self.app.get('/api/0/projects?tags=infra')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        del data['pagination']
        self.assertDictEqual(
            data,
            {
                'args': {
                    'fork': None,
                    'namespace': None,
                    'owner': None,
                    'page': 1,
                    'pattern': None,
                    'per_page': 20,
                    'short': False,
                    'tags': ['infra'],
                    'username': None
                },
                'projects': [],
                'total_projects': 0
            }
        )

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            # Request by a non authorized user
            output = self.app.get('/api/0/projects?tags=infra')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            del data['pagination']
            self.assertDictEqual(
                data,
                {
                    'args': {
                        'fork': None,
                        'namespace': None,
                        'owner': None,
                        'page': 1,
                        'pattern': None,
                        'per_page': 20,
                        'short': False,
                        'tags': ['infra'],
                        'username': None
                    },
                    'projects': [],
                    'total_projects': 0
                }
            )

        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            # Private repo username is compulsion to pass
            output = self.app.get('/api/0/projects?tags=infra')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            del data['pagination']
            self.assertDictEqual(
                data,
                {
                    'args': {
                        'fork': None,
                        'namespace': None,
                        'owner': None,
                        'page': 1,
                        'pattern': None,
                        'per_page': 20,
                        'short': False,
                        'tags': ['infra'],
                        'username': None
                    },
                    'projects': [],
                    'total_projects': 0
                }
            )

            output = self.app.get('/api/0/projects?username=pingou')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            data['projects'][0]['date_created'] = "1436527638"
            data['projects'][0]['date_modified'] = "1436527638"
            del data['pagination']
            self.assertDictEqual(
                data,
                {
                    "args": {
                        "fork": None,
                        "namespace": None,
                        "owner": None,
                        "page": 1,
                        "pattern": None,
                        "per_page": 20,
                        "short": False,
                        "tags": [],
                        "username": "pingou"
                    },
                    "total_projects": 1,
                    "projects": [
                        {
                            "access_groups": {
                                "admin": [],
                                "commit": [],
                                "ticket": []
                            },
                            "access_users": {
                                "admin": [],
                                "commit": [],
                                "owner": [
                                    "pingou"
                                ],
                                "ticket": []
                            },
                            "close_status": [],
                            "custom_keys": [],
                            "date_created": "1436527638",
                            "date_modified": "1436527638",
                            "description": "test project description",
                            "id": 1,
                            "milestones": {},
                            "name": "test4",
                            "fullname": "test4",
                            "url_path": "test4",
                            "namespace": None,
                            "parent": None,
                            "priorities": {},
                            "tags": ["infra"],
                            "user": {
                                "fullname": "PY C",
                                "name": "pingou"
                            }
                        },
                    ]
                }
            )

            output = self.app.get('/api/0/projects?username=pingou&tags=infra')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            data['projects'][0]['date_created'] = "1436527638"
            data['projects'][0]['date_modified'] = "1436527638"
            del data['pagination']
            self.assertDictEqual(
                data,
                {
                    "args": {
                        "fork": None,
                        "namespace": None,
                        "owner": None,
                        "page": 1,
                        "pattern": None,
                        "per_page": 20,
                        "short": False,
                        "tags": ["infra"],
                        "username": "pingou"
                    },
                    "total_projects": 1,
                    "projects": [
                        {
                            "access_groups": {
                                "admin": [],
                                "commit": [],
                                "ticket": []
                            },
                            "access_users": {
                                "admin": [],
                                "commit": [],
                                "owner": [
                                    "pingou"
                                ],
                                "ticket": []
                            },
                            "close_status": [],
                            "custom_keys": [],
                            "date_created": "1436527638",
                            "date_modified": "1436527638",
                            "description": "test project description",
                            "id": 1,
                            "milestones": {},
                            "name": "test4",
                            "fullname": "test4",
                            "url_path": "test4",
                            "namespace": None,
                            "parent": None,
                            "priorities": {},
                            "tags": ["infra"],
                            "user": {
                                "fullname": "PY C",
                                "name": "pingou"
                            }
                        }
                    ]
                }

            )

    # Api pull-request views
    @patch('pagure.lib.notify.send_email')
    def test_api_private_repo_fork(self, send_email):
        """ Test api endpoints in api/fork"""

        send_email.return_value = True

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}
        # Create a pull-request
        repo = pagure.lib.query._get_project(self.session, 'test4')
        forked_repo = pagure.lib.query._get_project(self.session, 'test4')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Check list of PR
        output = self.app.get('/api/0/test4/pull-requests')
        self.assertEqual(output.status_code, 404)

        # Check single PR
        output = self.app.get('/api/0/test/pull-request/1')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            # List pull-requests
            output = self.app.get('/api/0/test4/pull-requests')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            data['requests'][0]['date_created'] = '1431414800'
            data['requests'][0]['updated_on'] = '1431414800'
            data['requests'][0]['project']['date_created'] = '1431414800'
            data['requests'][0]['project']['date_modified'] = '1431414800'
            data['requests'][0]['repo_from']['date_created'] = '1431414800'
            data['requests'][0]['repo_from']['date_modified'] = '1431414800'
            data['requests'][0]['uid'] = '1431414800'
            data['requests'][0]['last_updated'] = '1431414800'
            for k in ['first', 'last']:
                self.assertIsNotNone(data['pagination'][k])
                data['pagination'][k] = 'http://localhost...'
            self.assertDictEqual(
                data,
                {
                    "args": {
                        "assignee": None,
                        "author": None,
                        "page": 1,
                        "per_page": 20,
                        "status": True
                    },
                    "pagination": {
                        "first": 'http://localhost...',
                        "last": 'http://localhost...',
                        "next": None,
                        "page": 1,
                        "pages": 1,
                        "per_page": 20,
                        "prev": None
                    },
                    "requests": [
                        {
                            "assignee": None,
                            "branch": "master",
                            "branch_from": "master",
                            "cached_merge_status": "unknown",
                            "closed_at": None,
                            "closed_by": None,
                            "comments": [],
                            "commit_start": None,
                            "commit_stop": None,
                            "date_created": "1431414800",
                            "last_updated": "1431414800",
                            "id": 1,
                            "initial_comment": None,
                            "project": {
                                "access_groups": {
                                    "admin": [],
                                    "commit": [],
                                    "ticket": []
                                },
                                "access_users": {
                                    "admin": [],
                                    "commit": [],
                                    "owner": [
                                        "pingou"
                                    ],
                                    "ticket": []
                                },
                                "close_status": [],
                                "custom_keys": [],
                                "date_created": "1431414800",
                                "date_modified": "1431414800",
                                "description": "test project description",
                                "id": 1,
                                "milestones": {},
                                "name": "test4",
                                "fullname": "test4",
                                "url_path": "test4",
                                "namespace": None,
                                "parent": None,
                                "priorities": {},
                                "tags": [],
                                "user": {
                                    "fullname": "PY C",
                                    "name": "pingou"
                                }
                            },
                            "remote_git": None,
                            "repo_from": {
                                "access_groups": {
                                    "admin": [],
                                    "commit": [],
                                    "ticket": []
                                },
                                "access_users": {
                                    "admin": [],
                                    "commit": [],
                                    "owner": [
                                        "pingou"
                                    ],
                                    "ticket": []
                                },
                                "close_status": [],
                                "custom_keys": [],
                                "date_created": "1431414800",
                                "date_modified": "1431414800",
                                "description": "test project description",
                                "id": 1,
                                "milestones": {},
                                "fullname": "test4",
                                "url_path": "test4",
                                "name": "test4",
                                "namespace": None,
                                "parent": None,
                                "priorities": {},
                                "tags": [],
                                "user": {
                                    "fullname": "PY C",
                                    "name": "pingou"
                                }
                            },
                            "status": "Open",
                            "tags": [],
                            "threshold_reached": None,
                            "title": "test pull-request",
                            "uid": "1431414800",
                            "updated_on": "1431414800",
                            "user": {
                                "fullname": "PY C",
                                "name": "pingou"
                            }
                        }
                    ],
                    "total_requests": 1
                }
            )
            headers = {'Authorization': 'token foobar_token'}

            # Access Pull-Request authenticated
            output = self.app.get(
                '/api/0/test4/pull-requests', headers=headers)
            self.assertEqual(output.status_code, 200)
            data2 = json.loads(output.get_data(as_text=True))
            data2['requests'][0]['date_created'] = '1431414800'
            data2['requests'][0]['updated_on'] = '1431414800'
            data2['requests'][0]['project']['date_created'] = '1431414800'
            data2['requests'][0]['project']['date_modified'] = '1431414800'
            data2['requests'][0]['repo_from']['date_created'] = '1431414800'
            data2['requests'][0]['repo_from']['date_modified'] = '1431414800'
            data2['requests'][0]['uid'] = '1431414800'
            data2['requests'][0]['last_updated'] = '1431414800'
            for k in ['first', 'last']:
                self.assertIsNotNone(data['pagination'][k])
                data2['pagination'][k] = 'http://localhost...'

            self.assertDictEqual(data, data2)

            # For single PR
            output = self.app.get('/api/0/test4/pull-request/1')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            data['date_created'] = '1431414800'
            data['updated_on'] = '1431414800'
            data['project']['date_created'] = '1431414800'
            data['project']['date_modified'] = '1431414800'
            data['repo_from']['date_created'] = '1431414800'
            data['repo_from']['date_modified'] = '1431414800'
            data['uid'] = '1431414800'
            data['last_updated'] = '1431414800'
            self.assertDictEqual(
                data,
                {
                    "assignee": None,
                    "branch": "master",
                    "branch_from": "master",
                    "cached_merge_status": "unknown",
                    "closed_at": None,
                    "closed_by": None,
                    "comments": [],
                    "commit_start": None,
                    "commit_stop": None,
                    "date_created": "1431414800",
                    "last_updated": "1431414800",
                    "id": 1,
                    "initial_comment": None,
                    "project": {
                        "access_groups": {
                            "admin": [],
                            "commit": [],
                            "ticket": []
                        },
                        "access_users": {
                            "admin": [],
                            "commit": [],
                            "owner": [
                                "pingou"
                            ],
                            "ticket": []
                        },
                        "close_status": [],
                        "custom_keys": [],
                        "date_created": "1431414800",
                        "date_modified": "1431414800",
                        "description": "test project description",
                        "id": 1,
                        "milestones": {},
                        "name": "test4",
                        "fullname": "test4",
                        "url_path": "test4",
                        "namespace": None,
                        "parent": None,
                        "priorities": {},
                        "tags": [],
                        "user": {
                            "fullname": "PY C",
                            "name": "pingou"
                        }
                    },
                    "remote_git": None,
                    "repo_from": {
                         "access_groups": {
                            "admin": [],
                            "commit": [],
                            "ticket": []
                        },
                        "access_users": {
                            "admin": [],
                            "commit": [],
                            "owner": [
                                "pingou"
                            ],
                            "ticket": []
                        },
                        "close_status": [],
                        "custom_keys": [],
                        "date_created": "1431414800",
                        "date_modified": "1431414800",
                        "description": "test project description",
                        "id": 1,
                        "milestones": {},
                        "name": "test4",
                        "fullname": "test4",
                        "url_path": "test4",
                        "namespace": None,
                        "parent": None,
                        "priorities": {},
                        "tags": [],
                        "user": {
                            "fullname": "PY C",
                            "name": "pingou"
                        }
                    },
                    "status": "Open",
                    "tags": [],
                    "threshold_reached": None,
                    "title": "test pull-request",
                    "uid": "1431414800",
                    "updated_on": "1431414800",
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou"
                    },
                }

            )

            # Access Pull-Request authenticated
            output = self.app.get(
                '/api/0/test4/pull-request/1', headers=headers)
            self.assertEqual(output.status_code, 200)
            data2 = json.loads(output.get_data(as_text=True))
            data2['date_created'] = '1431414800'
            data2['project']['date_created'] = '1431414800'
            data2['project']['date_modified'] = '1431414800'
            data2['repo_from']['date_created'] = '1431414800'
            data2['repo_from']['date_modified'] = '1431414800'
            data2['uid'] = '1431414800'
            data2['date_created'] = '1431414800'
            data2['updated_on'] = '1431414800'
            data2['last_updated'] = '1431414800'
            self.assertDictEqual(data, data2)

    @patch('pagure.lib.notify.send_email')
    def test_api_pr_private_repo_add_comment(self, mockemail):
        """ Test the api_pull_request_add_comment method of the flask api. """
        mockemail.return_value = True
        pagure.config.config['REQUESTS_FOLDER'] = None

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}
        # Create a pull-request
        repo = pagure.lib.query._get_project(self.session, 'test4')
        forked_repo = pagure.lib.query._get_project(self.session, 'test4')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Check comments before
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 0)

        data = {
            'title': 'test issue',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test4/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"comment": ["This field is required."]}
            }
        )

        # No change
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 0)

        data = {
            'comment': 'This is a very interesting question',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test4/pull-request/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'message': 'Comment added'}
        )

        # One comment added
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.comments), 1)

    @patch('pagure.lib.notify.send_email')
    def test_api_private_repo_pr_add_flag(self, mockemail):
        """ Test the api_pull_request_add_flag method of the flask api. """
        mockemail.return_value = True
        pagure.config.config['REQUESTS_FOLDER'] = None

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test2',
            description='test project description',
            hook_token='foo_bar',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

        # Valid token, wrong project
        output = self.app.post(
            '/api/0/test2/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ['error', 'error_code'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.value, data['error'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data['error_code'])

        # No input
        output = self.app.post(
            '/api/0/test4/pull-request/1/flag', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Pull-Request not found",
                "error_code": "ENOREQ",
            }
        )

        # Create a pull-request
        repo = pagure.lib.query._get_project(self.session, 'test4')
        forked_repo = pagure.lib.query._get_project(self.session, 'test4')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        # Check comments before
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 0)

        data = {
            'username': 'Jenkins',
            'percent': 100,
            'url': 'http://jenkins.cloud.fedoraproject.org/',
            'uid': 'jenkins_build_pagure_100+seed',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test4/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"comment": ["This field is required."]}
            }
        )

        # No change
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 0)

        data = {
            'username': 'Jenkins',
            'percent': 0,
            'comment': 'Tests failed',
            'url': 'http://jenkins.cloud.fedoraproject.org/',
            'uid': 'jenkins_build_pagure_100+seed',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test4/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['flag']['date_created'] = '1510742565'
        data['flag']['date_updated'] = '1510742565'
        data['flag']['pull_request_uid'] = '62b49f00d489452994de5010565fab81'
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                'flag': {
                    'comment': 'Tests failed',
                    'date_created': '1510742565',
                    'date_updated': '1510742565',
                    'percent': 0,
                    'pull_request_uid': '62b49f00d489452994de5010565fab81',
                    'status': 'failure',
                    'url': 'http://jenkins.cloud.fedoraproject.org/',
                    'user': {
                        'default_email': 'bar@pingou.com',
                        'emails': ['bar@pingou.com', 'foo@pingou.com'],
                         'fullname': 'PY C',
                         'name': 'pingou'},
                    'username': 'Jenkins'},
                'message': 'Flag added',
                'uid': 'jenkins_build_pagure_100+seed',
                'avatar_url': 'https://seccdn.libravatar.org/avatar/...',
                'user': 'pingou'
            }
        )

        # One flag added
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].comment, 'Tests failed')
        self.assertEqual(request.flags[0].percent, 0)

        # Update flag
        data = {
            'username': 'Jenkins',
            'percent': 100,
            'comment': 'Tests passed',
            'url': 'http://jenkins.cloud.fedoraproject.org/',
            'uid': 'jenkins_build_pagure_100+seed',
        }

        output = self.app.post(
            '/api/0/test4/pull-request/1/flag', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['flag']['date_created'] = '1510742565'
        data['flag']['date_updated'] = '1510742565'
        data['flag']['pull_request_uid'] = '62b49f00d489452994de5010565fab81'
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                'flag': {
                    'comment': 'Tests passed',
                    'date_created': '1510742565',
                    'date_updated': '1510742565',
                    'percent': 100,
                    'pull_request_uid': '62b49f00d489452994de5010565fab81',
                    'status': 'success',
                    'url': 'http://jenkins.cloud.fedoraproject.org/',
                    'user': {
                        'default_email': 'bar@pingou.com',
                        'emails': ['bar@pingou.com', 'foo@pingou.com'],
                         'fullname': 'PY C',
                         'name': 'pingou'},
                    'username': 'Jenkins'},
                'message': 'Flag updated',
                'uid': 'jenkins_build_pagure_100+seed',
                'avatar_url': 'https://seccdn.libravatar.org/avatar/...',
                'user': 'pingou'
            }
        )

        # One flag added
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1)
        self.assertEqual(len(request.flags), 1)
        self.assertEqual(request.flags[0].comment, 'Tests passed')
        self.assertEqual(request.flags[0].percent, 100)

    @patch('pagure.lib.notify.send_email')
    def test_api_private_repo_pr_close(self, send_email):
        """ Test the api_pull_request_close method of the flask api. """
        send_email.return_value = True

        pagure.config.config['REQUESTS_FOLDER'] = None

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test2',
            description='test project description',
            hook_token='foo_bar',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        # Create the pull-request to close
        repo = pagure.lib.query._get_project(self.session, 'test4')
        forked_repo = pagure.lib.query._get_project(self.session, 'test4')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/close', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

        # Valid token, wrong project
        output = self.app.post(
            '/api/0/test2/pull-request/1/close', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ['error', 'error_code'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.value, data['error'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data['error_code'])

        # Invalid PR
        output = self.app.post(
            '/api/0/test4/pull-request/2/close', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'error': 'Pull-Request not found', 'error_code': "ENOREQ"}
        )

        # Create a token for foo for this project
        item = pagure.lib.model.Token(
            id='foobar_token',
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)
        self.session.commit()
        # Allow the token to close PR
        acls = pagure.lib.query.get_acls(self.session)
        acl = None
        for acl in acls:
            if acl.name == 'pull_request_close':
                break
        item = pagure.lib.model.TokenAcl(
            token_id='foobar_token',
            acl_id=acl.id,
        )
        self.session.add(item)
        self.session.commit()

        headers = {'Authorization': 'token foobar_token'}

        # User not admin
        output = self.app.post(
            '/api/0/test4/pull-request/1/close', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Close PR
        output = self.app.post(
            '/api/0/test4/pull-request/1/close', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {"message": "Pull-request closed!"}
        )

    @patch('pagure.lib.notify.send_email')
    def test_api_private_repo_pr_merge(self, send_email):
        """ Test the api_pull_request_merge method of the flask api. """
        send_email.return_value = True

        pagure.config.config['REQUESTS_FOLDER'] = None

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(os.path.join(self.path, 'requests'),
                                  bare=True)
        tests.add_readme_git_repo(os.path.join(self.path, 'repos',
                                               'test4.git'))
        tests.add_commit_git_repo(os.path.join(self.path, 'repos',
                                               'test4.git'),
                                  branch='test')
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test2',
            description='test project description',
            hook_token='foo_bar',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        # Create the pull-request to close
        repo = pagure.lib.query._get_project(self.session, 'test4')
        forked_repo = pagure.lib.query._get_project(self.session, 'test4')
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from='test',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post(
            '/api/0/foo/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

        # Valid token, wrong project
        output = self.app.post(
            '/api/0/test2/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ['error', 'error_code'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.value, data['error'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data['error_code'])

        # Invalid PR
        output = self.app.post(
            '/api/0/test4/pull-request/2/merge', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {'error': 'Pull-Request not found', 'error_code': "ENOREQ"}
        )

        # Create a token for foo for this project
        item = pagure.lib.model.Token(
            id='foobar_token',
            user_id=2,
            project_id=1,
            expiration=datetime.datetime.utcnow() + datetime.timedelta(
                days=30)
        )
        self.session.add(item)
        self.session.commit()

        # Allow the token to merge PR
        acls = pagure.lib.query.get_acls(self.session)
        acl = None
        for acl in acls:
            if acl.name == 'pull_request_merge':
                break
        item = pagure.lib.model.TokenAcl(
            token_id='foobar_token',
            acl_id=acl.id,
        )
        self.session.add(item)
        self.session.commit()

        headers = {'Authorization': 'token foobar_token'}

        # User not admin
        output = self.app.post(
            '/api/0/test4/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Merge PR
        output = self.app.post(
            '/api/0/test4/pull-request/1/merge', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {"message": "Changes merged!"}
        )

    def test_api_private_repo_new_issue(self):
        """ Test the api_new_issue method of the flask api. """
        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        for repo in ['GIT_FOLDER', 'TICKETS_FOLDER']:
            # Add a git repo
            repo_path = os.path.join(
                pagure.config.config.get(repo), 'test4.git')
            if not os.path.exists(repo_path):
                os.makedirs(repo_path)
            pygit2.init_repository(repo_path, bare=True)

        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Add private repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test2',
            description='test project description',
            hook_token='foo_bar',
            private=True,
        )
        self.session.add(item)
        self.session.commit()

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Valid token, wrong project
        output = self.app.post('/api/0/test2/new_issue', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ['error', 'error_code'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.value, data['error'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data['error_code'])

        # No input
        output = self.app.post('/api/0/test4/new_issue', headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "issue_content": ["This field is required."],
                    "title": ["This field is required."]
                }
            })

        data = {
            'title': 'test issue',
        }

        # Invalid repo
        output = self.app.post(
            '/api/0/foo/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

        # Incomplete request
        output = self.app.post(
            '/api/0/test4/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "issue_content": ["This field is required."],
                    "title": ["This field is required."]
                }

            }
        )

        data = {
            'title': 'test issue',
            'issue_content': 'This issue needs attention',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test4/new_issue', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['issue']['date_created'] = '1431414800'
        data['issue']['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
                'issue': FULL_ISSUE_LIST[7],
                'message': 'Issue created'
            }
        )

    def test_api_private_repo_view_issues(self):
        """ Test the api_view_issues method of the flask api. """
        self.test_api_private_repo_new_issue()

        # Invalid repo
        output = self.app.get('/api/0/foo/issues')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

        # List all opened issues
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/api/0/test4/issues')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            data['issues'][0]['date_created'] = '1431414800'
            data['issues'][0]['last_updated'] = '1431414800'
            for k in ['first', 'last']:
                self.assertIsNotNone(data['pagination'][k])
                data['pagination'][k] = 'http://localhost...'

            self.assertDictEqual(
                data,
                {
                    "args": {
                        "assignee": None,
                        "author": None,
                        "milestones": [],
                        "no_stones": None,
                        "order": None,
                        "priority": None,
                        "since": None,
                        "status": None,
                        "tags": []
                    },
                    "total_issues": 1,
                    "issues": [
                        {
                            "assignee": None,
                            "blocks": [],
                            "close_status": None,
                            "closed_at": None,
                            "closed_by": None,
                            "comments": [],
                            "content": "This issue needs attention",
                            "custom_fields": [],
                            "date_created": "1431414800",
                            "last_updated": "1431414800",
                            "depends": [],
                            "id": 1,
                            "milestone": None,
                            "priority": None,
                            "private": False,
                            "status": "Open",
                            "tags": [],
                            "title": "test issue",
                            "user": {
                                "fullname": "PY C",
                                "name": "pingou"

                            }
                        }
                    ],
                    'pagination': {
                        u'first': u'http://localhost...',
                        u'last': u'http://localhost...',
                        u'next': None,
                        u'page': 1,
                        u'pages': 1,
                        u'per_page': 20,
                        u'prev': None
                    },
                }
            )

        # Create private issue
        repo = pagure.lib.query._get_project(self.session, 'test4')
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        # Private issues are retrieved
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/api/0/test4/issues')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            data['issues'][0]['date_created'] = '1431414800'
            data['issues'][0]['last_updated'] = '1431414800'
            data['issues'][1]['date_created'] = '1431414800'
            data['issues'][1]['last_updated'] = '1431414800'
            for k in ['first', 'last']:
                self.assertIsNotNone(data['pagination'][k])
                data['pagination'][k] = 'http://localhost...'

            self.assertDictEqual(
                data,
                {
                    "args": {
                        "assignee": None,
                        "author": None,
                        "milestones": [],
                        "no_stones": None,
                        "order": None,
                        "priority": None,
                        "status": None,
                        "since": None,
                        "tags": []
                    },
                    "issues": [
                        {
                            "assignee": None,
                            "blocks": [],
                            "close_status": None,
                            "closed_at": None,
                            "closed_by": None,
                            "comments": [],
                            "content": "We should work on this",
                            "custom_fields": [],
                            "date_created": "1431414800",
                            "last_updated": "1431414800",
                            "depends": [],
                            "id": 2,
                            "milestone": None,
                            "priority": None,
                            "private": True,
                            "status": "Open",
                            "tags": [],
                            "title": "Test issue",
                            "user": {
                                "fullname": "PY C",
                                "name": "pingou"
                            }
                        },
                        {
                            "assignee": None,
                            "blocks": [],
                            "close_status": None,
                            "closed_at": None,
                            "closed_by": None,
                            "comments": [],
                            "content": "This issue needs attention",
                            "custom_fields": [],
                            "date_created": "1431414800",
                            "last_updated": "1431414800",
                            "depends": [],
                            "id": 1,
                            "milestone": None,
                            "priority": None,
                            "private": False,
                            "status": "Open",
                            "tags": [],
                            "title": "test issue",
                            "user": {
                                "fullname": "PY C",
                                "name": "pingou"
                            }
                        }
                    ],
                    'pagination': {
                        u'first': u'http://localhost...',
                        u'last': u'http://localhost...',
                        u'next': None,
                        u'page': 1,
                        u'pages': 1,
                        u'per_page': 20,
                        u'prev': None
                    },
                    "total_issues": 2
                }

            )

        # Access issues authenticated but non-existing token
        headers = {'Authorization': 'token aaabbbccc'}
        output = self.app.get('/api/0/test4/issues', headers=headers)
        self.assertEqual(output.status_code, 401)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Access issues authenticated correctly
        output = self.app.get('/api/0/test4/issues', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['issues'][0]['date_created'] = '1431414800'
        data['issues'][0]['last_updated'] = '1431414800'
        data['issues'][1]['date_created'] = '1431414800'
        data['issues'][1]['last_updated'] = '1431414800'
        for k in ['first', 'last']:
            self.assertIsNotNone(data['pagination'][k])
            data['pagination'][k] = 'http://localhost...'

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "status": None,
                    "since": None,
                    "tags": []
                },
                "issues": [
                    {
                        "assignee": None,
                        "blocks": [],
                        "close_status": None,
                        "closed_at": None,
                        "closed_by": None,
                        "comments": [],
                        "content": "We should work on this",
                        "custom_fields": [],
                        "date_created": "1431414800",
                        "last_updated": "1431414800",
                        "depends": [],
                        "id": 2,
                        "milestone": None,
                        "priority": None,
                        "private": True,
                        "status": "Open",
                        "tags": [],
                        "title": "Test issue",
                        "user": {
                            "fullname": "PY C",
                            "name": "pingou"
                        }
                    },
                    {
                        "assignee": None,
                        "blocks": [],
                        "close_status": None,
                        "closed_at": None,
                        "closed_by": None,
                        "comments": [],
                        "content": "This issue needs attention",
                        "custom_fields": [],
                        "date_created": "1431414800",
                        "last_updated": "1431414800",
                        "depends": [],
                        "id": 1,
                        "milestone": None,
                        "priority": None,
                        "private": False,
                        "status": "Open",
                        "tags": [],
                        "title": "test issue",
                        "user": {
                            "fullname": "PY C",
                            "name": "pingou"
                        }
                    }
                ],
                'pagination': {
                    u'first': u'http://localhost...',
                    u'last': u'http://localhost...',
                    u'next': None,
                    u'page': 1,
                    u'pages': 1,
                    u'per_page': 20,
                    u'prev': None
                },
                "total_issues": 2
            }

        )

        # List closed issue
        output = self.app.get(
            '/api/0/test4/issues?status=Closed', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for k in ['first', 'last']:
            self.assertIsNotNone(data['pagination'][k])
            data['pagination'][k] = 'http://localhost...'

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "status": "Closed",
                    "since": None,
                    "tags": []
                },
                "issues": [],
                'pagination': {
                    u'first': u'http://localhost...',
                    u'last': u'http://localhost...',
                    u'next': None,
                    u'page': 1,
                    u'pages': 0,
                    u'per_page': 20,
                    u'prev': None
                },
                "total_issues": 0,
            }
        )

        # List closed issue
        output = self.app.get(
            '/api/0/test4/issues?status=Invalid', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        for k in ['first', 'last']:
            self.assertIsNotNone(data['pagination'][k])
            data['pagination'][k] = 'http://localhost...'

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "status": "Invalid",
                    "since": None,
                    "tags": []
                },
                "issues": [],
                'pagination': {
                    u'first': u'http://localhost...',
                    u'last': u'http://localhost...',
                    u'next': None,
                    u'page': 1,
                    u'pages': 0,
                    u'per_page': 20,
                    u'prev': None
                },
                "total_issues": 0,
            }
        )

        # List all issues
        output = self.app.get(
            '/api/0/test4/issues?status=All', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['issues'][0]['date_created'] = '1431414800'
        data['issues'][0]['last_updated'] = '1431414800'
        data['issues'][1]['date_created'] = '1431414800'
        data['issues'][1]['last_updated'] = '1431414800'
        for k in ['first', 'last']:
            self.assertIsNotNone(data['pagination'][k])
            data['pagination'][k] = 'http://localhost...'

        self.assertDictEqual(
            data,
            {
                "args": {
                    "assignee": None,
                    "author": None,
                    "milestones": [],
                    "no_stones": None,
                    "order": None,
                    "priority": None,
                    "since": None,
                    "status": "All",
                    "tags": []
                },
                "issues": [
                    {
                        "assignee": None,
                        "blocks": [],
                        "close_status": None,
                        "closed_at": None,
                        "closed_by": None,
                        "comments": [],
                        "content": "We should work on this",
                        "custom_fields": [],
                        "date_created": "1431414800",
                        "last_updated": "1431414800",
                        "depends": [],
                        "id": 2,
                        "milestone": None,
                        "priority": None,
                        "private": True,
                        "status": "Open",
                        "tags": [],
                        "title": "Test issue",
                        "user": {
                            "fullname": "PY C",
                            "name": "pingou"
                        }
                    },
                    {
                        "assignee": None,
                        "blocks": [],
                        "close_status": None,
                        "closed_at": None,
                        "closed_by": None,
                        "comments": [],
                        "content": "This issue needs attention",
                        "custom_fields": [],
                        "date_created": "1431414800",
                        "last_updated": "1431414800",
                        "depends": [],
                        "id": 1,
                        "milestone": None,
                        "priority": None,
                        "private": False,
                        "status": "Open",
                        "tags": [],
                        "title": "test issue",
                        "user": {
                            "fullname": "PY C",
                            "name": "pingou"
                        }
                    }
                ],
                'pagination': {
                    u'first': u'http://localhost...',
                    u'last': u'http://localhost...',
                    u'next': None,
                    u'page': 1,
                    u'pages': 1,
                    u'per_page': 20,
                    u'prev': None
                },
                "total_issues": 2
            }

        )

    def test_api_pivate_repo_view_issue(self):
        """ Test the api_view_issue method of the flask api. """
        self.test_api_private_repo_new_issue()

        # Invalid repo
        output = self.app.get('/api/0/foo/issue/1')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

        # Invalid issue for this repo
        output = self.app.get('/api/0/test4/issue/1')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

        # Un-authorized user
        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/api/0/test4/issue/1')
            self.assertEqual(output.status_code, 404)
            data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(
                data,
                {
                    "error": "Project not found",
                    "error_code": "ENOPROJECT",
                }
            )

        # Valid issue
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/api/0/test4/issue/1')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            data['date_created'] = '1431414800'
            data['last_updated'] = '1431414800'
            self.assertDictEqual(
                data,
                {
                    "assignee": None,
                    "blocks": [],
                    "close_status": None,
                    "closed_at": None,
                    "closed_by": None,
                    "comments": [],
                    "content": "This issue needs attention",
                    "custom_fields": [],
                    "date_created": "1431414800",
                    "depends": [],
                    "id": 1,
                    "last_updated": "1431414800",
                    "milestone": None,
                    "priority": None,
                    "private": False,
                    "status": "Open",
                    "tags": [],
                    "title": "test issue",
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou"
                    }
                }

            )

        headers = {'Authorization': 'token aaabbbccc'}

        # Access issue authenticated but non-existing token
        output = self.app.get('/api/0/test4/issue/1', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ['error', 'error_code', 'errors'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.value, data['error'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data['error_code'])
        self.assertEqual(data['errors'], 'Invalid token')

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Access issue authenticated correctly
        output = self.app.get('/api/0/test4/issue/1', headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data['date_created'] = '1431414800'
        data['last_updated'] = '1431414800'
        self.assertDictEqual(
            data,
            {
                "assignee": None,
                "blocks": [],
                "close_status": None,
                "closed_at": None,
                "closed_by": None,
                "comments": [],
                "content": "This issue needs attention",
                "custom_fields": [],
                "date_created": "1431414800",
                "depends": [],
                "id": 1,
                "last_updated": "1431414800",
                "milestone": None,
                "priority": None,
                "private": False,
                "status": "Open",
                "tags": [],
                "title": "test issue",
                "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                }

            }
        )

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_api_private_repo_change_status_issue(self):
        """ Test the api_change_status_issue method of the flask api. """
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        self.session.add(item)
        self.session.commit()

        for repo in ['GIT_FOLDER', 'TICKETS_FOLDER']:
            # Add a git repo
            repo_path = os.path.join(
                pagure.config.config.get(repo), 'test4.git')
            if not os.path.exists(repo_path):
                os.makedirs(repo_path)
            pygit2.init_repository(repo_path, bare=True)

        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post('/api/0/foo/issue/1/status', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

        # Valid token, wrong project
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                '/api/0/test2/issue/1/status', headers=headers)
            self.assertEqual(output.status_code, 404)
            data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(
                data,
                {
                    "error": "Project not found",
                    "error_code": "ENOPROJECT",
                }
            )

        # No input
        output = self.app.post('/api/0/test4/issue/1/status', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Issue not found",
                "error_code": "ENOISSUE",
            }
        )

        # Create normal issue
        repo = pagure.lib.query._get_project(self.session, 'test4')
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this',
            user='pingou',
            private=False,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')

        # Check status before
        repo = pagure.lib.query._get_project(self.session, 'test4')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.status, 'Open')

        data = {
            'title': 'test issue',
        }

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            # Incomplete request
            output = self.app.post(
                '/api/0/test4/issue/1/status', data=data, headers=headers)
            self.assertEqual(output.status_code, 400)
            data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(
                data,
                {
                    "error": "Invalid or incomplete input submitted",
                    "error_code": "EINVALIDREQ",
                    "errors": {"status": ["Not a valid choice"]}
                }
            )

            # No change
            repo = pagure.lib.query._get_project(self.session, 'test4')
            issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
            self.assertEqual(issue.status, 'Open')

            data = {
                'status': 'Open',
            }

            # Valid request but no change
            output = self.app.post(
                '/api/0/test4/issue/1/status', data=data, headers=headers)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(
                data,
                {'message': 'No changes'}
            )

            # No change
            repo = pagure.lib.query._get_project(self.session, 'test4')
            issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
            self.assertEqual(issue.status, 'Open')

            data = {
                'status': 'Fixed',
            }

            # Valid request
            output = self.app.post(
                '/api/0/test4/issue/1/status', data=data, headers=headers)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(
                data,
                {'message':[
                    'Issue status updated to: Closed (was: Open)',
                    'Issue close_status updated to: Fixed'
                ]}
            )

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_private_repo_comment_issue(self, p_send_email, p_ugt):
        """ Test the api_comment_issue method of the flask api. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test4',
            description='test project description',
            hook_token='aaabbbeeeceee',
            private=True,
        )
        self.session.add(item)
        self.session.commit()
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Invalid project
        output = self.app.post('/api/0/foo/issue/1/comment', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT",
            }
        )

        # Invalid token, right project
        headers = {'Authorization': 'token aaabbbccc'}
        output = self.app.post('/api/0/test4/issue/1/comment', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ['error', 'error_code', 'errors'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.value, data['error'])
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data['error_code'])
        self.assertEqual(data['errors'], 'Invalid token')

        headers = {'Authorization': 'token aaabbbcccddd'}
        # No input
        output = self.app.post('/api/0/test4/issue/1/comment', headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Issue not found",
                "error_code": "ENOISSUE",
            }
        )

        # Create normal issue
        repo = pagure.lib.query._get_project(self.session, 'test4')
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this',
            user='pingou',
            private=False,
            issue_uid='aaabbbccc1',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')

        # Check comments before
        self.session.commit()
        repo = pagure.lib.query._get_project(self.session, 'test4')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 0)

        data = {
            'title': 'test issue',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/test4/issue/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"comment": ["This field is required."]}
            }
        )

        # No change
        self.session.commit()
        repo = pagure.lib.query._get_project(self.session, 'test4')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(issue.status, 'Open')

        data = {
            'comment': 'This is a very interesting question',
        }

        # Valid request
        output = self.app.post(
            '/api/0/test4/issue/1/comment', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {'message': 'Comment added',
             'avatar_url': 'https://seccdn.libravatar.org/avatar/...',
             'user': 'pingou'}
        )

        # One comment added
        self.session.commit()
        repo = pagure.lib.query._get_project(self.session, 'test4')
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.comments), 1)

    @patch('pagure.lib.git.update_git')
    @patch('pagure.lib.notify.send_email')
    def test_api_view_issue_comment(self, p_send_email, p_ugt):
        """ Test the api_view_issue_comment endpoint. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        self.test_api_private_repo_comment_issue()

        # View a comment that does not exist
        output = self.app.get('/api/0/foo/issue/100/comment/2')
        self.assertEqual(output.status_code, 404)

        # Issue exists but not the comment
        output = self.app.get('/api/0/test/issue/1/comment/2')
        self.assertEqual(output.status_code, 404)

        # Issue and comment exists
        output = self.app.get('/api/0/test/issue/1/comment/1')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/api/0/test4/issue/1/comment/1')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            data['date_created'] = '1435821770'
            data["comment_date"] = "2015-07-02 09:22"
            data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
            self.assertDictEqual(
                data,
                {
                    "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                    "comment": "This is a very interesting question",
                    "comment_date": "2015-07-02 09:22",
                    "notification": False,
                    "date_created": "1435821770",
                    "edited_on": None,
                    "editor": None,
                    "id": 1,
                    "parent": None,
                    "reactions": {},
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou"
                    }
                }
            )

            # Issue and comment exists, using UID
            output = self.app.get('/api/0/test4/issue/aaabbbccc1/comment/1')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))
            data['date_created'] = '1435821770'
            data["comment_date"] = "2015-07-02 09:22"
            data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
            self.assertDictEqual(
                data,
                {
                    "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                    "comment": "This is a very interesting question",
                    "comment_date": "2015-07-02 09:22",
                    "notification": False,
                    "date_created": "1435821770",
                    "edited_on": None,
                    "editor": None,
                    "id": 1,
                    "parent": None,
                    "reactions": {},
                    "user": {
                        "fullname": "PY C",
                        "name": "pingou"
                    }
                }
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
