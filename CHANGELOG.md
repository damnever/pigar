### Change Logs


#### Version 2.0.4 (2022.12.22)

See what’s changed in detail [between v2.0.3 and v2.0.4](https://github.com/damnever/pigar/compare/v2.0.3...v2.0.4).


#### Version 2.0.3 (2022.12.15)

- Bump certifi from 2022.9.24 to 2022.12.7 (ref: https://github.com/advisories/GHSA-43fp-rhv2-5gv8)
- Fixed os.path.commonpath raises ValueError for different drives.

See what’s changed in detail [between v2.0.2 and v2.0.3](https://github.com/damnever/pigar/compare/v2.0.2...v2.0.3).


#### Version 2.0.2 (2022.12.04)

- Ignore absolute path in [distributions' installed files](https://peps.python.org/pep-0627/#clarifications-in-the-record-file).
- Ignore vcs exception when parsing information for EggInfoDistribution.
- Sort searched results, print unknown if version not found.
- Fix dirty records in the index database.


#### Version 2.0.1 (2022.12.03)

Make absolute import more reliable by searching parent directory as well.


#### Version 2.0.0 (2022.12.02)

This version has changed a lot of things, most of them are **BREAKING CHANGE**s!

- **Dropped support for Python versions older than 3.7.**
- **Redesigned the command line interface.**
  - `pigar generate` to generate requirements.txt.
  - `pigar search` to search packages/distributions by the top level module names.
  - `pigar check` to check the latest versions of requirements.
  - `pigar -h` to explore more.
  - `pigar` accepts a prefix for a command, such as `pigar gen`, `pigar c`.
- **Refactored a lot of code and interfaces.**
- [Vendoring](https://github.com/pradyunsg/vendoring) the [pip](https://github.com/pypa/pip) to access more sophisticated utilities(`pip` named it's module as `_internal` so vendoring technology is introduced).
  - Fixed a lot of issues when parsing the requirements file, e.g. [#113](https://github.com/damnever/pigar/issues/113).
  - Fixed the issues for editable requirements, e.g. [#60](https://github.com/damnever/pigar/issues/60).
- Tweaked some default actions and introduced more options for better user experience.
  - `pigar` will ask user to choose the right packages/distributions if `pigar` has found multiple packages/distributions for the same module names. With `--auto-select` enabled, `pigar` will guess the best matched one or choose all possible packages/distributions automatically.
  - Added an option `--dry-run` which allows `pigar` to not write a requirements.txt file, just print it.
  - Added an option `--follow-symbolic-links/--dont-follow-symbolic-links` to let user decide whether to follow the symbolic links, fixed [#89](https://github.com/damnever/pigar/issues/89).
  - Added an option `-i/--index-url` to allow the custom URL of the Python Package Index, fixed [#52](https://github.com/damnever/pigar/issues/52).
  - Removed the spaces from requirements specifier, fixed [#86](https://github.com/damnever/pigar/issues/86).
  - Added an option `--show-differences/--dont-show-differences` to enable or disable showing the differences when the requirements file is overwritten.
- Introduced `asyncio` to synchronize distributions' metadata with the PyPI, the process is much faster now.
- Refactored the code to make the index database more reliable.
  - Add unique contstraints to avoid duplicate records, fixed [#119](https://github.com/damnever/pigar/issues/119).
  - Store versions in the database to do incremental index synchronization.


#### Version 1.0.2 (2022.11.12)

- Fix requirements list in setup.py [#122](https://github.com/damnever/pigar/pull/122).

#### Version 1.0.1 (2022.11.12)

- Support `*.ipynb` magics and shell command, fixed [#87](https://github.com/damnever/pigar/issues/87). See [#102](https://github.com/damnever/pigar/pull/102), [#117](https://github.com/damnever/pigar/pull/117), [#118](https://github.com/damnever/pigar/pull/118) for details.
- Parse requirements file with the more sophisticated utility, fixed [#48](https://github.com/damnever/pigar/issues/48), [#113](https://github.com/damnever/pigar/issues/113). See [#115](https://github.com/damnever/pigar/pull/115) for details.
- Fixed [#99](https://github.com/damnever/pigar/issues/99), continue if a local package isn't exists. See [#107](https://github.com/damnever/pigar/pull/107) for details.
- Fixed too many values to unpack error when parsing git config. See [#97](https://github.com/damnever/pigar/pull/97) for details.


#### Version 1.0.0 (2022.06.22)

- **BREAKING CHANGE:** Disable the comments which contain filenames and line numbers by default, use `--with-referenced-comments` to enable this feature.
- Skip if local package (edit-mode project) not found, fixed [#99]((https://github.com/damnever/pigar/issues/61)).


#### Version 0.10.0 (2020.03.14)

- Refactored the main logic, **the interface has been changed**, be careful if you are using `pigar` as a library.
- Handle the HTTP error, fixed [#61](https://github.com/damnever/pigar/issues/61).
- Ignore local packages quietly, fixed [#47](https://github.com/damnever/pigar/issues/47), [#58](https://github.com/damnever/pigar/issues/58) and [#65](https://github.com/damnever/pigar/issues/65).

Thank [@bganglia](https://github.com/bganglia) for the following contributions:

- Add Jupyter notebook(`.ipynb`) support, refer to [#69](https://github.com/damnever/pigar/issues/69).
- Option to turn off filenames and line numbers in requirements.txt, refer to [#65](https://github.com/damnever/pigar/issues/65).
- Fix check path, refer to [#64](https://github.com/damnever/pigar/issues/64).
- And [more](https://github.com/damnever/pigar/pulls?q=is%3Apr+author%3Abganglia).


#### Version 0.9.2 (2019.04.11)

- Make version comparison operator configurable, fixed [#37](https://github.com/damnever/pigar/issues/37)


#### Version 0.9.1 (2019.02.17)

- Fixed potential security vulnerabilities by updating requests.
- Fixed [#49](https://github.com/damnever/pigar/issues/49)


#### Version 0.9.0 (2018.08.12)

- Reuse connections.
- Update database.
- Fixed [#44](https://github.com/damnever/pigar/issues/44)


#### Version 0.7.2 (2018.04.24)

- Use https://pypi.org/
- Fixed [#41](https://github.com/damnever/pigar/issues/41)


#### Version 0.7.1 (2017.11.07)

- Fixed [#34](https://github.com/damnever/pigar/issues/34)


#### Version 0.7.0 (2017.07.03)

- Fixed the .egg suffix which caused by sudo pip install ... on Ubuntu.
- Workaround for special packages, such as [#29](https://github.com/damnever/pigar/issues/34)


#### Version 0.6.10 (2016.06.17)

- Fixed [#26](https://github.com/damnever/pigar/issues/26)
- Fixed relative import issue.


#### Version 0.6.9 (2016.05.08)

- Fixed ImportError.


#### Version 0.6.8 (2016.05.08)

- Supported flask extension.
- Sorted requirements.
- Use gevent if possible.


#### Version 0.6.7 (2015.12.13)

- If modules in the `try...except...` block, assume they are optional.


#### Version 0.6.6 (2015.11.22)

- Fixed IndexError.


#### Version 0.6.5 (2015.11.22)

- Fixed AttributeError.
- Fixed PEP8 warning.


#### Version 0.6.4 (2015.11.22)

- Removed useless code.
- Cache modules, to avoid duplication of inspection.

Thank [@spacewander](https://github.com/spacewander) for the following contributions:

- Fixed error for Python 2.7.6.
- Fixed error when using './xxx' as relative path.
- Support `importlib.import_module` and `__import__`.


#### Version 0.6.3 (2015.11.09)

- Sort files, make comments more clearer.
- Fixed grammar, to make the README clearer. Thank [@roryokane](https://github.com/roryokane) and [@flyingfisch](https://github.com/flyingfisch).
- Make it work with `python -m pigar`. Thank [@lilydjwg](https://github.com/lilydjwg).
- Fixed the pep8 warnings: [#15](https://github.com/damnever/pigar/pull/15).
- Make output more clearer: [#12](https://github.com/damnever/pigar/issues/12).
- Fixed UnicodeDecodeError for Python 3.


#### Version 0.6.2 (2015.11.05)

- If requirements file is overwritten over, show difference between old and new.
- Adjust the structure of the code.


#### Version 0.6.1 (2015.11.03)

- Fixed typo.
- Follow symlinks.


#### Version 0.6.0 (2015.10.30)

- Enhancement: issue [#7](https://github.com/damnever/pigar/issues/7), show imported module come from which files.
- Consider package installed via Git.
- Add command "-i", used to ignore a list of directory.


#### Version 0.5.5 (2015.10.21)

- Fixed issue [#2](https://github.com/damnever/pigar/issues/2) , [#3](https://github.com/damnever/pigar/issues/3) , [#4](https://github.com/damnever/pigar/issues/4) , [#5](https://github.com/damnever/pigar/issues/5).


#### Version 0.5.2-0.5.4 (2015.10.6)

- Fixed issue [#1](https://github.com/damnever/pigar/issues/1).
- Make version compare more effective.
- Removed useless code.


#### Version 0.5.1 (2015.10.01)

- Available in PyPI(https://pypi.python.org/pypi/pigar).
- Generate requirements for Python project.
- Can consider different for different Python versions.
- Search package names by imported names.
