import os
import sqlite3
import contextlib

from .helpers import Dict

_DB_INIT_SCRIPT = '''BEGIN;

CREATE TABLE IF NOT EXISTS {distributions} (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    version VARCHAR DEFAULT ''
);
CREATE UNIQUE INDEX `_uidx_{distributions}_name_` ON `{distributions}` (`name`);

CREATE TABLE IF NOT EXISTS {top_level_module_names} (
    id INTEGER PRIMARY KEY,
    distribution_id INTEGER NOT NULL,
    name VARCHAR NOT NULL
);
CREATE UNIQUE INDEX `_uidx_{top_level_module_names}_distribution_id_name_` ON `{top_level_module_names}` (`distribution_id`, `name`);

COMMIT;
'''


class Database(object):
    _DB_PATH = os.path.join(os.path.dirname(__file__), '.db.sqlite3')
    _TABLE_DISTRIBUTIONS = 'distributions'
    _TABLE_TOP_LEVEL_MODULE_NAMES = 'top_level_module_names'

    def __init__(self, path=_DB_PATH):
        exist = os.path.isfile(path)
        self._db = path
        self._conn = None
        self._reconnect()
        if not exist:
            self._init()

    def _init(self):
        script = _DB_INIT_SCRIPT.format(
            distributions=self._TABLE_DISTRIBUTIONS,
            top_level_module_names=self._TABLE_TOP_LEVEL_MODULE_NAMES,
        )

        cursor = self._conn.cursor()
        try:
            cursor.executescript(script)
        finally:
            cursor.close()

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
        self,
        distribution,
        version,
        modules_to_add,
        modules_to_delete=None,
    ):
        cursor = self._conn.cursor()
        # conn = self._conn
        distributions_table = self._TABLE_DISTRIBUTIONS
        top_level_modules_table = self._TABLE_TOP_LEVEL_MODULE_NAMES
        sql_insert_distribution = f'INSERT OR REPLACE INTO {distributions_table} (name, version) VALUES(?, ?)'
        sql_select_distribution_id = f'SELECT id FROM {distributions_table} WHERE name = ?'
        sql_insert_top_level_modules = f'INSERT OR IGNORE INTO {top_level_modules_table} (distribution_id, name) VALUES(?, ?)'
        sql_delete_top_level_modules = f'DELETE FROM {top_level_modules_table} WHERE distribution_id=? and name=?'
        try:
            cursor.execute('BEGIN')
            cursor.execute(sql_insert_distribution, (distribution, version))
            if modules_to_add or modules_to_delete:
                res = cursor.execute(
                    sql_select_distribution_id, (distribution, )
                )
                distribution_id = res.fetchone()[0]
                for module_name in modules_to_add:
                    cursor.execute(
                        sql_insert_top_level_modules,
                        (distribution_id, module_name)
                    )
                if modules_to_delete:
                    for module_name in modules_to_delete:
                        cursor.execute(
                            sql_delete_top_level_modules,
                            (distribution_id, module_name)
                        )
            cursor.execute('COMMIT')
            # conn.commit()
        except sqlite3.OperationalError:
            try:
                # conn.rollback()
                cursor.execute('ROLLBACK')
            except Exception:
                pass
            self._reconnect()
            raise
        finally:
            cursor.close()

    def query_distributions_by_top_level_module(self, module_name):
        distributions_table = self._TABLE_DISTRIBUTIONS
        top_level_modules_table = self._TABLE_TOP_LEVEL_MODULE_NAMES
        sql = f'''SELECT name, version FROM {distributions_table} WHERE id IN
        (SELECT distribution_id FROM {top_level_modules_table} WHERE name=?)'''
        return self._query(sql, module_name)

    def query_distribution_with_top_level_modules(self, dist_name):
        distributions_table = self._TABLE_DISTRIBUTIONS
        top_level_modules_table = self._TABLE_TOP_LEVEL_MODULE_NAMES

        sql_query_dist = f'SELECT id, name, version FROM {distributions_table} WHERE name=?'
        dists = self._query(sql_query_dist, dist_name)
        dist = dists[0] if dists else None
        if dist is None:
            return None

        sql_query_modules = f'SELECT name FROM {top_level_modules_table} WHERE distribution_id=?'
        modules = self._query(sql_query_modules, dist.id) or []
        dist['modules'] = [m.name for m in modules]
        return dist

    def query_distribution_by_name(self, dist_name):
        distributions_table = self._TABLE_DISTRIBUTIONS
        sql = f'SELECT name, version FROM {distributions_table} WHERE name=?'
        rows = self._query(sql, dist_name)
        return rows[0] if rows else None

    def query_distributions(self):
        distributions_table = self._TABLE_DISTRIBUTIONS
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


@contextlib.contextmanager
def database():
    """A Database shortcut can auto close."""
    db = Database()
    yield db
    db.close()
