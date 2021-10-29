# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import imp
import json
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
from io import open, StringIO

logging.basicConfig(stream=sys.stderr)

from bs4 import BeautifulSoup
from contextlib import contextmanager
from datetime import date
from datetime import datetime
from datetime import timedelta
from functools import wraps
from six.moves.urllib.parse import urlparse, parse_qs

import mock
import pygit2
import redis
import six

from bs4 import BeautifulSoup
from celery.app.task import EagerResult
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session

if six.PY2:
    # Always enable performance counting for tests
    os.environ["PAGURE_PERFREPO"] = "true"

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure
import pagure.api
from pagure.api.ci import jenkins
import pagure.flask_app
import pagure.lib.git
import pagure.lib.login
import pagure.lib.model
import pagure.lib.query
import pagure.lib.tasks_mirror
import pagure.perfrepo as perfrepo
from pagure.config import config as pagure_config, reload_config
from pagure.lib.repo import PagureRepo

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)))
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

PAGLOG = logging.getLogger("pagure")
PAGLOG.setLevel(logging.CRITICAL)
PAGLOG.handlers = []

if "PYTHONPATH" not in os.environ:
    os.environ["PYTHONPATH"] = os.path.normpath(os.path.join(HERE, "../"))

CONFIG_TEMPLATE = """
GIT_FOLDER = '%(path)s/repos'
ENABLE_DOCS = %(enable_docs)s
ENABLE_TICKETS = %(enable_tickets)s
REMOTE_GIT_FOLDER = '%(path)s/remotes'
DB_URL = '%(dburl)s'
ALLOW_PROJECT_DOWAIT = True
PAGURE_CI_SERVICES = ['jenkins']
EMAIL_SEND = False
TESTING = True
GIT_FOLDER = '%(path)s/repos'
REQUESTS_FOLDER = '%(path)s/repos/requests'
TICKETS_FOLDER = %(tickets_folder)r
DOCS_FOLDER = %(docs_folder)r
REPOSPANNER_PSEUDO_FOLDER = '%(path)s/repos/pseudo'
ATTACHMENTS_FOLDER = '%(path)s/attachments'
BROKER_URL = 'redis+socket://%(global_path)s/broker'
CELERY_CONFIG = {
    "task_always_eager": True,
    #"task_eager_propagates": True,
}
GIT_AUTH_BACKEND = '%(authbackend)s'
TEST_AUTH_STATUS = '%(path)s/testauth_status.json'
REPOBRIDGE_BINARY = '%(repobridge_binary)s'
REPOSPANNER_NEW_REPO = %(repospanner_new_repo)s
REPOSPANNER_NEW_REPO_ADMIN_OVERRIDE = %(repospanner_admin_override)s
REPOSPANNER_NEW_FORK = %(repospanner_new_fork)s
REPOSPANNER_ADMIN_MIGRATION = %(repospanner_admin_migration)s
REPOSPANNER_REGIONS = {
    'default': {'url': 'https://repospanner.localhost.localdomain:%(repospanner_gitport)s',
                'repo_prefix': 'pagure/',
                'hook': None,
                'ca': '%(path)s/repospanner/pki/ca.crt',
                'admin_cert': {'cert': '%(path)s/repospanner/pki/admin.crt',
                               'key': '%(path)s/repospanner/pki/admin.key'},
                'push_cert': {'cert': '%(path)s/repospanner/pki/pagure.crt',
                              'key': '%(path)s/repospanner/pki/pagure.key'}}
}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%%(asctime)s [%%(levelname)s] %%(name)s: %%(message)s"
        },
    },
    "handlers": {
        "console": {
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    # The root logger configuration; this is a catch-all configuration
    # that applies to all log messages not handled by a different logger
    "root": {"level": "WARN", "handlers": ["console"]},
}

NOGITHOOKS = %(nogithooks)s
"""
# The Celery docs warn against using task_always_eager:
# http://docs.celeryproject.org/en/latest/userguide/testing.html
# but that warning is only valid when testing the async nature of the task, not
# what the task actually does.


LOG.info("BUILD_ID: %s", os.environ.get("BUILD_ID"))


WAIT_REGEX = re.compile(r"""var _url = '(\/wait\/[a-z0-9-]+\??.*)'""")


def get_wait_target(html):
    """ This parses the window.location out of the HTML for the wait page. """
    found = WAIT_REGEX.findall(html)
    if len(found) == 0:
        raise Exception("Not able to get wait target in %s" % html)
    return found[-1]


def get_post_target(html):
    """ This parses the wait page form to get the POST url. """
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find(id="waitform")
    if not form:
        raise Exception("Not able to get the POST url in %s" % html)
    return form.get("action")


def get_post_args(html):
    """ This parses the wait page for the hidden arguments of the form. """
    soup = BeautifulSoup(html, "html.parser")
    output = {}
    inputs = soup.find_all("input")
    if not inputs:
        raise Exception("Not able to get the POST arguments in %s" % html)
    for inp in inputs:
        if inp.get("type") == "hidden":
            output[inp.get("name")] = inp.get("value")
    return output


def create_maybe_waiter(method, getter):
    def maybe_waiter(*args, **kwargs):
        """ A wrapper for self.app.get()/.post() that will resolve wait's """
        result = method(*args, **kwargs)

        # Handle the POST wait case
        form_url = None
        form_args = None
        try:
            result_text = result.get_data(as_text=True)
        except UnicodeDecodeError:
            return result
        if 'id="waitform"' in result_text:
            form_url = get_post_target(result_text)
            form_args = get_post_args(result_text)
            form_args["csrf_token"] = result_text.split(
                'name="csrf_token" type="hidden" value="'
            )[1].split('">')[0]

        count = 0
        while "We are waiting for your task to finish." in result_text:
            # Resolve wait page
            target_url = get_wait_target(result_text)
            if count > 10:
                time.sleep(0.5)
            else:
                time.sleep(0.1)
            result = getter(target_url, follow_redirects=True)
            try:
                result_text = result.get_data(as_text=True)
            except UnicodeDecodeError:
                return result
            if count > 50:
                raise Exception("Had to wait too long")
        else:
            if form_url and form_args:
                return method(form_url, data=form_args, follow_redirects=True)
            return result

    return maybe_waiter


@contextmanager
def user_set(APP, user, keep_get_user=False):
    """ Set the provided user as fas_user in the provided application."""

    # Hack used to remove the before_request function set by
    # flask.ext.fas_openid.FAS which otherwise kills our effort to set a
    # flask.g.fas_user.
    from flask import appcontext_pushed, g

    keep = []
    for meth in APP.before_request_funcs[None]:
        if "flask_fas_openid.FAS" in str(meth):
            continue
        keep.append(meth)
    APP.before_request_funcs[None] = keep

    def handler(sender, **kwargs):
        g.fas_user = user
        g.fas_session_id = b"123"
        g.authenticated = True

    old_get_user = pagure.flask_app._get_user
    if not keep_get_user:
        pagure.flask_app._get_user = mock.MagicMock(
            return_value=pagure.lib.model.User()
        )

    with appcontext_pushed.connected_to(handler, APP):
        yield

    pagure.flask_app._get_user = old_get_user


def create_user(session, username, fullname, emails):
    """Create an user with the provided information.
    Note that `emails` should be a list of emails.
    """
    user = pagure.lib.model.User(
        user=username,
        fullname=fullname,
        password=pagure.lib.login.generate_hashed_value("foo"),
        default_email=emails[0],
    )
    session.add(user)
    session.flush()
    for email in emails:
        item = pagure.lib.model.UserEmail(user_id=user.id, email=email)
        session.add(item)
    session.commit()


def _populate_db(session):
    # Create a couple of users
    create_user(
        session, "pingou", "PY C", ["bar@pingou.com", "foo@pingou.com"]
    )
    create_user(session, "foo", "foo bar", ["foo@bar.com"])


class SimplePagureTest(unittest.TestCase):
    """
    Simple Test class that does not set a broker/worker
    """

    populate_db = True
    config_values = {}

    def store_eager_results(self, *args, **kwargs):
        """A wrapper for EagerResult that stores the instance."""
        result = EagerResult(*args, **kwargs)
        self.results[result.id] = result
        return result

    @mock.patch("pagure.lib.notify.fedmsg_publish", mock.MagicMock())
    def __init__(self, method_name="runTest"):
        """ Constructor. """
        unittest.TestCase.__init__(self, method_name)
        self.session = None
        self.path = None
        self.gitrepo = None
        self.gitrepos = None
        self.results = {}

    def perfMaxWalks(self, max_walks, max_steps):
        """ Check that we have not performed too many walks/steps. """
        num_walks = 0
        num_steps = 0
        for reqstat in perfrepo.REQUESTS:
            for walk in reqstat["walks"].values():
                num_walks += 1
                num_steps += walk["steps"]
        self.assertLessEqual(
            num_walks,
            max_walks,
            "%s git repo walks performed, at most %s allowed"
            % (num_walks, max_walks),
        )
        self.assertLessEqual(
            num_steps,
            max_steps,
            "%s git repo steps performed, at most %s allowed"
            % (num_steps, max_steps),
        )

    def perfReset(self):
        """ Reset perfrepo stats. """
        perfrepo.reset_stats()
        perfrepo.REQUESTS = []

    def setUp(self):

        self.dbfolder = tempfile.mkdtemp(prefix="pagure-tests-")
        self.dbpath = "sqlite:///%s/db.sqlite" % self.dbfolder
        session = pagure.lib.model.create_tables(
            self.dbpath,
            acls=pagure_config.get("ACLS", {}),
        )
        self.db_session = session

        # Create a broker
        broker_url = os.path.join(self.dbfolder, "broker")

        self.broker = broker = subprocess.Popen(
            [
                "/usr/bin/redis-server",
                "--unixsocket",
                broker_url,
                "--port",
                "0",
                "--loglevel",
                "warning",
                "--logfile",
                "/dev/null",
            ],
            stdout=None,
            stderr=None,
        )
        broker.poll()
        if broker.returncode is not None:
            raise Exception("Broker failed to start")
        self.broker_client = redis.Redis(unix_socket_path=broker_url)

        # Store the EagerResults to be able to retrieve them later
        self.eg_patcher = mock.patch("celery.app.task.EagerResult")
        eg_mock = self.eg_patcher.start()
        eg_mock.side_effect = self.store_eager_results

        self.perfReset()

        self.path = tempfile.mkdtemp(prefix="pagure-tests-path-")

        LOG.debug("Testdir: %s", self.path)
        for folder in ["repos", "forks", "releases", "remotes", "attachments"]:
            os.mkdir(os.path.join(self.path, folder))

        if hasattr(pagure.lib.query, "REDIS") and pagure.lib.query.REDIS:
            pagure.lib.query.REDIS.connection_pool.disconnect()
            pagure.lib.query.REDIS = None

        # Database
        self._prepare_db()

        # Write a config file
        config_values = {
            "path": self.path,
            "dburl": self.dbpath,
            "enable_docs": True,
            "docs_folder": "%s/repos/docs" % self.path,
            "enable_tickets": True,
            "tickets_folder": "%s/repos/tickets" % self.path,
            "global_path": self.dbfolder,
            "authbackend": "gitolite3",
            "repobridge_binary": "/usr/libexec/repobridge",
            "repospanner_gitport": str(8443 + sys.version_info.major),
            "repospanner_new_repo": "None",
            "repospanner_admin_override": "False",
            "repospanner_new_fork": "True",
            "repospanner_admin_migration": "False",
            "nogithooks": False,
        }
        config_values.update(self.config_values)
        self.config_values = config_values
        self.config_path = os.path.join(self.path, "config")
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w") as f:
                f.write(CONFIG_TEMPLATE % self.config_values)
        os.environ["PAGURE_CONFIG"] = self.config_path
        pagure_config.update(reload_config())

        imp.reload(pagure.lib.tasks)
        imp.reload(pagure.lib.tasks_mirror)
        imp.reload(pagure.lib.tasks_services)

        self._app = pagure.flask_app.create_app({"DB_URL": self.dbpath})

        self.app = self._app.test_client()
        self.gr_patcher = mock.patch("pagure.lib.tasks.get_result")
        gr_mock = self.gr_patcher.start()
        gr_mock.side_effect = lambda tid: self.results[tid]

        # Refresh the DB session
        self.session = pagure.lib.query.create_session(self.dbpath)

    def tearDown(self):
        self.gr_patcher.stop()
        self.session.rollback()
        self._clear_database()

        self.db_session.close()
        self.eg_patcher.stop()
        self.broker.kill()
        self.broker.wait()

        # Remove testdir
        try:
            shutil.rmtree(self.path)
        except:
            # Sometimes there is a race condition that makes deleting the folder
            # fail during the first attempt. So just try a second time if that's
            # the case.
            shutil.rmtree(self.path)
        try:
            shutil.rmtree(self.dbfolder)
        except:
            pass

        self.path = None
        self.dbpath = None

        del self.app
        del self._app

    def shortDescription(self):
        doc = self.__str__() + ": " + self._testMethodDoc
        return doc or None

    def _prepare_db(self):
        self.session = self.db_session
        pagure.lib.model.create_default_status(
            self.session, acls=pagure_config.get("ACLS", {})
        )
        if self.populate_db:
            _populate_db(self.session)

    def _clear_database(self):
        tables = reversed(pagure.lib.model_base.BASE.metadata.sorted_tables)
        # This seems to be needed to load the tables in memory or so and
        # without this, clearing the database fails with the error:
        # ``sqlite3.OperationalError: foreign key mismatch - "board_statuses"
        # referencing "boards"``
        # for reasons that are really not quite understood...
        [t for t in tables]
        if self.dbpath.startswith("postgresql"):
            self.session.execute(
                "TRUNCATE %s CASCADE" % ", ".join([t.name for t in tables])
            )
        elif self.dbpath.startswith("sqlite"):
            for table in tables:
                self.session.execute("DELETE FROM %s" % table.name)
        elif self.dbpath.startswith("mysql"):
            self.session.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in tables:
                self.session.execute("TRUNCATE %s" % table.name)
            self.session.execute("SET FOREIGN_KEY_CHECKS = 1")
        self.session.commit()

    def set_auth_status(self, value):
        """ Set the return value for the test auth """
        with open(
            os.path.join(self.path, "testauth_status.json"), "w"
        ) as statusfile:
            statusfile.write(six.u(json.dumps(value)))

    def get_csrf(self, url="/new", output=None):
        """Retrieve a CSRF token from given URL."""
        if output is None:
            output = self.app.get(url)
            self.assertEqual(output.status_code, 200)

        return (
            output.get_data(as_text=True)
            .split('name="csrf_token" type="hidden" value="')[1]
            .split('">')[0]
        )

    def get_wtforms_version(self):
        """Returns the wtforms version as a tuple."""
        import wtforms

        wtforms_v = wtforms.__version__.split(".")
        for idx, val in enumerate(wtforms_v):
            try:
                val = int(val)
            except ValueError:
                pass
            wtforms_v[idx] = val
        return tuple(wtforms_v)

    def get_arrow_version(self):
        """ Returns the arrow version as a tuple."""
        import arrow

        arrow_v = arrow.__version__.split(".")
        for idx, val in enumerate(arrow_v):
            try:
                val = int(val)
            except ValueError:
                pass
            arrow_v[idx] = val
        return tuple(arrow_v)

    def assertURLEqual(self, url_1, url_2):
        url_parsed_1 = list(urlparse(url_1))
        url_parsed_1[4] = parse_qs(url_parsed_1[4])
        url_parsed_2 = list(urlparse(url_2))
        url_parsed_2[4] = parse_qs(url_parsed_2[4])
        return self.assertListEqual(url_parsed_1, url_parsed_2)

    def assertJSONEqual(self, json_1, json_2):
        return self.assertEqual(json.loads(json_1), json.loads(json_2))


class Modeltests(SimplePagureTest):
    """ Model tests. """

    def setUp(self):  # pylint: disable=invalid-name
        """ Set up the environnment, ran before every tests. """
        # Clean up test performance info
        super(Modeltests, self).setUp()
        self.app.get = create_maybe_waiter(self.app.get, self.app.get)
        self.app.post = create_maybe_waiter(self.app.post, self.app.get)

        # Refresh the DB session
        self.session = pagure.lib.query.create_session(self.dbpath)

    def tearDown(self):  # pylint: disable=invalid-name
        """ Remove the test.db database if there is one. """
        self.broker_client.flushall()
        super(Modeltests, self).tearDown()

    def create_project_full(self, projectname, extra=None):
        """Create a project via the API.

        This makes sure that the repo is fully setup the way a normal new
        project would be, with hooks and all setup.
        """

        headers = {"Authorization": "token aaabbbcccddd"}
        data = {"name": projectname, "description": "A test repo"}
        if extra:
            data.update(extra)

        # Valid request
        output = self.app.post("/api/0/new/", data=data, headers=headers)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.get_data(as_text=True))
        self.assertDictEqual(
            data, {"message": 'Project "%s" created' % projectname}
        )


class FakeGroup(object):  # pylint: disable=too-few-public-methods
    """Fake object used to make the FakeUser object closer to the
    expectations.
    """

    def __init__(self, name):
        """Constructor.
        :arg name: the name given to the name attribute of this object.
        """
        self.name = name
        self.group_type = "cla"


class FakeUser(object):  # pylint: disable=too-few-public-methods
    """ Fake user used to test the fedocallib library. """

    def __init__(
        self, groups=None, username="username", cla_done=True, id=None
    ):
        """Constructor.
        :arg groups: list of the groups in which this fake user is
            supposed to be.
        """
        if isinstance(groups, six.string_types):
            groups = [groups]
        self.id = id
        self.groups = groups or []
        self.user = username
        self.username = username
        self.name = username
        self.email = "foo@bar.com"
        self.default_email = "foo@bar.com"

        self.approved_memberships = [
            FakeGroup("packager"),
            FakeGroup("design-team"),
        ]
        self.dic = {}
        self.dic["timezone"] = "Europe/Paris"
        self.login_time = datetime.utcnow()
        self.cla_done = cla_done

    def __getitem__(self, key):
        return self.dic[key]


def create_locks(session, project):
    for ltype in ("WORKER", "WORKER_TICKET", "WORKER_REQUEST"):
        lock = pagure.lib.model.ProjectLock(
            project_id=project.id, lock_type=ltype
        )
        session.add(lock)


def create_projects(session, is_fork=False, user_id=1, hook_token_suffix=""):
    """ Create some projects in the database. """
    item = pagure.lib.model.Project(
        user_id=user_id,  # pingou
        name="test",
        is_fork=is_fork,
        parent_id=1 if is_fork else None,
        description="test project #1",
        hook_token="aaabbbccc" + hook_token_suffix,
    )
    item.close_status = ["Invalid", "Insufficient data", "Fixed", "Duplicate"]
    session.add(item)
    session.flush()
    create_locks(session, item)

    item = pagure.lib.model.Project(
        user_id=user_id,  # pingou
        name="test2",
        is_fork=is_fork,
        parent_id=2 if is_fork else None,
        description="test project #2",
        hook_token="aaabbbddd" + hook_token_suffix,
    )
    item.close_status = ["Invalid", "Insufficient data", "Fixed", "Duplicate"]
    session.add(item)
    session.flush()
    create_locks(session, item)

    item = pagure.lib.model.Project(
        user_id=user_id,  # pingou
        name="test3",
        is_fork=is_fork,
        parent_id=3 if is_fork else None,
        description="namespaced test project",
        hook_token="aaabbbeee" + hook_token_suffix,
        namespace="somenamespace",
    )
    item.close_status = ["Invalid", "Insufficient data", "Fixed", "Duplicate"]
    session.add(item)
    session.flush()
    create_locks(session, item)
    session.commit()


def create_projects_git(folder, bare=False):
    """ Create some projects in the database. """
    repos = []
    for project in [
        "test.git",
        "test2.git",
        os.path.join("somenamespace", "test3.git"),
    ]:
        repo_path = os.path.join(folder, project)
        repos.append(repo_path)
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
        pygit2.init_repository(repo_path, bare=bare)
    return repos


def create_tokens(session, user_id=1, project_id=1, suffix=None):
    """ Create some tokens for the project in the database. """
    token = "aaabbbcccddd"
    if suffix:
        token += suffix
    item = pagure.lib.model.Token(
        id=token,
        user_id=user_id,
        project_id=project_id,
        expiration=datetime.utcnow() + timedelta(days=30),
    )
    session.add(item)

    token = "foo_token"
    if suffix:
        token += suffix
    item = pagure.lib.model.Token(
        id=token,
        user_id=user_id,
        project_id=project_id,
        expiration=datetime.utcnow() + timedelta(days=30),
    )
    session.add(item)

    token = "expired_token"
    if suffix:
        token += suffix
    item = pagure.lib.model.Token(
        id=token,
        user_id=user_id,
        project_id=project_id,
        expiration=datetime.utcnow() - timedelta(days=1),
    )
    session.add(item)
    session.commit()


def create_tokens_acl(session, token_id="aaabbbcccddd", acl_name=None):
    """Create some ACLs for the token. If acl_name is not set, the token will
    have all the ACLs enabled.
    """
    if acl_name is None:
        for aclid in range(len(pagure_config["ACLS"])):
            token_acl = pagure.lib.model.TokenAcl(
                token_id=token_id, acl_id=aclid + 1
            )
            session.add(token_acl)
    else:
        acl = (
            session.query(pagure.lib.model.ACL).filter_by(name=acl_name).one()
        )
        token_acl = pagure.lib.model.TokenAcl(token_id=token_id, acl_id=acl.id)
        session.add(token_acl)

    session.commit()


def _clone_and_top_commits(folder, branch, branch_ref=False):
    """Clone the repository, checkout the specified branch and return
    the top commit of that branch if there is one.
    Returns the repo, the path to the clone and the top commit(s) in a tuple
    or the repo, the path to the clone and the reference to the branch
    object if branch_ref is True.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    brepo = pygit2.init_repository(folder, bare=True)

    newfolder = tempfile.mkdtemp(prefix="pagure-tests")
    repo = pygit2.clone_repository(folder, newfolder)

    branch_ref_obj = None
    if "origin/%s" % branch in repo.listall_branches(pygit2.GIT_BRANCH_ALL):
        branch_ref_obj = pagure.lib.git.get_branch_ref(repo, branch)
        repo.checkout(branch_ref_obj)

    if branch_ref:
        return (repo, newfolder, branch_ref_obj)

    parents = []
    commit = None
    try:
        if branch_ref_obj:
            commit = repo[branch_ref_obj.peel().hex]
        else:
            commit = repo.revparse_single("HEAD")
    except KeyError:
        pass
    if commit:
        parents = [commit.oid.hex]

    return (repo, newfolder, parents)


def add_content_git_repo(folder, branch="master", append=None):
    """ Create some content for the specified git repo. """
    repo, newfolder, parents = _clone_and_top_commits(folder, branch)

    # Create a file in that git repo
    filename = os.path.join(newfolder, "sources")
    content = "foo\n bar"
    if os.path.exists(filename):
        content = "foo\n bar\nbaz"
    if append:
        content += append
    with open(filename, "w") as stream:
        stream.write(content)
    repo.index.add("sources")
    repo.index.write()

    # Commits the files added
    tree = repo.index.write_tree()
    author = pygit2.Signature("Alice Author", "alice@authors.tld")
    committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
    commit = repo.create_commit(
        "refs/heads/%s" % branch,  # the name of the reference to update
        author,
        committer,
        "Add sources file for testing",
        # binary string representing the tree object ID
        tree,
        # list of binary strings representing parents of the new commit
        parents,
    )

    if commit:
        parents = [commit.hex]

    subfolder = os.path.join("folder1", "folder2")
    if not os.path.exists(os.path.join(newfolder, subfolder)):
        os.makedirs(os.path.join(newfolder, subfolder))
    # Create a file in that git repo
    with open(os.path.join(newfolder, subfolder, "file"), "w") as stream:
        stream.write("foo\n bar\nbaz")
    repo.index.add(os.path.join(subfolder, "file"))
    with open(os.path.join(newfolder, subfolder, "fileŠ"), "w") as stream:
        stream.write("foo\n bar\nbaz")
    repo.index.add(os.path.join(subfolder, "fileŠ"))
    repo.index.write()

    # Commits the files added
    tree = repo.index.write_tree()
    author = pygit2.Signature("Alice Author", "alice@authors.tld")
    committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
    commit = repo.create_commit(
        "refs/heads/%s" % branch,  # the name of the reference to update
        author,
        committer,
        "Add some directory and a file for more testing",
        # binary string representing the tree object ID
        tree,
        # list of binary strings representing parents of the new commit
        parents,
    )

    # Push to origin
    ori_remote = repo.remotes[0]
    master_ref = repo.lookup_reference(
        "HEAD" if branch == "master" else "refs/heads/%s" % branch
    ).resolve()
    refname = "%s:%s" % (master_ref.name, master_ref.name)

    PagureRepo.push(ori_remote, refname)

    shutil.rmtree(newfolder)


def add_readme_git_repo(folder, readme_name="README.rst", branch="master"):
    """ Create a README file for the specified git repo. """
    repo, newfolder, parents = _clone_and_top_commits(folder, branch)

    if readme_name == "README.rst":
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
    else:
        content = (
            """Pagure
======

This is a placeholder """
            + readme_name
            + """
that should never get displayed on the website if there is a README.rst in the repo.
"""
        )

    # Create a file in that git repo
    with open(os.path.join(newfolder, readme_name), "w") as stream:
        stream.write(content)
    repo.index.add(readme_name)
    repo.index.write()

    # Commits the files added
    tree = repo.index.write_tree()
    author = pygit2.Signature("Alice Author", "alice@authors.tld")
    committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
    branch_ref = "refs/heads/%s" % branch
    repo.create_commit(
        branch_ref,  # the name of the reference to update
        author,
        committer,
        "Add a README file",
        # binary string representing the tree object ID
        tree,
        # list of binary strings representing parents of the new commit
        parents,
    )

    # Push to origin
    ori_remote = repo.remotes[0]

    PagureRepo.push(ori_remote, "%s:%s" % (branch_ref, branch_ref))

    shutil.rmtree(newfolder)


def add_commit_git_repo(
    folder, ncommits=10, filename="sources", branch="master", symlink_to=None
):
    """ Create some more commits for the specified git repo. """
    repo, newfolder, branch_ref_obj = _clone_and_top_commits(
        folder, branch, branch_ref=True
    )

    for index in range(ncommits):
        # Create a file in that git repo
        if symlink_to:
            os.symlink(symlink_to, os.path.join(newfolder, filename))
        else:
            with open(os.path.join(newfolder, filename), "a") as stream:
                stream.write("Row %s\n" % index)
        repo.index.add(filename)
        repo.index.write()

        parents = []
        commit = None
        try:
            if branch_ref_obj:
                commit = repo[branch_ref_obj.peel().hex]
            else:
                commit = repo.revparse_single("HEAD")
        except (KeyError, AttributeError):
            pass
        if commit:
            parents = [commit.oid.hex]

        # Commits the files added
        tree = repo.index.write_tree()
        author = pygit2.Signature("Alice Author", "alice@authors.tld")
        committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
        branch_ref = "refs/heads/%s" % branch
        repo.create_commit(
            branch_ref,
            author,
            committer,
            "Add row %s to %s file" % (index, filename),
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            parents,
        )
        branch_ref_obj = pagure.lib.git.get_branch_ref(repo, branch)

    # Push to origin
    ori_remote = repo.remotes[0]
    PagureRepo.push(ori_remote, "%s:%s" % (branch_ref, branch_ref))

    shutil.rmtree(newfolder)


def add_tag_git_repo(folder, tagname, obj_hash, message):
    """ Add a tag to the given object of the given repo annotated by given message. """
    repo, newfolder, branch_ref_obj = _clone_and_top_commits(
        folder, "master", branch_ref=True
    )

    tag_sha = repo.create_tag(
        tagname,
        obj_hash,
        repo.get(obj_hash).type,
        pygit2.Signature("Alice Author", "alice@authors.tld"),
        message,
    )

    # Push to origin
    ori_remote = repo.remotes[0]
    PagureRepo.push(
        ori_remote, "refs/tags/%s:refs/tags/%s" % (tagname, tagname)
    )

    shutil.rmtree(newfolder)
    return tag_sha


def add_content_to_git(
    folder,
    branch="master",
    folders=None,
    filename="sources",
    content="foo",
    message=None,
    author=("Alice Author", "alice@authors.tld"),
    commiter=("Cecil Committer", "cecil@committers.tld"),
):
    """ Create some more commits for the specified git repo. """
    repo, newfolder, branch_ref_obj = _clone_and_top_commits(
        folder, branch, branch_ref=True
    )

    # Create a file in that git repo
    if folders:
        if not os.path.exists(os.path.join(newfolder, folders)):
            os.makedirs(os.path.join(newfolder, folders))
        filename = os.path.join(folders, filename)

    filepath = os.path.join(newfolder, filename)
    with open(filepath, "a", encoding="utf-8") as stream:
        stream.write("%s\n" % content)
    repo.index.add(filename)
    repo.index.write()

    parents = []
    commit = None
    try:
        if branch_ref_obj:
            commit = repo[branch_ref_obj.peel().hex]
        else:
            commit = repo.revparse_single("HEAD")
    except (KeyError, AttributeError):
        pass
    if commit:
        parents = [commit.oid.hex]

    # Commits the files added
    tree = repo.index.write_tree()
    author = pygit2.Signature(*author)
    committer = pygit2.Signature(*commiter)
    branch_ref = "refs/heads/%s" % branch
    message = message or "Add content to file %s" % (filename)
    repo.create_commit(
        branch_ref,  # the name of the reference to update
        author,
        committer,
        message,
        # binary string representing the tree object ID
        tree,
        # list of binary strings representing parents of the new commit
        parents,
    )

    # Push to origin
    ori_remote = repo.remotes[0]
    PagureRepo.push(ori_remote, "%s:%s" % (branch_ref, branch_ref))

    shutil.rmtree(newfolder)


def add_binary_git_repo(folder, filename):
    """ Create a fake image file for the specified git repo. """
    repo, newfolder, parents = _clone_and_top_commits(folder, "master")

    content = b"""\x00\x00\x01\x00\x01\x00\x18\x18\x00\x00\x01\x00 \x00\x88
\t\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x18\x00x00\x00\x01\x00 \x00\x00\x00
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00
00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa7lM\x01\xa6kM\t\xa6kM\x01
\xa4fF\x04\xa2dE\x95\xa2cD8\xa1a
"""

    # Create a file in that git repo
    with open(os.path.join(newfolder, filename), "wb") as stream:
        stream.write(content)
    repo.index.add(filename)
    repo.index.write()

    # Commits the files added
    tree = repo.index.write_tree()
    author = pygit2.Signature("Alice Author", "alice@authors.tld")
    committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
    repo.create_commit(
        "refs/heads/master",  # the name of the reference to update
        author,
        committer,
        "Add a fake image file",
        # binary string representing the tree object ID
        tree,
        # list of binary strings representing parents of the new commit
        parents,
    )

    # Push to origin
    ori_remote = repo.remotes[0]
    master_ref = repo.lookup_reference("HEAD").resolve()
    refname = "%s:%s" % (master_ref.name, master_ref.name)

    PagureRepo.push(ori_remote, refname)

    shutil.rmtree(newfolder)


def remove_file_git_repo(folder, filename, branch="master"):
    """ Delete the specified file on the give git repo and branch. """
    repo, newfolder, parents = _clone_and_top_commits(folder, branch)

    # Remove file
    repo.index.remove(filename)

    # Write the change and commit it
    tree = repo.index.write_tree()

    author = pygit2.Signature("Alice Author", "alice@authors.tld")
    committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
    branch_ref = "refs/heads/%s" % branch
    repo.create_commit(
        branch_ref,  # the name of the reference to update
        author,
        committer,
        "Remove file %s" % filename,
        # binary string representing the tree object ID
        tree,
        # list of binary strings representing parents of the new commit
        parents,
    )

    # Push to origin
    ori_remote = repo.remotes[0]

    PagureRepo.push(ori_remote, "%s:%s" % (branch_ref, branch_ref))

    shutil.rmtree(newfolder)


def add_pull_request_git_repo(
    folder,
    session,
    repo,
    fork,
    branch_from="feature",
    user="pingou",
    allow_rebase=False,
    append_content=None,
):
    """Set up the git repo and create the corresponding PullRequest
    object.
    """

    # Clone the main repo
    gitrepo = os.path.join(folder, "repos", repo.path)
    newpath = tempfile.mkdtemp(prefix="pagure-fork-test")
    repopath = os.path.join(newpath, "test")
    clone_repo = pygit2.clone_repository(gitrepo, repopath)

    # Create a file in that git repo
    with open(os.path.join(repopath, "sources"), "w") as stream:
        stream.write("foo\n bar")
    clone_repo.index.add("sources")
    clone_repo.index.write()

    # Commits the files added
    tree = clone_repo.index.write_tree()
    author = pygit2.Signature("Alice Author", "alice@authors.tld")
    committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
    clone_repo.create_commit(
        "refs/heads/master",  # the name of the reference to update
        author,
        committer,
        "Add sources file for testing",
        # binary string representing the tree object ID
        tree,
        # list of binary strings representing parents of the new commit
        [],
    )
    refname = "refs/heads/master:refs/heads/master"
    ori_remote = clone_repo.remotes[0]
    PagureRepo.push(ori_remote, refname)

    first_commit = clone_repo.revparse_single("HEAD")

    # Set the second repo
    repopath = os.path.join(folder, "repos", fork.path)
    new_gitrepo = os.path.join(newpath, "fork_test")
    clone_repo = pygit2.clone_repository(repopath, new_gitrepo)

    # Add the main project as remote repo
    upstream_path = os.path.join(folder, "repos", repo.path)
    remote = clone_repo.create_remote("upstream", upstream_path)
    remote.fetch()

    # Edit the sources file again
    content = "foo\n bar\nbaz\n boose"
    if append_content:
        content = content + append_content
    with open(os.path.join(new_gitrepo, "sources"), "w") as stream:
        stream.write(content)
    clone_repo.index.add("sources")
    clone_repo.index.write()

    # Commits the files added
    tree = clone_repo.index.write_tree()
    author = pygit2.Signature("Alice Author", "alice@authors.tld")
    committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
    clone_repo.create_commit(
        "refs/heads/%s" % branch_from,
        author,
        committer,
        "A commit on branch %s" % branch_from,
        tree,
        [first_commit.oid.hex],
    )
    refname = "refs/heads/%s" % (branch_from)
    ori_remote = clone_repo.remotes[0]
    PagureRepo.push(ori_remote, refname)

    # Create a PR for these changes
    project = pagure.lib.query.get_authorized_project(session, "test")
    req = pagure.lib.query.new_pull_request(
        session=session,
        repo_from=fork,
        branch_from=branch_from,
        repo_to=project,
        branch_to="master",
        title="PR from the %s branch" % branch_from,
        allow_rebase=allow_rebase,
        user=user,
    )
    session.commit()

    return req


def clean_pull_requests_path():
    newpath = tempfile.mkdtemp(prefix="pagure-fork-test")
    shutil.rmtree(newpath)


@contextmanager
def capture_output(merge_stderr=True):
    oldout, olderr = sys.stdout, sys.stderr
    try:
        out = StringIO()
        err = StringIO()
        if merge_stderr:
            sys.stdout = sys.stderr = out
            yield out
        else:
            sys.stdout, sys.stderr = out, err
            yield out, err
    finally:
        sys.stdout, sys.stderr = oldout, olderr


def get_alerts(html):
    soup = BeautifulSoup(html, "html.parser")
    alerts = []
    for element in soup.find_all("div", class_="alert"):
        severity = None
        for class_ in element["class"]:
            if not class_.startswith("alert-"):
                continue
            if class_ == "alert-dismissible":
                continue
            severity = class_[len("alert-") :]
            break
        element.find("button").decompose()  # close button
        alerts.append(
            dict(severity=severity, text="".join(element.stripped_strings))
        )
    return alerts


def definitely_wait(result):
    """ Helper function for definitely waiting in _maybe_wait. """
    result.wait()


if __name__ == "__main__":
    SUITE = unittest.TestLoader().loadTestsFromTestCase(Modeltests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
