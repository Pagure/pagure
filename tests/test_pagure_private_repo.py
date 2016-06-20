# -*- coding: utf-8 -*-

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


class PagurePrivateRepotest(tests.Modeltests):
    """ Tests for private repo in pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagurePrivateRepotest, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.APP.config['DATAGREPPER_URL'] = None
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
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            tests.HERE, 'requests')
        self.app = pagure.APP.test_client()

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

        user.username='pingou'
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


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagurePrivateRepotest)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
