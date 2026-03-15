import argparse
import os
from api.app import create_app
from api.config import Config

app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Photobooth backend")
    parser.add_argument("--debug", action="store_true", help="Lancer en mode debug")
    args = parser.parse_args()

    os.makedirs(Config.PHOTOS_DIR, exist_ok=True)
    os.makedirs(Config.MASKS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    app.run(host="0.0.0.0", port=Config.API_PORT, debug=args.debug)
