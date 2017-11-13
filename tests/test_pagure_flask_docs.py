# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

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

import mock
import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.docs_server
import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskDocstests(tests.SimplePagureTest):
    """ Tests for flask docs of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskDocstests, self).setUp()

        pagure.docs_server.APP.config['TESTING'] = True
        pagure.docs_server.SESSION = self.session

        pagure.docs_server.APP.config['GIT_FOLDER'] = os.path.join(
            self.path, 'repos')
        pagure.docs_server.APP.config['TICKETS_FOLDER'] = os.path.join(
            self.path, 'tickets')
        pagure.docs_server.APP.config['DOCS_FOLDER'] = os.path.join(
            self.path, 'docs')
        self.app = pagure.docs_server.APP.test_client()

    def _set_up_doc(self):
        # forked doc repo
        docrepo = os.path.join(self.path, 'docs', 'test', 'test.git')
        repo = pygit2.init_repository(docrepo)

        # Create files in that git repo
        with open(os.path.join(docrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
        repo.index.write()

        folderpart = os.path.join(docrepo, 'folder1', 'folder2')
        os.makedirs(folderpart)
        with open(os.path.join(folderpart, 'test_file'), 'w') as stream:
            stream.write('row1\nrow2\nrow3')
        repo.index.add(os.path.join('folder1', 'folder2', 'test_file'))
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        repo.create_commit(
            'refs/heads/master',  # the name of the reference to update
            author,
            committer,
            'Add test files and folder',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        # Push the changes to the bare repo
        remote = repo.create_remote(
            'origin', os.path.join(self.path, 'docs', 'test.git'))

        PagureRepo.push(remote, 'refs/heads/master:refs/heads/master')

        # Turn on the docs project since it's off by default
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        repo.settings = {'project_documentation': True}
        self.session.add(repo)
        self.session.commit()

    def test_view_docs_no_project(self):
        """ Test the view_docs endpoint with no project. """

        output = self.app.get('/foo/docs')
        self.assertEqual(output.status_code, 404)

    def test_view_docs_project_no_git(self):
        """ Test the view_docs endpoint with a project that has no
        corresponding git repo.
        """
        tests.create_projects(self.session)

        # Turn on the docs project since it's off by default
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        repo.settings = {'project_documentation': True}
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/docs', follow_redirects=True)
        self.assertEqual(output.status_code, 404)
        self.assertTrue(
            '<p>Documentation not found</p>' in output.data)

        output = self.app.get('/test', follow_redirects=True)
        self.assertEqual(output.status_code, 404)
        self.assertTrue(
            '<p>Documentation not found</p>' in output.data)

    def test_view_docs_project_no_docs(self):
        """ Test the view_docs endpoint with a project that disabled the
        docs.
        """
        tests.create_projects(self.session)
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        tests.create_projects_git(os.path.join(self.path, 'docs'))

        output = self.app.get('/test/docs')
        self.assertEqual(output.status_code, 404)

        repo.settings = {'project_documentation': False}
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/docs', follow_redirects=True)
        self.assertEqual(output.status_code, 404)

    def test_view_docs_empty_repo(self):
        """ Test the view_docs endpoint when the git repo is empty. """
        tests.create_projects(self.session)
        repo = pygit2.init_repository(
            os.path.join(self.path, 'docs', 'test.git'), bare=True)

        # Turn on the docs project since it's off by default
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        repo.settings = {'project_documentation': True}
        self.session.add(repo)
        self.session.commit()

        output = self.app.get('/test/docs')
        self.assertEqual(output.status_code, 404)
        self.assertIn(
            '<p>No content found in the repository, you may want to read '
            'the <a href="https://docs.pagure.org/pagure/usage/'
            'using_doc.html">Using the doc repository of your project</a> '
            'documentation.</p>', output.data)

    def test_view_docs(self):
        """ Test the view_docs endpoint. """
        tests.create_projects(self.session)
        repo = pygit2.init_repository(
            os.path.join(self.path, 'docs', 'test.git'), bare=True)

        output = self.app.get('/test/docs')
        self.assertEqual(output.status_code, 404)

        self._set_up_doc()

        # Now check the UI

        output = self.app.get('/test/docs')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/test/sources')
        self.assertEqual(output.status_code, 200)
        self.assertEqual('<pre>foo\n bar</pre>', output.data)

        output = self.app.get('/test/folder1/folder2')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<li><ul><a href="test_file">test_file</a></ul></li>'
            in output.data)

        output = self.app.get('/test/folder1/folder2/test_file')
        self.assertEqual(output.status_code, 200)
        self.assertEqual('<pre>row1\nrow2\nrow3</pre>', output.data)

        output = self.app.get('/test/folder1')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<li><ul><a href="folder2/">folder2/</a></ul></li>'
            in output.data)

        output = self.app.get('/test/folder1/foo')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/test/folder1/foo/folder2')
        self.assertEqual(output.status_code, 404)

    @mock.patch(
        'pagure.lib.encoding_utils.decode',
        mock.MagicMock(side_effect=pagure.exceptions.PagureEncodingException))
    def test_view_docs_encoding_error(self):
        """ Test viewing a file of which we cannot find the encoding. """
        tests.create_projects(self.session)
        repo = pygit2.init_repository(
            os.path.join(self.path, 'docs', 'test.git'), bare=True)

        output = self.app.get('/test/docs')
        self.assertEqual(output.status_code, 404)

        self._set_up_doc()

        output = self.app.get('/test/sources')
        self.assertEqual(output.status_code, 200)
        self.assertEqual('foo\n bar', output.data)

        output = self.app.get('/test/folder1')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<li><ul><a href="folder2/">folder2/</a></ul></li>'
            in output.data)

    @mock.patch(
        'pagure.lib.encoding_utils.decode',
        mock.MagicMock(side_effect=IOError))
    def test_view_docs_unknown_error(self):
        """ Test viewing a file of which we cannot find the encoding. """
        tests.create_projects(self.session)
        repo = pygit2.init_repository(
            os.path.join(self.path, 'docs', 'test.git'), bare=True)

        output = self.app.get('/test/docs')
        self.assertEqual(output.status_code, 404)

        self._set_up_doc()

        output = self.app.get('/test/sources')
        self.assertEqual(output.status_code, 500)

        output = self.app.get('/test/folder1')
        self.assertEqual(output.status_code, 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)
