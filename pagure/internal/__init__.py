# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

Internal endpoints.

"""

import flask

from functools import wraps

PV = flask.Blueprint('internal_ns', __name__, url_prefix='/pv')

import pagure
import pagure.forms
import pagure.lib
import pagure.ui.fork


def localonly(function):
    ''' Decorator used to check if the request is local or not.
    '''
    @wraps(function)
    def decorated_function(*args, **kwargs):
        ''' Wrapped function actually checking if the request is local.
        '''
        if flask.request.remote_addr not in [
                '127.0.0.1', 'localhost', '::1']:
            flask.abort(403)
        else:
            return function(*args, **kwargs)
    return decorated_function


@PV.route('/pull-request/comment/', methods=['PUT'])
@localonly
def pull_request_add_comment():
    """ Add a comment to a pull-request.
    """
    pform = pagure.forms.ProjectCommentForm(csrf_token=False)
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

    form = pagure.forms.AddPullRequestCommentForm(csrf_token=False)

    if not form.validate_on_submit():
        flask.abort(400, 'Invalid request')

    commit = form.commit.data
    filename= form.filename.data
    row = form.row.data
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
            requestfolder=APP.config['REQUESTS_FOLDER'],
        )
        pagure.SESSION.commit()
    except SQLAlchemyError, err:  # pragma: no cover
        pagure.SESSION.rollback()
        APP.logger.exception(err)
        flask.abort(400, 'Error when saving the request to the database')

    return flask.jsonify({'message': 'Comment added'})


@PV.route('/ticket/comment/', methods=['PUT'])
@localonly
def ticket_add_comment():
    """ Add a comment to a pull-request.
    """
    pform = pagure.forms.ProjectCommentForm(csrf_token=False)
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

    if issue.private and not is_repo_admin(issue.project) \
            and (
                not authenticated() or
                not issue.user.user == flask.g.fas_user.username):
        flask.abort(
            403, 'This issue is private and you are not allowed to view it')

    status = pagure.lib.get_issue_statuses(SESSION)
    form = pagure.forms.CommentForm(csrf_token=False)

    if not form.validate_on_submit():
        flask.abort(400, 'Invalid request')

    comment = form.comment.data

    try:
        message = pagure.lib.add_issue_comment(
            pagure.SESSION,
            issue=issue,
            comment=comment,
            user=useremail,
            ticketfolder=APP.config['TICKETS_FOLDER'],
            notify=True)
        pagure.SESSION.commit()
    except SQLAlchemyError, err:  # pragma: no cover
        pagure.SESSION.rollback()
        APP.logger.exception(err)
        flask.abort(400, 'Error when saving the request to the database')

    return flask.jsonify({'message': 'Comment added'})
