import unittest
import os
import tempfile
import dataclasses

from ..db import Database


class DBTests(unittest.TestCase):

    def setUp(self):
        self._db_path = os.path.join(tempfile.gettempdir(), 'pigar_test.db')
        self._db = Database(path=self._db_path)

    def tearDown(self):
        self._db.close
        os.remove(self._db_path)

    def test_db(self):
        # pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false, reportGeneralTypeIssues=false

        def _assert_moduels(modules, deleted=set()):
            for module in modules:
                rows = self._db.query_distributions_by_top_level_module(module)
                self.assertIsNotNone(rows)
                self.assertListEqual([r.name for r in rows], ['pigar'])
            dist = self._db.query_distribution_with_top_level_modules('pigar')
            self.assertIsNotNone(dist)
            self.assertListEqual(sorted(modules), sorted(dist.modules))

            for module in deleted:
                rows = self._db.query_distributions_by_top_level_module(module)
                self.assertIsNone(rows)

        self._db.store_distribution_with_top_level_modules(
            'pigar', '1.0.0', []
        )
        row = self._db.query_distribution_by_name('pigar')
        self.assertIsNotNone(row)
        self.assertDictEqual(
            dataclasses.asdict(row), {
                'name': 'pigar',
                'version': '1.0.0'
            }
        )
        modules1 = ['pigar', 'pigar1', 'pigar2']
        self._db.store_distribution_with_top_level_modules(
            'pigar', '1.9.0', modules1
        )
        _assert_moduels(modules1)

        modules2 = ['pigar', 'pigar3', 'pigar4']
        modules_to_delete = set(modules1) - set(modules2)
        self._db.store_distribution_with_top_level_modules(
            'pigar',
            '2.0.0',
            modules2,
            modules_to_delete=modules_to_delete,
        )
        _assert_moduels(modules2, modules_to_delete)

        rows = self._db.query_distributions()
        self.assertIsNotNone(rows)
        self.assertListEqual(
            [dataclasses.asdict(r) for r in rows], [{
                'name': 'pigar',
                'version': '2.0.0'
            }]
        )

        res = self._db.query_distribution_by_name('not-found')
        self.assertIsNone(res)
