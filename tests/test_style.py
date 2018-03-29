#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

Tests for flake8 compliance of the code

"""

from __future__ import unicode_literals

import os
import subprocess
import sys
import unittest


REPO_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'pagure'))


class TestStyle(unittest.TestCase):
    """This test class contains tests pertaining to code style."""
    def test_code_with_flake8(self):
        """Enforce PEP-8 compliance on the codebase.

        This test runs flake8 on the code, and will fail if it returns a non-zero exit code.
        """
        # We ignore E712, which disallows non-identity comparisons with True and False
        flake8_command = [sys.executable, '-m', 'flake8', '--ignore=E712,W503', REPO_PATH]

        self.assertEqual(subprocess.call(flake8_command), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
