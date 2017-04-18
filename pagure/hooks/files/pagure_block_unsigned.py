#! /usr/bin/env python2


"""Pagure specific hook to block commit not having a 'Signed-off-by'
statement.
"""

import os
import sys


if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure  # noqa: E402
import pagure.exceptions  # noqa: E402
import pagure.lib.link  # noqa: E402
import pagure.ui.plugins  # noqa: E402


abspath = os.path.abspath(os.environ['GIT_DIR'])


def run_as_pre_receive_hook():

    for line in sys.stdin:
        if pagure.APP.config.get('HOOK_DEBUG', False):
            print line
        (oldrev, newrev, refname) = line.strip().split(' ', 2)

        if pagure.APP.config.get('HOOK_DEBUG', False):
            print '  -- Old rev'
            print oldrev
            print '  -- New rev'
            print newrev
            print '  -- Ref name'
            print refname

        if set(newrev) == set(['0']):
            print "Deleting a reference/branch, so we won't run the "\
                "hook to block unsigned commits"
            return

        commits = pagure.lib.git.get_revs_between(
            oldrev, newrev, abspath, refname)
        for commit in commits:
            if pagure.APP.config.get('HOOK_DEBUG', False):
                print 'Processing commit: %s' % commit
            signed = False
            for line in pagure.lib.git.read_git_lines(
                    ['log', '--no-walk', commit], abspath):
                if line.lower().strip().startswith('signed-off-by'):
                    signed = True
                    break
            if pagure.APP.config.get('HOOK_DEBUG', False):
                print ' - Commit: %s is signed: %s' % (commit, signed)
            if not signed:
                print "Commit %s is not signed" % commit
                sys.exit(1)


def main(args):
    run_as_pre_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
