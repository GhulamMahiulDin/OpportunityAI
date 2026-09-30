"""
PostgreSQL & SQLite dual connection layer for OpportunityAI.

Supports PostgreSQL as primary database (via psycopg2) with automatic
PostgreSQL schema initialization on first connection, and provides seamless
automatic fallback to SQLite (local file or /tmp in serverless/Vercel)
if PostgreSQL is unreachable or not configured.

Both backends expose the exact same API surface:
  - execute(query, params)
  - executescript(script)
  - commit()
  - rollback()
  - close()
  - rows accessible via both positional row[0] and named row['col']
  - cursor.lastrowid
"""
import os
import re
import sqlite3
from pathlib import Path
from flask import g, current_app

_INSERT_RE = re.compile(r'^\s*INSERT\s+INTO', re.IGNORECASE)
_OR_IGNORE_RE = re.compile(r'INSERT\s+OR\s+IGNORE\s+INTO', re.IGNORECASE)

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BASE_DIR / 'database' / 'schema.sql'


# ============================================================
# POSTGRESQL WRAPPERS
# ============================================================

class PGCursorWrapper:
    """
    Wraps a psycopg2 cursor to add a sqlite3-style `.lastrowid` attribute.
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
    Wraps a psycopg2 connection to present the standard interface.
    Translates ? -> %s and INSERT OR IGNORE -> ON CONFLICT DO NOTHING.
    """
    def __init__(self, conn):
        self._conn = conn
        self.row_factory = None
        self.is_pg = True

    def execute(self, query, params=None):
        q = query
        or_ignore = bool(_OR_IGNORE_RE.search(q))
        if or_ignore:
            q = _OR_IGNORE_RE.sub('INSERT INTO', q, count=1)

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
            except Exception:
                wrapped.lastrowid = None
        return wrapped

    def executescript(self, script):
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


# ============================================================
# SQLITE WRAPPERS
# ============================================================

class SQLiteCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = cursor.lastrowid

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class SQLiteConnectionWrapper:
    """
    Wraps a sqlite3 connection to present the standard interface.
    """
    def __init__(self, conn):
        self._conn = conn
        self.row_factory = sqlite3.Row
        self.is_pg = False

    def execute(self, query, params=None):
        q = query
        # Normalizes %s to ? if %s placeholders were used
        if '%s' in q and '?' not in q:
            q = q.replace('%s', '?')

        cur = self._conn.cursor()
        if params:
            cur.execute(q, params)
        else:
            cur.execute(q)
        return SQLiteCursorWrapper(cur)

    def executescript(self, script):
        self._conn.executescript(script)
        self._conn.commit()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def cursor(self):
        return self._conn.cursor()


# ============================================================
# SCHEMA INITIALIZATION
# ============================================================

def init_db_schema_if_needed(wrapper, is_pg=True):
    """
    Checks if the database has tables initialized. If not, automatically
    reads schema.sql and creates all tables and default seed data.
    """
    try:
        if is_pg:
            row = wrapper.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
            ).fetchone()
            tables_exist = bool(row[0]) if row else False
        else:
            row = wrapper.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
            ).fetchone()
            tables_exist = bool(row)
    except Exception:
        tables_exist = False

    if not tables_exist and SCHEMA_FILE.exists():
        try:
            schema_sql = SCHEMA_FILE.read_text(encoding='utf-8')
            if not is_pg:
                schema_sql = schema_sql.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
            wrapper.executescript(schema_sql)
            print(f"[{'PostgreSQL' if is_pg else 'SQLite'}] Database schema and seed data initialized successfully.")
        except Exception as e:
            print(f"Warning: Could not auto-initialize schema: {e}")


# ============================================================
# FLASK DATABASE GETTER & LIFECYCLE
# ============================================================

def get_db():
    """
    Returns the active database connection for the current Flask request.
    Tries PostgreSQL first; falls back seamlessly to SQLite if PostgreSQL
    is unreachable or not configured.
    """
    if 'db' not in g:
        db_url = current_app.config.get('DATABASE_URL', '')
        # Fix legacy postgres:// URL format if provided by some hosters
        if db_url and db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)

        pg_connected = False
        conn = None

        if db_url and 'localhost' not in db_url and '127.0.0.1' not in db_url:
            try:
                import psycopg2
                import psycopg2.extras
                conn = psycopg2.connect(
                    db_url,
                    connect_timeout=4,
                    cursor_factory=psycopg2.extras.DictCursor
                )
                wrapped = PGConnectionWrapper(conn)
                init_db_schema_if_needed(wrapped, is_pg=True)
                g.db = wrapped
                pg_connected = True
            except Exception as e:
                current_app.logger.warning(
                    f"PostgreSQL connection to DATABASE_URL failed ({e}). Falling back to SQLite."
                )

        if not pg_connected and db_url and ('localhost' in db_url or '127.0.0.1' in db_url):
            # Try local postgres if available, with quick timeout
            try:
                import psycopg2
                import psycopg2.extras
                conn = psycopg2.connect(
                    db_url,
                    connect_timeout=2,
                    cursor_factory=psycopg2.extras.DictCursor
                )
                wrapped = PGConnectionWrapper(conn)
                init_db_schema_if_needed(wrapped, is_pg=True)
                g.db = wrapped
                pg_connected = True
            except Exception:
                pass

        if not pg_connected:
            # Fallback to SQLite (in /tmp for Vercel/serverless environments, or local file)
            if os.path.exists('/tmp') and os.access('/tmp', os.W_OK):
                sqlite_path = '/tmp/opportunityai.db'
            else:
                sqlite_path = str(BASE_DIR / 'opportunityai.db')

            s_conn = sqlite3.connect(sqlite_path, timeout=20.0, check_same_thread=False)
            s_conn.row_factory = sqlite3.Row
            wrapped = SQLiteConnectionWrapper(s_conn)
            init_db_schema_if_needed(wrapped, is_pg=False)
            g.db = wrapped

    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass


def init_app(app):
    app.teardown_appcontext(close_db)
