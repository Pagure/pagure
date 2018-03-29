#!/usr/bin/env python
""" Populate the pagure db with some dev data. """

from __future__ import print_function, unicode_literals

import argparse
import os
import sys

from sqlalchemy import create_engine, MetaData

import pagure
import tests
from pagure.lib import create_session

'''
Usage:
python dev-data.py --init
python dev-data.py --clean
python dev-data.py --populate
python dev-data.py --all
'''

_config = pagure.config.reload_config()


def init_database():
    DB_URL = _config['DB_URL']

    # create the table if it doesnt exist
    pagure.lib.model.create_tables(
        DB_URL,
        _config.get('PATH_ALEMBIC_INI', None),
        acls=_config.get('ACLS', {}),
        debug=True)

    engine = create_engine('%s' % DB_URL, echo=True)

    metadata = MetaData(engine)
    metadata.reflect(bind=engine)
    return engine, metadata


def empty_dev_db(metadata, engine):
    print('')
    print('')
    print('WARNING: Deleting all data from ', _config['DB_URL'])
    # Dangerous: this will wipe the data from the table but keep the schema
    print('')
    response = raw_input('Do you want to continue yes or no?    ')
    if 'yes'.startswith(response.lower()):
        for tbl in reversed(metadata.sorted_tables):
            if tbl.fullname != 'acls':
                engine.execute(tbl.delete())


def insert_data(session, username, user_email):
    _config['EMAIL_SEND'] = False
    _config['TESTING'] = True

    ######################################
    # tags
    item = pagure.lib.model.Tag(
        tag='tag1',
    )
    session.add(item)
    session.commit()

    ######################################
    # Users
    # Create a couple of users
    item = pagure.lib.model.User(
        user='pingou',
        fullname='PY C',
        password='foo',
        default_email='bar@pingou.com',
    )
    session.add(item)
    session.commit()

    item = pagure.lib.model.User(
        user='foo',
        fullname='foo bar',
        password='foo',
        default_email='foo@bar.com',
    )
    session.add(item)
    session.commit()

    item = pagure.lib.model.User(
        user=username,
        fullname=username,
        password='foo',
        default_email=user_email,
    )
    session.add(item)
    session.commit()

    ######################################
    # pagure_group
    item = pagure.lib.model.PagureGroup(
        group_name='admin',
        user_id=1,
        display_name='admin',
        description='Admin Group',
    )
    session.add(item)
    session.commit()

    # Add a couple of groups so that we can list them
    item = pagure.lib.model.PagureGroup(
        group_name='group',
        group_type='user',
        user_id=1,  # pingou
        display_name='group group',
        description='this is a group group',
    )
    session.add(item)
    session.commit()

    item = pagure.lib.model.PagureGroup(
        group_name='rel-eng',
        group_type='user',
        user_id=1,  # pingou
        display_name='Release Engineering',
        description='The group of release engineers',
    )
    session.add(item)
    session.commit()
    ######################################
    # projects

    import shutil
    # delete folder from local instance to start from a clean slate
    if os.path.exists(pagure.APP.config['GIT_FOLDER']):
        shutil.rmtree(_config['GIT_FOLDER'])

    tests.create_projects(session)
    tests.create_projects_git(_config['GIT_FOLDER'], bare=True)
    tests.add_content_git_repo(
        os.path.join(_config['GIT_FOLDER'], 'test.git'))
    tests.add_readme_git_repo(
        os.path.join(_config['GIT_FOLDER'], 'test.git'))

    # Add some content to the git repo
    tests.add_content_git_repo(
        os.path.join(_config['GIT_FOLDER'], 'forks', 'pingou',
                     'test.git'))
    tests.add_readme_git_repo(
        os.path.join(_config['GIT_FOLDER'], 'forks', 'pingou',
                     'test.git'))
    tests.add_commit_git_repo(
        os.path.join(_config['GIT_FOLDER'], 'forks', 'pingou',
                     'test.git'), ncommits=10)

    ######################################
    # user_emails
    item = pagure.lib.model.UserEmail(
        user_id=1,
        email='bar@pingou.com')
    session.add(item)

    item = pagure.lib.model.UserEmail(
        user_id=1,
        email='foo@pingou.com')
    session.add(item)

    item = pagure.lib.model.UserEmail(
        user_id=2,
        email='foo@bar.com')
    session.add(item)

    item = pagure.lib.model.UserEmail(
        user_id=3,
        email=user_email)
    session.add(item)

    session.commit()

    ######################################
    # user_emails_pending
    user = pagure.lib.search_user(session, username='pingou')
    email_pend = pagure.lib.model.UserEmailPending(
        user_id=user.id,
        email='foo@fp.o',
        token='abcdef',
    )
    session.add(email_pend)
    session.commit()

    ######################################
    # issues
    # Add an issue and tag it so that we can list them
    item = pagure.lib.model.Issue(
        id=1,
        uid='foobar',
        project_id=1,
        title='Problem with jenkins build',
        content='For some reason the tests fail at line:24',
        user_id=1,  # pingou
    )
    session.add(item)
    session.commit()

    item = pagure.lib.model.Issue(
        id=2,
        uid='foobar2',
        project_id=1,
        title='Unit tests failing',
        content='Need to fix code for the unit tests to '
                'pass so jenkins build can complete.',
        user_id=1,  # pingou
    )
    session.add(item)
    session.commit()

    user = pagure.lib.search_user(session, username=username)
    item = pagure.lib.model.Issue(
        id=3,
        uid='foobar3',
        project_id=1,
        title='Segfault during execution',
        content='Index out of bounds for variable i?',
        user_id=user.id,  # current user
    )
    session.add(item)
    session.commit()

    ######################################
    # pagure_user_group
    group = pagure.lib.search_groups(session, pattern=None,
                                     group_name="rel-eng", group_type=None)
    user = pagure.lib.search_user(session, username='pingou')
    item = pagure.lib.model.PagureUserGroup(
        user_id=user.id,
        group_id=group.id
    )
    session.add(item)
    session.commit()

    user = pagure.lib.search_user(session, username=username)
    group = pagure.lib.search_groups(session, pattern=None,
                                     group_name="admin", group_type=None)

    item = pagure.lib.model.PagureUserGroup(
        user_id=user.id,
        group_id=group.id
    )
    session.add(item)
    session.commit()

    user = pagure.lib.search_user(session, username='foo')
    group = pagure.lib.search_groups(session, pattern=None,
                                     group_name="group", group_type=None)

    item = pagure.lib.model.PagureUserGroup(
        user_id=user.id,
        group_id=group.id
    )
    session.add(item)
    session.commit()

    ######################################
    # projects_groups
    group = pagure.lib.search_groups(session, pattern=None,
                                     group_name="rel-eng", group_type=None)
    repo = pagure.lib.get_authorized_project(session, 'test')
    item = pagure.lib.model.ProjectGroup(
        project_id=repo.id,
        group_id=group.id
    )
    session.add(item)
    session.commit()

    group = pagure.lib.search_groups(session, pattern=None,
                                     group_name="admin", group_type=None)
    repo = pagure.lib.get_authorized_project(session, 'test2')
    item = pagure.lib.model.ProjectGroup(
        project_id=repo.id,
        group_id=group.id
    )
    session.add(item)
    session.commit()

    ######################################
    # pull_requests
    repo = pagure.lib.get_authorized_project(session, 'test')
    forked_repo = pagure.lib.get_authorized_project(session, 'test')
    req = pagure.lib.new_pull_request(
        session=session,
        repo_from=forked_repo,
        branch_from='master',
        repo_to=repo,
        branch_to='master',
        title='Fixing code for unittest',
        user=username,
        requestfolder=None,
    )
    session.commit()

    ######################################
    # tokens
    tests.create_tokens(session)

    ######################################
    # user_projects
    user = pagure.lib.search_user(session, username='foo')
    repo = pagure.lib.get_authorized_project(session, 'test')
    item = pagure.lib.model.ProjectUser(
        project_id=repo.id,
        user_id=user.id
    )
    session.add(item)
    session.commit()

    user = pagure.lib.search_user(session, username=username)
    repo = pagure.lib.get_authorized_project(session, 'test2')
    item = pagure.lib.model.ProjectUser(
        project_id=repo.id,
        user_id=user.id
    )
    session.add(item)
    session.commit()

    ######################################
    # issue_comments
    item = pagure.lib.model.IssueComment(
        user_id=1,
        issue_uid='foobar',
        comment='We may need to adjust the unittests instead of the code.',
    )
    session.add(item)
    session.commit()

    ######################################
    # issue_to_issue
    repo = pagure.lib.get_authorized_project(session, 'test')
    all_issues = pagure.lib.search_issues(session, repo)
    pagure.lib.add_issue_dependency(session, all_issues[0],
                                    all_issues[1], 'pingou',
                                    _config['GIT_FOLDER'])

    ######################################
    # pull_request_comments
    user = pagure.lib.search_user(session, username='pingou')
    # only 1 pull request available atm
    pr = pagure.lib.get_pull_request_of_user(session, "pingou")[0]
    item = pagure.lib.model.PullRequestComment(
        pull_request_uid=pr.uid,
        user_id=user.id,
        comment="+1 for me. Btw, could you rebase before you merge?",
        notification=0
    )
    session.add(item)
    session.commit()

    ######################################
    # pull_request_flags
    user = pagure.lib.search_user(session, username='pingou')
    # only 1 pull request available atm
    pr = pagure.lib.get_pull_request_of_user(session, "pingou")[0]
    item = pagure.lib.model.PullRequestFlag(
        uid="random_pr_flag_uid",
        pull_request_uid=pr.uid,
        user_id=user.id,
        username=user.user,
        percent=80,
        comment="Jenkins build passes",
        url=str(pr.id)
    )
    session.add(item)
    session.commit()

    ######################################
    # tags_issues
    repo = pagure.lib.get_authorized_project(session, 'test')
    issues = pagure.lib.search_issues(session, repo)
    item = pagure.lib.model.TagIssue(
        issue_uid=issues[0].uid,
        tag='Blocker',
    )
    session.add(item)
    session.commit()

    ######################################
    # tokens_acls
    tests.create_tokens_acl(session)

    ######################################
    # Fork a project
    # delete fork data
    fork_proj_location = "forks/foo/test.git"
    try:
        shutil.rmtree(os.path.join(_config['GIT_FOLDER'],
                                   fork_proj_location))
    except:
        print('git folder already deleted')

    try:
        shutil.rmtree(os.path.join(_config['DOCS_FOLDER'],
                                   fork_proj_location))
    except:
        print('docs folder already deleted')

    try:
        shutil.rmtree(os.path.join(_config['TICKETS_FOLDER'],
                                   fork_proj_location))
    except:
        print('tickets folder already deleted')

    try:
        shutil.rmtree(os.path.join(_config['REQUESTS_FOLDER'],
                                   fork_proj_location))
    except:
        print('requests folder already deleted')

    repo = pagure.lib.get_authorized_project(session, 'test')
    result = pagure.lib.fork_project(session, 'foo', repo,
                                     _config['GIT_FOLDER'],
                                     _config['DOCS_FOLDER'],
                                     _config['TICKETS_FOLDER'],
                                     _config['REQUESTS_FOLDER'])
    if result == 'Repo "test" cloned to "foo/test"':
        session.commit()


if __name__ == "__main__":
    desc = "Run the dev database initialization/insertion/deletion " \
           "script for db located  " + str(_config['DB_URL'])
    parser = argparse.ArgumentParser(prog="dev-data", description=desc)
    parser.add_argument('-i', '--init', action="store_true",
                        help="Create the dev db")
    parser.add_argument('-p', '--populate', action="store_true",
                        help="Add test data to the db")
    parser.add_argument('-d', '--delete', action="store_true",
                        help="Wipe the dev db")
    parser.add_argument('-a', '--all', action="store_true",
                        help="Create, Wipe, Populate the dev db")

    args = parser.parse_args()

    # forcing the user to choose
    if not any(vars(args).values()):
        parser.error('No arguments provided.')

    if args.init or args.delete or args.all:
        eng, meta = init_database()

    if args.delete or args.all:
        empty_dev_db(meta, eng)

    if args.populate or args.all:
        session = create_session(_config['DB_URL'])
        invalid_option = ['pingou', 'bar@pingou.com', 'foo', 'foo@bar.com']
        print("")
        user_name = raw_input(
            "Enter your username so we can add you into the test data:  ")
        while user_name in invalid_option:
            print("Reserved names: " + str(invalid_option))
            user_name = raw_input(
                "Enter your username so we can add you into the test data:  ")

        if not user_name.replace(" ", ""):
            user_name = 'pythagoras'

        print("")
        user_email = raw_input("Enter your user email:  ")

        while user_email in invalid_option:
            print("Reserved names: " + str(invalid_option))
            user_email = raw_input("Enter your user email:  ")

        if not user_email.replace(" ", ""):
            user_email = 'pythagoras@math.com'

        insert_data(session, user_name, user_email)
