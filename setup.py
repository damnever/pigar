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
   - Including the import statements/magic from ``exec``/``eval``/``importlib``, doctest of docstring, etc.
- Searching ditributions(packages) by the top level import/module names.
- Checking the latest versions of requirements.


You can find more information on [GitHub](https://github.com/damnever/pigar).
"""  # noqa

with codecs.open('CHANGELOG.md', encoding='utf-8') as f:
    change_logs = f.read()

install_requires = [
    'click>=8.1.3',
    'nbformat>=4.4.0',
    'aiohttp>=3.8.3',
    # The following distributions: ./pigar/_vendor/pip_vendor_requirements.txt
    "CacheControl==0.12.11",
    "colorama==0.4.5",
    "distlib==0.3.6",
    "distro==1.7.0",
    "packaging==21.3",
    "pep517==0.13.0",
    "platformdirs==2.5.2",
    "requests==2.28.1",
    "certifi==2022.09.24",
    "urllib3==1.26.12",
    "rich==12.5.1",
    "resolvelib==0.8.1",
    "setuptools>50.0.0",  # DO NOT PIN IT.
    "tenacity==8.1.0",
    "tomli==2.0.1",
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
    project_urls={
        'Documentation': 'https://github.com/damnever/pigar',
        'Source': 'https://github.com/damnever/pigar',
    },
    author='damnever',
    author_email='the.xcdong@gmail.com',
    license='The BSD 3-Clause License',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    keywords='requirements.txt,automation,tool,module-search',
    packages=find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests"]
    ),
    python_requires='>=3.7',
    install_requires=install_requires,
    include_package_data=True,
    entry_points={'console_scripts': [
        'pigar=pigar.__main__:main',
    ]},
)
