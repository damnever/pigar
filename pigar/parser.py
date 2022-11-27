import os
import re
import ast
import doctest
import collections
import fnmatch
import os.path as pathlib
from typing import List, NamedTuple, Optional

from .log import logger
from .helpers import trim_prefix

import nbformat


class Module(NamedTuple):
    name: str
    try_: bool
    file: str
    lineno: int


def _match_exclude_patterns(name, patterns, root=""):
    # name = trim_prefix(trim_prefix(name, root), "/")
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


DEFAULT_GLOB_EXCLUDE_PATTERNS = (
    "**/.git",
    "**/.hg",
    "**/.svn",
    "**/__pycache__",
    "*venv*",
)


def parse_imports(
    project_root: str,
    visit_doc_str: bool = False,
    exclude_patterns: Optional[List[str]] = None,
    followlinks: bool = True
) -> List[Module]:
    """package_root must be a absolute path to package root,
    e.g. /path/to/pigar/pigar."""
    exclude_patterns = set(trim_prefix(p, './') for p in exclude_patterns
                           ) if exclude_patterns else set()
    exclude_patterns |= set(DEFAULT_GLOB_EXCLUDE_PATTERNS)

    imported_modules = []

    for dirpath, subdirs, files in os.walk(
        project_root, followlinks=followlinks
    ):
        if _match_exclude_patterns(dirpath, exclude_patterns, project_root):
            logger.debug('excluded by glob patterns: %s', dirpath)
            subdirs.clear()
            continue

        for fn in files:
            fpath = pathlib.join(dirpath, fn)
            if _match_exclude_patterns(fpath, exclude_patterns, project_root):
                logger.debug('excluded by glob patterns: %s', fpath)
                continue
            logger.debug('analyzing file: %s', fpath)

            code = _read_code(fpath)
            if code:
                imported_modules.extend(
                    parse_file_imports(
                        fpath, code, visit_doc_str=visit_doc_str
                    )
                )
    return imported_modules


# Match ipython notebook magics and shell commands.
# e.g %matplotlib inline or !pip install pigar
#
# Ref:
#  - https://ipython.readthedocs.io/en/stable/interactive/magics.html
#  - https://ipython.org/ipython-doc/3/interactive/shell.html
_ipynb_magics_and_commands_regex = re.compile(
    r"[^#]*\s*(!|%)[{a-zA-Z][a-zA-Z0-9_-]*.*"
)


def _read_code(fpath):
    if fpath.endswith(".ipynb"):
        nb = nbformat.read(fpath, as_version=4)
        code = ""
        for cell in nb.cells:
            if cell.cell_type != "code":
                continue
            for line in cell.source.splitlines():
                match = _ipynb_magics_and_commands_regex.match(line)
                if not (match and match.group(0) == line):
                    code += line
                code += "\n"
        return code
    elif fpath.endswith(".py"):
        with open(fpath, 'rb') as f:
            return f.read()
    return None


def parse_file_imports(fpath, content, visit_doc_str=False):
    py_codes = collections.deque([(content, 1)])
    parser = ImportsParser(
        lambda code, lineno: py_codes.append((code, lineno)),  # noqa
        doc_str_enabled=visit_doc_str,
    )

    while py_codes:
        code, lineno = py_codes.popleft()
        try:
            parser.parse(code, fpath, lineno)
        except SyntaxError as e:
            # Ignore SyntaxError in Python code.
            logger.warn("parse %s:%d failed: %r", fpath, lineno, e)
    return parser.modules


class ImportsParser(object):

    def __init__(self, rawcode_callback=None, doc_str_enabled=False):
        self._modules = []
        self._rawcode_callback = rawcode_callback
        self._doc_str_enabled = doc_str_enabled

    def parse(self, content, fpath, lineno):
        parsed = ast.parse(content)
        self._fpath = fpath
        self._mods = fpath[:-3].split("/")
        self._lineno = lineno - 1
        self.visit(parsed)

    def _add_module(self, name, try_, lineno):
        self._modules.append(
            Module(name=name, try_=try_, file=self._fpath, lineno=lineno)
        )

    def _add_rawcode(self, code, lineno):
        if self._rawcode_callback:
            self._rawcode_callback(code, lineno)

    def visit_Import(self, node, try_=False):
        """As we know: `import a [as b]`."""
        lineno = node.lineno + self._lineno
        for alias in node.names:
            self._add_module(alias.name, try_, lineno)

    def visit_ImportFrom(self, node, try_=False):
        """
        As we know: `from a import b [as c]`. If node.level is not 0,
        import statement like this `from .a import b`.
        """
        mod_name = node.module
        level = node.level
        if mod_name is not None:
            name = level*"." + mod_name
            lineno = node.lineno + self._lineno
            self._add_module(name, try_, lineno)
            return

        # Handle cases like: from .. import a
        level -= 1
        mod_name = ""
        for alias in node.names:
            name = mod_name
            if level > 0 or mod_name == "":
                name = level*"." + mod_name + "." + alias.name
            lineno = node.lineno + self._lineno
            self._add_module(name, try_, lineno)

    def visit_TryExcept(self, node):
        """
        If modules which imported by `try except` and not found,
        maybe them come from other Python version.
        """
        for ipt in node.body:
            if ipt.__class__.__name__.startswith('Import'):
                method = 'visit_' + ipt.__class__.__name__
                getattr(self, method)(ipt, True)
        for handler in node.handlers:
            for ipt in handler.body:
                if ipt.__class__.__name__.startswith('Import'):
                    method = 'visit_' + ipt.__class__.__name__
                    getattr(self, method)(ipt, True)

    # For Python 3.3+
    visit_Try = visit_TryExcept

    def visit_Exec(self, node):
        """
        Check `expression` of `exec(expression[, globals[, locals]])`.
        **Just available in python 2.**
        """
        if hasattr(node.body, 's'):
            self._add_rawcode(node.body.s, node.lineno + self._lineno)
        # PR#13: https://github.com/damnever/pigar/pull/13
        # Sometimes exec statement may be called with tuple in Py2.7.6
        elif hasattr(node.body, 'elts') and len(
            node.body.elts
        ) >= 1 and hasattr(node.body.elts[0], 's'):
            self._add_rawcode(node.body.elts[0].s, node.lineno + self._lineno)

    def visit_Expr(self, node):
        """
        Check `expression` of `eval(expression[, globals[, locals]])`.
        Check `expression` of `exec(expression[, globals[, locals]])`
        in python 3.
        Check `name` of `__import__(name[, globals[, locals[,
        fromlist[, level]]]])`.
        Check `name` or `package` of `importlib.import_module(name,
        package=None)`.
        """
        # Built-in functions
        value = node.value
        if isinstance(value, ast.Call):
            lineno = node.lineno + self._lineno
            if hasattr(value.func, 'id'):
                if (
                    value.func.id == 'eval'
                    and hasattr(node.value.args[0], 's')
                ):
                    self._add_rawcode(node.value.args[0].s, lineno)
                # **`exec` function in Python 3.**
                elif (
                    value.func.id == 'exec'
                    and hasattr(node.value.args[0], 's')
                ):
                    self._add_rawcode(node.value.args[0].s, lineno)
                # `__import__` function.
                elif (
                    value.func.id == '__import__' and len(node.value.args) > 0
                    and hasattr(node.value.args[0], 's')
                ):
                    self._add_module(node.value.args[0].s, False, lineno)
            # `import_module` function.
            elif getattr(value.func, 'attr', '') == 'import_module':
                module = getattr(value.func, 'value', None)
                if (
                    module is not None
                    and getattr(module, 'id', '') == 'importlib'
                ):
                    args = node.value.args
                    arg_len = len(args)
                    if arg_len > 0 and hasattr(args[0], 's'):
                        name = args[0].s
                        if not name.startswith('.'):
                            self._add_module(name, False, lineno)
                        elif arg_len == 2 and hasattr(args[1], 's'):
                            self._add_module(args[1].s, False, lineno)

    def visit_FunctionDef(self, node):
        """
        Check docstring of function, if docstring is used for doctest.
        """
        if not self._doc_str_enabled:
            return

        docstring = self._parse_docstring(node)
        if docstring:
            self._add_rawcode(docstring, node.lineno + self._lineno + 2)

    def visit_ClassDef(self, node):
        """
        Check docstring of class, if docstring is used for doctest.
        """
        if not self._doc_str_enabled:
            return

        docstring = self._parse_docstring(node)
        if docstring:
            self._add_rawcode(docstring, node.lineno + self._lineno + 2)

    def visit(self, node):
        """Visit a node, no recursively."""
        for node in ast.walk(node):
            method = 'visit_' + node.__class__.__name__
            getattr(self, method, lambda x: x)(node)

    @staticmethod
    def _parse_docstring(node):
        """Extract code from docstring."""
        docstring = ast.get_docstring(node)
        if docstring:
            parser = doctest.DocTestParser()
            try:
                dt = parser.get_doctest(docstring, {}, "", None, None)
            except ValueError:
                # >>> 'abc'
                pass
            else:
                examples = dt.examples
                return '\n'.join([example.source for example in examples])
        return None

    @property
    def modules(self):
        return self._modules
