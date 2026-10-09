"""Module 3 · repérage du bac par sa bordure orange (OpenCV), pour le mode webcam de helper.py.

  python3 bac.py [/dev/video0]      # essai : écrit /tmp/bac-debug.jpg (bac en vert) et affiche la cadence
"""
import json, os
import cv2, numpy as np

# Couleur de la bordure (teinte OpenCV 0…180, de h_lo à h_hi en passant par 0 si h_lo > h_hi ; saturation et
# luminosité minimales). Par défaut : ruban orange-rouge très saturé. Un autre bac s'apprend depuis la vue de
# réglage de la page (appui de 5 s sur le ✕ de l'accueil), ce qui écrit COLOR_FILE ; le supprimer = défaut.
DEFAULT = {"h_lo": 172, "h_hi": 13, "s_min": 110, "v_min": 110}
COLOR_FILE = os.path.expanduser("~/.config/bip2026/module3-bac.json")
COLOR = dict(DEFAULT)
EMPTY = {"ref": None, "walls": None}   # bac vide, appris avec la couleur : son aspect, et la part de la photo
                                       # occupée par ses parois sur chaque bord (gauche, haut, droite, bas)
EMPTY_DIFF, EMPTY_CELLS = 20, 4   # « pas vide » : au moins EMPTY_CELLS cases s'écartent de EMPTY_DIFF du bac vide
try:
    _saved = json.load(open(COLOR_FILE))
    COLOR.update({k: int(v) for k, v in _saved.items() if k in DEFAULT})
    if len(_saved.get("empty") or []) == 96 * 60:
        EMPTY["ref"] = np.array(_saved["empty"], np.float32).reshape(60, 96)
    if len(_saved.get("walls") or []) == 4:
        EMPTY["walls"] = [float(v) for v in _saved["walls"]]
except (OSError, ValueError):
    pass
AREA_MIN, AREA_MAX = 0.08, 0.90   # part de l'image occupée par le bac
EDGE_MARGIN = 0.01                # un coin plus près du bord de l'image = bac coupé, on l'ignore
WORK_W = 640                      # largeur de travail : la détection n'a pas besoin de plus


def _rect(pts):
    """Part du rectangle englobant remplie par l'enveloppe des points (1 = rectangle parfait)."""
    hull = cv2.convexHull(pts)
    (_, (w, h), _) = cv2.minAreaRect(hull)
    return cv2.contourArea(hull) / max(w * h, 1)


def order(q):
    """Coins dans l'ordre haut-gauche, haut-droit, bas-droit, bas-gauche."""
    q = np.asarray(q, np.float32).reshape(4, 2)
    s, d = q.sum(1), q[:, 0] - q[:, 1]
    return np.array([q[s.argmin()], q[d.argmax()], q[s.argmax()], q[d.argmin()]], np.float32)


def _mask(hsv, c):
    """Pixels de la couleur `c` (la plage de teinte peut passer par 0)."""
    lo, hi, s, v = c["h_lo"], c["h_hi"], c["s_min"], c["v_min"]
    if lo <= hi:
        return cv2.inRange(hsv, (lo, s, v), (hi, 255, 255))
    return cv2.inRange(hsv, (0, s, v), (hi, 255, 255)) | cv2.inRange(hsv, (lo, s, v), (180, 255, 255))


def detect(frame, info=None, color=None, ring_only=False):
    """Renvoie les 4 coins du bac (pixels de `frame`, ordonnés) ou None s'il est absent ou coupé.
    Si `info` est un dict, y range "orange" : la part de l'image couverte par le plus grand morceau
    de bordure (enveloppe comprise), pour savoir si le bac est encore là quand il n'est pas repéré.
    `color` : autre couleur que COLOR ; `ring_only` : n'accepter qu'une bordure qui fait le tour complet."""
    k = WORK_W / frame.shape[1]
    small = cv2.resize(frame, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    h, w = small.shape[:2]
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    m = _mask(hsv, color or COLOR)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if info is not None:
        info["orange"] = max((cv2.contourArea(cv2.convexHull(c)) for c in cs), default=0) / (w * h)
    if hier is None:
        return None
    # cas normal : la bordure fait le tour complet, l'intérieur du bac est le « trou » de l'anneau orange
    # (insensible à ce qui est orange autour du bac)
    holes = [c for c, hh in zip(cs, hier[0]) if hh[3] >= 0 and AREA_MIN < cv2.contourArea(c) / (w * h) < AREA_MAX]
    holes = [c for c in holes if _rect(c) >= 0.85]
    if holes:
        return _quad(cv2.convexHull(max(holes, key=cv2.contourArea)), w, h, k)
    if ring_only:
        return None
    # sinon la bordure peut être coupée en morceaux (main, reflet) : on garde les longs morceaux
    cs = [c for c, hh in zip(cs, hier[0]) if hh[3] < 0 and cv2.arcLength(c, False) > 0.15 * h]
    if not cs:
        return None
    # on part du plus grand et on n'ajoute un morceau que s'il rend l'ensemble plus rectangulaire
    # (écarte un objet orange posé à côté du bac)
    cs.sort(key=lambda c: cv2.contourArea(cv2.convexHull(c)), reverse=True)
    pts = cs[0]
    for c in cs[1:]:
        both = np.vstack([pts, c])
        if _rect(both) >= max(_rect(pts), 0.93):
            pts = both
    hull = cv2.convexHull(pts)
    if not AREA_MIN < cv2.contourArea(hull) / (w * h) < AREA_MAX or _rect(pts) < 0.85:
        return None
    return _quad(hull, w, h, k)


def _quad(hull, w, h, k):
    """4 coins ordonnés (pixels de l'image d'origine) à partir d'une enveloppe, None si le bac est coupé."""
    quad = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
    if len(quad) != 4:
        quad = cv2.boxPoints(cv2.minAreaRect(hull))
    quad = order(quad)
    mx, my = EDGE_MARGIN * w, EDGE_MARGIN * h
    if (quad[:, 0] < mx).any() or (quad[:, 0] > w - mx).any() or (quad[:, 1] < my).any() or (quad[:, 1] > h - my).any():
        return None
    return quad / k


def cases(frame, quad):
    """Intérieur du bac en 96×60 cases de gris (médiane retirée) : assez fin pour voir une pièce de monnaie."""
    g = cv2.cvtColor(redresse(frame, quad, 0.10), cv2.COLOR_BGR2GRAY)
    g = cv2.resize(cv2.GaussianBlur(g, (0, 0), 2), (96, 60), interpolation=cv2.INTER_AREA).astype(np.float32)
    return g - np.median(g)


def walls(frame, quad):
    """Sur un bac vide : part de la photo redressée occupée, sur chaque bord, par la bordure et les parois.
    La limite entre paroi et fond est le dernier changement net de luminosité en venant du bord.
    Sert à ne garder que le fond du bac sur la photo."""
    g = cv2.GaussianBlur(cv2.cvtColor(redresse(frame, quad, 0), cv2.COLOR_BGR2GRAY), (0, 0), 2).astype(np.float32)
    h, w = g.shape
    out = []
    for prof, n in ((g[h // 5:4 * h // 5].mean(0), w), (g[:, w // 5:4 * w // 5].mean(1), h),
                    (g[h // 5:4 * h // 5].mean(0)[::-1], w), (g[:, w // 5:4 * w // 5].mean(1)[::-1], h)):
        steps = np.nonzero(np.abs(np.diff(prof[:n // 5])) > 2.5)[0]   # cherché dans les 20 % du bord
        out.append(round(float((steps.max() + 1) / n + .012) if len(steps) else .01, 4))
    return out


def is_empty(frame, quad):
    """True si le bac est vide, False s'il contient quelque chose, None si le bac vide n'a pas été appris."""
    if EMPTY["ref"] is None:
        return None
    return int((np.abs(cases(frame, quad) - EMPTY["ref"]) > EMPTY_DIFF).sum()) < EMPTY_CELLS


def learn(frame):
    """Apprend la couleur de la bordure du bac posé sous la caméra : cherche la couleur vive qui dessine un cadre
    fermé et mince autour d'un rectangle, mesure cette couleur sur le cadre lui-même et l'enregistre.
    Renvoie (réussi, message)."""
    k = WORK_W / frame.shape[1]
    small = cv2.resize(frame, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    h, w = small.shape[:2]
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hue, sat, val = cv2.split(hsv)
    vivid = (sat >= 90) & (val >= 80)
    hist = np.bincount(hue[vivid], minlength=180)[:180].astype(np.float32)
    hist = np.convolve(np.r_[hist[-3:], hist, hist[:3]], np.ones(7) / 7, "valid")   # lissage circulaire
    best, tried = None, []
    for peak in np.argsort(hist)[::-1]:
        if hist[peak] < 0.002 * hue.size or len(tried) >= 8:
            break
        if any(min(abs(int(peak) - t), 180 - abs(int(peak) - t)) < 8 for t in tried):
            continue
        tried.append(int(peak))
        for half in (5, 8, 12):   # plage de teinte de plus en plus large autour du pic
            c = {"h_lo": int(peak - half) % 180, "h_hi": int(peak + half) % 180, "s_min": 90, "v_min": 80}
            m = cv2.morphologyEx(_mask(hsv, c), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
            cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            for i, hh in enumerate(hier[0] if hier is not None else []):
                hole = cv2.contourArea(cs[i])
                if hh[3] < 0 or not AREA_MIN < hole / (w * h) < AREA_MAX or _rect(cs[i]) < 0.85:
                    continue
                # un vrai bord de bac est mince : l'intérieur remplit presque tout le cadre (la table qui entoure
                # le bac forme aussi un « cadre », mais très large)
                thin = hole / max(cv2.contourArea(cv2.convexHull(cs[hh[3]])), 1)
                if thin >= 0.6 and (best is None or hole * thin > best[0]):
                    ring = np.zeros((h, w), np.uint8)
                    cv2.drawContours(ring, cs, hh[3], 255, -1)
                    cv2.drawContours(ring, cs, i, 0, -1)
                    best = (hole * thin, c, int(peak), (ring > 0) & (_mask(hsv, c) > 0))
            if best is not None and best[2] == int(peak):
                break
    if best is None:
        return False, "pas de cadre de couleur vive complet : le bac doit etre en entier dans l'image, bordure visible sur les 4 cotes"
    _, c, peak, px = best
    if px.sum() > 200:
        # Resserre la plage sur les pixels du cadre lui-même, du plus strict au plus tolérant : on garde le
        # réglage le plus strict qui retrouve encore le cadre (moins de fausses détections sur la table).
        d = (hue[px].astype(np.int32) - peak + 90) % 180 - 90     # écart de teinte au pic, entre -90 et 90
        for p, ds, dv in ((25, 30, 40), (10, 30, 40), (3, 30, 35)):
            fine = {"h_lo": int(peak + np.percentile(d, p / 2) - 3) % 180, "h_hi": int(peak + np.percentile(d, 100 - p / 2) + 3) % 180,
                    "s_min": max(50, int(np.percentile(sat[px], p)) - ds), "v_min": max(50, int(np.percentile(val[px], p)) - dv)}
            if detect(small, color=fine, ring_only=True) is not None:
                c = fine
                break
    COLOR.clear(); COLOR.update(c)
    # Aspect du bac vide, pour ne pas scanner un bac sans rien dedans : appris seulement si le bac est uni
    # (vide) au moment de l'apprentissage.
    quad = detect(frame)
    ref = cases(frame, quad) if quad is not None else None
    EMPTY["ref"] = ref if ref is not None and ref.std() < 22 else None
    EMPTY["walls"] = walls(frame, quad) if EMPTY["ref"] is not None else None
    os.makedirs(os.path.dirname(COLOR_FILE), exist_ok=True)
    with open(COLOR_FILE, "w") as f:
        json.dump(dict(c, walls=EMPTY["walls"],
                       empty=None if EMPTY["ref"] is None else [int(v) for v in EMPTY["ref"].ravel()]), f)
    return True, (f"bac appris : teinte {c['h_lo']}-{c['h_hi']}, saturation >= {c['s_min']}, luminosite >= {c['v_min']} ; "
                  + ("bac vide appris aussi" if EMPTY["ref"] is not None else
                     "bac vide NON appris (il y a des objets dedans : recommencer avec le bac vide)"))


def forget():
    """Revient à la couleur d'origine (ruban orange)."""
    COLOR.clear(); COLOR.update(DEFAULT)
    EMPTY["ref"] = EMPTY["walls"] = None
    try:
        os.remove(COLOR_FILE)
    except OSError:
        pass
    return True, "couleur d'origine retablie"


def redresse(frame, quad, inset=0.01, crop=None):
    """Photo du seul bac, remise droite. `inset` rogne la bordure (fraction de chaque côté) ; `crop` rogne en plus
    une part de chaque bord (gauche, haut, droite, bas) : les parois du bac, mesurées par walls()."""
    q = order(quad)
    q = q + (q.mean(0) - q) * 2 * (0 if crop else inset)
    w = int(max(np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[3])))
    h = int(max(np.linalg.norm(q[3] - q[0]), np.linalg.norm(q[2] - q[1])))
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], np.float32)
    out = cv2.warpPerspective(frame, cv2.getPerspectiveTransform(q, dst), (w, h))
    if crop:
        left, top, right, bottom = crop
        out = out[int(top * h):h - int(bottom * h), int(left * w):w - int(right * w)]
    return out


def ouvre(dev, size):
    """Webcam en MJPG (seul format qui tient 30 i/s en HD sur USB 2)."""
    cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, size[0]); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


if __name__ == "__main__":
    import sys, time
    cap = ouvre(sys.argv[1] if len(sys.argv) > 1 else "/dev/video0", (1280, 720))
    for _ in range(30):
        cap.read()
    n = found = 0; t0 = time.perf_counter()
    while time.perf_counter() - t0 < 5:
        ok, frame = cap.read()
        if not ok:
            break
        quad = detect(frame); n += 1; found += quad is not None
    if quad is not None:
        cv2.polylines(frame, [quad.astype(np.int32)], True, (0, 255, 0), 4)
    cv2.imwrite("/tmp/bac-debug.jpg", frame)
    print(f"{n / (time.perf_counter() - t0):.1f} i/s, bac trouvé sur {found}/{n} images -> /tmp/bac-debug.jpg")
