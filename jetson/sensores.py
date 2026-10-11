# -*- coding: utf-8 -*-
"""
Fuentes de datos para el grabador y el script de vuelo.

FuenteReal  : cámara + YOLO + LiDAR TF03 + gimbal BaseCam (con seguimiento).
FuenteFalsa : escenario sintético (persona que se acerca) para probar el lazo
              MAVLink completo en SITL sin cámara ni sensores.

Ambas devuelven lo mismo en obtener(): (frame o None, Deteccion, LecturaLidar, EstadoGimbal)
"""
import math
import random
import time

from lidar_tf import LecturaLidar
from gimbal_basecam import EstadoGimbal
from percepcion import Deteccion, deteccion_vacia
from comun import vfov_desde_hfov


class FuenteReal(object):

    def __init__(self, cfg, fuente_video=None, usar_lidar=True, usar_gimbal=True, seguimiento=None):
        from percepcion import abrir_camara, CamaraHilo, DetectorPersonas
        from lidar_tf import LidarTF
        from gimbal_basecam import GimbalBaseCam

        self.cfg = cfg
        cap, desc = abrir_camara(cfg, fuente_video)
        es_archivo = fuente_video is not None and not str(fuente_video).isdigit()
        self.cam = CamaraHilo(cap, es_archivo).iniciar()
        print("[CAMARA] %s" % desc)
        print("[YOLO] cargando %s ..." % cfg.YOLO_MODELO)
        self.detector = DetectorPersonas(cfg.YOLO_MODELO, cfg.YOLO_CONF_MIN, cfg.YOLO_IMGSZ,
                                         cfg.YOLO_TRACKER, cfg.FRAMES_PERDIDA_OBJETIVO,
                                         cfg.FACTOR_CAMBIO_OBJETIVO)
        self.lidar = None
        if usar_lidar:
            self.lidar = LidarTF(cfg.PUERTO_LIDAR, cfg.BAUD_LIDAR, cfg.LIDAR_MIN_CM,
                                 cfg.LIDAR_MAX_CM, cfg.LIDAR_FUERZA_MIN).iniciar()
        self.gimbal = None
        if usar_gimbal:
            self.gimbal = GimbalBaseCam(cfg.PUERTO_GIMBAL, cfg.BAUD_GIMBAL, cfg.GIMBAL_PROTOCOLO,
                                        cfg.GIMBAL_FUENTE_PANEO, cfg.GIMBAL_SIGNO_PANEO,
                                        cfg.GIMBAL_HZ_LECTURA).iniciar()
        self._seguimiento_pedido = seguimiento
        self.seguidor = None
        self._n = 0

    def _crear_seguidor(self, det):
        from gimbal_basecam import SeguidorGimbal
        self.seguidor = SeguidorGimbal(self.gimbal, self.cfg, det.ancho, det.alto)
        if self._seguimiento_pedido is not None:
            self.seguidor.activo = bool(self._seguimiento_pedido) and self.gimbal is not None

    def obtener(self, timeout=1.0):
        frame, t, n = self.cam.leer_nuevo(self._n, timeout)
        if frame is None:
            return None
        self._n = n
        det = self.detector.procesar(frame, t)
        if self.gimbal is not None:
            if self.seguidor is None:
                self._crear_seguidor(det)
            self.seguidor.actualizar(det)
        lec = self.lidar.lectura() if self.lidar is not None else None
        est = self.gimbal.estado() if self.gimbal is not None else None
        return frame, det, lec, est

    @property
    def fin(self):
        return self.cam.fin

    def detener(self):
        self.cam.detener()
        if self.lidar is not None:
            self.lidar.detener()
        if self.gimbal is not None:
            self.gimbal.detener(liberar=True)


class FuenteFalsa(object):
    """Ciclos de 14 s: 3 s sin nadie y luego una persona que se acerca de 12 m a 1.5 m.
    Cada ciclo la persona viene por un lado distinto (paneo -25, 0, +25 deg)."""

    def __init__(self, cfg, periodo=14.0, hz=20.0, ancho=640, alto=480):
        self.cfg = cfg
        self.periodo = periodo
        self.dt = 1.0 / hz
        self.ancho, self.alto = ancho, alto
        vfov = math.radians(vfov_desde_hfov(cfg.CAMARA_HFOV_DEG, ancho, alto))
        self.f_px = (alto / 2.0) / math.tan(vfov / 2.0)
        self.t0 = time.time()
        self.fin = False

    def obtener(self, timeout=1.0):
        time.sleep(self.dt)
        t = time.time()
        fase = (t - self.t0) % self.periodo
        ciclo = int((t - self.t0) // self.periodo)
        paneo = [-25.0, 0.0, 25.0][ciclo % 3] + random.gauss(0, 1.0)
        est = EstadoGimbal(paneo, paneo, 0.0, 0.0, paneo, "marco", True, t)
        if fase < 3.0:
            return None, deteccion_vacia(self.ancho, self.alto, t, 20.0), \
                LecturaLidar(18000, 0, False, t), est
        s = min(1.0, (fase - 3.0) / (self.periodo - 4.0))
        d_m = 12.0 - 10.5 * s
        h_px = min(self.alto - 2.0, self.cfg.ALTURA_PERSONA_M * self.f_px / d_m)
        w_px = 0.4 * h_px
        # Cámara fija a la nariz en yaw: el lado de la persona se ve en la posición del bbox
        tan_h = math.tan(math.radians(self.cfg.CAMARA_HFOV_DEG) / 2.0)
        cx = self.ancho / 2.0 * (1.0 + math.tan(math.radians(paneo)) / tan_h) + random.gauss(0, 6)
        cy = self.alto / 2.0 + random.gauss(0, 4)
        x1, x2 = int(cx - w_px / 2), int(cx + w_px / 2)
        y1, y2 = int(max(0, cy - h_px / 2)), int(min(self.alto - 1, cy + h_px / 2))
        det = Deteccion(True, 1, 0.85, x1, y1, x2, y2, self.ancho, self.alto,
                        cx / self.ancho, cy / self.alto, (x2 - x1) * (y2 - y1) / float(self.ancho * self.alto),
                        (y2 - y1) / float(self.alto), "CENTRO", 1, t, 20.0)
        lec = LecturaLidar(int(d_m * 100 + random.gauss(0, 5)), 1000, True, t)
        return None, det, lec, est

    def detener(self):
        pass
