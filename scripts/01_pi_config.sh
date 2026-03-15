#!/usr/bin/env bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}  [01]${NC} $1"; }
ok()  { echo -e "${GREEN}  [OK]${NC} $1"; }
skip(){ echo -e "${YELLOW}  [--]${NC} $1 (déjà installé, ignoré)"; }

log "=== Configuration du Raspberry Pi ==="

# --- Packages système via apt ---

APT_PACKAGES=(vim git tmux zsh network-manager python3-dev libcups2-dev)

log "Mise à jour des paquets apt..."
sudo apt-get update -qq

for pkg in "${APT_PACKAGES[@]}"; do
    if dpkg -s "$pkg" &>/dev/null 2>&1; then
        skip "$pkg"
    else
        log "Installation de $pkg..."
        sudo apt-get install -y "$pkg"
        ok "$pkg installé"
    fi
done

# --- Node.js LTS 20.x via NodeSource ---

if command -v node &>/dev/null; then
    skip "node ($(node --version))"
else
    log "Installation de Node.js LTS 20.x..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    ok "node $(node --version) installé"
fi

# --- picamera2 ---

if dpkg -s python3-picamera2 &>/dev/null 2>&1; then
    skip "python3-picamera2"
else
    log "Installation de picamera2..."
    sudo apt-get install -y python3-picamera2
    ok "picamera2 installé"
fi

# --- Oh My Zsh ---

if [ -d "$HOME/.oh-my-zsh" ]; then
    skip "oh-my-zsh"
else
    log "Installation de oh-my-zsh..."
    RUNZSH=no CHSH=no sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

    # Désactiver les mises à jour automatiques
    if ! grep -q 'DISABLE_AUTO_UPDATE' "$HOME/.zshrc" 2>/dev/null; then
        echo 'DISABLE_AUTO_UPDATE="true"' >> "$HOME/.zshrc"
    fi
    ok "oh-my-zsh installé"
fi

ok "=== Configuration Pi terminée ==="
