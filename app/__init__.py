"""NAS Web File Server application."""

import os

from dotenv import load_dotenv

load_dotenv()

from flask import Flask

from app.utils import BASE_PATH


def create_app():
    """Create and configure the Flask application."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(root, "templates"),
        static_folder=os.path.join(root, "static"),
    )
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1GB max upload
    app.config["BASE_PATH"] = BASE_PATH

    from app import routes

    app.register_blueprint(routes.bp)

    return app
