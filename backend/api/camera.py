"""Abstraction caméra — sélectionne l'implémentation selon Config.CAMERA_TYPE.

Valeurs supportées :
  "integrated"  — caméra USB/intégrée via OpenCV (défaut, dev sur ordi)
  "picamera"    — Raspberry Pi Camera via picamera2
"""
import concurrent.futures
import io
import logging
import os
import threading
import time

import cv2
import numpy as np

from api.config import Config

logger = logging.getLogger(__name__)


def _max_resolution_factor(orientation: str) -> int:
    """Calcule le facteur maximum sans upscaling pour l'orientation donnée.

    Simule le crop sur la résolution main du capteur, puis cherche le plus grand k tel que
    (w_mm×k, h_mm×k) ≤ dimensions du crop.
    """
    main_w, main_h = Config.PICAMERA_MAIN_WIDTH, Config.PICAMERA_MAIN_HEIGHT
    w_mm, h_mm = Config.PHOTO_WIDTH_MM, Config.PHOTO_HEIGHT_MM
    if orientation == "landscape":
        w_mm, h_mm = h_mm, w_mm
    target_ratio = w_mm / h_mm
    frame_ratio = main_w / main_h
    if frame_ratio > target_ratio:
        crop_w, crop_h = int(main_h * target_ratio), main_h
    else:
        crop_w, crop_h = main_w, int(main_w / target_ratio)
    return min(crop_w // w_mm, crop_h // h_mm)


def _photo_output_size(orientation: str) -> tuple[int, int]:
    """Retourne (width, height) en pixels de la sortie finale pour l'orientation donnée.

    Les dimensions sont des multiples exacts des dimensions papier en mm, garantissant
    un ratio pixel-perfect sans erreur d'arrondi.
    Si PHOTO_RESOLUTION_FACTOR == "max", utilise la résolution native du capteur sans upscaling.
    """
    k = Config.PHOTO_RESOLUTION_FACTOR
    if k == "max":
        k = _max_resolution_factor(orientation)
    w_mm, h_mm = Config.PHOTO_WIDTH_MM, Config.PHOTO_HEIGHT_MM
    if orientation == "landscape":
        return (h_mm * k, w_mm * k)
    return (w_mm * k, h_mm * k)


def crop_to_orientation(frame: np.ndarray, orientation: str) -> np.ndarray:
    """Centre-crop la frame pour correspondre au ratio du format photo configuré.

    En portrait  : ratio = PHOTO_WIDTH_MM  / PHOTO_HEIGHT_MM  (ex. 100/148 ≈ 0.676)
    En paysage   : ratio = PHOTO_HEIGHT_MM / PHOTO_WIDTH_MM   (ex. 148/100 = 1.480)
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
    """Capture une frame, crop selon l'orientation, resize à la résolution de sortie exacte."""
    if Config.CAMERA_TYPE == "picamera":
        frame = _picamera_capture()
    else:
        frame = _integrated_capture()
    cropped = crop_to_orientation(frame, orientation)
    out_w, out_h = _photo_output_size(orientation)
    return cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)


def ensure_camera_ready():
    """Ouvre la caméra si nécessaire. Lève RuntimeError si elle est indisponible.

    Appelé avant de démarrer une réponse en streaming : une fois les headers envoyés,
    on ne peut plus renvoyer de code d'erreur HTTP au client.
    """
    if Config.CAMERA_TYPE == "picamera":
        _get_picamera()


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
        if Config.CAMERA_MIRROR:
            frame = cv2.flip(frame, 1)
        return frame
    finally:
        cap.release()


def _integrated_stream(orientation: str = "portrait", mask_path: str = None):
    cap = cv2.VideoCapture(Config.CAMERA_INDEX)
    try:
        if not cap.isOpened():
            logger.warning("Integrated camera %s could not be opened", Config.CAMERA_INDEX)
            return
        while True:
            success, frame = cap.read()
            if not success:
                break
            if Config.CAMERA_MIRROR:
                frame = cv2.flip(frame, 1)
            frame = crop_to_orientation(frame, orientation)
            if mask_path:
                frame = apply_mask(frame, mask_path)
            ok, buf = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
    finally:
        cap.release()


# ---------------------------------------------------------------------------
# PiCamera2 — Raspberry Pi
# picamera2 est importé en lazy pour ne pas bloquer le démarrage sur ordi de dev
#
# Architecture double flux (main + lores) sans changement de mode :
#   - main (2304×1296 RGB888)  → capture photo via capture_request()
#   - lores (640×480 YUV420)   → encodeur MJPEG hardware → StreamingOutput
#
# Résilience (l'app doit tenir des heures sans restart) :
#   - l'init est atomique : en cas d'échec la caméra est fermée et rien n'est mémorisé,
#     la tentative suivante repart de zéro ;
#   - un thread watchdog surveille l'arrivée des frames : si l'encodeur ne produit plus
#     rien pendant PICAMERA_STALL_TIMEOUT, la caméra est fermée puis ré-ouverte à la
#     prochaine demande (flux ou capture) ;
#   - si libcamera est bloqué au point que la fermeture elle-même ne rend pas la main,
#     ou si les resets s'enchaînent sans succès, le process se termine et systemd le
#     relance (Restart=always) — dernier recours plutôt qu'une caméra morte pour la soirée.
# ---------------------------------------------------------------------------

_picam2 = None
_stream_output = None
# RLock : _reset_picamera peut être appelé alors que le lock est déjà détenu par le même thread
_picam2_lock = threading.RLock()
_last_init_failure = 0.0
_watchdog_thread = None


class StreamingOutput(io.BufferedIOBase):
    """Buffer partagé entre l'encodeur MJPEG hardware et les clients Flask."""

    def __init__(self):
        self.frame = None
        self.seq = 0  # incrémenté à chaque frame : permet aux clients de ne jamais renvoyer deux fois la même
        self.last_write = time.monotonic()
        self.condition = threading.Condition()

    def write(self, buf):
        if not buf:
            return 0
        with self.condition:
            self.frame = bytes(buf)
            self.seq += 1
            self.last_write = time.monotonic()
            self.condition.notify_all()
        return len(buf)


def _fatal(reason: str):
    """Dernier recours : termine le process pour que systemd le relance proprement."""
    logger.critical("Camera unrecoverable (%s)", reason)
    if Config.PICAMERA_EXIT_ON_HANG:
        logger.critical("Exiting process so that systemd restarts the backend")
        os._exit(1)


def _close_camera(cam):
    """Arrête l'encodeur, la caméra et libère le device. Chaque étape est best-effort."""
    for step in ("stop_encoder", "stop", "close"):
        try:
            getattr(cam, step)()
        except Exception:  # noqa: BLE001 — une étape qui échoue ne doit pas empêcher les suivantes
            logger.warning("Camera %s() failed during close", step, exc_info=True)


def _close_camera_with_timeout(cam, timeout: float) -> bool:
    """Ferme la caméra dans un thread séparé ; retourne False si la fermeture est bloquée."""
    t = threading.Thread(target=_close_camera, args=(cam,), name="picamera-close", daemon=True)
    t.start()
    t.join(timeout)
    return not t.is_alive()


def _reset_picamera(reason: str, expected_cam=None):
    """Ferme la caméra courante ; elle sera ré-ouverte à la prochaine demande.

    expected_cam : ne reset que si la caméra courante est toujours celle-ci (évite qu'un
    appelant en retard ne ferme une caméra fraîchement ré-initialisée par un autre thread).
    """
    global _picam2, _stream_output
    with _picam2_lock:
        cam = _picam2
        if cam is None or (expected_cam is not None and cam is not expected_cam):
            return
        logger.warning("Resetting camera: %s", reason)
        _picam2 = None
        _stream_output = None
        # Fermeture sous le lock : une ré-init concurrente avant la libération du device
        # échouerait en "device busy".
        if not _close_camera_with_timeout(cam, Config.PICAMERA_CLOSE_TIMEOUT):
            _fatal("camera close hung")


def _watchdog_loop():
    """Redémarre la caméra si l'encodeur MJPEG ne produit plus de frames."""
    consecutive_resets = 0
    while True:
        time.sleep(1.0)
        try:
            cam, output = _picam2, _stream_output
            if cam is None or output is None:
                continue
            age = time.monotonic() - output.last_write
            if age < Config.PICAMERA_STALL_TIMEOUT:
                if output.seq > 0:
                    consecutive_resets = 0  # la caméra (ré)ouverte produit bien des frames
                continue
            consecutive_resets += 1
            if consecutive_resets > Config.PICAMERA_MAX_CONSECUTIVE_RESETS:
                _fatal(f"{consecutive_resets - 1} consecutive resets without any frame")
            _reset_picamera(f"no frame for {age:.1f}s", expected_cam=cam)
        except Exception:  # noqa: BLE001 — le watchdog ne doit jamais mourir
            logger.exception("Camera watchdog iteration failed")


def _ensure_watchdog():
    global _watchdog_thread
    if _watchdog_thread is None or not _watchdog_thread.is_alive():
        _watchdog_thread = threading.Thread(target=_watchdog_loop, name="picamera-watchdog", daemon=True)
        _watchdog_thread.start()


def _get_picamera():
    """Retourne l'instance Picamera2 singleton, en la créant si nécessaire.

    Lève RuntimeError si la caméra ne peut pas être ouverte.
    """
    global _picam2, _stream_output, _last_init_failure
    cam = _picam2
    if cam is not None:
        return cam
    with _picam2_lock:
        if _picam2 is not None:  # un autre thread a pu initialiser pendant l'attente du lock
            return _picam2
        # Limite le rythme des tentatives quand la caméra est absente (chaque client qui
        # se reconnecte déclencherait sinon une ouverture complète).
        if time.monotonic() - _last_init_failure < Config.PICAMERA_INIT_RETRY_DELAY:
            raise RuntimeError("Caméra indisponible, nouvelle tentative dans quelques secondes")

        cam = None
        try:
            from libcamera import Transform  # noqa: PLC0415
            from picamera2 import Picamera2  # noqa: PLC0415
            from picamera2.encoders import MJPEGEncoder  # noqa: PLC0415
            from picamera2.outputs import FileOutput  # noqa: PLC0415

            cam = Picamera2()
            controls = {
                "FrameRate": Config.PICAMERA_STREAM_FPS,
                "AfMode": 2,
                "AfSpeed": 1,
                "AwbEnable": Config.PICAMERA_COLOUR_GAINS is None,
                "AeEnable": Config.PICAMERA_EXPOSURE_TIME is None,
                "NoiseReductionMode": Config.PICAMERA_NOISE_REDUCTION,
                "Sharpness": Config.PICAMERA_SHARPNESS,
                "Contrast": Config.PICAMERA_CONTRAST,
                "Saturation": Config.PICAMERA_SATURATION,

                "HdrMode": 0,
            }
            if Config.PICAMERA_EXPOSURE_TIME is not None:
                controls["ExposureTime"] = Config.PICAMERA_EXPOSURE_TIME
            if Config.PICAMERA_ANALOGUE_GAIN is not None:
                controls["AnalogueGain"] = Config.PICAMERA_ANALOGUE_GAIN
            if Config.PICAMERA_COLOUR_GAINS is not None:
                controls["ColourGains"] = Config.PICAMERA_COLOUR_GAINS
            config = cam.create_video_configuration(
                main={"size": (Config.PICAMERA_MAIN_WIDTH, Config.PICAMERA_MAIN_HEIGHT), "format": "RGB888"},
                lores={"size": (Config.PICAMERA_LORES_WIDTH, Config.PICAMERA_LORES_HEIGHT), "format": "YUV420"},
                buffer_count=4,
                controls=controls,
                transform=Transform(hflip=Config.CAMERA_MIRROR),
            )
            cam.configure(config)
            cam.start()
            output = StreamingOutput()
            encoder = MJPEGEncoder(bitrate=Config.PICAMERA_STREAM_BITRATE)
            cam.start_encoder(encoder, FileOutput(output), name="lores")
        except Exception as e:
            _last_init_failure = time.monotonic()
            logger.exception("Camera initialisation failed")
            if cam is not None:
                # Libère le device, sinon la prochaine tentative échouera en "device busy"
                if not _close_camera_with_timeout(cam, Config.PICAMERA_CLOSE_TIMEOUT):
                    _fatal("camera close hung after failed init")
            raise RuntimeError(f"Caméra indisponible : {e}") from e

        # Publication uniquement une fois la caméra entièrement démarrée
        _stream_output = output
        _picam2 = cam
        logger.info("Camera started")
        _ensure_watchdog()
        return cam


def _picamera_capture() -> np.ndarray:
    picam2 = _get_picamera()
    time.sleep(Config.PICAMERA_CAPTURE_DELAY)
    try:
        job = picam2.capture_request(wait=False)
        try:
            request = job.get_result(timeout=Config.PICAMERA_CAPTURE_TIMEOUT)
        except TypeError:  # anciennes versions de picamera2 : pas de timeout possible
            request = job.get_result()
    except (TimeoutError, concurrent.futures.TimeoutError) as e:
        _reset_picamera("capture timed out", expected_cam=picam2)
        raise RuntimeError("La caméra ne répond pas, réessayez") from e
    except Exception as e:
        _reset_picamera(f"capture failed: {e}", expected_cam=picam2)
        raise RuntimeError(f"Erreur caméra : {e}") from e
    try:
        # picamera2 RGB888 stocke les bytes en ordre BGR (convention libcamera) → pas de conversion
        return request.make_array("main")
    finally:
        request.release()


def _picamera_stream():
    _get_picamera()  # s'assure que la caméra et l'encodeur sont démarrés
    output = _stream_output
    if output is None:  # reset concurrent entre l'init et ici
        return
    last_seq = -1

    def has_new_frame():
        return output.frame is not None and output.seq != last_seq

    while True:
        with output.condition:
            ok = output.condition.wait_for(has_new_frame, timeout=Config.PICAMERA_STALL_TIMEOUT)
            frame, seq = output.frame, output.seq
        # Plus de frame (encodeur bloqué) ou caméra ré-initialisée : on termine la réponse.
        # Sans yield, Werkzeug ne verrait jamais la déconnexion du client et le thread
        # resterait bloqué ici ; le client se reconnecte et récupère la nouvelle caméra.
        if not ok or output is not _stream_output:
            return
        last_seq = seq
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
