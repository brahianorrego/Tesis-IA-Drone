# -*- coding: utf-8 -*-
"""
IA #1 - Percepción visual: cámara (CSI por GStreamer o USB) + YOLO con
seguimiento por ID y bloqueo de objetivo.

Cambios respecto a yolo_tracking.py:
* La captura corre en su propio hilo y solo conserva el frame más reciente
  (antes cap.read() podía entregar frames viejos acumulados -> latencia).
* El pipeline CSI usa 'appsink drop=true max-buffers=1' (sin max-buffers,
  drop=true no descarta nada) y el modo 1640x1232 (campo completo, 4:3).
* track() se limita a la clase persona (classes=[0]).
* BLOQUEO DE OBJETIVO: antes se elegía la persona de mayor área en cada frame,
  así que al cruzarse dos personas el objetivo saltaba aunque tuvieran ID.
  Ahora se sigue el mismo ID; solo se cambia si ese ID desaparece o si otra
  persona es claramente más grande (más cercana = más peligrosa).
"""
import threading
import time
from collections import namedtuple

import cv2

Deteccion = namedtuple(
    "Deteccion",
    "persona track_id conf x1 y1 x2 y2 ancho alto cx_norm cy_norm area_norm alto_norm "
    "zona n_personas t_frame lat_ms")


def deteccion_vacia(ancho, alto, t_frame, lat_ms=0.0, n=0):
    return Deteccion(False, -1, 0.0, 0, 0, 0, 0, ancho, alto, 0.5, 0.5, 0.0, 0.0,
                     "NINGUNA", n, t_frame, lat_ms)


def zona_de(cx_norm):
    if cx_norm < 1.0 / 3.0:
        return "IZQUIERDA"
    if cx_norm < 2.0 / 3.0:
        return "CENTRO"
    return "DERECHA"


# --------------------------------------------------------------------------
# Cámara
# --------------------------------------------------------------------------
def gstreamer_pipeline(sensor_id=0, capture_width=1640, capture_height=1232,
                       display_width=640, display_height=480, framerate=30, flip_method=0):
    return (
        "nvarguscamerasrc sensor-id=%d ! "
        "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! video/x-raw, format=(string)BGR ! "
        "appsink drop=true max-buffers=1 sync=false"
        % (sensor_id, capture_width, capture_height, framerate, flip_method,
           display_width, display_height))


def abrir_camara(cfg, fuente=None):
    """Abre la cámara según config. 'fuente' permite forzar un índice o un video (.mp4)."""
    if fuente is not None:
        src = int(fuente) if str(fuente).isdigit() else fuente
        cap = cv2.VideoCapture(src)
        if cap.isOpened():
            return cap, "archivo/indice %s" % fuente
        raise RuntimeError("No se pudo abrir la fuente %s" % fuente)

    if cfg.CAMARA_TIPO == "csi_v4l2":
        # JetPack 7: nvargus no arranca; el ISP se hace por software (camara_csi.py)
        from camara_csi import CamaraCSI
        cap = CamaraCSI(cfg.CAMARA_CSI_DISPOSITIVO, ancho=cfg.CAMARA_ANCHO, alto=cfg.CAMARA_ALTO)
        if cap.isOpened():
            return cap, "CSI V4L2 (ISP por software)"
        raise RuntimeError("No se pudo abrir la camara CSI %s" % cfg.CAMARA_CSI_DISPOSITIVO)

    if cfg.CAMARA_TIPO == "csi":
        pipe = gstreamer_pipeline(cfg.CAMARA_INDICE, cfg.CSI_CAPTURA_ANCHO, cfg.CSI_CAPTURA_ALTO,
                                  cfg.CAMARA_ANCHO, cfg.CAMARA_ALTO, cfg.CAMARA_FPS, cfg.CAMARA_FLIP)
        cap = cv2.VideoCapture(pipe, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            return cap, "CSI GStreamer"
        print("[CAMARA] GStreamer CSI falló (¿OpenCV sin GStreamer o nvargus-daemon caído?). "
              "Probando USB...")

    cap = cv2.VideoCapture(cfg.CAMARA_INDICE, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.CAMARA_ANCHO)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.CAMARA_ALTO)
    cap.set(cv2.CAP_PROP_FPS, cfg.CAMARA_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if cap.isOpened():
        # La cámara Sonix pierde estos ajustes al reconectarse. Con exposure_dynamic_framerate=1
        # baja a ~11 FPS con poca luz; 60 Hz es la red eléctrica de Colombia (evita parpadeo).
        import subprocess
        subprocess.call(["v4l2-ctl", "-d", "/dev/video%d" % int(cfg.CAMARA_INDICE),
                         "-c", "exposure_dynamic_framerate=0", "-c", "power_line_frequency=2"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return cap, "USB V4L2"
    raise RuntimeError("No se pudo abrir ninguna cámara")


class CamaraHilo(object):
    """Lee la cámara continuamente y guarda solo el frame más reciente."""

    def __init__(self, cap, es_archivo=False):
        self.cap = cap
        self.es_archivo = es_archivo
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._periodo_archivo = 1.0 / fps if fps > 0 else 1.0 / 30.0
        self._lock = threading.Condition()
        self._frame = None
        self._t = 0.0
        self._n = 0
        self._activo = False
        self.fin = False

    def iniciar(self):
        self._activo = True
        threading.Thread(target=self._bucle, name="camara", daemon=True).start()
        return self

    def _bucle(self):
        while self._activo:
            ok, frame = self.cap.read()
            if not ok:
                if self.es_archivo:
                    self.fin = True
                    with self._lock:
                        self._lock.notify_all()
                    return
                time.sleep(0.01)
                continue
            with self._lock:
                self._frame, self._t = frame, time.time()
                self._n += 1
                self._lock.notify_all()
            if self.es_archivo:
                time.sleep(self._periodo_archivo)

    def leer_nuevo(self, ultimo_n, timeout=1.0):
        """Espera un frame con número > ultimo_n. Devuelve (frame, t, n) o (None, 0, ultimo_n)."""
        with self._lock:
            fin_espera = time.time() + timeout
            while self._n <= ultimo_n and not self.fin:
                restante = fin_espera - time.time()
                if restante <= 0:
                    return None, 0.0, ultimo_n
                self._lock.wait(restante)
            if self._n <= ultimo_n:
                return None, 0.0, ultimo_n
            return self._frame, self._t, self._n

    def detener(self):
        self._activo = False
        time.sleep(0.05)
        self.cap.release()


# --------------------------------------------------------------------------
# Detector YOLO con seguimiento
# --------------------------------------------------------------------------
class DetectorPersonas(object):

    def __init__(self, modelo, conf=0.4, imgsz=640, tracker="bytetrack.yaml",
                 frames_perdida=15, factor_cambio=1.8):
        from ultralytics import YOLO  # importación diferida: los modos de prueba no la necesitan
        self.modelo = YOLO(modelo)
        self.conf = conf
        self.imgsz = imgsz
        self.tracker = tracker
        self.frames_perdida = frames_perdida
        self.factor_cambio = factor_cambio
        self.id_bloqueado = None
        self._frames_sin_ver = 0

    def _elegir(self, personas):
        """personas: lista de (id, conf, x1, y1, x2, y2, area). Devuelve la elegida o None."""
        if not personas:
            if self.id_bloqueado is not None:
                self._frames_sin_ver += 1
                if self._frames_sin_ver > self.frames_perdida:
                    self.id_bloqueado = None
            return None
        mayor = max(personas, key=lambda p: p[6])
        actual = None
        for p in personas:
            if self.id_bloqueado is not None and p[0] == self.id_bloqueado:
                actual = p
                break
        if actual is None or mayor[6] > self.factor_cambio * actual[6]:
            actual = mayor            # ID perdido o alguien mucho más cerca
        self.id_bloqueado = actual[0]
        self._frames_sin_ver = 0
        return actual

    def procesar(self, frame, t_frame):
        alto, ancho = frame.shape[:2]
        t0 = time.time()
        res = self.modelo.track(frame, persist=True, classes=[0], conf=self.conf,
                                imgsz=self.imgsz, tracker=self.tracker, verbose=False)[0]
        lat_ms = (time.time() - t0) * 1000.0
        personas = []
        cajas = res.boxes
        if cajas is not None and len(cajas):
            xyxy = cajas.xyxy.cpu().numpy()
            confs = cajas.conf.cpu().numpy()
            ids = cajas.id.cpu().numpy().astype(int) if cajas.id is not None else [-1] * len(confs)
            for (x1, y1, x2, y2), c, i in zip(xyxy, confs, ids):
                area = float((x2 - x1) * (y2 - y1))
                personas.append((int(i), float(c), int(x1), int(y1), int(x2), int(y2), area))
        elegida = self._elegir(personas)
        if elegida is None:
            return deteccion_vacia(ancho, alto, t_frame, lat_ms, len(personas))
        i, c, x1, y1, x2, y2, area = elegida
        cx = (x1 + x2) / 2.0 / ancho
        cy = (y1 + y2) / 2.0 / alto
        return Deteccion(True, i, c, x1, y1, x2, y2, ancho, alto, cx, cy,
                         area / float(ancho * alto), (y2 - y1) / float(alto),
                         zona_de(cx), len(personas), t_frame, lat_ms)
