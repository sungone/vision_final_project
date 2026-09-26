from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")

from app.api import health_bp, inspections_bp, status_bp, stream_bp
from app.config import Config
from app.database import db
from app.lifecycle import install_runtime


def create_app(config: dict | type | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if isinstance(config, dict):
        app.config.update(config)
    elif config is not None:
        app.config.from_object(config)

    db.init_app(app)
    # Import registers model metadata before optional create_all.
    from app.models import Inspection  # noqa: F401

    Path(app.config["DEFECT_STORAGE_DIR"]).mkdir(parents=True, exist_ok=True)
    if app.config["DATABASE_AUTO_CREATE"]:
        with app.app_context():
            db.create_all()

    app.register_blueprint(stream_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(inspections_bp)
    app.register_blueprint(status_bp)
    install_runtime(app)
    _register_error_handlers(app)
    _register_cors_headers(app)
    return app


def _register_cors_headers(app: Flask) -> None:
    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin and origin.rstrip("/") in app.config["CORS_ALLOWED_ORIGINS"]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return jsonify({"error": error.name, "message": error.description}), error.code

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error: SQLAlchemyError):
        db.session.rollback()
        app.logger.exception("database request failed")
        return jsonify({"error": "database_unavailable", "message": "Database operation failed."}), 503

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("unhandled request error")
        return jsonify({"error": "internal_server_error", "message": "Unexpected server error."}), 500
