#!/usr/bin/env python2

# These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources

import sys
from werkzeug.contrib.profiler import ProfilerMiddleware

from pagure import APP
APP.debug = True

if '--profile' in sys.argv:
    APP.config['PROFILE'] = True
    APP.wsgi_app = ProfilerMiddleware(APP.wsgi_app, restrictions=[30])

APP.run(threaded=True)
