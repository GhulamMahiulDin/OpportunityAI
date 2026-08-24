"""
PostgreSQL connection layer for OpportunityAI.

The rest of the codebase (models/, routes/, services/) was written against
sqlite3's convenience API: `db.execute(query, params).fetchone()`, with
`?` placeholders, `cursor.lastrowid` after inserts, `INSERT OR IGNORE`,
and a settable `db.row_factory`. Rather than rewriting every query across
~15 files, this module wraps a psycopg2 connection so it presents that
same sqlite3-style API -- the query text is translated at the point of
execution, so nothing above this layer had to change.

Translations performed automatically on every db.execute() call:
  - `?` placeholders                -> `%s` (psycopg2 style)
  - `INSERT OR IGNORE INTO ...`      -> `INSERT INTO ...  ON CONFLICT DO NOTHING`
  - INSERTs without RETURNING        -> `... RETURNING id`, exposed as
                                         cursor.lastrowid (every table's
                                         primary key in this schema is
                                         literally named `id`)
  - `db.row_factory = sqlite3.Row`   -> accepted but unused (DictCursor rows
                                         already support BOTH `row[0]`
                                         positional access AND `row['x']`
                                         named access, exactly like
                                         sqlite3.Row did, so no call sites
                                         needed to change)
"""
import re
import psycopg2
import psycopg2.extras
from flask import g, current_app

_INSERT_RE = re.compile(r'^\s*INSERT\s+INTO', re.IGNORECASE)
_OR_IGNORE_RE = re.compile(r'INSERT\s+OR\s+IGNORE\s+INTO', re.IGNORECASE)


class PGCursorWrapper:
    """
    Wraps a psycopg2 cursor to add a sqlite3-style `.lastrowid` attribute.
    Everything else (fetchone, fetchall, iteration, rowcount, ...) passes
    straight through to the real cursor.
    """
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PGConnectionWrapper:
    """
    Wraps a psycopg2 connection to present the same surface the rest of
    the app already calls: `.execute()`, `.executescript()`, `.commit()`,
    `.rollback()`, `.close()`, and a settable-but-unused `.row_factory`.
    """
    def __init__(self, conn):
        self._conn = conn
        self.row_factory = None  # kept for API compatibility with sqlite3; unused

    def execute(self, query, params=None):
        q = query

        # SQLite's "INSERT OR IGNORE" -> Postgres "INSERT ... ON CONFLICT DO NOTHING"
        # (no explicit conflict target needed: DO NOTHING with no target
        # applies to whatever unique/exclusion constraint would fire)
        or_ignore = bool(_OR_IGNORE_RE.search(q))
        if or_ignore:
            q = _OR_IGNORE_RE.sub('INSERT INTO', q, count=1)

        # SQLite `?` placeholders -> psycopg2 `%s`
        q = q.replace('?', '%s')

        is_insert = bool(_INSERT_RE.match(q))
        wants_lastrowid = is_insert and 'returning' not in q.lower()

        q = q.rstrip().rstrip(';')
        if or_ignore and 'on conflict' not in q.lower():
            q += ' ON CONFLICT DO NOTHING'
        if wants_lastrowid:
            q += ' RETURNING id'

        cur = self._conn.cursor()
        cur.execute(q, params or ())

        wrapped = PGCursorWrapper(cur)
        if wants_lastrowid:
            try:
                row = cur.fetchone()
                wrapped.lastrowid = row['id'] if row else None
            except (psycopg2.ProgrammingError, TypeError, KeyError):
                wrapped.lastrowid = None
        return wrapped

    def executescript(self, script):
        """Runs a multi-statement SQL script (used once, for schema.sql)."""
        cur = self._conn.cursor()
        cur.execute(script)
        self._conn.commit()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def cursor(self):
        return self._conn.cursor()


def get_db():
    if 'db' not in g:
        conn = psycopg2.connect(
            current_app.config['DATABASE_URL'],
            cursor_factory=psycopg2.extras.DictCursor
        )
        g.db = PGConnectionWrapper(conn)
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)
