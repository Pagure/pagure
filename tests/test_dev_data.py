# -*- coding: utf-8 -*-

"""
 (c) 2019 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import os
import subprocess
import sys
import unittest

import six


REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

import tests  # noqa


class TestDevData(tests.Modeltests):
    """This test class contains tests pertaining to the dev-data utility
    script."""

    maxDiff = None

    def test_dev_data_all(self):
        """Check how dev-data --all performs"""

        config_path = os.path.join(self.path, "config")
        with open(config_path, "w") as f:
            f.write("DB_URL = 'sqlite:///%s/db_dev_data.sqlite'\n" % self.path)
            f.write("GIT_FOLDER = '%s/repos'\n" % self.path)
            f.write(
                "BROKER_URL = 'redis+socket://%(global_path)s/broker'\n"
                % self.config_values
            )
            f.write("CELERY_CONFIG = {'task_always_eager': True}\n")

        env = {
            "USER_NAME": "testuser",
            "USER_EMAIL": "testuser@example.com",
            "FORCE_DELETE": "yes",
            "PAGURE_CONFIG": config_path,
        }
        proc1 = subprocess.Popen(
            [sys.executable, "dev-data.py", "--all"],
            cwd=REPO_PATH,
            stdout=subprocess.PIPE,
            env=env,
        )
        stdout, stderr = proc1.communicate()
        if isinstance(stdout, six.binary_type):
            stdout = stdout.decode("utf-8")
        output = (
            """Database created
User created: pingou <bar@pingou.com>, testing123
User created: foo <foo@bar.com>, testing123
User created: testuser <testuser@example.com>, testing123
Created "admin" group. Pingou is a member.
Created "group" group. Pingou is a member.
Created "rel-eng" group. Pingou is a member.
git folder already deleted
docs folder already deleted
tickets folder already deleted
requests folder already deleted

WARNING: Deleting all data from sqlite:///%s/db_dev_data.sqlite
"""
            % self.path
        )

        self.assertEqual(len(stdout.split("\n")), 14)
        self.assertEqual(stdout, output)

    def test_dev_data_delete(self):
        """Check how dev-data --init --delete performs"""

        config_path = os.path.join(self.path, "config")

        env = {
            "USER_NAME": "testuser",
            "USER_EMAIL": "testuser@example.com",
            "FORCE_DELETE": "yes",
            "PAGURE_CONFIG": config_path,
        }
        proc1 = subprocess.Popen(
            [sys.executable, "dev-data.py", "--init", "--delete"],
            cwd=REPO_PATH,
            stdout=subprocess.PIPE,
            env=env,
        )
        stdout, stderr = proc1.communicate()
        if isinstance(stdout, six.binary_type):
            stdout = stdout.decode("utf-8")
        output = (
            """Database created

WARNING: Deleting all data from %s
"""
            % self.dbpath
        )

        self.assertEqual(len(stdout.split("\n")), 4)
        self.assertEqual(stdout.split("\n"), output.split("\n"))

    def test_dev_data_init(self):
        """Check how dev-data --init performs"""

        config_path = os.path.join(self.path, "config")

        env = {
            "USER_NAME": "testuser",
            "USER_EMAIL": "testuser@example.com",
            "FORCE_DELETE": "yes",
            "PAGURE_CONFIG": config_path,
        }
        proc1 = subprocess.Popen(
            [sys.executable, "dev-data.py", "--init"],
            cwd=REPO_PATH,
            stdout=subprocess.PIPE,
            env=env,
        )
        stdout, stderr = proc1.communicate()
        if isinstance(stdout, six.binary_type):
            stdout = stdout.decode("utf-8")
        output = "Database created\n"

        self.assertEqual(len(stdout.split("\n")), 2)
        self.assertEqual(stdout.split("\n"), output.split("\n"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
