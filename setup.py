#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import codecs

from setuptools import setup, find_packages

version = ''
with open('pigar/version.py', 'r') as f:
    version = re.search(
        r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.M
    ).group(1)

if not version:
    raise RuntimeError('Cannot find version information')

long_description = """
[![](https://img.shields.io/github/workflow/status/damnever/pigar/PyCI?style=flat-square)](https://github.com/damnever/pigar/actions)


- Generating requirements.txt for Python project.
   - Handling the difference between different Python versions.
   - Jupyter notebook (`*.ipynb`) support.
   - Including the import statements from `exec`/`eval`, doctest of docstring, etc.
- Searching packages by import name.
- Checking the latest versions for Python project.


You can find more information on [GitHub](https://github.com/damnever/pigar).
"""  # noqa

with codecs.open('CHANGELOG.md', encoding='utf-8') as f:
    change_logs = f.read()

install_requires = [
    'colorama>=0.3.9', 'requests>=2.20.0', 'nbformat>=4.4.0', 'packaging>=20.9'
    'futures;python_version<"3.2"'
]

setup(
    name='pigar',
    version=version,
    description=(
        'A fantastic tool to generate requirements for your'
        ' Python project, and more than that.'
    ),
    long_description=long_description + '\n\n' + change_logs,
    long_description_content_type="text/markdown",
    url='https://github.com/damnever/pigar',
    author='damnever',
    author_email='dxc.wolf@gmail.com',
    license='The BSD 3-Clause License',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3',
    ],
    keywords='requirements.txt,automation,tool,module-search',
    packages=find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests"]
    ),
    install_requires=install_requires,
    include_package_data=True,
    entry_points={'console_scripts': [
        'pigar=pigar.__main__:main',
    ]},
)
