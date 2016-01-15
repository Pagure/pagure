# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import datetime
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


class PagureFlaskLogintests(tests.Modeltests):
    """ Tests for flask app controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskLogintests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.APP.config['EMAIL_SEND'] = True
        pagure.APP.config['PAGURE_AUTH'] = 'local'
        pagure.SESSION = self.session
        pagure.ui.SESSION = self.session
        pagure.ui.login.SESSION = self.session

        self.app = pagure.APP.test_client()


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(PagureFlaskLogintests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
