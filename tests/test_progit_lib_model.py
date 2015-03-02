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

from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib
import tests


class ProgitLibModeltests(tests.Modeltests):
    """ Tests for progit.lib.model """

    def test_user__repr__(self):
        """ Test the User.__repr__ function of progit.lib.model. """
        item = progit.lib.search_user(self.session, email='foo@bar.com')
        self.assertEqual(str(item), 'User: 2 - name foo')
        self.assertEqual('foo', item.user)
        self.assertEqual('foo', item.username)
        self.assertEqual([], item.groups)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitLibModeltests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
