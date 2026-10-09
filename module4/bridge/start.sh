#!/usr/bin/env bash
# Lance le pont Kinect et le relance s'il s'arrête (Kinect débranchée, plantage…).
# Usage : start.sh [freenect|kinect|webcam|fake] [options de kinect_bridge.py]
DIR="$(cd "$(dirname "$0")" && pwd)"
# MediaPipe (sources kinect et webcam) vit dans un environnement Python à part s'il existe
PY=python3; [ -x "$HOME/bip2026-local/venv/bin/python" ] && PY="$HOME/bip2026-local/venv/bin/python"
SRC="${1:-freenect}"; shift || true
while true; do
  "$PY" "$DIR/kinect_bridge.py" --source "$SRC" "$@"
  sleep 3
done
