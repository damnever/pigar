# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import os
import argparse

from ._version import version


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        prog='pigar',
        #  usage='%(prog)s [options]',
        description='Python requirements tool -- %(prog)s, it will '
        'do only one thing at each time. Default action is generate'
        ' requirements.txt in current directory.'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s {0}'.format(version),
        help='show %(prog)s version information and exit')
    parser.add_argument(
        '-u', '--update',
        dest='update_db',
        action='store_true',
        help='update database, use it when %(prog)s failed you, exit when'
        ' action done')
    parser.add_argument(
        '-s',  # '--search',
        dest='search_names',
        nargs='+',
        metavar='NAME',
        default=[],
        help='search package name by import name, use it if you do not '
        'know import name come from which package, exit when action done')
    parser.add_argument(
        '-c',  # '--check',
        dest='check_path',
        metavar='PATH',
        nargs='?',
        type=path_check,
        const=os.getcwd(),
        help='check requirements latest version. If file path not given, '
        'search *requirements.txt in current directory, if not found, '
        'generate file requirements.txt, exit when action done')
    parser.add_argument(
        '-l',  # '--log_level'
        dest='log_level',
        nargs=1,
        type=log_level_check,
        default=['error'],
        help='Show given level log messages, argument can be '
        '(ERROR, WARNING, INFO, DEBUG), case-insensitive')
    parser.add_argument(
        '-p',  # '--path',
        dest='save_path',
        nargs=1,
        type=path_check,
        default=[os.path.join(os.getcwd(), 'requirements.txt')],
        help='save requirements in given file path, *used for* default action')
    parser.add_argument(
        '-P',  # '--projectpath',
        dest='project_path',
        nargs=1,
        type=projectpath_check,
        default=[os.getcwd()],
        help='project path, which is directory, *used for* default action')
    if args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(args=args)
    return (args.log_level[0], args.update_db, args.check_path,
            args.search_names, args.save_path[0], args.project_path[0])


def log_level_check(level):
    levels = ('ERROR', 'WRANING', 'INFO', 'DEBUG')
    if level.upper() in levels:
        return level
    raise argparse.ArgumentTypeError(
        '"{0}" not in "{1}"'.format(level, ', '.join(levels)))


def path_check(path):
    path = os.path.abspath(path)
    fdir = os.path.dirname(path)
    if os.path.isdir(fdir):
        return path
    msg = '"{0}" is not a valid file path.'.format(path)
    raise argparse.ArgumentTypeError(msg)


def projectpath_check(path):
    path = os.path.abspath(path)
    if os.path.isdir(path):
        return path
    msg = '"{0}" is not a valid directory path.'.format(path)
    raise argparse.ArgumentTypeError(msg)
