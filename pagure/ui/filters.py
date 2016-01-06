# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import datetime
import textwrap

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
def format_loc(loc, commit=None, filename=None, prequest=None, index=None):
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
                '<tr><td class="cell1">'
                '<a id="%(cnt)s" href="#%(cnt)s" data-line-number="%(cnt_lbl)s"></a></td>'
                '<td class="prc" data-row="%(cnt_lbl)s"'
                ' data-filename="%(filename)s" data-commit="%(commit)s">'
                '<p>'
                '<img class="prc_img" src="%(img)s" alt="Add comment" title="Add comment"/>'
                '</p>'
                '</td>' % (
                    {
                        'cnt': '%s_%s' % (index, cnt),
                        'cnt_lbl': cnt,
                        'img': flask.url_for('static', filename='users.png'),
                        'filename': filename,
                        'commit': commit,
                    }
                )
            )
        else:
            output.append(
                '<tr><td class="cell1">'
                '<a id="%(cnt)s" href="#%(cnt)s" data-line-number="%(cnt_lbl)s"></a></td>'
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
            'class="edit_btn" data-comment="%(commentid)s" ' \
            'data-objid="%(requestid)s">' \
            '<span class="icon icon-edit blue"></span>' \
            '</a>'
        tpl_edited = '<small class="text-muted" title="%(edit_date)s"> ' \
            'Edited %(human_edit_date)s by %(user)s </small>'

        tpl_delete = '<button class="btn btn-danger btn-sm" '\
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
                if authenticated() and (
                        (comment.parent.status is True
                         and comment.user.user == flask.g.fas_user.username)
                         or is_repo_admin(comment.parent.project)):
                    templ_delete = tpl_delete % ({'commentid': comment.id})
                    templ_edit = tpl_edit %({
                        'edit_url': flask.url_for(
                            'pull_request_edit_comment',
                            repo=comment.parent.project.name,
                            requestid=comment.parent.id,
                            commentid=comment.id,
                            username=comment.parent.user.user \
                                if comment.parent.project.is_fork else None
                        ),
                        'requestid': comment.parent.id,
                        'commentid': comment.id,
                    })

                if comment.edited_on:
                    templ_edited = tpl_edited %({
                        'edit_date':comment.edited_on.strftime(
                            '%b %d %Y %H:%M:%S'),
                        'human_edit_date': humanize_date(comment.edited_on),
                        'user': comment.editor.user,
                    })

                output.append(
                    '<tr><td></td>'
                    '<td colspan="2">'
                    '<div class="card clearfix">'
                    '<div id="comment-%(commentid)s" class="card-header">'
                    '<img class="avatar circle" src="%(avatar_url)s"/>'
                    '<a href="%(url)s"> %(user)s</a>'
                    '<a class="headerlink pull-xs-right" title="Permalink '
                    'to this headline" href="#comment-%(commentid)s">'
                    '<span title="%(date)s">%(human_date)s</span>'
                    '</a></div>'
                    '<div class="card-block">'
                    '<section class="issue_comment">'
                    '<div class="comment_body">'
                    '%(comment)s'
                    '</div>'
                    '</section>'
                    '<div class="issue_actions m-t-2">'
                    '%(templ_edited)s'
                    '<aside class="issue_action icon pull-xs-right p-b-1">'
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
                                comment.user.default_email, 32),
                            'date': comment.date_created.strftime(
                                '%b %d %Y %H:%M:%S'),
                            'human_date': humanize_date(comment.date_created),
                            'comment': markdown_filter(comment.comment),
                            'commentid': comment.id,
                            'anchor': u'¶',
                        }
                    )
                )

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
def avatar(packager, size=64, default="retro"):
    """ Template filter sorting the given branches, Fedora first then EPEL,
    then whatever is left.
    """
    output = '<img class="avatar circle" src="%s"/>' % (
        pagure.lib.avatar_url(packager, size, default)
    )

    return output


@APP.template_filter('avatar_url')
def avatar_url(email, size=64):
    """ Template filter sorting the given branches, Fedora first then EPEL,
    then whatever is left.
    """
    return pagure.lib.avatar_url_from_openid(email, size)


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
                content = content + line.origin + ' '+ line.content
            else:
                # Avoid situation where at the end of a file we get:
                # + foo<
                # \ No newline at end of file
                if line[0] == '<':
                    line = ('',line[1])
                content = content + ' '.join(line)

    return content


@APP.template_filter('author2user')
def author_to_user(author, size=16):
    """ Template filter transforming a pygit2 Author object into a text
    either with just the username or linking to the user in pagure.
    """
    user = pagure.lib.search_user(SESSION, email=author.email)
    output = author.name
    if user:
        output = "%s <a href='%s'>%s</a>" % (
            avatar(user.user, size),
            flask.url_for('view_user', username=user.username),
            author.name,
        )
    return output


@APP.template_filter('author2avatar')
def author_to_avatar(author, size=32):
    """ Template filter transforming a pygit2 Author object into an avatar.
    """
    user = pagure.lib.search_user(SESSION, email=author.email)
    output = user.user if user else author.name
    return avatar(output, size)


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
    m = md5.new()
    m.update(text)
    return pagure.lib.clean_input(m.hexdigest())
