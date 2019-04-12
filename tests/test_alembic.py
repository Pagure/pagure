# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import os
import subprocess
import unittest

import six


REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestAlembic(unittest.TestCase):
    """This test class contains tests pertaining to alembic."""

    def test_alembic_history(self):
        """Enforce a linear alembic history.

        This test runs the `alembic history | grep ' (head), '` command,
        and ensure it returns only one line.
        """

        proc1 = subprocess.Popen(
            ["alembic", "history"], cwd=REPO_PATH, stdout=subprocess.PIPE
        )
        proc2 = subprocess.Popen(
            ["grep", " (head), "], stdin=proc1.stdout, stdout=subprocess.PIPE
        )
        stdout = proc2.communicate()[0]
        stdout = stdout.strip().decode("utf-8").split("\n")

        self.assertEqual(len(stdout), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
