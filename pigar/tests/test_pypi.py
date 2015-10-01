# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import unittest
import os
import sys

from ..pypi import _extract_html
from ..unpack import unpack_html


class ExtractHtmlTest(unittest.TestCase):

    def test_extract_html(self):
        path = os.path.join(os.path.dirname(__file__),
                            './fake_simple_html.txt')
        with open(path) as f:
            names = _extract_html(f.read())
        self.assertListEqual(names, 'a b c d e f g'.split())


class UnpackHtmlTest(unittest.TestCase):

    @unittest.skipIf(sys.version_info[0] != 3, 'Not python 3.x')
    def test_py3_unpack_html(self):
        data = bytes('cde', 'utf-8')
        self.assertEqual(unpack_html(data), data.decode('utf-8'))

    @unittest.skipIf(sys.version_info[0] != 2, 'Not python 2.x')
    def test_py2_unpack_html(self):
        data = 'abc'
        self.assertEqual(unpack_html(data), data.decode('utf-8'))
