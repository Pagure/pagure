# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-many-arguments

from __future__ import unicode_literals

import re
import pagure
import pagure.exceptions


FIXES = [
    re.compile(r'(?:.*\s+)?fixe?[sd]?:?\s*?#(\d+)', re.I),
    re.compile(
        r'(?:.*\s+)?fixe?[sd]?:?\s*?https?://.*/([a-zA-z0-9_][a-zA-Z0-9-_]*)'
        '/(?:issue|pull-request)/(\d+)', re.I),
    re.compile(r'(?:.*\s+)?merge?[sd]?:?\s*?#(\d+)', re.I),
    re.compile(
        r'(?:.*\s+)?merge?[sd]?:?\s*?https?://.*/([a-zA-z0-9_][a-zA-Z0-9-_]*)'
        '/(?:issue|pull-request)/(\d+)', re.I),
    re.compile(r'(?:.*\s+)?close?[sd]?:?\s*?#(\d+)', re.I),
    re.compile(
        r'(?:.*\s+)?close?[sd]?:?\s*?https?://.*/([a-zA-z0-9_][a-zA-Z0-9-_]*)'
        '/(?:issue|pull-request)/(\d+)', re.I),
]

RELATES = [
    re.compile(r'(?:.*\s+)?relate[sd]?:?\s*?(?:to)?\s*?#(\d+)', re.I),
    re.compile(r'(?:.*\s+)?relate[sd]?:?\s?#(\d+)', re.I),
    re.compile(
        r'(?:.*\s+)?relate[sd]?:?\s*?(?:to)?\s*?'
        'https?://.*/(\w+)/issue/(\d+)', re.I),
]


def get_relation(session, reponame, username, namespace, text,
                 reftype='relates', include_prs=False):
    ''' For a given text, searches using regex if the text contains
    reference to another issue in this project or another one.

    Returns the list of issues referenced (possibly empty).
    If include_prs=True, it may also contain pull requests (may still
    be empty).

    By default it searches for references of type: `relates`, for example:
    ``this commits relates to #2``.
    Another reference type is: `fixes` refering to text including for
    example: ``this commits fixes #3``.


    '''

    repo = pagure.lib.get_authorized_project(
        session, reponame, user=username, namespace=namespace)
    if not repo:
        return []

    regex = RELATES
    if reftype == 'fixes':
        regex = FIXES

    relations = []
    for motif in regex:
        relid = None
        project = None
        if motif.match(text):
            if len(motif.match(text).groups()) >= 2:
                relid = motif.match(text).group(2)
                project = motif.match(text).group(1)
            else:
                relid = motif.match(text).group(1)

        if relid:
            relation = pagure.lib.search_issues(
                session, repo=repo, issueid=relid)

            if relation is None and include_prs:
                relation = pagure.lib.search_pull_requests(
                    session, project_id=repo.id, requestid=relid)

            if relation is None or relation.project.name not in [project,
                                                                 repo.name]:
                continue

            if relation not in relations:
                relations.append(relation)

    return relations
