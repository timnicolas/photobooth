import os


class Config:
    API_PORT = int(os.environ.get("API_PORT", 2022))
    SECRET_KEY = os.environ.get("SECRET_KEY", "photobooth-secret-change-in-prod")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "photobooth-jwt-change-in-prod")
    DATA_DIR = os.environ.get("DATA_DIR", "../data")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(DATA_DIR, "photobooth.db"))
    # Type de caméra : "integrated" (USB/OpenCV, défaut) ou "picamera" (Raspberry Pi)
    CAMERA_TYPE = os.environ.get("CAMERA_TYPE", "integrated")
    # Index de la caméra (0 = première caméra USB détectée, ignoré pour picamera)
    CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", 0))
    # Dossier où les photos capturées sont sauvegardées
    PHOTOS_DIR = os.environ.get("PHOTOS_DIR", os.path.join(DATA_DIR, "photos"))
    # Dossier où les masques PNG sont stockés
    MASKS_DIR = os.environ.get("MASKS_DIR", os.path.join(DATA_DIR, "masks"))
    # Nom exact de l'imprimante dans CUPS
    PRINTER_NAME = os.environ.get("PRINTER_NAME", "Canon_SELPHY_CP1500")
