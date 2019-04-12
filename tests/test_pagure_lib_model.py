# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import sys
import os

from mock import patch

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.model
import pagure.lib.query
import tests


class PagureLibModeltests(tests.Modeltests):
    """ Tests for pagure.lib.model """

    def test_user__repr__(self):
        """ Test the User.__repr__ function of pagure.lib.model. """
        item = pagure.lib.query.search_user(self.session, email="foo@bar.com")
        self.assertEqual(str(item), "User: 2 - name foo")
        self.assertEqual("foo", item.user)
        self.assertEqual("foo", item.username)
        self.assertEqual([], item.groups)

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_issue__repr__(self, p_send_email, p_ugt):
        """ Test the Issue.__repr__ function of pagure.lib.model. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Create an issue
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
        )
        self.assertEqual(msg.title, "Test issue")

        issues = pagure.lib.query.search_issues(self.session, repo)
        self.assertEqual(len(issues), 1)
        self.assertEqual(
            str(issues[0]),
            "Issue(1, project:test, user:pingou, title:Test issue)",
        )

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def test_pullrequest__repr__(self, p_send_email, p_ugt):
        """ Test the PullRequest.__repr__ function of pagure.lib.model. """
        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        # Create a forked repo
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test",
            description="test project #1",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbyyy",
        )
        self.session.commit()
        self.session.add(item)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        forked_repo = pagure.lib.query.get_authorized_project(
            self.session, "test", user="pingou"
        )

        # Create an pull-request
        req = pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=forked_repo,
            branch_from="master",
            repo_to=repo,
            branch_to="master",
            title="test pull-request",
            user="pingou",
        )
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, "test pull-request")

        self.assertEqual(
            str(req),
            "PullRequest(1, project:test, user:pingou, "
            "title:test pull-request)",
        )

        request = pagure.lib.query.search_pull_requests(
            self.session, requestid=1
        )
        self.assertEqual(
            str(request),
            "PullRequest(1, project:test, user:pingou, "
            "title:test pull-request)",
        )

    def test_paguregroup__repr__(self):
        """ Test the PagureGroup.__repr__ function of pagure.lib.model. """
        item = pagure.lib.model.PagureGroup(
            group_name="admin",
            display_name="admin group",
            description="the local admin group",
            user_id=1,
        )
        self.session.add(item)
        self.session.commit()

        self.assertEqual(str(item), "Group: 1 - name admin")

    def test_tagissue__repr__(self):
        """ Test the TagIssue.__repr__ function of pagure.lib.model. """
        self.test_issue__repr__()
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issues = pagure.lib.query.search_issues(self.session, repo)
        self.assertEqual(len(issues), 1)

        item = pagure.lib.model.Tag(tag="foo")
        self.session.add(item)
        self.session.commit()

        item = pagure.lib.model.TagIssue(issue_uid=issues[0].uid, tag="foo")
        self.session.add(item)
        self.session.commit()
        self.assertEqual(str(item), "TagIssue(issue:1, tag:foo)")

    def test_tagissuecolor__repr__(self):
        """ Test the TagIssue.__repr__ function of pagure.lib.model. """
        self.test_issue__repr__()
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        issues = pagure.lib.query.search_issues(self.session, repo)
        self.assertEqual(len(issues), 1)

        item = pagure.lib.model.TagColored(
            tag="foo",
            tag_description="bar",
            tag_color="DeepSkyBlue",
            project_id=repo.id,
        )
        self.session.add(item)
        self.session.commit()

        item = pagure.lib.model.TagIssueColored(
            issue_uid=issues[0].uid, tag_id=item.id
        )
        self.session.add(item)
        self.session.commit()
        self.assertEqual(
            str(item), "TagIssueColored(issue:1, tag:foo, project:test)"
        )

    def test_group_project_ordering(self):
        """ Test the ordering of project.groups. """
        # Create three projects
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="aaa",
            description="Project aaa",
            hook_token="aaabbbccc",
        )
        item.close_status = ["Invalid", "Fixed", "Duplicate"]
        self.session.add(item)

        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="KKK",
            description="project KKK",
            hook_token="aaabbbddd",
        )
        item.close_status = ["Invalid", "Fixed", "Duplicate"]
        self.session.add(item)

        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="zzz",
            description="Namespaced project zzz",
            hook_token="aaabbbeee",
            namespace="somenamespace",
        )
        item.close_status = ["Invalid", "Fixed", "Duplicate"]
        self.session.add(item)

        # Create a group
        group = pagure.lib.model.PagureGroup(
            group_name="testgrp",
            display_name="Test group",
            description=None,
            group_type="user",
            user_id=1,  # pingou
        )
        item.close_status = ["Invalid", "Fixed", "Duplicate"]
        self.session.add(group)

        self.session.commit()

        # Add projects to group
        for ns, reponame in [
            (None, "aaa"),
            (None, "KKK"),
            ("somenamespace", "zzz"),
        ]:

            repo = pagure.lib.query.get_authorized_project(
                self.session, reponame, namespace=ns
            )
            msg = pagure.lib.query.add_group_to_project(
                self.session,
                project=repo,
                new_group="testgrp",
                user="pingou",
                create=False,
                is_admin=False,
            )
            self.session.commit()
            self.assertEqual(msg, "Group added")

        # Check the ordering
        group = pagure.lib.query.search_groups(
            self.session, group_name="testgrp"
        )
        # Default PostgreSQL order
        order = ["aaa", "KKK", "somenamespace/zzz"]
        # Odd, SQLite order
        if str(self.session.bind.engine.url).startswith("sqlite:"):
            order = ["somenamespace/zzz", "aaa", "KKK"]

        self.assertEqual([p.fullname for p in group.projects], order)


if __name__ == "__main__":
    unittest.main(verbosity=2)
