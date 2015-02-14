#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources

__version__ = '0.0'

import datetime
import logging
import os
import subprocess
import textwrap
import urlparse
from logging.handlers import SMTPHandler

import arrow
import flask
import pygit2
from flask_fas_openid import FAS
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError

import progit.lib
import progit.mail_logging
import progit.doc_utils
import progit.login_forms
import markdown

from pygments import highlight
from pygments.lexers.text import DiffLexer
from pygments.formatters import HtmlFormatter

# Create the application.
APP = flask.Flask(__name__)
APP.jinja_env.trim_blocks = True
APP.jinja_env.lstrip_blocks = True

# set up FAS
APP.config.from_object('progit.default_config')

if 'PROGIT_CONFIG' in os.environ:
    APP.config.from_envvar('PROGIT_CONFIG')


FAS = FAS(APP)
SESSION = progit.lib.create_session(APP.config['DB_URL'])

if not APP.debug:
    APP.logger.addHandler(progit.mail_logging.get_mail_handler(
        smtp_server=APP.config.get('SMTP_SERVER', '127.0.0.1'),
        mail_admin=APP.config.get('MAIL_ADMIN', APP.config['EMAIL_ERROR'])
    ))

## Send classic logs into syslog
handler = logging.StreamHandler()
handler.setLevel(APP.config.get('log_level', 'INFO'))
APP.logger.addHandler(handler)

LOG = APP.logger


def authenticated():
    return hasattr(flask.g, 'fas_user') and flask.g.fas_user


def is_safe_url(target):
    """ Checks that the target url is safe and sending to the current
    website not some other malicious one.
    """
    ref_url = urlparse.urlparse(flask.request.host_url)
    test_url = urlparse.urlparse(
        urlparse.urljoin(flask.request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


def is_admin():
    """ Return whether the user is admin for this application or not. """
    if not authenticated():
        return False

    user = flask.g.fas_user

    auth_method = APP.config.get('PROGIT_AUTH', None)
    if auth_method == 'fas':
        if not user.cla_done or len(user.groups) < 1:
            return False

    admins = APP.config['ADMIN_GROUP']
    if isinstance(admins, basestring):
        admins = [admins]
    admins = set(admins)
    groups = set(flask.g.fas_user.groups)

    return not groups.isdisjoint(admins)


def is_repo_admin(repo_obj):
    """ Return whether the user is an admin of the provided repo. """
    if not authenticated():
        return False

    user = flask.g.fas_user.username

    return user == repo_obj.user.user or (
        user in [user.user for user in repo_obj.users])


def generate_gitolite_acls():
    """ Generate the gitolite configuration file for all repos
    """
    progit.lib.generate_gitolite_acls(
        SESSION, APP.config['GITOLITE_CONFIG'])

    gitolite_folder = APP.config.get('GITOLITE_HOME', None)
    if gitolite_folder:
        cmd = 'GL_RC=%s GL_BINDIR=%s gl-compile-conf' % (
            APP.config.get('GL_RC'), APP.config.get('GL_BINDIR')
        )
        output = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=gitolite_folder
        )


def generate_gitolite_key(user, key):
    """ Generate the gitolite ssh key file for the specified user
    """
    gitolite_keydir = APP.config.get('GITOLITE_KEYDIR', None)
    if gitolite_keydir:
        keyfile = os.path.join(gitolite_keydir, '%s.pub' % user)
        with open(keyfile, 'w') as stream:
            stream.write(key + '\n')


def generate_authorized_key_file():
    """ Regenerate the `authorized_keys` file used by gitolite.
    """
    gitolite_home = APP.config.get('GITOLITE_HOME', None)
    if gitolite_home:
        users = progit.lib.get_all_users(SESSION)

        authorized_file = os.path.join(
            gitolite_home, '.ssh', 'authorized_keys')
        with open(authorized_file, 'w') as stream:
            stream.write('# gitolite start\n')
            for user in users:
                if not user.public_ssh_key:
                    continue
                row = 'command="/usr/bin/gl-auth-command %s",' \
                      'no-port-forwarding,no-X11-forwarding,'\
                      'no-agent-forwarding,no-pty %s' % (
                          user.user, user.public_ssh_key)
                stream.write(row + '\n')
            stream.write('# gitolite end\n')


def cla_required(function):
    """ Flask decorator to retrict access to CLA signed user.
To use this decorator you need to have a function named 'auth_login'.
Without that function the redirect if the user is not logged in will not
work.
"""
    auth_method = APP.config.get('PROGIT_AUTH', None)
    @wraps(function)
    def decorated_function(*args, **kwargs):
        """ Decorated function, actually does the work. """
        if not authenticated():
            return flask.redirect(
                flask.url_for('auth_login', next=flask.request.url))
        elif auth_method == 'fas' and not flask.g.fas_user.cla_done:
            flask.flash('You must sign the CLA (Contributor License '
                        'Agreement to use progit', 'errors')
            return flask.redirect(flask.url_for('.index'))
        return function(*args, **kwargs)
    return decorated_function


@APP.context_processor
def inject_variables():
    """ With this decorator we can set some variables to all templates.
    """
    user_admin = is_admin()

    return dict(
        version=__version__,
        admin=user_admin,
        authenticated=authenticated(),
    )


# pylint: disable=W0613
@APP.before_request
def set_session():
    """ Set the flask session as permanent. """
    flask.session.permanent = True


@APP.template_filter('lastcommit_date')
def lastcommit_date_filter(repo):
    """ Template filter returning the last commit date of the provided repo.
    """
    if not repo.is_empty:
        commit = repo[repo.head.target]
        return arrow.get(commit.commit_time).humanize()


@APP.template_filter('humanize')
def humanize_date(date):
    """ Template filter returning the last commit date of the provided repo.
    """
    return arrow.get(date).humanize()


@APP.template_filter('rst2html')
def rst2html(rst_string):
    """ Template filter transforming rst text into html
    """
    if rst_string:
        return progit.doc_utils.convert_doc(unicode(rst_string))


@APP.template_filter('format_ts')
def format_ts(string):
    """ Template filter transforming a timestamp to a date
    """
    dt = datetime.datetime.fromtimestamp(int(string))
    return dt.strftime('%b %d %Y %H:%M:%S')


@APP.template_filter('format_loc')
def format_loc(loc, commit=None, prequest=None, index=None):
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
            if commit and com.commit_id == commit.oid.hex:
                if com.line in comments:
                    comments[com.line].append(com)
                else:
                    comments[com.line] = [com]
    for key in comments:
        comments[key] = sorted(comments[key], key=lambda obj: obj.date_created)

    if not index:
        index = ''

    cnt = 1
    for line in loc.split('\n'):
        if commit:
            output.append(
                '<tr><td class="cell1">'
                '<a id="%(cnt)s" href="#%(cnt)s">%(cnt_lbl)s</a></td>'
                '<td class="prc" data-row="%(cnt_lbl)s" data-commit="%(commitid)s">'
                '<p>'
                '<img src="%(img)s" alt="Add comment" title="Add comment"/>'
                '</p>'
                '</td>' % (
                    {
                        'cnt': '%s_%s' % (index, cnt),
                        'cnt_lbl': cnt,
                        'img': flask.url_for('static', filename='users.png'),
                        'commitid': commit.oid.hex,
                    }
                )
            )
        else:
            output.append(
                '<tr><td class="cell1">'
                '<a id="%(cnt)s" href="#%(cnt)s">%(cnt_lbl)s</a></td>'
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
        if line == '</pre></div>':
            continue
        if line.startswith('<div'):
            line = line.split('<pre style="line-height: 125%">')[1]
        output.append('<td class="cell2"><pre>%s</pre></td>' % line)
        output.append('</tr>')

        if cnt - 1 in comments:
            for comment in comments[cnt -1]:
                output.append(
                    '<tr><td></td>'
                    '<td colspan="2"><table style="width:100%%"><tr>'
                    '<td><a href="%(url)s">%(user)s</a></td><td class="right">%(date)s</td>'
                    '</tr>'
                    '<tr><td colspan="2" class="pr_comment">%(comment)s</td></tr>'
                    '</table></td></tr>' % (
                        {
                            'url': flask.url_for(
                                'view_user', username=comment.user.user),
                            'user': comment.user.user,
                            'date': comment.date_created.strftime(
                                '%b %d %Y %H:%M:%S'),
                            'comment': comment.comment,
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
def avatar(packager, size=64):
    """ Template filter sorting the given branches, Fedora first then EPEL,
    then whatever is left.
    """
    output = '<img class="avatar circle" src="%s"/>' % (
        progit.lib.avatar_url(packager, size)
    )

    return output


@APP.template_filter('short')
def shorted_commit(cid):
    """Gets short version of the commit id"""
    return cid[:APP.config['SHORT_LENGTH']]


@APP.template_filter('markdown')
def markdown_filter(text):
    """ Template filter converting a string into html content using the
    markdown library.
    """
    if text:
        # Hack to allow blockquotes to be marked by ~~~
        ntext = []
        indent = False
        for line in text.split('\n'):
            if line.startswith('~~~'):
                indent = not indent
                continue
            if indent:
                line = '    %s' % line
            ntext.append(line)
        return markdown.markdown('\n'.join(ntext))

    return ''


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
        content = content + "@@ -%i,%i +%i,%i @@\n" % (hunk.old_start,
            hunk.old_lines, hunk.new_start, hunk.new_lines)
        for line in hunk.lines:
            content = content + ' '.join(line)
    return content


@APP.template_filter('diff_to_diff')
def diff_to_diff(diff):
    """Render a hunk as a diff"""
    content = ""
    patches = [p for p in diff]
    for patch in patches:
        for hunk in patch.hunks:
            content = content + "@@ -%i,%i +%i,%i @@\n" % (hunk.old_start,
                hunk.old_lines, hunk.new_start, hunk.new_lines)
            for line in hunk.lines:
                content = content + ' '.join(line)
    return content


@FAS.postlogin
def set_user(return_url):
    ''' After login method. '''
    try:
        progit.lib.set_up_user(
            session=SESSION,
            username=flask.g.fas_user.username,
            fullname=flask.g.fas_user.fullname,
            user_email=flask.g.fas_user.email,
        )
        SESSION.commit()
    except SQLAlchemyError, err:
        SESSION.rollback()
        LOG.debug(err)
        LOG.exception(err)
        flask.flash(
            'Could not set up you as a user properly, please contact '
            'an admin', 'error')
    return flask.redirect(return_url)


@APP.errorhandler(404)
def not_found(error):
    """404 Not Found page"""
    return flask.render_template('not_found.html'), 404


@APP.errorhandler(500)
def fatal_error(error):
    """500 Fatal Error page"""
    return flask.render_template('fatal_error.html'), 500


@APP.errorhandler(401)
def unauthorized(error):
    """401 Unauthorized page"""
    return flask.render_template('unauthorized.html'), 401


@APP.route('/login/', methods=('GET', 'POST'))
def auth_login():
    """ Method to log into the application using FAS OpenID. """
    return_point = flask.url_for('index')
    if 'next' in flask.request.args:
        if is_safe_url(flask.request.args['next']):
            return_point = flask.request.args['next']

    if authenticated():
        return flask.redirect(return_point)

    admins = APP.config['ADMIN_GROUP']
    if isinstance(admins, basestring):
        admins = set([admins])
    else:  # pragma: no cover
        admins = set(admins)

    if APP.config.get('PROGIT_AUTH', None) == 'fas':
        return FAS.login(return_url=return_point, groups=admins)
    elif APP.config.get('PROGIT_AUTH', None) == 'local':
        form = progit.login_forms.LoginForm()
        return flask.render_template(
            'login/login.html',
            next_url=return_point,
            form=form,
        )


@APP.route('/logout/')
def auth_logout():
    """ Method to log out from the application. """
    return_point = flask.url_for('index')
    if 'next' in flask.request.args:
        if is_safe_url(flask.request.args['next']):
            return_point = flask.request.args['next']

    if not authenticated():
        return flask.redirect(return_point)

    if APP.config.get('PROGIT_AUTH', None) == 'fas':
        if hasattr(flask.g, 'fas_user') and flask.g.fas_user is not None:
            FAS.logout()
            flask.flash("You are no longer logged-in")
    elif APP.config.get('PROGIT_AUTH', None) == 'local':
        login.logout()
    return flask.redirect(return_point)


def __get_file_in_tree(repo_obj, tree, filepath):
    ''' Retrieve the entry corresponding to the provided filename in a
    given tree.
    '''
    filename = filepath[0]
    if isinstance(tree, pygit2.Blob):
        return
    for el in tree:
        if el.name == filename:
            if len(filepath) == 1:
                return repo_obj[el.oid]
            else:
                return __get_file_in_tree(
                    repo_obj, repo_obj[el.oid], filepath[1:])


## Import the application
import progit.ui.app
import progit.ui.admin
import progit.ui.docs
import progit.ui.fork
import progit.ui.issues
import progit.ui.plugins
import progit.ui.repo


# Only import the login controller if the app is set up for local login
if APP.config.get('PROGIT_AUTH', None) == 'local':
    import progit.ui.login as login
    APP.before_request(login._check_session_cookie)
    APP.after_request(login._send_session_cookie)
