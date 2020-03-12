# -*- coding: utf-8 -*-

import os
import sys
import collections

import foobar

eval('import foo')

exec("import bar", {}, {})

exec("import foobaz")


def foo():
    import json
    pass


class A(object):
    """
    >>> import itertools
    """
    def baz(self):
        """
        >>> import baz
        """


def bar():
    """
    >>> import queue
    >>> def test():
    ...     import bisect
    ...     pass
    """
    pass


__import__('mod', globals(), locals())

importlib.import_module('name')

importlib.import_module('.name', 'pkg.subpkg')
