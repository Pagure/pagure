#!/usr/bin/env python

import argparse
import requests
import os

from sqlalchemy.exc import SQLAlchemyError

if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    print 'Using configuration file `/etc/pagure/pagure.cfg`'
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'

import pagure


def get_poc_of_pkgs(debug=False):
    """ Retrieve a dictionary giving the point of contact of each package
    in pkgdb.
    """
    if debug:
        print 'Querying pkgdb'
    PKGDB_URL = 'https://admin.fedoraproject.org/pkgdb/api/'
    req = requests.get(PKGDB_URL + 'bugzilla').text
    if debug:
        print 'Pkgdb data retrieved, getting POC'
    pkgs = {}
    for line in req.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        line = line.split('|')
        if len(line) < 4:
            continue
        pkgs[line[1]] = line[3]

    return pkgs


def main(folder, debug=False):
    """
    Logic:
    - Query the list of maintainer/PoC from pkgdb
    - Browse the directory
    - For each git in the directory, create the project with the correct POC
    """
    pocs = get_poc_of_pkgs(debug=debug)

    if debug:
        print 'Adding the user to the DB'
    for user in sorted(set(pocs.values())):
        if debug:
            print user
        try:
            pagure.lib.set_up_user(
                session=pagure.SESSION,
                username=user,
                fullname=user,
                default_email='%s@fedoraproject.org' % user,
                keydir=pagure.APP.config.get('GITOLITE_KEYDIR', None),
            )
            pagure.SESSION.commit()
        except SQLAlchemyError, err:
            pagure.SESSION.rollback()
            print 'ERROR with user %s' % user
            print err

    for project in sorted(os.listdir(folder)):
        if debug:
            print project

        if not project.endswith('.git'):
            if debug:
                print '  -skip: not a git repository'
            continue

        if project.split('.git')[0] not in pocs:
            if debug:
                print '  -skip: no pocs'
            continue

        try:
            name = project.split('.git')[0]
            pagure.lib.new_project(
                session=pagure.SESSION,
                user=pocs[name],
                name=name,
                blacklist=pagure.APP.config['BLACKLISTED_PROJECTS'],
                gitfolder=pagure.APP.config['GIT_FOLDER'],
                docfolder=pagure.APP.config['DOCS_FOLDER'],
                ticketfolder=pagure.APP.config['TICKETS_FOLDER'],
                requestfolder=pagure.APP.config['REQUESTS_FOLDER'],
            )
            pagure.SESSION.commit()
        except pagure.exceptions.PagureException, err:
            print 'ERROR with project %s' % project
            print err
        except SQLAlchemyError, err:  # pragma: no cover
            pagure.SESSION.rollback()
            print 'ERROR (DB) with project %s' % project
            print err


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Script creating projects on pagure based on the git '
        'repos present in the specified folder and the pkgdb information.'
    )
    parser.add_argument(
        'folder',
        help='Folder containing all the git repos of the projects to create')
    parser.add_argument(
        '--debug', dest='debug', action='store_true', default=False,
        help='Print the debugging output')

    args = parser.parse_args()

    main(args.folder, debug=args.debug)
