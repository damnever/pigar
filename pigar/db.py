import os
import sqlite3
import contextlib
from string import ascii_lowercase

from .helpers import Dict


class Database(object):
    _DB = os.path.join(os.path.dirname(__file__), '.db.sqlite3')

    def __init__(self, path=_DB):
        exist = os.path.isfile(path)
        self._db = path
        self._conn = None
        self._reconnect()
        if not exist:
            self._create_tables()

    def _reconnect(self):
        self.close()
        self._conn = sqlite3.connect(
            self._db, timeout=5
        )  # Timeout to avoid lock exception..
        self._conn.row_factory = sqlite3.Row

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def store_distribution_with_top_level_modules(
        self, distribution, version, top_levels
    ):
        cursor = self._conn.cursor()
        conn = self._conn
        distributions_table = self._table_distributions()
        sql_insert_distribution = f'INSERT OR REPLACE INTO {distributions_table} (name, version) VALUES (?, ?)'
        sql_select_distribution_id = f'SELECT id FROM {distributions_table} WHERE name = ?'
        sqltpl = '''INSERT OR IGNORE INTO {0} (name, distribution_id) VALUES
        (?, ?)'''
        try:
            cursor.execute(sql_insert_distribution, (distribution, version))
            conn.commit()
            if not top_levels:
                return
            res = cursor.execute(sql_select_distribution_id, (distribution, ))
            distribution_id = res.fetchone()
            for module_name in top_levels:
                sql = sqltpl.format(
                    self._table_top_level_import_names(module_name)
                )
                cursor.execute(sql, (module_name, distribution_id[0]))
            conn.commit()
        except sqlite3.OperationalError:
            try:
                conn.rollback()
            except Exception:
                pass
            self._reconnect()
            raise
        finally:
            cursor.close()

    def query_distributions_by_top_level_module(self, name):
        top_levels_table = self._table_top_level_import_names(name)
        distributions_table = self._table_distributions()
        sql = f'''SELECT name, version FROM {distributions_table} WHERE id IN
        (SELECT distribution_id FROM {top_levels_table} WHERE name=?)'''
        return self._query(sql, name)

    def query_distribution_by_name(self, name):
        distributions_table = self._table_distributions()
        sql = f'SELECT name, version FROM {distributions_table} WHERE name=?'
        rows = self._query(sql, name)
        return rows[0] if rows else None

    def query_distributions(self):
        distributions_table = self._table_distributions()
        sql = f'SELECT name, version FROM {distributions_table}'
        return self._query(sql)

    def _query(self, sql, *parameters):
        cursor = self._conn.cursor()
        try:
            res = cursor.execute(sql, parameters)
            rows = res.fetchall()
            return [Dict(r) for r in rows] if rows else None
        except sqlite3.OperationalError:
            self._reconnect()
            raise
        finally:
            cursor.close()

    def _table_top_level_import_names(self, import_name):
        first_char = import_name[0].lower()
        if first_char not in ascii_lowercase:
            first_char = "blackhole"
        return f"top_level_import_names_partition_{first_char}"

    def _table_distributions(self):
        return "distributions"

    def _create_tables(self):
        cursor = self._conn.cursor()
        conn = self._conn
        try:
            distributions_table = self._table_distributions()
            cursor.execute(
                f'''CREATE TABLE IF NOT EXISTS {distributions_table} (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL,
                version VARCHAR DEFAULT ''
            );'''
            )
            cursor.execute(
                f'''CREATE UNIQUE INDEX `_uidx_name_` ON `{distributions_table}` (`name`);'''
            )

            tli_table_sql = '''CREATE TABLE IF NOT EXISTS {0} (
                id INTEGER PRIMARY KEY,
                distribution_id INTEGER NOT NULL,
                name VARCHAR NOT NULL
            );'''
            tli_index_sql = '''
            CREATE UNIQUE INDEX `_uidx_{0}_distribution_id_name_` ON `{0}` (`distribution_id`, `name`);
            '''
            for x in (list(ascii_lowercase) + ["__other"]):
                table_name = self._table_top_level_import_names(x)
                cursor.execute(tli_table_sql.format(table_name))
                cursor.execute(tli_index_sql.format(table_name))
            conn.commit()
        except sqlite3.OperationalError:
            try:
                conn.rollback()
            except Exception:
                pass
            self._reconnect()
            raise
        finally:
            cursor.close()


@contextlib.contextmanager
def database():
    """A Database shortcut can auto close."""
    db = Database()
    yield db
    db.close()
