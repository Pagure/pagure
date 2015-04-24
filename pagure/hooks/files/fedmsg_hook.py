#!/usr/bin/env python

import getpass
import os
import subprocess
import sys

from collections import defaultdict

import fedmsg
import fedmsg.config

sys.path.insert(0, os.path.expanduser('~/repos/gitrepo/pagure'))

if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    print 'Using configuration file `/etc/pagure/pagure.cfg`'
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'

import pagure.lib.git

abspath = os.path.abspath(os.environ['GIT_DIR'])


def get_repo_name():
    ''' Return the name of the git repo based on its path.
    '''
    repo_name = '.'.join(abspath.split(os.path.sep)[-1].split('.')[:-1])
    return repo_name


def get_username():
    ''' Return the username of the git repo based on its path.
    '''
    username = None
    repo = os.path.abspath(os.path.join(abspath, '..'))
    if pagure.APP.config['FORK_FOLDER'] in repo:
        username = repo.split(pagure.APP.config['FORK_FOLDER'])[1]
    return username


print "Emitting a message to the fedmsg bus."
config = fedmsg.config.load_config([], None)
config['active'] = True
config['endpoints']['relay_inbound'] = config['relay_inbound']
fedmsg.init(name='relay_inbound', cert_prefix='scm', **config)


def build_stats(commit):
    cmd = ['diff-tree', '--numstat', '%s' % (commit)]
    output = pagure.lib.git.read_git_lines(cmd)

    files = {}
    total = {}
    for line in output[1:]:
        additions, deletions, path = line.split('\t')
        path = path.strip()
        files[path] = {
            'additions': int(additions.strip()),
            'deletions': int(deletions.strip()),
            'lines': int(additions.strip()) + int(deletions.strip()),
        }

    total = defaultdict(int)
    for name, stats in files.items():
        total['additions'] += stats['additions']
        total['deletions'] += stats['deletions']
        total['lines'] += stats['lines']
        total['files'] += 1

    return files, total


seen = []

# Read in all the rev information git-receive-pack hands us.
for line in sys.stdin.readlines():
    (oldrev, newrev, refname) = line.strip().split(' ', 2)
    revs = pagure.lib.git.get_revs_between(oldrev, newrev)

    def _build_commit(rev):
        files, total = build_stats(rev)

        summary = pagure.lib.git.read_git_lines(
            ['log', '-1', rev, "--pretty='%s'"])[0].replace("'", '')
        message = pagure.lib.git.read_git_lines(
            ['log', '-1', rev, "--pretty='%B'"])[0].replace("'", '')

        return dict(
            name=pagure.lib.git.get_pusher(rev),
            email=pagure.lib.git.get_pusher_email(rev),
            summary=summary,
            message=message,
            stats=dict(
                files=files,
                total=total,
            ),
            rev=unicode(rev),
            path=abspath,
            username=pagure.lib.git.get_username(),
            repo=pagure.lib.git.get_repo_name(),
            branch=refname,
            agent=os.getlogin(),
        )

    commits = map(_build_commit, revs)

    print "* Publishing information for %i commits" % len(commits)
    for commit in reversed(commits):
        if commit is None:
            continue

        # Keep track of whether or not we have already published this commit
        # on another branch or not.  It is conceivable that someone could
        # make a commit to a number of branches, and push them all at the
        # same time.
        # Make a note in the fedmsg payload so we can try to reduce spam at
        # a later stage.
        if commit['rev'] in seen:
            commit['seen'] = True
        else:
            commit['seen'] = False
            seen.append(commit['rev'])

        fedmsg.publish(
            topic="receive",
            msg=dict(commit=commit),
            modname="git",
        )
