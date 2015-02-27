#-*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib
import tests


class ProgitLibtests(tests.Modeltests):
    """ Tests for progit.lib """

    def test_get_next_id(self):
        """ Test the get_next_id function of progit.lib. """
        tests.create_projects(self.session)
        self.assertEqual(1, progit.lib.get_next_id(self.session, 1))


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitLibtests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
