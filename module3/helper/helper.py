#!/usr/bin/env python3
"""Module 3 · Vide ton sac : petit serveur local du Raspberry Pi.

Surveille un GPIO (le bac entre dans le faux scanner), prend une photo avec la Pi Camera
et prévient la page web (index.html) par Server-Sent Events. Aucune dépendance hors
Raspberry Pi OS (python3-gpiozero et python3-picamera2 y sont préinstallés).

  python3 helper.py                 # GPIO 17 vers la masse, Pi Camera
  python3 helper.py --sim           # sans Pi : images d'exemple, Entrée = passage

Points d'accès (http://127.0.0.1:8765) :
  GET  /events          flux SSE : « trigger » puis « photo » {"url": "/photo/N.jpg"} ou « failed »
  POST /trigger         simule le GPIO (touche Espace de la page, tests)
  GET  /photo/N.jpg     dernière photo
"""
import argparse, io, json, os, queue, shutil, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = [os.path.join(HERE, "..", "assets", f"sample-{i}.svg") for i in (1, 2, 3)]

clients, clients_lock = [], threading.Lock()
photo = {"n": 0, "data": b"", "type": "image/jpeg"}
busy = threading.Lock()


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def broadcast(event, data=None):
    msg = f"event: {event}\ndata: {json.dumps(data or {})}\n\n".encode()
    with clients_lock:
        for q in clients:
            q.put(msg)


# --- Caméra -----------------------------------------------------------------
class Camera:
    def __init__(self, args):
        self.args, self.cam = args, None
        if args.sim:
            return
        try:
            from picamera2 import Picamera2
            self.cam = Picamera2()
            self.cam.configure(self.cam.create_still_configuration(main={"size": (args.width, args.height)}))
            self.cam.start()
            time.sleep(1)  # réglage auto de l'exposition
            log("Caméra : picamera2", args.width, "x", args.height)
        except Exception as e:  # pas de picamera2 : on passera par la commande rpicam-still
            log("picamera2 indisponible :", e)
            self.cam = None
            self.cli = shutil.which("rpicam-still") or shutil.which("libcamera-still")
            log("Caméra : commande", self.cli or "introuvable")

    def capture(self):
        """Renvoie (octets, type MIME)."""
        if self.args.sim:
            path = SAMPLES[photo["n"] % len(SAMPLES)]
            return open(path, "rb").read(), "image/svg+xml"
        if self.cam:
            buf = io.BytesIO()
            self.cam.capture_file(buf, format="jpeg")
            return buf.getvalue(), "image/jpeg"
        if not self.cli:
            raise RuntimeError("aucune caméra")
        out = subprocess.run([self.cli, "-n", "--immediate", "-t", "1", "--width", str(self.args.width),
                              "--height", str(self.args.height), "-e", "jpg", "-o", "-"],
                             capture_output=True, timeout=15, check=True)
        return out.stdout, "image/jpeg"


def on_trigger(camera, args):
    """Un passage : prévient la page, attend que le bac soit en place, photographie."""
    if not busy.acquire(blocking=False):
        return  # passage déjà en cours
    def run():
        try:
            log("Déclenchement")
            broadcast("trigger")
            time.sleep(args.delay)
            data, mime = camera.capture()
            photo.update(n=photo["n"] + 1, data=data, type=mime)
            ext = "svg" if "svg" in mime else "jpg"
            broadcast("photo", {"url": f"/photo/{photo['n']}.{ext}"})
            log("Photo", photo["n"], len(data), "octets")
        except Exception as e:
            log("Échec de la capture :", e)
            broadcast("failed", {"error": str(e)})
        finally:
            time.sleep(args.cooldown)
            busy.release()
    threading.Thread(target=run, daemon=True).start()


# --- Serveur HTTP -----------------------------------------------------------
def make_handler(camera, args):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def head(self, code, mime, extra=()):
            self.send_response(code)
            self.send_header("Access-Control-Allow-Origin", "*")  # la page est ouverte en file://
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            for k, v in extra:
                self.send_header(k, v)
            self.end_headers()

        def do_OPTIONS(self):
            self.head(204, "text/plain", [("Access-Control-Allow-Methods", "GET, POST")])

        def do_POST(self):
            if self.path == "/trigger":
                on_trigger(camera, args)
                self.head(202, "application/json"); self.wfile.write(b"{}")
            else:
                self.head(404, "text/plain")

        def do_GET(self):
            if self.path == "/events":
                q = queue.Queue()
                with clients_lock:
                    clients.append(q)
                self.head(200, "text/event-stream")
                try:
                    self.wfile.write(b"retry: 2000\n\n"); self.wfile.flush()
                    while True:
                        try:
                            msg = q.get(timeout=15)
                        except queue.Empty:
                            msg = b": ping\n\n"  # détecte les pages fermées
                        self.wfile.write(msg); self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    with clients_lock:
                        clients.remove(q)
            elif self.path.startswith("/photo/") and photo["data"]:
                self.head(200, photo["type"]); self.wfile.write(photo["data"])
            elif self.path == "/health":
                self.head(200, "application/json")
                self.wfile.write(json.dumps({"ok": True, "photos": photo["n"], "sim": args.sim}).encode())
            else:
                self.head(404, "text/plain")
    return H


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pin", type=int, default=17, help="GPIO (BCM) du capteur, défaut 17")
    p.add_argument("--active-high", action="store_true",
                   help="capteur qui envoie 3,3 V (défaut : contact vers la masse, pull-up interne)")
    p.add_argument("--delay", type=float, default=0.4, help="attente avant la photo (s)")
    p.add_argument("--cooldown", type=float, default=6, help="délai minimal entre deux passages (s)")
    p.add_argument("--width", type=int, default=1640)
    p.add_argument("--height", type=int, default=1232)
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--sim", action="store_true", help="sans GPIO ni caméra : images d'exemple, Entrée = passage")
    args = p.parse_args()

    camera = Camera(args)
    if not args.sim:
        try:
            from gpiozero import Button
            btn = Button(args.pin, pull_up=not args.active_high, bounce_time=0.05)
            btn.when_pressed = lambda: on_trigger(camera, args)
            log(f"GPIO {args.pin} surveillé")
        except Exception as e:
            log("GPIO indisponible :", e, "(déclenchement possible via POST /trigger)")
    else:
        def keyboard():
            for _ in sys.stdin:
                on_trigger(camera, args)
        threading.Thread(target=keyboard, daemon=True).start()
        log("Simulation : Entrée = un passage")

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(camera, args))
    srv.daemon_threads = True
    log(f"Prêt sur http://127.0.0.1:{args.port}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
