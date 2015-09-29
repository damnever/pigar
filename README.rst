Python requirements tool -- pigar
=================================

----

What pigar can do?
------------------

- Generate requirements for project, ``pigar`` can consider all kinds of complicated situations.::

    # Generate requirements.txt for current directory.
    $ pigar

    # Generate requirements for given directory in given file.
    $ pigar -p ../dev-requirements.txt -P ../

- If you do not know the import name belong to which package, such as ``bs4`` come from ``beautifulsoup4``, ``MySQLdb`` come from ``MySQL_Python``, search it:::

    $ pigar -s bs4 MySQLdb

- Check requirements latest version, just do:::

    # Specific a requirements file.
    $ pigar -c ./requirements.txt

    # Or, you can leave pigar search *requirements.txt in current directory level by itself,
    # if not found, pigar will generate requirements.txt for current project then check latest version.
    $ pigar -c

Installation
------------

Available in Python: 2.7.x, 3.3.x, 3.4.x::

    [sudo] pip install pyprg

Usage
-----

::

	usage: pigar [-h] [-v] [-u] [-s NAME [NAME ...]] [-c [PATH]] [-l LOG_LEVEL]
	             [-p SAVE_PATH] [-P PROJECT_PATH]

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
	  -p SAVE_PATH        save requirements in given file path, *used for* default
	                      action
	  -P PROJECT_PATH     project path, which is directory, *used for* default
	                      action

FAQ
---

My exercise... ``pipreqs`` use regular expression and write all standard module names to a file, this project use AST and a little trick.

Also, the project can consider all kinds of complicated situations, see [testcase]().

You do not want to install this package in pip2, and use it to gather python3 project requirements, such as Ubuntu 14.04(default python version is 2, but also has python3). Use virtual environment is recommended.

The version 2 and 3 compliant code, the program will ask you some module whether is belong to python2 or python3, depend on your current python version.

LISENSE
-------

`The BSD 3-Clause License <./LICENSE>`_