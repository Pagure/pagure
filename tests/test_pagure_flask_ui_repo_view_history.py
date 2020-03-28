# -*- coding: utf-8 -*-

"""
Authors:
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


class PagureFlaskRepoViewHistoryFileSimpletests(tests.Modeltests):
    """ Tests for view_history_file endpoint of the flask pagure app """

    def test_view_history_file_no_project(self):
        """ Test the view_history_file endpoint """
        output = self.app.get("/foo/history/sources")
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            "<title>Page not found :'( - Pagure</title>", output_text
        )
        self.assertIn("<h2>Page not found (404)</h2>", output_text)
        self.assertIn("<p>Project not found</p>", output_text)

    def test_view_history_file_no_git_repo(self):
        """ Test the view_history_file endpoint """
        tests.create_projects(self.session)

        output = self.app.get("/test/history/sources")
        # No git repo associated
        self.assertEqual(output.status_code, 404)

    def test_view_history_file_no_git_content(self):
        """ Test the view_history_file endpoint """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)

        output = self.app.get("/test/history/sources")
        # project and associated repo, but no file
        self.assertEqual(output.status_code, 404)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            "<title>Page not found :'( - Pagure</title>", output_text
        )
        self.assertIn("<h2>Page not found (404)</h2>", output_text)
        self.assertIn("<p>Empty repo cannot have a file</p>", output_text)


class PagureFlaskRepoViewHistoryFiletests(tests.Modeltests):
    """ Tests for view_history_file endpoint of the flask pagure app """

    def setUp(self):
        """ Set up the environment, ran before every tests. """
        super(PagureFlaskRepoViewHistoryFiletests, self).setUp()
        self.regex = re.compile(r' <div class="list-group-item " id="c_')
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

    def test_view_history_file_default_branch_master(self):
        """ Test the view_history_file endpoint """
        output = self.app.get("/test/history/sources")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<strong>foo</strong>", output_text)
        data = self.regex.findall(output_text)
        self.assertEqual(len(data), 2)

    def test_view_history_file_default_branch_non_master(self):
        """ Test the view_history_file endpoint """
        repo = pygit2.Repository(os.path.join(self.path, "repos", "test.git"))
        reference = repo.lookup_reference("refs/heads/feature").resolve()
        repo.set_head(reference.name)
        output = self.app.get("/test/history/sources")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<strong>bar</strong>", output_text)
        data = self.regex.findall(output_text)
        self.assertEqual(len(data), 3)

    def test_view_history_file_on_commit(self):
        """ Test the view_history_file endpoint """
        repo_obj = pygit2.Repository(
            os.path.join(self.path, "repos", "test.git")
        )
        commit = repo_obj[repo_obj.head.target]
        parent = commit.parents[0].oid.hex

        output = self.app.get(
            "/test/history/sources?identifier={}".format(parent)
        )
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<strong>initial commit</strong>", output_text)
        data = self.regex.findall(output_text)
        self.assertEqual(len(data), 1)

    def test_view_history_file_on_branch(self):
        """ Test the view_history_file endpoint """
        output = self.app.get("/test/history/sources?identifier=feature")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<strong>bar</strong>", output_text)
        data = self.regex.findall(output_text)
        self.assertEqual(len(data), 3)

    def test_view_history_file_on_tag(self):
        """ Test the view_history_file endpoint """
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

        output = self.app.get("/test/history/sources?identifier=v1.0")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<strong>initial commit</strong>", output_text)
        data = self.regex.findall(output_text)
        self.assertEqual(len(data), 1)

    def test_view_history_file_binary(self):
        """ Test the view_history_file endpoint """
        # Add binary content
        tests.add_binary_git_repo(
            os.path.join(self.path, "repos", "test.git"), "test.jpg"
        )
        output = self.app.get("/test/history/test.jpg")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn("<strong>Add a fake image file</strong>", output_text)

    def test_view_history_file_non_ascii_name(self):
        """ Test the view_history_file endpoint """
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "test.git"),
            ncommits=1,
            filename="Šource",
        )
        output = self.app.get("/test/history/Šource")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertEqual(
            output.headers["Content-Type"].lower(), "text/html; charset=utf-8"
        )
        self.assertIn("</span>&nbsp; Šource", output_text)
        self.assertIn("<strong>Add row 0 to Šource file</strong>", output_text)

    def test_view_history_file_fork_of_a_fork(self):
        """ Test the view_history_file endpoint """
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

        output = self.app.get("/fork/pingou/test3/history/sources")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            "<strong>Add row 2 to sources file</strong>", output_text
        )

    def test_view_history_file_no_file(self):
        """ Test the view_history_file endpoint """
        output = self.app.get("/test/history/foofile")
        self.assertEqual(output.status_code, 400)
        output_text = output.get_data(as_text=True)
        self.assertIn("No history could be found for this file", output_text)

    def test_view_history_file_folder(self):
        """ Test the view_history_file endpoint """
        tests.add_commit_git_repo(
            os.path.join(self.path, "repos", "test.git/folder1"),
            ncommits=1,
            filename="sources",
        )
        output = self.app.get("/test/history/folder1")
        self.assertEqual(output.status_code, 400)
        output_text = output.get_data(as_text=True)
        self.assertIn("No history could be found for this file", output_text)

    def test_view_history_file_existing_folder(self):
        """ Test the view_history_file endpoint """
        tests.add_content_to_git(
            os.path.join(self.path, "repos", "test.git"), folders="foo/bar"
        )

        output = self.app.get("/test/history/foo/bar/")
        self.assertEqual(output.status_code, 200)
        output_text = output.get_data(as_text=True)
        self.assertIn(
            "<strong>Add content to file foo/bar/sources</strong>", output_text
        )
        data = self.regex.findall(output_text)
        self.assertEqual(len(data), 1)

    def test_view_history_file_unborn_head_no_identifier(self):
        repo_obj = pygit2.Repository(
            os.path.join(self.path, "repos", "test.git")
        )
        repo_obj.set_head("refs/heads/unexistent")

        output = self.app.get("/test/history/sources")
        self.assertEqual(output.status_code, 400)
        output_text = output.get_data(as_text=True)
        self.assertIn("Invalid repository", output_text)
