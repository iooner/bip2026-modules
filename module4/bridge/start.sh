#!/usr/bin/env bash
# Lance le pont Kinect et le relance s'il s'arrête (Kinect débranchée, plantage…).
# Usage : start.sh [freenect|webcam|fake] [options de kinect_bridge.py]
DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="${1:-freenect}"; shift || true
while true; do
  python3 "$DIR/kinect_bridge.py" --source "$SRC" "$@"
  sleep 3
done
