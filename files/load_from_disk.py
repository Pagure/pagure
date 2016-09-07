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
import pagure.lib
import pagure.lib.model


def get_poc_of_pkgs(debug=False):
    """ Retrieve a dictionary giving the point of contact of each package
    in pkgdb.
    """
    if debug:
        print 'Querying pkgdb'
    PKGDB_URL = 'https://admin.stg.fedoraproject.org/pkgdb/api/'
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
        except SQLAlchemyError as err:
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
            orig_name = name
            name = 'rpms/%s' % name
            if name in pagure.APP.config['BLACKLISTED_PROJECTS']:
                raise pagure.exceptions.RepoExistsException(
                    'No project "%s" are allowed to be created due to potential '
                    'conflicts in URLs with pagure itself' % name
                )

            user_obj = pagure.lib.get_user(pagure.SESSION, pocs[orig_name])
            allowed_prefix = pagure.APP.config[
                'ALLOWED_PREFIX'] + [grp for grp in user_obj.groups]

            first_part, _, second_part = name.partition('/')
            if second_part and first_part not in allowed_prefix:
                raise pagure.exceptions.PagureException(
                    'The prefix of your project must be in the list of allowed '
                    'prefixes set by the admins of this pagure instance, or the name '
                    'of a group of which you are a member.'
                )

            gitfolder = pagure.APP.config['GIT_FOLDER']
            docfolder = pagure.APP.config['DOCS_FOLDER']
            ticketfolder = pagure.APP.config['TICKETS_FOLDER']
            requestfolder = pagure.APP.config['REQUESTS_FOLDER']

            gitrepo = os.path.join(gitfolder, '%s.git' % name)

            project = pagure.lib.model.Project(
                name=name,
                description=None,
                url=None,
                avatar_email=None,
                user_id=user_obj.id,
                parent_id=None,
                hook_token=pagure.lib.login.id_generator(40)
            )
            pagure.SESSION.add(project)
            # Make sure we won't have SQLAlchemy error before we create the repo
            pagure.SESSION.flush()

            http_clone_file = os.path.join(gitrepo, 'git-daemon-export-ok')
            if not os.path.exists(http_clone_file):
                with open(http_clone_file, 'w') as stream:
                    pass

            docrepo = os.path.join(docfolder, project.path)
            if os.path.exists(docrepo):
                shutil.rmtree(gitrepo)
                raise pagure.exceptions.RepoExistsException(
                    'The docs repo "%s" already exists' % project.path
                )
            pygit2.init_repository(docrepo, bare=True)

            ticketrepo = os.path.join(ticketfolder, project.path)
            if os.path.exists(ticketrepo):
                shutil.rmtree(gitrepo)
                shutil.rmtree(docrepo)
                raise pagure.exceptions.RepoExistsException(
                    'The tickets repo "%s" already exists' % project.path
                )
            pygit2.init_repository(
                ticketrepo, bare=True,
                mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP)

            requestrepo = os.path.join(requestfolder, project.path)
            if os.path.exists(requestrepo):
                shutil.rmtree(gitrepo)
                shutil.rmtree(docrepo)
                shutil.rmtree(ticketrepo)
                raise pagure.exceptions.RepoExistsException(
                    'The requests repo "%s" already exists' % project.path
                )
            pygit2.init_repository(
                requestrepo, bare=True,
                mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP)

            pagure.SESSION.commit()
        except pagure.exceptions.PagureException as err:
            print 'ERROR with project %s' % project
            print err
        except SQLAlchemyError as err:  # pragma: no cover
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
