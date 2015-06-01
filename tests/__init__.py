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


DB_PATH = 'sqlite:///:memory:'
FAITOUT_URL = 'http://209.132.184.152/faitout/'
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


@contextmanager
def user_set(APP, user):
    """ Set the provided user as fas_user in the provided application."""

    # Hack used to remove the before_request function set by
    # flask.ext.fas_openid.FAS which otherwise kills our effort to set a
    # flask.g.fas_user.
    from flask import appcontext_pushed, g
    APP.before_request_funcs[None] = []

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
        self.path = tempfile.mkdtemp(prefix='pagure-tests')
        self.gitrepo = None
        self.gitrepos = None

    # pylint: disable=C0103
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        # Clean up eventual git repo left in the present folder.
        for filename in os.listdir(HERE):
            filename = os.path.join(HERE, filename)
            if filename.endswith('.git') and os.path.isdir(filename):
                shutil.rmtree(filename)

        for folder in ['tickets', 'repos', 'forks', 'docs', 'requests']:
            folder = os.path.join(HERE, folder)
            if os.path.exists(folder):
                shutil.rmtree(folder)
            os.mkdir(folder)

        self.session = pagure.lib.model.create_tables(DB_PATH)

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

    # pylint: disable=C0103
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


# pylint: disable=R0903
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
    session.add(item)

    item = pagure.lib.model.Project(
        user_id=1,  # pingou
        name='test2',
        description='test project #2',
        hook_token='aaabbbddd',
    )
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


def create_acls(session):
    """ Create some acls for the tokens. """
    for acl in [
            'issue_create', 'pull_request_merge', 'pull_request_comment',
            'issue_change_status', 'issue_comment', 'pull_request_close',
            'pull_request_flag',
            ]:
        item = pagure.lib.model.ACL(
            name=acl,
            description=acl.replace('_', ' '),
        )
        session.add(item)

    session.commit()


def create_tokens_acl(session):
    """ Create some acls for the tokens. """
    for aclid in range(7):
        item = pagure.lib.model.TokenAcl(
            token_id='aaabbbcccddd',
            acl_id=aclid + 1,
        )
        session.add(item)

    session.commit()


def add_content_git_repo(folder):
    """ Create some content for the specified git repo. """
    if not os.path.exists(folder):
        os.makedirs(folder)
    repo = pygit2.init_repository(folder)

    # Create a file in that git repo
    with open(os.path.join(folder, 'sources'), 'w') as stream:
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
    if not os.path.exists(os.path.join(folder, subfolder)):
        os.makedirs(os.path.join(folder, subfolder))
    # Create a file in that git repo
    with open(os.path.join(folder, subfolder, 'file'), 'w') as stream:
        stream.write('foo\n bar\nbaz')
    repo.index.add(os.path.join(subfolder, 'file'))
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


def add_readme_git_repo(folder):
    """ Create a README file for the specified git repo. """
    if not os.path.exists(folder):
        os.makedirs(folder)
    repo = pygit2.init_repository(folder)

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
    with open(os.path.join(folder, 'README.rst'), 'w') as stream:
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


def add_commit_git_repo(folder, ncommits=10):
    """ Create some more commits for the specified git repo. """
    if not os.path.exists(folder):
        os.makedirs(folder)
    repo = pygit2.init_repository(folder)

    for index in range(ncommits):
        # Create a file in that git repo
        with open(os.path.join(folder, 'sources'), 'a') as stream:
            stream.write('Row %s\n' % index)
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
            'Add row %s to sources file' % index,
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            parents,
        )


def add_binary_git_repo(folder, filename):
    """ Create a fake image file for the specified git repo. """
    if not os.path.exists(folder):
        os.makedirs(folder)
    repo = pygit2.init_repository(folder)

    content = """<89>PNG^M
^Z
^@^@^@^MIHDR^@^@^@K^@^@^@K^H^F^@^@^@8Nzê^@^@^@^FbKGD^@ÿ^@ÿ^@ÿ ½§<93>^@^@^@  pHYs^@^@^M×^@^@^M×^AB(<9b>x^@^@^@^GtIM
E^GÞ
^N^U^F^[<88>]·<9c>^@^@  <8a>IDATxÚí<9c>ÛO^Tg^_Ç?3³»ì^B
<8b>®ËË<8b>X^NÕõ^EQÚ^Z­^Qc<82>^Pk5Úô¦iMÄ^[{×^K<9b>&^^Xÿ^A<8d>WM^S^SmÒ<8b>j¯Zê<8d>   6^QO^Dª¶´/Ö^M^T5^^*¼¬<9c>^Oî<8
1><99>÷<82>Y<8b>03;3»<83>hù&d óìÃÌw~§çûüf`^Q<8b>XÄ"^V±<88>^?:<84>^Er^N^R ª¿^K3ÎK<99>ñ3^EÈêïÿ8²ò<81> <90>¥C^T^Z<84>
É@^Tè^E<86>_g²²<80>^\<95>$^?<86>æ^\TI^[SI|åÉ^R<81>Õ*QNb^\èVÝõ<95>#Ë^M^T^C^Eóì-<83>ÀC þ*<90>%^B+<80>^?¿äÄñ^XèÏ¤¥e<9
a>,^O°^Vp-<90>l<9f>^@Â<99><8a>gR^FOÌ^O<84>TËZ(HZù3õ'íÉ2<81>^R Ìé+oll¤½½<9d>þþ~^TEAQ^T"<91>^HW¯^åèÑ£¸\º^F]^F¬|Ùn(^@
å@<9e>S^DíÚµ<8b>cÇ<8e>±iÓ¦<94>cãñ8Ç<8f>^_§©©<89>^[7nh^M^Y^Fþ|YdU8ET0^X¤©©<89>Í<9b>7[þî^W_|ÁÄÄ^DçÏ<9f>çÑ£G^Y#,<9d><
98>µ^RXæ^DQõõõ´¶¶RVfÏ³ÇÇÇyøð!<95><95><95>dggsïÞ½<99><87>½j^B^Z<99>¯<98>åW^CgÆ±sçN<9a><9b><9b>ÉÎÎ¶=G<þw<89>µaÃ^F^Z^
Z^Zf^OYag^UaÇ²<jÖË86nÜÈåË<97>§ã<83>`?B<9c>9sæï<85>¥¢^P^L^Fµ,Ì^O^LX©Ã$^[<96>XéTyðË/¿<90><9b><9b>kûûCCC<9c>:u<8a>ÁÁÁ
^WÈN^RöøñcFF^ð¾^B bVÉ°Z<^F<9c>*8¿ùæ^[<82>Á á<98>X,FKK^K'O<9e>äâÅ<8b>È²LAA^A[·n¥¸¸^XA^Pp»ÝºV¹wï^¾üòËÙ×^_PU<8c><8c>f
C7Pí^DQeee<84>ÃaÜn·î<98><9e><9e>^^¶oß®<95>Ý¦M^^T©®®¦®®<8e>©©)Ý1×¯_§½½}ö¡ßÍ¬%­¸S±SµÔ<9e>={^L<89>úé§<9f>¨¨¨Ð%
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
    with open(os.path.join(folder, filename), 'w') as stream:
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


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(Modeltests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
