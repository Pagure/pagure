#!/usr/bin/python

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources

from progit import APP
from progit import model

model.create_tables(
    APP.config['DB_URL'],
    APP.config.get('PATH_ALEMBIC_INI', None),
    debug=True)
