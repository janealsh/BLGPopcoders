from flask import Flask
from pathlib import Path
import views  # import the whole module, we’ll use views.home, views.search_logs, etc.


def create_app():
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    app = Flask(__name__, template_folder=str(templates_dir))
    app.config["DEBUG"] = True
    app.config["PORT"] = 8080

    # Main pages
    app.add_url_rule("/", view_func=views.home)
    app.add_url_rule("/movies", view_func=views.movies)
    app.add_url_rule("/reviews", view_func=views.reviews)
    app.add_url_rule("/watch_history", view_func=views.watch_history)
    app.add_url_rule("/recommend", view_func=views.recommend)

    # Search logs pages
    app.add_url_rule("/search-logs", view_func=views.search_logs)
    app.add_url_rule(
        "/search-logs/add",
        view_func=views.add_search_log,
        methods=["POST"],
    )
    app.add_url_rule(
        "/search-logs/delete/<int:search_id>",
        view_func=views.delete_search_log,
        methods=["POST"],
    )

    return app


if __name__ == "__main__":
    app = create_app()
    port = app.config.get("PORT", 5000)
    app.run(host="0.0.0.0", port=port)
