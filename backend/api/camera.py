"""Abstraction caméra — sélectionne l'implémentation selon Config.CAMERA_TYPE.

Valeurs supportées :
  "integrated"  — caméra USB/intégrée via OpenCV (défaut, dev sur ordi)
  "picamera"    — Raspberry Pi Camera via picamera2
"""
import cv2
import numpy as np

from api.config import Config


def capture_frame() -> np.ndarray:
    """Capture une frame et retourne un array numpy BGR."""
    if Config.CAMERA_TYPE == "picamera":
        return _picamera_capture()
    return _integrated_capture()


def mjpeg_frames():
    """Générateur de frames MJPEG (multipart/x-mixed-replace)."""
    if Config.CAMERA_TYPE == "picamera":
        yield from _picamera_stream()
    else:
        yield from _integrated_stream()


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


def _integrated_stream():
    cap = cv2.VideoCapture(Config.CAMERA_INDEX)
    try:
        while True:
            success, frame = cap.read()
            if not success:
                break
            _, buf = cv2.imencode(".jpg", frame)
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
    finally:
        cap.release()


# ---------------------------------------------------------------------------
# PiCamera2 — Raspberry Pi
# picamera2 est importé en lazy pour ne pas bloquer le démarrage sur ordi de dev
# ---------------------------------------------------------------------------

def _picamera_capture() -> np.ndarray:
    from picamera2 import Picamera2  # noqa: PLC0415

    picam2 = Picamera2()
    try:
        picam2.configure(picam2.create_still_configuration())
        picam2.start()
        frame = picam2.capture_array()  # RGB
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    finally:
        picam2.stop()
        picam2.close()


def _picamera_stream():
    from picamera2 import Picamera2  # noqa: PLC0415

    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"size": (1280, 720)}))
    picam2.start()
    try:
        while True:
            frame = picam2.capture_array()  # RGB
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            _, buf = cv2.imencode(".jpg", frame_bgr)
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
    finally:
        picam2.stop()
        picam2.close()
