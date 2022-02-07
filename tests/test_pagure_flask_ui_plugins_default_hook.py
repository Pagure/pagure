# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import json
import unittest
import shutil
import sys
import os

import flask
import pygit2
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.hooks.default
import pagure.lib.plugins
import pagure.lib.query
import tests


class PagureFlaskPluginDefaultHooktests(tests.Modeltests):
    """Tests for default_hook plugin of pagure"""

    def test_plugin_default_active_on_project(self):
        """Test that the default hook is active on random project."""

        tests.create_projects(self.session)
        test = pagure.lib.query.search_projects(self.session)[0]
        self.assertIsNone(pagure.hooks.default.Default.backref)
        self.assertTrue(pagure.hooks.default.Default.is_enabled_for(test))
        self.assertEqual(
            [(pagure.hooks.default.Default, None)],
            pagure.lib.plugins.get_enabled_plugins(test),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
