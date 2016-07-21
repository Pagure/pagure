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

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import tests


class PagureFlaskInternaltests(tests.Modeltests):
    """ Tests for flask Internal controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskInternaltests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.APP.config['IP_ALLOWED_INTERNAL'] = list(set(
            pagure.APP.config['IP_ALLOWED_INTERNAL'] + [None]))
        pagure.SESSION = self.session
        pagure.internal.SESSION = self.session
        pagure.ui.repo.SESSION = self.session
        pagure.ui.filters.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = self.path
        pagure.APP.config['REQUESTS_FOLDER'] = None
        pagure.APP.config['TICKETS_FOLDER'] = None
        pagure.APP.config['DOCS_FOLDER'] = None
        self.app = pagure.APP.test_client()

    @patch('pagure.lib.notify.send_email')
    def test_pull_request_add_comment(self, send_email):
        """ Test the pull_request_add_comment function.  """
        send_email.return_value = True

        tests.create_projects(self.session)

        repo = pagure.get_authorized_project(self.session, 'test')

        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='feature',
            repo_to=repo,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
            requestfolder=None,
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
        js_data = json.loads(output.data)
        self.assertDictEqual(js_data, {'message': 'Comment added'})

        repo = pagure.get_authorized_project(self.session, 'test')
        request = repo.requests[0]
        self.assertEqual(len(request.comments), 1)
        self.assertEqual(len(request.discussion), 1)

        # Check the @localonly
        before = pagure.APP.config['IP_ALLOWED_INTERNAL'][:]
        pagure.APP.config['IP_ALLOWED_INTERNAL'] = []

        output = self.app.put('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 403)

        pagure.APP.config['IP_ALLOWED_INTERNAL'] = before[:]

    @patch('pagure.lib.notify.send_email')
    def test_ticket_add_comment(self, send_email):
        """ Test the ticket_add_comment function.  """
        send_email.return_value = True

        tests.create_projects(self.session)

        # Create issues to play with
        repo = pagure.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this',
            user='pingou',
            ticketfolder=None
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
        js_data = json.loads(output.data)
        self.assertDictEqual(js_data, {'message': 'Comment added'})

        repo = pagure.get_authorized_project(self.session, 'test')
        issue = repo.issues[0]
        self.assertEqual(len(issue.comments), 1)

        # Check the @localonly
        pagure.APP.config['IP_ALLOWED_INTERNAL'].remove(None)
        before = pagure.APP.config['IP_ALLOWED_INTERNAL'][:]
        pagure.APP.config['IP_ALLOWED_INTERNAL'] = []

        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 403)

        pagure.APP.config['IP_ALLOWED_INTERNAL'] = before[:]

    @patch('pagure.lib.notify.send_email')
    def test_private_ticket_add_comment(self, send_email):
        """ Test the ticket_add_comment function on a private ticket.  """
        send_email.return_value = True

        tests.create_projects(self.session)

        # Create issues to play with
        repo = pagure.get_authorized_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this, really',
            user='pingou',
            private=True,
            ticketfolder=None
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
        js_data = json.loads(output.data)
        self.assertDictEqual(js_data, {'message': 'Comment added'})

        repo = pagure.get_authorized_project(self.session, 'test')
        issue = repo.issues[0]
        self.assertEqual(len(issue.comments), 1)

        # Check the @localonly
        before = pagure.APP.config['IP_ALLOWED_INTERNAL'][:]
        pagure.APP.config['IP_ALLOWED_INTERNAL'] = []

        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 403)

        pagure.APP.config['IP_ALLOWED_INTERNAL'] = before[:]

    @patch('pagure.lib.notify.send_email')
    def test_private_ticket_add_comment_acl(self, send_email):
        """ Test the ticket_add_comment function on a private ticket.  """
        send_email.return_value = True

        tests.create_projects(self.session)

        # Create issues to play with
        repo = pagure.lib.get_project(self.session, 'test')
        msg = pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue',
            content='We should work on this, really',
            user='pingou',
            private=True,
            ticketfolder=None
        )
        self.session.commit()
        self.assertEqual(msg.title, 'Test issue')

        repo = pagure.lib.get_project(self.session, 'test')
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

        repo = pagure.lib.get_project(self.session, 'test')
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
        repo = pagure.lib.get_project(self.session, 'test')
        self.assertEqual(
            sorted([u.username for u in repo.users]), ['foo'])
        self.assertEqual(
            sorted([u.username for u in repo.committers]), [])
        self.assertEqual(
            sorted([u.username for u in repo.admins]), [])

        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 403)

        repo = pagure.lib.get_project(self.session, 'test')
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
        repo = pagure.lib.get_project(self.session, 'test')
        self.assertEqual(
            sorted([u.username for u in repo.users]), ['foo'])
        self.assertEqual(
            sorted([u.username for u in repo.committers]), ['foo'])
        self.assertEqual(
            sorted([u.username for u in repo.admins]), [])

        # Add comment
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.data)
        self.assertDictEqual(js_data, {'message': 'Comment added'})

        repo = pagure.lib.get_project(self.session, 'test')
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

        repo = pagure.lib.get_project(self.session, 'test')
        self.assertEqual(
            sorted([u.username for u in repo.users]), ['foo'])
        self.assertEqual(
            sorted([u.username for u in repo.committers]), ['foo'])
        self.assertEqual(
            sorted([u.username for u in repo.admins]), ['foo'])

        # Add comment
        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.data)
        self.assertDictEqual(js_data, {'message': 'Comment added'})

        repo = pagure.lib.get_project(self.session, 'test')
        issue = repo.issues[0]
        self.assertEqual(len(issue.comments), 2)

        # Check the @localonly
        before = pagure.APP.config['IP_ALLOWED_INTERNAL'][:]
        pagure.APP.config['IP_ALLOWED_INTERNAL'] = []

        output = self.app.put('/pv/ticket/comment/', data=data)
        self.assertEqual(output.status_code, 403)

        pagure.APP.config['IP_ALLOWED_INTERNAL'] = before[:]

    @patch('pagure.lib.notify.send_email')
    def test_mergeable_request_pull_FF(self, send_email):
        """ Test the mergeable_request_pull endpoint with a fast-forward
        merge.
        """
        send_email.return_value = True

        # Create a git repo to play with

        gitrepo = os.path.join(self.path, 'test.git')
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

        # Create a PR for these changes
        tests.create_projects(self.session)
        project = pagure.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
            requestfolder=None,
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
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/adduser')
            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Missing request identifier
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 404)

            # With all the desired information
            project = pagure.get_authorized_project(self.session, 'test')
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

            js_data = json.loads(output.data)
            self.assertDictEqual(js_data, exp)

    @patch('pagure.lib.notify.send_email')
    def test_mergeable_request_pull_no_change(self, send_email):
        """ Test the mergeable_request_pull endpoint when there are no
        changes to merge.
        """
        send_email.return_value = True

        # Create a git repo to play with

        gitrepo = os.path.join(self.path, 'test.git')
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
        project = pagure.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='master',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
            requestfolder=None,
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
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/adduser')
            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Missing request identifier
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 404)

            # With all the desired information
            project = pagure.get_authorized_project(self.session, 'test')
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

            js_data = json.loads(output.data)
            self.assertDictEqual(js_data, exp)

    @patch('pagure.lib.notify.send_email')
    def test_mergeable_request_pull_merge(self, send_email):
        """ Test the mergeable_request_pull endpoint when the changes can
        be merged with a merge commit.
        """
        send_email.return_value = True

        # Create a git repo to play with

        gitrepo = os.path.join(self.path, 'test.git')
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

        # Create a PR for these changes
        tests.create_projects(self.session)
        project = pagure.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
            requestfolder=None,
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
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/adduser')
            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Missing request identifier
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 404)

            # With all the desired information
            project = pagure.get_authorized_project(self.session, 'test')
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

            js_data = json.loads(output.data)
            self.assertDictEqual(js_data, exp)

    @patch('pagure.lib.notify.send_email')
    def test_mergeable_request_pull_conflicts(self, send_email):
        """ Test the mergeable_request_pull endpoint when the changes cannot
        be merged due to conflicts.
        """
        send_email.return_value = True

        # Create a git repo to play with

        gitrepo = os.path.join(self.path, 'test.git')
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

        # Create a PR for these changes
        tests.create_projects(self.session)
        project = pagure.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=project,
            branch_from='feature',
            repo_to=project,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
            requestfolder=None,
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
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/adduser')
            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Missing request identifier
            data = {
                'csrf_token': csrf_token,
            }
            output = self.app.post('/pv/pull-request/merge', data=data)
            self.assertEqual(output.status_code, 404)

            # With all the desired information
            project = pagure.get_authorized_project(self.session, 'test')
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

            js_data = json.loads(output.data)
            self.assertDictEqual(js_data, exp)

    def test_get_branches_of_commit(self):
        ''' Test the get_branches_of_commit from the internal API. '''
        tests.create_projects(self.session)
        tests.create_projects_git(self.path)

        user = tests.FakeUser()
        user.username = 'pingou'
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 200)
            csrf_token = output.data.split(
                b'name="csrf_token" type="hidden" value="')[1].split(b'">')[0]

        # No CSRF token
        data = {
            'repo': 'fakerepo',
            'commit_id': 'foo',
        }
        output = self.app.post('/pv/branches/commit/', data=data)
        self.assertEqual(output.status_code, 400)
        js_data = json.loads(output.data.decode('utf-8'))
        self.assertDictEqual(
            js_data,
            {u'code': u'ERROR', u'message': u'Invalid input submitted'}
        )

        # Invalid repo
        data = {
            'repo': 'fakerepo',
            'commit_id': 'foo',
            'csrf_token': csrf_token,
        }
        output = self.app.post('/pv/branches/commit/', data=data)
        self.assertEqual(output.status_code, 404)
        js_data = json.loads(output.data.decode('utf-8'))
        self.assertDictEqual(
            js_data,
            {
                u'code': u'ERROR',
                u'message': u'No repo found with the information provided'
            }
        )

        # Rigth repo, no commit
        data = {
            'repo': 'test',
            'csrf_token': csrf_token,
        }

        output = self.app.post('/pv/branches/commit/', data=data)
        self.assertEqual(output.status_code, 400)
        js_data = json.loads(output.data.decode('utf-8'))
        self.assertDictEqual(
            js_data,
            {u'code': u'ERROR', u'message': u'No commit id submitted'}
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
        js_data = json.loads(output.data.decode('utf-8'))
        self.assertDictEqual(
            js_data,
            {
                u'code': u'ERROR',
                u'message': u'No git repo found with the information provided'
            }
        )

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'test.git')
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
        js_data = json.loads(output.data.decode('utf-8'))
        self.assertDictEqual(
            js_data,
            {
                u'code': u'ERROR',
                u'message': 'This commit could not be found in this repo'
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
        js_data = json.loads(output.data.decode('utf-8'))
        self.assertDictEqual(
            js_data,
            {
                u'code': u'OK',
                u'branches': ['feature_branch'],
            }
        )


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskInternaltests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
