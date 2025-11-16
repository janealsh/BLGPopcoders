from flask import Flask, render_template
app = Flask(__name__)

import views

def create_app():
    app = Flask(__name__)
    app.config["DEBUG"] = True
    app.config["PORT"] = 8080

    return app


if __name__ == '__main__':
    app = create_app()
    port = app.config.get("PORT", 5000)
    app.run(host="0.0.0.0" , port=port)
