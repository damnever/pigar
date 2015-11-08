 # -*- coding: utf-8 -*-

try:
	import urlparse as parse  # Py2
except ImportError:
	from urllib import parse  # Py3
try:
	import __builtin__ as builtins  # Py2
except ImportError:
	import builtins  # Py3

import example1