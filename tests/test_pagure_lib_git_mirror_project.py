# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

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
from mock import patch, MagicMock, ANY, call

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib.git
import tests

from pagure.lib.repo import PagureRepo


class PagureLibGitMirrorProjecttests(tests.Modeltests):
    """ Tests for pagure.lib.git.mirror_pull_project """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureLibGitMirrorProjecttests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, "repos"),
            bare=True
        )

        # Make the test project mirrored from elsewhere
        self.project = pagure.lib.query.get_authorized_project(
            self.session, 'test')
        self.project.mirrored_from = "https://example.com/foo/bar.git"
        self.session.add(self.project)
        self.session.commit()

    @patch('subprocess.Popen')
    @patch('subprocess.check_output')
    def test_mirror_pull_project(self, ck_out_mock, popen_mock):
        """ Test the mirror_pull_project method of pagure.lib.git. """

        tmp = MagicMock()
        tmp.communicate.return_value = ('', '')
        popen_mock.return_value = tmp
        ck_out_mock.return_value = "all good"

        output = pagure.lib.git.mirror_pull_project(
            self.session,
            self.project
        )

        self.assertEqual(
            popen_mock.call_count,
            2
        )

        calls = [
            call(
                [
                    u'git', u'clone', u'--mirror',
                    u'https://example.com/foo/bar.git', u'.'
                ],
                cwd=ANY,
                stderr=-1,
                stdin=None,
                stdout=-1
            ),
            ANY,
            ANY,
            ANY,
            ANY,
            call(
                [u'git', u'remote', u'add', u'local', ANY],
                cwd=ANY,
                stderr=-1,
                stdin=None,
                stdout=-1
            ),
            ANY,
            ANY,
            ANY,
            ANY,
        ]
        self.assertEqual(
            popen_mock.mock_calls,
            calls
        )

        ck_out_mock.assert_called_once_with(
            [u'git', u'push', u'local', u'--mirror'],
            cwd=ANY,
            env=ANY,
            stderr=-2
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
