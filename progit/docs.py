#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import os
from math import ceil

import pygit2
from sqlalchemy.exc import SQLAlchemyError
from pygments import highlight
from pygments.lexers import guess_lexer
from pygments.lexers.text import DiffLexer
from pygments.formatters import HtmlFormatter


import progit.doc_utils
import progit.exceptions
import progit.lib
import progit.forms
from progit import APP, SESSION, LOG, cla_required


def __get_tree(repo_obj, tree, filepath, startswith=False):
    ''' Retrieve the entry corresponding to the provided filename in a
    given tree.
    '''
    filename = filepath[0]
    if isinstance(tree, pygit2.Blob):
        return (tree, None)
    cnt = 0
    for el in tree:
        cnt += 1
        ok = False
        if el.name.startswith(filename):
            ok = True
        if el.name == filename:
            ok = True
        if ok and len(filepath) == 1:
            return (el, tree)
        elif ok:
            return __get_tree(
                repo_obj, repo_obj[el.oid], filepath[1:],
                startswith=startswith)

    if len(filepath) == 1:
        raise progit.exceptions.FileNotFoundException('File not found')
    else:
        return __get_tree(
            repo_obj, repo_obj[tree.oid], filepath[1:],
            startswith=startswith)


def __get_tree_and_content(repo_obj, commit, path, startswith):
    ''' Return the tree and the content of the specified file. '''

    try:
        (blob_or_tree, tree_obj) = __get_tree(
            repo_obj, commit.tree, path, startswith=startswith)
    except progit.exceptions.FileNotFoundException:
        flask.abort(404, 'File not found')

    if not repo_obj[blob_or_tree.oid]:
        flask.abort(404, 'File not found')

    blob_or_tree_obj = repo_obj[blob_or_tree.oid]
    blob = repo_obj[blob_or_tree.oid]

    content = None
    if isinstance(blob, pygit2.Blob):  # Returned a file
        name, ext = os.path.splitext(blob_or_tree.name)
        content = progit.doc_utils.convert_readme(blob_or_tree_obj.data, ext)
    else:  # Returned a tree
        raise progit.exceptions.FileNotFoundException('File not found')

    tree = sorted(tree_obj, key=lambda x: x.filemode)
    return (tree, content)


## URLs


@APP.route('/<repo>/docs')
@APP.route('/<repo>/docs/<path:filename>')
@APP.route('/<repo>/docs/<branchname>')
@APP.route('/<repo>/docs/<branchname>/<path:filename>')
@APP.route('/fork/<username>/<repo>/docs')
@APP.route('/fork/<username>/<repo>/docs/<path:filename>')
@APP.route('/fork/<username>/<repo>/docs/<branchname>')
@APP.route('/fork/<username>/<repo>/docs/<branchname>/<path:filename>')
def view_docs(repo, username=None, branchname=None, filename=None):
    """ Display the documentation
    """
    status = flask.request.args.get('status', None)

    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not repo.project_docs:
        flask.abort(404, 'No documentation found for this project')

    reponame = os.path.join(APP.config['DOCS_FOLDER'], repo.path)
    if not os.path.exists(reponame):
        flask.flash(
            'No docs repository could be found, please contact an admin',
            'error')
        return flask.redirect(flask.url_for(
            'view_repo', repo=repo.name, username=username))

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
    startswith = False
    if not filename:
        path = ['index']
        startswith = True
    else:
        path = filename.split('/')

    if commit:
        try:
            (tree, content) = __get_tree_and_content(
                repo_obj, commit, path, startswith)
        except progit.exceptions.FileNotFoundException:
            if not path[0].startswith('index'):
                path.append('index')
                filename = filename + '/'
        (tree, content) = __get_tree_and_content(
            repo_obj, commit, path, startswith=True)

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
    )
