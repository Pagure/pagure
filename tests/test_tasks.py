
from __future__ import unicode_literals, absolute_import

from mock import patch, MagicMock, Mock
from collections import namedtuple
import os
import unittest

from pagure.lib import tasks


MockUser = namedtuple('MockUser', ['fullname', 'default_email'])


class MockCommit(object):
    def __init__(self, name, email, time='1970-01-01 00:00'):
        self.author = Mock(email=email)
        self.author.name = name
        self.commit_time = time


@patch('pagure.lib.query.create_session', new=Mock())
class TestCommitsAuthorStats(unittest.TestCase):

    def setUp(self):
        self.search_user_patcher = patch('pagure.lib.query.search_user')
        mock_search_user = self.search_user_patcher.start()
        mock_search_user.side_effect = lambda _, email: self.authors.get(email)

        self.pygit_patcher = patch('pygit2.Repository')
        mock_repo = self.pygit_patcher.start().return_value

        def mock_walk_impl(*args, **kwargs):
            for commit in self.commits:
                yield commit

        mock_repo.walk.side_effect = mock_walk_impl

        self.repopath = Mock()
        exists = os.path.exists

        def mock_exists_impl(path):
            if path == self.repopath:
                return True
            return exists(path)

        self.exists_patcher = patch('os.path.exists')
        mock_exists = self.exists_patcher.start()
        mock_exists.side_effect = mock_exists_impl

    def tearDown(self):
        self.search_user_patcher.stop()
        self.pygit_patcher.stop()
        self.exists_patcher.stop()

    def test_no_change(self):
        self.commits = [
            MockCommit('Alice', 'alice@example.com', '2018-01-01 00:00'),
        ]
        self.authors = {
            'alice@example.com': MockUser('Alice', 'alice@example.com'),
        }

        num_commits, authors, num_authors, last_time = \
            tasks.commits_author_stats(self.repopath)

        self.assertEqual(num_commits, 1)
        self.assertEqual(num_authors, 1)
        self.assertEqual(last_time, '2018-01-01 00:00')
        self.assertIn(
            authors,
            [
                [(1, [(
                'Alice', 'alice@example.com',
                'https://seccdn.libravatar.org/avatar/'
                'ff8d9819fc0e12bf0d24892e45987e249a28dce836a85cad60e28eaaa8c6d976'
                '?s=32&d=retro'
                )])],
                [(1, [(
                'Alice', 'alice@example.com',
                'https://seccdn.libravatar.org/avatar/'
                'ff8d9819fc0e12bf0d24892e45987e249a28dce836a85cad60e28eaaa8c6d976'
                '?d=retro&s=32'
                )])]
            ]
        )

    def test_rename_user_and_merge(self):
        self.commits = [
            MockCommit('Alice', 'alice@example.com'),
            MockCommit('Bad name', 'alice@example.com', '2018-01-01 00:00'),
        ]
        self.authors = {
            'alice@example.com': MockUser('Alice', 'alice@example.com'),
        }

        num_commits, authors, num_authors, last_time = \
            tasks.commits_author_stats(self.repopath)

        self.assertEqual(num_commits, 2)
        self.assertEqual(num_authors, 1)
        self.assertEqual(last_time, '2018-01-01 00:00')
        self.assertIn(
            authors,
            [
                [(2, [(
                'Alice', 'alice@example.com',
                'https://seccdn.libravatar.org/avatar/'
                'ff8d9819fc0e12bf0d24892e45987e249a28dce836a85cad60e28eaaa8c6d976'
                '?s=32&d=retro'
                )])],
                [(2, [(
                'Alice', 'alice@example.com',
                'https://seccdn.libravatar.org/avatar/'
                'ff8d9819fc0e12bf0d24892e45987e249a28dce836a85cad60e28eaaa8c6d976'
                '?d=retro&s=32'
                )])]
            ]
        )

    def test_preserve_unknown_author(self):
        self.commits = [
            MockCommit('Alice', 'alice@example.com', '2018-01-01 00:00'),
        ]
        self.authors = {}

        num_commits, authors, num_authors, last_time = \
            tasks.commits_author_stats(self.repopath)

        self.assertEqual(num_commits, 1)
        self.assertEqual(num_authors, 1)
        self.assertEqual(last_time, '2018-01-01 00:00')
        self.assertIn(
            authors,
            [
                [(1, [(
                'Alice', 'alice@example.com',
                'https://seccdn.libravatar.org/avatar/'
                'ff8d9819fc0e12bf0d24892e45987e249a28dce836a85cad60e28eaaa8c6d976'
                '?s=32&d=retro'
                )])],
                [(1, [(
                'Alice', 'alice@example.com',
                'https://seccdn.libravatar.org/avatar/'
                'ff8d9819fc0e12bf0d24892e45987e249a28dce836a85cad60e28eaaa8c6d976'
                '?d=retro&s=32'
                )])]
            ]
        )

    def test_handle_empty_email(self):
        self.commits = [
            # Two commits for Alice to ensure order of the result.
            MockCommit('Alice', None),
            MockCommit('Alice', None),
            MockCommit('Bob', '', '2018-01-01 00:00'),
        ]
        self.authors = {}

        num_commits, authors, num_authors, last_time = \
            tasks.commits_author_stats(self.repopath)

        self.assertEqual(num_commits, 3)
        self.assertEqual(num_authors, 2)
        self.assertEqual(last_time, '2018-01-01 00:00')
        self.assertEqual(authors, [(2, [('Alice', None, None)]),
                                   (1, [('Bob', '', None)])])


class TestGitolitePostCompileOnly(object):
    @patch('pagure.lib.git_auth.get_git_auth_helper')
    def test_backend_has_post_compile_only(self, get_helper):
        helper = MagicMock()
        get_helper.return_value = helper
        helper.post_compile_only = MagicMock()
        tasks.gitolite_post_compile_only()
        helper.post_compile_only.assert_called_once()

    @patch('pagure.lib.git_auth.get_git_auth_helper')
    def test_backend_doesnt_have_post_compile_only(self, get_helper):
        helper = MagicMock()
        get_helper.return_value = helper
        helper.generate_acls = MagicMock()
        del helper.post_compile_only
        tasks.gitolite_post_compile_only()
        helper.generate_acls.assert_called_once_with(project=None)
