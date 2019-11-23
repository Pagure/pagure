# -*- coding: utf-8 -*-

"""
 Authors:
   Julen Landa Alustiza <jlanda@fedoraproject.org>
"""

from __future__ import unicode_literals, absolute_import

import json
import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import tests
import pagure.lib.query


class PagureFlaskApiProjectTagstests(tests.Modeltests):
    """ Tests for the flask API of pagure project tags """

    def test_api_project_tags_no_project(self):
        """ Test the api_project_tags function.  """
        output = self.app.get("/api/0/foo/tags/")
        self.assertEqual(output.status_code, 404)
        expected_rv = {
            "error": "Project not found",
            "error_code": "ENOPROJECT",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_project_tags(self):
        """ Test the api_project_tags function.  """
        tests.create_projects(self.session)

        output = self.app.get("/api/0/test/tags/")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["tags", "total_tags"])
        self.assertEqual(data["tags"], [])
        self.assertEqual(data["total_tags"], 0)

        # Add a tag so that we can list it
        item = pagure.lib.model.TagColored(
            tag="tag1", tag_color="DeepBlueSky", project_id=1
        )
        self.session.add(item)
        self.session.commit()

        output = self.app.get("/api/0/test/tags/")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["tags", "total_tags"])
        self.assertEqual(data["tags"], ["tag1"])
        self.assertEqual(data["total_tags"], 1)

        output = self.app.get("/api/0/test/tags/?pattern=t")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["tags", "total_tags"])
        self.assertEqual(data["tags"], ["tag1"])
        self.assertEqual(data["total_tags"], 1)

        output = self.app.get("/api/0/test/tags/?pattern=p")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(sorted(data.keys()), ["tags", "total_tags"])
        self.assertEqual(data["tags"], [])
        self.assertEqual(data["total_tags"], 0)
