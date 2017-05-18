# -*- coding: utf-8 -*-
"""
Tests for :module:`pagure.lib.mimetype`.
"""

import os
import unittest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

from pagure.lib import mimetype
from pagure import exceptions


class TestMIMEType(unittest.TestCase):
    def test_guess_type(self):
        dataset = [
            ('hello.html', None, 'text/html', None),
            ('hello.html', '#!', 'text/html', 'ascii'),
            ('hello', '#!', 'text/plain', 'ascii'),
            ('hello.jpg', None, 'image/jpeg', None),
            ('hello.jpg', '#!', 'image/jpeg', None),
            ('hello.jpg', '\0', 'image/jpeg', None),
            (None, '😋', 'text/plain', 'utf-8'),
            ('hello', '\0', 'application/octet-stream', None),
            ('hello', None, None, None)
        ]
        for data in dataset:
            result = mimetype.guess_type(data[0], data[1])
            self.assertEqual((data[2], data[3]), result)

    def test_get_html_file_headers(self):
        result = mimetype.get_type_headers('hello.html', None)
        expected = {
            'Content-Type': 'application/octet-stream',
            'Content-Disposition': 'attachment',
            'X-Content-Type-Options': 'nosniff'
        }
        self.assertEqual(result, expected)

    def test_get_normal_headers(self):
        dataset = [
            ('hello', '#!', 'text/plain; charset=ascii'),
            ('hello.jpg', None, 'image/jpeg'),
            ('hello.jpg', '#!', 'image/jpeg'),
            ('hello.jpg', '\0', 'image/jpeg'),
            (None, '😋', 'text/plain; charset=utf-8'),
            ('hello', '\0', 'application/octet-stream')
        ]
        for data in dataset:
            result = mimetype.get_type_headers(data[0], data[1])
            self.assertEqual(result['Content-Type'], data[2])

    def test_get_none_header(self):
        self.assertIsNone(mimetype.get_type_headers('hello', None))


if __name__ == '__main__':
    unittest.main(verbosity=2)
