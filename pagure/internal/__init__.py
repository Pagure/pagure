# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

Internal endpoints.

"""

import shutil
import tempfile

import flask
import pygit2

from functools import wraps
from sqlalchemy.exc import SQLAlchemyError

PV = flask.Blueprint('internal_ns', __name__, url_prefix='/pv')

import pagure
import pagure.forms
import pagure.lib
import pagure.lib.git
import pagure.ui.fork
from pagure import is_repo_admin, authenticated


MERGE_OPTIONS = {
    'NO_CHANGE': {
        'short_code': 'No changes',
        'message': 'Nothing to change, git is up to date'
    },
    'FFORWARD': {
        'short_code': 'Ok',
        'message': 'The pull-request can be merged and fast-forwarded'
    },
    'CONFLICTS': {
        'short_code': 'Conflicts',
        'message': 'The pull-request cannot be merged due to conflicts'
    },
    'MERGE': {
        'short_code': 'With merge',
        'message': 'The pull-request can be merged with a merge commit'
    }
}

# pylint: disable=E1101


def localonly(function):
    ''' Decorator used to check if the request is local or not.
    '''
    @wraps(function)
    def decorated_function(*args, **kwargs):
        ''' Wrapped function actually checking if the request is local.
        '''
        ip_allowed = pagure.APP.config.get(
            'IP_ALLOWED_INTERNAL', ['127.0.0.1', 'localhost', '::1'])
        if flask.request.remote_addr not in ip_allowed:
            flask.abort(403)
        else:
            return function(*args, **kwargs)
    return decorated_function


@PV.route('/pull-request/comment/', methods=['PUT'])
@localonly
def pull_request_add_comment():
    """ Add a comment to a pull-request.
    """
    pform = pagure.forms.ProjectCommentForm(csrf_enabled=False)
    if not pform.validate_on_submit():
        flask.abort(400, 'Invalid request')

    objid = pform.objid.data
    useremail = pform.useremail.data

    request = pagure.lib.get_request_by_uid(
        pagure.SESSION,
        request_uid=objid,
    )

    if not request:
        flask.abort(404, 'Pull-request not found')

    form = pagure.forms.AddPullRequestCommentForm(csrf_enabled=False)

    if not form.validate_on_submit():
        flask.abort(400, 'Invalid request')

    commit = form.commit.data or None
    filename = form.filename.data or None
    row = form.row.data or None
    comment = form.comment.data

    try:
        message = pagure.lib.add_pull_request_comment(
            pagure.SESSION,
            request=request,
            commit=commit,
            filename=filename,
            row=row,
            comment=comment,
            user=useremail,
            requestfolder=pagure.APP.config['REQUESTS_FOLDER'],
        )
        pagure.SESSION.commit()
    except SQLAlchemyError, err:  # pragma: no cover
        pagure.SESSION.rollback()
        pagure.APP.logger.exception(err)
        flask.abort(500, 'Error when saving the request to the database')

    return flask.jsonify({'message': message})


@PV.route('/ticket/comment/', methods=['PUT'])
@localonly
def ticket_add_comment():
    """ Add a comment to a pull-request.
    """
    pform = pagure.forms.ProjectCommentForm(csrf_enabled=False)
    if not pform.validate_on_submit():
        flask.abort(400, 'Invalid request')

    objid = pform.objid.data
    useremail = pform.useremail.data

    issue = pagure.lib.get_issue_by_uid(
        pagure.SESSION,
        issue_uid=objid
    )

    if issue is None:
        flask.abort(404, 'Issue not found')

    user_obj = pagure.lib.search_user(pagure.SESSION, email=useremail)
    admin = False
    if user_obj:
        admin = user_obj == issue.project.user.user or (
            user_obj in [user.user for user in issue.project.users])

    if issue.private and user_obj and not admin \
            and not issue.user.user == user_obj.username:
        flask.abort(
            403, 'This issue is private and you are not allowed to view it')

    form = pagure.forms.CommentForm(csrf_enabled=False)

    if not form.validate_on_submit():
        flask.abort(400, 'Invalid request')

    comment = form.comment.data

    try:
        message = pagure.lib.add_issue_comment(
            pagure.SESSION,
            issue=issue,
            comment=comment,
            user=useremail,
            ticketfolder=pagure.APP.config['TICKETS_FOLDER'],
            notify=True)
        pagure.SESSION.commit()
    except SQLAlchemyError, err:  # pragma: no cover
        pagure.SESSION.rollback()
        pagure.APP.logger.exception(err)
        flask.abort(500, 'Error when saving the request to the database')

    return flask.jsonify({'message': message})


@PV.route('/pull-request/merge', methods=['POST'])
def mergeable_request_pull():
    """ Returns if the specified pull-request can be merged or not.
    """
    force = flask.request.form.get('force', False)
    if force is not False:
        force = True

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.abort(400, 'Invalid input submitted')

    requestid = flask.request.form.get('requestid')

    request = pagure.lib.get_request_by_uid(
        pagure.SESSION, request_uid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if request.merge_status and not force:
        return flask.jsonify({
            'code': request.merge_status,
            'short_code': MERGE_OPTIONS[request.merge_status]['short_code'],
            'message': MERGE_OPTIONS[request.merge_status]['message']})

    try:
        merge_status = pagure.lib.git.merge_pull_request(
            session=pagure.SESSION,
            request=request,
            username=None,
            request_folder=None,
            domerge=False)
    except pygit2.GitError as err:
        flask.abort(409, err.message)
    except pagure.exceptions.PagureException as err:
        flask.abort(500, err.message)

    return flask.jsonify({
        'code': merge_status,
        'short_code': MERGE_OPTIONS[merge_status]['short_code'],
        'message': MERGE_OPTIONS[merge_status]['message']})
