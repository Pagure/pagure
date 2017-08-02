"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Clement Verna <cverna@tutanota.com>

"""


import unittest
import sys
import os
import json


sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure  # noqa: E402
import pagure.lib  # noqa: E402
import tests  # noqa: E402


class PagureFlaskApiCustomFieldIssuetests(tests.Modeltests):
    """ Tests for the flask API of pagure for issue's custom fields """
    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        self.maxDiff = None
        super(PagureFlaskApiCustomFieldIssuetests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.api.SESSION = self.session
        pagure.api.issue.SESSION = self.session
        pagure.lib.SESSION = self.session

        pagure.APP.config['TICKETS_FOLDER'] = None

        tests.create_projects(self.session)
        tests.create_projects_git(os.path.join(self.path, 'tickets'))
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)

        # Create normal issue
        repo = pagure.get_authorized_project(self.session, 'test')
        pagure.lib.new_issue(
            session=self.session,
            repo=repo,
            title='Test issue #1',
            content='We should work on this',
            user='pingou',
            ticketfolder=None,
            private=False,
        )
        self.session.commit()

    def test_api_update_custom_field_bad_request(self):
        """ Test the api_update_custom_field method of the flask api.
        This test that a badly form request returns the correct error.
        """

        headers = {'Authorization': 'token aaabbbcccddd'}

        # Request is not formated correctly
        payload = json.dumps({'field':
                             {'foo': 'bar'}})
        output = self.app.post(
            '/api/0/test/issue/1/custom', headers=headers, data=payload)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "error": "This request format is invalid",
                "error_code": "EINVALIDCUSTOMFIELDS",
            }
        )

    def test_api_update_custom_field_wrong_field(self):
        """ Test the api_update_custom_field method of the flask api.
        This test that an invalid field retruns the correct error.
        """

        headers = {'Authorization': 'token aaabbbcccddd'}
        # Project does not have this custom field
        payload = json.dumps({'fields':
                             {'foo': 'bar'}})
        output = self.app.post(
            '/api/0/test/issue/1/custom', headers=headers, data=payload)
        self.assertEqual(output.status_code, 400)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "error": "Invalid custom field submitted",
                "error_code": "EINVALIDISSUEFIELD",
            }
        )

    def test_api_update_custom_field(self):
        """ Test the api_update_custom_field method of the flask api.
        This test the successful requests scenarii.
        """

        headers = {'Authorization': 'token aaabbbcccddd'}

        repo = pagure.get_authorized_project(self.session, 'test')
        settings = repo.settings
        settings['issue_tracker'] = True
        repo.settings = settings
        self.session.add(repo)
        self.session.commit()

        # Set some custom fields
        repo = pagure.get_authorized_project(self.session, 'test')
        msg = pagure.lib.set_custom_key_fields(
            self.session, repo,
            ['bugzilla', 'upstream', 'reviewstatus'],
            ['link', 'boolean', 'list'],
            ['unused data for non-list type', '', 'ack', 'nack', 'needs review'],
            [None, None, None])
        self.session.commit()
        self.assertEqual(msg, 'List of custom fields updated')

        payload = json.dumps({'fields':
                             {'bugzilla': '', 'upstream': True}})
        output = self.app.post(
            '/api/0/test/issue/1/custom', headers=headers, data=payload)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "fields": [
                    {"bugzilla": "No changes"},
                    {"upstream": "Custom field upstream adjusted to True"},
                ]
            }
        )

        repo = pagure.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.other_fields), 1)

        payload = json.dumps({'fields':
                              {'bugzilla': 'https://bugzilla.redhat.com/1234',
                               'upstream': False,
                               'reviewstatus': 'ack'}})
        output = self.app.post(
            '/api/0/test/issue/1/custom', headers=headers,
            data=payload)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "fields": [
                    {"bugzilla": "Custom field bugzilla adjusted to "
                                 "https://bugzilla.redhat.com/1234"},
                    {"reviewstatus": "Custom field reviewstatus adjusted to ack"},
                    {"upstream": "Custom field upstream reset (from 1)"},

                ]
            }
        )

        repo = pagure.get_authorized_project(self.session, 'test')
        issue = pagure.lib.search_issues(self.session, repo, issueid=1)
        self.assertEqual(len(issue.other_fields), 3)

        # Reset the value
        payload = json.dumps({'fields':
                             {'bugzilla': '',
                              'upstream': '',
                              'reviewstatus': ''}})
        output = self.app.post(
            '/api/0/test/issue/1/custom', headers=headers,
            data=payload)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertDictEqual(
            data,
            {
                "fields": [
                    {"bugzilla": "Custom field bugzilla reset "
                                 "(from https://bugzilla.redhat.com/1234)"},
                    {"reviewstatus": "Custom field reviewstatus reset (from ack)"},
                    {"upstream": "Custom field upstream reset (from 0)"},
                ]
            }
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)