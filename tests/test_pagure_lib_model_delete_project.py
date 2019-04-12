# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import json
import unittest
import sys
import os
import uuid


sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.model as model
import pagure.lib.query

import tests


class DeleteProjectTests(tests.Modeltests):
    """ Tests for flask issues controller of pagure """

    def test_delete_project_with_group(self):
        """ Test the model when we delete a project with a group. """

        # Create a project
        item = model.Project(
            user_id=1,  # pingou
            name="test",
            description="test project #1",
            hook_token="aaabbbiii",
        )
        self.session.add(item)
        self.session.commit()

        # Create a group
        grp = model.PagureGroup(
            group_name="testgrp",
            display_name="Test group",
            description=None,
            group_type="user",
            user_id=1,  # pingou
        )
        self.session.add(grp)
        self.session.commit()

        # Add group to project
        project_group = model.ProjectGroup(
            project_id=1, group_id=1, access="admin"
        )
        self.session.add(project_group)
        self.session.commit()

        self.assertEqual(self.session.query(model.Project).count(), 1)
        self.assertEqual(self.session.query(model.ProjectGroup).count(), 1)

        project = (
            self.session.query(model.Project)
            .filter(model.Project.id == 1)
            .one()
        )
        self.session.delete(project)
        self.session.commit()

        self.assertEqual(self.session.query(model.Project).count(), 0)
        self.assertEqual(self.session.query(model.ProjectGroup).count(), 0)

    def test_delete_project_with_user(self):
        """ Test the model when we delete a project with users. """

        # Create a project
        item = model.Project(
            user_id=1,  # pingou
            name="test",
            description="test project #1",
            hook_token="aaabbbiii",
        )
        self.session.add(item)
        self.session.commit()

        # Add user #2 to project
        project_user = model.ProjectUser(
            project_id=1, user_id=2, access="admin"
        )
        self.session.add(project_user)
        self.session.commit()

        self.assertEqual(self.session.query(model.Project).count(), 1)
        self.assertEqual(self.session.query(model.ProjectUser).count(), 1)
        self.assertEqual(self.session.query(model.User).count(), 2)

        project = (
            self.session.query(model.Project)
            .filter(model.Project.id == 1)
            .one()
        )
        self.session.delete(project)
        self.session.commit()

        self.assertEqual(self.session.query(model.Project).count(), 0)
        self.assertEqual(self.session.query(model.ProjectUser).count(), 0)
        self.assertEqual(self.session.query(model.User).count(), 2)

    def test_delete_project_with_coloredtags(self):
        """ Test the model when we delete a project with Colored tags. """

        # Create a project
        item = model.Project(
            user_id=1,  # pingou
            name="test",
            description="test project #1",
            hook_token="aaabbbiii",
        )
        self.session.add(item)
        self.session.commit()

        # Create two ColoredTags
        tagobj = model.TagColored(tag="Tag#1", project_id=1)
        self.session.add(tagobj)
        self.session.flush()

        tagobj = model.TagColored(tag="Tag#2", project_id=1)
        self.session.add(tagobj)
        self.session.flush()

        self.assertEqual(self.session.query(model.Project).count(), 1)
        self.assertEqual(self.session.query(model.TagColored).count(), 2)

        project = (
            self.session.query(model.Project)
            .filter(model.Project.id == 1)
            .one()
        )
        self.session.delete(project)
        self.session.commit()

        self.assertEqual(self.session.query(model.Project).count(), 0)
        self.assertEqual(self.session.query(model.TagColored).count(), 0)

    def test_delete_project_with_coloredtags_and_issues(self):
        """ Test the model when we delete a project with Colored tags and
        issues. """

        # Create a project
        item = model.Project(
            user_id=1,  # pingou
            name="test",
            description="test project #1",
            hook_token="aaabbbiii",
        )
        self.session.add(item)
        self.session.commit()

        # Create two ColoredTags
        tagobj = model.TagColored(tag="Tag#1", project_id=1)
        self.session.add(tagobj)
        self.session.flush()

        tagobj = model.TagColored(tag="Tag#2", project_id=1)
        self.session.add(tagobj)
        self.session.flush()

        # Create issues
        issue = model.Issue(
            id=pagure.lib.query.get_next_id(self.session, 1),
            project_id=1,
            title="Issue #1",
            content="Description #1",
            user_id=1,
            uid=uuid.uuid4().hex,
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        issue = model.Issue(
            id=pagure.lib.query.get_next_id(self.session, 1),
            project_id=1,
            title="Issue #2",
            content="Description #2",
            user_id=1,
            uid=uuid.uuid4().hex,
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        self.assertEqual(self.session.query(model.Project).count(), 1)
        self.assertEqual(self.session.query(model.TagColored).count(), 2)
        self.assertEqual(self.session.query(model.Issue).count(), 2)

        project = (
            self.session.query(model.Project)
            .filter(model.Project.id == 1)
            .one()
        )
        self.session.delete(project)
        self.session.commit()

        self.assertEqual(self.session.query(model.Project).count(), 0)
        self.assertEqual(self.session.query(model.TagColored).count(), 0)
        self.assertEqual(self.session.query(model.Issue).count(), 0)

    def test_delete_project_with_coloredtags_and_tagged_issues(self):
        """ Test the model when we delete a project with Colored tags and
        tagged issues. """

        # Create a project
        item = model.Project(
            user_id=1,  # pingou
            name="test",
            description="test project #1",
            hook_token="aaabbbiii",
        )
        self.session.add(item)
        self.session.commit()

        # Create two ColoredTags
        tagobj = model.TagColored(tag="Tag#1", project_id=1)
        self.session.add(tagobj)
        self.session.flush()

        tagobj = model.TagColored(tag="Tag#2", project_id=1)
        self.session.add(tagobj)
        self.session.flush()

        # Create issues
        issue = model.Issue(
            id=pagure.lib.query.get_next_id(self.session, 1),
            project_id=1,
            title="Issue #1",
            content="Description #1",
            user_id=1,
            uid="Issue#1",
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        issue = model.Issue(
            id=pagure.lib.query.get_next_id(self.session, 1),
            project_id=1,
            title="Issue #2",
            content="Description #2",
            user_id=1,
            uid="Issue#2",
            private=False,
        )
        self.session.add(issue)
        self.session.commit()

        # Tag the issue
        tagissue = model.TagIssueColored(issue_uid="Issue#1", tag_id=1)
        self.session.add(tagissue)
        self.session.commit()

        tagissue = model.TagIssueColored(issue_uid="Issue#2", tag_id=2)
        self.session.add(tagissue)
        self.session.commit()

        self.assertEqual(self.session.query(model.Project).count(), 1)
        self.assertEqual(self.session.query(model.TagColored).count(), 2)
        self.assertEqual(self.session.query(model.Issue).count(), 2)

        project = (
            self.session.query(model.Project)
            .filter(model.Project.id == 1)
            .one()
        )
        self.session.delete(project)
        self.session.commit()

        self.assertEqual(self.session.query(model.Project).count(), 0)
        self.assertEqual(self.session.query(model.TagColored).count(), 0)
        self.assertEqual(self.session.query(model.Issue).count(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
