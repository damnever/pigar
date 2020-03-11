#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
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

with codecs.open('README-PYPI.rst', encoding='utf-8') as f:
    long_description = f.read()

with codecs.open('CHANGELOGS.rst', encoding='utf-8') as f:
    change_logs = f.read()

install_requires = [
    'colorama>=0.3.9',
    'requests>=2.20.0',
]
if sys.version_info < (3, 2):
    install_requires.append('futures')

setup(
    name='pigar',
    version=version,
    description=(
        'A fantastic tool to generate requirements for your'
        ' Python project, and more than that.'
    ),
    long_description=long_description + '\n\n' + change_logs,
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
    ],
    keywords='requirements tool',
    packages=find_packages(),
    install_requires=install_requires,
    include_package_data=True,
    entry_points={'console_scripts': [
        'pigar=pigar.__main__:main',
    ]},
)
