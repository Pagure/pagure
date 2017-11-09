#-*- coding: utf-8 -*-

# The three lines below are required to run on EL6 as EL6 has
# two possible version of python-sqlalchemy and python-jinja2
# These lines make sure the application uses the correct version.
import __main__
__main__.__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources

# Set the environment variable pointing to the configuration file
import os
os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'

# Set the environment variable if the tmp folder needs to be moved
# Might be necessary to work around bug in libgit2:
# refs: https://github.com/libgit2/libgit2/issues/2965
# and   https://github.com/libgit2/libgit2/issues/2797
os.environ['TEMP'] = '/var/tmp/'

# The following is only needed if you did not install pagure
# as a python module (for example if you run it from a git clone).
#import sys
#sys.path.insert(0, '/path/to/pagure/')


# The most important line to make the wsgi working
from pagure import APP as application
#application.debug = True
