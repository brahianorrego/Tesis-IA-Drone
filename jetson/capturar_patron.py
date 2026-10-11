# -*- coding: utf-8 -*-
"""
Captura la cuadrícula fija de la cámara Sonix (sin filtro IR-cut) para restarla después.

Mientras corre, mueva la cámara despacio mirando superficies OSCURAS: como la
cuadrícula no se mueve y el fondo sí, la mediana de muchos frames deja solo la
cuadrícula. Guarda patron_camara.npy (float32, componente de alta frecuencia).
Uso:  python3 capturar_patron.py [--segundos 15]
"""
import argparse
import time

import cv2
import numpy as np

import config as C
from percepcion import abrir_camara

ap = argparse.ArgumentParser()
ap.add_argument("--segundos", type=float, default=15.0)
ap.add_argument("--salida", default="patron_camara.npy")
ap.add_argument("--sigma", type=float, default=120.0,
                help="solo se quitan variaciones más anchas que esto; los círculos miden ~100 px")
a = ap.parse_args()

cap, tipo = abrir_camara(C)
for _ in range(10):
    cap.read()
print("LISTO", flush=True)
frames = []
t0 = time.time()
while time.time() - t0 < a.segundos:
    ok, f = cap.read()
    if ok:
        frames.append(f)
cap.release()
paso = max(1, len(frames) // 120)
pila = np.stack(frames[::paso])
print("frames capturados %d, usados %d" % (len(frames), len(pila)), flush=True)

mediana = np.median(pila, axis=0).astype(np.float32)
np.save("mediana_camara.npy", mediana)
patron = mediana - cv2.GaussianBlur(mediana, (0, 0), a.sigma)
np.save(a.salida, patron.astype(np.float32))

vis = cv2.normalize(patron.mean(axis=2), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
cv2.imwrite("patron_camara.png", vis)
print("patron guardado: rango %.1f a %.1f, desviacion %.2f" % (patron.min(), patron.max(), patron.std()))
