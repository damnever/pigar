Python project requirements tool – pigar
========================================

.. image:: https://img.shields.io/travis/damnever/pigar.svg?style=flat-square
    :target: https://travis-ci.org/damnever/pigar

.. image:: https://img.shields.io/pypi/v/pigar.svg?style=flat-square
    :target: https://pypi.python.org/pypi/pigar


**NOTE**: `Pipenv <https://packaging.python.org/tutorials/managing-dependencies/#managing-dependencies>`_ or other tools is recommended for improving your development flow.


.. image:: https://raw.githubusercontent.com/damnever/pigar/master/short-guide.gif
    :target: https://raw.githubusercontent.com/damnever/pigar/master/short-guide.gif

(In the GIF, the module ``urlparse`` has been removed in Python3, ``requests`` has been installed in virtual environment ``pigar-2.7``, not in ``pigar-3.5``)


Features
--------

- When generating requirements for a project, ``pigar`` can consider all kinds of complicated situations. For example, this project has `py2_requirements.txt <https://github.com/damnever/pigar/blob/master/py2_requirements.txt>`_ and `py3_requirements.txt <https://github.com/damnever/pigar/blob/master/py3_requirements.txt>`_ for different Python versions. ::

    # Generate requirements.txt for current directory.
    $ pigar

    # Generate requirements for given directory in given file.
    $ pigar -p ../dev-requirements.txt -P ../

  ``pigar`` will list all files which referenced the package, for example: ::

    # project/foo.py: 2,3
    # project/bar/baz.py: 2,7,8,9
    foobar == 3.3.3

  If the requirements file is overwritten, ``pigar`` will show the difference between the old and the new.

- If you do not know the import name that belongs to a specific package (more generally, does ``Import Error: xxx`` drive you crazy?), such as ``bs4`` which may come from ``beautifulsoup4`` or ``MySQLdb`` which could come from ``MySQL_Python``, try searching for it: ::

    $ pigar -s bs4 MySQLdb

- To check requirements for the latest version, just do: ::

    # Specify a requirements file.
    $ pigar -c ./requirements.txt

    # Or, you can let pigar search for *requirements.txt in the current directory
    # level by itself. If not found, pigar will generate requirements.txt
    # for the current project, then check for the latest versions.
    $ pigar -c

Installation
------------

``pigar`` can run on Python 2.7.+ and 3.2+. Install it with ``pip``: ::

    [sudo] pip install pigar

To get the newest code from GitHub: ::

  pip install git+https://github.com/damnever/pigar.git@[master or other branch] --upgrade

Usage
-----

::

    usage: pigar [-h] [-v] [-u] [-s NAME [NAME ...]] [-c [PATH]] [-l LOG_LEVEL]
                 [-i DIR [DIR ...]] [-p SAVE_PATH] [-P PROJECT_PATH]
                 [-o COMPARISON_OPERATOR]

    Python requirements tool -- pigar, it will do only one thing at each time.
    Default action is generate requirements.txt in current directory.

    optional arguments:
      -h, --help          show this help message and exit
      -v, --version       show pigar version information and exit
      -u, --update        update database, use it when pigar failed you, exit when
                          action done
      -s NAME [NAME ...]  search package name by import name, use it if you do not
                          know import name come from which package, exit when
                          action done
      -c [PATH]           check requirements for the latest version. If file path
                          not given, search *requirements.txt in current
                          directory, if not found, generate file requirements.txt,
                          exit when action done
      -l LOG_LEVEL        show given level log messages, argument can be (ERROR,
                          WARNING, INFO), case-insensitive
      -i DIR [DIR ...]    given a list of directory to ignore, relative directory,
                          *used for* -c and default action
      -p SAVE_PATH        save requirements in given file path, *used for* default
                          action
      -P PROJECT_PATH     project path, which is directory, *used for* default
                          action
      -o COMPARISON_OPERATOR
                          The comparison operator for versions, alternatives:
                          [==, ~=, >=]


More
----

``pigar`` does not use regular expressions in such a violent way. Instead, it uses AST, which is a better method for extracting imported names from arguments of ``exec``/``eval``, doctest of docstring, etc.

Also, ``pigar`` can detect the difference between different Python versions. For example, you can find ``concurrent.futures`` from the Python 3.2 standard library, but you will need install ``futures`` in earlier versions of Python to get ``concurrent.futures``.

Finally, you already saw ``Features``. You can learn more from the source code.

If you have any issues or suggestions, `please submit an issue on GitHub <https://github.com/damnever/pigar/issues>`_.

LICENSE
-------

`The BSD 3-Clause License <https://github.com/damnever/pigar/blob/master/LICENSE>`_
