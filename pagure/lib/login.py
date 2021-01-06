# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Farhaan Bukhsh <farhaan@fedoraproject.org>

"""

from __future__ import unicode_literals, absolute_import

try:
    # Provided in Python 3.6+
    from secrets import choice as random_choice
except ImportError:
    # Fall back to SystemRandom, backed by os.urandom
    import random

    random = random.SystemRandom()
    random_choice = random.choice

import string
import hashlib
import bcrypt
import six

import pagure.config
from pagure.lib import model
from cryptography.hazmat.primitives import constant_time


def id_generator(size=15, chars=string.ascii_uppercase + string.digits):
    """Generates a random identifier for the given size and using the
    specified characters.
    If no size is specified, it uses 15 as default.
    If no characters are specified, it uses ascii char upper case and
    digits.
    :arg size: the size of the identifier to return.
    :arg chars: the list of characters that can be used in the
        idenfitier.
    """
    return "".join(random_choice(chars) for x in range(size))


def get_session_by_visitkey(session, sessionid):
    """Return a specified VisitUser via its session identifier (visit_key).

    :arg session: the session with which to connect to the database.

    """
    query = session.query(model.PagureUserVisit).filter(
        model.PagureUserVisit.visit_key == sessionid
    )

    return query.first()


def generate_hashed_value(password):
    """Generate hash value for password.

    :arg password: password for which the hash has to be generated.
    :type password: str (Python 3) or unicode (Python 2)
    :return: a hashed string of characters.
    :rtype: an encoded string(bytes).
    """
    if not isinstance(password, six.text_type):
        raise ValueError("Password supplied is not unicode text")

    return (
        b"$2$" + bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    ).decode("utf-8")


def check_password(entered_password, user_password, seed=None):
    """Version checking and returning the password

    :arg entered_password: password entered by the user.
    :type entered_password: str (Python 3) or unicode (Python 2)
    :arg user_password: the hashed string fetched from the database.
    :type user_password: bytes
    :return: a Boolean depending upon the entered_password, True if the
             password matches
    """
    if not isinstance(entered_password, six.text_type):
        raise ValueError("Entered password is not unicode text")
    if isinstance(user_password, six.text_type):
        user_password = user_password.encode("utf-8")

    if not user_password.count(b"$") >= 2:
        raise pagure.exceptions.PagureException(
            "Password of unknown version found in the database"
        )

    _, version, user_password = user_password.split(b"$", 2)

    if version == b"2":
        password = bcrypt.hashpw(
            entered_password.encode("utf-8"), user_password
        )
    elif version == b"1":
        password = "%s%s" % (entered_password, seed)
        password = (
            hashlib.sha512(password.encode("utf-8"))
            .hexdigest()
            .encode("utf-8")
        )

    else:
        raise pagure.exceptions.PagureException(
            "Password of unknown version found in the database"
        )

    return constant_time.bytes_eq(password, user_password)


def check_username_and_password(session, username, password):
    """Check if the provided username and password match what is in the
    database and raise an pagure.exceptions.PagureException if that is
    not the case.
    """

    user_obj = pagure.lib.query.search_user(session, username=username)
    if not user_obj:
        raise pagure.exceptions.PagureException(
            "Username or password invalid."
        )

    try:
        password_checks = check_password(
            password,
            user_obj.password,
            seed=pagure.config.config.get("PASSWORD_SEED", None),
        )
    except pagure.exceptions.PagureException:
        raise pagure.exceptions.PagureException(
            "Username or password invalid."
        )

    if not password_checks:
        raise pagure.exceptions.PagureException(
            "Username or password invalid."
        )

    elif user_obj.token:
        raise pagure.exceptions.PagureException(
            "Invalid user, did you confirm the creation with the url "
            "provided by email?"
        )

    else:
        password = user_obj.password
        if not isinstance(password, six.text_type):
            password = password.decode("utf-8")
        if not password.startswith("$2$"):
            user_obj.password = generate_hashed_value(password)
            session.add(user_obj)
            session.flush()
