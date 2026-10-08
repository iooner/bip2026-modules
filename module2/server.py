#!/usr/bin/env python3
"""Serveur local du module 2 (360°), à lancer sur la borne.

Sert l'app (index.html…) sur http://127.0.0.1:<port>/ et relaie les snapshots des caméras IP :
GET /snap/1 … /snap/4 -> image JPEG de la caméra correspondante (cameras.json).
Le navigateur ne peut pas appeler les caméras directement (CORS, identifiants), d'où ce relais.
URL http(s):// : image snapshot de la caméra. URL rtsp:// (Tapo C110…) : flux lu en continu par ffmpeg
(sudo apt install ffmpeg), la dernière image est gardée en mémoire et servie tout de suite.
Sinon Python 3 seul, aucune dépendance.
"""
import json
import pathlib
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "cameras.json").read_text(encoding="utf-8"))
CAMS = CFG["cameras"]
# Identifiants hors dépôt : cameras.secret.json (ignoré par git) = {"user": "…", "password": "…"},
# appliqués aux caméras dont user est vide dans cameras.json.
SECRET = HERE / "cameras.secret.json"
if SECRET.exists():
    _s = json.loads(SECRET.read_text(encoding="utf-8"))
    for _c in CAMS:
        if not _c.get("user"):
            _c["user"], _c["password"] = _s.get("user", ""), _s.get("password", "")
TIMEOUT = CFG.get("timeout_s", 8)
LIVE = CFG.get("live", True)              # connexion RTSP permanente (sinon une connexion par photo)
DECODE = CFG.get("decode", "key")         # "key" : images clés seules (peu de CPU) ; "all" : toutes
LIVE_FPS = CFG.get("live_fps", 4)         # en mode "all" : images gardées par seconde
SNAP_WAIT = CFG.get("snap_wait_s", 2)     # attente max d'une image prise après le clic
STALE = 10                                # au-delà (s), la dernière image est trop vieille


def rtsp_url(cam):
    """URL rtsp:// avec user / password insérés (échappés) s'ils ne sont pas déjà dans l'URL."""
    url = cam["url"]
    if cam.get("user") and "@" not in url:
        auth = urllib.parse.quote(cam["user"], safe="") + ":" + urllib.parse.quote(cam.get("password", ""), safe="")
        url = url.replace("rtsp://", f"rtsp://{auth}@", 1)
    return url


def grab_rtsp(cam):
    """Une image JPEG du flux RTSP via ffmpeg.

    select=I : garde la première image clé (complète), jamais une image baveuse prise entre deux.
    -q:v 1 : JPEG qualité max, à la pleine résolution du flux (stream1 = 2304×1296 sur C110).
    """
    url = rtsp_url(cam)
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-rtsp_transport", "tcp", "-analyzeduration", "0",
           "-i", url, "-vf", r"select=eq(pict_type\,I)", "-frames:v", "1", "-q:v", "1",
           "-f", "image2", "-vcodec", "mjpeg", "pipe:1"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"pas d'image après {TIMEOUT} s") from None
    if r.returncode or not r.stdout:
        err = r.stderr.decode(errors="replace").replace(url, cam["url"])   # masque le mot de passe
        raise RuntimeError(err.strip().splitlines()[-1] if err.strip() else "ffmpeg sans image")
    return r.stdout, "image/jpeg"


class Live(threading.Thread):
    """Lit un flux RTSP en continu (ffmpeg -> JPEG) et garde la dernière image en mémoire."""

    def __init__(self, n, cam):
        super().__init__(daemon=True)
        self.n, self.cam, self.url = n, cam, rtsp_url(cam)
        self.frame, self.at, self.error = None, 0.0, "connexion en cours"
        self.cond = threading.Condition()

    def cmd(self):
        c = ["ffmpeg", "-nostdin", "-loglevel", "error", "-rtsp_transport", "tcp"]
        if DECODE == "key":
            c += ["-skip_frame", "nokey"]
        c += ["-i", self.url]
        # key : sans passthrough, ffmpeg répète chaque image clé pour garder 15 i/s (CPU x15)
        c += ["-fps_mode", "passthrough"] if DECODE == "key" else ["-vf", f"fps={LIVE_FPS}"]
        return c + ["-q:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1"]

    def run(self):
        while True:
            p = subprocess.Popen(self.cmd(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            threading.Thread(target=self.drain, args=(p,), daemon=True).start()
            threading.Thread(target=self.watch, args=(p, time.monotonic()), daemon=True).start()
            buf = b""
            while True:
                chunk = p.stdout.read1(1 << 16)
                if not chunk:
                    break
                buf += chunk
                while True:   # découpe le flux en JPEG (FFD8 … FFD9)
                    a = buf.find(b"\xff\xd8")
                    e = buf.find(b"\xff\xd9", a + 2) if a >= 0 else -1
                    if e < 0:
                        break
                    with self.cond:
                        self.frame, self.at, self.error = buf[a:e + 2], time.monotonic(), None
                        self.cond.notify_all()
                    buf = buf[e + 2:]
                if len(buf) > 8 << 20:
                    buf = b""
            p.kill(); p.wait()
            print(f"caméra {self.n} : flux coupé ({self.error or 'fin du flux'}), reconnexion", flush=True)
            time.sleep(2)

    def watch(self, p, started):
        """Relance ffmpeg si plus aucune image n'arrive (caméra débranchée, réseau coupé…)."""
        while p.poll() is None:
            time.sleep(2)
            if time.monotonic() - max(self.at, started) > STALE + 5:
                self.error = "plus d'image"
                p.kill()

    def drain(self, p):
        for line in p.stderr:
            self.error = line.decode(errors="replace").strip().replace(self.url, self.cam["url"])

    def snap(self):
        """Image prise après la demande (attente max SNAP_WAIT), sinon la dernière si récente."""
        t = time.monotonic()
        with self.cond:
            self.cond.wait_for(lambda: self.at > t, timeout=SNAP_WAIT)
            if self.frame and time.monotonic() - self.at < STALE:
                return self.frame, "image/jpeg"
        raise RuntimeError(self.error or "pas d'image récente")


def grab_http(i):
    with OPENERS[i].open(CAMS[i]["url"], timeout=TIMEOUT) as r:
        return r.read(), r.headers.get("Content-Type", "image/jpeg")


def opener(cam):
    """Opener urllib avec authentification Basic ou Digest si user est renseigné."""
    handlers = []
    if cam.get("user"):
        pm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        pm.add_password(None, cam["url"], cam["user"], cam.get("password", ""))
        handlers = [urllib.request.HTTPBasicAuthHandler(pm), urllib.request.HTTPDigestAuthHandler(pm)]
    return urllib.request.build_opener(*handlers)


OPENERS = [opener(c) for c in CAMS]
LIVES = {}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path.startswith("/snap/"):
            return self.snap(path[6:])
        if path.endswith(".json") or path.endswith(".py"):   # identifiants des caméras
            return self.send_error(404)
        return super().do_GET()

    def snap(self, n):
        if not n.isdigit() or not 1 <= int(n) <= len(CAMS):
            return self.send_error(404)
        i = int(n) - 1
        if not CAMS[i].get("url"):
            return self.send_error(503, f"camera {n} not configured")
        try:
            if i in LIVES:
                data, ctype = LIVES[i].snap()
            elif CAMS[i]["url"].startswith("rtsp://"):
                data, ctype = grab_rtsp(CAMS[i])
            else:
                data, ctype = grab_http(i)
        except Exception as e:  # caméra éteinte, mauvaise adresse, délai dépassé…
            self.log_message("caméra %s : %s", n, e)
            return self.send_error(502, f"camera {n} unreachable")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    port = CFG.get("port", 8360)
    print(f"Module 2 : http://127.0.0.1:{port}/")
    for i, cam in enumerate(CAMS):
        if LIVE and cam.get("url", "").startswith("rtsp://"):
            LIVES[i] = Live(i + 1, cam)
            LIVES[i].start()
    ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(HERE))).serve_forever()
