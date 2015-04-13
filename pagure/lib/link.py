# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


import re
import os

import pagure.exceptions


FIXES = [
    re.compile('fixe?[sd]?:?\s*?#(\d+)', re.I),
    re.compile('.*\s*fixe?[sd]?:?\s*?#(\d+)', re.I),
    re.compile('fixe?[sd]?:?\s*?https?://.*/(\w+)/issue/(\d+)', re.I),
    re.compile('.*\s*?fixe?[sd]?:?\s*?https?://.*/(\w+)/issue/(\d+)', re.I),
]

RELATES = [
    re.compile('.*\s*relate[sd]?:?\s*?(?:to)?\s*?#(\d+)', re.I),
    re.compile('.*\s*relate[sd]?:?\s?#(\d+)', re.I),
    re.compile(
        '.*\s*relate[sd]?:?\s*?(?:to)?\s*?https?://.*/(\w+)/issue/(\d+)',
        re.I),
]


def get_relation(session, reponame, username, text, reftype='relates'):
    ''' For a given text, searches using regex if the text contains
    reference to another issue in this project or another one.

    Returns the list of issues referenced (possibly empty).

    By default it searches for references of type: `relates`, for example:
    ``this commits relates to #2``.
    Another reference type is: `fixes` refering to text including for
    example: ``this commits fixes #3``.


    '''

    repo = pagure.lib.get_project(session, reponame, user=username)
    if not repo:
        return []

    regex = RELATES
    if reftype == 'fixes':
        regex = FIXES

    issues = []
    for motif in regex:
        issueid = None
        project = None
        if motif.match(text):
            if len(motif.match(text).groups()) >= 2:
                issueid = motif.match(text).group(2)
                project = motif.match(text).group(1)
            else:
                issueid = motif.match(text).group(1)

        if issueid:
            issue = pagure.lib.search_issues(
                session, repo=repo, issueid=issueid)
            if issue is None or issue.project.name not in [project, repo.name]:
                continue

            if issue not in issues:
                issues.append(issue)

    return issues
