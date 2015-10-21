# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import os
import sys
import fnmatch
import importlib
import imp
import ast
import doctest
try:
    from types import FileType  # py2
except ImportError:
    from io import IOBase as FileType  # py3

from .log import logger
from .utils import parse_git_config


def project_import_modules(path):
    """Get entire project all imported modules."""
    modules = list()
    local_mods = list()

    logger.info('Extracting project: {0}'.format(path))
    for dirpath, dirnames, files in os.walk(path):
        if '.git' in dirpath:
            continue
        logger.info('Extracting directory: {0}'.format(dirpath))
        files = [fn for fn in files if fn[-3:] == '.py']
        local_mods.extend([fn[:-3] for fn in files])
        if '__init__.py' in files:
            local_mods.append(os.path.basename(dirpath))
        for file in files:
            fpath = os.path.join(dirpath, file)
            logger.info('Extracting file: {0}'.format(fpath))
            with open(fpath, 'r') as f:
                modules.extend(file_import_modules(f.read()))

    logger.info('Finish extracting in project: {0}'.format(path))
    return modules, local_mods


def file_import_modules(data):
    """Get single file all imported modules."""
    modules = set()
    str_codes = set([data])
    ic = ImportChecker()

    while str_codes:
        ic.clear()
        str_code = str_codes.pop()
        try:
            parsed = ast.parse(str_code)
            ic.visit(parsed)
        # Ignore SyntaxError in Python code.
        except SyntaxError:
            pass
        modules |= set(ic.modules)
        str_codes |= set(ic.str_codes)

    return list(modules)


class ImportChecker(ast.NodeVisitor):

    def __init__(self, *args, **kwargs):
        self._modules = set()
        self._str_codes = set()
        super(ImportChecker, self).__init__(*args, **kwargs)

    def visit_Import(self, node):
        """As we know: `import a [as b]`."""
        self._modules |= {alias.name for alias in node.names}

    def visit_ImportFrom(self, node):
        """As we know: `from a import b [as c]`."""
        self._modules.add(node.module)

    def visit_Exec(self, node):
        """
        Check `expression` of `exec(expression[, globals[, locals]])`.
        **Just available in python 2.**
        """
        if hasattr(node.body, 's'):
            self._str_codes.add(node.body.s)

    def visit_Expr(self, node):
        """
        Check `expressin` of `eval(expression[, globals[, locals]])`.
        """
        # Built-in functions
        value = node.value
        if isinstance(value, ast.Call):
            if hasattr(value.func, 'id'):
                if (value.func.id == 'eval' and
                        hasattr(node.value.args[0], 's')):
                    self._str_codes.add(node.value.args[0].s)
                # **`exec` function in Python 3.**
                elif (value.func.id == 'exec' and
                        hasattr(node.value.args[0], 's')):
                    self._str_codes.add(node.value.args[0].s)

    def visit_FunctionDef(self, node):
        """
        Check docstring of function, if docstring is used for doctest.
        """
        docstring = self._parse_docstring(node)
        if docstring:
            self._str_codes.add(docstring)

    def visit_ClassDef(self, node):
        """
        Check docstring of class, if docstring is used for doctest.
        """
        docstring = self._parse_docstring(node)
        if docstring:
            self._str_codes.add(docstring)

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

    def clear(self):
        self._modules = set()
        self._str_codes = set()

    @property
    def modules(self):
        return list(self._modules)

    @property
    def str_codes(self):
        return list(self._str_codes)


# #
# Check whether it is stdlib module.
# #
_CHECKED = dict()


def is_stdlib(name):
    if '.' in name:
        name = name.split('.', 1)[0]
    if name in _CHECKED:
        return _CHECKED[name]

    exist = True
    module_info = ('', '', '')
    try:
        module_info = imp.find_module(name)
    except ImportError:
        try:
            # __import__(name)
            importlib.import_module(name)
            module_info = imp.find_module(name)
            sys.modules.pop(name)
        except ImportError:
            exist = False
    # Testcase: ResourceWarning
    if isinstance(module_info[0], FileType):
        module_info[0].close()
    if exist and (module_info[1] is not None and
                  'site-packages' in module_info[1]):
        exist = False
    _CHECKED[name] = exist
    return exist


def get_installed_pkgs_detail():
    """Get mapping for import top level name
    and install package name with version.
    """
    mapping = dict()
    search_path = None
    for path in sys.path:
        if os.path.isdir(path) and path.rstrip('/').endswith(
                ('site-packages', 'dist-packages')):
            search_path = path
            break

    if search_path is None:
        return mapping

    for file in os.listdir(search_path):
        # Install from PYPI.
        if fnmatch.fnmatch(file, '*-info'):
            top_level = os.path.join(search_path, file, 'top_level.txt')
            if not os.path.isfile(top_level):
                continue
            pkg_name, version = file.split('-')[:2]
            if version.endswith('dist'):
                version = version.rsplit('.', 1)[0]
            with open(top_level, 'r') as f:
                for line in f:
                    mapping[line.strip()] = (pkg_name, version)

        # Install from local and available in GitHub.
        elif fnmatch.fnmatch(file, '*-link'):
            link = os.path.join(search_path, file)
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
            info_dir = [_file for _file in os.listdir(dev_dir)
                        if _file.endswith('egg-info')]
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
