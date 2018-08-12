# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import os
import sqlite3
import contextlib
try:  # py2
    from string import lowercase
except ImportError:  # py3
    from string import ascii_lowercase as lowercase

from .utils import Dict


# TODO(damnever): insert into db by default.
# (import_name, package_name)
_F_PACKAGES = {
    'yaml': 'PyYAML',
}


class Database(object):
    """Database store (top_level_name, package_name) piars.

    `top_level_name` is name can be imported from package,
    use `name` replace in db.
    `package_name` is name which be installed by pip, use
    `package` replace in db.

    Split table by `top_level_name` first letter, such as
    'table_a', `package_name` stored in `table_packages`.
    """
    _DB = os.path.join(os.path.dirname(__file__), '.db.sqlite3')
    _TABLE_PREFIX = 'table_{0}'
    _TABLE_OTHER_SUFFIX = 'lambda'
    _TABLE_PACKAGES = 'table_packages'

    def __init__(self, db=_DB):
        exist = os.path.isfile(db)
        self._conn = sqlite3.connect(db, timeout=30)  # Avoid lock exception..
        if not exist:
            self._create_tables()

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def insert_package_with_imports(self, pkgname, inames):
        package_table = self._package_table()
        sql = 'INSERT OR IGNORE INTO {0} (package) VALUES (?)'.format(
            package_table)
        sqls = [(sql, (pkgname,))]
        sqltpl = '''INSERT OR IGNORE INTO {0} (name, pkgid) VALUES
        (?, (SELECT id from {1} WHERE package=?))'''
        for iname in inames:
            iname = iname or pkgname  # empty top_level.txt
            sql = sqltpl.format(self._name_table(iname[0]), package_table)
            sqls.append((sql, (iname, pkgname)))
        self.insert(sqls)

    def query_all(self, name):
        name_table = self._name_table(name[0])
        package_table = self._package_table()
        sql = '''SELECT {0}.name , {1}.package
        FROM {0} INNER JOIN {1} ON {0}.pkgid == {1}.id
        WHERE name=?'''.format(name_table, package_table)
        return self.query(sql, name)

    def query_package(self, package):
        package_table = self._package_table()
        if package:
            sql = 'SELECT * FROM {0} WHERE package=?'.format(package_table)
            rows = self.query(sql, package)
        else:
            sql = 'SELECT package FROM {0}'.format(package_table)
            rows = self.query(sql)
        if package:
            return rows[0] if rows else None
        else:
            return [r.package for r in rows]

    def insert(self, sqls):
        cursor = self._conn.cursor()
        conn = self._conn
        try:
            for (sql, params) in sqls:
                cursor.execute(sql, params)
        except sqlite3.OperationalError:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            cursor.close()

    def query(self, sql, *parameters):
        cursor = self._conn.cursor()
        try:
            self._execute(cursor, sql, *parameters)
            names = [d[0] for d in cursor.description]
            return [Dict(zip(names, row)) for row in cursor]
        finally:
            cursor.close()

    def _execute(self, cursor, sql, *parameters):
        conn = self._conn
        try:
            result = cursor.execute(sql, parameters)
        except sqlite3.OperationalError:
            conn.rollback()
            raise
        else:
            conn.commit()
            return result

    def _name_table(self, initial, prefix=_TABLE_PREFIX,
                    other=_TABLE_OTHER_SUFFIX):
        initial = initial.lower()
        if initial not in lowercase:
            initial = other
        return prefix.format(initial)

    def _package_table(self, pkg_table=_TABLE_PACKAGES):
        return pkg_table

    def _create_tables(self, other=_TABLE_OTHER_SUFFIX):
        cursor = self._conn.cursor()
        try:
            # Create table `table_packages`.
            sql = '''CREATE TABLE IF NOT EXISTS {0} (
                id INTEGER PRIMARY KEY,  -- id will auto increment
                package VARCHAR NOT NULL UNIQUE
            )'''.format(self._package_table())
            self._execute(cursor, sql)

            # Create `table_[a-z]`.
            sql = '''CREATE TABLE IF NOT EXISTS {0} (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL,
                pkgid INTEGER NOT NULL
                -- FOREIGN KEY(pkgid) REFERENCES packages(id)
            )'''
            for initial in (list(lowercase) + [other]):
                table = self._name_table(initial)
                self._execute(cursor, sql.format(table))
        finally:
            cursor.close()


@contextlib.contextmanager
def database():
    """A Database shortcut can auto close."""
    db = Database()
    yield db
    db.close()
