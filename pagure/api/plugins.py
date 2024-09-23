# -*- coding: utf-8 -*-

"""
 (c) 2019 - Copyright Red Hat Inc

 Authors:
   Michal Konecny <mkonecny@redhat.com>

"""

from __future__ import absolute_import, print_function, unicode_literals

import logging

import flask
from sqlalchemy.exc import SQLAlchemyError

import pagure.exceptions
import pagure.lib.plugins as plugins_lib
import pagure.lib.query
from pagure.api import (
    API,
    APIERROR,
    api_login_optional,
    api_login_required,
    api_method,
)
from pagure.api.utils import _check_plugin, _check_token, _get_repo

_log = logging.getLogger(__name__)

# List of ignored form fields, these fields will be not returned in response
IGNORED_FIELDS = ["active"]


def _filter_fields(plugin):
    """
    Filter IGNORED_FIELDS from form and return list of the valid fields.

    :arg plugin: plugin class from which to read fields
    :type plugin: plugin class
    :return: list of valid fields
    """
    fields = []
    for field in plugin.form_fields:
        if field not in IGNORED_FIELDS:
            fields.append(field)

    return fields


@API.route("/<repo>/settings/<plugin>/install", methods=["POST"])
@API.route("/<namespace>/<repo>/settings/<plugin>/install", methods=["POST"])
@API.route(
    "/fork/<username>/<repo>/settings/<plugin>/install", methods=["POST"]
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/settings/<plugin>/install",
    methods=["POST"],
)
@api_login_required(acls=["modify_project"])
@api_method
def api_install_plugin(repo, plugin, username=None, namespace=None):
    """
    Install plugin
    --------------
    Install a plugin to a repository.

    ::

        POST /api/0/<repo>/settings/<plugin>/install
        POST /api/0/<namespace>/<repo>/settings/<plugin>/install

    ::

        POST /api/0/fork/<username>/<repo>/settings/<plugin>/install
        POST /api/0/fork/<username>/<namespace>/<repo>/settings/<plugin>
             /install

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "plugin": {
            "mail_to": "serg@wh40k.com"
          },
          "message": "Hook 'Mail' activated"
        }

    """
    output = {}
    repo = _get_repo(repo, username, namespace)
    _check_token(repo, project_token=False)
    plugin = _check_plugin(repo, plugin)

    fields = []
    new = True
    dbobj = plugin.db_object()

    if hasattr(repo, plugin.backref):
        dbobj = getattr(repo, plugin.backref)

        # There should always be only one, but let's double check
        if dbobj:
            new = False
        else:
            dbobj = plugin.db_object()

    form = plugin.form(obj=dbobj, meta={"csrf": False})
    form.active.data = True
    for field in plugin.form_fields:
        fields.append(getattr(form, field))

    if form.validate_on_submit():
        form.populate_obj(obj=dbobj)

        if new:
            dbobj.project_id = repo.id
            flask.g.session.add(dbobj)
        try:
            flask.g.session.flush()
        except SQLAlchemyError:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception("Could not add plugin %s", plugin.name)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

        try:
            # Set up the main script if necessary
            plugin.set_up(repo)
            # Install the plugin itself
            plugin.install(repo, dbobj)
        except pagure.exceptions.FileNotFoundException as err:
            flask.g.session.rollback()
            _log.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

        try:
            flask.g.session.commit()
            output["message"] = "Hook '%s' activated" % plugin.name
            output["plugin"] = {
                field: form[field].data for field in _filter_fields(plugin)
            }
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors
        )

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/settings/<plugin>/remove", methods=["POST"])
@API.route("/<namespace>/<repo>/settings/<plugin>/remove", methods=["POST"])
@API.route(
    "/fork/<username>/<repo>/settings/<plugin>/remove", methods=["POST"]
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/settings/<plugin>/remove",
    methods=["POST"],
)
@api_login_required(acls=["modify_project"])
@api_method
def api_remove_plugin(repo, plugin, username=None, namespace=None):
    """
    Remove plugin
    --------------
    Remove a plugin from repository.

    ::

        POST /api/0/<repo>/settings/<plugin>/remove
        POST /api/0/<namespace>/<repo>/settings/<plugin>/remove

    ::

        POST /api/0/fork/<username>/<repo>/settings/<plugin>/remove
        POST /api/0/fork/<username>/<namespace>/<repo>/settings/<plugin>
             /remove

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "plugin": {
            "mail_to": "serg@wh40k.com"
          },
          "message": "Hook 'Mail' deactivated"
        }

    """
    output = {}
    repo = _get_repo(repo, username, namespace)
    _check_token(repo, project_token=False)
    plugin = _check_plugin(repo, plugin)

    dbobj = plugin.db_object()

    enabled_plugins = {
        plugin[0]: plugin[1]
        for plugin in plugins_lib.get_enabled_plugins(repo)
    }

    # If the plugin is not installed raise error
    if plugin not in enabled_plugins.keys():
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EPLUGINNOTINSTALLED
        )

    if enabled_plugins[plugin]:
        dbobj = enabled_plugins[plugin]

    form = plugin.form(obj=dbobj)
    form.active.data = False

    try:
        plugin.remove(repo)
    except pagure.exceptions.FileNotFoundException as err:
        flask.g.session.rollback()
        _log.exception(err)
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    try:
        flask.g.session.commit()
        output["message"] = "Hook '%s' deactivated" % plugin.name
        output["plugin"] = {
            field: form[field].data for field in _filter_fields(plugin)
        }
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        _log.exception(err)
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<namespace>/<repo>/settings/plugins")
@API.route("/fork/<username>/<repo>/settings/plugins")
@API.route("/<repo>/settings/plugins")
@API.route("/fork/<username>/<namespace>/<repo>/settings/plugins")
@api_login_optional()
@api_method
def api_view_plugins_project(repo, username=None, namespace=None):
    """
    List project's plugins
    ----------------------
    List installed plugins on a project.

    ::

        GET /api/0/<repo>/settings/plugins
        GET /api/0/<namespace>/<repo>/settings/plugins

    ::

        GET /api/0/fork/<username>/<repo>/settings/plugins
        GET /api/0/fork/<username>/<namespace>/<repo>/settings/plugins

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            'plugins':
            [
                {
                    'Mail':
                    {
                        'mail_to': 'serg@wh40k.com'
                    }
                }
            ],
            'total_plugins': 1
        }

    """
    repo = _get_repo(repo, username, namespace)

    plugins = {
        plugin[0]: plugin[1]
        for plugin in plugins_lib.get_enabled_plugins(repo)
    }
    output = {}

    output["plugins"] = []

    for plugin, dbobj in plugins.items():
        if dbobj:
            form = plugin.form(obj=dbobj)
            fields = _filter_fields(plugin)
            output["plugins"].append(
                {plugin.name: {field: form[field].data for field in fields}}
            )

    output["total_plugins"] = len(output["plugins"])

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/_plugins")
@api_method
def api_view_plugins():
    """
    List plugins
    ------------
    List every plugin available in this pagure instance. For each plugin their
    name is provided as well as the name of the argument
    to provide to enable/disable them.

    ::

        GET /api/0/plugins

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            'plugins': [
                {
                    'Block Un-Signed commits': [
                    ]
                },
                {
                    'Block non fast-forward pushes': [
                        'branches',
                    ]
                },
                {
                    'Fedmsg': [
                    ]
                },
            ],
            'total_issues': 3
        }

    """
    plugins = plugins_lib.get_plugin_names()

    output = {}

    output["total_plugins"] = len(plugins)
    output["plugins"] = []

    for plugin_name in plugins:
        # Skip plugins that are disabled
        if plugin_name in pagure.config.config.get("DISABLED_PLUGINS", []):
            continue
        plugin = plugins_lib.get_plugin(plugin_name)
        fields = _filter_fields(plugin)
        output["plugins"].append({plugin_name: fields})

    jsonout = flask.jsonify(output)
    return jsonout
