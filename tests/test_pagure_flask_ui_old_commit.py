# -*- coding: utf-8 -*-

"""
 (c) 2016-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']
import unittest
import sys
import os

import pygit2
from mock import patch
import pagure.lib
import tests

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))


class PagureFlaskRepoOldUrltests(tests.SimplePagureTest):
    """ Tests for flask app controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskRepoOldUrltests, self).setUp()

        pagure.config.config['EMAIL_SEND'] = False
        pagure.config.config['UPLOAD_FOLDER_PATH'] = os.path.join(
            self.path, 'releases')

    @patch.dict('pagure.config.config', {'OLD_VIEW_COMMIT_ENABLED': True})
    def test_view_commit_old_with_bogus_url(self):
        """ Test the view_commit_old endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))

        # View first commit
        output = self.app.get('/apple-touch-icon-152x152-precomposed.png')
        self.assertEqual(output.status_code, 404)

    @patch.dict('pagure.config.config', {'OLD_VIEW_COMMIT_ENABLED': True})
    def test_view_commit_old(self):
        """ Test the view_commit_old endpoint. """

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(os.path.join(self.path, 'repos', 'test.git'))
        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View first commit
        output = self.app.get('/test/%s' % commit.oid.hex)
        self.assertEqual(output.status_code, 302)

        output = self.app.get(
            '/test/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.get_data(as_text=True))
        self.assertTrue('  Merged by Alice Author\n' in output.get_data(as_text=True))
        self.assertTrue('  Committed by Cecil Committer\n' in output.get_data(as_text=True))

        self.assertTrue(
            '<span style="background-color: #f0f0f0; padding: 0 5px 0 5px">' +
            ' 2 </span><span style="color: #00A000; background-color: ' +
            '#ddffdd">+ Pagure</span>' in output.get_data(as_text=True))
        self.assertTrue(
            '<span style="background-color: #f0f0f0; padding: 0 5px 0 5px">' +
            ' 3 </span><span style="color: #00A000; background-color: ' +
            '#ddffdd">+ ======</span>' in output.get_data(as_text=True))
        self.assertTrue(
            '<span class="label label-success">+16</span>' in output.get_data(as_text=True))
        self.assertTrue('title="View file as of %s"' % commit.oid.hex[0:6]
                        in output.get_data(as_text=True))

        # View first commit - with the old URL scheme
        output = self.app.get(
            '/test/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.get_data(as_text=True))
        self.assertTrue('  Merged by Alice Author\n' in output.get_data(as_text=True))
        self.assertTrue('  Committed by Cecil Committer\n' in output.get_data(as_text=True))

        self.assertTrue(
            '<span style="background-color: #f0f0f0; padding: 0 5px 0 5px"> 2' +
            ' </span><span style="color: #00A000; background-color: #ddffdd">' +
            '+ Pagure</span>' in output.get_data(as_text=True))
        self.assertTrue(
            '<span style="background-color: #f0f0f0; padding: 0 5px 0 5px">' +
            ' 3 </span><span style="color: #00A000; background-color: ' +
            '#ddffdd">+ ======</span>' in output.get_data(as_text=True))

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(self.path, 'repos',
                                   'test.git'))

        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
        commit = repo.revparse_single('HEAD')

        # View another commit
        output = self.app.get(
            '/test/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.get_data(as_text=True))
        self.assertTrue('  Authored by Alice Author\n' in output.get_data(as_text=True))
        self.assertTrue('  Committed by Cecil Committer\n' in output.get_data(as_text=True))
        self.assertTrue(
            # new version of pygments
            '<div class="highlight" style="background: #f8f8f8"><pre style' +
            '="line-height: 125%"><span></span><span style="background-color' +
            ': #f0f0f0; padding: 0 5px 0 5px">1 </span><span style="color: ' +
            '#800080; font-weight: bold">@@ -0,0 +1,3 @@</span>' in
            output.get_data(as_text=True)
            or
            # old version of pygments
            '<div class="highlight" style="background: #f8f8f8">' +
            '<pre style="line-height: 125%">' +
            '<span style="color: #800080; font-weight: bold">' +
            '@@ -0,0 +1,3 @@</span>' in output.get_data(as_text=True))

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbkkk',
        )
        self.session.add(item)
        self.session.commit()
        forkedgit = os.path.join(
            self.path, 'repos', 'forks', 'pingou', 'test3.git')

        tests.add_content_git_repo(forkedgit)
        tests.add_readme_git_repo(forkedgit)

        repo = pygit2.Repository(forkedgit)
        commit = repo.revparse_single('HEAD')

        # Commit does not exist in anothe repo :)
        output = self.app.get(
            '/test/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 404)

        # View commit of fork
        output = self.app.get(
            '/fork/pingou/test3/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.get_data(as_text=True))
        self.assertTrue('  Authored by Alice Author\n' in output.get_data(as_text=True))
        self.assertTrue('  Committed by Cecil Committer\n' in output.get_data(as_text=True))
        self.assertTrue(
            '<span style="background-color: #f0f0f0; padding: 0 5px 0 5px"> 2' +
            ' </span><span style="color: #00A000; background-color: #ddffdd">' +
            '+ Pagure</span>' in output.get_data(as_text=True))
        self.assertTrue(
            '<span style="background-color: #f0f0f0; padding: 0 5px 0 5px"> 3' +
            ' </span><span style="color: #00A000; background-color: #ddffdd">' +
            '+ ======</span>' in output.get_data(as_text=True))
        self.assertTrue(
            '<span class="label label-success">+16</span>' in output.get_data(as_text=True))
        self.assertTrue('title="View file as of %s"' % commit.oid.hex[0:6]
                        in output.get_data(as_text=True))

        # View commit of fork - With the old URL scheme
        output = self.app.get(
            '/fork/pingou/test3/%s' % commit.oid.hex, follow_redirects=True)
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<div class="list-group" id="diff_list" style="display:none;">'
            in output.get_data(as_text=True))
        self.assertTrue('  Authored by Alice Author\n' in output.get_data(as_text=True))
        self.assertTrue('  Committed by Cecil Committer\n' in output.get_data(as_text=True))
        self.assertTrue(
            '<span style="background-color: #f0f0f0; padding: 0 5px 0 5px"> 2' +
            ' </span><span style="color: #00A000; background-color: #ddffdd">' +
            '+ Pagure</span>' in output.get_data(as_text=True))
        self.assertTrue(
            '<span style="background-color: #f0f0f0; padding: 0 5px 0 5px"> 3' +
            ' </span><span style="color: #00A000; background-color: #ddffdd">' +
            '+ ======</span>' in output.get_data(as_text=True))

        # Try the old URL scheme with a short hash
        output = self.app.get(
            '/fork/pingou/test3/%s' % commit.oid.hex[:10],
            follow_redirects=True)
        self.assertEqual(output.status_code, 404)
        self.assertIn('<p>Project not found</p>', output.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main(verbosity=2)
