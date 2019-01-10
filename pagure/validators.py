import re

import six
from wtforms import validators


class EmailValidator(object):
    """Validates wtform email field"""

    def __init__(self, message="The field data was not an email"):
        self._message = message

    def __call__(self, form, email):
        if not isinstance(email.data, six.text_type):
            raise validators.ValidationError(
                "Email fields should be of text type. Found {0}".format(
                    type(email.data)
                )
            )
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email.data):
            raise validators.ValidationError(self._message)
