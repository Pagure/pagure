# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import absolute_import, unicode_literals

import gc
from functools import wraps

import pagure.lib.model_base
from pagure.config import config as pagure_config


def pagure_task(function):
    """Simple decorator that is responsible for:
    * Adjusting the status of the task when it starts
    * Creating and cleaning up a SQLAlchemy session
    """

    @wraps(function)
    def decorated_function(self, *args, **kwargs):
        """Decorated function, actually does the work."""
        if self is not None:
            try:
                self.update_state(state="RUNNING")
            except TypeError:
                pass
        session = pagure.lib.model_base.create_session(pagure_config["DB_URL"])
        try:
            return function(self, session, *args, **kwargs)
        except:  # noqa: E722
            # if the task has raised for any reason, we need to rollback the
            # session first to not leave open uncomitted transaction hanging
            session.rollback()
            raise
        finally:
            session.remove()
            gc_clean()

    return decorated_function


def gc_clean():
    """Force a run of the garbage collector."""
    # https://pagure.io/pagure/issue/2302
    gc.collect()
