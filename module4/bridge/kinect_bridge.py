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
    DEPTH_MM = 5

    def __init__(self, a):
        self.near, self.far, self.mirror = a.near * 1000, a.far * 1000, not a.no_mirror
        self.a, self.bg, self.learn_at, self.st = a, None, 0, {}
        self.ring = []                                          # dernières images, pour --keep-sessions
        try:
            import freenect
            self.depth = lambda: freenect.sync_get_depth(format=freenect.DEPTH_MM)[0]
        except ImportError:
            # Pas de module Python freenect (absent de Debian 13) : libfreenect_sync en direct.
            import ctypes
            lib = ctypes.CDLL("libfreenect_sync.so.0.5")
            lib.freenect_sync_get_depth.argtypes = [ctypes.POINTER(ctypes.c_void_p),
                                                    ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int]
            buf, ts, u16 = ctypes.c_void_p(), ctypes.c_uint32(), ctypes.POINTER(ctypes.c_uint16)

            def depth():
                if lib.freenect_sync_get_depth(ctypes.byref(buf), ctypes.byref(ts), 0, self.DEPTH_MM):
                    raise RuntimeError("Kinect introuvable")
                return np.ctypeslib.as_array(ctypes.cast(buf, u16), (480, 640))
            self.depth = depth

    def read(self):
        depth = self.depth()                                         # 480×640, mm, 0 = inconnu
        d = depth[::4, ::4].astype(np.float32)                       # 120×160, suffisant
        if self.a.keep_sessions:
            self.ring.append(d.astype(np.uint16)); del self.ring[:-600]      # ~20 s
        if self.learn_at and time.time() >= self.learn_at:      # demandé depuis la page
            self.learn_at, self.bg = 0, self.background(d, force=True)
        if self.bg is None:
            self.bg = self.background(d)
        zone = (d > self.near) & (d < self.far)
        # Ne garde que ce qui est nettement devant le décor appris
        mask = zone & (self.bg > 0) & (d < self.bg - self.a.bg_margin * 1000)
        # Décor inconnu (0, instable) : accepté seulement dans les colonnes d'une personne déjà vue
        cols = np.convolve(mask.any(0), np.ones(7), "same") > 0
        mask |= zone & (self.bg == 0) & cols[None, :]
        if not mask.any():
            self.st = {}
        bodies = silhouette(mask, d, self.mirror, self.st)
        if not bodies:
            self.st = {}                                        # personne : le suivi des mains repart de zéro
        return bodies

    def save_session(self):
        """Garde sur disque les 20 dernières secondes de profondeur (diagnostic d'une session ratée)."""
        import glob, os
        d = os.path.expanduser("~/.cache/bip2026/sessions")
        os.makedirs(d, exist_ok=True)
        np.savez_compressed(os.path.join(d, time.strftime("session-%H%M%S.npz")), depth=np.stack(self.ring), bg=self.bg)
        for old in sorted(glob.glob(d + "/session-*.npz"))[:-self.a.keep_sessions]:
            os.remove(old)

    def background(self, first, force=False):
        """Décor vide : relu du fichier, sinon appris maintenant (personne devant la Kinect !)."""
        import os
        path = os.path.expanduser(self.a.background)
        if not force and not self.a.learn_background and os.path.exists(path):
            bg = np.load(path)
            if bg.shape == first.shape:
                return bg
        print("Apprentissage du décor vide (2 s)…", flush=True)
        frames = np.stack([first] + [self.depth()[::4, ::4].astype(np.float32) for _ in range(59)])
        seen = frames > 0
        frames[~seen] = np.nan
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                bg = np.nanmedian(frames, axis=0)
        bg = np.where(seen.mean(0) > 0.3, np.nan_to_num(bg), 0).astype(np.float32)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.save(path, bg)
        print("Décor enregistré dans", path, flush=True)
        return bg


def blob(mask):
    """Plus gros objet d'un seul tenant : part de la colonne la plus remplie et s'étend de proche en proche."""
    x = int(mask.sum(0).argmax())
    rows = np.nonzero(mask[:, x])[0]
    if not len(rows):
        return mask
    reg = np.zeros_like(mask)
    reg[rows[len(rows) // 2], x] = True
    n = 0
    while True:
        g = reg.copy()
        for _ in range(2):                       # 2 pas de dilatation par tour
            g[1:] |= g[:-1]; g[:-1] |= g[1:]; g[:, 1:] |= g[:, :-1]; g[:, :-1] |= g[:, 1:]
            g &= mask
        m = int(g.sum())
        if m == n:
            return g
        reg, n = g, m


def silhouette(mask, depth, mirror, st=None):
    """Tête, mains, pieds d'une personne debout, tirés de sa silhouette (pas de squelette avec libfreenect).
    On repère le torse, puis : tête = sommet au-dessus du torse ; mains = bout des bras, c.-à-d. le point
    le plus loin des épaules hors du torse (main au repos le long de la hanche si le bras est collé au corps) ;
    pieds = points les plus loin du bassin sous les genoux.
    Une main passée devant le torse (bras croisés) ne dépasse plus de la silhouette : on la retrouve par la
    profondeur (plus proche que le torse). `st` (dict gardé d'une image à l'autre) permet de suivre chaque
    main par continuité, pour qu'elles puissent se croiser sans échanger leurs noms."""
    h, w = mask.shape
    if mask.sum() < h * w * 0.01:
        return []
    # Isolation à demi-résolution (4× moins de calcul), puis retour à la silhouette fine
    small = mask[: h // 2 * 2, : w // 2 * 2].reshape(h // 2, 2, w // 2, 2).any((1, 3))
    keep = np.zeros_like(mask)
    keep[: h // 2 * 2, : w // 2 * 2] = np.kron(blob(small), np.ones((2, 2), bool))
    mask = mask & keep
    ys, xs = np.nonzero(mask)
    if len(xs) < h * w * 0.01:
        return []
    bot = ys.max()
    # Axe du corps : médiane des colonnes dans la moitié basse (les bras n'y pèsent pas)
    cx = float(np.median(xs[ys > (ys.min() + bot) / 2]))
    core = np.abs(xs - cx) <= 3
    top = ys[core].min() if core.any() else ys.min()          # sommet de la tête, même bras levés
    if bot - top < h * 0.25 or top <= 1:                        # trop petit, ou tête hors champ (trop près)
        return []
    z = float(np.median(depth[mask])) / 1000
    # Taille du corps en pixels. Pieds visibles : mesurée. Corps coupé par le bas de l'image (personne
    # trop près) : estimée d'après la distance (focale Kinect ≈ 0,9 × largeur d'image, adulte ≈ 1,7 m).
    cut = bot >= h - 2
    hh = max(float(bot - top), 1.7 * 0.9 * w / z) if cut and z > 0 else float(bot - top)
    dx, dy = xs - cx, ys - top

    def pt(x, y):
        x = float(x) / (w - 1)
        return [round(1 - x if mirror else x, 4), round(float(y) / (h - 1), 4)]

    def far(sel, ox, oy):
        """Moyenne des points sélectionnés les plus éloignés de (ox, oy), en pixels ; None si trop peu."""
        if sel.sum() < 4:
            return None
        d = (xs[sel] - ox) ** 2 + (ys[sel] - oy) ** 2
        k = np.argsort(d)[-max(3, len(d) // 12):]
        return (float(xs[sel][k].mean()), float(ys[sel][k].mean()))

    sh_y, hip_y = top + 0.19 * hh, top + 0.52 * hh
    j = {"head": pt(cx, top + 0.06 * hh), "neck": pt(cx, top + 0.15 * hh), "hip": pt(cx, hip_y)}
    tips, rest, feet = [], [], []
    for side in (-1, 1):
        sx = cx + side * 0.11 * hh                              # épaule
        j["shoulder" + ("L" if (side < 0) != mirror else "R")] = pt(sx, sh_y)
        s_ = dx * side
        # Bras : à l'écart du torse au-dessus du bassin, ou au-dessus des épaules à côté de la tête
        arm = ((s_ > 0.15 * hh) & (dy < 0.62 * hh)) | ((s_ > 0.08 * hh) & (dy < 0.12 * hh))
        tips.append(far(arm, sx, sh_y))
        rest.append((cx + side * 0.16 * hh, min(hip_y, h - 1.0)))   # main au repos, le long de la hanche
        leg = (s_ >= 0) & (dy > 0.75 * hh)
        if not cut:                                             # pas de pieds si les jambes sortent du champ
            f = far(leg, cx, hip_y) or (cx + side * 0.06 * hh, bot)
            feet.append(pt(*f))
    st = st if st is not None else {}
    prev, lost = st.get("hands"), st.get("lost", [0, 0])
    hands = list(tips)                                          # un bras qui dépasse d'un côté = la main de ce côté
    free = [i for i in (0, 1) if hands[i] is None]
    if free:
        # Mains devant le torse (bras croisés, main tendue vers la Kinect) : zones nettement plus proches
        # que le torse à la même hauteur (comparaison ligne par ligne, insensible au buste penché).
        torso = (np.abs(dx) <= 0.15 * hh) & (dy > 0.12 * hh) & (dy < 0.62 * hh)
        dz = depth[ys, xs]
        front = np.zeros(len(xs), bool)
        for y in np.unique(ys[torso]):
            row = torso & (ys == y) & (dz > 0)
            if row.sum() >= 4:
                front |= row & (dz < np.median(dz[row]) - 70)
        cand = []
        if front.sum() >= 12:
            fx, fy = xs[front], ys[front]
            lo, hi = np.percentile(fx, [20, 80])
            if hi - lo > 0.12 * hh and len(free) == 2:          # étalé : deux avant-bras croisés
                cand = [(float(fx[fx <= lo].mean()), float(fy[fx <= lo].mean())),
                        (float(fx[fx >= hi].mean()), float(fy[fx >= hi].mean()))]
            else:                                               # groupé : une seule main devant
                near = dz[front] <= np.percentile(dz[front], 30)
                cand = [(float(fx[near].mean()), float(fy[near].mean()))]
        # Attribution par continuité : la combinaison la plus proche des positions précédentes
        ref = prev or rest
        dist = lambda p, q: math.hypot(p[0] - q[0], p[1] - q[1])
        best = None
        for combo in ([(None, None)] + [(c, None) for c in cand] + [(None, c) for c in cand]
                      + [(c, e) for c in cand for e in cand if c is not e]):
            if any(combo[i] is not None and i not in free for i in (0, 1)):
                continue
            used = sum(c is not None for c in combo)
            cost = sum(dist(ref[i], combo[i]) for i in free if combo[i] is not None) + 0.5 * hh * (len(cand) - used)
            if best is None or cost < best[0]:
                best = (cost, combo)
        for i in free:
            hands[i] = best[1][i]
    for i in (0, 1):
        # Main perdue un instant (entre le côté et le devant du corps) : on garde sa position 5 images
        lost[i] = 0 if hands[i] is not None else lost[i] + 1
        if hands[i] is None:
            hands[i] = prev[i] if prev and lost[i] <= 5 else rest[i]
    st["hands"], st["lost"] = hands, lost
    # hands[0] est partie du côté gauche de l'image : main droite de l'écran si l'image est en miroir
    names = ("handR", "handL") if mirror else ("handL", "handR")
    j[names[0]], j[names[1]] = pt(*hands[0]), pt(*hands[1])
    if feet:
        feet.sort()
        j.update(footL=feet[0], footR=feet[1])
    # "rest" : mains non vues sur cette image (position de repos ou gardée) ; la page ne trace pas d'encre pour elles
    return [{"center": j["hip"], "z": round(z, 2), "joints": j, "rest": [names[i] for i in (0, 1) if lost[i] > 0]}]


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
            # {"cmd": "learn", "delay": 5} : réapprend le décor vide après le délai (le temps de sortir du champ)
            async for raw in ws:
                try:
                    m = json.loads(raw)
                    if m.get("cmd") == "session" and getattr(src, "ring", None) and a.keep_sessions:
                        asyncio.get_running_loop().run_in_executor(None, src.save_session)
                    if m.get("cmd") == "learn" and hasattr(src, "learn_at"):
                        src.learn_at = time.time() + float(m.get("delay", 5))
                        print("Décor : réapprentissage demandé", flush=True)
                except (ValueError, AttributeError):
                    pass
        finally:
            clients.discard(ws)

    async with websockets.serve(handler, a.host, a.port):
        print(f"Pont {a.source} sur ws://{a.host}:{a.port}")
        while True:
            t = time.time()
            bodies = await asyncio.to_thread(src.read)
            # Lissage exponentiel des articulations (le capteur tremble)
            for b in bodies:
                for k in b.get("rest", ()):
                    smooth.pop(k, None)                     # main non vue : elle repartira de sa vraie position
                for k, p in b["joints"].items():
                    q = smooth.get(k, p)
                    # Pas borné : un point qui saute d'un coup (faux contour) est rattrapé en douceur
                    step = lambda d: max(-a.max_step, min(a.max_step, a.smooth * d))
                    smooth[k] = p = [q[0] + step(p[0] - q[0]), q[1] + step(p[1] - q[1])]
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
    ap.add_argument("--background", default="~/.cache/bip2026/kinect-fond.npy",
                    help="fichier du décor vide (source freenect), appris au premier lancement")
    ap.add_argument("--learn-background", action="store_true", help="réapprend le décor vide au lancement")
    ap.add_argument("--bg-margin", type=float, default=0.2, help="écart mini devant le décor (m)")
    ap.add_argument("--keep-sessions", type=int, default=0, help="garde les N dernières sessions (profondeur) pour diagnostic")
    ap.add_argument("--smooth", type=float, default=0.5, help="0..1, plus bas = plus lisse")
    ap.add_argument("--max-step", type=float, default=0.08, help="déplacement maxi d'un point par image (0..1)")
    ap.add_argument("--camera", type=int, default=0, help="index webcam (source webcam)")
    ap.add_argument("--no-mirror", action="store_true")
    asyncio.run(main(ap.parse_args()))
