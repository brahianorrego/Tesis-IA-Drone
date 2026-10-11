# -*- coding: utf-8 -*-
"""
Sensores del mínimo indispensable (copia congelada de los modelos de la V15, 2026-10-10; independiente de entorno.py).

  · Cámara + YOLO: detecta personas dentro del cuadro (HFOV 38.9°, VFOV 29.7°) con una probabilidad que cae con la
    distancia, ruido en el rumbo y distancia por la altura de la caja suponiendo 1.72 m de estatura (si la persona real es
    más alta o más baja, o si la caja sale cortada por el borde de la imagen, la distancia sale sesgada, como en la Jetson).
  · LiDAR TF03 montado con la cámara: un solo rayo por el eje de la cámara, 0.1-30 m (objetivo oscuro a pleno sol),
    ruido de 2 cm. Ve paneles (2.6 m de alto), personas (cilindros) y el suelo.
  · Retardo: lo que llega a la lógica es la medida del paso anterior (100 ms: inferencia de YOLO + MAVLink).
"""
import numpy as np

DT = 0.1
HFOV, VFOV = 38.9, 29.7
RETARDO_PASOS = 1                  # 100 ms
LIDAR_MIN, LIDAR_MAX, LIDAR_SIGMA = 0.1, 30.0, 0.02
ALTURA_SUPUESTA = 1.72             # estatura que supone la Jetson para la distancia por la caja
ESTATURA = (1.72, 0.07, 1.58, 1.88)  # media, desviación, mínima, máxima (población colombiana adulta)
RADIO_PERSONA = 0.25
ANCHO_HOMBROS = 0.45               # si la caja sale cortada por el borde de la imagen, la distancia sale del ancho
ALTO_PANEL = 2.6
P_FRAC = (0.05, 0.35)              # la probabilidad de detección sube de 0 (5 % del alto visible) a la de la persona entera
                                   # (35 % visible), como en la V15
SIGMA_RUMBO, SIGMA_CAJA = 0.3, 0.03   # ° de ruido en el rumbo y fracción de ruido en la altura de la caja


def p_deteccion(d):
    """Probabilidad de que YOLO detecte a una persona entera a d m (igual que en la V15)."""
    return np.where(d < 20, 0.97, np.clip(0.97 - (d - 20) * 0.06, 0, 1))


class Condicion(object):
    """Condiciones degradadas (todas desactivadas = nominal).
    recall: tope de la probabilidad de detección por cuadro (sol de frente, desenfoque por movimiento).
    oclusion: fracción máxima del alto de la persona que queda a la vista (algo tapa el resto; la caja sale cortada).
    k_lidar, perdida_lidar: ruido del LiDAR multiplicado y fracción de lecturas perdidas (superficie poco reflectiva).
    retardo: pasos de 100 ms entre la medida y la lógica. viento: rapidez media del viento de cola (m/s), con ráfagas."""

    def __init__(self, nombre="Nominal", recall=1.0, oclusion=1.0, k_lidar=1.0, perdida_lidar=0.0, retardo=1, viento=0.0):
        self.nombre, self.recall, self.oclusion = nombre, recall, oclusion
        self.k_lidar, self.perdida_lidar, self.retardo, self.viento = k_lidar, perdida_lidar, retardo, viento


NOMINAL = Condicion()


def camara(rng, dx, dy, dz, psi, pitch_cam, px, py, estatura, activa, paneles, cond=NOMINAL):
    """Detección de UNA persona por entorno. Devuelve (detectada, distancia estimada, rumbo medido en °, fracción vista)."""
    rx, ry = px - dx, py - dy
    d = np.maximum(np.hypot(rx, ry), 1e-6)
    rumbo = np.degrees(np.arctan2(ry, rx) - psi)
    rumbo = (rumbo + 180.0) % 360.0 - 180.0
    # fracción vertical del cuerpo dentro del cuadro (de los pies a la cabeza)
    e_pies = np.degrees(np.arctan2(0.0 - dz, d))
    e_cab = np.degrees(np.arctan2(estatura - dz, d))
    abajo, arriba = pitch_cam - VFOV / 2, pitch_cam + VFOV / 2
    vis_v = np.clip(np.minimum(e_cab, arriba) - np.maximum(e_pies, abajo), 0, None)
    frac = vis_v / np.maximum(e_cab - e_pies, 1e-6)
    en_cuadro = (np.abs(rumbo) < HFOV / 2) & activa
    # un panel entre el dron y la persona la tapa (el dron vuela por debajo del borde del panel)
    tapada = np.zeros_like(d, dtype=bool)
    for ax, ay, bx, by, h in paneles:
        tapada |= _cruza(dx, dy, px, py, ax, ay, bx, by) & (dz < h)
    frac = np.where(en_cuadro & ~tapada, np.minimum(frac, cond.oclusion), 0.0)
    p_frac = np.clip((frac - P_FRAC[0]) / (P_FRAC[1] - P_FRAC[0]), 0.0, 1.0)
    det = (frac >= P_FRAC[0]) & (rng.random(d.shape) < np.minimum(p_deteccion(d), cond.recall) * p_frac)
    # distancia por la altura de la caja: alto visible en la imagen frente a la estatura que se supone
    alto_vis = frac * estatura * (1 + rng.normal(0, SIGMA_CAJA, d.shape))
    d_alto = d * ALTURA_SUPUESTA / np.maximum(alto_vis, 0.05)
    # caja cortada (cerca, los pies o la cabeza fuera del cuadro): la Jetson usa el ancho de los hombros (5 % de ruido;
    # los hombros reales varían ±10 % con la persona)
    hombros = ANCHO_HOMBROS * estatura / ESTATURA[0]
    d_ancho = d * ANCHO_HOMBROS / hombros * (1 + rng.normal(0, 0.05, d.shape))
    d_est = np.where(frac < 0.98, d_ancho, d_alto)
    rumbo_m = rumbo + rng.normal(0, SIGMA_RUMBO, d.shape)
    return det, np.minimum(d_est, 60.0), rumbo_m, frac


def caja(rng, dx, dy, dz, psi, pitch_cam, px, py, estatura, frac, det):
    """V15 · fase G: la caja de YOLO tal como la entrega la Jetson (normalizada al tamaño de la imagen) y su confianza.
    alto y ancho: fracción del alto y del ancho de la imagen; confianza: sube con lo visible y con el tamaño de la caja."""
    d = np.maximum(np.hypot(px - dx, py - dy), 1e-6)
    alto_ang = frac * (np.degrees(np.arctan2(estatura - dz, d)) - np.degrees(np.arctan2(0.0 - dz, d)))
    hombros = ANCHO_HOMBROS * estatura / ESTATURA[0]
    ancho_ang = 2 * np.degrees(np.arctan2(hombros / 2, d))
    alto = np.clip(alto_ang / VFOV * (1 + rng.normal(0, SIGMA_CAJA, d.shape)), 0, 1)
    ancho = np.clip(ancho_ang / HFOV * (1 + rng.normal(0, 0.05, d.shape)), 0, 1)
    p_frac = np.clip((frac - P_FRAC[0]) / (P_FRAC[1] - P_FRAC[0]), 0.0, 1.0)
    conf = np.clip(0.30 + 0.45 * p_frac + 0.25 * np.minimum(alto / 0.25, 1.0) + rng.normal(0, 0.06, d.shape), 0.05, 0.99)
    return np.where(det, alto, 0.0), np.where(det, ancho, 0.0), np.where(det, conf, 0.0)


def lidar(rng, dx, dy, dz, psi, pitch_cam, px, py, estatura, activa, paneles, cond=NOMINAL, rng_deg=None):
    """Rayo del TF03 por el eje de la cámara. Devuelve (distancia medida, distancia real, qué tocó: 0 nada, 1 suelo,
    2 panel, 3 persona)."""
    g = np.radians(pitch_cam)
    c, s = np.cos(psi), np.sin(psi)
    tg = np.tan(g)
    rng_ = np.full(dx.shape, np.inf)
    que = np.zeros(dx.shape, int)
    # suelo
    suelo = np.where(g < -1e-3, dz / np.maximum(-np.sin(g), 1e-6), np.inf)
    m = suelo < rng_
    rng_, que = np.where(m, suelo, rng_), np.where(m, 1, que)
    # paneles: distancia horizontal al cruce y altura del rayo ahí
    for ax, ay, bx, by, h in paneles:
        sh = _rayo_segmento(dx, dy, c, s, ax, ay, bx, by)
        z_r = dz + sh * tg
        r_ = np.where((z_r >= 0) & (z_r <= h), sh / np.cos(g), np.inf)
        m = r_ < rng_
        rng_, que = np.where(m, r_, rng_), np.where(m, 2, que)
    # persona (cilindro vertical)
    ox, oy = px - dx, py - dy
    t_c = ox * c + oy * s
    d_perp2 = ox ** 2 + oy ** 2 - t_c ** 2
    dentro = (d_perp2 < RADIO_PERSONA ** 2) & (t_c > 0) & activa
    sh = t_c - np.sqrt(np.maximum(RADIO_PERSONA ** 2 - d_perp2, 0))
    z_r = dz + sh * tg
    r_ = np.where(dentro & (z_r <= estatura) & (z_r >= 0), sh / np.cos(g), np.inf)
    m = r_ < rng_
    rng_, que = np.where(m, r_, rng_), np.where(m, 3, que)
    que = np.where(rng_ > LIDAR_MAX, 0, que)
    real = np.clip(rng_, LIDAR_MIN, LIDAR_MAX)
    medida = np.clip(real + rng.normal(0, LIDAR_SIGMA, dx.shape), LIDAR_MIN, LIDAR_MAX)
    if cond.k_lidar != 1.0 or cond.perdida_lidar > 0:
        medida = np.clip(real + (medida - real) * cond.k_lidar, LIDAR_MIN, LIDAR_MAX)
        medida = np.where(rng_deg.random(dx.shape) < cond.perdida_lidar, LIDAR_MAX, medida)   # sin retorno
    return medida, real, que


def _cruza(x1, y1, x2, y2, ax, ay, bx, by):
    """¿El segmento (x1,y1)-(x2,y2) corta al segmento A-B? (vectorizado en el primero)."""
    def lado(px_, py_, qx, qy, rx, ry):
        return (qx - px_) * (ry - py_) - (qy - py_) * (rx - px_)
    d1 = lado(ax, ay, bx, by, x1, y1)
    d2 = lado(ax, ay, bx, by, x2, y2)
    d3 = lado(x1, y1, x2, y2, ax, ay)
    d4 = lado(x1, y1, x2, y2, bx, by)
    return (d1 * d2 < 0) & (d3 * d4 < 0)


def _rayo_segmento(ox, oy, c, s, ax, ay, bx, by):
    """Distancia horizontal desde (ox, oy) en la dirección (c, s) hasta el segmento A-B (inf si no lo corta)."""
    ex, ey = bx - ax, by - ay
    den = c * ey - s * ex
    ok = np.abs(den) > 1e-9
    den = np.where(ok, den, 1.0)
    t = ((ax - ox) * ey - (ay - oy) * ex) / den
    u = ((ax - ox) * s - (ay - oy) * c) / den
    return np.where(ok & (t > 0) & (u >= 0) & (u <= 1), t, np.inf)


def distancia_segmento(px, py, ax, ay, bx, by):
    ex, ey = bx - ax, by - ay
    t = np.clip(((px - ax) * ex + (py - ay) * ey) / max(ex * ex + ey * ey, 1e-9), 0, 1)
    return np.hypot(px - (ax + t * ex), py - (ay + t * ey))
