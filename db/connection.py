import sqlite3
import os
import threading
from contextlib import contextmanager
from config import DB_URL, DATA_DIR

_local = threading.local()


def _get_sqlite_path():
    url = DB_URL
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "")
    return str(DATA_DIR / "stock_screener.db")


def init_connection():
    db_path = _get_sqlite_path()
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_connection():
    conn = getattr(_local, "connection", None)
    if conn is None:
        conn = init_connection()
        _local.connection = conn
    return conn


@contextmanager
def get_cursor():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        schema = f.read()
    conn = get_connection()
    conn.executescript(schema)
    conn.commit()
