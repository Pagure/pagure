# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask

from sqlalchemy.exc import SQLAlchemyError
from straight.plugin import load
from pagure.hooks import BaseHook

import pagure.exceptions
import pagure.lib
import pagure.forms
from pagure import APP, SESSION, login_required, is_repo_admin
from pagure.lib.model import BASE
from pagure.exceptions import FileNotFoundException
from pagure.hooks import jenkins_hook
from pagure.lib import model

try:
    from pagure.lib import pagure_ci
except ImportError:
    pagure_ci = None

import json
from kitchen.text.converters import to_bytes
from cryptography.hazmat.primitives import constant_time

# pylint: disable=E1101


def get_plugin_names(blacklist=None):
    ''' Return the list of plugins names. '''
    plugins = load('pagure.hooks', subclasses=BaseHook)
    if not blacklist:
        blacklist = []
    elif not isinstance(blacklist, list):
        blacklist = [blacklist]

    if pagure_ci is None and 'Pagure CI' not in blacklist:
        blacklist.append('Pagure CI')

    output = [
        plugin.name
        for plugin in plugins
        if plugin.name not in blacklist
    ]
    return sorted(output)


def get_plugin_tables():
    ''' Return the list of all plugins. '''
    plugins = load('pagure.hooks', subclasses=BASE)
    return plugins


def get_plugin(plugin_name):
    ''' Return the list of plugins names. '''
    plugins = load('pagure.hooks', subclasses=BaseHook)
    for plugin in plugins:
        if plugin.name == plugin_name:
            return plugin


@APP.route('/<repo:repo>/settings/<plugin>/', methods=('GET', 'POST'))
@APP.route('/<repo:repo>/settings/<plugin>', methods=('GET', 'POST'))
@APP.route('/<repo:repo>/settings/<plugin>/<int:full>/', methods=('GET', 'POST'))
@APP.route('/<repo:repo>/settings/<plugin>/<int:full>', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/settings/<plugin>/',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/settings/<plugin>',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/settings/<plugin>/<int:full>/',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/settings/<plugin>/<int:full>',
           methods=('GET', 'POST'))
@login_required
def view_plugin(repo, plugin, username=None, full=True):
    """ Presents the settings of the project.
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    if plugin in APP.config.get('DISABLED_PLUGINS', []):
        flask.abort(404, 'Plugin disabled')

    plugin = get_plugin(plugin)
    fields = []
    new = True
    dbobj = plugin.db_object()
    pagure_ci_token = None

    if hasattr(repo, plugin.backref):
        dbobj = getattr(repo, plugin.backref)

        # There should always be only one, but let's double check
        if dbobj and len(dbobj) > 0:
            dbobj = dbobj[0]
            new = False
            # To populate the pagure CI token if generated
            if hasattr(dbobj, "pagure_ci_token") and plugin.backref == "hook_pagure_ci":
                pagure_ci_token = dbobj.pagure_ci_token
        else:
            dbobj = plugin.db_object()

    form = plugin.form(obj=dbobj)
    for field in plugin.form_fields:
        fields.append(getattr(form, field))

    if form.validate_on_submit():
        form.populate_obj(obj=dbobj)

        if new:
            dbobj.project_id = repo.id
            SESSION.add(dbobj)
        try:
            SESSION.flush()
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.debug('Could not add plugin %s', plugin.name)
            APP.logger.exception(err)
            flask.flash(
                'Could not add plugin %s, please contact an admin'
                % plugin.name)

            return flask.render_template(
                'plugin.html',
                select='settings',
                full=full,
                repo=repo,
                username=username,
                plugin=plugin,
                form=form,
                pagure_ci_token=pagure_ci_token,
                fields=fields)

        if form.active.data:
            # Set up the main script if necessary
            plugin.set_up(repo)
            # Install the plugin itself
            try:
                plugin.install(repo, dbobj)
                flask.flash('Hook %s activated' % plugin.name)
            except FileNotFoundException as err:
                pagure.APP.logger.exception(err)
                flask.abort(404, 'No git repo found')
        else:
            try:
                plugin.remove(repo)
                flask.flash('Hook %s inactived' % plugin.name)
            except FileNotFoundException as err:
                pagure.APP.logger.exception(err)
                flask.abort(404, 'No git repo found')

        SESSION.commit()

        return flask.redirect(flask.url_for(
            'view_settings', repo=repo.name, username=username))

    return flask.render_template(
        'plugin.html',
        select='settings',
        full=full,
        repo=repo,
        username=username,
        plugin=plugin,
        form=form,
        pagure_ci_token=pagure_ci_token,
        fields=fields)

if pagure_ci is not None:
    @APP.route('/hooks/<pagure_ci_token>/build-finished', methods=['POST'])
    def hook_finished(pagure_ci_token):
        """ Flags the Pull-request after getting notification from Jenkins
        """

        try:
            data = json.loads(flask.request.get_data())
            cfg = jenkins_hook.get_configs(
                data['name'], jenkins_hook.Service.JENKINS)[0]
            build_id = data['build']['number']

            if not constant_time.bytes_eq(
                      to_bytes(pagure_ci_token), to_bytes(cfg.pagure_ci_token)):
                return ('Token mismatch', 401)

        except (TypeError, ValueError, KeyError, jenkins_hook.ConfigNotFound) as exc:
            APP.logger.error('Error processing jenkins notification', exc_info=exc)
            flask.abort(400, "Bad Request")

        APP.logger.info('Received jenkins notification')
        pagure_ci.process_build(APP.logger, cfg, build_id)
        return ('', 204)
