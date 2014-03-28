#-*- coding: utf-8 -*-

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


class AddIssueCommentForm(wtf.Form):
    ''' Form to add a comment to an issue. '''
    comment = wtforms.TextAreaField(
        'Comment<span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class UpdateIssueStatusForm(wtf.Form):
    ''' Form to update the status of an issue. '''
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
        super(UpdateIssueStatusForm, self).__init__(*args, **kwargs)
        if 'status' in kwargs:
            self.status.choices = [
                (status, status) for status in kwargs['status']
            ]
