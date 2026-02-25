from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from api.decorators import admin_required
from api.models import AppSettings

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET"])
@jwt_required()
def get_settings():
    """Retourne les paramètres globaux de l'application."""
    s = AppSettings.get_instance()
    return jsonify({"allow_no_mask": s.allow_no_mask})


@settings_bp.route("/settings", methods=["PUT"])
@admin_required
def update_settings():
    """Met à jour les paramètres globaux (admin uniquement)."""
    data = request.get_json(silent=True) or {}
    s = AppSettings.get_instance()
    if "allow_no_mask" in data:
        s.allow_no_mask = bool(data["allow_no_mask"])
        s.save()
    return jsonify({"allow_no_mask": s.allow_no_mask})
