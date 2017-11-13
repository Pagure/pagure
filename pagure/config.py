# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os  # noqa: E402
import flask  # noqa: E402


def reload_config():
    """ Reload the configuration. """
    config = flask.config.Config(
        os.path.dirname(os.path.abspath(__file__)),
        flask.Flask.default_config
    )

    config.from_object('pagure.default_config')

    if 'PAGURE_CONFIG' in os.environ:
        config.from_envvar('PAGURE_CONFIG')

    return config


config = reload_config()
