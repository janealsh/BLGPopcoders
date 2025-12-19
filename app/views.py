from flask import current_app, render_template

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
