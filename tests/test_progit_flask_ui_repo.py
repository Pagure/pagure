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


class PagureFlaskRepotests(tests.Modeltests):
    """ Tests for flask app controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskRepotests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.filters.SESSION = self.session
        pagure.ui.repo.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = tests.HERE
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = pagure.APP.test_client()

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_add_user(self, ast):
        """ Test the add_user endpoint. """
        ast.return_value = False

        output = self.app.get('/foo/adduser')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/foo/adduser')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Add user</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'user': 'ralph',
            }

            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Add user</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            data['csrf_token'] = csrf_token
            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Add user</h2>' in output.data)
            self.assertTrue(
                '<li class="error">No user &#34;ralph&#34; found</li>'
                in output.data)

            data['user'] = 'foo'
            tests.create_projects_git(tests.HERE)
            output = self.app.post(
                '/test/adduser', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="message">User added</li>' in output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_add_group_project(self, ast):
        """ Test the add_group_project endpoint. """
        ast.return_value = False

        output = self.app.get('/foo/addgroup')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/foo/addgroup')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.get('/test/addgroup')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.get('/test/addgroup')
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

        msg = pagure.lib.add_group(
            self.session,
            group_name='foo',
            group_type='bar',
            user='pingou',
            is_admin=False,
        )
        self.session.commit()
        self.assertEqual(msg, 'User `pingou` added to the group `foo`.')

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/addgroup')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Add group</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'group': 'ralph',
            }

            output = self.app.post('/test/addgroup', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Add group</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            data['csrf_token'] = csrf_token
            output = self.app.post('/test/addgroup', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Add group</h2>' in output.data)
            self.assertTrue(
                '<li class="error">No group ralph found.</li>'
                in output.data)

            data['group'] = 'foo'
            tests.create_projects_git(tests.HERE)
            output = self.app.post(
                '/test/addgroup', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="message">Group added</li>' in output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_remove_user(self, ast):
        """ Test the remove_user endpoint. """
        ast.return_value = False

        output = self.app.post('/foo/dropuser/1')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/dropuser/1')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.post('/test/dropuser/1')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.post('/test/dropuser/1')
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            tests.create_projects_git(tests.HERE)
            output = self.app.post('/test/settings')

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'csrf_token': csrf_token}

            output = self.app.post(
                '/test/dropuser/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="error">User does not have commit or cannot '
                'loose it right</li>' in output.data)

        # Add an user to a project
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.add_user_to_project(
            session=self.session,
            project=repo,
            new_user='foo',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/dropuser/2', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            self.assertFalse(
                '<li class="message">User removed</li>' in output.data)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/dropuser/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="message">User removed</li>' in output.data)

    def test_update_project(self):
        """ Test the update_project endpoint. """
        output = self.app.post('/foo/update')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/update')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.post('/test/update')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            tests.create_projects_git(tests.HERE)
            output = self.app.post('/test/update', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'description': 'new description for test project #1',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertIn(
                '<input name="avatar_email" value="" />', output.data)
            self.assertTrue(
                '<li class="message">Project updated</li>'
                in output.data)

            # Edit the avatar_email
            data = {
                'description': 'new description for test project #1',
                'avatar_email': 'pingou@fp.o',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertIn(
                '<input name="avatar_email" value="pingou@fp.o" />',
                output.data)
            self.assertTrue(
                '<li class="message">Project updated</li>'
                in output.data)

            # Reset the avatar_email
            data = {
                'description': 'new description for test project #1',
                'avatar_email': '',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/update', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertIn(
                '<input name="avatar_email" value="" />',
                output.data)
            self.assertTrue(
                '<li class="message">Project updated</li>'
                in output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_view_settings(self, ast):
        """ Test the view_settings endpoint. """
        ast.return_value = False

        output = self.app.get('/foo/settings')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/foo/settings')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(tests.HERE)

            output = self.app.get('/test/settings')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            ast.return_value = True
            output = self.app.get('/test/settings')
            self.assertEqual(output.status_code, 302)

            ast.return_value = False
            output = self.app.get('/test/settings')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            # Both checkbox checked before
            self.assertTrue(
                '<input id="project_documentation" type="checkbox" value="y" '
                'name="project_documentation" checked=""/>' in output.data)
            self.assertTrue(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" checked=""/>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}
            output = self.app.post(
                '/test/settings', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            # Both checkbox are still checked
            output = self.app.get('/test/settings', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            self.assertTrue(
                '<input id="project_documentation" type="checkbox" value="y" '
                'name="project_documentation" checked=""/>' in output.data)
            self.assertTrue(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" checked=""/>' in output.data)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue(
                '<title>Overview - test - Pagure</title>' in output.data)
            self.assertTrue(
                '<li class="message">Edited successfully settings of '
                'repo: test</li>' in output.data)

            # Both checkbox are now un-checked
            output = self.app.get('/test/settings', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            self.assertTrue(
                '<input id="project_documentation" type="checkbox" value="y" '
                'name="project_documentation" />' in output.data)
            self.assertTrue(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" />' in output.data)

            data = {
                'csrf_token': csrf_token,
                'project_documentation': 'y',
                'issue_tracker': 'y',
            }
            output = self.app.post(
                '/test/settings', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue(
                '<title>Overview - test - Pagure</title>' in output.data)
            self.assertTrue(
                '<li class="message">Edited successfully settings of '
                'repo: test</li>' in output.data)

            # Both checkbox are again checked
            output = self.app.get('/test/settings', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            self.assertTrue(
                '<input id="project_documentation" type="checkbox" value="y" '
                'name="project_documentation" checked=""/>' in output.data)
            self.assertTrue(
                '<input id="issue_tracker" type="checkbox" value="y" '
                'name="issue_tracker" checked=""/>' in output.data)

    def test_view_forks(self):
        """ Test the view_forks endpoint. """

        output = self.app.get('/foo/forks')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/forks')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('This project has not been forked.' in output.data)

    def test_view_repo(self):
        """ Test the view_repo endpoint. """

        output = self.app.get('/foo')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE, bare=True)

        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))

        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        # Turn that repo into a fork
        repo = pagure.lib.get_project(self.session, 'test')
        repo.parent_id = 2
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get('/test')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test.git'))

        output = self.app.get('/fork/pingou/test')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue('Forked from' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
            hook_token='aaabbbmmm',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #3</p>' in output.data)
        self.assertTrue('Forked from' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

    def test_view_repo_empty(self):
        """ Test the view_repo endpoint on a repo w/o master branch. """

        tests.create_projects(self.session)
        # Create a git repo to play with
        gitrepo = os.path.join(tests.HERE, 'test.git')
        pygit2.init_repository(gitrepo, bare=True)

        # Create a fork of this repo
        newpath = tempfile.mkdtemp(prefix='pagure-viewrepo-test')
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
        refname = 'refs/heads/feature'
        ori_remote = new_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 0)

    def test_view_repo_branch(self):
        """ Test the view_repo_branch endpoint. """

        output = self.app.get('/foo/branch/master')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/branch/master')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE, bare=True)

        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))

        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        # Turn that repo into a fork
        repo = pagure.lib.get_project(self.session, 'test')
        repo.parent_id = 2
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test.git'))

        output = self.app.get('/fork/pingou/test/branch/master')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue('Forked from' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
            hook_token='aaabbbnnn',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3/branch/master')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #3</p>' in output.data)
        self.assertTrue('Forked from' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 10)

    def test_view_commits(self):
        """ Test the view_commits endpoint. """
        output = self.app.get('/foo/commits')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/commits')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE, bare=True)

        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))

        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        output = self.app.get('/test/commits/master')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        # Turn that repo into a fork
        repo = pagure.lib.get_project(self.session, 'test')
        repo.parent_id = 2
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test.git'))

        output = self.app.get('/fork/pingou/test/commits?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue('Forked from' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
            hook_token='aaabbbooo',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3/commits/fobranch')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/fork/pingou/test3/commits')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #3</p>' in output.data)
        self.assertTrue('Forked from' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 13)

    def test_view_file(self):
        """ Test the view_file endpoint. """
        output = self.app.get('/foo/blob/foo/f/sources')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/blob/foo/f/sources')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE, bare=True)

        output = self.app.get('/test/blob/foo/f/sources')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))
        tests.add_binary_git_repo(
            os.path.join(tests.HERE, 'test.git'), 'test.jpg')
        tests.add_binary_git_repo(
            os.path.join(tests.HERE, 'test.git'), 'test_binary')

        output = self.app.get('/test/blob/master/foofile')
        self.assertEqual(output.status_code, 404)

        # View in a branch
        output = self.app.get('/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="file_content">' in output.data)
        self.assertTrue(
            '<tr><td class="cell1"><a id="_1" href="#_1">1</a></td>'
            in output.data)
        self.assertTrue(
            '<td class="cell2"><pre> bar</pre></td>' in output.data)

        # View what's supposed to be an image
        output = self.app.get('/test/blob/master/f/test.jpg')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="file_content">' in output.data)
        self.assertTrue(
            'Binary files cannot be rendered.<br/>' in output.data)

        # View by commit id
        repo = pygit2.Repository(os.path.join(tests.HERE, 'test.git'))
        commit = repo.revparse_single('HEAD')

        output = self.app.get('/test/blob/%s/f/test.jpg' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="file_content">' in output.data)
        self.assertTrue(
            'Binary files cannot be rendered.<br/>' in output.data)

        # View by image name -- somehow we support this
        output = self.app.get('/test/blob/sources/f/test.jpg')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="file_content">' in output.data)
        self.assertTrue(
            'Binary files cannot be rendered.<br/>'
            in output.data)

        # View binary file
        output = self.app.get('/test/blob/sources/f/test_binary')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="file_content">' in output.data)
        self.assertTrue(
            'Binary files cannot be rendered.<br/>'
            in output.data)

        # View folder
        output = self.app.get('/test/blob/master/f/folder1')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="tree_list">' in output.data)
        self.assertTrue('<h3>Tree</h3>' in output.data)
        self.assertTrue(
            '<a href="/test/blob/master/f/folder1/folder2">' in output.data)

        # View by image name -- with a non-existant file
        output = self.app.get('/test/blob/sources/f/testfoo.jpg')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/blob/master/f/folder1/testfoo.jpg')
        self.assertEqual(output.status_code, 404)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
            hook_token='aaabbbppp',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="file_content">' in output.data)
        self.assertTrue(
            '<tr><td class="cell1"><a id="_1" href="#_1">1</a></td>'
            in output.data)
        self.assertTrue(
            '<td class="cell2"><pre> barRow 0</pre></td>' in output.data)

    def test_view_raw_file(self):
        """ Test the view_raw_file endpoint. """
        output = self.app.get('/foo/raw/foo/sources')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/raw/foo/sources')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE, bare=True)

        output = self.app.get('/test/raw/foo/sources')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))

        # View first commit
        output = self.app.get('/test/raw/master')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(':Author: Pierre-Yves Chibon' in output.data)

        # Add some more content to the repo
        tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))
        tests.add_binary_git_repo(
            os.path.join(tests.HERE, 'test.git'), 'test.jpg')
        tests.add_binary_git_repo(
            os.path.join(tests.HERE, 'test.git'), 'test_binary')

        output = self.app.get('/test/raw/master/f/foofile')
        self.assertEqual(output.status_code, 404)

        # View in a branch
        output = self.app.get('/test/raw/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('foo\n bar' in output.data)

        # View what's supposed to be an image
        output = self.app.get('/test/raw/master/f/test.jpg')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(output.data.startswith('<89>PNG^M'))

        # View by commit id
        repo = pygit2.Repository(os.path.join(tests.HERE, 'test.git'))
        commit = repo.revparse_single('HEAD')

        output = self.app.get('/test/raw/%s/f/test.jpg' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(output.data.startswith('<89>PNG^M'))

        # View by image name -- somehow we support this
        output = self.app.get('/test/raw/sources/f/test.jpg')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(output.data.startswith('<89>PNG^M'))

        # View binary file
        output = self.app.get('/test/raw/sources/f/test_binary')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(output.data.startswith('<89>PNG^M'))

        # View folder
        output = self.app.get('/test/raw/master/f/folder1')
        self.assertEqual(output.status_code, 404)

        # View by image name -- with a non-existant file
        output = self.app.get('/test/raw/sources/f/testfoo.jpg')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/raw/master/f/folder1/testfoo.jpg')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/test/raw/master/f/')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/test/raw/master')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(output.data.startswith(
            'diff --git a/test_binary b/test_binary\n'))

        output = self.app.get('/test/raw/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(output.data.startswith(
            'diff --git a/test_binary b/test_binary\n'))

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
            hook_token='aaabbbqqq',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3/raw/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('foo\n bar' in output.data)

    def test_view_commit(self):
        """ Test the view_commit endpoint. """
        output = self.app.get('/foo/bar')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/bar')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE, bare=True)

        output = self.app.get('/test/bar')
        self.assertEqual(output.status_code, 404)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))
        repo = pygit2.Repository(os.path.join(tests.HERE, 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View first commit
        output = self.app.get('/test/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="commit_diff">' in output.data)
        self.assertTrue('<th>Author</th>' in output.data)
        self.assertTrue('<th>Committer</th>' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ Pagure</span>' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ ======</span>' in output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))

        repo = pygit2.Repository(os.path.join(tests.HERE, 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View another commit
        output = self.app.get('/test/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="commit_diff">' in output.data)
        self.assertTrue('<th>Author</th>' in output.data)
        self.assertTrue('<th>Committer</th>' in output.data)
        self.assertTrue(
            '<div class="highlight" style="background: #f8f8f8">'
            '<pre style="line-height: 125%">'
            '<span style="color: #800080; font-weight: bold">'
            '@@ -0,0 +1,3 @@</span>' in output.data)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
            hook_token='aaabbbkkk',
        )
        self.session.add(item)
        self.session.commit()
        forkedgit = os.path.join(
            tests.HERE, 'forks', 'pingou', 'test3.git')

        tests.add_content_git_repo(forkedgit)
        tests.add_readme_git_repo(forkedgit)

        repo = pygit2.Repository(forkedgit)
        commit = repo.revparse_single('HEAD')

        # Commit does not exist in anothe repo :)
        output = self.app.get('/test/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 404)

        # View commit of fork
        output = self.app.get('/fork/pingou/test3/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="commit_diff">' in output.data)
        self.assertTrue('<th>Author</th>' in output.data)
        self.assertTrue('<th>Committer</th>' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ Pagure</span>' in output.data)
        self.assertTrue(
            '<span style="color: #00A000">+ ======</span>' in output.data)

    def test_view_commit_patch(self):
        """ Test the view_commit_patch endpoint. """
        output = self.app.get('/foo/bar.patch')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/bar.patch')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE, bare=True)

        output = self.app.get('/test/bar.patch')
        self.assertEqual(output.status_code, 404)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))
        repo = pygit2.Repository(os.path.join(tests.HERE, 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View first commit
        output = self.app.get('/test/%s.patch' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue('''diff --git a/README.rst b/README.rst
new file mode 100644
index 0000000..fb7093d
--- /dev/null
+++ b/README.rst
@@ -0,0 +1,16 @@
+Pagure
+======
+
+:Author: Pierre-Yves Chibon <pingou@pingoured.fr>
+
+
+Pagure is a light-weight git-centered forge based on pygit2.
+
+Currently, Pagure offers a web-interface for git repositories, a ticket
+system and possibilities to create new projects, fork existing ones and
+create/merge pull-requests across or within projects.
+
+
+Homepage: https://github.com/pypingou/pagure
+
+Dev instance: http://209.132.184.222/ (/!\ May change unexpectedly, it's a dev instance ;-))
''' in output.data)
        self.assertTrue('Subject: Add a README file' in output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))

        repo = pygit2.Repository(os.path.join(tests.HERE, 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View another commit
        output = self.app.get('/test/%s.patch' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            'Subject: Add some directory and a file for more testing'
            in output.data)
        self.assertTrue('''diff --git a/folder1/folder2/file b/folder1/folder2/file
new file mode 100644
index 0000000..11980b1
--- /dev/null
+++ b/folder1/folder2/file
@@ -0,0 +1,3 @@
+foo
+ bar
+baz
\ No newline at end of file
''' in output.data)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
            hook_token='aaabbblll',
        )
        self.session.add(item)
        self.session.commit()
        forkedgit = os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git')

        tests.add_content_git_repo(forkedgit)
        tests.add_readme_git_repo(forkedgit)

        repo = pygit2.Repository(forkedgit)
        commit = repo.revparse_single('HEAD')

        # Commit does not exist in anothe repo :)
        output = self.app.get('/test/%s.patch' % commit.oid.hex)
        self.assertEqual(output.status_code, 404)

        # View commit of fork
        output = self.app.get('/fork/pingou/test3/%s.patch' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue('''diff --git a/README.rst b/README.rst
new file mode 100644
index 0000000..fb7093d
--- /dev/null
+++ b/README.rst
@@ -0,0 +1,16 @@
+Pagure
+======
+
+:Author: Pierre-Yves Chibon <pingou@pingoured.fr>
+
+
+Pagure is a light-weight git-centered forge based on pygit2.
+
+Currently, Pagure offers a web-interface for git repositories, a ticket
+system and possibilities to create new projects, fork existing ones and
+create/merge pull-requests across or within projects.
+
+
+Homepage: https://github.com/pypingou/pagure
+
+Dev instance: http://209.132.184.222/ (/!\ May change unexpectedly, it's a dev instance ;-))
''' in output.data)

    def test_view_tree(self):
        """ Test the view_tree endpoint. """
        output = self.app.get('/foo/tree/')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/tree/')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE, bare=True)

        output = self.app.get('/test/tree/')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<h2>\n    <a href="/test/tree">None</a>/</h2>' in output.data)
        self.assertTrue(
            'No content found in this repository' in output.data)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))
        repo = pygit2.Repository(os.path.join(tests.HERE, 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View first commit
        output = self.app.get('/test/tree/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue('<h3>Tree</h3>' in output.data)
        self.assertTrue('README.rst' in output.data)
        self.assertFalse(
            'No content found in this repository' in output.data)

        # View tree by branch
        output = self.app.get('/test/tree/master')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue('<h3>Tree</h3>' in output.data)
        self.assertTrue('README.rst' in output.data)
        self.assertFalse(
            'No content found in this repository' in output.data)

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
            hook_token='aaabbbfff',
        )
        self.session.add(item)
        self.session.commit()
        forkedgit = os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git')

        tests.add_content_git_repo(forkedgit)

        output = self.app.get('/fork/pingou/test3/tree/')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>test project #3</p>' in output.data)
        self.assertTrue('<h3>Tree</h3>' in output.data)
        self.assertTrue(
            '<a href="/fork/pingou/test3/blob/master/f/folder1">'
            in output.data)
        self.assertTrue(
            '<a href="/fork/pingou/test3/blob/master/f/sources">'
            in output.data)
        self.assertFalse(
            'No content found in this repository' in output.data)

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.ui.repo.admin_session_timedout')
    def test_delete_repo(self, ast, send_email):
        """ Test the delete_repo endpoint. """
        ast.return_value = False
        send_email.return_value = True

        output = self.app.post('/foo/delete')
        # User not logged in
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/delete')
            # No project registered in the DB
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.post('/test/delete')
            # No git repo associated
            self.assertEqual(output.status_code, 403)

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            ast.return_value = True
            output = self.app.post('/test/delete')
            self.assertEqual(output.status_code, 302)

            ast.return_value = False
            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="error">Could not delete all the repos from the '
                'system</li>' in output.data)
            self.assertTrue('<h2>Projects (1)</h2>' in output.data)
            self.assertTrue('<h2>Forks (0)</h2>' in output.data)

            # Only git repo
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbggg',
            )
            self.session.add(item)
            self.session.commit()
            tests.create_projects_git(tests.HERE)
            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="error">Could not delete all the repos from the '
                'system</li>' in output.data)
            self.assertTrue('<h2>Projects (1)</h2>' in output.data)
            self.assertTrue('<h2>Forks (0)</h2>' in output.data)

            # Only git and doc repo
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbhhh',
            )
            self.session.add(item)
            self.session.commit()
            tests.create_projects_git(tests.HERE)
            tests.create_projects_git(os.path.join(tests.HERE, 'docs'))
            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="error">Could not delete all the repos from the '
                'system</li>' in output.data)

            # All repo there
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test',
                description='test project #1',
                hook_token='aaabbbiii',
            )
            self.session.add(item)
            self.session.commit()
            tests.create_projects_git(tests.HERE)
            tests.create_projects_git(os.path.join(tests.HERE, 'docs'))
            tests.create_projects_git(
                os.path.join(tests.HERE, 'tickets'), bare=True)
            tests.create_projects_git(
                os.path.join(tests.HERE, 'requests'), bare=True)

            # add issues
            repo = pagure.lib.get_project(self.session, 'test')
            msg = pagure.lib.new_issue(
                session=self.session,
                repo=repo,
                title='Test issue',
                content='We should work on this',
                user='pingou',
                ticketfolder=os.path.join(tests.HERE, 'tickets')
            )
            self.session.commit()
            self.assertEqual(msg.title, 'Test issue')

            msg = pagure.lib.new_issue(
                session=self.session,
                repo=repo,
                title='Test issue #2',
                content='We should work on this, really',
                user='pingou',
                ticketfolder=os.path.join(tests.HERE, 'tickets')
            )
            self.session.commit()
            self.assertEqual(msg.title, 'Test issue #2')

            # Add a comment to an issue
            issue = pagure.lib.search_issues(self.session, repo, issueid=1)
            msg = pagure.lib.add_issue_comment(
                session=self.session,
                issue=issue,
                comment='Hey look a comment!',
                user='foo',
                ticketfolder=None
            )
            self.session.commit()
            self.assertEqual(msg, 'Comment added')

            # add pull-requests
            req = pagure.lib.new_pull_request(
                session=self.session,
                repo_from=repo,
                branch_from='feature',
                repo_to=repo,
                branch_to='master',
                title='test pull-request',
                user='pingou',
                requestfolder=os.path.join(tests.HERE, 'requests'),
            )
            self.session.commit()
            self.assertEqual(req.id, 3)
            self.assertEqual(req.title, 'test pull-request')

            req = pagure.lib.new_pull_request(
                session=self.session,
                repo_from=repo,
                branch_from='feature2',
                repo_to=repo,
                branch_to='master',
                title='test pull-request',
                user='pingou',
                requestfolder=os.path.join(tests.HERE, 'requests'),
            )
            self.session.commit()
            self.assertEqual(req.id, 4)
            self.assertEqual(req.title, 'test pull-request')

            # Add comment on a pull-request
            request = pagure.lib.search_pull_requests(
                self.session, requestid=3)

            msg = pagure.lib.add_pull_request_comment(
                session=self.session,
                request=request,
                commit='commithash',
                filename='file',
                row=None,
                comment='This is awesome, I got to remember it!',
                user='foo',
                requestfolder=None,
            )
            self.assertEqual(msg, 'Comment added')

            output = self.app.post('/test/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Projects (1)</h2>' in output.data)
            self.assertTrue('<h2>Forks (0)</h2>' in output.data)

            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(repo, None)
            repo = pagure.lib.get_project(self.session, 'test2')
            self.assertNotEqual(repo, None)

            # Add a fork of a fork
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test3',
                description='test project #3',
                parent_id=2,
                hook_token='aaabbbjjj',
            )
            self.session.add(item)
            self.session.commit()
            tests.add_content_git_repo(
                os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
            tests.add_content_git_repo(
                os.path.join(tests.HERE, 'docs', 'pingou', 'test3.git'))
            tests.add_content_git_repo(
                os.path.join(tests.HERE, 'tickets', 'pingou', 'test3.git'))

            output = self.app.post(
                '/fork/pingou/test3/delete', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Projects (1)</h2>' in output.data)
            self.assertTrue('<h2>Forks (0)</h2>' in output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_new_repo_hook_token(self, ast):
        """ Test the new_repo_hook_token endpoint. """
        ast.return_value = False
        tests.create_projects(self.session)

        repo = pagure.lib.get_project(self.session, 'test')
        self.assertEqual(repo.hook_token, 'aaabbbccc')

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New project</h2>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            output = self.app.post('/foo/hook_token')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/hook_token')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.post('/test/hook_token')
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

        repo = pagure.lib.get_project(self.session, 'test')
        self.assertEqual(repo.hook_token, 'aaabbbccc')

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/hook_token')
            self.assertEqual(output.status_code, 400)

            data = {'csrf_token': csrf_token}

            repo = pagure.lib.get_project(self.session, 'test')
            self.assertEqual(repo.hook_token, 'aaabbbccc')

            tests.create_projects_git(tests.HERE)
            output = self.app.post(
                '/test/hook_token', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="message">New hook token generated</li>',
                output.data)

        repo = pagure.lib.get_project(self.session, 'test')
        self.assertNotEqual(repo.hook_token, 'aaabbbccc')

    @patch('pagure.ui.repo.admin_session_timedout')
    @patch('pagure.lib.git.update_git')
    def test_regenerate_git(self, upgit, ast):
        """ Test the regenerate_git endpoint. """
        ast.return_value = False
        upgit.return_value = True
        tests.create_projects(self.session)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New project</h2>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            output = self.app.post('/foo/regenerate')
            self.assertEqual(output.status_code, 404)

            output = self.app.post('/test/regenerate')
            self.assertEqual(output.status_code, 403)

            ast.return_value = True
            output = self.app.post('/test/regenerate')
            self.assertEqual(output.status_code, 302)
            ast.return_value = False

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/test/regenerate')
            self.assertEqual(output.status_code, 400)

            data = {'csrf_token': csrf_token}

            output = self.app.post('/test/regenerate', data=data)
            self.assertEqual(output.status_code, 400)

            data['regenerate'] = 'ticket'
            output = self.app.post('/test/regenerate', data=data)
            self.assertEqual(output.status_code, 400)

            data['regenerate'] = 'tickets'
            tests.create_projects_git(tests.HERE)
            output = self.app.post(
                '/test/regenerate', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="message">Tickets git repo updated</li>',
                output.data)

            data['regenerate'] = 'requests'
            output = self.app.post(
                '/test/regenerate', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<li class="message">Requests git repo updated</li>',
                output.data)

    def test_view_tags(self):
        """ Test the view_tags endpoint. """
        output = self.app.get('/foo/tags')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/tags')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE, bare=True)

        output = self.app.get('/test/tags')
        self.assertEqual(output.status_code, 200)
        self.assertIn('This project has not been tagged.', output.data)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))
        repo = pygit2.Repository(os.path.join(tests.HERE, 'test.git'))
        first_commit = repo.revparse_single('HEAD')
        tagger = pygit2.Signature('Alice Doe', 'adoe@example.com', 12347, 0)
        repo.create_tag(
            "0.0.1", first_commit.oid.hex, pygit2.GIT_OBJ_COMMIT, tagger,
            "Release 0.0.1")

        output = self.app.get('/test/tags')
        self.assertEqual(output.status_code, 200)
        self.assertIn('0.0.1', output.data)
        self.assertIn('<span class="tagid">', output.data)
        self.assertTrue(output.data.count('tagid'), 1)

    def test_edit_file(self):
        """ Test the edit_file endpoint. """

        output = self.app.get('/foo/edit/foo/f/sources')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            # No project registered in the DB
            output = self.app.get('/foo/edit/foo/f/sources')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            # No a repo admin
            output = self.app.get('/test/edit/foo/f/sources')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):

            # No associated git repo
            output = self.app.get('/test/edit/foo/f/sources')
            self.assertEqual(output.status_code, 404)

            tests.create_projects_git(tests.HERE, bare=True)

            output = self.app.get('/test/edit/foo/f/sources')
            self.assertEqual(output.status_code, 404)

            # Add some content to the git repo
            tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))
            tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))
            tests.add_binary_git_repo(
                os.path.join(tests.HERE, 'test.git'), 'test.jpg')
            tests.add_binary_git_repo(
                os.path.join(tests.HERE, 'test.git'), 'test_binary')

            output = self.app.get('/test/edit/master/foofile')
            self.assertEqual(output.status_code, 404)

            # Edit page
            output = self.app.get('/test/edit/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<a href="/test/tree/master">master</a>/sources</h2>',
                output.data)
            self.assertIn(
                '<textarea cols="140" rows="3 " id="textareaCode" '
                'name="content">', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # View what's supposed to be an image
            output = self.app.get('/test/edit/master/f/test.jpg')
            self.assertEqual(output.status_code, 400)
            self.assertIn('<p>Cannot edit binary files</p>', output.data)

            # Check file before the commit:
            output = self.app.get('/test/raw/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertEqual(output.data, 'foo\n bar')

            # No CSRF Token
            data = {
                'content': 'foo\n bar\n  baz',
                'commit_title': 'test commit',
                'commit_message': 'Online commits from the tests',
            }
            output = self.app.post('/test/edit/master/f/sources', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Edit - test - Pagure</title>', output.data)

            # Check that nothing changed
            output = self.app.get('/test/raw/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertEqual(output.data, 'foo\n bar')

            # Missing email
            data['csrf_token'] = csrf_token
            output = self.app.post('/test/edit/master/f/sources', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Edit - test - Pagure</title>', output.data)

            # Invalid email
            data['email'] = 'pingou@fp.o'
            output = self.app.post('/test/edit/master/f/sources', data=data)
            self.assertIn(
                '<title>Edit - test - Pagure</title>', output.data)

            # Works
            data['email'] = 'bar@pingou.com'
            data['branch'] = 'master'
            output = self.app.post(
                '/test/edit/master/f/sources', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Logs - test - Pagure</title>', output.data)
            self.assertIn(
                '<li class="message">Changes committed</li>', output.data)

            # Check file after the commit:
            output = self.app.get('/test/raw/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertEqual(output.data, 'foo\n bar\n  baz')

            # Add a fork of a fork
            item = pagure.lib.model.Project(
                user_id=1,  # pingou
                name='test3',
                description='test project #3',
                parent_id=1,
                hook_token='aaabbbppp',
            )
            self.session.add(item)
            self.session.commit()

            tests.add_content_git_repo(
                os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
            tests.add_readme_git_repo(
                os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
            tests.add_commit_git_repo(
                os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'),
                ncommits=10)

            output = self.app.get('/fork/pingou/test3/edit/master/f/sources')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<a href="/fork/pingou/test3/tree/master">'
                'master</a>/sources</h2>', output.data)
            self.assertIn(
                '<textarea cols="140" rows="13 " id="textareaCode" '
                'name="content">', output.data)

    @patch('pagure.ui.repo.admin_session_timedout')
    def test_change_ref_head(self,ast):
        """ Test the change_ref_head endpoint. """
        ast.return_value = False

        output = self.app.post('/foo/default/branch/')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/foo/default/branch/')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.post('/test/default/branch/')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            repo = tests.create_projects_git(tests.HERE)
            output = self.app.post('/test/default/branch/',
                                    follow_redirects=True) # without git branch
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            self.assertIn(
                '<select id="branches" name="branches"></select>', output.data)
            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            repo_obj = pygit2.Repository(repo[0])
            tree = repo_obj.index.write_tree()
            author = pygit2.Signature(
                'Alice Author', 'alice@authors.tld')
            committer = pygit2.Signature(
                'Cecil Committer', 'cecil@committers.tld')
            repo_obj.create_commit(
                'refs/heads/master',  # the name of the reference to update
                author,
                committer,
                'Add sources file for testing',
                # binary string representing the tree object ID
                tree,
                # list of binary strings representing parents of the new commit
                []
            )
            repo_obj.create_branch("feature",repo_obj.head.get_object())

            data = {
                'branches': 'feature',
                'csrf_token': csrf_token,
            }

            output = self.app.post('/test/default/branch/',     # changing head to feature branch
                                    data=data,
                                    follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertIn(
                '<select id="branches" name="branches">', output.data)
            self.assertTrue(
                '<li class="message">Default branch updated to feature</li>'
                in output.data)

            data = {
                'branches': 'master',
                'csrf_token': csrf_token,
            }

            output = self.app.post('/test/default/branch/',     # changing head to master branch
                                    data=data,
                                    follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertIn(
                '<select id="branches" name="branches">', output.data)
            self.assertTrue(
                '<li class="message">Default branch updated to master</li>'
                in output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagureFlaskRepotests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
