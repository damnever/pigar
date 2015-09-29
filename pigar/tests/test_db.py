# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import unittest
import os
import tempfile

from ..db import Database


class DbTests(unittest.TestCase):

    def setUp(self):
        self._db = os.path.join(tempfile.gettempdir(), 'pigar_test.db')
        self._conn = Database(db=self._db)

    def tearDown(self):
        self._conn.close
        os.remove(self._db)

    def test_db(self):
        self.assertGreaterEqual(self._conn.insert_package('pigar'), 1)
        row = self._conn.query_package('pigar')
        self.assertEqual(row.id, 1)
        self.assertGreaterEqual(self._conn.insert_name('pigar', row.id), 1)
        row = self._conn.query_all('pigar')
        self.assertDictEqual(dict(row[0]), {'name': 'pigar', 'package': 'pigar'})
        rows = self._conn.query_package(None)
        self.assertListEqual(rows, ['pigar'])
