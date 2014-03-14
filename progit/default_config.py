#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os


# url to the database server:
DB_URL = 'sqlite:////var/tmp/progit_dev.sqlite'


# The FAS group in which the admin of fedocal are
ADMIN_GROUP = 'progit_admin'

# The email address to which the flask.log will send the errors (tracebacks)
EMAIL_ERROR = 'pingou@pingoured.fr'

# The URL at which the project is available.
APP_URL = 'https://apps.fedoraproject.org/progit/'

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
