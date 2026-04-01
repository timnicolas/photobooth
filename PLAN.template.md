# Refactoring complet de la gestion de la camera
 
> **Prompt de lancement :**
> ```
> Lis PLAN.md et exécute toutes les étapes dans l'ordre.
> Coche chaque étape quand c'est fait et note ce que tu as fait dans Notes.
> Utilise les agents spécialisés quand c'est pertinent.
> Arrête-toi si tu as un doute.
> ```
 
---
 
## Contexte
 
L'objectif du plan et de faire a 100% le système de gestion de la camera.

J'utilise la picamera 3 sur un raspberrypi 4.

J'ai besoin de prendre des photos avec la qualité la plus optimale possible (autofocus, bonne qualité, etc.).
Sinon j'ai quasi en permanence besoin d'un flux vidéo et la je m'en fiche un peu de la qualité.
Pour le flux, ca me dérange pas de perdre des frames ou des pixels mais je veux surtout pas "prendre du retard". Le flux doit rester temps réel a au moins 10Hz (si on peut avoir plus tant mieux).
C'est pas génant si le flux se coupe quelques secondes pendant la prise de photo.
Si il faut lancer un autre programme en parallele au backend / frontend, c'est possible
 
## Étapes

- [ ] 1. Fait des recherches sur internet pour trouver les parametres optimaux pour une photo avec la picamera 3
- [ ] 2. Fait des recherches sur internet et trouve le fonctionnement optimal pour avoir un flux temps réel + de la prise de photo de qualité avec mon backend flask et mon frontend vue.
- [ ] 3. Fait moi un plan générale sur l'architecture, on fera dans un second temps un plan plus détaillé d'implémentation dans le code
- [ ] 4. Écrit ta proposition de plan en bas de ce fichier
 
## Proposition de Claude
 
<!-- Claude remplit ici -->
 