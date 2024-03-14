# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import sqlalchemy as sa
import os
import pygit2
import subprocess
import wtforms

try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from pagure.config import config as pagure_config
from pagure.hooks import BaseHook, BaseRunner, RequiredIf
from pagure.lib.model import BASE, Project


class MailTable(BASE):
    """Stores information about the mail hook deployed on a project.

    Table -- hook_mail
    """

    __tablename__ = "hook_mail"

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    mail_to = sa.Column(sa.Text, nullable=False)
    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        "Project",
        remote_side=[Project.id],
        backref=backref(
            "mail_hook",
            cascade="delete, delete-orphan",
            single_parent=True,
            uselist=False,
        ),
    )


class MailForm(FlaskForm):
    """ Form to configure the mail hook. """

    mail_to = wtforms.StringField("Mail to", [RequiredIf("active")])
    active = wtforms.BooleanField("Active", [wtforms.validators.Optional()])


class MailRunner(BaseRunner):
    @staticmethod
    def post_receive(
        session, username, project, repotype, repodir, changes, pull_request
    ):
        """Run the multimail post-receive hook.

        For args, see BaseRunner.runhook.
        """
        if repotype != "main":
            # This hook is only useful on the main repo
            return

        # This may run on a temporary clone, but that doesn't matter.
        # We set these options every time again anyway
        repo_obj = pygit2.Repository(repodir)
        repo_obj.config.set_multivar(
            "multimailhook.mailingList", "", project.mail_hook.mail_to
        )
        repo_obj.config.set_multivar(
            "multimailhook.environment", "", "gitolite"
        )
        repo_obj.config.set_multivar(
            "multimailhook.repoName", "", project.fullname
        )
        repo_obj.config.set_multivar("multimailhook.mailer", "", "smtp")
        repo_obj.config.set_multivar(
            "multimailhook.smtpServer", "", pagure_config["SMTP_SERVER"]
        )
        repo_obj.config.set_multivar(
            "multimailhook.smtpUser", "", pagure_config["SMTP_USERNAME"] or ""
        )
        repo_obj.config.set_multivar(
            "multimailhook.smtpPass", "", pagure_config["SMTP_PASSWORD"] or ""
        )
        repo_obj.config.set_multivar(
            "multimailhook.smtpEncryption",
            "",
            "tls" if pagure_config["SMTP_SSL"] else "none",
        )
        repo_obj.config.set_multivar(
            "multimailhook.from", "", pagure_config["FROM_EMAIL"]
        )

        # Now just run the .py file as a git hook
        hook_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "files",
            "git_multimail_upstream.py",
        )
        stdin = (
            "\n".join(
                [
                    "%s %s %s" % (changes[refname] + (refname,))
                    for refname in changes
                ]
            )
            + "\n"
        )

        proc = subprocess.Popen(
            [hook_file], cwd=repodir, stdin=subprocess.PIPE
        )
        proc.communicate(stdin.encode())
        ecode = proc.wait()
        if ecode != 0:
            print("git_multimail failed")
            raise Exception("git_multimail failed")


class Mail(BaseHook):
    """ Mail hooks. """

    name = "Mail"
    description = (
        "Generate notification emails for pushes to a git "
        "repository. This hook sends emails describing changes introduced "
        "by pushes to a git repository."
    )
    form = MailForm
    db_object = MailTable
    backref = "mail_hook"
    form_fields = ["mail_to", "active"]
    runner = MailRunner
