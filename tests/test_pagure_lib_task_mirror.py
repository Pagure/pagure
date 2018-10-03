# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

import datetime
import os
import shutil
import sys
import tempfile
import time
import unittest

import pygit2
import six
from mock import patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure
import pagure.lib.git
import tests

import pagure.lib.tasks_mirror


class PagureLibTaskMirrortests(tests.Modeltests):
    """ Tests for pagure.lib.task_mirror """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureLibTaskMirrortests, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None
        self.sshkeydir = os.path.join(self.path, 'sshkeys')
        pagure.config.config['MIRROR_SSHKEYS_FOLDER'] = self.sshkeydir

        tests.create_projects(self.session)

    def test_create_ssh_key(self):
        """ Test the _create_ssh_key method. """
        # before
        self.assertFalse(os.path.exists(self.sshkeydir))
        os.mkdir(self.sshkeydir)
        self.assertEqual(sorted(os.listdir(self.sshkeydir)), [])

        keyfile = os.path.join(self.sshkeydir, 'testkey')
        pagure.lib.tasks_mirror._create_ssh_key(keyfile)

        # after
        self.assertEqual(
            sorted(os.listdir(self.sshkeydir)),
            [u'testkey', u'testkey.pub']
        )

    def test_setup_mirroring(self):
        """ Test the setup_mirroring method. """

        # before
        self.assertFalse(os.path.exists(self.sshkeydir))
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNone(project.mirror_hook)

        # Install the plugin at the DB level
        plugin = pagure.lib.plugins.get_plugin('Mirroring')
        dbobj = plugin.db_object()
        dbobj.project_id = project.id
        self.session.add(dbobj)
        self.session.commit()

        pagure.lib.tasks_mirror.setup_mirroring(
            username=None,
            namespace=None,
            name='test')

        # after
        self.assertEqual(
            sorted(os.listdir(self.sshkeydir)),
            [u'test', u'test.pub']
        )
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNotNone(project.mirror_hook.public_key)
        self.assertTrue(
            project.mirror_hook.public_key.startswith('ssh-rsa '))

    def test_setup_mirroring_ssh_folder_exists_wrong_permissions(self):
        """ Test the setup_mirroring method. """

        os.makedirs(self.sshkeydir)

        # before
        self.assertEqual(sorted(os.listdir(self.sshkeydir)), [])
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNone(project.mirror_hook)

        # Install the plugin at the DB level
        plugin = pagure.lib.plugins.get_plugin('Mirroring')
        dbobj = plugin.db_object()
        dbobj.project_id = project.id
        self.session.add(dbobj)
        self.session.commit()

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.tasks_mirror.setup_mirroring,
            username=None,
            namespace=None,
            name='test')

        # after
        self.assertEqual(sorted(os.listdir(self.sshkeydir)), [])
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNone(project.mirror_hook.public_key)

    def test_setup_mirroring_ssh_folder_symlink(self):
        """ Test the setup_mirroring method. """

        os.symlink(
            self.path,
            self.sshkeydir
        )

        # before
        self.assertEqual(
            sorted(os.listdir(self.sshkeydir)),
            [u'attachments', u'config', u'forks', u'releases',
             u'remotes', u'repos', u'sshkeys']
        )
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNone(project.mirror_hook)

        # Install the plugin at the DB level
        plugin = pagure.lib.plugins.get_plugin('Mirroring')
        dbobj = plugin.db_object()
        dbobj.project_id = project.id
        self.session.add(dbobj)
        self.session.commit()

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.tasks_mirror.setup_mirroring,
            username=None,
            namespace=None,
            name='test')

        # after
        self.assertEqual(
            sorted(os.listdir(self.sshkeydir)),
            [u'attachments', u'config', u'forks', u'releases',
             u'remotes', u'repos', u'sshkeys']
        )
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNone(project.mirror_hook.public_key)

    @patch('os.getuid', MagicMock(return_value=450))
    def test_setup_mirroring_ssh_folder_owner(self):
        """ Test the setup_mirroring method. """
        os.makedirs(self.sshkeydir, mode=0o700)

        # before
        self.assertEqual(sorted(os.listdir(self.sshkeydir)), [])
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNone(project.mirror_hook)

        # Install the plugin at the DB level
        plugin = pagure.lib.plugins.get_plugin('Mirroring')
        dbobj = plugin.db_object()
        dbobj.project_id = project.id
        self.session.add(dbobj)
        self.session.commit()

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.tasks_mirror.setup_mirroring,
            username=None,
            namespace=None,
            name='test')

        # after
        self.assertEqual(sorted(os.listdir(self.sshkeydir)), [])
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNone(project.mirror_hook.public_key)


class PagureLibTaskMirrorSetuptests(tests.Modeltests):
    """ Tests for pagure.lib.task_mirror """

    maxDiff = None

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureLibTaskMirrorSetuptests, self).setUp()

        pagure.config.config['REQUESTS_FOLDER'] = None
        self.sshkeydir = os.path.join(self.path, 'sshkeys')
        pagure.config.config['MIRROR_SSHKEYS_FOLDER'] = self.sshkeydir

        tests.create_projects(self.session)
        project = pagure.lib.get_authorized_project(self.session, 'test')

        # Install the plugin at the DB level
        plugin = pagure.lib.plugins.get_plugin('Mirroring')
        dbobj = plugin.db_object()
        dbobj.target = 'ssh://user@localhost.localdomain/foobar.git'
        dbobj.project_id = project.id
        self.session.add(dbobj)
        self.session.commit()

        pagure.lib.tasks_mirror.setup_mirroring(
            username=None,
            namespace=None,
            name='test')

    def test_setup_mirroring_twice(self):
        """ Test the setup_mirroring method. """

        # before
        self.assertEqual(
            sorted(os.listdir(self.sshkeydir)), [u'test', u'test.pub']
        )
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNotNone(project.mirror_hook.public_key)
        before_key = project.mirror_hook.public_key
        self.assertTrue(
            project.mirror_hook.public_key.startswith('ssh-rsa '))

        self.assertRaises(
            pagure.exceptions.PagureException,
            pagure.lib.tasks_mirror.setup_mirroring,
            username=None,
            namespace=None,
            name='test')

        # after
        self.assertEqual(
            sorted(os.listdir(self.sshkeydir)),
            [u'test', u'test.pub']
        )
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNotNone(project.mirror_hook.public_key)
        self.assertEqual(project.mirror_hook.public_key, before_key)

    def test_teardown_mirroring(self):
        """ Test the teardown_mirroring method. """

        # before
        self.assertEqual(
            sorted(os.listdir(self.sshkeydir)), [u'test', u'test.pub']
        )
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNotNone(project.mirror_hook.public_key)
        self.assertTrue(
            project.mirror_hook.public_key.startswith('ssh-rsa '))

        pagure.lib.tasks_mirror.teardown_mirroring(
            username=None,
            namespace=None,
            name='test')

        # after
        self.session = pagure.lib.create_session(self.dbpath)
        self.assertEqual(sorted(os.listdir(self.sshkeydir)), [])
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNone(project.mirror_hook.public_key)

    @patch('pagure.lib.git.read_git_lines')
    def test_mirror_project(self,rgl):
        """ Test the mirror_project method. """
        rgl.return_value = ('stdout', 'stderr')
        tests.create_projects_git(
            os.path.join(self.path, 'repos'), bare=True)

        # before
        self.assertEqual(
            sorted(os.listdir(self.sshkeydir)), [u'test', u'test.pub']
        )
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNotNone(project.mirror_hook.public_key)
        self.assertTrue(
            project.mirror_hook.public_key.startswith('ssh-rsa '))

        pagure.lib.tasks_mirror.mirror_project(
            username=None,
            namespace=None,
            name='test')

        # after
        self.assertEqual(
            sorted(os.listdir(self.sshkeydir)),
            [u'test', u'test.pub']
        )
        project = pagure.lib.get_authorized_project(self.session, 'test')
        self.assertIsNotNone(project.mirror_hook.public_key)
        self.assertTrue(
            project.mirror_hook.public_key.startswith('ssh-rsa '))

        ssh_script = os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'pagure','lib', 'ssh_script.sh'))

        calls = [
            call(
                [u'push', u'--mirror', u'ssh://user@localhost.localdomain/foobar.git'],
                abspath=os.path.join(self.path, 'repos', 'test.git'),
                env={
                    u'GIT_SSH': ssh_script,
                    u'SSHKEY': u'%s/sshkeys/test' % self.path
                },
                error=True
            )
        ]

        self.assertEqual(rgl.call_count, 1)
        self.assertEqual(
            calls,
            rgl.mock_calls
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
