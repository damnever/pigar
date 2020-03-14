## pigar

[![](https://img.shields.io/github/workflow/status/damnever/pigar/PyCI?style=flat-square)](https://github.com/damnever/pigar/actions) [![](https://img.shields.io/pypi/v/pigar.svg?style=flat-square)](https://pypi.org/project/pigar)


- Generating requirements.txt for Python project.
   - Handling the difference between different Python versions.
   - Jupyter nodebook (`*.ipynb`) support.
   - Including the import statements from ``exec``/``eval``, doctest of docstring, etc.
- Searching packages by import name.
- Checking the latest versions for Python project.

**NOTE**: [Pipenv](https://packaging.python.org/tutorials/managing-dependencies/#managing-dependencies) or other tools is recommended for improving your development flow.

![](https://raw.githubusercontent.com/damnever/pigar/master/guide.gif)


### Installation

`pigar` can run on Python 2.7.+ and 3.2+.

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
pip install git+https://github.com/damnever/pigar.git@[master or other branch] --upgrade
```


### Usage

- `pigar` can consider all kinds of complicated situations. For example, this project has [py2_requirements.txt](./py2_requirements.txt) and [py3_requirements.txt](./py3_requirements.txt) for different Python versions(see the above GIF).

    ```
    # Generate requirements.txt for current directory.
    $ pigar

    # Generating requirements.txt for given directory in given file.
    $ pigar -p ../dev-requirements.txt -P ../
    ```

    `pigar` can list all files which referenced the package(the line numbers for Jupyter nodebook may be a bit confusing), for example:
    ```
    # project/foo.py: 2,3
    # project/bar/baz.py: 2,7,8,9
    foobar == 3.3.3
    ```

    If the requirements.txt is overwritten, ``pigar`` will show the difference between the old and the new.

- If you do not know the import name that belongs to a specific package (more generally, does `Import Error: xxx` drive you crazy?), such as `bs4` which may come from `beautifulsoup4` or `MySQLdb` which could come from `MySQL_Python`, try searching for it:

    ```
    $ pigar -s bs4 MySQLdb
    ```

- Checking for the latest version:

    ```
    # Specify a requirements file.
    $ pigar -c ./requirements.txt

    # Or, you can let pigar searching all *requirements.txt in the current directory
    # level by itself. If not found, pigar will generate a new requirements.txt
    # for the current project, then check for the latest versions.
    $ pigar -c
    ```

- More:

   ```
   pigar --help
   ```


### FAQ

<details>
  <summary>
  (1) Why `pigar` generates multiple packages for same import name?

  (2) Why `pigar` generates different packages for same import name in different environment?
  </summary>

`pigar` can not handle it gracefully, you may need to remove the duplicate packages in requirements.txt manually.
Install the required package(remove others) in local environment should fix it as well.

Related issues: [#32](https://github.com/damnever/pigar/issues/32), [#68](https://github.com/damnever/pigar/issues/68).
</details>


### More

`pigar` does not use regular expressions in such a violent way. Instead, it uses AST, which is a better method for extracting imported names from arguments of `exec`/`eval`, doctest of docstring, etc.

Also, `pigar` can detect the difference between different Python versions. For example, you can find `concurrent.futures` from the Python 3.2 standard library, but you will need install `futures` in earlier versions of Python to get `concurrent.futures`, this is not a hardcode.

If you have any issues or suggestions, [please submit an issue on GitHub](https://github.com/damnever/pigar/issues). [**All contributions are appreciated!**](https://github.com/damnever/pigar/graphs/contributors)


### LICENSE

[The BSD 3-Clause License](https://github.com/damnever/pigar/blob/master/LICENSE)
