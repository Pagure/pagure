# -*- coding: utf-8 -*-
"""
Tests for :module:`pagure.lib.encoding_utils`.
"""

import chardet
import os
import unittest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

from pagure.lib import encoding_utils


class TestGuessEncoding(unittest.TestCase):

    def test_guess_encoding_ascii(self):
        """
        Assert when ascii-only data is provided ascii is the guessed encoding.
        """
        data = u'Twas bryllyg, and the slythy toves did gyre and gymble'
        result = encoding_utils.guess_encoding(data.encode('ascii'))
        self.assertEqual(result, 'ascii')

    def test_guess_encoding_favor_utf_8(self):
        """
        Test that strings that could be UTF-8 or ISO-8859-2 result in UTF-8.
        """
        data = u'Šabata'.encode('utf-8')
        result = encoding_utils.guess_encoding(data)
        chardet_result = chardet.detect(data)
        self.assertEqual(result, 'utf-8')
        self.assertEqual(chardet_result['encoding'], 'ISO-8859-2')

    def test_guess_encoding_no_data(self):
        """ Test encoding_utils.guess_encoding() with an emtpy string """
        result = encoding_utils.guess_encoding(u''.encode('utf-8'))
        self.assertEqual(result, 'ascii')


class TestGuessEncodings(unittest.TestCase):

    def test_guess_encodings(self):
        """ Test the encoding_utils.guess_encodings() method. """
        data = u'Šabata'.encode('utf-8')
        result = encoding_utils.guess_encodings(data)
        chardet_result = chardet.detect(data)
        self.assertEqual(
            [encoding.encoding for encoding in result],
            ['utf-8', 'ISO-8859-2', 'windows-1252'])
        self.assertEqual(chardet_result['encoding'], 'ISO-8859-2')

    def test_guess_encodings_no_data(self):
        """ Test encoding_utils.guess_encodings() with an emtpy string """
        result = encoding_utils.guess_encodings(u''.encode('utf-8'))
        self.assertEqual(
            [encoding.encoding for encoding in result],
            ['ascii'])

class TestDecode(unittest.TestCase):

    def test_decode(self):
        """ Test encoding_utils.decode() """
        data = u'Šabata'
        self.assertEqual(data, encoding_utils.decode(data.encode('utf-8')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
