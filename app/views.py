try:
    from flask import render_template, request, redirect, url_for, render_template_string, flash
except ImportError as e:
    raise RuntimeError("Missing dependency 'Flask'. Install with: python -m pip install Flask") from e

try:
    import mysql.connector
except ImportError as e:
    raise RuntimeError("Missing dependency 'mysql-connector-python'. Install with: python -m pip install mysql-connector-python") from e

from .database import get_db
from mysql.connector import errorcode
from datetime import date
import os

def home():
    return render_template("home.html")

def movies():
    return render_template("movies.html")


def add_review_form():
    # Render the reviews page which includes the add-review form
    return render_template("reviews.html")


def reviews():
    # Pagination and optional filtering by movie_id and/or user_id
    page_arg = request.args.get('page', '1')
    try:
        page = int(page_arg)
        if page < 1:
            page = 1
    except Exception:
        page = 1

    print("We're here!!")

    per_page = 20
    movie_id = request.args.get('movie_id') or None
    user_id = request.args.get('user_id') or None

    print(f"movie_id: {movie_id}, user_id: {user_id}")

    where_clauses = []
    params = []
    if movie_id:
        where_clauses.append("reviews.movie_id = %s")
        params.append(movie_id)
    if user_id:
        where_clauses.append("user_id = %s")
        params.append(user_id)

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    conn = get_db()
    cursor = conn.cursor()
    try:
        # total count for pagination
        count_sql = f"SELECT COUNT(*) FROM reviews{where_sql}"
        cursor.execute(count_sql, tuple(params))
        total = cursor.fetchone()[0] or 0
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1

        offset = (page - 1) * per_page
        sql = f"""
            SELECT reviews.review_id, reviews.user_id, reviews.movie_id, movies.title AS movie_title,
                reviews.rating, reviews.review_date, reviews.device_type, reviews.is_verified_watch, reviews.total_votes
            FROM reviews
            LEFT JOIN movies ON reviews.movie_id = movies.movie_id
            {where_sql}
            ORDER BY review_date DESC
            LIMIT %s OFFSET %s
        """
        exec_params = params + [per_page, offset]
        cursor.execute(sql, tuple(exec_params))
        reviews = cursor.fetchall()
        print(f"Fetched {len(reviews)} reviews for page {page}")
    except Exception as e:
        print(f"Error fetching reviews: {e}")
        reviews = []
        total_pages = 1
    finally:
        cursor.close()
        conn.close()

    return render_template("reviews.html", reviews=reviews, page=page, total_pages=total_pages, movie_id=movie_id, user_id=user_id)


def add_review():
    # required fields (review_id is AUTO_INCREMENT in DB)
    user_id = request.form.get('user_id')
    movie_id = request.form.get('movie_id')
    rating = request.form.get('rating')
    device_type = request.form.get('device_type') or None
    # accept either form field name used in templates
    is_verified_watch = request.form.get('is_verified_watch') if request.form.get('is_verified_watch') is not None else request.form.get('is_verified_watch') or 0
    total_votes = request.form.get('total_votes') or 0

    if not (user_id and movie_id and rating):
        return "Missing required fields", 400

    sql = """
    INSERT INTO reviews (user_id, movie_id, rating, review_date, device_type, is_verified_watch, total_votes)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    values = (user_id, movie_id, rating, date.today(), device_type, is_verified_watch, total_votes)

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
    except mysql.connector.Error as e:
        return f"Database error: {e}", 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    return render_template_string("""
    <h2>Review added successfully! ✅</h2>
    <a href="{{ url_for('home') }}">Back to Home 🏠</a>
    """)


def update_review():
    review_id = request.form.get('review_id')
    rating = request.form.get('rating')
    device_type = request.form.get('device_type')
    is_verified_watch = request.form.get('is_verified_watch') if request.form.get('is_verified_watch') is not None else request.form.get('is_verified_watch') or 0
    total_votes = request.form.get('total_votes') or 0
    movie_id = request.form.get('movie_id')

    if not review_id:
        return "Missing review_id", 400

    sql = """
    UPDATE reviews
    SET rating=%s, device_type=%s, is_verified_watch=%s, total_votes=%s
    WHERE review_id=%s
    """
    values = (rating, device_type, is_verified_watch, total_votes, review_id)
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
    except mysql.connector.Error as e:
        return f"Database error: {e}", 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    return redirect(f"/reviews?movie_id={movie_id}")


def delete_review():
    # prefer deletion by review_id, otherwise by user_id+movie_id
    review_id = request.form.get('review_id')
    if review_id:
        sql = "DELETE FROM reviews WHERE review_id=%s"
        values = (review_id,)
    else:
        user_id = request.form.get('user_id')
        movie_id = request.form.get('movie_id')
        if not (user_id and movie_id):
            return "Missing identifiers for deletion", 400
        sql = "DELETE FROM reviews WHERE user_id=%s AND movie_id=%s"
        values = (user_id, movie_id)

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
    except mysql.connector.Error as e:
        return f"Database error: {e}", 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    # redirect back to the movie reviews page if possible
    movie_id = request.form.get('movie_id') or ''
    return redirect(f"/reviews?movie_id={movie_id}")



def watch_history():
    # db = current_app.config["db"]
    # watch_history = db.watch_history()
    # return render_template("watch_history.html", watch_history = watch_history)

    conn = get_db()
    cursor = conn.cursor()
    try:
        query = """SELECT * FROM watch_history
            ORDER BY watch_date DESC
            LIMIT 100"""
        cursor.execute(query)
        watch_history_data = cursor.fetchall()
        watch_history_columns = [column[0] for column in cursor.description]

    except mysql.connector.Error as e:
        cursor.close()
        conn.close()
        return f"Database error: {e}. Please check your database and connection, then try again."

    cursor.close()
    conn.close()
    return render_template("watch_history.html", watch_history=watch_history_data, columns=watch_history_columns)



def recommend():
    return render_template("recommend.html")


def search_logs():
    # pagination
    page_arg = request.args.get('page', '1')
    try:
        page = int(page_arg)
        if page < 1:
            page = 1
    except Exception:
        page = 1

    per_page = 20
    offset = (page - 1) * per_page

    conn = get_db()
    # get total count from search_logs
    count_cursor = conn.cursor()
    total = 0
    try:
        count_cursor.execute("SELECT COUNT(*) FROM search_logs")
        total = count_cursor.fetchone()[0] or 0
        print(f"[search_logs] Total rows in search_logs: {total}")
    except Exception as e:
        print(f"[search_logs] Error counting rows: {e}")
    finally:
        try:
            count_cursor.close()
        except Exception:
            pass

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    cursor = conn.cursor(dictionary=True)
    # Join with users to show user names when available
    query = """
        SELECT s.*, u.first_name AS user_name, u.email AS user_email
        FROM search_logs s
        LEFT JOIN users u ON s.user_id = u.user_id
        ORDER BY s.search_date DESC, s.search_id DESC
        LIMIT %s OFFSET %s
    """
    logs = []
    try:
        cursor.execute(query, (per_page, offset))
        logs = cursor.fetchall()
        print(f"[search_logs] Fetched {len(logs)} rows for page {page}")
    except Exception as e:
        print(f"[search_logs] Error fetching logs: {e}")
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    return render_template("search_logs.html", logs=logs, page=page, total_pages=total_pages)


# Add record
def add_search_log():
    if request.method == "POST":
        # accept user_id OR user_name/user_email
        user_id_raw = request.form.get("user_id")
        user_name = request.form.get("user_name")
        user_email = request.form.get("user_email")
        search_query = request.form.get("search_query")
        location_country = request.form.get("location_country")
        clicked_pos_raw = request.form.get("clicked_result_position")

        # basic validation
        if not search_query:
            return "Missing search_query", 400

        # convert clicked_pos to int or None
        try:
            clicked_pos = int(clicked_pos_raw) if clicked_pos_raw not in (None, "") else None
        except ValueError:
            clicked_pos = None

        # determine user_id: prefer explicit id; otherwise lookup/create by email or name
        user_id = None
        if user_id_raw not in (None, ""):
            uid = user_id_raw.strip()
            if uid != "":
                conn_check = get_db()
                cur_check = conn_check.cursor()
                try:
                    cur_check.execute("SELECT 1 FROM users WHERE user_id = %s LIMIT 1", (uid,))
                    exists = cur_check.fetchone()
                    if exists:
                        user_id = uid
                finally:
                    try:
                        cur_check.close()
                    except Exception:
                        pass
                    try:
                        conn_check.close()
                    except Exception:
                        pass
        else:
            # try email first
            if user_email:
                conn_check = get_db()
                cur_check = conn_check.cursor()
                try:
                    cur_check.execute("SELECT user_id FROM users WHERE LOWER(TRIM(email)) = %s LIMIT 1", (user_email.lower().strip(),))
                    res = cur_check.fetchone()
                    if res:
                        user_id = res[0]
                    else:
                        # try to insert new user; handle schemas where user_id is required
                        insert_q = "INSERT INTO users (email, first_name) VALUES (%s, %s)"
                        try:
                            cur_check.execute(insert_q, (user_email, user_name or None))
                            user_id = cur_check.lastrowid
                            conn_check.commit()
                        except mysql.connector.Error as ie:
                            # If the users table requires user_id (no AUTO_INCREMENT), generate a string id and insert explicitly
                            if ie.errno in (errorcode.ER_NO_DEFAULT_FOR_FIELD, errorcode.ER_BAD_NULL_ERROR, 1364):
                                gen_id = f"u_{int(date.today().strftime('%Y%m%d'))}_{os.urandom(3).hex()}"
                                cur_check.execute("INSERT INTO users (user_id, email, first_name, is_active) VALUES (%s, %s, %s, %s)", (gen_id, user_email, user_name or None, 1))
                                user_id = gen_id
                                conn_check.commit()
                            else:
                                raise
                finally:
                    try:
                        cur_check.close()
                    except Exception:
                        pass
                    try:
                        conn_check.close()
                    except Exception:
                        pass
            elif user_name:
                conn_check = get_db()
                cur_check = conn_check.cursor()
                try:
                    cur_check.execute("SELECT user_id FROM users WHERE first_name = %s LIMIT 1", (user_name,))
                    res = cur_check.fetchone()
                    if res:
                        user_id = res[0]
                    else:
                        # Attempt to insert with a generated placeholder email (some schemas require non-NULL email)
                        gen_email = f"unknown_{int(date.today().strftime('%Y%m%d'))}_{os.urandom(3).hex()}@example.local"
                        insert_q = "INSERT INTO users (first_name, email) VALUES (%s, %s)"
                        try:
                            cur_check.execute(insert_q, (user_name, gen_email))
                            user_id = cur_check.lastrowid
                            conn_check.commit()
                        except mysql.connector.Error as ie:
                            # If the users table requires explicit user_id (no AUTO_INCREMENT), fall back to generating an id
                            if ie.errno in (errorcode.ER_NO_DEFAULT_FOR_FIELD, errorcode.ER_BAD_NULL_ERROR, 1364):
                                gen_id = f"u_{int(date.today().strftime('%Y%m%d'))}_{os.urandom(3).hex()}"
                                cur_check.execute("INSERT INTO users (user_id, first_name, email, is_active) VALUES (%s, %s, %s, %s)", (gen_id, user_name, gen_email, 1))
                                user_id = gen_id
                                conn_check.commit()
                            else:
                                raise
                finally:
                    try:
                        cur_check.close()
                    except Exception:
                        pass
                    try:
                        conn_check.close()
                    except Exception:
                        pass

        # we set the date automatically to today
        search_date = date.today()

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO search_logs (user_id, search_query, search_date, clicked_result_position, location_country)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, search_query, search_date, clicked_pos, location_country))
            conn.commit()
            flash('Search log added successfully.')
        except Exception as e:
            # close and show an informative message
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            return render_template_string(f"""
                <h2>Failed to add search log</h2>
                <pre>{e}</pre>
                <a href="{{{{ url_for('search_logs') }}}}">Back</a>
            """), 500
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        return redirect(url_for("search_logs"))

    
    return redirect(url_for("search_logs"))


# Delete record
def delete_search_log(search_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM search_logs WHERE search_id = %s", (search_id,))
    conn.commit()
    flash('Search log deleted.')
    cursor.close()
    conn.close()

    return redirect(url_for("search_logs"))


def edit_search_log(search_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM search_logs WHERE search_id = %s", (search_id,))
        row = cursor.fetchone()
    except mysql.connector.Error as e:
        row = None
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    if not row:
        return f"Search log {search_id} not found", 404

    return render_template("search_log_edit.html", row=row)


def update_search_log():
    if request.method != "POST":
        return redirect(url_for("search_logs"))

    search_id = request.form.get("search_id")
    user_id = request.form.get("user_id") or None
    search_query = request.form.get("search_query")
    location_country = request.form.get("location_country") or None
    clicked_pos = request.form.get("clicked_result_position") or None

    if not search_id or not search_query:
        return "Missing required fields", 400

    # normalize types
    try:
        search_id = int(search_id)
    except Exception:
        return "Invalid search_id", 400

    # accept either numeric or string user_id values (DB may use varchar ids)
    if user_id is not None and user_id != '':
        user_id = user_id.strip()
    else:
        user_id = None

    try:
        if clicked_pos is not None and clicked_pos != '':
            clicked_pos = int(clicked_pos)
        else:
            clicked_pos = None
    except Exception:
        clicked_pos = None

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE search_logs
            SET user_id=%s, search_query=%s, clicked_result_position=%s, location_country=%s
            WHERE search_id=%s
            """,
            (user_id, search_query, clicked_pos, location_country, search_id),
        )
        conn.commit()
    except mysql.connector.Error as e:
        return f"Database error: {e}", 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    return redirect(url_for("search_logs"))


def users_list():
    """List users with simple management UI."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id, first_name, email, is_active FROM users ORDER BY first_name IS NULL, first_name, user_id LIMIT 500")
        users = cursor.fetchall()
    except Exception as e:
        users = []
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    return render_template("users.html", users=users)


def add_user():
    # Accepts POST from users list page
    if request.method != "POST":
        return redirect(url_for("users_list"))

    user_id = request.form.get("user_id") or None
    first_name = request.form.get("first_name") or None
    email = request.form.get("email") or None
    is_active = 1 if request.form.get("is_active") in ("1", "on", "true", "True") else 0

    conn = get_db()
    cursor = conn.cursor()
    try:
        if user_id:
            # allow inserting explicit user_id (varchar PK scenarios)
            cursor.execute("INSERT INTO users (user_id, first_name, email, is_active) VALUES (%s, %s, %s, %s)", (user_id, first_name, email, is_active))
        else:
            cursor.execute("INSERT INTO users (first_name, email, is_active) VALUES (%s, %s, %s)", (first_name, email, is_active))
        conn.commit()
        flash("User added.")
    except Exception as e:
        conn.rollback()
        flash(f"Failed to add user: {e}")
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    return redirect(url_for("users_list"))


def edit_user(user_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id, first_name, email, is_active FROM users WHERE user_id = %s LIMIT 1", (user_id,))
        row = cursor.fetchone()
    except Exception:
        row = None
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    if not row:
        return f"User {user_id} not found", 404

    return render_template("user_edit.html", row=row)


def update_user():
    if request.method != "POST":
        return redirect(url_for("users_list"))

    user_id = request.form.get("user_id")
    first_name = request.form.get("first_name") or None
    email = request.form.get("email") or None
    is_active = 1 if request.form.get("is_active") in ("1", "on", "true", "True") else 0

    if not user_id:
        return "Missing user_id", 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET first_name=%s, email=%s, is_active=%s WHERE user_id=%s", (first_name, email, is_active, user_id))
        conn.commit()
        flash("User updated.")
    except Exception as e:
        conn.rollback()
        return f"Database error: {e}", 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    return redirect(url_for("users_list"))


def delete_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        flash("User deleted.")
    except Exception as e:
        conn.rollback()
        flash(f"Failed to delete user: {e}")
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    return redirect(url_for("users_list"))


def analytics():
    """Analytics endpoint demonstrating nested queries, GROUP BY, and multi-table joins.

    Returns per-user summary: total searches, total watches, avg rating, and top watched movie (via nested subquery).
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Check which tables exist so we can adapt queries (allow analytics to run partially)
    info_cur = conn.cursor()
    info_cur.execute("SELECT DATABASE()")
    db_name = info_cur.fetchone()[0]

    def table_exists(name):
        info_cur.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
            (db_name, name),
        )
        return info_cur.fetchone()[0] > 0

    has_users = table_exists('users')
    has_search = table_exists('search_logs')
    has_watch = table_exists('watch_history')
    has_reviews = table_exists('reviews')
    has_movies = table_exists('movies')
    info_cur.close()

    # Build main user summary SQL adaptively
    parts = []
    parts.append("SELECT u.user_id, COALESCE(u.first_name, u.email) AS user_name")
    if has_search:
        parts.append("COUNT(DISTINCT s.search_id) AS total_searches")
    else:
        parts.append("0 AS total_searches")

    if has_watch:
        parts.append("COALESCE(w.total_watches, 0) AS total_watches")
    else:
        parts.append("0 AS total_watches")

    if has_reviews:
        parts.append("COALESCE(r.avg_rating, 0) AS avg_rating")
    else:
        parts.append("0 AS avg_rating")

    if has_watch and has_movies:
        parts.append("COALESCE(mfav.top_movie, '') AS top_movie")
    else:
        parts.append("'' AS top_movie")

    select_clause = ",\n    ".join(parts)

    sql = f"""
        {select_clause}
        FROM users u
    """

    if has_search:
        sql += "\nLEFT JOIN search_logs s ON s.user_id = u.user_id"

    if has_watch:
        sql += "\nLEFT JOIN (SELECT user_id, COUNT(*) AS total_watches FROM watch_history GROUP BY user_id) w ON w.user_id = u.user_id"

    if has_reviews:
        sql += "\nLEFT JOIN (SELECT user_id, AVG(rating) AS avg_rating FROM reviews GROUP BY user_id) r ON r.user_id = u.user_id"

    if has_watch and has_movies:
        sql += "\nLEFT JOIN (\n            SELECT wh.user_id, (\n                SELECT m2.title FROM movies m2 WHERE m2.movie_id = (\n                    SELECT wh2.movie_id FROM watch_history wh2 WHERE wh2.user_id = wh.user_id GROUP BY wh2.movie_id ORDER BY COUNT(*) DESC LIMIT 1\n                ) LIMIT 1\n            ) AS top_movie FROM watch_history wh GROUP BY wh.user_id\n        ) mfav ON mfav.user_id = u.user_id"

    sql += "\nGROUP BY u.user_id\nORDER BY total_searches DESC, total_watches DESC\nLIMIT 200"

    try:
        cursor.execute(sql)
        rows = cursor.fetchall()

        # Country-level report: build per-country aggregates using derived tables
        # This avoids referencing non-grouped outer columns in correlated subqueries
        country_rows = []
        if has_search:
            # base select
            country_sql = "SELECT c.country, COALESCE(s.total_searches,0) AS total_searches"
            if has_watch:
                country_sql += ", COALESCE(w.total_watch_events,0) AS total_watch_events"
            else:
                country_sql += ", 0 AS total_watch_events"
            if has_reviews:
                country_sql += ", COALESCE(r.avg_rating,0) AS avg_rating"
            else:
                country_sql += ", 0 AS avg_rating"
            country_sql += ", COALESCE(tp.top_search_query, '') AS top_search_query\n"

            # derive list of countries from search_logs
            country_sql += "FROM (SELECT DISTINCT COALESCE(location_country,'Unknown') AS country FROM search_logs) c\n"

            # attach search aggregates
            country_sql += "LEFT JOIN (SELECT COALESCE(location_country,'Unknown') AS country, COUNT(*) AS total_searches FROM search_logs GROUP BY country) s ON s.country = c.country\n"

            # attach watch aggregates if available
            if has_watch:
                country_sql += "LEFT JOIN (SELECT COALESCE(location_country,'Unknown') AS country, COUNT(*) AS total_watch_events FROM watch_history GROUP BY country) w ON w.country = c.country\n"

            # attach review aggregates if available
            if has_reviews:
                country_sql += "LEFT JOIN (SELECT COALESCE(location_country,'Unknown') AS country, AVG(rating) AS avg_rating FROM reviews GROUP BY country) r ON r.country = c.country\n"

            # compute top search per country using ROW_NUMBER for deterministic tie-breaking
            # Requires MySQL 8+ (window functions). This selects the single top query per country
            # ordered by count desc, then search_query asc to break ties deterministically.
            country_sql += (
                "LEFT JOIN (\n"
                "  SELECT country, search_query AS top_search_query FROM (\n"
                "    SELECT country, search_query, ROW_NUMBER() OVER (PARTITION BY country ORDER BY cnt DESC, search_query ASC) AS rn FROM (\n"
                "      SELECT COALESCE(location_country,'Unknown') AS country, search_query, COUNT(*) AS cnt\n"
                "      FROM search_logs\n"
                "      GROUP BY country, search_query\n"
                "    ) x\n"
                "  ) t WHERE rn = 1\n"
                ") tp ON tp.country = c.country\n"
            )

            country_sql += "ORDER BY total_searches DESC, total_watch_events DESC\nLIMIT 200"

            try:
                cursor.execute(country_sql)
                country_rows = cursor.fetchall()
            except Exception as ce:
                # if something unexpected happens, return empty country rows but continue
                print(f"[analytics] country query error: {ce}")
                country_rows = []
        else:
            country_rows = []
    except Exception as e:
        # Handle missing-table errors with a helpful message
        try:
            import mysql.connector as _mysql
            is_mysql_err = isinstance(e, _mysql.Error)
        except Exception:
            is_mysql_err = False

        cursor.close()
        conn.close()

        if is_mysql_err and getattr(e, 'errno', None) == errorcode.ER_NO_SUCH_TABLE:
            # Extract table name from error message if possible
            import re
            m = re.search(r"Table '([^']+)'", str(e))
            table_name = m.group(1) if m else None
            msg = "Analytics can't run because a required table is missing."
            if table_name:
                msg += f" Missing table: {table_name}."
            msg += "\nRun the database initialization or import scripts to create tables/data."
            return render_template_string(f"""
                <h2>Analytics unavailable</h2>
                <p>{msg}</p>
                <p><a href="{{{{ url_for('home') }}}}">Back to Home</a></p>
            """), 500

        return f"Analytics query error: {e}", 500

    cursor.close()
    conn.close()

    return render_template("analytics.html", rows=rows, country_rows=country_rows)




