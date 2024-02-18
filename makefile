clean: clean-pyc
test: run-tests

clean-pyc:
	find . -type f -name '*.pyc' -exec rm -f {} +
	find . -type f -name '*.pyo' -exec rm -f {} +
	find . -type f -name '*.~' -exec rm -f {} +
	find . -type d -name '__pycache__' -exec rm -rf {} +

run-tests:
	python -m unittest discover pigar/tests/ -t . -v


generate-requirements:
	pigar gen --exclude-glob '**/tests/data/*' --exclude-glob '**/_vendor/pip/*' --with-referenced-comments -f ./requirements/py$(shell python -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')").txt pigar


sqlite3-vacuum:
	sqlite3 pigar/.db.sqlite3 'VACUUM;'
