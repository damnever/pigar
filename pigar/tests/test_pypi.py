# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import unittest
import os

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

    def test_unpack_html(self):
        if not isinstance(u'', type('')):
            data = 'abc'
        else:
            data = bytes('cde', 'utf-8')
        self.assertEqual(unpack_html(data), data.decode('utf-8'))
