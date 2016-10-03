# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.7']
import pkg_resources

import unittest
import shutil
import sys
import tempfile
import os

from datetime import date
from datetime import datetime
from datetime import timedelta
from functools import wraps

import pygit2

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib
import pagure.lib.model
from pagure.lib.repo import PagureRepo

DB_PATH = 'sqlite:///:memory:'
FAITOUT_URL = 'http://faitout.cloud.fedoraproject.org/faitout/'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)))


if os.environ.get('BUILD_ID'):
    try:
        import requests
        req = requests.get('%s/new' % FAITOUT_URL)
        if req.status_code == 200:
            DB_PATH = req.text
            print 'Using faitout at: %s' % DB_PATH
    except:
        pass

# Remove the log handlers for the tests
pagure.LOG.handlers = []


def reload_pagure(config_file=None):
    ''' Reload the different component of the pagure app.

    You may want to use this for some tests that require a specific
    configuration key to include or not a controller (for example the
    old_commit endpoint that's included or not depending on a value in
    the configuration file).
    '''

    # We need to reload pagure as otherwise the configuration file will
    # not be taken into account
    pagure.APP.view_functions = {}
    if config_file:
        os.environ['PAGURE_CONFIG'] = config_file
    else:
        if 'PAGURE_CONFIG' in os.environ:
            del os.environ['PAGURE_CONFIG']

    reload(pagure)
    reload(pagure.lib)
    reload(pagure.lib.model)
    reload(pagure.hooks)
    reload(pagure.hooks.mail)
    reload(pagure.hooks.irc)
    reload(pagure.hooks.fedmsg)
    reload(pagure.hooks.pagure_force_commit)
    reload(pagure.hooks.pagure_hook)
    reload(pagure.hooks.pagure_request_hook)
    reload(pagure.hooks.pagure_ticket_hook)
    reload(pagure.hooks.pagure_ci)
    reload(pagure.hooks.rtd)
    reload(pagure.api)
    reload(pagure.api.fork)
    reload(pagure.api.issue)
    reload(pagure.api.project)
    reload(pagure.api.user)
    reload(pagure.ui.admin)
    reload(pagure.ui.app)
    reload(pagure.ui.groups)
    reload(pagure.ui.repo)
    reload(pagure.ui.filters)
    reload(pagure.ui.plugins)
    reload(pagure.ui.issues)
    reload(pagure.ui.fork)


@contextmanager
def user_set(APP, user):
    """ Set the provided user as fas_user in the provided application."""

    # Hack used to remove the before_request function set by
    # flask.ext.fas_openid.FAS which otherwise kills our effort to set a
    # flask.g.fas_user.
    from flask import appcontext_pushed, g
    keep = []
    for meth in APP.before_request_funcs[None]:
        if 'flask_fas_openid.FAS' in str(meth):
            continue
        keep.append(meth)
    APP.before_request_funcs[None] = keep

    def handler(sender, **kwargs):
        g.fas_user = user
        g.fas_session_id = b'123'

    with appcontext_pushed.connected_to(handler, APP):
        yield


class Modeltests(unittest.TestCase):
    """ Model tests. """

    def __init__(self, method_name='runTest'):
        """ Constructor. """
        unittest.TestCase.__init__(self, method_name)
        self.session = None
        self.path = None
        self.gitrepo = None
        self.gitrepos = None

    # pylint: disable=invalid-name
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        # Clean up eventual git repo left in the present folder.
        self.path = tempfile.mkdtemp(prefix='pagure-tests')
        for folder in ['tickets', 'repos', 'forks', 'docs', 'requests',
                       'releases']:
            os.mkdir(os.path.join(self.path, folder))

        self.session = pagure.lib.model.create_tables(
            DB_PATH, acls=pagure.APP.config.get('ACLS', {}))

        # Create a couple of users
        item = pagure.lib.model.User(
            user='pingou',
            fullname='PY C',
            password='foo',
            default_email='bar@pingou.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=1,
            email='bar@pingou.com')
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=1,
            email='foo@pingou.com')
        self.session.add(item)

        item = pagure.lib.model.User(
            user='foo',
            fullname='foo bar',
            password='foo',
            default_email='foo@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=2,
            email='foo@bar.com')
        self.session.add(item)

        self.session.commit()

        # Prevent unit-tests to send email, globally
        pagure.APP.config['EMAIL_SEND'] = False

    # pylint: disable=invalid-name
    def tearDown(self):
        """ Remove the test.db database if there is one. """
        self.session.close()

        # Clear temp directory
        shutil.rmtree(self.path)

        # Clear DB
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        if DB_PATH.startswith('postgres'):
            if 'localhost' in DB_PATH:
                pagure.lib.model.drop_tables(DB_PATH, self.session.bind)
            else:
                db_name = DB_PATH.rsplit('/', 1)[1]
                requests.get('%s/clean/%s' % (FAITOUT_URL, db_name))


class FakeGroup(object):
    """ Fake object used to make the FakeUser object closer to the
    expectations.
    """

    def __init__(self, name):
        """ Constructor.
        :arg name: the name given to the name attribute of this object.
        """
        self.name = name
        self.group_type = 'cla'


# pylint: disable=too-few-public-methods
class FakeUser(object):
    """ Fake user used to test the fedocallib library. """

    def __init__(self, groups=[], username='username', cla_done=True):
        """ Constructor.
        :arg groups: list of the groups in which this fake user is
            supposed to be.
        """
        if isinstance(groups, basestring):
            groups = [groups]
        self.groups = groups
        self.username = username
        self.name = username
        self.email = 'foo@bar.com'
        self.approved_memberships = [
            FakeGroup('packager'),
            FakeGroup('design-team')
        ]
        self.dic = {}
        self.dic['timezone'] = 'Europe/Paris'
        self.login_time = datetime.utcnow()
        self.cla_done = cla_done

    def __getitem__(self, key):
        return self.dic[key]


def create_projects(session):
    """ Create some projects in the database. """
    item = pagure.lib.model.Project(
        user_id=1,  # pingou
        name='test',
        description='test project #1',
        hook_token='aaabbbccc',
    )
    item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
    session.add(item)

    item = pagure.lib.model.Project(
        user_id=1,  # pingou
        name='test2',
        description='test project #2',
        hook_token='aaabbbddd',
    )
    item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
    session.add(item)

    session.commit()


def create_projects_git(folder, bare=False):
    """ Create some projects in the database. """
    repos = []
    for project in ['test.git', 'test2.git']:
        repo_path = os.path.join(folder, project)
        repos.append(repo_path)
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
        pygit2.init_repository(repo_path, bare=bare)

    return repos


def create_tokens(session, user_id=1):
    """ Create some tokens for the project in the database. """
    item = pagure.lib.model.Token(
        id='aaabbbcccddd',
        user_id=user_id,
        project_id=1,
        expiration=datetime.utcnow() + timedelta(days=30)
    )
    session.add(item)

    item = pagure.lib.model.Token(
        id='foo_token',
        user_id=user_id,
        project_id=1,
        expiration=datetime.utcnow() + timedelta(days=30)
    )
    session.add(item)

    item = pagure.lib.model.Token(
        id='expired_token',
        user_id=user_id,
        project_id=1,
        expiration=datetime.utcnow() - timedelta(days=1)
    )
    session.add(item)

    session.commit()


def create_tokens_acl(session, token_id='aaabbbcccddd'):
    """ Create some acls for the tokens. """
    for aclid in range(len(pagure.APP.config['ACLS'])):
        item = pagure.lib.model.TokenAcl(
            token_id=token_id,
            acl_id=aclid + 1,
        )
        session.add(item)

    session.commit()


def add_content_git_repo(folder):
    """ Create some content for the specified git repo. """
    if not os.path.exists(folder):
        os.makedirs(folder)
    brepo = pygit2.init_repository(folder, bare=True)

    newfolder = tempfile.mkdtemp(prefix='pagure-tests')
    repo = pygit2.clone_repository(folder, newfolder)

    # Create a file in that git repo
    with open(os.path.join(newfolder, 'sources'), 'w') as stream:
        stream.write('foo\n bar')
    repo.index.add('sources')
    repo.index.write()

    parents = []
    commit = None
    try:
        commit = repo.revparse_single('HEAD')
    except KeyError:
        pass
    if commit:
        parents = [commit.oid.hex]

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
        parents,
    )

    parents = []
    commit = None
    try:
        commit = repo.revparse_single('HEAD')
    except KeyError:
        pass
    if commit:
        parents = [commit.oid.hex]

    subfolder = os.path.join('folder1', 'folder2')
    if not os.path.exists(os.path.join(newfolder, subfolder)):
        os.makedirs(os.path.join(newfolder, subfolder))
    # Create a file in that git repo
    with open(os.path.join(newfolder, subfolder, 'file'), 'w') as stream:
        stream.write('foo\n bar\nbaz')
    repo.index.add(os.path.join(subfolder, 'file'))
    with open(os.path.join(newfolder, subfolder, 'fileŠ'), 'w') as stream:
        stream.write('foo\n bar\nbaz')
    repo.index.add(os.path.join(subfolder, 'fileŠ'))
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
        'Add some directory and a file for more testing',
        # binary string representing the tree object ID
        tree,
        # list of binary strings representing parents of the new commit
        parents
    )

    # Push to origin
    ori_remote = repo.remotes[0]
    master_ref = repo.lookup_reference('HEAD').resolve()
    refname = '%s:%s' % (master_ref.name, master_ref.name)

    PagureRepo.push(ori_remote, refname)

    shutil.rmtree(newfolder)


def add_readme_git_repo(folder):
    """ Create a README file for the specified git repo. """
    if not os.path.exists(folder):
        os.makedirs(folder)
    brepo = pygit2.init_repository(folder, bare=True)

    newfolder = tempfile.mkdtemp(prefix='pagure-tests')
    repo = pygit2.clone_repository(folder, newfolder)

    content = """Pagure
======

:Author: Pierre-Yves Chibon <pingou@pingoured.fr>


Pagure is a light-weight git-centered forge based on pygit2.

Currently, Pagure offers a web-interface for git repositories, a ticket
system and possibilities to create new projects, fork existing ones and
create/merge pull-requests across or within projects.


Homepage: https://github.com/pypingou/pagure

Dev instance: http://209.132.184.222/ (/!\\ May change unexpectedly, it's a dev instance ;-))
"""

    parents = []
    commit = None
    try:
        commit = repo.revparse_single('HEAD')
    except KeyError:
        pass
    if commit:
        parents = [commit.oid.hex]

    # Create a file in that git repo
    with open(os.path.join(newfolder, 'README.rst'), 'w') as stream:
        stream.write(content)
    repo.index.add('README.rst')
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
        'Add a README file',
        # binary string representing the tree object ID
        tree,
        # list of binary strings representing parents of the new commit
        parents
    )

    # Push to origin
    ori_remote = repo.remotes[0]
    master_ref = repo.lookup_reference('HEAD').resolve()
    refname = '%s:%s' % (master_ref.name, master_ref.name)

    PagureRepo.push(ori_remote, refname)

    shutil.rmtree(newfolder)


def add_commit_git_repo(folder, ncommits=10, filename='sources'):
    """ Create some more commits for the specified git repo. """
    if not os.path.exists(folder):
        os.makedirs(folder)
    brepo = pygit2.init_repository(folder, bare=True)

    newfolder = tempfile.mkdtemp(prefix='pagure-tests')
    repo = pygit2.clone_repository(folder, newfolder)

    for index in range(ncommits):
        # Create a file in that git repo
        with open(os.path.join(newfolder, filename), 'a') as stream:
            stream.write('Row %s\n' % index)
        repo.index.add(filename)
        repo.index.write()

        parents = []
        commit = None
        try:
            commit = repo.revparse_single('HEAD')
        except KeyError:
            pass
        if commit:
            parents = [commit.oid.hex]

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
            'Add row %s to %s file' % (index, filename),
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            parents,
        )

    # Push to origin
    ori_remote = repo.remotes[0]
    master_ref = repo.lookup_reference('HEAD').resolve()
    refname = '%s:%s' % (master_ref.name, master_ref.name)

    PagureRepo.push(ori_remote, refname)

    shutil.rmtree(newfolder)


def add_binary_git_repo(folder, filename):
    """ Create a fake image file for the specified git repo. """
    if not os.path.exists(folder):
        os.makedirs(folder)
    brepo = pygit2.init_repository(folder, bare=True)

    newfolder = tempfile.mkdtemp(prefix='pagure-tests')
    repo = pygit2.clone_repository(folder, newfolder)

    content = b"""\x00\x00\x01\x00\x01\x00\x18\x18\x00\x00\x01\x00 \x00\x88
\t\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x18\x00x00\x00\x01\x00 \x00\x00\x00
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00
00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa7lM\x01\xa6kM\t\xa6kM\x01
\xa4fF\x04\xa2dE\x95\xa2cD8\xa1a
"""

    parents = []
    commit = None
    try:
        commit = repo.revparse_single('HEAD')
    except KeyError:
        pass
    if commit:
        parents = [commit.oid.hex]

    # Create a file in that git repo
    with open(os.path.join(newfolder, filename), 'wb') as stream:
        stream.write(content)
    repo.index.add(filename)
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
        'Add a fake image file',
        # binary string representing the tree object ID
        tree,
        # list of binary strings representing parents of the new commit
        parents
    )

    # Push to origin
    ori_remote = repo.remotes[0]
    master_ref = repo.lookup_reference('HEAD').resolve()
    refname = '%s:%s' % (master_ref.name, master_ref.name)

    PagureRepo.push(ori_remote, refname)

    shutil.rmtree(newfolder)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(Modeltests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
