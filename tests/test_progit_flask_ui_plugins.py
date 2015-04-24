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
import wtforms
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import pagure.hooks
import pagure.ui.plugins
import tests


class FakeForm(wtforms.Form):
    ''' Form to configure the mail hook. '''
    field1 = wtforms.TextField(
        'Title', [pagure.hooks.RequiredIf('active')]
    )
    field2 = wtforms.BooleanField(
        'Title2', [wtforms.validators.Optional()]
    )


class PagureFlaskPluginstests(tests.Modeltests):
    """ Tests for flask plugins controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskPluginstests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.plugins.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = tests.HERE
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = pagure.APP.test_client()

    def test_get_plugin_names(self):
        """ Test the get_plugin_names function. """
        names = pagure.ui.plugins.get_plugin_names()
        self.assertEqual(
            sorted(names),
            ['Fedmsg', 'IRC', 'Mail', 'pagure', 'pagure requests',
             'pagure tickets'])

    def test_get_plugin(self):
        """ Test the get_plugin function. """
        name = pagure.ui.plugins.get_plugin('Mail')
        self.assertEqual(str(name), "<class 'pagure.hooks.mail.Mail'>")

    def test_view_plugin_page(self):
        """ Test the view_plugin_page endpoint. """

        output = self.app.get('/foo/settings/Mail')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/foo/settings/Mail')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(tests.HERE)

            output = self.app.get('/test/settings/Mail')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/settings/Mail')
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<section class="settings">\n  <h3>Mail</h3>', output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'active': True,
                'mail_to': 'pingou@fp.org',
                'csrf_token': csrf_token,
            }

            output = self.app.post('/test/settings/Mail', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<section class="settings">\n  <h3>Mail</h3>', output.data)
            self.assertIn(
                '<li class="message">Hook activated</li>', output.data)

            data = {
                'mail_to': '',
                'csrf_token': csrf_token,
            }

            output = self.app.post('/test/settings/Mail', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<section class="settings">\n  <h3>Mail</h3>', output.data)
            self.assertIn(
                '<li class="message">Hook inactived</li>', output.data)

    def test_RequiredIf(self):
        """ Test the behavior of the RequiredIf validator. """
        form = FakeForm()

        try:
            form.validate()
        except Exception, err:
            self.assertEqual(
                str(err), 'no field named "active" in form')


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagureFlaskPluginstests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
