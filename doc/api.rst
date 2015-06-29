Pagure API v0 Reference
=======================

Overview
--------

This documentation describes the Pagure API v0.

Authentication
~~~~~~~~~~~~~~

To access some endpoints, you need login Pagure using API token. You can
generate one in the project setting page.

When sending HTTP request, include ``Authorization`` field in the header
with value ``token $your-api-token``, where ``$your-api-token`` is the
API token generated in the project setting page.

Anyone with the token can access the APIs on your behalf, so please be
sure to keep it private and safe.

Request Encode
~~~~~~~~~~~~~~

The payload of POST and GET requests is encoded as
``application/x-www-form-urlencoded``. This is an example URL of a GET
request:
``https://pagure.io/api/0/test/issues?status=Open&tags=Pagure&tags=Enhancement``

Return Type
~~~~~~~~~~~

The return value of API calls is ``application/json``. This is an
example of return value:

::

    {
      "args": {
        "assignee": null,
        "author": null,
        "status": null,
        "tags": []
      },
      "issues": [
        {
          "assignee": null,
          "blocks": [],
          "comments": [],
          "content": "Sample ticket",
          "date_created": "1434266418",
          "depends": [],
          "id": 4,
          "private": false,
          "status": "Open",
          "tags": [],
          "title": "This is a sample",
          "user": {
            "fullname": "Pagure",
            "name": "API"
          }
        }
      ]
    }

Project
-------

Project issue tags
~~~~~~~~~~~~~~~~~~

List the tags made on the project's issues.

::

    GET /api/0/<repo>/tags

::

    GET /api/0/fork/<username>/<repo>/tags

Parameters
^^^^^^^^^^

+---------------+----------+--------------------------------------------+
| Key           | Type     | Description                                |
+===============+==========+============================================+
| ``pattern``   | string   | Filters the starting letters of the tags   |
+---------------+----------+--------------------------------------------+

Sample response
^^^^^^^^^^^^^^^

::

    {
      "tags": ["tag1", "tag2"]
    }

Project git tags
~~~~~~~~~~~~~~~~

List the tags made on the project Git repository.

::

    GET /api/0/<repo>/git/tags

::

    GET /api/0/fork/<username>/<repo>/git/tags

Sample response
^^^^^^^^^^^^^^^

::

    {
      "tags": ["this-is-a-tag"]
    }

Create a new issue
~~~~~~~~~~~~~~~~~~

Open a new issue on a project.

::

    POST /api/0/<repo>/new_issue

::

    POST /api/0/fork/<username>/<repo>/new_issue

Input
^^^^^

+---------------+-----------+--------------------------------------------------------------+
| Key           | Type      | Description                                                  |
+===============+===========+==============================================================+
| ``title``     | string    | **Required**. The title of the issue                         |
+---------------+-----------+--------------------------------------------------------------+
| ``private``   | boolean   | Include this key if you want a private issue to be created   |
+---------------+-----------+--------------------------------------------------------------+
| ``content``   | string    | **Required**. The description of the issue                   |
+---------------+-----------+--------------------------------------------------------------+

Sample response
^^^^^^^^^^^^^^^

::

    {
      "message": "Issue created"
    }

List project's issues
~~~~~~~~~~~~~~~~~~~~~

List issues of a project.

::

    GET /api/0/<repo>/issues

::

    GET /api/0/fork/<username>/<repo>/issues

Parameters
^^^^^^^^^^

+----------------+----------+--------------------------------------------------------------------------------------------------------------------------------+
| Key            | Type     | Description                                                                                                                    |
+================+==========+================================================================================================================================+
| ``status``     | string   | Filters the status of issues. Default: ``Open``                                                                                |
+----------------+----------+--------------------------------------------------------------------------------------------------------------------------------+
| ``tags``       | string   | A list of tags you wish to filter. If you want to filter for issues not having a tag, add an exclamation mark in front of it   |
+----------------+----------+--------------------------------------------------------------------------------------------------------------------------------+
| ``assignee``   | string   | Filter the issues by assignee                                                                                                  |
+----------------+----------+--------------------------------------------------------------------------------------------------------------------------------+
| ``author``     | string   | Filter the issues by creator                                                                                                   |
+----------------+----------+--------------------------------------------------------------------------------------------------------------------------------+

Sample response
^^^^^^^^^^^^^^^

::

    {
      "args": {
        "assignee": null,
        "author": null,
        "status": "Closed",
        "tags": [
          "0.1"
        ]
      },
      "issues": [
        {
          "assignee": null,
          "blocks": [],
          "comments": [],
          "content": "asd",
          "date_created": "1427442217",
          "depends": [],
          "id": 4,
          "private": false,
          "status": "Fixed",
          "tags": [
            "0.1"
          ],
          "title": "bug",
          "user": {
            "fullname": "PY.C",
            "name": "pingou"
          }
        }
      ]
    }

Get information of a single issue
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information of a specific issue.

::

    GET /api/0/<repo>/issue/<issue id>

::

    GET /api/0/fork/<username>/<repo>/issue/<issue id>

Sample response
^^^^^^^^^^^^^^^

::

    {
      "assignee": None,
      "blocks": [],
      "comments": [],
      "content": "This issue needs attention",
      "date_created": "1431414800",
      "depends": [],
      "id": 1,
      "private": False,
      "status": "Open",
      "tags": [],
      "title": "test issue",
      "user": {
        "fullname": "PY C",
        "name": "pingou"
      }
    }

Comment on an issue
~~~~~~~~~~~~~~~~~~~

Add a comment to an issue.

::

    POST /api/0/<repo>/issue/<issue id>/comment

::

    POST /api/0/fork/<username>/<repo>/issue/<issue id>/comment

Input
^^^^^

+---------------+----------+-------------------------------------------------+
| Key           | Type     | Description                                     |
+===============+==========+=================================================+
| ``comment``   | string   | **Required**. The comment to add to the issue   |
+---------------+----------+-------------------------------------------------+

Sample response
^^^^^^^^^^^^^^^

::

    {
      "message": "Comment added"
    }

Change status of issue
~~~~~~~~~~~~~~~~~~~~~~

Change the status of an issue.

::

    POST /api/0/<repo>/issue/<issue id>/status

::

    POST /api/0/fork/<username>/<repo>/issue/<issue id>/status

Input
^^^^^

+--------------+----------+---------------------------------------------+
| Key          | Type     | Description                                 |
+==============+==========+=============================================+
| ``status``   | string   | **Required**. The new status of the issue   |
+--------------+----------+---------------------------------------------+

Sample response
^^^^^^^^^^^^^^^

::

    {
      "message": "Successfully edited issue #1"
    }

List project's pull requests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve pull requests of a project.

::

    GET /api/0/<repo>/pull-requests

::

    GET /api/0/fork/<username>/<repo>/pull-requests

Parameters
^^^^^^^^^^

+----------------+-----------+--------------------------------------------------------------------------------+
| Key            | Type      | Description                                                                    |
+================+===========+================================================================================+
| ``status``     | boolean   | Filter the status of pull requests. Default: ``True`` (opened pull requests)   |
+----------------+-----------+--------------------------------------------------------------------------------+
| ``assignee``   | string    | Filter the assignee of pull requests                                           |
+----------------+-----------+--------------------------------------------------------------------------------+
| ``author``     | string    | Filter the author of pull requests                                             |
+----------------+-----------+--------------------------------------------------------------------------------+

Sample response
^^^^^^^^^^^^^^^

::

    {
      "args": {
        "assignee": null,
        "author": null,
        "status": true
      },
      "requests": [
        {
          "assignee": null,
          "branch": "master",
          "branch_from": "master",
          "comments": [],
          "commit_start": null,
          "commit_stop": null,
          "date_created": "1431414800",
          "id": 1,
          "project": {
            "date_created": "1431414800",
            "description": "test project #1",
            "id": 1,
            "name": "test",
            "parent": null,
            "user": {
              "fullname": "PY C",
              "name": "pingou"
            }
          },
          "repo_from": {
            "date_created": "1431414800",
            "description": "test project #1",
            "id": 1,
            "name": "test",
            "parent": null,
            "user": {
              "fullname": "PY C",
              "name": "pingou"
            }
          },
          "status": true,
          "title": "test pull-request",
          "uid": "1431414800",
          "user": {
            "fullname": "PY C",
            "name": "pingou"
          }
        }
      ]
    }

Get information of a single pull request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information of a specific pull request.

::

    GET /api/0/<repo>/pull-request/<request id>

::

    GET /api/0/fork/<username>/<repo>/pull-request/<request id>

Sample response
^^^^^^^^^^^^^^^

::

    {
      "assignee": null,
      "branch": "master",
      "branch_from": "master",
      "comments": [],
      "commit_start": null,
      "commit_stop": null,
      "date_created": "1431414800",
      "id": 1,
      "project": {
        "date_created": "1431414800",
        "description": "test project #1",
        "id": 1,
        "name": "test",
        "parent": null,
        "user": {
          "fullname": "PY C",
          "name": "pingou"
        }
      },
      "repo_from": {
        "date_created": "1431414800",
        "description": "test project #1",
        "id": 1,
        "name": "test",
        "parent": null,
        "user": {
          "fullname": "PY C",
          "name": "pingou"
        }
      },
      "status": true,
      "title": "test pull-request",
      "uid": "1431414800",
      "user": {
        "fullname": "PY C",
        "name": "pingou"
      }
    }

Merge pull request
~~~~~~~~~~~~~~~~~~

Instruct Paugre to merge a pull request.

::

    POST /api/0/<repo>/pull-request/<request id>/merge

::

    POST /api/0/fork/<username>/<repo>/pull-request/<request id>/merge

Sample response
^^^^^^^^^^^^^^^

::

    {
      "message": "Changes merged!"
    }

Close pull request
~~~~~~~~~~~~~~~~~~

Instruct Pagure to close a pull request.

::

    POST /api/0/<repo>/pull-request/<request id>/close

::

    POST /api/0/fork/<username>/<repo>/pull-request/<request id>/close

Sample response
^^^^^^^^^^^^^^^

::

    {
      "message": "Pull-request closed!"
    }

Comment on pull request
~~~~~~~~~~~~~~~~~~~~~~~

Add comment to a pull request.

::

    POST /api/0/<repo>/pull-request/<request id>/comment

::

    POST /api/0/fork/<username>/<repo>/pull-request/<request id>/comment

Input
^^^^^

+----------------+----------+----------------------------------------------------------------------------+
| Key            | Type     | Description                                                                |
+================+==========+============================================================================+
| ``comment``    | string   | **Required**. The comment to add to the pull request                       |
+----------------+----------+----------------------------------------------------------------------------+
| ``commit``     | string   | The hash of the specific commit you wish to comment on                     |
+----------------+----------+----------------------------------------------------------------------------+
| ``filename``   | string   | The filename of the specific file you wish to comment on                   |
+----------------+----------+----------------------------------------------------------------------------+
| ``row``        | int      | Used in combination with filename to comment on a specific row of a file   |
+----------------+----------+----------------------------------------------------------------------------+

Sample response
^^^^^^^^^^^^^^^

::

    {
      "message": "Comment added"
    }

Flag pull request
~~~~~~~~~~~~~~~~~

Add or edit flags on a pull-request.

::

    POST /api/0/<repo>/pull-request/<request id>/flag

::

    POST /api/0/fork/<username>/<repo>/pull-request/<request id>/flag

Input
^^^^^

+----------------+----------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Key            | Type     | Description                                                                                                                                                                                                                                              |
+================+==========+==========================================================================================================================================================================================================================================================+
| ``username``   | string   | **Required**. The name of the application to be presented to users on the pull request page                                                                                                                                                              |
+----------------+----------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``percent``    | int      | **Required**. A percentage of completion compared to the goal. The percentage also determine the background color of the flag on the pull-request page                                                                                                   |
+----------------+----------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``comment``    | string   | **Required**. A short message summarizing the presented results                                                                                                                                                                                          |
+----------------+----------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``url``        | string   | **Required**. A URL to the result of this flag                                                                                                                                                                                                           |
+----------------+----------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``uid``        | string   | A unique identifier used to identify a flag on a pull-request. If the provided UID matches an existing one, then the API call will update the existing one rather than create a new one. Maximum Length: 32 characters. Default: an auto generated UID   |
+----------------+----------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``commit``     | string   | The hash of the commit you use                                                                                                                                                                                                                           |
+----------------+----------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Sample response
^^^^^^^^^^^^^^^

::

    {
      "message": "Flag added"
    }

::

    {
      "message": "Flag updated"
    }

Users
-----

List users
~~~~~~~~~~

Retrieve users that have logged into the Paugre instance.

::

    GET /api/0/users

Parameters
^^^^^^^^^^

+---------------+----------+-------------------------------------------------+
| Key           | Type     | Description                                     |
+===============+==========+=================================================+
| ``pattern``   | string   | Filters the starting letters of the usernames   |
+---------------+----------+-------------------------------------------------+

Sample response
^^^^^^^^^^^^^^^

::

    {
      "users": ["user1", "user2"]
    }

List groups
~~~~~~~~~~~

Retrieve groups on this Pagure instance.

::

    GET /api/0/groups

Parameters
^^^^^^^^^^

+---------------+----------+---------------------------------------------------+
| Key           | Type     | Description                                       |
+===============+==========+===================================================+
| ``pattern``   | string   | Filters the starting letters of the group names   |
+---------------+----------+---------------------------------------------------+

Sample response
^^^^^^^^^^^^^^^

::

    {
      "groups": ["group1", "group2"]
    }

Extras
------

API version
~~~~~~~~~~~

Get the current API version.

::

    GET /api/0/version

Sample response
^^^^^^^^^^^^^^^

::

    {
      "version": "1"
    }

Error codes
~~~~~~~~~~~

Get a dictionary of all error codes.

::

    GET /api/0/error_codes

Sample response
^^^^^^^^^^^^^^^

::

    {
      ENOCODE: 'Variable message describing the issue',
      ENOPROJECT: 'Project not found',
    }
