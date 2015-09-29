# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import unittest
import os

from ..pypi import _extract_html


class ExtractHtmlTest(unittest.TestCase):

    def test_extract_html(self):
        path = os.path.join(os.path.dirname(__file__),
                            './fake_simple_html.txt')
        with open(path) as f:
            names = _extract_html(f.read())
        self.assertListEqual(names, 'a b c d e f g'.split())
