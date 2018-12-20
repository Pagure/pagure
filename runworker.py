#!/usr/bin/env python

from __future__ import unicode_literals, absolute_import

# These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources

import argparse
import sys
import os
import subprocess


parser = argparse.ArgumentParser(
    description='Run the Pagure worker')
parser.add_argument(
    '--config', '-c', dest='config',
    help='Configuration file to use for pagure.')
parser.add_argument(
    '--debug', dest='debug', action='store_true',
    default=False,
    help='Expand the level of data returned.')
parser.add_argument(
    '--noinfo', dest='noinfo', action='store_true',
    default=False,
    help='Reduce the log level.')

args = parser.parse_args()

env = {}
if args.config:
    config = args.config
    if not config.startswith('/'):
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        config = os.path.join(here, config)
    env['PAGURE_CONFIG'] = config

cmd = [
    sys.executable, '-m', 'celery', 'worker', '-A', 'pagure.lib.tasks'
]

if args.debug:
    cmd.append('--loglevel=debug')
elif args.noinfo:
    pass
else:
    cmd.append('--loglevel=info')

subp = subprocess.Popen(cmd, env=env or None)
subp.wait()
