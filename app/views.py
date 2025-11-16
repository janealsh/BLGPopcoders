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

def recommend():
    return render_template("recommend.html")
