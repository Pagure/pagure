# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import datetime
import json
import unittest
import shutil
import sys
import tempfile
import os


import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskApiProjecttests(tests.Modeltests):
    """ Tests for the flask API of pagure for issue """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiProjecttests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.api.SESSION = self.session
        pagure.api.project.SESSION = self.session
        pagure.lib.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = os.path.join(self.path, 'repos')
        pagure.APP.config['FORK_FOLDER'] = os.path.join(
            self.path, 'forks')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            self.path, 'requests')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            self.path, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            self.path, 'docs')

        self.app = pagure.APP.test_client()

    def test_api_git_tags(self):
        """ Test the api_git_tags method of the flask api. """
        tests.create_projects(self.session)

        # Create a git repo to play with
        gitrepo = os.path.join(self.path, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        newpath = tempfile.mkdtemp(prefix='pagure-fork-test')
        repopath = os.path.join(newpath, 'test')
        clone_repo = pygit2.clone_repository(gitrepo, repopath)

        # Create a file in that git repo
        with open(os.path.join(repopath, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        clone_repo.index.add('sources')
        clone_repo.index.write()

        # Commits the files added
        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        clone_repo.create_commit(
            'refs/heads/master',  # the name of the reference to update
            author,
            committer,
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )
        refname = 'refs/heads/master:refs/heads/master'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        # Tag our first commit
        first_commit = repo.revparse_single('HEAD')
        tagger = pygit2.Signature('Alice Doe', 'adoe@example.com', 12347, 0)
        repo.create_tag(
            "0.0.1", first_commit.oid.hex, pygit2.GIT_OBJ_COMMIT, tagger,
            "Release 0.0.1")

        # Check tags
        output = self.app.get('/api/0/test/git/tags')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'tags': ['0.0.1'], 'total_tags': 1}
        )

        shutil.rmtree(newpath)

    def test_api_projects(self):
        """ Test the api_projects method of the flask api. """
        tests.create_projects(self.session)

        # Check before adding
        repo = pagure.lib.get_project(self.session, 'test')
        self.assertEqual(repo.tags, [])

        # Adding a tag
        output = pagure.lib.update_tags(
            self.session, repo, 'infra', 'pingou',
            ticketfolder=None)
        self.assertEqual(output, ['Tag added: infra'])

        # Check after adding
        repo = pagure.lib.get_project(self.session, 'test')
        self.assertEqual(len(repo.tags), 1)
        self.assertEqual(repo.tags_text, ['infra'])

        # Check the API
        output = self.app.get('/api/0/projects?tags=inf')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'error_code': 'ENOPROJECTS', 'error': 'No projects found'}
        )
        output = self.app.get('/api/0/projects?tags=infra')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['projects'][0]['date_created'] = "1436527638"
        self.assertDictEqual(
            data,
            {
              "total_projects": 1,
              "projects": [
                {
                  "date_created": "1436527638",
                  "description": "test project #1",
                  "id": 1,
                  "name": "test",
                  "namespace": None,
                  "parent": None,
                  "priorities": {},
                  "tags": ["infra"],
                  "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ]
            }
        )
        output = self.app.get('/api/0/projects?username=pingou')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['projects'][0]['date_created'] = "1436527638"
        data['projects'][1]['date_created'] = "1436527638"
        self.assertDictEqual(
            data,
            {
              "total_projects": 2,
              "projects": [
                {
                  "date_created": "1436527638",
                  "description": "test project #1",
                  "id": 1,
                  "name": "test",
                  "namespace": None,
                  "parent": None,
                  "priorities": {},
                  "tags": ["infra"],
                  "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                },
                {
                  "date_created": "1436527638",
                  "description": "test project #2",
                  "id": 2,
                  "name": "test2",
                  "namespace": None,
                  "parent": None,
                  "priorities": {},
                  "tags": [],
                  "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ]
            }
        )
        output = self.app.get('/api/0/projects?username=pingou&tags=infra')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        data['projects'][0]['date_created'] = "1436527638"
        self.assertDictEqual(
            data,
            {
              "total_projects": 1,
              "projects": [
                {
                  "date_created": "1436527638",
                  "description": "test project #1",
                  "id": 1,
                  "name": "test",
                  "namespace": None,
                  "parent": None,
                  "priorities": {},
                  "tags": ["infra"],
                  "user": {
                    "fullname": "PY C",
                    "name": "pingou"
                  }
                }
              ]
            }
        )

    @patch('pagure.lib.git.generate_gitolite_acls')
    def test_api_new_project(self, p_gga):
        """ Test the api_new_project method of the flask api. """
        p_gga.return_value = True

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'tickets'))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token foo_token'}

        # Invalid token
        output = self.app.post('/api/0/new', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        headers = {'Authorization': 'token aaabbbcccddd'}

        # No input
        output = self.app.post('/api/0/new', headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": "EINVALIDREQ",
            }
        )

        data = {
            'name': 'test',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/new', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": "EINVALIDREQ",
            }
        )

        data = {
            'name': 'test',
            'description': 'Just a small test project',
        }

        # Valid request but repo already exists
        output = self.app.post(
            '/api/0/new/', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "error": "The tickets repo \"test.git\" already exists",
                "error_code": "ENOCODE"
            }
        )

        data = {
            'name': 'test_42',
            'description': 'Just another small test project',
        }

        # Valid request
        output = self.app.post(
            '/api/0/new/', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {'message': 'Project "test_42" created'}
        )

    @patch('pagure.lib.git.generate_gitolite_acls')
    def test_api_fork_project(self, p_gga):
        """ Test the api_fork_project method of the flask api. """
        p_gga.return_value = True

        tests.create_projects(self.session)
        for folder in ['docs', 'tickets', 'requests', 'repos']:
            tests.create_projects_git(
                os.path.join(self.path, folder), bare=True)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        headers = {'Authorization': 'token foo_token'}

        # Invalid token
        output = self.app.post('/api/0/fork', headers=headers)
        self.assertEqual(output.status_code, 401)
        data = json.loads(output.data)
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.name,
                         data['error_code'])
        self.assertEqual(pagure.api.APIERROR.EINVALIDTOK.value, data['error'])

        headers = {'Authorization': 'token aaabbbcccddd'}

        # No input
        output = self.app.post('/api/0/fork', headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": "EINVALIDREQ",
            }
        )

        data = {
            'name': 'test',
        }

        # Incomplete request
        output = self.app.post(
            '/api/0/fork', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
              "error": "Invalid or incomplete input submited",
              "error_code": "EINVALIDREQ",
            }
        )

        data = {
            'repo': 'test',
        }

        # Valid request
        output = self.app.post(
            '/api/0/fork/', data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "message": "Repo \"test\" cloned to \"pingou/test\""
            }
        )

        data = {
            'repo': 'test',
        }

        # project already forked
        output = self.app.post(
            '/api/0/fork/', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "error": "Repo \"forks/pingou/test\" already exists",
                "error_code": "ENOCODE"
            }
        )

        data = {
            'repo': 'test',
            'username': 'pingou',
        }

        # Fork already exists
        output = self.app.post(
            '/api/0/fork/', data=data, headers=headers)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "error": "Repo \"forks/pingou/test\" already exists",
                "error_code": "ENOCODE"
            }
        )

        data = {
            'repo': 'test',
            'namespace': 'pingou',
        }

        # Repo does not exists
        output = self.app.post(
            '/api/0/fork/', data=data, headers=headers)
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "error": "Project not found",
                "error_code": "ENOPROJECT"
            }
        )

if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskApiProjecttests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
