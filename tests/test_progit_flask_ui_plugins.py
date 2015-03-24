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

    def test_index(self):
        """ Test the index endpoint. """

        output = self.app.get('/foo/settings/Mail')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/foo/settings/Mail')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.get('/test/settings/Mail')
            self.assertEqual(output.status_code, 403)

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
