import logging
import os
import time

import cv2
from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import jwt_required

from api.camera import apply_mask, capture_frame, ensure_camera_ready, mjpeg_frames
from api.config import Config
from api.models import Mask, Photo
from api.printer import PrinterManager


camera_bp = Blueprint("camera", __name__)
logger = logging.getLogger(__name__)


def _write_jpeg(path: str, image, params) -> None:
    """Écrit un JPEG ; lève OSError si OpenCV n'a pas pu écrire (disque plein, droits...)."""
    if not cv2.imwrite(path, image, params):
        raise OSError(f"Écriture impossible : {path}")


def _remove_quietly(*paths: str) -> None:
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            pass


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

    try:
        ensure_camera_ready()
    except RuntimeError as e:
        # 503 avant le début du streaming : le client sait qu'il doit réessayer
        return jsonify({"error": str(e)}), 503

    return Response(
        mjpeg_frames(orientation),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
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
    except Exception as e:  # noqa: BLE001 — toute erreur caméra/libcamera doit renvoyer du JSON
        logger.exception("Capture failed")
        message = str(e) if isinstance(e, RuntimeError) else f"Erreur caméra : {e}"
        return jsonify({"error": message}), 503

    # 2. Chemins de sauvegarde (millisecondes : deux captures dans la même seconde ne s'écrasent pas)
    os.makedirs(Config.PHOTOS_DIR, exist_ok=True)
    filename = f"photo_{int(time.time() * 1000)}.jpg"
    filepath = os.path.join(Config.PHOTOS_DIR, filename)
    raw_filename = filename.replace(".jpg", "_raw.jpg")
    raw_filepath = os.path.join(Config.PHOTOS_DIR, raw_filename)

    # 3. Application du masque actif (si existant) puis écriture sur disque
    active_mask = Mask.get_or_none(Mask.is_active == True)  # noqa: E712
    jpeg_params = [cv2.IMWRITE_JPEG_QUALITY, Config.PHOTO_JPEG_QUALITY]
    composited = frame
    if active_mask:
        try:
            composited = apply_mask(frame, os.path.join(Config.MASKS_DIR, active_mask.filename))
        except Exception:  # noqa: BLE001 — mieux vaut une photo sans masque que pas de photo
            logger.exception("Applying mask %s failed, saving photo without mask", active_mask.id)
            active_mask = None
            composited = frame
    try:
        _write_jpeg(raw_filepath, frame, jpeg_params)  # version brute (sans masque)
        _write_jpeg(filepath, composited, jpeg_params)  # version finale
    except (OSError, cv2.error):
        logger.exception("Saving photo %s failed", filename)
        _remove_quietly(filepath, raw_filepath)
        return jsonify({"error": "Impossible d'enregistrer la photo (carte SD pleine ?)"}), 507

    # 4. Enregistrement en base
    try:
        photo = Photo.create(
            filename=filename,
            mask=active_mask,
            orientation=orientation,
            printed=False,
        )
    except Exception:
        _remove_quietly(filepath, raw_filepath)
        raise

    # 5. Impression si demandée
    print_error = None
    if should_print:
        try:
            pm = PrinterManager()
            pm.imprimer_image(Config.PRINTER_NAME, filepath, sans_bordure=True)
            photo.printed = True
            photo.save()
        except Exception as e:  # noqa: BLE001 — la photo est prise, l'impression peut être relancée
            logger.exception("Printing photo %s failed", photo.id)
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
