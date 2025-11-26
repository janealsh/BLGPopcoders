from flask import current_app, render_template
from flask import request, redirect, url_for
from database import get_db 
from datetime import date



def home():
    return render_template("home.html")


def movies():
    return render_template("movies.html")

def reviews():
    return render_template("reviews.html")

def watch_history():
    # db = current_app.config["db"]
    # watch_history = db.get_watch_history()
    # return render_template("watch_history.html", watch_history = watch_history)
    return render_template("watch_history.html")

def recommend():
    return render_template("recommend.html")

# we will create this function

# Show all logs (you should already have something like this)
def search_logs():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM search_logs ORDER BY search_id DESC")
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

    # if someone goes to /search-logs/add with GET, just go back to main page
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



