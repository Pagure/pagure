from mock import patch, Mock
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


@patch('pagure.lib.create_session', new=Mock())
class TestCommitsAuthorStats(unittest.TestCase):

    def setUp(self):
        self.search_user_patcher = patch('pagure.lib.search_user')
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
        self.assertEqual(authors, [(1, [('Alice', 'alice@example.com')])])

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
        self.assertEqual(authors, [(2, [('Alice', 'alice@example.com')])])

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
        self.assertEqual(authors, [(1, [('Alice', 'alice@example.com')])])

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
        self.assertEqual(authors, [(2, [('Alice', None)]),
                                   (1, [('Bob', '')])])
