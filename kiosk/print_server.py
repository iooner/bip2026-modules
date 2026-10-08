#!/usr/bin/env python3
"""Impression silencieuse des étiquettes, commune aux 4 modules.

Le navigateur en kiosk affiche brièvement son aperçu d'impression à chaque window.print(). À la place, la page
envoie son étiquette (HTML) ici : un Chromium invisible en fait un PDF, envoyé à l'imprimante par défaut (lp).
Rien n'apparaît à l'écran. Si ce service ne tourne pas, les modules reviennent à l'impression du navigateur.

  POST http://127.0.0.1:8361/print   corps = document HTML de l'étiquette
Lancé par kiosk/linux/kiosk.sh. Essai sans imprimer : BIP_NO_LP=1 python3 kiosk/print_server.py
"""
import os, shutil, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("BIP_PRINT_PORT", 8361))   # autre port : essais sans toucher au service de la borne
DIR = os.path.expanduser("~/.cache/bip2026/print")
LOCK = threading.Lock()   # une étiquette à la fois


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
        self.reply(200, "bip2026 print")

    def do_POST(self):
        if self.path != "/print":
            return self.reply(404)
        try:
            print_label(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            self.reply(200, "ok")
        except Exception as e:
            print("Impression impossible :", e, flush=True)
            self.reply(500, str(e))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except OSError as e:
        sys.exit(f"Service d'impression : {e}")
