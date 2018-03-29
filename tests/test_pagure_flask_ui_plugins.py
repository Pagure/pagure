# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']

import unittest
import sys
import os
import wtforms

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import pagure.lib.plugins
import pagure.hooks
import tests


class FakeForm(wtforms.Form):
    ''' Form to configure the mail hook. '''
    field1 = wtforms.TextField(
        'Title', [pagure.hooks.RequiredIf('active')]
    )
    field2 = wtforms.BooleanField(
        'Title2', [wtforms.validators.Optional()]
    )


class PagureFlaskPluginstests(tests.SimplePagureTest):
    """ Tests for flask plugins controller of pagure """

    def test_get_plugin_names(self):
        """ Test the get_plugin_names function. """
        names = pagure.lib.plugins.get_plugin_names()
        self.assertEqual(
            sorted(names),
            [
                'Block Un-Signed commits',  'Block non fast-forward pushes',
                'Fedmsg', 'IRC', 'Mail', 'Pagure', 'Pagure CI',
                'Pagure requests', 'Pagure tickets', 'Read the Doc',
            ]
        )

    def test_get_plugin(self):
        """ Test the get_plugin function. """
        name = pagure.lib.plugins.get_plugin('Mail')
        self.assertEqual(str(name), "<class 'pagure.hooks.mail.Mail'>")

    def test_view_plugin_page(self):
        """ Test the view_plugin_page endpoint. """

        # No Git repo
        output = self.app.get('/foo/settings/Mail')
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(self.app.application, user):
            output = self.app.get('/foo/settings/Mail')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(os.path.join(self.path, 'repos'))

            output = self.app.get('/test/settings/Mail')
            self.assertEqual(output.status_code, 403)

        # User not logged in
        output = self.app.get('/test/settings/Mail')
        self.assertEqual(output.status_code, 302)

        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/settings/Mail')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<form action="/test/settings/Mail" method="post">',
                output_text)
            self.assertIn(
                '<label for="mail_to">Mail to</label>',
                output_text)

            csrf_token = output_text.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'active': True,
                'mail_to': 'pingou@fp.org',
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/test/settings/Mail', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output.get_data(as_text=True))
            self.assertIn(
                '</button>\n                      Hook Mail activated', output.get_data(as_text=True))

            data = {
                'mail_to': '',
                'csrf_token': csrf_token,
            }

            output = self.app.post(
                '/test/settings/Mail', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<section class="settings">\n  <h3>Settings for test</h3>',
                output.get_data(as_text=True))
            self.assertIn(
                '</button>\n                      Hook Mail deactivated', output.get_data(as_text=True))

    def test_RequiredIf(self):
        """ Test the behavior of the RequiredIf validator. """
        form = FakeForm()

        try:
            form.validate()
        except Exception as err:
            self.assertEqual(
                str(err), 'no field named "active" in form')


if __name__ == '__main__':
    unittest.main(verbosity=2)
