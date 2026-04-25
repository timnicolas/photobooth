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
    # Miroir horizontal : True = flip gauche/droite (mode selfie), False = image naturelle
    CAMERA_MIRROR = os.environ.get("CAMERA_MIRROR", "true").lower() in ("1", "true", "yes")
    # Format papier en millimètres (100×148 = carte postale Canon SELPHY CP1500, pleine surface)
    # Défini en premier car utilisé pour calculer les dimensions caméra ci-dessous
    PHOTO_WIDTH_MM = int(os.environ.get("PHOTO_WIDTH_MM", 100))
    PHOTO_HEIGHT_MM = int(os.environ.get("PHOTO_HEIGHT_MM", 148))
    # Facteur de résolution de sortie des photos : dimension en px = mm × facteur
    # "max" = calcule automatiquement le facteur maximum sans upscaling selon l'orientation et la résolution capteur
    # facteur=12 → 100×148mm = 1200×1776px (ratio exact 100:148, ≈ 304 DPI pour une carte postale)
    _factor = os.environ.get("PHOTO_RESOLUTION_FACTOR", "max")
    PHOTO_RESOLUTION_FACTOR: "int | str" = _factor if _factor == "max" else int(_factor)
    # Résolution flux main (capture photo) — plein capteur IMX708 (4608×2592)
    # La hauteur suit le ratio natif 16:9 du capteur IMX708 si non surchargée.
    # Pour le module HQ (IMX477) : PICAMERA_MAIN_WIDTH=4056 PICAMERA_MAIN_HEIGHT=3040
    PICAMERA_MAIN_WIDTH = int(os.environ.get("PICAMERA_MAIN_WIDTH", 4608))
    _main_h = os.environ.get("PICAMERA_MAIN_HEIGHT")
    PICAMERA_MAIN_HEIGHT = int(_main_h) if _main_h else round(PICAMERA_MAIN_WIDTH * 9 / 16)
    # Résolution flux lores (stream MJPEG hardware preview)
    # Le lores DOIT avoir le même ratio 16:9 que le main (contrainte ISP picamera2) ;
    # utiliser un ratio différent provoque une distorsion dans les frames encodées.
    # C'est le CSS (object-fit: cover + aspect-ratio) qui recadre visuellement au ratio d'impression.
    PICAMERA_LORES_WIDTH = int(os.environ.get("PICAMERA_LORES_WIDTH", 640))
    PICAMERA_LORES_HEIGHT = round(PICAMERA_LORES_WIDTH * 9 / 16)  # 640 → 360 (ratio capteur 16:9)
    # Framerate et bitrate de l'encodeur MJPEG hardware
    PICAMERA_STREAM_FPS = int(os.environ.get("PICAMERA_STREAM_FPS", 30))
    PICAMERA_STREAM_BITRATE = int(os.environ.get("PICAMERA_STREAM_BITRATE", 5_000_000))
    # Qualité image — contrôles ISP picamera2
    PICAMERA_CAPTURE_DELAY = float(os.environ.get("PICAMERA_CAPTURE_DELAY", 0.5))
    PICAMERA_NOISE_REDUCTION = int(os.environ.get("PICAMERA_NOISE_REDUCTION", 2))
    PICAMERA_SHARPNESS = float(os.environ.get("PICAMERA_SHARPNESS", 1.5))
    PICAMERA_CONTRAST = float(os.environ.get("PICAMERA_CONTRAST", 1.15))
    PICAMERA_SATURATION = float(os.environ.get("PICAMERA_SATURATION", 1.05))
    # Exposition fixe (µs) — None = auto AE
    _exp = os.environ.get("PICAMERA_EXPOSURE_TIME")
    PICAMERA_EXPOSURE_TIME = int(_exp) if _exp else None
    _gain = os.environ.get("PICAMERA_ANALOGUE_GAIN")
    PICAMERA_ANALOGUE_GAIN = float(_gain) if _gain else None
    # Balance des blancs fixe — None = auto AWB ; format "R,B" ex. "1.5,1.5"
    _awb = os.environ.get("PICAMERA_COLOUR_GAINS")
    PICAMERA_COLOUR_GAINS = tuple(float(x) for x in _awb.split(",")) if _awb else None
    # Qualité JPEG des photos sauvegardées (0-100)
    PHOTO_JPEG_QUALITY = int(os.environ.get("PHOTO_JPEG_QUALITY", 95))
    # Dossier où les photos capturées sont sauvegardées
    PHOTOS_DIR = os.environ.get("PHOTOS_DIR", os.path.join(DATA_DIR, "photos"))
    # Dossier où les masques PNG sont stockés
    MASKS_DIR = os.environ.get("MASKS_DIR", os.path.join(DATA_DIR, "masks"))
    # Nom exact de l'imprimante dans CUPS
    # Canon_SELPHY_CP1500_WiFi = connexion IPP WiFi (recommandée, remonte les erreurs hardware)
    # Canon_SELPHY_CP1500      = connexion USB via Gutenprint (fallback)
    PRINTER_NAME = os.environ.get("PRINTER_NAME", "Canon_SELPHY_CP1500_WiFi")
    # IP WiFi de la Selphy pour requêtes IPP directes (bypass cache CUPS)
    # Laisser vide pour désactiver et utiliser uniquement CUPS
    PRINTER_WIFI_IP = os.environ.get("PRINTER_WIFI_IP", "10.4.4.32")
    # Nombre de photos par page dans la galerie
    PHOTO_PAGE_SIZE = int(os.environ.get("PHOTO_PAGE_SIZE", 30))
