"""Refresh materialized analytics tables: analytics_user, analytics_country.

Run: python scripts/refresh_analytics.py
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.database import get_db


def main():
    conn = get_db()
    cur = conn.cursor()
    try:
        # helper to check tables
        def table_exists(name):
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s", (name,))
            return cur.fetchone()[0] > 0

        # Create analytics_user table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS analytics_user (
                user_id VARCHAR(50) PRIMARY KEY,
                user_name VARCHAR(255),
                total_searches INT DEFAULT 0,
                total_watches INT DEFAULT 0,
                avg_rating DECIMAL(5,2) DEFAULT 0,
                top_movie VARCHAR(255)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        conn.commit()

        # Populate analytics_user by aggregating source tables (skip unavailable tables)
        cur.execute('TRUNCATE TABLE analytics_user')
        # Build dynamic insert selecting only available sources
        select_parts = ["u.user_id, COALESCE(u.first_name, u.email) AS user_name"]
        joins = []

        # search_logs
        if table_exists('search_logs'):
            joins.append("LEFT JOIN (SELECT user_id, COUNT(*) AS total_searches FROM search_logs GROUP BY user_id) s ON s.user_id = u.user_id")
            select_parts.append("COALESCE(s.total_searches, 0) AS total_searches")
        else:
            select_parts.append("0 AS total_searches")

        # watch_history
        if table_exists('watch_history'):
            joins.append("LEFT JOIN (SELECT user_id, COUNT(*) AS total_watches FROM watch_history GROUP BY user_id) w ON w.user_id = u.user_id")
            select_parts.append("COALESCE(w.total_watches, 0) AS total_watches")
        else:
            select_parts.append("0 AS total_watches")

        # reviews
        if table_exists('reviews'):
            joins.append("LEFT JOIN (SELECT user_id, AVG(rating) AS avg_rating FROM reviews GROUP BY user_id) r ON r.user_id = u.user_id")
            select_parts.append("COALESCE(r.avg_rating, 0) AS avg_rating")
        else:
            select_parts.append("0 AS avg_rating")

        # top movie if watch_history and movies exist
        if table_exists('watch_history') and table_exists('movies'):
            joins.append("LEFT JOIN (SELECT wh.user_id, (SELECT m2.title FROM movies m2 WHERE m2.movie_id = (SELECT wh2.movie_id FROM watch_history wh2 WHERE wh2.user_id = wh.user_id GROUP BY wh2.movie_id ORDER BY COUNT(*) DESC LIMIT 1) LIMIT 1) AS top_movie FROM watch_history wh GROUP BY wh.user_id) mfav ON mfav.user_id = u.user_id")
            select_parts.append("COALESCE(mfav.top_movie, '') AS top_movie")
        else:
            select_parts.append("'' AS top_movie")

        insert_sql = f"INSERT INTO analytics_user (user_id, user_name, total_searches, total_watches, avg_rating, top_movie) SELECT {', '.join(select_parts)} FROM users u {' '.join(joins)} LIMIT 100000"
        cur.execute(insert_sql)
        conn.commit()

        # Create analytics_country table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS analytics_country (
                country VARCHAR(128) PRIMARY KEY,
                total_searches INT DEFAULT 0,
                total_watch_events INT DEFAULT 0,
                avg_rating DECIMAL(5,2) DEFAULT 0,
                top_movie VARCHAR(255)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        conn.commit()

        cur.execute('TRUNCATE TABLE analytics_country')
        # Build country insert dynamically depending on available tables
        parts = ["c.country"]
        joins = []
        # determine countries from available tables
        country_sources = []
        if table_exists('search_logs'):
            country_sources.append('SELECT location_country FROM search_logs')
        if table_exists('watch_history'):
            country_sources.append('SELECT location_country FROM watch_history')
        if table_exists('reviews'):
            country_sources.append('SELECT location_country FROM reviews')

        if not country_sources:
            # nothing to populate
            print('No source tables for country analytics found; skipping analytics_country population.')
        else:
            parts.append("COALESCE(s.total_searches,0) AS total_searches") if table_exists('search_logs') else parts.append("0 AS total_searches")
            parts.append("COALESCE(w.total_watch_events,0) AS total_watch_events") if table_exists('watch_history') else parts.append("0 AS total_watch_events")
            parts.append("COALESCE(r.avg_rating,0) AS avg_rating") if table_exists('reviews') else parts.append("0 AS avg_rating")
            # include top_movie only if we can compute it
            if table_exists('watch_history') and table_exists('movies'):
                parts.append("COALESCE(tm.top_movie,'') AS top_movie")
            else:
                parts.append("'' AS top_movie")

            country_union = ' UNION ALL '.join(country_sources)
            insert_sql = f"INSERT INTO analytics_country (country, total_searches, total_watch_events, avg_rating, top_movie) SELECT c.country, {', '.join(parts[1:])} FROM (SELECT DISTINCT COALESCE(location_country,'Unknown') AS country FROM ({country_union}) x) c"

            if table_exists('search_logs'):
                insert_sql += " LEFT JOIN (SELECT COALESCE(location_country,'Unknown') AS country, COUNT(*) AS total_searches FROM search_logs GROUP BY country) s ON s.country = c.country"
            if table_exists('watch_history'):
                insert_sql += " LEFT JOIN (SELECT COALESCE(location_country,'Unknown') AS country, COUNT(*) AS total_watch_events FROM watch_history GROUP BY country) w ON w.country = c.country"
            if table_exists('reviews'):
                insert_sql += " LEFT JOIN (SELECT COALESCE(location_country,'Unknown') AS country, AVG(rating) AS avg_rating FROM reviews GROUP BY country) r ON r.country = c.country"

            # top movie per country only possible if watch_history and movies exist
            if table_exists('watch_history') and table_exists('movies'):
                insert_sql += " LEFT JOIN (SELECT t.country, mv.title AS top_movie FROM (SELECT COALESCE(location_country,'Unknown') AS country, movie_id, COUNT(*) AS cnt FROM watch_history GROUP BY country, movie_id) t JOIN (SELECT country, MAX(cnt) AS maxcnt FROM (SELECT COALESCE(location_country,'Unknown') AS country, movie_id, COUNT(*) AS cnt FROM watch_history GROUP BY country, movie_id) u GROUP BY country) m ON t.country = m.country AND t.cnt = m.maxcnt LEFT JOIN movies mv ON mv.movie_id = t.movie_id) tm ON tm.country = c.country"

            insert_sql += " LIMIT 1000"
            cur.execute(insert_sql)
            conn.commit()

        print('Analytics refreshed: analytics_user and analytics_country updated.')
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

if __name__ == '__main__':
    main()
