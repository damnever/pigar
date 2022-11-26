# Reference:
# http://stackoverflow.com/questions/16571150/how-to-capture-stdout-output-from-a-python-function-call

import sys
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


def py_version():
    return sys.version.split(' ')[0]
