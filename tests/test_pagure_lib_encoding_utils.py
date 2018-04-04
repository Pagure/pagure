# -*- coding: utf-8 -*-
"""
Tests for :module:`pagure.lib.encoding_utils`.
"""

from __future__ import unicode_literals

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
        data = 'Twas bryllyg, and the slythy toves did gyre and gymble'
        result = encoding_utils.guess_encoding(data.encode('ascii'))
        self.assertEqual(result, 'ascii')

    def test_guess_encoding_favor_utf_8(self):
        """
        Test that strings that could be UTF-8 or ISO-8859-* result in UTF-8.

        python-chardet-3.0.4-2.fc27.noarch detects it as ISO-8859-9
        python-chardet-2.2.1-1.el7_1.noarch detects it as ISO-8859-2
        """
        data = 'Šabata'.encode('utf-8')
        result = encoding_utils.guess_encoding(data)
        chardet_result = chardet.detect(data)
        self.assertEqual(result, 'utf-8')
        if chardet.__version__[0] == '3':
            self.assertEqual(chardet_result['encoding'], 'ISO-8859-9')
        else:
            self.assertEqual(chardet_result['encoding'], 'ISO-8859-2')

    def test_guess_encoding_no_data(self):
        """ Test encoding_utils.guess_encoding() with an empty string """
        result = encoding_utils.guess_encoding(''.encode('utf-8'))
        self.assertEqual(result, 'ascii')


class TestGuessEncodings(unittest.TestCase):

    def test_guess_encodings(self):
        """ Test the encoding_utils.guess_encodings() method. """
        data = 'Šabata'.encode('utf-8')
        result = encoding_utils.guess_encodings(data)
        chardet_result = chardet.detect(data)
        if chardet.__version__[0] == '3':
            # The first three have different confidence values
            self.assertListEqual(
                [encoding.encoding for encoding in result][:3],
                ['utf-8', 'ISO-8859-9', 'ISO-8859-1']
            )
            # This is the one with the least confidence
            self.assertEqual(result[-1].encoding, 'windows-1255')
            # The values in the middle of the list all have the same confidence
            # value and can't be sorted reliably: use sets.
            self.assertEqual(
                set([encoding.encoding for encoding in result]),
                set(['utf-8', 'ISO-8859-9', 'ISO-8859-1', 'MacCyrillic',
                     'IBM866', 'TIS-620', 'EUC-JP', 'EUC-KR', 'GB2312',
                     'KOI8-R', 'Big5', 'IBM855', 'ISO-8859-7', 'SHIFT_JIS',
                     'windows-1253', 'CP949', 'EUC-TW', 'ISO-8859-5',
                     'windows-1251', 'windows-1255'])
            )
            self.assertEqual(chardet_result['encoding'], 'ISO-8859-9')
        else:
            self.assertListEqual(
                [encoding.encoding for encoding in result],
                ['utf-8', 'ISO-8859-2', 'windows-1252'])
            self.assertEqual(chardet_result['encoding'], 'ISO-8859-2')

    def test_guess_encodings_no_data(self):
        """ Test encoding_utils.guess_encodings() with an emtpy string """
        result = encoding_utils.guess_encodings(''.encode('utf-8'))
        self.assertEqual(
            [encoding.encoding for encoding in result],
            ['ascii'])

class TestDecode(unittest.TestCase):

    def test_decode(self):
        """ Test encoding_utils.decode() """
        data = 'Šabata'
        self.assertEqual(data, encoding_utils.decode(data.encode('utf-8')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
