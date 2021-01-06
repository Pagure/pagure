#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

Tests for flake8 compliance of the code

"""

from __future__ import unicode_literals, absolute_import

import os
import subprocess
import sys
import unittest

import six

REPO_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "pagure")
)
TESTS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__)))


class TestStyle(unittest.TestCase):
    """This test class contains tests pertaining to code style."""

    def test_code_with_flake8(self):
        """Enforce PEP-8 compliance on the codebase.

        This test runs flake8 on the code, and will fail if it returns a
        non-zero exit code.
        """
        # We ignore E712, which disallows non-identity comparisons with True and False
        # We ignore W503, which disallows line break before binary operator
        flake8_command = [
            sys.executable,
            "-m",
            "flake8",
            "--ignore=E712,W503,E203,E902",
            "--max-line-length=80",
            REPO_PATH,
        ]

        # check if we have an old flake8 or not
        import flake8

        flake8_v = flake8.__version__.split(".")
        for idx, val in enumerate(flake8_v):
            try:
                val = int(val)
            except ValueError:
                pass
            flake8_v[idx] = val
        old_flake = tuple(flake8_v) < (3, 0)

        if old_flake:
            raise unittest.SkipTest("Flake8 version too old to be useful")

        proc = subprocess.Popen(
            flake8_command, stdout=subprocess.PIPE, cwd=REPO_PATH
        )
        print(proc.communicate())

        self.assertEqual(proc.returncode, 0)

    @unittest.skipIf(
        not (six.PY3 and sys.version_info.minor >= 6),
        "Black is only available in python 3.6+",
    )
    def test_code_with_black(self):
        """Enforce black compliance on the codebase.

        This test runs black on the code, and will fail if it returns a
        non-zero exit code.
        """
        black_command = [
            sys.executable,
            "-m",
            "black",
            "-l",
            "79",
            "--check",
            "--diff",
            "--exclude",
            '"/(\.eggs|\.git|\.hg|\.mypy_cache|\.nox|\.tox|\.venv|_build|buck-out|build|dist)/"',
            REPO_PATH,
            TESTS_PATH,
        ]
        proc = subprocess.Popen(
            black_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=REPO_PATH,
        )
        stdout, stderr = proc.communicate()
        print("stdout: ")
        print(stdout.decode("utf-8"))
        print("stderr: ")
        print(stderr.decode("utf-8"))

        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
