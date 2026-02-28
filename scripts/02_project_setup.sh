#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}  [02]${NC} $1"; }
ok()  { echo -e "${GREEN}  [OK]${NC} $1"; }
skip(){ echo -e "${YELLOW}  [--]${NC} $1 (déjà fait, ignoré)"; }

log "=== Configuration du projet photobooth ==="
log "Répertoire du projet : $PROJECT_ROOT"

# --- Venv Python ---

VENV_DIR="$PROJECT_ROOT/photobooth-venv"

if [ -d "$VENV_DIR" ]; then
    skip "venv Python ($VENV_DIR)"
else
    log "Création du venv Python (avec --system-site-packages pour picamera2)..."
    python3 -m venv --system-site-packages "$VENV_DIR"
    ok "Venv créé"
fi

# --- Dépendances Python ---

log "Installation des dépendances Python..."
"$VENV_DIR/bin/pip" install --quiet -r "$PROJECT_ROOT/backend/requirements.txt"
ok "Dépendances Python installées"

# --- Dépendances Node ---

if [ -d "$PROJECT_ROOT/frontend/node_modules" ]; then
    skip "node_modules frontend"
else
    log "Installation des dépendances Node.js..."
    npm --prefix "$PROJECT_ROOT/frontend" install
    ok "Dépendances Node installées"
fi

# --- Services systemd ---

BACKEND_SERVICE="/etc/systemd/system/photobooth-backend.service"
FRONTEND_SERVICE="/etc/systemd/system/photobooth-frontend.service"

if [ -f "$BACKEND_SERVICE" ]; then
    skip "service photobooth-backend"
else
    log "Création du service photobooth-backend..."
    sudo tee "$BACKEND_SERVICE" > /dev/null <<EOF
[Unit]
Description=Photobooth Backend (Flask)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_ROOT/backend
ExecStart=$VENV_DIR/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    ok "Service photobooth-backend créé"
fi

if [ -f "$FRONTEND_SERVICE" ]; then
    skip "service photobooth-frontend"
else
    log "Création du service photobooth-frontend..."
    NODE_BIN="$(command -v node)"
    NPM_BIN="$(command -v npm)"
    sudo tee "$FRONTEND_SERVICE" > /dev/null <<EOF
[Unit]
Description=Photobooth Frontend (Vite)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_ROOT/frontend
ExecStart=$NPM_BIN run dev
Environment=NODE_ENV=development
Environment=PATH=$(dirname "$NODE_BIN"):/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    ok "Service photobooth-frontend créé"
fi

# --- Activation et démarrage des services ---

log "Rechargement de systemd et activation des services..."
sudo systemctl daemon-reload

for svc in photobooth-backend photobooth-frontend; do
    sudo systemctl enable "$svc"
    sudo systemctl restart "$svc"
    ok "Service $svc activé et démarré"
done

log ""
ok "=== Configuration projet terminée ==="
log "Backend  : http://localhost:2027"
log "Frontend : http://localhost:2022"
