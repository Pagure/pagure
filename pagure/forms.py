# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from flask.ext import wtf
import wtforms


class ProjectForm(wtf.Form):
    ''' Form to create or edit project. '''
    name = wtforms.TextField(
        'Project name <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    description = wtforms.TextField(
        'description',
        [wtforms.validators.optional()]
    )


class IssueForm(wtf.Form):
    ''' Form to create or edit an issue. '''
    title = wtforms.TextField(
        'Title<span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    issue_content = wtforms.TextAreaField(
        'Content<span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    status = wtforms.SelectField(
        'Status',
        [wtforms.validators.Required()],
        choices=[(item, item) for item in []]
    )
    private = wtforms.BooleanField(
        'Private',
        [wtforms.validators.optional()],
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


class AddIssueTagForm(wtf.Form):
    ''' Form to add a comment to an issue. '''
    tag = wtforms.TextField(
        'tag', [wtforms.validators.Optional()]
    )


class UpdateIssueForm(wtf.Form):
    ''' Form to add a comment to an issue. '''
    tag = wtforms.TextField(
        'tag', [wtforms.validators.Optional()]
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


class DescriptionForm(wtf.Form):
    ''' Form to edit the description of a project. '''
    description = wtforms.TextField(
        'description <span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class ConfirmationForm(wtf.Form):
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
    project = wtforms.TextField(
        'Project',
        [wtforms.validators.Required()]
    )
    username = wtforms.TextField(
        'Username',
        [wtforms.validators.Optional()]
    )
    objid = wtforms.TextField(
        'Ticket/Request id',
        [wtforms.validators.Required()]
    )
    useremail = wtforms.TextField(
        'Email',
        [wtforms.validators.Required()]
    )
