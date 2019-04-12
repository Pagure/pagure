#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Populate the pagure db with some dev data. """

from __future__ import print_function, unicode_literals, absolute_import

import argparse
import os
import tempfile
import pygit2
import shutil
import six

from sqlalchemy import create_engine, MetaData

import pagure
import tests
import pagure.lib.model
import pagure.lib.query
from pagure.lib.login import generate_hashed_value
from pagure.lib.model import create_default_status
from pagure.lib.repo import PagureRepo


"""
Usage:
python dev-data.py --init
python dev-data.py --clean
python dev-data.py --populate
python dev-data.py --all
"""

_config = pagure.config.reload_config()


def empty_dev_db(session):
    print("")
    print("WARNING: Deleting all data from", _config["DB_URL"])
    response = os.environ.get("FORCE_DELETE")
    if not response:
        response = six.moves.input("Do you want to continue? (yes/no)    ")
    if response.lower().startswith("y"):
        tables = reversed(pagure.lib.model_base.BASE.metadata.sorted_tables)
        for tbl in tables:
            session.execute(tbl.delete())
    else:
        exit("Aborting.")


def insert_data(session, username, user_email):
    _config["EMAIL_SEND"] = False
    _config["TESTING"] = True

    ######################################
    # tags
    item = pagure.lib.model.Tag(tag="tag1")
    session.add(item)
    session.commit()

    ######################################
    # Users
    # Create a couple of users
    pingou = item = pagure.lib.model.User(
        user="pingou",
        fullname="PY C",
        password=generate_hashed_value("testing123"),
        token=None,
        default_email="bar@pingou.com",
    )
    session.add(item)
    session.commit()
    print(
        "User created: {} <{}>, {}".format(
            item.user, item.default_email, "testing123"
        )
    )

    foo = item = pagure.lib.model.User(
        user="foo",
        fullname="foo bar",
        password=generate_hashed_value("testing123"),
        token=None,
        default_email="foo@bar.com",
    )
    session.add(item)
    session.commit()
    print(
        "User created: {} <{}>, {}".format(
            item.user, item.default_email, "testing123"
        )
    )

    you = item = pagure.lib.model.User(
        user=username,
        fullname=username,
        password=generate_hashed_value("testing123"),
        token=None,
        default_email=user_email,
    )
    session.add(item)
    session.commit()
    print(
        "User created: {} <{}>, {}".format(
            item.user, item.default_email, "testing123"
        )
    )

    ######################################
    # pagure_group
    item = pagure.lib.model.PagureGroup(
        group_name="admin",
        group_type="admin",
        user_id=pingou.id,
        display_name="admin",
        description="Admin Group",
    )
    session.add(item)
    session.commit()
    print('Created "admin" group. Pingou is a member.')

    # Add a couple of groups so that we can list them
    item = pagure.lib.model.PagureGroup(
        group_name="group",
        group_type="user",
        user_id=pingou.id,
        display_name="group group",
        description="this is a group group",
    )
    session.add(item)
    session.commit()
    print('Created "group" group. Pingou is a member.')

    item = pagure.lib.model.PagureGroup(
        group_name="rel-eng",
        group_type="user",
        user_id=pingou.id,
        display_name="Release Engineering",
        description="The group of release engineers",
    )
    session.add(item)
    session.commit()
    print('Created "rel-eng" group. Pingou is a member.')
    ######################################
    # projects

    import shutil

    # delete folder from local instance to start from a clean slate
    if os.path.exists(_config["GIT_FOLDER"]):
        shutil.rmtree(_config["GIT_FOLDER"])

    # Create projects
    item = project1 = pagure.lib.model.Project(
        user_id=pingou.id,
        name="test",
        is_fork=False,
        parent_id=None,
        description="test project #1",
        hook_token="aaabbbccc",
    )
    item.close_status = ["Invalid", "Insufficient data", "Fixed", "Duplicate"]
    session.add(item)
    session.flush()
    tests.create_locks(session, item)

    item = project2 = pagure.lib.model.Project(
        user_id=pingou.id,
        name="test2",
        is_fork=False,
        parent_id=None,
        description="test project #2",
        hook_token="aaabbbddd",
    )
    item.close_status = ["Invalid", "Insufficient data", "Fixed", "Duplicate"]
    session.add(item)

    item = project3 = pagure.lib.model.Project(
        user_id=pingou.id,
        name="test3",
        is_fork=False,
        parent_id=None,
        description="namespaced test project",
        hook_token="aaabbbeee",
        namespace="somenamespace",
    )
    item.close_status = ["Invalid", "Insufficient data", "Fixed", "Duplicate"]
    session.add(item)

    session.commit()

    tests.create_projects_git(_config["GIT_FOLDER"], bare=True)
    add_content_git_repo(os.path.join(_config["GIT_FOLDER"], "test.git"))
    tests.add_readme_git_repo(os.path.join(_config["GIT_FOLDER"], "test.git"))

    # Add some content to the git repo
    add_content_git_repo(
        os.path.join(_config["GIT_FOLDER"], "forks", "pingou", "test.git")
    )
    tests.add_readme_git_repo(
        os.path.join(_config["GIT_FOLDER"], "forks", "pingou", "test.git")
    )
    tests.add_commit_git_repo(
        os.path.join(_config["GIT_FOLDER"], "forks", "pingou", "test.git"),
        ncommits=10,
    )

    ######################################
    # user_emails
    item = pagure.lib.model.UserEmail(
        user_id=pingou.id, email="bar@pingou.com"
    )
    session.add(item)

    item = pagure.lib.model.UserEmail(
        user_id=pingou.id, email="foo@pingou.com"
    )
    session.add(item)

    item = pagure.lib.model.UserEmail(user_id=foo.id, email="foo@bar.com")
    session.add(item)

    item = pagure.lib.model.UserEmail(user_id=you.id, email=user_email)
    session.add(item)

    session.commit()

    ######################################
    # user_emails_pending
    email_pend = pagure.lib.model.UserEmailPending(
        user_id=pingou.id, email="foo@fp.o", token="abcdef"
    )
    session.add(email_pend)
    session.commit()

    ######################################
    # issues
    # Add an issue and tag it so that we can list them
    item = pagure.lib.model.Issue(
        id=1001,
        uid="foobar",
        project_id=project1.id,
        title="Problem with jenkins build",
        content="For some reason the tests fail at line:24",
        user_id=pingou.id,
    )
    session.add(item)
    session.commit()

    item = pagure.lib.model.Issue(
        id=1002,
        uid="foobar2",
        project_id=project1.id,
        title="Unit tests failing",
        content="Need to fix code for the unit tests to "
        "pass so jenkins build can complete.",
        user_id=pingou.id,
    )
    session.add(item)
    session.commit()

    item = pagure.lib.model.Issue(
        id=1003,
        uid="foobar3",
        project_id=project1.id,
        title="Segfault during execution",
        content="Index out of bounds for variable i?",
        user_id=you.id,
    )
    session.add(item)
    session.commit()

    ######################################
    # pagure_user_group
    group = pagure.lib.query.search_groups(
        session, pattern=None, group_name="rel-eng", group_type=None
    )
    item = pagure.lib.model.PagureUserGroup(
        user_id=pingou.id, group_id=group.id
    )
    session.add(item)
    session.commit()

    group = pagure.lib.query.search_groups(
        session, pattern=None, group_name="admin", group_type=None
    )

    item = pagure.lib.model.PagureUserGroup(user_id=you.id, group_id=group.id)
    session.add(item)
    session.commit()

    group = pagure.lib.query.search_groups(
        session, pattern=None, group_name="group", group_type=None
    )

    item = pagure.lib.model.PagureUserGroup(user_id=foo.id, group_id=group.id)
    session.add(item)
    session.commit()

    ######################################
    # projects_groups
    group = pagure.lib.query.search_groups(
        session, pattern=None, group_name="rel-eng", group_type=None
    )
    repo = pagure.lib.query.get_authorized_project(session, "test")
    item = pagure.lib.model.ProjectGroup(
        project_id=repo.id, group_id=group.id, access="commit"
    )
    session.add(item)
    session.commit()

    group = pagure.lib.query.search_groups(
        session, pattern=None, group_name="admin", group_type=None
    )
    repo = pagure.lib.query.get_authorized_project(session, "test2")
    item = pagure.lib.model.ProjectGroup(
        project_id=repo.id, group_id=group.id, access="admin"
    )
    session.add(item)
    session.commit()

    ######################################
    # pull_requests
    repo = pagure.lib.query.get_authorized_project(session, "test")
    forked_repo = pagure.lib.query.get_authorized_project(session, "test")
    req = pagure.lib.query.new_pull_request(
        session=session,
        repo_from=forked_repo,
        branch_from="master",
        repo_to=repo,
        branch_to="master",
        title="Fixing code for unittest",
        user=username,
        status="Open",
    )
    session.commit()

    repo = pagure.lib.query.get_authorized_project(session, "test")
    forked_repo = pagure.lib.query.get_authorized_project(session, "test")
    req = pagure.lib.query.new_pull_request(
        session=session,
        repo_from=forked_repo,
        branch_from="master",
        repo_to=repo,
        branch_to="master",
        title="add very nice README",
        user=username,
        status="Open",
    )
    session.commit()

    repo = pagure.lib.query.get_authorized_project(session, "test")
    forked_repo = pagure.lib.query.get_authorized_project(session, "test")
    req = pagure.lib.query.new_pull_request(
        session=session,
        repo_from=forked_repo,
        branch_from="master",
        repo_to=repo,
        branch_to="master",
        title="Add README",
        user=username,
        status="Closed",
    )
    session.commit()

    repo = pagure.lib.query.get_authorized_project(session, "test")
    forked_repo = pagure.lib.query.get_authorized_project(session, "test")
    req = pagure.lib.query.new_pull_request(
        session=session,
        repo_from=forked_repo,
        branch_from="master",
        repo_to=repo,
        branch_to="master",
        title="Fix some containers",
        user=username,
        status="Merged",
    )
    session.commit()

    repo = pagure.lib.query.get_authorized_project(session, "test")
    forked_repo = pagure.lib.query.get_authorized_project(session, "test")
    req = pagure.lib.query.new_pull_request(
        session=session,
        repo_from=forked_repo,
        branch_from="master",
        repo_to=repo,
        branch_to="master",
        title="Fix pull request statuses",
        user=username,
        status="Closed",
    )
    session.commit()

    repo = pagure.lib.query.get_authorized_project(session, "test")
    forked_repo = pagure.lib.query.get_authorized_project(session, "test")
    req = pagure.lib.query.new_pull_request(
        session=session,
        repo_from=forked_repo,
        branch_from="master",
        repo_to=repo,
        branch_to="master",
        title="Fixing UI of issue",
        user=username,
        status="Merged",
    )
    session.commit()

    #####################################
    # tokens
    tests.create_tokens(session, user_id=pingou.id, project_id=project1.id)

    ######################################
    # user_projects
    repo = pagure.lib.query.get_authorized_project(session, "test")
    item = pagure.lib.model.ProjectUser(
        project_id=repo.id, user_id=foo.id, access="commit"
    )
    session.add(item)
    session.commit()

    repo = pagure.lib.query.get_authorized_project(session, "test2")
    item = pagure.lib.model.ProjectUser(
        project_id=repo.id, user_id=you.id, access="commit"
    )
    session.add(item)
    session.commit()

    ######################################
    # issue_comments
    item = pagure.lib.model.IssueComment(
        user_id=pingou.id,
        issue_uid="foobar",
        comment="We may need to adjust the unittests instead of the code.",
    )
    session.add(item)
    session.commit()

    ######################################
    # issue_to_issue
    repo = pagure.lib.query.get_authorized_project(session, "test")
    all_issues = pagure.lib.query.search_issues(session, repo)
    pagure.lib.query.add_issue_dependency(
        session, all_issues[0], all_issues[1], "pingou"
    )

    ######################################
    # pull_request_comments
    user = pagure.lib.query.search_user(session, username="pingou")
    # only 1 pull request available atm
    pr = pagure.lib.query.get_pull_request_of_user(session, "pingou")[0]
    item = pagure.lib.model.PullRequestComment(
        pull_request_uid=pr.uid,
        user_id=user.id,
        comment="+1 for me. Btw, could you rebase before you merge?",
        notification=0,
    )
    session.add(item)
    session.commit()

    ######################################
    # pull_request_flags
    # only 1 pull request available atm
    pr = pagure.lib.query.get_pull_request_of_user(session, "pingou")[0]
    item = pagure.lib.model.PullRequestFlag(
        uid="random_pr_flag_uid",
        pull_request_uid=pr.uid,
        user_id=pingou.id,
        username=pingou.user,
        percent=80,
        comment="Jenkins build passes",
        url=str(pr.id),
        status="success",
    )
    session.add(item)
    session.commit()

    pr = pagure.lib.query.get_pull_request_of_user(session, "foo")[1]
    item = pagure.lib.model.PullRequestFlag(
        uid="oink oink uid",
        pull_request_uid=pr.uid,
        user_id=pingou.id,
        username=pingou.user,
        percent=80,
        comment="Jenkins does not pass",
        url=str(pr.id),
        status="failure",
    )
    session.add(item)
    session.commit()

    ######################################
    # pull_request_assignee
    pr = pagure.lib.query.search_pull_requests(session, requestid="1006")
    pr.assignee_id = pingou.id
    session.commit()

    pr = pagure.lib.query.search_pull_requests(session, requestid="1007")
    pr.assignee_id = you.id
    session.commit()

    pr = pagure.lib.query.search_pull_requests(session, requestid="1004")
    pr.assignee_id = foo.id
    session.commit()

    ######################################
    # tags_issues
    repo = pagure.lib.query.get_authorized_project(session, "test")
    issues = pagure.lib.query.search_issues(session, repo)
    item = pagure.lib.model.TagIssue(issue_uid=issues[0].uid, tag="tag1")
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
        shutil.rmtree(os.path.join(_config["GIT_FOLDER"], fork_proj_location))
    except:
        print("git folder already deleted")

    try:
        shutil.rmtree(os.path.join(_config["DOCS_FOLDER"], fork_proj_location))
    except:
        print("docs folder already deleted")

    try:
        shutil.rmtree(
            os.path.join(_config["TICKETS_FOLDER"], fork_proj_location)
        )
    except:
        print("tickets folder already deleted")

    try:
        shutil.rmtree(
            os.path.join(_config["REQUESTS_FOLDER"], fork_proj_location)
        )
    except:
        print("requests folder already deleted")

    repo = pagure.lib.query.get_authorized_project(session, "test")
    result = pagure.lib.query.fork_project(session, "foo", repo)
    if result == 'Repo "test" cloned to "foo/test"':
        session.commit()


def add_content_git_repo(folder, branch="master"):
    """ Create some content for the specified git repo. """
    if not os.path.exists(folder):
        os.makedirs(folder)
    brepo = pygit2.init_repository(folder, bare=True)

    newfolder = tempfile.mkdtemp(prefix="pagure-tests")
    repo = pygit2.clone_repository(folder, newfolder)

    # Create a file in that git repo
    with open(os.path.join(newfolder, "sources"), "w") as stream:
        stream.write("foo\n bar")
    repo.index.add("sources")
    repo.index.write()

    parents = []
    commit = None
    try:
        commit = repo.revparse_single("HEAD" if branch == "master" else branch)
    except KeyError:
        pass
    if commit:
        parents = [commit.oid.hex]

    # Commits the files added
    tree = repo.index.write_tree()
    author = pygit2.Signature("Alice Author", "alice@authors.tld")
    committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
    repo.create_commit(
        "refs/heads/%s" % branch,  # the name of the reference to update
        author,
        committer,
        "Add sources file for testing",
        # binary string representing the tree object ID
        tree,
        # list of binary strings representing parents of the new commit
        parents,
    )

    parents = []
    commit = None
    try:
        commit = repo.revparse_single("HEAD" if branch == "master" else branch)
    except KeyError:
        pass
    if commit:
        parents = [commit.oid.hex]

    subfolder = os.path.join("folder1", "folder2")
    if not os.path.exists(os.path.join(newfolder, subfolder)):
        os.makedirs(os.path.join(newfolder, subfolder))
    # Create a file in that git repo
    with open(os.path.join(newfolder, subfolder, "file"), "w") as stream:
        stream.write("foo\n bar\nbaz")
    repo.index.add(os.path.join(subfolder, "file"))
    repo.index.write()

    # Commits the files added
    tree = repo.index.write_tree()
    author = pygit2.Signature("Alice Author", "alice@authors.tld")
    committer = pygit2.Signature("Cecil Committer", "cecil@committers.tld")
    repo.create_commit(
        "refs/heads/%s" % branch,  # the name of the reference to update
        author,
        committer,
        "Add some directory and a file for more testing",
        # binary string representing the tree object ID
        tree,
        # list of binary strings representing parents of the new commit
        parents,
    )

    # Push to origin
    ori_remote = repo.remotes[0]
    master_ref = repo.lookup_reference(
        "HEAD" if branch == "master" else "refs/heads/%s" % branch
    ).resolve()
    refname = "%s:%s" % (master_ref.name, master_ref.name)

    PagureRepo.push(ori_remote, refname)

    shutil.rmtree(newfolder)


def _get_username():
    invalid_option = ["pingou", "foo"]
    user_name = os.environ.get("USER_NAME")
    if not user_name:
        print("")
        user_name = six.moves.input(
            "Enter your username so we can add you into the test data:  "
        )
    cnt = 0
    while not user_name.strip() or user_name in invalid_option:
        print("Reserved names: " + str(invalid_option))
        user_name = six.moves.input(
            "Enter your username so we can add you into the " "test data:  "
        )
        cnt += 1
        if cnt == 4:
            print("We asked too many times, bailing")
            sys.exit(1)

    return user_name


def _get_user_email():
    invalid_option = ["bar@pingou.com", "foo@bar.com"]
    user_email = os.environ.get("USER_EMAIL")
    if not user_email:
        print("")
        user_email = six.moves.input("Enter your user email:  ")

    cnt = 0
    while not user_email.strip() or user_email in invalid_option:
        print("Reserved names: " + str(invalid_option))
        user_email = six.moves.input("Enter your user email:  ")
        cnt += 1
        if cnt == 4:
            print("We asked too many times, bailing")
            sys.exit(1)

    return user_email


if __name__ == "__main__":
    desc = (
        "Run the dev database initialization/insertion/deletion "
        "script for db located  " + str(_config["DB_URL"])
    )
    parser = argparse.ArgumentParser(prog="dev-data", description=desc)
    parser.add_argument(
        "-i", "--init", action="store_true", help="Create the dev db"
    )
    parser.add_argument(
        "-p", "--populate", action="store_true", help="Add test data to the db"
    )
    parser.add_argument(
        "-d", "--delete", action="store_true", help="Wipe the dev db"
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Create, Populate then Wipe the dev db",
    )

    args = parser.parse_args()

    # forcing the user to choose
    if not any(vars(args).values()):
        parser.error("No arguments provided.")

    session = None

    if args.init or args.all:
        session = pagure.lib.model.create_tables(
            db_url=_config["DB_URL"],
            alembic_ini=None,
            acls=_config["ACLS"],
            debug=False,
        )
        print("Database created")

    if args.populate or args.all:
        if not session:
            session = pagure.lib.query.create_session(_config["DB_URL"])

        user_name = _get_username()
        user_email = _get_user_email()
        insert_data(session, user_name, user_email)

    if args.delete or args.all:
        empty_dev_db(session)
