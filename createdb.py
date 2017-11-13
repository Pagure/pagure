#!/usr/bin/env python2

from __future__ import print_function

# These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources  # noqa

import argparse
import sys
import os


parser = argparse.ArgumentParser(
    description='Create/Update the Pagure database')
parser.add_argument(
    '--config', '-c', dest='config',
    help='Configuration file to use for pagure.')
parser.add_argument(
    '--initial', '-i', dest='alembic_cfg',
    help='With this option, the database will be automatically stamped to '
         'the latest version according to alembic. Point to the alembic.ini '
         'file to use.')


args = parser.parse_args()

if args.config:
    config = args.config
    if not config.startswith('/'):
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        config = os.path.join(here, config)
    os.environ['PAGURE_CONFIG'] = config


if args.alembic_cfg:
    if not args.alembic_cfg.endswith('alembic.ini'):
        print('--initial should point to the alembic.ini file to use.')
        sys.exit(1)
    if not os.path.exists(args.alembic_cfg):
        print('The file `{0}` could not be found'.format(args.alembic_cfg))
        sys.exit(2)


import pagure
from pagure.lib import model

model.create_tables(
    pagure.config.config['DB_URL'],
    pagure.config.config.get('PATH_ALEMBIC_INI', args.alembic_cfg),
    acls=pagure.config.config.get('ACLS', {}),
    debug=True)
