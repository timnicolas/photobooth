#!/usr/bin/env bash
set -e

# ─── Configuration ────────────────────────────────────────────────────────────
SSID="PhotoBooth"
PASSWORD="photobooth"     # WPA2, min 8 caractères
WIFI_IFACE="wlan0"
AP_IP="10.4.4.12/24"
CON_NAME="PhotoBooth-AP"
# ──────────────────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${CYAN}  [AP]${NC} $1"; }
ok()  { echo -e "${GREEN}  [OK]${NC} $1"; }
skip(){ echo -e "${YELLOW}  [--]${NC} $1 (déjà configuré, ignoré)"; }
err() { echo -e "${RED}  [!!]${NC} $1" >&2; }

log "=== Configuration du point d'accès WiFi ==="

# --- NetworkManager actif ---
if ! command -v nmcli &>/dev/null; then
    err "NetworkManager (nmcli) non trouvé. Lancer d'abord scripts/setup.sh"
    exit 1
fi

if ! systemctl is-active --quiet NetworkManager; then
    log "Démarrage de NetworkManager..."
    sudo systemctl enable --now NetworkManager
    ok "NetworkManager démarré"
fi

# --- Interface WiFi disponible ---
if ! ip link show "$WIFI_IFACE" &>/dev/null 2>&1; then
    err "Interface WiFi '$WIFI_IFACE' introuvable. Interfaces disponibles :"
    ip -br link show
    exit 1
fi

# --- IP forwarding persistant (partage internet eth0 → wlan0) ---
if grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf 2>/dev/null; then
    skip "IP forwarding"
else
    log "Activation du forwarding IP (persistant)..."
    echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf > /dev/null
    sudo sysctl -p /etc/sysctl.conf > /dev/null
    ok "IP forwarding activé"
fi

# --- Création ou mise à jour de la connexion AP ---
if nmcli con show "$CON_NAME" &>/dev/null 2>&1; then
    log "Connexion '$CON_NAME' déjà présente — mise à jour..."
    nmcli con modify "$CON_NAME" \
        ssid "$SSID" \
        wifi-sec.psk "$PASSWORD" \
        ipv4.addresses "$AP_IP"
    ok "Connexion mise à jour"
else
    log "Création du point d'accès '$SSID' (IP : ${AP_IP%/*})..."
    nmcli con add \
        type wifi \
        ifname "$WIFI_IFACE" \
        con-name "$CON_NAME" \
        autoconnect yes \
        ssid "$SSID" \
        802-11-wireless.mode ap \
        802-11-wireless.band bg \
        802-11-wireless.channel 6 \
        wifi-sec.key-mgmt wpa-psk \
        wifi-sec.psk "$PASSWORD" \
        ipv4.method shared \
        ipv4.addresses "$AP_IP" \
        ipv6.method disabled
    ok "Connexion '$CON_NAME' créée"
fi

# --- Activation ---
log "Activation du point d'accès..."
nmcli con up "$CON_NAME"
ok "Point d'accès actif"

# --- Résumé ---
echo ""
ok "=== Point d'accès WiFi opérationnel ==="
echo -e "  SSID         : ${GREEN}${SSID}${NC}"
echo -e "  Mot de passe : ${GREEN}${PASSWORD}${NC}"
echo -e "  IP Raspberry : ${GREEN}${AP_IP%/*}${NC}"
echo -e "  Plage DHCP   : ${GREEN}10.4.4.0/24${NC} (géré par NetworkManager)"
echo -e "  Partage      : ${GREEN}eth0 → wlan0${NC} (si câble RJ45 branché)"
echo ""
log "Ce script peut être relancé sans risque pour reconfigurer le point d'accès."
