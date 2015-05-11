# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask

import pagure
import pagure.lib
from pagure import APP, SESSION
from pagure.api import API, api_login_required, API_ERROR_CODE


@API.route('/<repo>/new_issue', methods=['POST'])
@API.route('/fork/<username>/<repo>/new_issue', methods=['POST'])
@api_login_required(acls=['create_issue'])
def new_issue(repo, username=None):
    """ Create a new issue
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

    if repo is None:
        output['error_code'] = 1
        output['error'] = API_ERROR_CODE[1]
        jsonout = flask.jsonify(output)
        jsonout.status_code = 404
        return jsonout

    if not repo.settings.get('issue_tracker', True):
        output['error_code'] = 2
        output['error'] = API_ERROR_CODE[2]
        jsonout = flask.jsonify(output)
        jsonout.status_code = 404
        return jsonout

    status = pagure.lib.get_issue_statuses(SESSION)
    form = pagure.forms.IssueForm(status=status, csrf_token=False)
    if form.validate_on_submit():
        title = form.title.data
        content = form.issue_content.data
        private = form.private.data

        try:
            issue = pagure.lib.new_issue(
                SESSION,
                repo=repo,
                title=title,
                content=content,
                private=private or False,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
            )
            SESSION.commit()
            # If there is a file attached, attach it.
            filestream = flask.request.files.get('filestream')
            if filestream and '<!!image>' in issue.content:
                new_filename = pagure.lib.git.add_file_to_git(
                    repo=repo,
                    issue=issue,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                    user=flask.g.fas_user,
                    filename=filestream.filename,
                    filestream=filestream.stream,
                )
                # Replace the <!!image> tag in the comment with the link
                # to the actual image
                filelocation = flask.url_for(
                    'view_issue_raw_file',
                    repo=repo.name,
                    username=username,
                    filename=new_filename,
                )
                new_filename = new_filename.split('-', 1)[1]
                url = '[![%s](%s)](%s)' % (
                    new_filename, filelocation, filelocation)
                issue.content = issue.content.replace('<!!image>', url)
                SESSION.add(issue)
                SESSION.commit()

            output['message'] = 'issue created'
            output['message'] = 'issue created'
        except pagure.exceptions.PagureException, err:
            output['error_code'] = 0
            output['error'] = str(err)
            httpcode = 400
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            output['error_code'] = 3
            output['error'] = API_ERROR_CODE[3]
            httpcode = 400
    else:
        output['error_code'] = 4
        output['error'] = API_ERROR_CODE[4]
        httpcode = 400

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout
