# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging
import mimetypes
import kitchen.text.converters as ktc
import six

import pagure.lib.encoding_utils


_log = logging.getLogger(__name__)


def guess_type(filename, data):
    '''
    Guess the type of a file based on its filename and data.

    Return value is a tuple (type, encoding) where type or encoding is None
    if it can't be guessed.

    :param filename: file name string
    :param data: file data string
    '''
    mimetype = None
    encoding = None
    if filename:
        mimetype, encoding = mimetypes.guess_type(filename)
    if data:
        if not mimetype:
            if not isinstance(data, six.text_type) and b'\0' in data:
                mimetype = 'application/octet-stream'
            else:
                mimetype = 'text/plain'

        if mimetype.startswith('text/') and not encoding:
            try:
                encoding = pagure.lib.encoding_utils.guess_encoding(
                    ktc.to_bytes(data))
            except pagure.exceptions.PagureException:  # pragma: no cover
                # We cannot decode the file, so bail but warn the admins
                _log.exception('File could not be decoded')

    return mimetype, encoding


def get_type_headers(filename, data):
    '''
    Get the HTTP headers used for downloading or previewing the file.

    If the file is html, it will return headers which make browser start
    downloading.

    :param filename: file name string
    :param data: file data string
    '''
    mimetype, encoding = guess_type(filename, data)
    if not mimetype:
        return None
    headers = {'X-Content-Type-Options': 'nosniff'}
    if 'html' in mimetype or 'javascript' in mimetype or 'svg' in mimetype:
        mimetype = 'application/octet-stream'
        headers['Content-Disposition'] = 'attachment'
    if encoding:
        mimetype += '; charset={encoding}'.format(encoding=encoding)
    headers['Content-Type'] = mimetype
    return headers
