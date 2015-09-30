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

from .utils import Color
from .log import logger


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

    logger.info('Finish extracting in project: {0}'.format(path), Color.GREEN)
    return modules, local_mods


def file_import_modules(data):
    """Get single file all imported modules."""
    def _recursion(ic, str_code):
        modules = set()
        ic.clear()
        parsed = ast.parse(str_code)
        ic.visit(parsed)
        modules |= set(ic.modules)
        for str_code in ic.str_codes:
            modules |= _recursion(ic, str_code)
        return modules
    ic = ImportChecker()
    return list(_recursion(ic, data))


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
        self._str_codes.add(node.body.s)

    def visit_Expr(self, node):
        """
        Check `expressin` of `eval(expression[, globals[, locals]])`.
        """
        # Built-in functions
        value = node.value
        if isinstance(value, ast.Call):
            if hasattr(value.func, 'id'):
                if value.func.id == 'eval':
                    self._str_codes.add(node.value.args[0].s)
                # **`exec` function in Python 3.**
                elif value.func.id == 'exec':
                    self._str_codes.add(node.value.args[0].s)

    def visit_FunctionDef(self, node):
        """
        Check docstring of function, if docstring is used for doctest.
        """
        docstring = _parse_docstring(node)
        if docstring:
            self._str_codes.add(docstring)
        # Do not ignore other node.
        for _node in node.body:
            self.visit(_node)

    def visit_ClassDef(self, node):
        """
        Check docstring of class, if docstring is used for doctest.
        """
        docstring = _parse_docstring(node)
        if docstring:
            self._str_codes.add(docstring)
        # Do not ignore other node!
        for _node in node.body:
            self.visit(_node)

    def clear(self):
        self._modules = set()
        self._str_codes = set()

    @property
    def modules(self):
        return list(self._modules)

    @property
    def str_codes(self):
        return list(self._str_codes)


def _parse_docstring(node):
    """Extract code from docstring."""
    docstring = ast.get_docstring(node)
    if docstring:
        parser = doctest.DocTestParser()
        examples = parser.get_doctest(docstring, {}, None, None, None).examples
        return ''.join([example.source for example in examples])
    return None


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


# #
# Get mapping for import top level name
# and install package name with version.
# #
def get_installed_pkgs_detail():
    mapping = dict()
    search_path = None
    for path in sys.path:
        if 'site-packages' in path:
            search_path = path

    for file in os.listdir(search_path):
        if fnmatch.fnmatch(file, '*-info'):
            pkg_name, version = file.split('-')[:2]
            if version.endswith('dist'):
                version = version.rsplit('.', 1)[0]
            top_level = os.path.join(search_path, file, 'top_level.txt')
            with open(top_level, 'r') as f:
                for line in f:
                    mapping[line.strip()] = (pkg_name, version)
    return mapping
