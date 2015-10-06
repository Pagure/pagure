#!/usr/bin/env python

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources

import argparse
import sys
import os

from pagure import APP
APP.debug = True

parser = argparse.ArgumentParser(
    description='Run the packages2 app')
parser.add_argument(
    '--config', '-c', dest='config',
    help='Configuration file to use for packages.')
parser.add_argument(
    '--debug', dest='debug', action='store_true',
    default=False,
    help='Expand the level of data returned.')
parser.add_argument(
    '--profile', dest='profile', action='store_true',
    default=False,
    help='Profile the packages2 application.')
parser.add_argument(
    '--port', '-p', default=5000,
    help='Port for the flask application.')

args = parser.parse_args()

if args.profile:
    from werkzeug.contrib.profiler import ProfilerMiddleware
    APP.config['PROFILE'] = True
    APP.wsgi_app = ProfilerMiddleware(APP.wsgi_app, restrictions=[30])

if args.config:
    os.environ['PKGS_CONFIG'] = args.config

APP.run(port=int(args.port))
