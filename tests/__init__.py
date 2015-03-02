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
from datetime import timedelta
from functools import wraps

import pygit2

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib
import progit.lib.model


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

    with appcontext_pushed.connected_to(handler, APP):
        yield


class Modeltests(unittest.TestCase):
    """ Model tests. """

    def __init__(self, method_name='runTest'):
        """ Constructor. """
        unittest.TestCase.__init__(self, method_name)
        self.session = None
        self.path = tempfile.mkdtemp(prefix='progit-tests')
        self.gitrepo = None
        self.gitrepos = None

    # pylint: disable=C0103
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        # Clean up eventual git repo left in the present folder.
        for filename in os.listdir(HERE):
            if filename.endswith('.git') and os.path.isdir(filename):
                print '**', filename
                shutil.rmtree(filename)

        self.session = progit.lib.model.create_tables(DB_PATH)

        # Create a couple of users
        item = progit.lib.model.User(
            user='pingou',
            fullname='PY C',
            password='foo',
        )
        self.session.add(item)
        item = progit.lib.model.UserEmail(
            user_id=1,
            email='bar@pingou.com')
        self.session.add(item)
        item = progit.lib.model.UserEmail(
            user_id=1,
            email='foo@pingou.com')
        self.session.add(item)

        item = progit.lib.model.User(
            user='foo',
            fullname='foo bar',
            password='foo',
        )
        self.session.add(item)
        item = progit.lib.model.UserEmail(
            user_id=2,
            email='foo@bar.com')
        self.session.add(item)

        self.session.commit()

    # pylint: disable=C0103
    def tearDown(self):
        """ Remove the test.db database if there is one. """
        self.session.close()

        # Clear temp directory
        if sys.exc_info() == (None, None, None):
            shutil.rmtree(self.path)
        else:
            print('FAILED TESTS AT %s' % self.path)

        # Clear DB
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        if DB_PATH.startswith('postgres'):
            if 'localhost' in DB_PATH:
                progit.lib.model.drop_tables(DB_PATH, self.session.bind)
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
        self.approved_memberships = [
            FakeGroup('packager'),
            FakeGroup('design-team')
        ]
        self.dic = {}
        self.dic['timezone'] = 'Europe/Paris'
        self.cla_done = cla_done

    def __getitem__(self, key):
        return self.dic[key]


def create_projects(session):
    """ Create some projects in the database. """
    item = progit.lib.model.Project(
        user_id=1,  # pingou
        name='test',
        description='test project #1',
    )
    session.add(item)

    item = progit.lib.model.Project(
        user_id=1,  # pingou
        name='test2',
        description='test project #2',
    )
    session.add(item)

    session.commit()


def create_projects_git(folder):
    """ Create some projects in the database. """
    repos = []
    for project in ['test.git', 'test2.git']:
        repo_path = os.path.join(folder, project)
        repos.append(repo_path)
        os.makedirs(repo_path)
        pygit2.init_repository(repo_path)

    return repos


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(Modeltests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
