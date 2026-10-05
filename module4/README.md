# Module 4 · Signature corporelle

Choix de la langue → la personne se place sur la croix au sol (aperçu « miroir » de sa silhouette) →
3, 2, 1 → 10 s pour bouger → ses mains, pieds et tête tracent une signature à l'encre (trait épais
quand le geste est lent, fin quand il est rapide) → étiquette Dymo 59×102 mm imprimée.

Réglages (durées, tolérance de la croix, simulation…) : `config.js`.

## Fonctionnement

```
Kinect ──USB──> bridge/kinect_bridge.py ──WebSocket ws://localhost:8765──> index.html (kiosk)
```

La page lit le corps envoyé par le pont. Si le pont ne répond pas, elle passe en **simulation**
(`CONFIG.SIMULATION`) : `mouse` (souris ou doigt = main droite, main gauche en miroir), `demo` (danseur
virtuel), `webcam` (détection de pose MediaPipe dans le navigateur, internet requis). L'écran de la croix
indique la source utilisée (`kinect` ou le mode de simulation). Le bouton « Je suis prêt·e » force le départ.

## Pont capteur (`bridge/`)

```
python3 bridge/kinect_bridge.py --source freenect   # Kinect v1
python3 bridge/kinect_bridge.py --source webcam     # webcam + MediaPipe (pip install opencv-python mediapipe)
python3 bridge/kinect_bridge.py --source fake       # test sans matériel
```
Options : `--near 1.2 --far 3.5` (zone où se trouve la personne, en mètres), `--smooth`, `--no-mirror`.

## Kinect et Raspberry Pi

| Kinect | Sur Raspberry Pi | Squelette |
|---|---|---|
| **v1** (Xbox 360, modèles 1414/1473) | Oui, via libfreenect (paquets Debian). Pi 4 ou 5. | Non (le squelette Microsoft est Windows only) : on extrait tête, mains, pieds de la silhouette en profondeur. Suffisant pour la signature. |
| **v2** (Xbox One) | Déconseillé : USB 3 + libfreenect2, décodage profondeur très lent sans GPU compatible, instable. | Non sous Linux. |

Les deux modèles ont besoin de leur **alimentation secteur** (adaptateur Kinect USB + 12 V ; pour la v2,
« Kinect Adapter for Windows »). Si c'est une v2 ou si on veut un vrai squelette : mini-PC Windows +
Kinect SDK (pont à écrire, même format JSON), ou plus simple : une webcam + `--source webcam`.

Installation sur la borne (Kinect v1) :
```
./kiosk/linux/setup-pi.sh module4
./module4/bridge/setup-pi.sh
```
Placement conseillé : Kinect à ~1 m de haut, croix au sol à ~2,5 m (le corps entier doit être visible).

**Non testé sur le matériel** : réglages `--near/--far` et détection des mains à ajuster sur place.
