# coding=utf-8
"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Slavek Kabrda <bkabrda@redhat.com>

"""

from __future__ import unicode_literals, absolute_import

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import os
import sys

from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.hooks
import pagure.lib.plugins
import tests


class EnabledForAll(pagure.hooks.BaseHook):
    name = "EnabledForAll"

    @classmethod
    def is_enabled_for(cls, project):
        return True

class DisabledForAll(pagure.hooks.BaseHook):
    name = "DisabledForAll"
    # disabled for all is the default

class PagureLibtests_plugins(tests.Modeltests):
    """
    Test the pagure.lib.plugins module
    """

    maxDiff = None

    @patch("pagure.lib.plugins.load")
    def test_plugin_is_enabled_for(self, load):
        """ Test the is_enabled_for method of plugins is properly
        handled by pagure.lib.plugins.get_enabled_plugins.
        """
        tests.create_projects(self.session)
        project = pagure.lib.query._get_project(self.session, "test")

        load.return_value = [EnabledForAll]
        self.assertEqual(
            pagure.lib.plugins.get_enabled_plugins(project),
            [(EnabledForAll, None)]
        )

        load.return_value = [DisabledForAll]
        self.assertEqual(
            pagure.lib.plugins.get_enabled_plugins(project),
            []
        )

    @patch("pagure.lib.plugins.load")
    def test_get_plugin_names(self, load):
        """ Test the get_plugin_names method with plugins that don't
        have backref.
        """
        load.return_value = [EnabledForAll]
        self.assertEqual(pagure.lib.plugins.get_plugin_names(), [])
        self.assertEqual(
            pagure.lib.plugins.get_plugin_names(without_backref=True),
            ['EnabledForAll']
        )
