# -*- coding: utf-8 -*-
# Reference:
# http://stackoverflow.com/questions/16571150/how-to-capture-stdout-output-from-a-python-function-call

from __future__ import print_function, division, absolute_import

import sys
try:
    from cStringIO import StringIO
except ImportError:
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO


class CaptureOutput(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._strio = StringIO()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.extend(self._strio.getvalue().splitlines())
        self._strio.close()
        sys.stdout = self._stdout
