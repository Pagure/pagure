# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Matt Prahl <mprahl@redhat.com>

"""

import flask

import pagure
import pagure.exceptions
import pagure.lib
from pagure import SESSION
from pagure.api import API, APIERROR, api_method, api_login_optional


@API.route('/groups/')
@API.route('/groups')
def api_groups():
    '''
    List groups
    -----------
    Retrieve groups on this Pagure instance.
    This can then be used as input for autocompletion in some forms/fields.

    ::

        GET /api/0/groups

    Parameters
    ^^^^^^^^^^

    +---------------+----------+---------------+--------------------------+
    | Key           | Type     | Optionality   | Description              |
    +===============+==========+===============+==========================+
    | ``pattern``   | string   | Optional      | | Filters the starting   |
    |               |          |               |   letters of the group   |
    |               |          |               |   names                  |
    +---------------+----------+---------------+--------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "total_groups": 2,
          "groups": ["group1", "group2"]
        }

    '''
    pattern = flask.request.args.get('pattern', None)
    if pattern is not None and not pattern.endswith('*'):
        pattern += '*'

    groups = pagure.lib.search_groups(SESSION, pattern=pattern)

    return flask.jsonify(
        {
            'total_groups': len(groups),
            'groups': [group.group_name for group in groups]
        }
    )


@API.route('/group/<group>')
@api_login_optional()
@api_method
def api_view_group(group):
    """
    Group information
    -----------------
    Use this endpoint to retrieve information about a specific group.

    ::

        GET /api/0/group/<group>

    ::

        GET /api/0/group/some_group_name

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "creator": {
            "default_email": "user1@example.com",
            "emails": [
              "user1@example.com"
            ],
            "fullname": "User1",
            "name": "user1"
          },
          "date_created": "1492011511",
          "description": "Some Group",
          "display_name": "Some Group",
          "group_type": "user",
          "members": [
            "user1",
            "user2"
          ],
          "name": "some_group_name"
        }
    """  # noqa
    group = pagure.lib.search_groups(SESSION, group_name=group)
    if not group:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOGROUP)

    jsonout = flask.jsonify(group.to_json(
        public=(not pagure.api_authenticated())))
    jsonout.status_code = 200
    return jsonout
