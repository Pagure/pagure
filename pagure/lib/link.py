# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-many-arguments

from __future__ import unicode_literals, absolute_import

import re
import pagure.lib.query
import pagure.exceptions
import pagure.utils
from pagure.config import config as pagure_config


FIXES = [
    re.compile(r"(?:.*\s+)?{0}?[sd]?:?\s*?#(\d+)".format(kw), re.I)
    for kw in ["fixe", "merge", "close"]
]
FIXES += [
    re.compile(
        r"(?:.*\s+)?{0}?[sd]?:?\s*?{1}"
        r"(/.*?/(?:issue|pull-request)/\d+)".format(
            kw, pagure_config["APP_URL"].rstrip("/")
        ),
        re.I,
    )
    for kw in ["fixe", "merge", "close"]
]


RELATES = [
    re.compile(r"(?:.*\s+)?{0}?[sd]?:?\s*?(?:to)?\s*?#(\d+)".format(kw), re.I)
    for kw in ["relate"]
]
RELATES += [
    re.compile(
        r"(?:.*\s+)?{0}?[sd]?:?\s*?(?:to)?\s*?{1}(/.*?/issue/\d+)".format(
            kw, pagure_config["APP_URL"].rstrip("/")
        ),
        re.I,
    )
    for kw in ["relate"]
]


def get_relation(
    session,
    reponame,
    username,
    namespace,
    text,
    reftype="relates",
    include_prs=False,
):
    """ For a given text, searches using regex if the text contains
    reference to another issue in this project or another one.

    Returns the list of issues referenced (possibly empty).
    If include_prs=True, it may also contain pull requests (may still
    be empty).

    By default it searches for references of type: `relates`, for example:
    ``this commits relates to #2``.
    Another reference type is: `fixes` refering to text including for
    example: ``this commits fixes #3``.


    """

    repo = pagure.lib.query.get_authorized_project(
        session, reponame, user=username, namespace=namespace
    )
    if not repo:
        return []

    regex = RELATES
    if reftype == "fixes":
        regex = FIXES

    relations = []
    for motif in regex:
        relid = None
        project = None
        got_match = motif.match(text)
        if got_match:
            relid = got_match.group(1)
            if not relid.isdigit():
                (
                    username,
                    namespace,
                    reponame,
                    objtype,
                    relid,
                ) = pagure.utils.parse_path(relid)
                repo = pagure.lib.query.get_authorized_project(
                    session, reponame, user=username, namespace=namespace
                )
                if not repo:
                    continue

        if relid:
            relation = pagure.lib.query.search_issues(
                session, repo=repo, issueid=relid
            )

            if relation is None and include_prs:
                relation = pagure.lib.query.search_pull_requests(
                    session, project_id=repo.id, requestid=relid
                )

            if relation is None or relation.project.name not in [
                project,
                repo.name,
            ]:
                continue

            if relation not in relations:
                relations.append(relation)

    return relations
