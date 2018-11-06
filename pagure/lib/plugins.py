# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

from straight.plugin import load

from pagure.lib.model_base import BASE


def get_plugin_names(blacklist=None, without_backref=False):
    """ Return the list of plugins names.

    :arg blacklist: name or list of names to not return
    :type blacklist: string or list of strings
    :arg without_backref: whether or not to include hooks that
        have backref "None"
    :type without_backref: bool
    :return: list of plugin names (strings)
    """
    from pagure.hooks import BaseHook

    plugins = load("pagure.hooks", subclasses=BaseHook)
    if not blacklist:
        blacklist = []
    elif not isinstance(blacklist, list):
        blacklist = [blacklist]

    output = [
        plugin.name
        for plugin in plugins
        if plugin.name not in blacklist and (plugin.backref or without_backref)
    ]
    # The default hook is not one we show
    if "default" in output:
        output.remove("default")
    return sorted(output)


def get_plugin_tables():
    """ Return the list of all plugins. """
    plugins = load("pagure.hooks", subclasses=BASE)
    return plugins


def get_plugin(plugin_name):
    """ Return the list of plugins names. """
    from pagure.hooks import BaseHook

    plugins = load("pagure.hooks", subclasses=BaseHook)
    for plugin in plugins:
        if plugin.name == plugin_name:
            return plugin


def get_enabled_plugins(project):
    """ Returns a list of plugins enabled for a specific project.

    Args:
        project (model.Project): The project to look for.
    Returns: (list): A  list of tuples (pluginclass, dbobj) with the plugin
        classess and dbobjects for plugins enabled for the project.
    """
    from pagure.hooks import BaseHook

    enabled = []
    for plugin in load("pagure.hooks", subclasses=BaseHook):
        if plugin.backref is None:
            if plugin.is_enabled_for(project):
                enabled.append((plugin, None))
        else:
            plugin.db_object()
            if hasattr(project, plugin.backref):
                dbobj = getattr(project, plugin.backref)
                if dbobj and dbobj.active:
                    enabled.append((plugin, dbobj))
    return enabled
