# -*- coding: utf-8 -*-
"""
MÍNIMO INDISPENSABLE del proyecto de grado: el piloto vuela; el sistema solo interviene ante un riesgo definido.

Qué hace y qué NO hace:
  · El PILOTO manda siempre el avance frontal en línea recta (o deja el dron quieto: MODO ESTÁTICO).
  · El sistema NO navega, NO esquiva hacia los lados y NO elige objetivos. Solo, ante un RIESGO DEFINIDO:
        DETENCIÓN (consigna horizontal 0: frena con el control de velocidad de ArduPilot)
        + ASCENSO VERTICAL hasta la altura segura (3.30 m, fuera del alcance de una persona de pie y de su salto).
    La intervención queda retenida hasta que el operador la libera (REANUDAR): el humano decide qué sigue.
  · El OPERADOR puede intervenir siempre: PARADA (CH8: frena en el sitio; si el sistema está subiendo, el ascenso de
    protección sigue) y ANULAR (mando total del piloto, sin sistema).

RIESGO DEFINIDO (con las medidas de los sensores, retrasadas 100 ms y con ruido):
  1. Obstáculo al frente: el LiDAR mide menos que la distancia de frenado más un margen,
         L < v·T_LAG + v²/(2·A_FRENO) + MARGEN + RADIO_DRON          (v = rapidez de avance hacia el frente)
     o faltan menos de TTC_RIESGO (2.5 s) para tocarlo, o hay menos de D_BLOQUEO (3 m, el bloqueo frontal de las reglas
     duras) mientras avanza. Con los 2.5 s el sistema frena antes de que un operador atento sienta que tiene que hacerlo.
  2. Persona (YOLO) según el árbitro de las reglas duras: a menos de D_CRITICA (3 m), o a menos de D_AMENAZA (8 m)
     acercándose a más de V_ACERCA (0.4 m/s) Y con el punto de máximo acercamiento previsto en 6 s a menos de
     CPA_RIESGO (2 m). La última condición es más estricta que la regla dura (evita activarse con quien pasa de lado).

Las mismas condiciones con la verdad del simulador (sin ruido ni retardo) definen el "riesgo real" con que se miden las
activaciones verdaderas y falsas y la latencia.
"""
import numpy as np

from .control import AutopilotoArduPilot, GimbalBaseCam
from . import sensores as S

DT = S.DT
Z_PILOTO, Z_SEGURA = 2.3, 3.30
GIMBAL_FRONTAL = -5.0              # cámara casi horizontal: ve personas y paneles al frente; el suelo cae a ~26 m
RADIO_DRON = 0.4
ALCANCE_H, ALCANCE_Z = 1.0, 2.6    # burbuja de una persona (horizontal y por debajo de esta altura)
D_CRITICA, D_AMENAZA, V_ACERCA = 3.0, 8.0, 0.4
CPA_RIESGO, T_CPA = 2.0, 6.0            # 6 s: con 3 s, a 1 m/s solo se activaba bajo los ~5 m
D_BLOQUEO = 3.0
A_FRENO, T_LAG, MARGEN = 2.5, 0.5, 1.5
TTC_RIESGO = 2.5
VEL_ASCENSO_MAX = 2.5              # m/s (WPNAV_SPEED_UP de ArduPilot)
ALFA_AB, BETA_AB = 0.5, 0.1        # filtro alfa-beta de la posición y la velocidad relativas de la persona
T_SOSTIENE = 0.5                   # s que el seguimiento se sostiene sin detección (predice) antes de soltarlo


class Mundo(object):
    """n vuelos en paralelo: un dron, a lo sumo una persona y una lista fija de paneles [(ax, ay, bx, by, h)]."""

    def __init__(self, n, semilla, paneles=(), nivel_viento=0.1, cond=S.NOMINAL):
        self.n, self.rng = n, np.random.default_rng(semilla)
        self.cond = cond
        self.rng_deg = np.random.default_rng(semilla + 7919)      # azar propio de las degradaciones (no altera el nominal)
        self.rng_caja = np.random.default_rng(semilla + 104729)   # azar propio de la caja de YOLO (fase G)
        self.w_rafaga = np.zeros(n)
        z = lambda: np.zeros(n)
        self.paneles = [tuple(p) for p in paneles]
        self.dx, self.dy, self.dz, self.psi = z(), z(), np.full(n, Z_PILOTO), z()
        self.dvx, self.dvy, self.dvz, self.yaw_dps = z(), z(), z(), z()
        self.chasis_pitch, self.chasis_roll, self.acc_x, self.acc_y = z(), z(), z(), z()
        self.px, self.py, self.pvx, self.pvy = np.full(n, 999.0), np.full(n, 999.0), z(), z()
        self.activa = np.zeros(n, bool)
        e = S.ESTATURA
        self.estatura = np.clip(self.rng.normal(e[0], e[1], n), e[2], e[3])
        self.ap = AutopilotoArduPilot(n, self.rng)
        self.ap.reset(np.ones(n, bool), nivel_viento)
        self.gb = GimbalBaseCam(n, GIMBAL_FRONTAL)
        self.cam = np.full(n, GIMBAL_FRONTAL)
        self.t = 0.0
        self.cola = []                                   # medidas en tránsito (retardo de 100 ms)
        self.choque_panel, self.choque_persona = np.zeros(n, bool), np.zeros(n, bool)
        self.ultima = None

    def medir(self):
        det, d_est, rumbo, frac = S.camara(self.rng, self.dx, self.dy, self.dz, self.psi, self.cam, self.px, self.py,
                                           self.estatura, self.activa, self.paneles, self.cond)
        lid, lid_real, que = S.lidar(self.rng, self.dx, self.dy, self.dz, self.psi, self.cam, self.px, self.py,
                                     self.estatura, self.activa, self.paneles, self.cond, self.rng_deg)
        # velocidad propia (EKF de ArduPilot: GPS + IMU), con un poco de ruido
        v_av = (self.dvx * np.cos(self.psi) + self.dvy * np.sin(self.psi)) + self.rng.normal(0, 0.05, self.n)
        alto, ancho, conf = S.caja(self.rng_caja, self.dx, self.dy, self.dz, self.psi, self.cam, self.px, self.py,
                                   self.estatura, frac, det)
        m = dict(det=det, d=d_est, rumbo=rumbo, frac=frac, lid=lid, lid_real=lid_real, que=que, v_av=v_av,
                 dz=self.dz.copy(), psi=self.psi.copy(), alto=alto, ancho=ancho, conf=conf)
        self.cola.append(m)
        if len(self.cola) > self.cond.retardo + 1:
            self.cola.pop(0)
        self.ultima = m
        return self.cola[0]                              # lo que ve la lógica: la medida de hace 100 ms

    def paso(self, vx_sp, vy_sp, vz_sp):
        """Aplica consignas de velocidad (marco mundo) con la cascada de ArduPilot y mueve a la persona."""
        self.ap.paso(self, vx_sp, vy_sp, vz_sp, DT)
        if self.cond.viento > 0:
            # viento de cola (+x) con ráfagas (Ornstein-Uhlenbeck, ~2 s, ±1 m/s): empuja con el arrastre del cuadricóptero
            # relativo al aire. Se suma fuera de control.py (copia congelada), igual que una fuerza externa.
            a_ = np.exp(-DT / 2.0)
            self.w_rafaga = a_ * self.w_rafaga + 1.0 * np.sqrt(1 - a_ ** 2) * self.rng_deg.normal(size=self.n)
            w = np.clip(self.cond.viento + self.w_rafaga, 0.0, None)
            self.dvx += self.ap.ARRASTRE * w * DT
        self.ap.guinada(self, np.zeros(self.n), DT)
        self.psi = self.psi + np.radians(self.yaw_dps) * DT
        cab0 = self.chasis_pitch.copy()
        self.dx += self.dvx * DT
        self.dy += self.dvy * DT
        self.dz = np.clip(self.dz + self.dvz * DT, 0.5, 8.0)
        self.cam = self.gb.paso(np.full(self.n, GIMBAL_FRONTAL), self.chasis_pitch - cab0, DT)
        self.px = np.where(self.activa, self.px + self.pvx * DT, self.px)
        self.py = np.where(self.activa, self.py + self.pvy * DT, self.py)
        self.t += DT
        # choques (la verdad del simulador)
        for ax, ay, bx, by, h in self.paneles:
            d = S.distancia_segmento(self.dx, self.dy, ax, ay, bx, by)
            self.choque_panel |= (d < RADIO_DRON + 0.1) & (self.dz < h + 0.2)
        dh = np.hypot(self.px - self.dx, self.py - self.dy)
        self.choque_persona |= self.activa & (dh < ALCANCE_H) & (self.dz < ALCANCE_Z)


def riesgo_obstaculo(L, v_av, util=None):
    """Riesgo de obstáculo con la lectura del LiDAR L y la rapidez de avance v_av."""
    v = np.maximum(v_av, 0.0)
    d_freno = v * T_LAG + v ** 2 / (2 * A_FRENO) + MARGEN + RADIO_DRON
    r = (L < d_freno) | (L - RADIO_DRON < TTC_RIESGO * v) | ((L < D_BLOQUEO) & (v > 0.2))
    return r if util is None else r & util


def riesgo_persona(d, vac, cpa, det):
    return det & ((d < D_CRITICA) | ((d < D_AMENAZA) & (vac > V_ACERCA) & (cpa < CPA_RIESGO)))


def cpa_previsto(rx, ry, vx, vy):
    """Mínima distancia prevista en los próximos T_CPA s entre el dron (origen) y la persona en (rx, ry) con velocidad
    relativa (vx, vy)."""
    v2 = np.maximum(vx * vx + vy * vy, 1e-9)
    t = np.clip(-(rx * vx + ry * vy) / v2, 0.0, T_CPA)
    return np.hypot(rx + vx * t, ry + vy * t)


class SistemaMinimo(object):
    """La lógica que correría en la Jetson. Entrada: medidas (con retardo), mando del piloto, botones del operador.
    Salida: consignas de velocidad para ArduPilot."""

    def __init__(self, n, activo=True):
        self.n, self.activo = n, activo
        z = lambda: np.zeros(n)
        self.interviene = np.zeros(n, bool)
        self.motivo = np.zeros(n, int)                 # 0 nada, 1 obstáculo, 2 persona
        self.rel_x, self.rel_y, self.vrx, self.vry = z(), z(), z(), z()
        self.t_sin = np.full(n, np.inf)              # s desde la última detección
        self.vac, self.cpa = z(), np.full(n, np.inf)
        self.z_hold = np.full(n, np.nan)

    def actualizar(self, m, piloto_v, operador_parada, operador_anular, operador_reanudar, dz_actual):
        """m: medidas (retrasadas). piloto_v: avance pedido por el piloto (m/s, al frente). Devuelve (vx, vy, vz)."""
        n = self.n
        # persona: posición relativa (marco mundo) medida y seguimiento alfa-beta (predice a través de fallos cortos)
        b = m["psi"] + np.radians(m["rumbo"])
        mx, my = m["d"] * np.cos(b), m["d"] * np.sin(b)
        nuevo_trk = m["det"] & (self.t_sin > T_SOSTIENE)
        px_, py_ = self.rel_x + self.vrx * DT, self.rel_y + self.vry * DT       # predicción
        ex, ey = mx - px_, my - py_
        act = m["det"] & ~nuevo_trk
        self.rel_x = np.where(nuevo_trk, mx, np.where(act, px_ + ALFA_AB * ex, px_))
        self.rel_y = np.where(nuevo_trk, my, np.where(act, py_ + ALFA_AB * ey, py_))
        self.vrx = np.where(nuevo_trk, 0.0, np.where(act, self.vrx + BETA_AB * ex / DT, self.vrx))
        self.vry = np.where(nuevo_trk, 0.0, np.where(act, self.vry + BETA_AB * ey / DT, self.vry))
        self.t_sin = np.where(m["det"], 0.0, self.t_sin + DT)
        en_trk = self.t_sin <= T_SOSTIENE
        rx, ry = self.rel_x, self.rel_y
        d = np.hypot(rx, ry)
        self.vac = np.where(en_trk, -(rx * self.vrx + ry * self.vry) / np.maximum(d, 1e-6), 0.0)
        self.cpa = np.where(en_trk, cpa_previsto(rx, ry, self.vrx, self.vry), np.inf)
        r_per = riesgo_persona(d, self.vac, self.cpa, en_trk)
        # LiDAR: se descarta la lectura del suelo (la altura y el ángulo dicen dónde cae)
        suelo = m["dz"] / max(np.sin(np.radians(-GIMBAL_FRONTAL)), 1e-6)
        util = (m["lid"] < S.LIDAR_MAX - 0.05) & (np.abs(m["lid"] - suelo) > 1.0)
        r_obs = riesgo_obstaculo(m["lid"], m["v_av"], util)
        riesgo = (r_per | r_obs) & self.activo
        nuevo = riesgo & ~self.interviene
        self.motivo = np.where(nuevo, np.where(r_per, 2, 1), self.motivo)
        self.interviene |= riesgo
        self.interviene &= ~operador_reanudar                      # solo el operador la libera
        # consignas
        vx = np.full(n, 0.0)
        vy = np.full(n, 0.0)
        vx = piloto_v * np.cos(m["psi"])
        vy = piloto_v * np.sin(m["psi"])
        self.z_hold = np.where(np.isnan(self.z_hold), dz_actual, self.z_hold)
        vz = np.clip(1.0 * (self.z_hold - dz_actual), -0.5, 0.5)    # el piloto mantiene la altura
        sis = self.interviene & ~operador_anular
        vx, vy = np.where(sis, 0.0, vx), np.where(sis, 0.0, vy)
        vz = np.where(sis, np.clip(2.0 * (Z_SEGURA - dz_actual), 0.0, VEL_ASCENSO_MAX), vz)
        self.z_hold = np.where(sis, np.maximum(dz_actual, self.z_hold), self.z_hold)
        vx, vy = np.where(operador_parada, 0.0, vx), np.where(operador_parada, 0.0, vy)
        vz = np.where(operador_parada & ~sis, 0.0, vz)
        return vx, vy, vz, nuevo
