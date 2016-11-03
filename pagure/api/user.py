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

        GET /api/0/user/ralph/activity/stats?format=timestamp

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
    |               |          |              |   from iso formato to unix |
    |               |          |              |   timestamp                |
    |               |          |              |   Can be: `timestamp`      |
    |               |          |              |   or `isoformat`           |
    +---------------+----------+--------------+----------------------------+


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "2015-11-04": 9,
          "2015-11-06": 3,
          "2015-11-09": 6,
          "2015-11-13": 4,
          "2015-11-15": 3,
          "2015-11-18": 15,
          "2015-11-19": 3,
          "2015-11-20": 15,
          "2015-11-26": 18,
          "2015-11-30": 116,
          "2015-12-02": 12,
          "2015-12-03": 2
        }

    or::

        {
          "1446591600": 9,
          "1446764400": 3,
          "1447023600": 6,
          "1447369200": 4,
          "1447542000": 3,
          "1447801200": 15,
          "1447887600": 3,
          "1447974000": 15,
          "1448492400": 18,
          "1448838000": 116,
          "1449010800": 12,
          "1449097200": 2
        }

    """
    date_format = flask.request.args.get('format', 'isoformat')

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
            d = d.isoformat()
        return d

    stats = [
        (format_date(d[0]), d[1])
        for d in stats
    ]

    jsonout = flask.jsonify(stats)
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
    | ``date``      | string   | Mandatory    | | The date of interest,    |
    |               |          |              |   best provided in ISO     |
    |               |          |              |   format: YYYY-MM-DD       |
    +---------------+----------+--------------+----------------------------+
    | ``grouped``   | boolean  | Optional     | | Whether to group the     |
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
            if activity.log_type == 'commit':
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
    return jsonout
