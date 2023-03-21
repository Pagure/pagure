Authentication
~~~~~~~~~~~~~~

To access some endpoints, you need to log in to Pagure using an API token. You
can generate one in the project setting page.

When sending HTTP request, include an ``Authorization`` field in the header
with value ``token $your-api-token``, where ``$your-api-token`` is the
API token generated in the project setting page.

So the result should look like:

::

    Authorization: token abcdefghijklmnop

Where ``abcdefghijklmnop`` is the API token provided by pagure.

Anyone with the token can access the APIs on your behalf, so please be
sure to keep it private and safe.

Request Encoding
~~~~~~~~~~~~~~~~

The payload of POST and GET requests is encoded as

``application/x-www-form-urlencoded``.


This is an example URL of a GET request:

``https://pagure.io/api/0/test/issues?status=Open&tags=Pagure&tags=Enhancement``


Return Encoding
~~~~~~~~~~~~~~~

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
