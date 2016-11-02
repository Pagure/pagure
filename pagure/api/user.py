# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import collections
import datetime

import arrow
import flask

import pagure
import pagure.exceptions
import pagure.lib
from pagure import SESSION
from pagure.api import API, api_method, APIERROR


@API.route('/user/<username>')
@api_method
def api_view_user(username):
    """
    User information
    ----------------
    Use this endpoint to retrieve information about a specific user.

    ::

        GET /api/0/user/<username>

    ::

        GET /api/0/user/ralph

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "forks": [],
          "repos": [
            {
              "date_created": "1426595173",
              "description": "",
              "id": 5,
              "name": "pagure",
              "parent": null,
              "settings": {
                "Minimum_score_to_merge_pull-request": -1,
                "Only_assignee_can_merge_pull-request": false,
                "Web-hooks": null,
                "issue_tracker": true,
                "project_documentation": true,
                "pull_requests": true
              },
              "user": {
                "fullname": "ralph",
                "name": "ralph"
              }
            }
          ],
          "user": {
            "fullname": "ralph",
            "name": "ralph"
          }
        }

    """
    httpcode = 200
    output = {}

    user = pagure.lib.search_user(SESSION, username=username)
    if not user:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOUSER)

    repopage = flask.request.args.get('repopage', 1)
    try:
        repopage = int(repopage)
    except ValueError:
        repopage = 1

    forkpage = flask.request.args.get('forkpage', 1)
    try:
        forkpage = int(forkpage)
    except ValueError:
        forkpage = 1

    repos = pagure.lib.search_projects(
        SESSION,
        username=username,
        fork=False)

    forks = pagure.lib.search_projects(
        SESSION,
        username=username,
        fork=True)

    output['user'] = user.to_json(public=True)
    output['repos'] = [repo.to_json(public=True) for repo in repos]
    output['forks'] = [repo.to_json(public=True) for repo in forks]

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout



@API.route('/user/<username>/activity/stats')
@api_method
def api_view_user_activity_stats(username):
    """
    User activity stats
    -------------------
    Use this endpoint to retrieve activity stats about a specific user over
    the last year.

    ::

        GET /api/0/user/<username>/activity/stats

    ::

        GET /api/0/user/ralph/activity/stats

    Parameters
    ^^^^^^^^^^

    +---------------+----------+--------------+----------------------------+
    | Key           | Type     | Optionality  | Description                |
    +===============+==========+==============+============================+
    | ``username``  | string   | Mandatory    | | The username of the user |
    |               |          |              |   whose activity you are   |
    |               |          |              |   interested in.           |
    +---------------+----------+--------------+----------------------------+
    | ``format``    | string   | Optional     | | Allows changing the      |
    |               |          |              |   of the date/time returned|
    |               |          |              |   can be: `timestamp`      |
    +---------------+----------+--------------+----------------------------+


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "2016-05-04 00:00:00": 5,
          "2016-05-09 00:00:00": 4,
          "2016-05-28 00:00:00": 1,
          "2016-06-27 00:00:00": 4,
          "2016-08-06 00:00:00": 2,
          "2016-08-08 00:00:00": 5,
          "2016-08-09 00:00:00": 41,
          "2016-08-12 00:00:00": 36,
          "2016-08-30 00:00:00": 1,
          "2016-09-12 00:00:00": 1,
          "2016-09-13 00:00:00": 1,
          "2016-09-18 00:00:00": 3,
          "2016-09-30 00:00:00": 2,
          "2016-10-03 00:00:00": 6,
          "2016-10-04 00:00:00": 7,
          "2016-10-06 00:00:00": 1,
          "2016-10-13 00:00:00": 11,
          "2016-10-17 00:00:00": 1,
          "2016-10-20 00:00:00": 5
        }

    or::

        {
          "1462312800": 5,
          "1462744800": 4,
          "1464386400": 1,
          "1466978400": 4,
          "1470434400": 2,
          "1470607200": 5,
          "1470693600": 41,
          "1470952800": 36,
          "1472508000": 1,
          "1473631200": 1,
          "1473717600": 1,
          "1474149600": 3,
          "1475186400": 2,
          "1475445600": 6,
          "1475532000": 7,
          "1475704800": 1,
          "1476309600": 11,
          "1476655200": 1,
          "1476914400": 5
        }

    """
    httpcode = 200

    date_format = flask.request.args.get('format')

    user = pagure.lib.search_user(SESSION, username=username)
    if not user:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOUSER)

    stats = pagure.lib.get_yearly_stats_user(
        SESSION, user, datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
    )
    def format_date(d):
        if date_format == 'timestamp':
            d = d.strftime('%s')
        else:
            d = d.strftime('%Y-%m-%d %H:%M:%S')
        return d
    stats = [
        (format_date(d[0]), d[1])
        for d in stats
    ]

    jsonout = flask.jsonify(stats)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/user/<username>/activity/<date>')
@api_method
def api_view_user_activity_date(username, date):
    """
    User activity on a specific date
    --------------------------------
    Use this endpoint to retrieve activity information about a specific user
    on the specified date.

    ::

        GET /api/0/user/<username>/activity/<date>

    ::

        GET /api/0/user/ralph/activity/2016-01-02

    Parameters
    ^^^^^^^^^^

    +---------------+----------+--------------+----------------------------+
    | Key           | Type     | Optionality  | Description                |
    +===============+==========+==============+============================+
    | ``username``  | string   | Mandatory    | | The username of the user |
    |               |          |              |   whose activity you are   |
    |               |          |              |   interested in.           |
    +---------------+----------+--------------+----------------------------+
    | ``date``      | string   | Mandatory    | | The date of interest     |
    +---------------+----------+--------------+----------------------------+
    | ``grouped``   | string   | Optional     | | Whether to group the     |
    |               |          |              |   commits or not           |
    +---------------+----------+--------------+----------------------------+


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "activities": [
            {
              "date": "2016-02-24",
              "date_created": "1456305852",
              "description": "pingou created PR test#44",
              "description_mk": "<p>pingou created PR <a href=\"/test/pull-request/44\" title=\"Update test_foo\">test#44</a></p>",
              "id": 4067,
              "user": {
                "fullname": "Pierre-YvesC",
                "name": "pingou"
              }
            },
            {
              "date": "2016-02-24",
              "date_created": "1456305887",
              "description": "pingou commented on PR test#44",
              "description_mk": "<p>pingou commented on PR <a href=\"/test/pull-request/44\" title=\"Update test_foo\">test#44</a></p>",
              "id": 4112,
              "user": {
                "fullname": "Pierre-YvesC",
                "name": "pingou"
              }
            }
          ]
        }

    """
    httpcode = 200

    grouped = str(flask.request.args.get('grouped')).lower() in ['1', 'true']

    try:
        date = arrow.get(date)
        date = date.strftime('%Y-%m-%d')
    except arrow.ParserError as err:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(err))

    user = pagure.lib.search_user(SESSION, username=username)
    if not user:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOUSER)

    activities = pagure.lib.get_user_activity_day(SESSION, user, date)
    js_act = []
    if grouped:
        commits = collections.defaultdict(list)
        acts = []
        for activity in activities:
            if activity.type_ == 'commit':
                commits[activity.project.fullname].append(activity)
            else:
                acts.append(activity)
        for project in commits:
            if len(commits[project]) == 1:
                tmp = commits[project]
            else:
                tmp = dict(
                    description_mk=pagure.lib.text2markdown(
                        '@%s pushed %s commits to %s' % (
                            username, len(commits[project]), project
                        )
                    )
                )
            js_act.append(tmp)
        activities = acts
    for activity in activities:
        activity = activity.to_json(public=True)
        activity['description_mk'] = pagure.lib.text2markdown(
            activity['description']
        )
        js_act.append(activity)

    jsonout = flask.jsonify(
        dict(activities=js_act)
    )
    jsonout.status_code = httpcode
    return jsonout
