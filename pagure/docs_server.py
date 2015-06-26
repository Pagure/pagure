# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import logging
import os

import flask
import pygit2

import pagure.doc_utils
import pagure.exceptions
import pagure.lib
import pagure.forms

# Create the application.
APP = flask.Flask(__name__)

# set up FAS
APP.config.from_object('pagure.default_config')

if 'PAGURE_CONFIG' in os.environ:
    APP.config.from_envvar('PAGURE_CONFIG')

SESSION = pagure.lib.create_session(APP.config['DB_URL'])

if not APP.debug:
    APP.logger.addHandler(pagure.mail_logging.get_mail_handler(
        smtp_server=APP.config.get('SMTP_SERVER', '127.0.0.1'),
        mail_admin=APP.config.get('MAIL_ADMIN', APP.config['EMAIL_ERROR'])
    ))

# Send classic logs into syslog
handler = logging.StreamHandler()
handler.setLevel(APP.config.get('log_level', 'INFO'))
APP.logger.addHandler(handler)

LOG = APP.logger


def __get_tree(repo_obj, tree, filepath, index=0, extended=False):
    ''' Retrieve the entry corresponding to the provided filename in a
    given tree.
    '''
    filename = filepath[index]
    if isinstance(tree, pygit2.Blob):  # pragma: no cover
        # If we were given a blob, then let's just return it
        return (tree, None, None)

    for element in tree:
        if element.name == filename or element.name.startswith('index'):
            # If we have a folder we must go one level deeper
            if element.filemode == 16384:
                if (index + 1) == len(filepath):
                    filepath.append('')
                return __get_tree(
                    repo_obj, repo_obj[element.oid], filepath,
                    index=index + 1, extended=True)
            else:
                return (element, tree, False)

    if filename == '':
        return (None, tree, extended)
    else:
        raise pagure.exceptions.FileNotFoundException(
            'File %s not found' % ('/'.join(filepath),))


def __get_tree_and_content(repo_obj, commit, path):
    ''' Return the tree and the content of the specified file. '''

    (blob_or_tree, tree_obj, extended) = __get_tree(
        repo_obj, commit.tree, path)

    if blob_or_tree is None:
        return (tree_obj, None, False, extended)

    if not repo_obj[blob_or_tree.oid]:
        # Not tested and no idea how to test it, but better safe than sorry
        flask.abort(404, 'File not found')

    if isinstance(blob_or_tree, pygit2.TreeEntry):  # Returned a file
        ext = os.path.splitext(blob_or_tree.name)[1]
        blob_obj = repo_obj[blob_or_tree.oid]
        content, safe = pagure.doc_utils.convert_readme(blob_obj.data, ext)

    tree = sorted(tree_obj, key=lambda x: x.filemode)
    return (tree, content, safe, extended)


# Jinja filter required

@APP.template_filter('markdown')
def markdown_filter(text):
    """ Template filter converting a string into html content using the
    markdown library.
    """
    return pagure.lib.text2markdown(text, extended=False)


# Placeholder to allow re-using pagure's templates
@APP.route('/')
def index():
    return flask.redirect(APP.config['APP_URL'])


@APP.route('/users/')
def view_users():
    root_url = APP.config['APP_URL']
    if root_url.endswith('/'):
        root_url = root_url[:-1]
    return flask.redirect(root_url + '/users/')


@APP.route('/groups/')
def group_lists():
    root_url = APP.config['APP_URL']
    if root_url.endswith('/'):
        root_url = root_url[:-1]
    return flask.redirect(root_url + '/groups/')


@APP.route('/new/')
def new_project():
    root_url = APP.config['APP_URL']
    if root_url.endswith('/'):
        root_url = root_url[:-1]
    return flask.redirect(root_url + '/new/')


@APP.route('/repo/<repo>/')
@APP.route('/repo/fork/<username>/<repo>/')
def view_repo(repo, username=None):
    root_url = APP.config['APP_URL']
    if root_url.endswith('/'):
        root_url = root_url[:-1]
    return flask.redirect(
        root_url + flask.url_for('.view_docs', repo=repo, username=username))


@APP.route('/<repo>/issues/')
@APP.route('/fork/<username>/<repo>/issues/')
def view_issues(repo, username=None):
    root_url = APP.config['APP_URL']
    if root_url.endswith('/'):
        root_url = root_url[:-1]
    return flask.redirect(
        root_url
        + flask.url_for('.view_docs', repo=repo, username=username)
        + 'issues/')


@APP.route('/<repo>/commits/')
@APP.route('/fork/<username>/<repo>/commits/')
def view_commits(repo, username=None):
    root_url = APP.config['APP_URL']
    if root_url.endswith('/'):
        root_url = root_url[:-1]
    return flask.redirect(
        root_url
        + flask.url_for('.view_docs', repo=repo, username=username)
        + 'commits/')


@APP.route('/<repo>/tree/')
@APP.route('/fork/<username>/<repo>/tree/')
def view_tree(repo, username=None):
    root_url = APP.config['APP_URL']
    if root_url.endswith('/'):
        root_url = root_url[:-1]
    return flask.redirect(
        root_url
        + flask.url_for('.view_docs', repo=repo, username=username)
        + 'tree/')


@APP.route('/<repo>/tags/')
@APP.route('/fork/<username>/<repo>/tags/')
def view_tags(repo, username=None):
    root_url = APP.config['APP_URL']
    if root_url.endswith('/'):
        root_url = root_url[:-1]
    return flask.redirect(
        root_url
        + flask.url_for('.view_docs', repo=repo, username=username)
        + 'tags/')


@APP.route('/<repo>/pull-requests/')
@APP.route('/fork/<username>/<repo>/pull-requests/')
def request_pulls(repo, username=None):
    root_url = APP.config['APP_URL']
    if root_url.endswith('/'):
        root_url = root_url[:-1]
    return flask.redirect(
        root_url
        + flask.url_for('.view_docs', repo=repo, username=username)
        + 'pull-requests/')


@APP.route('/<repo>/forks/')
@APP.route('/fork/<username>/<repo>/forks/')
def view_forks(repo, username=None):
    root_url = APP.config['APP_URL']
    if root_url.endswith('/'):
        root_url = root_url[:-1]
    return flask.redirect(
        root_url
        + flask.url_for('.view_docs', repo=repo, username=username)
        + 'forks/')


# The actual logic of the doc server

@APP.route('/<repo>/')
@APP.route('/<repo>')
@APP.route('/<repo>/<path:filename>')
@APP.route('/<repo>/<branchname>')
@APP.route('/<repo>/<branchname>/<path:filename>')
@APP.route('/fork/<username>/<repo>/')
@APP.route('/fork/<username>/<repo>')
@APP.route('/fork/<username>/<repo>/<path:filename>')
@APP.route('/fork/<username>/<repo>/<branchname>')
@APP.route('/fork/<username>/<repo>/<branchname>/<path:filename>')
def view_docs(repo, username=None, branchname=None, filename=None):
    """ Display the documentation
    """

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('project_documentation', True):
        flask.abort(404, 'No documentation found for this project')

    reponame = os.path.join(APP.config['DOCS_FOLDER'], repo.path)
    if not os.path.exists(reponame):
        flask.abort(404, 'Documentation not found')

    repo_obj = pygit2.Repository(reponame)

    if branchname in repo_obj.listall_branches():
        branch = repo_obj.lookup_branch(branchname)
        commit = branch.get_object()
    else:
        if not repo_obj.is_empty:
            commit = repo_obj[repo_obj.head.target]
        else:
            commit = None
        branchname = 'master'

    content = None
    tree = None
    safe = False
    if not filename:
        path = ['']
    else:
        path = [it for it in filename.split('/') if it]

    if commit:
        try:
            (tree, content, safe, extended) = __get_tree_and_content(
                repo_obj, commit, path)
            if extended:
                filename += '/'
        except pagure.exceptions.FileNotFoundException as err:
            flask.flash(err.message, 'error')

    return flask.render_template(
        'docs.html',
        select='docs',
        repo_obj=repo_obj,
        repo=repo,
        username=username,
        branchname=branchname,
        filename=filename,
        tree=tree,
        content=content,
        safe=safe,
        nologin=True,
    )
