# -*- coding: utf-8 -*-

"""pypr - Python project requirements tool."""

from __future__ import print_function, division, absolute_import

from .utils import PY32

if not PY32:
    from gevent import monkey
    monkey.patch_all()
