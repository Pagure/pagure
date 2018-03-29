# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

from straight.plugin import load

from pagure.lib.model import BASE


def get_plugin_names(blacklist=None):
    ''' Return the list of plugins names. '''
    from pagure.hooks import BaseHook
    plugins = load('pagure.hooks', subclasses=BaseHook)
    if not blacklist:
        blacklist = []
    elif not isinstance(blacklist, list):
        blacklist = [blacklist]

    output = [
        plugin.name
        for plugin in plugins
        if plugin.name not in blacklist
    ]
    # The default hook is not one we show
    if 'default' in output:
        output.remove('default')
    return sorted(output)


def get_plugin_tables():
    ''' Return the list of all plugins. '''
    plugins = load('pagure.hooks', subclasses=BASE)
    return plugins


def get_plugin(plugin_name):
    ''' Return the list of plugins names. '''
    from pagure.hooks import BaseHook
    plugins = load('pagure.hooks', subclasses=BaseHook)
    for plugin in plugins:
        if plugin.name == plugin_name:
            return plugin
