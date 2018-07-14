# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-many-branches
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals


from __future__ import unicode_literals

import textwrap

import arrow
import flask
import six

from six.moves.urllib.parse import urlparse, parse_qsl
from pygments import highlight
from pygments.lexers.text import DiffLexer
from pygments.formatters import HtmlFormatter
from pygments.filters import VisibleWhitespaceFilter

import pagure.exceptions
import pagure.lib
import pagure.forms
from pagure.config import config as pagure_config
from pagure.ui import UI_NS
from pagure.utils import authenticated, is_repo_committer, is_true


# Jinja filters


@UI_NS.app_template_filter('hasattr')
def jinja_hasattr(obj, string):
    """ Template filter checking if the provided object at the provided
    string as attribute
    """
    return hasattr(obj, string)


@UI_NS.app_template_filter('render')
def jinja_render(tmpl, **kwargs):
    """ Render the given template with the provided arguments
    """
    return flask.render_template_string(tmpl, **kwargs)


@UI_NS.app_template_filter('humanize')
def humanize_date(date):
    """ Template filter returning the last commit date of the provided repo.
    """
    if date:
        return arrow.get(date).humanize()


@UI_NS.app_template_filter('format_ts')
@UI_NS.app_template_filter('format_datetime')
def format_ts(string):
    """ Template filter transforming a timestamp, datetime or anything
    else arrow.get() can handle to a human-readable date
    """
    # We *could* enhance this by allowing users to specify preferred
    # timezone, localized time format etc. and customizing this display
    # to user's preferences. But we don't have that, so for now, we
    # always use UTC timezone, and we don't use localized forms like
    # %b or %d because they will be 'localized' for the *server*.
    # This format should be pretty 'locale-neutral'.
    arr = arrow.get(string)
    return arr.strftime('%Y-%m-%d %H:%M:%S %Z')


@UI_NS.app_template_filter('format_loc')
def format_loc(loc, commit=None, filename=None, tree_id=None, prequest=None,
               index=None):
    """ Template filter putting the provided lines of code into a table
    """
    if loc is None:
        return

    output = [
        '<div class="highlight">',
        '<table class="code_table">'
    ]

    comments = {}
    if prequest and not isinstance(prequest, flask.wrappers.Request):
        for com in prequest.comments:
            if commit and com.commit_id == commit \
                    and com.filename == filename:
                if com.line in comments:
                    comments[com.line].append(com)
                else:
                    comments[com.line] = [com]
    for key in comments:
        comments[key] = sorted(
            comments[key], key=lambda obj: obj.date_created)

    if not index:
        index = ''

    cnt = 1
    for line in loc.split('\n'):
        if line == '</pre></div>':
            break
        if filename and commit:
            if isinstance(filename, str) and six.PY2:
                filename = filename.decode('UTF-8')
            output.append(
                '<tr id="c-%(commit)s-%(cnt_lbl)s"><td class="cell1">'
                '<a id="%(cnt)s" href="#%(cnt)s" data-line-number='
                '"%(cnt_lbl)s"></a></td>'
                '<td class="prc" data-row="%(cnt_lbl)s"'
                ' data-filename="%(filename)s" data-commit="%(commit)s"'
                ' data-tree="%(tree_id)s">'
                '<p>'
                '<span class="fa fa-comment prc_img" style="display: none;"'
                'alt="Add comment" title="Add comment"></span>'
                '</p>'
                '</td>' % (
                    {
                        'cnt': '%s_%s' % (index, cnt),
                        'cnt_lbl': cnt,
                        'filename': filename,
                        'commit': commit,
                        'tree_id': tree_id,
                    }
                )
            )
        else:
            output.append(
                '<tr><td class="cell1">'
                '<a id="%(cnt)s" href="#%(cnt)s" data-line-number='
                '"%(cnt_lbl)s"></a></td>'
                % (
                    {
                        'cnt': '%s_%s' % (index, cnt),
                        'cnt_lbl': cnt,
                    }
                )
            )

        cnt += 1
        if not line:
            output.append(line)
            continue
        if line.startswith('<div'):
            line = line.split('<pre style="line-height: 125%">')[1]
            if prequest and prequest.project_from:
                rangeline = line.partition('font-weight: bold">@@ ')[2] \
                    if line.partition('font-weight: bold">@@ ')[1] == \
                    'font-weight: bold">@@ ' else None
                if rangeline:
                    rangeline = rangeline.split(' @@</span>')[0]
                    linenumber = rangeline.split('+')[1].split(',')[0]
                    line = line + '&nbsp;<a href="%s#_%s" target="_blank" ' % (
                        flask.url_for(
                            'ui_ns.view_file',
                            repo=prequest.project_from.name,
                            username=prequest.project_from.user.username
                            if prequest.project_from.is_fork else None,
                            namespace=prequest.project_from.namespace,
                            identifier=prequest.branch_from,
                            filename=filename), linenumber)
                    line = line + 'class="open_changed_file_icon_wrap">' + \
                        '<span class="oi open_changed_file_icon" ' + \
                        'data-glyph="eye" alt="Open changed file" ' + \
                        'title="Open changed file"></span></a>'
        output.append('<td class="cell2"><pre>%s</pre></td>' % line)
        output.append('</tr>')

        tpl_edit = '<a href="%(edit_url)s" ' \
            'class="btn btn-secondary btn-sm" data-comment="%(commentid)s" ' \
            'data-objid="%(requestid)s">' \
            '<i class="fa fa-pencil"></i>' \
            '</a>'
        tpl_edited = '<small class="text-muted" title="%(edit_date)s"> ' \
            'Edited %(human_edit_date)s by %(user)s </small>'

        tpl_delete = '<button class="btn btn-secondary btn-sm" '\
            'title="Remove comment" '\
            'name="drop_comment" value="%(commentid)s" type="submit" ' \
            'onclick="return confirm(\'Do you really want to remove this' \
            ' comment?\');" ><i class="fa fa-trash"></i>' \
            '</button>'

        if cnt - 1 in comments:
            for comment in comments[cnt - 1]:

                templ_delete = ''
                templ_edit = ''
                templ_edited = ''
                if authenticated() and (
                        (
                            is_true(comment.parent.status, ['true', 'open'])
                            and comment.user.user == flask.g.fas_user.username
                        )
                        or is_repo_committer(comment.parent.project)):
                    templ_delete = tpl_delete % ({'commentid': comment.id})
                    templ_edit = tpl_edit % ({
                        'edit_url': flask.url_for(
                            'ui_ns.pull_request_edit_comment',
                            repo=comment.parent.project.name,
                            requestid=comment.parent.id,
                            commentid=comment.id,
                            username=comment.parent.user.user
                            if comment.parent.project.is_fork else None
                        ),
                        'requestid': comment.parent.id,
                        'commentid': comment.id,
                    })

                if comment.edited_on:
                    templ_edited = tpl_edited % ({
                        'edit_date': format_ts(comment.edited_on),
                        'human_edit_date': humanize_date(comment.edited_on),
                        'user': comment.editor.user,
                    })

                output.append(
                    '<tr class="inline-pr-comment"><td></td>'
                    '<td colspan="2">'
                    '<div class="card clearfix m-x-1 ">'
                    '<div class="card-block">'
                    '<small><div id="comment-%(commentid)s">'
                    '<img class="avatar circle" src="%(avatar_url)s"/>'
                    '<a href="%(url)s" title="%(user_html)s">'
                    '%(user)s</a> commented '
                    '<a class="headerlink" title="Permalink '
                    'to this headline" href="#comment-%(commentid)s">'
                    '<span title="%(date)s">%(human_date)s</span>'
                    '</a></div></small>'
                    '<section class="issue_comment">'
                    '<div class="comment_body">'
                    '%(comment)s'
                    '</div>'
                    '</section>'
                    '<div class="issue_actions m-t-2">'
                    '%(templ_edited)s'
                    '<aside class="btn-group issue_action icon '
                    'pull-xs-right p-b-1">'
                    '%(templ_edit)s'
                    '%(templ_delete)s'
                    '</aside>'
                    '</div></div></div>'
                    '</td></tr>' % (
                        {
                            'url': flask.url_for(
                                'ui_ns.view_user', username=comment.user.user),
                            'templ_delete': templ_delete,
                            'templ_edit': templ_edit,
                            'templ_edited': templ_edited,
                            'user': comment.user.user,
                            'user_html': comment.user.html_title,
                            'avatar_url': avatar_url(
                                comment.user.default_email, 16),
                            'date': format_ts(comment.date_created),
                            'human_date': humanize_date(comment.date_created),
                            'comment': markdown_filter(comment.comment),
                            'commentid': comment.id,
                        }
                    )
                )

    output.append('</table></div>')

    return '\n'.join(output)


@UI_NS.app_template_filter('blame_loc')
def blame_loc(loc, repo, username, blame):
    """ Template filter putting the provided lines of code into a table


    This method blame lines of code (loc) takes as input a text (lines of
    code) concerning a given repo, with its repo and a pygit2.Blame object
    and convert it into a html table displayed to the user with the git
    blame information (user, commit, commit date).

    :arg loc: a unicode object of the lines of code to display (in this case,
        most likely the content of a file).
    :arg repo: the name of the repo in which this file is.
    :arg username: the user name of the user whose repo this is, if the repo
        is not a *fork*, this value is ``None``.
    :arg blame: a pygit2.Blame object allowing us to link a given line of
        code to a commit.

    """
    if loc is None:
        return

    if not isinstance(loc, six.text_type):
        raise ValueError(
            '"loc" must be a unicode string, not %s' % type(loc))

    output = [
        '<div class="highlight">',
        '<table class="code_table">'
    ]

    for idx, line in enumerate(loc.split('\n')):
        if line == '</pre></div>':
            break

        try:
            diff = blame.for_line(idx + 1)
        except IndexError:
            # Happens at the end of the file, since we are using idx + 1
            continue

        if '<pre style="line-height: 125%">' in line:
            line = line.split('<pre style="line-height: 125%">')[1]

        output.append(
            '<tr><td class="cell1">'
            '<a id="%(cnt)s" href="#%(cnt)s" data-line-number='
            '"%(cnt)s"></a></td>'
            % ({'cnt': idx + 1})
        )

        committer = None
        try:
            committer = diff.orig_committer
        except ValueError:
            pass
        output.append(
            '<td class="cell_user">%s</td>' % (author_to_user(
                committer, with_name=False) if committer else ' ')
        )

        output.append(
            '<td class="cell_commit"><a href="%s">%s</a></td>' % (
                flask.url_for(
                    'ui_ns.view_commit',
                    repo=repo.name,
                    username=username,
                    namespace=repo.namespace,
                    commitid=diff.final_commit_id
                ),
                shorted_commit(diff.final_commit_id)
            )
        )
        output.append('<td class="cell2"><pre>%s</pre></td>' % line)
        output.append('</tr>')

    output.append('</table></div>')

    return '\n'.join(output)


@UI_NS.app_template_filter('wraps')
def text_wraps(text, size=10):
    """ Template filter to wrap text at a specified size
    """
    if text:
        parts = textwrap.wrap(text, size)
        if len(parts) > 1:
            parts = '%s...' % parts[0]
        else:
            parts = parts[0]
        return parts


@UI_NS.app_template_filter('avatar')
def avatar(packager, size=64, css_class=None):
    """ Template filter that returns html for avatar of any given Username.
    """
    if not isinstance(packager, six.text_type):
        packager = packager.decode('utf-8')

    if '@' not in packager:
        user = pagure.lib.search_user(flask.g.session, username=packager)
        if user:
            packager = user.default_email

    class_string = "avatar circle"
    if css_class:
        class_string = class_string + " " + css_class

    output = '<img class="%s" src="%s"/>' % (
        class_string,
        avatar_url(packager, size)
    )

    return output


@UI_NS.app_template_filter('avatar_url')
def avatar_url(email, size=64):
    """ Template filter that returns html for avatar of any given Email.
    """
    return pagure.lib.avatar_url_from_email(email, size)


@UI_NS.app_template_filter('short')
def shorted_commit(cid):
    """Gets short version of the commit id"""
    return ("%s" % cid)[:pagure_config['SHORT_LENGTH']]


@UI_NS.app_template_filter('markdown')
def markdown_filter(text):
    """ Template filter converting a string into html content using the
    markdown library.
    """
    return pagure.lib.text2markdown(text)


@UI_NS.app_template_filter('html_diff')
def html_diff(diff, linenos='inline'):
    """Display diff as HTML"""
    if diff is None:
        return
    difflexer = DiffLexer()
    # Do not give whitespaces the special Whitespace token type as this
    # prevents the html formatter from picking up on trailing whitespaces in
    # the diff.
    difflexer.add_filter(VisibleWhitespaceFilter(wstokentype=False, tabs=True))

    style = 'diffstyle'

    return highlight(
        diff,
        difflexer,
        HtmlFormatter(
            linenos=linenos,
            noclasses=True,
            style=style)
    )


@UI_NS.app_template_filter('patch_to_diff')
def patch_to_diff(patch):
    """Render a hunk as a diff"""
    content = []
    for hunk in patch.hunks:
        content.append("@@ -%i,%i +%i,%i @@\n" % (
            hunk.old_start, hunk.old_lines, hunk.new_start, hunk.new_lines))

        for line in hunk.lines:
            if hasattr(line, 'content'):
                origin = line.origin
                if line.origin in ['<', '>', '=']:
                    origin = ''
                content.append(origin + ' ' + line.content)
            else:
                # Avoid situation where at the end of a file we get:
                # + foo<
                # \ No newline at end of file
                if line[0] in ['<', '>', '=']:
                    line = ('', line[1])
                content.append(' '.join(line))

    return ''.join(content)


@UI_NS.app_template_filter('author2user')
def author_to_user(author, size=16, cssclass=None, with_name=True):
    """ Template filter transforming a pygit2 Author object into a text
    either with just the username or linking to the user in pagure.
    """
    output = author.name
    if not author.email:
        return output
    user = pagure.lib.search_user(flask.g.session, email=author.email)
    if user:
        output = "%(avatar)s <a title='%(name)s' href='%(url)s' "\
            "%(cssclass)s>%(username)s</a>"
        if not with_name:
            output = "<a title='%(name)s' href='%(url)s' "\
                "%(cssclass)s>%(avatar)s</a>"

        output = output % (
            {
                'avatar': avatar(user.default_email, size),
                'url': flask.url_for(
                    'ui_ns.view_user', username=user.username),
                'cssclass': ('class="%s"' % cssclass) if cssclass else '',
                'username': user.username,
                'name': author.name,
            }
        )

    return output


@UI_NS.app_template_filter('author2avatar')
def author_to_avatar(author, size=32):
    """ Template filter transforming a pygit2 Author object into an avatar.
    """
    if not author.email:
        return ''
    user = pagure.lib.search_user(flask.g.session, email=author.email)
    output = user.default_email if user else author.email
    return avatar(output.encode('utf-8'), size)


@UI_NS.app_template_filter('author2user_commits')
def author_to_user_commits(author, link, size=16, cssclass=None):
    """ Template filter transforming a pygit2 Author object into a text
    either with just the username or linking to the user in pagure.
    """
    output = author.name
    if not author.email:
        return output
    user = pagure.lib.search_user(flask.g.session, email=author.email)
    if user:
        output = "<a href='%s'>%s</a> <a href='%s' %s>%s</a>" % (
            flask.url_for('ui_ns.view_user', username=user.username),
            avatar(user.default_email, size),
            link,
            ('class="%s"' % cssclass) if cssclass else '',
            author.name,
        )

    return output


@UI_NS.app_template_filter('InsertDiv')
def insert_div(content):
    """ Template filter inserting an opening <div> and closing </div>
    after the first title and then at the end of the content.
    """
    # This is quite a hack but simpler solution using .replace() didn't work
    # for some reasons...
    content = content.split('\n')
    output = []
    for row in content:
        if row.startswith('<div class="document" id='):
            continue
        if '<h1 class="title">' in row:
            row = ("%s" % row).replace(
                '<h1 class="title">',
                '<h1 class="title">'
                '<span class="oi" data-glyph="collapse-down"></span> &nbsp;'
            )
        output.append(row)
    output = "\n".join(output)
    output = output.replace('</h1>', '</h1>\n<div>', 1)
    output = output.replace('h1', 'h3')

    return output


@UI_NS.app_template_filter('noJS')
def no_js(content, ignore=None):
    """ Template filter replacing <script by &lt;script and </script> by
    &lt;/script&gt;
    """
    return pagure.lib.clean_input(content, ignore=ignore)


@UI_NS.app_template_filter('toRGB')
def int_to_rgb(percent):
    """ Template filter converting a given percentage to a css RGB value.
    """
    output = "rgb(255, 0, 0);"
    try:
        percent = int(percent)
        if percent < 50:
            red = 255
            green = (255.0 / 50) * percent
        else:
            green = 255
            red = (255.0 / 50) * (100 - percent)
        output = "rgb(%s, %s, 0);" % (int(red), int(green))
    except ValueError:
        pass
    return output


@UI_NS.app_template_filter('increment_largest_priority')
def largest_priority(dictionary):
    """ Template filter to return the largest priority +1
    """
    if dictionary:
        keys = [int(k) for k in dictionary if k]
        if keys:
            return max(keys) + 1
    return 1


@UI_NS.app_template_filter('unicode')
def convert_unicode(text):
    ''' If the provided string is a binary string, this filter converts it
    to UTF-8 (unicode).
    '''
    if isinstance(text, str) and six.PY2:
        return text.decode("utf8")
    else:
        return text


@UI_NS.app_template_filter('combine_url')
def combine_url(url, page, pagetitle, **kwargs):
    """ Add the specified arguments in the provided kwargs dictionary to
    the given URL.
    """
    url_obj = urlparse(url)
    url = url_obj.geturl().replace(url_obj.query, '').rstrip('?')
    query = {}
    for k, v in parse_qsl(url_obj.query):
        if k in query:
            if isinstance(query[k], list):
                query[k].append(v)
            else:
                query[k] = [query[k], v]
        else:
            query[k] = v
    query[pagetitle] = page
    query.update(kwargs)
    args = ''
    for key in query:
        if isinstance(query[key], list):
            for val in query[key]:
                args += '&%s=%s' % (key, val)
        else:
            args += '&%s=%s' % (key, query[key])
    return url + '?' + args[1:]


@UI_NS.app_template_filter('add_or_remove')
def add_or_remove(item, items):
    """ Adds the item to the list if it is not in there and remove it
    otherwise.
    """
    if item in items:
        items.remove(item)
    else:
        items.append(item)
    return items


@UI_NS.app_template_filter('table_sort_arrow')
def table_sort_arrow(column, order_key, order):
    """ Outputs an arrow icon if the column is currently being sorted on
    """
    arrow_html = ('<span class="oi" data-glyph="arrow-thick-{0}"></span>')
    if column == order_key:
        if order == 'desc':
            return arrow_html.format('bottom')
        else:
            return arrow_html.format('top')
    return ''


@UI_NS.app_template_filter('table_get_link_order')
def table_get_link_order(column, order_key, order):
    """ Get the correct order parameter value for the table heading link
    """
    if column == order_key:
        # If the user is clicking on the column again, they want the
        # oposite order
        if order == 'desc':
            return 'asc'
        else:
            return 'desc'
    else:
        # Default to descending
        return 'desc'


@UI_NS.app_template_filter('flag2label')
def flag_to_label(flag):
    """ For a given flag return the bootstrap label to use
    """
    return pagure_config['FLAG_STATUSES_LABELS'][flag.status.lower()]


@UI_NS.app_template_filter('join_prefix')
def join_prefix(values, num):
    """Produce a string joining first `num` items in the list and indicate
    total number total number of items.
    """
    if len(values) <= 1:
        return "".join(values)
    if len(values) <= num:
        return ", ".join(values[:-1]) + " and " + values[-1]
    return "%s and %d others" % (", ".join(values[:num]), len(values) - num)
