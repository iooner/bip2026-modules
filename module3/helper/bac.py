"""Module 3 · repérage du bac par sa bordure orange (OpenCV), pour le mode webcam de helper.py.

  python3 bac.py [/dev/video0]      # essai : écrit /tmp/bac-debug.jpg (bac en vert) et affiche la cadence
"""
import cv2, numpy as np

# Bordure orange-rouge très saturée (teinte OpenCV 0…180). À réajuster sur le bac définitif (orange fluo).
HUE_MAX, HUE_WRAP, SAT_MIN, VAL_MIN = 13, 172, 110, 110
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


def detect(frame, info=None):
    """Renvoie les 4 coins du bac (pixels de `frame`, ordonnés) ou None s'il est absent ou coupé.
    Si `info` est un dict, y range "orange" : la part de l'image couverte par le plus grand morceau
    de bordure (enveloppe comprise), pour savoir si le bac est encore là quand il n'est pas repéré."""
    k = WORK_W / frame.shape[1]
    small = cv2.resize(frame, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    h, w = small.shape[:2]
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (0, SAT_MIN, VAL_MIN), (HUE_MAX, 255, 255)) | \
        cv2.inRange(hsv, (HUE_WRAP, SAT_MIN, VAL_MIN), (180, 255, 255))
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


def redresse(frame, quad, inset=0.01):
    """Photo du seul bac, remise droite. `inset` rogne la bordure (fraction de chaque côté)."""
    q = order(quad)
    q = q + (q.mean(0) - q) * 2 * inset
    w = int(max(np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[3])))
    h = int(max(np.linalg.norm(q[3] - q[0]), np.linalg.norm(q[2] - q[1])))
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], np.float32)
    return cv2.warpPerspective(frame, cv2.getPerspectiveTransform(q, dst), (w, h))


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
