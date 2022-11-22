import unittest
import os
import tempfile

from ..db import Database


class DBTests(unittest.TestCase):

    def setUp(self):
        self._db_path = os.path.join(tempfile.gettempdir(), 'pigar_test.db')
        self._db = Database(path=self._db_path)

    def tearDown(self):
        self._db.close
        os.remove(self._db_path)

    def test_db(self):
        self._db.store_distribution_with_top_level_modules(
            'pigar', '1.0.0', []
        )
        row = self._db.query_distribution_by_name('pigar')
        self.assertDictEqual(dict(row), {'name': 'pigar', 'version': '1.0.0'})
        self._db.store_distribution_with_top_level_modules(
            'pigar', '2.0.0', ['pigar']
        )
        rows = self._db.query_distributions_by_top_level_module('pigar')
        self.assertListEqual([r.name for r in rows], ['pigar'])
        rows = self._db.query_distributions()
        self.assertListEqual(
            [dict(r) for r in rows], [{
                'name': 'pigar',
                'version': '2.0.0'
            }]
        )
