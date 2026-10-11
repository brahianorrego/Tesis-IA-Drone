# -*- coding: utf-8 -*-
"""
Cámara CSI IMX219 (puerto CAM0) sin el ISP de NVIDIA.

En JetPack 7 (L4T R39) el nvargus-daemon no arranca ("No EGL device available"), así que
no hay nvarguscamerasrc. El sensor sí entrega Bayer RAW10 por V4L2 (/dev/video2) a 30 FPS en
el modo 3 (1640x1232) y este módulo hace por software lo que haría el ISP:
  1. Captura cruda con `v4l2-ctl --stream-to=-` (un proceso hijo; es lo más robusto).
  2. Nivel de negro y demosaico (RGGB) en 8 bits con OpenCV, y reducción a 640x480.
  3. Balance de blancos (mundo gris, suavizado) y gamma.
  4. Exposición automática: ajusta exposure y gain del sensor varias veces por segundo.

Imita la interfaz de cv2.VideoCapture (read, isOpened, release, get, set) para que el resto
del código no cambie.

Prueba rápida:  python3 camara_csi.py      -> guarda csi_prueba.jpg e imprime FPS y exposición
"""
import subprocess
import threading
import time

import cv2
import numpy as np

MODOS = {3: (1640, 1232, 30), 4: (1280, 720, 60), 2: (1920, 1080, 30)}
NEGRO = 64.0 / 1023.0                 # nivel de negro del IMX219 en 10 bits
EXP_MIN, EXP_MAX = 100, 30000         # us (a 30 FPS el cuadro dura 33 ms)
GAN_MIN, GAN_MAX = 16, 170            # 16 = 1x
OBJETIVO = 0.42                       # brillo medio buscado (0..1, después de la gamma)


class CamaraCSI(object):

    def __init__(self, dispositivo="/dev/video2", modo=3, ancho=640, alto=480):
        self.dev = dispositivo
        self.modo = modo
        self.w, self.h, self.fps_sensor = MODOS[modo]
        self.ancho, self.alto = ancho, alto
        self.exp, self.gan = 15000, 40
        self.ganancias = np.array([1.0, 1.0, 1.0], np.float32)     # B, G, R
        self._lut = (np.linspace(0, 1, 256) ** (1 / 2.2) * 255).astype(np.uint8)   # gamma 2.2
        self._lock = threading.Lock()
        self._frame = None
        self._n = 0
        self._activo = False
        self._proc = None
        self.fps = 0.0
        self._abrir()

    # ---------------- captura ----------------
    def _abrir(self):
        cmd = ["v4l2-ctl", "-d", self.dev,
               "--set-ctrl=sensor_mode=%d" % self.modo,
               "--set-fmt-video=width=%d,height=%d,pixelformat=RG10" % (self.w, self.h),
               "--set-ctrl=frame_rate=%d" % (self.fps_sensor * 1000000),
               "--set-ctrl=exposure=%d,gain=%d" % (self.exp, self.gan),
               "--stream-mmap", "--stream-to=-"]
        self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
        self._activo = True
        threading.Thread(target=self._bucle, name="csi", daemon=True).start()

    def _bucle(self):
        tam = self.w * self.h * 2
        buf = bytearray(tam)
        vista = memoryview(buf)
        t_fps, n_fps, t_ae = time.time(), 0, 0.0
        while self._activo:
            leido = 0
            while leido < tam:
                k = self._proc.stdout.readinto(vista[leido:])
                if not k:
                    self._activo = False
                    return
                leido += k
            img = self._procesar(np.frombuffer(buf, np.uint16).reshape(self.h, self.w))
            with self._lock:
                self._frame = img
                self._n += 1
            n_fps += 1
            ahora = time.time()
            if ahora - t_fps >= 1.0:
                self.fps, n_fps, t_fps = n_fps / (ahora - t_fps), 0, ahora
            if ahora - t_ae >= 0.25:
                t_ae = ahora
                self._auto_exposicion(img)

    # ---------------- "ISP" por software ----------------
    def _procesar(self, raw):
        # Todo en 8 bits (~12 ms por cuadro en la Orin): RAW10 alineado a la izquierda -> byte alto
        r8 = cv2.subtract((raw >> 8).astype(np.uint8), int(NEGRO * 255))
        bgr = cv2.cvtColor(r8, cv2.COLOR_BayerBG2BGR)    # el IMX219 es RGGB = "BayerBG" en OpenCV
        bgr = cv2.resize(bgr, (self.ancho, self.alto), interpolation=cv2.INTER_AREA)
        # balance de blancos de mundo gris, suavizado para que no parpadee
        medias = np.array(cv2.mean(bgr)[:3], np.float32) + 1e-3
        objetivo = medias[1] / medias
        self.ganancias = 0.9 * self.ganancias + 0.1 * np.clip(objetivo, 0.5, 4.0).astype(np.float32)
        b, g, r = cv2.split(bgr)
        bgr = cv2.merge([cv2.convertScaleAbs(b, alpha=float(self.ganancias[0])), g,
                         cv2.convertScaleAbs(r, alpha=float(self.ganancias[2]))])
        return cv2.LUT(bgr, self._lut)

    def _auto_exposicion(self, img):
        brillo = img.mean() / 255.0
        error = OBJETIVO / max(brillo, 1e-3)
        if 0.9 < error < 1.1:
            return
        factor = float(np.clip(error, 0.6, 1.6))
        exp, gan = self.exp, self.gan
        if factor > 1:      # falta luz: primero exposición, después ganancia
            exp = min(EXP_MAX, int(exp * factor))
            if exp >= EXP_MAX:
                gan = min(GAN_MAX, int(gan * factor))
        else:               # sobra luz: primero ganancia, después exposición
            gan = max(GAN_MIN, int(gan * factor))
            if gan <= GAN_MIN:
                exp = max(EXP_MIN, int(exp * factor))
        if (exp, gan) != (self.exp, self.gan):
            self.exp, self.gan = exp, gan
            subprocess.call(["v4l2-ctl", "-d", self.dev, "--set-ctrl=exposure=%d,gain=%d" % (exp, gan)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ---------------- interfaz tipo cv2.VideoCapture ----------------
    def isOpened(self):
        return self._activo

    def read(self, timeout=1.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            with self._lock:
                if self._frame is not None:
                    f, self._frame = self._frame, None
                    return True, f
            time.sleep(0.002)
        return False, None

    def get(self, prop):
        if prop == cv2.CAP_PROP_FPS:
            return float(self.fps_sensor)
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return float(self.ancho)
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return float(self.alto)
        return 0.0

    def set(self, prop, valor):
        return False

    def release(self):
        self._activo = False
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except Exception:
                self._proc.kill()


if __name__ == "__main__":
    cam = CamaraCSI()
    t0 = time.time()
    n = 0
    f = None
    while time.time() - t0 < 6:
        ok, x = cam.read()
        if ok:
            n += 1
            f = x
    print("cuadros en 6 s: %d (%.1f FPS) | exposicion %d us, ganancia %d | balance B,G,R = %s"
          % (n, n / 6.0, cam.exp, cam.gan, np.round(cam.ganancias, 2)))
    if f is not None:
        cv2.imwrite("csi_prueba.jpg", f)
        print("imagen guardada en csi_prueba.jpg", f.shape)
    cam.release()
