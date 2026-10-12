# -*- coding: utf-8 -*-
"""
Texturas del visor V16 (pasto, tierra, concreto del muro y del piso del hangar), hechas con ruido fractal periódico
(se repiten sin costuras). Son de autoría propia y se publican como CC0, igual que los recursos de Poly Haven.

Uso (desde simulacion/):  .venv/bin/python herramientas/generar_texturas.py
Salida: recursos/texturas/<nombre>_color.jpg, _normal.jpg, _rugosidad.jpg (1024 x 1024)
"""
import os

import numpy as np
from PIL import Image

N = 1024
AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "..", "recursos", "texturas")


def ruido(rng, escala, potencia=2.0, n=N):
    """Ruido fractal periódico: ruido blanco filtrado en frecuencia (espectro 1/f^potencia), normalizado a 0..1."""
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    r = np.sqrt(fx ** 2 + fy ** 2)
    r[0, 0] = 1.0
    filtro = 1.0 / (r * n / escala + 1.0) ** potencia
    filtro[0, 0] = 0.0
    z = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * filtro))
    return (z - z.min()) / (z.max() - z.min() + 1e-9)


def manchas(rng, n_manchas, radio, n=N):
    """Manchas suaves que se repiten en los bordes (para charcos de tierra, hongos, óxido)."""
    y, x = np.mgrid[0:n, 0:n]
    out = np.zeros((n, n))
    for _ in range(n_manchas):
        cx, cy, rr = rng.uniform(0, n), rng.uniform(0, n), radio * rng.uniform(0.5, 1.5)
        dx = np.minimum(np.abs(x - cx), n - np.abs(x - cx))
        dy = np.minimum(np.abs(y - cy), n - np.abs(y - cy))
        out = np.maximum(out, np.exp(-(dx ** 2 + dy ** 2) / (2 * rr ** 2)))
    return out


def normal_desde_altura(h, fuerza):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * fuerza
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * fuerza
    nz = np.ones_like(h)
    L = np.sqrt(gx ** 2 + gy ** 2 + nz ** 2)
    return np.stack([(-gx / L + 1) / 2, (gy / L + 1) / 2, (nz / L + 1) / 2], -1)


def guardar(nombre, color, normal, rug):
    os.makedirs(SALIDA, exist_ok=True)
    a8 = lambda a: (np.clip(a, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(a8(color)).save(os.path.join(SALIDA, nombre + "_color.jpg"), quality=88)
    Image.fromarray(a8(normal)).save(os.path.join(SALIDA, nombre + "_normal.jpg"), quality=92)
    Image.fromarray(a8(rug)).convert("L").save(os.path.join(SALIDA, nombre + "_rugosidad.jpg"), quality=88)
    print("  " + nombre)


def mezclar(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


def pasto(rng):
    """Pasto de potrero colombiano visto desde 2-6 m: matas, hojas finas, zonas secas y algo de tierra."""
    matas = ruido(rng, 40, 1.6)
    hojas = ruido(rng, 600, 0.6)                      # alta frecuencia: briznas
    seco = ruido(rng, 6, 2.2)
    tierra = np.clip((ruido(rng, 10, 2.0) - 0.62) * 5, 0, 1) * 0.55
    verde_osc = np.array([0.16, 0.24, 0.07])
    verde = np.array([0.30, 0.40, 0.12])
    amarillo = np.array([0.46, 0.44, 0.20])
    cafe = np.array([0.33, 0.26, 0.17])
    c = mezclar(np.broadcast_to(verde_osc, (N, N, 3)), np.broadcast_to(verde, (N, N, 3)), np.clip(matas * 1.3 - 0.1, 0, 1))
    c = mezclar(c, np.broadcast_to(amarillo, (N, N, 3)), np.clip((seco - 0.45) * 2.2, 0, 1) * 0.7)
    c = c * (0.72 + 0.5 * hojas[..., None])
    c = mezclar(c, np.broadcast_to(cafe, (N, N, 3)) * (0.8 + 0.4 * hojas[..., None]), tierra)
    alt = 0.6 * hojas + 0.4 * matas
    guardar("pasto", c, normal_desde_altura(alt, 6.0), 0.86 + 0.1 * hojas)


def tierra(rng):
    """Tierra apisonada (senderos y bases de los muros)."""
    a = ruido(rng, 30, 1.8)
    g = ruido(rng, 400, 0.7)
    piedras = np.clip((ruido(rng, 160, 1.0) - 0.7) * 6, 0, 1)
    c = np.array([0.36, 0.29, 0.21]) * (0.75 + 0.35 * a[..., None]) * (0.85 + 0.3 * g[..., None])
    c = mezclar(c, np.broadcast_to(np.array([0.52, 0.49, 0.45]), (N, N, 3)), piedras * 0.6)
    alt = 0.5 * a + 0.3 * g + 0.6 * piedras
    guardar("tierra", c, normal_desde_altura(alt, 5.0), 0.92 - 0.1 * piedras)


def concreto(rng, nombre, base, desgaste=1.0):
    """Concreto vaciado con poros, manchas de humedad y escurrimientos verticales (muros) o pulido (piso)."""
    a = ruido(rng, 8, 2.0)
    poros = np.clip((ruido(rng, 700, 0.4) - 0.72) * 8, 0, 1)
    fino = ruido(rng, 300, 0.8)
    hum = manchas(rng, 9, 90) * ruido(rng, 20, 1.5)
    # escurrimientos: ruido estirado en vertical (filas = alto del muro)
    chorros = ruido(rng, 50, 1.4)
    chorros = np.clip((np.repeat(chorros[::16, :], 16, 0)[:N] - 0.55) * 3, 0, 1) * desgaste
    c = np.array(base) * (0.72 + 0.5 * a[..., None]) * (0.86 + 0.24 * fino[..., None])
    c = c * (1 - 0.35 * hum[..., None] * desgaste) * (1 - 0.25 * chorros[..., None]) * (1 - 0.45 * poros[..., None])
    c = mezclar(c, np.broadcast_to(np.array([0.24, 0.25, 0.23]), (N, N, 3)), hum * 0.35 * desgaste)   # humedad oscura
    alt = 0.4 * fino + 0.3 * a - 0.8 * poros
    guardar(nombre, c, normal_desde_altura(alt, 3.0), 0.78 + 0.15 * fino - 0.2 * hum * desgaste)


def main():
    rng = np.random.default_rng(16)
    print("Generando texturas en", os.path.normpath(SALIDA))
    pasto(rng)
    tierra(rng)
    concreto(rng, "concreto_muro", [0.44, 0.44, 0.43], 1.0)
    concreto(rng, "concreto_piso", [0.40, 0.40, 0.40], 0.35)


if __name__ == "__main__":
    main()
