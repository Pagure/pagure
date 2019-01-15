# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session


CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_label)s",
    # Checks are currently buggy and prevent us from naming them correctly
    # "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
    "uq": "%(table_name)s_%(column_0_name)s_key",
}

BASE = declarative_base(
    metadata=sqlalchemy.MetaData(naming_convention=CONVENTION))


SESSIONMAKER = None


def create_session(db_url=None, debug=False, pool_recycle=3600):
    """ Create the Session object to use to query the database.

    :arg db_url: URL used to connect to the database. The URL contains
    information with regards to the database engine, the host to connect
    to, the user and password and the database name.
      ie: <engine>://<user>:<password>@<host>/<dbname>
    :kwarg debug: a boolean specifying whether we should have the verbose
        output of sqlalchemy or not.
    :return a Session that can be used to query the database.

    """
    global SESSIONMAKER

    if SESSIONMAKER is None or (
        db_url and db_url != ("%s" % SESSIONMAKER.kw["bind"].engine.url)
    ):
        if db_url is None:
            raise ValueError("First call to create_session needs db_url")
        if db_url.startswith("postgres"):  # pragma: no cover
            engine = sqlalchemy.create_engine(
                db_url,
                echo=debug,
                pool_recycle=pool_recycle,
                client_encoding="utf8",
            )
        else:  # pragma: no cover
            engine = sqlalchemy.create_engine(
                db_url, echo=debug, pool_recycle=pool_recycle
            )

        if db_url.startswith("sqlite:"):
            # Ignore the warning about con_record
            # pylint: disable=unused-argument
            def _fk_pragma_on_connect(dbapi_con, _):  # pragma: no cover
                """ Tries to enforce referential constraints on sqlite. """
                dbapi_con.execute("pragma foreign_keys=ON")

            sqlalchemy.event.listen(engine, "connect", _fk_pragma_on_connect)
        SESSIONMAKER = sessionmaker(bind=engine)

    scopedsession = scoped_session(SESSIONMAKER)
    BASE.metadata.bind = scopedsession
    return scopedsession
