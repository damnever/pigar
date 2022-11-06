# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import unittest
import os

from ..__main__ import parser

CUR_DIR = os.getcwd()


def parse_args(args):
    args = parser.parse_args(args)
    return (
        args.log_level[0], args.update_db, args.check_path, args.search_names,
        args.ignores, args.save_path[0], args.project_path[0],
        args.comparison_operator[0], args.ref_comments, args.answer_yes,
        args.answer_no
    )


class CmdTests(unittest.TestCase):
    def setUp(self):
        reqs_path = os.path.join(CUR_DIR, 'requirements.txt')
        self._default_args = [
            'WARNING',
            False,
            None,
            [],
            [],
            reqs_path,
            CUR_DIR,
            '==',
            False,
            False,
            False,
        ]

    def tearDown(self):
        del self._default_args

    def test_default(self):
        self.assertListEqual(list(parse_args([])), self._default_args)

    def test_update(self):
        target = self._default_args
        target[1] = True
        self.assertListEqual(list(parse_args(['-u'])), target)
        self.assertListEqual(list(parse_args(['--update'])), target)

    def test_search(self):
        args = ['-s', 'foo', 'bar']
        target = self._default_args
        target[3] = args[1:]
        self.assertListEqual(list(parse_args(args)), target)

    def test_check(self):
        target = self._default_args
        target[2] = CUR_DIR
        self.assertListEqual(list(parse_args(['-c'])), target)
        args = ['-c', os.path.join('..', CUR_DIR)]
        target[2] = args[-1]
        self.assertListEqual(list(parse_args(args)), target)

    def test_log_level(self):
        args = ['-l', 'info']
        target = self._default_args
        target[0] = args[-1]
        self.assertListEqual(list(parse_args(args)), target)

    def test_ignores(self):
        target = self._default_args
        target[4] = [os.path.join(os.path.join('..', CUR_DIR), 'pigar')]

        args = ['-i', 'pigar']
        self.assertListEqual(list(parse_args(args)), target)
        args = ['-i', './pigar']
        self.assertListEqual(list(parse_args(args)), target)
        args = ['-i', 'pigar/']
        self.assertListEqual(list(parse_args(args)), target)

    def test_save_path(self):
        args = ['-p', os.path.join(os.path.join('..', CUR_DIR), 'test.txt')]
        target = self._default_args
        target[5] = args[-1]
        self.assertListEqual(list(parse_args(args)), target)

    def test_project_path(self):
        args = ['-P', os.path.join('..', CUR_DIR)]
        target = self._default_args
        target[6] = args[-1]
        self.assertListEqual(list(parse_args(args)), target)

    def test_comparison_operator(self):
        args = ['-o', '>=']
        target = self._default_args
        target[7] = args[-1]
        self.assertListEqual(list(parse_args(args)), target)

    def test_answer(self):
        target = self._default_args
        target[9] = True
        self.assertListEqual(list(parse_args(['-y'])), target)
        self.assertListEqual(list(parse_args(['--yes'])), target)
        target = self._default_args
        target[9] = False
        target[10] = True
        self.assertListEqual(list(parse_args(['-n'])), target)
        self.assertListEqual(list(parse_args(['--no'])), target)
