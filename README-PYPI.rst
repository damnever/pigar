.. image:: https://img.shields.io/travis/damnever/pigar.svg?style=flat-square
    :target: https://travis-ci.org/damnever/pigar

.. image:: https://img.shields.io/pypi/v/pigar.svg?style=flat-square
    :target: https://pypi.python.org/pypi/pigar


Features
--------

- Generate requirements for project, ``pigar`` can consider all kinds of complicated situations. In this project, `py2_requirements.txt <https://github.com/damnever/pigar/blob/master/py2_requirements.txt>`_ and `py3_requirements.txt <https://github.com/damnever/pigar/blob/master/py3_requirements.txt>`_ for different python versions ::

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

More
----

You can find more information on `GitHub <https://github.com/damnever/pigar>`_ .


