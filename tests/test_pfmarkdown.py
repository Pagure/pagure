# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Jeremy Cline <jeremy@jcline.org>

"""

from __future__ import unicode_literals, absolute_import

import unittest
from xml.etree import ElementTree

from mock import patch, Mock

from pagure import pfmarkdown
from pagure.lib import model


@patch('pagure.pfmarkdown.flask.url_for', Mock(return_value='http://eh/'))
class TestObjAnchorTag(unittest.TestCase):
    """
    A set of tests for the pagure.pfmarkdown._obj_anchor_tag function
    """

    def test_obj_anchor_tag_issue(self):
        """Assert links to issues are generated correctly"""
        issue = model.Issue(
            title='The issue summary',
            content='The issue description',
        )
        expected_markup = (b'<a href="http://eh/" title="The issue summary">'
                           b'My Issue</a>')
        element = pfmarkdown._obj_anchor_tag(
            'jcline', None, None, issue, 'My Issue')

        self.assertEqual(expected_markup, ElementTree.tostring(element))

    def test_obj_anchor_tag_private_issue(self):
        """Assert links to private issues hide the title"""
        issue = model.Issue(
            title='The private issue summary',
            content='The issue description',
            private=True
        )
        expected_markup = (b'<a href="http://eh/" title="Private issue">'
                           b'My Issue</a>')
        element = pfmarkdown._obj_anchor_tag(
            'jcline', None, None, issue, 'My Issue')

        self.assertEqual(expected_markup, ElementTree.tostring(element))

    def test_obj_anchor_tag_pr(self):
        """Assert links to pull requests are generated correctly"""
        pr = model.PullRequest(title='The pull request summary')
        expected_markup = (b'<a href="http://eh/" title="The pull request '
                           b'summary">My Pull Request</a>')
        element = pfmarkdown._obj_anchor_tag(
            'jcline', None, None, pr, 'My Pull Request')

        self.assertEqual(expected_markup, ElementTree.tostring(element))


if __name__ == '__main__':
    unittest.main(verbosity=2)
