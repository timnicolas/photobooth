import os
import time

import cv2
from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import jwt_required

from api.camera import apply_mask, capture_frame, mjpeg_frames
from api.config import Config
from api.models import Mask, Photo
from api.printer import PrinterManager

camera_bp = Blueprint("camera", __name__)


# Le flux vidéo est accessible sans JWT car un <img src="..."> dans le navigateur
# ne peut pas envoyer de headers d'autorisation. Sur réseau local c'est acceptable.
@camera_bp.route("/camera/stream")
def stream():
    """Flux vidéo MJPEG en temps réel, croppé selon l'orientation, avec masque optionnel.

    Query params:
        orientation (str, défaut "portrait") — "portrait" ou "landscape"
        mask_id     (int, optionnel)         — id du masque à appliquer dans le flux
    """
    orientation = request.args.get("orientation", "portrait")
    mask_id = request.args.get("mask_id", type=int)

    mask_path = None
    if mask_id:
        mask = Mask.get_or_none(Mask.id == mask_id)
        if mask:
            mask_path = os.path.join(Config.MASKS_DIR, mask.filename)

    return Response(
        mjpeg_frames(orientation, mask_path),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@camera_bp.route("/camera/capture", methods=["POST"])
@jwt_required()
def capture():
    """Capture une photo, applique le masque actif, enregistre en DB et imprime si demandé.

    Query params:
        print       (bool, défaut false)      — si true, envoie la photo à l'imprimante
        orientation (str,  défaut "portrait") — "portrait" ou "landscape"
    """
    should_print = request.args.get("print", "false").lower() == "true"
    orientation = request.args.get("orientation", "portrait")

    # 1. Capture de la frame (avec crop selon orientation)
    try:
        frame = capture_frame(orientation)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    # 2. Sauvegarde sur disque
    os.makedirs(Config.PHOTOS_DIR, exist_ok=True)
    filename = f"photo_{int(time.time())}.jpg"
    filepath = os.path.join(Config.PHOTOS_DIR, filename)
    raw_filename = filename.replace(".jpg", "_raw.jpg")
    raw_filepath = os.path.join(Config.PHOTOS_DIR, raw_filename)

    # 3. Application du masque actif (si existant)
    active_mask = Mask.get_or_none(Mask.is_active == True)  # noqa: E712
    if active_mask:
        mask_path = os.path.join(Config.MASKS_DIR, active_mask.filename)
        # Version brute (sans masque)
        cv2.imwrite(raw_filepath, frame)
        # Version finale avec masque
        composited = apply_mask(frame, mask_path)
        cv2.imwrite(filepath, composited)
    else:
        # Sans masque : raw et filtered sont identiques
        cv2.imwrite(filepath, frame)
        cv2.imwrite(raw_filepath, frame)

    # 4. Enregistrement en base
    photo = Photo.create(
        filename=filename,
        mask=active_mask,
        printed=False,
    )

    # 5. Impression si demandée
    print_error = None
    if should_print:
        try:
            pm = PrinterManager()
            pm.imprimer_image(Config.PRINTER_NAME, filepath, sans_bordure=True)
            photo.printed = True
            photo.save()
        except Exception as e:
            print_error = str(e)

    response = {
        "id": photo.id,
        "filename": filename,
        "mask_applied": active_mask.id if active_mask else None,
        "printed": photo.printed,
    }
    if print_error:
        response["print_error"] = print_error

    return jsonify(response), 201
