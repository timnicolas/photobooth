#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}================================================${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}================================================${NC}"
    echo ""
}

print_step() {
    echo -e "${YELLOW}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}[OK] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERREUR] $1${NC}"
}

print_header "Installation Photobooth Raspberry Pi"

echo -e "Ce script va effectuer les étapes suivantes :"
echo -e "  ${BOLD}1.${NC} Configuration du Raspberry Pi (packages système, oh-my-zsh, picamera2)"
echo -e "  ${BOLD}2.${NC} Configuration du projet (venv Python, dépendances, services systemd)"
echo ""
echo -e "${YELLOW}Chaque étape vérifie si elle a déjà été effectuée avant de s'exécuter.${NC}"
echo ""

read -p "Appuyez sur Entrée pour continuer (Ctrl+C pour annuler)..."

# Étape 1 : Config Pi
print_step "Étape 1/2 : Configuration du Raspberry Pi"
bash "$SCRIPT_DIR/01_pi_config.sh"
print_success "Étape 1 terminée"

# Étape 2 : Projet
print_step "Étape 2/2 : Configuration du projet"
bash "$SCRIPT_DIR/02_project_setup.sh"
print_success "Étape 2 terminée"

print_header "Installation terminée !"

echo -e "Les services sont maintenant actifs et démarreront automatiquement au reboot :"
echo -e "  ${GREEN}photobooth-backend${NC}  → http://localhost:2027"
echo -e "  ${GREEN}photobooth-frontend${NC} → http://localhost:2022"
echo ""
echo -e "${YELLOW}Prochaines étapes :${NC}"
echo -e "  1. Créer un utilisateur admin :"
echo -e "     ${BOLD}cd ~/photobooth/backend && ../photobooth-venv/bin/python create_user.py${NC}"
echo -e "  2. Installer les drivers de l'imprimante CUPS"
echo -e "  3. Configurer git et votre clé SSH si nécessaire"
echo ""
