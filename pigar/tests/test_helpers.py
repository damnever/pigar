import unittest
import os
import random

from .helper import CaptureOutput
from ..helpers import (
    print_table, ParsedRequirementParts, parse_requirements, compare_version,
    cmp_to_key
)

from .._vendor.pip._vendor.packaging.requirements import Requirement
from .._vendor.pip._vendor.packaging.markers import Marker


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
        path = os.path.join(os.path.dirname(__file__), 'data/fake_reqs.txt')
        expected = [
            ParsedRequirementParts(
                Requirement('a==4.1.4'),
                '',
                None,
                set(),
            ),
            ParsedRequirementParts(
                Requirement('b==2.3.0'),
                '',
                None,
                set(),
            ),
            ParsedRequirementParts(
                Requirement('c'),
                '',
                None,
                set(),
            ),
            ParsedRequirementParts(
                Requirement(
                    'd @ https://example.com/d/d/archive/refs/tags/1.0.0.zip'
                ),
                '',
                None,
                set(),
            ),
            ParsedRequirementParts(
                Requirement('e[fake] ==2.8.*,>=2.8.1'),
                '',
                Marker('python_version < "2.7"'),
                set(),
            ),
            ParsedRequirementParts(
                Requirement('pigar'),
                'git+ssh://git@github.com/damnever/pigar.git@abcdef#egg=pigar',
                None,
                set(),
            ),
            ParsedRequirementParts(
                None,
                'git+https://git@github.com/damnever/pigar.git@abcdef',
                None,
                set(),
            ),
            ParsedRequirementParts(
                Requirement('another-in-ref'),
                '',
                None,
                set(),
            ),
        ]
        reqs = list(parse_requirements(path))
        self.assertEqual(len(reqs), len(expected))
        for idx, req in enumerate(reqs):
            oth = expected[idx]
            self.assertEqual(
                str(req.requirement or ''), str(oth.requirement or ''), idx
            )
            self.assertEqual(req.url, oth.url, idx)
            self.assertEqual(
                str(req.markers or ''), str(oth.markers or ''), idx
            )
            self.assertEqual(req.extras, oth.extras, idx)


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
