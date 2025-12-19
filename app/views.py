from flask import render_template, request , render_template_string
import mysql.connector
from datetime import date
from recommend import RecommendationLogs
from movies import Movies

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="PopC.2025",
    database="netflix2025"
)

cursor = db.cursor()

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

    cursor.execute(sql, values)
    db.commit()

    return render_template_string("""
    <h2>Review added successfully! ✅</h2>
    <a href="{{ url_for('home') }}">Back to Home 🏠</a>
     """)


def watch_history():
    # db = current_app.config["db"]
    # watch_history = db.get_watch_history()
    # return render_template("watch_history.html", watch_history = watch_history)
    return render_template("watch_history.html")

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
