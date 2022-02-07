# -*- coding: utf-8 -*-

"""
 (c) 2019-2019 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Patrick Uiterwijk <patrick@puiterwijk.org>

"""

from __future__ import unicode_literals, absolute_import

import json
import os
import sys

from mock import Mock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests

from pagure.config import config as pagure_config
from pagure.lib.repo import PagureRepo


class PagureLibGitAuthPagureGitAuthtests(tests.Modeltests):
    """Tests for pagure.lib.git_auth PagureGitAuth dynamic ACL"""

    config_values = {"authbackend": "pagure"}

    def setUp(self):
        super(PagureLibGitAuthPagureGitAuthtests, self).setUp()

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        self.create_project_full("acltest")
        project = pagure.lib.query._get_project(self.session, "acltest")
        # Create non-push deploy key
        non_push_dkey = pagure.lib.model.SSHKey(
            project_id=project.id,
            pushaccess=False,
            public_ssh_key="\n foo bar",
            ssh_short_key="\n foo bar",
            ssh_search_key="\n foo bar",
            creator_user_id=1,  # pingou
        )
        self.session.add(non_push_dkey)
        # Create push deploy key
        push_dkey = pagure.lib.model.SSHKey(
            project_id=project.id,
            pushaccess=True,
            public_ssh_key="\n bar foo",
            ssh_short_key="\n bar foo",
            ssh_search_key="\n bar foo",
            creator_user_id=1,  # pingou
        )
        self.session.add(push_dkey)
        self.session.commit()

        # Allow the user foo to commit to project test on epel* branches
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="collaborator",
            branches="epel*",
        )
        self.session.commit()

    def create_fork(self):
        # Create fork
        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"repo": "acltest"}
        output = self.app.post("/api/0/fork/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": 'Repo "acltest" cloned to "pingou/acltest"'}
        )

    CASES = (
        # Internal push
        {
            "internal": True,
            "username": "foo",
            "project_pr_only": False,
            "global_pr_only": False,
            "project": {"name": "acltest"},
            "ref": "refs/heads/master",
            "repotype": "main",
            "expected_messages": ["Internal push allowed"],
            "expected_result": True,
        },
        # Globally PR required push: PR merges are always internal
        {
            "internal": False,
            "username": "foo",
            "project_pr_only": False,
            "global_pr_only": True,
            "project": {"name": "acltest"},
            "ref": "refs/heads/master",
            "repotype": "main",
            "expected_messages": ["Pull request required"],
            "expected_result": False,
        },
        # GLobally PR required, push is to fork
        {
            "internal": False,
            "username": "foo",
            "project_pr_only": False,
            "global_pr_only": True,
            "project": {"name": "acltest", "user": "pingou"},
            "ref": "refs/heads/master",
            "repotype": "main",
            "expected_messages": ["Has commit access: False"],
            "expected_result": False,
        },
        # PR required push: PR merges are always internal
        {
            "internal": False,
            "username": "foo",
            "project_pr_only": True,
            "global_pr_only": False,
            "project": {"name": "acltest"},
            "ref": "refs/heads/master",
            "repotype": "main",
            "expected_messages": ["Pull request required"],
            "expected_result": False,
        },
        # PR required for main repo, but not for ticket
        {
            "internal": False,
            "username": "foo",
            "project_pr_only": True,
            "global_pr_only": False,
            "project": {"name": "acltest"},
            "ref": "refs/heads/master",
            "repotype": "ticket",
            "expected_messages": ["Has commit access: False"],
            "expected_result": False,
        },
        # Non-push deploy key
        {
            "internal": False,
            "username": "deploykey_acltest_1",
            "project_pr_only": False,
            "global_pr_only": False,
            "project": {"name": "acltest"},
            "ref": "refs/heads/master",
            "repotype": "main",
            "expected_messages": [
                "Deploykey used. Push access: False",
                "Has commit access: False",
            ],
            "expected_result": False,
        },
        # Push deploy key
        {
            "internal": False,
            "username": "deploykey_acltest_2",
            "project_pr_only": False,
            "global_pr_only": False,
            "project": {"name": "acltest"},
            "ref": "refs/heads/master",
            "repotype": "main",
            "expected_messages": [
                "Deploykey used. Push access: True",
                "Has commit access: True",
            ],
            "expected_result": True,
        },
        # Non-committer
        {
            "internal": False,
            "username": "foo",
            "project_pr_only": False,
            "global_pr_only": False,
            "project": {"name": "acltest"},
            "ref": "refs/heads/master",
            "repotype": "main",
            "expected_messages": ["Has commit access: False"],
            "expected_result": False,
        },
        # Committer
        {
            "internal": False,
            "username": "pingou",
            "project_pr_only": False,
            "global_pr_only": False,
            "project": {"name": "acltest"},
            "ref": "refs/heads/master",
            "repotype": "main",
            "expected_messages": ["Has commit access: True"],
            "expected_result": True,
        },
        # Contributor invalid branch
        {
            "internal": False,
            "username": "foo",
            "project_pr_only": False,
            "global_pr_only": False,
            "project": {"name": "acltest"},
            "ref": "refs/heads/master",
            "repotype": "main",
            "expected_messages": ["Has commit access: False"],
            "expected_result": False,
        },
        # Contributor valid branch epel-foo
        {
            "internal": False,
            "username": "foo",
            "project_pr_only": False,
            "global_pr_only": False,
            "project": {"name": "acltest"},
            "ref": "refs/heads/epel-foo",
            "repotype": "main",
            "expected_messages": ["Has commit access: True"],
            "expected_result": True,
        },
        # Contributor valid branch epel
        {
            "internal": False,
            "username": "foo",
            "project_pr_only": False,
            "global_pr_only": False,
            "project": {"name": "acltest"},
            "ref": "refs/heads/epel",
            "repotype": "main",
            "expected_messages": ["Has commit access: True"],
            "expected_result": True,
        },
    )

    def test_cases(self):
        self.create_fork()

        ga = pagure.lib.git_auth.PagureGitAuth()
        ga.info = Mock()

        casenum = 0

        for case in self.CASES:
            casenum += 1
            print("Case %d: %s" % (casenum, case))
            project = pagure.lib.query._get_project(
                self.session, **case["project"]
            )

            # Set global PR setting
            pagure_config["PR_ONLY"] = case["global_pr_only"]

            # Set per-project PR setting
            curset = project.settings
            curset["pull_request_access_only"] = case["project_pr_only"]
            project.settings = curset
            self.session.commit()

            result = ga.check_acl(
                session=self.session,
                project=project,
                username=case["username"],
                refname=case["ref"],
                pull_request=None,
                repotype=case["repotype"],
                is_internal=case["internal"],
            )
            print("Result: %s" % result)
            self.assertEqual(
                result,
                case["expected_result"],
                "Expected result not met in case %s" % case,
            )
            print("Correct result")
            self.assertListEqual(
                case["expected_messages"],
                [info_call[0][0] for info_call in ga.info.call_args_list],
            )
            print("Correct messages")
            ga.info.reset_mock()
