#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os.path
import sys

from setuptools import setup


cur_dir = os.path.abspath(os.path.dirname(__file__))


with codecs.open(os.path.join(cur_dir, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

install_requires = ['colorama']
if sys.version_info < (3, 2):
    install_requires.append('futures')


setup(
    name='pigar',
    version='0.5.0',
    description='Python requirements tool -- pigar',
    long_description=long_description,
    url='https://github.com/Damnever/pigar',
    author='Damnever',
    author_email='dxc.wolf@gmail.com',
    license='BSD License',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='requirements tool',
    packages=['pigar', 'pigar.tests'],
    install_requires=install_requires,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'pigar=pigar.__main__:main',
        ]
    },
)
