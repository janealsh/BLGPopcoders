import os
import sys
import sqlite3
import pytest

# ensure project root is on sys.path so `import app.server` works
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class CursorWrapper:
    def __init__(self, cur, dictionary=False):
        self.cur = cur
        self.dictionary = dictionary

    def execute(self, sql, params=None):
        # convert MySQL-style %s placeholders to sqlite ? placeholders
        if params is None:
            return self.cur.execute(sql)
        sql_conv = sql.replace('%s', '?')
        return self.cur.execute(sql_conv, params)

    def fetchall(self):
        rows = self.cur.fetchall()
        if self.dictionary:
            return [dict(row) for row in rows]
        return rows

    def fetchone(self):
        row = self.cur.fetchone()
        if self.dictionary and row is not None:
            return dict(row)
        return row

    def close(self):
        try:
            self.cur.close()
        except Exception:
            pass


class SQLiteDB:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def cursor(self, dictionary=False):
        cur = self.conn.cursor()
        return CursorWrapper(cur, dictionary=dictionary)

    def commit(self):
        return self.conn.commit()

    def close(self):
        # Do not close the shared in-memory connection when views call conn.close()
        # Tests will let the process exit clean up resources.
        return


def setup_db():
    db = SQLiteDB()
    cur = db.cursor()
    cur.execute("""
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            email TEXT,
            first_name TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE search_logs (
            search_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            search_query TEXT,
            search_date TEXT,
            clicked_result_position INTEGER,
            location_country TEXT
        )
    """)
    cur.execute("INSERT INTO users (user_id, email, first_name) VALUES (1, 'a@example.com', 'Alice')")
    cur.execute("INSERT INTO search_logs (user_id, search_query, search_date, clicked_result_position, location_country) VALUES (1, 'hello', '2025-12-20', 1, 'USA')")
    db.commit()
    return db


def create_app_with_db(monkeypatch):
    import app.server as server
    import app.database as database
    import app.views as views_module

    db = setup_db()
    # monkeypatch the real get_db() used by views (database.get_db)
    monkeypatch.setattr(database, 'get_db', lambda: db)
    # views imported get_db at module import time; patch there too so handlers use the test DB
    monkeypatch.setattr(views_module, 'get_db', lambda: db)

    app = server.create_app()
    return app, db


def test_list_and_add(monkeypatch):
    app, db = create_app_with_db(monkeypatch)
    client = app.test_client()

    rv = client.get('/search-logs')
    assert rv.status_code == 200
    assert b'hello' in rv.data

    # add new log
    rv = client.post('/search-logs/add', data={
        'user_id': '1',
        'search_query': 'world',
        'location_country': 'USA',
        'clicked_result_position': ''
    }, follow_redirects=True)
    assert rv.status_code == 200
    assert b'world' in rv.data


def test_edit_update_delete(monkeypatch):
    app, db = create_app_with_db(monkeypatch)
    client = app.test_client()

    # create a row to edit
    client.post('/search-logs/add', data={'user_id': '1', 'search_query': 'to-edit', 'location_country': 'USA'}, follow_redirects=True)

    cur = db.cursor()
    cur.execute("SELECT search_id FROM search_logs WHERE search_query = ?", ('to-edit',))
    row = cur.fetchone()
    assert row is not None
    search_id = row[0]
 
    rv = client.get(f'/search-logs/edit/{search_id}')
    assert rv.status_code == 200
    assert b'to-edit' in rv.data

    # update
    rv = client.post('/search-logs/update', data={
        'search_id': str(search_id),
        'user_id': '1',
        'search_query': 'edited',
        'location_country': 'CA',
        'clicked_result_position': ''
    }, follow_redirects=True)
    assert rv.status_code == 200
    assert b'edited' in rv.data

    # delete
    rv = client.post(f'/search-logs/delete/{search_id}', follow_redirects=True)
    assert rv.status_code == 200
    assert b'edited' not in rv.data

