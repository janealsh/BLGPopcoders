try:
    from flask import render_template, request, redirect, url_for, render_template_string, flash, jsonify
except ImportError as e:
    raise RuntimeError("Missing dependency 'Flask'. Install with: python -m pip install Flask") from e

try:
    import mysql.connector
except ImportError as e:
    raise RuntimeError("Missing dependency 'mysql-connector-python'. Install with: python -m pip install mysql-connector-python") from e

import random
from .database import get_db
from mysql.connector import errorcode
from datetime import datetime, date
import os
from .recommend import RecommendationLogs
from .movies import Movies

# Do NOT open a DB connection at import time; use `get_db()` inside request handlers

def home():
    return render_template("home.html")

def movies():
    try:
        query = """
            SELECT m.movie_id, m.title, m.content_type, m.rating, COUNT(wh.session_id) as watch_count
            FROM movies m
            LEFT JOIN watch_history wh ON m.movie_id = wh.movie_id
            GROUP BY m.movie_id, m.title, m.content_type, m.rating
            ORDER BY watch_count DESC, m.movie_id
            LIMIT 20
        """
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(query)
        movies_list = cursor.fetchall()
        
        movies_data = []
        for movie in movies_list:
            movies_data.append({
                'movie_id': movie[0],
                'title': movie[1],
                'content_type': movie[2],
                'rating': movie[3],
                'watch_count': movie[4]
            })
        
        return render_template("movies.html", movies=movies_data)
    except Exception as e:
        print(f"Error fetching movies: {e}")
        return render_template("movies.html", movies=[], error=str(e))
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def movie_detail():
    movie_id = request.args.get('movie_id')
    
    if not movie_id:
        return "Movie ID required", 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movies WHERE movie_id = %s", (movie_id,))
        movie = cursor.fetchone()
        
        if not movie:
            return "Movie not found", 404
        
        movie_data = {
            'movie_id': movie[0],
            'title': movie[1],
            'genre': movie[2] if len(movie) > 2 else None,
            'release_year': movie[3] if len(movie) > 3 else None
        }
        
        cursor.execute("""
            SELECT * FROM reviews 
            WHERE movie_id = %s 
            ORDER BY review_id ASC 
            LIMIT 10
        """, (movie_id,))
        reviews = cursor.fetchall()
        
        return render_template("movie_detail.html", movie=movie_data, reviews=reviews)
    except Exception as e:
        print(f"Error fetching movie detail: {e}")
        return f"Error: {e}", 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass



def add_review_form():
    # Render the reviews page which includes the add-review form
    return render_template("reviews.html")


def reviews():
    # List reviews with optional filters and pagination
    movie_id = request.args.get("movie_id")
    user_id = request.args.get("user_id")
    try:
        page = int(request.args.get("page", 1))
    except Exception:
        page = 1
    per_page = 20

    conn = get_db()
    cursor = conn.cursor()
    params = []
    where = []
    if movie_id:
        where.append("reviews.movie_id = %s")
        params.append(movie_id)
    if user_id:
        where.append("reviews.user_id = %s")
        params.append(user_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    try:
        # total count for pagination
        count_sql = f"SELECT COUNT(*) FROM reviews {where_sql}"
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
            ORDER BY review_id ASC
            LIMIT %s OFFSET %s
        """
        exec_params = params + [per_page, offset]
        cursor.execute(sql, tuple(exec_params))
        reviews = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching reviews: {e}")
        reviews = []
        total_pages = 1
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    return render_template("reviews.html", reviews=reviews, page=page, total_pages=total_pages, movie_id=movie_id, user_id=user_id)



def add_review():
    # required fields (review_id is AUTO_INCREMENT in DB)
    user_id = request.form.get('user_id')
    movie_id = request.form.get('movie_id')
    rating = request.form.get('rating')
    device_type = request.form.get('device_type') or None
    is_verified_watch = request.form.get('is_verified_watch') or 0
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
    conn = get_db()
    cursor = conn.cursor()
    user_filter = request.args.get("user_name") or None

    try:
       base_query = """
        SELECT 
            wh.session_id AS ID,
            COALESCE(u.first_name, u.user_id, wh.user_id) AS UserName,
            COALESCE(m.title, wh.movie_id) AS MovieTitle,
            wh.watch_date AS WatchDate,
            wh.watch_duration_minutes AS MinutesWatched,
            wh.progress_percentage AS ProgressPercentage,
            wh.location_country AS Country,
            wh.user_rating AS Rating
        FROM watch_history wh
        LEFT JOIN movies m ON m.movie_id = wh.movie_id
        LEFT JOIN users u ON u.user_id = wh.user_id
        """
       params = []
       if user_filter:
            base_query += " WHERE u.first_name = %s "
            params.append(user_filter)

       base_query += " ORDER BY wh.watch_date DESC LIMIT 100"

       cursor.execute(base_query, tuple(params))
       watch_history_data = cursor.fetchall()

       return render_template("watch_history.html", watch_history=watch_history_data, user_name=user_filter)

    except Exception as e:
        print(f"Error fetching watch history: {e}", flush=True)
        return render_template_string(f"""
        <h2>Error loading watch history</h2>
        <p>Error: {e}</p>
        <a href="{{{{ url_for('home') }}}}">Back to Home</a>
        """)
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def delete_watch_history():
    conn = get_db()
    cursor = conn.cursor()
    wh_id = request.form.get("primary_key")
    
    if not wh_id:
        return jsonify(success=False, error="missing primary_key"), 400
    try:
        query = "DELETE FROM watch_history WHERE session_id = %s"
        cursor.execute(query, (wh_id,))
        conn.commit()

        want_json = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.accept_mimetypes.accept_json
        )
        if want_json:
            return jsonify(success=True, id=wh_id, deleted=cursor.rowcount)
        return redirect("/watch_history")
    except Exception as e:
        print("delete_watch_history error:", e, flush=True)
        return jsonify(success=False, error=str(e)), 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
    

def edit_watch_history(session_id):
    conn = get_db()
    cursor = conn.cursor()
    # this endpoint is used to access the form to update the specific watch history row
    try:
        cursor.execute(
            """
            SELECT session_id, user_id, movie_id, watch_date,
                   watch_duration_minutes, progress_percentage,
                   location_country, user_rating
            FROM watch_history
            WHERE session_id = %s
            """,
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            return render_template_string(f"""
                <h2>Not found</h2>
                <p>No watch history entry with id: {session_id}</p>
                <a href="{{{{ url_for('watch_history') }}}}">Back</a>
            """), 404

        # row is in the same order as the SELECT in the query above
        return render_template("edit_watch_history.html", entry=row)
    except Exception as e:
        print("edit_watch_history error:", e, flush=True)
        return render_template_string(f"""
            <h2>Error loading edit form</h2>
            <p>Error: {e}</p>
            <a href="{{{{ url_for('watch_history') }}}}">Back</a>
        """), 500


def update_watch_history():
    conn = get_db()
    cursor = conn.cursor()

    session_id = request.form.get("session_id")
    if not session_id:
        return "Missing session_id", 400

    # collect fields (allow blank fields)
    user_id = request.form.get("user_id") or None
    movie_id = request.form.get("movie_id") or None
    watch_date = request.form.get("watch_date") or None
    watch_duration_minutes = request.form.get("watch_duration_minutes") or None
    progress_percentage = request.form.get("progress_percentage") or None
    location_country = request.form.get("location_country") or None
    user_rating = request.form.get("user_rating") or None

    try:
        sql = """
        UPDATE watch_history
        SET user_id=%s,
            movie_id=%s,
            watch_date=%s,
            watch_duration_minutes=%s,
            progress_percentage=%s,
            location_country=%s,
            user_rating=%s
        WHERE session_id=%s
        """
        values = (
            user_id,
            movie_id,
            watch_date,
            watch_duration_minutes,
            progress_percentage,
            location_country,
            user_rating,
            session_id,
        )
        cursor.execute(sql, values)
        conn.commit()
    except Exception as e:
        print("update_watch_history error:", e, flush=True)
        return render_template_string(f"<p>Error: {e}</p><a href='/watch_history'>Back</a>"), 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    # redirect back to watch_history based on the user_id of the row that was being edited
    if user_id:
        return redirect(f"/watch_history?user_id={user_id}")
    return redirect("/watch_history")

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

    # optional filtering by user (name or email)
    user_filter = request.args.get('user')

    conn = get_db()
    # prepare users list for the filter dropdown
    users_list = []
    ucur = conn.cursor(dictionary=True)
    try:
        ucur.execute("SELECT user_id, first_name, email FROM users ORDER BY first_name IS NULL, first_name, user_id LIMIT 2000")
        rows = ucur.fetchall()
        # build a deduplicated display list (show each display name once)
        seen = set()
        for r in rows:
            disp = (r.get('first_name') or r.get('email') or r.get('user_id') or '').strip()
            if not disp:
                continue
            key = disp.lower()
            if key in seen:
                continue
            seen.add(key)
            users_list.append({'user_id': r.get('user_id'), 'display': disp})
    except Exception:
        users_list = []
    finally:
        try:
            ucur.close()
        except Exception:
            pass

    # get total count with optional filter (join users when needed)
    count_cursor = conn.cursor()
    total = 0
    try:
        if user_filter:
            count_sql = "SELECT COUNT(*) FROM search_logs s LEFT JOIN users u ON s.user_id = u.user_id WHERE (u.first_name LIKE %s OR u.email LIKE %s OR s.user_id = %s)"
            like_param = f"%{user_filter}%"
            count_cursor.execute(count_sql, (like_param, like_param, user_filter))
        else:
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
    base_query = """
        SELECT s.*, u.first_name AS user_name, u.email AS user_email
        FROM search_logs s
        LEFT JOIN users u ON s.user_id = u.user_id
    """
    where_clauses = []
    params = []
    if user_filter:
        where_clauses.append("(u.first_name LIKE %s OR u.email LIKE %s OR s.user_id = %s)")
        like_param = f"%{user_filter}%"
        params.extend([like_param, like_param, user_filter])

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    query = f"{base_query}{where_sql} ORDER BY s.search_date DESC, s.search_id DESC LIMIT %s OFFSET %s"

    logs = []
    try:
        exec_params = params + [per_page, offset]
        cursor.execute(query, tuple(exec_params))
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

    return render_template("search_logs.html", logs=logs, page=page, total_pages=total_pages, users_list=users_list, user_filter=user_filter)


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
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Query with actual watch and rating calculations - show users with watch history
        sql = """
            SELECT 
                w.user_id,
                w.user_id AS user_name,
                COUNT(DISTINCT s.search_id) AS total_searches,
                COUNT(DISTINCT w.session_id) AS total_watch_events,
                COALESCE(AVG(r.rating), 0.0) AS avg_rating,
                (SELECT m.title 
                 FROM watch_history w2 
                 JOIN movies m ON w2.movie_id = m.movie_id
                 WHERE w2.user_id = w.user_id 
                 GROUP BY m.movie_id 
                 ORDER BY COUNT(*) DESC 
                 LIMIT 1) AS top_movie
            FROM watch_history w
            LEFT JOIN search_logs s ON w.user_id = s.user_id
            LEFT JOIN reviews r ON CONCAT('user_', w.user_id) = r.user_id
            GROUP BY w.user_id
            ORDER BY total_watch_events DESC
            LIMIT 50
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        # Country stats with nested subqueries - using derived table to avoid GROUP BY issues
        country_sql = """
            SELECT 
                country,
                total_searches,
                (SELECT COUNT(*)
                 FROM watch_history w
                 WHERE COALESCE(w.location_country, 'Unknown') = country
                ) AS total_watch_events,
                0.0 AS avg_rating,
                (SELECT search_query 
                 FROM search_logs s2
                 WHERE COALESCE(s2.location_country, 'Unknown') = country
                 GROUP BY search_query
                 ORDER BY COUNT(*) DESC
                 LIMIT 1
                ) AS top_search_query,
                (SELECT m.title
                 FROM watch_history w2
                 JOIN movies m ON w2.movie_id = m.movie_id
                 WHERE COALESCE(w2.location_country, 'Unknown') = country
                 GROUP BY m.movie_id
                 ORDER BY COUNT(*) DESC
                 LIMIT 1
                ) AS top_movie
            FROM (
                SELECT 
                    COALESCE(location_country, 'Unknown') AS country,
                    COUNT(*) AS total_searches
                FROM search_logs
                GROUP BY COALESCE(location_country, 'Unknown')
            ) AS country_searches
            ORDER BY total_searches DESC
            LIMIT 20
        """
        cursor.execute(country_sql)
        country_rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template("analytics.html", rows=rows, country_rows=country_rows)
        
    except Exception as e:
        import traceback
        return f"<h1>Analytics Error</h1><pre>{traceback.format_exc()}</pre>", 500

    # analytics returns above; recommendation logic is handled by `recommend()` function
    
def recommend():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    rec_logs = RecommendationLogs(db)
    movies = Movies(db)
    
    user_id = None
    success_message = None
    
    if request.args.get('success') and request.args.get('movie_title'):
        success_message = f"New recommendation added: {request.args.get('movie_title')}"
    
    if request.method == 'POST':
        user_id = request.form.get('user_id')
    elif request.method == 'GET':
        user_id = request.args.get('user_id')
    
    if user_id:
        try:
            recommendations = rec_logs.get_user_recommendations(user_id, limit=10)
            
            if not recommendations:
                return render_template("recommend.html", 
                                     error=f"No recommendations found for User ID: {user_id}", 
                                     show_form=True,
                                     user_id=user_id)
            
            movie_titles = []
            for rec in recommendations:
                movie = movies.select_movie(rec['movie_id'])
                if movie:
                    movie_titles.append(movie['title'])
                else:
                    movie_titles.append(f"Unknown Movie (ID: {rec['movie_id']})")
            
            print(f"Recommendations: {len(recommendations)}, Titles: {len(movie_titles)}")
            return render_template("recommend.html", 
                                 recommendations=recommendations, 
                                 movie_titles=movie_titles,
                                 user_id=user_id,
                                 show_form=False,
                                 success_message=success_message)
        except Exception as e:
            print(f"Error fetching recommendations: {e}")
            return render_template("recommend.html", 
                                 error=f"Error: {str(e)}", 
                                 show_form=True)
    
    return render_template("recommend.html", show_form=True)

def click_recommendation():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    recommendation_id = request.form.get('recommendation_id')
    movie_id = request.form.get('movie_id')
    
    if not recommendation_id:
        return "Recommendation ID required", 400
    
    try:
        cursor.execute("""
            UPDATE recommendation_logs 
            SET clicked = 1 
            WHERE recommendation_id = %s
        """, (recommendation_id,))
        db.commit()
        
        return redirect(f"/movie?movie_id={movie_id}")
    except Exception as e:
        print(f"Error updating recommendation: {e}")
        return f"Error: {e}", 500
    
def remove_recommendation():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    recommendation_id = request.form.get('recommendation_id')
    user_id = request.form.get('user_id')
    
    if not recommendation_id:
        return "Recommendation ID required", 400
    
    try:
        cursor.execute("""
            DELETE FROM recommendation_logs 
            WHERE recommendation_id = %s
        """, (recommendation_id,))
        db.commit()
        
        print(f"Deleted recommendation: {recommendation_id}")
        
        return redirect(f"/recommend?user_id={user_id}")
    except Exception as e:
        print(f"Error removing recommendation: {e}")
        return f"Error: {e}", 500
    
def add_new_recommendation():
    if request.method != 'POST':
        return redirect(url_for('recommend'))
    
    user_id = request.form.get('user_id')
    
    if not user_id:
        return "User ID required", 400
    
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT m.movie_id, m.title 
            FROM movies m
            WHERE m.movie_id NOT IN (
                SELECT movie_id 
                FROM recommendation_logs 
                WHERE user_id = %s
            )
            ORDER BY RAND()
            LIMIT 1
        """, (user_id,))
        
        movie = cursor.fetchone()
        
        if not movie:
            cursor.execute("""
                SELECT movie_id, title 
                FROM movies 
                ORDER BY RAND() 
                LIMIT 1
            """)
            movie = cursor.fetchone()
        
        if not movie:
            return "No movies available", 404
        
        cursor.execute("""
            SELECT MAX(CAST(SUBSTRING(recommendation_id, 5) AS UNSIGNED)) as max_id
            FROM recommendation_logs
            WHERE recommendation_id LIKE 'rec_%'
        """)
        max_result = cursor.fetchone()
        max_id = max_result['max_id'] if max_result and max_result['max_id'] else 0
        recommendation_id = f"rec_{str(max_id + 1).zfill(6)}"
        
        score = round(random.uniform(0.5, 1.0), 3)
        
        cursor.execute("""
            SELECT COALESCE(MAX(position), 0) + 1 as next_position
            FROM recommendation_logs
            WHERE user_id = %s
        """, (user_id,))
        position_result = cursor.fetchone()
        position = position_result['next_position'] if position_result else 1
        
        cursor.execute("""
            INSERT INTO recommendation_logs 
            (recommendation_id, user_id, movie_id, score, clicked, position)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (recommendation_id, user_id, movie['movie_id'], score, 0, position))
        
        db.commit()
        cursor.close()
        db.close()
        
        return redirect(f"/recommend?user_id={user_id}&success=1&movie_title={movie['title']}")
        
    except Exception as e:
        print(f"Error adding new recommendation: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {e}", 500
    