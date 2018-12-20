# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import sys
import os

import mock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.hooks.pagure_hook
import tests


class PagureHooksPagureHooktests(tests.SimplePagureTest):
    """ Tests for pagure.hooks.pagure_hook """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureHooksPagureHooktests, self).setUp()
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'), bare=True)

        # Add one issue to each projects otherwise we won't be able to find
        project = pagure.lib.query.get_authorized_project(self.session, 'test')
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=project,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        project = pagure.lib.query.get_authorized_project(
            self.session, 'test2')
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=project,
            title='Test issue on test2',
            content='We should work on this, really',
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue on test2')

        # Create a fork of test for foo with its own ticket
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            is_fork=True,
            parent_id=1,
            description='test project #1',
            hook_token='aaabbbccc_foo',
        )
        item.close_status = [
            'Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        self.session.add(item)
        self.session.commit()
        project = pagure.lib.query.get_authorized_project(
            self.session, 'test', user="foo")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=project,
            title='Test issue on fork/foo/test',
            content='We should work on this, really',
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue on fork/foo/test')

        self.folder = os.path.join(self.path, 'repos', 'test.git')

        # Add a README to the git repo - First commit
        tests.add_readme_git_repo(self.folder)

    @mock.patch("pagure.hooks.pagure_hook.fixes_relation")
    def test_generate_revision_change_log_short_url(self, fixes_relation):
        """ Test generate_revision_change_log when the comment contains
        a short link to the same project.
        """

        # Add a commit with an url in the commit message
        tests.add_content_to_git(
            self.folder, branch='master', filename='sources', content='foo',
            message='Test commit message\n\nFixes #1'
        )

        project = pagure.lib.query.get_authorized_project(self.session, 'test')

        pagure.hooks.pagure_hook.generate_revision_change_log(
            session=self.session,
            project=project,
            username=None,
            repodir=self.folder,
            new_commits_list=['HEAD']
        )
        fixes_relation.assert_called_once_with(
            mock.ANY, None, mock.ANY, project.issues[0],
            'http://localhost.localdomain/')

    @mock.patch("pagure.hooks.pagure_hook.fixes_relation")
    def test_generate_revision_change_log_full_url(self, fixes_relation):
        """ Test generate_revision_change_log when the comment contains
        a full link to another project.
        """

        # Add a commit with an url in the commit message
        tests.add_content_to_git(
            self.folder, branch='master', filename='sources', content='foo',
            message='Test commit message\n\n'
            'Fixes http://localhost.localdomain/test2/issue/1'
        )

        project = pagure.lib.query.get_authorized_project(
            self.session, 'test')
        project2 = pagure.lib.query.get_authorized_project(
            self.session, 'test2')

        pagure.hooks.pagure_hook.generate_revision_change_log(
            session=self.session,
            project=project,
            username=None,
            repodir=self.folder,
            new_commits_list=['HEAD']
        )
        fixes_relation.assert_called_once_with(
            mock.ANY, None, mock.ANY, project2.issues[0],
            'http://localhost.localdomain/')

    @mock.patch("pagure.hooks.pagure_hook.fixes_relation")
    def test_generate_revision_change_log_full_url_fork(self, fixes_relation):
        """ Test generate_revision_change_log when the comment contains
        a full link to a fork.
        """

        # Add a commit with an url in the commit message
        tests.add_content_to_git(
            self.folder, branch='master', filename='sources', content='foo',
            message='Test commit message\n\n'
            'Fixes http://localhost.localdomain/fork/foo/test/issue/1'
        )

        project = pagure.lib.query.get_authorized_project(
            self.session, 'test')
        project_fork = pagure.lib.query.get_authorized_project(
            self.session, 'test', user="foo")

        pagure.hooks.pagure_hook.generate_revision_change_log(
            session=self.session,
            project=project,
            username=None,
            repodir=self.folder,
            new_commits_list=['HEAD']
        )
        fixes_relation.assert_called_once_with(
            mock.ANY, None, mock.ANY, project_fork.issues[0],
            'http://localhost.localdomain/')


if __name__ == '__main__':
    unittest.main(verbosity=2)
