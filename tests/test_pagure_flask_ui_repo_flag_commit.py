# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

import unittest
import sys
import os

from mock import patch
import pygit2

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests


class ViewCommitFlagtests(tests.SimplePagureTest):
    """ Tests for the UI related to commit flags """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(ViewCommitFlagtests, self).setUp()

        tests.create_projects(self.session)
        tests.create_tokens(self.session)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
        self.commit = repo.revparse_single('HEAD')

    def test_view_commit_no_flag(self):
        """ Test the view_commit endpoint. """

        # View first commit
        output = self.app.get('/test/c/%s' % self.commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<title>Commit - test - %s - Pagure</title>' % self.commit.oid.hex,
            output.get_data(as_text=True))
        self.assertIn(
            '#commit-overview-collapse',
            output.get_data(as_text=True))
        self.assertIn('Merged by Alice Author', output.get_data(as_text=True))
        self.assertIn('Committed by Cecil Committer', output.get_data(as_text=True))

    def test_view_commit_pending_flag(self):
        """ Test the view_commit endpoint with a pending flag. """
        repo = pagure.lib.get_authorized_project(self.session, 'test')

        msg = pagure.lib.add_commit_flag(
            session=self.session,
            repo=repo,
            commit_hash=self.commit.oid.hex,
            username='simple-koji-ci',
            status='pending',
            percent=None,
            comment='Build is running',
            url='https://koji.fp.o/koji...',
            uid='uid',
            user='foo',
            token='aaabbbcccddd'
        )
        self.session.commit()
        self.assertEqual(msg, ('Flag added', 'uid'))

        # View first commit
        output = self.app.get('/test/c/%s' % self.commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>Commit - test - %s - Pagure</title>' % self.commit.oid.hex,
            output_text)
        self.assertIn(
            '#commit-overview-collapse',
            output_text)
        self.assertIn('Merged by Alice Author', output_text)
        self.assertIn('Committed by Cecil Committer', output_text)
        self.assertIn(
            '<span>\n                    <a '
            'href="https://koji.fp.o/koji...">simple-koji-ci</a>'
            '\n                  </span>', output_text)
        self.assertIn(
            '<div class="pull-xs-right">\n                    '
            '<span class="badge badge-info">pending</span>'
            '\n                  </div>', output_text)
        self.assertIn(
            '<span>Build is running</span>', output_text)

    def test_view_commit_success_flag(self):
        """ Test the view_commit endpoint with a successful flag. """
        repo = pagure.lib.get_authorized_project(self.session, 'test')

        msg = pagure.lib.add_commit_flag(
            session=self.session,
            repo=repo,
            commit_hash=self.commit.oid.hex,
            username='simple-koji-ci',
            status='success',
            percent=100,
            comment='Build passed',
            url='https://koji.fp.o/koji...',
            uid='uid',
            user='foo',
            token='aaabbbcccddd'
        )
        self.session.commit()
        self.assertEqual(msg, ('Flag added', 'uid'))

        # View first commit
        output = self.app.get('/test/c/%s' % self.commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>Commit - test - %s - Pagure</title>' % self.commit.oid.hex,
            output_text)
        self.assertIn(
            '#commit-overview-collapse',
            output_text)
        self.assertIn('Merged by Alice Author', output_text)
        self.assertIn('Committed by Cecil Committer', output_text)
        self.assertIn(
            '<span>\n                    <a '
            'href="https://koji.fp.o/koji...">simple-koji-ci</a>'
            '\n                  </span>', output_text)
        self.assertIn(
            '<div class="pull-xs-right">\n                    '
            '<span class="badge badge-success">success (100%)</span>'
            '\n                  </div>', output_text)
        self.assertIn(
            '<span>Build passed</span>', output_text)

    def test_view_commit_error_flag(self):
        """ Test the view_commit endpoint with a error flag. """
        repo = pagure.lib.get_authorized_project(self.session, 'test')

        msg = pagure.lib.add_commit_flag(
            session=self.session,
            repo=repo,
            commit_hash=self.commit.oid.hex,
            username='simple-koji-ci',
            status='error',
            percent=None,
            comment='Build errored',
            url='https://koji.fp.o/koji...',
            uid='uid',
            user='foo',
            token='aaabbbcccddd'
        )
        self.session.commit()
        self.assertEqual(msg, ('Flag added', 'uid'))

        # View first commit
        output = self.app.get('/test/c/%s' % self.commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>Commit - test - %s - Pagure</title>' % self.commit.oid.hex,
            output_text)
        self.assertIn(
            '#commit-overview-collapse',
            output_text)
        self.assertIn('Merged by Alice Author', output_text)
        self.assertIn('Committed by Cecil Committer', output_text)
        self.assertIn(
            '<span>\n                    <a '
            'href="https://koji.fp.o/koji...">simple-koji-ci</a>'
            '\n                  </span>', output_text)
        self.assertIn(
            '<div class="pull-xs-right">\n                    '
            '<span class="badge badge-danger">error</span>'
            '\n                  </div>', output_text)
        self.assertIn(
            '<span>Build errored</span>', output_text)

    def test_view_commit_failure_flag(self):
        """ Test the view_commit endpoint with a failure flag. """
        repo = pagure.lib.get_authorized_project(self.session, 'test')

        msg = pagure.lib.add_commit_flag(
            session=self.session,
            repo=repo,
            commit_hash=self.commit.oid.hex,
            username='simple-koji-ci',
            status='failure',
            percent=None,
            comment='Build failed',
            url='https://koji.fp.o/koji...',
            uid='uid',
            user='foo',
            token='aaabbbcccddd'
        )
        self.session.commit()
        self.assertEqual(msg, ('Flag added', 'uid'))

        # View first commit
        output = self.app.get('/test/c/%s' % self.commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>Commit - test - %s - Pagure</title>' % self.commit.oid.hex,
            output_text)
        self.assertIn(
            '#commit-overview-collapse',
            output_text)
        self.assertIn('Merged by Alice Author', output_text)
        self.assertIn('Committed by Cecil Committer', output_text)
        self.assertIn(
            '<span>\n                    <a href="https://koji.fp.o/koji...">'
            'simple-koji-ci</a>\n                  </span>', output_text)
        self.assertIn(
            '<div class="pull-xs-right">\n                    '
            '<span class="badge badge-danger">failure</span>'
            '\n                  </div>', output_text)
        self.assertIn(
            '<span>Build failed</span>', output_text)

    def test_view_commit_canceled_flag(self):
        """ Test the view_commit endpoint with a canceled flag. """
        repo = pagure.lib.get_authorized_project(self.session, 'test')

        msg = pagure.lib.add_commit_flag(
            session=self.session,
            repo=repo,
            commit_hash=self.commit.oid.hex,
            username='simple-koji-ci',
            status='canceled',
            percent=None,
            comment='Build canceled',
            url='https://koji.fp.o/koji...',
            uid='uid',
            user='foo',
            token='aaabbbcccddd'
        )
        self.session.commit()
        self.assertEqual(msg, ('Flag added', 'uid'))

        # View first commit
        output = self.app.get('/test/c/%s' % self.commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>Commit - test - %s - Pagure</title>' % self.commit.oid.hex,
            output_text)
        self.assertIn(
            '#commit-overview-collapse',
            output_text)
        self.assertIn('Merged by Alice Author', output_text)
        self.assertIn('Committed by Cecil Committer', output_text)
        self.assertIn(
            '<span>\n                    <a href="https://koji.fp.o/koji...">'
            'simple-koji-ci</a>\n                  </span>', output_text)
        self.assertIn(
            '<div class="pull-xs-right">\n                    '
            '<span class="badge badge-warning">canceled</span>'
            '\n                  </div>', output_text)
        self.assertIn(
            '<span>Build canceled</span>', output_text)

    @patch.dict('pagure.config.config',
                {
                    'FLAG_STATUSES_LABELS':
                        {
                            'status1': 'badge-warning',
                            'otherstatus': 'badge-success',
                        },
                })
    def test_view_commit_with_custom_flags(self):
        """ Test the view_commit endpoint while having custom flags. """
        repo = pagure.lib.get_authorized_project(self.session, 'test')

        msg = pagure.lib.add_commit_flag(
            session=self.session,
            repo=repo,
            commit_hash=self.commit.oid.hex,
            username='simple-koji-ci',
            status='status1',
            percent=None,
            comment='Build canceled',
            url='https://koji.fp.o/koji...',
            uid='uid',
            user='foo',
            token='aaabbbcccddd'
        )
        self.session.commit()
        self.assertEqual(msg, ('Flag added', 'uid'))

        # View first commit
        output = self.app.get('/test/c/%s' % self.commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<title>Commit - test - %s - Pagure</title>' % self.commit.oid.hex,
            output_text)
        self.assertIn(
            '#commit-overview-collapse',
            output_text)
        self.assertIn('Merged by Alice Author', output_text)
        self.assertIn('Committed by Cecil Committer', output_text)
        self.assertIn(
            '<span>\n                    <a href="https://koji.fp.o/koji...">'
            'simple-koji-ci</a>\n                  </span>', output_text)
        self.assertIn(
            '<div class="pull-xs-right">\n                    '
            '<span class="badge badge-warning">status1</span>'
            '\n                  </div>', output_text)
        self.assertIn(
            '<span>Build canceled</span>', output_text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
