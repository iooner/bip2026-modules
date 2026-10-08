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
import json, os, select, shutil, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("BIP_PRINT_PORT", 8361))   # autre port : essais sans toucher au service de la borne
DIR = os.path.expanduser("~/.cache/bip2026/print")
LOCK = threading.Lock()   # une étiquette à la fois
STUCK_S = 45              # une étiquette encore en file après ce délai = imprimante bloquée (vide, éteinte, débranchée…)
LAST = {"error": None, "printer_msg": None}
SEEN = {}                 # étiquettes en file -> heure où on les a vues pour la première fois


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
    if LAST["error"]:
        out.append({"code": "impression", "detail": LAST["error"]})
    return out


def printer_message():
    """Après une impression, lit ce que l'imprimante renvoie sur l'USB (la LW650XL PRO écrit des lignes du type
    « SSSGETPRINTING:DOING »). Seulement journalisé pour l'instant : sert à reconnaître « plus d'étiquettes »."""
    try:
        fd = os.open("/dev/usb/lp0", os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return
    try:
        data = b""
        while select.select([fd], [], [], 0.3)[0]:
            data += os.read(fd, 256)
        if data:
            LAST["printer_msg"] = data.decode("latin-1").strip()
            print("Imprimante :", LAST["printer_msg"], flush=True)
    except OSError:
        pass
    finally:
        os.close(fd)


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
        subprocess.run([exe, "--headless=new", "--no-pdf-header-footer", "--disable-gpu", "--no-first-run",
                        f"--user-data-dir={DIR}/profil", f"--print-to-pdf={pdf}", "file://" + src],
                       timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(pdf):
            raise RuntimeError("PDF non produit")
        if os.environ.get("BIP_NO_LP"):
            print("Étiquette prête (non imprimée) :", pdf, flush=True)
        else:
            subprocess.run(["lp", pdf], timeout=20, check=True, stdout=subprocess.DEVNULL)
            print("Étiquette envoyée à l'imprimante", flush=True)
            threading.Timer(12, printer_message).start()


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, text=""):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")   # pages en file:// ou sur un autre port local
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
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
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except OSError as e:
        sys.exit(f"Service d'impression : {e}")
