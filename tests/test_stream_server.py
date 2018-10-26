#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Adam Williamson <awilliam@redhat.com>

Tests for the Pagure streaming server.

"""

# obviously this is fine for testing.
# pylint: disable=locally-disabled, protected-access

from __future__ import unicode_literals

import logging
import os
import sys
import unittest

import mock
import six

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '../pagure-ev'))

if six.PY3:
    raise unittest.case.SkipTest('Skipping on python3')

import pagure.lib.query                             # pylint: disable=wrong-import-position
from pagure.exceptions import PagureEvException     # pylint: disable=wrong-import-position
import tests                                        # pylint: disable=wrong-import-position
# comes from ev-server/
import pagure_stream_server as pss                  # pylint: disable=wrong-import-position, import-error

logging.basicConfig(stream=sys.stderr)


class StreamingServerTests(tests.Modeltests):
    """Tests for the streaming server."""

    def setUp(self):
        """Set up the environnment, run before every test."""
        super(StreamingServerTests, self).setUp()

        # Make sure the server uses the existing session
        pss.SESSION = self.session

        # Mock send_email, we never want to send or see emails here.
        self.mailpatcher = mock.patch('pagure.lib.notify.send_email')
        self.mailpatcher.start()

        # Setup projects
        tests.create_projects(self.session)
        self.repo = pagure.lib.query._get_project(self.session, 'test')
        self.repo2 = pagure.lib.query._get_project(self.session, 'test2')

        # Disable repo 2's issue tracker and PR tracker
        pagure.lib.query.update_project_settings(
            session=self.session,
            repo=self.repo2,
            user='pingou',
            settings={
                'issue_tracker': False,
                'pull_requests': False,
            }
        )

        # Create a public issue
        pagure.lib.query.new_issue(
            session=self.session,
            repo=self.repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )

        # Create a private issue
        pagure.lib.query.new_issue(
            session=self.session,
            repo=self.repo,
            title='Private issue #2',
            content='The world can see my porn folder',
            user='pingou',
            private=True,
        )

        # Create a PR
        pagure.lib.query.new_pull_request(
            session=self.session,
            repo_from=self.repo,
            repo_to=self.repo,
            branch_from='feature',
            branch_to='master',
            title='Test PR',
            user='pingou',
        )

    def tearDown(self):
        "Stop the patchers, as well as calling super."""
        super(StreamingServerTests, self).tearDown()
        self.mailpatcher.stop()

    def test_parse_path(self):
        """Tests for _parse_path."""
        # Result format is: (username, namespace, repo, objtype, objid)
        # Simple case: issue for non-namespaced, non-forked repo.
        result = pss._parse_path('/pagure/issue/1')
        self.assertEqual(result, (None, None, 'pagure', 'issue', '1'))

        # Pull request for namespaced repo.
        result = pss._parse_path('/fedora-qa/fedfind/pull-request/2')
        self.assertEqual(result, (None, 'fedora-qa', 'fedfind', 'pull-request', '2'))

        # Issue for forked repo.
        result = pss._parse_path('/fork/adamwill/pagure/issue/3')
        self.assertEqual(result, ('adamwill', None, 'pagure', 'issue', '3'))

        # Issue for forked, namespaced repo.
        result = pss._parse_path('/fork/pingou/fedora-qa/fedfind/issue/4')
        self.assertEqual(result, ('pingou', 'fedora-qa', 'fedfind', 'issue', '4'))

        # Issue for repo named 'pull-request' (yeah, now we're getting tricksy).
        result = pss._parse_path('/pull-request/issue/5')
        self.assertEqual(result, (None, None, 'pull-request', 'issue', '5'))

        # Unknown object type.
        six.assertRaisesRegex(
            self,
            PagureEvException,
            r"No known object",
            pss._parse_path, '/pagure/unexpected/1'
        )

        # No object ID.
        six.assertRaisesRegex(
            self,
            PagureEvException,
            r"No project or object ID",
            pss._parse_path, '/pagure/issue'
        )

        # No repo name. Note: we cannot catch 'namespace but no repo name',
        # but that should fail later in pagure.lib.query.get_project
        six.assertRaisesRegex(
            self,
            PagureEvException,
            r"No project or object ID",
            pss._parse_path, '/issue/1'
        )

        # /fork but no user name.
        six.assertRaisesRegex(
            self,
            PagureEvException,
            r"no user found!",
            pss._parse_path, '/fork/pagure/issue/1'
        )

        # Too many path components before object type.
        six.assertRaisesRegex(
            self,
            PagureEvException,
            r"More path components",
            pss._parse_path, '/fork/adamwill/fedora-qa/fedfind/unexpected/issue/1'
        )
        six.assertRaisesRegex(
            self,
            PagureEvException,
            r"More path components",
            pss._parse_path, '/fedora-qa/fedfind/unexpected/issue/1'
        )

    def test_get_issue(self):
        """Tests for _get_issue."""
        # Simple case: get the existing issue from the existing repo.
        result = pss._get_issue(self.repo, '1')
        self.assertEqual(result.id, 1)

        # Issue that doesn't exist.
        six.assertRaisesRegex(
            self,
            PagureEvException,
            r"Issue '3' not found",
            pss._get_issue, self.repo, '3'
        )

        # Private issue (for now we don't handle auth).
        six.assertRaisesRegex(
            self,
            PagureEvException,
            r"issue is private",
            pss._get_issue, self.repo, '2'
        )

        # Issue from a project with no issue tracker.
        six.assertRaisesRegex(
            self,
            PagureEvException,
            r"No issue tracker found",
            pss._get_issue, self.repo2, '1'
        )

    def test_get_pull_request(self):
        """Tests for _get_pull_request."""
        # Simple case: get the existing PR from the existing repo.
        result = pss._get_pull_request(self.repo, '3')
        self.assertEqual(result.id, 3)

        # PR that doesn't exist.
        six.assertRaisesRegex(
            self,
            PagureEvException,
            r"Pull-Request '2' not found",
            pss._get_pull_request, self.repo, '2'
        )

        # PR from a project with no PR tracker.
        six.assertRaisesRegex(
            self,
            PagureEvException,
            r"No pull-request tracker found",
            pss._get_pull_request, self.repo2, '1'
        )

    def test_get_obj_from_path(self):
        """Tests for get_obj_from_path."""
        # Simple issue case.
        result = pss.get_obj_from_path('/test/issue/1')
        self.assertEqual(result.id, 1)

        # Simple PR case.
        result = pss.get_obj_from_path('/test/pull-request/3')
        self.assertEqual(result.id, 3)

        # Non-existent repo.
        six.assertRaisesRegex(
            self,
            PagureEvException,
            r"Project 'foo' not found",
            pss.get_obj_from_path, '/foo/issue/1'
        )

        # NOTE: we cannot test the 'Invalid object provided' exception
        # as it's a backup (current code will never hit it)


if __name__ == '__main__':
    unittest.main(verbosity=2)
