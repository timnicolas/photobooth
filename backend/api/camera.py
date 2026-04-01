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
    """Générateur de frames MJPEG. Pour picamera, flux hardware brut (pas de crop/masque).
    Pour la caméra intégrée, crop et masque sont appliqués par frame."""
    if Config.CAMERA_TYPE == "picamera":
        yield from _picamera_stream()
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
# Architecture double flux (main + lores) sans changement de mode :
#   - main (2304×1296 RGB888)  → capture photo via captured_request()
#   - lores (640×480 YUV420)   → encodeur MJPEG hardware → StreamingOutput
#
# Pas de thread maison, pas de lock : picamera2 gère ses propres threads internes.
# ---------------------------------------------------------------------------
import io
from threading import Condition, Lock

_picam2 = None
_stream_output = None
_picam2_init_lock = Lock()


class StreamingOutput(io.BufferedIOBase):
    """Buffer partagé entre l'encodeur MJPEG hardware et les clients Flask."""

    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


def _get_picamera():
    """Retourne l'instance Picamera2 singleton, en la créant si nécessaire."""
    global _picam2, _stream_output
    if _picam2 is not None:
        return _picam2
    with _picam2_init_lock:
        if _picam2 is not None:  # un autre thread a pu initialiser pendant l'attente du lock
            return _picam2
        from picamera2 import Picamera2  # noqa: PLC0415
        from picamera2.encoders import MJPEGEncoder  # noqa: PLC0415
        from picamera2.outputs import FileOutput  # noqa: PLC0415

        _picam2 = Picamera2()
        config = _picam2.create_video_configuration(
            main={"size": (Config.PICAMERA_MAIN_WIDTH, Config.PICAMERA_MAIN_HEIGHT), "format": "RGB888"},
            lores={"size": (Config.PICAMERA_LORES_WIDTH, Config.PICAMERA_LORES_HEIGHT), "format": "YUV420"},
            buffer_count=4,
            controls={"FrameRate": Config.PICAMERA_STREAM_FPS, "AfMode": 2, "AfSpeed": 1},
        )
        _picam2.configure(config)
        _picam2.start()
        _stream_output = StreamingOutput()
        encoder = MJPEGEncoder(bitrate=Config.PICAMERA_STREAM_BITRATE)
        _picam2.start_encoder(encoder, FileOutput(_stream_output), name="lores")
    return _picam2


def _picamera_capture() -> np.ndarray:
    picam2 = _get_picamera()
    with picam2.captured_request() as request:
        array = request.make_array("main")
    return cv2.cvtColor(array, cv2.COLOR_RGB2BGR)


def _picamera_stream():
    _get_picamera()  # s'assure que la caméra et l'encodeur sont démarrés
    while True:
        with _stream_output.condition:
            _stream_output.condition.wait()
            frame = _stream_output.frame
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
