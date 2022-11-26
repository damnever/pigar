## pigar

[![](https://img.shields.io/github/workflow/status/damnever/pigar/PyCI?style=flat-square)](https://github.com/damnever/pigar/actions) [![](https://img.shields.io/pypi/v/pigar.svg?style=flat-square)](https://pypi.org/project/pigar)


- Generating requirements.txt for Python project.
   - Handling the difference between different Python versions.
   - Jupyter notebook (`*.ipynb`) support.
   - Including the import statements/magic from ``exec``/``eval``/``importlib``, doctest of docstring, etc.
- Searching ditributions(packages) by the top level import/module names.
- Checking the latest versions of requirements.

**NOTE**: [Pipenv](https://packaging.python.org/tutorials/managing-dependencies/#managing-dependencies) or other tools is recommended for improving your development flow.


### Installation

`pigar` can run on Python 3.7+.

To install it with `pip`, use:
```
[sudo] pip install pigar
```
To install it with ``conda``, use:
```
conda install -c conda-forge pigar
```
To get the newest code from GitHub:
```
pip install git+https://github.com/damnever/pigar.git@[main or other branch] --upgrade
```

### Usage

- `pigar` can consider most kinds of complicated situations(see [FAQ](#faq)). For example, this project has different [requirements](./requirements/) for different Python versions (`pigar v1` has [py2_requirements.txt](https://github.com/damnever/pigar/blob/c68d372fba4a6f98228ec3cf8e273f59d68d0e3c/py2_requirements.txt) and [py3_requirements.txt](https://github.com/damnever/pigar/blob/c68d372fba4a6f98228ec3cf8e273f59d68d0e3c/py3_requirements.txt)).

    ```
    # Generate requirements.txt for current directory.
    $ pigar generate

    # Generating requirements.txt for given directory in given file.
    $ pigar gen -f ../dev-requirements.txt ../
    ```

    `pigar gen --with-referenced-comments` can list all files which referenced the package/distribution(the line numbers for Jupyter notebook may be a bit confusing), for example:
    ```
    # project/foo.py: 2,3
    # project/bar/baz.py: 2,7,8,9
    foobar == 3.3.3
    ```

    If the requirements.txt is overwritten, ``pigar`` will show the difference between the old and the new, use `--dont-show-differences` to disable it.

    **NOTE**, `pigar` will search the packages/distributions in local environment first, then it will do further analysis and search missing packages/distributions on PyPI.

- If you do not know the import name that belongs to a specific distribution (more generally, does `Import Error: xxx` drive you crazy?), such as `bs4` which may come from `beautifulsoup4` or `MySQLdb` which could come from `mysql-python`, try searching for it:

    ```
    $ pigar search bs4 MySQLdb
    ```

- Checking for the latest version:

    ```
    # Specify a requirements file.
    $ pigar check -f ./requirements.txt

    # Or, you can let pigar searching all *requirements.txt in the current directory
    # level by itself.
    $ pigar check
    ```

- More:

  TIP: `pigar` accepts a prefix for a command, such as `pigar gen`, `pigar c`.
   ```
   pigar --help
   ```


### FAQ

<details>
  <summary>
  Is `pigar` a dependency management tool?
  </summary>

**No.** I've thought about this many times, but there is too much dirty work to be done to make `pigar`'s way reliable.

I like the way `pigar` does the job, but sadly, `pigar` does a bad job of managing dependencies, `pigar` is more like a tool to assist an old project to migrate to a new development workflow.
</details>

<details>
  <summary>
  (1) Why does `pigar` show multiple packages/distributions for the same import name?

  (2) Why does `pigar` generate different packages/distributions for the same import name in different environment?
  </summary>

`pigar` can not handle those situations gracefully, you may need to remove the duplicate packages in requirements.txt manually, or select one of them when `pigar` asks you.
Install the required packages/distributions(remove others) in local environment should fix it as well.

Related issues: [#32](https://github.com/damnever/pigar/issues/32), [#68](https://github.com/damnever/pigar/issues/68), [#75](https://github.com/damnever/pigar/issues/75#issuecomment-605639825).
</details>

<details>
  <summary>
  Why can't `pigar` find the packages/distributions that have not been explicit import?
  </summary>

Some frameworks may use some magic to import the modules for users automatically, and `pigar` can not handle it, you may need to fix it manually.

Related issues: [#33](https://github.com/damnever/pigar/issues/33), [#103](https://github.com/damnever/pigar/issues/103)
</details>


### More

`pigar` does not use regular expressions in such a violent way. Instead, it uses AST, which is a better method for extracting imported names from arguments of `exec`/`eval`/`importlib`, doctest of docstring, etc. However, `pigar` can not solve all the tricky problems, see [FAQ](https://github.com/damnever/pigar#faq).

Also, `pigar` can detect the difference between different Python versions. For example, you can find `concurrent.futures` from the Python 3.2 standard library, but you will need install `futures` in earlier versions of Python to get `concurrent.futures`, this is not a hardcode.

If you have any issues or suggestions, [please submit an issue on GitHub](https://github.com/damnever/pigar/issues). [**All contributions are appreciated!**](https://github.com/damnever/pigar/graphs/contributors)


### LICENSE

[The BSD 3-Clause License](https://github.com/damnever/pigar/blob/master/LICENSE)
