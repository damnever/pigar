import os
import re
import io
import ast
import tokenize
import doctest
import collections
import fnmatch
import os.path as pathlib
from typing import List, NamedTuple, Optional, Callable, Deque, Tuple, Iterable, Union

from .log import logger
from .helpers import trim_prefix

import nbformat


class Module(NamedTuple):
    name: str
    try_: bool
    file: str
    lineno: int


class Annotation(NamedTuple):
    distribution_name: Optional[str]
    top_level_import_name: Optional[str]
    file: str
    lineno: int


def _match_exclude_patterns(
    name: str, patterns: Iterable[str], root: str = ""
) -> bool:
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
    followlinks: bool = True,
    parse_requirement_annotations: bool = False,
) -> Tuple[List[Module], List[Annotation]]:
    """package_root must be a absolute path to package root,
    e.g. /path/to/pigar/pigar."""
    exclude_pattern_set = set(trim_prefix(p, './') for p in exclude_patterns
                              ) if exclude_patterns else set()
    exclude_pattern_set |= set(DEFAULT_GLOB_EXCLUDE_PATTERNS)

    imported_modules: List[Module] = []
    annotations: List[Annotation] = []

    for dirpath, subdirs, files in os.walk(
        project_root, followlinks=followlinks
    ):
        if _match_exclude_patterns(dirpath, exclude_pattern_set, project_root):
            logger.debug('excluded by glob patterns: %s', dirpath)
            subdirs.clear()
            continue

        for fn in files:
            fpath = pathlib.join(dirpath, fn)
            if _match_exclude_patterns(
                fpath, exclude_pattern_set, project_root
            ):
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
                if parse_requirement_annotations:
                    annotations.extend(
                        parse_file_comment_annotations(fpath, code)
                    )
    return imported_modules, annotations


def parse_file_comment_annotations(fpath: str,
                                   code: bytes) -> List[Annotation]:
    """Parse annotations in comments, the valid format is as follows:
        import foo # pigar: required-packages=pkg-bar
        import foo # pigar: required-distributions=pkg-bar # package name
        import foo # pigar: required-imports=bar # top level import name
    """
    annotations: List[Annotation] = []
    try:
        for token in tokenize.tokenize(io.BytesIO(code).readline):
            if token.type != tokenize.COMMENT:
                continue
            lineno, offset = token.start
            comment = token.line[offset:]
            if not comment.startswith("#"):
                continue
            comment = comment.lstrip("#").strip()
            if not comment.startswith("pigar:"):
                continue
            annotation = comment.lstrip("pigar:").strip().split("#", 1)[0]
            parts = annotation.split("=", 1)
            if len(parts) != 2:
                continue
            # No empty space allowed in parts.
            if parts[0] in ("required-packages", "required-distributions"):
                for name in parts[1].split(","):
                    annotations.append(
                        Annotation(
                            distribution_name=name,
                            top_level_import_name=None,
                            file=fpath,
                            lineno=lineno
                        )
                    )
            elif parts[0] == "required-imports":
                for name in parts[1].split(","):
                    annotations.append(
                        Annotation(
                            distribution_name=None,
                            top_level_import_name=name,
                            file=fpath,
                            lineno=lineno
                        )
                    )
    except Exception as e:
        logger.error("parse %s failed: %r", fpath, e)
    return annotations


# Match ipython notebook magics and shell commands.
# e.g %matplotlib inline or !pip install pigar
#
# Ref:
#  - https://ipython.readthedocs.io/en/stable/interactive/magics.html
#  - https://ipython.org/ipython-doc/3/interactive/shell.html
_ipynb_magics_and_commands_regex = re.compile(
    r"[^#]*\s*(!|%)[{a-zA-Z][a-zA-Z0-9_-]*.*"
)


def _read_code(fpath: str) -> Optional[bytes]:
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
        return code.encode(encoding="utf-8")
    elif fpath.endswith(".py"):
        with open(fpath, 'rb') as f:
            return f.read()
    return None


def parse_file_imports(
    fpath: str, content: bytes, visit_doc_str: bool = False
) -> List[Module]:
    py_codes: Deque[Tuple[bytes, int]] = collections.deque([(content, 1)])
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

    def __init__(
        self,
        rawcode_callback: Optional[Callable[[bytes, int], None]] = None,
        doc_str_enabled: bool = False,
    ):
        self._modules: List[Module] = []
        self._rawcode_callback = rawcode_callback
        self._doc_str_enabled = doc_str_enabled

    def parse(self, content: bytes, fpath: str, lineno: int):
        parsed = ast.parse(content)
        self._fpath = fpath
        self._mods = fpath[:-3].split("/")
        self._lineno = lineno - 1
        self.visit(parsed)

    def _add_module(self, name: str, try_: bool, lineno: int):
        self._modules.append(
            Module(name=name, try_=try_, file=self._fpath, lineno=lineno)
        )

    def _add_rawcode(self, code: bytes, lineno: int):
        if self._rawcode_callback:
            self._rawcode_callback(code, lineno)

    def visit_Import(self, node: ast.Import, try_: bool = False):
        """As we know: `import a [as b]`."""
        lineno = node.lineno + self._lineno
        for alias in node.names:
            self._add_module(alias.name, try_, lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom, try_: bool = False):
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

    def visit_TryExcept(self, node: ast.Try):
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

    def visit_Expr(self, node: ast.Expr):
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

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """
        Check docstring of function, if docstring is used for doctest.
        """
        if not self._doc_str_enabled:
            return

        docstring = self._parse_docstring(node)
        if docstring:
            self._add_rawcode(docstring, node.lineno + self._lineno + 2)

    def visit_ClassDef(self, node: ast.ClassDef):
        """
        Check docstring of class, if docstring is used for doctest.
        """
        if not self._doc_str_enabled:
            return

        docstring = self._parse_docstring(node)
        if docstring:
            self._add_rawcode(docstring, node.lineno + self._lineno + 2)

    def visit(self, node: ast.AST):
        """Visit a node, no recursively."""
        for node in ast.walk(node):
            method = 'visit_' + node.__class__.__name__
            getattr(self, method, lambda x: x)(node)

    @staticmethod
    def _parse_docstring(
        node: Union[ast.AsyncFunctionDef, ast.FunctionDef, ast.ClassDef,
                    ast.Module]
    ) -> Optional[bytes]:
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
                return '\n'.join([example.source for example in examples]
                                 ).encode(encoding="utf-8")
        return None

    @property
    def modules(self) -> List[Module]:
        return self._modules
