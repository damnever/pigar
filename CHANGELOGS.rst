Change Logs
-----------

Version 0.9.0 (2018.08.12)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Reuse connections.
- Update database.
- Fixed `#44 <https://github.com/damnever/pigar/issues/44>`_


Version 0.7.2 (2018.04.24)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Use https://pypi.org/
- Fixed `#41 <https://github.com/damnever/pigar/issues/41>`_


Version 0.7.1 (2017.11.07)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fixed `#34 <https://github.com/damnever/pigar/issues/34>`_


Version 0.7.0 (2017.07.03)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fixed the .egg suffix which caused by sudo pip install ... on Ubuntu.
- Workaround for special packages, such as `#29 <https://github.com/damnever/pigar/issues/34>`_


Version 0.6.10 (2016.06.17)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fixed `#26 <https://github.com/damnever/pigar/issues/26>`_
- Fixed relative import issue.


Version 0.6.9 (2016.05.08)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fixed ImportError.


Version 0.6.8 (2016.05.08)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Supported flask extension.
- Sorted requirements.
- Use gevent if possible.


Version 0.6.7 (2015.12.13)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- If modules in the ``try...except...`` block, assume they are optional.


Version 0.6.6 (2015.11.22)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fixed IndexError.


Version 0.6.5 (2015.11.22)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fixed AttributeError.
- Fixed PEP8 warning.


Version 0.6.4 (2015.11.22)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Removed useless code.
- Cache modules, to avoid duplication of inspection.

Thank `@spacewander <https://github.com/spacewander>`_ for the following contributions:

- Fixed error for Python 2.7.6.
- Fixed error when using './xxx' as relative path.
- Support ``importlib.import_module`` and ``__import__``.


Version 0.6.3 (2015.11.09)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Sort files, make comments more clearer.
- Fixed grammar, to make the README clearer. Thank `@roryokane <https://github.com/roryokane>`_ and `@flyingfisch <https://github.com/flyingfisch>`_.
- Make it work with ``python -m pigar``. Thank `@lilydjwg <https://github.com/lilydjwg>`_.
- Fixed the pep8 warnings: `#15 <https://github.com/damnever/pigar/pull/15>`_.
- Make output more clearer: `#12 <https://github.com/damnever/pigar/issues/12>`_.
- Fixed UnicodeDecodeError for Python 3.


Version 0.6.2 (2015.11.05)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- If requirements file is overwritten over, show difference between old and new.
- Adjust the structure of the code.


Version 0.6.1 (2015.11.03)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fixed typo.
- Follow symlinks.


Version 0.6.0 (2015.10.30)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Enhancement: issue `#7 <https://github.com/damnever/pigar/issues/7>`_, show imported module come from which files.
- Consider package installed via Git.
- Add command "-i", used to ignore a list of directory.


Version 0.5.5 (2015.10.21)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fixed issue `#2 <https://github.com/damnever/pigar/issues/2>`_ , `#3 <https://github.com/damnever/pigar/issues/3>`_ , `#4 <https://github.com/damnever/pigar/issues/4>`_ , `#5 <https://github.com/damnever/pigar/issues/5>`_.


Version 0.5.2-0.5.4 (2015.10.6)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fixed issue `#1 <https://github.com/damnever/pigar/issues/1>`_.
- Make version compare more effective.
- Removed useless code.


Version 0.5.1 (2015.10.01)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Available in PyPI(https://pypi.python.org/pypi/pigar).
- Generate requirements for Python project.
- Can consider different for different Python versions.
- Search package names by imported names.
