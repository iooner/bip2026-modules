# Autorun des bornes

Même principe pour les 4 modules : à l'ouverture de session, Chrome/Chromium s'ouvre en plein écran
(`--kiosk`) sur `moduleN/index.html`, imprime sans dialogue (`--kiosk-printing`), et une boucle le relance
s'il se ferme ou plante.

Pré-requis : session avec **connexion automatique**, imprimante d'étiquettes **par défaut**, Chrome installé
(Windows) ou Chromium (Linux / Raspberry Pi).

## Windows
Copier le dépôt (ex. `C:\bip2026-modules`), puis double-cliquer :
```
kiosk\windows\install.bat module1
```
(raccourci dans le dossier Démarrage + écran jamais en veille). Pour sortir : Alt+F4 puis fermer la fenêtre noire réduite.

## Linux / Raspberry Pi OS
```
./kiosk/linux/install.sh module1
```
Pour sortir : Alt+F4 puis `pkill -f kiosk.sh`.

## Tester sans installer
`kiosk\windows\kiosk.bat module1` ou `./kiosk/linux/kiosk.sh module1`.
