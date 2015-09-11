## PyPRG - Python project requirements gatherer. (Developing)

-- Not just another [pipreqs](https://github.com/bndr/pipreqs).

***

[![Downloads](https://img.shields.io/pypi/dm/rq.svg)](https://pypi.python.org/pypi/rq)

My exercise... `pipreqs` use regular expression and write all standard module names to a file, this project use AST and a little trick.

Also, the project can consider all kinds of complicated situations, see [testcase]().

You do not want to install this package in pip2, and use it to gather python3 project requirements, such as Ubuntu 14.04(default python version is 2, but also has python3). Use virtual environment is recommended.

The version 2 and 3 compliant code, the program will ask you some module whether is belong to python2 or python3, depend on your current python version.

### Installation

```
[sudo] pip install pyprg
```

### Usage

Except `-o` do not write to file, other will do.

```
usage: pyprg [-h] [-o] [-p PATH] [-c] [-u] [projectpath]

positional arguments:
  projectpath           Project path, default to current directory.

optional arguments:
  -h, --help            show this help message and exit
  -o, --output          Just print out requirements information.
  -p PATH, --path PATH  Save requirements in given file path, default
                        to requirements.txt in current directory.
  -c, --check           Check requirements latest version in PYPI.
  -u, --update          Update requirements to latest version.
```

### LISENSE

[The BSD 3-Clause License](./LICENSE)