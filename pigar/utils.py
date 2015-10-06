# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import re
import sys
try:
    import colorama
except ImportError:
    colorama = None


_PKG_V_RE = re.compile(r'^(?P<pkg>[^><==]+)[><==]{,2}(?P<version>.*)$')


class Dict(dict):
    """Convert dict key object to attribute."""

    def __init__(self, *args, **kwargs):
        super(Dict, self).__init__(*args, **kwargs)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError('"{0}"'.format(name))


# Color functions, win8 ...
_NONE = lambda text: text
if colorama and not sys.platform.startswith('win'):
    _GREEN = lambda text: colorama.Fore.GREEN + text + colorama.Fore.RESET
    _YELLOW = lambda text: colorama.Fore.YELLOW + text + colorama.Fore.RESET
    _RED = lambda text: colorama.Fore.RED + text + colorama.Fore.RESET
    _BLUE = lambda text: colorama.Fore.BLUE + text + colorama.Fore.RESET
    _WHITE = lambda text: colorama.Fore.WHITE + text + colorama.Fore.RESET
else:
    _GREEN = _YELLOW = _RED = _BLUE = _WHITE = _NONE

Color = Dict(
    GREEN=_GREEN, YELLOW=_YELLOW, RED=_RED,
    BLUE=_BLUE, WHITE=_WHITE, NONE=_NONE,
)


def print_table(rows, headers=['PACKAGE', 'CURRENT', 'LATEST']):
    """Print table. Such as:
     PACKAGE | CURRENT | LATEST
     --------+---------+-------
     pigar   | 0.4.5   | 0.5.0
    """
    end = len(headers) - 1
    hlens = [len(col) for col in headers]
    col_lens = hlens[:]
    for row in rows:
        col_lens = [max(col_lens[idx], len(col))
                    for idx, col in enumerate(row)]
    width = sum(col_lens) + end * 3 + 2
    print(' ' + '=' * width, end='\n ')
    for idx, header in enumerate(headers):
        print(" {0}{1}".format(header, (col_lens[idx] - hlens[idx]) * ' '),
              end=' |' if idx != end else '\n  ')
    for idx, col_len in enumerate(col_lens):
        print('{0}'.format(col_len * '-'), end='-+-' if idx != end else '\n ')
    for row in rows:
        for idx, col in enumerate(row):
            print(' {0}{1}'.format(col, (col_lens[idx] - len(col)) * ' '),
                  end=' |' if idx != end else '\n ')
    print('=' * width)


def parse_reqs(fpath):
    """Parse requirements file."""
    reqs = dict()
    with open(fpath, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            m = _PKG_V_RE.match(line.strip())
            if m:
                d = m.groupdict()
                reqs[d['pkg'].strip()] = d['version'].strip()
    return reqs


def cmp_to_key(cmp_func):
    """Convert a cmp=fcuntion into a key=function."""
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
    """Compare version number, such as 1.1.1 and 1.1b2.0."""
    v1, v2 = list(), list()

    for item in version1.split('.'):
        if item.isdigit():
            v1.append(int(item))
        else:
            v1.extend([i for i in _group_alnum(item)])
    for item in version2.split('.'):
        if item.isdigit():
            v2.append(int(item))
        else:
            v2.extend([i for i in _group_alnum(item)])

    while v1 and v2:
        item1, item2 = v1.pop(0), v2.pop(0)
        if item1 > item2:
            return 1
        elif item1 < item2:
            return -1

    if v1:
        return 1
    elif v2:
        return -1
    return 0


def _group_alnum(s):
    tmp = list()
    flag = 1 if s[0].isdigit() else 0
    for c in s:
        if c.isdigit():
            if flag == 0:
                yield ''.join(tmp)
                tmp = list()
                flag = 1
            tmp.append(c)
        elif c.isalpha():
            if flag == 1:
                yield int(''.join(tmp))
                tmp = list()
                flag = 0
            tmp.append(c)
    last = ''.join(tmp)
    yield (int(last) if flag else last)
