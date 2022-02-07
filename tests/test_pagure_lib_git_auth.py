# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Patrick Uiterwijk <patrick@puiterwijk.org>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import os
import shutil
import sys
import tempfile
import time
import unittest

import pygit2
import six
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.git
import pagure.lib.query
import tests

from pagure.lib.repo import PagureRepo


class PagureLibGitAuthtests(tests.Modeltests):
    """Tests for pagure.lib.git_auth"""

    config_values = {"authbackend": "test_auth"}

    def setUp(self):
        super(PagureLibGitAuthtests, self).setUp()

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        self.create_project_full("hooktest")

    def test_edit_with_all_allowed(self):
        """Tests that editing a file is possible if ACLs say allowed."""
        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "hooktest.git")
            )

            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "email": "bar@pingou.com",
                "branch": "master",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/hooktest/edit/master/f/sources",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Commits - hooktest - Pagure</title>", output_text
            )
            self.assertIn("test commit", output_text)

            # Check file after the commit
            output = self.app.get("/hooktest/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar\n  baz")

    def test_edit_with_all_denied(self):
        """Tests that editing a file is not possible if ACLs say denied."""
        self.set_auth_status(False)

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "hooktest.git")
            )

            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "email": "bar@pingou.com",
                "branch": "master",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/hooktest/edit/master/f/sources",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "Remote hook declined the push: "
                "Denied push for ref &#39;refs/heads/master&#39; for user &#39;pingou&#39;",
                output_text,
            )
            self.assertIn("All changes have been rejected", output_text)

            # Check file after the commit:
            output = self.app.get("/hooktest/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar")

    def test_edit_pr(self):
        """Tests the ACLs if they only accept PRs."""
        self.set_auth_status(
            {"refs/heads/master": "pronly", "refs/heads/source": True}
        )

        user = tests.FakeUser()
        user.username = "pingou"
        with tests.user_set(self.app.application, user):
            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "hooktest.git")
            )

            # Try editing master branch, should fail (only PRs allowed)
            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "email": "bar@pingou.com",
                "branch": "master",
                "csrf_token": self.get_csrf(),
            }
            output = self.app.post(
                "/hooktest/edit/master/f/sources",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "Remote hook declined the push: "
                "Denied push for ref &#39;refs/heads/master&#39; for user &#39;pingou&#39;",
                output_text,
            )
            self.assertIn("All changes have been rejected", output_text)

            # Change something in the "source" branch
            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "email": "bar@pingou.com",
                "branch": "source",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/hooktest/edit/master/f/sources",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Commits - hooktest - Pagure</title>", output_text
            )
            self.assertIn("test commit", output_text)

            # Check file after the commit:
            output = self.app.get("/hooktest/raw/source/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar\n  baz")

            # Create the PRs
            project = pagure.lib.query.get_authorized_project(
                self.session, "hooktest"
            )
            req = pagure.lib.query.new_pull_request(
                session=self.session,
                repo_from=project,
                branch_from="source",
                repo_to=project,
                branch_to="master",
                title="PR to master",
                user="pingou",
            )
            self.session.add(req)
            self.session.commit()

            # Check file before the merge
            output = self.app.get("/hooktest/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar")

            # Try to merge (should work)
            output = self.app.post(
                "/hooktest/pull-request/1/merge",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>PR#1: PR to master - hooktest\n - Pagure</title>",
                output_text,
            )

            # Check file after the merge
            output = self.app.get("/hooktest/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar\n  baz")


class PagureLibGitAuthPagureBackendtests(tests.Modeltests):
    """Tests for pagure.lib.git_auth"""

    config_values = {"authbackend": "pagure"}

    def setUp(self):
        super(PagureLibGitAuthPagureBackendtests, self).setUp()

        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        self.create_project_full("hooktest")

    def test_edit_no_commit(self):

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "hooktest.git")
            )

            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "email": "bar@pingou.com",
                "branch": "master",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/hooktest/edit/master/f/sources",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 403)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "You are not allowed to edit files in this project",
                output_text,
            )

            # Check file after the commit:
            output = self.app.get("/hooktest/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar")

    def test_edit_ticket_rejected(self):
        project = pagure.lib.query._get_project(self.session, "hooktest")

        # Add user foo to project test
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="ticket",
            branches="epel*",
        )
        self.session.commit()

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "hooktest.git")
            )

            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "email": "foo@bar.com",
                "branch": "master",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/hooktest/edit/master/f/sources",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 403)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "You are not allowed to edit files in this project",
                output_text,
            )

            # Check file after the commit:
            output = self.app.get("/hooktest/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar")

    def test_edit_contributor_rejected(self):
        project = pagure.lib.query._get_project(self.session, "hooktest")

        # Add user foo to project test
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="collaborator",
            branches="epel*",
        )
        self.session.commit()

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "hooktest.git")
            )

            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "email": "foo@bar.com",
                "branch": "master",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/hooktest/edit/master/f/sources",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 403)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "You are not allowed to edit files in this project",
                output_text,
            )

            # Check file after the commit:
            output = self.app.get("/hooktest/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar")

    def test_edit_contributor_passed_epel8(self):
        project = pagure.lib.query._get_project(self.session, "hooktest")

        # Add user foo to project test
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="collaborator",
            branches="epel*",
        )
        self.session.commit()

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "hooktest.git")
            )

            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "email": "foo@bar.com",
                "branch": "epel8",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/hooktest/edit/master/f/sources",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Commits - hooktest - Pagure</title>", output_text
            )

            # Check file after the commit:
            # master did not change
            output = self.app.get("/hooktest/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar")

            # epel8 did change
            output = self.app.get("/hooktest/raw/epel8/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar\n  baz")

    def test_edit_commit_passed_epel8(self):
        project = pagure.lib.query._get_project(self.session, "hooktest")

        # Add user foo to project test
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="commit",
            branches="epel*",
        )
        self.session.commit()

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "hooktest.git")
            )

            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "email": "foo@bar.com",
                "branch": "epel8",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/hooktest/edit/master/f/sources",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Commits - hooktest - Pagure</title>", output_text
            )

            # Check file after the commit:
            # master did not change
            output = self.app.get("/hooktest/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar")

            # epel8 did change
            output = self.app.get("/hooktest/raw/epel8/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar\n  baz")

    def test_edit_contributor_passed_epel(self):
        # Same test as above but the target branch change
        project = pagure.lib.query._get_project(self.session, "hooktest")

        # Add user foo to project test
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="collaborator",
            branches="epel*",
        )
        self.session.commit()

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "hooktest.git")
            )

            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "email": "foo@bar.com",
                "branch": "epel",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/hooktest/edit/master/f/sources",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Commits - hooktest - Pagure</title>", output_text
            )

            # Check file after the commit:
            # master did not change
            output = self.app.get("/hooktest/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar")

            # epel did change
            output = self.app.get("/hooktest/raw/epel/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar\n  baz")

    def test_edit_contributor_passed_epel_no_regex(self):
        # Same test as above but the allowed branch has no regex
        project = pagure.lib.query._get_project(self.session, "hooktest")

        # Add user foo to project test
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="collaborator",
            branches="epel",
        )
        self.session.commit()

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "hooktest.git")
            )

            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "email": "foo@bar.com",
                "branch": "epel",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/hooktest/edit/master/f/sources",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Commits - hooktest - Pagure</title>", output_text
            )

            # Check file after the commit:
            # master did not change
            output = self.app.get("/hooktest/raw/master/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar")

            # epel did change
            output = self.app.get("/hooktest/raw/epel/f/sources")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar\n  baz")

    def test_edit_contributor_denied_epel8_no_regex(self):
        # Same test as above but the allowed branch has no regex
        project = pagure.lib.query._get_project(self.session, "hooktest")

        # Add user foo to project test
        msg = pagure.lib.query.add_user_to_project(
            self.session,
            project=project,
            new_user="foo",
            user="pingou",
            access="collaborator",
            branches="epel",
        )
        self.session.commit()

        user = tests.FakeUser()
        user.username = "foo"
        with tests.user_set(self.app.application, user):
            # Add some content to the git repo
            tests.add_content_git_repo(
                os.path.join(self.path, "repos", "hooktest.git")
            )

            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commits from the gure.lib.get",
                "email": "foo@bar.com",
                "branch": "epel8",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/hooktest/edit/master/f/sources",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 403)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "You are not allowed to edit files in this project",
                output_text,
            )

            # Check file after the commit:
            # epel not found
            output = self.app.get("/hooktest/raw/epel8/f/sources")
            self.assertEqual(output.status_code, 404)
