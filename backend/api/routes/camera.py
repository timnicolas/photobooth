import os
import time

import cv2
import numpy as np
from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import jwt_required

from api.camera import capture_frame, mjpeg_frames
from api.config import Config
from api.models import Mask, Photo
from api.printer import PrinterManager

camera_bp = Blueprint("camera", __name__)


def _apply_mask(frame_bgr: np.ndarray, mask_path: str) -> np.ndarray:
    """Alpha-composite un masque PNG (BGRA) sur la frame BGR de la caméra.

    Formule Porter-Duff "over" :
        résultat = alpha * masque + (1 - alpha) * photo
    """
    mask_bgra = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
    if mask_bgra is None or mask_bgra.ndim < 3 or mask_bgra.shape[2] != 4:
        return frame_bgr  # masque absent ou sans canal alpha → retour tel quel

    h, w = frame_bgr.shape[:2]
    mask_bgra = cv2.resize(mask_bgra, (w, h), interpolation=cv2.INTER_LINEAR)

    mask_bgr = mask_bgra[:, :, :3].astype(np.float32)
    alpha = mask_bgra[:, :, 3].astype(np.float32) / 255.0
    alpha3 = alpha[:, :, np.newaxis]  # (h, w, 1) pour broadcaster sur 3 canaux

    composited = alpha3 * mask_bgr + (1.0 - alpha3) * frame_bgr.astype(np.float32)
    return composited.astype(np.uint8)


# Le flux vidéo est accessible sans JWT car un <img src="..."> dans le navigateur
# ne peut pas envoyer de headers d'autorisation. Sur réseau local c'est acceptable.
@camera_bp.route("/camera/stream")
def stream():
    """Flux vidéo MJPEG en temps réel.
    Protocole : multipart/x-mixed-replace — compatible nativement avec <img> HTML.
    """
    return Response(
        mjpeg_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@camera_bp.route("/camera/capture", methods=["POST"])
@jwt_required()
def capture():
    """Capture une photo, applique le masque actif, enregistre en DB et imprime si demandé.

    Query params:
        print (bool, défaut false) — si true, envoie la photo à l'imprimante
    """
    should_print = request.args.get("print", "false").lower() == "true"

    # 1. Capture de la frame
    try:
        frame = capture_frame()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    # 2. Sauvegarde sur disque
    os.makedirs(Config.PHOTOS_DIR, exist_ok=True)
    filename = f"photo_{int(time.time())}.jpg"
    filepath = os.path.join(Config.PHOTOS_DIR, filename)
    cv2.imwrite(filepath, frame)

    # 3. Application du masque actif (si existant)
    active_mask = Mask.get_or_none(Mask.is_active == True)  # noqa: E712
    if active_mask:
        mask_path = os.path.join(Config.MASKS_DIR, active_mask.filename)
        composited = _apply_mask(frame, mask_path)
        cv2.imwrite(filepath, composited)

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
