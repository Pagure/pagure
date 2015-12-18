# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

import json
from mock import patch

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
        pagure.ui.repo.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = tests.HERE
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            tests.HERE, 'requests')
        self.app = pagure.APP.test_client()

    def test_index(self):
        """ Test the index endpoint. """

        output = self.app.get('/')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h2 class=" m-b-1">All Projects '
            '<span class="label label-default">0</span></h2>', output.data)

        tests.create_projects(self.session)

        output = self.app.get('/?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h2 class=" m-b-1">All Projects '
            '<span class="label label-default">2</span></h2>', output.data)

        # Add a 3rd project with a long description
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test3',
            description='test project #3 with a very long description',
            hook_token='aaabbbeee',
        )
        self.session.add(item)
        self.session.commit()

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/?repopage=abc&forkpage=def')
            self.assertIn(
                'My Projects <span class="label label-default">0</span>',
                output.data)
            self.assertIn(
                'My Forks <span class="label label-default">0</span>',
                output.data)
            self.assertEqual(
                output.data.count('<p>No projects found</p>'), 2)
            self.assertEqual(
                output.data.count('<div class="card-header">'), 2)

    def test_view_users(self):
        """ Test the view_users endpoint. """

        output = self.app.get('/users/?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h2 class="m-b-1">\n        Users <span class="label '
            'label-default">2</span></h2', output.data)
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
            '<section class="project_list container p-t-2" id="repos">',
            output.data)
        self.assertIn(
            '<h2 class=" m-b-1">Projects '
            '<span class="label label-default">0</span></h2>', output.data)
        self.assertIn(
            '<section class="project_list container p-t-2" id="forks">',
            output.data)
        self.assertIn(
            '<h2 class=" m-b-1">Forks <span class="label '
            'label-default">0</span></h2', output.data)

        tests.create_projects(self.session)
        self.gitrepos = tests.create_projects_git(
            pagure.APP.config['GIT_FOLDER'])

        output = self.app.get('/user/pingou?repopage=abc&forkpage=def')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<section class="project_list container p-t-2" id="repos">',
            output.data)
        self.assertIn(
            '<h2 class=" m-b-1">Projects '
            '<span class="label label-default">2</span></h2>', output.data)
        self.assertIn(
            '<section class="project_list container p-t-2" id="forks">',
            output.data)
        self.assertIn(
            '<h2 class=" m-b-1">Forks <span class="label '
            'label-default">0</span></h2', output.data)

    def test_new_project(self):
        """ Test the new_project endpoint. """
        # Before
        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(os.path.exists(
            os.path.join(tests.HERE, 'project#1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(tests.HERE, 'tickets', 'project#1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(tests.HERE, 'docs', 'project#1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(tests.HERE, 'requests', 'project#1.git')))

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'description': 'Project #1',
            }

            output = self.app.post('/new/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)
            self.assertIn(
                '<small>\n                      This field is required.'
                '&nbsp;\n                    </small>', output.data)

            data['name'] = 'project-1'
            output = self.app.post('/new/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)
            self.assertNotIn(
                '<small>\n                      This field is required.'
                '&nbsp;\n                    </small>', output.data)

            data['csrf_token'] =  csrf_token
            output = self.app.post('/new/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn('<strong>Create new Project</strong>', output.data)
            self.assertIn(
                '</button>\n                      No user &#34;username&#34; found',
                output.data)

        user.username = 'foo'
        with tests.user_set(pagure.APP, user):
            data['csrf_token'] =  csrf_token
            output = self.app.post('/new/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>Project #1</p>' in output.data)
            self.assertIn(
                '</button>\n                      Project &#34;project-1&#34; created',
                output.data)

        # After
        projects = pagure.lib.search_projects(self.session)
        self.assertEqual(len(projects), 1)
        self.assertTrue(os.path.exists(
            os.path.join(tests.HERE, 'project-1.git')))
        self.assertTrue(os.path.exists(
            os.path.join(tests.HERE, 'tickets', 'project-1.git')))
        self.assertTrue(os.path.exists(
            os.path.join(tests.HERE, 'docs', 'project-1.git')))
        self.assertTrue(os.path.exists(
            os.path.join(tests.HERE, 'requests', 'project-1.git')))

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
                'ssh_key': 'this is my ssh key',
            }

            output = self.app.post('/settings/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '<textarea class="form-control" id="ssh_key" name="ssh_key">'
                'this is my ssh key</textarea>', output.data)

            data['csrf_token'] =  csrf_token

            output = self.app.post(
                '/settings/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '</button>\n                      Public ssh key updated'
                in output.data)
            self.assertIn(
                '<div class="card-header">\n          Basic Information\n'
                '      </div>', output.data)
            self.assertIn(
                '<textarea class="form-control" id="ssh_key" name="ssh_key">'
                'this is my ssh key</textarea>', output.data)

            ast.return_value = True
            output = self.app.get('/settings/')
            self.assertEqual(output.status_code, 302)

    def test_markdown_preview(self):
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
    def test_add_user_email(self, ast, send_email):
        """ Test the add_user_email endpoint. """
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
            self.assertEqual(output.data.count('bar@pingou.com'), 4)
            self.assertEqual(output.data.count('foobar@pingou.com'), 1)

            # User already has this email
            data = {
                'csrf_token':  csrf_token,
                'email': 'foo@pingou.com',
            }

            output = self.app.post(
                '/settings/email/add', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue("<strong>Add new email</strong>" in output.data)
            self.assertIn(
                'Invalid value, can&#39;t be any of: bar@pingou.com, '
                'foo@pingou.com.&nbsp;', output.data)
            self.assertEqual(output.data.count('foo@pingou.com'), 5)
            self.assertEqual(output.data.count('bar@pingou.com'), 4)
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


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagureFlaskApptests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
