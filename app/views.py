from flask import render_template, request , render_template_string
import mysql.connector
from datetime import date
from recommend import RecommendationLogs

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

    try:
        recommendations = rec_logs.get_random_logs(count=4)
        
        if recommendations:
            column_names = list(recommendations[0].keys())
        else:
            column_names = []
        
        return render_template("recommend.html", recommendations=recommendations, column_names=column_names)
    except Exception as e:
        print(f"Error fetching recommendation logs: {e}")
        return render_template("recommend.html", recommendations=[], column_names=[], error=str(e))
