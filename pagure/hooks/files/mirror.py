#! /usr/bin/env python


"""Pagure specific hook to mirror a repo to another location.
"""
from __future__ import unicode_literals, print_function


import logging
import os
import sys


if "PAGURE_CONFIG" not in os.environ and os.path.exists(
    "/etc/pagure/pagure.cfg"
):
    os.environ["PAGURE_CONFIG"] = "/etc/pagure/pagure.cfg"


import pagure.config  # noqa: E402
import pagure.exceptions  # noqa: E402
import pagure.lib  # noqa: E402
import pagure.lib.tasks_mirror  # noqa: E402
import pagure.ui.plugins  # noqa: E402


_log = logging.getLogger(__name__)
_config = pagure.config.config
abspath = os.path.abspath(os.environ["GIT_DIR"])


def main(args):

    repo = pagure.lib.git.get_repo_name(abspath)
    username = pagure.lib.git.get_username(abspath)
    namespace = pagure.lib.git.get_repo_namespace(abspath)
    if _config.get("HOOK_DEBUG", False):
        print("repo:", repo)
        print("user:", username)
        print("namespace:", namespace)

    session = pagure.lib.create_session(_config["DB_URL"])
    project = pagure.lib._get_project(
        session, repo, user=username, namespace=namespace
    )

    if not project:
        print("Could not find a project corresponding to this git repo")
        session.close()
        return 1

    pagure.lib.tasks_mirror.mirror_project.delay(
        username=project.user.user if project.is_fork else None,
        namespace=project.namespace,
        name=project.name,
    )

    session.close()
    return 0


if __name__ == "__main__":
    main(sys.argv[1:])
