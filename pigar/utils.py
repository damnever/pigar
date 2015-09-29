# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import re
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


# Color functions.
_NONE = lambda text: text
if colorama:
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


if __name__ == '__main__':
    rows = [
        ['tornado', '3.0.0', '4.0.1'],
        ['django', '1.5.0.1', '1.8']
    ]
    print_table(rows)
