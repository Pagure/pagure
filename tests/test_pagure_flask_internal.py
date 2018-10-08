# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import datetime
import json
import unittest
import shutil
import sys
import time
import os

import pygit2
from mock import patch, MagicMock, Mock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskInternaltests(tests.Modeltests):
    """ Tests for flask Internal controller of pagure """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskInternaltests, self).setUp()

        pagure.config.config['IP_ALLOWED_INTERNAL'] = list(set(
            pagure.config.config['IP_ALLOWED_INTERNAL'] + [None]))

        pagure.config.config['GIT_FOLDER'] = os.path.join(
            self.path, 'repos')

    @patch('pagure.lib.notify.send_email')
    def test_pull_request_add_comment(self, send_email):
        """ Test the pull_request_add_comment function.  """
        send_email.return_value = True

        tests.create_projects(self.session)

        repo = pagure.lib.get_authorized_project(self.session, 'test')

        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='feature',
            repo_to=repo,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        request = repo.requests[0]
        self.assertEqual(len(request.comments), 0)
        self.assertEqual(len(request.discussion), 0)

        data = {
            'objid': 'foo',
        }

        # Wrong http request
        output = self.app.post('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 405)

        # Invalid request
        output = self.app.put('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 400)

        data = {
            'objid': 'foo',
            'useremail': 'foo@pingou.com',
        }

        # Invalid objid
        output = self.app.put('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 404)

        data = {
            'objid': request.uid,
            'useremail': 'foo@pingou.com',
        }

        # Valid objid, in-complete data for a comment
        output = self.app.put('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 400)

        data = {
            'objid': request.uid,
            'useremail': 'foo@pingou.com',
            'comment': 'Looks good to me!',
        }

        # Add comment
        output = self.app.put('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(js_data, {'message': 'Comment added'})

        self.session.commit()
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        request = repo.requests[0]
        self.assertEqual(len(request.comments), 1)
        self.assertEqual(len(request.discussion), 1)

        # Check the @localonly
        before = pagure.config.config['IP_ALLOWED_INTERNAL'][:]
        pagure.config.config['IP_ALLOWED_INTERNAL'] = []

        output = self.app.put('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 403)

        pagure.config.config['IP_ALLOWED_INTERNAL'] = before[:]

    @patch('pagure.lib.notify.send_email')
    def test_ticket_add_comment(self, send_email):
        """ Test the ticket_add_comment function.  """
        send_email.return_value = True

        tests.create_projects(self.session)

        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        issue = repo.issues[0]
        self.assertEqual(len(issue.comments), 0)

        data = {
            'objid': 'foo',
        }

        # Wrong http request
        output = self.app.post('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 405)

        # Invalid request
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 400)

        data = {
            'objid': 'foo',
            'useremail': 'foo@pingou.com',
        }

        # Invalid objid
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 404)

        data = {
            'objid': issue.uid,
            'useremail': 'foo@pingou.com',
        }

        # Valid objid, in-complete data for a comment
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 400)

        data = {
            'objid': issue.uid,
            'useremail': 'foo@pingou.com',
            'comment': 'Looks good to me!',
        }

        # Add comment
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(js_data, {'message': 'Comment added'})

        self.session.commit()
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = repo.issues[0]
        self.assertEqual(len(issue.comments), 1)

        # Check the @localonly
        pagure.config.config['IP_ALLOWED_INTERNAL'].remove(None)
        before = pagure.config.config['IP_ALLOWED_INTERNAL'][:]
        pagure.config.config['IP_ALLOWED_INTERNAL'] = []

        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 403)

        pagure.config.config['IP_ALLOWED_INTERNAL'] = before[:]

    @patch('pagure.lib.notify.send_email')
    def test_private_ticket_add_comment(self, send_email):
        """ Test the ticket_add_comment function on a private ticket.  """
        send_email.return_value = True

        tests.create_projects(self.session)

        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this, really',
            user='pingou',
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        issue = repo.issues[0]
        self.assertEqual(len(issue.comments), 0)

        data = {
            'objid': 'foo',
        }

        # Wrong http request
        output = self.app.post('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 405)

        # Invalid request
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 400)

        data = {
            'objid': 'foo',
            'useremail': 'foo@pingou.com',
        }

        # Invalid objid
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 404)

        data = {
            'objid': issue.uid,
            'useremail': 'foo@bar.com',
        }

        # Valid objid, un-allowed user for this (private) ticket
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 403)

        data = {
            'objid': issue.uid,
            'useremail': 'foo@pingou.com',
        }

        # Valid objid, un-allowed user for this (private) ticket
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 400)

        data = {
            'objid': issue.uid,
            'useremail': 'foo@pingou.com',
            'comment': 'Looks good to me!',
        }

        # Add comment
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(js_data, {'message': 'Comment added'})

        self.session.commit()
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = repo.issues[0]
        self.assertEqual(len(issue.comments), 1)

        # Check the @localonly
        before = pagure.config.config['IP_ALLOWED_INTERNAL'][:]
        pagure.config.config['IP_ALLOWED_INTERNAL'] = []

        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 403)

        pagure.config.config['IP_ALLOWED_INTERNAL'] = before[:]

    @patch('pagure.lib.notify.send_email')
    def test_private_ticket_add_comment_acl(self, send_email):
        """ Test the ticket_add_comment function on a private ticket.  """
        send_email.return_value = True

        tests.create_projects(self.session)

        # Create issues to play with
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this, really',
            user='pingou',
            private=True,
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = repo.issues[0]
        self.assertEqual(len(issue.comments), 0)

        # Currently, he is just an average user,
        # He doesn't have any access in this repo
        data = {
            'objid': issue.uid,
            'useremail': 'foo@bar.com',
            'comment': 'Looks good to me!',
        }

        # Valid objid, un-allowed user for this (private) ticket
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 403)

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        # Let's promote him to be a ticketer
        # He shoudn't be able to comment even then though
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='ticket'
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertEqual(
            sorted([u.username for u in repo.users]), ['foo'])
        self.assertEqual(
            sorted([u.username for u in repo.committers]), [])
        self.assertEqual(
            sorted([u.username for u in repo.admins]), [])

        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 403)

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        # Let's promote him to be a committer
        # He should be able to comment
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='commit'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')
        repo = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertEqual(
            sorted([u.username for u in repo.users]), ['foo'])
        self.assertEqual(
            sorted([u.username for u in repo.committers]), ['foo'])
        self.assertEqual(
            sorted([u.username for u in repo.admins]), [])

        # Add comment
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(js_data, {'message': 'Comment added'})

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = repo.issues[0]
        self.assertEqual(len(issue.comments), 1)

        # Let's promote him to be a admin
        # He should be able to comment
        msg = pagure.lib.add_user_to_project(
            self.session,
            project=repo,
            new_user='foo',
            user='pingou',
            access='admin'
        )
        self.session.commit()
        self.assertEqual(msg, 'User access updated')

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertEqual(
            sorted([u.username for u in repo.users]), ['foo'])
        self.assertEqual(
            sorted([u.username for u in repo.committers]), ['foo'])
        self.assertEqual(
            sorted([u.username for u in repo.admins]), ['foo'])

        # Add comment
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(js_data, {'message': 'Comment added'})

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        issue = repo.issues[0]
        self.assertEqual(len(issue.comments), 2)

        # Check the @localonly
        before = pagure.config.config['IP_ALLOWED_INTERNAL'][:]
        pagure.config.config['IP_ALLOWED_INTERNAL'] = []

        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 403)

        pagure.config.config['IP_ALLOWED_INTERNAL'] = before[:]

    @patch('pagure.lib.notify.send_email')
    def test_mergeable_request_pull_FF(self, send_email):
        """ Test the mergeable_request_pull endpoint with a fast-forward
        merge.
        """
        send_email.return_value = True

        # Create a git repo to play with

        origgitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(origgitrepo))
        os.makedirs(origgitrepo)
        orig_repo = pygit2.init_repository(origgitrepo, bare=True)
        os.makedirs(os.path.join(self.path, 'repos_tmp'))
        gitrepo = os.path.join(self.path, 'repos_tmp', 'test.git')
        repo = pygit2.clone_repository(origgitrepo, gitrepo)

        # Create a file in that git repo
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
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
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        first_commit = repo.revparse_single('HEAD')
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Edit the sources file again
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        repo.index.add('sources')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        repo.create_commit(
            'refs/heads/feature',  # the name of the reference to update
            author,
            committer,
            'Add baz and boose to the sources\n\n There are more objects to '
            'consider',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )

        second_commit = repo.revparse_single('HEAD')
        refname = 'refs/heads/feature:refs/heads/feature'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create a PR for these changes
        tests.create_projects(self.session)
        project = pagure.lib.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        # Check if the PR can be merged
        data = {
            'objid': 'blah',
        }

        # Missing CSRF
        output = self.app.post('/pv/pull-request/merge', data=data)
        self.assertEqual(output.status_code, 400)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/adduser')
            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Missing request identifier
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 404)

            # With all the desired information
            project = pagure.lib.get_authorized_project(self.session, 'test')
            data = {
                'csrf_token': csrf_token,
                'requestid': project.requests[0].uid,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            exp = {
              "code": "FFORWARD",
              "message": "The pull-request can be merged and fast-forwarded",
              "short_code": "Ok"
            }

            js_data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(js_data, exp)

    @patch('pagure.lib.notify.send_email')
    def test_mergeable_request_pull_no_change(self, send_email):
        """ Test the mergeable_request_pull endpoint when there are no
        changes to merge.
        """
        send_email.return_value = True

        # Create a git repo to play with

        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(gitrepo))
        os.makedirs(gitrepo)
        repo = pygit2.init_repository(gitrepo)

        # Create a file in that git repo
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
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
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        first_commit = repo.revparse_single('HEAD')

        # Edit the sources file again
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        repo.index.add('sources')
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
            'Add baz and boose to the sources\n\n There are more objects to '
            'consider',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )

        second_commit = repo.revparse_single('HEAD')

        # Create a PR for these changes
        tests.create_projects(self.session)
        project = pagure.lib.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='master',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        # Check if the PR can be merged
        data = {
            'objid': 'blah',
        }

        # Missing CSRF
        output = self.app.post('/pv/pull-request/merge', data=data)
        self.assertEqual(output.status_code, 400)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/adduser')
            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Missing request identifier
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 404)

            # With all the desired information
            project = pagure.lib.get_authorized_project(self.session, 'test')
            data = {
                'csrf_token': csrf_token,
                'requestid': project.requests[0].uid,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            exp = {
              "code": "NO_CHANGE",
              "message": "Nothing to change, git is up to date",
              "short_code": "No changes"
            }

            js_data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(js_data, exp)

    @patch('pagure.lib.notify.send_email')
    def test_mergeable_request_pull_merge(self, send_email):
        """ Test the mergeable_request_pull endpoint when the changes can
        be merged with a merge commit.
        """
        send_email.return_value = True

        # Create a git repo to play with

        origgitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(origgitrepo))
        os.makedirs(origgitrepo)
        orig_repo = pygit2.init_repository(origgitrepo, bare=True)
        os.makedirs(os.path.join(self.path, 'repos_tmp'))
        gitrepo = os.path.join(self.path, 'repos_tmp', 'test.git')
        repo = pygit2.clone_repository(origgitrepo, gitrepo)

        # Create a file in that git repo
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
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
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        first_commit = repo.revparse_single('HEAD')
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Edit the sources file again
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        repo.index.add('sources')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        repo.create_commit(
            'refs/heads/feature',  # the name of the reference to update
            author,
            committer,
            'Add baz and boose to the sources\n\n There are more objects to '
            'consider',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/feature:refs/heads/feature'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create another file in the master branch
        with open(os.path.join(gitrepo, '.gitignore'), 'w') as stream:
            stream.write('*~')
        repo.index.add('.gitignore')
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
            'Add .gitignore file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create a PR for these changes
        tests.create_projects(self.session)
        project = pagure.lib.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        # Check if the PR can be merged
        data = {}

        # Missing CSRF
        output = self.app.post('/pv/pull-request/merge', data=data)
        self.assertEqual(output.status_code, 400)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/adduser')
            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Missing request identifier
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 404)

            # With all the desired information
            project = pagure.lib.get_authorized_project(self.session, 'test')
            data = {
                'csrf_token': csrf_token,
                'requestid': project.requests[0].uid,
                'force': True,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            exp = {
              "code": "MERGE",
              "message": "The pull-request can be merged with a merge commit",
              "short_code": "With merge"
            }

            js_data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(js_data, exp)

            # Asking a second time will trigger the cache
            data = {
                'csrf_token': csrf_token,
                'requestid': project.requests[0].uid,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            exp = {
              "code": "MERGE",
              "message": "The pull-request can be merged with a merge commit",
              "short_code": "With merge"
            }

            js_data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(js_data, exp)

    @patch('pagure.lib.notify.send_email')
    def test_mergeable_request_pull_conflicts(self, send_email):
        """ Test the mergeable_request_pull endpoint when the changes cannot
        be merged due to conflicts.
        """
        send_email.return_value = True

        # Create a git repo to play with
        origgitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(origgitrepo))
        os.makedirs(origgitrepo)
        orig_repo = pygit2.init_repository(origgitrepo, bare=True)
        os.makedirs(os.path.join(self.path, 'repos_tmp'))
        gitrepo = os.path.join(self.path, 'repos_tmp', 'test.git')
        repo = pygit2.clone_repository(origgitrepo, gitrepo)

        # Create a file in that git repo
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
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
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        first_commit = repo.revparse_single('HEAD')
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Edit the sources file again
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        repo.index.add('sources')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        repo.create_commit(
            'refs/heads/feature',  # the name of the reference to update
            author,
            committer,
            'Add baz and boose to the sources\n\n There are more objects to '
            'consider',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/feature:refs/heads/feature'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create another file in the master branch
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n')
        repo.index.add('sources')
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
            'Add .gitignore file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create a PR for these changes
        tests.create_projects(self.session)
        project = pagure.lib.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        # Check if the PR can be merged
        data = {}

        # Missing CSRF
        output = self.app.post('/pv/pull-request/merge', data=data)
        self.assertEqual(output.status_code, 400)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/adduser')
            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Missing request identifier
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 404)

            # With all the desired information
            project = pagure.lib.get_authorized_project(self.session, 'test')
            data = {
                'csrf_token': csrf_token,
                'requestid': project.requests[0].uid,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            exp = {
              "code": "CONFLICTS",
              "message": "The pull-request cannot be merged due to conflicts",
              "short_code": "Conflicts"
            }

            js_data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(js_data, exp)

    @patch('pagure.lib.notify.send_email')
    def test_mergeable_request_pull_merge_no_nonff_merges(self, send_email):
        """ Test the mergeable_request_pull endpoint when the changes can
        be merged with a merge commit, but project settings prohibit this.
        """
        send_email.return_value = True

        # Create a git repo to play with

        origgitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(origgitrepo))
        os.makedirs(origgitrepo)
        orig_repo = pygit2.init_repository(origgitrepo, bare=True)
        os.makedirs(os.path.join(self.path, 'repos_tmp'))
        gitrepo = os.path.join(self.path, 'repos_tmp', 'test.git')
        repo = pygit2.clone_repository(origgitrepo, gitrepo)

        # Create a file in that git repo
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
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
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        first_commit = repo.revparse_single('HEAD')
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Edit the sources file again
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        repo.index.add('sources')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        repo.create_commit(
            'refs/heads/feature',  # the name of the reference to update
            author,
            committer,
            'Add baz and boose to the sources\n\n There are more objects to '
            'consider',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/feature:refs/heads/feature'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create another file in the master branch
        with open(os.path.join(gitrepo, '.gitignore'), 'w') as stream:
            stream.write('*~')
        repo.index.add('.gitignore')
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
            'Add .gitignore file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create a PR for these changes
        tests.create_projects(self.session)
        project = pagure.lib.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
        )
        settings = {'disable_non_fast-forward_merges': True}
        project.settings = settings
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        # Check if the PR can be merged
        data = {}

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/adduser')
            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # With all the desired information
            project = pagure.lib.get_authorized_project(self.session, 'test')
            data = {
                'csrf_token': csrf_token,
                'requestid': project.requests[0].uid,
                'force': True,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            exp = {
              "code": "CONFLICTS",
              "message": "The pull-request must be rebased before merging",
              "short_code": "Conflicts"
            }

            js_data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(js_data, exp)

            # Asking a second time will trigger the cache
            data = {
                'csrf_token': csrf_token,
                'requestid': project.requests[0].uid,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 200)
            exp = {
              "code": "CONFLICTS",
              "message": "The pull-request must be rebased before merging",
              "short_code": "Conflicts"
            }

            js_data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(js_data, exp)

    @patch('pagure.lib.notify.send_email')
    def test_mergeable_request_pull_minimum_score(self, send_email):
        """ Test the mergeable_request_pull endpoint when the changes can
        be merged with a merge FF, but project settings enforces vote on
        the PR.
        """
        send_email.return_value = True

        # Create a git repo to play with

        origgitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(origgitrepo))
        os.makedirs(origgitrepo)
        orig_repo = pygit2.init_repository(origgitrepo, bare=True)
        os.makedirs(os.path.join(self.path, 'repos_tmp'))
        gitrepo = os.path.join(self.path, 'repos_tmp', 'test.git')
        repo = pygit2.clone_repository(origgitrepo, gitrepo)

        # Create a file in that git repo
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
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
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        first_commit = repo.revparse_single('HEAD')
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Edit the sources file again
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        repo.index.add('sources')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        repo.create_commit(
            'refs/heads/feature',  # the name of the reference to update
            author,
            committer,
            'Add baz and boose to the sources\n\n There are more objects to '
            'consider',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/feature:refs/heads/feature'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create a PR for these changes
        tests.create_projects(self.session)
        project = pagure.lib.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
        )
        settings = {'Minimum_score_to_merge_pull-request': 2}
        project.settings = settings
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        # Check if the PR can be merged
        data = {}

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/adduser')
            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # With all the desired information
            project = pagure.lib.get_authorized_project(self.session, 'test')
            data = {
                'csrf_token': csrf_token,
                'requestid': project.requests[0].uid,
                'force': True,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 400)
            exp = {
              "code": "CONFLICTS",
              "message": "Pull-Request does not meet the minimal number "
                  "of review required: 0/2"
            }

            js_data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(js_data, exp)

            # Asking a second time will trigger the cache
            data = {
                'csrf_token': csrf_token,
                'requestid': project.requests[0].uid,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 400)
            exp = {
              "code": "CONFLICTS",
              "message": "Pull-Request does not meet the minimal number "
                  "of review required: 0/2"
            }

            js_data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(js_data, exp)

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    @patch(
        'pagure.lib.git.merge_pull_request',
        MagicMock(side_effect=pagure.exceptions.PagureException('error')))
    def test_mergeable_request_pull_merge_pagureerror(self):
        """ Test the mergeable_request_pull endpoint when the backend
        raises an GitError exception.
        """
        # Create a git repo to play with

        origgitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(origgitrepo))
        os.makedirs(origgitrepo)
        orig_repo = pygit2.init_repository(origgitrepo, bare=True)
        os.makedirs(os.path.join(self.path, 'repos_tmp'))
        gitrepo = os.path.join(self.path, 'repos_tmp', 'test.git')
        repo = pygit2.clone_repository(origgitrepo, gitrepo)

        # Create a file in that git repo
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
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
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        first_commit = repo.revparse_single('HEAD')
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Edit the sources file again
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        repo.index.add('sources')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        repo.create_commit(
            'refs/heads/feature',  # the name of the reference to update
            author,
            committer,
            'Add baz and boose to the sources\n\n There are more objects to '
            'consider',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/feature:refs/heads/feature'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create another file in the master branch
        with open(os.path.join(gitrepo, '.gitignore'), 'w') as stream:
            stream.write('*~')
        repo.index.add('.gitignore')
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
            'Add .gitignore file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create a PR for these changes
        tests.create_projects(self.session)
        project = pagure.lib.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        # Check if the PR can be merged
        data = {}

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/adduser')
            csrf_token = self.get_csrf(output=output)

            # With all the desired information
            project = pagure.lib.get_authorized_project(self.session, 'test')
            data = {
                'csrf_token': csrf_token,
                'requestid': project.requests[0].uid,
                'force': True,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 500)
            exp = {u'code': u'CONFLICTS', u'message': u'error'}

            js_data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(js_data, exp)

    @patch('pagure.lib.notify.send_email', MagicMock(return_value=True))
    @patch(
        'pagure.lib.git.merge_pull_request',
        MagicMock(side_effect=pygit2.GitError('git error')))
    def test_mergeable_request_pull_merge_giterror(self):
        """ Test the mergeable_request_pull endpoint when the backend
        raises an GitError exception.
        """
        # Create a git repo to play with

        origgitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertFalse(os.path.exists(origgitrepo))
        os.makedirs(origgitrepo)
        orig_repo = pygit2.init_repository(origgitrepo, bare=True)
        os.makedirs(os.path.join(self.path, 'repos_tmp'))
        gitrepo = os.path.join(self.path, 'repos_tmp', 'test.git')
        repo = pygit2.clone_repository(origgitrepo, gitrepo)

        # Create a file in that git repo
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
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
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        first_commit = repo.revparse_single('HEAD')
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Edit the sources file again
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        repo.index.add('sources')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        repo.create_commit(
            'refs/heads/feature',  # the name of the reference to update
            author,
            committer,
            'Add baz and boose to the sources\n\n There are more objects to '
            'consider',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/feature:refs/heads/feature'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create another file in the master branch
        with open(os.path.join(gitrepo, '.gitignore'), 'w') as stream:
            stream.write('*~')
        repo.index.add('.gitignore')
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
            'Add .gitignore file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Create a PR for these changes
        tests.create_projects(self.session)
        project = pagure.lib.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'PR from the feature branch')

        # Check if the PR can be merged
        data = {}

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/adduser')
            csrf_token = self.get_csrf(output=output)

            # With all the desired information
            project = pagure.lib.get_authorized_project(self.session, 'test')
            data = {
                'csrf_token': csrf_token,
                'requestid': project.requests[0].uid,
                'force': True,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 409)
            exp = {u'code': u'CONFLICTS', u'message': u'git error'}

            js_data = json.loads(output.get_data(as_text=True))
            self.assertDictEqual(js_data, exp)

    def test_get_branches_of_commit(self):
        ''' Test the get_branches_of_commit from the internal API. '''
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 200)
            csrf_token = output.get_data(as_text=True).split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

        # No CSRF token
        data = {
            'repo': 'fakerepo',
            'commit_id': 'foo',
        }
        output = self.app.post('/pv/branches/commit/', data=data)
        self.assertEqual(output.status_code, 400)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {'code': 'ERROR', 'message': 'Invalid input submitted'}
        )

        # Invalid repo
        data = {
            'repo': 'fakerepo',
            'commit_id': 'foo',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/branches/commit/', data=data)
        self.assertEqual(output.status_code, 404)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {
                'code': 'ERROR',
                'message': 'No repo found with the information provided'
            }
        )

        # Rigth repo, no commit
        data = {
            'repo': 'test',
            'csrf_token': csrf_token,
        }

        output = self.app.post('/pv/branches/commit/', data=data)
        self.assertEqual(output.status_code, 400)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {'code': 'ERROR', 'message': 'No commit id submitted'}
        )

        # Request is fine, but git repo doesn't exist
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test20',
            description='test project #20',
            hook_token='aaabbbhhh',
        )
        self.session.add(item)
        self.session.commit()

        data = {
            'repo': 'test20',
            'commit_id': 'foo',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/branches/commit/', data=data)
        self.assertEqual(output.status_code, 404)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {
                'code': 'ERROR',
                'message': 'No git repo found with the information provided'
            }
        )

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertTrue(os.path.exists(gitrepo))
        repo = pygit2.Repository(gitrepo)

        # Create a file in that git repo
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
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
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        first_commit = repo.revparse_single('HEAD')

        # Edit the sources file again
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        repo.index.add('sources')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        repo.create_commit(
            'refs/heads/feature',  # the name of the reference to update
            author,
            committer,
            'Add baz and boose to the sources\n\n There are more objects to '
            'consider',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )

        # Create another file in the master branch
        with open(os.path.join(gitrepo, '.gitignore'), 'w') as stream:
            stream.write('*~')
        repo.index.add('.gitignore')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        commit_hash = repo.create_commit(
            'refs/heads/feature_branch',  # the name of the reference to update
            author,
            committer,
            'Add .gitignore file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )

        # All good but the commit id
        data = {
            'repo': 'test',
            'commit_id': 'foo',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/branches/commit/', data=data)
        self.assertEqual(output.status_code, 404)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {
                'code': 'ERROR',
                'message': 'This commit could not be found in this repo'
            }
        )

        # All good
        data = {
            'repo': 'test',
            'commit_id': commit_hash,
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/branches/commit/', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {
                'code': 'OK',
                'branches': ['feature_branch'],
            }
        )

    def test_get_branches_of_commit_with_unrelated_branches(self):
        ''' Test the get_branches_of_commit from the internal API. '''
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser(username='pingou')
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertTrue(os.path.exists(gitrepo))
        repo = pygit2.Repository(gitrepo)

        # Create a file in that git repo
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
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
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        first_commit = repo.revparse_single('HEAD')

        # Edit the sources file again
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        repo.index.add('sources')
        repo.index.write()

        # Commits the files added, but unrelated with the first commit
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        commit = repo.create_commit(
            'refs/heads/feature',  # the name of the reference to update
            author,
            committer,
            'Add baz and boose to the sources\n\n There are more objects to '
            'consider',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )
        commit_hash = commit.hex

        # All good
        data = {
            'repo': 'test',
            'commit_id': commit_hash,
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/branches/commit/', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {
                u'code': u'OK',
                u'branches': ['feature'],
            }
        )

    def test_get_branches_head(self):
        ''' Test the get_branches_head from the internal API. '''
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # No CSRF token
        data = {
            'repo': 'fakerepo',
        }
        output = self.app.post('/pv/branches/heads/', data=data)
        self.assertEqual(output.status_code, 400)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {'code': 'ERROR', 'message': 'Invalid input submitted'}
        )

        # Invalid repo
        data = {
            'repo': 'fakerepo',
            'commit_id': 'foo',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/branches/heads/', data=data)
        self.assertEqual(output.status_code, 404)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {
                'code': 'ERROR',
                'message': 'No repo found with the information provided'
            }
        )

        # Rigth repo, no commit
        data = {
            'repo': 'test',
            'csrf_token': csrf_token,
        }

        output = self.app.post('/pv/branches/heads/', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {"branches": {}, "code": "OK", "heads": {}}
        )

        # Request is fine, but git repo doesn't exist
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test20',
            description='test project #20',
            hook_token='aaabbbhhh',
        )
        self.session.add(item)
        self.session.commit()

        data = {
            'repo': 'test20',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/branches/heads/', data=data)
        self.assertEqual(output.status_code, 404)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {
                'code': 'ERROR',
                'message': 'No git repo found with the information provided'
            }
        )

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        self.assertTrue(os.path.exists(gitrepo))
        repo = pygit2.Repository(gitrepo)

        # Create a file in that git repo
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        repo.index.add('sources')
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
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )

        first_commit = repo.revparse_single('HEAD')

        # Edit the sources file again
        with open(os.path.join(gitrepo, 'sources'), 'w') as stream:
            stream.write('foo\n bar\nbaz\n boose')
        repo.index.add('sources')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        repo.create_commit(
            'refs/heads/feature',  # the name of the reference to update
            author,
            committer,
            'Add baz and boose to the sources\n\n There are more objects to '
            'consider',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )

        # Create another file in the master branch
        with open(os.path.join(gitrepo, '.gitignore'), 'w') as stream:
            stream.write('*~')
        repo.index.add('.gitignore')
        repo.index.write()

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        commit_hash = repo.create_commit(
            'refs/heads/feature_branch',  # the name of the reference to update
            author,
            committer,
            'Add .gitignore file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit.oid.hex]
        )

        # All good
        data = {
            'repo': 'test',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/branches/heads/', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        # We can't test the content since the commit hash will change all
        # the time, so let's just check the structure
        self.assertEqual(
            sorted(js_data.keys()), ['branches', 'code', 'heads'])
        self.assertEqual(js_data['code'], 'OK')
        self.assertEqual(len(js_data['heads']), 3)
        self.assertEqual(len(js_data['branches']), 3)

    def test_get_stats_commits_no_token(self):
        ''' Test the get_stats_commits from the internal API. '''
        # No CSRF token
        data = {
            'repo': 'fakerepo',
        }
        output = self.app.post('/pv/stats/commits/authors', data=data)
        self.assertEqual(output.status_code, 400)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {'code': 'ERROR', 'message': 'Invalid input submitted'}
        )

    def test_get_stats_commits_invalid_repo(self):
        ''' Test the get_stats_commits from the internal API. '''
        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # Invalid repo
        data = {
            'repo': 'fakerepo',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/stats/commits/authors', data=data)
        self.assertEqual(output.status_code, 404)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {'code': 'ERROR',
             'message': 'No repo found with the information provided'}
        )

    def test_get_stats_commits_empty_git(self):
        ''' Test the get_stats_commits from the internal API. '''
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # No content in git
        data = {
            'repo': 'test',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/stats/commits/authors', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'message', 'task_id', 'url']
        )
        self.assertEqual(js_data['code'], 'OK')
        self.assertEqual(js_data['message'], 'Stats asked')
        self.assertTrue(js_data['url'].startswith('/pv/task/'))

        output = self.app.get(js_data['url'])
        js_data2 = json.loads(output.get_data(as_text=True))
        self.assertTrue(
            js_data2 in [
                {'results': "reference 'refs/heads/master' not found"},
                {'results': "Reference 'refs/heads/master' not found"}
            ]
        )

    def test_get_stats_commits_git_populated(self):
        ''' Test the get_stats_commits from the internal API. '''
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'test.git'))

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # Content in git
        data = {
            'repo': 'test',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/stats/commits/authors', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'message', 'task_id', 'url']
        )
        self.assertEqual(js_data['code'], 'OK')
        self.assertEqual(js_data['message'], 'Stats asked')
        self.assertTrue(js_data['url'].startswith('/pv/task/'))

        output = self.app.get(js_data['url'])
        while output.status_code == 418:
            time.sleep(0.5)
            output = self.app.get(js_data['url'])
        js_data2 = json.loads(output.get_data(as_text=True))
        self.assertTrue(js_data2['results'][3] > 1509110062)
        js_data2['results'][3] = 1509110062
        self.assertDictEqual(
            js_data2,
            {'results': [
                2,
                [[2, [['Alice Author', 'alice@authors.tld']]]],
                1,
                1509110062
            ]
            }
        )

    def test_get_stats_commits_trend_no_token(self):
        ''' Test the get_stats_commits_trend from the internal API. '''
        # No CSRF token
        data = {
            'repo': 'fakerepo',
        }
        output = self.app.post('/pv/stats/commits/trend', data=data)
        self.assertEqual(output.status_code, 400)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {'code': 'ERROR', 'message': 'Invalid input submitted'}
        )

    def test_get_stats_commits_trend_invalid_repo(self):
        """ Test the get_stats_commits_trend from the internal API. """
        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # Invalid repo
        data = {
            'repo': 'fakerepo',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/stats/commits/trend', data=data)
        self.assertEqual(output.status_code, 404)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            js_data,
            {'code': 'ERROR',
             'message': 'No repo found with the information provided'}
        )

    def test_get_stats_commits_trend_empty_git(self):
        ''' Test the get_stats_commits_trend from the internal API. '''
        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'repos'))

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # No content in git
        data = {
            'repo': 'test',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/stats/commits/trend', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'message', 'task_id', 'url']
        )
        self.assertEqual(js_data['code'], 'OK')
        self.assertEqual(js_data['message'], 'Stats asked')
        self.assertTrue(js_data['url'].startswith('/pv/task/'))

        output = self.app.get(js_data['url'])
        js_data2 = json.loads(output.get_data(as_text=True))
        self.assertTrue(
            js_data2 in [
                {'results': "reference 'refs/heads/master' not found"},
                {'results': "Reference 'refs/heads/master' not found"}
            ]
        )

    def test_get_stats_commits_trend_git_populated(self):
        ''' Test the get_stats_commits_trend from the internal API. '''
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'test.git'))

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # Content in git
        data = {
            'repo': 'test',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/stats/commits/trend', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'message', 'task_id', 'url']
        )
        self.assertEqual(js_data['code'], 'OK')
        self.assertEqual(js_data['message'], 'Stats asked')
        self.assertTrue(js_data['url'].startswith('/pv/task/'))

        output = self.app.get(js_data['url'])
        js_data2 = json.loads(output.get_data(as_text=True))
        today = datetime.datetime.utcnow().date()
        self.assertDictEqual(
            js_data2,
            {'results': [[str(today), 2]]}
        )

    def test_get_project_family_no_project(self):
        ''' Test the get_project_family from the internal API. '''
        output = self.app.post('/pv/test/family')
        self.assertEqual(output.status_code, 404)

    def test_get_project_family_no_csrf(self):
        ''' Test the get_project_family from the internal API. '''
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'test.git'))

        output = self.app.post('/pv/test/family')
        self.assertEqual(output.status_code, 400)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'message']
        )
        self.assertEqual(js_data['code'], 'ERROR')
        self.assertEqual(js_data['message'], 'Invalid input submitted')

    def test_get_project_family(self):
        ''' Test the get_project_family from the internal API. '''
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'test.git'))

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        data = {
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/test/family', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'family']
        )
        self.assertEqual(js_data['code'], 'OK')
        self.assertEqual(js_data['family'], ['test'])

    def test_get_project_larger_family(self):
        ''' Test the get_project_family from the internal API. '''
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        # Create a 3rd user
        item = pagure.lib.model.User(
            user='ralph',
            fullname='Ralph bar',
            password='ralph_foo',
            default_email='ralph@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='ralph@bar.com')
        self.session.add(item)
        self.session.commit()

        # Create a couple of forks of the test project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            is_fork=True,
            parent_id=1,  # test
            description='test project #1',
            hook_token='aaabbbcccddd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        self.session.add(item)
        item = pagure.lib.model.Project(
            user_id=3,  # Ralph
            name='test',
            is_fork=True,
            parent_id=1,  # test
            description='test project #1',
            hook_token='aaabbbccceee',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        self.session.add(item)
        self.session.commit()

        # Get on with testing
        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        data = {
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/test/family', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'family']
        )
        self.assertEqual(js_data['code'], 'OK')
        self.assertEqual(
            js_data['family'],
            ['test', 'fork/foo/test', 'fork/ralph/test'])

    def test_get_project_larger_family_pr_only(self):
        ''' Test the get_project_family from the internal API. '''
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        # Create a 3rd user
        item = pagure.lib.model.User(
            user='ralph',
            fullname='Ralph bar',
            password='ralph_foo',
            default_email='ralph@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='ralph@bar.com')
        self.session.add(item)
        self.session.commit()

        # Create a couple of forks of the test project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            is_fork=True,
            parent_id=1,  # test
            description='test project #1',
            hook_token='aaabbbcccddd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        # disable issues in this fork
        default_repo_settings = item.settings
        default_repo_settings['issue_tracker'] = False
        item.settings = default_repo_settings
        self.session.add(item)

        item = pagure.lib.model.Project(
            user_id=3,  # Ralph
            name='test',
            is_fork=True,
            parent_id=1,  # test
            description='test project #1',
            hook_token='aaabbbccceee',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        # disable PRs in this fork
        default_repo_settings = item.settings
        default_repo_settings['pull_requests'] = False
        item.settings = default_repo_settings
        self.session.add(item)
        self.session.commit()

        # Get on with testing
        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        data = {
            'csrf_token': csrf_token,
            'allows_pr': '1',
        }
        output = self.app.post('/pv/test/family', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'family']
        )
        self.assertEqual(js_data['code'], 'OK')
        self.assertEqual(
            js_data['family'],
            ['test', 'fork/foo/test'])

        data = {
            'csrf_token': csrf_token,
            'allows_issues': '1',
        }
        output = self.app.post('/pv/test/family', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'family']
        )
        self.assertEqual(js_data['code'], 'OK')
        self.assertEqual(
            js_data['family'],
            ['test', 'fork/ralph/test'])

    def test_get_pull_request_ready_branch_no_csrf(self):
        '''Test the get_pull_request_ready_branch from the internal API
        on the main repository
        '''
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        # Query branches on the main repo
        data = {
            'repo': 'test',
        }
        output = self.app.post('/pv/pull-request/ready', data=data)
        self.assertEqual(output.status_code, 400)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'message']
        )
        self.assertEqual(js_data['code'], 'ERROR')
        self.assertEqual(
            js_data['message'],
            'Invalid input submitted'
        )

    def test_get_pull_request_ready_branch_no_repo(self):
        '''Test the get_pull_request_ready_branch from the internal API
        on the main repository
        '''
        with tests.user_set(self.app.application, tests.FakeUser()):
            csrf_token = self.get_csrf()

        # Query branches on an invalid repo
        data = {
            'repo': 'test',
            'namespace': 'fake',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/pull-request/ready', data=data)
        self.assertEqual(output.status_code, 404)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'message']
        )
        self.assertEqual(js_data['code'], 'ERROR')
        self.assertEqual(
            js_data['message'],
            'No repo found with the information provided'
        )

    def test_get_pull_request_ready_branch_main_repo_no_branch(self):
        '''Test the get_pull_request_ready_branch from the internal API
        on the main repository
        '''
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        # Get on with testing
        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # Query branches on the main repo
        data = {
            'csrf_token': csrf_token,
            'repo': 'test',
        }
        output = self.app.post('/pv/pull-request/ready', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'task']
        )
        self.assertEqual(js_data['code'], 'OK')

    def test_get_pull_request_ready_branch_on_fork(self):
        '''Test the get_pull_request_ready_branch from the internal API on
        a fork
        '''
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, 'repos', 'forks', 'foo'), bare=True)

        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'foo', 'test.git'),
            branch='feature')

        # Create foo's fork of the test project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            is_fork=True,
            parent_id=1,  # test
            description='test project #1',
            hook_token='aaabbbcccddd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        self.session.add(item)
        self.session.commit()

        # Get on with testing
        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # Query branches on the Ralph's fork
        data = {
            'csrf_token': csrf_token,
            'repo': 'test',
            'repouser': 'foo',
        }
        output = self.app.post('/pv/pull-request/ready', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'task']
        )
        self.assertEqual(js_data['code'], 'OK')
        output = self.app.get('/pv/task/' + js_data['task'])
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            js_data,
            {'results': {
                'branch_w_pr': {},
                'new_branch': {'feature':
                    {'commits': 2, 'target_branch': 'master'}}}}
        )

    def test_get_pull_request_ready_branch_on_fork_no_parent_no_pr(self):
        '''Test the get_pull_request_ready_branch from the internal API on
        a fork that has no parent repo (deleted) and doesn't allow PR
        '''
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, 'repos', 'forks', 'foo'), bare=True)

        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'foo', 'test.git'),
            branch='feature')

        # Create foo's fork of the test project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            is_fork=True,
            parent_id=1,  # test
            description='test project #1',
            hook_token='aaabbbcccddd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        self.session.add(item)
        self.session.commit()
        settings = item.settings
        settings['pull_requests'] = False
        item.settings = settings
        self.session.add(item)
        self.session.commit()

        # Delete the parent project
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.session.delete(project)
        self.session.commit()

        # Get on with testing
        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # Query branches on the Ralph's fork
        data = {
            'csrf_token': csrf_token,
            'repo': 'test',
            'repouser': 'foo',
        }
        output = self.app.post('/pv/pull-request/ready', data=data)
        self.assertEqual(output.status_code, 400)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'message']
        )
        self.assertEqual(js_data['code'], 'ERROR')
        self.assertEqual(
            js_data['message'],
            'Pull-request have been disabled for this repo')

    def test_get_pull_request_ready_branch_on_fork_no_parent(self):
        '''Test the get_pull_request_ready_branch from the internal API on
        a fork that has no parent repo (deleted).
        '''
        tests.create_projects(self.session)
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, 'repos', 'forks', 'foo'), bare=True)

        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'foo', 'test.git'),
            branch='feature')

        # Create foo's fork of the test project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            is_fork=True,
            parent_id=1,  # test
            description='test project #1',
            hook_token='aaabbbcccddd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        self.session.add(item)
        self.session.commit()
        settings = item.settings
        settings['pull_requests'] = True
        item.settings = settings
        self.session.add(item)
        self.session.commit()

        # Delete the parent project
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.session.delete(project)
        self.session.commit()

        # Get on with testing
        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # Query branches on the Ralph's fork
        data = {
            'csrf_token': csrf_token,
            'repo': 'test',
            'repouser': 'foo',
        }
        output = self.app.post('/pv/pull-request/ready', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'task']
        )
        self.assertEqual(js_data['code'], 'OK')
        output = self.app.get('/pv/task/' + js_data['task'])
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            js_data,
            {'results': {
                'branch_w_pr': {},
                'new_branch': {'feature':
                    {'commits': 2, 'target_branch': 'master'}}}}
        )

    def test_get_pull_request_ready_branch_matching_target_off(self):
        '''Test the get_pull_request_ready_branch from the internal API on
        a fork while PR_TARGET_MATCHING_BRANCH is False
        '''
        tests.create_projects(self.session)
        # make sure that head is not unborn
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'test.git'),
            branch='master')
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'test.git'),
            branch='feature')

        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, 'repos', 'forks', 'foo'), bare=True)
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'foo', 'test.git'),
            branch='feature')

        # Create foo's fork of the test project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            is_fork=True,
            parent_id=1,  # test
            description='test project #1',
            hook_token='aaabbbcccddd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        self.session.add(item)
        self.session.commit()

        # Get on with testing
        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # Query branches on the Ralph's fork
        data = {
            'csrf_token': csrf_token,
            'repo': 'test',
            'repouser': 'foo',
        }
        output = self.app.post('/pv/pull-request/ready', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'task']
        )
        self.assertEqual(js_data['code'], 'OK')
        output = self.app.get('/pv/task/' + js_data['task'])
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            js_data,
            {'results': {
                'branch_w_pr': {},
                'new_branch': {'feature':
                    {'commits': 2, 'target_branch': 'master'}}}}
        )

    @patch.dict('pagure.config.config', {'PR_TARGET_MATCHING_BRANCH': True})
    def test_get_pull_request_ready_branch_matching_target_on(self):
        '''Test the get_pull_request_ready_branch from the internal API on
        a fork while PR_TARGET_MATCHING_BRANCH is True
        '''
        tests.create_projects(self.session)
        # make sure that head is not unborn
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'test.git'),
            branch='master')
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'test.git'),
            branch='feature')

        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)
        tests.create_projects_git(
            os.path.join(self.path, 'repos', 'forks', 'foo'), bare=True)
        tests.add_content_git_repo(
            os.path.join(self.path, 'repos', 'forks', 'foo', 'test.git'),
            append="testing from foo's fork",
            branch='feature')

        # Create foo's fork of the test project
        item = pagure.lib.model.Project(
            user_id=2,  # foo
            name='test',
            is_fork=True,
            parent_id=1,  # test
            description='test project #1',
            hook_token='aaabbbcccddd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
        self.session.add(item)
        self.session.commit()

        # Get on with testing
        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(self.app.application, user):
            csrf_token = self.get_csrf()

        # Query branches on the Ralph's fork
        data = {
            'csrf_token': csrf_token,
            'repo': 'test',
            'repouser': 'foo',
        }
        output = self.app.post('/pv/pull-request/ready', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            sorted(js_data.keys()),
            ['code', 'task']
        )
        self.assertEqual(js_data['code'], 'OK')
        output = self.app.get('/pv/task/' + js_data['task'])
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.get_data(as_text=True))
        self.assertEqual(
            js_data,
            {'results': {
                'branch_w_pr': {},
                'new_branch': {'feature':
                    {'commits': 1, 'target_branch': 'feature'}}}}
        )

    def test_task_info_task_running(self):
        """ Test the task_info internal API endpoint when the task isn't
        ready.
        """
        task = MagicMock()
        task.get = MagicMock(return_value='FAILED')
        task.ready = MagicMock(return_value=False)
        with patch('pagure.lib.tasks.get_result', MagicMock(return_value=task)):
            output = self.app.get('/pv/task/2')
            self.assertEqual(output.status_code, 418)

    def test_task_info_task_passed(self):
        """ Test the task_info internal API endpoint when the task failed.
        """
        task = MagicMock()
        task.get = MagicMock(return_value='PASSED')
        with patch('pagure.lib.tasks.get_result', MagicMock(return_value=task)):
            output = self.app.get('/pv/task/2')
            self.assertEqual(output.status_code, 200)
            js_data = json.loads(output.get_data(as_text=True))
            self.assertEqual(js_data, {u'results': u'PASSED'})

    def test_task_info_task_failed(self):
        """ Test the task_info internal API endpoint when the task failed.
        """
        task = MagicMock()
        task.get = MagicMock(return_value=Exception('Random error'))
        with patch('pagure.lib.tasks.get_result', MagicMock(return_value=task)):
            output = self.app.get('/pv/task/2')
            self.assertEqual(output.status_code, 200)
            js_data = json.loads(output.get_data(as_text=True))
            self.assertEqual(js_data, {u'results': u'Random error'})

    def test_lookup_ssh_key(self):
        """ Test the mergeable_request_pull endpoint when the backend
        raises an GitError exception.
        """
        tests.create_projects(self.session)

        repo = pagure.lib.get_authorized_project(self.session, 'test')
        project_key = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC4zmifEL8TLLZUZnjAuVL8495DAkpAAM2eBhwHwawBm'
        project_key_fp = 'SHA256:ZSUQAqpPDWi90Fs6Ow8Epc8F3qiKVfU+H5ssvo7jiI0'

        pingou = pagure.lib.get_user(self.session, 'pingou')
        user_key = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDTsfdTcXw4rlU1aQwOTbLOXqossLwpPIk27S/G17kUz'
        user_key_fp = 'SHA256:jUJHzrq2Ct6Ubf7Y9rnB6tGnbHM9dMVsveyfPojm+i0'

        pagure.lib.add_sshkey_to_project_or_user(
            self.session,
            user_key,
            pushaccess=True,
            creator=pingou,
            user=pingou,
        )
        pagure.lib.add_sshkey_to_project_or_user(
            self.session,
            project_key,
            pushaccess=True,
            creator=pingou,
            project=repo,
        )
        self.session.commit()

        url = '/pv/ssh/lookupkey/'

        output = self.app.post(
            url,
            data={'search_key': 'asdf'},
        )
        self.assertEqual(output.status_code, 200)
        result = json.loads(output.get_data(as_text=True))
        self.assertEqual(result['found'], False)

        output = self.app.post(
            url,
            data={'search_key': user_key_fp},
        )
        self.assertEqual(output.status_code, 200)
        result = json.loads(output.get_data(as_text=True))
        self.assertEqual(result['found'], True)
        self.assertEqual(result['username'], 'pingou')
        self.assertEqual(result['public_key'], user_key)

        output = self.app.post(
            url,
            data={'search_key': user_key_fp,
                  'username': 'pingou'},
        )
        self.assertEqual(output.status_code, 200)
        result = json.loads(output.get_data(as_text=True))
        self.assertEqual(result['found'], True)
        self.assertEqual(result['username'], 'pingou')
        self.assertEqual(result['public_key'], user_key)

        output = self.app.post(
            url,
            data={'search_key': user_key_fp,
                  'username': 'foo'},
        )
        self.assertEqual(output.status_code, 200)
        result = json.loads(output.get_data(as_text=True))
        self.assertEqual(result['found'], False)

        output = self.app.post(
            url,
            data={'search_key': project_key_fp},
        )
        self.assertEqual(output.status_code, 200)
        result = json.loads(output.get_data(as_text=True))
        self.assertEqual(result['found'], True)
        self.assertEqual(result['username'], 'deploykey_test_2')
        self.assertEqual(result['public_key'], project_key)

    def test_check_ssh_access(self):
        """ Test the SSH access check endpoint. """
        tests.create_projects(self.session)

        url = '/pv/ssh/checkaccess/'
        def runtest(project, username, access):
            output = self.app.post(
                url,
                data={
                    'gitdir': project,
                    'username': username,
                }
            )
            self.assertEqual(output.status_code, 200)
            result = json.loads(output.get_data(as_text=True))
            self.assertEqual(result['access'], access)
            return result

        runtest('project.git', 'pingou', False)
        i1 = runtest('test.git', 'pingou', True)
        i2 = runtest('test.git', 'foo', True)
        i3 = runtest('tickets/test.git', 'pingou', True)
        runtest('tickets/test.git', 'foo', False)

        self.assertEqual(i1['reponame'], 'test.git')
        self.assertEqual(i1['repotype'], 'main')
        self.assertEqual(i1['region'], None)
        self.assertEqual(i1['project_name'], 'test')
        self.assertEqual(i1['project_user'], None)
        self.assertEqual(i1['project_namespace'], None)
        self.assertEqual(i1, i2)
        self.assertEqual(i3['reponame'], 'tickets/test.git')
        self.assertEqual(i3['repotype'], 'tickets')
        self.assertEqual(i3['region'], None)
        self.assertEqual(i3['project_name'], 'test')
        self.assertEqual(i3['project_user'], None)
        self.assertEqual(i3['project_namespace'], None)


if __name__ == '__main__':
    unittest.main(verbosity=2)
