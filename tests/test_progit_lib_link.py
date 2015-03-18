# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
import unittest
import shutil
import sys
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib.link
import tests

COMMENTS = [
    'Did you see #1?',
    'This is a duplicate of #2',
    'This is a fixes #3',
    'Might be worth looking at https://fedorahosted.org/progit/tests2/issue/4',
    'This relates to #5',
    'Could this be related to https://fedorahosted.org/progit/tests2/issue/6',
]


class ProgitLibLinktests(tests.Modeltests):
    """ Tests for progit.lib.link """

    def test_get_relation_relates(self):
        """ Test the get_relation function of progit.lib.link with relates.
        """

        self.assertEqual(
            progit.lib.link.get_relation(
                self.session,
                'test',
                None,
                COMMENTS[0],
                'relates',
            ),
            []
        )

        tests.create_projects(self.session)

        link = progit.lib.link.get_relation(
            self.session, 'test', None, COMMENTS[4], 'relates')
        self.assertEqual(link, [])

        # Create the issue
        repo = progit.lib.get_project(self.session, 'test')
        progit.lib.new_issue(
            self.session,
            repo,
            title='foo',
            content='bar',
            user='pingou',
            ticketfolder=None,
            issue_id=5,
            notify=False)
        self.session.commit()

        for idx, comment in enumerate(COMMENTS):
            link = progit.lib.link.get_relation(
                self.session, 'test', None, comment, 'relates')
            if idx == 4:
                self.assertEqual(
                    str(link),
                    '[Issue(5, project:test, user:pingou, title:foo)]')
            else:
                self.assertEqual(link, [])

        link = progit.lib.link.get_relation(
            self.session, 'test', None, COMMENTS[5], 'relates')
        self.assertEqual(link, [])

        # Create the issue
        repo = progit.lib.get_project(self.session, 'test')
        progit.lib.new_issue(
            self.session,
            repo,
            title='another foo',
            content='another bar',
            user='pingou',
            ticketfolder=None,
            issue_id=6,
            notify=False)
        self.session.commit()

        for idx, comment in enumerate(COMMENTS):
            link = progit.lib.link.get_relation(
                self.session, 'test', None, comment, 'relates')
            if idx == 4:
                self.assertEqual(
                    str(link),
                    '[Issue(5, project:test, user:pingou, title:foo)]')
            elif idx == 5:
                self.assertEqual(
                    str(link),
                    '[Issue(6, project:test, user:pingou, title:another foo)]')
            else:
                self.assertEqual(link, [])

    def test_get_relation_fixes(self):
        """ Test the get_relation function of progit.lib.link with fixes.
        """

        self.assertEqual(
            progit.lib.link.get_relation(
                self.session,
                'test',
                None,
                COMMENTS[0],
                'fixes',
            ),
            []
        )

        tests.create_projects(self.session)

        link = progit.lib.link.get_relation(
            self.session, 'test', None, COMMENTS[2], 'fixes')
        self.assertEqual(link, [])

        # Create the issue
        repo = progit.lib.get_project(self.session, 'test')
        progit.lib.new_issue(
            self.session,
            repo,
            title='issue 3',
            content='content issue 3',
            user='pingou',
            ticketfolder=None,
            issue_id=3,
            notify=False)
        self.session.commit()

        for idx, comment in enumerate(COMMENTS):
            link = progit.lib.link.get_relation(
                self.session, 'test', None, comment, 'fixes')
            if idx == 2:
                self.assertEqual(
                    str(link),
                    '[Issue(3, project:test, user:pingou, title:issue 3)]')
            else:
                self.assertEqual(link, [])



if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitLibLinktests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
