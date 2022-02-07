#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

Tests the fnmatch method of the stdlib to ensure it works as expected
elsewhere in the code.

"""

from __future__ import unicode_literals, absolute_import

import os
import sys
import unittest

import fnmatch


class FnmatchTests(unittest.TestCase):
    """Tests for the streaming server."""

    def test_fnmatch(self):
        """Test the matching done by fnmatch."""
        matrix = [
            ["pagure", "*", True],
            ["ns/pagure", "*", True],
            ["forks/user/ns/pagure", "*", True],
            ["forks/user/pagure", "*", True],
            ["pagure", "rpms/*", False],
            ["rpms/pagure", "rpms/*", True],
            ["forks/user/pagure", "rpms/*", False],
            ["forks/user/pagure", "rpms/*", False],
            ["pagure", "pagure", True],
            ["rpms/pagure", "pagure", False],
            ["forks/user/pagure", "pagure", False],
            ["forks/user/pagure", "pagure", False],
            ["pagure", "pag*", True],
            ["rpms/pagure", "pag*", False],
            ["forks/user/pagure", "pag*", False],
            ["forks/user/pagure", "pag*", False],
        ]
        for row in matrix:
            self.assertEqual(fnmatch.fnmatch(row[0], row[1]), row[2])


if __name__ == "__main__":
    unittest.main(verbosity=2)
