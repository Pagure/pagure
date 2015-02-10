#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os
from datetime import timedelta


# Set the time after which the session expires
PERMANENT_SESSION_LIFETIME = timedelta(hours=1)

# secret key used to generate unique csrf token
SECRET_KEY = '<insert here your own key>'

# url to the database server:
DB_URL = 'sqlite:////var/tmp/progit_dev.sqlite'

# The FAS group in which the admin of progit are
ADMIN_GROUP = 'sysadmin-main'

# The email address to which the flask.log will send the errors (tracebacks)
EMAIL_ERROR = 'pingou@pingoured.fr'

# The URL at which the project is available.
APP_URL = 'https://fedorahosted.org/progit/'

# The URL to use to clone the git repositories.
GIT_URL_SSH = 'git@progit.fedorahosted.org'
GIT_URL_GIT = 'git://progit.fedorahosted.org'


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

# Folder containing the tickets repos
TICKETS_FOLDER = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    '..',
    'tickets'
)

# Configuration file for gitolite
GITOLITE_CONFIG = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    '..',
    'gitolite.conf'
)

# Home folder of the gitolite user -- Folder where to run gl-compile-conf from
GITOLITE_HOME = None

# Folder containing all the public ssh keys for gitolite
GITOLITE_KEYDIR = None

# Path to the gitolite.rc file
GL_RC = None
# Path to the /bin directory where the gitolite tools can be found
GL_BINDIR = None


# Default SMTP server to use for sending emails
SMTP_SERVER = 'localhost'

# Email used to sent emails
FROM_EMAIL = 'progit@fedoraproject.org'

# Specify which authentication method to use, defaults to `fas` can be or
# `local`
# Default: ``fas``.
PROGIT_AUTH = 'fas'

# When this is set to True, the session cookie will only be returned to the
# server via ssl (https). If you connect to the server via plain http, the
# cookie will not be sent. This prevents sniffing of the cookie contents.
# This may be set to False when testing your application but should always
# be set to True in production.
# Default: ``True``.
PROGIT_COOKIE_REQUIRES_HTTPS = False

# The name of the cookie used to store the session id.
# Default: ``.MirrorManager``.
PROGIT_COOKIE_NAME = 'progit'

# If not specified the application will rely on the root_url when sending
# emails, otherwise it will use this URL
# Default: ``None``.
APPLICATION_URL = None

# Boolean specifying wether to check the user's IP address when retrieving
# its session. This make things more secure (thus is on by default) but
# under certain setup it might not work (for example is there are proxies
# in front of the application).
CHECK_SESSION_IP = True

# Lenght for short commits ids or file hex
SHORT_LENGTH = 6

# Make browsers send session cookie only via HTTPS
SESSION_COOKIE_SECURE = True
