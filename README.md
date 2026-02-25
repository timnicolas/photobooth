# photobooth
Photobooth avec raspberrypi, Canon Selphy CP1500 et interface WEB

## Principe de fonctionnement

La carte Raspberrypi emet un réseau WIFI.
- L'imprimante se connecte au réseau du Raspberry (ou en USB).
- Une interface (tablette, tel, ordi, etc.) se connecte au réseau et ouvre un page web avec l'interface

## Installation

Préparer l'environnement python
```bash
python3 -m venv photobooth-venv
source photobooth-venv/bin/activate

pip install -r backend/requirements.txt
```

Créez un utilisateur admin et un utilisateur classique
```bash
cd backend
python create_user.py
```

Installez l'imprimante sur le raspberrypi (ou ordinateur). Par la suite l'API sera capable de lancer une impression.

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

## Todo

- [ ] Test raspberry CAM
- [ ] Gestion erreurs d'imprimante ?
- [ ] Tester en mode hors connection

BUGS
- [ ] pb d'icon : ca risque de planter en hors ligne

- [ ] créer script raspberrypi pour tout lancer sur 10.4.4.12:2022