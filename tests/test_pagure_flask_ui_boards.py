# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import shutil
import sys
import os

import json
from mock import patch, MagicMock
import pygit2
import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.api
import pagure.flask_app
import pagure.lib.query
import tests


def set_projects_up(self):
    tests.create_projects(self.session)
    tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
    tests.add_content_git_repo(os.path.join(self.path, "repos", "test.git"))
    tests.create_tokens(self.session)
    tests.create_tokens_acl(self.session)

    tag = pagure.lib.model.TagColored(
        tag="dev", tag_color="DeepBlueSky", project_id=1
    )
    self.session.add(tag)
    tag = pagure.lib.model.TagColored(
        tag="infra", tag_color="DeepGreen", project_id=1
    )
    self.session.add(tag)
    self.session.commit()


def set_up_board(self):
    headers = {
        "Authorization": "token aaabbbcccddd",
        "Content-Type": "application/json",
    }

    data = json.dumps({"dev": {"active": True, "tag": "dev"}})
    output = self.app.post("/api/0/test/boards", headers=headers, data=data)
    self.assertEqual(output.status_code, 200)
    data = json.loads(output.get_data(as_text=True))
    self.assertDictEqual(
        data,
        {
            "boards": [
                {
                    "active": True,
                    "name": "dev",
                    "status": [],
                    "tag": {
                        "tag": "dev",
                        "tag_color": "DeepBlueSky",
                        "tag_description": "",
                    },
                    "full_url": "http://localhost.localdomain/test/boards/dev",
                }
            ]
        },
    )


class PagureFlaskUiBoardstests(tests.SimplePagureTest):
    """ Tests for flask UI Boards controller of pagure """

    maxDiff = None

    def setUp(self):
        super(PagureFlaskUiBoardstests, self).setUp()

        set_projects_up(self)

        set_up_board(self)

        # Set up the ticket repo
        tests.create_projects_git(
            os.path.join(self.path, "repos", "tickets"), bare=True
        )

        # Set up some status to the board
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        data = json.dumps(
            {
                "Backlog": {
                    "close": False,
                    "close_status": "",
                    "bg_color": "#FFB300",
                    "default": True,
                    "rank": 1,
                },
                "In Progress": {
                    "close": False,
                    "close_status": "",
                    "bg_color": "#ca0eef",
                    "default": False,
                    "rank": 2,
                },
                "Done": {
                    "close": True,
                    "close_status": "Fixed",
                    "bg_color": "#34d240",
                    "default": False,
                    "rank": 4,
                },
            }
        )
        output = self.app.post(
            "/api/0/test/boards/dev/status", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)

        # Create two issues to play with
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue")
        self.assertEqual(repo.open_tickets, 1)
        self.assertEqual(repo.open_tickets_public, 1)

        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #2",
            content="We should work on this for the second time",
            user="foo",
            status="Open",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #2")
        self.assertEqual(repo.open_tickets, 2)
        self.assertEqual(repo.open_tickets_public, 2)

        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Private issue #3",
            content="We should work on this for the second time",
            user="foo",
            status="Open",
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, "Private issue #3")
        self.assertEqual(repo.open_tickets, 3)
        self.assertEqual(repo.open_tickets_public, 2)

        self.tickets_uid = [t.uid for t in repo.issues]

    def test_view_board_empty(self):
        output = self.app.get("/test/boards/dev")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        # There are 3 columns
        self.assertEqual(output_text.count("drag-inner-list"), 3)
        self.assertEqual(output_text.count("drag-inner"), 3)
        # No tickets
        self.assertEqual(output_text.count("text-success"), 0)
        # One (!) in the nav bar on the issues title
        self.assertEqual(output_text.count("fa-exclamation-circle"), 1)

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_update_issue_add_tags_check_board_not_tagged(self):
        """ Test the update_issue endpoint. """

        # Before update, list tags
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        tags = pagure.lib.query.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ["dev", "infra"])
        self.assertEqual(repo.issues[0].tags_text, [])

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            # Tag to the issue
            data = {"csrf_token": csrf_token, "tag": "infra"}
            output = self.app.post(
                "/test/issue/1/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn("</i> Issue tagged with: infra</div>", output_text)

        # After update, list tags
        self.session = pagure.lib.query.create_session(self.dbpath)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        tags = pagure.lib.query.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ["dev", "infra"])
        self.assertEqual(repo.issues[0].tags_text, ["infra"])
        self.assertEqual(repo.issues[1].tags_text, [])

        # Check the board - No changes since the ticket was tagged `infra`
        output = self.app.get("/test/boards/dev")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        # There are 3 columns
        self.assertEqual(output_text.count("drag-inner-list"), 3)
        self.assertEqual(output_text.count("drag-inner"), 3)
        # 0 ticket
        self.assertEqual(output_text.count("id_txt"), 0)
        self.assertEqual(output_text.count("text-success"), 0)
        self.assertEqual(output_text.count("text-danger"), 0)
        # One (!) in the nav bar on the issues title
        self.assertEqual(output_text.count("fa-exclamation-circle"), 1)

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_update_issue_add_tags_check_board(self):
        """ Test the update_issue endpoint. """

        # Before update, list tags
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        tags = pagure.lib.query.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ["dev", "infra"])
        self.assertEqual(repo.issues[0].tags_text, [])

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            # Tag to the issue
            data = {"csrf_token": csrf_token, "tag": "dev"}
            output = self.app.post(
                "/test/issue/1/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn("</i> Issue tagged with: dev</div>", output_text)

        # After update, list tags
        self.session = pagure.lib.query.create_session(self.dbpath)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        tags = pagure.lib.query.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ["dev", "infra"])
        self.assertEqual(repo.issues[0].tags_text, ["dev"])
        self.assertEqual(repo.issues[1].tags_text, [])

        # Check the board - Ticket added
        output = self.app.get("/test/boards/dev")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        # There are 3 columns
        self.assertEqual(output_text.count("drag-inner-list"), 3)
        self.assertEqual(output_text.count("drag-inner"), 3)
        # One ticket
        self.assertEqual(output_text.count(" id_txt"), 1)
        self.assertEqual(output_text.count(" text-success"), 1)
        self.assertEqual(output_text.count(" text-danger"), 0)
        # Two (!) in the nav bar on the issues title + the ticket
        self.assertEqual(output_text.count("fa-exclamation-circle"), 2)

    @patch("pagure.lib.git.update_git", MagicMock(return_value=True))
    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def test_update_issue_add_tags_check_board_remove_tag_check_board(self):
        """ Test the update_issue endpoint. """

        # Before update, list tags
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        tags = pagure.lib.query.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ["dev", "infra"])
        self.assertEqual(repo.issues[0].tags_text, [])

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            # Tag to the issue
            data = {"csrf_token": csrf_token, "tag": "dev"}
            output = self.app.post(
                "/test/issue/1/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn("</i> Issue tagged with: dev</div>", output_text)

        # After update, list tags
        self.session = pagure.lib.query.create_session(self.dbpath)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        tags = pagure.lib.query.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ["dev", "infra"])
        self.assertEqual(repo.issues[0].tags_text, ["dev"])
        self.assertEqual(repo.issues[1].tags_text, [])

        # Check the board - Ticket added
        output = self.app.get("/test/boards/dev")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        # There are 3 columns
        self.assertEqual(output_text.count("drag-inner-list"), 3)
        self.assertEqual(output_text.count("drag-inner"), 3)
        # One ticket
        self.assertEqual(output_text.count(" id_txt"), 1)
        self.assertEqual(output_text.count(" text-success"), 1)
        self.assertEqual(output_text.count(" text-danger"), 0)
        # Two (!) in the nav bar on the issues title + the ticket
        self.assertEqual(output_text.count("fa-exclamation-circle"), 2)

        # Now remove the "dev" tag in favor of the "infra" one
        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            # Tag to the issue
            data = {"csrf_token": csrf_token, "tag": "infra"}
            output = self.app.post(
                "/test/issue/1/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn("</i> Issue tagged with: infra</div>", output_text)

        # After update, list tags
        self.session = pagure.lib.query.create_session(self.dbpath)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        tags = pagure.lib.query.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ["dev", "infra"])
        self.assertEqual(repo.issues[0].tags_text, ["infra"])
        self.assertEqual(repo.issues[1].tags_text, [])

        # Check the board - Ticket added
        output = self.app.get("/test/boards/dev")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        # There are 3 columns
        self.assertEqual(output_text.count("drag-inner-list"), 3)
        self.assertEqual(output_text.count("drag-inner"), 3)
        # 0 ticket
        self.assertEqual(output_text.count(" id_txt"), 0)
        self.assertEqual(output_text.count(" text-success"), 0)
        self.assertEqual(output_text.count(" text-danger"), 0)
        # One (!) in the nav bar on the issues title
        self.assertEqual(output_text.count("fa-exclamation-circle"), 1)

    def test_view_board_ticket_closed(self):

        headers = {"Content-Type": "application/json"}
        data = json.dumps({"2": {"status": "Done", "rank": 2}})
        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            output = self.app.post(
                "/api/0/test/boards/dev/add_issue", headers=headers, data=data
            )
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))

        self.session = pagure.lib.query.create_session(self.dbpath)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.issues[0].status, "Open")
        self.assertEqual(repo.issues[1].status, "Closed")
        self.assertEqual(repo.issues[1].close_status, "Fixed")

        # Check the board - Ticket added - as Done
        output = self.app.get("/test/boards/dev")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        # There are 3 columns
        self.assertEqual(output_text.count("drag-inner-list"), 3)
        self.assertEqual(output_text.count("drag-inner"), 3)
        # One ticket
        self.assertEqual(output_text.count(" id_txt"), 1)
        self.assertEqual(output_text.count(" text-success"), 0)
        self.assertEqual(output_text.count(" text-danger"), 1)
        # Two (!) in the nav bar on the issues title + the ticket
        self.assertEqual(output_text.count("fa-exclamation-circle"), 2)

    def test_view_board_private_ticket(self):
        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            headers = {"Content-Type": "application/json"}
            data = json.dumps({"3": {"status": "Done", "rank": 2}})
            output = self.app.post(
                "/api/0/test/boards/dev/add_issue", headers=headers, data=data
            )
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.get_data(as_text=True))

        self.session = pagure.lib.query.create_session(self.dbpath)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.issues[0].status, "Open")
        self.assertEqual(len(repo.issues[0].boards_issues), 0)
        self.assertEqual(repo.issues[1].status, "Open")
        self.assertEqual(len(repo.issues[1].boards_issues), 0)
        self.assertEqual(repo.issues[2].status, "Closed")
        self.assertEqual(repo.issues[2].close_status, "Fixed")
        self.assertEqual(len(repo.issues[2].boards_issues), 1)

        # Check the board - Looks empty user not authenticated
        output = self.app.get("/test/boards/dev")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        # There are 3 columns
        self.assertEqual(output_text.count("drag-inner-list"), 3)
        self.assertEqual(output_text.count("drag-inner"), 3)
        # 0 ticket
        self.assertEqual(output_text.count(" id_txt"), 0)
        self.assertEqual(output_text.count("text-success"), 0)
        self.assertEqual(output_text.count("text-danger"), 0)
        # 1 (!) in the nav bar on the issues title
        self.assertEqual(output_text.count("fa-exclamation-circle"), 1)
        self.assertEqual(output_text.count('title="Private ticket"'), 0)

        user = tests.FakeUser()
        user.username = "ralph"
        with tests.user_set(self.app.application, user):
            # Check the board - Looks empty user not allowed
            output = self.app.get("/test/boards/dev")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # There are 3 columns
            self.assertEqual(output_text.count("drag-inner-list"), 3)
            self.assertEqual(output_text.count("drag-inner"), 3)
            # 0 ticket
            self.assertEqual(output_text.count(" id_txt"), 0)
            self.assertEqual(output_text.count("text-success"), 0)
            self.assertEqual(output_text.count("text-danger"), 0)
            # 1 (!) in the nav bar on the issues title
            self.assertEqual(output_text.count("fa-exclamation-circle"), 2)
            self.assertEqual(output_text.count('title="Private ticket"'), 0)

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            # Check the board - 1 ticket
            output = self.app.get("/test/boards/dev")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # There are 3 columns
            self.assertEqual(output_text.count("drag-inner-list"), 3)
            self.assertEqual(output_text.count("drag-inner"), 3)
            # 1 ticket
            self.assertEqual(output_text.count(" id_txt"), 1)
            self.assertEqual(output_text.count(" text-success"), 0)
            self.assertEqual(output_text.count(" text-danger"), 1)
            # 2 (!) in the nav bar on the issues title
            self.assertEqual(output_text.count("fa-exclamation-circle"), 3)
            self.assertEqual(output_text.count('title="Private ticket"'), 1)

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            # Check the board - 1 ticket
            output = self.app.get("/test/boards/dev")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            # There are 3 columns
            self.assertEqual(output_text.count("drag-inner-list"), 3)
            self.assertEqual(output_text.count("drag-inner"), 3)
            # 1 ticket
            self.assertEqual(output_text.count(" id_txt"), 1)
            self.assertEqual(output_text.count(" text-success"), 0)
            self.assertEqual(output_text.count(" text-danger"), 1)
            # 2 (!) in the nav bar on the issues title
            self.assertEqual(output_text.count("fa-exclamation-circle"), 3)
            self.assertEqual(output_text.count('title="Private ticket"'), 1)

    @patch("pagure.lib.notify.send_email", new=MagicMock(return_value=True))
    def test_ticket_representation_in_git(self):
        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

            # Tag to the issue
            data = {"csrf_token": csrf_token, "tag": "dev"}
            output = self.app.post(
                "/test/issue/1/update", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Issue #1: Test issue - test - Pagure</title>",
                output_text,
            )
            self.assertIn(
                '<a class="btn btn-outline-secondary btn-sm border-0"'
                ' href="/test/issue/1/edit" title="Edit this issue">',
                output_text,
            )
            self.assertIn("</i> Issue tagged with: dev</div>", output_text)

        # After update, list tags
        self.session = pagure.lib.query.create_session(self.dbpath)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        tags = pagure.lib.query.get_tags_of_project(self.session, repo)
        self.assertEqual([tag.tag for tag in tags], ["dev", "infra"])
        self.assertEqual(repo.issues[0].tags_text, ["dev"])
        self.assertEqual(repo.issues[1].tags_text, [])

        self.session = pagure.lib.query.create_session(self.dbpath)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.issues[1].status, "Open")
        self.assertEqual(repo.issues[1].close_status, None)

        # Clone the repo so it isn't a bare repo
        pygit2.clone_repository(
            os.path.join(self.path, "repos", "tickets", "test.git"),
            os.path.join(self.path, "repos", "tickets", "test"),
        )

        exp = {
            "assignee": None,
            "blocks": [],
            "boards": [
                {
                    "board": {
                        "active": True,
                        "name": "dev",
                        "status": [
                            {
                                "bg_color": "#FFB300",
                                "close": False,
                                "close_status": None,
                                "default": True,
                                "name": "Backlog",
                            },
                            {
                                "bg_color": "#ca0eef",
                                "close": False,
                                "close_status": None,
                                "default": False,
                                "name": "In Progress",
                            },
                            {
                                "bg_color": "#34d240",
                                "close": True,
                                "close_status": "Fixed",
                                "default": False,
                                "name": "Done",
                            },
                        ],
                        "tag": {
                            "tag": "dev",
                            "tag_color": "DeepBlueSky",
                            "tag_description": "",
                        },
                        "full_url": "http://localhost.localdomain/test/boards/dev",
                    },
                    "rank": 1,
                    "status": {
                        "bg_color": "#FFB300",
                        "close": False,
                        "close_status": None,
                        "default": True,
                        "name": "Backlog",
                    },
                }
            ],
            "close_status": None,
            "closed_at": None,
            "closed_by": None,
            "comments": [
                {
                    "comment": "**Metadata Update from @pingou**:\n"
                    "- Issue tagged with: dev",
                    "date_created": "1594654596",
                    "edited_on": None,
                    "editor": None,
                    "id": 1,
                    "notification": True,
                    "parent": None,
                    "reactions": {},
                    "user": {
                        "default_email": "bar@pingou.com",
                        "emails": ["bar@pingou.com", "foo@pingou.com"],
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                        "full_url": "http://localhost.localdomain/user/pingou",
                    },
                }
            ],
            "content": "We should work on this",
            "custom_fields": [],
            "date_created": "1594654596",
            "depends": [],
            "full_url": "http://localhost.localdomain/test/issue/1",
            "id": 1,
            "last_updated": "1594654596",
            "milestone": None,
            "priority": None,
            "private": False,
            "related_prs": [],
            "status": "Open",
            "tags": ["dev"],
            "title": "Test issue",
            "user": {
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com", "foo@pingou.com"],
                "fullname": "PY C",
                "name": "pingou",
                "url_path": "user/pingou",
                "full_url": "http://localhost.localdomain/user/pingou",
            },
        }

        with open(
            os.path.join(
                self.path, "repos", "tickets", "test", repo.issues[0].uid
            )
        ) as stream:
            data = json.load(stream)

        # Make the date fix
        for idx, com in enumerate(data["comments"]):
            com["date_created"] = "1594654596"
            data["comments"][idx] = com
        data["date_created"] = "1594654596"
        data["last_updated"] = "1594654596"

        self.assertDictEqual(data, exp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
