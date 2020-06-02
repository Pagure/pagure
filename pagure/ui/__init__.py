# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import flask

UI_NS = flask.Blueprint("ui_ns", __name__)

# Import the different controllers in the UI namespace/blueprint
import pagure.config  # noqa: E402
import pagure.ui.app  # noqa: E402
from pagure.ui.clone import add_clone_proxy_cmds  # noqa: E402
import pagure.ui.fork  # noqa: E402
import pagure.ui.groups  # noqa: E402

if pagure.config.config.get("ENABLE_TICKETS", True):
    import pagure.ui.issues  # noqa: E402
    import pagure.ui.boards  # noqa: E402
import pagure.ui.plugins  # noqa: E402
import pagure.ui.repo  # noqa: E402

if pagure.config.config["PAGURE_AUTH"] == "local":
    import pagure.ui.login  # noqa: E402


add_clone_proxy_cmds()


@UI_NS.errorhandler(404)
def not_found(error):
    """404 Not Found page"""
    return flask.render_template("not_found.html", error=error), 404


@UI_NS.errorhandler(401)
def unauthorized(error):  # pragma: no cover
    """401 Unauthorized page"""
    return flask.render_template("unauthorized.html", error=error), 401


@UI_NS.route("/api/")
@UI_NS.route("/api")
def api_redirect():
    """ Redirects the user to the API documentation page.

    """
    return flask.redirect(flask.url_for("api_ns.api"))
