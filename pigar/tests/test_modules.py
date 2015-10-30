# -*- coding: utf-8 -*-

import unittest

from ..modules import ImportedModules, ReqsModules, _Locations


class LocationsTests(unittest.TestCase):

    def setUp(self):
        self._data = {
            'oo/xx.py': 33,
            'bar/baz.py': 10,
        }

    def test_add(self):
        loc = _Locations()
        for file, lineno in self._data.items():
            loc.add(file, lineno)

        for file in self._data:
            if file not in loc:
                self.fail('add "{0}" failed'.format(file))
            else:
                self.assertEqual(loc[file], [self._data[file]])

        loc.add('oo/xx.py', 2)
        self.assertListEqual(sorted(loc['oo/xx.py']), [2, 33])

    def test_extend(self):
        loc1 = _Locations()
        loc2 = _Locations()
        r1, r2 = self._data.items()
        loc1.add(r1[0], r1[1])
        loc2.add(r2[0], r2[1])

        loc1.extend(loc2)

        self.assertListEqual(sorted(loc1.items()),
                             sorted([(k, [v]) for k, v in self._data.items()]))

    def test_iter(self):
        loc = _Locations()
        for file, lineno in self._data.items():
            loc.add(file, lineno)

        target = ['{0}: {1}'.format(k, v) for k, v in self._data.items()]
        self.assertListEqual(sorted(loc), sorted(target))


class ImportedModulesTests(unittest.TestCase):

    def setUp(self):
        self._mapping = {
            'pigar': ('oo/xx.py', 33),
            'foo': ('bar/baz.py', 10),
        }

    def test_add(self):
        im = ImportedModules()
        for name, (file, lineno) in self._mapping.items():
            im.add(name, file, lineno)

        self.assertListEqual(sorted(im.keys()), sorted(self._mapping.keys()))
        for name in self._mapping:
            if name not in im:
                self.fail('add "{0}" failed!'.format(name))
            else:
                file, linenos = list(im[name].items())[0]
                self.assertTupleEqual((file, linenos[0]), self._mapping[name])

        im.add('pigar', 'oo/xx.py', 2)
        file, linenos = list(im['pigar'].items())[0]
        self.assertListEqual(sorted(linenos), [2, 33])

    def test_or(self):
        im1 = ImportedModules()
        im2 = ImportedModules()
        r1, r2 = list(self._mapping.items())
        im1.add(r1[0], r1[1][0], r1[1][1])
        im2.add(r2[0], r2[1][0], r2[1][1])

        im1 |= im2
        self.assertListEqual(sorted(im1.keys()), sorted(self._mapping.keys()))


class ReqsModulesTest(unittest.TestCase):

    def setUp(self):
        loc1 = _Locations()
        loc2 = _Locations()
        loc1.add('oo/xx.py', 33)
        loc2.add('bar/baz.py', 10)
        self._data = {
            'pigar': ('9.9.9', loc1),
            'foo': ('3.3.3', loc2),
        }

    def test_add(self):
        rm = ReqsModules()
        for pkg, (ver, loc) in self._data.items():
            rm.add(pkg, ver, loc)

        for pkg in self._data:
            if pkg not in rm:
                self.fail('add "{0}" failed'.format(pkg))
            else:
                detail = rm[pkg]
                val = self._data[pkg]
                self.assertEqual(detail.version, val[0])
                self.assertIs(detail.comments, val[1])

        loc = _Locations()
        loc.add('foobar.py', 2)
        rm.add('pigar', '9.9.9', loc)
        self.assertListEqual(sorted(rm['pigar'].comments),
                             sorted(['oo/xx.py: 33', 'foobar.py: 2']))
