#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os

# secret key used to generate unique csrf token
SECRET_KEY = '<insert here your own key>'

# url to the database server:
DB_URL = 'sqlite:////var/tmp/progit_dev.sqlite'

# The FAS group in which the admin of progit are
ADMIN_GROUP = 'progit_admin'

# The email address to which the flask.log will send the errors (tracebacks)
EMAIL_ERROR = 'pingou@pingoured.fr'

# The URL at which the project is available.
APP_URL = 'https://fedorahosted.org/progit/'

# The URL to use to clone the git repositories.
GIT_URL = 'git@progit.fedorahosted.org'

# Number of items displayed per page
ITEM_PER_PAGE = 50

# Folder containing to the git repos
GIT_FOLDER = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    '..',
    'repos'
)

# Folder containing the forks repos
FORK_FOLDER = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    '..',
    'forks'
)

# Folder containing the docs repos
DOCS_FOLDER = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    '..',
    'docs'
)

# Configuration file for gitolite
GITOLITE_CONFIG = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    '..',
    'gitolite.conf'
)

# Home folder of the gitolite user -- Folder where to run gl-compile-conf from
GITOLITE_HOME = None

# Path to the gitolite.rc file
GL_RC = None
# Path to the /bin directory where the gitolite tools can be found
GL_BINDIR = None
