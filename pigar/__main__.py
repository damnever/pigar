# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import os
import sys
import fnmatch
import codecs

from .cmd import parse_args
from .reqs import project_import_modules, is_stdlib, get_installed_pkgs_detail
from .pypi import update_db, check_latest_version, search_names
from .db import database
from .utils import Color, parse_reqs, print_table, lines_diff
from .log import logger, enable_pretty_logging
from .modules import ReqsModules


class Main(object):

    def __init__(self):
        # Parse command arguments.
        (log_level, updatedb, check_path, names, ignores, save_path,
         project_path, comparison_operator) = parse_args()
        # Enable logging.
        enable_pretty_logging(log_level=log_level)
        # Just allow do one thing at each time.
        if updatedb:
            self.update_db()
        elif check_path:
            self.check_reqs_latest_version(
                check_path, ignores, comparison_operator)
        elif names:
            self.search_package_by_name(names)
        else:
            self.generate_reqs(save_path, project_path,
                               ignores, comparison_operator)

    @property
    def installed_pkgs(self):
        # Lazy calculation.
        if not hasattr(self, '_installed_pkgs'):
            self._installed_pkgs = get_installed_pkgs_detail()
        return self._installed_pkgs

    def update_db(self):
        """Update database."""
        update_db()

    def search_package_by_name(self, names):
        """Search package name by import name."""
        print(Color.BLUE('Starting search names ...'))
        found, not_found = search_names(names, self.installed_pkgs)
        for name in found:
            print('Found package(s) for "{0}":'.format(Color.GREEN(name)))
            print_table(found[name], headers=['PACKAGE', 'VERSION', 'WHERE'])
        if not_found:
            msg = '"{0}" not found.\n'.format(Color.RED(', '.join(not_found)))
            msg += 'Maybe you need update database.'
            print(Color.YELLOW(msg))

    def check_reqs_latest_version(self, check_path, ignores,
                                  comparison_operator):
        """Check requirements latest version."""
        print(Color.BLUE('Starting check requirements latest version ...'))
        files = list()
        reqs = dict()
        pkg_versions = list()
        # If no requirements file given, check in current directory.
        if os.path.isdir(check_path):
            print(Color.BLUE('Searching file in "{0}" ...'.format(check_path)))
            for fn in os.listdir(check_path):
                if fnmatch.fnmatch(fn, '*requirements.txt'):
                    files.append(os.path.abspath(fn))
            # If not found in directory, generate requirements.
            if not files:
                print(Color.YELLOW('Requirements file not found, '
                                   'generate requirements ...'))
                save_path = os.path.join(check_path, 'requirements.txt')
                self.generate_reqs(save_path, check_path,
                                   ignores, comparison_operator)
                files.append(save_path)
        else:
            files.append(check_path)
        for fpath in files:
            reqs.update(parse_reqs(fpath))

        print(Color.BLUE('Checking requirements latest version ...'))
        installed_pkgs = {v[0]: v[1] for k, v in self.installed_pkgs.items()}
        for pkg in reqs:
            current = reqs[pkg]
            # If no version specifies in requirements,
            # check in installed packages.
            if current == '' and pkg in installed_pkgs:
                current = installed_pkgs[pkg]
            logger.info('Checking "{0}" latest version ...'.format(pkg))
            latest = check_latest_version(pkg)
            pkg_versions.append((pkg, current, latest))

        print(Color.BLUE('Checking requirements latest version done.'))
        print()
        print_table(pkg_versions)

    def generate_reqs(self, save_path, check_path,
                      ignores, comparison_operator):
        gr = GenerateReqs(save_path, check_path, ignores,
                          self.installed_pkgs, comparison_operator)
        gr.generate_reqs()


class GenerateReqs(object):

    def __init__(self, save_path, project_path, ignores,
                 installed_pkgs, comparison_operator='=='):
        self._save_path = save_path
        self._project_path = project_path
        self._ignores = ignores
        self._installed_pkgs = installed_pkgs
        self._maybe_local_mods = set()
        self._comparison_operator = comparison_operator

    def generate_reqs(self):
        """Generate requirements for `project_path`, save file in
        `save_path`.
        """
        print(Color.BLUE('Starting generate requirements ...'))
        reqs, try_imports, guess = self.extract_reqs()
        in_pypi = set()
        answer = 'n'
        pyver = None

        guess.remove(*try_imports)
        if guess:
            print(Color.RED('The following modules are not found yet:'))
            self._invalid_reqs(guess)
            msg = ('Some of them may not install in local environment.\n'
                   'Try to search PyPI for the missing modules and filter'
                   ' some unnecessary modules? (y/[N]) '
                   ).format(pyver)
            sys.stdout.write(Color.RED(msg))
            sys.stdout.flush()
            answer = sys.stdin.readline()
            answer = answer.strip().lower()
            if answer in ('y', 'yes'):
                print(Color.BLUE('Checking modules on the PyPI...'))
                for name, detail in guess.sorted_items():
                    logger.info('Checking %s on the PyPI ...', name)
                    with database() as db:
                        rows = db.query_all(name)
                        pkgs = [row.package for row in rows]
                        if pkgs:
                            in_pypi.add(name)
                            if name in self._maybe_local_mods:
                                self._maybe_local_mods.remove(name)
                        for pkg in self._best_matchs(name, pkgs):
                            latest = check_latest_version(pkg)
                            reqs.add(pkg, latest, detail.comments)

        # Save old requirements file.
        self._save_old_reqs()
        # Write requirements to file.
        self._write_reqs(reqs)
        # If requirements has been covered, show difference.
        self._reqs_diff()
        print(Color.BLUE('Generate requirements done!'))
        del reqs

        if guess and answer in ('y', 'yes'):
            guess.remove(*(in_pypi | self._maybe_local_mods))
            if guess:
                print(Color.RED('These modules are not found:'))
                self._invalid_reqs(guess)
                print(Color.RED('Maybe or you need update database.'))

    def extract_reqs(self):
        """Extract requirements from project."""
        reqs = ReqsModules()
        guess = ReqsModules()
        modules, try_imports, local_mods = project_import_modules(
            self._project_path, self._ignores)
        app_name = os.path.basename(self._project_path)
        if app_name in local_mods:
            local_mods.remove(app_name)

        # Filtering modules
        candidates = self._filter_modules(modules, local_mods)

        logger.info('Check module in local environment.')
        for name in candidates:
            logger.info('Checking module: %s', name)
            if name in self._installed_pkgs:
                pkg_name, version = self._installed_pkgs[name]
                reqs.add(pkg_name, version, modules[name])
            else:
                guess.add(name, 0, modules[name])
        logger.info('Finish local environment checking.')
        return reqs, try_imports, guess

    def _write_reqs(self, reqs):
        print(Color.BLUE('Writing requirements to "{0}"'.format(
            self._save_path)))
        with open(self._save_path, 'w+') as f:
            f.write('# Requirements automatically generated by pigar.\n'
                    '# https://github.com/damnever/pigar\n')
            for k, v in reqs.sorted_items():
                f.write('\n')
                f.write(''.join(['# {0}\n'.format(c)
                                 for c in v.comments.sorted_items()]))
                if k == '-e':
                    f.write('{0} {1}\n'.format(k, v.version))
                elif v:
                    f.write('{0} {1} {2}\n'.format(
                        k, self._comparison_operator, v.version))
                else:
                    f.write('{0}\n'.format(k))

    def _best_matchs(self, name, pkgs):
        # If imported name equals to package name.
        if name in pkgs:
            return [pkgs[pkgs.index(name)]]
        # If not, return all possible packages.
        return pkgs

    def _filter_modules(self, modules, local_mods):
        candidates = set()

        logger.info('Filtering modules ...')
        for module in modules:
            logger.info('Checking module: %s', module)
            if not module or module.startswith('.'):
                continue
            if module in local_mods:
                self._maybe_local_mods.add(module)
            if is_stdlib(module):
                continue
            candidates.add(module)

        return candidates

    def _invalid_reqs(self, reqs):
        for name, detail in reqs.sorted_items():
            print(
                '  {0} referenced from:\n    {1}'.format(
                    Color.YELLOW(name),
                    '\n    '.join(detail.comments.sorted_items())
                )
            )

    def _save_old_reqs(self):
        if os.path.isfile(self._save_path):
            with codecs.open(self._save_path, 'rb', 'utf-8') as f:
                self._old_reqs = f.readlines()

    def _reqs_diff(self):
        if not hasattr(self, '_old_reqs'):
            return
        with codecs.open(self._save_path, 'rb', 'utf-8') as f:
            new_reqs = f.readlines()
        is_diff, diffs = lines_diff(self._old_reqs, new_reqs)
        msg = 'Requirements file has been covered, '
        if is_diff:
            msg += 'there is the difference:'
            print('{0}\n{1}'.format(Color.YELLOW(msg), ''.join(diffs)), end='')
        else:
            msg += 'no difference.'
            print(Color.YELLOW(msg))


def main():
    Main()


if __name__ == '__main__':
    main()
