# -*- coding: utf-8 -*-
"""
FASE G · DECISOR IA del mínimo indispensable: la IA no solo detecta, también DECIDE si intervenir.

Un clasificador MLP (scikit-learn, la arquitectura original del proyecto) estima, cuadro a cuadro, la probabilidad de que
"si el piloto sigue igual, en los próximos T_HORIZONTE s el dron choque o una persona quede a menos de 2 m". Con esa
probabilidad decide CONTINUAR o DETENER_Y_ASCENDER (o solo DETENER cuando la envolvente no autoriza el ascenso).

Entradas: SOLO lo que la Jetson tiene en el dron real, calculado igual que allí (ver CARACTERISTICAS): la caja de YOLO
(alto, ancho, área, ángulo horizontal y su variación, confianza, cuadros seguidos), el LiDAR, la velocidad propia del EKF
de ArduPilot y el seguimiento alfa-beta (distancia, velocidad de acercamiento y lateral, tiempo sin detección).

Etiquetas AUTOMÁTICAS: vuelos sin intervención (el piloto sigue igual) con la verdad del simulador; para cada cuadro se
mira el futuro real del mismo vuelo. Entrenamiento, validación y prueba se separan por SEMILLAS (mundos distintos).

Decisores para comparar (misma interfaz que sistema.SistemaMinimo):
  · "reglas": sistema.SistemaMinimo (umbrales fijos)
  · "ia": la IA sola (sin reglas)
  · "ia_env": la IA dentro de la ENVOLVENTE de reglas duras, tal como las escribe CLAUDE.md (regla 5): el bloqueo
    frontal por LiDAR (< 3 m avanzando) y la parada del operador MANDAN sobre la IA; el árbitro AUTORIZA (no obliga) la
    evasión ante amenaza real (< 3 m, o < 8 m acercándose): sin su autorización la IA solo puede DETENER, no subir.
    Más una salvaguarda GEOMÉTRICA (TTC_SALVAGUARDA): persona seguida que va a pasar a < 2 m en menos de 1.5 s.
  · "ia_env_estricta": lo mismo y, además, una persona a menos de 3 m OBLIGA a detenerse (más estricto que la regla).

Exportación para la Jetson: decision.pkl (modelo de scikit-learn) y decision.json (pesos, normalización, umbral y nombres
de las entradas) con `predecir_json`, una implementación en NumPy puro que da lo mismo que scikit-learn.
"""
import json
import os
import pickle

import numpy as np

from . import sensores as S
from . import sistema as M

AQUI = os.path.dirname(os.path.abspath(__file__))
T_HORIZONTE = 3.0              # s hacia adelante para la etiqueta
D_PERSONA_ETIQ = 2.0           # m: "la persona entra a 2 m" (horizontal, con el dron a su alcance)
TTC_SALVAGUARDA = 1.5          # s: salvaguarda GEOMÉTRICA de la envolvente (no es el árbitro): con la persona seguida, si
                               # su punto de máximo acercamiento previsto queda a < 2 m y le faltan menos de esto para
                               # entrar a los 2 m, se detiene aunque la IA diga CONTINUAR (personas que entran tarde al
                               # campo de la cámara, de lado)
HOLGURA_PANEL = 0.5            # m: holgura mínima al panel
CARACTERISTICAS = ["detectada", "alto_caja", "ancho_caja", "area_caja", "angulo_abs", "d_angulo_abs", "confianza",
                   "cuadros_seguidos", "lidar", "lidar_util", "v_propia", "d_seguimiento", "v_acercamiento", "v_lateral",
                   "t_sin_deteccion"]


class Extractor(object):
    """Calcula las entradas del decisor a partir de las medidas (con retardo), como lo haría la Jetson."""

    def __init__(self, n):
        self.n = n
        self.trk = M.SistemaMinimo(n, activo=False)        # mismo seguimiento alfa-beta que las reglas
        self.seguidos = np.zeros(n)
        self.ang_ant = np.full(n, np.nan)
        self.d_ang = np.zeros(n)

    def __call__(self, m, piloto_v, dz):
        no = np.zeros(self.n, bool)
        self.trk.actualizar(m, piloto_v, no, no, no, dz)
        t = self.trk
        det = m["det"]
        self.seguidos = np.where(det, self.seguidos + 1, 0)
        ang = np.abs(m["rumbo"])
        d_ang_i = np.where(det & ~np.isnan(self.ang_ant), (ang - self.ang_ant) / M.DT, 0.0)
        self.d_ang = np.where(det, 0.7 * self.d_ang + 0.3 * d_ang_i, self.d_ang)
        self.ang_ant = np.where(det, ang, np.nan)
        en_trk = t.t_sin <= M.T_SOSTIENE
        d = np.hypot(t.rel_x, t.rel_y)
        # velocidad lateral relativa: componente perpendicular a la línea de vista
        ux, uy = t.rel_x / np.maximum(d, 1e-6), t.rel_y / np.maximum(d, 1e-6)
        v_lat = np.abs(-uy * t.vrx + ux * t.vry)
        suelo = m["dz"] / max(np.sin(np.radians(-M.GIMBAL_FRONTAL)), 1e-6)
        util = (m["lid"] < S.LIDAR_MAX - 0.05) & (np.abs(m["lid"] - suelo) > 1.0)
        X = np.stack([
            det.astype(float), m["alto"], m["ancho"], m["alto"] * m["ancho"],
            np.where(det, ang / (S.HFOV / 2), 1.0), np.clip(self.d_ang, -30, 30) / 10.0, m["conf"],
            np.minimum(self.seguidos, 30) / 30.0,
            np.where(util, m["lid"], S.LIDAR_MAX) / S.LIDAR_MAX, util.astype(float), m["v_av"] / 10.0,
            np.where(en_trk, np.minimum(d, 30.0), 30.0) / 30.0, np.where(en_trk, np.clip(t.vac, -8, 8), 0.0) / 5.0,
            np.where(en_trk, np.minimum(v_lat, 8), 0.0) / 5.0, np.minimum(t.t_sin, 2.0) / 2.0], axis=1)
        return X.astype(np.float32)


# ------------------------------------------------------------------------------------------- datos y etiquetas
def _mundo_aleatorio(semilla, n):
    """Un mundo con n vuelos variados: velocidades, personas (quietas, que vienen, que cruzan, paralelas), panel o no y una
    degradación de sensores al azar (todo el mundo comparte panel y degradación; los vuelos no)."""
    r = np.random.default_rng(10_000 + semilla)
    cond = S.Condicion("aleatoria", recall=float(r.choice([1.0, 1.0, 0.85, 0.7])),
                       oclusion=float(r.choice([1.0, 1.0, 1.0, 0.5, 0.3])),
                       k_lidar=float(r.choice([1.0, 1.0, 3.0])), perdida_lidar=float(r.choice([0.0, 0.0, 0.05])),
                       retardo=int(r.choice([1, 1, 2, 3])), viento=float(r.choice([0.0, 0.0, 3.0])))
    paneles = []
    if r.random() < 0.4:
        x_p = r.uniform(5, 30)
        paneles = [(x_p, -3.0, x_p, 3.0, S.ALTO_PANEL)]
    w = M.Mundo(n, semilla, paneles=paneles, cond=cond)
    rr = w.rng
    v = np.where(rr.random(n) < 0.2, 0.0, rr.uniform(0.5, 8.0, n))
    w.dx[:] = -rr.uniform(0, 10, n)
    w.psi[:] = np.radians(rr.uniform(-2.0, 2.0, n))
    w.dy[:] = rr.uniform(-0.3, 0.3, n)
    # nada, quieta, viene, cruza, paralela, al azar, delante en el mismo sentido (más rápida o más lenta que el dron)
    tipo = rr.choice(7, n, p=[0.08, 0.17, 0.17, 0.28, 0.13, 0.05, 0.12])
    w.activa[:] = tipo > 0
    px = rr.uniform(5, 35, n)
    py = rr.uniform(-1.5, 1.5, n)
    vp = rr.uniform(0.8, 4.0, n)
    pvx, pvy = np.zeros(n), np.zeros(n)
    pvx = np.where(tipo == 2, -vp, pvx)
    # cruza: atraviesa la trayectoria a xc, a veces a tiempo de chocar y a veces no
    xc = rr.uniform(3, 30, n)
    lado = np.where(rr.random(n) < 0.5, -1.0, 1.0)
    dist_lat = rr.uniform(3, 15, n)
    px = np.where(tipo == 3, xc, px)
    py = np.where(tipo == 3, lado * dist_lat, py)
    pvy = np.where(tipo == 3, -lado * vp, pvy)
    # paralela: camina a 2-6 m del costado, en el mismo sentido o en contra
    py = np.where(tipo == 4, lado * rr.uniform(2.0, 6.0, n), py)
    pvx = np.where(tipo == 4, np.where(rr.random(n) < 0.5, -vp, vp * 0.5), pvx)
    # al azar
    ang = rr.uniform(0, 2 * np.pi, n)
    pvx = np.where(tipo == 5, vp * np.cos(ang), pvx)
    pvy = np.where(tipo == 5, vp * np.sin(ang), pvy)
    py = np.where(tipo == 5, rr.uniform(-8, 8, n), py)
    # delante en la trayectoria, caminando o trotando en el mismo sentido: si es más lenta que el dron hay riesgo
    pvx = np.where(tipo == 6, rr.uniform(0.3, 3.0, n), pvx)
    py = np.where(tipo == 6, rr.uniform(-1.0, 1.0, n), py)
    w.px[:], w.py[:], w.pvx[:], w.pvy[:] = px, py, pvx, pvy
    return w, v, tipo


def generar(semillas, n=64, dur=25.0):
    """Vuelos SIN intervención (el piloto sigue igual). Devuelve X, y (riesgo en los próximos T_HORIZONTE s) y el grupo
    (semilla) de cada cuadro."""
    Xs, ys, gs = [], [], []
    pasos, H = int(dur / M.DT), int(T_HORIZONTE / M.DT)
    for sem in semillas:
        w, v, _ = _mundo_aleatorio(sem, n)
        ex = Extractor(n)
        malo = np.zeros((pasos, n), bool)
        X = np.zeros((pasos, n, len(CARACTERISTICAS)), np.float32)
        for k in range(pasos):
            m = w.medir()
            X[k] = ex(m, v, w.dz)
            w.paso(v * np.cos(w.psi), v * np.sin(w.psi), np.clip(1.0 * (M.Z_PILOTO - w.dz), -0.5, 0.5))
            # verdad: ¿en este instante (después del paso) hay choque, persona a < 2 m o holgura < 0.5 m al panel?
            dh = np.hypot(w.px - w.dx, w.py - w.dy)
            b = w.activa & (dh < D_PERSONA_ETIQ) & (w.dz < M.ALCANCE_Z)
            for ax, ay, bx, by, h in w.paneles:
                b |= (S.distancia_segmento(w.dx, w.dy, ax, ay, bx, by) - M.RADIO_DRON < HOLGURA_PANEL) & (w.dz < h + 0.2)
            malo[k] = b
        # etiqueta: algún "malo" en (k, k + H]
        acum = np.concatenate([np.zeros((1, n), int), np.cumsum(malo, 0)], 0)
        y = np.zeros((pasos, n), bool)
        for k in range(pasos):
            fin = min(k + H, pasos - 1)
            y[k] = (acum[fin + 1] - acum[k + 1]) > 0
        # solo cuadros con el dron sano (antes del primer choque real) y con horizonte completo
        primer = np.where(malo.any(0), malo.argmax(0), pasos)
        valido = (np.arange(pasos)[:, None] <= primer[None, :]) & (np.arange(pasos)[:, None] < pasos - H)
        Xs.append(X[valido]); ys.append(y[valido]); gs.append(np.full(valido.sum(), sem))
    return np.concatenate(Xs), np.concatenate(ys), np.concatenate(gs)


# ------------------------------------------------------------------------------------------- modelo
class Modelo(object):
    """MLP + normalización + umbral; se guarda en pickle y en JSON."""

    def __init__(self, clf=None, media=None, desv=None, umbral=0.5, k_seguidos=1):
        self.clf, self.media, self.desv, self.umbral, self.k_seguidos = clf, media, desv, umbral, k_seguidos

    def proba(self, X):
        return self.clf.predict_proba((X - self.media) / self.desv)[:, 1]

    def a_json(self):
        return {"entradas": CARACTERISTICAS, "media": self.media.tolist(), "desv": self.desv.tolist(),
                "capas": [{"W": W.tolist(), "b": b.tolist()} for W, b in zip(self.clf.coefs_, self.clf.intercepts_)],
                "activacion": self.clf.activation, "salida": "logistic", "umbral": float(self.umbral),
                "k_seguidos": int(self.k_seguidos), "horizonte_s": T_HORIZONTE,
                "clases": ["CONTINUAR", "DETENER_Y_ASCENDER"]}

    def guardar(self, carpeta=AQUI):
        with open(os.path.join(carpeta, "decision.pkl"), "wb") as fh:
            pickle.dump({"clf": self.clf, "media": self.media, "desv": self.desv, "umbral": self.umbral,
                         "k_seguidos": self.k_seguidos, "entradas": CARACTERISTICAS}, fh)
        with open(os.path.join(carpeta, "decision.json"), "w", encoding="utf-8") as fh:
            json.dump(self.a_json(), fh)

    @staticmethod
    def cargar(carpeta=AQUI):
        with open(os.path.join(carpeta, "decision.pkl"), "rb") as fh:
            d = pickle.load(fh)
        return Modelo(d["clf"], d["media"], d["desv"], d["umbral"], d["k_seguidos"])


def predecir_json(pesos, X):
    """Lo que corre en la Jetson: el MLP con NumPy puro a partir de decision.json. Devuelve la probabilidad de riesgo."""
    a = (np.asarray(X, float) - np.array(pesos["media"])) / np.array(pesos["desv"])
    capas = pesos["capas"]
    for j, c in enumerate(capas):
        a = a @ np.array(c["W"]) + np.array(c["b"])
        if j < len(capas) - 1:
            a = np.maximum(a, 0.0) if pesos["activacion"] == "relu" else np.tanh(a)
    return 1.0 / (1.0 + np.exp(-a[:, 0]))


# ------------------------------------------------------------------------------------------- decisores
class DecisorIA(object):
    """Misma interfaz que sistema.SistemaMinimo. con_envolvente: reglas duras alrededor de la IA."""

    def __init__(self, n, modelo, con_envolvente=True, activo=True, forzar_3m=False, ascenso_libre=False):
        self.n, self.modelo, self.env, self.activo = n, modelo, con_envolvente, activo
        self.forzar_3m = forzar_3m
        self.ascenso_libre = ascenso_libre        # SOLO para medir el costo del veto del árbitro al ascenso (no va al dron)
        self.ex = Extractor(n)
        self.interviene = np.zeros(n, bool)
        self.motivo = np.zeros(n, int)                  # 1 obstáculo, 2 persona, 3 IA
        self.sobre = np.zeros(n, int)
        self.sube = np.zeros(n, bool)                   # con envolvente: el ascenso necesita al árbitro (o un obstáculo)
        self.z_hold = np.full(n, np.nan)
        self.p = np.zeros(n)

    def actualizar(self, m, piloto_v, operador_parada, operador_anular, operador_reanudar, dz_actual):
        X = self.ex(m, piloto_v, dz_actual)
        self.p = self.modelo.proba(X)
        self.sobre = np.where(self.p >= self.modelo.umbral, self.sobre + 1, 0)
        r_ia = self.sobre >= self.modelo.k_seguidos
        t = self.ex.trk
        en_trk = t.t_sin <= M.T_SOSTIENE
        d = np.hypot(t.rel_x, t.rel_y)
        arbitro = en_trk & ((d < M.D_CRITICA) | ((d < M.D_AMENAZA) & (t.vac > M.V_ACERCA)))
        suelo = m["dz"] / max(np.sin(np.radians(-M.GIMBAL_FRONTAL)), 1e-6)
        util = (m["lid"] < S.LIDAR_MAX - 0.05) & (np.abs(m["lid"] - suelo) > 1.0)
        bloqueo = util & (m["lid"] < M.D_BLOQUEO) & (m["v_av"] > 0.2)
        if self.env:
            geo = en_trk & (t.vac > M.V_ACERCA) & (t.cpa < M.CPA_RIESGO) & (d - D_PERSONA_ETIQ < TTC_SALVAGUARDA * t.vac)
            r_env = bloqueo | geo | ((en_trk & (d < M.D_CRITICA)) if self.forzar_3m else False)
            riesgo = (r_ia | r_env) & self.activo
            # sube si lo autoriza el árbitro, si es un obstáculo (LiDAR) o si no hay ninguna persona seguida cerca
            sube_ok = arbitro | bloqueo | (util & ~en_trk) | ~(en_trk & (d < 15.0)) | self.ascenso_libre
        else:
            riesgo = r_ia & self.activo
            sube_ok = np.ones(self.n, bool)
        nuevo = riesgo & ~self.interviene
        self.motivo = np.where(nuevo, np.where(bloqueo, 1, np.where(arbitro, 2, 3)), self.motivo)
        self.interviene |= riesgo
        self.interviene &= ~operador_reanudar
        self.sube = np.where(self.interviene, self.sube | sube_ok, False)
        vx = piloto_v * np.cos(m["psi"])
        vy = piloto_v * np.sin(m["psi"])
        self.z_hold = np.where(np.isnan(self.z_hold), dz_actual, self.z_hold)
        vz = np.clip(1.0 * (self.z_hold - dz_actual), -0.5, 0.5)
        sis = self.interviene & ~operador_anular
        vx, vy = np.where(sis, 0.0, vx), np.where(sis, 0.0, vy)
        sube = sis & self.sube
        vz = np.where(sube, np.clip(2.0 * (M.Z_SEGURA - dz_actual), 0.0, M.VEL_ASCENSO_MAX), vz)
        self.z_hold = np.where(sube, np.maximum(dz_actual, self.z_hold), self.z_hold)
        vx, vy = np.where(operador_parada, 0.0, vx), np.where(operador_parada, 0.0, vy)
        vz = np.where(operador_parada & ~sube, 0.0, vz)
        return vx, vy, vz, nuevo


_MODELO = None


def modelo_guardado():
    global _MODELO
    if _MODELO is None:
        _MODELO = Modelo.cargar()
    return _MODELO


def crear_decisor(nombre, n, activo=True):
    if nombre == "reglas":
        return M.SistemaMinimo(n, activo=activo)
    return DecisorIA(n, modelo_guardado(), con_envolvente=nombre.startswith("ia_env"), activo=activo,
                     forzar_3m=(nombre == "ia_env_estricta"), ascenso_libre=(nombre == "ia_env_ascenso_libre"))
