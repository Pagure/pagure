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

import pygit2

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure  # noqa
import pagure.lib  # noqa
import tests  # noqa
from pagure.lib.repo import PagureRepo  # noqa


class LocalBasetests(tests.Modeltests):
    """ Tests for view_file endpoint of the flask pagure app """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(LocalBasetests, self).setUp()

        pagure.config.config['VIRUS_SCAN_ATTACHMENTS'] = False
        pagure.config.config['UPLOAD_FOLDER_URL'] = '/releases/'
        pagure.config.config['UPLOAD_FOLDER_PATH'] = os.path.join(
            self.path, 'releases')


class PagureFlaskRepoViewFileSimpletests(LocalBasetests):
    """ Tests for view_file endpoint of the flask pagure app """

    def test_view_file_no_project(self):
        """ Test the view_file when the project is unknown. """
        output = self.app.get('/foo/blob/foo/f/sources')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

    def test_view_file_no_git(self):
        """ Test the view_file when the project has no git repo. """
        tests.create_projects(self.session)

        output = self.app.get('/test/blob/foo/f/sources')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

    def test_view_file_no_git_content(self):
        """ Test the view_file when the file doesn't exist. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        output = self.app.get('/test/blob/foo/f/sources')
        self.assertEqual(output.status_code, 404)


class PagureFlaskRepoViewFiletests(LocalBasetests):
    """ Tests for view_file endpoint of the flask pagure app """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskRepoViewFiletests, self).setUp()
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'test.git'))
        tests.add_binary_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), 'test.jpg')
        tests.add_binary_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), 'test_binary')

    def test_view_file_invalid_file(self):
        """ Test the view_file when the file doesn't exist. """

        output = self.app.get('/test/blob/master/foofile')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/blob/sources/f/testfoo.jpg')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/blob/master/f/folder1/testfoo.jpg')
        self.assertEqual(output.status_code, 404)

    def test_view_file_basic_text(self):
        """ Test the view_file with a basic text file. """
        output = self.app.get('/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<pre class="syntaxhighlightblock"><code>foo\n bar</code></pre>',
            output_text
        )

    def test_view_file_empty_file(self):
        """ Test the view_file with an empty file. """

        # Empty files should also be displayed
        tests.add_content_to_git(
            os.path.join(self.path, 'repos', 'test.git'),
            filename="emptyfile.md",
            content="")
        output = self.app.get('/test/blob/master/f/emptyfile.md')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<a class="btn btn-secondary btn-sm" '
            'href="/test/raw/master/f/emptyfile.md" '
            'title="View as raw">Raw</a>', output_text)
        self.assertIn(
            '<div class="m-2">\n'
            '        \n      </div>', output_text)

    def test_view_file_binary_file(self):
        """ Test the view_file with a binary file. """

        # View what's supposed to be an image
        output = self.app.get('/test/blob/master/f/test.jpg')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            'Binary files cannot be rendered.<br/>', output_text)
        self.assertIn(
            '<a href="/test/raw/master/f/test.jpg">view the raw version',
            output_text)

    def test_view_file_by_commit(self):
        """ Test the view_file in a specific commit. """

        # View by commit id
        repo = pygit2.Repository(os.path.join(self.path, 'repos', 'test.git'))
        commit = repo.revparse_single('HEAD')

        output = self.app.get('/test/blob/%s/f/test.jpg' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            'Binary files cannot be rendered.<br/>', output_text)
        self.assertIn('/f/test.jpg">view the raw version', output_text)

    def test_view_file_by_name(self):
        """ Test the view_file via a image name. """

        # View by image name -- somehow we support this
        output = self.app.get('/test/blob/sources/f/test.jpg')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            'Binary files cannot be rendered.<br/>', output_text)
        self.assertIn('/f/test.jpg">view the raw version', output_text)

    def test_view_file_binary_file2(self):
        """ Test the view_file with a binary file (2). """

        # View binary file
        output = self.app.get('/test/blob/sources/f/test_binary')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('/f/test_binary">view the raw version', output_text)
        self.assertTrue(
            'Binary files cannot be rendered.<br/>'
            in output_text)

    def test_view_file_for_folder(self):
        """ Test the view_file with a folder. """

        # View folder
        output = self.app.get('/test/blob/master/f/folder1')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<span class="fa fa-folder text-muted"></span>',
            output_text)
        self.assertIn('<title>Tree - test - Pagure</title>', output_text)
        self.assertIn(
            '<a href="/test/blob/master/f/folder1/folder2">', output_text)

    def test_view_file_nested_file(self):
        """ Test the view_file with a nested file. """

        # Verify the nav links correctly when viewing a nested folder/file.
        output = self.app.get('/test/blob/master/f/folder1/folder2/file')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<li class="breadcrumb-item"><a '
            'href="/test/blob/master/f/folder1/folder2">\n            '
            '<span class="fa fa-folder"></span>&nbsp; folder2</a>'
            '\n          </li>', output_text)

    def test_view_file_non_ascii_file(self):
        """ Test the view_file with a non-ascii file name. """

        # View file with a non-ascii name
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'test.git'),
            ncommits=1, filename='Šource')
        output = self.app.get('/test/blob/master/f/Šource')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertEqual(output.headers['Content-Type'].lower(),
                         'text/html; charset=utf-8')
        self.assertIn('</span>&nbsp; Šource', output_text)
        self.assertIn(
            '<pre class="syntaxhighlightblock"><code>Row 0\n</code></pre>',
            output_text
        )

    def test_view_file_fork_and_edit_logged_out(self):
        """ Test the view_file fork and edit button presence when logged
        out.
        """

        # not logged in, no edit button but fork & edit is there
        output = self.app.get('/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn(
            '<a class="btn btn-sm btn-secondary" '
            'href="/test/edit/master/f/sources" title="Edit file">'
            'Edit</a>', output_text)
        self.assertIn(
            'onclick="fork_project.submit();">\n                    '
            '        Fork and Edit', output_text)

    def test_view_file_fork_and_edit_logged_in(self):
        """ Test the view_file fork and edit button presence when logged
        in.
        """

        # logged in, both buttons are there
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/blob/master/f/sources')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<a class="btn btn-sm btn-secondary" '
                'href="/test/edit/master/f/sources" title="Edit file">'
                'Edit</a>', output_text)
            self.assertIn(
                'onclick="fork_project.submit();">\n                    '
                '        Fork and Edit', output_text)


class PagureFlaskRepoViewFileForktests(LocalBasetests):
    """ Tests for view_file endpoint of the flask pagure app for a fork """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskRepoViewFileForktests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'test.git'))
        tests.add_binary_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), 'test.jpg')
        tests.add_binary_git_repo(
            os.path.join(self.path, 'repos', 'test.git'), 'test_binary')

        # Add a fork of a fork
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test',
            description='test project #3',
            is_fork=True,
            parent_id=1,
            hook_token='aaabbbppp',
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test.git'))
        tests.add_commit_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'pingou', 'test.git'),
            ncommits=10)

    def test_view_file_nested_file_in_fork(self):
        """ Test the view_file with a nested file in fork. """
        # Verify the nav links correctly when viewing a file/folder in a fork.
        output = self.app.get(
            '/fork/pingou/test/blob/master/f/folder1/folder2/file')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<li class="breadcrumb-item"><a '
            'href="/fork/pingou/test/blob/master/f/folder1/folder2">'
            '\n            <span class="fa fa-folder"></span>&nbsp; folder2'
            '</a>\n          </li>', output.get_data(as_text=True))

    def test_view_file_in_branch_in_fork(self):
        """ Test the view_file in a specific branch of a fork. """
        output = self.app.get('/fork/pingou/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            '<pre class="syntaxhighlightblock"><code>foo\n barRow 0\n'
            'Row 1\nRow 2\nRow 3\nRow 4\nRow 5\nRow 6\nRow 7\nRow 8\n'
            'Row 9\n</code></pre>', output_text
        )

    def test_view_file_fork_and_edit_on_fork_logged_out(self):
        """ Test the view_file on a text file on a fork when logged out. """

        # not logged in, no edit button but fork & edit is there
        output = self.app.get('/fork/pingou/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertNotIn(
            '<a class="btn btn-sm btn-secondary" '
            'href="/test/edit/master/f/sources" title="Edit file">'
            'Edit</a>', output_text)
        self.assertIn(
            'onclick="fork_project.submit();">\n                    '
            '        Fork and Edit', output_text)

    def test_view_file_fork_and_edit_on_your_fork(self):
        """ Test the view_file on a text file on your fork when logged in.
        """

        # logged in, but it's your own fork, so just edit button is there
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/fork/pingou/test/blob/master/f/sources')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<a class="btn btn-sm btn-secondary" '
                'href="/fork/pingou/test/edit/master/f/sources" title="Edit file">'
                'Edit</a>', output_text)
            self.assertNotIn(
                'onclick="fork_project.submit();">\n                    '
                '        Fork and Edit', output_text)

    def test_view_file_fork_and_edit_on_a_fork(self):
        """ Test the view_file on a text file on somone else's fork when
        logged in.
        """

        # logged in, but it's not your fork, so only fork and edit button
        # is there
        user = tests.FakeUser(username='foo')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/fork/pingou/test/blob/master/f/sources')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertNotIn(
                '<a class="btn btn-sm btn-secondary" '
                'href="/fork/pingou/test/edit/master/f/sources" title="Edit file">'
                'Edit</a>', output_text)
            self.assertIn(
                'onclick="fork_project.submit();">\n                    '
                '        Fork and Edit', output_text)

    def test_view_file_fork_and_edit_on_project(self):
        """ Test the view_file on a text file on somone else's fork when
        logged in.
        """

        # logged in and seeing the project you forked
        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/blob/master/f/sources')
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<a class="btn btn-sm btn-secondary" '
                'href="/test/edit/master/f/sources" title="Edit file">'
                'Edit</a>', output_text)
            self.assertIn(
                'onclick="fork_project.submit();">\n                    '
                '        Edit in your fork', output_text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
