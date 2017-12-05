# -*- coding: utf-8 -*-

"""
 (c) 2014-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-branches
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements


import datetime
import logging
import os
import re
from collections import defaultdict
from math import ceil

import flask
import pygit2
import werkzeug.datastructures
from sqlalchemy.exc import SQLAlchemyError
from binaryornot.helpers import is_binary_string

import pagure.doc_utils
import pagure.exceptions
import pagure.lib
import pagure.lib.mimetype
from pagure.decorators import has_issue_tracker, is_repo_admin
import pagure.forms
from pagure.config import config as pagure_config
from pagure.ui import UI_NS
from pagure.utils import (
    __get_file_in_tree,
    authenticated,
    login_required,
    urlpattern,
)


_log = logging.getLogger(__name__)


@UI_NS.route(
    '/<repo>/issue/<int:issueid>/update/',
    methods=['GET', 'POST'])
@UI_NS.route(
    '/<repo>/issue/<int:issueid>/update',
    methods=['GET', 'POST'])
@UI_NS.route(
    '/<namespace>/<repo>/issue/<int:issueid>/update/',
    methods=['GET', 'POST'])
@UI_NS.route(
    '/<namespace>/<repo>/issue/<int:issueid>/update',
    methods=['GET', 'POST'])
@UI_NS.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/update/',
    methods=['GET', 'POST'])
@UI_NS.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/update',
    methods=['GET', 'POST'])
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/update/',
    methods=['GET', 'POST'])
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/update',
    methods=['GET', 'POST'])
@login_required
@has_issue_tracker
def update_issue(repo, issueid, username=None, namespace=None):
    ''' Add comment or update metadata of an issue. '''
    is_js = flask.request.args.get('js', False)

    repo = flask.g.repo

    if flask.request.method == 'GET':
        if not is_js:
            flask.flash('Invalid method: GET', 'error')
        return flask.redirect(flask.url_for(
            'ui_ns.view_issue', username=username, repo=repo.name,
            namespace=repo.namespace, issueid=issueid))

    issue = pagure.lib.search_issues(flask.g.session, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if issue.private and not flask.g.repo_committer \
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

    status = pagure.lib.get_issue_statuses(flask.g.session)
    form = pagure.forms.UpdateIssueForm(
        status=status,
        priorities=repo.priorities,
        milestones=repo.milestones,
        close_status=repo.close_status,
    )

    if form.validate_on_submit():
        if flask.request.form.get('drop_comment'):
            commentid = flask.request.form.get('drop_comment')

            comment = pagure.lib.get_issue_comment(
                flask.g.session, issue.uid, commentid)
            if comment is None or comment.issue.project != repo:
                flask.abort(404, 'Comment not found')

            if (flask.g.fas_user.username != comment.user.username
                    or comment.parent.status != 'Open') \
                    and not flask.g.repo_committer:
                flask.abort(
                    403,
                    'You are not allowed to remove this comment from '
                    'this issue')

            issue.last_updated = datetime.datetime.utcnow()
            flask.g.session.add(issue)
            flask.g.session.delete(comment)
            pagure.lib.git.update_git(
                issue,
                repo=issue.project,
                repofolder=pagure_config['TICKETS_FOLDER'])
            try:
                flask.g.session.commit()
                if not is_js:
                    flask.flash('Comment removed')
            except SQLAlchemyError as err:  # pragma: no cover
                is_js = False
                flask.g.session.rollback()
                _log.error(err)
                if not is_js:
                    flask.flash(
                        'Could not remove the comment: %s' % commentid,
                        'error')
            if is_js:
                return 'ok'
            else:
                return flask.redirect(flask.url_for(
                    'ui_ns.view_issue', username=username, repo=repo.name,
                    namespace=repo.namespace, issueid=issueid))

        comment = form.comment.data
        depends = []
        for depend in form.depending.data.split(','):
            if depend.strip():
                try:
                    depends.append(int(depend.strip()))
                except ValueError:
                    pass

        blocks = []
        for block in form.blocking.data.split(','):
            if block.strip():
                try:
                    blocks.append(int(block.strip()))
                except ValueError:
                    pass

        assignee = form.assignee.data.strip() or None
        new_status = form.status.data.strip() or None
        close_status = form.close_status.data or None
        if close_status not in repo.close_status:
            close_status = None

        new_priority = None
        try:
            new_priority = int(form.priority.data)
        except (ValueError, TypeError):
            pass
        tags = [
            tag.strip()
            for tag in form.tag.data.split(',')
            if tag.strip()]

        new_milestone = None
        try:
            if repo.milestones:
                new_milestone = form.milestone.data.strip() or None
        except AttributeError:
            pass

        try:
            messages = set()

            # The status field can be updated by both the admin and the
            # person who opened the ticket.
            # Update status
            if flask.g.repo_user \
                    or flask.g.fas_user.username == issue.user.user:
                if new_status in status:
                    msgs = pagure.lib.edit_issue(
                        flask.g.session,
                        issue=issue,
                        status=new_status,
                        close_status=close_status,
                        milestone=issue.milestone,
                        private=issue.private,
                        user=flask.g.fas_user.username,
                        ticketfolder=pagure_config['TICKETS_FOLDER']
                    )
                    flask.g.session.commit()
                    if msgs:
                        messages = messages.union(set(msgs))

            # All the other meta-data can be changed only by admins
            # while other field will be missing for non-admin and thus
            # reset if we let them
            if flask.g.repo_user:
                # Adjust (add/remove) tags
                msgs = pagure.lib.update_tags(
                    flask.g.session, issue, tags,
                    username=flask.g.fas_user.username,
                    gitfolder=pagure_config['TICKETS_FOLDER'],
                )
                messages = messages.union(set(msgs))

                # The meta-data can only be changed by admins, which means
                # they will be missing for non-admin and thus reset if we
                # let them

                # Assign or update assignee of the ticket
                message = pagure.lib.add_issue_assignee(
                    flask.g.session,
                    issue=issue,
                    assignee=assignee or None,
                    user=flask.g.fas_user.username,
                    ticketfolder=pagure_config['TICKETS_FOLDER'],
                )
                flask.g.session.commit()
                if message and message != 'Nothing to change':
                    messages.add(message)

                # Adjust priority if needed
                if str(new_priority) not in repo.priorities:
                    new_priority = None

                # Update core metadata
                msgs = pagure.lib.edit_issue(
                    flask.g.session,
                    repo=repo,
                    issue=issue,
                    milestone=new_milestone,
                    priority=new_priority,
                    private=form.private.data,
                    user=flask.g.fas_user.username,
                    ticketfolder=pagure_config['TICKETS_FOLDER'],
                )
                if msgs:
                    messages = messages.union(set(msgs))

                # Update the custom keys/fields
                for key in repo.issue_keys:
                    value = flask.request.form.get(key.name)
                    if value:
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

                    msg = pagure.lib.set_custom_key_value(
                        flask.g.session, issue, key, value)
                    if key.key_notify and msg is not None:
                        # Custom field changed that is set for notifications
                        pagure.lib.notify.notify_meta_change_issue(
                            issue, flask.g.fas_user, msg)
                    if msg:
                        messages.add(msg)

                # Update ticket this one depends on
                msgs = pagure.lib.update_dependency_issue(
                    flask.g.session, repo, issue, depends,
                    username=flask.g.fas_user.username,
                    ticketfolder=pagure_config['TICKETS_FOLDER'],
                )
                messages = messages.union(set(msgs))

                # Update ticket(s) depending on this one
                msgs = pagure.lib.update_blocked_issue(
                    flask.g.session, repo, issue, blocks,
                    username=flask.g.fas_user.username,
                    ticketfolder=pagure_config['TICKETS_FOLDER'],
                )
                messages = messages.union(set(msgs))

            flask.g.session.commit()

            # New comment
            if comment:
                message = pagure.lib.add_issue_comment(
                    flask.g.session,
                    issue=issue,
                    comment=comment,
                    user=flask.g.fas_user.username,
                    ticketfolder=pagure_config['TICKETS_FOLDER'],
                )

                if not is_js:
                    if message:
                        messages.add(message)

            flask.g.session.commit()

            if not is_js:
                for message in messages:
                    flask.flash(message)

            # Add the comment for field updates:
            if messages:
                not_needed = set(['Comment added', 'Updated comment'])
                pagure.lib.add_metadata_update_notif(
                    session=flask.g.session,
                    obj=issue,
                    messages=messages - not_needed,
                    user=flask.g.fas_user.username,
                    gitfolder=pagure_config['TICKETS_FOLDER']
                )
                messages.add('Metadata fields updated')

        except pagure.exceptions.PagureException as err:
            is_js = False
            flask.g.session.rollback()
            flask.flash(err.message, 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            is_js = False
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash(str(err), 'error')
    else:
        if is_js:
            return 'notok: %s' % form.errors

    if is_js:
        return 'ok'
    else:
        return flask.redirect(flask.url_for(
            'ui_ns.view_issue',
            repo=repo.name,
            username=username,
            namespace=namespace,
            issueid=issueid)
        )


@UI_NS.route('/<repo>/tag/<tag>/edit/', methods=('GET', 'POST'))
@UI_NS.route('/<repo>/tag/<tag>/edit', methods=('GET', 'POST'))
@UI_NS.route('/<namespace>/<repo>/tag/<tag>/edit/', methods=('GET', 'POST'))
@UI_NS.route('/<namespace>/<repo>/tag/<tag>/edit', methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/tag/<tag>/edit/',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/tag/<tag>/edit',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/tag/<tag>/edit/',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/tag/<tag>/edit',
    methods=('GET', 'POST'))
@login_required
@is_repo_admin
@has_issue_tracker
def edit_tag(repo, tag, username=None, namespace=None):
    """ Edit the specified tag associated with the issues of a project.
    """
    repo = flask.g.repo

    tags = pagure.lib.get_tags_of_project(flask.g.session, repo)
    if not tags:
        flask.abort(404, 'Project has no tags to edit')

    # Check the tag exists, and get its old/original color
    tagobj = pagure.lib.get_colored_tag(flask.g.session, tag, repo.id)
    if not tagobj:
        flask.abort(404, 'Tag %s not found in this project' % tag)

    form = pagure.forms.AddIssueTagForm()
    if form.validate_on_submit():
        new_tag = form.tag.data
        new_tag_description = form.tag_description.data
        new_tag_color = form.tag_color.data

        msgs = pagure.lib.edit_issue_tags(
            flask.g.session,
            repo,
            tagobj,
            new_tag,
            new_tag_description,
            new_tag_color,
            user=flask.g.fas_user.username,
            ticketfolder=pagure_config['TICKETS_FOLDER']
        )

        try:
            flask.g.session.commit()
            for msg in msgs:
                flask.flash(msg)
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.error(err)
            flask.flash('Could not edit tag: %s' % tag, 'error')

        return flask.redirect(flask.url_for(
            'ui_ns.view_settings', repo=repo.name, username=username,
            namespace=repo.namespace))
    elif flask.request.method == 'GET':
        tag_color = tagobj.tag_color
        if tag_color == 'DeepSkyBlue':
            tag_color = '#00bfff'
        form.tag_color.data = tag_color
        form.tag_description.data = tagobj.tag_description
        form.tag.data = tag

    return flask.render_template(
        'edit_tag.html',
        username=username,
        repo=repo,
        form=form,
        tagname=tag,
    )


@UI_NS.route('/<repo>/update/tags', methods=['POST'])
@UI_NS.route('/<namespace>/<repo>/update/tags', methods=['POST'])
@login_required
@is_repo_admin
@has_issue_tracker
def update_tags(repo, username=None, namespace=None):
    """ Update the tags of a project.
    """

    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()

    error = False
    if form.validate_on_submit():
        # Uniquify and order preserving
        seen = set()
        tags = [
            tag.strip()
            for tag in flask.request.form.getlist('tag')
            if tag.strip()
            and tag.strip() not in seen  # noqa
            and not seen.add(tag.strip())
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
            if col.strip()
            and col.strip() not in seen
            and not seen.add(col.strip())
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
                        flask.g.session,
                        tag,
                        tag_descriptions[idx],
                        colors[idx],
                        repo.id)
                    flask.g.session.commit()
                    flask.flash('Tags updated')
                except SQLAlchemyError as err:  # pragma: no cover
                    flask.g.session.rollback()
                    flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'ui_ns.view_settings', username=username, repo=repo.name,
        namespace=namespace))


@UI_NS.route('/<repo>/droptag/', methods=['POST'])
@UI_NS.route('/<namespace>/<repo>/droptag/', methods=['POST'])
@UI_NS.route('/fork/<username>/<repo>/droptag/', methods=['POST'])
@UI_NS.route('/fork/<username>/<namespace>/<repo>/droptag/', methods=['POST'])
@login_required
@is_repo_admin
@has_issue_tracker
def remove_tag(repo, username=None, namespace=None):
    """ Remove the specified tag, associated with the issues, from the project.
    """
    repo = flask.g.repo

    form = pagure.forms.DeleteIssueTagForm()
    if form.validate_on_submit():
        tags = form.tag.data
        tags = [tag.strip() for tag in tags.split(',')]

        msgs = pagure.lib.remove_tags(
            flask.g.session, repo, tags,
            user=flask.g.fas_user.username,
            gitfolder=pagure_config['TICKETS_FOLDER']
        )

        try:
            flask.g.session.commit()
            for msg in msgs:
                flask.flash(msg)
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.error(err)
            flask.flash(
                'Could not remove tag: %s' % ','.join(tags), 'error')

    return flask.redirect(flask.url_for(
        'ui_ns.view_settings', repo=repo.name, username=username,
        namespace=repo.namespace)
    )


@UI_NS.route('/<repo>/issues/')
@UI_NS.route('/<repo>/issues')
@UI_NS.route('/<namespace>/<repo>/issues/')
@UI_NS.route('/<namespace>/<repo>/issues')
@UI_NS.route('/fork/<username>/<repo>/issues/')
@UI_NS.route('/fork/<username>/<repo>/issues')
@UI_NS.route('/fork/<username>/<namespace>/<repo>/issues/')
@UI_NS.route('/fork/<username>/<namespace>/<repo>/issues')
@has_issue_tracker
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
    milestones = flask.request.args.getlist('milestone', None)
    order = flask.request.args.get('order', 'desc')
    order_key = flask.request.args.get('order_key', 'date_created')

    # Custom fields
    custom_keys = flask.request.args.getlist('ckeys')
    custom_values = flask.request.args.getlist('cvalue')
    custom_search = {}
    if len(custom_keys) == len(custom_values):
        for idx, key in enumerate(custom_keys):
            custom_search[key] = custom_values[idx]

    try:
        priority = int(priority)
    except (ValueError, TypeError):
        priority = None

    fields = {
        'status': status,
        'priority': priority,
        'tags': tags,
        'assignee': assignee,
        'author': author,
        'milestones': milestones,
    }

    no_stone = None
    if "none" in milestones:
        no_stone = True
        milestones.remove("none")

    search_string = search_pattern
    extra_fields, search_pattern = pagure.lib.tokenize_search_string(
        search_pattern)

    for field in fields:
        if field in extra_fields:
            fields[field] = extra_fields[field]
            del(extra_fields[field])

    custom_search.update(extra_fields)

    repo = flask.g.repo

    # Hide private tickets
    private = False
    # If user is authenticated, show him/her his/her private tickets
    if authenticated():
        private = flask.g.fas_user.username
    # If user is repo committer, show all tickets including the private ones
    if flask.g.repo_committer:
        private = None

    status = fields['status']
    del(fields['status'])

    if status.lower() in ['all']:
        status = None

    oth_issues_cnt = None
    total_issues_cnt = pagure.lib.search_issues(
        flask.g.session, repo, private=private, count=True,
        **fields)
    if status is not None:
        issues = pagure.lib.search_issues(
            flask.g.session,
            repo,
            closed=True if status.lower() != 'open' else False,
            private=private,
            offset=flask.g.offset,
            limit=flask.g.limit,
            search_pattern=search_pattern,
            custom_search=custom_search,
            no_milestones=no_stone,
            order=order,
            order_key=order_key,
            status=status.capitalize() if status.lower() != 'closed' else None,
            **fields
        )
        issues_cnt = pagure.lib.search_issues(
            flask.g.session,
            repo,
            closed=True if status.lower() != 'open' else False,
            private=private,
            search_pattern=search_pattern,
            custom_search=custom_search,
            no_milestones=no_stone,
            count=True,
            status=status.capitalize() if status.lower() != 'closed' else None,
            **fields
        )
        oth_issues_cnt = pagure.lib.search_issues(
            flask.g.session,
            repo,
            closed=True if status.lower() != 'open' else False,
            private=private,
            search_pattern=search_pattern,
            custom_search=custom_search,
            no_milestones=no_stone,
            count=True,
            **fields
        )
    else:
        issues = pagure.lib.search_issues(
            flask.g.session,
            repo,
            private=private,
            offset=flask.g.offset,
            limit=flask.g.limit,
            search_pattern=search_pattern,
            custom_search=custom_search,
            order=order,
            order_key=order_key,
            **fields
        )
        issues_cnt = pagure.lib.search_issues(
            flask.g.session,
            repo,
            private=private,
            search_pattern=search_pattern,
            custom_search=custom_search,
            count=True,
            **fields
        )
    tag_list = pagure.lib.get_tags_of_project(flask.g.session, repo)

    total_page = 1
    if issues_cnt:
        total_page = int(ceil(issues_cnt / float(flask.g.limit)))

    return flask.render_template(
        'issues.html',
        select='issues',
        repo=repo,
        username=username,
        tag_list=tag_list,
        issues=issues,
        issues_cnt=issues_cnt,
        total_issues_cnt=total_issues_cnt,
        oth_issues_cnt=oth_issues_cnt,
        total_page=total_page,
        add_report_form=pagure.forms.AddReportForm(),
        search_pattern=search_string,
        order=order,
        order_key=order_key,
        status=status,
        **fields
    )


@UI_NS.route('/<repo>/roadmap/')
@UI_NS.route('/<repo>/roadmap')
@UI_NS.route('/<namespace>/<repo>/roadmap/')
@UI_NS.route('/<namespace>/<repo>/roadmap')
@UI_NS.route('/fork/<username>/<repo>/roadmap/')
@UI_NS.route('/fork/<username>/<repo>/roadmap')
@UI_NS.route('/fork/<username>/<namespace>/<repo>/roadmap/')
@UI_NS.route('/fork/<username>/<namespace>/<repo>/roadmap')
@has_issue_tracker
def view_roadmap(repo, username=None, namespace=None):
    """ List all issues associated to a repo as roadmap
    """
    status = flask.request.args.get('status', 'Open')
    milestones = flask.request.args.getlist('milestone', None)
    tags = flask.request.args.getlist('tag', None)
    all_stones = flask.request.args.get('all_stones')
    no_stones = flask.request.args.get('no_stones')

    repo = flask.g.repo

    # Hide private tickets
    private = False
    # If user is authenticated, show him/her his/her private tickets
    if authenticated():
        private = flask.g.fas_user.username

    # If user is repo committer, show all tickets including the private ones
    if flask.g.repo_committer:
        private = None

    tag_list = [
        tag.tag
        for tag in pagure.lib.get_tags_of_project(flask.g.session, repo)
    ]

    all_milestones = sorted(list(repo.milestones.keys()))
    active_milestones = pagure.lib.get_active_milestones(flask.g.session, repo)

    milestones_list = active_milestones
    if all_stones:
        milestones_list = all_milestones

    if 'unplanned' in all_milestones:
        index = all_milestones.index('unplanned')
        cnt = len(all_milestones)
        all_milestones.insert(cnt, all_milestones.pop(index))

    if no_stones:
        # Return only issues that do not have a milestone set
        issues = pagure.lib.search_issues(
            flask.g.session,
            repo,
            no_milestones=True,
            tags=tags,
            private=private,
            status=status if status.lower() != 'all' else None,
        )
        return flask.render_template(
            'roadmap.html',
            select='issues',
            repo=repo,
            username=username,
            tag_list=tag_list,
            status=status,
            no_stones=True,
            issues=issues,
            tags=tags,
            all_stones=all_stones,
            requested_stones=milestones,
        )

    issues = pagure.lib.search_issues(
        flask.g.session,
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


@UI_NS.route('/<repo>/new_issue/', methods=('GET', 'POST'))
@UI_NS.route('/<repo>/new_issue', methods=('GET', 'POST'))
@UI_NS.route('/<namespace>/<repo>/new_issue/', methods=('GET', 'POST'))
@UI_NS.route('/<namespace>/<repo>/new_issue', methods=('GET', 'POST'))
@UI_NS.route('/fork/<username>/<repo>/new_issue/', methods=('GET', 'POST'))
@UI_NS.route('/fork/<username>/<repo>/new_issue', methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/new_issue/',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/new_issue',
    methods=('GET', 'POST'))
@login_required
@has_issue_tracker
def new_issue(repo, username=None, namespace=None):
    """ Create a new issue
    """
    repo = flask.g.repo

    form = pagure.forms.IssueFormSimplied(
        priorities=repo.priorities,
        milestones=repo.milestones,
    )

    if form.validate_on_submit():
        title = form.title.data
        content = form.issue_content.data
        private = form.private.data

        try:
            user_obj = pagure.lib.get_user(
                flask.g.session, flask.g.fas_user.username)
        except pagure.exceptions.PagureException:
            flask.abort(
                404,
                'No such user found in the database: %s' % (
                    flask.g.fas_user.username))

        try:
            priority = None
            if repo.default_priority:
                for key, val in repo.priorities.items():
                    if repo.default_priority == val:
                        priority = key

            assignee = None
            milestone = None
            tags = None
            if flask.g.repo_user:
                assignee = flask.request.form.get(
                    'assignee', '').strip() or None
                milestone = form.milestone.data or None
                priority = form.priority.data or priority
                tags = [
                    tag.strip()
                    for tag in flask.request.form.get(
                        'tag', '').split(',')
                    if tag.strip()]

            issue = pagure.lib.new_issue(
                flask.g.session,
                repo=repo,
                title=title,
                content=content,
                private=private or False,
                user=flask.g.fas_user.username,
                assignee=assignee,
                milestone=milestone,
                priority=priority,
                tags=tags,
                ticketfolder=pagure_config['TICKETS_FOLDER'],
            )
            flask.g.session.commit()

            # If there is a file attached, attach it.
            form = pagure.forms.UploadFileForm()
            if form.validate_on_submit():
                streams = flask.request.files.getlist('filestream')
                n_img = issue.content.count('<!!image>')
                if n_img == len(streams):
                    for filestream in streams:
                        new_filename = pagure.lib.add_attachment(
                            repo=repo,
                            issue=issue,
                            attachmentfolder=pagure_config[
                                'ATTACHMENTS_FOLDER'],
                            user=user_obj,
                            filename=filestream.filename,
                            filestream=filestream.stream,
                        )
                        # Replace the <!!image> tag in the comment with the
                        # link to the actual image
                        filelocation = flask.url_for(
                            'ui_ns.view_issue_raw_file',
                            repo=repo.name,
                            username=username,
                            namespace=repo.namespace,
                            filename=new_filename,
                        )
                        new_filename = new_filename.split('-', 1)[1]
                        url = '[![%s](%s)](%s)' % (
                            new_filename, filelocation, filelocation)
                        issue.content = issue.content.replace(
                            '<!!image>', url, 1)
                    flask.g.session.add(issue)
                    flask.g.session.commit()

            return flask.redirect(flask.url_for(
                'ui_ns.view_issue', username=username, repo=repo.name,
                namespace=namespace, issueid=issue.id))
        except pagure.exceptions.PagureException as err:
            flask.flash(str(err), 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(str(err), 'error')

    types = None
    default = None
    ticketrepopath = os.path.join(pagure_config['TICKETS_FOLDER'], repo.path)
    if os.path.exists(ticketrepopath):
        ticketrepo = pygit2.Repository(ticketrepopath)
        if not ticketrepo.is_empty and not ticketrepo.head_is_unborn:
            commit = ticketrepo[ticketrepo.head.target]
            # Get the different ticket types
            files = __get_file_in_tree(
                ticketrepo, commit.tree, ['templates'],
                bail_on_tree=True)
            if files:
                types = [f.name.rsplit('.md', 1)[0] for f in files]
            # Get the default template
            default_file = __get_file_in_tree(
                ticketrepo, commit.tree, ['templates', 'default.md'],
                bail_on_tree=True)
            if default_file:
                default, _ = pagure.doc_utils.convert_readme(
                    default_file.data, 'md')

    tag_list = pagure.lib.get_tags_of_project(flask.g.session, repo)
    if flask.request.method == 'GET':
        form.private.data = repo.settings.get(
            'issues_default_to_private', False)
        form.title.data = flask.request.args.get('title')
        form.issue_content.data = flask.request.args.get('content')
        default_priority = None
        if repo.default_priority:
                for key, val in repo.priorities.items():
                    if repo.default_priority == val:
                        default_priority = key
        form.priority.data = flask.request.form.get(
            'priority', str(default_priority))

    return flask.render_template(
        'new_issue.html',
        select='issues',
        form=form,
        repo=repo,
        username=username,
        types=types,
        default=default,
        tag_list=tag_list,
    )


@UI_NS.route('/<repo>/issue/<int:issueid>/')
@UI_NS.route('/<repo>/issue/<int:issueid>')
@UI_NS.route('/<namespace>/<repo>/issue/<int:issueid>/')
@UI_NS.route('/<namespace>/<repo>/issue/<int:issueid>')
@UI_NS.route('/fork/<username>/<repo>/issue/<int:issueid>/')
@UI_NS.route('/fork/<username>/<repo>/issue/<int:issueid>')
@UI_NS.route('/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/')
@UI_NS.route('/fork/<username>/<namespace>/<repo>/issue/<int:issueid>')
@has_issue_tracker
def view_issue(repo, issueid, username=None, namespace=None):
    """ List all issues associated to a repo
    """

    repo = flask.g.repo

    issue = pagure.lib.search_issues(flask.g.session, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if issue.private:
        if not authenticated() or (
                not flask.g.repo_committer
                and issue.user.user != flask.g.fas_user.username):
            flask.abort(404, 'Issue not found')

    status = pagure.lib.get_issue_statuses(flask.g.session)

    form = pagure.forms.UpdateIssueForm(
        status=status,
        priorities=repo.priorities,
        milestones=repo.milestones_keys or repo.milestones or None,
        close_status=repo.close_status,
    )
    form.status.data = issue.status
    form.priority.data = '%s' % issue.priority
    # issue.priority is an int that we need to convert to string as the form
    # relies on string
    form.milestone.data = issue.milestone
    form.private.data = issue.private
    form.close_status.data = ''
    if issue.close_status:
        form.close_status.data = issue.close_status
    tag_list = pagure.lib.get_tags_of_project(flask.g.session, repo)

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
        subscribers=pagure.lib.get_watch_list(flask.g.session, issue),
        attachments=issue.attachments,
    )


@UI_NS.route('/<repo>/issue/<int:issueid>/drop', methods=['POST'])
@UI_NS.route(
    '/<namespace>/<repo>/issue/<int:issueid>/drop', methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/drop', methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/drop',
    methods=['POST'])
@has_issue_tracker
def delete_issue(repo, issueid, username=None, namespace=None):
    """ Delete the specified issue
    """

    repo = flask.g.repo

    issue = pagure.lib.search_issues(flask.g.session, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if not flask.g.repo_committer:
        flask.abort(
            403,
            'You are not allowed to remove tickets of this project')

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        try:
            pagure.lib.drop_issue(
                flask.g.session, issue,
                user=flask.g.fas_user.username,
                ticketfolder=pagure_config['TICKETS_FOLDER'],
            )
            flask.g.session.commit()
            flask.flash('Issue deleted')
            return flask.redirect(flask.url_for(
                'ui_ns.view_issues', username=username, repo=repo.name,
                namespace=namespace))
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash('Could not delete the issue', 'error')

    return flask.redirect(flask.url_for(
        'ui_ns.view_issue', username=username, repo=repo.name,
        namespace=repo.namespace, issueid=issueid))


@UI_NS.route('/<repo>/issue/<int:issueid>/edit/', methods=('GET', 'POST'))
@UI_NS.route('/<repo>/issue/<int:issueid>/edit', methods=('GET', 'POST'))
@UI_NS.route(
    '/<namespace>/<repo>/issue/<int:issueid>/edit/',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/<namespace>/<repo>/issue/<int:issueid>/edit',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/edit/',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/edit',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/edit/',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/edit',
    methods=('GET', 'POST'))
@login_required
@has_issue_tracker
def edit_issue(repo, issueid, username=None, namespace=None):
    """ Edit the specified issue
    """
    repo = flask.g.repo

    issue = pagure.lib.search_issues(flask.g.session, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if not (flask.g.repo_committer
            or flask.g.fas_user.username == issue.user.username):
        flask.abort(
            403, 'You are not allowed to edit issues for this project')

    status = pagure.lib.get_issue_statuses(flask.g.session)
    form = pagure.forms.IssueForm(status=status)
    if form.validate_on_submit():
        title = form.title.data
        content = form.issue_content.data
        status = form.status.data
        private = form.private.data

        try:
            user_obj = pagure.lib.get_user(
                flask.g.session, flask.g.fas_user.username)
        except pagure.exceptions.PagureException:
            flask.abort(
                404, 'No such user found in the database: %s' % (
                    flask.g.fas_user.username))

        try:
            messages = pagure.lib.edit_issue(
                flask.g.session,
                issue=issue,
                title=title,
                content=content,
                status=status,
                user=flask.g.fas_user.username,
                ticketfolder=pagure_config['TICKETS_FOLDER'],
                private=private,
            )
            flask.g.session.commit()
            if messages:
                pagure.lib.add_metadata_update_notif(
                    session=flask.g.session,
                    obj=issue,
                    messages=messages,
                    user=flask.g.fas_user.username,
                    gitfolder=pagure_config['TICKETS_FOLDER']
                )

            # If there is a file attached, attach it.
            filestream = flask.request.files.get('filestream')
            if filestream and '<!!image>' in issue.content:
                new_filename = pagure.lib.add_attachment(
                    repo=repo,
                    issue=issue,
                    attachmentfolder=pagure_config['ATTACHMENTS_FOLDER'],
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
                flask.g.session.add(issue)
                flask.g.session.commit()
            if messages:
                for message in messages:
                    flask.flash(message)
            url = flask.url_for(
                'ui_ns.view_issue', username=username, namespace=namespace,
                repo=repo.name, issueid=issueid)
            return flask.redirect(url)
        except pagure.exceptions.PagureException as err:
            flask.g.session.rollback()
            flask.flash(str(err), 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(str(err), 'error')

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


@UI_NS.route('/<repo>/issue/<int:issueid>/upload', methods=['POST'])
@UI_NS.route(
    '/<namespace>/<repo>/issue/<int:issueid>/upload', methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/upload',
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/upload',
    methods=['POST'])
@login_required
@has_issue_tracker
def upload_issue(repo, issueid, username=None, namespace=None):
    ''' Upload a file to a ticket.
    '''
    repo = flask.g.repo

    issue = pagure.lib.search_issues(flask.g.session, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    try:
        user_obj = pagure.lib.get_user(
            flask.g.session, flask.g.fas_user.username)
    except pagure.exceptions.PagureException:
        flask.abort(
            404, 'No such user found in the database: %s' % (
                flask.g.fas_user.username))

    form = pagure.forms.UploadFileForm()

    if form.validate_on_submit():
        filenames = []
        for filestream in flask.request.files.getlist('filestream'):
            new_filename = pagure.lib.add_attachment(
                repo=repo,
                issue=issue,
                attachmentfolder=pagure_config['ATTACHMENTS_FOLDER'],
                user=user_obj,
                filename=filestream.filename,
                filestream=filestream.stream,
            )
            filenames.append(new_filename)

        return flask.jsonify({
            'output': 'ok',
            'filenames': [
                filename.split('-', 1)[1]
                for filename in filenames],
            'filelocations': [
                flask.url_for(
                    'ui_ns.view_issue_raw_file',
                    repo=repo.name,
                    username=username,
                    namespace=repo.namespace,
                    filename='files/%s' % nfilename,
                )
                for nfilename in filenames
            ]
        })
    else:
        return flask.jsonify({'output': 'notok'})


@UI_NS.route('/<repo>/issue/raw/<path:filename>')
@UI_NS.route('/<namespace>/<repo>/issue/raw/<path:filename>')
@UI_NS.route('/fork/<username>/<repo>/issue/raw/<path:filename>')
@UI_NS.route('/fork/<username>/<namespace>/<repo>/issue/raw/<path:filename>')
@has_issue_tracker
def view_issue_raw_file(
        repo, filename=None, username=None, namespace=None):
    """ Displays the raw content of a file of a commit for the specified
    ticket repo.
    """
    raw = flask.request.args.get('raw')
    raw = str(raw).lower() in ['1', 'true', 't']

    repo = flask.g.repo

    attachdir = os.path.join(
        pagure_config['ATTACHMENTS_FOLDER'], repo.fullname)
    attachpath = os.path.join(attachdir, filename)
    if not os.path.exists(attachpath):
        if not os.path.exists(attachdir):
            os.makedirs(attachdir)

        # Try to copy from git repo to attachments folder
        reponame = os.path.join(pagure_config['TICKETS_FOLDER'], repo.path)
        repo_obj = pygit2.Repository(reponame)

        if repo_obj.is_empty:
            flask.abort(404, 'Empty repo cannot have a file')

        branch = repo_obj.lookup_branch('master')
        commit = branch.get_object()

        content = __get_file_in_tree(
            repo_obj, commit.tree, ['files', filename], bail_on_tree=True)
        if not content or isinstance(content, pygit2.Tree):
            flask.abort(404, 'File not found')

        data = repo_obj[content.oid].data

        if not data:
            flask.abort(404, 'No content found')

        _log.info("Migrating file %s for project %s to attachments",
                  filename, repo.fullname)

        with open(attachpath, 'w') as stream:
            stream.write(data)
        data = None

    # At this moment, attachpath exists and points to the file
    with open(attachpath, 'r') as f:
        data = f.read()

    if not raw \
            and (filename.endswith('.patch') or filename.endswith('.diff')) \
            and not is_binary_string(data):
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

    return (data, 200, pagure.lib.mimetype.get_type_headers(filename, data))


@UI_NS.route(
    '/<repo>/issue/<int:issueid>/comment/<int:commentid>/edit',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/<namespace>/<repo>/issue/<int:issueid>/comment/<int:commentid>/'
    'edit', methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/comment'
    '/<int:commentid>/edit', methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/comment'
    '/<int:commentid>/edit', methods=('GET', 'POST'))
@login_required
@has_issue_tracker
def edit_comment_issue(
        repo, issueid, commentid, username=None, namespace=None):
    """Edit comment of an issue
    """
    is_js = flask.request.args.get('js', False)

    project = flask.g.repo

    issue = pagure.lib.search_issues(flask.g.session, project, issueid=issueid)

    if issue is None or issue.project != project:
        flask.abort(404, 'Issue not found')

    comment = pagure.lib.get_issue_comment(
        flask.g.session, issue.uid, commentid)

    if comment is None or comment.parent.project != project:
        flask.abort(404, 'Comment not found')

    if (flask.g.fas_user.username != comment.user.username
            or comment.parent.status != 'Open') \
            and not flask.g.repo_user:
        flask.abort(403, 'You are not allowed to edit this comment')

    form = pagure.forms.EditCommentForm()

    if form.validate_on_submit():

        updated_comment = form.update_comment.data
        try:
            message = pagure.lib.edit_comment(
                flask.g.session,
                parent=issue,
                comment=comment,
                user=flask.g.fas_user.username,
                updated_comment=updated_comment,
                folder=pagure_config['TICKETS_FOLDER'],
            )
            flask.g.session.commit()
            if not is_js:
                flask.flash(message)
        except SQLAlchemyError, err:  # pragma: no cover
            flask.g.session.rollback()
            _log.error(err)
            if is_js:
                return 'error'
            flask.flash(
                'Could not edit the comment: %s' % commentid, 'error')

        if is_js:
            return 'ok'

        return flask.redirect(flask.url_for(
            'ui_ns.view_issue', username=username, namespace=namespace,
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


@UI_NS.route('/<repo>/issues/reports', methods=['POST'])
@UI_NS.route('/<namespace>/<repo>/issues/reports', methods=['POST'])
@UI_NS.route('/fork/<username>/<repo>/issues/reports', methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/issues/reports', methods=['POST'])
@login_required
@is_repo_admin
def save_reports(repo, username=None, namespace=None):
    """ Marked for watching or Unwatching
    """

    return_point = flask.url_for(
        'ui_ns.view_issues', repo=repo, username=username, namespace=namespace)
    if pagure.utils.is_safe_url(flask.request.referrer):
        return_point = flask.request.referrer

    form = pagure.forms.AddReportForm()
    if not form.validate_on_submit():
        flask.abort(400)

    name = form.report_name.data

    try:
        msg = pagure.lib.save_report(
            flask.g.session,
            flask.g.repo,
            name=name,
            url=flask.request.referrer,
            username=flask.g.fas_user.username)
        flask.g.session.commit()
        flask.flash(msg)
    except pagure.exceptions.PagureException as msg:
        flask.flash(msg, 'error')

    return flask.redirect(return_point)


@UI_NS.route('/<repo>/report/<report>')
@UI_NS.route('/<namespace>/<repo>/report/<report>')
@UI_NS.route('/fork/<username>/<repo>/report/<report>')
@UI_NS.route('/fork/<username>/<namespace>/<repo>/report/<report>')
def view_report(repo, report, username=None, namespace=None):
    """ Show the specified report.
    """
    reports = flask.g.repo.reports
    if report not in reports:
        flask.abort(404, 'No such report found')

    flask.request.args = werkzeug.datastructures.ImmutableMultiDict(
        reports[report])

    return view_issues(repo=repo, username=username, namespace=namespace)
