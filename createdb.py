#!/usr/bin/env python2

# These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources

from pagure import APP
from pagure.lib import model

model.create_tables(
    APP.config['DB_URL'],
    APP.config.get('PATH_ALEMBIC_INI', None),
    acls=APP.config.get('ACLS', {}),
    debug=True)
