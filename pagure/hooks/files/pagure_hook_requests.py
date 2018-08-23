#!/usr/bin/env python


"""Pagure specific hook to update pull-requests stored in the database
based on the information pushed in the requests git repository.
"""

from __future__ import print_function, unicode_literals

import os
import sys


# We need to access the database
if "PAGURE_CONFIG" not in os.environ and os.path.exists(
    "/etc/pagure/pagure.cfg"
):
    os.environ["PAGURE_CONFIG"] = "/etc/pagure/pagure.cfg"


import pagure.config  # noqa: E402
import pagure.lib.tasks_services  # noqa: E402


_config = pagure.config.config
abspath = os.path.abspath(os.environ["GIT_DIR"])


def get_files_to_load(new_commits_list):

    print("Files changed by new commits:\n")
    file_list = []
    new_commits_list.reverse()
    for commit in new_commits_list:
        filenames = pagure.lib.git.read_git_lines(
            ["diff-tree", "--no-commit-id", "--name-only", "-r", commit],
            abspath,
        )
        for line in filenames:
            if line.strip():
                file_list.append(line.strip())

    return file_list


def run_as_post_receive_hook():

    repo = pagure.lib.git.get_repo_name(abspath)
    username = pagure.lib.git.get_username(abspath)
    namespace = pagure.lib.git.get_repo_namespace(
        abspath, gitfolder=_config["TICKETS_FOLDER"]
    )
    if _config.get("HOOK_DEBUG", False):
        print("repo:", repo)
        print("user:", username)
        print("namespace:", namespace)

    for line in sys.stdin:
        if _config.get("HOOK_DEBUG", False):
            print(line)
        (oldrev, newrev, refname) = line.strip().split(" ", 2)

        if _config.get("HOOK_DEBUG", False):
            print("  -- Old rev")
            print(oldrev)
            print("  -- New rev")
            print(newrev)
            print("  -- Ref name")
            print(refname)

        if set(newrev) == set(["0"]):
            print(
                "Deleting a reference/branch, so we won't run the "
                "pagure hook"
            )
            return

        commits = pagure.lib.git.get_revs_between(
            oldrev, newrev, abspath, refname
        )

        pagure.lib.tasks_services.load_json_commits_to_db.delay(
            name=repo,
            commits=commits,
            abspath=abspath,
            data_type="pull-request",
            agent=os.environ.get("GL_USER"),
            namespace=namespace,
            username=username,
        )


def main(args):
    run_as_post_receive_hook()


if __name__ == "__main__":
    main(sys.argv[1:])
