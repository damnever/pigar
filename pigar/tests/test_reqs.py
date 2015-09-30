# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import os
import sys
import unittest

from ..__main__ import extract_reqs
from ..reqs import is_stdlib


class ReqsTests(unittest.TestCase):

    def setUp(self):
        self._installed_packages = {
            'foo': ('Foo', '0.1.0'),
            'bar': ('Bar', '1.1.1')
        }
        if sys.version_info[0] == 2:
            self._installed_packages.update({'foobar': ('FooBar', '3.6.9')})
        self._path = os.path.join(os.path.dirname(__file__), 'imports_example/')

    def tearDown(self):
        del self._installed_packages
        del self._path

    @unittest.skipIf(sys.version_info[0] != 3, 'Not python 3.x')
    def test_py3_reqs(self):
        reqs, guess = extract_reqs(self._path, self._installed_packages)
        self.assertDictEqual(reqs, dict(self._installed_packages.values()))
        # Assume 'foobar' is Py3 builtin package, no need install.
        self.assertListEqual(
            sorted(guess),
            sorted(['Queue', '__builtin__', 'foobar', 'urlparse']))

    @unittest.skipIf(sys.version_info[0] != 2, 'Not python 2.x')
    def test_py2_reqs(self):
        reqs, guess = extract_reqs(self._path, self._installed_packages)
        self.assertDictEqual(reqs, dict(self._installed_packages.values()))
        self.assertListEqual(guess, ['builtins'])


class StdlibTest(unittest.TestCase):

    def test_stdlib(self):
        self.assertTrue(is_stdlib('os'))
        self.assertTrue(is_stdlib('sys'))
