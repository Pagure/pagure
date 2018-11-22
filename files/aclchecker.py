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

import requests

if "SSH_ORIGINAL_COMMAND" not in os.environ:
    print("Welcome %s. This server does not offer shell access." % sys.argv[1])
    sys.exit(0)

# Since this is run by sshd, we don't have a way to set environment
# variables ahead of time
if "PAGURE_CONFIG" not in os.environ and os.path.exists(
    "/etc/pagure/pagure.cfg"
):
    os.environ["PAGURE_CONFIG"] = "/etc/pagure/pagure.cfg"

# Here starts the code
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
gitdir = args[1]
if cmd not in ("git-receive-pack", "git-upload-pack"):
    print("Invalid call, invalid operation", file=sys.stderr)
    sys.exit(1)

# Normalization of the gitdir
# Git will encode the file path argument within single quotes
if gitdir[0] != "'" or gitdir[-1] != "'":
    print("Invalid call: invalid path", file=sys.stderr)
    sys.exit(1)
gitdir = gitdir[1:-1]
# With the "ssh://hostname/repo.git", SSH sends "/repo.git"
if gitdir[0] == "/":
    gitdir = gitdir[1:]
# Always add .git for good measure
if not gitdir.endswith(".git"):
    gitdir = gitdir + ".git"


url = "%s/pv/ssh/checkaccess/" % pagure_config["APP_URL"]
data = {"gitdir": gitdir, "username": remoteuser}
headers = {}
if pagure_config.get("SSH_ADMIN_TOKEN"):
    headers["Authorization"] = "token %s" % pagure_config["SSH_ADMIN_TOKEN"]
resp = requests.post(url, data=data, headers=headers)
if not resp.status_code == 200:
    print(
        "Error during lookup request: status: %s" % resp.status_code,
        file=sys.stderr,
    )
    sys.exit(1)

result = resp.json()

if not result["access"]:
    # The user does not have access to this repo, or project does
    # not exist. Whatever it is, no access.
    print("No such repository", file=sys.stderr)
    sys.exit(1)


# Now go run the configured command
# We verified that cmd is either "git-receive-pack" or "git-send-pack"
# and "path" is a path that points to a valid Pagure repository.
if result["region"]:
    runner, env = pagure_config["SSH_COMMAND_REPOSPANNER"]
else:
    runner, env = pagure_config["SSH_COMMAND_NON_REPOSPANNER"]

result.update({"username": remoteuser, "cmd": cmd})

for key in result:
    if result[key] is None:
        result[key] = ''

runargs = [arg % result for arg in runner]
if env:
    for key in env:
        os.environ[key] = env[key] % result
os.execvp(runargs[0], runargs)
