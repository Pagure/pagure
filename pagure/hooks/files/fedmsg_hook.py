#!/usr/bin/env python

import getpass
import os
import subprocess
import sys

from collections import defaultdict

import fedmsg
import fedmsg.config


if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'

import pagure
import pagure.lib.git

abspath = os.path.abspath(os.environ['GIT_DIR'])


print "Emitting a message to the fedmsg bus."
config = fedmsg.config.load_config([], None)
config['active'] = True
config['endpoints']['relay_inbound'] = config['relay_inbound']
fedmsg.init(name='relay_inbound', **config)


seen = []

# Read in all the rev information git-receive-pack hands us.
for line in sys.stdin.readlines():
    (oldrev, newrev, refname) = line.strip().split(' ', 2)

    forced = False
    if set(newrev) == set(['0']):
        print "Deleting a reference/branch, so we won't run the "\
            "pagure hook"
        break
    elif set(oldrev) == set(['0']):
        print "New reference/branch"
        oldrev = '^%s' % oldrev
    elif pagure.lib.git.is_forced_push(oldrev, newrev, abspath):
        forced = True
        base = pagure.lib.git.get_base_revision(oldrev, newrev, abspath)
        if base:
            oldrev = base[0]

    revs = pagure.lib.git.get_revs_between(
        oldrev, newrev, abspath, forced=forced)
    project_name = pagure.lib.git.get_repo_name(abspath)
    username = pagure.lib.git.get_username(abspath)
    project = pagure.lib.get_project(pagure.SESSION, project_name, username)
    if not project:
        project = project_name

    pushers = set()
    for rev in revs:
        email = pagure.lib.git.get_pusher_email(rev, abspath)
        name = pagure.lib.git.get_pusher(rev, abspath)
        pusher = search_user(pagure.SESSION, email=email) or name
        pushers.add(pusher)

    if revs:
        revs.reverse()
        print "* Publishing information for %i commits" % len(revs)
        pagure.lib.notify.log(
            project=project,
            topic="git.receive",
            msg=dict(
                total_commits=len(revs),
                start_commit=revs[0],
                end_commit=revs[-1],
                branch=refname,
                forced=forced,
                users=list(pushers),
                agent=username,
                repo=project.to_json(public=True)
                if not isinstance(project, basestring) else project,
            ),
        )
