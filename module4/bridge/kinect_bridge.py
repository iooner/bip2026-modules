#!/usr/bin/env python3
"""Pont capteur -> page web du module 4.

Envoie en WebSocket (ws://localhost:8765), ~30 fois par seconde :
  {"bodies": [{"center": [x, y], "z": m, "joints": {"head": [x, y], "handL": [x, y], ...}}]}
Coordonnées normalisées 0..1, image en miroir, y vers le bas. Liste vide si personne.

Sources :
  freenect  Kinect v1 (Xbox 360) via libfreenect, sans squelette : on segmente la personne dans
            l'image de profondeur et on prend les extrémités de la silhouette (tête, mains, pieds).
            Fonctionne sur Raspberry Pi.
  webcam    n'importe quelle webcam (ou caméra couleur de la Kinect) + MediaPipe Pose.
  fake      danseur synthétique, pour tester sans matériel.

Usage : python3 kinect_bridge.py --source freenect [--near 1.2 --far 3.5] [--port 8765]
"""
import argparse, asyncio, json, math, time

import numpy as np
import websockets


# ---------- Kinect v1 : silhouette dans l'image de profondeur ----------
class Freenect:
    def __init__(self, a):
        import freenect
        self.fn = freenect
        self.near, self.far, self.mirror = a.near * 1000, a.far * 1000, not a.no_mirror

    def read(self):
        depth, _ = self.fn.sync_get_depth(format=self.fn.DEPTH_MM)  # 480×640, mm, 0 = inconnu
        d = depth[::4, ::4].astype(np.float32)                       # 120×160, suffisant
        mask = (d > self.near) & (d < self.far)
        return silhouette(mask, d, self.mirror)


def silhouette(mask, depth, mirror):
    """Extrémités de la plus grosse silhouette : tête = point le plus haut,
    mains = points les plus à gauche / à droite du haut du corps, pieds = bas gauche / bas droit."""
    h, w = mask.shape
    # Garde les colonnes vraiment occupées (enlève le bruit, le sol lointain…)
    cols = mask.sum(0) > h * 0.02
    mask = mask & cols[None, :]
    ys, xs = np.nonzero(mask)
    if len(xs) < h * w * 0.01:
        return []
    top, bot = ys.min(), ys.max()
    hh = bot - top
    if hh < h * 0.25:
        return []

    def pt(x, y):
        x = float(x) / (w - 1)
        return [round(1 - x if mirror else x, 4), round(float(y) / (h - 1), 4)]

    head_rows = ys < top + hh * 0.08
    upper = ys < top + hh * 0.6
    low = ys > bot - hh * 0.08
    cx = xs.mean()
    j = {"head": pt(xs[head_rows].mean(), top)}
    i = np.argmin(np.where(upper, xs, 1e9)); a = pt(xs[i], ys[i])
    k = np.argmax(np.where(upper, xs, -1)); b = pt(xs[k], ys[k])
    left = low & (xs < cx); right = low & (xs >= cx)
    fa = pt(xs[left].mean(), bot) if left.any() else pt(cx, bot)
    fb = pt(xs[right].mean(), bot) if right.any() else pt(cx, bot)
    # En miroir, le côté gauche de l'image est la main droite de la personne : on trie par x écran.
    hands = sorted([a, b]); feet = sorted([fa, fb])
    j.update(handL=hands[0], handR=hands[1], footL=feet[0], footR=feet[1])
    j["hip"] = pt(cx, ys.mean())
    z = float(np.median(depth[mask])) / 1000
    return [{"center": j["hip"], "z": round(z, 2), "joints": j}]


# ---------- Webcam + MediaPipe ----------
class Webcam:
    MAP = dict(head=0, shoulderL=11, shoulderR=12, elbowL=13, elbowR=14, handL=15, handR=16,
               kneeL=25, kneeR=26, footL=27, footR=28)

    def __init__(self, a):
        import cv2, mediapipe as mp
        self.cv2, self.mirror = cv2, not a.no_mirror
        self.cap = cv2.VideoCapture(a.camera)
        self.pose = mp.solutions.pose.Pose(model_complexity=0)

    def read(self):
        ok, img = self.cap.read()
        if not ok:
            return []
        r = self.pose.process(self.cv2.cvtColor(img, self.cv2.COLOR_BGR2RGB))
        if not r.pose_landmarks:
            return []
        L = r.pose_landmarks.landmark
        p = lambda i: [round(1 - L[i].x if self.mirror else L[i].x, 4), round(L[i].y, 4)]
        j = {k: p(i) for k, i in self.MAP.items()}
        j["neck"] = [(j["shoulderL"][0] + j["shoulderR"][0]) / 2, (j["shoulderL"][1] + j["shoulderR"][1]) / 2]
        hip = [(p(23)[0] + p(24)[0]) / 2, (p(23)[1] + p(24)[1]) / 2]
        j["hip"] = hip
        return [{"center": hip, "joints": j}]


# ---------- Danseur synthétique ----------
class Fake:
    def __init__(self, a):
        self.t0 = time.time()

    def read(self):
        t = time.time() - self.t0
        return [{"center": [0.5, 0.55], "z": 2.5, "joints": {
            "head": [0.5, 0.17], "hip": [0.5, 0.55],
            "handL": [0.3 + 0.15 * math.sin(t * 1.3), 0.4 + 0.25 * math.sin(t * 2.1 + 1)],
            "handR": [0.7 + 0.15 * math.sin(t * 1.7 + 2), 0.4 + 0.25 * math.cos(t * 1.1)],
            "footL": [0.44, 0.92], "footR": [0.56, 0.92]}}]


SOURCES = {"freenect": Freenect, "webcam": Webcam, "fake": Fake}


async def main(a):
    src = SOURCES[a.source](a)
    clients = set()
    smooth = {}

    async def handler(ws, *_):
        clients.add(ws)
        try:
            await ws.wait_closed()
        finally:
            clients.discard(ws)

    async with websockets.serve(handler, a.host, a.port):
        print(f"Pont {a.source} sur ws://{a.host}:{a.port}")
        while True:
            t = time.time()
            bodies = await asyncio.to_thread(src.read)
            # Lissage exponentiel des articulations (le capteur tremble)
            for b in bodies:
                for k, p in b["joints"].items():
                    q = smooth.get(k, p)
                    smooth[k] = p = [q[0] + a.smooth * (p[0] - q[0]), q[1] + a.smooth * (p[1] - q[1])]
                    b["joints"][k] = [round(p[0], 4), round(p[1], 4)]
            if not bodies:
                smooth.clear()
            msg = json.dumps({"bodies": bodies})
            for ws in list(clients):
                try:
                    await ws.send(msg)
                except Exception:
                    clients.discard(ws)
            await asyncio.sleep(max(0, 1 / a.fps - (time.time() - t)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=SOURCES, default="freenect")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--near", type=float, default=1.2, help="distance mini de la personne (m)")
    ap.add_argument("--far", type=float, default=3.5, help="distance maxi (m), au-delà = décor")
    ap.add_argument("--smooth", type=float, default=0.5, help="0..1, plus bas = plus lisse")
    ap.add_argument("--camera", type=int, default=0, help="index webcam (source webcam)")
    ap.add_argument("--no-mirror", action="store_true")
    asyncio.run(main(ap.parse_args()))
