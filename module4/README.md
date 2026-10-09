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

## Borne recommandée : petit PC Windows + Kinect v1

Sous Windows, le **Kinect for Windows SDK 1.8** (Microsoft, gratuit) donne un vrai squelette
(20 articulations) avec la Kinect Xbox 360. C'est la seule option avec squelette pour une v1.

1. Windows 10/11, Chrome, imprimante Dymo par défaut, connexion automatique.
2. Installer le Kinect for Windows SDK 1.8 (KinectSDK-v1.8-Setup.exe, site Microsoft).
3. Brancher la Kinect avec son **adaptateur secteur** (USB + 12 V), sur un port USB 2.0 de préférence.
   Tester avec « Kinect Developer Toolkit » ou simplement l'étape 4.
4. `module4\bridge\windows\build.bat` (compile `KinectBridge.exe` avec le compilateur C# fourni avec Windows).
5. `kiosk\windows\install.bat module4` : au démarrage, `kiosk.bat` lance le pont puis Chrome en kiosk.

Placement : Kinect à ~1 m de haut, croix au sol à ~2,5 m (le corps entier doit être visible, portée 0,8–4 m).
Le pont suit la personne la plus proche du centre.

## Autres ponts (`bridge/kinect_bridge.py`, Linux / Raspberry Pi)

```
python3 bridge/kinect_bridge.py --source freenect   # Kinect v1 via libfreenect : pas de squelette,
                                                    # tête/mains/pieds tirés de la silhouette en profondeur
python3 bridge/kinect_bridge.py --source kinect     # Kinect v1 + vrai squelette (MediaPipe sur sa caméra couleur,
                                                    # profondeur pour la zone et en repli) : PC type Core i5
python3 bridge/kinect_bridge.py --source webcam     # webcam + MediaPipe
python3 bridge/kinect_bridge.py --source fake       # test sans matériel
```
Options : `--near 1.2 --far 3.5` (zone de la personne, en mètres), `--smooth`, `--no-mirror`.
Installation Linux : `./kiosk/linux/setup-pi.sh module4 && ./module4/bridge/setup-pi.sh`.

Squelette MediaPipe (sources `kinect` et `webcam`), dans un environnement Python à part que `bridge/start.sh` utilise
s'il existe, avec le modèle de pose à côté du décor appris :
```
sudo apt install python3-venv libfreenect0.5t64
echo "blacklist gspca_kinect" | sudo tee /etc/modprobe.d/bip2026-kinect.conf   # pilote webcam du noyau : gêne libfreenect
python3 -m venv ~/bip2026-local/venv && ~/bip2026-local/venv/bin/pip install mediapipe numpy websockets
curl -fL -o ~/.cache/bip2026/pose_landmarker_full.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task
./module4/bridge/start.sh kinect
```
La caméra couleur a besoin de lumière sur la personne ; dans le noir, le pont retombe sur la silhouette en profondeur
(décor vide à réapprendre sur place : F9). Mesuré sur un Optiplex XE2 (i5-4570S) : 29 images/s, un cœur sur quatre occupé.

**Non testé sur le matériel** : le pont Windows est compilé ici contre une maquette du SDK, pas avec une vraie Kinect.
