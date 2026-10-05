#!/usr/bin/env bash
# Kinect v1 (Xbox 360) sur Raspberry Pi : pilote libfreenect + démarrage auto du pont.
# À lancer après ./kiosk/linux/setup-pi.sh module4
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$DIR/start.sh"

sudo apt-get update
sudo apt-get install -y freenect python3-freenect python3-numpy python3-websockets

# Accès USB à la Kinect sans être root
sudo tee /etc/udev/rules.d/51-kinect.rules >/dev/null <<'RULES'
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02b0", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ad", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ae", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02c2", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02be", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02bf", MODE="0666"
RULES
sudo udevadm control --reload-rules && sudo udevadm trigger

# Démarrage du pont à l'ouverture de session
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/bip2026-kinect.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=BIP2026 pont Kinect
Exec=$DIR/start.sh freenect
DESK
if [ -d "$HOME/.config/labwc" ] || command -v labwc >/dev/null; then
  mkdir -p "$HOME/.config/labwc"
  grep -q bip2026-kinect "$HOME/.config/labwc/autostart" 2>/dev/null || \
    echo "$DIR/start.sh freenect &  # bip2026-kinect" >> "$HOME/.config/labwc/autostart"
fi

cat <<MSG
OK. Test : freenect-glview (image de profondeur), puis $DIR/start.sh freenect
Régler la zone de détection avec --near / --far (mètres) dans l'autostart si besoin.
MSG
