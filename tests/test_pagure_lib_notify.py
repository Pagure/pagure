# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

from mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import pagure.lib.model
import pagure.lib.notify
import tests


class PagureLibNotifytests(tests.Modeltests):
    """ Tests for pagure.lib.notify """

    def test_get_emails_for_obj_issue(self):
        """ Test the _get_emails_for_obj method from pagure.lib.notify. """

        # Create the project ns/test
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Create the ticket
        iss = pagure.lib.new_issue(
            issue_id=4,
            session=self.session,
            repo=item,
            title='test issue',
            content='content test issue',
            user='pingou',
            ticketfolder=None,
        )
        self.session.commit()
        self.assertEqual(iss.id, 4)
        self.assertEqual(iss.title, 'test issue')

        exp = set(['bar@pingou.com'])
        out = pagure.lib.notify._get_emails_for_obj(iss)
        self.assertEqual(out, exp)

        # Comment on the ticket
        out = pagure.lib.add_issue_comment(
            self.session,
            issue=iss,
            comment='This is a comment',
            user='foo',
            ticketfolder=None,
            notify=False)
        self.assertEqual(out, 'Comment added')

        exp = set(['bar@pingou.com', 'foo@bar.com'])
        out = pagure.lib.notify._get_emails_for_obj(iss)
        self.assertEqual(out, exp)

        # Create user `bar`
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar name',
            password='bar',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)
        self.session.commit()

        # Watch the ticket
        out = pagure.lib.set_watch_obj(self.session, 'bar', iss, True)
        self.assertEqual(out, 'You are now watching this issue')

        exp = set(['bar@pingou.com', 'foo@bar.com', 'bar@bar.com'])
        out = pagure.lib.notify._get_emails_for_obj(iss)
        self.assertEqual(out, exp)

    def test_get_emails_for_obj_issue_watching_project(self):
        """ Test the _get_emails_for_obj method from pagure.lib.notify. """

        # Create the project ns/test
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Create the ticket
        iss = pagure.lib.new_issue(
            issue_id=4,
            session=self.session,
            repo=item,
            title='test issue',
            content='content test issue',
            user='pingou',
            ticketfolder=None,
        )
        self.session.commit()
        self.assertEqual(iss.id, 4)
        self.assertEqual(iss.title, 'test issue')

        exp = set(['bar@pingou.com'])
        out = pagure.lib.notify._get_emails_for_obj(iss)
        self.assertEqual(out, exp)

        # Comment on the ticket
        out = pagure.lib.add_issue_comment(
            self.session,
            issue=iss,
            comment='This is a comment',
            user='foo',
            ticketfolder=None,
            notify=False)
        self.assertEqual(out, 'Comment added')

        exp = set(['bar@pingou.com', 'foo@bar.com'])
        out = pagure.lib.notify._get_emails_for_obj(iss)
        self.assertEqual(out, exp)

        # Create user `bar`
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar name',
            password='bar',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)
        self.session.commit()

        # Watch the project
        repo = pagure.get_authorized_project(self.session, 'test3', namespace='ns')
        out = pagure.lib.update_watch_status(self.session, repo, 'bar', '1')
        self.assertEqual(
            out, 'You are now watching issues and PRs on this project')

        exp = set(['bar@pingou.com', 'foo@bar.com', 'bar@bar.com'])
        out = pagure.lib.notify._get_emails_for_obj(iss)
        self.assertEqual(out, exp)

    @patch('pagure.lib.notify.smtplib.SMTP')
    def test_get_emails_for_obj_pr(self, mock_smtp):
        """ Test the _get_emails_for_obj method from pagure.lib.notify. """
        mock_smtp.return_value = MagicMock()

        tests.create_projects(self.session)

        # Create the project ns/test
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Create the PR
        repo = pagure.lib._get_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')
        self.assertEqual(repo.open_requests, 1)

        exp = set(['bar@pingou.com'])
        out = pagure.lib.notify._get_emails_for_obj(req)
        self.assertEqual(out, exp)

        # Comment on the ticket
        out = pagure.lib.add_pull_request_comment(
            self.session,
            request=req,
            commit=None,
            tree_id=None,
            filename=None,
            row=None,
            comment='This is a comment',
            user='foo',
            requestfolder=None,
            notify=False)
        self.assertEqual(out, 'Comment added')

        exp = set(['bar@pingou.com', 'foo@bar.com'])
        out = pagure.lib.notify._get_emails_for_obj(req)
        self.assertEqual(out, exp)

        # Create user `bar`
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar name',
            password='bar',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)
        self.session.commit()

        # Watch the pull-request
        out = pagure.lib.set_watch_obj(self.session, 'bar', req, True)
        self.assertEqual(out, 'You are now watching this pull-request')

        exp = set(['bar@pingou.com', 'foo@bar.com', 'bar@bar.com'])
        out = pagure.lib.notify._get_emails_for_obj(req)
        self.assertEqual(out, exp)

    @patch('pagure.lib.notify.smtplib.SMTP')
    def test_get_emails_for_obj_pr_watching_project(self, mock_smtp):
        """ Test the _get_emails_for_obj method from pagure.lib.notify. """
        mock_smtp.return_value = MagicMock()

        tests.create_projects(self.session)

        # Create the project ns/test
        item = pagure.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            namespace='ns',
            description='test project #1',
            hook_token='aaabbbcccdd',
        )
        item.close_status = ['Invalid', 'Insufficient data', 'Fixed']
        self.session.add(item)
        self.session.commit()

        # Create the PR
        repo = pagure.get_authorized_project(self.session, 'test')
        req = pagure.lib.new_pull_request(
            session=self.session,
            repo_from=repo,
            branch_from='master',
            repo_to=repo,
            branch_to='master',
            title='test pull-request',
            user='pingou',
            requestfolder=None,
        )
        self.session.commit()
        self.assertEqual(req.id, 1)
        self.assertEqual(req.title, 'test pull-request')
        self.assertEqual(repo.open_requests, 1)

        exp = set(['bar@pingou.com'])
        out = pagure.lib.notify._get_emails_for_obj(req)
        self.assertEqual(out, exp)

        # Comment on the ticket
        out = pagure.lib.add_pull_request_comment(
            self.session,
            request=req,
            commit=None,
            tree_id=None,
            filename=None,
            row=None,
            comment='This is a comment',
            user='foo',
            requestfolder=None,
            notify=False)
        self.assertEqual(out, 'Comment added')

        exp = set(['bar@pingou.com', 'foo@bar.com'])
        out = pagure.lib.notify._get_emails_for_obj(req)
        self.assertEqual(out, exp)

        # Create user `bar`
        item = pagure.lib.model.User(
            user='bar',
            fullname='bar name',
            password='bar',
            default_email='bar@bar.com',
        )
        self.session.add(item)
        item = pagure.lib.model.UserEmail(
            user_id=3,
            email='bar@bar.com')
        self.session.add(item)
        self.session.commit()

        # Watch the project
        repo = pagure.get_authorized_project(self.session, 'test')
        out = pagure.lib.update_watch_status(self.session, repo, 'bar', '1')
        self.assertEqual(
            out, 'You are now watching issues and PRs on this project')

        exp = set(['bar@pingou.com', 'foo@bar.com', 'bar@bar.com'])
        out = pagure.lib.notify._get_emails_for_obj(req)
        self.assertEqual(out, exp)

    @patch('pagure.lib.notify.smtplib.SMTP')
    def test_send_email(self, mock_smtp):
        """ Test the notify_new_comment method from pagure.lib.notify. """
        mock_smtp.return_value = MagicMock()

        email = pagure.lib.notify.send_email(
            'Email content',
            'Email “Subject“',
            'foo@bar.com,zöé@foo.net',
            mail_id='test-pull-request-2edbf96ebe644f4bb31b94605e-1',
            in_reply_to='test-pull-request-2edbf96ebe644f4bb31b94605e@pagure',
            project_name='namespace/project',
            user_from='Zöé',
        )
        exp = '''Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: base64
Subject: =?utf-8?b?W25hbWVzcGFjZS9wcm9qZWN0XSBFbWFpbCDigJxTdWJqZWN04oCc?=
From: =?utf-8?b?WsO2w6k=?= <pagure@pagure.org>
mail-id: test-pull-request-2edbf96ebe644f4bb31b94605e-1@pagure.org
Message-Id: <test-pull-request-2edbf96ebe644f4bb31b94605e-1@pagure.org>
In-Reply-To: <test-pull-request-2edbf96ebe644f4bb31b94605e@pagure>
X-Auto-Response-Suppress: All
X-pagure: https://pagure.org/
X-pagure-project: namespace/project
List-ID: namespace/project
List-Archive: https://pagure.org/namespace/project
To: zöé@foo.net
Reply-To: reply+819debcaa294a19ddedd9cfe0cb8faebb50d126adda0f02f203fce83824add55f2e640b75691d4a57cb95b25cc856b0815d1ad2a35ab358cda9de42e2b021957@pagure.org
Mail-Followup-To: reply+819debcaa294a19ddedd9cfe0cb8faebb50d126adda0f02f203fce83824add55f2e640b75691d4a57cb95b25cc856b0815d1ad2a35ab358cda9de42e2b021957@pagure.org

RW1haWwgY29udGVudA==
'''
        self.assertEqual(email.as_string(), exp)

        email = pagure.lib.notify.send_email(
            'Email content',
            'Email “Subject“',
            u'foo@bar.com,zöé@foo.net',
            mail_id='test-pull-request-2edbf96ebe644f4bb31b94605e-1',
            in_reply_to='test-pull-request-2edbf96ebe644f4bb31b94605e@pagure',
            project_name='namespace/project',
            user_from='Zöé',
        )
        self.assertEqual(email.as_string(), exp)


if __name__ == '__main__':
    unittest.main(verbosity=2)
