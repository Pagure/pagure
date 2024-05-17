# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import os  # noqa: E402
import flask  # noqa: E402


def reload_config():
    """ Reload the configuration. """
    config = flask.config.Config(
        os.path.dirname(os.path.abspath(__file__)), flask.Flask.default_config
    )

    config.from_object("pagure.default_config")

    if "PAGURE_CONFIG" in os.environ:
        config.from_envvar("PAGURE_CONFIG")

    # These were previously respected config values, but as explained
    # in https://pagure.io/pagure/issue/2991 they don't really work
    # as expected and their values must be based on GIT_FOLDER.
    # To prevent large changes throughout the codebase, we omitted them
    # from config and we add them here.
    if config["ENABLE_DOCS"]:
        config["DOCS_FOLDER"] = os.path.join(config["GIT_FOLDER"], "docs")
    else:
        config[
            "DOCS_FOLDER"
        ] = None  # Avoid 'KeyError' Exception down the line
    if config["ENABLE_TICKETS"]:
        config["TICKETS_FOLDER"] = os.path.join(
            config["GIT_FOLDER"], "tickets"
        )
    config["REQUESTS_FOLDER"] = os.path.join(config["GIT_FOLDER"], "requests")

    if "GITOLITE_BACKEND" in config:
        # This is for backwards compatibility purposes
        config["GIT_AUTH_BACKEND"] = config["GITOLITE_BACKEND"]

    return config


config = reload_config()
