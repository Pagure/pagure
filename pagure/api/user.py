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


def _get_user(username):
    """ Check user is valid or not
    """
    try:
        return pagure.lib.get_user(SESSION, username)
    except pagure.exceptions.PagureException:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOUSER)


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
              "custom_keys": [],
              "description": "",
              "parent": null,
              "settings": {
                "issues_default_to_private": false,
                "Minimum_score_to_merge_pull-request": -1,
                "Web-hooks": None,
                "fedmsg_notifications": true,
                "always_merge": false,
                "project_documentation": true,
                "Enforce_signed-off_commits_in_pull-request": false,
                "pull_requests": true,
                "Only_assignee_can_merge_pull-request": false,
                "issue_tracker": true
              },
              "tags": [],
              "namespace": None,
              "priorities": {},
              "close_status": [
                "Invalid",
                "Insufficient data",
                "Fixed",
                "Duplicated"
              ],
              "milestones": {},
              "user": {
                "fullname": "ralph",
                "name": "ralph"
              },
              "date_created": "1426595173",
              "id": 5,
              "name": "pagure"
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

    user = _get_user(username=username)

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
    |               |          |              |   from iso format to unix  |
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

    user = _get_user(username=username)

    stats = pagure.lib.get_yearly_stats_user(
        SESSION,
        user,
        datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
    )

    def format_date(d):
        if date_format == 'timestamp':
            d = d.strftime('%s')
        else:
            d = d.isoformat()
        return d

    stats = {format_date(d[0]): d[1] for d in stats}

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

        GET /api/0/user/ralph/activity/2016-01-02?grouped=true


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
    | ``grouped``   | boolean  | Optional     | | Whether or not to group  |
    |               |          |              |   the commits              |
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

    """  # noqa
    grouped = str(flask.request.args.get('grouped')).lower() in ['1', 'true']

    try:
        date = arrow.get(date)
        date = date.strftime('%Y-%m-%d')
    except arrow.parser.ParserError as err:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(err))

    user = _get_user(username=username)

    activities = pagure.lib.get_user_activity_day(SESSION, user, date)
    js_act = []
    if grouped:
        commits = collections.defaultdict(list)
        acts = []
        for activity in activities:
            if activity.log_type == 'committed':
                commits[activity.project.fullname].append(activity)
            else:
                acts.append(activity)
        for project in commits:
            if len(commits[project]) == 1:
                tmp = dict(
                    description_mk=pagure.lib.text2markdown(
                        str(commits[project][0]))
                )
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

    for act in activities:
        activity = act.to_json(public=True)
        activity['description_mk'] = pagure.lib.text2markdown(str(act))
        js_act.append(activity)

    jsonout = flask.jsonify(
        dict(
            activities=js_act,
            date=date,
        )
    )
    return jsonout


@API.route('/user/<username>/requests/filed')
@api_method
def api_view_user_requests_filed(username):
    """
    Pull requests that were filed by a user over all projects
    -------------------
    Use this endpoint to retrieve a list of open pull requests a user has filed
    over the entire pagure instance.

    ::

        GET /api/0/user/<username>/requests/filed

    ::

        GET /api/0/user/dudemcpants/requests/filed

    Parameters
    ^^^^^^^^^^

    +---------------+----------+--------------+----------------------------+
    | Key           | Type     | Optionality  | Description                |
    +===============+==========+==============+============================+
    | ``username``  | string   | Mandatory    | | The username of the user |
    |               |          |              |   whose activity you are   |
    |               |          |              |   interested in.           |
    +---------------+----------+--------------+----------------------------+
    | ``status``    | string   | Optional     | | Filter the status of     |
    |               |          |              |   pull requests. Default:  |
    |               |          |              |   ``Open`` (open pull      |
    |               |          |              |   requests), can be        |
    |               |          |              |   ``Closed`` for closed    |
    |               |          |              |   requests, ``Merged``     |
    |               |          |              |   for merged requests, or  |
    |               |          |              |   ``Open`` for open        |
    |               |          |              |   requests.                |
    |               |          |              |   ``All`` returns closed,  |
    |               |          |              |   merged and open requests.|
    +---------------+----------+--------------+----------------------------+


    Sample response
    ^^^^^^^^^^^^^^^

    ::
    {
    "args": {
        "status": "open",
        "username": "dudemcpants"
    },
    "requests": [
        {
        "assignee": null,
        "branch": "master",
        "branch_from": "master",
        "closed_at": null,
        "closed_by": null,
        "comments": [],
        "commit_start": "3973fae98fc485783ca14f5c3612d85832185065",
        "commit_stop": "3973fae98fc485783ca14f5c3612d85832185065",
        "date_created": "1510227832",
        "id": 2,
        "initial_comment": null,
        "last_updated": "1510227833",
        "project": {
            "access_groups": {
            "admin": [],
            "commit": [],
            "ticket": []
            },
            "access_users": {
            "admin": [],
            "commit": [],
            "owner": [
                "ryanlerch"
            ],
            "ticket": []
            },
            "close_status": [],
            "custom_keys": [],
            "date_created": "1510227638",
            "date_modified": "1510227638",
            "description": "this is a quick project",
            "fullname": "aquickproject",
            "id": 1,
            "milestones": {},
            "name": "aquickproject",
            "namespace": null,
            "parent": null,
            "priorities": {},
            "tags": [],
            "url_path": "aquickproject",
            "user": {
            "fullname": "ryanlerch",
            "name": "ryanlerch"
            }
        },
        "remote_git": null,
        "repo_from": {
            "access_groups": {
            "admin": [],
            "commit": [],
            "ticket": []
            },
            "access_users": {
            "admin": [],
            "commit": [],
            "owner": [
                "dudemcpants"
            ],
            "ticket": []
            },
            "close_status": [],
            "custom_keys": [],
            "date_created": "1510227729",
            "date_modified": "1510227729",
            "description": "this is a quick project",
            "fullname": "forks/dudemcpants/aquickproject",
            "id": 2,
            "milestones": {},
            "name": "aquickproject",
            "namespace": null,
            "parent": {
            "access_groups": {
                "admin": [],
                "commit": [],
                "ticket": []
            },
            "access_users": {
                "admin": [],
                "commit": [],
                "owner": [
                "ryanlerch"
                ],
                "ticket": []
            },
            "close_status": [],
            "custom_keys": [],
            "date_created": "1510227638",
            "date_modified": "1510227638",
            "description": "this is a quick project",
            "fullname": "aquickproject",
            "id": 1,
            "milestones": {},
            "name": "aquickproject",
            "namespace": null,
            "parent": null,
            "priorities": {},
            "tags": [],
            "url_path": "aquickproject",
            "user": {
                "fullname": "ryanlerch",
                "name": "ryanlerch"
            }
            },
            "priorities": {},
            "tags": [],
            "url_path": "fork/dudemcpants/aquickproject",
            "user": {
            "fullname": "Dude McPants",
            "name": "dudemcpants"
            }
        },
        "status": "Open",
        "title": "Update README.md",
        "uid": "819e0b1c449e414fa291c914f28d73ec",
        "updated_on": "1510227832",
        "user": {
            "fullname": "Dude McPants",
            "name": "dudemcpants"
        }
        }
    ],
    "total_requests": 1
    }

    """
    status = flask.request.args.get('status', 'open')

    pullrequests = pagure.lib.get_pull_request_of_user(
        SESSION,
        username=username
    )

    pullrequestslist = []

    for pr in pullrequests:
        if pr.user.username == username:
            if str(status).lower() == 'all':
                pullrequestslist.append(pr.to_json(public=True, api=True))
            elif str(status).lower() == 'open' and pr.status == 'Open':
                pullrequestslist.append(pr.to_json(public=True, api=True))
            elif str(status).lower() == 'closed' and pr.status == 'Closed':
                pullrequestslist.append(pr.to_json(public=True, api=True))
            elif str(status).lower() == 'merged' and pr.status == 'Merged':
                pullrequestslist.append(pr.to_json(public=True, api=True))

    return flask.jsonify({
        'total_requests': len(pullrequestslist),
        'requests': pullrequestslist,
        'args': {
            'username': username,
            'status': status,
        }
    })


@API.route('/user/<username>/requests/actionable')
@api_method
def api_view_user_requests_actionable(username):
    """
    Pull requests that are actionable by a user over all projects
    -------------------
    Use this endpoint to retrieve a list of open pull requests a user is able
    to action (e.g. merge) over the entire pagure instance.

    ::

        GET /api/0/user/<username>/requests/actionable

    ::

        GET /api/0/user/dudemcpants/requests/actionable

    Parameters
    ^^^^^^^^^^

    +---------------+----------+--------------+----------------------------+
    | Key           | Type     | Optionality  | Description                |
    +===============+==========+==============+============================+
    | ``username``  | string   | Mandatory    | | The username of the user |
    |               |          |              |   whose activity you are   |
    |               |          |              |   interested in.           |
    +---------------+----------+--------------+----------------------------+
    | ``status``    | string   | Optional     | | Filter the status of     |
    |               |          |              |   pull requests. Default:  |
    |               |          |              |   ``Open`` (open pull      |
    |               |          |              |   requests), can be        |
    |               |          |              |   ``Closed`` for closed    |
    |               |          |              |   requests, ``Merged``     |
    |               |          |              |   for merged requests, or  |
    |               |          |              |   ``Open`` for open        |
    |               |          |              |   requests.                |
    |               |          |              |   ``All`` returns closed,  |
    |               |          |              |   merged and open requests.|
    +---------------+----------+--------------+----------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::
    {
    "args": {
        "status": "open",
        "username": "ryanlerch"
    },
    "requests": [
        {
        "assignee": null,
        "branch": "master",
        "branch_from": "master",
        "closed_at": null,
        "closed_by": null,
        "comments": [],
        "commit_start": "3973fae98fc485783ca14f5c3612d85832185065",
        "commit_stop": "3973fae98fc485783ca14f5c3612d85832185065",
        "date_created": "1510227832",
        "id": 2,
        "initial_comment": null,
        "last_updated": "1510227833",
        "project": {
            "access_groups": {
            "admin": [],
            "commit": [],
            "ticket": []
            },
            "access_users": {
            "admin": [],
            "commit": [],
            "owner": [
                "ryanlerch"
            ],
            "ticket": []
            },
            "close_status": [],
            "custom_keys": [],
            "date_created": "1510227638",
            "date_modified": "1510227638",
            "description": "this is a quick project",
            "fullname": "aquickproject",
            "id": 1,
            "milestones": {},
            "name": "aquickproject",
            "namespace": null,
            "parent": null,
            "priorities": {},
            "tags": [],
            "url_path": "aquickproject",
            "user": {
            "fullname": "ryanlerch",
            "name": "ryanlerch"
            }
        },
        "remote_git": null,
        "repo_from": {
            "access_groups": {
            "admin": [],
            "commit": [],
            "ticket": []
            },
            "access_users": {
            "admin": [],
            "commit": [],
            "owner": [
                "dudemcpants"
            ],
            "ticket": []
            },
            "close_status": [],
            "custom_keys": [],
            "date_created": "1510227729",
            "date_modified": "1510227729",
            "description": "this is a quick project",
            "fullname": "forks/dudemcpants/aquickproject",
            "id": 2,
            "milestones": {},
            "name": "aquickproject",
            "namespace": null,
            "parent": {
            "access_groups": {
                "admin": [],
                "commit": [],
                "ticket": []
            },
            "access_users": {
                "admin": [],
                "commit": [],
                "owner": [
                "ryanlerch"
                ],
                "ticket": []
            },
            "close_status": [],
            "custom_keys": [],
            "date_created": "1510227638",
            "date_modified": "1510227638",
            "description": "this is a quick project",
            "fullname": "aquickproject",
            "id": 1,
            "milestones": {},
            "name": "aquickproject",
            "namespace": null,
            "parent": null,
            "priorities": {},
            "tags": [],
            "url_path": "aquickproject",
            "user": {
                "fullname": "ryanlerch",
                "name": "ryanlerch"
            }
            },
            "priorities": {},
            "tags": [],
            "url_path": "fork/dudemcpants/aquickproject",
            "user": {
            "fullname": "Dude McPants",
            "name": "dudemcpants"
            }
        },
        "status": "Open",
        "title": "Update README.md",
        "uid": "819e0b1c449e414fa291c914f28d73ec",
        "updated_on": "1510227832",
        "user": {
            "fullname": "Dude McPants",
            "name": "dudemcpants"
        }
        }
    ],
    "total_requests": 1
    }

    """
    status = flask.request.args.get('status', 'open')

    pullrequests = pagure.lib.get_pull_request_of_user(
        SESSION,
        username=username
    )

    pullrequestslist = []

    for pr in pullrequests:
        if pr.user.username != username:
            if str(status).lower() == 'all':
                pullrequestslist.append(pr.to_json(public=True, api=True))
            elif str(status).lower() == 'open' and pr.status == 'Open':
                pullrequestslist.append(pr.to_json(public=True, api=True))
            elif str(status).lower() == 'closed' and pr.status == 'Closed':
                pullrequestslist.append(pr.to_json(public=True, api=True))
            elif str(status).lower() == 'merged' and pr.status == 'Merged':
                pullrequestslist.append(pr.to_json(public=True, api=True))

    return flask.jsonify({
        'total_requests': len(pullrequestslist),
        'requests': pullrequestslist,
        'args': {
            'username': username,
            'status': status,
        }
    })
