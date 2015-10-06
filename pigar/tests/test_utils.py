# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import unittest
import os
import random

from .helper import CaptureOutput
from ..utils import (
    Dict, print_table, parse_reqs, compare_version, cmp_to_key
)


class DictTests(unittest.TestCase):

    def test_init_with_kwargs(self):
        d = Dict(foo='foo', bar='bar')
        self.assertIn('foo', d)
        self.assertIn('bar', d)

    def test_init_with_zip_list(self):
        d = Dict(zip(('foo', 'bar'), ('bar', 'foo')))
        self.assertIn('foo', d)
        self.assertIn('bar', d)

    def test_init_with_dict(self):
        d = Dict({'foo': 'foo', 'bar': 'bar'})
        self.assertIn('foo', d)
        self.assertIn('bar', d)

    def test_getattr(self):
        d = Dict(foo='bar', bar='foo')
        self.assertEqual(d.foo, 'bar')
        self.assertEqual(d.bar, 'foo')

    def test_attr_error(self):
        d = Dict({'foo': 'bar'})
        with self.assertRaises(AttributeError):
            d.bar


class PrintTableTests(unittest.TestCase):

    def test_default_headers(self):
        rows = [
            ('pigar', '0.5.0', '1.1.1'),
            ('test', '8.0.0', '2.4.8')
        ]
        target = [
            ' ============================',
            '  PACKAGE | CURRENT | LATEST',
            '  --------+---------+-------',
            '  pigar   | 0.5.0   | 1.1.1 ',
            '  test    | 8.0.0   | 2.4.8 ',
            ' ============================'
        ]
        with CaptureOutput() as output:
            print_table(rows)
        self.assertListEqual(output, target)

    def test_custom_headers(self):
        headers = ['PACKAGE', 'VERSION']
        rows = [('pigar', '1.1.1')]
        target = [
            ' ===================',
            '  PACKAGE | VERSION',
            '  --------+--------',
            '  pigar   | 1.1.1  ',
            ' ==================='
        ]
        with CaptureOutput() as output:
            print_table(rows, headers)
        self.assertListEqual(output, target)


class ParseReqsTest(unittest.TestCase):

    def test_parse_reqs(self):
        path = os.path.join(os.path.dirname(__file__),
                            './fake_reqs.txt')
        target = {'a': '4.1.4', 'b': '2.3.0', 'c': ''}
        reqs = parse_reqs(path)
        self.assertDictEqual(reqs, target)


class CompareVersionTests(unittest.TestCase):

    def test_compare_version(self):
        self.assertEqual(compare_version('1.1.1', '1.2.1'), -1)
        self.assertEqual(compare_version('1.10.1', '1.2.1'), 1)
        self.assertEqual(compare_version('1.2', '1.2.1'), -1)
        self.assertEqual(compare_version('1.1.1', '1.1.1'), 0)
        self.assertEqual(compare_version('1.1.1', '1.1.1b'), -1)
        self.assertEqual(compare_version('1.1b2', '1.1a2'), 1)
        self.assertEqual(compare_version('1.1b1', '1.1b2'), -1)
        self.assertEqual(compare_version('1.1b', '1.1b'), 0)

    def test_sort_versions(self):
        target = ['1.1.1', '1.1.1b1', '1.1.1b2', '1.2.1', '1.10.1']
        test = target[:]
        random.shuffle(test)
        self.assertListEqual(sorted(test, key=cmp_to_key(compare_version)),
                             target)
