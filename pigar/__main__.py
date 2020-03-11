# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import os
import argparse

from .version import version
from .log import enable_pretty_logging
from .core import (
    RequirementsGenerator, check_requirements_latest_versions,
    search_packages_by_names, update_database
)


def _log_level_check(level):
    levels = ('ERROR', 'WARNING', 'INFO', 'DEBUG')
    if level.upper() in levels:
        return level
    raise argparse.ArgumentTypeError(
        '"{0}" not in "{1}"'.format(level, ', '.join(levels))
    )


def _ignore_dirs_check(d):
    ignore = os.path.abspath(d)
    if not os.path.isdir(ignore):
        raise argparse.ArgumentTypeError('"{0}" is not directory.'.format(d))
    return ignore


def _path_check(path):
    path = os.path.abspath(path)
    fdir = os.path.dirname(path)
    if os.path.isdir(fdir):
        return path
    msg = '"{0}" is not a valid file path.'.format(path)
    raise argparse.ArgumentTypeError(msg)


def _projectpath_check(path):
    path = os.path.abspath(path)
    if os.path.isdir(path):
        return path
    msg = '"{0}" is not a valid directory path.'.format(path)
    raise argparse.ArgumentTypeError(msg)


def _comparison_operator_check(op, supported_ops=('==', '~=', '>=')):
    if op in supported_ops:
        return op
    msg = 'invalid operator: {0}, supported operators: {1}'.format(
        op, supported_ops
    )
    raise argparse.ArgumentTypeError(msg)


parser = argparse.ArgumentParser(
    prog='pigar',
    #  usage='%(prog)s [options]',
    description='Python requirements tool -- %(prog)s, it will '
    'do only one thing at each time. Default action is generate'
    ' requirements.txt in current directory.'
)
parser.add_argument(
    '-v',
    '--version',
    action='version',
    version='%(prog)s {0}'.format(version),
    help='show %(prog)s version information and exit'
)
parser.add_argument(
    '-u',
    '--update',
    dest='update_db',
    action='store_true',
    help='update database, use it when %(prog)s failed you, exit when'
    ' action done'
)
parser.add_argument(
    '-s',  # '--search',
    dest='search_names',
    nargs='+',
    metavar='NAME',
    default=[],
    help='search package name by import name, use it if you do not '
    'know import name come from which package, exit when action done'
)
parser.add_argument(
    '-c',  # '--check',
    dest='check_path',
    metavar='PATH',
    nargs='?',
    type=_path_check,
    const=os.getcwd(),
    help='check requirements for the latest version. If file path not '
    'given, search *requirements.txt in current directory, if not found, '
    'generate file requirements.txt, exit when action done'
)
parser.add_argument(
    '-l',  # '--log_level'
    dest='log_level',
    nargs=1,
    type=_log_level_check,
    default=['error'],
    help='show given level log messages, argument can be '
    '(ERROR, WARNING, INFO, DEBUG), case-insensitive'
)
parser.add_argument(
    '-i',  # '--ignore'
    dest='ignores',
    nargs='+',
    metavar='DIR',
    default=[],
    type=_ignore_dirs_check,
    help='given a list of directory to ignore, relative directory, '
    '*used for* -c and default action'
)
parser.add_argument(
    '-p',  # '--path',
    dest='save_path',
    nargs=1,
    type=_path_check,
    default=[os.path.join(os.getcwd(), 'requirements.txt')],
    help='save requirements in given file path, *used for* default action'
)
parser.add_argument(
    '-P',  # '--projectpath',
    dest='project_path',
    nargs=1,
    type=_projectpath_check,
    default=[os.getcwd()],
    help='project path, which is directory, *used for* default action'
)
parser.add_argument(
    '-o',  # '--comparison-operator',
    dest='comparison_operator',
    nargs=1,
    type=_comparison_operator_check,
    default=['=='],
    help='The comparison operator for versions, alternatives: [==, ~=, >=]'
)
parser.add_argument(
    '--without-referenced-comments',
    dest='ref_comments',
    action='store_false',
    help='Omit requirements.txt comments showing the file and line of '
    'each import'
)


def main():
    args = parser.parse_args()

    enable_pretty_logging(log_level=args.log_level[0])

    if args.update_db:
        update_database()
    elif args.check_path:
        check_requirements_latest_versions(
            args.check_path, args.ignores, args.comparison_operator[0],
            args.ref_comments
        )
    elif args.search_names:
        search_packages_by_names(args.search_names)
    else:
        RequirementsGenerator(
            args.project_path[0], args.save_path[0], args.ignores,
            args.comparison_operator[0], args.ref_comments
        ).generate()


if __name__ == '__main__':
    main()
