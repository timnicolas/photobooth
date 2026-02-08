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

pip install -r requirements.txt
```

Installez l'imprimante sur le raspberrypi (ou ordinateur). Par la suite l'API sera capable de lancer une impression.

## Lancement

Activez l'environnement
```bash
source photobooth-venv/bin/activate
```
