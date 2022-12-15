import os
import os.path
import pathlib
import io
import sys
import re
import difflib
import urllib.parse
import contextlib
from typing import Optional, List

from ._vendor.pip._internal.req.req_file import get_file_content
from ._vendor.pip._internal.req.constructors import parse_req_from_line
from ._vendor.pip._internal.network.session import PipSession
from ._vendor.pip._internal.exceptions import InstallationError

from packaging.version import Version
try:
    import colorama
except ImportError:
    colorama = None


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


class PraseRequirementError(InstallationError):
    pass


PIP_INSTALL_OPTIONS_RE = re.compile(
    r'^\s*(?P<opt>-r|--requirement|-e|--editable)\s*(?P<value>\S*)\s*.*'
)
SCHEME_RE = re.compile(r"^(http|https|file):", re.I)


def parse_requirements(fpath):
    """Parse requirements file."""
    referenced_files = set()

    with contextlib.closing(PipSession()) as pip_session:
        _, content = get_file_content(fpath, pip_session)

    for lineno, line in enumerate(content.splitlines()):
        origin_line = line
        line = line.strip()
        if line == '' or line.startswith('#'):
            continue
        match = PIP_INSTALL_OPTIONS_RE.match(line)
        if match:
            groups = match.groupdict()
            if groups['opt'] in ('-r', '--requirement'):
                req_path = groups['value']
                # original file is over http
                if SCHEME_RE.search(fpath):
                    # do a url join so relative paths work
                    req_path = urllib.parse.urljoin(fpath, req_path)
                # original file and nested file are paths
                elif not SCHEME_RE.search(req_path):
                    # do a join so relative paths work
                    req_path = os.path.join(
                        os.path.dirname(fpath),
                        req_path,
                    )
                referenced_files.add(req_path)
                continue
            elif groups['opt'] in ('-e', '--editable'):
                line = groups['value']
        elif line.startswith('-'):
            # Ignore all other options..
            continue

        line_source = "line {} of {}".format(lineno, fpath)
        try:
            req = parse_req_from_line(line, line_source)
            yield ParsedRequirementParts(
                req.requirement,
                req.link.url if req.link else '',
                req.markers,
                req.extras,
            )
        except InstallationError as e:
            raise PraseRequirementError(e.args)
        except Exception as e:
            raise PraseRequirementError(
                "Fail to parse {} on {}: {}", origin_line, line_source, e
            )

    for rfile in referenced_files:
        for req in parse_requirements(rfile):
            yield req


class ParsedRequirementParts(object):

    def __init__(
        self,
        requirement,
        url,
        markers,
        extras,
    ):
        self.requirement = requirement
        self.url = url
        self.markers = markers
        self.extras = extras

    @property
    def has_name(self):
        return self.requirement is not None

    @property
    def name(self):
        if self.requirement is not None:
            return self.requirement.name
        return self.url

    @property
    def specifier(self):
        if self.requirement is not None:
            spec = str(self.requirement.specifier)
            if spec != '':
                return spec
        return self.url


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


class InMemoryOrDiskFile(object):
    # The instance must be picklable.

    def __init__(
        self,
        name: str,
        data: Optional[bytes] = None,
        file_path: Optional[str] = None
    ):
        assert (data is not None or file_path is not None)
        self.name = name
        self._data = data
        self._path = file_path

        self._stream = None

    def opened(self):
        return self._stream is not None

    def open(self):
        if self._stream is not None:
            raise IOError(f'{self.name} already opened')

        if self._data is not None:
            self._stream = io.BytesIO(self._data)
        elif self._path is not None:
            self._stream = open(self._path, 'rb')
        else:
            raise RuntimeError('unreachable')

    def close(self):
        if self._stream is None:
            return
        self._stream.close()

    def __enter__(self):
        self.open()
        return self._stream

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()


def determine_python_sys_lib_paths() -> List[str]:
    pythonmmv_zip = f'python{sys.version_info.major}{sys.version_info.minor}.zip'
    # Ref: https://docs.python.org/3/library/sys_path_init.html
    py_sys_path_prefix = ''
    for path in sys.path:
        if os.path.basename(path) == pythonmmv_zip:
            py_sys_path_prefix = os.path.dirname(path)
            break
    if py_sys_path_prefix == '':
        raise RuntimeError('python sys path prefix not found')

    lib_paths = []
    for path in sys.path:
        if path == '':
            continue
        parts = pathlib.PurePath(path).parts
        if 'site-packages' in parts or 'dist-packages' in parts:
            continue
        if is_commonpath([path, py_sys_path_prefix], py_sys_path_prefix):
            lib_paths.append(path)
    return lib_paths


def is_commonpath(paths: List[str], target: str) -> bool:
    try:
        return os.path.commonpath(paths) == target
    except ValueError:
        # Raise ValueError if paths contain both absolute and relative pathnames,
        # the paths are on the different drives or if *paths* is empty.
        return False


def is_site_packages_path(path: str) -> bool:
    parts = pathlib.PurePath(path).parts
    return 'site-packages' in parts or 'dist-packages' in parts
