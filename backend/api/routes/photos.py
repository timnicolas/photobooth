import os

from flask import Blueprint, jsonify, send_from_directory
from flask_jwt_extended import jwt_required

from api.config import Config
from api.decorators import admin_required
from api.models import Photo

photos_bp = Blueprint("photos", __name__)


@photos_bp.route("/photos", methods=["GET"])
@jwt_required()
def list_photos():
    """Liste toutes les photos, de la plus récente à la plus ancienne."""
    photos = Photo.select().order_by(Photo.captured_at.desc())
    return jsonify(
        [
            {
                "id": p.id,
                "filename": p.filename,
                "mask_id": p.mask_id,
                "captured_at": p.captured_at.isoformat(),
                "printed": p.printed,
            }
            for p in photos
        ]
    )


@photos_bp.route("/photos/<int:photo_id>", methods=["GET"])
@jwt_required()
def get_photo(photo_id):
    """Détail d'une photo."""
    photo = Photo.get_or_none(Photo.id == photo_id)
    if not photo:
        return jsonify({"error": "Photo introuvable"}), 404
    return jsonify(
        {
            "id": photo.id,
            "filename": photo.filename,
            "mask_id": photo.mask_id,
            "captured_at": photo.captured_at.isoformat(),
            "printed": photo.printed,
        }
    )


@photos_bp.route("/photos/<int:photo_id>", methods=["DELETE"])
@admin_required
def delete_photo(photo_id):
    """Supprime une photo du disque et de la base (admin uniquement)."""
    photo = Photo.get_or_none(Photo.id == photo_id)
    if not photo:
        return jsonify({"error": "Photo introuvable"}), 404

    filepath = os.path.join(Config.PHOTOS_DIR, photo.filename)
    try:
        os.remove(filepath)
    except FileNotFoundError:
        pass

    photo.delete_instance()
    return jsonify({"message": "Photo supprimée"}), 200


@photos_bp.route("/photos/<int:photo_id>/file", methods=["GET"])
def serve_photo(photo_id):
    """Télécharge le fichier JPEG d'une photo.
    Pas de JWT : utilisé comme src d'image dans le navigateur (réseau local).
    """
    photo = Photo.get_or_none(Photo.id == photo_id)
    if not photo:
        return jsonify({"error": "Photo introuvable"}), 404
    return send_from_directory(
        os.path.abspath(Config.PHOTOS_DIR),
        photo.filename,
        mimetype="image/jpeg",
    )
