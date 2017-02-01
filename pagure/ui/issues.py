# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-branches
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements


import datetime
import flask
import os
import re
from collections import defaultdict
from math import ceil

import filelock
import pygit2
import werkzeug.datastructures
from sqlalchemy.exc import SQLAlchemyError
from binaryornot.helpers import is_binary_string

import kitchen.text.converters as ktc
import mimetypes

import pagure.doc_utils
import pagure.exceptions
import pagure.lib
import pagure.lib.encoding_utils
import pagure.forms
from pagure import (APP, SESSION, LOG, __get_file_in_tree,
                    login_required, authenticated, urlpattern)


# URLs


@APP.route(
    '/<repo>/issue/<int:issueid>/update/',
    methods=['GET', 'POST'])
@APP.route(
    '/<repo>/issue/<int:issueid>/update',
    methods=['GET', 'POST'])
@APP.route(
    '/<namespace>/<repo>/issue/<int:issueid>/update/',
    methods=['GET', 'POST'])
@APP.route(
    '/<namespace>/<repo>/issue/<int:issueid>/update',
    methods=['GET', 'POST'])
@APP.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/update/',
    methods=['GET', 'POST'])
@APP.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/update',
    methods=['GET', 'POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/update/',
    methods=['GET', 'POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/update',
    methods=['GET', 'POST'])
@login_required
def update_issue(repo, issueid, username=None, namespace=None):
    ''' Add a comment to an issue. '''
    is_js = flask.request.args.get('js', False)

    repo = flask.g.repo

    if flask.request.method == 'GET':
        if not is_js:
            flask.flash('Invalid method: GET', 'error')
        return flask.redirect(flask.url_for(
            'view_issue', username=username, repo=repo.name,
            namespace=repo.namespace, issueid=issueid))

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if issue.private and not flask.g.repo_admin \
            and (not authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        flask.abort(
            403, 'This issue is private and you are not allowed to view it')

    if flask.request.form.get('edit_comment'):
        commentid = flask.request.form.get('edit_comment')
        form = pagure.forms.EditCommentForm()
        if form.validate_on_submit():
            return edit_comment_issue(
                repo.name, issueid, commentid, username=username)

    status = pagure.lib.get_issue_statuses(SESSION)
    form = pagure.forms.UpdateIssueForm(
        status=status,
        priorities=repo.priorities,
        milestones=repo.milestones,
        close_status=repo.close_status,
    )

    if form.validate_on_submit():
        repo_admin = flask.g.repo_admin

        if flask.request.form.get('drop_comment'):
            commentid = flask.request.form.get('drop_comment')

            comment = pagure.lib.get_issue_comment(
                SESSION, issue.uid, commentid)
            if comment is None or comment.issue.project != repo:
                flask.abort(404, 'Comment not found')

            if (flask.g.fas_user.username != comment.user.username
                    or comment.parent.status != 'Open') \
                    and not flask.g.repo_admin:
                flask.abort(
                    403,
                    'You are not allowed to remove this comment from '
                    'this issue')

            issue.last_updated = datetime.datetime.utcnow()
            SESSION.add(issue)
            SESSION.delete(comment)
            try:
                SESSION.commit()
                if not is_js:
                    flask.flash('Comment removed')
            except SQLAlchemyError as err:  # pragma: no cover
                is_js = False
                SESSION.rollback()
                LOG.error(err)
                if not is_js:
                    flask.flash(
                        'Could not remove the comment: %s' % commentid,
                        'error')
            if is_js:
                return 'ok'
            else:
                return flask.redirect(flask.url_for(
                    'view_issue', username=username, repo=repo.name,
                    namespace=repo.namespace, issueid=issueid))

        comment = form.comment.data
        depends = []
        for depend in form.depends.data.split(','):
            if depend.strip():
                try:
                    depends.append(int(depend.strip()))
                except ValueError:
                    pass

        blocks = []
        for block in form.blocks.data.split(','):
            if block.strip():
                try:
                    blocks.append(int(block.strip()))
                except ValueError:
                    pass

        assignee = form.assignee.data.strip() or None
        new_status = form.status.data.strip() or None
        close_status = form.close_status.data or None
        if new_status != 'Closed':
            close_status = None
        if close_status not in repo.close_status:
            close_status = None

        new_priority = None
        try:
            new_priority = int(form.priority.data)
        except:
            pass
        tags = [
            tag.strip()
            for tag in form.tag.data.split(',')
            if tag.strip()]

        new_milestone = None
        try:
            if repo.milestones:
                new_milestone = form.milestone.data.strip() or None
        except:
            pass

        try:
            messages = set()

            # New comment
            if comment:
                message = pagure.lib.add_issue_comment(
                    SESSION,
                    issue=issue,
                    comment=comment,
                    user=flask.g.fas_user.username,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                )
                SESSION.commit()
                if message and not is_js:
                    messages.add(message)

            # The status field can be updated by both the admin and the
            # person who opened the ticket.
            # Update status
            if repo_admin or flask.g.fas_user.username == issue.user.user:
                if new_status in status:
                    message = pagure.lib.edit_issue(
                        SESSION,
                        issue=issue,
                        status=new_status,
                        close_status=close_status,
                        private=issue.private,
                        user=flask.g.fas_user.username,
                        ticketfolder=APP.config['TICKETS_FOLDER'],
                    )
                    SESSION.commit()
                    if message:
                        messages.add(message)

            # All the other meta-data can be changed only by admins
            # while other field will be missing for non-admin and thus
            # reset if we let them
            if repo_admin:
                # Adjust (add/remove) tags
                messages.union(set(pagure.lib.update_tags(
                    SESSION, issue, tags,
                    username=flask.g.fas_user.username,
                    ticketfolder=APP.config['TICKETS_FOLDER']
                )))

            # The meta-data can be changed by admins and issue creator,
            # where issue creators can only change status of their issue while
            # other fields will be missing for non-admin and thus reset if we let them
            if repo_admin:
                # Assign or update assignee of the ticket
                message = pagure.lib.add_issue_assignee(
                    SESSION,
                    issue=issue,
                    assignee=assignee or None,
                    user=flask.g.fas_user.username,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                )
                SESSION.commit()
                if message and message != 'Nothing to change':
                    messages.add(message)

                # Update priority
                if str(new_priority) in repo.priorities:
                    message = pagure.lib.edit_issue(
                        SESSION,
                        issue=issue,
                        priority=new_priority,
                        private=issue.private,
                        user=flask.g.fas_user.username,
                        ticketfolder=APP.config['TICKETS_FOLDER'],
                    )
                    SESSION.commit()
                    if message:
                        messages.add(message)

                # Update milestone and privacy setting
                message = pagure.lib.edit_issue(
                    SESSION,
                    issue=issue,
                    milestone=new_milestone,
                    private=form.private.data,
                    user=flask.g.fas_user.username,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                )
                SESSION.commit()
                if message:
                    messages.add(message)

                # Update the custom keys/fields
                for key in repo.issue_keys:
                    value = flask.request.form.get(key.name)
                    if key.key_type == 'link':
                        links = value.split(',')
                        for link in links:
                            link = link.replace(' ', '')
                            if not urlpattern.match(link):
                                flask.abort(
                                    400,
                                    'Meta-data "link" field '
                                    '(%s) has invalid url (%s) ' %
                                    (key.name, link))
                    messages.add(
                        pagure.lib.set_custom_key_value(
                            SESSION, issue, key, value)
                    )

                # Update ticket this one depends on
                messages.union(set(pagure.lib.update_dependency_issue(
                    SESSION, repo, issue, depends,
                    username=flask.g.fas_user.username,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                )))

                # Update ticket(s) depending on this one
                messages.union(set(pagure.lib.update_blocked_issue(
                    SESSION, repo, issue, blocks,
                    username=flask.g.fas_user.username,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                )))

            if not is_js:
                for message in messages:
                    flask.flash(message)

        except pagure.exceptions.PagureException as err:
            is_js = False
            SESSION.rollback()
            flask.flash(err.message, 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            is_js = False
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash(str(err), 'error')
        except filelock.Timeout as err:  # pragma: no cover
            is_js = False
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash(
                    'We could not save all the info, please try again',
                    'error')
    else:
        if is_js:
            return 'notok: %s' % form.errors

    if is_js:
        return 'ok'
    else:
        return flask.redirect(flask.url_for(
            'view_issue',
            repo=repo.name,
            username=username,
            namespace=namespace,
            issueid=issueid)
        )


@APP.route('/<repo>/tag/<tag>/edit/', methods=('GET', 'POST'))
@APP.route('/<repo>/tag/<tag>/edit', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/tag/<tag>/edit/', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/tag/<tag>/edit', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<repo>/tag/<tag>/edit/',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<repo>/tag/<tag>/edit',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/tag/<tag>/edit/',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/tag/<tag>/edit',
    methods=('GET', 'POST'))
@login_required
def edit_tag(repo, tag, username=None, namespace=None):
    """ Edit the specified tag associated with the issues of a project.
    """
    repo = flask.g.repo

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to edit tags associated with the issues of \
            this project')

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    tags = pagure.lib.get_tags_of_project(SESSION, repo)
    if not tags:
        flask.abort(404, 'Project has no tags to edit')

    # Check the tag exists, and get its old/original color
    tagobj = pagure.lib.get_tag(SESSION, tag, repo.id)
    if not tagobj:
        flask.abort(404, 'Tag %s not found in this project' % tag)

    form = pagure.forms.AddIssueTagForm()
    if form.validate_on_submit():
        new_tag = form.tag.data
        new_tag_description = form.tag_description.data
        new_tag_color = form.tag_color.data

        msgs = pagure.lib.edit_issue_tags(
            SESSION,
            repo,
            tagobj,
            new_tag,
            new_tag_description,
            new_tag_color,
            user=flask.g.fas_user.username,
            ticketfolder=APP.config['TICKETS_FOLDER']
        )

        try:
            SESSION.commit()
            for msg in msgs:
                flask.flash(msg)
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            LOG.error(err)
            flask.flash('Could not edit tag: %s' % tag, 'error')

        return flask.redirect(flask.url_for(
            '.view_settings', repo=repo.name, username=username,
            namespace=repo.namespace))
    elif flask.request.method == 'GET':
        form.tag_color.data = tagobj.tag_color
        form.tag_description.data = tagobj.tag_description
        form.tag.data = tag

    return flask.render_template(
        'edit_tag.html',
        username=username,
        repo=repo,
        form=form,
        tagname=tag,
    )


@APP.route('/<repo>/update/tags', methods=['POST'])
@APP.route('/<namespace>/<repo>/update/tags', methods=['POST'])
@login_required
def update_tags(repo, username=None, namespace=None):
    """ Update the tags of a project.
    """

    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    form = pagure.forms.ConfirmationForm()

    error = False
    if form.validate_on_submit():
        # Uniquify and order preserving
        seen = set()
        tags = [
            tag.strip()
            for tag in flask.request.form.getlist('tag')
            if tag.strip() and tag.strip() not in seen and not seen.add(tag.strip())
        ]

        tag_descriptions = [
            desc.strip()
            for desc in flask.request.form.getlist('tag_description')
        ]

        # Uniquify and order preserving
        seen = set()
        colors = [
            col.strip()
            for col in flask.request.form.getlist('tag_color')
            if col.strip() and col.strip() not in seen and not seen.add(col.strip())
        ]

        color_pattern = re.compile('^#\w{3,6}$')
        for color in colors:
            if not color_pattern.match(color):
                flask.flash(
                    'Color: %s does not match the expected pattern' % color,
                    'error')
                error = True

        if not (len(tags) == len(colors) == len(tag_descriptions)):
            error = True
            # Store the lengths because we are going to use them a lot
            len_tags = len(tags)
            len_tag_descriptions = len(tag_descriptions)
            len_colors = len(colors)
            error_message = 'Error: Incomplete request. '

            if len_colors > len_tags or len_tag_descriptions > len_tags:
                error_message += 'One or more tag fields missing.'
            elif len_colors < len_tags:
                error_message += 'One or more tag color fields missing.'
            elif len_tag_descriptions < len_tags:
                error_message += 'One or more tag description fields missing.'

            flask.flash(error_message, 'error')

        if not error:
            for idx, tag in enumerate(tags):
                try:
                    pagure.lib.new_tag(
                        SESSION,
                        tag,
                        tag_descriptions[idx],
                        colors[idx],
                        repo.id)
                    SESSION.commit()
                    flask.flash('Tags updated')
                except SQLAlchemyError as err:  # pragma: no cover
                    SESSION.rollback()
                    flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_settings', username=username, repo=repo.name,
        namespace=namespace))


@APP.route('/<repo>/droptag/', methods=['POST'])
@APP.route('/<namespace>/<repo>/droptag/', methods=['POST'])
@APP.route('/fork/<username>/<repo>/droptag/', methods=['POST'])
@APP.route('/fork/<username>/<namespace>/<repo>/droptag/', methods=['POST'])
@login_required
def remove_tag(repo, username=None, namespace=None):
    """ Remove the specified tag, associated with the issues, from the project.
    """
    repo = flask.g.repo

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to remove tags associated with the issues \
            of this project')

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    form = pagure.forms.DeleteIssueTagForm()
    if form.validate_on_submit():
        tags = form.tag.data
        tags = [tag.strip() for tag in tags.split(',')]

        msgs = pagure.lib.remove_tags(
            SESSION, repo, tags,
            user=flask.g.fas_user.username,
            ticketfolder=APP.config['TICKETS_FOLDER']
        )

        try:
            SESSION.commit()
            for msg in msgs:
                flask.flash(msg)
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            LOG.error(err)
            flask.flash(
                'Could not remove tag: %s' % ','.join(tags), 'error')

    return flask.redirect(flask.url_for(
        '.view_settings', repo=repo.name, username=username,
        namespace=repo.namespace)
    )


@APP.route('/<repo>/issues/')
@APP.route('/<repo>/issues')
@APP.route('/<namespace>/<repo>/issues/')
@APP.route('/<namespace>/<repo>/issues')
@APP.route('/fork/<username>/<repo>/issues/')
@APP.route('/fork/<username>/<repo>/issues')
@APP.route('/fork/<username>/<namespace>/<repo>/issues/')
@APP.route('/fork/<username>/<namespace>/<repo>/issues')
def view_issues(repo, username=None, namespace=None):
    """ List all issues associated to a repo
    """
    status = flask.request.args.get('status', 'Open')
    priority = flask.request.args.get('priority', None)
    tags = flask.request.args.getlist('tags')
    tags = [tag.strip() for tag in tags if tag.strip()]
    assignee = flask.request.args.get('assignee', None)
    author = flask.request.args.get('author', None)
    search_pattern = flask.request.args.get('search_pattern', None)

    # Custom fields
    custom_keys = flask.request.args.getlist('ckeys')
    custom_values = flask.request.args.getlist('cvalue')
    custom_search = {}
    if len(custom_keys) == len(custom_values):
        for idx, key in enumerate(custom_keys):
            custom_search[key] = custom_values[idx]

    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    try:
        priority = int(priority)
    except:
        priority = None

    # Hide private tickets
    private = False
    # If user is authenticated, show him/her his/her private tickets
    if authenticated():
        private = flask.g.fas_user.username
    # If user is repo admin, show all tickets included the private ones
    if flask.g.repo_admin:
        private = None

    if str(status).lower() in ['all']:
        status = None

    oth_issues = None
    oth_issues_cnt = None
    total_issues_cnt = pagure.lib.search_issues(
            SESSION, repo, tags=tags, assignee=assignee,
            author=author, private=private, priority=priority, count=True)
    if status is not None:
        issues = pagure.lib.search_issues(
            SESSION,
            repo,
            closed=True if status.lower() != 'open' else False,
            status=status.capitalize() if status.lower() != 'closed' else None,
            tags=tags,
            assignee=assignee,
            author=author,
            private=private,
            priority=priority,
            offset=flask.g.offset,
            limit=flask.g.limit,
            search_pattern=search_pattern,
            custom_search=custom_search,
        )
        issues_cnt = pagure.lib.search_issues(
            SESSION,
            repo,
            closed=True if status.lower() != 'open' else False,
            status=status.capitalize() if status.lower() != 'closed' else None,
            tags=tags,
            assignee=assignee,
            author=author,
            private=private,
            priority=priority,
            search_pattern=search_pattern,
            custom_search=custom_search,
            count=True
        )
        oth_issues = pagure.lib.search_issues(
            SESSION,
            repo,
            closed=True if status.lower() != 'open' else False,
            tags=tags,
            assignee=assignee,
            author=author,
            private=private,
            priority=priority,
            count=True,
            search_pattern=search_pattern,
            custom_search=custom_search,
        )
        oth_issues_cnt = total_issues_cnt - issues_cnt
    else:
        issues = pagure.lib.search_issues(
            SESSION, repo, tags=tags, assignee=assignee,
            author=author, private=private, priority=priority,
            offset=flask.g.offset, limit=flask.g.limit,
            search_pattern=search_pattern,
            custom_search=custom_search,
        )
        issues_cnt = total_issues_cnt

    tag_list = pagure.lib.get_tags_of_project(SESSION, repo)

    total_page = int(ceil(issues_cnt / float(flask.g.limit)) if issues_cnt > 0 else 1)

    return flask.render_template(
        'issues.html',
        select='issues',
        repo=repo,
        username=username,
        tag_list=tag_list,
        status=status,
        issues=issues,
        issues_cnt=issues_cnt,
        total_issues_cnt=total_issues_cnt,
        oth_issues=oth_issues,
        oth_issues_cnt=oth_issues_cnt,
        tags=tags,
        assignee=assignee,
        author=author,
        priority=priority,
        total_page=total_page,
        add_report_form=pagure.forms.AddReportForm(),
        search_pattern=search_pattern,
    )


@APP.route('/<repo>/roadmap/')
@APP.route('/<repo>/roadmap')
@APP.route('/<namespace>/<repo>/roadmap/')
@APP.route('/<namespace>/<repo>/roadmap')
@APP.route('/fork/<username>/<repo>/roadmap/')
@APP.route('/fork/<username>/<repo>/roadmap')
@APP.route('/fork/<username>/<namespace>/<repo>/roadmap/')
@APP.route('/fork/<username>/<namespace>/<repo>/roadmap')
def view_roadmap(repo, username=None, namespace=None):
    """ List all issues associated to a repo as roadmap
    """
    status = flask.request.args.get('status', 'Open')
    milestones = flask.request.args.getlist('milestone', None)
    tags = flask.request.args.getlist('tag', None)
    all_stones = flask.request.args.get('all_stones')

    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    # Hide private tickets
    private = False
    # If user is authenticated, show him/her his/her private tickets
    if authenticated():
        private = flask.g.fas_user.username
    # If user is repo admin, show all tickets included the private ones
    if flask.g.repo_admin:
        private = None

    all_milestones = sorted(list(repo.milestones.keys()))
    active_milestones = pagure.lib.get_active_milestones(SESSION, repo)

    issues = pagure.lib.search_issues(
        SESSION,
        repo,
        milestones=milestones or all_milestones,
        tags=tags,
        private=private,
        status=status if status.lower() != 'all' else None,
    )

    # Change from a list of issues to a dict of milestone/issues
    milestone_issues = defaultdict(list)
    for issue in issues:
        saved = False
        for mlstone in sorted(milestones or all_milestones):
            if mlstone == issue.milestone:
                milestone_issues[mlstone].append(issue)
                saved = True
                break
        if saved:
            continue

    if status and status.lower() != 'all':
        for key in milestone_issues.keys():
            active = False
            for issue in milestone_issues[key]:
                if issue.status == status:
                    active = True
                    break
            if not active:
                del milestone_issues[key]

    tag_list = [
        tag.tag
        for tag in pagure.lib.get_tags_of_project(SESSION, repo)
    ]

    if 'unplanned' in all_milestones:
        index = all_milestones.index('unplanned')
        cnt = len(all_milestones)
        all_milestones.insert(cnt, all_milestones.pop(index))

    milestones_list = active_milestones
    if all_stones:
        milestones_list = all_milestones

    return flask.render_template(
        'roadmap.html',
        select='issues',
        repo=repo,
        username=username,
        tag_list=tag_list,
        status=status,
        all_stones=all_stones,
        milestones=milestones_list,
        requested_stones=milestones,
        issues=milestone_issues,
        tags=tags,
    )


@APP.route('/<repo>/new_issue/', methods=('GET', 'POST'))
@APP.route('/<repo>/new_issue', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/new_issue/', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/new_issue', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/new_issue/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/new_issue', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/new_issue/',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/new_issue',
    methods=('GET', 'POST'))
@login_required
def new_issue(repo, username=None, namespace=None):
    """ Create a new issue
    """
    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    form = pagure.forms.IssueFormSimplied()
    if form.validate_on_submit():
        title = form.title.data
        content = form.issue_content.data
        private = form.private.data

        try:
            user_obj = pagure.lib.get_user(
                SESSION, flask.g.fas_user.username)
        except pagure.exceptions.PagureException:
            flask.abort(
                404,
                'No such user found in the database: %s' % (
                    flask.g.fas_user.username))

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
                    user=user_obj,
                    filename=filestream.filename,
                    filestream=filestream.stream,
                )
                # Replace the <!!image> tag in the comment with the link
                # to the actual image
                filelocation = flask.url_for(
                    'view_issue_raw_file',
                    repo=repo.name,
                    username=username,
                    namespace=repo.namespace,
                    filename=new_filename,
                )
                new_filename = new_filename.split('-', 1)[1]
                url = '[![%s](%s)](%s)' % (
                    new_filename, filelocation, filelocation)
                issue.content = issue.content.replace('<!!image>', url)
                SESSION.add(issue)
                SESSION.commit()

            return flask.redirect(flask.url_for(
                '.view_issue', username=username, repo=repo.name,
                namespace=namespace, issueid=issue.id))
        except pagure.exceptions.PagureException as err:
            flask.flash(str(err), 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')
        except filelock.Timeout as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash(
                    'We could not save all the info, please try again',
                    'error')

    types = None
    default = None
    ticketrepopath = os.path.join(APP.config['TICKETS_FOLDER'], repo.path)
    if os.path.exists(ticketrepopath):
        ticketrepo = pygit2.Repository(ticketrepopath)
        if not ticketrepo.is_empty and not ticketrepo.head_is_unborn:
            commit = ticketrepo[ticketrepo.head.target]
            # Get the different ticket types
            files = __get_file_in_tree(
                ticketrepo, commit.tree, ['templates'],
                bail_on_tree=True)
            if files:
                types = [f.name.rstrip('.md') for f in files]
            # Get the default template
            default_file = __get_file_in_tree(
                ticketrepo, commit.tree, ['templates', 'default.md'],
                bail_on_tree=True)
            if default_file:
                default, _ = pagure.doc_utils.convert_readme(
                    default_file.data, 'md')

    if flask.request.method == 'GET':
        form.private.data = repo.settings.get(
            'issues_default_to_private', False)

    return flask.render_template(
        'new_issue.html',
        select='issues',
        form=form,
        repo=repo,
        username=username,
        types=types,
        default=default,
    )


@APP.route('/<repo>/issue/<int:issueid>/')
@APP.route('/<repo>/issue/<int:issueid>')
@APP.route('/<namespace>/<repo>/issue/<int:issueid>/')
@APP.route('/<namespace>/<repo>/issue/<int:issueid>')
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/')
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>')
@APP.route('/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/')
@APP.route('/fork/<username>/<namespace>/<repo>/issue/<int:issueid>')
def view_issue(repo, issueid, username=None, namespace=None):
    """ List all issues associated to a repo
    """

    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if issue.private and not flask.g.repo_admin \
            and (not authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        flask.abort(
            403, 'This issue is private and you are not allowed to view it')

    status = pagure.lib.get_issue_statuses(SESSION)

    form = pagure.forms.UpdateIssueForm(
        status=status,
        priorities=repo.priorities,
        milestones=repo.milestones,
        close_status=repo.close_status,
    )
    form.status.data = issue.status
    form.priority.data = issue.priority
    form.milestone.data = issue.milestone
    form.private.data = issue.private
    form.close_status.data = ''
    if issue.close_status:
        form.close_status.data = issue.close_status
    tag_list = pagure.lib.get_tags_of_project(SESSION, repo)

    knowns_keys = {}
    for key in issue.other_fields:
        knowns_keys[key.key.name] = key

    return flask.render_template(
        'issue.html',
        select='issues',
        repo=repo,
        username=username,
        tag_list=tag_list,
        issue=issue,
        issueid=issueid,
        form=form,
        knowns_keys=knowns_keys,
        subscribers=pagure.lib.get_watch_list(SESSION, issue),
        attachments=issue.attachments,
    )


@APP.route('/<repo>/issue/<int:issueid>/drop', methods=['POST'])
@APP.route('/<namespace>/<repo>/issue/<int:issueid>/drop', methods=['POST'])
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/drop',
           methods=['POST'])
@APP.route('/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/drop',
           methods=['POST'])
def delete_issue(repo, issueid, username=None, namespace=None):
    """ Delete the specified issue
    """

    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to remove tickets of this project')

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        try:
            pagure.lib.drop_issue(
                SESSION, issue,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
            )
            SESSION.commit()
            flask.flash('Issue deleted')
            return flask.redirect(flask.url_for(
                'view_issues', username=username, repo=repo.name,
                namespace=namespace))
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash('Could not delete the issue', 'error')

    return flask.redirect(flask.url_for(
        'view_issue', username=username, repo=repo.name,
        namespace=repo.namespace, issueid=issueid))


@APP.route('/<repo>/issue/<int:issueid>/edit/', methods=('GET', 'POST'))
@APP.route('/<repo>/issue/<int:issueid>/edit', methods=('GET', 'POST'))
@APP.route(
    '/<namespace>/<repo>/issue/<int:issueid>/edit/',
    methods=('GET', 'POST'))
@APP.route(
    '/<namespace>/<repo>/issue/<int:issueid>/edit',
    methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/edit/',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/edit',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/edit/',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/edit',
           methods=('GET', 'POST'))
@login_required
def edit_issue(repo, issueid, username=None, namespace=None):
    """ Edit the specified issue
    """
    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if not (flask.g.repo_admin
            or flask.g.fas_user.username == issue.user.username):
        flask.abort(
            403, 'You are not allowed to edit issues for this project')

    status = pagure.lib.get_issue_statuses(SESSION)
    form = pagure.forms.IssueForm(status=status)
    if form.validate_on_submit():
        title = form.title.data
        content = form.issue_content.data
        status = form.status.data
        private = form.private.data

        try:
            user_obj = pagure.lib.get_user(
                SESSION, flask.g.fas_user.username)
        except pagure.exceptions.PagureException:
            flask.abort(
                404, 'No such user found in the database: %s' % (
                    flask.g.fas_user.username))

        try:
            message = pagure.lib.edit_issue(
                SESSION,
                issue=issue,
                title=title,
                content=content,
                status=status,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
                private=private,
            )
            SESSION.commit()

            # If there is a file attached, attach it.
            filestream = flask.request.files.get('filestream')
            if filestream and '<!!image>' in issue.content:
                new_filename = pagure.lib.git.add_file_to_git(
                    repo=repo,
                    issue=issue,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                    user=user_obj,
                    filename=filestream.filename,
                    filestream=filestream.stream,
                )
                # Replace the <!!image> tag in the comment with the link
                # to the actual image
                filelocation = flask.url_for(
                    'view_issue_raw_file',
                    repo=repo.name,
                    namespace=repo.namespace,
                    username=username,
                    filename=new_filename,
                )
                new_filename = new_filename.split('-', 1)[1]
                url = '[![%s](%s)](%s)' % (
                    new_filename, filelocation, filelocation)
                issue.content = issue.content.replace('<!!image>', url)
                SESSION.add(issue)
                SESSION.commit()
            flask.flash(message)
            url = flask.url_for(
                'view_issue', username=username, namespace=namespace,
                repo=repo.name, issueid=issueid)
            return flask.redirect(url)
        except pagure.exceptions.PagureException as err:
            SESSION.rollback()
            flask.flash(str(err), 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')
        except filelock.Timeout as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash(
                    'We could not save all the info, please try again',
                    'error')

    elif flask.request.method == 'GET':
        form.title.data = issue.title
        form.issue_content.data = issue.content
        form.status.data = issue.status
        form.private.data = issue.private

    return flask.render_template(
        'new_issue.html',
        select='issues',
        type='edit',
        form=form,
        repo=repo,
        username=username,
        issue=issue,
        issueid=issueid,
    )


@APP.route('/<namespace>/<repo>/issue/<int:issueid>/upload', methods=['POST'])
@APP.route('/<repo>/issue/<int:issueid>/upload', methods=['POST'])
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/upload',
           methods=['POST'])
@APP.route('/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/upload',
           methods=['POST'])
@login_required
def upload_issue(repo, issueid, username=None, namespace=None):
    ''' Upload a file to a ticket.
    '''
    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    try:
        user_obj = pagure.lib.get_user(
            SESSION, flask.g.fas_user.username)
    except pagure.exceptions.PagureException:
        flask.abort(
            404, 'No such user found in the database: %s' % (
                flask.g.fas_user.username))

    form = pagure.forms.UploadFileForm()

    if form.validate_on_submit():
        filestream = flask.request.files['filestream']
        try:
            new_filename = pagure.lib.git.add_file_to_git(
                repo=repo,
                issue=issue,
                ticketfolder=APP.config['TICKETS_FOLDER'],
                user=user_obj,
                filename=filestream.filename,
                filestream=filestream.stream,
            )
        except filelock.Timeout as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash(
                    'We could not save all the info, please try again',
                    'error')

        return flask.jsonify({
            'output': 'ok',
            'filename': new_filename.split('-', 1)[1],
            'filelocation': flask.url_for(
                'view_issue_raw_file',
                repo=repo.name,
                username=username,
                namespace=repo.namespace,
                filename=new_filename,
            )
        })
    else:
        return flask.jsonify({'output': 'notok'})


@APP.route('/<repo>/issue/raw/<path:filename>')
@APP.route('/<namespace>/<repo>/issue/raw/<path:filename>')
@APP.route('/fork/<username>/<repo>/issue/raw/<path:filename>')
@APP.route('/fork/<username>/<namespace>/<repo>/issue/raw/<path:filename>')
def view_issue_raw_file(
        repo, filename=None, username=None, namespace=None):
    """ Displays the raw content of a file of a commit for the specified
    ticket repo.
    """
    raw = flask.request.args.get('raw')
    raw = str(raw).lower() in ['1', 'true', 't']

    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    reponame = os.path.join(APP.config['TICKETS_FOLDER'], repo.path)

    repo_obj = pygit2.Repository(reponame)

    if repo_obj.is_empty:
        flask.abort(404, 'Empty repo cannot have a file')

    branch = repo_obj.lookup_branch('master')
    commit = branch.get_object()

    mimetype = None
    encoding = None

    content = __get_file_in_tree(
        repo_obj, commit.tree, filename.split('/'), bail_on_tree=True)
    if not content or isinstance(content, pygit2.Tree):
        flask.abort(404, 'File not found')

    mimetype, encoding = mimetypes.guess_type(filename)
    data = repo_obj[content.oid].data

    if not data:
        flask.abort(404, 'No content found')

    if not raw \
            and (filename.endswith('.patch') or filename.endswith('.diff')) \
            and not is_binary_string(content.data):
        # We have a patch file attached to this issue, render the diff in html
        orig_filename = filename.partition('-')[2]
        return flask.render_template(
            'patchfile.html',
            select='issues',
            repo=repo,
            username=username,
            diff=data,
            patchfile=orig_filename,
            form=pagure.forms.ConfirmationForm(),
        )

    if not mimetype and data[:2] == '#!':
        mimetype = 'text/plain'

    headers = {}
    if not mimetype:
        if '\0' in data:
            mimetype = 'application/octet-stream'
        else:
            mimetype = 'text/plain'
    elif 'html' in mimetype:
        mimetype = 'application/octet-stream'
        headers['Content-Disposition'] = 'attachment'

    if mimetype.startswith('text/') and not encoding:
        try:
            encoding = pagure.lib.encoding_utils.guess_encoding(
                ktc.to_bytes(data))
        except pagure.exceptions.PagureException:
            # We cannot decode the file, so bail but warn the admins
            LOG.exception('File could not be decoded')

    if encoding:
        mimetype += '; charset={encoding}'.format(encoding=encoding)
    headers['Content-Type'] = mimetype

    return (data, 200, headers)


@APP.route('/<repo>/issue/<int:issueid>/comment/<int:commentid>/edit',
           methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/issue/<int:issueid>/comment/<int:commentid>/'
           'edit', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/comment'
           '/<int:commentid>/edit', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/comment'
           '/<int:commentid>/edit', methods=('GET', 'POST'))
@login_required
def edit_comment_issue(
        repo, issueid, commentid, username=None, namespace=None):
    """Edit comment of an issue
    """
    is_js = flask.request.args.get('js', False)

    project = flask.g.repo

    if not project.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    issue = pagure.lib.search_issues(SESSION, project, issueid=issueid)

    if issue is None or issue.project != project:
        flask.abort(404, 'Issue not found')

    comment = pagure.lib.get_issue_comment(
        SESSION, issue.uid, commentid)

    if comment is None or comment.parent.project != project:
        flask.abort(404, 'Comment not found')

    if (flask.g.fas_user.username != comment.user.username
            or comment.parent.status != 'Open') \
            and not flask.g.repo_admin:
        flask.abort(403, 'You are not allowed to edit this comment')

    form = pagure.forms.EditCommentForm()

    if form.validate_on_submit():

        updated_comment = form.update_comment.data
        try:
            message = pagure.lib.edit_comment(
                SESSION,
                parent=issue,
                comment=comment,
                user=flask.g.fas_user.username,
                updated_comment=updated_comment,
                folder=APP.config['TICKETS_FOLDER'],
            )
            SESSION.commit()
            if not is_js:
                flask.flash(message)
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            LOG.error(err)
            if is_js:
                return 'error'
            flask.flash(
                'Could not edit the comment: %s' % commentid, 'error')
        except filelock.Timeout as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash(
                    'We could not save all the info, please try again',
                    'error')

        if is_js:
            return 'ok'

        return flask.redirect(flask.url_for(
            'view_issue', username=username, namespace=namespace,
            repo=project.name, issueid=issueid))

    if is_js and flask.request.method == 'POST':
        return 'failed'

    return flask.render_template(
        'comment_update.html',
        select='issues',
        requestid=issueid,
        repo=project,
        username=username,
        form=form,
        comment=comment,
        is_js=is_js,
    )


@APP.route('/<repo>/issues/reports', methods=['POST'])
@APP.route('/<namespace>/<repo>/issues/reports', methods=['POST'])
@APP.route('/fork/<username>/<repo>/issues/reports', methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/issues/reports', methods=['POST'])
@login_required
def save_reports(repo, username=None, namespace=None):
    """ Marked for watching or Unwatching
    """
    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to create reports for this project')

    return_point = flask.url_for(
        'view_issues', repo=repo, username=username, namespace=namespace)
    if pagure.is_safe_url(flask.request.referrer):
        return_point = flask.request.referrer

    form = pagure.forms.AddReportForm()
    if not form.validate_on_submit():
        flask.abort(400)

    name = form.report_name.data

    try:
        msg = pagure.lib.save_report(
            SESSION,
            flask.g.repo,
            name=name,
            url=flask.request.referrer,
            username=flask.g.fas_user.username)
        SESSION.commit()
        flask.flash(msg)
    except pagure.exceptions.PagureException as msg:
        flask.flash(msg, 'error')

    return flask.redirect(return_point)


@APP.route('/<repo>/report/<report>')
@APP.route('/<namespace>/<repo>/report/<report>')
@APP.route('/fork/<username>/<repo>/report/<report>')
@APP.route('/fork/<username>/<namespace>/<repo>/report/<report>')
def view_report(repo, report, username=None, namespace=None):
    """ Show the specified report.
    """
    reports = flask.g.repo.reports
    if report not in reports:
        flask.abort(404, 'No such report found')

    flask.request.args = werkzeug.datastructures.ImmutableMultiDict(
        reports[report])

    return view_issues(repo=repo, username=username, namespace=namespace)
