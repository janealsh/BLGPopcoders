from flask import Flask, render_template
from pathlib import Path

def create_app():
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    app = Flask(__name__, template_folder=str(templates_dir))    
    app.config["DEBUG"] = True
    app.config["PORT"] = 8080

    import views

    app.add_url_rule("/", view_func=views.home)
    app.add_url_rule("/movies", view_func=views.movies)
    app.add_url_rule("/reviews", view_func=views.reviews)
    app.add_url_rule("/watch_history", view_func=views.watch_history)
    app.add_url_rule("/recommend", view_func=views.recommend)

    return app


if __name__ == "__main__":
    app = create_app()
    port = app.config.get("PORT", 5000)
    app.run(host="0.0.0.0", port=port)
