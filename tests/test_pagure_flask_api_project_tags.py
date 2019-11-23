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

    def test_api_project_tags_new_wrong_token(self):
        """ Test the api_tags_new method of the flask api. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaa"}
        output = self.app.post("/api/0/test/tags/new", headers=headers)
        self.assertEqual(output.status_code, 401)
        expected_rv = {
            "error": "Invalid or expired token. Please visit "
            "http://localhost.localdomain/settings#nav-api-tab to get or renew "
            "your API token.",
            "error_code": "EINVALIDTOK",
            "errors": "Invalid token",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_project_tags_new_wrong_project(self):
        """ Test the api_tags_new method of the flask api. """

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.post("/api/0/foo/tags/new", headers=headers)
        self.assertEqual(output.status_code, 404)
        expected_rv = {
            "error": "Project not found",
            "error_code": "ENOPROJECT",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_project_tags_new_wrong_acls(self):
        """ Test the api_tags_new method of the flask api. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session, acl_name="create_project")
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.post("/api/0/test/tags/new", headers=headers)
        self.assertEqual(output.status_code, 401)
        expected_rv = {
            "error": "Invalid or expired token. Please visit "
            "http://localhost.localdomain/settings#nav-api-tab to get or renew "
            "your API token.",
            "error_code": "EINVALIDTOK",
            "errors": "Missing ACLs: modify_project",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_project_tags_new_no_input(self):
        """ Test the api_tags_new method of the flask api. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.post("/api/0/test/tags/new", headers=headers)
        self.assertEqual(output.status_code, 400)
        expected_rv = {
            "error": "Invalid or incomplete input submitted",
            "error_code": "EINVALIDREQ",
            "errors": {
                "tag": ["This field is required."],
                "tag_color": ["This field is required."],
            },
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_project_tags_new(self):
        """ Test the api_tags_new method of the flask api. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/tags/")
        self.assertEqual(output.status_code, 200)
        expected_rv = {"tags": [], "total_tags": 0}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

        data = {"tag": "blue", "tag_color": "DeepBlueSky"}

        output = self.app.post(
            "/api/0/test/tags/new", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        expected_rv = {
            "message": "Tag created",
            "tag": {
                "tag": "blue",
                "tag_description": "",
                "tag_color": "DeepBlueSky",
            },
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

        output = self.app.get("/api/0/test/tags/")
        self.assertEqual(output.status_code, 200)
        expected_rv = {"tags": ["blue"], "total_tags": 1}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_project_tags_new_existing_tag(self):
        """ Test the api_tags_new method of the flask api. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        # Add an issue and tag it so that we can list them
        item = pagure.lib.model.TagColored(
            tag="blue", tag_color="DeepBlueSky", project_id=1
        )
        self.session.add(item)
        self.session.commit()
        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.get("/api/0/test/tags/")
        self.assertEqual(output.status_code, 200)
        expected_rv = {"tags": ["blue"], "total_tags": 1}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

        data = {"tag": "blue", "tag_color": "DeepBlueSky"}

        output = self.app.post(
            "/api/0/test/tags/new", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        expected_rv = {
            "error": "An error occurred at the database level and prevent "
            "the action from reaching completion",
            "error_code": "EDBERROR",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

        output = self.app.get("/api/0/test/tags/")
        self.assertEqual(output.status_code, 200)
        expected_rv = {"tags": ["blue"], "total_tags": 1}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_project_tag_delete_wrong_token(self):
        """ Test the api_project_tag_delete method of flask api. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaa"}
        output = self.app.delete("/api/0/test/tag/blue", headers=headers)
        self.assertEqual(output.status_code, 401)
        expected_rv = {
            "error": "Invalid or expired token. Please visit "
            "http://localhost.localdomain/settings#nav-api-tab to get or renew "
            "your API token.",
            "error_code": "EINVALIDTOK",
            "errors": "Invalid token",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_project_tag_delete_wrong_project(self):
        """ Test the api_project_tag_delete method of flask api. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.delete("/api/0/foo/tag/blue", headers=headers)
        self.assertEqual(output.status_code, 404)
        expected_rv = {
            "error": "Project not found",
            "error_code": "ENOPROJECT",
        }
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_project_tag_delete_wrong_tag(self):
        """ Test the api_project_tag_delete method of flask api. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.delete("/api/0/test/tag/blue", headers=headers)
        self.assertEqual(output.status_code, 404)
        expected_rv = {"error": "Tag not found", "error_code": "ENOTAG"}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_project_tag_delete(self):
        """ Test the api_project_tag_delete method of flask api. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        item = pagure.lib.model.TagColored(
            tag="blue", tag_color="DeepBlueSky", project_id=1
        )
        self.session.add(item)
        self.session.commit()
        output = self.app.get("/api/0/test/tags/")
        self.assertEqual(output.status_code, 200)
        expected_rv = {"tags": ["blue"], "total_tags": 1}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.delete("/api/0/test/tag/blue", headers=headers)
        self.assertEqual(output.status_code, 200)
        expected_rv = {"message": "Tag: blue has been deleted"}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)
        output = self.app.get("/api/0/test/tags/")
        self.assertEqual(output.status_code, 200)
        expected_rv = {"tags": [], "total_tags": 0}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

    def test_api_project_tag_delete_with_assigned_issue_and_pr(self):
        """ Test the api_project_tag_delete method of flask api. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Add a tag
        item = pagure.lib.model.TagColored(
            tag="blue", tag_color="DeepBlueSky", project_id=1
        )
        self.session.add(item)
        self.session.commit()

        # Add a tagged issue
        item = pagure.lib.model.Issue(
            id=1,
            uid="foobar",
            project_id=1,
            title="issue",
            content="a bug report",
            user_id=1,  # pingou
        )
        self.session.add(item)
        self.session.commit()
        item = pagure.lib.model.TagIssueColored(issue_uid="foobar", tag_id=1)
        self.session.add(item)
        self.session.commit()

        # Add a tagged pull request
        item = pagure.lib.model.PullRequest(
            id=1,
            uid="barfoo",
            project_id=1,
            branch="master",
            branch_from="master",
            title="pull request",
            allow_rebase=False,
            user_id=1,  # pingou
        )
        self.session.add(item)
        self.session.commit()
        item = pagure.lib.model.TagPullRequest(request_uid="barfoo", tag_id=1)
        self.session.add(item)
        self.session.commit()

        output = self.app.get("/api/0/test/tags/")
        self.assertEqual(output.status_code, 200)
        expected_rv = {"tags": ["blue"], "total_tags": 1}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

        headers = {"Authorization": "token aaabbbcccddd"}
        output = self.app.delete("/api/0/test/tag/blue", headers=headers)
        self.assertEqual(output.status_code, 200)
        expected_rv = {"message": "Tag: blue has been deleted"}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)

        output = self.app.get("/api/0/test/tags/")
        self.assertEqual(output.status_code, 200)
        expected_rv = {"tags": [], "total_tags": 0}
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, expected_rv)
