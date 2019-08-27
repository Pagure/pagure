# -*- coding: utf-8 -*-

"""
Authors:
  Julen Landa Alustiza <julen@landa.eus>
  Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import re
import sys
import os
import pygit2

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import tests
import pagure.lib.model


class PagureFlaskRepoViewBlameFileSimpletests(tests.Modeltests):
    """ Tests for view_blame_file endpoint of the flask pagure app """

    def test_view_blame_file_no_project(self):
        """ Test the view_blame_file endpoint """
        output = self.app.get("/foo/blame/sources")
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            "<title>Page not found :'( - Pagure</title>", output_text
        )
        self.assertIn("<h2>Page not found (404)</h2>", output_text)
        self.assertIn("<p>Project not found</p>", output_text)

    def test_view_blame_file_no_git_repo(self):
        """ Test the view_blame_file endpoint """
        tests.create_projects(self.session)

        output = self.app.get("/test/blame/sources")
        # No git repo associated
        self.assertEqual(output.status_code, 404)

    def test_view_blame_file_no_git_content(self):
        """ Test the view_blame_file endpoint """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/blame/sources")
        # project and associated repo, but no file
        self.assertEqual(output.status_code, 404)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            "<title>Page not found :'( - Pagure</title>", output_text
        )
        self.assertIn("<h2>Page not found (404)</h2>", output_text)
        self.assertIn("<p>Empty repo cannot have a file</p>", output_text)


class PagureFlaskRepoViewBlameFiletests(tests.Modeltests):
    """ Tests for view_blame_file endpoint of the flask pagure app """

    def setUp(self):
        """ Set up the environment, ran before every tests. """
        super(PagureFlaskRepoViewBlameFiletests, self).setUp()
        self.regex = re.compile(r'>(\w+)</a></td>\n<td class="cell2">')
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        # Add some content to the git repo
        tests.add_content_to_git(
            os.path.join(self.path, "repos", "test.git"),
            message="initial commit",
        )
        tests.add_content_to_git(
            os.path.join(self.path, "repos", "test.git"), message="foo"
        )
        tests.add_content_to_git(
            os.path.join(self.path, "repos", "test.git"),
            branch="feature",
            content="bar",
            message="bar",
            author=("Aritz Author", "aritz@authors.tld"),
        )

    def test_view_blame_file_default_branch_master(self):
        """ Test the view_blame_file endpoint """
        output = self.app.get("/test/blame/sources")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<table class="code_table">', output_text)
        self.assertTrue(
            '<tr><td class="cell1"><a id="1" href="#1" '
            'data-line-number="1"></a></td>' in output_text
            or '<tr><td class="cell1"><a data-line-number="1" '
            'href="#1" id="1"></a></td>' in output_text
        )
        self.assertIn(
            '<td class="cell2"><pre><code>foo</code></pre></td>', output_text
        )
        self.assertIn('<td class="cell_user">Alice Author</td>', output_text)
        data = self.regex.findall(output_text)
        self.assertEqual(len(data), 2)

    def test_view_blame_file_default_branch_non_master(self):
        """ Test the view_blame_file endpoint """
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        reference = repo.lookup_reference("refs/heads/feature").resolve()
        repo.set_head(reference.name)
        output = self.app.get("/test/blame/sources")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<table class="code_table">', output_text)
        self.assertTrue(
            '<tr><td class="cell1"><a id="1" href="#1" '
            'data-line-number="1"></a></td>' in output_text
            or '<tr><td class="cell1"><a data-line-number="1" '
            'href="#1" id="1"></a></td>' in output_text
        )
        self.assertIn(
            '<td class="cell2"><pre><code>bar</code></pre></td>', output_text
        )
        self.assertIn('<td class="cell_user">Aritz Author</td>', output_text)
        data = self.regex.findall(output_text)
        self.assertEqual(len(data), 3)

    def test_view_blame_file_on_commit(self):
        """ Test the view_blame_file endpoint """
        repo_obj = pygit2.Repository(
            os.path.join(self.path, "repos", "test.git")
        )
        commit = repo_obj[repo_obj.head.target]
        parent = commit.parents[0].oid.hex

        output = self.app.get(
            "/test/blame/sources?identifier={}".format(parent)
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<table class="code_table">', output_text)
        self.assertTrue(
            '<tr><td class="cell1"><a id="1" href="#1" '
            'data-line-number="1"></a></td>' in output_text
            or '<tr><td class="cell1"><a data-line-number="1" '
            'href="#1" id="1"></a></td>' in output_text
        )
        self.assertIn(
            '<td class="cell2"><pre><code>foo</code></pre></td>', output_text
        )
        self.assertIn('<td class="cell_user">Alice Author</td>', output_text)
        data = self.regex.findall(output_text)
        self.assertEqual(len(data), 1)

    def test_view_blame_file_on_branch(self):
        """ Test the view_blame_file endpoint """
        output = self.app.get("/test/blame/sources?identifier=feature")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<table class="code_table">', output_text)
        self.assertTrue(
            '<tr><td class="cell1"><a id="1" href="#1" '
            'data-line-number="1"></a></td>' in output_text
            or '<tr><td class="cell1"><a data-line-number="1" '
            'href="#1" id="1"></a></td>' in output_text
        )
        self.assertIn(
            '<td class="cell2"><pre><code>bar</code></pre></td>', output_text
        )
        self.assertIn('<td class="cell_user">Aritz Author</td>', output_text)
        data = self.regex.findall(output_text)
        self.assertEqual(len(data), 3)

    def test_view_blame_file_on_tag(self):
        """ Test the view_blame_file endpoint """
        # set a tag on the head's parent commit
        repo_obj = pygit2.Repository(
            os.path.join(self.path, "repos", "test.git")
        )
        commit = repo_obj[repo_obj.head.target]
        parent = commit.parents[0].oid.hex
        tagger = pygit2.Signature("Alice Doe", "adoe@example.com", 12347, 0)
        repo_obj.create_tag(
            "v1.0", parent, pygit2.GIT_OBJ_COMMIT, tagger, "Release v1.0"
        )

        output = self.app.get("/test/blame/sources?identifier=v1.0")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<table class="code_table">', output_text)
        self.assertTrue(
            '<tr><td class="cell1"><a id="1" href="#1" '
            'data-line-number="1"></a></td>' in output_text
            or '<tr><td class="cell1"><a data-line-number="1" '
            'href="#1" id="1"></a></td>' in output_text
        )
        self.assertIn(
            '<td class="cell2"><pre><code>foo</code></pre></td>', output_text
        )
        self.assertIn('<td class="cell_user">Alice Author</td>', output_text)
        data = self.regex.findall(output_text)
        self.assertEqual(len(data), 1)

    def test_view_blame_file_binary(self):
        """ Test the view_blame_file endpoint """
        # Add binary content
        tests.add_binary_git_repo(
            os.path.join(self.path, "repos", "test.git"), "test.jpg"
        )
        output = self.app.get("/test/blame/test.jpg")
        self.assertEqual(output.status_code, 400)
        output_text = output.get_data(as_text=True)
        self.assertIn("<title>400 Bad Request</title>", output_text)
        self.assertIn("<p>Binary files cannot be blamed</p>", output_text)

    def test_view_blame_file_non_ascii_name(self):
        """ Test the view_blame_file endpoint """
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "test.git"),
            ncommits=1,
            filename="Šource",
        )
        output = self.app.get("/test/blame/Šource")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertEqual(
            output.headers["Content-Type"].lower(), "text/html; charset=utf-8"
        )
        self.assertIn("</span>&nbsp; Šource", output_text)
        self.assertIn('<table class="code_table">', output_text)
        self.assertTrue(
            '<tr><td class="cell1"><a id="1" href="#1" '
            'data-line-number="1"></a></td>' in output_text
            or '<tr><td class="cell1"><a data-line-number="1" '
            'href="#1" id="1"></a></td>' in output_text
        )
        self.assertIn(
            '<td class="cell2"><pre><code>Row 0</code></pre></td>', output_text
        )

    def test_view_blame_file_fork_of_a_fork(self):
        """ Test the view_blame_file endpoint """
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name="test3",
            description="test project #3",
            is_fork=True,
            parent_id=1,
            hook_token="aaabbbppp",
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git")
        )
        tests.add_readme_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git")
        )
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git"),
            ncommits=10,
        )
        tests.add_content_to_git(
            os.path.join(self.path, "repos", "forks", "pingou", "test3.git"),
            content="✨☃🍰☃✨",
        )

        output = self.app.get("/fork/pingou/test3/blame/sources")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn('<table class="code_table">', output_text)
        self.assertTrue(
            '<tr><td class="cell1"><a id="1" href="#1" '
            'data-line-number="1"></a></td>' in output_text
            or '<tr><td class="cell1"><a data-line-number="1" '
            'href="#1" id="1"></a></td>' in output_text
        )
        self.assertIn(
            '<td class="cell2"><pre><code> barRow 0</code></pre></td>',
            output_text,
        )

    def test_view_blame_file_no_file(self):
        """ Test the view_blame_file endpoint """
        output = self.app.get("/test/blame/foofile")
        self.assertEqual(output.status_code, 404)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            "<title>Page not found :'( - Pagure</title>", output_text
        )
        self.assertIn("<h2>Page not found (404)</h2>", output_text)
        self.assertIn("<p>File not found</p>", output_text)

    def test_view_blame_file_folder(self):
        """ Test the view_blame_file endpoint """
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "test.git/folder1"),
            ncommits=1,
            filename="sources",
        )
        output = self.app.get("/test/blame/folder1")
        self.assertEqual(output.status_code, 404)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            "<title>Page not found :'( - Pagure</title>", output_text
        )
        self.assertIn("<h2>Page not found (404)</h2>", output_text)
        self.assertIn("<p>File not found</p>", output_text)

    def test_view_blame_file_unborn_head_no_identifier(self):
        repo_obj = pygit2.Repository(
            os.path.join(self.path, "repos", "test.git")
        )
        repo_obj.set_head("refs/heads/unexistent")

        output = self.app.get("/test/blame/sources")
        self.assertEqual(output.status_code, 404)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            "<title>Page not found :'( - Pagure</title>", output_text
        )
        self.assertIn("<h2>Page not found (404)</h2>", output_text)
        self.assertIn(
            "<p>Identifier is mandatory on unborn HEAD repos</p>", output_text
        )
