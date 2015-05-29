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
from pagure import APP, SESSION, cla_required, is_repo_admin
from pagure.lib.model import BASE

# pylint: disable=E1101


def get_plugin_names():
    ''' Return the list of plugins names. '''
    plugins = load('pagure.hooks', subclasses=BaseHook)
    output = [plugin.name for plugin in plugins]
    return output


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


@APP.route('/<repo>/settings/<plugin>/', methods=('GET', 'POST'))
@APP.route('/<repo>/settings/<plugin>', methods=('GET', 'POST'))
@APP.route('/<repo>/settings/<plugin>/<int:full>/', methods=('GET', 'POST'))
@APP.route('/<repo>/settings/<plugin>/<int:full>', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/settings/<plugin>/',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/settings/<plugin>',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/settings/<plugin>/<int:full>/',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/settings/<plugin>/<int:full>',
           methods=('GET', 'POST'))
@cla_required
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
        except SQLAlchemyError, err:  # pragma: no cover
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
                fields=fields)

        if form.active.data:
            # Set up the main script if necessary
            plugin.set_up(repo)
            # Install the plugin itself
            plugin.install(repo, dbobj)
            flask.flash('Hook %s activated' % plugin.name)
        else:
            plugin.remove(repo)
            flask.flash('Hook %s inactived' % plugin.name)

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
        fields=fields)
