"""Abstraction caméra — sélectionne l'implémentation selon Config.CAMERA_TYPE.

Valeurs supportées :
  "integrated"  — caméra USB/intégrée via OpenCV (défaut, dev sur ordi)
  "picamera"    — Raspberry Pi Camera via picamera2
"""
import cv2
import numpy as np

from api.config import Config


def crop_to_orientation(frame: np.ndarray, orientation: str) -> np.ndarray:
    """Centre-crop la frame pour correspondre au ratio du format photo configuré.

    En portrait  : ratio = PHOTO_WIDTH_MM  / PHOTO_HEIGHT_MM  (ex. 89/119 ≈ 0.748)
    En paysage   : ratio = PHOTO_HEIGHT_MM / PHOTO_WIDTH_MM   (ex. 119/89 ≈ 1.337)
    """
    w_mm = Config.PHOTO_WIDTH_MM
    h_mm = Config.PHOTO_HEIGHT_MM
    if orientation == "landscape":
        w_mm, h_mm = h_mm, w_mm

    target_ratio = w_mm / h_mm
    h, w = frame.shape[:2]
    frame_ratio = w / h

    if frame_ratio > target_ratio:
        new_w = int(h * target_ratio)
        x = (w - new_w) // 2
        return frame[:, x : x + new_w]
    else:
        new_h = int(w / target_ratio)
        y = (h - new_h) // 2
        return frame[y : y + new_h, :]


def apply_mask(frame_bgr: np.ndarray, mask_path: str) -> np.ndarray:
    """Alpha-composite un masque PNG (BGRA) sur la frame BGR.

    Formule Porter-Duff "over" :
        résultat = alpha * masque + (1 - alpha) * photo
    """
    mask_bgra = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
    if mask_bgra is None or mask_bgra.ndim < 3 or mask_bgra.shape[2] != 4:
        return frame_bgr

    h, w = frame_bgr.shape[:2]
    mask_bgra = cv2.resize(mask_bgra, (w, h), interpolation=cv2.INTER_LINEAR)

    mask_bgr = mask_bgra[:, :, :3].astype(np.float32)
    alpha = mask_bgra[:, :, 3].astype(np.float32) / 255.0
    alpha3 = alpha[:, :, np.newaxis]

    composited = alpha3 * mask_bgr + (1.0 - alpha3) * frame_bgr.astype(np.float32)
    return composited.astype(np.uint8)


def capture_frame(orientation: str = "portrait") -> np.ndarray:
    """Capture une frame, crop selon l'orientation, retourne un array numpy BGR."""
    if Config.CAMERA_TYPE == "picamera":
        frame = _picamera_capture()
    else:
        frame = _integrated_capture()
    return crop_to_orientation(frame, orientation)


def mjpeg_frames(orientation: str = "portrait", mask_path: str = None):
    """Générateur de frames MJPEG croppées selon l'orientation, avec masque optionnel."""
    if Config.CAMERA_TYPE == "picamera":
        yield from _picamera_stream(orientation, mask_path)
    else:
        yield from _integrated_stream(orientation, mask_path)


# ---------------------------------------------------------------------------
# Integrated — OpenCV (USB / caméra intégrée)
# ---------------------------------------------------------------------------

def _integrated_capture() -> np.ndarray:
    cap = cv2.VideoCapture(Config.CAMERA_INDEX)
    try:
        success, frame = cap.read()
        if not success:
            raise RuntimeError("Impossible de lire la caméra intégrée")
        return frame
    finally:
        cap.release()


def _integrated_stream(orientation: str = "portrait", mask_path: str = None):
    cap = cv2.VideoCapture(Config.CAMERA_INDEX)
    try:
        while True:
            success, frame = cap.read()
            if not success:
                break
            frame = crop_to_orientation(frame, orientation)
            if mask_path:
                frame = apply_mask(frame, mask_path)
            _, buf = cv2.imencode(".jpg", frame)
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
    finally:
        cap.release()


# ---------------------------------------------------------------------------
# PiCamera2 — Raspberry Pi
# picamera2 est importé en lazy pour ne pas bloquer le démarrage sur ordi de dev
#
# Singleton: une seule instance Picamera2 est conservée ouverte pour éviter
# les erreurs "Device or resource busy" entre requêtes successives.
# ---------------------------------------------------------------------------
import threading

_picam2 = None
_picam2_lock = threading.Lock()


def _get_picamera():
    """Retourne l'instance Picamera2 singleton, en la créant si nécessaire.

    Preview léger (stream_size, BGR888) en continu.
    La capture haute résolution bascule temporairement en mode still via
    switch_mode_and_capture_array, puis revient au preview automatiquement.

    Note format : BGR888 en picamera2 stocke les bytes en ordre B,G,R — directement
    utilisable par OpenCV sans conversion. RGB888 stocke aussi en BGR (convention V4L2),
    ce qui entraînerait une double inversion et une teinte bleue si on convertissait.
    """
    global _picam2
    if _picam2 is None:
        from picamera2 import Picamera2  # noqa: PLC0415
        _picam2 = Picamera2()
        stream_size = (Config.PICAMERA_STREAM_WIDTH, Config.PICAMERA_STREAM_HEIGHT)
        config = _picam2.create_preview_configuration(
            main={"size": stream_size, "format": "BGR888"},
        )
        _picam2.configure(config)
        _picam2.start()
    return _picam2


def _picamera_capture() -> np.ndarray:
    with _picam2_lock:
        picam2 = _get_picamera()
        # Snapshot AWB/exposition du preview pour éviter la teinte bleue au switch
        metadata = picam2.capture_metadata()
        controls = {
            "AeEnable": False,
            "ExposureTime": metadata["ExposureTime"],
            "AnalogueGain": metadata["AnalogueGain"],
        }
        if "ColourGains" in metadata:
            controls["AwbEnable"] = False
            controls["ColourGains"] = metadata["ColourGains"]

        capture_size = (Config.PICAMERA_CAPTURE_WIDTH, Config.PICAMERA_CAPTURE_HEIGHT)
        still_config = picam2.create_still_configuration(
            main={"size": capture_size, "format": "BGR888"},
        )
        picam2.set_controls(controls)
        # Bascule en mode still, capture, revient au preview automatiquement
        frame = picam2.switch_mode_and_capture_array(still_config, "main")
        return frame  # BGR888 → directement utilisable par OpenCV, pas de conversion


def _picamera_stream(orientation: str = "portrait", mask_path: str = None):
    while True:
        with _picam2_lock:
            picam2 = _get_picamera()
            frame = picam2.capture_array("main")  # BGR888 — pas de conversion
        frame = crop_to_orientation(frame, orientation)
        if mask_path:
            frame = apply_mask(frame, mask_path)
        _, buf = cv2.imencode(".jpg", frame)
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
