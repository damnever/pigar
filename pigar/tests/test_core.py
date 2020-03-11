# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import os
import os.path as pathlib
import sys
import unittest

from ..core import parse_packages, is_stdlib, _RequiredModules, _Locations


class ReqsTests(unittest.TestCase):
    def setUp(self):
        self._installed_packages = {
            'foo': ('Foo', '0.1.0'),
            'bar': ('Bar', '1.1.1'),
            'baz': ('Baz', '2.2.2'),
            'foobaz': ('FooBaz', '20151110'),
            'mod': ('Mod', '1.0.0'),
            'name': ('Name', '1.0.0'),
            'pkg': ('Pkg', '1.0.0'),
            'mainfoobar': ('min-foo-bar', '0.10.0rc0'),
        }
        self._path = os.path.abspath(
            pathlib.join(os.path.dirname(__file__), 'imports_example/')
        )
        self._module_infos = {}
        for k, v in {
            'foobar': ['example1.py: 7'],
            'FooBar': ['example1.py: 7'],
            'Foo': ['example1.py: 9'],
            'Bar': ['example1.py: 11'],
            'FooBaz': ['example1.py: 13'],
            'Baz': ['example1.py: 27'],
            'queue': ['example1.py: 33'],
            'Mod': ['example1.py: 41'],
            'Name': ['example1.py: 43'],
            'Pkg': ['example1.py: 45'],
            'min-foo-bar': ['mainfoobar.py: 2'],
        }.items():
            paths = []
            for subp in v:
                paths.append(pathlib.join(self._path, subp))
            self._module_infos[k] = paths

        if sys.version_info[0] == 2:
            self._installed_packages.update({'foobar': ('FooBar', '3.6.9')})

    def tearDown(self):
        del self._installed_packages
        del self._path
        del self._module_infos

    @unittest.skipIf(sys.version_info[0] != 3, 'Not python 3.x')
    def test_py3_requirements(self):
        pv = {k: v for k, v in self._installed_packages.values()}
        pkgs, guess = self._parse_packages()

        self.assertListEqual(sorted(pkgs.keys()), sorted(pv.keys()))
        # Assume 'foobar' is Py3 builtin package, no need install.
        self.assertListEqual(sorted(guess.keys()), ['foobar'])
        self._check_require_pkgs(pkgs, pv)
        self._check_guess(guess, pv)

    @unittest.skipIf(sys.version_info[0] != 2, 'Not python 2.x')
    def test_py2_requirements(self):
        self._installed_packages.update({'foobar': ('FooBar', '3.3.3')})
        pv = {k: v for k, v in self._installed_packages.values()}
        pkgs, guess = self._parse_packages()

        self.assertListEqual(sorted(pkgs.keys()), sorted(pv.keys()))
        self.assertListEqual(guess.keys(), ['queue'])
        self._check_require_pkgs(pkgs, pv)
        self._check_guess(guess, pv)

    def _check_require_pkgs(self, pkgs, pv):
        for pkg, detail in pkgs.sorted_items():
            if pkg not in pv:
                self.fail('"{0}" not installed'.format(pkg))
            self.assertEqual(detail.version, pv[pkg])
            self.assertListEqual(
                sorted(detail.comments.sorted_items()),
                sorted(self._module_infos[pkg])
            )

    def _check_guess(self, mods, pv):
        for mod, locs in mods.items():
            self.assertListEqual(
                sorted(locs.sorted_items()), sorted(self._module_infos[mod])
            )

    def _parse_packages(self):
        return parse_packages(self._path, [], self._installed_packages)


class StdlibTest(unittest.TestCase):
    def test_stdlib(self):
        self.assertTrue(is_stdlib('os'))
        self.assertTrue(is_stdlib('sys'))


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

        self.assertListEqual(
            sorted(loc1.items()),
            sorted([(k, [v]) for k, v in self._data.items()])
        )

    def test_sorted_items(self):
        loc = _Locations()
        for file, lineno in self._data.items():
            loc.add(file, lineno)

        target = ['{0}: {1}'.format(k, v) for k, v in self._data.items()]
        self.assertListEqual(loc.sorted_items(), sorted(target))


class RequiredModulesTest(unittest.TestCase):
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
        rm = _RequiredModules()
        for pkg, (ver, loc) in self._data.items():
            rm.add_locs(pkg, ver, loc)

        for pkg in self._data:
            if pkg not in rm:
                self.fail('add "{0}" failed'.format(pkg))
            else:
                detail = rm[pkg]
                val = self._data[pkg]
                self.assertEqual(detail.version, val[0])
                self.assertIs(detail.comments, val[1])

        rm.add('pigar', '9.9.9', 'foobar.py', 2)
        self.assertListEqual(
            rm['pigar'].comments.sorted_items(),
            sorted(['oo/xx.py: 33', 'foobar.py: 2'])
        )
