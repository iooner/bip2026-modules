#!/usr/bin/env bash
# Lance un module en kiosk plein écran et le relance s'il se ferme ou plante.
# Usage : kiosk.sh module1
set -u
MODULE="${1:?usage: kiosk.sh moduleN}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
URL="file://$ROOT/$MODULE/index.html"
PROFILE="$HOME/.cache/bip2026-kiosk-$MODULE"
BROWSER="$(command -v chromium || command -v chromium-browser || command -v google-chrome)"

# Pas de mise en veille de l'écran (X11 ; sans effet sous Wayland)
xset s off -dpms s noblank 2>/dev/null || true

while true; do
  # Évite le bandeau « Chromium ne s'est pas fermé correctement »
  sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' "$PROFILE/Default/Preferences" 2>/dev/null || true
  "$BROWSER" --kiosk --kiosk-printing --noerrdialogs --disable-infobars \
    --disable-pinch --overscroll-history-navigation=0 --disable-session-crashed-bubble \
    --disable-features=Translate --no-first-run --check-for-update-interval=31536000 \
    --user-data-dir="$PROFILE" "$URL"
  sleep 2
done
