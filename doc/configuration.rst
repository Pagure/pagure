Configuration
=============

Pagure offers a wide varieties of options that must or can be used to
adjust its behavior.



Must options
------------

Here are the options you must set up in order to get pagure running.


SECRET_KEY
~~~~~~~~~~

This configuration key is used by flask to create the session. It should be kept secret
and set as a long and random string.


SALT_EMAIL
~~~~~~~~~~

This configuration key is used to ensure that when sending
notifications to different users, each one of them has a different, unique
and unfakeable ``Reply-To`` header. This header is then used by the milter to find
out if the response received is a real one or a fake/invalid one.


DB_URL
~~~~~~

This configuration key indicates to the framework how and where to connect to the database
server. Pagure uses `SQLAchemy <http://www.sqlalchemy.org/>`_ to connect
to a wide range of database server including MySQL, PostgreSQL, and SQLite.

Examples values:

::

    DB_URL = 'mysql://user:pass@host/db_name'
    DB_URL = 'postgres://user:pass@host/db_name'
    DB_URL = 'sqlite:////var/tmp/pagure_dev.sqlite'

Defaults to ``sqlite:////var/tmp/pagure_dev.sqlite``


APP_URL
~~~~~~~

This configuration key indicates the URL at which this pagure instance will be made available.

Defaults to: ``http://localhost.localdomain/``


EMAIL_ERROR
~~~~~~~~~~~

Pagure sends email when it catches an unexpected error (which saves you from
having to monitor the logs regularly; but if you like, the error is still
present in the logs).
This configuration key allows you to specify to which email address to send
these error reports.


GIT_URL_SSH
~~~~~~~~~~~

This configuration key provides the information to the user on how to clone
the git repos hosted on pagure via `SSH <https://en.wikipedia.org/wiki/Secure_Shell>`_.

The URL should end with a slash ``/``.

Defaults to: ``'ssh://git@llocalhost.localdomain/'``

.. note:: If you are using a custom setup for your deployment where every
        user has an account on the machine you may want to tweak this URL
        to include the username. If that is the case, you can use
        ``{username}`` in the URL and it will be expanded to the username
        of the user viewing the page when rendered.
        For example: ``'ssh://{username}@pagure.org/'``


GIT_URL_GIT
~~~~~~~~~~~

This configuration key provides the information to the user on how to clone
the git repos hosted on pagure anonymously. This access can be granted via
the ``git://`` or ``http(s)://`` protocols.

The URL should end with a slash ``/``.

Defaults to: ``'git://localhost.localdomain/'``


BROKER_URL
~~~~~~~~~~

This configuration key is used to point celery to the broker to use. This
is the broker that is used to communicate between the web application and
its workers.

Defaults to: ``'redis://%s' % APP.config['REDIS_HOST']``

.. note:: See the :ref:`redis-section` for the ``REDIS_HOST`` configuration
          key


Repo Directories
----------------

Each project in pagure has 2 to 4 git repositories, depending on configuration
of the Pagure instance (see below):

- the main repo for the code
- the doc repo showed in the doc server (optional)
- the ticket repo storing the metadata of the tickets (optional)
- the request repo storing the metadata of the pull-requests

There are then another 3 folders: one for specifying the locations of the forks, one
for the remote git repo used for the remotes pull-requests (ie: those coming from
a project not hosted on this instance of pagure), and one for user-uploaded tarballs.


GIT_FOLDER
~~~~~~~~~~

This configuration key points to the folder where the git repos are stored.
For every project, two to four repos are created:

* a repo with source code of the project
* a repo with documentation of the project
  (if ``ENABLE_DOCS`` is ``True``)
* a repo with metadata of tickets opened against the project
  (if ``ENABLE_TICKETS`` is ``True``)
* a repo with metadata of pull requests opened against the project

Note that gitolite config value ``GL_REPO_BASE`` (if using gitolite 3)
or ``$REPO_BASE`` (if using gitolite 2) **must** have exactly the same
value as ``GIT_FOLDER``.


REMOTE_GIT_FOLDER
~~~~~~~~~~~~~~~~~

This configuration key points to the folder where the remote git repos (ie:
not hosted on pagure) that someone used to open a pull-request against a
project hosted on pagure are stored.


UPLOAD_FOLDER_PATH
~~~~~~~~~~~~~~~~~~

This configuration key points to the folder where user-uploaded tarballs
are stored and served from.


ATTACHMENTS_FOLDER
~~~~~~~~~~~~~~~~~~

This configuration key points to the folder where attachments can be cached
for easier access by the web-server (allowing to not interact with the git
repo having it to serve it).


UPLOAD_FOLDER_URL
~~~~~~~~~~~~~~~~~~

Full URL to where the uploads are available. It is highly recommended for
security reasons that this URL lives on a different domain than the main
application (an entirely different domain, not just a sub-domain).

Defaults to: ``/releases/``, unsafe for production!


.. warning:: both `UPLOAD_FOLDER_PATH` and `UPLOAD_FOLDER_URL` must be
            specified for the upload release feature to work


SESSION_COOKIE_SECURE
~~~~~~~~~~~~~~~~~~~~~

When this is set to True, the session cookie will only be returned to the
server via ssl (https). If you connect to the server via plain http, the
cookie will not be sent. This prevents sniffing of the cookie contents.
This may be set to False when testing your application but should always
be set to True in production.

Defaults to: ``False`` for development, must be ``True`` in production with
https.


SESSION_TYPE
~~~~~~~~~~~~

Enables the `flask-session <https://pythonhosted.org/Flask-Session/>`_
extension if set to a value other than ``None``. The ``flask-session``
package needs to be installed and proper
`configuration <https://pythonhosted.org/Flask-Session/#configuration>`_
needs to be included in the Pagure config file.

This is useful when the Pagure server needs to be scaled up to multiple
instances, which requires the flask session keys to be shared between those.
Flask-session allows you to use Redis, Memcached, relational database
or MongoDB for storing shared session keys.


FROM_EMAIL
~~~~~~~~~~

This configuration key specifies the email address used by this pagure instance
when sending emails (notifications).

Defaults to: ``pagure@localhost.localdomain``


DOMAIN_EMAIL_NOTIFICATIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~

This configuration key specifies the domain used by this pagure instance
when sending emails (notifications). More precisely, it is used
when building the ``msg-id`` header of the emails sent.

Defaults to: ``localhost.localdomain``


VIRUS_SCAN_ATTACHMENTS
~~~~~~~~~~~~~~~~~~~~~~

This configuration key configures whether attachments are scanned for viruses on
upload. For more information, see the install.rst guide.

Defaults to: ``False``


GIT_AUTH_BACKEND
^^^^^^^^^^^^^^^^

This configuration key allows specifying which git auth backend to use.

Git auth backends can either be static (like gitolite), where a file is
generated when something changed and then used on login, or dynamic,
where the actual ACLs are checked in a git hook before being applied.

By default pagure provides the following backends:

- `test_auth`: simple debugging backend printing and returning the string ``Called GitAuthTestHelper.generate_acls()``
- `gitolite2`: allows deploying pagure on the top of gitolite 2
- `gitolite3`: allows deploying pagure on the top of gitolite 3

Defaults to: ``gitolite3``

.. note:: The option GITOLITE_BACKEND is the legacy name, and for backwards compatibility reasons will override this setting

.. note:: These options can be expended, cf :ref:`custom-gitolite`.


Configure Gitolite
------------------

Pagure can use `gitolite <http://gitolite.com/>`_ as an authorization layer.
Gitolite relies on `SSH <https://en.wikipedia.org/wiki/Secure_Shell>`_ for
the authentication. In other words, SSH lets you in and gitolite checks if
you are allowed to do what you are trying to do once you are inside.

Pagure supports both gitolite 2 and gitolite 3 and the code generating
the gitolite configuration can be customized for easier integration with
other systems (cf :ref:`custom-gitolite`).


**gitolite 2 and 3**
~~~~~~~~~~~~~~~~~~~~

GITOLITE_HOME
^^^^^^^^^^^^^

This configuration key points to the home directory of the user under which
gitolite is ran.


GITOLITE_KEYDIR
^^^^^^^^^^^^^^^

This configuration key points to the folder where gitolite stores and accesses
the public SSH keys of all the user have access to the server.

Since pagure is the user interface, it is pagure that writes down the files
in this directory, effectively setting up the users to be able to use gitolite.


GITOLITE_CONFIG
^^^^^^^^^^^^^^^

This configuration key points to the gitolite.conf file where pagure writes
the gitolite repository access configuration.


GITOLITE_CELERY_QUEUE
^^^^^^^^^^^^^^^^^^^^^

This configuration is useful for large pagure deployment where recompiling
the gitolite config file can take a long time. By default the compilation
of gitolite's configuration file is done by the pagure_worker, which spawns
by default 4 concurrent workers. If it takes a while to recompile the
gitolite configuration file, these workers may be stepping on each others'
toes.
In this situation, this configuration key allows you to direct the messages
asking for the gitolite configuration file to be compiled to a different
queue which can then be handled by a different service/worker.

Pagure provides a ``pagure_gitolite_worker.service`` systemd service file
pre-configured to handles these messages if this configuration key is set
to ``gitolite_queue``.


**gitolite 2 only**
~~~~~~~~~~~~~~~~~~~

GL_RC
^^^^^

This configuration key points to the file ``gitolite.rc`` used by gitolite
to record who has access to what (ie: who has access to which repo/branch).


GL_BINDIR
^^^^^^^^^

This configuration key indicates the folder in which the gitolite tools can
be found. It can be as simple as ``/usr/bin/`` if the tools have been installed
using a package manager or something like ``/opt/bin/`` for a more custom
install.


**gitolite 3 only**
~~~~~~~~~~~~~~~~~~~

GITOLITE_HAS_COMPILE_1
^^^^^^^^^^^^^^^^^^^^^^

By setting this configuration key to ``True``, you can turn on using the
gitolite ``compile-1`` binary. This speeds up gitolite task when it recompiles
configuration after new project is created. In order to use this, you need to
have the ``compile-1`` gitolite command.

There are two ways to have it,

#. You distribution already has the file installed for you and you can then
   just use it.
#. You need to download and install it yourself. We are describing what
   needs to be done for this here below.

Installing the ``compile-1`` command:

* You also have to make sure that your distribution of gitolite contains
  `patch <https://github.com/sitaramc/gitolite/commit/c4b6521a4b82e639f6ed776abad79c>`_
  which makes gitolite respect ``ALLOW_ORPHAN_GL_CONF`` configuration variable,
  if this patch isn't already present, you will have to make the change yourself.
* In your ``gitolite.rc`` set ``ALLOW_ORPHAN_GL_CONF`` to ``1`` (you may
  have to add it yourself).
* Still in your ``gitolite.rc`` file, uncomment ``LOCAL_CODE`` file and set
  it to a full path of a directory that you choose (for example
  ``/usr/local/share/gitolite3``).
* Create a subdirectory ``commands`` under the path you picked for ``LOCAL_CODE``
  (in our example, you will need to do: ``mkdir -p /usr/local/share/gitolite3/commands``)
* Finally, install the ``compile-1`` command in this ``commands`` subdirectory
  If your installation doesn't ship this file, you can `download it
  <https://github.com/sitaramc/gitolite/blob/master/contrib/commands/compile-1>`_.
  (Ensure the file is executable, otherwise gitolite will not find it)

Defaults to: ``False``


EventSource options
-------------------

EVENTSOURCE_SOURCE
~~~~~~~~~~~~~~~~~~

This configuration key indicates the URL at which the EventSource server is
available. If not defined, pagure will behave as if there are no EventSource
server running.


EVENTSOURCE_PORT
~~~~~~~~~~~~~~~~

This configuration key indicates the port at which the EventSource server is
running.

.. note:: The EventSource server requires a redis server (see ``Redis options``
         below)



Web-hooks notifications
-----------------------

WEBHOOK
~~~~~~~

This configuration key allows turning on or off web-hooks notifications for
this pagure instance.

Defaults to: ``False``.

.. note:: The Web-hooks server requires a redis server (see ``Redis options``
         below)


.. _redis-section:

Redis options
-------------

REDIS_HOST
~~~~~~~~~~

This configuration key indicates the host at which the `redis <http://redis.io/>`_
server is running.

Defaults to: ``0.0.0.0``.

REDIS_PORT
~~~~~~~~~~

This configuration key indicates the port at which the redis server can be
contacted.

Defaults to: ``6379``.

REDIS_DB
~~~~~~~~

This configuration key indicates the name of the redis database to use for
communicating with the EventSource server.

Defaults to: ``0``.



Authentication options
----------------------

ADMIN_GROUP
~~~~~~~~~~~

List of groups, either local or remote (if the openid server used supports the
group extension), that are the site admins. These admins can regenerate the
gitolite configuration, the ssh key files, and the hook-token for every project
as well as manage users and groups.


PAGURE_ADMIN_USERS
~~~~~~~~~~~~~~~~~~

List of local users that are the site admins. These admins have the same rights as
the users in the admin groups listed above as well as admin rights to
all projects hosted on this pagure instance.


Celery Queue options
--------------------

In order to help prioritize between tasks having a direct impact on the user
experience and tasks needed to be run on the background but not directly
impacting the users, we have split the generic tasks triggered by the web
application into three possible queues: Fast, Medium, Slow.
If none of these options are set, a single queue will be used for all tasks.

FAST_CELERY_QUEUE
~~~~~~~~~~~~~~~~~

This configuration key allows to specify a dedicated queue for tasks that
are triggered by the web frontend and need to be processed quickly for the
best user experience.

This will be used for tasks such as creating a new project, forking or
merging a pull-request.

Defaults to: ``None``.

MEDIUM_CELERY_QUEUE
~~~~~~~~~~~~~~~~~~~

This configuration key allows to specify a dedicated queue for tasks that
are triggered by the web frontend and need to be processed but aren't critical
for the best user experience.

This will be used for tasks such as updating a file in a git repository.

Defaults to: ``None``.

SLOW_CELERY_QUEUE
~~~~~~~~~~~~~~~~~

This configuration key allows to specify a dedicated queue for tasks that
are triggered by the web frontend, are slow and do not impact the user
experience in the user interface.

This will be used for tasks such as updating the ticket git repo based on
the content posted in the user interface.

Defaults to: ``None``.



Stomp Options
-------------

Pagure integration with Stomp allows you to emit messages to any
stomp-compliant message bus.

STOMP_NOTIFICATIONS
~~~~~~~~~~~~~~~~~~~

This configuration key allows to turn on or off notifications via
`stomp protocol <https://stomp.github.io/>`_. All other stomp-related
settings don't need to be present if this is set to ``False``.

Defaults to: ``False``.

STOMP_BROKERS
~~~~~~~~~~~~~

List of 2-tuples with broker domain names and ports. For example
``[('primary.msg.bus.com', 6543), ('backup.msg.bus.com`, 6543)]``.

STOMP_HIERARCHY
~~~~~~~~~~~~~~~

Base name of the hierarchy to emit messages to. For example
``/queue/some.hierarchy.``. Note that this **must** end with
a dot. Pagure will append queue names such as ``project.new``
to this value, resulting in queue names being e.g.
``/queue/some.hierarchy.project.new``.

STOMP_SSL
~~~~~~~~~

Whether or not to use SSL when connecting to message brokers.

Defaults to: ``False``.

STOMP_KEY_FILE
~~~~~~~~~~~~~~

Absolute path to key file for SSL connection. Only required if
``STOMP_SSL`` is set to ``True``.

STOMP_CERT_FILE
~~~~~~~~~~~~~~~

Absolute path to certificate file for SSL connection. Only required if
``STOMP_SSL`` is set to ``True``.

STOMP_CREDS_PASSWORD
~~~~~~~~~~~~~~~~~~~~

Password for decoding ``STOMP_CERT_FILE`` and ``STOMP_KEY_FILE``. Only
required if ``STOMP_SSL`` is set to ``True`` and credentials files are
password-encoded.


API token ACLs
--------------

ACLS
~~~~

This configuration key lists all the ACLs that can be associated with an API
token with a short description of what the ACL allows to do.
This key it not really meant to be changed unless you really know what you
are doing.

USER_ACLS
~~~~~~~~~

This configuration key allows to list which of the ACLs listed in ``ACLS``
can be associated with an API token of a project in the (web) user interface.

Use this configuration key in combination with ``ADMIN_API_ACLS`` to disable
certain ACLs for users while allowing admins to generate keys with them.

Defaults to: ``[key for key in ACLS.keys() if key != 'generate_acls_project']``
    (ie: all the ACLs in ``ACLS`` except for ``generate_acls_project``)


ADMIN_API_ACLS
~~~~~~~~~~~~~~

This configuration key allows to list which of the ACLs listed in ``ACLS``
can be generated by the ``pagure-admin`` CLI tool by admins.

Defaults to: ``['issue_comment', 'issue_create', 'issue_change_status', 'pull_request_flag', 'pull_request_comment', 'pull_request_merge', 'generate_acls_project', 'commit_flag', 'create_branch']``


CROSS_PROJECT_ACLS
~~~~~~~~~~~~~~~~~~

This configuration key allows to list which of the ACLs listed in ``ACLS``
can be associated with a project-less API token in the (web) user interface.
These project-less API tokens can be generated in the user's settings page
and allows action in multiple projects instead of being restricted to a
specific one.

Defaults to: ``['create_project', 'fork_project', 'modify_project']``


Optional options
----------------

Git repository templates
~~~~~~~~~~~~~~~~~~~~~~~~

PROJECT_TEMPLATE_PATH
^^^^^^^^^^^^^^^^^^^^^

This configuration key allows you to specify the path to a git repository
to use as a template when creating new repository for new projects.
This template will not be used for forks nor any of the git repository but
the one used for the sources (ie: it will not be used for the tickets,
requests or docs repositories).

FORK_TEMPLATE_PATH
^^^^^^^^^^^^^^^^^^

This configuration key allows you to specify the path to a git repository
to use as a template when creating new repository for new forks.
This template will not be used for any of the git repository but
the one used for the sources of forks (ie: it will not be used for the
tickets, requests or docs repositories).


SSH_KEYS
~~~~~~~~

It is a good practice to publish the fingerprint and public SSH key of a
server you provide access to.
Pagure offers the possibility to expose this information based on the values
set in the configuration file, in the ``SSH_KEYS`` configuration key.

See the `SSH hostkeys/Fingerprints page on pagure.io <https://pagure.io/ssh_info>`_.

.. warning: The format is important

    SSH_KEYS = {'RSA': {'fingerprint': '<foo>', 'pubkey': '<bar>'}}

Where `<foo>` and `<bar>` must be replaced by your values.


LOGGING
~~~~~~~

This configuration key allows you to set up the logging of the application.
It relies on the standard `python logging module
<https://docs.python.org/2/library/logging.html>`_.

The default value is:

::

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'email_format': {
                'format': MSG_FORMAT
            }
        },
        'filters': {
            'myfilter': {
                '()': ContextInjector,
            }
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
            },
            'email': {
                'level': 'ERROR',
                'formatter': 'email_format',
                'class': 'logging.handlers.SMTPHandler',
                'mailhost': 'localhost',
                'fromaddr': 'pagure@localhost',
                'toaddrs': 'root@localhost',
                'subject': 'ERROR on pagure',
                'filters': ['myfilter'],
            },
        },
        # The root logger configuration; this is a catch-all configuration
        # that applies to all log messages not handled by a different logger
        'root': {
            'level': 'INFO',
            'handlers': ['console'],
        },
        'loggers': {
            'pagure': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': True
            },
            'flask': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            },
            'sqlalchemy': {
                'handlers': ['console'],
                'level': 'WARN',
                'propagate': False
            },
            'binaryornot': {
                'handlers': ['console'],
                'level': 'WARN',
                'propagate': True
            },
            'pagure.lib.encoding_utils': {
                'handlers': ['console'],
                'level': 'WARN',
                'propagate': False
            },
        }
    }

.. note:: as you can see there is an ``email`` handler defined. It's not used
    anywhere by default but you can use it to get report of errors by email
    and thus monitor your pagure instance.
    To do this the easiest is to set, on the ``root`` logger:
    ::

        'handlers': ['console', 'email'],


ITEM_PER_PAGE
~~~~~~~~~~~~~

This configuration key allows you to configure the length of a page by
setting the number of items on the page. Items can be commits, users, groups,
or projects for example.

Defaults to: ``50``.


PR_TARGET_MATCHING_BRANCH
~~~~~~~~~~~~~~~~~~~~~~~~~

If set to ``True``, the default target branch for all pull requests in UI
is the branch that is longest substring of the branch that the pull request
is created from. For example, a ``mybranch`` branch in original repo will
be the default target of a pull request from branch ``mybranch-feature-1``
in a fork when opening a new pull request. If this is set to ``False``,
the default branch of the repo will be the default target of all pull requests.

Defaults to: ``False``.


SMTP_SERVER
~~~~~~~~~~~

This configuration key specifies the SMTP server to use when
sending emails.

Defaults to: ``localhost``.


SMTP_PORT
~~~~~~~~~

This configuration key specifies the SMTP server port.

SMTP by default uses TCP port 25. The protocol for mail submission is
the same, but uses port 587.
SMTP connections secured by SSL, known as SMTPS, default to port 465
(nonstandard, but sometimes used for legacy reasons).

Defaults to: ``25``


SMTP_SSL
~~~~~~~~

This configuration key specifies whether the SMTP connections
should be secured over SSL.

Defaults to: ``False``


SMTP_USERNAME
~~~~~~~~~~~~~

This configuration key allows usage of SMTP with auth.

Note: Specify SMTP_USERNAME and SMTP_PASSWORD for using SMTP auth

Defaults to: ``None``


SMTP_PASSWORD
~~~~~~~~~~~~~

This configuration key allows usage of SMTP with auth.

Note: Specify SMTP_USERNAME and SMTP_PASSWORD for using SMTP auth

Defaults to: ``None``


SHORT_LENGTH
~~~~~~~~~~~~

This configuration key specifies the length of the commit ids or
file hex displayed in the user interface.

Defaults to: ``6``.


BLACKLISTED_PROJECTS
~~~~~~~~~~~~~~~~~~~~

This configuration key specifies a list of project names that are forbidden.
This list is used for example to avoid conflicts at the URL level between the
static files located under ``/static/`` and a project that would be named
``static`` and thus be located at ``/static``.

Defaults to:

::

    [
        'static', 'pv', 'releases', 'new', 'api', 'settings',
        'logout', 'login', 'users', 'groups'
    ]


CHECK_SESSION_IP
~~~~~~~~~~~~~~~~

This configuration key specifies whether to check the user's IP
address when retrieving its session. This makes things more secure but
under certain setups it might not work (for example if there
are proxies in front of the application).

Defaults to: ``True``.


PAGURE_AUTH
~~~~~~~~~~~~

This configuration key specifies which authentication method to use.
Valid options are ``fas``, ``openid``, ``oidc``, or ``local``.

* ``fas`` uses the Fedora Account System `FAS <https://admin.fedoraproject.org/accounts>`
  to provide user authentication and enforces that users sign the FPCA.

* ``openid`` uses OpenID authentication.  Any provider may be used by
  changing the FAS_OPENID_ENDPOINT configuration key.  By default
  FAS (without FPCA) will be used.

* ``oidc`` enables OpenID Connect using any provider.  This provider requires
  the configuration options starting with ``OIDC_`` (see below) to be provided.

* ``local`` causes pagure to use the local pagure database for user management.

Defaults to: ``local``.


OIDC Settings
~~~~~~~~~~~~~

.. note:: Pagure uses `flask-oidc <https://github.com/puiterwijk/flask-oidc/>`_
   to support OIDC authentication. This extension has a `number of configuration
   keys <http://flask-oidc.readthedocs.io/en/latest/#settings-reference>`_
   that may be useful depending on your set-up


OIDC_CLIENT_SECRETS
^^^^^^^^^^^^^^^^^^^

Provide a path to client secrets file on local filesystem. This file can be
obtained from your OpenID Connect identity provider. Note that some providers
don't fill in ``userinfo_uri``. If that is the case, you need to add it to
the secrets file manually.

OIDC_ID_TOKEN_COOKIE_SECURE
^^^^^^^^^^^^^^^^^^^^^^^^^^^

When this is set to True, the cookie with OpenID Connect Token will only be
returned to the server via ssl (https). If you connect to the server via plain
http, the cookie will not be sent. This prevents sniffing of the cookie contents.
This may be set to False when testing your application but should always
be set to True in production.

Defaults to: ``True`` for production with https, can be set to ``False`` for
convenient development.

OIDC_SCOPES
^^^^^^^^^^^

List of `OpenID Connect scopes http://openid.net/specs/openid-connect-core-1_0.html#ScopeClaims`
to request from identity provider.

OIDC_PAGURE_EMAIL
^^^^^^^^^^^^^^^^^

Name of key of user's email in userinfo JSON returned by identity provider.

OIDC_PAGURE_FULLNAME
^^^^^^^^^^^^^^^^^^^^

Name of key of user's full name in userinfo JSON returned by identity provider.

OIDC_PAGURE_USERNAME
^^^^^^^^^^^^^^^^^^^^

Name of key of user's preferred username in userinfo JSON returned by identity
provider.

OIDC_PAGURE_SSH_KEY
^^^^^^^^^^^^^^^^^^^

Name of key of user's ssh key in userinfo JSON returned by identity provider.

OIDC_PAGURE_GROUPS
^^^^^^^^^^^^^^^^^^

Name of key of user's groups in userinfo JSON returned by identity provider.

OIDC_PAGURE_USERNAME_FALLBACK
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This specifies fallback for getting username assuming ``OIDC_PAGURE_USERNAME``
is empty - can be ``email`` (to use the part before ``@``) or ``sub``
(IdP-specific user id, can be a nickname, email or a numeric ID
depending on identity provider).


IP_ALLOWED_INTERNAL
~~~~~~~~~~~~~~~~~~~

This configuration key specifies which IP addresses are allowed
to access the internal API endpoint. These endpoints are accessed by the
milters for example and allow performing actions in the name of someone else
which is sensitive, thus the origin of the request using
these endpoints is validated.

Defaults to: ``['127.0.0.1', 'localhost', '::1']``.


MAX_CONTENT_LENGTH
~~~~~~~~~~~~~~~~~~

This configuration key specifies the maximum file size allowed when
uploading content to pagure (for example, screenshots to a ticket).

Defaults to: ``4 * 1024 * 1024`` which corresponds to 4 megabytes.


ENABLE_TICKETS
~~~~~~~~~~~~~~

This configuration key activates or deactivates the ticketing system
for all the projects hosted on this pagure instance.

Defaults to: ``True``


ENABLE_DOCS
~~~~~~~~~~~

This configuration key activates or deactivates creation of git repos
for documentation for all the projects hosted on this pagure instance.

Defaults to: ``True``


ENABLE_NEW_PROJECTS
~~~~~~~~~~~~~~~~~~~

This configuration key permits or forbids creation of new projects via
the user interface and the API of this pagure instance.

Defaults to: ``True``


ENABLE_UI_NEW_PROJECTS
~~~~~~~~~~~~~~~~~~~~~~

This configuration key permits or forbids creation of new projects via
the user interface (only) of this pagure instance. It allows forbidding
to create new project in the user interface while letting a set of trusted
person to create projects via the API granted they have the API token with
the corresponding ACL.

Defaults to: ``True``


ENABLE_DEL_PROJECTS
~~~~~~~~~~~~~~~~~~~

This configuration key permits or forbids deletion of projects via
the user interface of this pagure instance.

Defaults to: ``True``


ENABLE_DEL_FORKS
~~~~~~~~~~~~~~~~

This configuration key permits or forbids deletion of forks via
the user interface of this pagure instance.

Defaults to: ``ENABLE_DEL_PROJECTS``


EMAIL_SEND
~~~~~~~~~~

This configuration key enables or disables all email notifications for
this pagure instance. This can be useful to turn off when developing on
pagure, or for test or pre-production instances.

Defaults to: ``False``.

.. note::
    This does not disable emails to the email address set in ``EMAIL_ERROR``.


FEDMSG_NOTIFICATIONS
~~~~~~~~~~~~~~~~~~~~

This configuration key allows to turn on or off notifications via `fedmsg
<http://www.fedmsg.com/>`_.

Defaults to: ``False``.


ALWAYS_FEDMSG_ON_COMMITS
~~~~~~~~~~~~~~~~~~~~~~~~

This configuration key allows to enforce `fedmsg <http://www.fedmsg.com/>`_
notifications on commits made on all projects in a pagure instance.

Defaults to: ``True``.


ALLOW_DELETE_BRANCH
~~~~~~~~~~~~~~~~~~~

This configuration keys enables or disables allowing users to delete git
branches from the user interface. In sensible pagure instance you may
want to turn this off and with a customized gitolite configuration you can
prevent users from deleting branches in their git repositories.

Defaults to: ``True``.


LOCAL_SSH_KEY
~~~~~~~~~~~~~

This configuration key allows to let pagure administrate the user's ssh keys
or have a third party tool do it for you.
In most cases, it will be fine to let pagure handle it.

Defaults to ``True``.


DEPLOY_KEY
~~~~~~~~~~

This configuration key allows to disable the deploy keys feature of an
entire pagure instance. This feature enable to add extra public ssh keys
that a third party could use to push to a project.

Defaults to ``True``.


OLD_VIEW_COMMIT_ENABLED
~~~~~~~~~~~~~~~~~~~~~~~

In version 1.3, pagure changed its URL scheme to view the commit of a
project in order to add support for pseudo-namespaced projects.

For pagure instances older than 1.3, who care about backward compatibility,
we added an endpoint ``view_commit_old`` that brings URL backward
compatibility for URLs using the complete git hash (the 40 characters).
For URLs using a shorter hash, the URLs will remain broken.

This configuration key enables or disables this backward compatibility
which is useful for pagure instances running since before 1.3 but is not
for newer instances.

Defaults to: ``False``.


PAGURE_CI_SERVICES
~~~~~~~~~~~~~~~~~~

Pagure can be configure to integrate results of a Continuous Integration (CI)
service to pull-requests open against a project.

To enable this integration, follow the documentation on how to install
pagure-ci and set this configuration key to ``['jenkins']`` (Jenkins being
the only CI service supported at the moment).

Defaults to: ``None``.

.. warning:: Requires `Redis` to be configured and running.


INSTANCE_NAME
~~~~~~~~~~~~~

This allows giving a name to this running instance of pagure. The name is
then used in the welcome screen shown upon first login.

Defaults to: ``Pagure``

.. note: the welcome screen currently does not work with the `local`
         authentication.


USER_NAMESPACE
~~~~~~~~~~~~~~

This configuration key allows to enforce that project are namespaced under
the user's username, behaving in this way in a similar fashion as github.com
or gitlab.com.

Defaults to: ``False``


DOC_APP_URL
~~~~~~~~~~~

This configuration key allows you to specify where the documentation server
is running (preferably in a different domain name entirely).
If not set, the documentation page will show an error message saying that
this pagure instance does not have a documentation server.

Defaults to: ``None``


PRIVATE_PROJECTS
~~~~~~~~~~~~~~~~

This configuration key allows you to host private repositories. These
repositories are visible only to the creator of the repository and to the
users who are given access to the repository. No information is leaked about the
private repository which means redis doesn't have the access to the repository
and even fedmsg doesn't get any notifications.

Defaults to: ``True``


EXCLUDE_GROUP_INDEX
~~~~~~~~~~~~~~~~~~~

This configuration key can be used to hide project an user has access to via
one of the groups listed in this key.

The use-case is the following: the Fedora project is deploying pagure has a
front-end for the git repos of the packages in the distribution, that means
about 17,000 git repositories in pagure. The project has a group of people
that have access to all of these repositories, so when viewing the user's
page of one member of that group, instead of seeing all the project that
this user works on, you can see all the projects hosted in that pagure
instance. Using this configuration key, pagure will hide all the projects
that this user has access to via the specified groups and thus return only
the groups of forks of that users.

Defaults to: ``[]``


TRIGGER_CI
~~~~~~~~~~

A run of pagure-ci can be manually triggered if some key sentences are added
as comment to a pull-request. This allows to re-run a test that failed due
to some network outage or other unexpected issues unrelated to the test
suite.

This configuration key allows to define all the sentences that can be used
to trigger this pagure-ci run.

Defaults to: ``['pretty please pagure-ci rebuild']``

.. note:: The sentences defined in this configuration key should be lower
          case only!


FLAG_STATUSES_LABELS
~~~~~~~~~~~~~~~~~~~~

By default, Pagure has ``success``, ``failure``, ``error``, ``pending`` and
``canceled`` statuses of PR and commit flags. This setting allows you to
define a custom mapping of statuses to their respective Bootstrap labels.


FLAG_SUCCESS
~~~~~~~~~~~~

Holds name of PR/commit flag that is considered a success.

Defaults to: ``success``


FLAG_FAILURE
~~~~~~~~~~~~

Holds name of PR/commit flag that is considered a failure.

Defaults to: ``failure``


FLAG_PENDING
~~~~~~~~~~~~

Holds name of PR/commit flag that is considered a pending state.

Defaults to: ``pending``


EXTERNAL_COMMITTER
~~~~~~~~~~~~~~~~~~

The external committer feature is a way to allow members of groups defined
outside pagure (and provided to pagure upon login by the authentication
system) to be consider committers on pagure.

This feature can give access to all the projects on the instance, all but
some or just some.

Defaults to: ``{}``

To give access to all the projects to a group named ``fedora-altarch`` use
a such a structure::

    EXTERNAL_COMMITTER = {
        'fedora-altarch': {}
    }

To give access to all the projects but one (named ``rpms/test``) to a group
named ``provenpackager`` use a such a structure::

    EXTERNAL_COMMITTER = {
        'fedora-altarch': {},
        'provenpackager': {
            'exclude': ['rpms/test']
        }
    }

To give access to just some projects (named ``rpms/test`` and
``modules/test``) to a group named ``testers`` use a such a structure::

    EXTERNAL_COMMITTER = {
        'fedora-altarch': {},
        'provenpackager': {
            'exclude': ['rpms/test']
        },
        'testers': {
            'restrict': ['rpms/test', 'modules/test']
        }
    }


REQUIRED_GROUPS
~~~~~~~~~~~~~~~

The required groups allows to specify in which group an user must be to be
added to a project with commit or admin access.

Defaults to: ``{}``

Example configuration::

    REQUIRED_GROUPS = {
        'rpms/kernel': ['packager', 'kernel-team'],
        'modules/*': ['module-packager', 'packager'],
        'rpms/*': ['packager'],
        '*': ['contributor'],
    }

With this configuration (evaluated in the provided order):

* only users that are in the groups ``packager`` and ``kernel-team`` will be
  allowed to be added the ``rpms/kernel`` project (where ``rpms`` is the
  namespace and ``kernel`` the project name).

* only users that are in the groups ``module-packager`` and ``packager``
  will be allowed to be added to projects in the ``modules`` namespace.

* only users that are in the group ``packager`` will be allowed to be added
  to projects in the ``rpms`` namespace.

* only users in the ``contributor`` group will be allowed to be added to
  any project on this pagure instance.


GITOLITE_PRE_CONFIG
~~~~~~~~~~~~~~~~~~~

This configuration key allows you to include some content at the *top* of
the gitolite configuration file (such as some specific group definition),
thus allowing to customize the gitolite configuration file with elements
and information that are outside of pagure's control.

This can be used in combination with ``GITOLITE_POST_CONFIG`` to further
customize gitolite's configuration file. It can also be used with
``EXTERNAL_COMMITTER`` to give commit access to git repos based on external
information.

Defaults to: ``None``


GITOLITE_POST_CONFIG
~~~~~~~~~~~~~~~~~~~~

This configuration key allows you to include some content at the *end* of
the gitolite configuration file (such as some project definition or access),
thus allowing to customize the gitolite configuration file with elements
and information that are outside of pagure's control.

This can be used in combination with ``GITOLITE_PRE_CONFIG`` to further
customize gitolite's configuration file. It can also be used with
``EXTERNAL_COMMITTER`` to give commit access to git repos based on external
information.

Defaults to: ``None``


CELERY_CONFIG
~~~~~~~~~~~~~

This configuration key allows you to tweak the configuration of celery for
your needs.
See the documentation about `celery configuration
<http://docs.celeryproject.org/en/latest/userguide/configuration.html>`_ for
more information.

Defaults to: ``{}``


CASE_SENSITIVE
~~~~~~~~~~~~~~

This configuration key allows to make this pagure instance case sensitive
instead of its default: case-insensitive.

Defaults to: ``False``


PROJECT_NAME_REGEX
~~~~~~~~~~~~~~~~~~

This configuration key allows to customize the regular expression used to
validate new project name.

Defaults to: ``^[a-zA-z0-9_][a-zA-Z0-9-_]*$``


APPLICATION_ROOT
~~~~~~~~~~~~~~~~

This configuration key is used in the path of the cookie used by pagure.

Defaults to: ``'/'``


ALLOWED_PREFIX
~~~~~~~~~~~~~~

This configuration key allows to specify a list of allowed namespaces that
will not require creating a group for users to create projects in.

Defaults to: ``[]``


ADMIN_SESSION_LIFETIME
~~~~~~~~~~~~~~~~~~~~~~

This configuration key allows specifying the lifetime of the session during
which the user won't have to re-login for admin actions.
In other words, the maximum time between which an user can access a project's
settings page without re-login.

Defaults to: ``timedelta(minutes=20)``

where timedelta comes from the python datetime module


BLACKLISTED_GROUPS
~~~~~~~~~~~~~~~~~~

This configuration key allows to blacklist some group names.

Defaults to: ``['forks', 'group']``


ENABLE_GROUP_MNGT
~~~~~~~~~~~~~~~~~

This configuration key allows to turn on or off managing (ie: creating a
group, adding or removing users in that group) groups in this pagure instance.
If turned off, groups and group members are to be managed outside of pagure
and synced upon login.

Defaults to: ``True``


ENABLE_USER_MNGT
~~~~~~~~~~~~~~~~

This configuration key allows to turn on or off managing users (adding or
removing them from a project) in this pagure instance.
If turned off, users are managed outside of pagure.

Defaults to: ``True``


SESSION_COOKIE_NAME
~~~~~~~~~~~~~~~~~~~

This configuration key allows to specify the name of the session cookie used
by pagure.

Defaults to: ``'pagure'``


SHOW_PROJECTS_INDEX
~~~~~~~~~~~~~~~~~~~

This configuration key allows to specify what is shown in the index page of
logged in users.

Defaults to: ``['repos', 'myrepos', 'myforks']``


EMAIL_ON_WATCHCOMMITS
~~~~~~~~~~~~~~~~~~~~~

By default pagure sends an email to every one watch commits on a project when a
commit is made.
However some pagure instances may be using a different notification mechanism on
commits and thus may not want this feature to double the notifications received.
This configuration key allows to turn on or off email being sent to people
watching commits on a project upon commits.

Defaults to: ``True``


RepoSpanner Options
-------------

Pagure can be integrated with `repoSpanner <https://repospanner.org>`_
allowing to deploy pagure in a load-balanced environment since the git
repositories are then synced accross multiple servers simultaneously.

Support for this integration has been included in Pagure version 5.0 and higher.

Here below are the different options one can/should use to integrate pagure
with repoSpanner.

REPOSPANNER_NEW_REPO
~~~~~~~~~~~~~~~~~~~~

This configuration key instructs pagure to create new git repositories on
repoSpanner or not.
Its value should be the region in which the new git repositories should be
created on.

Defaults to: ``None``.

REPOSPANNER_NEW_REPO_ADMIN_OVERRIDE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This configuration key can be used to let pagure admin override the default
region used when creating new git repositories on repoSpanner.
Its value should be a boolean.

Defaults to: ``False``

REPOSPANNER_NEW_FORK
~~~~~~~~~~~~~~~~~~~~

This configuration key instructs pagure on where/how to create new git
repositories for the forks with repoSpanner.
If ``None``, git repositories for forks are created outside of repoSpanner
entirely.
If ``True``, git repositories for forks are created in the same region as
the parent project.
Otherwise, a region can be directly specified where git repositories for
forks will be created.

Defaults to: ``True``

REPOSPANNER_ADMIN_MIGRATION
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This configuration key can be used to let admin manually migrate individual
project into repoSpanner once it is set up.

Defaults to: ``False``

REPOSPANNER_REGIONS
~~~~~~~~~~~~~~~~~~~

This configuration key allows to specify the different region where repoSpanner
is deployed and thus with which this pagure instance can be integrated.

An example entry could look like:

::

    REPOSPANNER_REGIONS = {
        'default': {'url': 'https://nodea.regiona.repospanner.local:8444',
                    'repo_prefix': 'pagure/',
                    'hook': None,
                    'ca': '/etc/pki/repospanner/pki/ca.crt',
                    'admin_cert': {'cert': '/etc/pki/repospanner/pki/admin.crt',
                                   'key': '/etc/pki/repospanner/pki/admin.key'},
                    'push_cert': {'cert': '/etc/pki/repospanner/pki/pagure.crt',
                                  'key': '/etc/pki/repospanner/pki/pagure.key'}}
    }

If this configuration key is not defined, pagure will consider that it is
not set to be integrated with repoSpanner.

Defaults to: ``{}``


SSH_KEYS_USERNAME_LOOKUP
~~~~~~~~~~~~~~~~~~~~~~~~

This configuration key is used by the keyhelper script to indicate that the
git username should be used and looked up. Use this if the username that is sent
to ssh is specific for a unique Pagure user (i.e. not using a single "git@" user
for all git operations).


SSH_KEYS_USERNAME_EXPECT
~~~~~~~~~~~~~~~~~~~~~~~~

This configuration key should contain the username that is used for git if a single
SSH user is used for all git ssh traffic (i.e. "git").


SSH_KEYS_OPTIONS
~~~~~~~~~~~~~~~~

This configuration key provides the options added to keys as they are returned
to sshd, in the same format as AuthorizedKeysFile
(see "AUTHORIZED_KEYS FILE FORMAT" in sshd(8)).


Deprecated configuration keys
-----------------------------

FORK_FOLDER
~~~~~~~~~~~

This configuration key used to be use to specify the folder where the forks
are placed. Since the release 2.0 of pagure, it has been deprecated, forks
are now automatically placed in a sub-folder of the folder containing the
mains git repositories (ie ``GIT_FOLDER``).

See the ``UPGRADING.rst`` file for more information about this change and
how to handle it.


UPLOAD_FOLDER
~~~~~~~~~~~~~

This configuration key used to be use to specify where the uploaded releases
are available. It has been replaced by `UPLOAD_FOLDER_PATH` in the release
2.10 of pagure.


GITOLITE_VERSION
~~~~~~~~~~~~~~~~

This configuration key specifies which version of gitolite you are
using, it can be either ``2`` or ``3``.

Defaults to: ``3``.

This has been replaced by `GITOLITE_BACKEND` in the release 3.0 of pagure.


DOCS_FOLDER, REQUESTS_FOLDER, TICKETS_FOLDER
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These configuration values were removed. It has been found out that
due to how Pagure writes repo names in the gitolite configuration file,
these must have fixed paths relative to `GIT_FOLDER`. Specifically, they
must occupy subdirectories `docs`, `requests` and `tickets` under `GIT_FOLDER`.
They are now computed automatically based on value of `GIT_FOLDER`.
Usage of docs and tickets can be triggered by setting `ENABLE_DOCS` and
`ENABLE_TICKETS` to `True` (this is the default).


FILE_SIZE_HIGHLIGHT
~~~~~~~~~~~~~~~~~~~

This configuration key allows to specify the maximum number of characters a file
or diff should have to have syntax highlighting. Everything above this limit
will not have syntax highlighting as this is a memory intensive procedure that
easily leads to out of memory error on large files or diff.

Defaults to: ``5000``


BOOTSTRAP_URLS_CSS
~~~~~~~~~~~~~~~~~~

This configuration key allows to specify the URL where are hosted the bootstrap
CSS file since the files hosted on apps.fedoraproject.org used in pagure.io
are not restricted in browser access.

Defaults to: ``'https://apps.fedoraproject.org/global/fedora-bootstrap-1.1.1/fedora-bootstrap.css'``

This has been deprecated by the new way of theming pagure, see the `theming
documentation <https://docs.pagure.org/pagure/usage/theming.html>`_


BOOTSTRAP_URLS_JS
~~~~~~~~~~~~~~~~~

This configuration key allows to specify the URL where are hosted the bootstrap
JS file since the files hosted on apps.fedoraproject.org used in pagure.io
are not restricted in browser access.

Defaults to: ``'https://apps.fedoraproject.org/global/fedora-bootstrap-1.1.1/fedora-bootstrap.js'``

This has been deprecated by the new way of theming pagure, see the `theming
documentation <https://docs.pagure.org/pagure/usage/theming.html>`_


HTML_TITLE
~~~~~~~~~~

This configuration key allows you to customize the HTML title of all the
pages, from ``... - pagure`` (default) to ``... - <your value>``.

Defaults to: ``Pagure``

This has been deprecated by the new way of theming pagure, see the `theming
documentation <https://docs.pagure.org/pagure/usage/theming.html>`_


GITOLITE_BACKEND
~~~~~~~~~~~~~~~~

This configuration key allowed specifying the gitolite backend.
This has now been replaced by GIT_AUTH_BACKEND, please see that option
for information on valid values.
