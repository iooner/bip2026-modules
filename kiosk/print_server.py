#!/usr/bin/env python3
"""Impression silencieuse des étiquettes, commune aux 4 modules.

Le navigateur en kiosk affiche brièvement son aperçu d'impression à chaque window.print(). À la place, la page
envoie son étiquette (HTML) ici : un Chromium invisible en fait un PDF, envoyé à l'imprimante par défaut (lp).
Rien n'apparaît à l'écran. Si ce service ne tourne pas, les modules reviennent à l'impression du navigateur.

  POST http://127.0.0.1:8361/print   corps = document HTML de l'étiquette
  GET  http://127.0.0.1:8361/status  {"ok": bool, "problems": [{"code", "detail"}]} : état de l'impression,
                                     lu par status.js de chaque module (bandeau « en panne » sur l'accueil)
Lancé par kiosk/linux/kiosk.sh. Essai sans imprimer : BIP_NO_LP=1 python3 kiosk/print_server.py
"""
import atexit, base64, json, os, re, select, shutil, signal, socket, struct, subprocess, sys, threading, time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("BIP_PRINT_PORT", 8361))   # autre port : essais sans toucher au service de la borne
DIR = os.path.expanduser("~/.cache/bip2026/print")
LOCK = threading.Lock()   # une étiquette à la fois
STUCK_S = 30              # une étiquette encore en file après ce délai = imprimante bloquée (vide, éteinte, débranchée…)
LAST = {"error": None, "printer_msg": None}
SEEN = {}                 # étiquettes en file -> heure où on les a vues pour la première fois
# Navigateur invisible gardé ouvert entre deux étiquettes (évite 3 à 4 s de démarrage à chaque impression sur un
# petit processeur). Au moindre souci, l'étiquette en cours repasse par un lancement classique et le navigateur
# est relancé pour la suivante. BIP_PRINT_WARM=0 pour ne jamais le garder ouvert.
WARM = os.environ.get("BIP_PRINT_WARM", "1") != "0"
CDP_PORT = int(os.environ.get("BIP_CDP_PORT", PORT + 1000))
BROWSER = {"proc": None}


def sh(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=8,
                              env={**os.environ, "LC_ALL": "C"}).stdout
    except Exception:
        return ""


def problems():
    """Ce qui empêche d'imprimer, vu depuis CUPS. Liste vide = tout va bien."""
    out = []
    default = sh("lpstat", "-d")
    if ":" not in default:
        return [{"code": "imprimante", "detail": "aucune imprimante par défaut dans CUPS"}]
    name = default.split(":", 1)[1].strip()
    state = sh("lpstat", "-p", name)
    if "disabled" in state or not state.strip():
        reason = " ".join(state.split()[4:])[:120] or "introuvable"
        out.append({"code": "imprimante", "detail": f"{name} arrêtée par CUPS : {reason}"})
    # Étiquettes qui ne sortent pas : encore en file bien après y avoir été vues la première fois
    now, queued = time.time(), {line.split()[0] for line in sh("lpstat", "-o", name).splitlines() if line.strip()}
    for job in list(SEEN):
        if job not in queued:
            del SEEN[job]
    old = sum(now - SEEN.setdefault(job, now) > STUCK_S for job in queued)
    if old:
        out.append({"code": "file", "detail": f"{old} étiquette(s) bloquée(s) dans la file de {name} "
                                              "(rouleau vide, imprimante éteinte ou débranchée ?)"})
    out += printer_problems(name)
    # Pilote d'impression installé différent de celui du dépôt : mise à jour du dépôt faite sans réinstaller le pilote
    repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "linux", "tspl", "rastertotspl-bip")
    try:
        if os.path.exists(TSPL) and open(repo, "rb").read() != open(TSPL, "rb").read():
            out.append({"code": "pilote", "detail": "pilote d'impression pas à jour : lancer ./kiosk/linux/update.sh "
                                                    f"(ou sudo install -m 755 {repo} /usr/lib/cups/filter/)"})
    except OSError:
        pass
    if LAST["error"]:
        out.append({"code": "impression", "detail": LAST["error"]})
    return out


PRINTER = {"paper": None, "cap": None, "absent": 0, "seen": False, "mute": 0}   # dernier état donné par l'imprimante ; absent = nb de lectures ratées
DEV = "/dev/usb/lp0"
TSPL = "/usr/lib/cups/filter/rastertotspl-bip"        # pilote installé = cette borne a l'imprimante USB interrogeable
MUTE_N = 4                # lectures sans réponse d'affilée (environ 12 s) avant de la dire muette


def ask_printer():
    """Interroge la LW650XL PRO sur l'USB. Elle répond en clair : « SSSGETPAPER » -> SSSGETPAPER:YES|NO,
    « SSSGETCAP » -> SSSGETCAP:OPEN|CLOSE (elle ne connaît pas la requête d'état TSPL « ESC !? »). Elle écrit aussi
    ces lignes d'elle-même quand on ouvre le capot ou que le rouleau manque.
    Pendant une impression CUPS tient l'USB : l'ouverture échoue, on garde le dernier état."""
    try:
        fd = os.open(DEV, os.O_RDWR | os.O_NONBLOCK)
    except FileNotFoundError:
        if PRINTER["seen"] or os.path.exists(TSPL):  # débranchée ou éteinte (autre borne sans cette imprimante : rien)
            PRINTER["absent"] += 1
        return
    except OSError:
        return                                       # occupée (impression en cours)
    try:
        text = b""
        for q in (b"SSSGETPAPER\r\n", b"SSSGETCAP\r\n"):
            os.write(fd, q)
            end = time.time() + 1.0
            while time.time() < end and not text.endswith(b"\n"):
                if select.select([fd], [], [], 0.3)[0]:
                    text += os.read(fd, 256)
            text += b" "
        said = dict(re.findall(r"SSSGET([A-Z]+):([A-Z]+)", text.decode("latin-1")))
        if "PAPER" in said:
            PRINTER["paper"] = said["PAPER"] == "YES"
        if "CAP" in said:
            PRINTER["cap"] = said["CAP"] == "CLOSE"
        PRINTER["absent"], PRINTER["seen"] = 0, True
        # Ouverte mais muette (vu après un rebranchement USB) : son état n'est plus connu, on oublie le dernier
        PRINTER["mute"] = 0 if said else PRINTER["mute"] + 1
        if PRINTER["mute"] >= MUTE_N:
            PRINTER["paper"] = PRINTER["cap"] = None
        msg = " / ".join(text.decode("latin-1").split())
        if msg != LAST["printer_msg"]:
            LAST["printer_msg"] = msg
            print("Imprimante :", msg, flush=True)
    except OSError:
        pass
    finally:
        os.close(fd)


def watch_printer():
    # Pas d'abandon si /dev/usb manque au lancement : au démarrage de la borne, le service part souvent avant que
    # l'imprimante soit reconnue sur l'USB, et son état (rouleau, capot, débranchée) n'était alors jamais lu.
    while True:
        ask_printer()
        time.sleep(1)


def printer_problems(name):
    out = []
    if PRINTER["absent"] >= 3:
        out.append({"code": "imprimante", "detail": f"{name} débranchée ou éteinte (USB absent)"})
    if PRINTER["mute"] >= MUTE_N and os.path.exists(TSPL):
        out.append({"code": "imprimante", "detail": f"{name} ne répond pas (l'éteindre puis la rallumer)"})
    if PRINTER["paper"] is False:
        out.append({"code": "etiquettes", "detail": f"{name} : plus d'étiquettes (rouleau vide ou mal engagé)"})
    if PRINTER["cap"] is False:
        out.append({"code": "capot", "detail": f"{name} : capot ouvert"})
    return out


class DevTools:
    """Dialogue minimal avec un onglet de Chromium (protocole DevTools sur WebSocket, sans dépendance)."""
    def __init__(self, url, timeout=20):
        host, path = url.split("://", 1)[1].split("/", 1)
        name, port = host.split(":")
        self.sock = socket.create_connection((name, int(port)), timeout=timeout)
        self.buf, self.n, self.events = b"", 0, []
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET /{path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        while b"\r\n\r\n" not in self.buf:
            self.fill()
        head, self.buf = self.buf.split(b"\r\n\r\n", 1)
        if b" 101 " not in head.split(b"\r\n")[0]:
            raise RuntimeError("WebSocket refusé : " + head[:60].decode("latin1"))

    def fill(self):
        chunk = self.sock.recv(1 << 16)
        if not chunk:
            raise ConnectionError("navigateur fermé")
        self.buf += chunk

    def read(self, n):
        while len(self.buf) < n:
            self.fill()
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self):
        msg = b""
        while True:
            b0, b1 = self.read(2)
            n = b1 & 0x7f
            if n == 126:
                n = struct.unpack(">H", self.read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self.read(8))[0]
            data = self.read(n)
            if b0 & 0x0f == 8:
                raise ConnectionError("navigateur fermé")
            if b0 & 0x0f in (9, 10):   # ping / pong
                continue
            msg += data
            if b0 & 0x80:
                return json.loads(msg)

    def call(self, method, **params):
        self.n += 1
        data = json.dumps({"id": self.n, "method": method, "params": params}).encode()
        n, mask = len(data), os.urandom(4)
        size = bytes([0x80 | n]) if n < 126 else b"\xfe" + struct.pack(">H", n) if n < 1 << 16 else b"\xff" + struct.pack(">Q", n)
        self.sock.sendall(b"\x81" + size + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(data)))
        while True:
            m = self.recv()
            if m.get("id") == self.n:
                if "error" in m:
                    raise RuntimeError(f"{method} : {m['error'].get('message')}")
                return m.get("result", {})
            self.events.append(m.get("method"))

    def wait(self, event):
        while event not in self.events:
            self.events.append(self.recv().get("method"))


def warm_stop(*_):
    """Arrête le navigateur gardé ouvert et tous ses processus (il a son propre groupe)."""
    p, BROWSER["proc"] = BROWSER["proc"], None
    if p:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            pass
        p.wait()


def warm_ready():
    try:
        return bool(urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=.5).read())
    except OSError:
        return False


def warm_launch(exe):
    """(Re)lance le navigateur gardé ouvert, sans attendre qu'il soit prêt : il servira à l'étiquette suivante."""
    p = BROWSER["proc"]
    if p and p.poll() is None and time.time() - BROWSER.get("since", 0) < 15:
        return   # encore en train de démarrer
    warm_stop()  # planté ou bloqué : on nettoie ce qu'il en reste
    profile = f"{DIR}/profil-ouvert"
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):   # verrous laissés par un plantage
        try:
            os.remove(os.path.join(profile, name))
        except OSError:
            pass
    BROWSER["since"] = time.time()
    BROWSER["proc"] = subprocess.Popen(
        [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--password-store=basic",
         f"--remote-debugging-port={CDP_PORT}", f"--user-data-dir={profile}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def warm_pdf(exe, src, pdf):
    """Fabrique le PDF dans le navigateur gardé ouvert. False = échec : l'appelant repasse par un lancement classique."""
    api = f"http://127.0.0.1:{CDP_PORT}/json"
    if not warm_ready():   # pas (encore) là : cette étiquette n'attend pas, on le relance pour la suivante
        warm_launch(exe)
        return False
    try:
        tab = json.load(urllib.request.urlopen(urllib.request.Request(api + "/new?about:blank", method="PUT"), timeout=5))
        try:
            dt = DevTools(tab["webSocketDebuggerUrl"])
            dt.call("Page.enable")
            dt.call("Page.navigate", url="file://" + src)
            dt.wait("Page.loadEventFired")
            dt.call("Runtime.evaluate", expression="document.fonts.ready", awaitPromise=True)
            data = dt.call("Page.printToPDF", printBackground=True, preferCSSPageSize=True, displayHeaderFooter=False,
                           marginTop=0, marginBottom=0, marginLeft=0, marginRight=0)["data"]
            dt.sock.close()
        finally:
            urllib.request.urlopen(f"{api}/close/{tab['id']}", timeout=5).read()
        with open(pdf, "wb") as f:
            f.write(base64.b64decode(data))
        return True
    except Exception as e:
        print("Navigateur gardé ouvert en échec (lancement classique pour cette étiquette) :", e, flush=True)
        warm_stop()
        warm_launch(exe)
        return False


def print_label(html):
    os.makedirs(DIR, exist_ok=True)
    src, pdf = os.path.join(DIR, "etiquette.html"), os.path.join(DIR, "etiquette.pdf")
    exe = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    if not exe:
        raise RuntimeError("Chromium introuvable")
    with LOCK:
        with open(src, "wb") as f:
            f.write(html)
        if os.path.exists(pdf):
            os.remove(pdf)
        if not (WARM and warm_pdf(exe, src, pdf)):
            subprocess.run([exe, "--headless=new", "--no-pdf-header-footer", "--disable-gpu", "--no-first-run", "--password-store=basic",
                            f"--user-data-dir={DIR}/profil", f"--print-to-pdf={pdf}", "file://" + src],
                           timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(pdf):
            raise RuntimeError("PDF non produit")
        if os.environ.get("BIP_NO_LP"):
            print("Étiquette prête (non imprimée) :", pdf, flush=True)
        else:
            subprocess.run(["lp", pdf], timeout=20, check=True, stdout=subprocess.DEVNULL)
            print("Étiquette envoyée à l'imprimante", flush=True)


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, text=""):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")   # pages en file:// ou sur un autre port local
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(text.encode())

    def do_OPTIONS(self):
        self.reply(204)

    def do_GET(self):
        if self.path.startswith("/status"):
            p = problems()
            return self.reply(200, json.dumps({"ok": not p, "problems": p, "printer_msg": LAST["printer_msg"]}))
        self.reply(200, "bip2026 print")

    def do_POST(self):
        if self.path != "/print":
            return self.reply(404)
        try:
            print_label(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            LAST["error"] = None
            self.reply(200, "ok")
        except Exception as e:
            LAST["error"] = f"étiquette non imprimée : {e}"[:160]
            print("Impression impossible :", e, flush=True)
            self.reply(500, str(e))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    threading.Thread(target=watch_printer, daemon=True).start()
    if WARM:
        atexit.register(warm_stop)
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))   # arrêt du kiosk : ferme aussi le navigateur
        # ouvert dès le lancement du service, pour que la première étiquette soit rapide aussi
        warm_launch(shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome"))
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except OSError as e:
        sys.exit(f"Service d'impression : {e}")
