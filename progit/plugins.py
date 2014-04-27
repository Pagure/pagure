#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import os
import sys
from math import ceil

import pygit2
from sqlalchemy.exc import SQLAlchemyError
from straight.plugin import load
from hooks import BaseHook

import progit.exceptions
import progit.lib
import progit.forms
from progit import APP, SESSION, LOG, cla_required, is_repo_admin
from progit.model import BASE


def get_plugin_names():
    ''' Return the list of plugins names. '''
    plugins = load('progit.hooks', subclasses=BaseHook)
    output = [plugin.name for plugin in plugins]
    return output


def get_plugin_tables():
    ''' Return the list of all plugins. '''
    plugins = load('progit.hooks', subclasses=BASE)
    return plugins


def get_plugin(plugin_name):
    ''' Return the list of plugins names. '''
    plugins = load('progit.hooks', subclasses=BaseHook)
    for plugin in plugins:
        if plugin.name == plugin_name:
            return plugin


@APP.route('/<repo>/settings/<plugin>', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/settings/<plugin>', methods=('GET', 'POST'))
@cla_required
def view_plugin(repo, plugin, username=None):
    """ Presents the settings of the project.
    """
    return view_plugin_page(repo, plugin, username=username, full=True)


@APP.route(
    '/<repo>/settings/<plugin>/<int:full>', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<repo>/settings/<plugin>/<int:full>',
    methods=('GET', 'POST'))
@cla_required
def view_plugin_page(repo, plugin, full, username=None):
    """ Presents the settings of the project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    plugin = get_plugin(plugin)
    fields = []
    new = True
    dbobj = plugin.db_object()
    if hasattr(repo, plugin.backref):
        dbobj = getattr(repo, plugin.backref)
        # There should always be only one, but let's double check
        if dbobj and len(dbobj) > 0:
            dbobj = dbobj[0]
            new = False
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
        except SQLAlchemyError, err:
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
                fields=fields,
            )

        if form.active.data:
            plugin.install(repo)
            flask.flash('Hook activated')
        else:
            plugin.remove(repo)
            flask.flash('Hook inactived')

        SESSION.commit()

    return flask.render_template(
        'plugin.html',
        select='settings',
        full=full,
        repo=repo,
        username=username,
        plugin=plugin,
        form=form,
        fields=fields,
    )
