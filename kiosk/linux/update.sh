#!/usr/bin/env bash
# Met une borne à jour : dépôt + pilote d'impression. À lancer sur chaque borne après une mise à jour du projet.
# Usage : ./kiosk/linux/update.sh     (demande le mot de passe sudo seulement si le pilote a changé)
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [ -d "$ROOT/.git" ]; then git -C "$ROOT" pull --ff-only; else echo "Pas un dépôt git : fichiers laissés tels quels."; fi
SRC="$ROOT/kiosk/linux/tspl/rastertotspl-bip"; DST=/usr/lib/cups/filter/rastertotspl-bip
if [ -e "$DST" ] && cmp -s "$SRC" "$DST"; then
  echo "Pilote d'impression déjà à jour."
elif [ -e "$DST" ]; then
  sudo install -o root -g root -m 755 "$SRC" "$DST" && echo "Pilote d'impression mis à jour."
else
  echo "Pilote TSPL non installé sur cette borne (autre imprimante ?) : rien à faire."
fi
echo "Redémarrer la borne (ou fermer le kiosk : Alt+F4 puis attendre la relance) pour charger la nouvelle version."
