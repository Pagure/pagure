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

Defaults to: ``https://pagure.org/``


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

Defaults to: ``'ssh://git@pagure.org/'``


GIT_URL_GIT
~~~~~~~~~~~

This configuration key provides the information to the user on how to clone
the git repos hosted on pagure anonymously. This access can be granted via
the ``git://`` or ``http(s)://`` protocols.

The URL should end with a slash ``/``.

Defaults to: ``'git://pagure.org/'``


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

Each project in pagure has 4 git repositories:

- the main repo for the code
- the doc repo showed in the doc server
- the ticket repo storing the metadata of the tickets
- the request repo storing the metadata of the pull-requests

There are then another 3 folders: one for specifying the locations of the forks, one
for the remote git repo used for the remotes pull-requests (ie: those coming from
a project not hosted on this instance of pagure), and one for user-uploaded tarballs.


GIT_FOLDER
~~~~~~~~~~

This configuration key points to the folder where the git repos for the
source code of the projects are stored.


DOCS_FOLDER
~~~~~~~~~~~

This configuration key points to the folder where the git repos for the
documentation of the projects are stored.


TICKETS_FOLDER
~~~~~~~~~~~~~~

This configuration key points to the folder where the git repos for the
metadata of the tickets opened against the project are stored .


REQUESTS_FOLDER
~~~~~~~~~~~~~~~

This configuration key points to the folder where the git repos for the
metadata of the pull-requests opened against the project are stored.


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


FROM_EMAIL
~~~~~~~~~~

This configuration key specifies the email address used by this pagure instance
when sending emails (notifications).

Defaults to: ``pagure@pagure.org``


DOMAIN_EMAIL_NOTIFICATIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~

This configuration key specifies the domain used by this pagure instance
when sending emails (notifications). More precisely, it is used
when building the ``msg-id`` header of the emails sent.

Defaults to: ``pagure.org``


VIRUS_SCAN_ATTACHMENTS
~~~~~~~~~~~~~~~~~~~~~~

This configuration key configures whether attachments are scanned for viruses on
upload. For more information, see the install.rst guide.

Defaults to: ``False``



Configure Gitolite
------------------

Pagure uses `gitolite <http://gitolite.com/>`_ as an authorization layer.
Gitolite relies on `SSH <https://en.wikipedia.org/wiki/Secure_Shell>`_ for
the authentication. In other words, SSH lets you in and gitolite checks if
you are allowed to do what you are trying to do once you are inside.

Pagure supports both gitolite 2 and gitolite 3 and the code generating
the gitolite configuration can be customized for easier integration with
other systems (cf :ref:`custom-gitolite`).


**gitolite 2 and 3**
~~~~~~~~~~~~~~~~~~~~

GITOLITE_HOME
~~~~~~~~~~~~~

This configuration key points to the home directory of the user under which
gitolite is ran.


GITOLITE_KEYDIR
~~~~~~~~~~~~~~~

This configuration key points to the folder where gitolite stores and accesses
the public SSH keys of all the user have access to the server.

Since pagure is the user interface, it is pagure that writes down the files
in this directory, effectively setting up the users to be able to use gitolite.


GITOLITE_CONFIG
~~~~~~~~~~~~~~~

This configuration key points to the gitolite.conf file where pagure writes
the gitolite repository access configuration.


GITOLITE_BACKEND
~~~~~~~~~~~~~~~~

This configuration key allows specifying which helper method to use to
generate and compile gitolite's configuration file.

By default pagure provides the following backends:

- `test_auth`: simple debugging backend printing and returning the string ``Called GitAuthTestHelper.generate_acls()``
- `gitolite2`: allows deploying pagure on the top of gitolite 2
- `gitolite3`: allows deploying pagure on the top of gitolite 3

Defaults to: ``gitolite3``

.. note:: These options can be expended, cf :ref:`custom-gitolite`.


GITOLITE_CELERY_QUEUE
~~~~~~~~~~~~~~~~~~~~~

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
~~~~~

This configuration key points to the file ``gitolite.rc`` used by gitolite
to record who has access to what (ie: who has access to which repo/branch).


GL_BINDIR
~~~~~~~~~

This configuration key indicates the folder in which the gitolite tools can
be found. It can be as simple as ``/usr/bin/`` if the tools have been installed
using a package manager or something like ``/opt/bin/`` for a more custom
install.



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

Defaults to: ``['create_project', 'fork_project', 'modify_project']``


CROSS_PROJECT_ACLS
~~~~~~~~~~~~~~~~~~

This configuration key allows to list which of the ACLs listed in ``ACLS``
can be associated with a project-less API token in the (web) user interface.
These project-less API tokens can be generated in the user's settings page
and allows action in multiple projects instead of being restricted to a
specific one.

Defaults to: ``['issue_comment', 'issue_create', 'issue_change_status', 'pull_request_flag', 'pull_request_comment', 'pull_request_merge']``


Optional options
----------------

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


ITEM_PER_PAGE
~~~~~~~~~~~~~
This configuration key allows you to configure the length of a page by
setting the number of items on the page. Items can be commits, users, groups,
or projects for example.

Defaults to: ``50``.


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
Pagure currently supports two authentication methods: one relying on the
Fedora Account System `FAS <https://admin.fedoraproject.org/accounts>`_,
and the other using only the local database.
It can therefore be either ``fas`` or ``local``.

Defaults to: ``fas``.


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


ENABLE_NEW_PROJECTS
~~~~~~~~~~~~~~~~~~~

This configuration key permits or forbids creation of new projects via
the user interface of this pagure instance.

Defaults to: ``True``


ENABLE_DEL_PROJECTS
~~~~~~~~~~~~~~~~~~~

This configuration key permits or forbids deletion of projects via
the user interface of this pagure instance.

Defaults to: ``True``


EMAIL_SEND
~~~~~~~~~~

This configuration key enables or disables all email notifications for
this pagure instance. This can be useful to turn off when developing on
pagure, or for test or pre-production instances.

Defaults to: ``False``.

.. note::
    This does not disable emails to the email address set in ``EMAIL_ERROR``.


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

Defaults to: ``False``


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


HTML_TITLE
~~~~~~~~~~

This configuration key allows you to customize the HTML title of all the
pages, from ``... - pagure`` (default) to ``... - <your value>``.

Defaults to: ``Pagure``


CASE_SENSITIVE
~~~~~~~~~~~~~~

This configuration key allows to make this pagure instance case sensitive
instead of its default: case-insensitive.

Defaults to: ``False``


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
