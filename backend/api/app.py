import os

from flask import Flask, send_from_directory
from flask_jwt_extended import JWTManager
from flask_swagger_ui import get_swaggerui_blueprint

from api.config import Config
from api.models import init_db
from api.routes.auth import auth_bp
from api.routes.camera import camera_bp
from api.routes.masks import masks_bp
from api.routes.photos import photos_bp
from api.routes.printer import printer_bp

_HERE = os.path.dirname(os.path.abspath(__file__))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    JWTManager(app)

    init_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(masks_bp)
    app.register_blueprint(photos_bp)
    app.register_blueprint(printer_bp)

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

    return app
