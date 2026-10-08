#!/usr/bin/env bash
# Lance un module en kiosk plein écran et le relance s'il se ferme ou plante.
# Usage : kiosk.sh module1
set -u
# Groupe de processus à part : le nettoyage final (kill 0) ne doit arrêter que le kiosk,
# jamais la session graphique qui l'a lancé (sinon déconnexion à l'arrêt du script).
if [ "$(ps -o pgid= -p $$ | tr -d ' ')" != "$$" ]; then exec setsid "$0" "$@"; fi
MODULE="${1:?usage: kiosk.sh moduleN}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
URL="file://$ROOT/$MODULE/index.html"
PROFILE="$HOME/.cache/bip2026-kiosk-$MODULE"
RELAUNCH_S=15   # délai avant relance du navigateur s'il est fermé (Alt+F4) : le temps de reprendre la main
BROWSER="$(command -v chromium || command -v chromium-browser || command -v google-chrome)"

# Impression silencieuse des étiquettes (pas d'aperçu à l'écran) : service commun aux 4 modules
( while true; do python3 "$ROOT/kiosk/print_server.py"; sleep 2; done ) &
trap 'kill 0' EXIT

# Module avec serveur local (ex. module2 : relais des caméras IP) : lancé et relancé en tâche de fond
if [ -f "$ROOT/$MODULE/server.py" ]; then
  PORT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("port", 8360))' "$ROOT/$MODULE/cameras.json")"
  URL="http://127.0.0.1:$PORT/index.html"
  ( while true; do python3 "$ROOT/$MODULE/server.py"; sleep 2; done ) &
  trap 'kill 0' EXIT
  sleep 1
fi

# Pas de mise en veille de l'écran (X11 ; sans effet sous Wayland)
xset s off -dpms s noblank 2>/dev/null || true

# Module avec matériel (GPIO, caméra…) : son petit serveur local tourne en parallèle
HELPER="$ROOT/$MODULE/helper/helper.py"
if [ -f "$HELPER" ]; then
  ( while true; do python3 "$HELPER" >>"/tmp/bip2026-$MODULE-helper.log" 2>&1; sleep 2; done ) &
  trap 'kill 0' EXIT
fi

while true; do
  # Évite le bandeau « Chromium ne s'est pas fermé correctement »
  sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' "$PROFILE/Default/Preferences" 2>/dev/null || true
  "$BROWSER" --kiosk --kiosk-printing --noerrdialogs --disable-infobars \
    --disable-pinch --overscroll-history-navigation=0 --disable-session-crashed-bubble \
    --autoplay-policy=no-user-gesture-required \
    --disable-features=Translate,TranslateUI --no-first-run --check-for-update-interval=31536000 \
    --password-store=basic --user-data-dir="$PROFILE" "$URL"
  sleep "$RELAUNCH_S"
done
