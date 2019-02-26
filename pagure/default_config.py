# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import os
from datetime import timedelta

from pagure.mail_logging import ContextInjector, MSG_FORMAT


# Set the time after which the admin session expires
ADMIN_SESSION_LIFETIME = timedelta(minutes=20)

# secret key used to generate unique csrf token
SECRET_KEY = str("<insert here your own key>")

# url to the database server:
DB_URL = "sqlite:////var/tmp/pagure_dev.sqlite"

# Name the instance, used in the welcome screen upon first login (not
# working with `local` auth)
INSTANCE_NAME = "Pagure"

# Provide an email to contact an instance Administrator
ADMIN_EMAIL = "root@localhost.localdomain"

# url to datagrepper (optional):
# DATAGREPPER_URL = 'https://apps.fedoraproject.org/datagrepper'
# DATAGREPPER_CATEGORY = 'pagure'

# Send FedMsg notifications of events in pagure
FEDMSG_NOTIFICATIONS = False

# The FAS group in which the admin of pagure are
ADMIN_GROUP = "sysadmin-main"

# Hard-code a list of users that are global admins
PAGURE_ADMIN_USERS = []

# Whether or not to send emails
EMAIL_SEND = False

# The email address to which the flask.log will send the errors (tracebacks)
EMAIL_ERROR = "root@localhost.localdomain"

# The URL at which the project is available.
APP_URL = "http://localhost.localdomain/"

# Enables / Disables tickets for project for the entire pagure instance
ENABLE_TICKETS = True

# Enables / Disables docs for project for the entire pagure instance
ENABLE_DOCS = True

# Enables / Disables creating projects on this pagure instance
ENABLE_NEW_PROJECTS = True

# Enables / Disables deleting projects on this pagure instance
ENABLE_DEL_PROJECTS = True

# Enables / Disables giving projects on this pagure instance
ENABLE_GIVE_PROJECTS = True

# Enables / Disables managing access to the repos
ENABLE_USER_MNGT = True

# Enables / Disables managing groups via the UI
ENABLE_GROUP_MNGT = True

# Enables / Disables private projects
PRIVATE_PROJECTS = True

# Enable / Disable deleting branches in the UI
ALLOW_DELETE_BRANCH = True

# Allow admins to ignore existing repos when creating a new project
ALLOW_ADMIN_IGNORE_EXISTING_REPOS = False

# List of users that can ignore existing repos when creating a new project
USERS_IGNORE_EXISTING_REPOS = []

# Enable / Disable having pagure manage the user's ssh keys
LOCAL_SSH_KEY = True

# Enable / Disable deploy keys
DEPLOY_KEY = True

# Set to True if default target branch for all PRs in UI
# should be the branch that is longest substring of the branch
# that the PR is to be created from
PR_TARGET_MATCHING_BRANCH = False

# Enables / Disables showing all the projects by default on the front page
SHOW_PROJECTS_INDEX = ["repos", "myrepos", "myforks"]

# The URL to use to clone the git repositories.
GIT_URL_SSH = "ssh://git@localhost.localdomain/"
GIT_URL_GIT = "git://localhost.localdomain/"

# Set to True if git ssh URLs should be displayed even if user
# doesn't have SSH key uploaded
ALWAYS_RENDER_SSH_CLONE_URL = False

# Default queue names for the different services
WEBHOOK_CELERY_QUEUE = "pagure_webhook"
LOGCOM_CELERY_QUEUE = "pagure_logcom"
LOADJSON_CELERY_QUEUE = "pagure_loadjson"
CI_CELERY_QUEUE = "pagure_ci"
MIRRORING_QUEUE = "pagure_mirror"

# Number of items displayed per page
ITEM_PER_PAGE = 48

# Maximum size of the uploaded content
MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 megabytes

# IP addresses allowed to access the internal endpoints
IP_ALLOWED_INTERNAL = ["127.0.0.1", "localhost", "::1"]

# Worker configuration
CELERY_CONFIG = {}

# Redis configuration
EVENTSOURCE_SOURCE = None
WEBHOOK = False
REDIS_HOST = "0.0.0.0"
REDIS_PORT = 6379
REDIS_DB = 0
EVENTSOURCE_PORT = 8080

# Disallow remote pull requests
DISABLE_REMOTE_PR = False

# Folder where to place the ssh keys for the mirroring feature
MIRROR_SSHKEYS_FOLDER = "/var/lib/pagure/sshkeys/"

# Folder containing to the git repos
# Note that this must be exactly the same as GL_REPO_BASE in gitolite.rc
GIT_FOLDER = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "..", "lcl", "repos"
)

# Folder containing the clones for the remote pull-requests
REMOTE_GIT_FOLDER = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "..", "lcl", "remotes"
)

# Folder containing attachments
ATTACHMENTS_FOLDER = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "..", "lcl", "attachments"
)

# Folder for repoSpanner pseudo repos
REPOSPANNER_PSEUDO_FOLDER = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "..", "lcl", "pseudo"
)

# Whether to enable scanning for viruses in attachments
VIRUS_SCAN_ATTACHMENTS = False

# Configuration file for gitolite
GITOLITE_CONFIG = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "..", "lcl", "gitolite.conf"
)

# Configuration keys to specify where the upload folder is and what is its
# name
UPLOAD_FOLDER_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "..", "lcl", "releases"
)


# Home folder of the gitolite user -- Folder where to run gl-compile-conf from
GITOLITE_HOME = None

# Version of gitolite used: 2 or 3?
GITOLITE_VERSION = 3

# Folder containing all the public ssh keys for gitolite
GITOLITE_KEYDIR = None

# Backend for git auth decisions
# This may be either a static helper (like gitolite based) or dynamic.
GIT_AUTH_BACKEND = "gitolite3"

# Legacy option name for GIT_AUTH_BACKEND, retained for backwards compatibility
# This option overrides GIT_AUTH_BACKEND
# GITOLITE_BACKEND = "gitolite3"

# Whether or not this installation of Pagure should use `gitolite compile-1`
# to improve speed of some gitolite operations. See documentation for more
# info about how to set this up.
GITOLITE_HAS_COMPILE_1 = False

# Path to the gitolite.rc file
GL_RC = None
# Path to the /bin directory where the gitolite tools can be found
GL_BINDIR = None


# Whether or not to run "git gc --auto" after every change to a project
# This will only run for projects not on repospanner and will use
# default git config values
# See https://git-scm.com/docs/git-gc#git-gc---auto for more details
GIT_GARBAGE_COLLECT = False


# SMTP settings
SMTP_SERVER = "localhost"
SMTP_PORT = 25
SMTP_SSL = False

# Specify both for enabling SMTP auth
SMTP_USERNAME = None
SMTP_PASSWORD = None


# Email used to sent emails
FROM_EMAIL = "pagure@localhost.localdomain"

DOMAIN_EMAIL_NOTIFICATIONS = "localhost.localdomain"
SALT_EMAIL = "<secret key to be changed>"

# Specify which authentication method to use.
# Refer to
# https://docs.pagure.org/pagure/configuration.html?highlight=authentication#pagure-auth
# for information regarding authentication providers.

# Available options: `fas`, `openid`, `oidc`, `local`
# Default: ``local``.
PAGURE_AUTH = "local"

# If PAGURE_AUTH is set to 'oidc', the following variables must be set:
# The path to JSON file with client secrets (provided by your IdP)
# OIDC_CLIENT_SECRETS = 'client_secrets.json'
# When this is set to True, the cookie with OpenID Connect Token will only
# be returned to the server via ssl (https). If you connect to the server
# via plain http, the cookie will not be sent. This prevents sniffing
# of the cookie contents. This may be set to False when testing your
# application but should always be set to True in production.
# OIDC_ID_TOKEN_COOKIE_SECURE = False
# OIDC_SCOPES = ['openid', 'email', 'profile']
# These specify names of expected keys provided as userinfo by IdP.
# They may vary across different IdPs
# OIDC_PAGURE_EMAIL = 'email'
# OIDC_PAGURE_FULLNAME = 'name'
# OIDC_PAGURE_USERNAME = 'preferred_username'
# OIDC_PAGURE_SSH_KEY = 'ssh_key'
# OIDC_PAGURE_GROUPS = 'groups'
# This specifies fallback for getting username assuming OIDC_PAGURE_USERNAME
# is empty - can be `email` (to use the part before `@`) or `sub`
# (IdP-specific user id, can be a nickname, email or a numeric ID
#  depending on IdP).
# OIDC_PAGURE_USERNAME_FALLBACK = 'email'
#
# More settings for OIDC are available from flask-oidc at:
# http://flask-oidc.readthedocs.io/en/latest/#settings-reference

# When this is set to True, the session cookie will only be returned to the
# server via ssl (https). If you connect to the server via plain http, the
# cookie will not be sent. This prevents sniffing of the cookie contents.
# This may be set to False when testing your application but should always
# be set to True in production.
# Default: ``True``.
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_NAME = "pagure"

# Boolean specifying whether to check the user's IP address when retrieving
# its session. This make things more secure (thus is on by default) but
# under certain setup it might not work (for example is there are proxies
# in front of the application).
CHECK_SESSION_IP = True

# Lenght for short commits ids or file hex
SHORT_LENGTH = 6

# Used by SESSION_COOKIE_PATH
APPLICATION_ROOT = "/"

# List of blacklisted project names
BLACKLISTED_PROJECTS = [
    "static",
    "pv",
    "releases",
    "new",
    "api",
    "settings",
    "search",
    "fork",
    "logout",
    "login",
    "user",
    "users",
    "groups",
    "projects",
    "ssh_info",
    "issues",
    "pull-requests",
    "commits",
    "tree",
    "forks",
    "admin",
    "c",
    "wait",
    "dashboard",
    "docs/*, tickets/*, requests/*",
]

# List of prefix allowed in project names
ALLOWED_PREFIX = []

# List of blacklisted group names
BLACKLISTED_GROUPS = ["forks", "group"]


ACLS = {
    "create_branch": "Create a git branch on a project",
    "create_project": "Create a new project",
    "commit_flag": "Flag a commit",
    "fork_project": "Fork a project",
    "generate_acls_project": "Generate the Gitolite ACLs on a project",
    "internal_access": "Access Pagure's internal APIs",
    "issue_assign": "Assign issue to someone",
    "issue_change_status": "Change the status of a ticket",
    "issue_comment": "Comment on a ticket",
    "issue_create": "Create a new ticket",
    "issue_subscribe": "Subscribe the user with this token to an issue",
    "issue_update": "Update an issue, status, comments, custom fields...",
    "issue_update_custom_fields": "Update the custom fields of an issue",
    "issue_update_milestone": "Update the milestone of an issue",
    "modify_project": "Modify an existing project",
    "pull_request_create": "Open a new pull-request",
    "pull_request_close": "Close a pull-request",
    "pull_request_comment": "Comment on a pull-request",
    "pull_request_flag": "Flag a pull-request",
    "pull_request_merge": "Merge a pull-request",
    "pull_request_subscribe": (
        "Subscribe the user with this token to a pull-request"
    ),
    "pull_request_assign": "Assign someone to a pull-request",
    "pull_request_update": (
        "Update a pull-request (title, description, assignee...)"
    ),
    "update_watch_status": "Update the watch status on a project",
    "pull_request_rebase": "Rebase a pull-request",
}

# List of ACLs which a regular user is allowed to associate to an API token
# from the ACLs above
USER_ACLS = [
    key
    for key in ACLS.keys()
    if key not in ["generate_acls_project", "internal_access"]
]

# From the ACLs above lists which ones are tolerated to be associated with
# an API token that isn't linked to a particular project.
CROSS_PROJECT_ACLS = [
    "create_project",
    "fork_project",
    "modify_project",
    "update_watch_status",
]

# ACLs with which admins are allowed to create project-less API tokens
ADMIN_API_ACLS = [
    "internal_access",
    "issue_comment",
    "issue_create",
    "issue_change_status",
    "pull_request_flag",
    "pull_request_comment",
    "pull_request_merge",
    "generate_acls_project",
    "commit_flag",
    "create_branch",
]

# List of the type of CI service supported by this pagure instance
PAGURE_CI_SERVICES = []

# Boolean to turn on project being by default in the user's namespace
USER_NAMESPACE = False

# List of groups whose projects should not be shown on the user's info page
# unless the user has direct access to it.
EXCLUDE_GROUP_INDEX = []

TRIGGER_CI = {
    "pretty please pagure-ci rebuild": {
        "name": "Default CI",
        "description": "Rerun default CI",
        "requires_project_hook_attr": ("ci_hook", "active_pr", True),
    }
}

FLAG_STATUSES_LABELS = {
    "success": "badge-success",
    "failure": "badge-danger",
    "error": "badge-danger",
    "pending": "badge-info",
    "canceled": "badge-warning",
}
FLAG_SUCCESS = "success"
FLAG_FAILURE = "failure"
FLAG_PENDING = "pending"

# Never enable this option, this is intended for tests only, and can allow
# easy denial of service to the system if enabled.
ALLOW_PROJECT_DOWAIT = False

# Settings for MQTT message sending
MQTT_NOTIFICATIONS = False
MQTT_HOST = None
MQTT_PORT = None
MQTT_USERNAME = None
MQTT_PASSWORD = None
MQTT_CA_CERTS = None
MQTT_CERTFILE = None
MQTT_KEYFILE = None
MQTT_CIPHERS = None

# Settings for Stomp message sending
STOMP_NOTIFICATIONS = False
STOMP_BROKERS = []
STOMP_SSL = False
STOMP_KEY_FILE = None
STOMP_CERT_FILE = None
STOMP_CREDS_PASSWORD = None
STOMP_HIERARCHY = None

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "email_format": {"format": MSG_FORMAT},
    },
    "filters": {"myfilter": {"()": ContextInjector}},
    "handlers": {
        "console": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "email": {
            "level": "ERROR",
            "formatter": "email_format",
            "class": "logging.handlers.SMTPHandler",
            "mailhost": "localhost",
            "fromaddr": "pagure@localhost",
            "toaddrs": "root@localhost",
            "subject": "ERROR on pagure",
            "filters": ["myfilter"],
        },
    },
    # The root logger configuration; this is a catch-all configuration
    # that applies to all log messages not handled by a different logger
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "pagure": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        },
        "flask": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "sqlalchemy": {
            "handlers": ["console"],
            "level": "WARN",
            "propagate": False,
        },
        "binaryornot": {
            "handlers": ["console"],
            "level": "WARN",
            "propagate": True,
        },
        "MARKDOWN": {
            "handlers": ["console"],
            "level": "WARN",
            "propagate": True,
        },
        "PIL": {"handlers": ["console"], "level": "WARN", "propagate": True},
        "chardet": {
            "handlers": ["console"],
            "level": "WARN",
            "propagate": True,
        },
        "pagure.lib.encoding_utils": {
            "handlers": ["console"],
            "level": "WARN",
            "propagate": False,
        },
    },
}

# Gives commit access to all, all but some or just some project based on
# groups provided by the auth system.
EXTERNAL_COMMITTER = {}

# Allows to require that the users are members of a certain group to be added
# to a project (not a fork).
REQUIRED_GROUPS = {}

# Predefined reactions. Selecting others is possible by typing their name. The
# order here will be preserved in the web UI picker for reactions.
REACTIONS = [
    ("Thumbs up", "emojione-1F44D"),  # Thumbs up
    ("Thumbs down", "emojione-1F44E"),  # Thumbs down
    ("Confused", "emojione-1F615"),  # Confused
    ("Heart", "emojione-2764"),  # Heart
]
# This is used for faster indexing. Do not change.
_REACTIONS_DICT = dict(REACTIONS)

# HTTP pull/push options
# Whether to allow Git HTTP proxying
ALLOW_HTTP_PULL_PUSH = True
# Whether to allow pushing via HTTP
ALLOW_HTTP_PUSH = False
# Path to Gitolite-shell if using that, None to use Git directly
HTTP_REPO_ACCESS_GITOLITE = "/usr/share/gitolite3/gitolite-shell"

# repoSpanner integration settings
# Path the the repoBridge binary
REPOBRIDGE_BINARY = "/usr/libexec/repobridge"
# Whether to create new repositories on repoSpanner by default.
# Either None or a region name.
REPOSPANNER_NEW_REPO = None
# Whether to allow admins to override region selection on creation.
REPOSPANNER_NEW_REPO_ADMIN_OVERRIDE = False
# Whether to create new forks on repoSpanner.
# Either None (no repoSpanner), True (same as origin project) or a region name.
REPOSPANNER_NEW_FORK = True
# Whether to allow an admin to manually migrate an individual project.
REPOSPANNER_ADMIN_MIGRATION = False
# The repoSpanner regions to be used in this Pagure instance.
# Example entry:
# 'default': {'url': 'https://nodea.regiona.repospanner.local:8444',
#             'repo_prefix': 'pagure/',
#             'hook': None,
#             'ca': '',
#             'admin_cert': {'cert': '',
#                            'key': ''},
#             'push_cert': {'cert': '',
#                           'key': ''}}
REPOSPANNER_REGIONS = {}

# Configuration for the key helper
# Look a username up in the database, overrides SSH_KEYS_USERNAME_EXPECT
SSH_KEYS_USERNAME_LOOKUP = False
# Except certain usernames from being used via the keyhelper
SSH_KEYS_USERNAME_FORBIDDEN = ["root"]
# Username to expect for ssh. Set to None to disallow any access
SSH_KEYS_USERNAME_EXPECT = None
# Arguments to add to the SSH keys, possible replacements:
# %(username)s: username owning this key
SSH_KEYS_OPTIONS = (
    'restrict,command="/usr/libexec/pagure/aclchecker.py %(username)s"'
)
# If not set to None, aclchecker and keyhelper will use this api admin
# token to get authorized to internal endpoints that they use. The token
# must have the internal_access ACL.
SSH_ADMIN_TOKEN = None

# ACL Checker options
SSH_COMMAND_REPOSPANNER = (
    [
        "/usr/libexec/repobridge",
        "--extra",
        "username",
        "%(username)s",
        "--extra",
        "repotype",
        "%(repotype)s",
        "--extra",
        "project_name",
        "%(project_name)s",
        "--extra",
        "project_user",
        "%(project_user)s",
        "--extra",
        "project_namespace",
        "%(project_namespace)s",
        "%(cmd)s",
        "'%(repospanner_reponame)s'",
    ],
    {"REPOBRIDGE_CONFIG": "/etc/repospanner/bridge_%(region)s.json"},
)
SSH_COMMAND_NON_REPOSPANNER = (
    [
        "/usr/share/gitolite3/gitolite-shell",
        "%(username)s",
        "%(cmd)s",
        "%(reponame)s",
    ],
    {},
)
