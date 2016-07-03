# -*- coding: utf-8 -*-

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import datetime
import unittest
import shutil
import sys
import tempfile
import os

import json
import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagurePrivateRepotest(tests.Modeltests):
    """ Tests for private repo in pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagurePrivateRepotest, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.lib.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.filters.SESSION = self.session
        pagure.ui.fork.SESSION = self.session
        pagure.ui.repo.SESSION = self.session
        pagure.ui.issues.SESSION = self.session
        pagure.api.SESSION = self.session
        pagure.api.project.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = os.path.join(tests.HERE, 'repos')
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
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
        gitrepo = os.path.join(tests.HERE, 'repos', 'pmc.git')
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
        project = pagure.lib.get_project(self.session, 'pmc')
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

    def test_index(self):
        """ Test the index endpoint. """

        output = self.app.get('/')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h2 class="m-b-1">All Projects '
            '<span class="label label-default">0</span></h2>', output.data)

        tests.create_projects(self.session)

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
        self.assertIn(
            '<h2 class="m-b-1">All Projects '
            '<span class="label label-default">3</span></h2>', output.data)

        user = tests.FakeUser(username='foo')
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/')
            self.assertIn(
                'My Projects <span class="label label-default">2</span>',
                output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)
            self.assertEqual(
                output.data.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output.data.count('<div class="card-header">'), 3)

    def test_view_user(self):
        """ Test the view_user endpoint. """

        output = self.app.get('/user/foo?repopage=abc&forkpage=def')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'Projects <span class="label label-default">0</span>',
            output.data)
        self.assertIn(
            'Forks <span class="label label-default">0</span>',
            output.data)

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
            pagure.APP.config['GIT_FOLDER'])

        output = self.app.get('/user/foo')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'Projects <span class="label label-default">1</span>',
            output.data)
        self.assertIn(
            'Forks <span class="label label-default">0</span>', output.data)

        user = tests.FakeUser(username='foo')
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/user/foo')
            self.assertIn(
                'Projects <span class="label label-default">2</span>',
                output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)
            self.assertEqual(
                output.data.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output.data.count('<div class="card-header">'), 3)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/user/foo')
            self.assertIn(
                'Projects <span class="label label-default">1</span>',
                output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)
            self.assertEqual(
                output.data.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output.data.count('<div class="card-header">'), 3)

        repo = pagure.lib.get_project(self.session, 'test3')

        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='pingou',
            user='foo',
        )
        self.assertEqual(msg, 'User added')

        # New user added to private projects
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/')
            self.assertIn(
                'My Projects <span class="label label-default">1</span>',
                output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)
            self.assertEqual(
                output.data.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output.data.count('<div class="card-header">'), 3)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_private_settings_ui(self, ast):
        """ Test UI for private repo"""

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
            pagure.APP.config.get('GIT_FOLDER'), 'test4.git')
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
        pygit2.init_repository(repo_path)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            tests.create_projects(self.session)
            tests.create_projects_git(pagure.APP.config.get('GIT_FOLDER'))

            ast.return_value = False
            output = self.app.post('/test/settings')

            # Check for a public repo
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<input type="checkbox" value="private" name="private"', output.data)

            ast.return_value = False
            output = self.app.post('/test4/settings')

            # Check for private repo
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<input type="checkbox" value="private" name="private" checked=""/>', output.data)

            # Check the new project form has 'private' checkbox
            output = self.app.get('/new')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<input id="private" name="private" type="checkbox" value="y">', output.data)

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

        repo = pagure.lib.get_project(self.session, 'pmc')

        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        # Create all the git repos
        tests.create_projects_git(
            os.path.join(tests.HERE, 'requests'), bare=True)

        # Add a git repo
        repo_path = os.path.join(
            pagure.APP.config.get('REQUESTS_FOLDER'), 'pmc.git')
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
        pygit2.init_repository(repo_path, bare=True)

        # Check repo was created
        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):

            output = self.app.get('/user/pingou/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n            Projects <span '
                'class="label label-default">1</span>', output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)

            self.set_up_git_repo(new_project=None, branch_from='feature')
            project = pagure.lib.get_project(self.session, 'pmc')
            self.assertEqual(len(project.requests), 1)

            output = self.app.get('/pmc/pull-request/1')
            self.assertEqual(output.status_code, 200)

        # Check repo was created
        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/pmc/pull-requests')
            self.assertEqual(output.status_code, 401)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/pmc/pull-requests')
            self.assertEqual(output.status_code, 200)

        user = tests.FakeUser(username='foo')
        with tests.user_set(pagure.APP, user):
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

        # Add a git repo
        repo_path = os.path.join(
            pagure.APP.config.get('GIT_FOLDER'), 'test4.git')
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
        pygit2.init_repository(repo_path)

        # Add a git repo
        repo_path = os.path.join(
            pagure.APP.config.get('TICKETS_FOLDER'), 'test4.git')
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
        pygit2.init_repository(repo_path, bare=True)

        # Check if the private repo issues are publicly accesible
        output = self.app.get('/test4/issues')
        self.assertEqual(output.status_code, 401)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test4')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):

            # Whole list
            output = self.app.get('/test4/issues')
            self.assertEqual(output.status_code, 401)

            # Check single issue
            output = self.app.get('/test4/issue/1')
            self.assertEqual(output.status_code, 401)



        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):

            # Whole list
            output = self.app.get('/test4/issues')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<title>Issues - test4 - Pagure</title>', output.data)
            self.assertTrue(
            '<h2>\n      1 Open Issues' in output.data)

            # Check single issue
            output = self.app.get('/test4/issue/1')
            self.assertEqual(output.status_code, 200)

        repo = pagure.lib.get_project(self.session, 'test4')

        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        user.username='foo'
        with tests.user_set(pagure.APP, user):

            # Whole list
            output = self.app.get('/test4/issues')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<title>Issues - test4 - Pagure</title>', output.data)
            self.assertTrue(
            '<h2>\n      1 Open Issues' in output.data)

            # Check single issue
            output = self.app.get('/test4/issue/1')
            self.assertEqual(output.status_code, 200)

    def test_api_private_repo(self):
        """ Test api points for private repo"""

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
        gitrepo = os.path.join(tests.HERE, 'repos', 'test4.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        repopath = os.path.join(newpath, 'test4')
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
            acl_id=3,
        )
        self.session.add(item)
        self.session.commit()


        # Check tags
        output = self.app.get('/api/0/test4/git/tags')
        self.assertEqual(output.status_code, 403)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):

            output = self.app.get('/api/0/test4/git/tags')
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertDictEqual(
                data,
                {'tags': ['0.0.1'], 'total_tags': 1}
            )

        shutil.rmtree(newpath)

if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagurePrivateRepotest)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
