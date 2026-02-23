import os
import uuid

from flask import Blueprint, jsonify, request, send_from_directory
from flask_jwt_extended import jwt_required

from api.config import Config
from api.decorators import admin_required
from api.models import Mask, db

masks_bp = Blueprint("masks", __name__)

_ALLOWED_EXTENSIONS = {"png"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in _ALLOWED_EXTENSIONS


@masks_bp.route("/masks", methods=["POST"])
@admin_required
def upload_mask():
    """Upload un masque PNG (admin uniquement)."""
    if "file" not in request.files:
        return jsonify({"error": "Champ 'file' manquant"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Aucun fichier sélectionné"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "Seuls les fichiers PNG sont acceptés"}), 400

    label = request.form.get("label", "").strip() or file.filename
    unique_filename = f"{uuid.uuid4().hex}.png"

    os.makedirs(Config.MASKS_DIR, exist_ok=True)
    filepath = os.path.join(Config.MASKS_DIR, unique_filename)
    file.save(filepath)

    mask = Mask.create(filename=unique_filename, label=label)

    return jsonify(
        {
            "id": mask.id,
            "label": mask.label,
            "filename": mask.filename,
            "is_active": mask.is_active,
            "created_at": mask.created_at.isoformat(),
        }
    ), 201


@masks_bp.route("/masks", methods=["GET"])
@jwt_required()
def list_masks():
    """Liste tous les masques disponibles."""
    masks = Mask.select().order_by(Mask.created_at.desc())
    return jsonify(
        [
            {
                "id": m.id,
                "label": m.label,
                "filename": m.filename,
                "is_active": m.is_active,
                "created_at": m.created_at.isoformat(),
            }
            for m in masks
        ]
    )


@masks_bp.route("/masks/<int:mask_id>", methods=["DELETE"])
@admin_required
def delete_mask(mask_id):
    """Supprime un masque (admin uniquement)."""
    mask = Mask.get_or_none(Mask.id == mask_id)
    if not mask:
        return jsonify({"error": "Masque introuvable"}), 404

    filepath = os.path.join(Config.MASKS_DIR, mask.filename)
    try:
        os.remove(filepath)
    except FileNotFoundError:
        pass

    mask.delete_instance()
    return jsonify({"message": "Masque supprimé"}), 200


@masks_bp.route("/masks/<int:mask_id>/select", methods=["PUT"])
@jwt_required()
def select_mask(mask_id):
    """Définit le masque actif (un seul à la fois)."""
    mask = Mask.get_or_none(Mask.id == mask_id)
    if not mask:
        return jsonify({"error": "Masque introuvable"}), 404

    with db.atomic():
        Mask.update(is_active=False).execute()
        mask.is_active = True
        mask.save()

    return jsonify({"message": "Masque actif", "id": mask.id, "label": mask.label}), 200


@masks_bp.route("/masks/<int:mask_id>/file", methods=["GET"])
def serve_mask(mask_id):
    """Télécharge l'image d'un masque.
    Pas de JWT : utilisé comme src d'image dans le navigateur (réseau local).
    """
    mask = Mask.get_or_none(Mask.id == mask_id)
    if not mask:
        return jsonify({"error": "Masque introuvable"}), 404
    return send_from_directory(os.path.abspath(Config.MASKS_DIR), mask.filename, mimetype="image/png")
