# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Farhaan Bukhsh <farhaan.bukhsh@gmail.com>

"""

import random
import string
import bcrypt

import hashlib
import pagure
from pagure.lib import model
from kitchen.text.converters import to_unicode, to_bytes
from cryptography.hazmat.primitives import constant_time


def id_generator(size=15, chars=string.ascii_uppercase + string.digits):
    """ Generates a random identifier for the given size and using the
    specified characters.
    If no size is specified, it uses 15 as default.
    If no characters are specified, it uses ascii char upper case and
    digits.
    :arg size: the size of the identifier to return.
    :arg chars: the list of characters that can be used in the
        idenfitier.
    """
    return ''.join(random.choice(chars) for x in range(size))


def get_session_by_visitkey(session, sessionid):
    ''' Return a specified VisitUser via its session identifier (visit_key).

    :arg session: the session with which to connect to the database.

    '''
    query = session.query(
        model.PagureUserVisit
    ).filter(
        model.PagureUserVisit.visit_key == sessionid
    )

    return query.first()


def generate_hashed_value(password):
    """ Generate hash value for password
    """
    return '$2$' + bcrypt.hashpw(to_unicode(password), bcrypt.gensalt())


def check_password(entered_password, user_password, seed=None):
    """ Version checking and returning the password
    """
    if not user_password.count('$') >= 2:
        raise pagure.exceptions.PagureException(
            'Password of unknown version found in the database'
        )

    _, version, user_password = user_password.split('$', 2)

    if version == '2':
        password = bcrypt.hashpw(to_unicode(entered_password), user_password)

    elif version == '1':
        password = '%s%s' % (to_unicode(entered_password), seed)
        password = hashlib.sha512(password).hexdigest()

    else:
        raise pagure.exceptions.PagureException(
            'Password of unknown version found in the database'
        )

    return constant_time.bytes_eq(
        to_bytes(password), to_bytes(user_password))
