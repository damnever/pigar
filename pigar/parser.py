# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import os
import sys
import fnmatch
import ast
import doctest
import collections
import os.path as pathlib

from .log import logger
from .helpers import parse_git_config, trim_suffix

Module = collections.namedtuple('Module', ['name', 'try_', 'file', 'lineno'])


def parse_imports(package_root, ignores=None):
    """package_root must be a absolute path to package root,
    e.g. /path/to/pigar/pigar."""
    ignores = set(ignores) if ignores else set()
    ignores |= set([".hg", ".svn", ".git", "__pycache__"])
    ignored_paths = collections.defaultdict(set)
    for path in ignores:
        path = trim_suffix(path, "/")
        ignored_paths[pathlib.dirname(path)].add(pathlib.basename(path))

    imported_modules = []
    user_modules = set()

    for dirpath, dirnames, files in os.walk(package_root, followlinks=True):
        if dirpath in ignored_paths:
            dirnames[:] = [
                d for d in dirnames if d not in ignored_paths[dirpath]
            ]
        has_py = False
        for fn in files:
            fpath = pathlib.join(dirpath, fn)
            # C extension.
            if fn.endswith('.so'):
                has_py = True
                user_modules.add(fpath[:-3])
            # Normal Python file.
            if fn.endswith('.py'):
                has_py = True
                user_modules.add(fpath[:-3])
                imported_modules.extend(parse_file_imports(fpath))
        if has_py:
            user_modules.add(trim_suffix(dirpath, "/"))
    return imported_modules, user_modules


def parse_file_imports(fpath):
    with open(fpath, 'rb') as f:
        content = f.read()
    py_codes = collections.deque([(content, 1)])
    parser = ImportsParser(
        lambda code, lineno: py_codes.append((code, lineno))  # noqa
    )

    while py_codes:
        code, lineno = py_codes.popleft()
        try:
            parser.parse(code, fpath, lineno)
        except SyntaxError as e:
            # Ignore SyntaxError in Python code.
            logger.debug("parse %s:%d failed: %e", fpath, lineno, e)
    return parser.modules


class ImportsParser(object):
    def __init__(self, rawcode_callback=None):
        self._modules = []
        self._rawcode_callback = rawcode_callback

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
        if mod_name is None:
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
        elif hasattr(node.body, 'elts') and len(node.body.elts) >= 1:
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
        docstring = self._parse_docstring(node)
        if docstring:
            self._add_rawcode(docstring, node.lineno + self._lineno + 2)

    def visit_ClassDef(self, node):
        """
        Check docstring of class, if docstring is used for doctest.
        """
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
                dt = parser.get_doctest(docstring, {}, None, None, None)
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


def parse_installed_packages():
    """Get mapping for import top level name
    and install package name with version.
    """
    mapping = dict()

    for path in sys.path:
        if pathlib.isdir(path) and trim_suffix(path, '/').endswith(
            ('site-packages', 'dist-packages')
        ):
            mapping.update(_search_path(path))

    return mapping


def _search_path(path):
    mapping = dict()

    for file in os.listdir(path):
        # Install from PYPI.
        if fnmatch.fnmatch(file, '*-info'):
            top_level = os.path.join(path, file, 'top_level.txt')
            pkg_name, version = file.split('-')[:2]
            if version.endswith('dist'):
                version = version.rsplit('.', 1)[0]
            # Issue for ubuntu: sudo pip install xxx
            elif version.endswith('egg'):
                version = version.rsplit('.', 1)[0]
            mapping[pkg_name] = (pkg_name, version)
            if not os.path.isfile(top_level):
                continue
            with open(top_level, 'r') as f:
                for line in f:
                    mapping[line.strip()] = (pkg_name, version)

        # Install from local and available in GitHub.
        elif fnmatch.fnmatch(file, '*-link'):
            link = os.path.join(path, file)
            if not os.path.isfile(link):
                continue
            # Link path.
            with open(link, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line != '.':
                        dev_dir = line
            if not dev_dir:
                continue
            # Egg info path.
            info_dir = [
                _file for _file in os.listdir(dev_dir)
                if _file.endswith('egg-info')
            ]
            if not info_dir:
                continue
            info_dir = info_dir[0]
            top_level = os.path.join(dev_dir, info_dir, 'top_level.txt')
            # Check whether it can be imported.
            if not os.path.isfile(top_level):
                continue

            # Check .git dir.
            git_path = os.path.join(dev_dir, '.git')
            if os.path.isdir(git_path):
                config = parse_git_config(git_path)
                url = config.get('remote "origin"', {}).get('url')
                if not url:
                    continue
                branch = 'branch "master"'
                if branch not in config:
                    for section in config:
                        if 'branch' in section:
                            branch = section
                            break
                if not branch:
                    continue
                branch = branch.split()[1][1:-1]

                pkg_name = info_dir.split('.egg')[0]
                git_url = 'git+{0}@{1}#egg={2}'.format(url, branch, pkg_name)
                with open(top_level, 'r') as f:
                    for line in f:
                        mapping[line.strip()] = ('-e', git_url)
    return mapping
