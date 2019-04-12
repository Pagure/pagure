# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import json
import unittest
import shutil
import sys
import os

import pygit2
from mock import patch

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.link
import pagure.lib.query
import tests

COMMENTS = [
    "Did you see #1?",
    "This is a duplicate of #2",
    "This is a fixes #3",
    "Might be worth looking at http://localhost.localdomain/pagure/tests2/issue/4",
    "This relates to #5",
    "Could this be related to http://localhost.localdomain/test/issue/6",
]


class PagureLibLinktests(tests.Modeltests):
    """ Tests for pagure.lib.link """

    def test_get_relation_relates(self):
        """ Test the get_relation function of pagure.lib.link with relates.
        """

        link = pagure.lib.link.get_relation(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            text=COMMENTS[0],
            reftype="relates",
        )
        self.assertEqual(link, [])

        tests.create_projects(self.session)

        link = pagure.lib.link.get_relation(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            text=COMMENTS[4],
            reftype="relates",
        )
        self.assertEqual(link, [])

        # Create the issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        pagure.lib.query.new_issue(
            self.session,
            repo,
            title="foo",
            content="bar",
            user="pingou",
            issue_id=5,
            notify=False,
        )
        self.session.commit()

        for idx, comment in enumerate(COMMENTS):
            link = pagure.lib.link.get_relation(
                self.session,
                reponame="test",
                namespace=None,
                username=None,
                text=comment,
                reftype="relates",
            )
            if idx == 4:
                self.assertEqual(
                    str(link),
                    "[Issue(5, project:test, user:pingou, title:foo)]",
                )
            else:
                self.assertEqual(link, [])

        link = pagure.lib.link.get_relation(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            text=COMMENTS[5],
            reftype="relates",
        )
        self.assertEqual(link, [])

        # Create the issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        pagure.lib.query.new_issue(
            self.session,
            repo,
            title="another foo",
            content="another bar",
            user="pingou",
            issue_id=6,
            notify=False,
        )
        self.session.commit()

        for idx, comment in enumerate(COMMENTS):
            link = pagure.lib.link.get_relation(
                self.session,
                reponame="test",
                namespace=None,
                username=None,
                text=comment,
                reftype="relates",
            )
            if idx == 4:
                self.assertEqual(
                    str(link),
                    "[Issue(5, project:test, user:pingou, title:foo)]",
                )
            elif idx == 5:
                self.assertEqual(
                    str(link),
                    "[Issue(6, project:test, user:pingou, title:another foo)]",
                )
            else:
                self.assertEqual(link, [])

    def test_get_relation_fixes(self):
        """ Test the get_relation function of pagure.lib.link with fixes.
        """

        link = pagure.lib.link.get_relation(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            text=COMMENTS[0],
            reftype="fixes",
        )
        self.assertEqual(link, [])

        tests.create_projects(self.session)

        link = pagure.lib.link.get_relation(
            self.session,
            reponame="test",
            namespace=None,
            username=None,
            text=COMMENTS[2],
            reftype="fixes",
        )
        self.assertEqual(link, [])

        # Create the issue
        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        pagure.lib.query.new_issue(
            self.session,
            repo,
            title="issue 3",
            content="content issue 3",
            user="pingou",
            issue_id=3,
            notify=False,
        )
        self.session.commit()

        for idx, comment in enumerate(COMMENTS):
            link = pagure.lib.link.get_relation(
                self.session,
                reponame="test",
                namespace=None,
                username=None,
                text=comment,
                reftype="fixes",
            )
            if idx == 2:
                self.assertEqual(
                    str(link),
                    "[Issue(3, project:test, user:pingou, title:issue 3)]",
                )
                self.assertEqual(len(link), 1)
                self.assertEqual(link[0].project.fullname, "test")
            else:
                self.assertEqual(link, [])

    def test_relates_regex(self):
        """ Test the relates regex present in pagure.lib.link. """
        text = "relates  to   http://localhost.localdomain/fork/pingou/test/issue/1"
        for index, regex in enumerate(pagure.lib.link.RELATES):
            if index == 1:
                self.assertNotEqual(regex.match(text), None)
            else:
                self.assertEqual(regex.match(text), None)

        text = "relates http://localhost.localdomain/fork/pingou/test/issue/1"
        for index, regex in enumerate(pagure.lib.link.RELATES):
            if index == 1:
                self.assertNotEqual(regex.match(text), None)
            else:
                self.assertEqual(regex.match(text), None)

        text = "This relates  to  #5"
        for index, regex in enumerate(pagure.lib.link.RELATES):
            if index == 0:
                self.assertNotEqual(regex.match(text), None)
            else:
                self.assertEqual(regex.match(text), None)

        text = (
            "Could this be related to  "
            " http://localhost.localdomain/pagure/tests2/issue/6"
        )
        for index, regex in enumerate(pagure.lib.link.RELATES):
            if index == 1:
                self.assertNotEqual(regex.match(text), None)
            else:
                self.assertEqual(regex.match(text), None)

        text = "relates http://localhost.localdomain/SSSD/ding-libs/issue/31"
        for index, regex in enumerate(pagure.lib.link.RELATES):
            if index == 1:
                self.assertNotEqual(regex.match(text), None)
            else:
                self.assertEqual(regex.match(text), None)

    def test_fixes_regex(self):
        """ Test the fixes regex present in pagure.lib.link. """

        # project/issue matches
        def project_match(text, groups):
            match = None
            for regex in pagure.lib.link.FIXES:
                match = regex.match(text)
                if match:
                    break
            self.assertNotEqual(match, None)
            self.assertEqual(len(match.groups()), 1)
            self.assertEqual(match.groups(), groups)

        data = [
            # [string, groups]
        ]

        project_match(
            "fixes     "
            "http://localhost.localdomain/fork/pingou/test/issue/1",
            ("/fork/pingou/test/issue/1",),
        )
        project_match(
            "Could this be fixes  "
            " http://localhost.localdomain/pagure/tests2/issue/6",
            ("/pagure/tests2/issue/6",),
        )
        project_match(
            "merged http://localhost.localdomain/myproject/pull-request/70",
            ("/myproject/pull-request/70",),
        )
        project_match(
            "Now we merge http://localhost.localdomain/myproject/pull-request/99",
            ("/myproject/pull-request/99",),
        )
        project_match(
            "Merges     http://localhost.localdomain/fork/pingou/test/issue/1",
            ("/fork/pingou/test/issue/1",),
        )
        project_match(
            "Merges: http://localhost.localdomain/fork/pingou/test/issue/12",
            ("/fork/pingou/test/issue/12",),
        )
        project_match(
            "Merged http://localhost.localdomain/fork/pingou/test/issue/123#",
            ("/fork/pingou/test/issue/123",),
        )
        project_match(
            "Merge: http://localhost.localdomain/fork/pingou/test/issue/1234#foo",
            ("/fork/pingou/test/issue/1234",),
        )
        project_match(
            "Merges: http://localhost.localdomain/SSSD/ding-libs/pull-request/3188",
            ("/SSSD/ding-libs/pull-request/3188",),
        )
        project_match(
            "Fixes: http://localhost.localdomain/fedpkg/issue/220",
            ("/fedpkg/issue/220",),
        )
        project_match(
            "resolved: http://localhost.localdomain/fork/pingou/test/issue/1234#foo",
            ("/fork/pingou/test/issue/1234",),
        )
        project_match(
            "resolve http://localhost.localdomain/fork/pingou/test/issue/1234#foo",
            ("/fork/pingou/test/issue/1234",),
        )

        # issue matches
        def issue_match(text, issue):
            match = None
            for regex in pagure.lib.link.FIXES:
                match = regex.match(text)
                if match:
                    break
            self.assertNotEqual(match, None)
            self.assertEqual(len(match.groups()), 1)
            self.assertEqual(match.group(1), issue)

        issue_match("This fixed  #5", "5")
        issue_match("This fix  #5", "5")
        issue_match("Merged  #17", "17")
        issue_match("Fixed:  #23", "23")
        issue_match("Fix:  #23", "23")
        issue_match("This commit fixes:  #42", "42")
        issue_match("This commit fix   #42", "42")
        issue_match("Merge #137", "137")
        issue_match("Merges #137", "137")
        issue_match("Merges: #137", "137")
        issue_match("resolve #137", "137")
        issue_match("Resolves #137", "137")
        issue_match("RESOLVED: #137", "137")
        issue_match(
            "Fixes: http://localhost.localdomain/fedpkg/issue/220",
            "/fedpkg/issue/220",
        )
        issue_match(
            "Resolved: http://localhost.localdomain/fedpkg/issue/222",
            "/fedpkg/issue/222",
        )

        # no match
        def no_match(text):
            match = None
            for regex in pagure.lib.link.FIXES:
                match = regex.match(text)
                if match:
                    break
            self.assertEqual(match, None)

        no_match("nowhitespacemerge: #47")
        no_match("This commit unmerges #45")
        no_match("Fixed 45 typos")
        no_match("Fixed 4 typos")
        no_match("Merge branch 'work'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
