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
import pygit2
from mock import patch, MagicMock

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
                }
            ]
        },
    )


class PagureFlaskApiBoardstests(tests.SimplePagureTest):
    """ Tests for flask API Boards controller of pagure """

    maxDiff = None

    def setUp(self):
        super(PagureFlaskApiBoardstests, self).setUp()

        set_projects_up(self)

    def test_api_boards_view_no_project(self):
        output = self.app.get("/api/0/invalid/boards")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_api_boards_view_empty(self):
        output = self.app.get("/api/0/test/boards")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"boards": [], "total_requests": 0})

    def test_api_board_create_no_token(self):
        headers = {}
        data = {}
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or expired token. Please visit "
                "http://localhost.localdomain/settings#nav-api-tab to get or renew "
                "your API token.",
                "error_code": "EINVALIDTOK",
                "errors": "Invalid token",
            },
        )

    def test_api_board_create_expired_token(self):
        headers = {"Authorization": "token expired_token"}
        data = {}
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or expired token. Please visit "
                "http://localhost.localdomain/settings#nav-api-tab to get or renew "
                "your API token.",
                "error_code": "EINVALIDTOK",
                "errors": "Expired token",
            },
        )

    def test_api_board_create_invalid_token_project(self):
        headers = {"Authorization": "token aaabbbcccddd"}
        data = {}
        output = self.app.post(
            "/api/0/test2/boards", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or expired token. Please visit "
                "http://localhost.localdomain/settings#nav-api-tab to get or renew "
                "your API token.",
                "error_code": "EINVALIDTOK",
            },
        )

    def test_api_board_create_no_data(self):
        headers = {"Authorization": "token aaabbbcccddd"}
        data = {}
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "No (JSON) data provided",
            },
        )

    def test_api_board_create_no_contenttype(self):
        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"name": "board", "active": True, "Tag": "not found"}
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "No (JSON) data provided",
            },
        )

    def test_api_board_create_html_data(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        data = {"name": "board", "active": True, "tag": "not found"}
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        self.assertIn(
            "The browser (or proxy) sent a request that this server could not understand.",
            output.get_data(as_text=True),
        )

    def test_api_board_create_invalid_json(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        data = json.dumps(
            {"name": "board", "active": True, "tag": "not found"}
        )
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "No tag associated with at least one of the boards",
            },
        )

    def test_api_board_create_invalid_tag(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        data = json.dumps({"dev": {"active": True, "tag": "not found"}})
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "No tag found with the name not found",
                "error_code": "ENOCODE",
            },
        )

    def test_api_board_create(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }
        data = json.dumps({"dev": {"active": True, "tag": "dev"}})
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
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
                    }
                ]
            },
        )

    def test_api_board_edit_board_delete_board(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        # Add 2 boards to the project
        data = json.dumps(
            {
                "dev": {"active": True, "tag": "dev"},
                "infra": {"active": True, "tag": "infra"},
            }
        )
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
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
                    },
                    {
                        "active": True,
                        "name": "infra",
                        "status": [],
                        "tag": {
                            "tag": "infra",
                            "tag_color": "DeepGreen",
                            "tag_description": "",
                        },
                    },
                ]
            },
        )

        # Remove one of the 2 boards
        data = json.dumps({"dev": {"active": True, "tag": "dev"},})
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
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
                    }
                ]
            },
        )

        # Removing the last board doesn't work (no JSON data provided)
        data = json.dumps({})
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)

    def test_api_board_delete_board(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({"name": ["dev"]})
        output = self.app.post(
            "/api/0/test/boards/delete", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"boards": []})

    def test_api_board_api_board_status_no_board(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({"foo": "bar"})
        output = self.app.post(
            "/api/0/test/boards/invalid/status", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "Board not found",
            },
        )


class PagureFlaskApiBoardsWithBoardtests(tests.SimplePagureTest):
    """ Tests for flask API Boards controller of pagure for the tests
    requiring a pre-existing board.
    """

    maxDiff = None

    def setUp(self):
        super(PagureFlaskApiBoardsWithBoardtests, self).setUp()

        set_projects_up(self)

        set_up_board(self)

    def test_api_board_edit_board(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        # Make the board inactive
        data = json.dumps({"dev": {"active": False, "tag": "dev"}})
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "boards": [
                    {
                        "active": False,
                        "name": "dev",
                        "status": [],
                        "tag": {
                            "tag": "dev",
                            "tag_color": "DeepBlueSky",
                            "tag_description": "",
                        },
                    }
                ]
            },
        )

    def test_api_board_edit_board_invalid_tag(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        # Associate the existing board with an invalid tag
        data = json.dumps({"dev": {"active": True, "tag": "invalid"},})
        output = self.app.post(
            "/api/0/test/boards", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "No tag found with the name invalid",
                "error_code": "ENOCODE",
            },
        )

    def test_api_board_delete_invalid_json_input(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        # Remove this board
        data = json.dumps({})
        output = self.app.post(
            "/api/0/test/boards/delete", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"name": ["This field is required"]},
            },
        )

    def test_api_board_delete_invalid_html_input(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
        }

        # Remove the board
        headers = {
            "Authorization": "token aaabbbcccddd",
        }
        data = {}
        output = self.app.post(
            "/api/0/test/boards/delete", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"name": ["This field is required"]},
            },
        )

    def test_api_board_delete_json_input(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        # Remove the board
        data = json.dumps({"name": ["dev"]})
        output = self.app.post(
            "/api/0/test/boards/delete", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"boards": []},
        )

    def test_api_board_delete_html_input(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
        }

        # Remove the board
        data = {"name": ["dev"]}
        output = self.app.post(
            "/api/0/test/boards/delete", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"boards": []},
        )

    def test_api_board_api_board_status_no_data(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({})
        output = self.app.post(
            "/api/0/test/boards/dev/status", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "No (JSON) data provided",
            },
        )

    def test_api_board_api_board_status_invalid_tag_name(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps(
            {
                "-Triaged": {
                    "close": False,
                    "close_status": "",
                    "bg_color": "#ca0dcd",
                    "default": True,
                    "rank": 1,
                }
            }
        )
        output = self.app.post(
            "/api/0/test/boards/dev/status", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "name": [
                        "Invalid status name provided, it should match: "
                        "^[a-zA-Z0-9][a-zA-Z0-9-_ .:]+$."
                    ]
                },
            },
        )

    def test_api_board_api_board_status_missing_rank(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps(
            {
                "Triaged": {
                    "close": False,
                    "close_status": "",
                    "bg_color": "#ca0dcd",
                    "default": True,
                }
            }
        )
        output = self.app.post(
            "/api/0/test/boards/dev/status", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "The 'rank' and 'default' fields are mandatory.",
            },
        )

    def test_api_board_api_board_status_missing_default(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps(
            {
                "Triaged": {
                    "close": False,
                    "close_status": "",
                    "bg_color": "#ca0dcd",
                    "rank": 1,
                }
            }
        )
        output = self.app.post(
            "/api/0/test/boards/dev/status", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "The 'rank' and 'default' fields are mandatory.",
            },
        )

    def test_api_board_api_board_status_no_default(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps(
            {
                "Triaged": {
                    "close": False,
                    "close_status": "",
                    "bg_color": "#ca0dcd",
                    "default": False,
                    "rank": 1,
                }
            }
        )
        output = self.app.post(
            "/api/0/test/boards/dev/status", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "There must be one and only one default.",
            },
        )

    def test_api_board_api_board_status_multiple_default(self):
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
                "Triaged": {
                    "close": False,
                    "close_status": "",
                    "bg_color": "#ca0dcd",
                    "default": True,
                    "rank": 1,
                },
            }
        )
        output = self.app.post(
            "/api/0/test/boards/dev/status", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "There must be one and only one default.",
            },
        )

    def test_api_board_api_board_status(self):
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
                "Triaged": {
                    "close": False,
                    "close_status": "",
                    "bg_color": "#ca0dcd",
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
                "  ": {
                    "close": True,
                    "close_status": "Fixed",
                    "bg_color": "#34d240",
                    "default": False,
                    "rank": 5,
                },
            }
        )
        output = self.app.post(
            "/api/0/test/boards/dev/status", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
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
                            "bg_color": "#ca0dcd",
                            "close": False,
                            "close_status": None,
                            "default": False,
                            "name": "Triaged",
                        },
                        {
                            "name": "Done",
                            "close": True,
                            "close_status": "Fixed",
                            "default": False,
                            "bg_color": "#34d240",
                        },
                    ],
                    "tag": {
                        "tag": "dev",
                        "tag_color": "DeepBlueSky",
                        "tag_description": "",
                    },
                }
            },
        )

    def test_api_board_api_board_status_no_close_status(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps(
            {
                "Backlog": {
                    "close": False,
                    "close_status": None,
                    "bg_color": "#FFB300",
                    "default": True,
                    "rank": 1,
                },
                "Triaged": {
                    "close": False,
                    "close_status": None,
                    "bg_color": "#ca0dcd",
                    "default": False,
                    "rank": 2,
                },
                "Done": {
                    "close": True,
                    "close_status": None,
                    "bg_color": "#34d240",
                    "default": False,
                    "rank": 4,
                },
                "  ": {
                    "close": True,
                    "close_status": None,
                    "bg_color": "#34d240",
                    "default": False,
                    "rank": 5,
                },
            }
        )
        output = self.app.post(
            "/api/0/test/boards/dev/status", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
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
                            "bg_color": "#ca0dcd",
                            "close": False,
                            "close_status": None,
                            "default": False,
                            "name": "Triaged",
                        },
                        {
                            "name": "Done",
                            "close": True,
                            "close_status": None,
                            "default": False,
                            "bg_color": "#34d240",
                        },
                    ],
                    "tag": {
                        "tag": "dev",
                        "tag_color": "DeepBlueSky",
                        "tag_description": "",
                    },
                }
            },
        )

    def test_api_board_api_board_status_adding_removing(self):
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
                "Triaged": {
                    "close": False,
                    "close_status": "",
                    "bg_color": "#ca0dcd",
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
                "  ": {
                    "close": True,
                    "close_status": "Fixed",
                    "bg_color": "#34d240",
                    "default": False,
                    "rank": 5,
                },
            }
        )
        output = self.app.post(
            "/api/0/test/boards/dev/status", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
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
                            "bg_color": "#ca0dcd",
                            "close": False,
                            "close_status": None,
                            "default": False,
                            "name": "Triaged",
                        },
                        {
                            "name": "Done",
                            "close": True,
                            "close_status": "Fixed",
                            "default": False,
                            "bg_color": "#34d240",
                        },
                    ],
                    "tag": {
                        "tag": "dev",
                        "tag_color": "DeepBlueSky",
                        "tag_description": "",
                    },
                }
            },
        )

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
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
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
                            "name": "Done",
                            "close": True,
                            "close_status": "Fixed",
                            "default": False,
                            "bg_color": "#34d240",
                        },
                    ],
                    "tag": {
                        "tag": "dev",
                        "tag_color": "DeepBlueSky",
                        "tag_description": "",
                    },
                }
            },
        )


class PagureFlaskApiBoardsWithBoardAndIssuetests(tests.SimplePagureTest):
    """ Tests for flask API Boards controller of pagure for the tests
    requiring a pre-existing board and issues.
    """

    maxDiff = None

    def setUp(self):
        super(PagureFlaskApiBoardsWithBoardAndIssuetests, self).setUp()

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
        self.tickets_uid = [t.uid for t in repo.issues]

    def test_api_board_ticket_add_status_invalid_board(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({"12": {"status": "In Progress", "rank": 2,}})
        output = self.app.post(
            "/api/0/test/boards/invalid/add_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "Board not found",
            },
        )

    def test_api_board_ticket_add_status_no_data(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({})
        output = self.app.post(
            "/api/0/test/boards/dev/add_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "No (JSON) data provided",
            },
        )

    def test_api_board_ticket_add_status_no_rank(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({"12": {"status": "In Progress"}})
        output = self.app.post(
            "/api/0/test/boards/dev/add_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "The 'rank' and 'status' fields are mandatory.",
            },
        )

    def test_api_board_ticket_add_status_no_status(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({"12": {"rank": 2,}})
        output = self.app.post(
            "/api/0/test/boards/dev/add_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "The 'rank' and 'status' fields are mandatory.",
            },
        )

    def test_api_board_ticket_add_status_invalid_ticket_id(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({"12": {"status": "In Progress", "rank": 2}})
        output = self.app.post(
            "/api/0/test/boards/dev/add_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "No ticket found with this identifier",
                "error_code": "ENOCODE",
            },
        )

    def test_api_board_ticket_add_status(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps(
            {
                "2": {"status": "In Progress", "rank": 2},
                "  ": {"status": "In Progress", "rank": 4},
            }
        )
        output = self.app.post(
            "/api/0/test/boards/dev/add_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
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
                }
            },
        )

    def test_api_board_ticket_update_status_invalid_board(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({"12": {"status": "In Progress", "rank": 2,}})
        output = self.app.post(
            "/api/0/test/boards/invalid/update_issue",
            headers=headers,
            data=data,
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "Board not found",
            },
        )

    def test_api_board_ticket_update_status_no_data(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({})
        output = self.app.post(
            "/api/0/test/boards/dev/update_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "No (JSON) data provided",
            },
        )

    def test_api_board_ticket_update_status_no_rank(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({"12": {"status": "In Progress"}})
        output = self.app.post(
            "/api/0/test/boards/dev/update_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "The 'rank' and 'status' fields are mandatory.",
            },
        )

    def test_api_board_ticket_update_status_no_status(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({"12": {"rank": 2,}})
        output = self.app.post(
            "/api/0/test/boards/dev/add_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": "The 'rank' and 'status' fields are mandatory.",
            },
        )

    def test_api_board_ticket_update_status_invalid_ticket_id(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({"12": {"status": "In Progress", "rank": 2}})
        output = self.app.post(
            "/api/0/test/boards/dev/update_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "No ticket found with this identifier",
                "error_code": "ENOCODE",
            },
        )

    def test_api_board_ticket_update_status(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps(
            {
                self.tickets_uid[1]: {"status": "In Progress", "rank": 2},
                "  ": {"status": "In Progress", "rank": 4},
            }
        )
        output = self.app.post(
            "/api/0/test/boards/dev/update_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
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
                }
            },
        )

    def test_api_board_ticket_update_status_close_re_opend(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps(
            {self.tickets_uid[1]: {"status": "Done", "rank": 2},}
        )
        output = self.app.post(
            "/api/0/test/boards/dev/update_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.session = pagure.lib.query.create_session(self.dbpath)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.issues[1].status, "Closed")
        self.assertEqual(repo.issues[1].close_status, "Fixed")

        data = json.dumps(
            {self.tickets_uid[1]: {"status": "In Progress", "rank": 2},}
        )
        output = self.app.post(
            "/api/0/test/boards/dev/update_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))

        self.session = pagure.lib.query.create_session(self.dbpath)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.issues[0].status, "Open")
        self.assertEqual(repo.issues[1].status, "Open")
        self.assertEqual(repo.issues[1].close_status, None)

    @patch("pagure.lib.notify.send_email", new=MagicMock(return_value=True))
    def test_ticket_representation_in_git(self):
        headers = {
            "Authorization": "token aaabbbcccddd",
            "Content-Type": "application/json",
        }

        data = json.dumps({"2": {"status": "In Progress", "rank": 2},})
        output = self.app.post(
            "/api/0/test/boards/dev/add_issue", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 200)

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
                    },
                    "rank": 2,
                    "status": {
                        "bg_color": "#ca0eef",
                        "close": False,
                        "close_status": None,
                        "default": False,
                        "name": "In Progress",
                    },
                }
            ],
            "close_status": None,
            "closed_at": None,
            "closed_by": None,
            "comments": [
                {
                    "comment": "Issue tagged with: dev",
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
                    },
                }
            ],
            "content": "We should work on this for the second time",
            "custom_fields": [],
            "date_created": "1594654596",
            "depends": [],
            "id": 2,
            "last_updated": "1594654596",
            "milestone": None,
            "priority": None,
            "private": False,
            "related_prs": [],
            "status": "Open",
            "tags": ["dev"],
            "title": "Test issue #2",
            "user": {
                "default_email": "foo@bar.com",
                "emails": ["foo@bar.com"],
                "fullname": "foo bar",
                "name": "foo",
                "url_path": "user/foo",
            },
        }

        with open(
            os.path.join(
                self.path, "repos", "tickets", "test", repo.issues[1].uid
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
