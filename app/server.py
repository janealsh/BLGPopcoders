from flask import Flask, render_template
from pathlib import Path
import views

def create_app():
    base_dir = Path(__file__).resolve().parents[1]
    templates_dir = base_dir / "templates"
    static_dir = base_dir / "static"
    app = Flask(__name__, template_folder=str(templates_dir), static_folder=str(static_dir))    
    app.config["DEBUG"] = True
    app.config["PORT"] = 8080

    app.add_url_rule("/", view_func=views.home)
    app.add_url_rule("/movies", view_func=views.movies)
    app.add_url_rule("/reviews", view_func=views.reviews)
    app.add_url_rule("/watch_history", view_func=views.watch_history)
    app.add_url_rule("/delete_watch_history", view_func=views.delete_watch_history, methods=["POST"])
    app.add_url_rule("/recommend", view_func=views.recommend)

    app.add_url_rule("/add_review", view_func=views.add_review, methods=["POST"])
    app.add_url_rule("/update_review", view_func=views.update_review, methods=["POST"])
    app.add_url_rule("/delete_review", view_func=views.delete_review, methods=["POST"])



    return app

if __name__ == "__main__":
    app = create_app()
    port = app.config.get("PORT", 5000)
    app.run(host="0.0.0.0", port=port)
