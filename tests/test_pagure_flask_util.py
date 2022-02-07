# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import sys
import os

from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

from pagure.utils import ssh_urlpattern
import tests


class PagureUtilSSHPatterntests(tests.Modeltests):
    """Tests for the ssh_urlpattern in pagure.util"""

    def test_ssh_pattern_valid(self):
        """Test the ssh_urlpattern with valid patterns."""
        patterns = [
            "ssh://user@host.com/repo.git",
            "git+ssh://user@host.com/repo.git",
            "ssh://user@host.lcl:/path/to/repo.git",
            "git@github.com:user/project.git",
            "ssh://user@host.org/target",
            "git+ssh://user@host.org/target",
            "git+ssh://user@host.lcl:/path/to/repo.git",
        ]
        for pattern in patterns:
            print(pattern)
            self.assertIsNotNone(ssh_urlpattern.match(pattern))

    def test_ssh_pattern_invalid(self):
        """Test the ssh_urlpattern with invalid patterns."""
        patterns = [
            "http://user@host.com/repo.git",
            "git+http://user@host.com/repo.git",
            "https://user@host.com/repo.git",
            "git+https://user@host.com/repo.git",
            "ssh://localhost/repo.git",
            "ssh://host.com/repo.git",
            "git+ssh://localhost/repo.git",
            "ssh://0.0.0.0/repo.git",
            "git+ssh://0.0.0.0/repo.git",
            "git+ssh://host.com/repo.git",
            "ssh://127.0.0.1/repo.git",
            "git+ssh://127.0.0.1/repo.git",
        ]
        for pattern in patterns:
            print(pattern)
            self.assertIsNone(ssh_urlpattern.match(pattern))


if __name__ == "__main__":
    unittest.main(verbosity=2)
