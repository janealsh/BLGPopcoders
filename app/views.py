from flask import render_template, request , render_template_string, redirect
import mysql.connector
from datetime import date

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="jane2004",
    database="netflix2025"
)

cursor = db.cursor()


def home():
    return render_template("home.html")

def movies():
    return render_template("movies.html")


def reviews():
    # Load movies for selector
    try:
        cursor.execute("SELECT movie_id, title FROM movies ORDER BY title")
        movies = cursor.fetchall()
    except Exception:
        movies = []

    selected_movie_id = request.args.get('movie_id')
    reviews = []
    if selected_movie_id:
        try:
            cursor.execute(
                """
                SELECT review_id, user_id, movie_id, rating, review_date, device_type, is_verified, total_votes
                FROM reviews
                WHERE movie_id = %s
                ORDER BY review_date DESC
                """,
                (selected_movie_id,)
            )
            reviews = cursor.fetchall()
        except Exception:
            reviews = []

    return render_template("reviews.html", movies=movies, reviews=reviews, selected_movie_id=selected_movie_id)


def add_review():
    # required fields
    review_id = request.form.get('review_id')
    user_id = request.form.get('user_id')
    movie_id = request.form.get('movie_id')
    rating = request.form.get('rating')
    device_type = request.form.get('device_type') or None
    is_verified = request.form.get('is_verified') or 0
    total_votes = request.form.get('total_votes') or 0

    if not (review_id and user_id and movie_id and rating):
        return "Missing required fields", 400

    sql = """
    INSERT INTO reviews (review_id, user_id, movie_id, rating, review_date, device_type, is_verified, total_votes)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (review_id, user_id, movie_id, rating, date.today(), device_type, is_verified, total_votes)
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
    is_verified = request.form.get('is_verified') or 0
    total_votes = request.form.get('total_votes') or 0
    movie_id = request.form.get('movie_id')

    if not review_id:
        return "Missing review_id", 400

    sql = """
    UPDATE reviews
    SET rating=%s, device_type=%s, is_verified=%s, total_votes=%s
    WHERE review_id=%s
    """
    values = (rating, device_type, is_verified, total_votes, review_id)
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
    # db = current_app.config["db"]
    # watch_history = db.watch_history()
    # return render_template("watch_history.html", watch_history = watch_history)

    try: 
        query = """SELECT * FROM watch_history
            ORDER BY watch_date DESC
            LIMIT 100"""
        cursor.execute(query)
        watch_history_data = cursor.fetchall()
        watch_history_columns = [column[0] for column in cursor.fetchall()]

    except mysql.connector.Error as e:
        return f"Database error: {e}. Please check your database and connection, then try again."

    return render_template("watch_history.html", watch_history=watch_history_data, columns=watch_history_columns)



def recommend():
    return render_template("recommend.html")
