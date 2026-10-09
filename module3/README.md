# Module 3 · Vide ton sac (Miroir Miroir, BIP 2026)

Faux scanner d'aéroport. Le visiteur choisit FR/EN, vide ses poches ou son sac dans un bac et le glisse
dans la machine. Un capteur (GPIO) déclenche une photo avec la Pi Camera, l'écran la « scanne » en rayons X
puis affiche **AUTORISÉ (FR) / CLEAR (EN)**, et une étiquette Dymo 59×102 mm s'imprime (photo scannée, n° de passage,
date, faux code-barres).

## Tester sans matériel
Ouvrir `index.html?sim=1` (ou `SIMULATE: true` dans `config.js`) : bouton « Simuler un passage » ou touche
**Espace**, avec des images d'exemple (`assets/sample-*.svg`). Échap = retour à l'accueil.

Pour tester toute la chaîne page ↔ serveur sans Pi : `python3 helper/helper.py --sim` (Entrée = un passage),
puis ouvrir `index.html` sans `?sim=1`.

## Sur la borne (Raspberry Pi)
`./kiosk/linux/setup-pi.sh module3` : comme les autres modules, plus `helper/helper.py` lancé
automatiquement à côté de Chromium par `kiosk.sh` (journal : `/tmp/bip2026-module3-helper.log`).

- **Capteur** : par défaut GPIO 17 (BCM, broche 11) relié à la masse (broche 9) par un contact
  (micro-switch, barrière IR à sortie collecteur ouvert…). Capteur qui envoie du 3,3 V : `--active-high`.
- **Caméra** : Pi Camera via `picamera2` (préinstallé sur Raspberry Pi OS), sinon commande `rpicam-still`.
- Options : `python3 helper/helper.py --help` (broche, délai avant photo, résolution, délai entre passages) ;
  pour les changer sur la borne, modifier les valeurs par défaut en bas de `helper.py`.
- Badge rouge « helper ✕ » en bas à droite : le serveur ne répond pas. Touche **S** ou Espace : photo sans
  le capteur. Sans photo après 8 s, une image d'exemple est utilisée pour ne pas bloquer le visiteur.

## Sur un mini PC avec webcam USB (sans capteur)
`sudo apt install python3-opencv`, puis `helper.py` passe tout seul en mode webcam s'il n'y a pas de Pi Camera
(`--webcam /dev/video0` pour le forcer, `--webcam off` pour l'interdire). La webcam, fixée au-dessus du bac,
le repère par sa **bordure orange** : dès que le bac entier est visible et que plus rien ne bouge dedans depuis
`--stable` secondes (1,5 par défaut), c'est un passage, et la photo est recadrée sur l'intérieur du bac.

Un bac n'est scanné qu'une fois. Le passage suivant demande que le bac sorte du champ (`--absent`, 1,5 s), ou
qu'il soit poussé par un autre bac : le helper garde une empreinte du contenu scanné et ne rescanne un bac
dérangé (déplacé, perdu de vue) que si son contenu a changé. Deux bacs vides qui se suivent sans que le champ
se vide ne donnent donc qu'un scan.

- **Écran des consignes** : petite vue en direct de la caméra (cadre vert = bac en place, `LIVE_PREVIEW` dans
  `config.js`) et bandeau coloré qui dit ce que le scanner attend (orange : il attend, vert : bac en place,
  rouge : bac coupé par le bord de l'image ou déjà scanné).
- **Vue de réglage** : appui de 5 s sur le ✕ de l'accueil (un appui pour fermer), ou
  `http://127.0.0.1:8765/live.mjpg?debug` : image en direct avec l'état du suivi en clair. Les quatre côtés de
  la bordure doivent être dans l'image, avec un peu de marge ; une butée au fond du tunnel aide.
- **Couleur de la bordure** : seuils en tête de `helper/bac.py` (à réajuster sur le bac définitif) ; essai rapide
  avec `python3 helper/bac.py`.
- Mesuré sur un Celeron N3150 avec une Logitech C920 en 1280×720 MJPG : suivi à 20 à 27 images/s.

## Réglages : `config.js`
Cadrage de la photo (`CROP`, `ROTATE`, `MIRROR`), rendu rayons X (`SCAN_STYLE` : néon, radio, aéroport, noir ou
ancien filtre ; contraste, luminosité, contours, négatif ; écran et étiquette séparément), durées, impression
(`PRINT_START_S` : lancée pendant le scan pour que l'étiquette sorte avec le verdict), son, curseur.

## Polices
Déposer dans `fonts/` : HelveticaNeueLTStd-Roman.otf, -It.otf, -Md.otf, -MdIt.otf (sinon repli Helvetica/Arial).
