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
    # Format papier en millimètres (89×119 = carte postale Canon SELPHY)
    # Défini en premier car utilisé pour calculer les dimensions caméra ci-dessous
    PHOTO_WIDTH_MM = int(os.environ.get("PHOTO_WIDTH_MM", 89))
    PHOTO_HEIGHT_MM = int(os.environ.get("PHOTO_HEIGHT_MM", 119))
    # Facteur de résolution de sortie des photos : dimension en px = mm × facteur
    # facteur=12 → 89×119mm = 1068×1428px (ratio exact 89:119, ≈ 304 DPI pour une carte postale)
    PHOTO_RESOLUTION_FACTOR = int(os.environ.get("PHOTO_RESOLUTION_FACTOR", 12))
    # Résolution flux main (capture photo) — 2304 = demi-résolution capteur IMX708, ~30fps
    # La hauteur suit le ratio natif 16:9 du capteur IMX708 (contrainte hardware)
    PICAMERA_MAIN_WIDTH = int(os.environ.get("PICAMERA_MAIN_WIDTH", 2304))
    PICAMERA_MAIN_HEIGHT = round(PICAMERA_MAIN_WIDTH * 9 / 16)  # 2304 → 1296
    # Résolution flux lores (stream MJPEG hardware preview)
    # Le lores DOIT avoir le même ratio 16:9 que le main (contrainte ISP picamera2) ;
    # utiliser un ratio différent provoque une distorsion dans les frames encodées.
    # C'est le CSS (object-fit: cover + aspect-ratio) qui recadre visuellement au ratio d'impression.
    PICAMERA_LORES_WIDTH = int(os.environ.get("PICAMERA_LORES_WIDTH", 640))
    PICAMERA_LORES_HEIGHT = round(PICAMERA_LORES_WIDTH * 9 / 16)  # 640 → 360 (ratio capteur 16:9)
    # Framerate et bitrate de l'encodeur MJPEG hardware
    PICAMERA_STREAM_FPS = int(os.environ.get("PICAMERA_STREAM_FPS", 30))
    PICAMERA_STREAM_BITRATE = int(os.environ.get("PICAMERA_STREAM_BITRATE", 5_000_000))
    # Dossier où les photos capturées sont sauvegardées
    PHOTOS_DIR = os.environ.get("PHOTOS_DIR", os.path.join(DATA_DIR, "photos"))
    # Dossier où les masques PNG sont stockés
    MASKS_DIR = os.environ.get("MASKS_DIR", os.path.join(DATA_DIR, "masks"))
    # Nom exact de l'imprimante dans CUPS
    # Canon_SELPHY_CP1500_WiFi = connexion IPP WiFi (recommandée, remonte les erreurs hardware)
    # Canon_SELPHY_CP1500      = connexion USB via Gutenprint (fallback)
    PRINTER_NAME = os.environ.get("PRINTER_NAME", "Canon_SELPHY_CP1500_WiFi")
    # Nombre de photos par page dans la galerie
    PHOTO_PAGE_SIZE = int(os.environ.get("PHOTO_PAGE_SIZE", 30))
