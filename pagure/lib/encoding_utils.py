# -*- coding: utf-8 -*-
"""
(c) 2016 - Copyright Red Hat Inc

Authors:
    Jeremy Cline <jeremy@jcline.org>

This module contains utilities to deal with character encoding. Git blobs are
just binary data and do not have a character encoding associated with them, so
the repetitive task of identifying the character encoding and decoding the
content to unicode is implemented here.
"""

from __future__ import unicode_literals, division, absolute_import
from collections import namedtuple
import logging

from chardet import universaldetector


_log = logging.getLogger(__name__)

Guess = namedtuple('Guess', ['encoding', 'confidence'])


def guess_encoding(data):
    """
    Attempt to guess the text encoding used for the given data.

    This uses chardet to guess the encoding, but biases the results towards
    UTF-8. There are cases where chardet cannot know the encoding and
    therefore is occasionally wrong. In those cases it was decided that it
    would be better to err on the side of UTF-8 rather than ISO-8859-*.
    However, it is important to be aware that this also guesses and _will_
    misclassify ISO-8859-* encoded text as UTF-8 in some cases.

    The discussion that lead to this decision can be found at
    https://pagure.io/pagure/issue/891.

    :param data: An array of bytes to treat as text data
    :type  data: bytes
    """
    encodings = detect_encodings(data)

    # Boost utf-8 confidence to heavily skew on the side of utf-8. chardet
    # confidence is between 1.0 and 0 (inclusive), so this boost remains within
    # the expected range from chardet. This requires chardet to be very
    # unconfident in utf-8 and very confident in something else for utf-8 to
    # not be selected.
    if 'utf-8' in encodings and encodings['utf-8'] > 0.0:
        encodings['utf-8'] = (encodings['utf-8'] + 2.0) / 3.0
    encodings = [Guess(encoding, confidence)
                 for encoding, confidence in encodings.items()]
    sorted_encodings = sorted(
        encodings, key=lambda guess: guess.confidence, reverse=True)

    _log.debug('Possible encodings: ' + str(sorted_encodings))
    return sorted_encodings[0].encoding


def detect_encodings(data):
    """
    Analyze the provided data for possible character encodings.

    This simply wraps chardet and extracts all the potential encodings it
    considered before deciding on a particular result.

    :param data: An array of bytes to treat as text data
    :type  data: bytes

    :return: A dictionary mapping possible encodings to confidence levels
    :rtype:  dict
    """
    if not data:
        # It's an empty string so we can safely say it's ascii
        return {'ascii': 1.0}

    # We can't use ``chardet.detect`` because we want to dig in the internals
    # of the detector to bias the utf-8 result.
    detector = universaldetector.UniversalDetector()
    detector.reset()
    detector.feed(data)
    result = detector.close()
    encodings = {result['encoding']: result['confidence']}
    for prober in detector._mCharSetProbers:
        if prober:
            encodings[prober.get_charset_name()] = prober.get_confidence()

    return encodings


def decode(data):
    """
    Guesses the encoding using ``guess_encoding`` and decodes the data.

    :param data: An array of bytes to treat as text data
    :type  data: bytes

    :return: A unicode string that has been decoded using the encoding provided
             by ``guest_encoding``
    :rtype: unicode str
    """
    encoding = guess_encoding(data)
    return data.decode(encoding)
