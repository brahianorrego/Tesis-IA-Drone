# -*- coding: utf-8 -*-
"""
Resta la cuadrícula fija de la cámara Sonix (ver capturar_patron.py).

La cuadrícula se suma a la imagen y pesa más en zonas oscuras, así que en cada
frame se estima cuánto de ella hay (alfa por canal, proyectando las altas
frecuencias del frame sobre el patrón en una versión reducida) y se resta eso.
"""
import os

import cv2
import numpy as np


class CorrectorPatron(object):

    def __init__(self, ruta="patron_camara.npy"):
        self.activo = os.path.exists(ruta)
        self.alfa = np.zeros(3, np.float32)
        if not self.activo:
            return
        self.patron = np.load(ruta).astype(np.float32)
        self._chico = cv2.resize(self.patron, (160, 120), interpolation=cv2.INTER_AREA)
        self._norma = (self._chico ** 2).sum(axis=(0, 1)) + 1e-6

    def corregir(self, frame):
        if not self.activo or frame.shape[:2] != self.patron.shape[:2]:
            return frame
        f = cv2.resize(frame, (160, 120), interpolation=cv2.INTER_AREA).astype(np.float32)
        hp = f - cv2.GaussianBlur(f, (0, 0), 30)   # misma escala que el sigma=120 del patrón (160 px de ancho)
        alfa = (hp * self._chico).sum(axis=(0, 1)) / self._norma
        self.alfa = np.clip(alfa, 0.0, 3.0).astype(np.float32)
        out = frame.astype(np.float32) - self.patron * self.alfa
        return np.clip(out, 0, 255).astype(np.uint8)


class RealceContraste(object):
    """CLAHE sobre la luminancia: quita el velo que deja el infrarrojo (la cámara no tiene IR-cut)."""

    def __init__(self, limite=2.5, rejilla=8):
        self._clahe = cv2.createCLAHE(clipLimit=limite, tileGridSize=(rejilla, rejilla))

    def aplicar(self, frame):
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = self._clahe.apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
