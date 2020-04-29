#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

from __future__ import unicode_literals, print_function, absolute_import

import sys
import os

import requests

# Since this is run by sshd, we don't have a way to set environment
# variables ahead of time
if "PAGURE_CONFIG" not in os.environ and os.path.exists(
    "/etc/pagure/pagure.cfg"
):
    os.environ["PAGURE_CONFIG"] = "/etc/pagure/pagure.cfg"

# Here starts the code
from pagure.config import config as pagure_config


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


pagure_url = pagure_config["APP_URL"].rstrip("/")
url = "%s/pv/ssh/lookupkey/" % pagure_url
data = {"search_key": fingerprint}
if username_lookup:
    data["username"] = username
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

if not result["found"]:
    # Everything OK, key just didn't exist.
    sys.exit(0)

print(
    "%s %s"
    % (pagure_config["SSH_KEYS_OPTIONS"] % result, result["public_key"])
)
