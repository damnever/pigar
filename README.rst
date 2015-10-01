Python requirements tool -- pigar
=================================



What pigar can do?
------------------

- Generate requirements for project, ``pigar`` can consider all kinds of complicated situations. ::

    # Generate requirements.txt for current directory.
    $ pigar

    # Generate requirements for given directory in given file.
    $ pigar -p ../dev-requirements.txt -P ../

- If you do not know the import name belong to which package, such as ``bs4`` may come from ``beautifulsoup4``, ``MySQLdb`` may come from ``MySQL_Python``, search it :::

    $ pigar -s bs4 MySQLdb

- Check requirements latest version, just do: ::

    # Specific a requirements file.
    $ pigar -c ./requirements.txt

    # Or, you can leave pigar search *requirements.txt in current directory
    # level by itself, if not found, pigar will generate requirements.txt
    # for current project then check latest version.
    $ pigar -c

Installation
------------

Available in Python: 2.7.x, 3.x ::

    [sudo] pip install pigar

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

More
----

Hope `pigar <https://github.com/Damnever/pigar>`_ is useful to you.

LISENSE
-------

`The BSD 3-Clause License <https://github.com/Damnever/pigar/blob/master/LICENSE>`_
