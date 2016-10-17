# -*- coding: utf-8 -*-
"""
Tests for :module:`pagure.lib.encoding_utils`.
"""

import chardet
import unittest

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

    def test_decode(self):
        data = u'Šabata'
        self.assertEqual(data, encoding_utils.decode(data.encode('utf-8')))


if __name__ == '__main__':
    unittest.main()
