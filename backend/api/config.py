import os


class Config:
    API_PORT = int(os.environ.get("API_PORT", 2027))
    SECRET_KEY = os.environ.get("SECRET_KEY", "photobooth-secret-change-in-prod")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "photobooth-jwt-change-in-prod")
    JWT_ACCESS_TOKEN_EXPIRES = False
    DATA_DIR = os.environ.get("DATA_DIR", "../data")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(DATA_DIR, "photobooth.db"))
    # Type de caméra : "integrated" (USB/OpenCV, défaut) ou "picamera" (Raspberry Pi)
    CAMERA_TYPE = os.environ.get("CAMERA_TYPE", "picamera")
    # Index de la caméra (0 = première caméra USB détectée, ignoré pour picamera)
    CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", 0))
    # Résolution du flux live picamera (lores, YUV420)
    PICAMERA_STREAM_WIDTH = int(os.environ.get("PICAMERA_STREAM_WIDTH", 1280))
    PICAMERA_STREAM_HEIGHT = int(os.environ.get("PICAMERA_STREAM_HEIGHT", 720))
    # Résolution de capture photo picamera (main, RGB888) — 2592×1944 fonctionne sur v1/v2/HQ
    PICAMERA_CAPTURE_WIDTH = int(os.environ.get("PICAMERA_CAPTURE_WIDTH", 4608))
    PICAMERA_CAPTURE_HEIGHT = int(os.environ.get("PICAMERA_CAPTURE_HEIGHT", 2592))
    # Dossier où les photos capturées sont sauvegardées
    PHOTOS_DIR = os.environ.get("PHOTOS_DIR", os.path.join(DATA_DIR, "photos"))
    # Dossier où les masques PNG sont stockés
    MASKS_DIR = os.environ.get("MASKS_DIR", os.path.join(DATA_DIR, "masks"))
    # Nom exact de l'imprimante dans CUPS
    PRINTER_NAME = os.environ.get("PRINTER_NAME", "Canon_SELPHY_CP1500")
    # Nombre de photos par page dans la galerie
    PHOTO_PAGE_SIZE = int(os.environ.get("PHOTO_PAGE_SIZE", 30))
    # Format papier en millimètres (89×119 = carte postale Canon SELPHY)
    PHOTO_WIDTH_MM = int(os.environ.get("PHOTO_WIDTH_MM", 89))
    PHOTO_HEIGHT_MM = int(os.environ.get("PHOTO_HEIGHT_MM", 119))
