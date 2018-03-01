# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.7']
import pkg_resources

import logging
import os
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
logging.basicConfig(stream=sys.stderr)

# Always enable performance counting for tests
os.environ['PAGURE_PERFREPO'] = 'true'

from contextlib import contextmanager
from datetime import date
from datetime import datetime
from datetime import timedelta
from functools import wraps

import mock
import pygit2

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.api
import pagure.flask_app
import pagure.lib
import pagure.lib.model
import pagure.perfrepo as perfrepo
from pagure.config import config as pagure_config
from pagure.lib.repo import PagureRepo

DB_PATH = None
FAITOUT_URL = 'http://faitout.fedorainfracloud.org/'
if os.environ.get('FAITOUT_URL'):
    FAITOUT_URL = os.environ.get('FAITOUT_URL')
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)))
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

PAGLOG = logging.getLogger('pagure')
PAGLOG.setLevel(logging.CRITICAL)
PAGLOG.handlers = []

CONFIG_TEMPLATE = """
GIT_FOLDER = '%(path)s/repos'
ENABLE_DOCS = True
ENABLE_TICKETS = True
REMOTE_GIT_FOLDER = '%(path)s/remotes'
ATTACHMENTS_FOLDER = '%(path)s/attachments'
DB_URL = '%(dburl)s'
ALLOW_PROJECT_DOWAIT = True
DEBUG = True
"""
MAX_NOFILE = 4096


LOG.info('BUILD_ID: %s', os.environ.get('BUILD_ID'))
if os.environ.get('BUILD_ID')or os.environ.get('FAITOUT_URL'):
    try:
        import requests
        req = requests.get('%s/new' % FAITOUT_URL)
        if req.status_code == 200:
            DB_PATH = req.text
            LOG.info('Using faitout at: %s', DB_PATH)
        else:
            LOG.info('faitout returned: %s : %s', req.status_code, req.text)
    except Exception as err:
        LOG.info('Error while querying faitout: %s', err)
        pass


WAIT_REGEX = re.compile("""var _url = '(\/wait\/[a-z0-9-]+\??.*)'""")
def get_wait_target(html):
    """ This parses the window.location out of the HTML for the wait page. """
    found = WAIT_REGEX.findall(html)
    if len(found) == 0:
        raise Exception("Not able to get wait target in %s" % html)
    return found[-1]


def create_maybe_waiter(method, getter):
    def maybe_waiter(*args, **kwargs):
        """ A wrapper for self.app.get()/.post() that will resolve wait's """
        result = method(*args, **kwargs)
        count = 0
        while 'We are waiting for your task to finish.' in result.data:
            # Resolve wait page
            target_url = get_wait_target(result.data)
            if count > 10:
                time.sleep(0.5)
            else:
                time.sleep(0.1)
            result = getter(target_url, follow_redirects=True)
            if count > 50:
                raise Exception('Had to wait too long')
        else:
            return result
    return maybe_waiter


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
        g.authenticated = True

    with appcontext_pushed.connected_to(handler, APP):
        yield

# In order to save time during local test execution, we create sqlite DB file
# only once and then we use a fresh copy of it for every test case (as opposed
# to creating DB file for every test case).
_, dbfile = tempfile.mkstemp()


def _create_db_entities(dbpath):
    session = pagure.lib.model.create_tables(
        dbpath, acls=pagure_config.get('ACLS', {}))

    # Create a couple of users
    item = pagure.lib.model.User(
        user='pingou',
        fullname='PY C',
        password='foo',
        default_email='bar@pingou.com',
    )
    session.add(item)
    item = pagure.lib.model.UserEmail(
        user_id=1,
        email='bar@pingou.com')
    session.add(item)
    item = pagure.lib.model.UserEmail(
        user_id=1,
        email='foo@pingou.com')
    session.add(item)

    item = pagure.lib.model.User(
        user='foo',
        fullname='foo bar',
        password='foo',
        default_email='foo@bar.com',
    )
    session.add(item)
    item = pagure.lib.model.UserEmail(
        user_id=2,
        email='foo@bar.com')
    session.add(item)

    session.commit()


def setUp():
    set_rlimit_nofiles()

    if DB_PATH:
        return

    dbpath = 'sqlite:///%s' % dbfile
    _create_db_entities(dbpath)


def tearDown():
    os.unlink(dbfile)


def set_rlimit_nofiles(limit=MAX_NOFILE):
    """
    Change the number of file descriptors allowed for this process, from
    1024 (the default) to the specified number.

    The test suite is leaking file descriptors, socket and a few others but
    we haven't managed to find the root cause so far, maybe in celery,
    maybe somewhere else :(
    In the mean time we're increasing the limit, it's very much a bandage
    in a wooden leg but at least it allows us to keep running the entire
    test suite.

    """
    try:
        msg = u'Setting RLIMIT_NOFILE to {max_files}'.format(
            max_files=limit)
        LOG.info(msg)
        resource.setrlimit(
            resource.RLIMIT_NOFILE, (limit, limit))
    except (resource.error, ValueError) as e:
        msg = u'Failed to raise the limit on the maximum number of ' \
              u'open file descriptors to {max_files}: {err}'
        LOG.warning(msg.format(max_files=limit, err=str(e)))
    finally:
        nofile = resource.getrlimit(resource.RLIMIT_NOFILE)
        LOG.info(
            u'RLIMIT_NOFILE is set to {nofile}'.format(nofile=nofile))


class SimplePagureTest(unittest.TestCase):
    """
    Simple Test class that does not set a broker/worker
    """

    @mock.patch('pagure.lib.notify.fedmsg_publish', mock.MagicMock())
    def __init__(self, method_name='runTest'):
        """ Constructor. """
        unittest.TestCase.__init__(self, method_name)
        self.session = None
        self.path = None
        self.gitrepo = None
        self.gitrepos = None

    def perfMaxWalks(self, max_walks, max_steps):
        """ Check that we have not performed too many walks/steps. """
        num_walks = 0
        num_steps = 0
        for reqstat in perfrepo.REQUESTS:
            for walk in reqstat['walks'].values():
                num_walks += 1
                num_steps += walk['steps']
        self.assertLessEqual(num_walks, max_walks,
                             '%s git repo walks performed, at most %s allowed'
                             % (num_walks, max_walks))
        self.assertLessEqual(num_steps, max_steps,
                             '%s git repo steps performed, at most %s allowed'
                             % (num_steps, max_steps))

    def perfReset(self):
        """ Reset perfrepo stats. """
        perfrepo.reset_stats()
        perfrepo.REQUESTS = []

    def setUp(self):
        self.perfReset()

        if self.path is not None:
            raise Exception('Double init?!')
        self.path = tempfile.mkdtemp(prefix='pagure-tests-path-')
        LOG.debug('Testdir: %s', self.path)
        for folder in ['repos', 'forks', 'releases', 'remotes', 'attachments']:
            os.mkdir(os.path.join(self.path, folder))

        if hasattr(pagure, 'REDIS') and pagure.REDIS:
            pagure.REDIS.connection_pool.disconnect()
            pagure.REDIS = None
        if hasattr(pagure.lib, 'REDIS') and pagure.lib.REDIS:
            pagure.lib.REDIS.connection_pool.disconnect()
            pagure.lib.REDIS = None

        if DB_PATH:
            self.dbpath = DB_PATH
            _create_db_entities(self.dbpath)
        else:
            self.dbpath = 'sqlite:///%s' % os.path.join(
                self.path, 'db.sqlite')
            shutil.copyfile(dbfile, self.dbpath[len('sqlite://'):])

        # Write a config file
        config_values = {'path': self.path, 'dburl': self.dbpath}
        with open(os.path.join(self.path, 'config'), 'w') as f:
            f.write(CONFIG_TEMPLATE % config_values)

        # Prevent unit-tests to send email, globally
        pagure_config['EMAIL_SEND'] = False
        pagure_config['TESTING'] = True
        pagure_config['GIT_FOLDER'] = gf = os.path.join(
            self.path, 'repos')
        pagure_config['TICKETS_FOLDER'] = os.path.join(
            gf, 'tickets')
        pagure_config['DOCS_FOLDER'] = os.path.join(
            gf, 'docs')
        pagure_config['REQUESTS_FOLDER'] = os.path.join(
            gf, 'requests')
        pagure_config['ATTACHMENTS_FOLDER'] = os.path.join(
            self.path, 'attachments')

        self._app = pagure.flask_app.create_app({'DB_URL': self.dbpath})
        # Remove the log handlers for the tests
        self._app.logger.handlers = []

        self.app = self._app.test_client()
        self.session = pagure.lib.create_session(self.dbpath)

    def tearDown(self):
        self.session.close()

        # Clear DB
        if self.dbpath.startswith('postgres'):
            if 'localhost' not in self.dbpath:
                db_name = self.dbpath.rsplit('/', 1)[1]
                requests.get('%s/clean/%s' % (FAITOUT_URL, db_name))

        # Remove testdir
        try:
            shutil.rmtree(self.path)
        except:
            # Sometimes there is a race condition that makes deleting the folder
            # fail during the first attempt. So just try a second time if that's
            # the case.
            shutil.rmtree(self.path)
        self.path = None

        del self.app
        del self._app

    def get_csrf(self, url='/new', output=None):
        """Retrieve a CSRF token from given URL."""
        if output is None:
            output = self.app.get(url)
            self.assertEqual(output.status_code, 200)

        return output.data.split(
            'name="csrf_token" type="hidden" value="')[1].split('">')[0]


class Modeltests(SimplePagureTest):
    """ Model tests. """

    def setUp(self):    # pylint: disable=invalid-name
        """ Set up the environnment, ran before every tests. """
        # Clean up test performance info
        super(Modeltests, self).setUp()

        # Create a broker
        broker_url = os.path.join(self.path, 'broker')

        self.broker = subprocess.Popen(
            ['/usr/bin/redis-server', '--unixsocket', broker_url, '--port',
             '0', '--loglevel', 'warning', '--logfile', '/dev/null'],
            stdout=None, stderr=None)
        self.broker.poll()
        if self.broker.returncode is not None:
            raise Exception('Broker failed to start')

        celery_broker_url = 'redis+socket://' + broker_url
        pagure_config['BROKER_URL'] = celery_broker_url
        reload(pagure.lib.tasks)
        reload(pagure.lib.tasks_services)

        # Start a worker
        # Using cocurrency 2 to test with some concurrency, but not be heavy
        # Using eventlet so that worker.terminate kills everything
        self.workerlog = open(os.path.join('.', 'worker.log'), 'w')
        celery_exec = 'celery'
        celery_env = os.environ.copy()
        celery_env.update({
            'PAGURE_BROKER_URL': celery_broker_url,
            'PAGURE_CONFIG': os.path.join(self.path, 'config'),
            'PYTHONPATH': '.'
        })
        celery_cwd = os.path.normpath(
            os.path.join(os.path.dirname(__file__),
            '..')
        )
        self.worker = subprocess.Popen(
            [celery_exec, '-A', 'pagure.lib.tasks', 'worker',
             '--loglevel=info', '--concurrency=2', '--pool=eventlet',
             '--without-gossip', '--without-mingle', '--quiet'],
            env=celery_env,
            cwd=celery_cwd,
            stdout=self.workerlog,
            stderr=self.workerlog)
        self.worker.poll()
        if self.worker.returncode is not None:
            raise Exception('Worker failed to start')
        # We could do the ping below in-process:
        # pagure.lib.tasks.conn.control.ping(timeout=0.1)
        # but if we try it, Python starts raising OSError
        # with too many open files. This is probably related
        # to https://github.com/celery/celery/issues/4465
        wait_start = time.time()
        while True:
            time.sleep(0.1)
            res = subprocess.call(
                [celery_exec, '-A', 'pagure.lib.tasks',
                 'inspect', '-t=0.1', 'ping'],
                env=celery_env,
                cwd=celery_cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if res == 0:
                break
            if time.time() - wait_start > 5:
                raise Exception('Worker failed to initialize in 5 seconds')

        self.app.get = create_maybe_waiter(self.app.get, self.app.get)
        self.app.post = create_maybe_waiter(self.app.post, self.app.get)

    def tearDown(self):     # pylint: disable=invalid-name
        """ Remove the test.db database if there is one. """
        super(Modeltests, self).tearDown()
        # Terminate worker and broker
        # We just send a SIGKILL (kill -9), since when the test finishes, we
        #  don't really care about the output of either worker or broker
        #  anymore
        self.worker.kill()
        self.worker.wait()
        self.worker = None
        self.workerlog.close()
        self.workerlog = None
        # close the connections to redis before killing redis,
        # otherwise we leak connections
        pagure.lib.tasks.conn.close()
        pagure.lib.tasks_services.conn.close()
        self.broker.kill()
        self.broker.wait()
        self.broker = None


class FakeGroup(object):    # pylint: disable=too-few-public-methods
    """ Fake object used to make the FakeUser object closer to the
    expectations.
    """

    def __init__(self, name):
        """ Constructor.
        :arg name: the name given to the name attribute of this object.
        """
        self.name = name
        self.group_type = 'cla'


class FakeUser(object):     # pylint: disable=too-few-public-methods
    """ Fake user used to test the fedocallib library. """

    def __init__(self, groups=None, username='username', cla_done=True, id=1):
        """ Constructor.
        :arg groups: list of the groups in which this fake user is
            supposed to be.
        """
        if isinstance(groups, basestring):
            groups = [groups]
        self.id = id
        self.groups = groups or []
        self.user = username
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

    item = pagure.lib.model.Project(
        user_id=1,  # pingou
        name='test3',
        description='namespaced test project',
        hook_token='aaabbbeee',
        namespace='somenamespace',
    )
    item.close_status = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
    session.add(item)

    session.commit()


def create_projects_git(folder, bare=False):
    """ Create some projects in the database. """
    repos = []
    for project in ['test.git', 'test2.git',
                    os.path.join('somenamespace', 'test3.git')]:
        repo_path = os.path.join(folder, project)
        repos.append(repo_path)
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
        pygit2.init_repository(repo_path, bare=bare)

    return repos


def create_tokens(session, user_id=1, project_id=1):
    """ Create some tokens for the project in the database. """
    item = pagure.lib.model.Token(
        id='aaabbbcccddd',
        user_id=user_id,
        project_id=project_id,
        expiration=datetime.utcnow() + timedelta(days=30)
    )
    session.add(item)

    item = pagure.lib.model.Token(
        id='foo_token',
        user_id=user_id,
        project_id=project_id,
        expiration=datetime.utcnow() + timedelta(days=30)
    )
    session.add(item)

    item = pagure.lib.model.Token(
        id='expired_token',
        user_id=user_id,
        project_id=project_id,
        expiration=datetime.utcnow() - timedelta(days=1)
    )
    session.add(item)

    session.commit()


def create_tokens_acl(session, token_id='aaabbbcccddd', acl_name=None):
    """ Create some ACLs for the token. If acl_name is not set, the token will
    have all the ACLs enabled.
    """
    if acl_name is None:
        for aclid in range(len(pagure_config['ACLS'])):
            token_acl = pagure.lib.model.TokenAcl(
                token_id=token_id,
                acl_id=aclid + 1,
            )
            session.add(token_acl)
    else:
        acl = session.query(pagure.lib.model.ACL).filter_by(
            name=acl_name).one()
        token_acl = pagure.lib.model.TokenAcl(
            token_id=token_id,
            acl_id=acl.id,
        )
        session.add(token_acl)

    session.commit()


def add_content_git_repo(folder, branch='master'):
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
        commit = repo.revparse_single(
            'HEAD' if branch == 'master' else branch)
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
        'refs/heads/%s' % branch,  # the name of the reference to update
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
        commit = repo.revparse_single(
            'HEAD' if branch == 'master' else branch)
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
        'refs/heads/%s' % branch,  # the name of the reference to update
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
    master_ref = repo.lookup_reference(
        'HEAD' if branch == 'master' else 'refs/heads/%s' % branch).resolve()
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


def add_commit_git_repo(folder, ncommits=10, filename='sources',
                        branch='master'):
    """ Create some more commits for the specified git repo. """
    if not os.path.exists(folder):
        os.makedirs(folder)
        pygit2.init_repository(folder, bare=True)

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
            'refs/heads/master',
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
    PagureRepo.push(ori_remote, 'HEAD:refs/heads/%s' % branch)

    shutil.rmtree(newfolder)


def add_content_to_git(folder, filename='sources', content='foo'):
    """ Create some more commits for the specified git repo. """
    if not os.path.exists(folder):
        os.makedirs(folder)
    brepo = pygit2.init_repository(folder, bare=True)

    newfolder = tempfile.mkdtemp(prefix='pagure-tests')
    repo = pygit2.clone_repository(folder, newfolder)

    # Create a file in that git repo
    with open(os.path.join(newfolder, filename), 'a') as stream:
        stream.write('%s\n' % content)
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
        'Add content to file %s' % (filename),
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
