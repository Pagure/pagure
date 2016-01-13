# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import random
import string
import bcrypt

from pagure.lib import model
from kitchen.text.converters import to_unicode, to_bytes


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


def get_users_by_group(session, group):
    ''' Return the list of users for a specified group.

    :arg session: the session with which to connect to the database.

    '''
    query = session.query(
        model.User
    ).filter(
        model.User.id == model.PagureUserGroup.user_id
    ).filter(
        model.PagureUserGroup.group_id == model.PagureGroup.id
    ).filter(
        model.PagureGroup.group_name == group
    ).order_by(
        model.User.user
    )

    return query.all()

def generate_hashed_value(password):
    """ Generate hash value for password
    """
    return '$2$' + bcrypt.hashpw(to_unicode(password), bcrypt.gensalt())

def retrieve_hashed_value(password, hash_value):
    """ Retrieve hash value to compare
    """
    return bcrypt.hashpw(to_unicode(password), hash_value)

def get_password(entered_password, user_password, version):
    """ Version checking and returning the password
    """
    if version == '2':
         password = retrieve_hashed_value(
                entered_password, user_password)
         return password

    elif version == '1':
            password = '%s%s' % (to_unicode(entered_password),
                                        APP.config.get('PASSWORD_SEED', None))
            password = hashlib.sha512(password).hexdigest()
            return password
