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

import progit.lib.git
import tests


class ProgitLibGittests(tests.Modeltests):
    """ Tests for progit.lib.git """

    def test_write_gitolite_acls(self):
        """ Test the write_gitolite_acls function of progit.lib.git. """
        tests.create_projects(self.session)

        here = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        outputconf = os.path.join(here, 'test_gitolite.conf')

        progit.lib.git.write_gitolite_acls(self.session, outputconf)

        self.assertTrue(os.path.exists(outputconf))

        with open(outputconf) as stream:
            data = stream.read()

        self.assertEqual(
            data,
            'repo test\n  R   = @all\n  RW+ = pingou\n\n'
            'repo docs/test\n  R   = @all\n  RW+ = pingou\n\n'
            'repo tickets/test\n  R   = @all\n  RW+ = pingou\n\n'
            'repo test2\n  R   = @all\n  RW+ = pingou\n\n'
            'repo docs/test2\n  R   = @all\n  RW+ = pingou\n\n'
            'repo tickets/test2\n  R   = @all\n  RW+ = pingou\n\n')



if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitLibGittests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
