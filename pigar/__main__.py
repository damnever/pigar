# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import os
import sys
import fnmatch

from .cmd import parse_args
from .reqs import project_import_modules, is_stdlib, get_installed_pkgs_detail
from .pypi import update_db, check_latest_version, search_names
from .db import database
from .utils import Color, parse_reqs, print_table
from .log import logger, enable_pretty_logging
from .modules import ReqsModules


_installed_pkgs = get_installed_pkgs_detail()


def main():
    """Just allow do one thing at each time."""
    (log_level, updatedb, check_path, names, ignores, save_path,
     project_path) = parse_args()
    enable_pretty_logging(log_level=log_level)
    if updatedb:
        update_db()
    elif check_path:
        check_reqs_latest_version(check_path, ignores)
    elif names:
        search_package_by_name(names)
    else:
        generate_reqs(save_path, project_path, ignores)


def search_package_by_name(names, installed_pkgs=_installed_pkgs):
    """Search package name by import name."""
    print(Color.BLUE('Starting search names ...'))
    found, not_found = search_names(names, installed_pkgs)
    for name in found:
        print('Found package(s) for "{0}":'.format(Color.GREEN(name)))
        print_table(found[name], headers=['PACKAGE', 'VERSION', 'WHERE'])
    if not_found:
        msg = '"{0}" not found.\n'.format(Color.RED(', '.join(not_found)))
        msg += 'Maybe you need update database.'
        print(Color.YELLOW(msg))


def check_reqs_latest_version(check_path, ignores,
                              installed_pkgs=_installed_pkgs):
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
            generate_reqs(save_path, check_path, ignores)
            files.append(save_path)
    else:
        files.append(check_path)
    for fpath in files:
        reqs.update(parse_reqs(fpath))

    print(Color.BLUE('Checking requirements latest version ...'))
    installed_pkgs = {v[0]: v[1] for k, v in installed_pkgs.items()}
    for pkg in reqs:
        current = reqs[pkg]
        # If no version specific in requirements,
        # check in installed packages.
        if current == '' and pkg in installed_pkgs:
            current = installed_pkgs[pkg]
        logger.info('Checking "{0}" latest version ...'.format(pkg))
        latest = check_latest_version(pkg)
        pkg_versions.append((pkg, current, latest))

    print(Color.BLUE('Checking requirements latest version done.'))
    print()
    print_table(pkg_versions)


def generate_reqs(save_path, project_path, ignores):
    """Generate requirements for `project_path`, save file in
    `save_path`.
    """
    print(Color.BLUE('Starting generate requirements ...'))
    reqs, guess = extract_reqs(project_path, ignores)
    in_pypi = list()
    answer = 'n'
    if guess:
        pyver = 'Python 3' if sys.version_info[0] == 2 else 'Python 2'
        print(Color.RED('The following modules not in local environment:'))
        for name, detail in guess.items():
            print('  {0} referenced from:\n    {1}'.format(
                Color.YELLOW(name), '\n    '.join(detail.comments)))
        msg = (Color.RED('Is there modules come from other Python '
               'version(i.e. {0}) or extension? [y/n] ')).format(pyver)
        sys.stdout.write(msg)
        sys.stdout.flush()
        answer = sys.stdin.readline()
        answer = answer.strip().lower()
        if answer not in ('y', 'yes'):
            print(Color.BLUE('Checking modules in pypi.'))
            for name in guess:
                logger.info('Checking {0} in pypi ...'.format(name))
                with database() as db:
                    rows = db.query_all(name)
                    pkgs = [row.package for row in rows]
                    if pkgs:
                        in_pypi.append(name)
                    # If imported name equals to package name.
                    if name in pkgs:
                        idx = pkgs.index(name)
                        latest = check_latest_version(pkgs[idx])
                        reqs.add(pkgs[idx], latest, guess[name].comments)
                        continue
                    # If not, add all possible packages.
                    for pkg in pkgs:
                        latest = check_latest_version(pkg)
                        reqs.add(pkg, latest, guess[name].comments)

    # Write requirements to file.
    print(Color.BLUE('Writing requirements to "{0}"'.format(save_path)))
    with open(save_path, 'w+') as f:
        f.write('# Requirements automatic generated by pigar.\n'
                '# https://github.com/Damnever/pigar\n')
        for k, v in reqs.items():
            f.write('\n')
            f.write(''.join(['# {0}\n'.format(c) for c in v.comments]))
            if k == '-e':
                f.write('{0} {1}\n'.format(k, v.version))
            elif v:
                f.write('{0} == {1}\n'.format(k, v.version))
            else:
                f.write('{0}\n'.format(k))
    print(Color.BLUE('DONE!'))

    if guess and answer not in ('y', 'yes'):
        guess.remove(*in_pypi)
        if guess:
            print(Color.RED('Following modules not found:'))
            for name, detail in guess.items():
                print('  {0} referenced from:\n    {1}'.format(
                    Color.YELLOW(name), '\n    '.join(detail.comments)))
            print(Color.RED('Maybe you need update database.'))


def extract_reqs(path, ignores, installed_pkgs=_installed_pkgs):
    """Extract requirements from project."""
    candidates = set()
    reqs = ReqsModules()
    guess = ReqsModules()
    modules, local_mods = project_import_modules(path, ignores)

    logger.info('Extracting third-part module ...')
    for module in modules:
        raw_name = module
        logger.info('Checking module: {0}'.format(module))
        if not module or module.startswith('.'):
            continue
        is_local = False
        for mod in local_mods:
            if mod == module or module.startswith(mod + '.'):
                is_local = True
                break
        if is_local:
            continue
        if is_stdlib(module):
            continue
        if '.' in module:
            module = module.split('.', 1)[0]
        candidates.add((module, raw_name))

    logger.info('Check module in local environment.')
    for (name, raw_name) in candidates:
        logger.info('Checking module: {0}'.format(name))
        if name in installed_pkgs:
            pkg_name, version = installed_pkgs[name]
            reqs.add(pkg_name, version, modules[raw_name])
        else:
            guess.add(name, 0, modules[raw_name])
    logger.info('Finish local environment checking.')
    return reqs, guess


if __name__ == '__main__':
    main()
