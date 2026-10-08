#!/usr/bin/env python3
"""Serveur local du module 2 (360°), à lancer sur la borne.

Sert l'app (index.html…) sur http://127.0.0.1:<port>/ et relaie les snapshots des caméras IP :
GET /snap/1 … /snap/4 -> image JPEG de la caméra correspondante (cameras.json).
Le navigateur ne peut pas appeler les caméras directement (CORS, identifiants), d'où ce relais.
URL http(s):// : image snapshot de la caméra. URL rtsp:// (Tapo C110…) : une image extraite du flux
par ffmpeg (sudo apt install ffmpeg). Sinon Python 3 seul, aucune dépendance.
"""
import json
import pathlib
import subprocess
import urllib.parse
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "cameras.json").read_text(encoding="utf-8"))
CAMS = CFG["cameras"]
TIMEOUT = CFG.get("timeout_s", 6)


def rtsp_url(cam):
    """URL rtsp:// avec user / password insérés (échappés) s'ils ne sont pas déjà dans l'URL."""
    url = cam["url"]
    if cam.get("user") and "@" not in url:
        auth = urllib.parse.quote(cam["user"], safe="") + ":" + urllib.parse.quote(cam.get("password", ""), safe="")
        url = url.replace("rtsp://", f"rtsp://{auth}@", 1)
    return url


def grab_rtsp(cam):
    """Une image JPEG du flux RTSP via ffmpeg."""
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-rtsp_transport", "tcp", "-i", rtsp_url(cam),
           "-frames:v", "1", "-q:v", "2", "-f", "image2", "-vcodec", "mjpeg", "pipe:1"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"pas d'image après {TIMEOUT} s") from None
    if r.returncode or not r.stdout:
        err = r.stderr.decode(errors="replace").replace(cmd[7], cam["url"])   # masque le mot de passe
        raise RuntimeError(err.strip().splitlines()[-1] if err.strip() else "ffmpeg sans image")
    return r.stdout, "image/jpeg"


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
            if CAMS[i]["url"].startswith("rtsp://"):
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
    ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(HERE))).serve_forever()
