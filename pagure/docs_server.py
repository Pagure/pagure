# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import logging
import os

import flask
import pygit2

from binaryornot.helpers import is_binary_string

import pagure.config
import pagure.doc_utils
import pagure.exceptions
import pagure.lib.mimetype
import pagure.lib.model_base
import pagure.lib.query
import pagure.forms

# Create the application.
APP = flask.Flask(__name__)

# set up FAS
APP.config = pagure.config.reload_config()

SESSION = pagure.lib.model_base.create_session(APP.config["DB_URL"])

if not APP.debug:
    APP.logger.addHandler(
        pagure.mail_logging.get_mail_handler(
            smtp_server=APP.config.get("SMTP_SERVER", "127.0.0.1"),
            mail_admin=APP.config.get("MAIL_ADMIN", APP.config["EMAIL_ERROR"]),
            from_email=APP.config.get(
                "FROM_EMAIL", "pagure@fedoraproject.org"
            ),
        )
    )

# Send classic logs into syslog
SHANDLER = logging.StreamHandler()
SHANDLER.setLevel(APP.config.get("log_level", "INFO"))
APP.logger.addHandler(SHANDLER)

_log = logging.getLogger(__name__)

TMPL_HTML = """
<!DOCTYPE html>
<html lang='en'>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
  <style type="text/css">
    ul {{
      margin: 0;
      padding: 0;
    }}
  </style>
</head>
<body>
{content}
</body>
</html>
"""


def __get_tree(repo_obj, tree, filepath, index=0, extended=False):
    """ Retrieve the entry corresponding to the provided filename in a
    given tree.
    """
    filename = filepath[index]
    if isinstance(tree, pygit2.Blob):  # pragma: no cover
        # If we were given a blob, then let's just return it
        return (tree, None, None)

    for element in tree:
        if element.name == filename or (
            not filename and element.name.startswith("index")
        ):
            # If we have a folder we must go one level deeper
            if element.filemode == 16384:
                if (index + 1) == len(filepath):
                    filepath.append("")
                return __get_tree(
                    repo_obj,
                    repo_obj[element.oid],
                    filepath,
                    index=index + 1,
                    extended=True,
                )
            else:
                return (element, tree, False)

    if filename == "":
        return (None, tree, extended)
    else:
        raise pagure.exceptions.FileNotFoundException(
            "File %s not found" % ("/".join(filepath),)
        )


def __get_tree_and_content(repo_obj, commit, path):
    """ Return the tree and the content of the specified file. """

    (blob_or_tree, tree_obj, extended) = __get_tree(
        repo_obj, commit.tree, path
    )

    if blob_or_tree is None:
        return (tree_obj, None, None)

    if not repo_obj[blob_or_tree.oid]:
        # Not tested and no idea how to test it, but better safe than sorry
        flask.abort(404, description="File not found")

    is_file = False
    try:
        is_file = isinstance(blob_or_tree, pygit2.TreeEntry)
    except AttributeError:
        is_file = isinstance(blob_or_tree, pygit2.Blob)

    if is_file:
        filename = blob_or_tree.name
        name, ext = os.path.splitext(filename)
        blob_obj = repo_obj[blob_or_tree.oid]
        if not is_binary_string(blob_obj.data):
            try:
                content, safe = pagure.doc_utils.convert_readme(
                    blob_obj.data, ext
                )
                if safe:
                    filename = name + ".html"
            except pagure.exceptions.PagureEncodingException:
                content = blob_obj.data
        else:
            content = blob_obj.data

    tree = sorted(tree_obj, key=lambda x: x.filemode)
    return (tree, content, filename)


@APP.route("/<repo>/")
@APP.route("/<namespace>.<repo>/")
@APP.route("/<repo>/<path:filename>")
@APP.route("/<namespace>.<repo>/<path:filename>")
@APP.route("/fork/<username>/<repo>/")
@APP.route("/fork/<namespace>.<username>/<repo>/")
@APP.route("/fork/<username>/<repo>/<path:filename>")
@APP.route("/fork/<namespace>.<username>/<repo>/<path:filename>")
def view_docs(repo, username=None, namespace=None, filename=None):
    """ Display the documentation
    """
    if "." in repo:
        namespace, repo = repo.split(".", 1)

    repo = pagure.lib.query.get_authorized_project(
        SESSION, repo, user=username, namespace=namespace
    )

    if not repo:
        flask.abort(404, description="Project not found")

    if not repo.settings.get("project_documentation", True):
        flask.abort(404, description="This project has documentation disabled")

    reponame = repo.repopath("docs")
    if not os.path.exists(reponame):
        flask.abort(404, description="Documentation not found")

    repo_obj = pygit2.Repository(reponame)

    if not repo_obj.is_empty:
        commit = repo_obj[repo_obj.head.target]
    else:
        flask.abort(
            404,
            flask.Markup(
                "No content found in the repository, you may want to read "
                'the <a href="'
                'https://docs.pagure.org/pagure/usage/using_doc.html">'
                "Using the doc repository of your project</a> documentation."
            ),
        )

    content = None
    tree = None
    if not filename:
        path = [""]
    else:
        path = [it for it in filename.split("/") if it]

    if commit:
        try:
            (tree, content, filename) = __get_tree_and_content(
                repo_obj, commit, path
            )
        except pagure.exceptions.FileNotFoundException as err:
            flask.flash("%s" % err, "error")
        except Exception as err:
            _log.exception(err)
            flask.abort(
                500, description="Unkown error encountered and reported"
            )

    if not content:
        if not tree or not len(tree):
            flask.abort(404, description="No content found in the repository")
        html = "<li>"
        for el in tree:
            name = el.name
            # Append a trailing '/' to the folders
            if el.filemode == 16384:
                name += "/"
            html += '<ul><a href="{0}">{1}</a></ul>'.format(name, name)
        html += "</li>"
        content = TMPL_HTML.format(content=html)
        mimetype = "text/html"
    else:
        mimetype, _ = pagure.lib.mimetype.guess_type(filename, content)

    return flask.Response(content, mimetype=mimetype)
