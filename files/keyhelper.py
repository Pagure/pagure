#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

from __future__ import unicode_literals, print_function

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
from pagure.config import config as pagure_config
from pagure.lib.model import User, DeployKey


# Get the arguments
# Expect sshd config:
# AuthorizedKeysCommand: <scriptpath> "%u" "%h" "%t" "%f"
# <us> <username> <homedir> <keytype> <fingerprint>
# At this moment, we ignore the homedir and fingerprint, since looking
# up a key by fingerprint would require some model changes (ssh keys would
#   need to be stored in a fashion like DeployKeys).
# But to not break installations in the future, we should ask installations
# to set up sshd in a way that it will work if we use them in the future.
if len(sys.argv) < 5:
    print("Invalid call, too few arguments", file=sys.stderr)
    sys.exit(1)


username, userhome, keytype, fingerprint = sys.argv[1:5]
username_lookup = pagure_config["SSH_KEYS_USERNAME_LOOKUP"]
expect_username = pagure_config["SSH_KEYS_USERNAME_EXPECT"]


if username in pagure_config["SSH_KEYS_USERNAME_FORBIDDEN"]:
    print("User is forbidden for keyhelper.", file=sys.stderr)
    sys.exit(1)


if not username_lookup:
    if not expect_username:
        print("Pagure keyhelper configured incorrectly", file=sys.stderr)
        sys.exit(1)

    if username != expect_username:
        # Nothing to look up, this user is not git-related
        sys.exit(0)


session = pagure.lib.create_session(pagure_config["DB_URL"])
if not session:
    print("Unable to get database access")
    sys.exit(1)


# First try to figure out if this is a deploykey.
# We can look those up very quickly, since those are already
# indexed by key fingerprint.
query = session.query(DeployKey).filter(
    DeployKey.ssh_search_key == fingerprint
)
for dkey in query.all():
    keyenv = {
        "username": "deploykey_%s_%s"
        % (werkzeug.secure_filename(dkey.project.fullname), dkey.id)
    }
    print(
        "%s %s"
        % (pagure_config["SSH_KEYS_OPTIONS"] % keyenv, dkey.public_ssh_key)
    )
    sys.exit(0)


# Now look if it's a normal user
query = session.query(User)
if username_lookup:
    query = query.filter(User.user == username)

for user in query.all():
    for key in user.public_ssh_key.split("\n"):
        # Make slightly more sane
        key = key.strip()
        # Check if this could even be a valid key
        key = key.split(" ")
        # Should be at the very least ["<keytype>", "<key"], e.g. ["ssh-rsa", "...."]
        if len(key) < 2:
            continue
        # If the keytype doesn't match, just ignore the key
        if key[0] != keytype:
            continue
        # Build up some variables to use in the ssh key options
        keyenv = {"username": user.username}
        # This is a possible key, print it
        print(
            "%s %s %s"
            % (pagure_config["SSH_KEYS_OPTIONS"] % keyenv, key[0], key[1])
        )
