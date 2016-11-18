# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-many-branches
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals


import datetime
import textwrap
import urlparse

import arrow
import flask
import md5

from pygments import highlight
from pygments.lexers.text import DiffLexer
from pygments.formatters import HtmlFormatter

import pagure.exceptions
import pagure.lib
import pagure.forms
from pagure import (APP, SESSION, authenticated, is_repo_admin)


# Jinja filters


@APP.template_filter('hasattr')
def jinja_hasattr(obj, string):
    """ Template filter checking if the provided object at the provided
    string as attribute
    """
    return hasattr(obj, string)


@APP.template_filter('render')
def jinja_render(tmpl, **kwargs):
    """ Render the given template with the provided arguments
    """
    return flask.render_template_string(tmpl, **kwargs)


@APP.template_filter('humanize')
def humanize_date(date):
    """ Template filter returning the last commit date of the provided repo.
    """
    return arrow.get(date).humanize()


@APP.template_filter('format_ts')
def format_ts(string):
    """ Template filter transforming a timestamp to a date
    """
    dattime = datetime.datetime.fromtimestamp(int(string))
    return dattime.strftime('%b %d %Y %H:%M:%S')


@APP.template_filter('format_loc')
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
            if commit and unicode(com.commit_id) == unicode(commit) \
                    and unicode(com.filename) == unicode(filename):
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
            output.append(
                '<tr id="c-%(commit)s-%(cnt_lbl)s"><td class="cell1">'
                '<a id="%(cnt)s" href="#%(cnt)s" data-line-number='
                '"%(cnt_lbl)s"></a></td>'
                '<td class="prc" data-row="%(cnt_lbl)s"'
                ' data-filename="%(filename)s" data-commit="%(commit)s"'
                ' data-tree="%(tree_id)s">'
                '<p>'
                '<span class="oi prc_img" data-glyph="comment-square" '
                'alt="Add comment" title="Add comment"></span>'
                '</p>'
                '</td>' % (
                    {
                        'cnt': '%s_%s' % (index, cnt),
                        'cnt_lbl': cnt,
                        'filename': filename.decode('UTF-8'),
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
        output.append('<td class="cell2"><pre>%s</pre></td>' % line)
        output.append('</tr>')

        tpl_edit = '<a href="%(edit_url)s" ' \
            'class="btn btn-secondary btn-sm" data-comment="%(commentid)s" ' \
            'data-objid="%(requestid)s">' \
            '<span class="oi" data-glyph="pencil"></span>' \
            '</a>'
        tpl_edited = '<small class="text-muted" title="%(edit_date)s"> ' \
            'Edited %(human_edit_date)s by %(user)s </small>'

        tpl_delete = '<button class="btn btn-secondary btn-sm" '\
            'title="Remove comment" '\
            'name="drop_comment" value="%(commentid)s" type="submit" ' \
            'onclick="return confirm(\'Do you really want to remove this comment?\');" '\
            '><span class="oi" data-glyph="trash"></span>' \
            '</button>'

        if cnt - 1 in comments:
            for comment in comments[cnt - 1]:

                templ_delete = ''
                templ_edit = ''
                templ_edited = ''
                status = str(comment.parent.status).lower()
                if authenticated() and (
                        (
                            status in ['true', 'open']
                            and comment.user.user == flask.g.fas_user.username
                        )
                        or is_repo_admin(comment.parent.project)):
                    templ_delete = tpl_delete % ({'commentid': comment.id})
                    templ_edit = tpl_edit % ({
                        'edit_url': flask.url_for(
                            'pull_request_edit_comment',
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
                        'edit_date': comment.edited_on.strftime(
                            '%b %d %Y %H:%M:%S'),
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
                    '<a href="%(url)s"> %(user)s</a> commented '
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
                                'view_user', username=comment.user.user),
                            'templ_delete': templ_delete,
                            'templ_edit': templ_edit,
                            'templ_edited': templ_edited,
                            'user': comment.user.user,
                            'avatar_url': avatar_url(
                                comment.user.default_email, 16),
                            'date': comment.date_created.strftime(
                                '%b %d %Y %H:%M:%S'),
                            'human_date': humanize_date(comment.date_created),
                            'comment': markdown_filter(comment.comment),
                            'commentid': comment.id,
                        }
                    )
                )

    output.append('</table></div>')

    return '\n'.join(output)


@APP.template_filter('blame_loc')
def blame_loc(loc, repo, username, blame):
    """ Template filter putting the provided lines of code into a table


    This method blame lines of code (loc) takes as input a text (lines of
    code) concerning a given repo, with its repo and a pygit2.Blame object
    and convert it into a html table displayed to the user with the git
    blame information (user, commit, commit date).

    :arg loc: a text object of the lines of code to display (in this case,
        most likely the content of a file).
    :arg repo: the name of the repo in which this file is.
    :arg username: the user name of the user whose repo this is, if the repo
        is not a *fork*, this value is ``None``.
    :arg blame: a pygit2.Blame object allowing us to link a given line of
        code to a commit.

    """
    if loc is None:
        return

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

        if line.startswith('<div'):
            line = line.split('<pre style="line-height: 125%">')[1]

        output.append(
            '<tr><td class="cell1">'
            '<a id="%(cnt)s" href="#%(cnt)s" data-line-number='
            '"%(cnt)s"></a></td>'
            % ({'cnt': idx + 1})
        )

        output.append(
            '<td class="cell_user">%s</td>' % author_to_user(
                diff.orig_committer, with_name=False)
        )

        output.append(
            '<td class="cell_commit"><a href="%s">%s</a></td>' % (
                flask.url_for('view_commit',
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


@APP.template_filter('wraps')
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


@APP.template_filter('avatar')
def avatar(packager, size=64):
    """ Template filter sorting the given branches, Fedora first then EPEL,
    then whatever is left.
    """
    if '@' not in packager:
        user = pagure.lib.search_user(SESSION, username=packager)
        if user:
            packager = user.default_email

    output = '<img class="avatar circle" src="%s"/>' % (
        avatar_url(packager, size)
    )

    return output


@APP.template_filter('avatar_url')
def avatar_url(email, size=64):
    """ Template filter sorting the given branches, Fedora first then EPEL,
    then whatever is left.
    """
    return pagure.lib.avatar_url_from_email(email, size)


@APP.template_filter('short')
def shorted_commit(cid):
    """Gets short version of the commit id"""
    return str(cid)[:APP.config['SHORT_LENGTH']]


@APP.template_filter('markdown')
def markdown_filter(text):
    """ Template filter converting a string into html content using the
    markdown library.
    """
    return pagure.lib.text2markdown(text)


@APP.template_filter('html_diff')
def html_diff(diff):
    """Display diff as HTML"""
    if diff is None:
        return
    return highlight(
        diff,
        DiffLexer(),
        HtmlFormatter(
            noclasses=True,
            style="tango",)
    )


@APP.template_filter('patch_to_diff')
def patch_to_diff(patch):
    """Render a hunk as a diff"""
    content = ""
    for hunk in patch.hunks:
        content = content + "@@ -%i,%i +%i,%i @@\n" % (
            hunk.old_start, hunk.old_lines, hunk.new_start, hunk.new_lines)
        for line in hunk.lines:
            if hasattr(line, 'content'):
                origin = line.origin
                if line.origin in ['<', '>', '=']:
                    origin = ''
                content = content + origin + ' ' + line.content
            else:
                # Avoid situation where at the end of a file we get:
                # + foo<
                # \ No newline at end of file
                if line[0] in ['<', '>', '=']:
                    line = ('', line[1])
                content = content + ' '.join(line)

    return content


@APP.template_filter('author2user')
def author_to_user(author, size=16, cssclass=None, with_name=True):
    """ Template filter transforming a pygit2 Author object into a text
    either with just the username or linking to the user in pagure.
    """
    output = author.name
    if not author.email:
        return output
    user = pagure.lib.search_user(SESSION, email=author.email)
    if user:
        output = "%(avatar)s <a title='%(name)s' href='%(url)s' "\
            "%(cssclass)s>%(username)s</a>"
        if not with_name:
            output = "<a title='%(name)s' href='%(url)s' "\
                "%(cssclass)s>%(avatar)s</a>"

        output = output % (
            {
                'avatar': avatar(user.default_email, size),
                'url': flask.url_for('view_user', username=user.username),
                'cssclass': ('class="%s"' % cssclass) if cssclass else '',
                'username': user.username,
                'name': author.name,
            }
        )

    return output


@APP.template_filter('author2avatar')
def author_to_avatar(author, size=32):
    """ Template filter transforming a pygit2 Author object into an avatar.
    """
    user = pagure.lib.search_user(SESSION, email=author.email)
    output = user.default_email if user else author.email
    return avatar(output.encode('utf-8'), size)


@APP.template_filter('author2user_commits')
def author_to_user_commits(author, link, size=16, cssclass=None):
    """ Template filter transforming a pygit2 Author object into a text
    either with just the username or linking to the user in pagure.
    """
    output = author.name
    if not author.email:
        return output
    user = pagure.lib.search_user(SESSION, email=author.email)
    if user:
        output = "<a href='%s'>%s</a> <a href='%s' %s>%s</a>" % (
            flask.url_for('view_user', username=user.username),
            avatar(user.default_email, size),
            link,
            ('class="%s"' % cssclass) if cssclass else '',
            author.name,
        )

    return output


@APP.template_filter('InsertDiv')
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
            row = str(row).replace(
                '<h1 class="title">',
                '<h1 class="title">'
                '<span class="oi" data-glyph="collapse-down"></span> &nbsp;'
            )
        output.append(row)
    output = "\n".join(output)
    output = output.replace('</h1>', '</h1>\n<div>', 1)
    output = output.replace('h1', 'h3')

    return output


@APP.template_filter('noJS')
def no_js(content, ignore=None):
    """ Template filter replacing <script by &lt;script and </script> by
    &lt;/script&gt;
    """
    return pagure.lib.clean_input(content, ignore=ignore)


@APP.template_filter('toRGB')
def int_to_rgb(percent):
    """ Template filter converting a given percentage to a css RGB value.
    """
    output = "rgb(255, 0, 0);"
    try:
        percent = int(percent)
        if percent < 50:
            red = 255
            green = (255.0/50) * percent
        else:
            green = 255
            red = (255.0/50) * (100 - percent)
        output = "rgb(%s, %s, 0);" % (int(red), int(green))
    except ValueError:
        pass
    return output


@APP.template_filter('return_md5')
def return_md5(text):
    """ Template filter to return an MD5 for a string
    """
    hashedtext = md5.new()
    hashedtext.update(text)
    return pagure.lib.clean_input(hashedtext.hexdigest())


@APP.template_filter('increment_largest_priority')
def largest_priority(dictionary):
    """ Template filter to return the largest priority +1
    """
    if dictionary:
        return max([int(k) for k in dictionary if k]) + 1
    else:
        return 1


@APP.template_filter('unicode')
def convert_unicode(text):
    ''' If the provided string is a binary string, this filter converts it
    to UTF-8 (unicode).
    '''
    if isinstance(text, str):
        return text.decode("utf8")
    else:
        return text


@APP.template_filter('combine_url')
def combine_url(url, page, pagetitle, **kwargs):
    """ Add the specified arguments in the provided kwargs dictionary to
    the given URL.
    """
    url_obj = urlparse.urlparse(url)
    url = url_obj.geturl().replace(url_obj.query, '').rstrip('?')
    query = dict(urlparse.parse_qsl(url_obj.query))
    query[pagetitle] = page
    query.update(kwargs)
    return url + '?' + '&'.join(['%s=%s' % (k, query[k]) for k in query])
