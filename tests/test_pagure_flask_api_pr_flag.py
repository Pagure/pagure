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

import json
import pagure_messages
from fedora_messaging import api, testing
from mock import ANY, patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.config  # noqa
import pagure.lib.query  # noqa
import tests  # noqa


class PagureFlaskApiPRFlagtests(tests.Modeltests):
    """ Tests for the flask API of pagure for flagging pull-requests """

    maxDiff = None

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiPRFlagtests, self).setUp()

        pagure.config.config["REQUESTS_FOLDER"] = None

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        forked_repo = pagure.lib.query.get_authorized_project(
            self.session, "test"
        )
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from="master",
            repo_to=repo,
            branch_to="master",
            title="test pull-request",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "test pull-request")

        # Check flags before
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        request.commit_stop = "hash_commit_stop"
        self.session.add(request)
        self.session.commit()
        self.assertEqual(len(request.flags), 0)

    def test_invalid_project(self):
        """ Test the flagging a PR on an invalid project. """

        headers = {"Authorization": "token aaabbbcccddd"}

        # Invalid project
        output = self.app.post(
            "/api/0/foo/pull-request/1/flag", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_incorrect_project(self):
        """ Test the flagging a PR on the wrong project. """
        headers = {"Authorization": "token aaabbbcccddd"}

        # Valid token, wrong project
        output = self.app.post(
            "/api/0/test2/pull-request/1/flag", headers=headers
        )
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            pagure.api.APIERROR.EINVALIDTOK.name, data["error_code"]
        )
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data["error"])

    def test_pr_disabled(self):
        """ Test the flagging a PR when PRs are disabled. """

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        settings = repo.settings
        settings["pull_requests"] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        headers = {"Authorization": "token aaabbbcccddd"}

        # PRs disabled
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Pull-Request have been deactivated for this project",
                "error_code": "EPULLREQUESTSDISABLED",
            },
        )

    def test_no_pr(self):
        """ Test the flagging a PR when the PR doesn't exist. """
        headers = {"Authorization": "token aaabbbcccddd"}

        # No PR
        output = self.app.post(
            "/api/0/test/pull-request/10/flag", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Pull-Request not found", "error_code": "ENOREQ"}
        )

    def test_no_input(self):
        """ Test the flagging an existing PR but with no data. """
        headers = {"Authorization": "token aaabbbcccddd"}

        # No input
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "comment": ["This field is required."],
                    "url": ["This field is required."],
                    "username": ["This field is required."],
                },
            },
        )

    def test_no_comment(self):
        """ Test the flagging an existing PR but with incomplete data. """
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "username": "Jenkins",
            "percent": 100,
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }

        # Incomplete request
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"comment": ["This field is required."]},
            },
        )

        # No change
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        self.assertEqual(len(request.flags), 0)

    @patch(
        "pagure.lib.query.add_pull_request_flag",
        MagicMock(side_effect=pagure.exceptions.PagureException("error")),
    )
    def test_raise_exception(self):
        """ Test the flagging a PR when adding a flag raises an exception. """

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {
            "username": "Jenkins",
            "comment": "Tests running",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }

        # Adding a flag raises an exception
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", headers=headers, data=data
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"error": "error", "error_code": "ENOCODE"})

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    @patch("pagure.lib.notify.send_email")
    def test_flagging_a_pul_request_with_notification(self, mock_email):
        """ Test the flagging a PR. """
        headers = {"Authorization": "token aaabbbcccddd"}

        # Enable PR notifications
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        settings = repo.settings
        settings["notify_on_pull-request_flag"] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        data = {
            "username": "Jenkins",
            "comment": "Tests running",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }

        # Valid request
        with testing.mock_sends(
            pagure_messages.CommitFlagAddedV1,
            pagure_messages.PullRequestFlagAddedV1(
                topic="pagure.pull-request.flag.added",
                body={
                    "pullrequest": {
                        "id": 1,
                        "uid": ANY,
                        "title": "test pull-request",
                        "branch": "master",
                        "project": {
                            "id": 1,
                            "name": "test",
                            "fullname": "test",
                            "url_path": "test",
                            "description": "test project #1",
                            "full_url": "http://localhost.localdomain/test",
                            "namespace": None,
                            "parent": None,
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "full_url": "http://localhost.localdomain/user/pingou",
                                "url_path": "user/pingou",
                            },
                            "access_users": {
                                "owner": ["pingou"],
                                "admin": [],
                                "commit": [],
                                "collaborator": [],
                                "ticket": [],
                            },
                            "access_groups": {
                                "admin": [],
                                "commit": [],
                                "collaborator": [],
                                "ticket": [],
                            },
                            "tags": [],
                            "priorities": {},
                            "custom_keys": [],
                            "close_status": [
                                "Invalid",
                                "Insufficient data",
                                "Fixed",
                                "Duplicate",
                            ],
                            "milestones": {},
                        },
                        "branch_from": "master",
                        "repo_from": {
                            "id": 1,
                            "name": "test",
                            "fullname": "test",
                            "url_path": "test",
                            "description": "test project #1",
                            "full_url": "http://localhost.localdomain/test",
                            "namespace": None,
                            "parent": None,
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "full_url": "http://localhost.localdomain/user/pingou",
                                "url_path": "user/pingou",
                            },
                            "access_users": {
                                "owner": ["pingou"],
                                "admin": [],
                                "commit": [],
                                "collaborator": [],
                                "ticket": [],
                            },
                            "access_groups": {
                                "admin": [],
                                "commit": [],
                                "collaborator": [],
                                "ticket": [],
                            },
                            "tags": [],
                            "priorities": {},
                            "custom_keys": [],
                            "close_status": [
                                "Invalid",
                                "Insufficient data",
                                "Fixed",
                                "Duplicate",
                            ],
                            "milestones": {},
                        },
                        "remote_git": None,
                        "date_created": ANY,
                        "full_url": "http://localhost.localdomain/test/pull-request/1",
                        "updated_on": ANY,
                        "last_updated": ANY,
                        "closed_at": None,
                        "user": {
                            "name": "pingou",
                            "fullname": "PY C",
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "url_path": "user/pingou",
                        },
                        "assignee": None,
                        "status": "Open",
                        "commit_start": None,
                        "commit_stop": "hash_commit_stop",
                        "closed_by": None,
                        "initial_comment": None,
                        "cached_merge_status": "unknown",
                        "threshold_reached": None,
                        "tags": [],
                        "comments": [],
                    },
                    "flag": {
                        "commit_hash": "hash_commit_stop",
                        "username": "Jenkins",
                        "percent": None,
                        "comment": "Tests running",
                        "status": "pending",
                        "url": "http://jenkins.cloud.fedoraproject.org/",
                        "date_created": ANY,
                        "date_updated": ANY,
                        "user": {
                            "name": "pingou",
                            "fullname": "PY C",
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "url_path": "user/pingou",
                        },
                    },
                    "agent": "pingou",
                },
            ),
        ):
            output = self.app.post(
                "/api/0/test/pull-request/1/flag", data=data, headers=headers
            )
            self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        commit_hash = data["flag"]["commit_hash"]
        data["flag"]["commit_hash"] = "62b49f00d489452994de5010565fab81"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "flag": {
                    "comment": "Tests running",
                    "date_created": "1510742565",
                    "date_updated": "1510742565",
                    "percent": None,
                    "commit_hash": "62b49f00d489452994de5010565fab81",
                    "status": "pending",
                    "url": "http://jenkins.cloud.fedoraproject.org/",
                    "user": {
                        "default_email": "bar@pingou.com",
                        "emails": ["bar@pingou.com", "foo@pingou.com"],
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                    "username": "Jenkins",
                },
                "message": "Flag added",
                "uid": "jenkins_build_pagure_100+seed",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "pingou",
            },
        )

        # One flag added
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        self.assertEqual(len(request.flags), 0)

        flags = pagure.lib.query.get_commit_flag(
            self.session, request.project, commit_hash
        )
        self.assertEqual(flags[0].comment, "Tests running")
        self.assertEqual(flags[0].percent, None)

        # Check the notification sent
        mock_email.assert_called_once_with(
            "\nJenkins flagged the pull-request `test pull-request` "
            "as pending: Tests running\n\n"
            "http://localhost.localdomain/test/pull-request/1\n",
            "PR #1 - Jenkins: pending",
            "bar@pingou.com",
            assignee=None,
            in_reply_to="test-pull-request-%s" % request.uid,
            mail_id="test-commit-1-1",
            project_name="test",
            reporter="pingou",
            user_from="Jenkins",
        )

    @patch.dict(
        "pagure.config.config", {"FEDORA_MESSAGING_NOTIFICATIONS": True}
    )
    def test_updating_flag(self):
        """ Test the updating the flag of a PR. """
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "username": "Jenkins",
            "comment": "Tests running",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }

        # Valid request
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "flag": {
                    "comment": "Tests running",
                    "commit_hash": "hash_commit_stop",
                    "date_created": "1510742565",
                    "date_updated": "1510742565",
                    "percent": None,
                    "status": "pending",
                    "url": "http://jenkins.cloud.fedoraproject.org/",
                    "user": {
                        "default_email": "bar@pingou.com",
                        "emails": ["bar@pingou.com", "foo@pingou.com"],
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                    "username": "Jenkins",
                },
                "message": "Flag added",
                "uid": "jenkins_build_pagure_100+seed",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "pingou",
            },
        )

        # One flag added
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        self.assertEqual(len(request.flags), 0)

        flags = pagure.lib.query.get_commit_flag(
            self.session, request.project, "hash_commit_stop"
        )
        self.assertEqual(flags[0].comment, "Tests running")
        self.assertEqual(flags[0].percent, None)

        # Update flag  -  w/o providing the status
        data = {
            "username": "Jenkins",
            "percent": 100,
            "comment": "Tests passed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }

        with testing.mock_sends(
            pagure_messages.CommitFlagUpdatedV1,
            pagure_messages.PullRequestFlagUpdatedV1(
                topic="pagure.pull-request.flag.updated",
                body={
                    "pullrequest": {
                        "id": 1,
                        "uid": ANY,
                        "title": "test pull-request",
                        "full_url": "http://localhost.localdomain/test/pull-request/1",
                        "branch": "master",
                        "project": {
                            "id": 1,
                            "name": "test",
                            "fullname": "test",
                            "url_path": "test",
                            "description": "test project #1",
                            "full_url": "http://localhost.localdomain/test",
                            "namespace": None,
                            "parent": None,
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "full_url": "http://localhost.localdomain/user/pingou",
                                "url_path": "user/pingou",
                            },
                            "access_users": {
                                "owner": ["pingou"],
                                "admin": [],
                                "commit": [],
                                "collaborator": [],
                                "ticket": [],
                            },
                            "access_groups": {
                                "admin": [],
                                "commit": [],
                                "collaborator": [],
                                "ticket": [],
                            },
                            "tags": [],
                            "priorities": {},
                            "custom_keys": [],
                            "close_status": [
                                "Invalid",
                                "Insufficient data",
                                "Fixed",
                                "Duplicate",
                            ],
                            "milestones": {},
                        },
                        "branch_from": "master",
                        "repo_from": {
                            "id": 1,
                            "name": "test",
                            "fullname": "test",
                            "url_path": "test",
                            "description": "test project #1",
                            "full_url": "http://localhost.localdomain/test",
                            "namespace": None,
                            "parent": None,
                            "date_created": ANY,
                            "date_modified": ANY,
                            "user": {
                                "name": "pingou",
                                "fullname": "PY C",
                                "full_url": "http://localhost.localdomain/user/pingou",
                                "url_path": "user/pingou",
                            },
                            "access_users": {
                                "owner": ["pingou"],
                                "admin": [],
                                "commit": [],
                                "collaborator": [],
                                "ticket": [],
                            },
                            "access_groups": {
                                "admin": [],
                                "commit": [],
                                "collaborator": [],
                                "ticket": [],
                            },
                            "tags": [],
                            "priorities": {},
                            "custom_keys": [],
                            "close_status": [
                                "Invalid",
                                "Insufficient data",
                                "Fixed",
                                "Duplicate",
                            ],
                            "milestones": {},
                        },
                        "remote_git": None,
                        "date_created": ANY,
                        "updated_on": ANY,
                        "last_updated": ANY,
                        "closed_at": None,
                        "user": {
                            "name": "pingou",
                            "fullname": "PY C",
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "url_path": "user/pingou",
                        },
                        "assignee": None,
                        "status": "Open",
                        "commit_start": None,
                        "commit_stop": "hash_commit_stop",
                        "closed_by": None,
                        "initial_comment": None,
                        "cached_merge_status": "unknown",
                        "threshold_reached": None,
                        "tags": [],
                        "comments": [],
                    },
                    "flag": {
                        "commit_hash": "hash_commit_stop",
                        "username": "Jenkins",
                        "percent": 100,
                        "comment": "Tests passed",
                        "status": "success",
                        "url": "http://jenkins.cloud.fedoraproject.org/",
                        "date_created": ANY,
                        "date_updated": ANY,
                        "user": {
                            "name": "pingou",
                            "fullname": "PY C",
                            "full_url": "http://localhost.localdomain/user/pingou",
                            "url_path": "user/pingou",
                        },
                    },
                    "agent": "pingou",
                },
            ),
        ):
            output = self.app.post(
                "/api/0/test/pull-request/1/flag", data=data, headers=headers
            )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "flag": {
                    "comment": "Tests passed",
                    "commit_hash": "hash_commit_stop",
                    "date_created": "1510742565",
                    "date_updated": "1510742565",
                    "percent": 100,
                    "status": "success",
                    "url": "http://jenkins.cloud.fedoraproject.org/",
                    "user": {
                        "default_email": "bar@pingou.com",
                        "emails": ["bar@pingou.com", "foo@pingou.com"],
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                    "username": "Jenkins",
                },
                "message": "Flag updated",
                "uid": "jenkins_build_pagure_100+seed",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "pingou",
            },
        )

        # One flag added
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        self.assertEqual(len(request.flags), 0)

        flags = pagure.lib.query.get_commit_flag(
            self.session, request.project, "hash_commit_stop"
        )
        self.assertEqual(flags[0].comment, "Tests passed")
        self.assertEqual(flags[0].percent, 100)

    def test_adding_two_flags(self):
        """ Test the adding two flags to a PR. """
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "username": "Jenkins",
            "comment": "Tests passed",
            "status": "success",
            "percent": "100",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }

        # Valid request
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "flag": {
                    "comment": "Tests passed",
                    "commit_hash": "hash_commit_stop",
                    "date_created": "1510742565",
                    "date_updated": "1510742565",
                    "percent": 100,
                    "status": "success",
                    "url": "http://jenkins.cloud.fedoraproject.org/",
                    "user": {
                        "default_email": "bar@pingou.com",
                        "emails": ["bar@pingou.com", "foo@pingou.com"],
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                    "username": "Jenkins",
                },
                "message": "Flag added",
                "uid": "jenkins_build_pagure_100+seed",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "pingou",
            },
        )

        # One flag added - but no longer on the request object
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        self.assertEqual(len(request.flags), 0)

        flags = pagure.lib.query.get_commit_flag(
            self.session, request.project, "hash_commit_stop"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].comment, "Tests passed")
        self.assertEqual(flags[0].percent, 100)

        data = {
            "username": "Jenkins",
            "comment": "Tests running again",
            "url": "http://jenkins.cloud.fedoraproject.org/",
        }

        # Valid request
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        self.assertNotEqual(data["uid"], "jenkins_build_pagure_100+seed")
        data["uid"] = "jenkins_build_pagure_100+seed"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "flag": {
                    "comment": "Tests running again",
                    "commit_hash": "hash_commit_stop",
                    "date_created": "1510742565",
                    "date_updated": "1510742565",
                    "percent": None,
                    "status": "pending",
                    "url": "http://jenkins.cloud.fedoraproject.org/",
                    "user": {
                        "default_email": "bar@pingou.com",
                        "emails": ["bar@pingou.com", "foo@pingou.com"],
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                    "username": "Jenkins",
                },
                "message": "Flag added",
                "uid": "jenkins_build_pagure_100+seed",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "pingou",
            },
        )

        # Two flags added - but no longer on the request object
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        self.assertEqual(len(request.flags), 0)

        flags = pagure.lib.query.get_commit_flag(
            self.session, request.project, "hash_commit_stop"
        )
        self.assertEqual(len(flags), 2)
        self.assertEqual(flags[1].comment, "Tests running again")
        self.assertEqual(flags[1].percent, None)
        self.assertEqual(flags[0].comment, "Tests passed")
        self.assertEqual(flags[0].percent, 100)

    @patch.dict(
        "pagure.config.config",
        {
            "FLAG_STATUSES_LABELS": {
                "pend!": "label-info",
                "succeed!": "label-success",
                "fail!": "label-danger",
                "what?": "label-warning",
            },
            "FLAG_PENDING": "pend!",
            "FLAG_SUCCESS": "succeed!",
            "FLAG_FAILURE": "fail!",
        },
    )
    def test_flagging_a_pull_request_while_having_custom_statuses(self):
        """ Test flagging a PR while having custom statuses. """
        headers = {"Authorization": "token aaabbbcccddd"}

        # No status and no percent => should use FLAG_PENDING
        send_data = {
            "username": "Jenkins",
            "comment": "Tests running",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }

        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=send_data, headers=headers
        )
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(output.status_code, 200)
        self.assertEqual(data["flag"]["status"], "pend!")

        # No status and 50 % => should use FLAG_SUCCESS
        send_data["percent"] = 50
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=send_data, headers=headers
        )
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(output.status_code, 200)
        self.assertEqual(data["flag"]["status"], "succeed!")

        # No status and 0 % => should use FLAG_FAILURE
        send_data["percent"] = 0
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=send_data, headers=headers
        )
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(output.status_code, 200)
        self.assertEqual(data["flag"]["status"], "fail!")

        # Explicitly set status
        send_data["status"] = "what?"
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=send_data, headers=headers
        )
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(output.status_code, 200)
        self.assertEqual(data["flag"]["status"], "what?")

        # Explicitly set wrong status
        send_data["status"] = "nooo....."
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=send_data, headers=headers
        )
        data = json.loads(output.get_data(as_text=True))
        self.assertEqual(output.status_code, 400)
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"status": ["Not a valid choice"]},
            },
        )


class PagureFlaskApiPRFlagUserTokentests(tests.Modeltests):
    """Tests for the flask API of pagure for flagging pull-requests using
    an user token (ie: not restricted to a specific project).
    """

    maxDiff = None

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiPRFlagUserTokentests, self).setUp()

        pagure.config.config["REQUESTS_FOLDER"] = None

        tests.create_projects(self.session)
        tests.create_tokens(self.session, project_id=None)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        forked_repo = pagure.lib.query.get_authorized_project(
            self.session, "test"
        )
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from="master",
            repo_to=repo,
            branch_to="master",
            title="test pull-request",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "test pull-request")

        # Check flags before
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        request.commit_stop = "hash_commit_stop"
        self.session.add(request)
        self.session.commit()
        self.assertEqual(len(request.flags), 0)

    def test_no_pr(self):
        """ Test flagging a non-existing PR. """
        headers = {"Authorization": "token aaabbbcccddd"}

        # Invalid project
        output = self.app.post(
            "/api/0/foo/pull-request/1/flag", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_no_pr_other_project(self):
        """ Test flagging a non-existing PR on a different project. """
        headers = {"Authorization": "token aaabbbcccddd"}
        # Valid token, wrong project
        output = self.app.post(
            "/api/0/test2/pull-request/1/flag", headers=headers
        )
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Pull-Request not found", "error_code": "ENOREQ"}
        )

    def test_no_input(self):
        """ Test flagging an existing PR but without submitting any data. """
        headers = {"Authorization": "token aaabbbcccddd"}

        # No input
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {
                    "comment": ["This field is required."],
                    "url": ["This field is required."],
                    "username": ["This field is required."],
                },
            },
        )

    def test_no_comment(self):
        """Test flagging an existing PR but without all the required info."""
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "username": "Jenkins",
            "percent": 100,
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }

        # Incomplete request
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"comment": ["This field is required."]},
            },
        )

        # No change
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        self.assertEqual(len(request.flags), 0)

    def test_invalid_status(self):
        """Test flagging an existing PR but with an invalid status."""
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "username": "Jenkins",
            "status": "failed",
            "comment": "Failed to run the tests",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }

        # Invalid status submitted
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Invalid or incomplete input submitted",
                "error_code": "EINVALIDREQ",
                "errors": {"status": ["Not a valid choice"]},
            },
        )

        # No change
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        self.assertEqual(len(request.flags), 0)

    @patch("pagure.lib.notify.send_email")
    def test_flag_pr_no_status(self, mock_email):
        """Test flagging an existing PR without providing a status.

        Also check that no notifications have been sent.
        """
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "username": "Jenkins",
            "percent": 0,
            "comment": "Tests failed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }

        # Valid request  -  w/o providing the status
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "flag": {
                    "comment": "Tests failed",
                    "commit_hash": "hash_commit_stop",
                    "date_created": "1510742565",
                    "date_updated": "1510742565",
                    "percent": 0,
                    "status": "failure",
                    "url": "http://jenkins.cloud.fedoraproject.org/",
                    "user": {
                        "default_email": "bar@pingou.com",
                        "emails": ["bar@pingou.com", "foo@pingou.com"],
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                    "username": "Jenkins",
                },
                "message": "Flag added",
                "uid": "jenkins_build_pagure_100+seed",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "pingou",
            },
        )

        # One flag added
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        self.assertEqual(len(request.flags), 0)

        flags = pagure.lib.query.get_commit_flag(
            self.session, request.project, "hash_commit_stop"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].comment, "Tests failed")
        self.assertEqual(flags[0].percent, 0)

        # no notifications sent
        mock_email.assert_not_called()

    def test_editing_flag(self):
        """Test flagging an existing PR without providing a status."""
        headers = {"Authorization": "token aaabbbcccddd"}

        data = {
            "username": "Jenkins",
            "status": "failure",
            "comment": "Tests failed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
        }

        # Valid request  -  w/o providing the status
        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "flag": {
                    "comment": "Tests failed",
                    "commit_hash": "hash_commit_stop",
                    "date_created": "1510742565",
                    "date_updated": "1510742565",
                    "percent": None,
                    "status": "failure",
                    "url": "http://jenkins.cloud.fedoraproject.org/",
                    "user": {
                        "default_email": "bar@pingou.com",
                        "emails": ["bar@pingou.com", "foo@pingou.com"],
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                    "username": "Jenkins",
                },
                "message": "Flag added",
                "uid": "jenkins_build_pagure_100+seed",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "pingou",
            },
        )

        # One flag added
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        self.assertEqual(len(request.flags), 0)

        flags = pagure.lib.query.get_commit_flag(
            self.session, request.project, "hash_commit_stop"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].comment, "Tests failed")
        self.assertEqual(flags[0].percent, None)

        # Update flag
        data = {
            "username": "Jenkins",
            "percent": 100,
            "comment": "Tests passed",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "uid": "jenkins_build_pagure_100+seed",
            "status": "success",
        }

        output = self.app.post(
            "/api/0/test/pull-request/1/flag", data=data, headers=headers
        )
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flag"]["date_created"] = "1510742565"
        data["flag"]["date_updated"] = "1510742565"
        data["avatar_url"] = "https://seccdn.libravatar.org/avatar/..."
        self.assertDictEqual(
            data,
            {
                "flag": {
                    "comment": "Tests passed",
                    "commit_hash": "hash_commit_stop",
                    "date_created": "1510742565",
                    "date_updated": "1510742565",
                    "percent": 100,
                    "status": "success",
                    "url": "http://jenkins.cloud.fedoraproject.org/",
                    "user": {
                        "default_email": "bar@pingou.com",
                        "emails": ["bar@pingou.com", "foo@pingou.com"],
                        "full_url": "http://localhost.localdomain/user/pingou",
                        "fullname": "PY C",
                        "name": "pingou",
                        "url_path": "user/pingou",
                    },
                    "username": "Jenkins",
                },
                "message": "Flag updated",
                "uid": "jenkins_build_pagure_100+seed",
                "avatar_url": "https://seccdn.libravatar.org/avatar/...",
                "user": "pingou",
            },
        )

        # Still only one flag
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        self.assertEqual(len(request.flags), 0)

        flags = pagure.lib.query.get_commit_flag(
            self.session, request.project, "hash_commit_stop"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].comment, "Tests passed")
        self.assertEqual(flags[0].percent, 100)


class PagureFlaskApiGetPRFlagtests(tests.Modeltests):
    """Tests for the flask API of pagure for retrieving pull-requests flags"""

    maxDiff = None

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiGetPRFlagtests, self).setUp()

        pagure.config.config["REQUESTS_FOLDER"] = None

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create a pull-request
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        forked_repo = pagure.lib.query.get_authorized_project(
            self.session, "test"
        )
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from="master",
            repo_to=repo,
            branch_to="master",
            title="test pull-request",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "test pull-request")

        # Check flags before
        self.session.commit()
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        request.commit_stop = "hash_commit_stop"
        self.session.add(request)
        self.session.commit()
        self.assertEqual(len(request.flags), 0)

    def test_invalid_project(self):
        """ Test the retrieving the flags of a PR on an invalid project. """

        # Invalid project
        output = self.app.get("/api/0/foo/pull-request/1/flag")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Project not found", "error_code": "ENOPROJECT"}
        )

    def test_pr_disabled(self):
        """ Test the retrieving the flags of a PR when PRs are disabled. """

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        settings = repo.settings
        settings["pull_requests"] = False
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        # PRs disabled
        output = self.app.get("/api/0/test/pull-request/1/flag")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data,
            {
                "error": "Pull-Request have been deactivated for this project",
                "error_code": "EPULLREQUESTSDISABLED",
            },
        )

    def test_no_pr(self):
        """ Test the retrieving the flags of a PR when the PR doesn't exist. """

        # No PR
        output = self.app.get("/api/0/test/pull-request/10/flag")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"error": "Pull-Request not found", "error_code": "ENOREQ"}
        )

    def test_no_flag(self):
        """ Test the retrieving the flags of a PR when the PR has no flags. """

        # No flag
        output = self.app.get("/api/0/test/pull-request/1/flag")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(data, {"flags": []})

    def test_get_flag(self):
        """ Test the retrieving the flags of a PR when the PR has one flag. """

        # Add a flag to the PR
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        msg = pagure.lib.query.add_pull_request_flag(
            session=self.session,
            request=request,
            username="jenkins",
            percent=None,
            comment="Build passes",
            status="success",
            url="http://jenkins.cloud.fedoraproject.org",
            uid="jenkins_build_pagure_34",
            user="foo",
            token="aaabbbcccddd",
        )
        self.assertEqual(msg, ("Flag added", "jenkins_build_pagure_34"))
        self.session.commit()

        self.assertEqual(len(request.flags), 0)

        flags = pagure.lib.query.get_commit_flag(
            self.session, request.project, "hash_commit_stop"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].token_id, "aaabbbcccddd")

        # 1 flag
        output = self.app.get("/api/0/test/pull-request/1/flag")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flags"][0]["date_created"] = "1541413645"
        data["flags"][0]["date_updated"] = "1541413645"
        self.assertDictEqual(
            data,
            {
                "flags": [
                    {
                        "comment": "Build passes",
                        "commit_hash": "hash_commit_stop",
                        "date_created": "1541413645",
                        "date_updated": "1541413645",
                        "percent": None,
                        "status": "success",
                        "url": "http://jenkins.cloud.fedoraproject.org",
                        "user": {
                            "fullname": "foo bar",
                            "full_url": "http://localhost.localdomain/user/foo",
                            "name": "foo",
                            "url_path": "user/foo",
                        },
                        "username": "jenkins",
                    }
                ]
            },
        )

    def test_get_flags(self):
        """ Test the retrieving the flags of a PR when the PR has one flag. """

        # Add two flags to the PR
        request = pagure.lib.query.search_pull_requests(
            self.session, project_id=1, requestid=1
        )
        msg = pagure.lib.query.add_pull_request_flag(
            session=self.session,
            request=request,
            username="jenkins",
            percent=None,
            comment="Build passes",
            status="success",
            url="http://jenkins.cloud.fedoraproject.org",
            uid="jenkins_build_pagure_34",
            user="foo",
            token="aaabbbcccddd",
        )
        self.assertEqual(msg, ("Flag added", "jenkins_build_pagure_34"))
        self.session.commit()

        msg = pagure.lib.query.add_pull_request_flag(
            session=self.session,
            request=request,
            username="travis",
            percent=None,
            comment="Build pending",
            status="pending",
            url="http://travis.io",
            uid="travis_build_pagure_34",
            user="foo",
            token="aaabbbcccddd",
        )
        self.assertEqual(msg, ("Flag added", "travis_build_pagure_34"))
        self.session.commit()

        self.assertEqual(len(request.flags), 0)

        flags = pagure.lib.query.get_commit_flag(
            self.session, request.project, "hash_commit_stop"
        )
        self.assertEqual(len(flags), 2)
        self.assertEqual(flags[1].token_id, "aaabbbcccddd")
        self.assertEqual(flags[0].token_id, "aaabbbcccddd")

        # 1 flag
        output = self.app.get("/api/0/test/pull-request/1/flag")
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        data["flags"][0]["date_created"] = "1541413645"
        data["flags"][0]["date_updated"] = "1541413645"
        data["flags"][1]["date_created"] = "1541413645"
        data["flags"][1]["date_updated"] = "1541413645"
        self.assertDictEqual(
            data,
            {
                "flags": [
                    {
                        "comment": "Build passes",
                        "commit_hash": "hash_commit_stop",
                        "date_created": "1541413645",
                        "date_updated": "1541413645",
                        "percent": None,
                        "status": "success",
                        "url": "http://jenkins.cloud.fedoraproject.org",
                        "user": {
                            "fullname": "foo bar",
                            "name": "foo",
                            "full_url": "http://localhost.localdomain/user/foo",
                            "url_path": "user/foo",
                        },
                        "username": "jenkins",
                    },
                    {
                        "comment": "Build pending",
                        "commit_hash": "hash_commit_stop",
                        "date_created": "1541413645",
                        "date_updated": "1541413645",
                        "percent": None,
                        "status": "pending",
                        "url": "http://travis.io",
                        "user": {
                            "fullname": "foo bar",
                            "name": "foo",
                            "full_url": "http://localhost.localdomain/user/foo",
                            "url_path": "user/foo",
                        },
                        "username": "travis",
                    },
                ]
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
