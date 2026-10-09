#!/usr/bin/env python3
"""Module 3 · Vide ton sac : petit serveur local de la borne.

Sur Raspberry Pi : surveille un GPIO (le bac entre dans le faux scanner), prend une photo avec la
Pi Camera et prévient la page web (index.html) par Server-Sent Events. Aucune dépendance hors
Raspberry Pi OS (python3-gpiozero et python3-picamera2 y sont préinstallés).

Sur mini PC avec webcam USB (python3-opencv) : pas de capteur. La webcam suit le bac par sa bordure
orange (bac.py) ; dès qu'il est posé et immobile depuis --stable secondes, c'est un passage et la
photo est recadrée sur le bac. Un bac n'est scanné qu'une fois : le passage suivant demande que le bac
sorte du champ, ou qu'il soit poussé par un autre bac au contenu différent.

  python3 helper.py                 # Pi Camera + GPIO 17, sinon webcam si OpenCV est installé
  python3 helper.py --webcam /dev/video0
  python3 helper.py --sim           # sans matériel : images d'exemple, Entrée = passage

Points d'accès (http://127.0.0.1:8765) :
  GET  /events          flux SSE : « trigger » puis « photo » {"url": "/photo/N.jpg"} ou « failed » ;
                        mode webcam : « state » {"code": absent | partial | moving | hold | done}
  POST /trigger         simule le GPIO (touche Espace de la page, tests)
  GET  /photo/N.jpg     dernière photo
  GET  /live.mjpg       mode webcam : petite vidéo en direct pour l'écran des consignes (cadre vert = bac en place)
  GET  /live.mjpg?debug mode webcam : la même en grand, avec l'état du suivi (vue de réglage de la page)
  GET  /debug.jpg       mode webcam : image en direct, bac repéré en vert (réglage de la caméra)
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


class Webcam:
    """Webcam USB : suit le bac en continu et appelle `trigger` quand il est posé et immobile."""
    MOVE = 0.04    # déplacement d'un coin (part de la largeur d'image) qui relance l'attente
    GONE = 0.3     # bac sorti : le plus grand morceau de bordure couvre moins de cette part du bac scanné
    PARTIAL = 0.05  # un morceau de bordure couvre au moins cette part de l'image : bac présent mais coupé
    LOST = 0.4     # bac perdu de vue plus longtemps que ça (s) = dérangé (poussé, bord caché…)
    PUSH = 0.2     # bac déplacé de plus de cette part de sa taille = dérangé
    SAME = 12.0    # écart moyen de gris (0…255) sous lequel deux bacs ont le même contenu
    MOTION = 0.004  # part des pixels du bac qui changent entre deux images : une main bouge dedans

    def __init__(self, args, trigger):
        import cv2, numpy as np
        sys.path.insert(0, HERE)
        import bac
        self.cv2, self.np, self.bac = cv2, np, bac
        self.args, self.trigger = args, trigger
        self.size = tuple(int(v) for v in args.cam_size.lower().split("x"))
        self.lock = threading.Lock()
        self.frame = self.quad = None
        self.info = {}
        self.cap = bac.ouvre(args.webcam, self.size)
        if not self.cap.read()[0]:
            raise RuntimeError(f"webcam {args.webcam} illisible")
        log("Caméra : webcam", args.webcam, args.cam_size, f"(bac immobile {args.stable} s = passage)")
        threading.Thread(target=self.watch, daemon=True).start()

    def empreinte(self, frame, quad):
        """Contenu du bac redressé et réduit (48×30, gris, moyenne retirée) : pour reconnaître un bac déjà scanné."""
        cv2 = self.cv2
        g = cv2.cvtColor(self.bac.redresse(frame, quad, 0.08), cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, (48, 30), interpolation=cv2.INTER_AREA).astype(self.np.float32)
        return g - g.mean()

    def watch(self):
        """Un passage par bac. Après un scan, le suivant n'est possible que si
        - le bac est sorti du champ (plus de grand morceau de bordure pendant --absent secondes), ou
        - le bac a été dérangé (poussé par le suivant : perdu de vue ou déplacé) ET le bac qui s'immobilise
          ensuite n'a pas le même contenu que celui déjà scanné.
        Un bac scanné qu'on bouscule ou dont on cache un bord sans rien y changer n'est donc pas rescanné."""
        cv2, np, bac, args = self.cv2, self.np, self.bac, self.args
        ref, since, gone, lost, prev, quads = None, 0, None, None, None, []
        fps, last, seen = 0.0, time.monotonic(), {}
        shot = None          # dernier bac scanné : empreinte "sig", centre, taille, part de bordure "orange"
        disturbed = False    # ce bac a été perdu de vue ou déplacé depuis son scan
        why = "pret pour un passage"
        code, shown, code_at = "absent", None, 0   # état annoncé à la page (événement « state »)
        while True:
            ok, frame = self.cap.read()
            if not ok:  # webcam débranchée : on la rouvre
                log("Webcam : lecture impossible, nouvel essai")
                time.sleep(2); self.cap.release(); self.cap = bac.ouvre(args.webcam, self.size)
                continue
            now = time.monotonic()
            fps, last = fps * .9 + .1 / max(now - last, 1e-3), now
            quad = bac.detect(frame, seen)
            gray = cv2.cvtColor(cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
            motion = 1.0
            if quad is not None and prev is not None:
                x0, y0 = (quad.min(0) * 320 / frame.shape[1]).astype(int)
                x1, y1 = (quad.max(0) * 320 / frame.shape[1]).astype(int) + 1
                motion = float((cv2.absdiff(gray, prev)[y0:y1, x0:x1] > 18).mean())
            prev = gray
            # Ce que le scanner attend, pour l'écran des consignes : bac absent, coupé par le bord de l'image,
            # encore en mouvement, immobile (le scan arrive) ou déjà scanné. Annoncé une fois stable 0,3 s.
            state = ("absent" if seen["orange"] < self.PARTIAL else "partial") if quad is None else \
                    "done" if shot and not disturbed else \
                    "moving" if ref is None or now - since < .3 else "hold"
            if state != code:
                code, code_at = state, now
            if code != shown and now - code_at >= .3:
                shown = code
                broadcast("state", {"code": code})
            self.info = {"why": why, "motion": motion, "fps": fps, "code": shown,
                         "still": now - since if quad is not None and ref is not None else 0}
            if shot:
                # sorti du champ : il ne reste plus de grand morceau de bordure orange
                away = quad is None and seen["orange"] < shot["orange"] * self.GONE
                gone = (gone or now) if away else None
                lost = (lost or now) if quad is None else None
                if gone and now - gone >= args.absent:
                    shot, disturbed, why = None, False, "pret pour un passage"
                    log("Bac retiré : prêt pour le passage suivant")
                elif not disturbed and ((lost and now - lost >= self.LOST) or (quad is not None and
                        np.linalg.norm(quad.mean(0) - shot["center"]) > self.PUSH * shot["size"])):
                    disturbed, why = True, "bac derange : nouveau scan si le contenu a change"
            if quad is None:
                ref, quads = None, []
            else:
                moved = ref is None or np.abs(quad - ref).max() > self.MOVE * frame.shape[1]
                if moved or motion > self.MOTION:
                    ref, since, quads = quad, now, []
                quads.append(quad)
                # sans page à l'écoute, on attend
                if clients and now - since >= args.stable and (shot is None or disturbed):
                    quad = np.median(quads, axis=0)  # coins lissés sur toute l'attente
                    sig = self.empreinte(frame, quad)
                    diff = float(np.abs(sig - shot["sig"]).mean()) if shot else 255.0
                    place = {"center": quad.mean(0), "size": cv2.contourArea(quad.astype(np.float32)) ** .5, "orange": seen["orange"]}
                    disturbed = False
                    if diff < self.SAME:  # même bac, seulement bousculé : pas de second scan
                        shot.update(place)
                        why = f"meme contenu qu'au dernier scan (ecart {diff:.1f}) : pas de nouveau scan"
                        log(f"Même bac (écart {diff:.1f} < {self.SAME}) : pas de nouveau scan")
                    else:
                        if shot:
                            log(f"Nouveau bac (écart {diff:.1f})")
                        shot = dict(place, sig=sig)
                        why = "scan fait : en attente du bac suivant"
                        with self.lock:
                            self.frame, self.quad = frame, quad
                        self.trigger()
                        continue
            with self.lock:
                self.frame, self.quad = frame, quad

    def capture(self):
        """Renvoie (octets, type MIME) : le bac redressé, ou l'image entière s'il n'est pas repéré."""
        with self.lock:
            frame, quad = self.frame, self.quad
        if frame is None:
            raise RuntimeError("pas encore d'image de la webcam")
        img = self.bac.redresse(frame, quad, self.args.inset) if quad is not None else frame
        return self.cv2.imencode(".jpg", img, [self.cv2.IMWRITE_JPEG_QUALITY, 90])[1].tobytes(), "image/jpeg"

    def live(self, debug=False):
        """Image en direct, cadre vert quand le bac est bien placé. Petite pour l'écran des consignes ;
        `debug` : grande, avec l'état du suivi (vue de réglage de la page, appui long sur le ✕)."""
        cv2 = self.cv2
        with self.lock:
            frame, quad = self.frame, self.quad
        if frame is None:
            return b""
        k = (960 if debug else 384) / frame.shape[1]
        small = cv2.resize(frame, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        if quad is not None:
            cv2.polylines(small, [(quad * k).astype(self.np.int32)], True, (111, 212, 43), 4)
        if debug:  # texte sans accents : la police d'OpenCV ne les connaît pas
            i = self.info
            lines = ["BAC EN PLACE" if quad is not None else "PAS DE BAC (absent, ou un bord hors de l'image)",
                     f"mouvement dans le bac : {i.get('motion', 0) * 100:.1f} %  (seuil {self.MOTION * 100:.1f} %)",
                     f"immobile depuis {i.get('still', 0):.1f} s  (passage a {self.args.stable} s)",
                     i.get("why", ""),
                     f"{i.get('fps', 0):.0f} images/s   {frame.shape[1]}x{frame.shape[0]}"]
            for n, text in enumerate(lines):
                for color, thick in (((0, 0, 0), 5), ((255, 255, 255), 2)):
                    cv2.putText(small, text, (16, 34 + 30 * n), cv2.FONT_HERSHEY_SIMPLEX, .75, color, thick, cv2.LINE_AA)
        return cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])[1].tobytes()

    def debug(self):
        with self.lock:
            frame, quad = self.frame, self.quad
        if frame is None:
            return b""
        frame = frame.copy()
        if quad is not None:
            self.cv2.polylines(frame, [quad.astype(self.np.int32)], True, (0, 255, 0), 4)
        return self.cv2.imencode(".jpg", frame)[1].tobytes()


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
                    code = getattr(camera, "info", {}).get("code")
                    if code:  # mode webcam : la page reçoit tout de suite l'état du suivi du bac
                        q.put(f"event: state\ndata: {json.dumps({'code': code})}\n\n".encode())
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
            elif self.path.startswith("/live") and hasattr(camera, "live"):
                self.head(200, "multipart/x-mixed-replace; boundary=image")
                try:
                    while True:  # environ 12 images/s, jusqu'à ce que la page ferme le flux
                        jpg = camera.live("debug" in self.path)
                        self.wfile.write(b"--image\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(jpg))
                        self.wfile.write(jpg + b"\r\n"); self.wfile.flush()
                        time.sleep(0.08)
                except (BrokenPipeError, ConnectionResetError):
                    pass
            elif self.path.startswith("/debug") and hasattr(camera, "debug"):
                self.head(200, "image/jpeg"); self.wfile.write(camera.debug())
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
    p.add_argument("--webcam", default="auto", metavar="DEV",
                   help="webcam USB (ex. /dev/video0) qui remplace Pi Camera et capteur ; "
                        "auto (défaut) : /dev/video0 s'il n'y a pas de Pi Camera ; off : jamais")
    p.add_argument("--cam-size", default="1280x720", help="résolution de la webcam, défaut 1280x720")
    p.add_argument("--stable", type=float, default=1.5, help="webcam : bac immobile depuis ce temps = passage (s)")
    p.add_argument("--absent", type=float, default=1.5, help="webcam : bac retiré depuis ce temps = réarmé (s)")
    p.add_argument("--inset", type=float, default=0.01, help="webcam : part de la photo rognée sur chaque bord")
    args = p.parse_args()

    camera = None
    if not args.sim and args.webcam != "off":
        try:
            if args.webcam == "auto":
                import importlib.util
                if importlib.util.find_spec("picamera2") or not os.path.exists("/dev/video0"):
                    raise RuntimeError("Pi Camera présente ou pas de /dev/video0")
                args.webcam = "/dev/video0"
            camera = Webcam(args, lambda: on_trigger(camera, args))
        except Exception as e:
            log("Mode webcam indisponible :", e)
    if camera:
        pass  # la webcam déclenche elle-même les passages
    elif not args.sim:
        camera = Camera(args)
        try:
            from gpiozero import Button
            btn = Button(args.pin, pull_up=not args.active_high, bounce_time=0.05)
            btn.when_pressed = lambda: on_trigger(camera, args)
            log(f"GPIO {args.pin} surveillé")
        except Exception as e:
            log("GPIO indisponible :", e, "(déclenchement possible via POST /trigger)")
    else:
        camera = Camera(args)
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
