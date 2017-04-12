# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Matt Prahl <mprahl@redhat.com>

"""

import flask

import pagure
import pagure.exceptions
import pagure.lib
from pagure import SESSION
from pagure.api import API, api_method, APIERROR


@API.route('/group/<group>')
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
    """
    group = pagure.lib.search_groups(SESSION, group_name=group)
    if not group:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOGROUP)

    jsonout = flask.jsonify(group.to_json())
    jsonout.status_code = 200
    return jsonout
