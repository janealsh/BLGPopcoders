from flask import render_template, request, render_template_string
import mysql.connector
from datetime import date

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
    try:
        query = """
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
        ORDER BY wh.watch_date DESC
        LIMIT 100
        """
    
        cursor.execute(query)
        watch_history_data = cursor.fetchall()
        
        return render_template(
            "watch_history.html", 
            watch_history=watch_history_data
        )
        
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

    try: 
        wh_id = request.form.get("primary_key")

        query = """DELETE FROM watch_history WHERE session_id = %s"""
        cursor.execute(query, (wh_id,))
        db.commit()

        return "Watch history entry deleted successfully. <a href='/watch_history'>Back to Watch History</a>"

    except Exception as e:
        return f"Error deleting entry: {e}"

def recommend():
    return render_template("recommend.html")
