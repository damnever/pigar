Python project requirements tool -- pigar
=========================================

.. image:: https://img.shields.io/travis/Damnever/pigar.svg?style=flat-square
    :target: https://travis-ci.org/Damnever/pigar

.. image:: https://img.shields.io/pypi/v/pigar.svg?style=flat-square
    :target: https://pypi.python.org/pypi/pigar


.. image:: https://raw.githubusercontent.com/Damnever/pigar/master/short-view.gif
    :target: https://raw.githubusercontent.com/Damnever/pigar/master/short-view.gif

(In GIF, Module ``urlparse`` has been removed in Python3, ``requests`` has been installed in virtual environment ``pigar-2.7``, not in ``pigar-3.5``)


Features
--------

- Generate requirements for project, ``pigar`` can consider all kinds of complicated situations. In this project, `py2_requirements.txt <https://github.com/Damnever/pigar/blob/master/py2_requirements.txt>`_ and `py3_requirements.txt <https://github.com/Damnever/pigar/blob/master/py3_requirements.txt>`_ for different python versions ::

    # Generate requirements.txt for current directory.
    $ pigar

    # Generate requirements for given directory in given file.
    $ pigar -p ../dev-requirements.txt -P ../

  ``pigar`` will list all files which referenced the package, for example: ::

    # project/foo.py: 2,3
    # project/bar/baz.py: 2,7,8,9
    foobar == 3.3.3

  If requirements file is overwritten over, ``pigar`` will show difference between old and new.

- If you do not know the import name that belongs to a specific package (more generally, does ``Import Error: xxx`` drive you crazy?), such as ``bs4`` which may come from ``beautifulsoup4`` or ``MySQLdb`` which could come from ``MySQL_Python``, try searching for it: ::

    $ pigar -s bs4 MySQLdb

- To check requirements for the latest version, just do: ::

    # Specific a requirements file.
    $ pigar -c ./requirements.txt

    # Or, you can leave pigar search *requirements.txt in current directory
    # level by itself, if not found, pigar will generate requirements.txt
    # for current project then check latest version.
    $ pigar -c

Installation
------------

Available for Python: 2.7.+, 3.2+ ::

    [sudo] pip install pigar

Get newest code from GitHub ::

  pip install git+https://github.com/Damnever/pigar.git@[master or other branch] --upgrade

Usage
-----

::

    usage: pigar [-h] [-v] [-u] [-s NAME [NAME ...]] [-c [PATH]] [-l LOG_LEVEL]
             [-i DIR [DIR ...]] [-p SAVE_PATH] [-P PROJECT_PATH]

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
      -c [PATH]           check requirements latest version. If file path not
                          given, search *requirements.txt in current directory, if
                          not found, generate file requirements.txt, exit when
                          action done
      -l LOG_LEVEL        Show given level log messages, argument can be (ERROR,
                          WARNING, INFO, DEBUG), case-insensitive
      -i DIR [DIR ...]    Given a list of directory to ignore, relative directory,
                          *used for* -c and default action
      -p SAVE_PATH        save requirements in given file path, *used for* default
                          action
      -P PROJECT_PATH     project path, which is directory, *used for* default
                          action


More
----

``pigar`` does not use regular expressions in such a violent way, it uses AST, which is a better method for extracting imported names from arguments of ``exec``/``eval``, doctest of docstring, etc.

Also, ``pigar`` can detect the difference between differen Python versions. For example, you can find ``concurrent.futures`` from the Python 3.2 standard library, but you will need install ``futures`` in earlier versions of Python to get ``concurrent.futures``.

Finally, you already saw ``Features``. You can learn more from source code.

If you have any issues or suggestions, `please submit an issue on GitHub <https://github.com/Damnever/pigar/issues>`_. 

LICENSE
-------

`The BSD 3-Clause License <https://github.com/Damnever/pigar/blob/master/LICENSE>`_
