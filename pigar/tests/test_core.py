# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import os
import os.path as pathlib
import sys
import unittest

from ..core import RequirementsAnalyzer, is_stdlib, _LocatableRequirements, _Locations
from ..dist import FrozenRequirement


class ReqsTests(unittest.TestCase):

    def setUp(self):
        self._installed_dists = {
            'foo': [FrozenRequirement('Foo', '0.1.0')],
            'bar': [FrozenRequirement('Bar', '1.1.1')],
            'baz': [FrozenRequirement('Baz', '2.2.2')],
            'foobaz': [FrozenRequirement('FooBaz', '20151110')],
            'mod': [FrozenRequirement('Mod', '1.0.0')],
            'name': [FrozenRequirement('Name', '1.0.0')],
            'pkg': [FrozenRequirement('Pkg', '1.0.0')],
            'pkg': [FrozenRequirement('Pkg-fork', '1.1.0')],
            'notebook': [FrozenRequirement('Notebook', '0.9.0')],
            'mainfoobar': [FrozenRequirement('min-foo-bar', '0.10.0rc0')],
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
            'Notebook': ['notebook.ipynb: 3'],
            'min-foo-bar': ['mainfoobar.py: 2'],
        }.items():
            paths = []
            for subp in v:
                paths.append(pathlib.join(self._path, subp))
            self._module_infos[k] = paths

    def tearDown(self):
        pass

    def test_analyze_requirements(self):
        analyzer = RequirementsAnalyzer(self._path)
        analyzer._installed_dists = self._installed_dists
        analyzer.analyze_requirements()
        pv = {v.name: v.version for v in self._installed_packages.values()}
        pkgs, guess = self._parse_packages()

        self.assertListEqual(sorted(pkgs.keys()), sorted(pv.keys()))
        # Assume 'foobar' is Py3 builtin package, no need install.
        self.assertListEqual(sorted(guess.keys()), ['foobar'])
        self._check_require_pkgs(pkgs, pv)
        self._check_guess(guess, pv)

    def _check_require_pkgs(self, pkgs, pv):
        for pkg, req in pkgs.sorted_items():
            if pkg not in pv:
                self.fail('"{0}" not installed'.format(pkg))
            self.assertEqual(req.req.version, pv[pkg])
            self.assertListEqual(
                sorted(req.locations.sorted_items()),
                sorted(self._module_infos[pkg])
            )

    def _check_guess(self, mods, pv):
        for mod, locs in mods.items():
            self.assertListEqual(
                sorted(locs.sorted_items()), sorted(self._module_infos[mod])
            )


class StdlibTest(unittest.TestCase):

    def test_stdlib(self):
        for lib in ['os', 'sys', 'importlib', 'asyncio']:
            self.assertTrue(is_stdlib(lib))

    @unittest.skipIf(
        sys.version_info[0] != 3 and sys.version_info[1] < 8, '< Py3.8'
    )
    def test_stdlib_py3_8(self):
        for lib in ['os', 'sys', 'importlib', 'asyncio', 'importlib.metadata']:
            self.assertTrue(is_stdlib(lib))

    @unittest.skipIf(
        sys.version_info[0] != 3 and sys.version_info[1] < 9, '< Py3.9'
    )
    def test_stdlib_py3_9(self):
        for lib in [
            'os', 'sys', 'importlib', 'asyncio', 'zoneinfo', 'graphlib'
        ]:
            self.assertTrue(is_stdlib(lib))

    @unittest.skipIf(
        sys.version_info[0] != 3 and sys.version_info[1] < 11, '< Py3.11'
    )
    def test_stdlib_py3_11(self):
        for lib in [
            'os', 'sys', 'importlib', 'asyncio', 'zoneinfo', 'tomllib'
        ]:
            self.assertTrue(is_stdlib(lib))


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


class LocatableRequirementsTest(unittest.TestCase):

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
        rm = _LocatableRequirements()
        for pkg, (ver, loc) in self._data.items():
            rm.add_locs(FrozenRequirement(pkg, ver), loc)

        for pkg in self._data:
            if pkg not in rm:
                self.fail('add "{0}" failed'.format(pkg))
            else:
                req = rm[pkg]
                val = self._data[pkg]
                self.assertEqual(req.req.version, val[0])
                self.assertIs(req.locations, val[1])

        rm.add(FrozenRequirement('pigar', '9.9.9'), 'foobar.py', 2)
        self.assertListEqual(
            rm['pigar'].locations.sorted_items(),
            sorted(['oo/xx.py: 33', 'foobar.py: 2'])
        )
