try:
    from flask import render_template, request, redirect, url_for, render_template_string
except ImportError as e:
    raise RuntimeError("Missing dependency 'Flask'. Install with: python -m pip install Flask") from e

try:
    import mysql.connector
except ImportError as e:
    raise RuntimeError("Missing dependency 'mysql-connector-python'. Install with: python -m pip install mysql-connector-python") from e

from database import get_db
from datetime import date
def home():
    return render_template("home.html")

def movies():
    return render_template("movies.html")

def reviews():
    return render_template("reviews.html")

def add_review_form():
    return render_template("reviews.html")

def add_review():
    review_id = request.form.get("review_id")
    user_id = request.form["user_id"]
    movie_id = request.form["movie_id"]
    rating = request.form["rating"]
    device_type = request.form.get("device_type")
    is_verified = request.form.get("is_verified")
    total_votes = request.form.get("total_votes")

    sql = """
    INSERT INTO reviews 
        (review_id, user_id, movie_id, rating, review_date, device_type, is_verified, total_votes)
    VALUES 
        (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (review_id, user_id, movie_id, rating, date.today(), device_type, is_verified, total_votes)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql, values)
    conn.commit()
    cursor.close()
    conn.close()

    return render_template_string("""
    <h2>Review added successfully! ✅</h2>
    <a href="{{ url_for('home') }}">Back to Home 🏠</a>
    """)


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
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM search_logs ORDER BY search_id DESC LIMIT 10")
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("search_logs.html", logs=logs)


# Add record
def add_search_log():
    if request.method == "POST":
        user_id = request.form["user_id"]
        search_query = request.form["search_query"]
        location_country = request.form["location_country"]
        clicked_pos = request.form.get("clicked_result_position") or None

        # we set the date automatically to today
        search_date = date.today()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO search_logs (user_id, search_query, search_date, clicked_result_position, location_country)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, search_query, search_date, clicked_pos, location_country))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for("search_logs"))

    
    return redirect(url_for("search_logs"))


# Delete record
def delete_search_log(search_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM search_logs WHERE search_id = %s", (search_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("search_logs"))




