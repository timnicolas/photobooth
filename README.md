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

### Post-installation

Créer un utilisateur admin et un utilisateur classique :
```bash
cd ~/photobooth/backend && ../photobooth-venv/bin/python create_user.py
```

Installer l'imprimante Canon SELPHY CP1500 via CUPS :
```bash
sudo apt-get install -y cups printer-driver-gutenprint
```
Puis accéder à l'interface CUPS sur `http://localhost:631` pour ajouter l'imprimante.

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

- [ ] Test raspberry CAM
- [ ] Test connection imprimante
- [ ] Gestion erreurs d'imprimante ?
- [ ] Tester en mode hors connection
