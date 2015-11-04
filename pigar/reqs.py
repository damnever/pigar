# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import os
import sys
import fnmatch
import importlib
import imp
import ast
import doctest
import collections
try:
    from types import FileType  # py2
except ImportError:
    from io import IOBase as FileType  # py3

from .log import logger
from .utils import parse_git_config
from .modules import ImportedModules


def project_import_modules(project_path, ignores):
    """Get entire project all imported modules."""
    modules = ImportedModules()
    local_mods = list()
    cur_dir = os.getcwd()
    if not ignores:
        ignores = [os.path.join(project_path, d) for d in ['.git']]

    logger.info('Extracting project: {0}'.format(project_path))
    for dirpath, dirnames, files in os.walk(project_path, followlinks=True):
        if dirpath.startswith(tuple(ignores)):
            continue
        logger.info('Extracting directory: {0}'.format(dirpath))
        files = [fn for fn in files if fn[-3:] == '.py']
        local_mods.extend([fn[:-3] for fn in files])
        if '__init__.py' in files:
            local_mods.append(os.path.basename(dirpath))
        for file in files:
            fpath = os.path.join(dirpath, file)
            fake_path = fpath.split(cur_dir)[1][1:]
            logger.info('Extracting file: {0}'.format(fpath))
            with open(fpath, 'r') as f:
                modules |= file_import_modules(fake_path, f.read())

    logger.info('Finish extracting in project: {0}'.format(project_path))
    return modules, local_mods


def file_import_modules(fpath, fdata):
    """Get single file all imported modules."""
    modules = ImportedModules()
    str_codes = collections.deque([(fdata, 1)])

    while str_codes:
        str_code, lineno = str_codes.popleft()
        ic = ImportChecker(fpath, lineno)
        try:
            parsed = ast.parse(str_code)
            ic.visit(parsed)
        # Ignore SyntaxError in Python code.
        except SyntaxError:
            pass
        modules |= ic.modules
        str_codes.extend(ic.str_codes)
        del ic

    return modules


class ImportChecker(object):

    def __init__(self, fpath, lineno):
        self._fpath = fpath
        self._lineno = lineno - 1
        self._modules = ImportedModules()
        self._str_codes = collections.deque()

    def visit_Import(self, node):
        """As we know: `import a [as b]`."""
        lineno = node.lineno + self._lineno
        for alias in node.names:
            self._modules.add(alias.name, self._fpath, lineno)

    def visit_ImportFrom(self, node):
        """As we know: `from a import b [as c]`."""
        self._modules.add(node.module, self._fpath, node.lineno + self._lineno)

    def visit_Exec(self, node):
        """
        Check `expression` of `exec(expression[, globals[, locals]])`.
        **Just available in python 2.**
        """
        if hasattr(node.body, 's'):
            self._str_codes.append((node.body.s, node.lineno + self._lineno))

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
                    self._str_codes.append(
                        (node.value.args[0].s, node.lineno + self._lineno))
                # **`exec` function in Python 3.**
                elif (value.func.id == 'exec' and
                        hasattr(node.value.args[0], 's')):
                    self._str_codes.append(
                        (node.value.args[0].s, node.lineno + self._lineno))

    def visit_FunctionDef(self, node):
        """
        Check docstring of function, if docstring is used for doctest.
        """
        docstring = self._parse_docstring(node)
        if docstring:
            self._str_codes.append((docstring, node.lineno + self._lineno + 2))

    def visit_ClassDef(self, node):
        """
        Check docstring of class, if docstring is used for doctest.
        """
        docstring = self._parse_docstring(node)
        if docstring:
            self._str_codes.append((docstring, node.lineno + self._lineno + 2))

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

    @property
    def str_codes(self):
        return self._str_codes


# #
# Check whether it is stdlib module.
# #
_CHECKED = dict()


def is_stdlib(name):
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
                  ('site-packages' in module_info[1] or
                   'dist-packages' in module_info[1])):
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
