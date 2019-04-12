# -*- coding: utf-8 -*-
"""
Tests for :module:`pagure.lib.mimetype`.
"""

from __future__ import unicode_literals, absolute_import

import os
import unittest
import sys

from pagure.lib import mimetype

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)


class TestMIMEType(unittest.TestCase):
    def test_guess_type(self):
        dataset = [
            ("hello.html", None, "text/html", None),
            ("hello.html", b"#!", "text/html", "ascii"),
            ("hello", b"#!", "text/plain", "ascii"),
            ("hello.jpg", None, "image/jpeg", None),
            ("hello.jpg", b"#!", "image/jpeg", None),
            ("hello.jpg", b"\0", "image/jpeg", None),
            (None, "😋".encode("utf-8"), "text/plain", "utf-8"),
            ("hello", b"\0", "application/octet-stream", None),
            ("hello", None, None, None),
        ]
        for data in dataset:
            result = mimetype.guess_type(data[0], data[1])
            self.assertEqual(
                (data[2], data[3]),
                result,
                "Wrong mimetype for filename %r and content %r"
                % (data[0], data[1]),
            )

    def test_get_html_file_headers(self):
        result = mimetype.get_type_headers("hello.html", None)
        expected = {
            "Content-Type": "application/octet-stream",
            "Content-Disposition": "attachment",
            "X-Content-Type-Options": "nosniff",
        }
        self.assertEqual(result, expected)

    def test_get_normal_headers(self):
        dataset = [
            ("hello", b"#!", "text/plain; charset=ascii"),
            ("hello.jpg", None, "image/jpeg"),
            ("hello.jpg", b"#!", "image/jpeg"),
            ("hello.jpg", b"\0", "image/jpeg"),
            (None, "😋".encode("utf-8"), "text/plain; charset=utf-8"),
            ("hello", b"\0", "application/octet-stream"),
        ]
        for data in dataset:
            result = mimetype.get_type_headers(data[0], data[1])
            self.assertEqual(
                result["Content-Type"],
                data[2],
                "Wrong Content-Type for filename %r and content %r"
                % (data[0], data[1]),
            )

    def test_get_none_header(self):
        self.assertIsNone(mimetype.get_type_headers("hello", None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
