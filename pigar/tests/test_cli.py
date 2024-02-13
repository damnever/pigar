import sys
import codecs
import os
import os.path
import unittest

from ..__main__ import cli

from click.testing import CliRunner


class CliTests(unittest.TestCase):

    def setUp(self):
        self._pigar_project_root = os.path.join(
            os.path.dirname(__file__), '../..'
        )
        self._pigar_requirements = os.path.join(
            self._pigar_project_root, 'requirements',
            f'py{sys.version_info.major}.{sys.version_info.minor}.txt'
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
                    '**/tests/data/*', '--exclude-glob',
                    '**/_vendor/pip/*', '-f',
                    generated_requirement_file, project_path
                ]
            )
            self.assertEqual(result.exit_code, 0, result.output)
            expected = self._read_filelines(expected_requirements)
            actual = self._read_filelines(generated_requirement_file)
            self.assertEqual(len(expected), len(actual))
            for idx, line in enumerate(expected):
                line2 = actual[idx]
                if not line or line.startswith('#') or line.startswith('\n'):
                    self.assertEqual(line, line2)
                else:
                    parts1 = line.split('==')
                    parts2 = line2.split('==')
                    self.assertEqual(len(parts1), len(parts2))
                    self.assertEqual(parts1[0], parts2[0])

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
