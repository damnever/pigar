import codecs
import os
import os.path
import unittest

from ..__main__ import cli
from .helper import py_version

from click.testing import CliRunner
from packaging.version import Version


class CliTests(unittest.TestCase):

    def setUp(self):
        self._pigar_project_root = os.path.join(
            os.path.dirname(__file__), '../..'
        )
        pigar_requirements_dir = os.path.join(
            self._pigar_project_root, 'requirements'
        )
        current_version = Version(py_version())
        requirement_file = 'requirements.txt'
        for fpath in os.listdir(pigar_requirements_dir):
            fname = os.path.basename(fpath)
            fname_no_ext, _ = os.path.splitext(fname)
            try:
                startv, endv = fname_no_ext.split('-', 1)
            except Exception:
                continue
            if Version(startv) <= current_version <= Version(endv):
                requirement_file = fname
                break
        self._pigar_requirements = os.path.join(
            pigar_requirements_dir, requirement_file
        )

        self.maxDiff = None

    def tearDown(self):
        pass

    def test_generate(self):
        project_path = os.path.join(self._pigar_project_root, 'pigar')
        expected_requirements = self._pigar_requirements
        runner = CliRunner()
        with runner.isolated_filesystem():
            generated_requirement_file = 'requirements.txt'
            result = runner.invoke(
                cli, [
                    'gen', '--with-referenced-comments',
                    '--dont-show-differences', '--exclude-glob',
                    '**/tests/data', '-f', generated_requirement_file,
                    project_path
                ]
            )
            self.assertEqual(result.exit_code, 0, result.output)
            relaxed_requirements = [
                'click==', 'nbformat==', 'aiohttp==', 'setuptools=='
            ]
            expected = self._read_filelines(expected_requirements)
            actual = self._read_filelines(generated_requirement_file)
            self.assertEqual(len(expected), len(actual))
            for idx, line in enumerate(expected):
                line2 = actual[idx]
                skip = False
                for req in relaxed_requirements:
                    if line.startswith(req):
                        self.assertTrue(line2.startswith(req))
                        skip = True
                if not skip:
                    self.assertEqual(line, line2)

    def test_check(self):
        expected_requirements = self._pigar_requirements
        runner = CliRunner()
        result = runner.invoke(cli, ['check', '-f', expected_requirements])
        self.assertEqual(result.exit_code, 0, result.output)

    def test_search(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'requests', 'mysql'])
        self.assertEqual(result.exit_code, 0, result.output)

    def _read_filelines(self, path):
        with codecs.open(path, 'r', encoding='utf-8') as f:
            return f.readlines()
