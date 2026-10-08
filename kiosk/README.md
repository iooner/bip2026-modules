# Autorun des bornes

Même principe pour les 4 modules : à l'ouverture de session, Chrome/Chromium s'ouvre en plein écran
(`--kiosk`) sur `moduleN/index.html`, imprime sans dialogue (`--kiosk-printing`), et une boucle le relance
s'il se ferme ou plante.
Si le module a un `server.py` (module2 : relais des caméras), il est lancé aussi et la page s'ouvre
sur `http://127.0.0.1:8360/` (Python 3, déjà présent sur Raspberry Pi OS).
Si le module a un `helper/helper.py` (module3 : capteur GPIO + Pi Camera), il tourne à côté de la page
(journal dans `/tmp/bip2026-moduleN-helper.log`).

Pré-requis : session avec **connexion automatique**, imprimante d'étiquettes **par défaut**, Chrome installé
(Windows) ou Chromium (Linux / Raspberry Pi).

## Windows
Copier le dépôt (ex. `C:\bip2026-modules`), puis double-cliquer :
```
kiosk\windows\install.bat module1
```
(raccourci dans le dossier Démarrage + écran jamais en veille). Pour sortir : Alt+F4 puis fermer la fenêtre noire réduite.

## Raspberry Pi (recommandé)
Matériel : Raspberry Pi 4 ou 5, Raspberry Pi OS Desktop, **adaptateur HDMI→VGA actif** (l'Elo est en VGA ;
micro-HDMI sur Pi 4/5), câble USB de l'Elo pour le tactile.
```
git clone https://github.com/iooner/bip2026-modules && cd bip2026-modules
./kiosk/linux/setup-pi.sh module1
```
Installe Chromium, CUPS et le pilote Dymo, active la connexion automatique et l'autorun.

## Linux (autre)
```
./kiosk/linux/install.sh module1
```
Pour sortir : Alt+F4 puis `pkill -f kiosk.sh`.

## Mettre une borne à jour
```
./kiosk/linux/update.sh
```
Met à jour le dépôt et réinstalle le pilote d'impression s'il a changé, puis redémarrer la borne.
Si on oublie le pilote, la borne le dit elle-même : bandeau « pause technique » avec la ligne `pilote : … pas à jour`.

## Bandeau « en panne »
Quand l'impression ou le matériel d'un module est hors service, l'accueil est grisé et barré d'un bandeau qui invite
à prévenir l'équipe ; la cause est écrite en petit en bas de l'écran (`etiquettes`, `capot`, `file`, `imprimante`,
`service`, `pilote`, `kinect`, `scanner`, `cameras`). Il disparaît seul quand tout remarche. Essai : `?panne=texte`.

## Tester sans installer
`kiosk\windows\kiosk.bat module1` ou `./kiosk/linux/kiosk.sh module1`.
