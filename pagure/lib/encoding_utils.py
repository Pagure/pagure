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

try:
    import cchardet
    from cchardet import __version__ as ch_version
except ImportError:
    cchardet = None
    from chardet import universaldetector, __version__ as ch_version

from pagure.exceptions import PagureEncodingException


_log = logging.getLogger(__name__)

Guess = namedtuple("Guess", ["encoding", "confidence"])


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
        return {"ascii": 1.0}

    # We can't use ``chardet.detect`` because we want to dig in the internals
    # of the detector to bias the utf-8 result.
    if cchardet is not None:
        detector = cchardet.UniversalDetector()
        detector.reset()
        detector.feed(data)
        detector.close()
        result = detector.result
    else:
        detector = universaldetector.UniversalDetector()
        detector.reset()
        detector.feed(data)
        result = detector.close()

    if not result or not result["encoding"]:
        return {"utf-8": 1.0}
    encodings = {result["encoding"]: result["confidence"]}

    if cchardet:
        return encodings

    if ch_version[0] in ("3", "4"):
        for prober in detector._charset_probers:
            if hasattr(prober, "probers"):
                for prober in prober.probers:
                    encodings[prober.charset_name] = prober.get_confidence()
            else:
                encodings[prober.charset_name] = prober.get_confidence()
    else:
        for prober in detector._mCharSetProbers:
            if prober:
                encodings[prober.get_charset_name()] = prober.get_confidence()

    return encodings


def guess_encodings(data):
    """
    List all the possible encoding found for the given data.

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
    :return: A dictionary mapping possible encodings to confidence levels
    :rtype:  dict

    """
    encodings = detect_encodings(data)

    # Boost utf-8 confidence to heavily skew on the side of utf-8. chardet
    # confidence is between 1.0 and 0 (inclusive), so this boost remains within
    # the expected range from chardet. This requires chardet to be very
    # unconfident in utf-8 and very confident in something else for utf-8 to
    # not be selected.
    if "utf-8" in encodings and encodings["utf-8"] > 0.0:
        encodings["utf-8"] = (encodings["utf-8"] + 2.0) / 3.0
    encodings = [
        Guess(encoding, confidence)
        for encoding, confidence in encodings.items()
    ]
    sorted_encodings = sorted(
        encodings, key=lambda guess: guess.confidence, reverse=True
    )

    _log.debug("Possible encodings: %s" % sorted_encodings)
    return sorted_encodings


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
    :return: A string of the best encoding found
    :rtype: str
    :raises PagureException: if no encoding was found that the data could
        be decoded into

    """
    encodings = guess_encodings(data)

    for encoding in encodings:
        _log.debug("Trying encoding: %s", encoding)
        try:
            data.decode(encoding.encoding)
            return encoding.encoding
        except (UnicodeDecodeError, TypeError):
            # The first error is thrown when we failed to decode in that
            # encoding, the second when encoding.encoding returned None
            pass
    raise PagureEncodingException("No encoding could be guessed for this file")


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
