# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Matt Prahl <mprahl@redhat.com>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import unittest
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.api
import pagure.lib
import tests


class PagureFlaskApiGroupTests(tests.Modeltests):
    """ Tests for the flask API of pagure for issue """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskApiGroupTests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.api.SESSION = self.session
        pagure.api.group.SESSION = self.session
        pagure.api.user.SESSION = self.session
        pagure.lib.SESSION = self.session

        pagure.APP.config['REQUESTS_FOLDER'] = None

        msg = pagure.lib.add_group(
            self.session,
            group_name='some_group',
            display_name='Some Group',
            description=None,
            group_type='bar',
            user='pingou',
            is_admin=False,
            blacklist=[],
        )
        self.session.commit()

        self.app = pagure.APP.test_client()

    def test_api_groups(self):
        """ Test the api_groups function.  """

        # Add a couple of groups so that we can list them
        item = pagure.lib.model.PagureGroup(
            group_name='group1',
            group_type='user',
            display_name='User group',
            user_id=1,  # pingou
        )
        self.session.add(item)

        item = pagure.lib.model.PagureGroup(
            group_name='rel-eng',
            group_type='user',
            display_name='Release engineering group',
            user_id=1,  # pingou
        )
        self.session.add(item)
        self.session.commit()

        output = self.app.get('/api/0/groups')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data['groups'], ['some_group', 'group1', 'rel-eng'])
        self.assertEqual(sorted(data.keys()), ['groups', 'total_groups'])
        self.assertEqual(data['total_groups'], 3)

        output = self.app.get('/api/0/groups?pattern=re')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data['groups'], ['rel-eng'])
        self.assertEqual(sorted(data.keys()), ['groups', 'total_groups'])
        self.assertEqual(data['total_groups'], 1)

    def test_api_view_group(self):
        """
            Test the api_view_group method of the flask api
            The tested group has one member.
        """
        output = self.app.get("/api/0/group/some_group")
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "default_email": "bar@pingou.com",
                "emails": [
                    "bar@pingou.com",
                    "foo@pingou.com"
                ],
                "name": "pingou"
            },
            "members": ["pingou"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group"
        }
        data = json.loads(output.data)
        data['date_created'] = '1492020239'
        self.assertDictEqual(data, exp)

    def test_api_view_group_two_members(self):
        """
            Test the api_view_group method of the flask api
            The tested group has two members.
        """
        user = pagure.lib.model.User(
            user='mprahl',
            fullname='Matt Prahl',
            password='foo',
            default_email='mprahl@redhat.com',
        )
        self.session.add(user)
        self.session.commit()
        group = pagure.lib.search_groups(self.session, group_name='some_group')
        result = pagure.lib.add_user_to_group(
            self.session, user.username, group, user.username, True)
        self.session.commit()
        output = self.app.get("/api/0/group/some_group")
        self.assertEqual(output.status_code, 200)
        exp = {
            "display_name": "Some Group",
            "description": None,
            "creator": {
                "fullname": "PY C",
                "default_email": "bar@pingou.com",
                "emails": [
                    "bar@pingou.com",
                    "foo@pingou.com"
                ],
                "name": "pingou"
            },
            "members": ["pingou", "mprahl"],
            "date_created": "1492020239",
            "group_type": "user",
            "name": "some_group"
        }
        self.maxDiff = None
        data = json.loads(output.data)
        data['date_created'] = '1492020239'
        from pprint import pprint
        pprint(data)
        self.assertDictEqual(data, exp)

    def test_api_view_group_no_group_error(self):
        """
            Test the api_view_group method of the flask api
            The tested group has one member.
        """
        output = self.app.get("/api/0/group/some_group3")
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertEqual(data['error'], 'Group not found')
        self.assertEqual(data['error_code'], 'ENOGROUP')

if __name__ == "__main__":
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskApiGroupTests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
