# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import datetime
import unittest
import shutil
import sys
import os

import six
import json
import pygit2
from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskApptests(tests.Modeltests):
    """ Tests for flask app controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApptests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.filters.SESSION = self.session
        pagure.ui.repo.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = self.path
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            self.path, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            self.path, 'docs')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            self.path, 'requests')
        self.app = pagure.APP.test_client()

    def test_index(self):
        """ Test the index endpoint. """

        output = self.app.get('/')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h2 class="m-b-1">All Projects '
            '<span class="label label-default">0</span></h2>', output.data)

        tests.create_projects(self.session)

        output = self.app.get('/?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h2 class="m-b-1">All Projects '
            '<span class="label label-default">3</span></h2>', output.data)

        # Add a 3rd project with a long description
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project #3 with a very long description',
            hook_token='aaabbbeeefff',
        )
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser(username='foo')
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/?repopage=abc&forkpage=def')
            self.assertIn(
                'Projects <span class="label label-default">1</span>',
                output.data)
            self.assertIn(
                'Forks <span class="label label-default">0</span>',
                output.data)
            self.assertEqual(
                output.data.count('<p>No group found</p>'), 1)
            self.assertEqual(
                output.data.count('<div class="card-header">'), 6)

    def test_watch_list(self):
        ''' Test for watch list of a user '''

        user = tests.FakeUser(username='pingou')
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/')
            self.assertIn(
                '<div class="text-xs-center">You have no projects</div>',
                output.data)
            self.assertIn(
                '<p>You have no forks</p>',
                output.data)
            self.assertIn(
                '<p>No project in watch list</p>',
                output.data)

            tests.create_projects(self.session)

            output = self.app.get('/')
            self.assertIn(
                'My Projects <span class="label label-default">3</span>',
                output.data)
            self.assertIn(
                'My Forks <span class="label label-default">0</span>',
                output.data)
            self.assertIn(
                'My Watch List <span class="label label-default">3</span>',
                output.data)

    def test_view_users(self):
        """ Test the view_users endpoint. """

        output = self.app.get('/users/?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h2 class="m-b-1">\n      Users '
            '<span class="label label-default">2</span></h2>', output.data)
        self.assertIn(
            '<a class="project_link logo_link" href="/user/pingou">',
            output.data)
        self.assertIn(
            '<a class="project_link logo_link" href="/user/foo">',
            output.data)

    def test_view_user(self):
        """ Test the view_user endpoint. """

        output = self.app.get('/user/pingou?repopage=abc&forkpage=def')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'Projects <span class="label label-default">0</span>',
            output.data)
        self.assertIn(
            'Forks <span class="label label-default">0</span>',
            output.data)

        tests.create_projects(self.session)
        self.gitrepos = tests.create_projects_git(
            pagure.APP.config['GIT_FOLDER'])

        output = self.app.get('/user/pingou?repopage=abc&forkpage=def')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            'Projects <span class="label label-default">3</span>',
            output.data)
        self.assertIn(
            'Forks <span class="label label-default">0</span>', output.data)


    def test_new_project_when_turned_off(self):
        """ Test the new_project endpoint when new project creation is
        not allowed in the pagure instance. """

        #turn the project creation off
        pagure.APP.config['ENABLE_NEW_PROJECTS'] = False

        # Before
        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'project-1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'tickets', 'project-1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'docs', 'project-1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'requests', 'project-1.git')))

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 404)

            #just get the csrf token
            pagure.APP.config['ENABLE_NEW_PROJECTS'] = True
            output = self.app.get('/new/')
            pagure.APP.config['ENABLE_NEW_PROJECTS'] = False

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'description': 'Project #1',
                'name': 'project-1',
            }

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            data['csrf_token'] =  csrf_token
            output = self.app.post('/new/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 404)

        #After
        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'project-1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'tickets', 'project-1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'docs', 'project-1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'requests', 'project-1.git')))

        pagure.APP.config['ENABLE_NEW_PROJECTS'] = True

    def test_new_project(self):
        """ Test the new_project endpoint. """
        # Before
        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'project#1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'tickets', 'project#1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'docs', 'project#1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'requests', 'project#1.git')))

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                u'<strong>Create new Project</strong>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'description': 'Project #1',
            }

            output = self.app.post('/new/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                u'<strong>Create new Project</strong>', output.data)
            self.assertIn(
                u'<small>\n            This field is required.&nbsp;\n'
                '          </small>', output.data)

            data['name'] = 'project-1'
            output = self.app.post('/new/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)
            self.assertNotIn(
                u'<small>\n            This field is required.&nbsp;\n'
                '          </small>', output.data)

            data['csrf_token'] =  csrf_token
            output = self.app.post('/new/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)
            self.assertIn(
                u'</button>\n                      No user '
                '&#34;username&#34; found\n                    </div>',
                output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            data['csrf_token'] =  csrf_token
            output = self.app.post('/new/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                u'<div class="projectinfo m-t-1 m-b-1">\nProject #1        </div>',
                output.data)
            self.assertIn(u'<p>This repo is brand new!</p>', output.data)
            self.assertIn(
                u'<title>Overview - project-1 - Pagure</title>', output.data)

        # After
        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 1)
        self.assertTrue(os.path.exists(
            os.path.join(self.path, 'project-1.git')))
        self.assertTrue(os.path.exists(
            os.path.join(self.path, 'tickets', 'project-1.git')))
        self.assertTrue(os.path.exists(
            os.path.join(self.path, 'docs', 'project-1.git')))
        self.assertTrue(os.path.exists(
            os.path.join(self.path, 'requests', 'project-1.git')))

    def test_non_ascii_new_project(self):
        """ Test the new_project endpoint with a non-ascii project. """
        # Before
        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'project-1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'tickets', 'project-1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'docs', 'project-1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(self.path, 'requests', 'project-1.git')))

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                b'<strong>Create new Project</strong>', output.data)

            csrf_token = output.data.decode('utf-8').split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'description': 'Prõjéctö #1',
                'name': 'project-1',
                'csrf_token':  csrf_token,
                'create_readme': True,
            }
            output = self.app.post('/new/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\nPrõjéctö #1        </div>',
                output.data if six.PY2 else output.data.decode('utf-8'))
            self.assertIn(
                '''<section class="readme">
                <h1>project-1</h1>
<p>Prõjéctö #1</p>
            </section>''', output.data if six.PY2 else output.data.decode('utf-8'))

            data = {
                'description': 'Мой первый суперский репозиторий',
                'name': 'project-2',
                'csrf_token':  csrf_token,
                'create_readme': True,
            }
            output = self.app.post('/new/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="projectinfo m-t-1 m-b-1">\nМой первый суперский репозиторий        </div>',
                output.data if six.PY2 else output.data.decode('utf-8'))
            self.assertIn(
                '''<section class="readme">
                <h1>project-2</h1>
<p>Мой первый суперский репозиторий</p>
            </section>''', output.data if six.PY2 else output.data.decode('utf-8'))

        # After
        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 2)
        for project in ['project-1', 'project-2']:
            self.assertTrue(os.path.exists(
                os.path.join(self.path, '%s.git' % project)))
            self.assertTrue(os.path.exists(
                os.path.join(self.path, 'tickets', '%s.git' % project)))
            self.assertTrue(os.path.exists(
                os.path.join(self.path, 'docs', '%s.git' % project)))
            self.assertTrue(os.path.exists(
                os.path.join(self.path, 'requests', '%s.git' % project)))

    @patch('pagure.ui.app.admin_session_timedout')
    def test_user_settings(self, ast):
        """ Test the user_settings endpoint. """
        ast.return_value = False
        self.test_new_project()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/settings/')
            self.assertEqual(output.status_code, 404)
            self.assertTrue('<h2>Page not found (404)</h2>' in output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/settings/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '<textarea class="form-control" id="ssh_key" name="ssh_key">'
                '</textarea>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'ssh_key': 'blah'
            }

            output = self.app.post('/settings/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)

            data['csrf_token'] =  csrf_token

            output = self.app.post(
                '/settings/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn('Invalid SSH keys', output.data)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn('>blah</textarea>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'ssh_key': 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDUkub32fZnNI'
                           '1zJYs43vhhx3c6IcYo4yzhw1gQ37BLhrrNeS6x8l5PKX4J8ZP5'
                           '1XhViPaLbeOpl94Vm5VSCbLy0xtY9KwLhMkbKj7g6vvfxLm2sT'
                           'Osb15j4jzIkUYYgIE7cHhZMCLWR6UA1c1HEzo6mewMDsvpQ9wk'
                           'cDnAuXjK3Q==',
                'csrf_token': csrf_token
            }

            output = self.app.post(
                '/settings/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn('Public ssh key updated', output.data)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '<textarea class="form-control" id="ssh_key" name="ssh_key">'
                'ssh-rsa AAAA', output.data)

            ast.return_value = True
            output = self.app.get('/settings/')
            self.assertEqual(output.status_code, 302)

    def patched_commit_exists(user, namespace, repo, githash):
        ''' Patched version of pagure.pfmarkdown._commit_exists to enforce
        returning true on some given hash without having us actually check
        the git repos.
        '''
        if githash in ['9364354', '9364354a', '9364354a4555ba17aa60f0dc844d70b74eb1aecd']:
            return True
        else:
            return False

    @patch(
        'pagure.pfmarkdown._commit_exists',
        MagicMock(side_effect=patched_commit_exists))
    def test_patched_markdown_preview(self):
        """ Test the markdown_preview endpoint. """

        data = {
            'content': 'test\n----\n\n * 1\n * item 2'
        }

        # CSRF missing
        output = self.app.post('/markdown/', data=data)
        self.assertEqual(output.status_code, 400)

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/settings/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '<textarea class="form-control" id="ssh_key" name="ssh_key">'
                '</textarea>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

        # With CSRF
        data['csrf_token'] = csrf_token
        output = self.app.post('/markdown/', data=data)
        self.assertEqual(output.status_code, 200)
        exp = """<h2>test</h2>
<ul>
<li>1</li>
<li>item 2</li>
</ul>"""
        self.assertEqual(output.data, exp)

        tests.create_projects(self.session)
        texts = [
            'pingou committed on test#9364354a4555ba17aa60f0dc844d70b74eb1aecd',
            'Cf commit 936435',  # 6 chars - not long enough
            'Cf commit 9364354',  # 7 chars - long enough
            'Cf commit 9364354a',  # 8 chars - still long enough
            'Cf commit 9364354a4555ba17aa60f0dc844d70b74eb1aecd',  # 40 chars
        ]
        expected = [
            # 'pingou committed on test#9364354a4555ba17aa60f0dc844d70b74eb1aecd',
            '<p>pingou committed on <a href="/test/c/9364354a4555ba17aa60f0dc844d70b74eb1aecd" '
            'title="Commit 9364354a4555ba17aa60f0dc844d70b74eb1aecd"'
            '>test#9364354a4555ba17aa60f0dc844d70b74eb1aecd</a></p>',
            # 'Cf commit 936435',
            '<p>Cf commit 936435</p>',
            # 'Cf commit 9364354',
            #'<p>Cf commit 9364354</p>',
            '<p>Cf commit<a href="/test/c/9364354" '
            'title="Commit 9364354"> 9364354</a></p>',
            # 'Cf commit 9364354a',
            '<p>Cf commit<a href="/test/c/9364354a" '
            'title="Commit 9364354a"> 9364354</a></p>',
            # 'Cf commit 9364354a4555ba17aa60f0dc844d70b74eb1aecd',
            '<p>Cf commit<a href="/test/c/9364354a4555ba17aa60f0dc844d70b74eb1aecd" '
            'title="Commit 9364354a4555ba17aa60f0dc844d70b74eb1aecd"'
            '> 9364354</a></p>',
        ]

        with pagure.APP.app_context():
            for idx, text in enumerate(texts):
                data = {
                    'content': text,
                    'csrf_token': csrf_token,
                }
                output = self.app.post('/markdown/?repo=test', data=data)
                self.assertEqual(output.status_code, 200)
                self.assertEqual(expected[idx], output.data)

    def test_markdown_preview(self):
        """ Test the markdown_preview endpoint with a non-existing commit.
        """

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/settings/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path), bare=True)
        text = 'Cf commit 9364354a4555ba17aa60f0d'
        exp = '<p>Cf commit 9364354a4555ba17aa60f0d</p>'

        with pagure.APP.app_context():
            data = {
                'content': text,
                'csrf_token': csrf_token,
            }
            output = self.app.post('/markdown/?repo=test', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertEqual(exp, output.data)

    def test_markdown_preview_valid_commit(self):
        """ Test the markdown_preview endpoint with an existing commit. """

        user = tests.FakeUser()
        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/settings/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path), bare=True)
        repopath = os.path.join(self.path, 'test.git')
        tests.add_content_git_repo(repopath)

        repo = pygit2.Repository(repopath)
        first_commit = repo.revparse_single('HEAD')

        text = 'Cf commit %s' % first_commit.oid.hex
        exp = '<p>Cf commit<a href="/test/c/{0}" title="Commit {0}"> {1}'\
        '</a></p>'.format(first_commit.oid.hex, first_commit.oid.hex[:7])

        with pagure.APP.app_context():
            data = {
                'content': text,
                'csrf_token': csrf_token,
            }
            output = self.app.post('/markdown/?repo=test', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertEqual(exp, output.data)

    @patch('pagure.ui.app.admin_session_timedout')
    def test_remove_user_email(self, ast):
        """ Test the remove_user_email endpoint. """
        ast.return_value = False
        self.test_new_project()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/settings/email/drop')
            self.assertEqual(output.status_code, 404)
            self.assertTrue('<h2>Page not found (404)</h2>' in output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/settings/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '<textarea class="form-control form-control-error" id="ssh_key" name="ssh_key">'
                '</textarea>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'email': 'foo@pingou.com',
            }

            output = self.app.post(
                '/settings/email/drop', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '<textarea class="form-control" id="ssh_key" name="ssh_key">'
                '</textarea>', output.data)
            self.assertIn(
                '</button>\n                      You must always have at least one email',
                output.data)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/settings/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '<textarea class="form-control form-control-error" id="ssh_key" name="ssh_key">'
                '</textarea>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'email': 'foo@pingou.com',
            }

            output = self.app.post(
                '/settings/email/drop', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertEqual(output.data.count('foo@pingou.com'), 4)

            data = {
                'csrf_token':  csrf_token,
                'email': 'foobar@pingou.com',
            }

            output = self.app.post(
                '/settings/email/drop', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '</button>\n                      You do not have the '
                'email: foobar@pingou.com, nothing to remove', output.data)

            data = {
                'csrf_token':  csrf_token,
                'email': 'foo@pingou.com',
            }

            output = self.app.post(
                '/settings/email/drop', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertEqual(output.data.count('foo@pingou.com'), 0)
            self.assertEqual(output.data.count('bar@pingou.com'), 3)

            output = self.app.post(
                '/settings/email/drop', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertEqual(output.data.count('foo@pingou.com'), 0)
            self.assertEqual(output.data.count('bar@pingou.com'), 3)

            ast.return_value = True
            output = self.app.post('/settings/email/drop', data=data)
            self.assertEqual(output.status_code, 302)

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.ui.app.admin_session_timedout')
    def test_add_api_user_email(self, ast, send_email):
        """ Test the add_api_user_email endpoint. """
        send_email.return_value = True
        ast.return_value = False
        self.test_new_project()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/settings/email/add')
            self.assertEqual(output.status_code, 404)
            self.assertTrue('<h2>Page not found (404)</h2>' in output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/settings/email/add')
            self.assertEqual(output.status_code, 200)

            self.assertTrue("<strong>Add new email</strong>" in output.data)
            self.assertIn(
                '<input class="form-control form-control-error" id="email" '
                'name="email" type="text" value="">', output.data)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/settings/email/add')
            self.assertEqual(output.status_code, 200)
            self.assertTrue("<strong>Add new email</strong>" in output.data)
            self.assertIn(
                '<input class="form-control form-control-error" id="email" '
                'name="email" type="text" value="">', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'email': 'foo2@pingou.com',
            }

            output = self.app.post(
                '/settings/email/add', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue("<strong>Add new email</strong>" in output.data)
            self.assertEqual(output.data.count('foo2@pingou.com'), 1)

            # New email
            data = {
                'csrf_token':  csrf_token,
                'email': 'foobar@pingou.com',
            }

            output = self.app.post(
                '/settings/email/add', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '</button>\n                      Email pending validation',
                output.data)
            self.assertEqual(output.data.count('foo@pingou.com'), 4)
            self.assertEqual(output.data.count('bar@pingou.com'), 5)
            self.assertEqual(output.data.count('foobar@pingou.com'), 2)

            # Email already pending
            output = self.app.post(
                '/settings/email/add', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n      '
                '<strong>Add new email</strong>', output.data)
            self.assertIn(
                '</button>\n                      This email is already '
                'pending confirmation', output.data)

            # User already has this email
            data = {
                'csrf_token':  csrf_token,
                'email': 'foo@pingou.com',
            }

            output = self.app.post(
                '/settings/email/add', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue("<strong>Add new email</strong>" in output.data)
            self.assertTrue(
                'Invalid value, can&#39;t be any of: bar@pingou.com, '
                'foo@pingou.com.&nbsp;' in output.data
                or
                'Invalid value, can&#39;t be any of: foo@pingou.com, '
                'bar@pingou.com.&nbsp;' in output.data
            )
            self.assertEqual(output.data.count('foo@pingou.com'), 6)
            self.assertEqual(output.data.count('bar@pingou.com'), 5)
            self.assertEqual(output.data.count('foobar@pingou.com'), 0)

            # Email registered by someone else
            data = {
                'csrf_token':  csrf_token,
                'email': 'foo@bar.com',
            }

            output = self.app.post(
                '/settings/email/add', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue("<strong>Add new email</strong>" in output.data)
            self.assertIn(
                'Invalid value, can&#39;t be any of: foo@bar.com.&nbsp;',
                output.data)

            ast.return_value = True
            output = self.app.post('/settings/email/add', data=data)
            self.assertEqual(output.status_code, 302)

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.ui.app.admin_session_timedout')
    def test_set_default_email(self, ast, send_email):
        """ Test the set_default_email endpoint. """
        send_email.return_value = True
        ast.return_value = False
        self.test_new_project()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/settings/email/default')
            self.assertEqual(output.status_code, 404)
            self.assertTrue('<h2>Page not found (404)</h2>' in output.data)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/settings/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '<textarea class="form-control" id="ssh_key" name="ssh_key">'
                '</textarea>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'email': 'foo@pingou.com',
            }

            output = self.app.post(
                '/settings/email/default', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertEqual(output.data.count('foo@pingou.com'), 4)

            # Set invalid default email
            data = {
                'csrf_token':  csrf_token,
                'email': 'foobar@pingou.com',
            }

            output = self.app.post(
                '/settings/email/default', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertEqual(output.data.count('foo@pingou.com'), 4)
            self.assertIn(
                '</button>\n                      You do not have the '
                'email: foobar@pingou.com, nothing to set',
                output.data)

            # Set default email
            data = {
                'csrf_token':  csrf_token,
                'email': 'foo@pingou.com',
            }

            output = self.app.post(
                '/settings/email/default', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertEqual(output.data.count('foo@pingou.com'), 4)
            self.assertIn(
                '</button>\n                      Default email set to: '
                'foo@pingou.com', output.data)

            ast.return_value = True
            output = self.app.post('/settings/email/default', data=data)
            self.assertEqual(output.status_code, 302)

    @patch('pagure.lib.notify.send_email')
    @patch('pagure.ui.app.admin_session_timedout')
    def test_reconfirm_email(self, ast, send_email):
        """ Test the reconfirm_email endpoint. """
        send_email.return_value = True
        ast.return_value = False
        self.test_new_project()

        # Add a pending email to pingou
        userobj = pagure.lib.search_user(self.session, username='pingou')

        self.assertEqual(len(userobj.emails), 2)

        email_pend = pagure.lib.model.UserEmailPending(
            user_id=userobj.id,
            email='foo@fp.o',
            token='abcdef',
        )
        self.session.add(email_pend)
        self.session.commit()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.post('/settings/email/resend')
            self.assertEqual(output.status_code, 404)
            self.assertTrue('<h2>Page not found (404)</h2>' in output.data)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/settings/')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '<textarea class="form-control" id="ssh_key" name="ssh_key">'
                '</textarea>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'email': 'foo@pingou.com',
            }

            output = self.app.post(
                '/settings/email/resend', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertEqual(output.data.count('foo@pingou.com'), 4)

            # Set invalid default email
            data = {
                'csrf_token':  csrf_token,
                'email': 'foobar@pingou.com',
            }

            output = self.app.post(
                '/settings/email/resend', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertEqual(output.data.count('foo@pingou.com'), 4)
            self.assertIn(
                '</button>\n                      This email address has '
                'already been confirmed', output.data)

            # Validate a non-validated email
            data = {
                'csrf_token':  csrf_token,
                'email': 'foo@fp.o',
            }

            output = self.app.post(
                '/settings/email/resend', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertEqual(output.data.count('foo@pingou.com'), 4)
            self.assertIn(
                '</button>\n                      Confirmation email re-sent',
                output.data)

            ast.return_value = True
            output = self.app.post('/settings/email/resend', data=data)
            self.assertEqual(output.status_code, 302)

    @patch('pagure.ui.app.admin_session_timedout')
    def test_confirm_email(self, ast):
        """ Test the confirm_email endpoint. """
        output = self.app.get('/settings/email/confirm/foobar')
        self.assertEqual(output.status_code, 302)

        ast.return_value = False

        # Add a pending email to pingou
        userobj = pagure.lib.search_user(self.session, username='pingou')

        self.assertEqual(len(userobj.emails), 2)

        email_pend = pagure.lib.model.UserEmailPending(
            user_id=userobj.id,
            email='foo@fp.o',
            token='abcdef',
        )
        self.session.add(email_pend)
        self.session.commit()

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            # Wrong token
            output = self.app.get(
                '/settings/email/confirm/foobar', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '</button>\n                      No email associated with this token.',
                output.data)

            # Confirm email
            output = self.app.get(
                '/settings/email/confirm/abcdef', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '</button>\n                      Email validated',
                output.data)

        userobj = pagure.lib.search_user(self.session, username='pingou')
        self.assertEqual(len(userobj.emails), 3)

        ast.return_value = True
        output = self.app.get('/settings/email/confirm/foobar')
        self.assertEqual(output.status_code, 302)


    def test_view_my_requests_no_user(self):
        """Test the view_user_requests endpoint."""
        output = self.app.get('/user/somenonexistentuser/requests')
        self.assertEqual(output.status_code, 404)

    @patch(
        'pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch(
        'pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_view_my_requests(self):
        """Test the view_user_requests endpoint. """
        # Create the PR
        tests.create_projects(self.session)
        repo = pagure.lib._get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='dev',
            repo_to=repo,
            branch_to='master',
            title='test pull-request #1',
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request #1')

        output = self.app.get('/user/pingou/requests')
        self.assertEqual(output.status_code, 200)
        self.assertIn('test pull-request #1', output.data)
        self.assertEqual(
            output.data.count('<tr class="pr-status pr-status-open"'),
            1)

        # Add a PR in a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test_fork',
            description='test project #1',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbttt',
        )
        self.session.add(item)
        repo = pagure.lib._get_project(
            self.session, 'test_fork', user='pingou')

        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='dev',
            repo_to=repo,
            branch_to='master',
            title='test pull-request #2',
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request #2')

        output = self.app.get('/user/pingou/requests')
        self.assertEqual(output.status_code, 200)
        self.assertIn('test pull-request #1', output.data)
        self.assertIn('test pull-request #2', output.data)
        self.assertEqual(
            output.data.count('<tr class="pr-status pr-status-open"'),
            2)

    def test_view_my_issues_no_user(self):
        """Test the view_user_issues endpoint with a missing user."""
        output = self.app.get('/user/somenonexistentuser/issues')
        self.assertEqual(output.status_code, 404)

    @patch(
        'pagure.lib.git.update_git', MagicMock(return_value=True))
    @patch(
        'pagure.lib.notify.send_email', MagicMock(return_value=True))
    def test_view_my_issues(self):
        """Test the view_user_issues endpoint when the user exists."""
        # Create the issue
        tests.create_projects(self.session)
        repo = pagure.lib._get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this for the second time',
            user='pingou',
            status='Open',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #1')

        output = self.app.get('/user/pingou/issues')
        self.assertEqual(output.status_code, 200)
        self.assertIn('Test issue #1', output.data)
        self.assertEqual(
            output.data.count('<tr class="issue-status issue-status-open"'),
            1)

        # Add an issue in a fork
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test_fork',
            description='test project #1',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbttt',
        )
        self.session.add(item)
        repo = pagure.lib._get_project(self.session, 'test_fork', user='foo')

        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #2',
            content='We should work on this for the second time',
            user='pingou',
            status='Open',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #2')

        # Test the assigned issue table.  Create issue then set the assignee
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #3',
            content='This issue created by foo, but assigned to pingou',
            user='foo',
            status='Open',
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue #3')

        msg = pagure.lib.add_issue_assignee(
            session=self.session,
            issue=msg,
            assignee='pingou',
            user='foo',
            ticketfolder=None)
        self.session.commit()
        self.assertEqual(msg, 'Issue assigned to pingou')

        output = self.app.get('/user/pingou/issues')
        self.assertEqual(output.status_code, 200)
        self.assertIn('Test issue #1', output.data)
        self.assertIn('Test issue #2', output.data)
        self.assertIn('Test issue #3', output.data)
        self.assertEqual(
            output.data.count('<tr class="issue-status issue-status-open"'), 3)

    def test_view_my_issues_tickets_turned_off(self):
        """Test the view_user_issues endpoint when the user exists and
        and ENABLE_TICKETS is False """

        # Turn off the tickets instance wide
        pagure.APP.config['ENABLE_TICKETS'] = False

        output = self.app.get('/user/pingou/issues')
        self.assertEqual(output.status_code, 404)
        pagure.APP.config['ENABLE_TICKETS'] = True

    @patch('pagure.ui.app.admin_session_timedout')
    def test_add_user_token(self, ast):
        """ Test the add_user_token endpoint. """
        ast.return_value = False
        self.test_new_project()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/settings/token/new/')
            self.assertEqual(output.status_code, 404)
            self.assertTrue('<h2>Page not found (404)</h2>' in output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/settings/token/new')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          <strong>'
                'Create a new token</strong>\n', output.data)
            self.assertIn(
                '<input type="checkbox" name="acls" value="create_project">',
                output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'acls': ['create_project', 'fork_project']
            }

            # missing CSRF
            output = self.app.post('/settings/token/new', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Create token - Pagure</title>', output.data)
            self.assertIn(
                '<div class="card-header">\n          <strong>'
                'Create a new token</strong>\n', output.data)
            self.assertIn(
                '<input type="checkbox" name="acls" value="create_project">',
                output.data)

            data = {
                'acls': ['new_project'],
                'csrf_token':  csrf_token
            }

            # Invalid ACLs
            output = self.app.post('/settings/token/new', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>Create token - Pagure</title>', output.data)
            self.assertIn(
                '<div class="card-header">\n          <strong>'
                'Create a new token</strong>\n', output.data)
            self.assertIn(
                '<input type="checkbox" name="acls" value="create_project">',
                output.data)

            data = {
                'acls': ['create_project', 'fork_project'],
                'csrf_token':  csrf_token
            }

            # All good
            output = self.app.post(
                '/settings/token/new', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<title>foo\'s settings - Pagure</title>', output.data)
            self.assertIn(
                '</button>\n                      Token created\n',
                output.data)
            self.assertEqual(
                output.data.count(
                    '<span class="text-success btn-align"><strong>Valid'
                    '</strong> until: '), 1)

            ast.return_value = True
            output = self.app.get('/settings/token/new')
            self.assertEqual(output.status_code, 302)

    @patch('pagure.ui.app.admin_session_timedout')
    def test_revoke_api_user_token(self, ast):
        """ Test the revoke_api_user_token endpoint. """
        ast.return_value = False
        self.test_new_project()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            # Token doesn't exist
            output = self.app.post('/settings/token/revoke/foobar')
            self.assertEqual(output.status_code, 404)
            self.assertTrue('<h2>Page not found (404)</h2>' in output.data)

            # Create the foobar API token but associated w/ the user 'foo'
            item = pagure.lib.model.Token(
                id='foobar',
                user_id=2,  # foo
                expiration=datetime.datetime.utcnow() \
                    + datetime.timedelta(days=30)
            )
            self.session.add(item)
            self.session.commit()

            # Token not associated w/ this user
            output = self.app.post('/settings/token/revoke/foobar')
            self.assertEqual(output.status_code, 404)
            self.assertTrue('<h2>Page not found (404)</h2>' in output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            # Missing CSRF token
            output = self.app.post(
                '/settings/token/revoke/foobar', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output.data)
            self.assertEqual(
                output.data.count(
                    '<span class="text-success btn-align"><strong>Valid'
                    '</strong> until: '), 1)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token': csrf_token
            }

            # All good - token is deleted
            output = self.app.post(
                '/settings/token/revoke/foobar', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output.data)
            self.assertEqual(
                output.data.count(
                    '<span class="text-success btn-align"><strong>Valid'
                    '</strong> until: '), 0)

            user = pagure.lib.get_user(self.session, key='foo')
            self.assertEqual(len(user.tokens), 1)
            expiration_dt = user.tokens[0].expiration

            # Token was already deleted - no changes
            output = self.app.post(
                '/settings/token/revoke/foobar', data=data,
                follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<title>foo's settings - Pagure</title>", output.data)
            self.assertEqual(
                output.data.count(
                    '<span class="text-success btn-align"><strong>Valid'
                    '</strong> until: '), 0)

            # Ensure the expiration date did not change
            user = pagure.lib.get_user(self.session, key='foo')
            self.assertEqual(len(user.tokens), 1)
            self.assertEqual(
                expiration_dt, user.tokens[0].expiration
            )

            ast.return_value = True
            output = self.app.get('/settings/token/new')
            self.assertEqual(output.status_code, 302)

if __name__ == '__main__':
    unittest.main(verbosity=2)
