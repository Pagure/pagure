# -*- coding: utf-8 -*-

"""
 (c) 2019 - Copyright Red Hat Inc

 Authors:
   Michal Konecny <mkonecny@redhat.com>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import sys
import os
import json

from mock import patch

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import tests  # noqa: E402


class PagureFlaskApiPluginViewtests(tests.Modeltests):
    """Tests for the flask API of pagure for viewing plugins"""

    def test_view_plugin(self):
        """Test viewing every plugin available in pagure."""

        output = self.app.get("/api/0/_plugins")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "plugins": [
                    {"Block Un-Signed commits": []},
                    {"Block non fast-forward pushes": ["branches"]},
                    {"Fedmsg": []},
                    {
                        "IRC": [
                            "server",
                            "port",
                            "room",
                            "nick",
                            "nick_pass",
                            "join",
                            "ssl",
                        ]
                    },
                    {"Mail": ["mail_to"]},
                    {"Mirroring": ["target", "public_key", "last_log"]},
                    {"Pagure": []},
                    {
                        "Pagure CI": [
                            "ci_type",
                            "ci_url",
                            "ci_job",
                            "active_commit",
                            "active_pr",
                        ]
                    },
                    {"Pagure requests": []},
                    {"Pagure tickets": []},
                    {"Prevent creating new branches by git push": []},
                    {"Read the Doc": ["api_url", "api_token", "branches"]},
                ],
                "total_plugins": 12,
            },
        )

    @patch.dict("pagure.config.config", {"DISABLED_PLUGINS": ["IRC"]})
    def test_view_plugin_disabled(self):
        """Test viewing every plugin available in pagure with one plugin disabled."""

        output = self.app.get("/api/0/_plugins")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            data,
            {
                "plugins": [
                    {"Block Un-Signed commits": []},
                    {"Block non fast-forward pushes": ["branches"]},
                    {"Fedmsg": []},
                    {"Mail": ["mail_to"]},
                    {"Mirroring": ["target", "public_key", "last_log"]},
                    {"Pagure": []},
                    {
                        "Pagure CI": [
                            "ci_type",
                            "ci_url",
                            "ci_job",
                            "active_commit",
                            "active_pr",
                        ]
                    },
                    {"Pagure requests": []},
                    {"Pagure tickets": []},
                    {"Prevent creating new branches by git push": []},
                    {"Read the Doc": ["api_url", "api_token", "branches"]},
                ],
                "total_plugins": 12,
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
