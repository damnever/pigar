# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import unittest
import os
import random

from .helper import CaptureOutput
from ..helpers import (
    Dict, print_table, ParsedRequirement, parse_requirements, parse_git_config,
    compare_version, cmp_to_key
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
        rows = [('pigar', '0.5.0', '1.1.1'), ('test', '8.0.0', '2.4.8')]
        target = [
            ' ============================', '  PACKAGE | CURRENT | LATEST',
            '  --------+---------+-------', '  pigar   | 0.5.0   | 1.1.1 ',
            '  test    | 8.0.0   | 2.4.8 ', ' ============================'
        ]
        with CaptureOutput() as output:
            print_table(rows, headers=['PACKAGE', 'CURRENT', 'LATEST'])
        self.assertListEqual(output, target)

    def test_custom_headers(self):
        headers = ['PACKAGE', 'VERSION']
        rows = [('pigar', '1.1.1')]
        target = [
            ' ===================', '  PACKAGE | VERSION',
            '  --------+--------', '  pigar   | 1.1.1  ',
            ' ==================='
        ]
        with CaptureOutput() as output:
            print_table(rows, headers)
        self.assertListEqual(output, target)


class ParseReqsTest(unittest.TestCase):

    def test_parse_requirements(self):
        path = os.path.join(os.path.dirname(__file__), './fake_reqs.txt')
        expected = [
            ParsedRequirement(
                name='a',
                specifier='==4.1.4',
                url='',
            ),
            ParsedRequirement(
                name='b',
                specifier='==2.3.0',
                url='',
            ),
            ParsedRequirement(
                name='c',
                specifier='',
                url='',
            ),
            ParsedRequirement(
                name='d',
                specifier='',
                url='https://example.com/d/d/archive/refs/tags/1.0.0.zip',
            ),
            ParsedRequirement(
                name='e',
                specifier='==2.8.*,>=2.8.1',
                url='',
            ),
            ParsedRequirement(
                name='another-in-ref',
                specifier='',
                url='',
            ),
        ]
        reqs = parse_requirements(path)
        self.assertListEqual(list(reqs), expected)


class ParseGitConfigTest(unittest.TestCase):

    def test_parse_gitconfig(self):
        path = os.path.join(os.path.dirname(__file__), 'fake_git_conf')
        target = {
            'core': {
                'editor': 'vim'
            },
            'user': {
                'email': 'pigar@example.com',
                'name': 'Pigar'
            },
            'credential': {
                'helper': 'cache--timeout=3600'
            }
        }
        reqs = parse_git_config(path)
        self.assertDictEqual(reqs, target)


class CompareVersionTests(unittest.TestCase):

    def test_compare_version(self):
        self.assertEqual(compare_version('1.1.1', '1.2.1'), -1)
        self.assertEqual(compare_version('1.10.1', '1.2.1'), 1)
        self.assertEqual(compare_version('1.2', '1.2.1'), -1)
        self.assertEqual(compare_version('1.1.1', '1.1.1'), 0)
        self.assertEqual(compare_version('1.1.1', '1.1.1b'), 1)
        self.assertEqual(compare_version('1.1b2', '1.1a2'), 1)
        self.assertEqual(compare_version('1.1b1', '1.1b2'), -1)
        self.assertEqual(compare_version('1.1b', '1.1b'), 0)
        self.assertEqual(compare_version('1.1b', '1.1b1.post2'), -1)

    def test_sort_versions(self):
        target = [
            '1.1.dev1', '1.1.rc1', '1.1.1b1', '1.1.1b2', '1.1.1', '1.2.1',
            '1.10.1'
        ]
        test = target[:]
        random.shuffle(test)
        self.assertListEqual(
            sorted(test, key=cmp_to_key(compare_version)), target
        )
