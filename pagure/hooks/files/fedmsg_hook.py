#!/usr/bin/env python

import getpass
import os
import subprocess as sp
import sys

from collections import defaultdict

import pygit2

import fedmsg
import fedmsg.config

abspath = os.path.abspath(os.environ['GIT_DIR'])

def read_output(cmd, input=None, keepends=False, **kw):
    if input:
        stdin = subprocess.PIPE
    else:
        stdin = None
    p = subprocess.Popen(
        cmd, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw
        )
    (out, err) = p.communicate(input)
    retcode = p.wait()
    if retcode:
        print 'ERROR: %s =-- %s' % (cmd, retcode)
    if not keepends:
        out = out.rstrip('\n\r')
    return out


def read_git_output(args, input=None, keepends=False, **kw):
    """Read the output of a Git command."""

    return read_output(['git'] + args, input=input, keepends=keepends, **kw)


def read_git_lines(args, keepends=False, **kw):
    """Return the lines output by Git command.

    Return as single lines, with newlines stripped off."""

    return read_git_output(args, keepends=True, **kw).splitlines(keepends)


def get_repo_name():
    ''' Return the name of the git repo based on its path.
    '''
    repo_name = '.'.join(abspath.split(os.path.sep)[-1].split('.')[:-1])
    return repo


def get_username():
    ''' Return the username of the git repo based on its path.
    '''
    username = None
    repo = os.path.abspath(os.path.join(abspath, '..'))
    if pagure.APP.config['FORK_FOLDER'] in repo:
        username = repo.split(pagure.APP.config['FORK_FOLDER'])[1]
    return username


def revs_between(head, base):
    """ Yield revisions between HEAD and BASE. """

    # pygit2 can't do a rev-list yet, so we have to shell out.. silly.
    cmd = '/usr/bin/git rev-list %s...%s' % (head.id, base.id)
    proc = sp.Popen(cmd.split(), stdout=sp.PIPE, stderr=sp.PIPE, cwd=abspath)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        raise IOError('git rev-list failed: %r, err: %r' % (stdout, stderr))

    for line in stdout.strip().split('\n'):
        yield line.strip()



repo = pygit2.Repository(abspath)

print "Emitting a message to the fedmsg bus."
config = fedmsg.config.load_config([], None)
config['active'] = True
config['endpoints']['relay_inbound'] = config['relay_inbound']
fedmsg.init(name='relay_inbound', cert_prefix='scm', **config)


def build_stats(commit):
    files = defaultdict(lambda: defaultdict(int))

    # Calculate diffs against all parent commits
    diffs = [repo.diff(parent, commit) for parent in commit.parents]
    # Unless this is the first commit, with no parents.
    diffs = diffs or [commit.tree.diff_to_tree(swap=True)]

    for diff in diffs:
        for patch in diff:
            path = patch.new_file_path
            files[path]['additions'] += patch.additions
            files[path]['deletions'] += patch.deletions
            files[path]['lines'] += patch.additions + patch.deletions

    total = defaultdict(int)
    for name, stats in files.items():
        total['additions'] += stats['additions']
        total['deletions'] += stats['deletions']
        total['lines'] += stats['lines']
        total['files'] += 1

    return files, total


seen = []

# Read in all the rev information git-receive-pack hands us.
lines = [line.split() for line in sys.stdin.readlines()]
for line in lines:
    base, head, branch = line
    branch = '/'.join(branch.split('/')[2:])

    try:
        head = repo.revparse_single(head)
    except KeyError:
        # This means they are deleting this branch.. and we don't have a fedmsg
        # for that (yet?).  It is disallowed by dist-git in Fedora anyways.
        continue

    try:
        base = repo.revparse_single(base)
        revs = revs_between(head, base)
    except KeyError:
        revs = [head.id]

    def _build_commit(rev):
        commit = repo.revparse_single(unicode(rev))

        # Tags are a little funny, and vary between versions of pygit2, so we'll
        # just ignore them as far as fedmsg is concerned.
        if isinstance(commit, pygit2.Tag):
            return None

        files, total = build_stats(commit)

        return dict(
            name=commit.author.name,
            email=commit.author.email,
            summary=commit.message.split('\n')[0],
            message=commit.message,
            stats=dict(
                files=files,
                total=total,
            ),
            rev=unicode(rev),
            path=abspath,
            username=get_username(),
            repo=get_repo_name(),
            branch=branch,
            agent=os.getlogin(),
        )

    commits = map(_build_commit, revs)

    print "* Publishing information for %i commits" % len(commits)
    for commit in reversed(commits):
        if commit is None:
            continue

        # Keep track of whether or not we have already published this commit on
        # another branch or not.  It is conceivable that someone could make a
        # commit to a number of branches, and push them all at the same time.
        # Make a note in the fedmsg payload so we can try to reduce spam at a
        # later stage.
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
