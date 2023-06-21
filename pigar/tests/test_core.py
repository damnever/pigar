import os
import os.path
import unittest

from ..core import RequirementsAnalyzer, check_stdlib, _LocatableRequirements, _Locations
from ..dist import FrozenRequirement
from .helper import py_version

from .._vendor.pip._vendor.packaging.version import Version


class RequirementsAnalyzerTests(unittest.TestCase):

    def setUp(self):
        self._installed_dists_by_imports = {
            'foo': [FrozenRequirement('Foo', '0.1.0')],
            'bar': [FrozenRequirement('Bar', '1.1.1')],
            'baz': [FrozenRequirement('Baz', '2.2.2')],
            'foobaz': [FrozenRequirement('FooBaz', '20151110')],
            'mod': [FrozenRequirement('Mod', '1.0.0')],
            'name': [FrozenRequirement('Name', '1.0.0')],
            'pkg': [
                FrozenRequirement('Pkg', '1.0.0'),
                FrozenRequirement('Pkg-fork', '1.1.0')
            ],
            'notebook': [FrozenRequirement('Notebook', '0.9.0')],
            'mainfoobar': [FrozenRequirement('min-foo-bar', '0.10.0rc0')],
            'annotations': [FrozenRequirement('annotations', '0.0.1')],
            'annotationsa': [FrozenRequirement('annotations-a', '0.0.1')],
            'annotationsb': [FrozenRequirement('annotations-b', '0.0.1')],
            'annotationsc': [FrozenRequirement('annotations-c', '0.0.1')],
        }
        self._path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'data/imports_example/')
        )

        def _abs_path(subpaths):
            paths = []
            for subp in subpaths:
                paths.append(os.path.join(self._path, subp))
            return paths

        self._certain_requirements = {}
        for k, v in {
            'Foo': ['example1.py: 9'],
            'Bar': ['example1.py: 11'],
            'FooBaz': ['example1.py: 13'],
            'Baz': ['example1.py: 28'],
            'Mod': ['example1.py: 42'],
            'Name': ['example1.py: 44'],
            'Notebook': ['notebook.ipynb: 3'],
            'min-foo-bar': ['mainfoobar.py: 2'],
            'annotations-a': ['annotations.py: 1'],
            'annotations-b': ['annotations.py: 2'],
            'annotations-c': ['annotations.py: 2'],
            'annotations': ['annotations.py: 3'],
        }.items():
            self._certain_requirements[k] = _abs_path(v)

        self._uncertain_requirements = {
            'pkg': {
                'Pkg': _abs_path(['example1.py: 46']),
                'Pkg-fork': _abs_path(['example1.py: 46']),
            }
        }

        self._guess = {}
        for k, v in {
            'foobar': ['example1.py: 7'],
        }.items():
            self._guess[k] = _abs_path(v)

    def tearDown(self):
        pass

    def test_analyze_requirements(self):
        analyzer = RequirementsAnalyzer(self._path)
        dist_mapping = {
            req.name: req
            for reqs in self._installed_dists_by_imports.values()
            for req in reqs
        }
        analyzer._installed_dists = dist_mapping
        analyzer._installed_dists_by_imports = self._installed_dists_by_imports
        analyzer.analyze_requirements(
            visit_doc_str=True, enable_requirement_annotations=True
        )

        self.assertListEqual(
            sorted(list(analyzer._requirements.keys())),
            sorted(list(self._certain_requirements.keys()))
        )
        for req in analyzer._requirements.values():
            dist = dist_mapping.get(req.req.name, None)
            self.assertIsNotNone(dist)
            self.assertEqual(req.req.version, dist.version)
            expected_locs = self._certain_requirements.get(req.req.name)
            self.assertIsNotNone(expected_locs)
            self.assertEqual(req.locations.sorted_items(), expected_locs)

        self.assertListEqual(
            sorted(list(analyzer._uncertain_requirements.keys())),
            sorted(list(self._uncertain_requirements.keys()))
        )
        for name, reqs in analyzer._uncertain_requirements.items():
            uncertain_locs = self._uncertain_requirements[name]
            for req in reqs.values():
                dist = dist_mapping.get(req.req.name, None)
                self.assertIsNotNone(dist)
                self.assertEqual(req.req.version, dist.version)
                expected_locs = uncertain_locs.get(req.req.name)
                self.assertIsNotNone(expected_locs)
                self.assertEqual(req.locations.sorted_items(), expected_locs)

        self.assertListEqual(
            sorted(list(analyzer._unknown_imports.keys())),
            sorted(list(self._guess.keys()))
        )
        for name, locs in analyzer._unknown_imports.items():
            expected_locs = self._guess.get(name)
            self.assertIsNotNone(expected_locs)
            self.assertEqual(locs.sorted_items(), expected_locs)


class StdlibTest(unittest.TestCase):

    def test_stdlibs(self):
        for lib in [
            'os', 'os.path', 'sys', 'io', 're', 'difflib', 'string',
            'collections', 'contextlib', 'contextvars', 'functools',
            'urllib.parse', 'urllib.request', 'itertools', 'time', 'typing',
            'importlib', 'asyncio', 'importlib.util'
        ]:
            self.assertTrue(self._is_stdlib(lib), lib)

    @unittest.skipIf(Version(py_version()) < Version('3.8'), '< Py3.8')
    def test_stdlibs_added_since_py3_8(self):
        for lib in ['importlib.metadata']:
            self.assertTrue(self._is_stdlib(lib), lib)

    @unittest.skipIf(Version(py_version()) < Version('3.9'), '< Py3.9')
    def test_stdlibs_added_since_py3_9(self):
        for lib in ['zoneinfo', 'graphlib']:
            self.assertTrue(self._is_stdlib(lib), lib)

    @unittest.skipIf(Version(py_version()) < Version('3.11'), '< Py3.11')
    def test_stdlibs_added_since_py3_11(self):
        for lib in ['tomllib']:
            self.assertTrue(self._is_stdlib(lib), lib)

    @unittest.skipIf(Version(py_version()) >= Version('3.12'), '< Py3.12')
    def test_stdlib_deprecated_since_py3_12(self):
        for lib in ['asynchat', 'asyncore', 'smtpd']:
            self.assertTrue(self._is_stdlib(lib), lib)

    def _is_stdlib(self, name):
        yes, _ = check_stdlib(name)
        return yes


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
