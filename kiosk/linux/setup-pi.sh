#!/usr/bin/env bash
# Préparation d'un Raspberry Pi (Raspberry Pi OS Desktop) pour une borne.
# Usage : ./kiosk/linux/setup-pi.sh module1
set -eu
MODULE="${1:?usage: setup-pi.sh moduleN}"
DIR="$(cd "$(dirname "$0")" && pwd)"

sudo apt-get update
sudo apt-get install -y chromium-browser cups printer-driver-dymo || \
  sudo apt-get install -y chromium cups printer-driver-dymo
sudo usermod -aG lpadmin "$USER"

# Connexion automatique au bureau + pas de mise en veille de l'écran
sudo raspi-config nonint do_boot_behaviour B4
sudo raspi-config nonint do_blanking 1 || true

"$DIR/install.sh" "$MODULE"

cat <<MSG

Reste à faire :
1. Brancher l'imprimante, ouvrir http://localhost:631 > Administration > Ajouter une imprimante
   (pilote DYMO LabelWriter 4XL, format 59x102 mm), puis : lpoptions -d <nom_imprimante>
2. Redémarrer : sudo reboot
MSG
