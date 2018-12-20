# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Clement Verna <cverna@tutanota.com>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import sys
import os
import time

import mock
import pygit2

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib.git
import pagure.lib.query
import tests
from tests.test_pagure_lib_git_get_tags_objects import add_repo_tag


class PagureFlaskUiArchivesTest(tests.Modeltests):
    """ Tests checking the archiving mechanism. """


    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskUiArchivesTest, self).setUp()
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        project = pagure.lib.query._get_project(self.session, 'test')

        # test has both commits and tags
        repopath = os.path.join(self.path, 'repos', 'test.git')
        tests.add_readme_git_repo(repopath)
        repo = pygit2.Repository(repopath)
        add_repo_tag(self.path, repo, ['v1.0', 'v1.1'], 'test.git')

        # test2 has only commits
        tests.add_readme_git_repo(os.path.join(
            self.path, 'repos', 'test2.git'))

        # somenamespace/test3 has neither commits nor tags

        # Create the archive folder:
        self.archive_path = os.path.join(self.path, 'archives')
        os.mkdir(self.archive_path)

    def test_project_no_conf(self):
        """ Test getting the archive when pagure isn't configured. """
        output = self.app.get(
            '/somenamespace/test3/archive/tag1/test3-tag1.zip',
            follow_redirects=True)

        self.assertEqual(output.status_code, 404)
        self.assertIn(
            "This pagure instance isn&#39;t configured to support "
            "this feature", output.get_data(as_text=True))

        self.assertEqual(os.listdir(self.archive_path), [])

    def test_project_invalid_conf(self):
        """ Test getting the archive when pagure is wrongly configured. """
        with mock.patch.dict(
                'pagure.config.config',
                {'ARCHIVE_FOLDER': os.path.join(self.path, 'invalid')}):
            output = self.app.get(
                '/somenamespace/test3/archive/tag1/test3-tag1.zip',
                follow_redirects=True)

            self.assertEqual(output.status_code, 500)
            self.assertIn(
                "Incorrect configuration, please contact your admin",
                output.get_data(as_text=True))

        self.assertEqual(os.listdir(self.archive_path), [])

    def test_project_invalid_format(self):
        """ Test getting the archive when the format provided is invalid. """
        with mock.patch.dict(
                'pagure.config.config',
                {'ARCHIVE_FOLDER': os.path.join(self.path, 'archives')}):
            output = self.app.get(
                '/somenamespace/test3/archive/tag1/test3-tag1.unzip',
                follow_redirects=True)

            self.assertEqual(output.status_code, 404)

        self.assertEqual(os.listdir(self.archive_path), [])

    def test_project_no_commit(self):
        """ Test getting the archive of an empty project. """
        with mock.patch.dict(
                'pagure.config.config',
                {'ARCHIVE_FOLDER': os.path.join(self.path, 'archives')}):
            output = self.app.get(
                '/somenamespace/test3/archive/tag1/test3-tag1.zip',
                follow_redirects=True)

            self.assertEqual(output.status_code, 404)
            self.assertIn(
                "<p>Invalid commit provided</p>",
                output.get_data(as_text=True))

        self.assertEqual(os.listdir(self.archive_path), [])

    def test_project_no_tag(self):
        """ Test getting the archive of a non-empty project but without
        tags. """
        with mock.patch.dict(
                'pagure.config.config',
                {'ARCHIVE_FOLDER': os.path.join(self.path, 'archives')}):
            output = self.app.get(
                '/test2/archive/tag1/test2-tag1.zip',
                follow_redirects=True)

            self.assertEqual(output.status_code, 404)
            self.assertIn(
                "<p>Invalid commit provided</p>",
                output.get_data(as_text=True))

        self.assertEqual(os.listdir(self.archive_path), [])

    def test_project_no_tag(self):
        """ Test getting the archive of an empty project. """
        with mock.patch.dict(
                'pagure.config.config',
                {'ARCHIVE_FOLDER': os.path.join(self.path, 'archives')}):
            output = self.app.get(
                '/test2/archive/tag1/test2-tag1.zip',
                follow_redirects=True)

            self.assertEqual(output.status_code, 404)
            self.assertIn(
                "<p>Invalid commit provided</p>",
                output.get_data(as_text=True))

        self.assertEqual(os.listdir(self.archive_path), [])

    def test_project_w_tag_zip(self):
        """ Test getting the archive from a tag. """
        with mock.patch.dict(
                'pagure.config.config',
                {'ARCHIVE_FOLDER': os.path.join(self.path, 'archives')}):
            output = self.app.get(
                '/test/archive/v1.0/test-v1.0.zip',
                follow_redirects=True)

            self.assertEqual(output.status_code, 200)

        self.assertEqual(
            os.listdir(self.archive_path), ['test'])
        self.assertEqual(
            os.listdir(os.path.join(self.archive_path, 'test')),
            ['tags'])
        self.assertEqual(
            os.listdir(os.path.join(self.archive_path, 'test', 'tags')),
            ['v1.0'])

        self.assertEqual(
            len(os.listdir(os.path.join(
                self.archive_path, 'test', 'tags', 'v1.0'))),
            1)

        files = os.listdir(os.path.join(
                self.archive_path, 'test', 'tags', 'v1.0'))
        self.assertEqual(
            os.listdir(os.path.join(
                self.archive_path, 'test', 'tags', 'v1.0', files[0])),
            ['test-v1.0.zip'])

    def test_project_w_tag_tar(self):
        """ Test getting the archive from a tag. """
        with mock.patch.dict(
                'pagure.config.config',
                {'ARCHIVE_FOLDER': os.path.join(self.path, 'archives')}):
            output = self.app.get(
                '/test/archive/v1.0/test-v1.0.tar',
                follow_redirects=True)

            self.assertEqual(output.status_code, 200)

        self.assertEqual(
            os.listdir(self.archive_path), ['test'])
        self.assertEqual(
            os.listdir(os.path.join(self.archive_path, 'test')),
            ['tags'])
        self.assertEqual(
            os.listdir(os.path.join(self.archive_path, 'test', 'tags')),
            ['v1.0'])

        self.assertEqual(
            len(os.listdir(os.path.join(
                self.archive_path, 'test', 'tags', 'v1.0'))),
            1)

        files = os.listdir(os.path.join(
                self.archive_path, 'test', 'tags', 'v1.0'))
        self.assertEqual(
            os.listdir(os.path.join(
                self.archive_path, 'test', 'tags', 'v1.0', files[0])),
            ['test-v1.0.tar'])

    def test_project_w_tag_tar_gz(self):
        """ Test getting the archive from a tag. """
        with mock.patch.dict(
                'pagure.config.config',
                {'ARCHIVE_FOLDER': os.path.join(self.path, 'archives')}):
            output = self.app.get(
                '/test/archive/v1.0/test-v1.0.tar.gz',
                follow_redirects=True)

            self.assertEqual(output.status_code, 200)

        self.assertEqual(
            os.listdir(self.archive_path), ['test'])
        self.assertEqual(
            os.listdir(os.path.join(self.archive_path, 'test')),
            ['tags'])
        self.assertEqual(
            os.listdir(os.path.join(self.archive_path, 'test', 'tags')),
            ['v1.0'])

        self.assertEqual(
            len(os.listdir(os.path.join(
                self.archive_path, 'test', 'tags', 'v1.0'))),
            1)

        files = os.listdir(os.path.join(
                self.archive_path, 'test', 'tags', 'v1.0'))
        self.assertEqual(
            os.listdir(os.path.join(
                self.archive_path, 'test', 'tags', 'v1.0', files[0])),
            ['test-v1.0.tar.gz'])

    def test_project_w_commit_tar_gz(self):
        """ Test getting the archive from a commit. """
        repopath = os.path.join(self.path, 'repos', 'test.git')
        repo = pygit2.Repository(repopath)
        commit = repo.head.target.hex
        with mock.patch.dict(
                'pagure.config.config',
                {'ARCHIVE_FOLDER': os.path.join(self.path, 'archives')}):
            output = self.app.get(
                '/test/archive/%s/test-v1.0.tar.gz' % commit,
                follow_redirects=True)

            self.assertEqual(output.status_code, 200)

        self.assertEqual(
            os.listdir(self.archive_path), ['test'])
        self.assertEqual(
            os.listdir(os.path.join(self.archive_path, 'test')),
            [commit])
        self.assertEqual(
            os.listdir(os.path.join(self.archive_path, 'test', commit)),
            ['test-v1.0.tar.gz'])

    def test_project_w_commit_tar_gz_twice(self):
        """ Test getting the archive from a commit twice, so we hit the
        disk cache. """
        repopath = os.path.join(self.path, 'repos', 'test.git')
        repo = pygit2.Repository(repopath)
        commit = repo.head.target.hex
        with mock.patch.dict(
                'pagure.config.config',
                {'ARCHIVE_FOLDER': os.path.join(self.path, 'archives')}):
            output = self.app.get(
                '/test/archive/%s/test-v1.0.tar.gz' % commit,
                follow_redirects=True)

            self.assertEqual(output.status_code, 200)

            output = self.app.get(
                '/test/archive/%s/test-v1.0.tar.gz' % commit,
                follow_redirects=True)

            self.assertEqual(output.status_code, 200)

        self.assertEqual(
            os.listdir(self.archive_path), ['test'])
        self.assertEqual(
            os.listdir(os.path.join(self.archive_path, 'test')),
            [commit])
        self.assertEqual(
            os.listdir(os.path.join(self.archive_path, 'test', commit)),
            ['test-v1.0.tar.gz'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
