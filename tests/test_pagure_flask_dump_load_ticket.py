# -*- coding: utf-8 -*-

"""
 (c) 2015-2020 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import json
import unittest
import shutil
import sys
import tempfile
import time
import os

import pygit2
from mock import patch

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests

from pagure.config import config as pagure_config, reload_config


class PagureFlaskDumpLoadTicketTests(tests.Modeltests):
    """Tests for flask application for dumping and re-loading the JSON of
    a ticket.
    """

    @patch("pagure.lib.notify.send_email")
    def test_dumping_reloading_ticket(self, send_email):
        """Test dumping a ticket into a JSON blob."""
        send_email.return_value = True

        tests.create_projects(self.session)

        # Create repo
        self.gitrepo = os.path.join(self.path, "repos", "tickets", "test.git")
        repopath = os.path.join(self.path, "repos", "tickets")
        os.makedirs(self.gitrepo)
        repo_obj = pygit2.init_repository(self.gitrepo, bare=True)

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        # Create an issue to play with
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue",
            content="We should work on this",
            user="pingou",
        )
        self.assertEqual(msg.title, "Test issue")

        # Need another two issue to test the dependencie chain
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #2",
            content="Another bug",
            user="pingou",
        )
        self.assertEqual(msg.title, "Test issue #2")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #3",
            content="That would be nice feature no?",
            user="foo",
        )
        self.assertEqual(msg.title, "Test issue #3")

        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        issue2 = pagure.lib.query.search_issues(self.session, repo, issueid=2)
        issue3 = pagure.lib.query.search_issues(self.session, repo, issueid=3)

        # Add a couple of comment on the ticket
        msg = pagure.lib.query.add_issue_comment(
            session=self.session,
            issue=issue,
            comment="Hey look a comment!",
            user="foo",
        )
        self.session.commit()
        self.assertEqual(msg, "Comment added")
        msg = pagure.lib.query.add_issue_comment(
            session=self.session,
            issue=issue,
            comment="crazy right?",
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(msg, "Comment added")
        # Assign the ticket to someone
        msg = pagure.lib.query.add_issue_assignee(
            session=self.session, issue=issue, assignee="pingou", user="pingou"
        )
        self.session.commit()
        self.assertEqual(msg, "Issue assigned to pingou")
        # Add a couple of tags on the ticket
        msg = pagure.lib.query.add_tag_obj(
            session=self.session,
            obj=issue,
            tags=[" feature ", "future "],
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(msg, "Issue tagged with: feature, future")
        # Add dependencies
        msg = pagure.lib.query.add_issue_dependency(
            session=self.session,
            issue=issue,
            issue_blocked=issue2,
            user="pingou",
        )
        self.session.commit()
        self.assertEqual(msg, "Issue marked as depending on: #2")
        msg = pagure.lib.query.add_issue_dependency(
            session=self.session, issue=issue3, issue_blocked=issue, user="foo"
        )
        self.session.commit()
        self.assertEqual(msg, "Issue marked as depending on: #1")

        # Dump the JSON
        pagure.lib.git.update_git(issue, repo).wait()
        repo = pygit2.Repository(self.gitrepo)
        cnt = len(
            [
                commit
                for commit in repo.walk(
                    repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL
                )
            ]
        )
        self.assertIn(cnt, (9, 10, 11))

        last_commit = repo.revparse_single("HEAD")
        patch = pagure.lib.git.commit_to_patch(repo, last_commit)
        for line in patch.split("\n"):
            if line.startswith("--- a/"):
                fileid = line.split("--- a/")[1]
                break

        newpath = tempfile.mkdtemp(prefix="pagure-dump-load")
        clone_repo = pygit2.clone_repository(self.gitrepo, newpath)

        self.assertEqual(len(os.listdir(newpath)), 4)

        ticket_json = os.path.join(self.path, "test_ticket.json")
        self.assertFalse(os.path.exists(ticket_json))
        shutil.copyfile(os.path.join(newpath, fileid), ticket_json)
        self.assertTrue(os.path.exists(ticket_json))
        jsondata = None
        with open(ticket_json) as stream:
            jsondata = json.load(stream)
        self.assertNotEqual(jsondata, None)

        shutil.rmtree(newpath)

        # Test reloading the JSON

        # Re-create the DB from scratch
        self.session.rollback()
        self._clear_database()
        self.db_session.close()
        del self.session
        del self.db_session

        os.unlink(os.path.join(self.dbfolder, "db.sqlite"))

        self.db_session = pagure.lib.model.create_tables(
            self.dbpath,
            acls=pagure_config.get("ACLS", {}),
        )
        self._prepare_db()
        tests.create_projects(self.session)

        # Create repo
        self.gitrepo = os.path.join(self.path, "tickets", "test.git")
        repopath = os.path.join(self.path, "tickets")
        os.makedirs(self.gitrepo)
        pygit2.init_repository(self.gitrepo, bare=True)

        pagure.lib.git.update_ticket_from_git(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            issue_uid="foobar",
            json_data=jsondata,
            agent="pingou",
        )

        # Post loading
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.issues), 1)
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)

        # Check after re-loading
        self.assertEqual(len(issue.comments), 3)
        self.assertEqual(len(issue.tags), 2)
        self.assertEqual(
            sorted(issue.tags_text), sorted(["future", "feature"])
        )
        self.assertEqual(issue.assignee.username, "pingou")
        self.assertEqual(issue.children, [])
        self.assertEqual(issue.parents, [])
        self.assertEqual(issue.status, "Open")


if __name__ == "__main__":
    unittest.main(verbosity=2)
