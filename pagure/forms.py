# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-few-public-methods
# pylint: disable=no-init
# pylint: disable=super-on-old-class

import re

import flask
import flask_wtf as wtf
try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm

import wtforms
import tempfile

import pagure
import pagure.lib


STRICT_REGEX = '^[a-zA-Z0-9-_]+$'
TAGS_REGEX = '^[a-zA-Z0-9-_, .]+$'
PROJECT_NAME_REGEX = \
    '^[a-zA-z0-9_][a-zA-Z0-9-_]*$'


class MultipleEmail(wtforms.validators.Email):
    """ Split the value by comma and run them through the email validator
    of wtforms.
    """
    def __call__(self, form, field):
        regex = re.compile(r'^.+@[^.].*\.[a-z]{2,10}$', re.IGNORECASE)
        message = field.gettext('One or more invalid email address.')
        for data in field.data.split(','):
            data = data.strip()
            if not self.regex.match(data or ''):
                raise wtforms.validators.ValidationError(message)


def file_virus_validator(form, field):
    if not pagure.APP.config['VIRUS_SCAN_ATTACHMENTS']:
        return
    from pyclamd import ClamdUnixSocket

    if field.name not in flask.request.files or \
            flask.request.files[field.name].filename == '':
        # If no file was uploaded, this field is correct
        return
    uploaded = flask.request.files[field.name]
    clam = ClamdUnixSocket()
    if not clam.ping():
        raise wtforms.ValidationError(
            'Unable to communicate with virus scanner')
    results = clam.scan_stream(uploaded.stream.read())
    if results is None:
        uploaded.stream.seek(0)
        return
    else:
        result = results.values()
        res_type, res_msg = result
        if res_type == 'FOUND':
            raise wtforms.ValidationError('Virus found: %s' % res_msg)
        else:
            raise wtforms.ValidationError('Error scanning uploaded file')


def ssh_key_validator(form, field):
    if not pagure.lib.are_valid_ssh_keys(field.data):
        raise wtforms.ValidationError('Invalid SSH keys')


class ProjectFormSimplified(FlaskForm):
    ''' Form to edit the description of a project. '''
    description = wtforms.TextField(
        'Description <span class="error">*</span>',
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
        [
            wtforms.validators.optional(),
            wtforms.validators.Length(max=255),
        ]
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
    create_readme = wtforms.BooleanField(
        'Create README',
        [wtforms.validators.optional()],
    )
    namespace = wtforms.SelectField(
        'Project Namespace',
        [wtforms.validators.optional()],
        choices=[],
        coerce=lambda val: unicode(val) if val else None
    )

    def __init__(self, *args, **kwargs):
        """ Calls the default constructor with the normal argument but
        uses the list of collection provided to fill the choices of the
        drop-down list.
        """
        super(ProjectForm, self).__init__(*args, **kwargs)
        if 'namespaces' in kwargs:
            self.namespace.choices = [
                (namespace, namespace) for namespace in kwargs['namespaces']
            ]
            self.namespace.choices.insert(0, ('', ''))


class IssueFormSimplied(FlaskForm):
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
        choices=[]
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


class RequestPullForm(FlaskForm):
    ''' Form to create a request pull. '''
    title = wtforms.TextField(
        'Title<span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    initial_comment = wtforms.TextAreaField(
        'Initial Comment', [wtforms.validators.Optional()])


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


class AddIssueTagForm(FlaskForm):
    ''' Form to add a comment to an issue. '''
    tag = wtforms.TextField(
        'tag',
        [
            wtforms.validators.Optional(),
            wtforms.validators.Regexp(TAGS_REGEX, flags=re.IGNORECASE),
            wtforms.validators.Length(max=255),
        ]
    )


class StatusForm(FlaskForm):
    ''' Form to add/change the status of an issue. '''
    status = wtforms.SelectField(
        'Status',
        [wtforms.validators.Required()],
        choices=[]
    )
    close_status = wtforms.SelectField(
        'Closed as',
        [wtforms.validators.Optional()],
        choices=[]
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
        self.close_status.choices = []
        if 'close_status' in kwargs:
            for key in sorted(kwargs['close_status']):
                self.close_status.choices.append((key, key))
            self.close_status.choices.insert(0, ('', ''))


class NewTokenForm(FlaskForm):
    ''' Form to add/change the status of an issue. '''
    acls = wtforms.SelectMultipleField(
        'ACLs',
        [wtforms.validators.Required()],
        choices=[]
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



class UpdateIssueForm(FlaskForm):
    ''' Form to add a comment to an issue. '''
    tag = wtforms.TextField(
        'tag',
        [
            wtforms.validators.Optional(),
            wtforms.validators.Regexp(TAGS_REGEX, flags=re.IGNORECASE),
            wtforms.validators.Length(max=255),
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
        choices=[]
    )
    priority = wtforms.SelectField(
        'Priority',
        [wtforms.validators.Optional()],
        choices=[]
    )
    milestone = wtforms.SelectField(
        'Milestone',
        [wtforms.validators.Optional()],
        choices=[],
        coerce=lambda val: unicode(val) if val else None
    )
    private = wtforms.BooleanField(
        'Private',
        [wtforms.validators.optional()],
    )
    close_status = wtforms.SelectField(
        'Closed as',
        [wtforms.validators.Optional()],
        choices=[],
        coerce=lambda val: unicode(val) if val else None
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

        self.priority.choices = []
        if 'priorities' in kwargs:
            for key in sorted(kwargs['priorities']):
                self.priority.choices.append(
                    (key, kwargs['priorities'][key])
                )

        self.milestone.choices = []
        if 'milestones' in kwargs and kwargs['milestones']:
            for key in sorted(kwargs['milestones']):
                self.milestone.choices.append((key, key))
            self.milestone.choices.insert(0, ('', ''))

        self.close_status.choices = []
        if 'close_status' in kwargs:
            for key in sorted(kwargs['close_status']):
                self.close_status.choices.append((key, key))
            self.close_status.choices.insert(0, ('', ''))


class AddPullRequestCommentForm(FlaskForm):
    ''' Form to add a comment to a pull-request. '''
    commit = wtforms.HiddenField('commit identifier')
    filename = wtforms.HiddenField('file changed')
    row = wtforms.HiddenField('row')
    requestid = wtforms.HiddenField('requestid')
    tree_id = wtforms.HiddenField('treeid')
    comment = wtforms.TextAreaField(
        'Comment<span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class AddPullRequestFlagForm(FlaskForm):
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


class UserSettingsForm(FlaskForm):
    ''' Form to create or edit project. '''
    ssh_key = wtforms.TextAreaField(
        'Public SSH key <span class="error">*</span>',
        [wtforms.validators.Required(),
         ssh_key_validator]
    )


class AddUserForm(FlaskForm):
    ''' Form to add a user to a project. '''
    user = wtforms.TextField(
        'Username <span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class AssignIssueForm(FlaskForm):
    ''' Form to assign an user to an issue. '''
    assignee = wtforms.TextField(
        'Assignee <span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class AddGroupForm(FlaskForm):
    ''' Form to add a group to a project. '''
    group = wtforms.TextField(
        'Group <span class="error">*</span>',
        [
            wtforms.validators.Required(),
            wtforms.validators.Regexp(STRICT_REGEX, flags=re.IGNORECASE)
        ]
    )


class ConfirmationForm(FlaskForm):
    ''' Simple form used just for CSRF protection. '''
    pass


class UploadFileForm(FlaskForm):
    ''' Form to upload a file. '''
    filestream = wtforms.FileField(
        'File',
        [wtforms.validators.Required(), file_virus_validator])


class UserEmailForm(FlaskForm):
    ''' Form to edit the description of a project. '''
    email = wtforms.TextField(
        'email', [wtforms.validators.Required()]
    )

    def __init__(self, *args, **kwargs):
        super(UserEmailForm, self).__init__(*args, **kwargs)
        if 'emails' in kwargs:
            if kwargs['emails']:
                self.email.validators.append(
                    wtforms.validators.NoneOf(kwargs['emails'])
                )
        else:
            self.email.validators = [wtforms.validators.Required()]


class ProjectCommentForm(FlaskForm):
    ''' Form to represent project. '''
    objid = wtforms.TextField(
        'Ticket/Request id',
        [wtforms.validators.Required()]
    )
    useremail = wtforms.TextField(
        'Email',
        [wtforms.validators.Required()]
    )


class CommentForm(FlaskForm):
    ''' Form to upload a file. '''
    comment = wtforms.FileField(
        'Comment',
        [wtforms.validators.Required(), file_virus_validator])


class EditGroupForm(FlaskForm):
    """ Form to ask for a password change. """
    display_name = wtforms.TextField(
        'Group name to display',
        [
            wtforms.validators.Required(),
            wtforms.validators.Length(max=255),
        ]
    )
    description = wtforms.TextField(
        'Description',
        [
            wtforms.validators.Required(),
            wtforms.validators.Length(max=255),
        ]
    )


class NewGroupForm(EditGroupForm):
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
        choices=[]
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


class EditFileForm(FlaskForm):
    """ Form used to edit a file. """
    content = wtforms.TextAreaField(
        'content', [wtforms.validators.Required()])
    commit_title = wtforms.TextField(
        'Title', [wtforms.validators.Required()])
    commit_message = wtforms.TextAreaField(
        'Commit message', [wtforms.validators.optional()])
    email = wtforms.SelectField(
        'Email', [wtforms.validators.Required()],
        choices=[]
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


class DefaultBranchForm(FlaskForm):
    """Form to change the default branh for a repository"""
    branches = wtforms.SelectField(
        'default_branch',
        [wtforms.validators.Required()],
        choices=[]
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


class EditCommentForm(FlaskForm):
    """ Form to verify that comment is not empty
    """
    update_comment = wtforms.TextAreaField(
        'Comment<span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class ForkRepoForm(FlaskForm):
    ''' Form to fork a project in the API. '''
    repo = wtforms.TextField(
        'The project name',
        [wtforms.validators.Required()]
    )
    username = wtforms.TextField(
        'User who forked the project',
        [wtforms.validators.optional()])
    namespace = wtforms.TextField(
        'The project namespace',
        [wtforms.validators.optional()]
    )


class AddReportForm(FlaskForm):
    """ Form to verify that comment is not empty
    """
    report_name = wtforms.TextAreaField(
        'Report name<span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class PublicNotificationForm(FlaskForm):
    """ Form to verify that comment is not empty
    """
    issue_notifs = wtforms.TextAreaField(
        'Public issue notification<span class="error">*</span>',
        [wtforms.validators.optional(), MultipleEmail()]
    )

    pr_notifs = wtforms.TextAreaField(
        'Public PR notification<span class="error">*</span>',
        [wtforms.validators.optional(), MultipleEmail()]
    )
