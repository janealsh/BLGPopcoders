try:
    from flask import Flask
except ImportError as e:
    raise RuntimeError("Missing dependency 'Flask'. Install with: python -m pip install Flask") from e
from pathlib import Path

def create_app():
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    app = Flask(__name__, template_folder=str(templates_dir))
    app.config["DEBUG"] = True
    app.config["PORT"] = 8080

    # Import views here to avoid circular imports during module import
    try:
        from . import views
    except Exception:
        import views

    # Main pages
    app.add_url_rule("/", view_func=views.home)
    app.add_url_rule("/movies", view_func=views.movies)
    app.add_url_rule("/reviews", view_func=views.reviews)
    app.add_url_rule("/watch_history", view_func=views.watch_history)
    app.add_url_rule("/recommend", view_func=views.recommend)

    # Reviews (from main)
    app.add_url_rule("/add_review_form", view_func=views.add_review_form)
    app.add_url_rule("/add_review", view_func=views.add_review, methods=["POST"])

    # Search logs
    app.add_url_rule("/search-logs", view_func=views.search_logs)
    app.add_url_rule("/search-logs/add", view_func=views.add_search_log, methods=["POST"])
    app.add_url_rule("/search-logs/delete/<int:search_id>", view_func=views.delete_search_log, methods=["POST"])

    return app

app = create_app()

if __name__ == "__main__":
    port = app.config.get("PORT", 5000)
    app.run(host="0.0.0.0", port=port)
