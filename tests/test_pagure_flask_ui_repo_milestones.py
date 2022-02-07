# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import sys
import unittest
import os

from mock import ANY, patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import tests


class PagureFlaskRepoMilestonestests(tests.Modeltests):
    """Tests for milestones in pagure"""

    @patch("pagure.lib.notify.send_email", MagicMock(return_value=True))
    def setUp(self):
        """Set up the environnment, ran before every tests."""
        super(PagureFlaskRepoMilestonestests, self).setUp()

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, "repos"))

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        msg = pagure.lib.query.new_issue(
            session=self.session,
            repo=repo,
            title="Test issue #1",
            content="We should work on this for the second time",
            user="foo",
            status="Open",
        )
        self.session.commit()
        self.assertEqual(msg.title, "Test issue #1")

    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_milestones_settings_empty(self):
        """Test the settings page when no milestones are set."""

        repo = pagure.lib.query.get_authorized_project(self.session, "test")
        self.assertEqual(repo.milestones, {})

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/settings")
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                "<title>Settings - test - Pagure</title>",
                output.get_data(as_text=True),
            )
            # Check that the milestones have their empty fields
            self.assertIn(
                """<div id="milestones">
      <div class="row p-t-1 milestone" id="milestone_1">
        <input type="hidden" name="milestones" value="1">
        <div class="col-sm-4 p-r-0">
          <input type="text" name="milestone_1_name"
            value="" size="3" class="form-control"/>
        </div>
        <div class="col-sm-4 p-r-0">
          <input type="text" name="milestone_1_date"
            value="" class="form-control"/>
        </div>
        <div class="col-sm-2 p-r-0" >
            <span class="fa fa-long-arrow-up milestone_order_up"
                data-stone="1"></span>
            <span class="fa fa-long-arrow-down milestone_order_bottom"
                data-stone="1"></span>
        </div>
        <div class="col-sm-1 p-r-0" >
            <input type="checkbox" name="milestone_1_active" />
        </div>
      </div>""",
                output.get_data(as_text=True),
            )

    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_setting_retrieving_milestones(self):
        """Test setting and retrieving milestones off a project."""

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        milestones = {
            "1.0": None,
            "1.1": None,
            "1.2": "2018-12-31",
            "2.0": "2019",
            "3.0": "future",
            "4.0": None,
        }
        repo.milestones = milestones
        self.session.add(repo)
        self.session.commit()

        self.assertEqual(
            repo.milestones,
            {
                "1.0": {"active": True, "date": None},
                "1.1": {"active": True, "date": None},
                "1.2": {"active": True, "date": "2018-12-31"},
                "2.0": {"active": True, "date": "2019"},
                "3.0": {"active": True, "date": "future"},
                "4.0": {"active": True, "date": None},
            },
        )

    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_issue_page_milestone_actives(self):
        """Test viewing tickets on a project having milestones, all active."""

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        milestones = {"1.0": None, "2.0": "2019", "3.0": "future"}
        milestones_keys = ["1.0", "3.0", "2.0"]
        repo.milestones = milestones
        repo.milestones_keys = milestones_keys
        self.session.add(repo)
        self.session.commit()

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<select class="form-control c-select" id="milestone" name="milestone">'
                '<option selected value=""></option>'
                '<option value="1.0">1.0</option>'
                '<option value="3.0">3.0</option>'
                '<option value="2.0">2.0</option>'
                "</select>",
                output.get_data(as_text=True),
            )

    @patch(
        "pagure.decorators.admin_session_timedout",
        MagicMock(return_value=False),
    )
    def test_issue_page_milestone_not_allactives(self):
        """Test viewing tickets on a project having milestones, not all
        being active.
        """

        repo = pagure.lib.query.get_authorized_project(self.session, "test")

        milestones = {
            "1.0": {"date": None, "active": False},
            "2.0": {"date": "2018-01-01", "active": False},
            "3.0": {"date": "2025-01-01", "active": True},
            "4.0": {"date": "future", "active": True},
        }
        milestones_keys = ["1.0", "2.0", "3.0", "4.0"]
        repo.milestones = milestones
        repo.milestones_keys = milestones_keys
        self.session.add(repo)
        self.session.commit()

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/test/issue/1")
            self.assertEqual(output.status_code, 200)
            self.assertIn(
                '<select class="form-control c-select" id="milestone" name="milestone">'
                '<option selected value=""></option>'
                '<option value="3.0">3.0</option>'
                '<option value="4.0">4.0</option>'
                "</select>",
                output.get_data(as_text=True),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
