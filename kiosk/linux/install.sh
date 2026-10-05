#!/usr/bin/env bash
# Installe le lancement automatique d'un module à l'ouverture de session.
# Usage : ./install.sh module1   (session graphique avec connexion automatique)
set -eu
MODULE="${1:?usage: install.sh moduleN}"
DIR="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$DIR/kiosk.sh"
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/bip2026-kiosk.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=BIP2026 $MODULE
Exec=$DIR/kiosk.sh $MODULE
X-GNOME-Autostart-enabled=true
DESK
# Raspberry Pi OS Bookworm (labwc) lit son propre fichier autostart
if [ -d "$HOME/.config/labwc" ] || command -v labwc >/dev/null; then
  mkdir -p "$HOME/.config/labwc"
  grep -q bip2026 "$HOME/.config/labwc/autostart" 2>/dev/null || \
    echo "$DIR/kiosk.sh $MODULE &  # bip2026" >> "$HOME/.config/labwc/autostart"
fi
echo "OK : $MODULE démarrera à la prochaine ouverture de session."
