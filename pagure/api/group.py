# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Matt Prahl <mprahl@redhat.com>

"""

from __future__ import unicode_literals

import flask

import pagure
import pagure.exceptions
import pagure.lib
from pagure.api import API, APIERROR, api_method, api_login_optional
from pagure.utils import is_true


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
    extended = is_true(flask.request.args.get('extended', False))

    if pattern is not None and not pattern.endswith('*'):
        pattern += '*'

    groups = pagure.lib.search_groups(flask.g.session, pattern=pattern)

    if extended:
        groups = [
            {
                'name': grp.group_name,
                'description': grp.description
            }
            for grp in groups
        ]
    else:
        groups = [group.group_name for group in groups]

    return flask.jsonify(
        {
            'total_groups': len(groups),
            'groups': groups
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


    ::

        GET /api/0/group/some_group_name?projects=1&acl=commit

    Input
    ^^^^^

    +------------------+---------+--------------+-----------------------------+
    | Key              | Type    | Optionality  | Description                 |
    +==================+=========+==============+=============================+
    | ``group name``   | str     | Mandatory    | The name of the group to    |
    |                  |         |              | retrieve information about. |
    +------------------+---------+--------------+-----------------------------+
    | ``projects``     | bool    | Optional     | Specifies whether to include|
    |                  |         |              | projects in the data        |
    |                  |         |              | returned.                   |
    +------------------+---------+--------------+-----------------------------+
    | ``acl``          | str     | Optional     | Filter the project returned |
    |                  |         |              | (if any) to those where the |
    |                  |         |              | has the specified ACL level.|
    |                  |         |              | Can be any of: ``admin``,   |
    |                  |         |              | ``commit`` or ``ticket``.   |
    +------------------+---------+--------------+-----------------------------+


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
          "name": "some_group_name",
          "projects": [],
        }


    """  # noqa
    projects = flask.request.values.get(
        'projects', '').strip().lower() in ['1', 'true']
    acl = flask.request.values.get('acl', '').strip().lower() or None
    if acl == 'ticket':
        acl = ['admin', 'commit', 'ticket']
    elif acl == 'commit':
        acl = ['commit', 'admin']
    elif acl:
        acl = [acl]

    group = pagure.lib.search_groups(flask.g.session, group_name=group)
    if not group:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOGROUP)

    output = group.to_json(public=(not pagure.utils.api_authenticated()))
    if projects and not acl:
        output['projects'] = [
            project.to_json(public=True)
            for project in group.projects
        ]
    elif projects and acl:
        output['projects'] = [
            pg.project.to_json(public=True)
            for pg in group.projects_groups
            if pg.access in acl
        ]
    jsonout = flask.jsonify(output)
    jsonout.status_code = 200
    return jsonout
