#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

from __future__ import unicode_literals, print_function

import subprocess
import sys
import os

# Since this is run by sshd, we don't have a way to set environment
# variables ahead of time
if "PAGURE_CONFIG" not in os.environ and os.path.exists(
    "/etc/pagure/pagure.cfg"
):
    os.environ["PAGURE_CONFIG"] = "/etc/pagure/pagure.cfg"

# Here starts the code
import pagure
import pagure.lib
from pagure.utils import is_repo_user
from pagure.config import config as pagure_config


# Get the arguments
if len(sys.argv) != 2:
    print("Invalid call, too few arguments", file=sys.stderr)
    sys.exit(1)
remoteuser = sys.argv[1]

args = os.environ["SSH_ORIGINAL_COMMAND"].split(" ")
# Expects: <git-(receive|upload)-pack> <repopath>
if len(args) != 2:
    print("Invalid call, too few inner arguments", file=sys.stderr)
    sys.exit(1)


cmd = args[0]
path = args[1]
if cmd not in ("git-receive-pack", "git-upload-pack"):
    print("Invalid call, invalid operation", file=sys.stderr)
    sys.exit(1)

# Git will encode the file path argument within single quotes
if path[0] != "'" or path[-1] != "'":
    print("Invalid call: invalid path", file=sys.stderr)
    sys.exit(1)
path = path[1:-1]

if os.path.isabs(path):
    print("Non-full path expected, not %s" % path, file=sys.stderr)
    sys.exit(1)

if not path.endswith(".git"):
    path = path + ".git"

session = pagure.lib.create_session(pagure_config["DB_URL"])
if not session:
    raise Exception("Unable to initialize db session")

gitdir = os.path.join(pagure_config["GIT_FOLDER"], path)
(repotype, username, namespace, repo) = pagure.lib.git.get_repo_info_from_path(
    gitdir, hide_notfound=True
)

if repo is None:
    print("Repo not found", file=sys.stderr)
    sys.exit(1)

project = pagure.lib.get_authorized_project(
    session, repo, user=username, namespace=namespace, asuser=remoteuser
)

if not project:
    print("Repo not found", file=sys.stderr)
    sys.exit(1)

if repotype != "main" and not is_repo_user(project, remoteuser):
    print("Repo not found", file=sys.stderr)
    sys.exit(1)

# Now go run git
# We verified that cmd is either "git-receive-pack" or "git-send-pack"
# and "gitdir" is a full, absolute, path within GIT_FOLDER that points to
# the canonical location for this git repo.
os.execvp(cmd, [cmd, gitdir])
