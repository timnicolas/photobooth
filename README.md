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

- [ ] Test end-to-end
- [ ] Test raspberry CAM
- [ ] Délai de 3s pour prise de photo
- [ ] Refaire interface (faut que ca prenne max 100% de la hauteur)
- [ ] Menu photo, ajouter un bouton pour re-imprimer
- [ ] Test masque
- [ ] Gestion erreurs d'imprimante ?
- [ ] Tester connection utilisateur normal ?
