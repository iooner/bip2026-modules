#!/usr/bin/env python3
"""Serveur local du module 2 (360°), à lancer sur la borne.

Sert l'app (index.html…) sur http://127.0.0.1:<port>/ et relaie les snapshots des caméras IP :
GET /snap/1 … /snap/4 -> image JPEG de la caméra correspondante (cameras.json).
Le navigateur ne peut pas appeler les caméras directement (CORS, identifiants), d'où ce relais.
Python 3 seul, aucune dépendance.
"""
import json
import pathlib
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "cameras.json").read_text(encoding="utf-8"))
CAMS = CFG["cameras"]
TIMEOUT = CFG.get("timeout_s", 4)


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
            with OPENERS[i].open(CAMS[i]["url"], timeout=TIMEOUT) as r:
                data, ctype = r.read(), r.headers.get("Content-Type", "image/jpeg")
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
