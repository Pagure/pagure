# -*- coding: utf-8 -*-
"""
Tests for :module:`pagure.lib.encoding_utils`.
"""

from __future__ import unicode_literals, absolute_import

import os
import unittest
import sys

cchardet = None
try:
    import cchardet
except ImportError:
    pass

import chardet

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

from pagure.lib import encoding_utils


class TestGuessEncoding(unittest.TestCase):
    def test_guess_encoding_ascii(self):
        """
        Assert when ascii-only data is provided ascii is the guessed encoding.
        """
        data = "Twas bryllyg, and the slythy toves did gyre and gymble"
        result = encoding_utils.guess_encoding(data.encode("ascii"))
        if cchardet is not None:
            self.assertEqual(result, "ASCII")
        else:
            self.assertEqual(result, "ascii")

    def test_guess_encoding_favor_utf_8(self):
        """
        Test that strings that could be UTF-8 or ISO-8859-* result in UTF-8.

        python-chardet-3.0.4-2.fc27.noarch and above detects it as ISO-8859-9
        python-chardet-2.2.1-1.el7_1.noarch detects it as ISO-8859-2
        """
        data = "Šabata".encode("utf-8")
        result = encoding_utils.guess_encoding(data)
        chardet_result = chardet.detect(data)
        if cchardet:
            self.assertEqual(result, "WINDOWS-1250")
        else:
            self.assertEqual(result, "utf-8")
            if chardet.__version__[0] in ("3", "4", "5"):
                self.assertEqual(chardet_result["encoding"], "ISO-8859-9")
            else:
                self.assertEqual(chardet_result["encoding"], "ISO-8859-2")

    def test_guess_encoding_no_data(self):
        """Test encoding_utils.guess_encoding() with an empty string"""
        result = encoding_utils.guess_encoding("".encode("utf-8"))
        self.assertEqual(result, "ascii")


class TestGuessEncodings(unittest.TestCase):
    def test_guess_encodings(self):
        """Test the encoding_utils.guess_encodings() method."""
        data = "Šabata".encode("utf-8")
        result = encoding_utils.guess_encodings(data)
        chardet_result = chardet.detect(data)
        if cchardet is not None:
            # The last one in the list (which apparently has only one)
            self.assertEqual(result[-1].encoding, "WINDOWS-1250")
        else:
            if chardet.__version__[0] in ("3", "4", "5"):
                # The first three have different confidence values
                expexted_list = ["utf-8", "ISO-8859-9", "ISO-8859-1"]
                # This is the one with the least confidence
                print(result)
                if chardet.__version__ >= '5.1.0':
                    self.assertEqual(result[-1].encoding, "TIS-620")
                else:
                    self.assertEqual(result[-1].encoding, "windows-1255")
                self.assertListEqual(
                    [encoding.encoding for encoding in result][:3],
                    expexted_list,
                )

                # The values in the middle of the list all have the same confidence
                # value and can't be sorted reliably: use sets.
                if chardet.__version__ >= '5.1.0':
                    expected_list = sorted(
                        [
                            "utf-8",
                            "ISO-8859-9",
                            "ISO-8859-1",
                            "MacCyrillic",
                            "IBM866",
                            "TIS-620",
                            "EUC-JP",
                            "EUC-KR",
                            "GB2312",
                            "KOI8-R",
                            "Big5",
                            "IBM855",
                            "ISO-8859-7",
                            "SHIFT_JIS",
                            "windows-1253",
                            "CP949",
                            "EUC-TW",
                            "ISO-8859-5",
                            "windows-1251",
                            "windows-1255",
                            "Johab",  # Added in 5.0.0
                            "MacRoman",  # Added in 5.1.0
                        ]
                    )
                else:
                    expected_list = sorted(
                        [
                            "utf-8",
                            "ISO-8859-9",
                            "ISO-8859-1",
                            "MacCyrillic",
                            "IBM866",
                            "TIS-620",
                            "EUC-JP",
                            "EUC-KR",
                            "GB2312",
                            "KOI8-R",
                            "Big5",
                            "IBM855",
                            "ISO-8859-7",
                            "SHIFT_JIS",
                            "windows-1253",
                            "CP949",
                            "EUC-TW",
                            "ISO-8859-5",
                            "windows-1251",
                            "windows-1255",
                        ]
                    )
                self.assertListEqual(
                    sorted(set([encoding.encoding for encoding in result])),
                    expected_list,
                )
                self.assertEqual(chardet_result["encoding"], "ISO-8859-9")
            else:
                self.assertListEqual(
                    [encoding.encoding for encoding in result],
                    ["utf-8", "ISO-8859-2", "windows-1252"],
                )
                self.assertEqual(chardet_result["encoding"], "ISO-8859-2")

    def test_guess_encodings_no_data(self):
        """Test encoding_utils.guess_encodings() with an emtpy string"""
        result = encoding_utils.guess_encodings("".encode("utf-8"))
        self.assertEqual([encoding.encoding for encoding in result], ["ascii"])


class TestDecode(unittest.TestCase):
    def test_decode(self):
        """Test encoding_utils.decode()"""
        data = (
            "This is a little longer text for testing Šabata's encoding. "
            "With more characters, let's see if it become more clear as to what "
            "encoding should be used for this. We'll include from french words "
            "in there for non-ascii: français, gagné!"
        )
        self.assertEqual(data, encoding_utils.decode(data.encode("utf-8")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
