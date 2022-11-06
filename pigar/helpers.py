# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import os
import sys
import re
import difflib
import functools
import os.path as pathlib
import collections

from packaging.requirements import Requirement, InvalidRequirement
from packaging.version import Version
try:
    import colorama
except ImportError:
    colorama = None

PY32 = sys.version_info[:2] == (3, 2)

if sys.version_info[0] == 3:
    binary_type = bytes
else:
    binary_type = str


class Dict(dict):
    """Convert dict key object to attribute."""

    def __init__(self, *args, **kwargs):
        super(Dict, self).__init__(*args, **kwargs)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError('"{0}"'.format(name))

    def __setattr__(self, name, value):
        self[name] = value


# Color functions, win8 ...
_NONE = lambda text: text  # noqa
if colorama and not sys.platform.startswith('win'):
    _GREEN = lambda text: colorama.Fore.GREEN + text + colorama.Fore.RESET  # noqa
    _YELLOW = lambda text: colorama.Fore.YELLOW + text + colorama.Fore.RESET  # noqa
    _RED = lambda text: colorama.Fore.RED + text + colorama.Fore.RESET  # noqa
    _BLUE = lambda text: colorama.Fore.BLUE + text + colorama.Fore.RESET  # noqa
    _WHITE = lambda text: colorama.Fore.WHITE + text + colorama.Fore.RESET  # noqa
else:
    _GREEN = _YELLOW = _RED = _BLUE = _WHITE = _NONE

Color = Dict(
    GREEN=_GREEN,
    YELLOW=_YELLOW,
    RED=_RED,
    BLUE=_BLUE,
    WHITE=_WHITE,
    NONE=_NONE,
)


def print_table(rows, headers=[]):
    """Print table. Such as:
     PACKAGE | CURRENT | LATEST
     --------+---------+-------
     pigar   | 0.4.5   | 0.5.0
    """
    end = len(headers) - 1
    hlens = [len(col) for col in headers]
    col_lens = hlens[:]
    for row in rows:
        col_lens = [
            max(col_lens[idx], len(col)) for idx, col in enumerate(row)
        ]
    width = sum(col_lens) + end*3 + 2
    print(' ' + '='*width, end='\n ')
    for idx, header in enumerate(headers):
        print(
            " {0}{1}".format(header, (col_lens[idx] - hlens[idx]) * ' '),
            end=' |' if idx != end else '\n  '
        )
    for idx, col_len in enumerate(col_lens):
        print('{0}'.format(col_len * '-'), end='-+-' if idx != end else '\n ')
    for row in rows:
        for idx, col in enumerate(row):
            print(
                ' {0}{1}'.format(col, (col_lens[idx] - len(col)) * ' '),
                end=' |' if idx != end else '\n '
            )
    print('=' * width)


ParsedRequirement = collections.namedtuple(
    'ParsedRequirement', ['name', 'specifier', 'url']
)


class PraseRequirementError(ValueError):
    pass


def parse_requirements(fpath):
    """Parse requirements file."""
    referenced_reqs_re = re.compile(r'^(-r|--requirement) *(?P<reqs_file>.*)')

    dup = set()
    referenced_files = set()
    with open(fpath, 'r') as f:
        for lineno, line in enumerate(f):
            line = line.strip()
            if line == '' or line.startswith('#'):
                continue
            referenced = referenced_reqs_re.match(line.strip())
            if referenced:
                # Parse referenced requirements file
                additional_reqs_file = referenced.groupdict()['reqs_file']
                if not pathlib.isabs(additional_reqs_file):
                    additional_reqs_file = os.path.join(
                        os.path.dirname(fpath), additional_reqs_file
                    )
                referenced_files.add(additional_reqs_file)
                continue
            if line.startswith('-'):
                # Ignore all other options..
                continue

            try:
                req = Requirement(line)
            except InvalidRequirement as e:
                raise PraseRequirementError('line {}: {}'.format(lineno, e))
            if req.name in dup:
                continue
            dup.add(req.name)
            yield ParsedRequirement(
                name=req.name,
                specifier=str(req.specifier)
                if req.specifier is not None else '',
                url=str(req.url) if req.url is not None else '',
            )

    for rfile in referenced_files:
        for req in parse_requirements(rfile):
            if req.name in dup:
                continue
            dup.add(req.name)
            yield req


def cmp_to_key(cmp_func):
    """Convert a cmp=function into a key=function."""

    class K(object):

        def __init__(self, obj, *args):
            self.obj = obj

        def __lt__(self, other):
            return cmp_func(self.obj, other.obj) < 0

        def __gt__(self, other):
            return cmp_func(self.obj, other.obj) > 0

        def __eq__(self, other):
            return cmp_func(self.obj, other.obj) == 0

    return K


def compare_version(version1, version2):
    """Compare version number, such as 1.1.1 and 1.1b2.0.
    Ref: https://peps.python.org/pep-0440/"""
    v1 = Version(version1)
    v2 = Version(version2)
    if v1 < v2:
        return -1
    if v1 > v2:
        return 1
    return 0


def parse_git_config(path):
    """Parse git config file."""
    config = dict()
    section = None

    with open(os.path.join(path, 'config'), 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('['):
                section = line[1:-1].strip()
                config[section] = dict()
            elif section:
                key, value = line.replace(' ', '').split('=', 1)
                config[section][key] = value
    return config


def lines_diff(lines1, lines2):
    """Show difference between lines."""
    is_diff = False
    diffs = list()

    for line in difflib.ndiff(lines1, lines2):
        if not is_diff and line[0] in ('+', '-'):
            is_diff = True
        diffs.append(line)

    return is_diff, diffs


def trim_prefix(content, prefix):
    if content.startswith(prefix):
        return content[len(prefix):]
    return content


def trim_suffix(content, suffix):
    if content.endswith(suffix):
        return content[:-len(suffix)]
    return content


def retry(e, count=3):

    def _wrapper(f):

        @functools.wraps(f)
        def _retry(*args, **kwargs):
            c = count
            while c > 1:
                try:
                    return f(*args, **kwargs)
                except e:
                    c -= 1
            return f(*args, **kwargs)

        return _retry

    return _wrapper
