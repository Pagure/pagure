# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base

CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_label)s",
    # Checks are currently buggy and prevent us from naming them correctly
    # "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
    "uq": "%(table_name)s_%(column_0_name)s_key",
}

BASE = declarative_base(metadata=MetaData(naming_convention=CONVENTION))
