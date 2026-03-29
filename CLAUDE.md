# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Raspberry Pi-based photobooth application with a French UI. A Flask REST API (port 2027) serves a Vue 3 + Vite + Vuetify SPA (port 2022). Photos are captured via Raspberry Pi Camera (`picamera2`) or USB camera (OpenCV), optionally composited with PNG mask overlays, and printed via a Canon SELPHY CP1500 through CUPS.

## Running the Application

```bash
# Backend
source ~/photobooth-venv/bin/activate
cd backend
python run.py

# Frontend (separate terminal)
cd frontend
npm run dev
```

Systemd services manage auto-start on boot:
```bash
sudo systemctl status photobooth-backend
sudo systemctl status photobooth-frontend
# Logs at ~/photobooth-backend.log and ~/photobooth-frontend.log
```

## Building

```bash
cd frontend
npm run build     # outputs to dist/
npm run preview   # preview built version
```

## Key Configuration

Backend is configured via environment variables (see `backend/api/config.py`):
- `CAMERA_TYPE`: `"picamera"` (RPi camera) or `"integrated"` (USB/OpenCV)
- `CAMERA_INDEX`: USB camera index (default: 0)
- `PRINTER_NAME`: CUPS printer name
- `PHOTOS_DIR` / `MASKS_DIR`: storage paths (default: `data/photos/`, `data/masks/`)
- `API_PORT`: default 2027

Frontend proxies `/api/*` to `http://localhost:2027` via Vite config.

WiFi hotspot: SSID `PhotoBooth`, password `photobooth`, IP `10.4.4.12`.

## Architecture

### Backend (`backend/api/`)

- **`app.py`** — Flask app factory; registers all route blueprints
- **`config.py`** — Centralised config via env vars
- **`models.py`** — Peewee ORM over SQLite (`data/photobooth.db`): `User`, `Photo`, `Mask`, `AppSettings`
- **`camera.py`** — Camera abstraction with singleton for picamera2 (prevents "device busy" errors); handles orientation-aware cropping and alpha-composite mask overlay (Porter-Duff)
- **`printer.py`** — pycups wrapper for Canon SELPHY; handles print options, status reporting, and error states
- **`decorators.py`** — `@jwt_required` and `@admin_required` route guards

Routes in `backend/api/routes/`: `auth`, `camera`, `photos`, `masks`, `printer`, `settings`.

Photos are stored twice: a masked composite and a raw version for re-printing without the mask.

### Frontend (`frontend/src/`)

- **`api/client.js`** — Axios instance; attaches JWT from `localStorage` to every request
- **`stores/`** — Pinia: `auth.js` (token, admin flag), `masks.js` (active mask), `settings.js`
- **`views/`** — 4 routes: `PhotoboothView` (live MJPEG stream + capture), `GalleryView` (paginated grid, batch ops), `LoginView`, `AdminView` (mask management, settings)
- Camera stream is a raw `<img>` pointed at `/api/camera/stream?orientation=...&mask_id=...`

### Installation

```bash
bash scripts/setup.sh        # full automated install
python backend/create_user.py  # create first admin user (run after setup)
```

## Python Dependencies

Managed in `backend/requirements.txt`. `picamera2` is installed system-wide by the setup script (not via pip). The venv lives at `~/photobooth-venv/`.

```bash
source ~/photobooth-venv/bin/activate
pip install -r backend/requirements.txt
```

## API Summary

All endpoints under `/api`. Auth via `Authorization: Bearer <token>`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/login` | Authenticate, returns JWT |
| GET | `/camera/stream` | MJPEG stream (`orientation`, `mask_id` params) |
| POST | `/camera/capture` | Capture photo (`print`, `orientation` params) |
| GET | `/photos` | List photos (paginated) |
| POST | `/photos/<id>/print` | Print a photo |
| GET/POST | `/masks` | List / upload masks |
| PUT | `/masks/<id>/select` | Set active mask |
| GET | `/printer/status` | Printer state |
| GET/PUT | `/settings` | App settings |

Swagger UI available at `http://localhost:2027/docs`.
