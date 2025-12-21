try:
    from flask import Flask
except ImportError as e:
    raise RuntimeError("Missing dependency 'Flask'. Install with: python -m pip install Flask") from e
from pathlib import Path

def create_app():
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    app = Flask(__name__, template_folder=str(templates_dir))
    base_dir = Path(__file__).resolve().parents[1]
    templates_dir = base_dir / "templates"
    static_dir = base_dir / "static"
    app = Flask(__name__, template_folder=str(templates_dir), static_folder=str(static_dir))    
    app.config["DEBUG"] = True
    app.config["PORT"] = 8080
    app.secret_key = "your-secret-key-change-in-production"

    # Import views here to avoid circular imports during module import
    # Make imports resilient when running as `python app/server.py` or `python -m app.server`.
    import sys
    import importlib
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    try:
        views = importlib.import_module("app.views")
    except Exception:
        try:
            views = importlib.import_module("views")
        except Exception:
            from . import views

    # Main pages
    app.add_url_rule("/", view_func=views.home)
    app.add_url_rule("/movies", view_func=views.movies)
    app.add_url_rule("/movie", view_func=views.movie_detail)
    app.add_url_rule("/reviews", view_func=views.reviews)
    app.add_url_rule("/watch_history", view_func=views.watch_history)
    app.add_url_rule("/recommend", view_func=views.recommend, methods=["GET", "POST"])

    # Reviews (from main)
    
    app.add_url_rule("/add_review_form", view_func=views.add_review_form)
    
    app.add_url_rule("/add_review", view_func=views.add_review, methods=["POST"])
    app.add_url_rule("/update_review", view_func=views.update_review, methods=["POST"])
    app.add_url_rule("/delete_review", view_func=views.delete_review, methods=["POST"])

    app.add_url_rule("/click-recommendation", view_func=views.click_recommendation, methods=["POST"])
    app.add_url_rule('/remove-recommendation', view_func=views.remove_recommendation, methods=['POST'])

    # Search logs
    app.add_url_rule("/search-logs", view_func=views.search_logs)
    app.add_url_rule("/search-logs/add", view_func=views.add_search_log, methods=["POST"])
    app.add_url_rule("/search-logs/delete/<int:search_id>", view_func=views.delete_search_log, methods=["POST"])
    app.add_url_rule("/search-logs/edit/<int:search_id>", view_func=views.edit_search_log)
    app.add_url_rule("/search-logs/update", view_func=views.update_search_log, methods=["POST"])
    # Users CRUD
    app.add_url_rule("/users", view_func=views.users_list)
    app.add_url_rule("/users/add", view_func=views.add_user, methods=["POST"])
    app.add_url_rule("/users/edit/<user_id>", view_func=views.edit_user)
    app.add_url_rule("/users/update", view_func=views.update_user, methods=["POST"])
    app.add_url_rule("/users/delete/<user_id>", view_func=views.delete_user, methods=["POST"])
    # Analytics / complex queries
    app.add_url_rule("/analytics", view_func=views.analytics)

    return app

app = create_app()

if __name__ == "__main__":
    port = app.config.get("PORT", 5000)
    app.run(host="0.0.0.0", port=port)
