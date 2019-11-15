Upgrading Pagure
================

From 5.7 to 5.8
---------------

The 5.8 release does not contain any database schema changes nor changes in the
configuration keys.


From 5.6 to 5.7
---------------

The 5.7 release does not contain any database schema changes nor changes in the
configuration keys.


From 5.5 to 5.6
---------------

The 5.6 release contains a database schema updates, so:

* Update the data schema using alembic: ``alembic upgrade head``

(As usual, do your backups before).

New configuration key added:

* CSP_HEADERS


From 5.4 to 5.5
---------------

The 5.5 release contains a database schema updates, so:

* Update the data schema using alembic: ``alembic upgrade head``

New configuration key added:

* GIT_HOOK_DB_RO


From 5.3.x to 5.4
-----------------

The 5.4 release does not contain any database schema changes, nor any new
configuration key.


From 5.2 to 5.3
---------------

The 5.3 release contains a database schema updates, so:

* Update the data schema using alembic: ``alembic upgrade head``

(As usual, do your backups before).

While working on pagure 5.3, we found that the version of python werkzeug
available in CentOS 7 is too old and makes some of pagure's tests fail. We
recomment it to be upgrade to at least 0.9.6.

New configuration keys have been added:

* ENABLE_TICKETS_NAMESPACE
* FEDORA_MESSAGING_NOTIFICATIONS
* SYNTAX_ALIAS_OVERRIDES
* ALWAYS_STOMP_ON_COMMITS
* ALWAYS_MQTT_ON_COMMITS
* MQTT_TOPIC_PREFIX


From 5.1.x to 5.2
-----------------

The 5.2 release contains a database schema updates, so:

* Update the data schema using alembic: ``alembic upgrade head``

(As usual, do your backups before).

If you run into issues with the ``hook_mirror``, see the upgrade notes for
the release 5.1.4 below.

Note that the minimal version of pygit2 has been bumped to: 0.26.0

New configuration keys have been added:

* MQTT_NOTIFICATIONS
* MQTT_HOST
* MQTT_PORT
* MQTT_USERNAME
* MQTT_PASSWORD
* MQTT_CA_CERTS
* MQTT_CERTFILE
* MQTT_KEYFILE
* MQTT_CERT_REQS
* MQTT_TLS_VERSION
* MQTT_CIPHERS
* DISABLE_MIRROR_IN
* SSH_ADMIN_TOKEN
* GIT_GARBAGE_COLLECT
* DISABLE_REMOTE_PR
* ADMIN_EMAIL
* LOG_ALL_COMMITS
* ARCHIVE_FOLDER

One configuration key changes its default structure:
* TRIGGER_CI

Changes in dependencies:
* Mimimal version of pygit2 version bumped to: 0.26.0
* Minimal version of openssh set to: 7.4


From 5.1 to 5.1.4
-----------------

In the development of 5.1.4 it was found out that the alembic migration
``ba538b2648b7`` that creates the ``hook_mirror`` table was incomplete.
If you created that table via alembic, you will likely want to re-run it. Beware
that applying the following commands will destroy any data you have in this
table.

* Mark the database to this migration::

   alembic stamp ba538b2648b7

* Remove the ``hook_mirror`` table so it can be re-generated::

   alembic downgrade -1

* Re-run that single migration::

   alembic upgrade +1

* Marking the database to the last current migration (as of 5.1.4)::

   alembic stamp f16ab75e4d32

Again, any project that tried to setup the mirroring feature in pagure will need
to be reconfigured.

Another option (that will prevent loosing any data in this table) is to
adjust the table manually using these SQL queries:

::

    ALTER TABLE hook_mirror ADD COLUMN 'public_key' TEXT;
    ALTER TABLE hook_mirror ADD COLUMN 'target' TEXT;
    ALTER TABLE hook_mirror ADD COLUMN 'last_log' TEXT;


From 5.x to 5.1
---------------

The 5.1 release contains a database schema updates, so:

* Update the data schema using alembic: ``alembic upgrade head``

(As usual, do your backups before).


New configuration keys added:

* ALLOW_ADMIN_IGNORE_EXISTING_REPOS
* ALLOW_HTTP_PULL_PUSH
* ALLOW_HTTP_PUSH
* HTTP_REPO_ACCESS_GITOLITE


From 5.0 to 5.0.1
-----------------

The 5.0 release was missing a database schema migration to add the
``hook_mirror`` table. This alembic migration has been added, so if you have
note update to 5.0, you will want to update your database schema using:
``alembic upgrade head``. If you went around this issue by running the
``pagure_createdb.py`` script, you can mark you database schema up to date using
``alembic stamp ba538b2648b7``.


From 4.x to 5.0
---------------

The release 5.0 brings some changes to the database schema.

* Update the data schema using alembic: ``alembic upgrade head``

New configuration keys added:

* PR_TARGET_MATCHING_BRANCH
* EMAIL_ON_WATCHCOMMITS
* THEME
* GIT_AUTH_BACKEND (replacing GITOLITE_BACKEND, backward compatibility kept for
  now)
* REPOSPANNER_PSEUDO_FOLDER
* REPOSPANNER_NEW_REPO
* REPOSPANNER_NEW_REPO_ADMIN_OVERRIDE
* REPOSPANNER_NEW_FORK
* REPOSPANNER_ADMIN_MIGRATION
* REPOSPANNER_REGIONS
* SSH_KEYS_USERNAME_LOOKUP
* SSH_KEYS_USERNAME_EXPECT
* SSH_KEYS_OPTIONS

Configuration deprecated:

* BOOTSTRAP_URLS_CSS
* BOOTSTRAP_URLS_JS
* FILE_SIZE_HIGHLIGHT
* HTML_TITLE
* GITOLITE_BACKEND

Note: Some configuration keys changed their default value:

* LOGGING
* PRIVATE_PROJECTS
* EMAIL_ERROR
* FROM_EMAIL
* DOMAIN_EMAIL_NOTIFICATIONS
* APP_URL
* DOC_APP_URL
* GIT_URL_SSH
* GIT_URL_GIT
* FEDMSG_NOTIFICATIONS
* PAGURE_AUTH

New dependencies:
* trololio (replaces trollius that is no longer a direct dependency)


From 3.x to 4.0
---------------

The release 4.0 brings some changes to the database schema.

* Update the data schema using alembic: ``alembic upgrade head``

New configuration keys added:

* EMAIL_ON_WATCHCOMMITS
* ALWAYS_FEDMSG_ON_COMMITS
* SESSION_TYPE
* PROJECT_TEMPLATE_PATH
* FORK_TEMPLATE_PATH


From 3.13 to 3.13.1
-------------------

The release 3.13.1 brings one change to the database schema to remove a database
constraint (pull_requests_check in the pull_requests table) that is not only no
longer needed but even blocking now.

* Update the data schema using alembic: ``alembic upgrade head``


From 3.12 to 3.13
-----------------

The release 3.13 brings some features and bug fixes but does not have any
changes made to the database schema or new configuration keys. Update should be
straight forward.


From 3.11 to 3.12
-----------------

The release 3.12 brings some changes to the database schema.

* Update the data schema using alembic: ``alembic upgrade head``

Note that this release bring support for `OpenID
Connect<https://en.wikipedia.org/wiki/OpenID_Connect>`_ authentication, meaning
pagure can now be deployed with authentication coming from, for example, google.
This brings a number of new configuration keys:

* OIDC_CLIENT_SECRETS
* OIDC_ID_TOKEN_COOKIE_SECURE
* OIDC_SCOPES
* OIDC_PAGURE_EMAIL
* OIDC_PAGURE_FULLNAME
* OIDC_PAGURE_USERNAME
* OIDC_PAGURE_SSH_KEY
* OIDC_PAGURE_GROUPS
* OIDC_PAGURE_USERNAME_FALLBACK


From 3.10 to 3.11
-----------------

The release 3.11 brings some changes to the database schema.

* Update the data schema using alembic: ``alembic upgrade head``

In addition, if you are deploying pagure with fedmsg support you had to set
fedmsg to the
`active <http://www.fedmsg.com/en/stable/publishing/#publishing-through-a-relay>`_
mode for the workers to be able to send fedmsg messages. This is now the
default and forced configuration.

New API acls:

* commit_flag
* pull_request_subscribe


From 3.9 to 3.10
----------------

The release 3.10 brings some changes to the database schema.

* Update the data schema using alembic: ``alembic upgrade head``


From 3.8 to 3.9
---------------

This release brings a number of bug fixes and features but does not require
any special precaution when upgrading.


From 3.7 to 3.8
---------------

The release 3.8 brings some changes to the database schema.

* Update the data schema using alembic: ``alembic upgrade head``

New configuration keys added:

* PROJECT_NAME_REGEX


From 3.6 to 3.7
---------------

The release 3.7 brings some changes to the database schema.

* Update the data schema using alembic: ``alembic upgrade head``

New configuration keys added:

* ENABLE_DEL_FORKS
* ENABLE_UI_NEW_PROJECTS


From 3.5 to 3.6
---------------
New configuration keys added:

* GITOLITE_CELERY_QUEUE


From 3.4 to 3.5
---------------

New configuration keys added:

* USER_ACLS
* CASE_SENSITIVE
* HTML_TITLE


From 3.3 to 3.4
---------------

New configuration keys added:

* DEPLOY_KEY
* LOCAL_SSH_KEY
* ALLOW_DELETE_BRANCH


From 3.2 to 3.3
---------------

[SECURITY FIX]: The 3.3 release contains an important security fix.
If you are using the private project feature of pagure, the gitolite
configuration generated was still granting access to the private projects. This
made the private projects visible and accessible.
After updating to 3.3, ensure your gitolite configuration gets re-generated
(pagure-admin refresh-gitolite can help you with this).


The 3.3 release brings some adjustments to the database schema.

* Update the database schema using alembic: ``alembic upgrade head``



From 3.1 to 3.2
---------------

While not being a bug fix, this release has no database schema changes.
However, this release breaks the plugin interface for auth introduced in 3.1 and
changed in 3.1. If you are using pagure-dist-git, make sure to upgrade to at
least 0.4. This interface will be considered stable in 3.4 and announced as
such.


From 3.0 to 3.1
---------------

While not being a bug fix, this release has no database schema changes.
However, this release breaks the plugin interface for auth introduced in 3.0. If
you are using pagure-dist-git, make sure to upgrade to at least 0.3.


From 2.15 to 3.0
----------------

The 3.0 version was released with some major re-architecturing. The interaction
with the backend git repo (being the main source repo or the tickets or requests
repos) are now done by a worker that is triggered via a message queue.
This communication is done using `celery <http://www.celeryproject.org/>`_ and
via one of the message queue celery supports (pagure currently defaulting to
`redis <https://redis.io/>`_.
So to get pagure 3.0 running, you will need to get your own message queue (such
as redis) up running and configured in pagure's configuration.

This major version bump has also been an opportunity to rename all the services
to use the same naming schema of pagure-<service>.
The rename is as such:

+------------------+-----------------+
|  In 2.x          | From 3.0        |
+==================+=================+
| pagure-ci        | pagure-ci       |
+------------------+-----------------+
| ev-server        | pagure-ev       |
+------------------+-----------------+
| pagure-loadjson  | pagure-loadjson |
+------------------+-----------------+
| pagure-logcom    | pagure-logcom   |
+------------------+-----------------+
| milters          | pagure-milters  |
+------------------+-----------------+
| webhook-server   | pagure-webhook  |
+------------------+-----------------+
|                  | pagure-worker   |
+------------------+-----------------+

.. note:: This last service is the service mentioned above and it is part of
          pagure core, not optional unlike the other services in this table.

This release also introduces some new configuration keys:

- ``CELERY_CONFIG`` defaults to ``{}``
- ``ATTACHMENTS_FOLDER``, to be configured
- ``GITOLITE_BACKEND`` defaults to ``gitolite3``, deprecates ``GITOLITE_VERSION``
- ``EXTERNAL_COMMITTER`` defaults to ``{}``
- ``REQUIRED_GROUPS`` defaults to ``{}``

This version also introduces a few database changes, so you will need to update
the database schema using alembic: ``alembic upgrade head``.


From 2.14 to 2.15
-----------------

The 2.15 release brings some adjustments to the database scheme.

* Update the database schame using alembic: ``alembic upgrade head``


From 2.13 to 2.14
-----------------

The 2.14 release brings some adjustments to the database scheme.

* Update the database schame using alembic: ``alembic upgrade head``


From 2.12 to 2.13
-----------------

The 2.13 release brings some adjustments to the database scheme.

* Update the database schame using alembic: ``alembic upgrade head``


From 2.11 to 2.12
-----------------

From this release on, we will have alembic migration script for new table
creation, so there will no longer be a need to use ``createdb.py``

The 2.12 release brings some adjustments to the database scheme.

* Update the database schame using alembic: ``alembic upgrade head``


From 2.10 to 2.11
-----------------

The 2.10 releases brings some adjustments to the database scheme.

* Create the new DB tables and the new status field using the ``createdb.py``
    script.

* Update the database schame using alembic: ``alembic upgrade head``


From 2.9 to 2.10
----------------

The 2.10 releases brings some little changes to the database scheme.

Therefore when upgrading to 2.10, you will have to:

* Update the database schame using alembic: ``alembic upgrade head``


From 2.8 to 2.9
---------------

The 2.9 releases brings some adjustments to the database scheme.

* Create the new DB tables and the new status field using the ``createdb.py``
    script.

* Update the database schame using alembic: ``alembic upgrade head``

If you are interested in loading your local data into the ``pagure_logs`` table
that this new release adds (data which is then displayed in the calendar heatmap
on the user's page), you can find two utility scripts in
https://pagure.io/pagure-utility that will help you to do that. They are:

* fill_logs_from_db - Based on the data present in the database, this script
  fills the ``pagure_logs`` table (this will add: new ticket, new comment, new
  PR, closing a PR or a ticket and so on).
* fill_logs_from_gits - By going through all the git repo hosted in your pagure
  instance, it will log who did what when.


From 2.7 to 2.8
---------------

2.8 brings a little change to the database scheme.

Therefore when upgrading to from 2.7 to 2.8, you will have to:

* Update the database schame using alembic: ``alembic upgrade head``


From 2.6 to 2.7
---------------

2.7 adds new tables as well as changes some of the existing ones.

Therefore when upgrading to 2.7, you will have to:

* Create the new DB tables and the new status field using the ``createdb.py``
  script.

* Update the database schame using alembic, one of the upgrade will require
  access to pagure's configuration file, which should thus be passed onto the
  command via an environment variable:
  ``PAGURE_CONFIG=/path/to/pagure.cf alembic upgrade head``


This release also brings a new configuration key:

* ``INSTANCE_NAME`` used in the welcome screen shown upon first login (only with
  FAS and OpenID auth) to describe the instance


The API has also been upgraded to a version ``0.8`` due to the changes (backward
compatible) made to support the introduction of `close_status` to issues.


From 2.5 to 2.6
---------------

2.6 brings quite a few changes and some of them impacting the database scheme.

Therefore when upgrading from 2.4 to 2.6, you will have to:

* Update the database schame using alembic: ``alembic upgrade head``


From 2.4 to 2.5
---------------

2.5 brings quite a few changes and some of them impacting the database scheme.

Therefore when upgrading from 2.4 to 2.5, you will have to:

* Update the database schame using alembic: ``alembic upgrade head``


From 2.3 to 2.4
---------------

2.4 brings quite a few changes and some of them impacting the database scheme.

Therefore when upgrading from 2.3.x to 2.4, you will have to:

* Update the database schame using alembic: ``alembic upgrade head``


This update also brings some new configuration keys:

* ``VIRUS_SCAN_ATTACHMENTS`` allows turning on or off checking attachments for
  virus using clamav. This requires pyclamd but is entirely optional (and off by
  default)
* ``PAGURE_CI_SERVICES`` allows specifying with which CI (Continuous
  Integration) services this pagure instance can integrate with. Currently, only
  `Jenkins` is supported, but this configuration key defaults to ``None``.


From 2.2 to 2.3
---------------

2.3 brings a few changes impacting the database scheme, including a new
`duplicate` status for tickets, a feature allowing one to `watch` or
`unwatch` a project and notifications on tickets as exist on pull-requests.

Therefore, when upgrading from 2.2.x to 2.3, you will have to :

* Create the new DB tables and the new status field using the ``createdb.py`` script.

* Update the database schame using alembic: ``alembic upgrade head``

This update also brings a new configuration key:

* ``PAGURE_ADMIN_USERS`` allows to mark some users as instance-wide admins, giving
  them full access to every projects, private or not. This feature can then be
  used as a way to clean spams.
* ``SMTP_PORT`` allows to specify the port to use when contacting the SMTP
  server
* ``SMTP_SSL`` allows to specify whether to use SSL when contacting the SMTP
  server
* ``SMTP_USERNAME`` and ``SMTP_PASSWORD`` if provided together allow to contact
  an SMTP requiring authentication.

In this update is also added the script ``api_key_expire_mail.py`` meant to be
run by a daily cron job and warning users when their API token is nearing its
expiration date.



2.2.2
-----

Release 2.2.2 contains an important security fix, blocking a source of XSS
attack.



From 2.1 to 2.2
---------------

2.2 brings a number of bug fixes and a few improvements.

One of the major changes impacts the databases where we must change some of the
table so that the foreign key cascade on delete (fixes deleting a project when a
few plugins were activated).

When upgrading for 2.1 to 2.2 all you will have to do is:

* Update the database scheme using alembic: ``alembic upgrade head``

.. note:: If you run another database system than PostgreSQL the alembic
  revision ``317a285e04a8_delete_hooks.py`` will require adjustment as the
  foreign key constraints are named and the names are driver dependant.



From 2.0 to 2.1
---------------

2.1 brings its usual flow of improvements and bug fixes.

When upgrading from 2.0.x to 2.1 all you will have to:

* Update the database schame using alembic: ``alembic upgrade head``



From 1.x to 2.0
---------------

As the version change indicates, 2.0 brings quite a number of changes,
including some that are not backward compatible.

When upgrading to 2.0 you will have to:

* Update the database schema using alembic: ``alembic upgrade head``

* Create the new DB tables so that the new plugins work using the
  ``createdb.py`` script

* Move the forks git repo

Forked git repos are now located under the same folder as the regular git
repos, just under a ``forks/`` subfolder.
So the structure changes from: ::

    repos/
    ├── foo.git
    └── bar.git

    forks/
    ├── patrick/
    │   ├── test.git
    │   └── ipsilon.git
    └── pingou/
        ├── foo.git
        └── bar.git

to: ::

    repos/
    ├── foo.git
    ├── bar.git
    └── forks/
        ├── patrick/
        │   ├── test.git
        │   └── ipsilon.git
        └── pingou/
            ├── foo.git
            └── bar.git

So the entire ``forks`` folder is moved under the ``repos`` folder where
the other repositories are, containing the sources of the projects.


Git repos for ``tickets``, ``requests`` and ``docs`` will be trickier to
move as the structure changes from: ::

    tickets/
    ├── foo.git
    ├── bar.git
    ├── patrick/
    │   ├── test.git
    │   └── ipsilon.git
    └── pingou/
        ├── foo.git
        └── bar.git

to: ::

    tickets/
    ├── foo.git
    ├── bar.git
    └── forks/
        ├── patrick/
        │   ├── test.git
        │   └── ipsilon.git
        └── pingou/
            ├── foo.git
            └── bar.git

Same for the ``requests`` and the ``docs`` git repos.

As you can see in the ``tickets``, ``requests`` and ``docs`` folders there
are two types of folders, git repos which are folder with a name ending
with ``.git``, and folder corresponding to usernames. These last ones are
the ones to be moved into a subfolder ``forks/``.

This can be done using something like: ::

    mkdir forks
    for i in `ls -1 |grep -v '\.git'`; do mv $i forks/; done

* Re-generate the gitolite configuration.

This can be done via the ``Re-generate gitolite ACLs file`` button in the
admin page.

* Keep URLs backward compatible

The support of pseudo-namespace in pagure 2.0 has required some changes
to the URL schema:
https://pagure.io/pagure/053d8cc95fcd50c23a8b0a7f70e55f8d1cc7aebb
became:
https://pagure.io/pagure/c/053d8cc95fcd50c23a8b0a7f70e55f8d1cc7aebb
(Note the added /c/ in it)

We introduced a backward compatibility fix for this.

This fix is however *disabled* by default so if you wish to keep the URLs
valid, you will need to adjust you configuration file to include: ::

    OLD_VIEW_COMMIT_ENABLED = True
