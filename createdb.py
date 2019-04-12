#!/usr/bin/env python

from __future__ import print_function, unicode_literals, absolute_import

import argparse
import sys
import os


parser = argparse.ArgumentParser(
    description="Create/Update the Pagure database"
)
parser.add_argument(
    "--config",
    "-c",
    dest="config",
    help="Configuration file to use for pagure.",
)
parser.add_argument(
    "--initial",
    "-i",
    dest="alembic_cfg",
    help="With this option, the database will be automatically stamped to "
    "the latest version according to alembic. Point to the alembic.ini "
    "file to use.",
)


args = parser.parse_args()

if args.config:
    config = args.config
    if not config.startswith("/"):
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        config = os.path.join(here, config)
    os.environ["PAGURE_CONFIG"] = config


if args.alembic_cfg:
    if not args.alembic_cfg.endswith("alembic.ini"):
        print("--initial should point to the alembic.ini file to use.")
        sys.exit(1)
    if not os.path.exists(args.alembic_cfg):
        print("The file `{0}` could not be found".format(args.alembic_cfg))
        sys.exit(2)


import pagure.config
from pagure.lib import model

_config = pagure.config.reload_config()

model.create_tables(
    _config["DB_URL"],
    _config.get("PATH_ALEMBIC_INI", args.alembic_cfg),
    acls=_config.get("ACLS", {}),
    debug=True,
)
