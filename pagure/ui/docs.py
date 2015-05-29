# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import os

import pygit2

import pagure.doc_utils
import pagure.exceptions
import pagure.lib
import pagure.forms
from pagure import APP, SESSION


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
        return (tree_obj, None, extended)

    if not repo_obj[blob_or_tree.oid]:
        # Not tested and no idea how to test it, but better safe than sorry
        flask.abort(404, 'File not found')

    if isinstance(blob_or_tree, pygit2.TreeEntry):  # Returned a file
        ext = os.path.splitext(blob_or_tree.name)[1]
        blob_obj = repo_obj[blob_or_tree.oid]
        content = pagure.doc_utils.convert_readme(blob_obj.data, ext)

    tree = sorted(tree_obj, key=lambda x: x.filemode)
    return (tree, content, extended)


# URLs


@APP.route('/<repo>/docs/')
@APP.route('/<repo>/docs')
@APP.route('/<repo>/docs/<path:filename>')
@APP.route('/<repo>/docs/<branchname>')
@APP.route('/<repo>/docs/<branchname>/<path:filename>')
@APP.route('/fork/<username>/<repo>/docs/')
@APP.route('/fork/<username>/<repo>/docs')
@APP.route('/fork/<username>/<repo>/docs/<path:filename>')
@APP.route('/fork/<username>/<repo>/docs/<branchname>')
@APP.route('/fork/<username>/<repo>/docs/<branchname>/<path:filename>')
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
    if not filename:
        path = ['']
    else:
        path = [it for it in filename.split('/') if it]

    if commit:
        try:
            (tree, content, extended) = __get_tree_and_content(
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
    )
