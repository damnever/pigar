# -*- coding: utf-8 -*-

import os
import sys
import collections

import foobar


eval('import foo')


exec("import bar", {}, {})


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
    >>> import Queue
    >>> def test():
    ...     import bisect
    ...     pass
    """
    pass
