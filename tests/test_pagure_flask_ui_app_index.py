# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

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

import pagure.lib.query
import tests


class PagureFlaskAppIndextests(tests.Modeltests):
    """ Tests for the index page of flask app controller of pagure """

    def test_index_logged_out(self):
        """ Test the index endpoint when logged out. """

        output = self.app.get('/')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<title>Home - Pagure</title>', output_text)
        self.assertIn(
            '<h3 class="m-0 font-weight-bold">All Projects '
            '<span class="badge badge-secondary">0</span></h3>',
            output_text)

        tests.create_projects(self.session)

        output = self.app.get('/?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<h3 class="m-0 font-weight-bold">All Projects '
            '<span class="badge badge-secondary">3</span></h3>',
            output.get_data(as_text=True))

    def test_index_logged_in(self):
        """
            Test the index endpoint when logged in.
            It should redirect to the userdash.
        """
        tests.create_projects(self.session)

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
        with tests.user_set(self.app.application, user):
            output = self.app.get('/', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<span class="btn btn-outline-secondary disabled '
                'opacity-100 border-0 ml-auto font-weight-bold">'
                '1 Projects</span>\n',
                output_text)
            self.assertNotIn(
                '<h3 class="m-0 font-weight-bold">All Projects '
                '<span class="badge badge-secondary">3</span></h3>',
                output_text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
