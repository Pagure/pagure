# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import shutil
import sys
import os

from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import pagure.lib.model
import tests


class PagureLibDropIssuetests(tests.Modeltests):
    """ Tests for pagure.lib.query.drop_issue """

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    def setUp(self, p_send_email, p_ugt):
        """Create a couple of tickets and add tag to the project so we can
        play with them later.
        """
        super(PagureLibDropIssuetests, self).setUp()

        p_send_email.return_value = True
        p_ugt.return_value = True

        tests.create_projects(self.session)
        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Before
        issues = pagure.lib.query.search_issues(self.session, repo)
        self.assertEqual(len(issues), 0)
        self.assertEqual(repo.open_tickets, 0)
        self.assertEqual(repo.open_tickets_public, 0)

        # Create two issues to play with
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

        # After
        issues = pagure.lib.query.search_issues(self.session, repo)
        self.assertEqual(len(issues), 2)

        # Add tag to the project
        pagure.lib.query.new_tag(
            self.session, "red", "red tag", "#ff0000", repo.id
        )
        self.session.commit()

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(
            str(repo.tags_colored),
            "[TagColored(id: 1, tag:red, tag_description:red tag, color:#ff0000)]",
        )

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    @patch("pagure.lib.git._maybe_wait", tests.definitely_wait)
    def test_drop_issue(self, p_send_email, p_ugt):
        """Test the drop_issue of pagure.lib.query.

        We had an issue where we could not delete issue that had been tagged
        with this test, we create two issues, tag one of them and delete
        it, ensuring it all goes well.
        """
        p_send_email.return_value = True
        p_ugt.return_value = True

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Add tag to the second issue
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)
        msgs = pagure.lib.query.update_tags(
            self.session, issue, tags=["red"], username="pingou"
        )
        self.session.commit()

        self.assertEqual(msgs, ["Issue tagged with: red"])

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.issues), 2)
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)
        self.assertEqual(
            str(issue.tags),
            "[TagColored(id: 1, tag:red, tag_description:red tag, color:#ff0000)]",
        )

        # Drop the issue #2
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)
        pagure.lib.query.drop_issue(self.session, issue, user="pingou")
        self.session.commit()

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.issues), 1)

    @patch("pagure.lib.git.update_git")
    @patch("pagure.lib.notify.send_email")
    @patch("pagure.lib.git._maybe_wait", tests.definitely_wait)
    def test_drop_issue_two_issues_one_tag(self, p_send_email, p_ugt):
        """Test the drop_issue of pagure.lib.query.

        We had an issue where we could not delete issue that had been tagged
        with this test, we create two issues, tag them both and delete one
        then we check that the other issue is still tagged.
        """
        p_send_email.return_value = True
        p_ugt.return_value = True

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        # Add the tag to both issues
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        msgs = pagure.lib.query.update_tags(
            self.session, issue, tags=["red"], username="pingou"
        )
        self.session.commit()
        self.assertEqual(msgs, ["Issue tagged with: red"])

        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)
        msgs = pagure.lib.query.update_tags(
            self.session, issue, tags=["red"], username="pingou"
        )
        self.session.commit()
        self.assertEqual(msgs, ["Issue tagged with: red"])

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.issues), 2)
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(
            str(issue.tags),
            "[TagColored(id: 1, tag:red, tag_description:red tag, color:#ff0000)]",
        )
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)
        self.assertEqual(
            str(issue.tags),
            "[TagColored(id: 1, tag:red, tag_description:red tag, color:#ff0000)]",
        )

        # Drop the issue #2
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)
        pagure.lib.query.drop_issue(self.session, issue, user="pingou")
        self.session.commit()

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(len(repo.issues), 1)

        issue = pagure.lib.query.search_issues(self.session, repo, issueid=1)
        self.assertEqual(
            str(issue.tags),
            "[TagColored(id: 1, tag:red, tag_description:red tag, color:#ff0000)]",
        )
        issue = pagure.lib.query.search_issues(self.session, repo, issueid=2)
        self.assertIsNone(issue)


if __name__ == "__main__":
    unittest.main(verbosity=2)
