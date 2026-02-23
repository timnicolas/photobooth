import os
from api.app import create_app
from api.config import Config

app = create_app()

if __name__ == "__main__":
    os.makedirs(Config.PHOTOS_DIR, exist_ok=True)
    os.makedirs(Config.MASKS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    app.run(host="0.0.0.0", port=Config.API_PORT, debug=True)
