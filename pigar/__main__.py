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


_installed_pkgs = get_installed_pkgs_detail()


def main():
    """Just allow do one thing at each time."""
    (log_level, updatedb, check_path, names, save_path,
     project_path) = parse_args()
    enable_pretty_logging(log_level=log_level)
    if updatedb:
        update_db()
    elif check_path:
        check_reqs_latest_version(check_path)
    elif names:
        search_package_by_name(names)
    else:
        generate_reqs(save_path, project_path)


def search_package_by_name(names, installed_pkgs=_installed_pkgs):
    """Search package name by import name."""
    found, not_found = search_names(names, installed_pkgs)
    for name in found:
        print('Found package(s) for "{0}":'.format(Color.GREEN(name)))
        print_table(found[name], headers=['PACKAGE', 'VERSION', 'WHERE'])
    if not_found:
        msg = '"{0}" not found.\n'.format(Color.RED(', '.join(not_found)))
        msg += 'Maybe you need update database.'
        print(Color.YELLOW(msg))


def check_reqs_latest_version(check_path, installed_pkgs=_installed_pkgs):
    """Check requirements latest version."""
    logger.info('Starting check requirements latest version ...')
    files = list()
    reqs = dict()
    pkg_versions = list()
    # If no requirements file given, check in current directory.
    if os.path.isdir(check_path):
        logger.info('Search *requirements.txt in "{0}" ...'.format(check_path))
        for fn in os.listdir(check_path):
            if fnmatch.fnmatch(fn, '*requirements.txt'):
                files.append(os.path.abspath(fn))
        # If not found in directory, generate requirements.
        if not files:
            logger.warning('Requirements file not found, '
                           'generate requirements ...')
            save_path = os.path.join(check_path, 'requirements.txt')
            generate_reqs(save_path, check_path)
            files.append(save_path)
    else:
        files.append(check_path)
    for fpath in files:
        reqs.update(parse_reqs(fpath))

    logger.info('Checking requirements latest version ...')
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

    logger.info('Checking requirements latest version done.')
    print()
    print_table(pkg_versions)


def generate_reqs(save_path, project_path):
    """Generate requirements for `project_path`, save file in
    `save_path`.
    """
    logger.info('Starting generate requirements ...')
    reqs, guess = extract_reqs(project_path)
    guess_reqs = dict()
    answer = 'n'
    if guess:
        pyver = 'Python 3' if sys.version_info[0] == 2 else 'Python 2'
        msg = 'Is there modules "{0}" '.format(Color.RED(', '.join(guess)))
        msg += 'come from other Python version(i.e. {0})[y/n]? '.format(pyver)
        sys.stdout.write(msg)
        sys.stdout.flush()
        answer = sys.stdin.readline()
        answer = answer.strip().lower()
        if answer not in ('y', 'yes'):
            logger.warning('Checking modules in pypi ...')
            for name in guess:
                with database() as db:
                    rows = db.query_all(name)
                    for row in rows:
                        latest = check_latest_version(row.package)
                        guess_reqs[name] = (row.package, latest)
            reqs.update({v[0]: v[1] for k, v in guess_reqs.items()})

    # Write requirements to file.
    logger.info('Writing requirements to "{0}"'.format(save_path))
    with open(save_path, 'w+') as f:
        for k, v in reqs.items():
            if v:
                f.write('{0} == {1}\n'.format(k, v))
            else:
                f.write('{0}\n'.format(k))

    if guess and answer not in ('y', 'yes'):
        not_found = list(set(guess) - set(guess_reqs.keys()))
        if not_found:
            msg = '"{0}" not found.\n'.format(Color.RED(', '.join(not_found)))
            print(msg + 'Maybe you need update database.')


def extract_reqs(path, installed_pkgs=_installed_pkgs):
    """Extract requirements from project."""
    candidates = set()
    reqs = dict()
    guess = list()
    modules, local_mods = project_import_modules(path)

    logger.info('Extracting third-part module ...')
    for module in modules:
        logger.info('Checking module: {0}'.format(module))
        if module.startswith('.'):
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
        candidates.add(module)

    logger.info('Check module in local environment.')
    for name in candidates:
        logger.info('Checking module: {0}'.format(name))
        if name in installed_pkgs:
            pkg_name, version = installed_pkgs[name]
            reqs[pkg_name] = version
        else:
            guess.append(name)
    logger.info('Finish local environment checking.')
    return reqs, guess


if __name__ == '__main__':
    main()
