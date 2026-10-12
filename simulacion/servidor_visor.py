# -*- coding: utf-8 -*-
"""
Servidor local del visor (http://127.0.0.1:8765/).

Igual que `python -m http.server`, pero fija los tipos de archivo que necesita el visor V16: en Windows el registro a
veces dice que un .js es "text/plain" y el navegador se niega a cargar los módulos de three.js. Tampoco guarda en caché
(el entrenamiento reescribe salida/*.json a cada rato).

Uso (desde simulacion/):  .venv\\Scripts\\python.exe servidor_visor.py [--puerto 8765]
"""
import argparse
import http.server
import os

TIPOS = {".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json", ".hdr": "application/octet-stream",
         ".jpg": "image/jpeg", ".png": "image/png", ".html": "text/html; charset=utf-8", ".css": "text/css"}


class Manejador(http.server.SimpleHTTPRequestHandler):
    extensions_map = dict(http.server.SimpleHTTPRequestHandler.extensions_map, **TIPOS)

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return TIPOS.get(ext) or super().guess_type(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", type=int, default=8765)
    a = ap.parse_args()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("Visor en http://127.0.0.1:%d/  (Ctrl+C para cerrar)" % a.puerto, flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", a.puerto), Manejador).serve_forever()
