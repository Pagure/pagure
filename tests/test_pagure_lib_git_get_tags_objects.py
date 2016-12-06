# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Clement Verna <cverna@tutanota.com>

"""

import unittest
import sys
import os
import time

import pygit2

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib.git
import tests


def get_tag_name(tags):
    """ Return a list of the tag names """
    output = []
    for tag in tags:
        output.append(tag['tagname'])
    return output


def add_repo_tag(git_dir, repo, tags, repo_name):
    """ Use a list to create multiple tags on a git repo """
    for tag in reversed(tags):
        time.sleep(1)
        tests.add_commit_git_repo(
            os.path.join(git_dir, 'repos', repo_name),
            ncommits=1)
        first_commit = repo.revparse_single('HEAD')
        tagger = pygit2.Signature('Alice Doe', 'adoe@example.com', 12347, 0)
        repo.create_tag(
            tag, first_commit.oid.hex, pygit2.GIT_OBJ_COMMIT, tagger,
            "Release " + tag)


class PagureLibGitGetTagstests(tests.Modeltests):

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureLibGitGetTagstests, self).setUp()

        pagure.lib.git.SESSION = self.session
        pagure.APP.config['GIT_FOLDER'] = os.path.join(
            self.path, 'repos')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            self.path, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            self.path, 'docs')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            self.path, 'requests')

    def test_get_git_tags_objects(self):
        """ Test the get_git_tags_objects method of pagure.lib.git. """
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)
        project = pagure.lib.get_project(self.session, 'test')

        # Case 1 - Empty repo with no tags
        exp = []
        tags = pagure.lib.git.get_git_tags_objects(project)
        self.assertEqual(exp, get_tag_name(tags))

        tests.add_readme_git_repo(os.path.join(os.path.join(
            self.path, 'repos'), 'test.git'))
        repo = pygit2.Repository(os.path.join(os.path.join(
            self.path, 'repos'), 'test.git'))

        # Case 2 - Repo with one commit and no tags
        exp = []
        tags = pagure.lib.git.get_git_tags_objects(project)
        self.assertEqual(exp, get_tag_name(tags))

        # Case 3 - Simple sort
        exp = ['0.1.0', 'test-0.0.21', '0.0.12-beta', '0.0.12-alpha', '0.0.12',
               '0.0.11', '0.0.3', 'foo-0.0.2', '0.0.1']
        add_repo_tag(self.path, repo, exp, 'test.git')
        tags = pagure.lib.git.get_git_tags_objects(project)
        self.assertEqual(exp, get_tag_name(tags))

        # Case 4 - Sorting with different splitting characters
        project = pagure.lib.get_project(self.session, 'test2')
        tests.add_readme_git_repo(os.path.join(os.path.join(
            self.path, 'repos'), 'test2.git'))
        repo = pygit2.Repository(os.path.join(os.path.join(
            self.path, 'repos'), 'test2.git'))

        exp = ['1.0-0_2', '1.0-0_1', '0.1-1_0', '0.1-0_0', '0.0-2_0',
               '0.0-1_34', '0.0-1_11', '0.0-1_3', '0.0-1_2', '0.0-1_1']
        add_repo_tag(self.path, repo, exp, 'test2.git')
        tags = pagure.lib.git.get_git_tags_objects(project)
        self.assertEqual(exp, get_tag_name(tags))


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureLibGitGetTagstests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
