import sqlite3
import sys
import pathlib
import pytest

# Ensure project root is on sys.path so `app` package can be imported
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app import server
import app.views as views
from datetime import date


class SQLiteAdapterCursor:
    def __init__(self, cur, dictionary=False):
        self._cur = cur
        self._dictionary = dictionary

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    def execute(self, sql, params=None):
        # Translate MySQL-style %s placeholders into sqlite ? placeholders
        if params is None:
            params = ()
        low = sql.lower()
        # emulate information_schema.tables queries using sqlite_master
        if 'information_schema.tables' in low:
            # params expected: (db_name, table_name)
            table_name = params[1] if len(params) > 1 else params[0] if params else None
            return self._cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))

        sql_trans = sql.replace('%s', '?')
        return self._cur.execute(sql_trans, params)

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        if not self._dictionary:
            return row
        return {col[0]: row[idx] for idx, col in enumerate(self._cur.description)}

    def fetchall(self):
        rows = self._cur.fetchall()
        if not self._dictionary:
            return rows
        cols = [c[0] for c in self._cur.description]
        return [dict(zip(cols, r)) for r in rows]

    @property
    def description(self):
        return self._cur.description

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass


class SQLiteAdapterConnection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self, dictionary=False):
        return SQLiteAdapterCursor(self._conn.cursor(), dictionary=dictionary)

    def commit(self):
        self._conn.commit()

    def close(self):
        # no-op for compatibility with app code which may call conn.close()
        # underlying connection closed explicitly with `terminate()` at fixture teardown
        return

    def terminate(self):
        try:
            self._conn.close()
        except Exception:
            pass


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = None
    # provide a DATABASE() function to satisfy MySQL-style calls in analytics
    try:
        conn.create_function('DATABASE', 0, lambda: 'sqlite_db')
    except Exception:
        pass
    c = conn.cursor()
    # Create minimal schema compatible with views
    c.executescript('''
    CREATE TABLE users (user_id TEXT PRIMARY KEY, first_name TEXT, email TEXT, is_active INTEGER DEFAULT 1);
    CREATE TABLE movies (movie_id TEXT PRIMARY KEY, title TEXT);
    CREATE TABLE search_logs (
        search_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        search_query TEXT,
        search_date TEXT,
        clicked_result_position INTEGER,
        location_country TEXT
    );
    CREATE TABLE watch_history (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        movie_id TEXT,
        watch_date TEXT,
        location_country TEXT
    );
    CREATE TABLE reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        movie_id TEXT,
        rating REAL,
        location_country TEXT
    );
    ''')

    # Seed data
    c.executemany('INSERT INTO users (user_id, first_name, email, is_active) VALUES (?, ?, ?, ?)', [
        ('u_1', 'Alice', 'alice@example.com', 1),
        ('u_2', 'Bob', 'bob@example.com', 1),
    ])

    c.executemany('INSERT INTO search_logs (user_id, search_query, search_date, clicked_result_position, location_country) VALUES (?, ?, ?, ?, ?)', [
        ('u_1', 'sci-fi', str(date.today()), 1, 'USA'),
        ('u_1', 'sci-fi', str(date.today()), None, 'USA'),
        ('u_2', 'stand up comedy', str(date.today()), None, 'Canada'),
    ])

    c.executemany('INSERT INTO watch_history (user_id, movie_id, watch_date, location_country) VALUES (?, ?, ?, ?)', [
        ('u_1', 'm1', str(date.today()), 'USA'),
    ])

    c.executemany('INSERT INTO movies (movie_id, title) VALUES (?, ?)', [
        ('m1', 'Space Movie'),
    ])

    conn.commit()

    adapter = SQLiteAdapterConnection(conn)
    try:
        yield adapter
    finally:
        adapter.terminate()


@pytest.fixture
def client(monkeypatch, db_conn):
    # Patch get_db to return our sqlite adapter
    monkeypatch.setattr(views, 'get_db', lambda: db_conn)
    app = server.create_app()
    app.testing = True
    with app.test_client() as c:
        yield c


def test_add_and_list_search_log(client):
    # Add a search log using form (no user id, provide name/email)
    resp = client.post('/search-logs/add', data={'user_email': 'new@example.com', 'user_name': 'New', 'search_query': 'romcom', 'location_country': 'USA'}, follow_redirects=True)
    assert resp.status_code in (200, 302)

    # Now fetch search logs page
    resp = client.get('/search-logs')
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'romcom' in body
    assert 'New' in body or 'new@example.com' in body


def test_analytics_country_summary(client):
    resp = client.get('/analytics')
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # Should contain seeded countries and top search queries
    assert 'USA' in body
    assert 'Canada' in body
    assert 'sci-fi' in body or 'stand up comedy' in body
