# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

from __future__ import unicode_literals, absolute_import

import unittest
import shutil
import sys
import os

import mock
import munch
import pygit2

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.model
import pagure.lib.query
import pagure.utils
import tests


class PagureUtilsTests(tests.SimplePagureTest):
    """ Tests for pagure.utils """

    def setUp(self):
        """ Set up the environnment, run before every tests. """
        super(PagureUtilsTests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"), bare=True)
        tests.add_content_git_repo(
            os.path.join(self.path, "repos", "test2.git")
        )

        project = pagure.lib.query._get_project(self.session, "test")
        # Add a deploy key to the project
        new_key_obj = pagure.lib.model.SSHKey(
            project_id=project.id,
            pushaccess=False,
            public_ssh_key="\n foo bar",
            ssh_short_key="\n foo bar",
            ssh_search_key="\n foo bar",
            creator_user_id=1,  # pingou
        )

        self.session.add(new_key_obj)
        self.session.commit()

    def test_lookup_deploykey_non_deploykey(self):
        """ Test lookup_deploykey with a non-deploykey username. """
        project = pagure.lib.query._get_project(self.session, "test")
        res = pagure.utils.lookup_deploykey(project, "pingou")
        self.assertEquals(res, None)

    def test_lookup_deploykey_different_project(self):
        """ Test lookup_deploykey with a username for another project. """
        project = pagure.lib.query._get_project(self.session, "test2")
        res = pagure.utils.lookup_deploykey(project, "deploykey_test_1")
        self.assertEquals(res, None)

    def test_lookup_deploykey_non_existent_key(self):
        """ Test lookup_deploykey with a non-existing deploykey. """
        project = pagure.lib.query._get_project(self.session, "test")
        res = pagure.utils.lookup_deploykey(project, "deploykey_test_2")
        self.assertEquals(res, None)

    def test_lookup_deploykey(self):
        """ Test lookup_deploykey with a correct username. """
        project = pagure.lib.query._get_project(self.session, "test")
        res = pagure.utils.lookup_deploykey(project, "deploykey_test_1")
        self.assertNotEquals(res, None)
        self.assertFalse(res.pushaccess)
