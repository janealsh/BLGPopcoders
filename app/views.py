from flask import render_template, request , render_template_string, redirect, jsonify
import mysql.connector
from datetime import date
from recommend import RecommendationLogs
from movies import Movies

# Database connection
db = mysql.connector.connect(
    host= 'localhost',
    user='root',
    password='jane2004',
    database='netflix2025'
)

cursor = db.cursor()


def home():
    return render_template("home.html")

def movies():
    return render_template("movies.html")


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
        cursor.execute(sql, values)
        db.commit()
    except mysql.connector.Error as e:
        return f"Database error: {e}", 500

    return redirect(f"/reviews?movie_id={movie_id}")


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
        cursor.execute(sql, values)
        db.commit()
    except mysql.connector.Error as e:
        return f"Database error: {e}", 500

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
        cursor.execute(sql, values)
        db.commit()
    except mysql.connector.Error as e:
        return f"Database error: {e}", 500

    # redirect back to the movie reviews page if possible
    movie_id = request.form.get('movie_id') or ''
    return redirect(f"/reviews?movie_id={movie_id}")

def watch_history():
    user_filter = request.args.get("user_id") or None

    try:
       base_query = """
        SELECT 
            wh.session_id AS ID,
            wh.user_id AS UserID,
            wh.movie_id AS MovieID,
            wh.watch_date AS WatchDate,
            wh.watch_duration_minutes AS MinutesWatched,
            wh.progress_percentage AS ProgressPercentage,
            wh.location_country AS Country,
            wh.user_rating AS Rating
        FROM watch_history wh
        """
       params = []
       if user_filter:
            base_query += " WHERE wh.user_id = %s "
            params.append(user_filter)

       base_query += " ORDER BY wh.watch_date DESC LIMIT 100"

       cursor.execute(base_query, tuple(params))
       watch_history_data = cursor.fetchall()

       return render_template("watch_history.html", watch_history=watch_history_data, user_id=user_filter)

    except Exception as e:
        print(f"Error fetching watch history: {e}")
        return render_template_string(f"""
        <h2>Error loading watch history</h2>
        <p>Error: {e}</p>
        <a href="{{{{ url_for('home') }}}}">Back to Home</a>
        """)

    # # db = current_app.config["db"]
    # # watch_history = db.get_watch_history()
    # # return render_template("watch_history.html", watch_history = watch_history)
    # return render_template("watch_history.html")


def delete_watch_history():
    wh_id = request.form.get("primary_key")
    if not wh_id:
        return jsonify(success=False, error="missing primary_key"), 400
    try:
        query = "DELETE FROM watch_history WHERE session_id = %s"
        cursor.execute(query, (wh_id,))
        db.commit()
        return redirect("/watch_history")
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    

def edit_watch_history(session_id):
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
        db.commit()
    except Exception as e:
        print("update_watch_history error:", e, flush=True)
        return render_template_string(f"""
            <h2>Error updating entry</h2>
            <p>{e}</p>
            <a href="{{{{ url_for('watch_history') }}}}">Back</a>
        """), 500

    # redirect back to watch_history based on the user_id of the row that was being edited
    if user_id:
        return redirect(f"/watch_history?user_id={user_id}")
    return redirect("/watch_history")

def recommend():
    rec_logs = RecommendationLogs(db)
    movies = Movies(db)

    try:
        recommendations = rec_logs.get_random_logs(count=4)
        movie_titles = []
        for rec in recommendations:
            movie = movies.select_movie(rec['movie_id'])
            if movie:
                movie_titles.append(movie['title'])
            else:
                print(f"No movie found for movie_id: {rec['movie_id']}")
        
        print(f"Recommendations: {len(recommendations)}, Titles: {len(movie_titles)}")
        return render_template("recommend.html", recommendations=recommendations, movie_titles=movie_titles)
    except Exception as e:
        print(f"Error fetching recommendations: {e}")
        return render_template("recommend.html", recommendations=[], movie_titles=[], error=str(e))
