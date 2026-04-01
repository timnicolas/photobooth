# Refactoring complet de la gestion de la camera

### Résumé du problème actuel

Le code actuel (`camera.py`) utilise :
- Un **preview à 1280×720** via `create_preview_configuration`
- Un **thread de fond** (`_preview_loop`) qui capture les frames en boucle avec `capture_array()` + encodage JPEG software (`cv2.imencode`)
- Un **`switch_mode_and_capture_array`** pour la photo haute résolution (actuellement bridée à 1280×720, la vraie résolution 4608×2592 est commentée dans `config.py`)
- Un **lock partagé** entre le thread preview et la capture photo → le stream se bloque pendant la capture

Problèmes : encodage JPEG en software (CPU élevé), changement de mode lent (~200-300ms), stream qui freeze pendant la capture, résolution de capture pas exploitée.

---

### Architecture proposée : Double flux (main + lores) sans changement de mode

**Principe** : Configurer la caméra avec **une seule configuration** qui expose deux flux simultanés :
- `main` en **2304×1296** (demi-résolution capteur, 2×2 binned) → pour la capture photo
- `lores` en **640×480 YUV420** → pour le stream MJPEG via encodeur **hardware**

Le stream et la capture fonctionnent **en parallèle** sans jamais changer de mode. Plus de freeze, plus de lock.

> **Pourquoi 2304×1296 et pas 4608×2592 ?** La Canon SELPHY CP1500 imprime en 1844×1240 natif (300dpi sur 4×6"). 2304×1296 est largement suffisant et permet ~30fps. La pleine résolution (4608×2592) limite à ~10fps et consomme beaucoup de mémoire, sans gain visible à l'impression.

---

### Schéma d'architecture

```
┌──────────────────────────────────────────────────┐
│                  Picamera2                        │
│                                                   │
│  Sensor IMX708 (mode 1 : 2304×1296 @ 30fps)      │
│       ┌─────────┐       ┌──────────┐              │
│       │  main   │       │  lores   │              │
│       │2304×1296│       │ 640×480  │              │
│       │ RGB888  │       │ YUV420   │              │
│       └────┬────┘       └────┬─────┘              │
│            │                 │                     │
│            │          ┌──────┴──────┐              │
│            │          │ MJPEGEncoder│ (hardware)   │
│            │          │  → lores    │              │
│            │          └──────┬──────┘              │
└────────────┼─────────────────┼────────────────────┘
             │                 │
             ▼                 ▼
     captured_request()   StreamingOutput
     → photo pleine       (Condition/wait)
       qualité                 │
             │                 ▼
             │           Flask /api/camera/stream
             │           (MJPEG multipart)
             ▼                 │
     crop + mask overlay       ▼
     → sauvegarde JPEG    Frontend <img src="...">
     → impression              │
                               │ (masque en overlay CSS)
                               ▼
                          Rendu final écran
```

---

### Détail des composants

#### 1. Initialisation caméra (`_get_picamera()`)

Les résolutions et le framerate sont configurables via `config.py` :

```python
# config.py
PICAMERA_MAIN_WIDTH = 2304       # résolution capture (main)
PICAMERA_MAIN_HEIGHT = 1296
PICAMERA_LORES_WIDTH = 640       # résolution stream (lores)
PICAMERA_LORES_HEIGHT = 480
PICAMERA_STREAM_FPS = 30         # framerate cible
PICAMERA_STREAM_BITRATE = 5_000_000  # bitrate encodeur MJPEG hardware
```

```python
# camera.py — init
config = picam2.create_video_configuration(
    main={"size": (Config.PICAMERA_MAIN_WIDTH, Config.PICAMERA_MAIN_HEIGHT), "format": "RGB888"},
    lores={"size": (Config.PICAMERA_LORES_WIDTH, Config.PICAMERA_LORES_HEIGHT), "format": "YUV420"},
    buffer_count=4,
    controls={"FrameRate": Config.PICAMERA_STREAM_FPS, "AfMode": 2, "AfSpeed": 1}
)
picam2.configure(config)
picam2.start()

# Démarrer l'encodeur hardware MJPEG sur le flux lores
stream_output = StreamingOutput()
encoder = MJPEGEncoder(bitrate=Config.PICAMERA_STREAM_BITRATE)
picam2.start_encoder(encoder, FileOutput(stream_output), name="lores")
```

- **Autofocus continu** activé dès le départ (la Pi Camera 3 a le PDAF)
- **Encodeur hardware MJPEG** sur le flux `lores` → ~50% CPU au lieu de ~95% en software
- **Pas de thread de fond** maison → picamera2 gère ses propres threads

#### 2. Stream MJPEG (`/api/camera/stream`)

```python
class StreamingOutput(io.BufferedIOBase):
    """Buffer partagé entre l'encodeur hardware et les clients Flask."""
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

def generate_mjpeg():
    while True:
        with stream_output.condition:
            stream_output.condition.wait()
            frame = stream_output.frame
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
```

- L'encodeur hardware écrit les JPEG directement dans `StreamingOutput`
- Flask lit via la `Condition` → pas de polling, pas de sleep
- **Le masque sur le stream est géré côté frontend** (overlay CSS d'un `<div>` avec le PNG par-dessus le `<img>`) → zéro coût backend par frame

#### 3. Capture photo (`/api/camera/capture`)

```python
def _picamera_capture() -> np.ndarray:
    # Optionnel : déclencher un cycle AF ponctuel pour s'assurer du focus
    picam2.autofocus_cycle()

    # Capturer depuis le flux main (2304×1296) sans changer de mode
    with picam2.captured_request() as request:
        array = request.make_array("main")  # numpy RGB

    return cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
```

- **`captured_request()`** lit directement depuis le flux `main` déjà actif
- **Pas de `switch_mode_and_capture_array`** → pas de délai, pas de freeze du stream
- Le masque est appliqué côté serveur sur la photo pleine résolution (code `apply_mask` existant)
- Qualité JPEG à 95 pour la sauvegarde

#### 4. Masque sur le stream (côté frontend)

Au lieu d'appliquer le masque frame par frame côté serveur (coûteux), on superpose le PNG en CSS :

```html
<div class="camera-container" style="position: relative">
  <img :src="streamUrl" style="width: 100%; display: block" />
  <img v-if="activeMask" :src="maskUrl"
       style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none" />
</div>
```

Le masque reste appliqué côté serveur uniquement pour la **photo finale** (capture).

---

### Ce qui change par rapport au code actuel

| Aspect | Avant | Après |
|--------|-------|-------|
| Config caméra | `create_preview_configuration` (1 flux) | `create_video_configuration` (main + lores) |
| Résolution capture | 1280×720 (bridée) | 2304×1296 (sans switch) |
| Résolution stream | 1280×720 | 640×480 (lores, suffisant pour preview) |
| Encodage JPEG stream | Software (`cv2.imencode`) | Hardware (`MJPEGEncoder`) |
| Thread de fond | `_preview_loop` maison + locks | Géré par picamera2 (encodeur interne) |
| Capture photo | `switch_mode_and_capture_array` (200-300ms) | `captured_request()` (instantané) |
| Masque sur stream | Appliqué par frame côté serveur | Overlay CSS côté frontend |
| Autofocus | Aucun | Continu (PDAF) + cycle ponctuel avant capture |
| Stream pendant capture | Freeze | Continue sans interruption |

### Fichiers à modifier

1. **`backend/api/config.py`** — Remplacer les params stream/capture par les nouveaux (`PICAMERA_MAIN_WIDTH/HEIGHT`, `PICAMERA_LORES_WIDTH/HEIGHT`, `PICAMERA_STREAM_FPS`, `PICAMERA_STREAM_BITRATE`)
2. **`backend/api/camera.py`** — Réécrire la partie picamera : init avec double flux, `StreamingOutput`, `MJPEGEncoder`, `captured_request()`, supprimer `_preview_loop` et les locks associés
3. **`backend/api/routes/camera.py`** — Adapter le endpoint stream pour ne plus passer `mask_path` côté serveur (ou le garder en option pour compatibilité)
4. **`frontend/src/views/PhotoboothView.vue`** — Ajouter l'overlay CSS du masque sur le stream au lieu de le passer en query param

### Risques et points d'attention

- **Qualité JPEG du stream** : à 640×480 + hardware encoder, la qualité est plus basse qu'avant (1280×720 software). C'est voulu — le stream est juste un viseur. Si le résultat semble trop pixelisé sur l'écran, on peut monter à 800×600.
- **Masque CSS vs masque serveur sur le stream** : le ratio du masque doit correspondre au ratio crop du stream. Il faut s'assurer que le crop d'orientation est fait avant d'afficher le masque en overlay.
- **`autofocus_cycle()`** bloque ~200-500ms. Si c'est gênant, on peut se reposer uniquement sur l'AF continu (qui est déjà actif) et ne pas faire de cycle ponctuel avant capture.
