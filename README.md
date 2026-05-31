# photobooth
Photobooth avec raspberrypi, Canon Selphy CP1500 et interface WEB

## Principe de fonctionnement

La carte Raspberrypi emet un réseau WIFI.
- L'imprimante se connecte au réseau du Raspberry (ou en USB).
- Une interface (tablette, tel, ordi, etc.) se connecte au réseau et ouvre un page web avec l'interface

---

## Installation rapide sur Raspberry Pi

```bash
git clone https://github.com/timnicolas/photobooth.git ~/photobooth && cd ~/photobooth && bash scripts/setup.sh
```

Le script installe automatiquement :
- Les packages système (node, vim, git, tmux, zsh, network-manager, picamera2)
- Oh My Zsh
- Le venv Python et les dépendances backend
- Les dépendances Node.js du frontend
- Les services systemd `photobooth-backend` et `photobooth-frontend` (démarrage automatique au boot)

Chaque étape vérifie si elle a déjà été effectuée — le script peut être relancé sans risque.

### Point d'accès WiFi

Configurer le Raspberry Pi comme routeur WiFi (IP fixe `10.4.4.12`, partage internet via RJ45) :

```bash
sudo bash scripts/03_wifi_ap.sh
```

Ce script :
- Crée un hotspot WPA2 via NetworkManager (`SSID: PhotoBooth`, `mdp: photobooth`)
- Attribue l'IP fixe `10.4.4.12` au Raspberry Pi
- Active le partage de connexion depuis `eth0` si un câble est branché
- Peut être relancé sans risque pour reconfigurer

> Pour modifier le SSID ou le mot de passe, éditer les variables en tête de `scripts/03_wifi_ap.sh`.

### Post-installation

Créer un utilisateur admin et un utilisateur classique :
```bash
cd ~/photobooth/backend && ../photobooth-venv/bin/python create_user.py
```

Installer l'imprimante Canon SELPHY CP1500 via CUPS :

```bash
sudo apt-get install -y cups printer-driver-gutenprint
```

Par défaut, CUPS n'écoute que sur `localhost`. Pour accéder à l'interface depuis le réseau, modifier `/etc/cups/cupsd.conf` :

```diff
- Listen localhost:631
+ Port 631

  <Location />
+   Allow @LOCAL
    Order allow,deny
  </Location>

  <Location /admin>
+   Allow @LOCAL
    AuthType Default
```

Puis redémarrer CUPS :

```bash
sudo systemctl restart cups
```

#### Connexion WiFi (recommandée)

Connecter la Selphy au réseau **PhotoBooth** via son menu (Paramètres réseau → Point d'accès → `PhotoBooth` / `photobooth`). L'imprimante affiche son IP dans Menu → Infos réseau.

Pour trouver l'IP sans écran : broadcast ping puis table ARP :

```bash
ping -b -c 3 10.4.4.255; ip neigh show dev wlan0
```

Ajouter l'imprimante dans CUPS en IPP (IPP Everywhere, pas de driver propriétaire requis) :

```bash
sudo /usr/sbin/lpadmin -p Canon_SELPHY_CP1500_WiFi \
  -E \
  -v "ipp://10.4.4.XX:631/ipp/print" \
  -m everywhere \
  -D "Canon SELPHY CP1500 WiFi"

sudo /usr/sbin/lpadmin -d Canon_SELPHY_CP1500_WiFi
```

> L'avantage du WiFi sur l'USB : la Selphy expose son serveur IPP natif, ce qui permet à CUPS de lire les erreurs hardware réelles (papier, encre, capot) au lieu de les ignorer.

Pour fixer l'IP de la Selphy (éviter qu'elle change au redémarrage), créer une réservation DHCP via le dnsmasq de NetworkManager :

```bash
# MAC de la Selphy : vérifier avec `ip neigh show dev wlan0`
echo "dhcp-host=6c:f2:d8:63:3f:73,10.4.4.32" | sudo tee /etc/NetworkManager/dnsmasq-shared.d/selphy-reservation.conf

# Redémarrer le hotspot pour appliquer
sudo nmcli connection down PhotoBooth-AP && sudo nmcli connection up PhotoBooth-AP
```

#### Connexion USB (fallback)

Le CP1500 n'est pas encore supporté nativement par Gutenprint. Utiliser le driver CP1300 (compatible) :

```bash
sudo /usr/sbin/lpadmin -p Canon_SELPHY_CP1500 \
  -E \
  -v "usb://Canon/SELPHY%20CP1500?serial=XXXXXXXXXXXXXXXX" \
  -m "gutenprint.5.3://canon-cp1300/expert"
```

> Pour trouver l'URI USB exacte : `sudo lpinfo -v`

L'interface CUPS est accessible sur `http://10.4.4.12:631` pour vérifier l'état de l'imprimante.

### Configuration git (si besoin de contribuer)

```bash
git config --global user.email "votre@email.com"
git config --global user.name "Votre Nom"

ssh-keygen -t ed25519 -C "votre@email.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub  # Ajouter cette clé sur GitHub
```

---

## Installation manuelle

### Préparer l'environnement python
```bash
python3 -m venv --system-site-packages photobooth-venv
source photobooth-venv/bin/activate

pip install -r backend/requirements.txt
```

### Dépendances Node
```bash
cd frontend
npm install
```

---

## Lancement

Lancer le backend
```bash
source photobooth-venv/bin/activate
cd backend
python run.py
```

Lancer le frontend
```bash
cd frontend
npm run dev
```

---

## Todo
