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

## Réglages : `config.js`
Cadrage de la photo (`CROP`, `ROTATE`, `MIRROR`), rendu rayons X (contraste, luminosité, négatif, écran et
étiquette séparément), durées, impression, son, curseur.

## Polices
Déposer dans `fonts/` : HelveticaNeueLTStd-Roman.otf, -It.otf, -Md.otf, -MdIt.otf (sinon repli Helvetica/Arial).
