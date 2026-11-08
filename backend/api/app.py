import logging
import os

from flask import Flask, jsonify, send_from_directory
from flask_jwt_extended import JWTManager
from flask_swagger_ui import get_swaggerui_blueprint
from werkzeug.exceptions import HTTPException

from api.config import Config
from api.models import db, init_db
from api.routes.auth import auth_bp
from api.routes.camera import camera_bp
from api.routes.masks import masks_bp
from api.routes.photos import photos_bp
from api.routes.printer import printer_bp
from api.routes.settings import settings_bp

_HERE = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    JWTManager(app)

    init_db()

    # Une connexion SQLite par requête, fermée systématiquement : sans ça chaque thread
    # Werkzeug garde sa connexion ouverte jusqu'au GC et les descripteurs s'accumulent.
    @app.before_request
    def _db_connect():
        db.connect(reuse_if_open=True)

    @app.teardown_request
    def _db_close(_exc):
        if not db.is_closed():
            db.close()

    # Toute exception non gérée renvoie du JSON (le frontend lit `error`) et est loggée.
    @app.errorhandler(Exception)
    def _handle_unexpected_error(e):
        if isinstance(e, HTTPException):
            return e
        logger.exception("Unhandled error")
        return jsonify({"error": f"Erreur serveur : {e}"}), 500

    app.register_blueprint(auth_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(masks_bp)
    app.register_blueprint(photos_bp)
    app.register_blueprint(printer_bp)
    app.register_blueprint(settings_bp)

    # Swagger UI — accessible à /docs
    swaggerui_bp = get_swaggerui_blueprint(
        "/docs",
        "/openapi.yaml",
        config={"app_name": "Photobooth API"},
    )
    app.register_blueprint(swaggerui_bp, url_prefix="/docs")

    @app.route("/openapi.yaml")
    def openapi_spec():
        return send_from_directory(_HERE, "openapi.yaml", mimetype="text/yaml")

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(_HERE, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

    return app
