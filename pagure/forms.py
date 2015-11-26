# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import re
from flask.ext import wtf
import wtforms
# pylint: disable=R0903,W0232,E1002


STRICT_REGEX = '^[a-zA-Z0-9-_]+$'
TAGS_REGEX = '^[a-zA-Z0-9-_, .]+$'
PROJECT_NAME_REGEX = '^[a-zA-z0-9_][a-zA-Z0-9-_]+$'


class ProjectFormSimplified(wtf.Form):
    ''' Form to edit the description of a project. '''
    description = wtforms.TextField(
        'description <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    url = wtforms.TextField(
        'URL',
        [wtforms.validators.optional()]
    )
    avatar_email = wtforms.TextField(
        'Avatar email',
        [wtforms.validators.optional()]
    )
    tags = wtforms.TextField(
        'Project tags',
        [wtforms.validators.optional()]
    )


class ProjectForm(ProjectFormSimplified):
    ''' Form to create or edit project. '''
    name = wtforms.TextField(
        'Project name <span class="error">*</span>',
        [
            wtforms.validators.Required(),
            wtforms.validators.Regexp(PROJECT_NAME_REGEX, flags=re.IGNORECASE)
        ]
    )


class IssueFormSimplied(wtf.Form):
    ''' Form to create or edit an issue. '''
    title = wtforms.TextField(
        'Title<span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    issue_content = wtforms.TextAreaField(
        'Content<span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    private = wtforms.BooleanField(
        'Private',
        [wtforms.validators.optional()],
    )


class IssueForm(IssueFormSimplied):
    ''' Form to create or edit an issue. '''
    status = wtforms.SelectField(
        'Status',
        [wtforms.validators.Required()],
        choices=[(item, item) for item in []]
    )

    def __init__(self, *args, **kwargs):
        """ Calls the default constructor with the normal argument but
        uses the list of collection provided to fill the choices of the
        drop-down list.
        """
        super(IssueForm, self).__init__(*args, **kwargs)
        if 'status' in kwargs:
            self.status.choices = [
                (status, status) for status in kwargs['status']
            ]


class RequestPullForm(wtf.Form):
    ''' Form to create a request pull. '''
    title = wtforms.TextField(
        'Title<span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class RemoteRequestPullForm(RequestPullForm):
    ''' Form to create a remote request pull. '''
    git_repo = wtforms.TextField(
        'Git repo address<span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    branch_from = wtforms.TextField(
        'Git branch<span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    branch_to = wtforms.TextField(
        'Git branch to merge in<span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class AddIssueTagForm(wtf.Form):
    ''' Form to add a comment to an issue. '''
    tag = wtforms.TextField(
        'tag',
        [
            wtforms.validators.Optional(),
            wtforms.validators.Regexp(TAGS_REGEX, flags=re.IGNORECASE)
        ]
    )


class StatusForm(wtf.Form):
    ''' Form to add/change the status of an issue. '''
    status = wtforms.SelectField(
        'Status',
        [wtforms.validators.Required()],
        choices=[(item, item) for item in []]
    )

    def __init__(self, *args, **kwargs):
        """ Calls the default constructor with the normal argument but
        uses the list of collection provided to fill the choices of the
        drop-down list.
        """
        super(StatusForm, self).__init__(*args, **kwargs)
        if 'status' in kwargs:
            self.status.choices = [
                (status, status) for status in kwargs['status']
            ]


class NewTokenForm(wtf.Form):
    ''' Form to add/change the status of an issue. '''
    acls = wtforms.SelectMultipleField(
        'ACLs',
        [wtforms.validators.Required()],
        choices=[(item, item) for item in []]
    )

    def __init__(self, *args, **kwargs):
        """ Calls the default constructor with the normal argument but
        uses the list of collection provided to fill the choices of the
        drop-down list.
        """
        super(NewTokenForm, self).__init__(*args, **kwargs)
        if 'acls' in kwargs:
            self.acls.choices = [
                (acl.name, acl.name) for acl in kwargs['acls']
            ]


class UpdateIssueForm(wtf.Form):
    ''' Form to add a comment to an issue. '''
    tag = wtforms.TextField(
        'tag',
        [
            wtforms.validators.Optional(),
            wtforms.validators.Regexp(TAGS_REGEX, flags=re.IGNORECASE)
        ]
    )
    depends = wtforms.TextField(
        'dependency issue', [wtforms.validators.Optional()]
    )
    blocks = wtforms.TextField(
        'blocked issue', [wtforms.validators.Optional()]
    )
    comment = wtforms.TextAreaField(
        'Comment', [wtforms.validators.Optional()]
    )
    assignee = wtforms.TextAreaField(
        'Assigned to', [wtforms.validators.Optional()]
    )
    status = wtforms.SelectField(
        'Status',
        [wtforms.validators.Optional()],
        choices=[(item, item) for item in []]
    )

    def __init__(self, *args, **kwargs):
        """ Calls the default constructor with the normal argument but
        uses the list of collection provided to fill the choices of the
        drop-down list.
        """
        super(UpdateIssueForm, self).__init__(*args, **kwargs)
        if 'status' in kwargs:
            self.status.choices = [
                (status, status) for status in kwargs['status']
            ]


class AddPullRequestCommentForm(wtf.Form):
    ''' Form to add a comment to a pull-request. '''
    commit = wtforms.HiddenField('commit identifier')
    filename = wtforms.HiddenField('file changed')
    row = wtforms.HiddenField('row')
    requestid = wtforms.HiddenField('requestid')
    comment = wtforms.TextAreaField(
        'Comment<span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class AddPullRequestFlagForm(wtf.Form):
    ''' Form to add a flag to a pull-request. '''
    username = wtforms.TextField(
        'Username', [wtforms.validators.Required()])
    percent = wtforms.TextField(
        'Percentage of completion', [wtforms.validators.Required()])
    comment = wtforms.TextAreaField(
        'Comment', [wtforms.validators.Required()])
    url = wtforms.TextField(
        'URL', [wtforms.validators.Required()])
    uid = wtforms.TextField(
        'UID', [wtforms.validators.optional()])


class UserSettingsForm(wtf.Form):
    ''' Form to create or edit project. '''
    ssh_key = wtforms.TextAreaField(
        'Public ssh key <span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class AddUserForm(wtf.Form):
    ''' Form to add a user to a project. '''
    user = wtforms.TextField(
        'Username <span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class AddGroupForm(wtf.Form):
    ''' Form to add a group to a project. '''
    group = wtforms.TextField(
        'Group <span class="error">*</span>',
        [
            wtforms.validators.Required(),
            wtforms.validators.Regexp(STRICT_REGEX, flags=re.IGNORECASE)
        ]
    )


class ConfirmationForm(wtf.Form):
    ''' Simple form used just for CSRF protection. '''
    pass


class UploadFileForm(wtf.Form):
    ''' Form to upload a file. '''
    filestream = wtforms.FileField(
        'File',
        [wtforms.validators.Required()])


class UserEmailForm(wtf.Form):
    ''' Form to edit the description of a project. '''
    email = wtforms.TextField(
        'email', [wtforms.validators.Required()]
    )


class ProjectCommentForm(wtf.Form):
    ''' Form to represent project. '''
    objid = wtforms.TextField(
        'Ticket/Request id',
        [wtforms.validators.Required()]
    )
    useremail = wtforms.TextField(
        'Email',
        [wtforms.validators.Required()]
    )


class CommentForm(wtf.Form):
    ''' Form to upload a file. '''
    comment = wtforms.FileField(
        'Comment',
        [wtforms.validators.Required()])


class NewGroupForm(wtf.Form):
    """ Form to ask for a password change. """
    group_name = wtforms.TextField(
        'Group name  <span class="error">*</span>',
        [
            wtforms.validators.Required(),
            wtforms.validators.Length(max=16),
            wtforms.validators.Regexp(STRICT_REGEX, flags=re.IGNORECASE)
        ]
    )
    group_type = wtforms.SelectField(
        'Group type',
        [wtforms.validators.Required()],
        choices=[(item, item) for item in []]
    )

    def __init__(self, *args, **kwargs):
        """ Calls the default constructor with the normal argument but
        uses the list of collection provided to fill the choices of the
        drop-down list.
        """
        super(NewGroupForm, self).__init__(*args, **kwargs)
        if 'group_types' in kwargs:
            self.group_type.choices = [
                (grptype, grptype) for grptype in kwargs['group_types']
            ]


class EditFileForm(wtf.Form):
    """ Form used to edit a file. """
    content = wtforms.TextAreaField(
        'content', [wtforms.validators.Required()])
    commit_title = wtforms.TextField(
        'Title', [wtforms.validators.Required()])
    commit_message = wtforms.TextAreaField(
        'Commit message', [wtforms.validators.optional()])
    email = wtforms.SelectField(
        'Email', [wtforms.validators.Required()],
        choices=[(item, item) for item in []]
    )
    branch = wtforms.TextField(
        'Branch', [wtforms.validators.Required()])

    def __init__(self, *args, **kwargs):
        """ Calls the default constructor with the normal argument but
        uses the list of collection provided to fill the choices of the
        drop-down list.
        """
        super(EditFileForm, self).__init__(*args, **kwargs)
        if 'emails' in kwargs:
            self.email.choices = [
                (email.email, email.email) for email in kwargs['emails']
            ]


class DefaultBranchForm(wtf.Form):
    """Form to change the default branh for a repository"""
    branches = wtforms.SelectField(
        'default_branch',
        [wtforms.validators.Required()],
        choices=[(item, item) for item in []]
    )

    def __init__(self, *args, **kwargs):
        """ Calls the default constructor with the normal argument but
        uses the list of collection provided to fill the choices of the
        drop-down list.
        """
        super(DefaultBranchForm, self).__init__(*args, **kwargs)
        if 'branches' in kwargs:
            self.branches.choices = [
                (branch, branch) for branch in kwargs['branches']
            ]

class EditCommentForm(wtf.Form):
    """ Form to verify that comment is not empty
    """
    update_comment = wtforms.TextAreaField(
        'Comment<span class="error">*</span>',
        [wtforms.validators.Required()]
    )
