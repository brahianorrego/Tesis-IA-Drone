# -*- coding: utf-8 -*-
"""
Visor en vivo para el banco: cámara + YOLO (TensorRT) + seguimiento, con el ángulo de la
persona respecto a la nariz del dron dibujado encima. Se ve en el navegador del portátil:
    http://<IP-de-la-Jetson>:8080
Uso:  python3 visor_web.py [--puerto 8080]
"""
import argparse
import math
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np

import config as C
from correccion_camara import CorrectorPatron, RealceContraste
from percepcion import abrir_camara

_lock = threading.Lock()
_jpeg = None
_args = None

PAGINA = (b"<html><head><meta charset='utf-8'><title>Camara del dron</title></head>"
          b"<body style='margin:0;background:#111'>"
          b"<img src='/video' style='width:100%;max-width:1280px;display:block;margin:auto'>"
          b"</body></html>")


def bucle_vision():
    global _jpeg
    from ultralytics import YOLO
    modelo = YOLO(C.YOLO_MODELO, task="detect")
    cap, tipo = abrir_camara(C)
    # la corrección de la cuadrícula es solo para la cámara USB (la CSI no la tiene)
    corrector = CorrectorPatron() if C.CAMARA_TIPO == "usb" else CorrectorPatron("no_existe.npy")
    realce = RealceContraste()
    print("[VISOR] camara %s, modelo %s, correccion de patron %s, YOLO sobre imagen %s"
          % (tipo, C.YOLO_MODELO, "ON" if corrector.activo else "sin patron", _args.yolo), flush=True)
    tan_h = math.tan(math.radians(C.CAMARA_HFOV_DEG) / 2.0)
    n, t_log, t_fps, fps = 0, time.time(), time.time(), 0.0
    while True:
        ok, crudo = cap.read()
        if not ok:
            time.sleep(0.05)
            continue
        corregido = corrector.corregir(crudo)
        if _args.realce:
            sin_realce = corregido
            corregido = realce.aplicar(corregido)
        frame = corregido if _args.yolo == "corregida" else crudo.copy()
        r = modelo.track(frame, imgsz=C.YOLO_IMGSZ, conf=C.YOLO_CONF_MIN, classes=[0],
                         persist=True, tracker=C.YOLO_TRACKER, verbose=False)[0]
        h, w = frame.shape[:2]
        mejor = None
        for b in r.boxes:
            x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
            tid = int(b.id[0]) if b.id is not None else -1
            area = (x2 - x1) * (y2 - y1) / float(w * h)
            cx = (x1 + x2) / 2.0 / w
            ang = math.degrees(math.atan((2 * cx - 1) * tan_h))
            if mejor is None or area > mejor[2]:
                mejor = (tid, ang, area, float(b.conf[0]))
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, "ID %d  %+.1f deg" % (tid, ang), (x1, max(15, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 255, 0), 1)   # nariz del dron
        n += 1
        if time.time() - t_fps >= 1.0:
            fps, n, t_fps = n / (time.time() - t_fps), 0, time.time()
        cv2.putText(frame, "%.1f FPS  YOLO: %s" % (fps, _args.yolo), (8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        if _args.lado_a_lado and corrector.activo:
            otro = (sin_realce if _args.realce else crudo if _args.yolo == "corregida" else corregido).copy()
            cv2.putText(otro, "corregida sin realce" if _args.realce else "original" if _args.yolo == "corregida" else "corregida",
                        (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.putText(frame, "alfa %.2f %.2f %.2f" % tuple(corrector.alfa), (8, 46),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            frame = np.hstack([otro, frame] if _args.yolo == "corregida" else [frame, otro])
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        with _lock:
            _jpeg = buf.tobytes()
        if time.time() - t_log >= 1.0:
            t_log = time.time()
            if mejor:
                print("%s fps=%4.1f persona ID=%d angulo=%+6.1f area=%.3f conf=%.2f"
                      % (time.strftime("%H:%M:%S"), fps, mejor[0], mejor[1], mejor[2], mejor[3]),
                      flush=True)
            else:
                print("%s fps=%4.1f sin persona" % (time.strftime("%H:%M:%S"), fps), flush=True)


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(PAGINA)
            return
        if self.path != "/video":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            while True:
                with _lock:
                    j = _jpeg
                if j:
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                     b"Content-Length: %d\r\n\r\n" % len(j))
                    self.wfile.write(j + b"\r\n")
                time.sleep(0.05)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", type=int, default=8080)
    ap.add_argument("--yolo", choices=["corregida", "original"], default="corregida",
                    help="imagen que recibe YOLO")
    ap.add_argument("--realce", action="store_true", help="CLAHE de contraste después de quitar la cuadrícula")
    ap.add_argument("--lado-a-lado", action="store_true", help="mostrar original y corregida juntas")
    ap.add_argument("--camara", choices=["usb", "csi"], default=None,
                    help="usb = Sonix (HFOV 38.9); csi = IMX219 por CAM0 con ISP por software")
    a = _args = ap.parse_args()
    if a.camara == "csi":
        C.CAMARA_TIPO, C.CAMARA_HFOV_DEG = "csi_v4l2", C.CAMARA_CSI_HFOV_DEG
    elif a.camara == "usb":
        C.CAMARA_TIPO = "usb"
    threading.Thread(target=bucle_vision, daemon=True).start()
    print("[VISOR] abra http://<IP-de-la-Jetson>:%d en el navegador" % a.puerto, flush=True)
    ThreadingHTTPServer(("0.0.0.0", a.puerto), Manejador).serve_forever()
