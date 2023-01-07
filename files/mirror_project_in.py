#!/usr/bin/env python

from __future__ import print_function, absolute_import
import os
import argparse

import pagure.config
import pagure.lib.model as model
import pagure.lib.model_base
import pagure.lib.notify
import pagure.lib.query

if "PAGURE_CONFIG" not in os.environ and os.path.exists(
    "/etc/pagure/pagure.cfg"
):
    print("Using configuration file `/etc/pagure/pagure.cfg`")
    os.environ["PAGURE_CONFIG"] = "/etc/pagure/pagure.cfg"

_config = pagure.config.reload_config()


def main(debug=False):
    """The function pulls in all the changes from upstream"""

    session = pagure.lib.model_base.create_session(_config["DB_URL"])
    projects = (
        session.query(model.Project)
        .filter(model.Project.mirrored_from is not None)
        .all()
    )

    for project in projects:
        if debug:
            print("Mirrorring %s" % project.fullname)
        try:
            pagure.lib.git.mirror_pull_project(session, project, debug=debug)
        except Exception as err:
            print("ERROR: %s" % err)

    session.remove()
    if debug:
        print("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script to PULL external repos into local (mirroring)"
    )
    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="Print the debugging output",
    )
    args = parser.parse_args()
    main(debug=args.debug)
