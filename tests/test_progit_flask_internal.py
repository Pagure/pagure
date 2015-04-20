# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

import json
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests


class PagureFlaskInternaltests(tests.Modeltests):
    """ Tests for flask Internal controller of pagure """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskInternaltests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.APP.config['IP_ALLOWED_INTERNAL'].append(None)
        pagure.SESSION = self.session
        pagure.internal.SESSION = self.session
        pagure.APP.config['REQUESTS_FOLDER'] = None
        self.app = pagure.APP.test_client()

    @patch('pagure.lib.notify.send_email')
    def test_pull_request_add_comment(self, send_email):
        """ Test the pull_request_add_comment function.  """
        send_email.return_value = True

        tests.create_projects(self.session)

        repo = pagure.lib.get_project(self.session, 'test')
        forked_repo = pagure.lib.get_project(
            self.session, 'test', user='pingou')

        msg = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='feature',
            repo_to=repo,
            branch_to='master',
            title='PR from the feature branch',
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(msg, 'Request created')

        request = repo.requests[0]
        self.assertEqual(len(request.comments), 0)
        self.assertEqual(len(request.discussion), 0)

        data = {
            'objid': 'foo',
        }

        # Wrong http request
        output = self.app.post('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 405)

        # Invalid request
        output = self.app.put('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 400)

        data = {
            'objid': 'foo',
            'useremail': 'foo@pingou.com',
        }

        # Invalid objid
        output = self.app.put('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 404)

        data = {
            'objid': request.uid,
            'useremail': 'foo@pingou.com',
        }

        # Valid objid, in-complete data for a comment
        output = self.app.put('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 400)

        data = {
            'objid': request.uid,
            'useremail': 'foo@pingou.com',
            'comment': 'Looks good to me!',
        }

        # Add comment
        output = self.app.put('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 200)
        js_data = json.loads(output.data)
        self.assertDictEqual(js_data, {'message': 'Comment added'})

        repo = pagure.lib.get_project(self.session, 'test')
        request = repo.requests[0]
        self.assertEqual(len(request.comments), 1)
        self.assertEqual(len(request.discussion), 1)

        # Check the @localonly
        pagure.APP.config['IP_ALLOWED_INTERNAL'].remove(None)
        output = self.app.put('/pv/pull-request/comment/', data=data)
        self.assertEqual(output.status_code, 403)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskInternaltests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
