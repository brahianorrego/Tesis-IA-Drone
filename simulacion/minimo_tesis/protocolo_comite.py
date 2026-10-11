# -*- coding: utf-8 -*-
"""
PROTOCOLO DEL COMITÉ para el mínimo indispensable (semillas fijas: siempre da los mismos números).

Escenarios (el piloto avanza de frente en línea recta, o deja el dron quieto en el modo estático):
  a) avance hacia un panel fijo a 1, 2, 3 y 4 m/s                      -> debe activarse y no chocar
  b) avance hacia una persona quieta a 1.5 y 3 m/s                       -> debe activarse y no chocar
  c) persona que viene de frente caminando (1.4 m/s) o corriendo (3.3)   -> debe activarse y no chocar
  d) persona que cruza lejos, caminando o corriendo                      -> NO debe activarse (falsos positivos)
  e) modo estático: persona que viene hacia el dron caminando o corriendo -> debe activarse (sube) y no chocar;
     persona que pasa de lado a 5 m                                      -> NO debe activarse
Cada variante se corre con N vuelos (dron un poco distinto, viento, estatura de la persona, ruido de los sensores) con el
sistema y, como referencia, sin el sistema (el operador solo, con su parada de emergencia).

Métricas: tasa de éxito, activaciones verdaderas y falsas, eventos de riesgo, latencia riesgo -> comando -> frenado
efectivo, intervenciones del operador (paradas de emergencia porque el sistema no actuó a tiempo).

Uso (desde simulacion\\):
  .venv\\Scripts\\python.exe -m minimo_tesis.protocolo_comite            (N = 100 por variante, ~1 min)
  .venv\\Scripts\\python.exe -m minimo_tesis.protocolo_comite --n 20     (rápido)
Salidas: informes\\minimo_tesis_protocolo.md (tablas con intervalos de confianza del 95 %), informes\\
minimo_tesis_protocolo.csv (un renglón por vuelo) y minimo_tesis\\replay\\replay_protocolo.json (para el visor:
"Mínimo indispensable · protocolo del comité").
"""
import argparse
import csv
import datetime
import json
import os
import time

import numpy as np

from . import sensores as S
from . import sistema as M

AQUI = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.dirname(AQUI)
INFORMES = os.path.join(SIM, "informes")
T_REACCION_OP = 0.7            # s que tarda el operador en apretar la parada al ver un peligro inminente
TTC_OPERADOR = 2.0             # s: el operador ve el peligro cuando faltan menos de esto para el choque (o a menos de 1 m)
PANEL = (0.0, -3.0, 0.0, 3.0, S.ALTO_PANEL)
DY_PANEL = -17.0              # solo en la repetición del visor

# nombre: (grupo, descripción, debe_activar, piloto m/s, panel, persona (x, y, vx, vy) o None, duración s, x0 del dron)
ESCENARIOS = {}
for v in (1.0, 2.0, 3.0, 4.0):
    ESCENARIOS["a_panel_%.0f" % v] = ("a", "Panel fijo, avance a %.0f m/s" % v, True, v, True, None, 20.0 / v + 8.0, -20.0)
for v in (1.5, 3.0):
    ESCENARIOS["b_quieta_%.1f" % v] = ("b", "Persona quieta, avance a %.1f m/s" % v, True, v, False, (0.0, 0.0, 0.0, 0.0),
                                       20.0 / v + 8.0, -20.0)
for nom, vp in (("camina", 1.4), ("corre", 3.3)):
    ESCENARIOS["c_frente_" + nom] = ("c", "Persona de frente que %s (%.1f m/s), avance a 1 m/s" % (nom, vp), True, 1.0,
                                     False, (10.0, 0.0, -vp, 0.0), 20.0, -20.0)
for nom, vp in (("camina", 1.4), ("corre", 3.3)):
    ESCENARIOS["d_cruza_" + nom] = ("d", "Persona que cruza lejos y %s (%.1f m/s), avance a 1 m/s" % (nom, vp), False, 1.0,
                                    False, (0.0, -12.0, 0.0, vp), 24.0 / vp + 2.0, -20.0)
for nom, vp in (("camina", 1.4), ("corre", 3.3)):
    ESCENARIOS["e_estatico_" + nom] = ("e", "Modo estático: persona que viene y %s (%.1f m/s)" % (nom, vp), True, 0.0,
                                       False, (15.0, 0.0, -vp, 0.0), 30.0 / vp + 2.0, 0.0)
ESCENARIOS["e_estatico_lado"] = ("e", "Modo estático: persona que pasa de lado a 5 m (1.4 m/s)", False, 0.0, False,
                                 (15.0, 5.0, -1.4, 0.0), 30.0 / 1.4 + 2.0, 0.0)
# FASE G · escenarios de DISCRIMINACIÓN (no son parte de las 13 variantes del protocolo): personas cerca de la trayectoria
# que no van a chocar (trampas de falsos positivos con cajas ruidosas) junto a las que sí. Avance a 2 m/s desde x = -20.
ESCENARIOS_DISC = {
    "f_cruza_delante": ("f", "Cruza 3-4 m por delante del dron y sigue (no debe activarse)", False, 2.0, False,
                        (-6.5, -6.0, 0.0, 1.4), 16.0, -20.0),
    "f_cruza_a_tiempo": ("f", "Cruza justo por donde pasa el dron (debe activarse)", True, 2.0, False,
                         (-9.5, -6.0, 0.0, 1.4), 16.0, -20.0),
    "f_paralela_3": ("f", "Viene de frente, 3 m al costado de la trayectoria (no debe activarse)", False, 2.0, False,
                     (10.0, 3.0, -1.4, 0.0), 14.0, -20.0),
    "f_paralela_1": ("f", "Viene de frente, 1 m al costado (debe activarse)", True, 2.0, False,
                     (10.0, 1.0, -1.4, 0.0), 14.0, -20.0),
    "f_aleja": ("f", "Camina delante en el mismo sentido, más rápido que el dron (no debe activarse)", False, 1.0, False,
                (-12.0, 0.3, 1.6, 0.0), 16.0, -20.0),
}
TODOS = dict(ESCENARIOS, **ESCENARIOS_DISC)


def riesgo_real(w):
    """El riesgo definido con la verdad del simulador (sin ruido ni retardo)."""
    v_av = w.dvx * np.cos(w.psi) + w.dvy * np.sin(w.psi)
    m = w.ultima
    util = (m["que"] == 2) | (m["que"] == 3)
    r_obs = M.riesgo_obstaculo(m["lid_real"], v_av, util)
    rx, ry = w.px - w.dx, w.py - w.dy
    vx, vy = w.pvx - w.dvx, w.pvy - w.dvy
    d = np.hypot(rx, ry)
    vac = -(rx * vx + ry * vy) / np.maximum(d, 1e-6)
    cpa = M.cpa_previsto(rx, ry, vx, vy)
    r_per = M.riesgo_persona(d, vac, cpa, w.activa)
    return r_obs | r_per


def peligro_inminente(w):
    """Lo que hace apretar la parada al operador: menos de TTC_OPERADOR s para chocar con el panel o para entrar en la
    burbuja de la persona, o ya a menos de 1 m de hacerlo."""
    v_av = w.dvx * np.cos(w.psi) + w.dvy * np.sin(w.psi)
    p = np.zeros(w.n, bool)
    for ax, ay, bx, by, h in w.paneles:
        holgura = S.distancia_segmento(w.dx, w.dy, ax, ay, bx, by) - M.RADIO_DRON
        p |= ((holgura < 1.0) | (holgura < TTC_OPERADOR * v_av)) & (v_av > 0.3) & (w.dz < h + 0.2)
    rx, ry = w.px - w.dx, w.py - w.dy
    dh = np.hypot(rx, ry)
    acerca = -(rx * (w.pvx - w.dvx) + ry * (w.pvy - w.dvy)) / np.maximum(dh, 1e-6)
    holgura = dh - M.ALCANCE_H
    p |= w.activa & (w.dz < M.ALCANCE_Z) & ((holgura < 1.0) | ((acerca > 0.2) & (holgura < TTC_OPERADOR * acerca)))
    return p


def correr(nombre, n, semilla, con_sistema=True, grabar=False, cf=None, cond=S.NOMINAL, v=None, decisor="reglas",
           operador=True):
    """cf: el mismo vuelo SIN sistema (misma semilla: idéntico hasta la primera intervención). De él sale el riesgo
    real "contrafactual": si el sistema frena antes, el riesgo ya no ocurre en su propio vuelo, pero sí habría ocurrido."""
    grupo, desc, debe, v_pil, con_panel, pers, dur, x0 = TODOS[nombre]
    if v is not None:
        # otra rapidez de avance (barrido de la velocidad máxima segura): parte de más lejos para llegar a crucero antes de
        # que el obstáculo entre en el alcance útil del LiDAR (~26 m)
        v_pil = v
        if x0 != 0.0:
            x0 = -(30.0 + v * v / 6.0)
        dur = (abs(x0) + 10.0) / max(v, 1.0) + 8.0
    w = M.Mundo(n, semilla, paneles=[PANEL] if con_panel else [], cond=cond)
    r = w.rng
    w.dx[:] = x0 + r.uniform(-0.3, 0.3, n)
    w.dy[:] = r.uniform(-0.3, 0.3, n)
    w.psi[:] = np.radians(r.uniform(-2.0, 2.0, n))
    # el piloto apunta al objetivo: con el rumbo un poco torcido, la línea de vuelo pasa a ±0.3 m de x = 0
    w.dy[:] += np.tan(w.psi) * (w.dx - 0.0)
    if pers is not None:
        w.activa[:] = True
        w.px[:] = pers[0] + r.uniform(-0.5, 0.5, n)
        w.py[:] = pers[1] + r.uniform(-0.3, 0.3, n)
        k = r.uniform(0.9, 1.1, n)
        w.pvx[:], w.pvy[:] = pers[2] * k, pers[3] * k
    if decisor == "reglas":
        sis = M.SistemaMinimo(n, activo=con_sistema)
    else:                                              # fase G: el decisor IA (sola o con la envolvente de reglas)
        from . import decisor_ia as DIA
        sis = DIA.crear_decisor(decisor, n, activo=con_sistema)
    t_det = np.zeros(n)
    malo = np.zeros(n, bool)                           # fase G: persona a < 2 m (a su alcance) u holgura < 0.5 m al panel
    d_min_seg = np.full(n, np.inf)                     # distancia horizontal a la persona con el dron bajo la altura segura
    z = lambda: np.zeros(n)
    nan = lambda: np.full(n, np.nan)
    t_riesgo, t_act, t_freno, t_fuera, t_op = nan(), nan(), nan(), nan(), nan()
    hubo_riesgo, n_ev, ant = np.zeros(n, bool), np.zeros(n, int), np.zeros(n, bool)
    t_inm, parada = z(), np.zeros(n, bool)
    d_min = np.full(n, np.inf)
    d_min_h = np.full(n, np.inf)                       # distancia horizontal mínima a la persona a cualquier altura
    cuadros = []
    for k in range(int(dur / M.DT)):
        t = (k + 1) * M.DT
        m = w.medir()
        rr = riesgo_real(w)
        n_ev += rr & ~ant
        ant = rr
        t_riesgo = np.where(rr & np.isnan(t_riesgo), t, t_riesgo)
        hubo_riesgo |= rr
        # operador: parada de emergencia si ve un peligro inminente y el sistema no está actuando
        inm = peligro_inminente(w) & ~sis.interviene
        t_inm = np.where(inm, t_inm + M.DT, 0.0)
        nueva_p = (t_inm >= T_REACCION_OP) & ~parada & operador
        t_op = np.where(nueva_p, t, t_op)
        parada |= nueva_p
        piloto = np.full(n, v_pil)
        vx, vy, vz, nuevo = sis.actualizar(m, piloto, parada, np.zeros(n, bool), np.zeros(n, bool), w.dz)
        t_act = np.where(nuevo & np.isnan(t_act), t, t_act)
        t_det += sis.interviene * M.DT
        w.paso(vx, vy, vz)
        v_av = w.dvx * np.cos(w.psi) + w.dvy * np.sin(w.psi)
        t_freno = np.where(~np.isnan(t_act) & np.isnan(t_freno) & (v_av < 0.3), t, t_freno)
        t_fuera = np.where(~np.isnan(t_act) & np.isnan(t_fuera) & (w.dz >= M.ALCANCE_Z), t, t_fuera)
        if con_panel:
            d_min = np.minimum(d_min, S.distancia_segmento(w.dx, w.dy, *PANEL[:4]) - M.RADIO_DRON)
            malo |= (S.distancia_segmento(w.dx, w.dy, *PANEL[:4]) - M.RADIO_DRON < 0.5) & (w.dz < PANEL[4] + 0.2)
        if pers is not None:
            dh = np.hypot(w.px - w.dx, w.py - w.dy)
            d_min = np.minimum(d_min, np.where(w.dz < M.ALCANCE_Z, dh, np.inf))
            d_min_h = np.minimum(d_min_h, dh)
            malo |= (dh < 2.0) & (w.dz < M.ALCANCE_Z)
            d_min_seg = np.minimum(d_min_seg, np.where(w.dz < M.Z_SEGURA - 0.05, dh, np.inf))
        if grabar:
            cuadros.append(_cuadro(w, sis, m, v_pil, parada, desc, 0))
    choque = w.choque_panel | w.choque_persona
    activo = ~np.isnan(t_act)
    seguro = ~choque & ~parada
    exito = ~choque & (activo if debe else ~activo)
    if cf is not None:
        hubo_riesgo, n_ev, t_riesgo = cf["hubo_riesgo"], cf["n_ev"], cf["t_riesgo"]
    # la latencia "riesgo -> comando" se mide desde el riesgo real; si el sistema se adelantó (predicción), sale negativa
    res = dict(escenario=nombre, grupo=grupo, debe=debe, exito=exito, seguro=seguro, t_riesgo=t_riesgo, activo=activo, choque=choque, parada=parada,
               hubo_riesgo=hubo_riesgo, n_ev=n_ev, lat_cmd=t_act - t_riesgo, lat_freno=t_freno - t_act,
               lat_fuera=t_fuera - t_act, d_min=d_min, d_min_h=d_min_h, z_max=w.dz, t_op=t_op, t_det=t_det, malo=malo, d_min_seg=d_min_seg,
               t_act=t_act)
    res["verdadera"] = activo & hubo_riesgo
    res["falsa"] = activo & ~hubo_riesgo
    res["op_antes"] = parada & ((t_op <= t_act) | np.isnan(t_act))       # el operador actuó antes que el sistema
    return res, cuadros


def _cuadro(w, sis, m, v_pil, parada, desc, i):
    """Un cuadro del visor (formato de la fase 1 de la misión: piloto al mando, BLOQUEO cuando interviene)."""
    lid = float(w.ultima["lid_real"][i])
    lh = [w.dx[i] + lid * np.cos(w.psi[i]) * np.cos(np.radians(w.cam[i])),
          w.dy[i] + lid * np.sin(w.psi[i]) * np.cos(np.radians(w.cam[i])), w.dz[i] + lid * np.sin(np.radians(w.cam[i]))]
    vis = bool(w.ultima["det"][i])
    pers = []
    if w.activa[i]:
        pers.append({"rol": "peaton", "p": [round(float(w.px[i]), 3), round(float(w.py[i]), 3)],
                     "v": [round(float(w.pvx[i]), 2), round(float(w.pvy[i]), 2)], "vis": vis, "tap": False, "id": 7, "sz": 0.0,
                     "fv": round(float(w.ultima["frac"][i]), 2), "est": round(float(w.estatura[i]), 2), "res": None, "hr": None,
                     "ign": False, "cand": False, "run": bool(np.hypot(w.pvx[i], w.pvy[i]) > 2.5)})
    if parada[i]:
        msg = "PARADA DEL OPERADOR (CH8) · el dron queda quieto"
    elif sis.interviene[i]:
        msg = ({1: "RIESGO: obstáculo al frente", 2: "RIESGO: persona al frente",
                3: "RIESGO previsto por la IA (persona al frente)"}.get(int(sis.motivo[i]), "RIESGO")) + \
              (" · DETENCIÓN (el ascenso espera la autorización del árbitro) · espera al operador"
               if hasattr(sis, "sube") and not sis.sube[i] else
               " · DETENCIÓN + ASCENSO a %.2f m · espera al operador" % M.Z_SEGURA)
    else:
        msg = desc + (" · piloto: avance %.1f m/s" % v_pil if v_pil > 0 else " · piloto: quieto (modo estático)")
    c = dict(PLANTILLA)
    c.update({"d": [round(float(w.dx[i]), 3), round(float(w.dy[i]), 3), round(float(w.dz[i]), 3), round(float(w.psi[i]), 4)],
              "dv": [round(float(w.dvx[i]), 2), round(float(w.dvy[i]), 2)], "pers": pers,
              "p": pers[0]["p"] if pers else [999.0, 999.0], "pv": pers[0]["v"] if pers else [0.0, 0.0],
              "vis": vis, "lid": round(lid, 2), "ldt": round(lid, 2), "lh": [round(float(x), 2) for x in lh],
              "gmb": round(float(w.cam[i]), 1), "cp": round(float(w.chasis_pitch[i]), 1), "cr": round(float(w.chasis_roll[i]), 1),
              "bloq": bool(sis.interviene[i] or parada[i]), "msg": msg,
              "piloto": [0.0 if (sis.interviene[i] or parada[i]) else round(v_pil / 5.0, 2), 0.0],
              "dm": round(float(np.hypot(w.px[i] - w.dx[i], w.py[i] - w.dy[i])), 2) if w.activa[i] else 99.0})
    return c


# campos que el visor espera en cada cuadro (valores de la fase 1: IA inactiva)
PLANTILLA = {"fase": 1, "modo": 0, "est": 0, "cl": 0, "run": False, "las": False, "dh": 0.0, "ang": 0.0, "vac": 0.0, "yaw": 0.0,
             "trk": 0, "amz": False, "per": False, "giro": 0.0, "rep": False, "bf": 0, "pj": 0, "ninsp": 0, "wx": 0.0, "wy": 0.0,
             "mx": 0.0, "my": 0.0, "nadir": False, "ev": [0.0, 0.0], "bd": -1, "rfx": False, "gd": False, "nube": [], "dsc": False,
             "zia": 0.0, "gia": 0.0, "lt": 0, "flq": False, "va": False, "ruta": [], "det": [], "ux": 0.0, "uy": 0.0, "yc": False,
             "eg": 0.0, "op": 0, "t2": 0.0, "tf": 0.0, "tc": 0.0, "trd": 0.0, "rinde": False, "tsv": 0.0, "lm": 0, "tac": False,
             "eb": "MANUAL", "tpd": 0.0, "ciego": False, "dcg": 0.0, "npts": 0, "ent": False, "enta": False, "kf": None, "pf": [],
             "pfm": None, "acn": False, "dsep": 0.0, "trkp": 0, "conf": 1.0, "rcf": False, "pm": 0, "cnt": None, "lgu": 0, "um": False}


# CONDICIONES DEGRADADAS: cada una por separado y una combinada (los límites que menciona el documento del comité)
CONDICIONES = [
    S.NOMINAL,
    S.Condicion("YOLO recall 0.85 (sol de frente)", recall=0.85),
    S.Condicion("YOLO recall 0.70 (desenfoque)", recall=0.70),
    S.Condicion("Oclusión: medio cuerpo visible", oclusion=0.50),
    S.Condicion("Oclusión: solo torso visible", oclusion=0.30),
    S.Condicion("LiDAR ruido ×3 y 5 % sin retorno", k_lidar=3.0, perdida_lidar=0.05),
    S.Condicion("Latencia total 200 ms", retardo=2),
    S.Condicion("Latencia total 300 ms", retardo=3),
    S.Condicion("Viento de cola 3 m/s con ráfagas", viento=3.0),
    S.Condicion("Viento de cola 5 m/s con ráfagas", viento=5.0),
    S.Condicion("Combinada: recall 0.85 + medio cuerpo + LiDAR + 200 ms + viento 4 m/s", recall=0.85, oclusion=0.50,
                k_lidar=3.0, perdida_lidar=0.05, retardo=2, viento=4.0),
    # extremas: más allá de lo esperable, para ver dónde se rompe la percepción
    S.Condicion("Extrema: YOLO recall 0.40", recall=0.40),
    S.Condicion("Extrema: solo cabeza y hombros (15 % del alto)", oclusion=0.15),
    S.Condicion("Extrema: latencia total 500 ms", retardo=5),
]
VELOCIDADES = [float(v) for v in range(1, 13)]
# barrido de la velocidad de avance: escenario base y criterio de DETENCIÓN CON MARGEN (más exigente que "no chocar")
BARRIDO = [("a_panel_1", "Panel fijo", "holgura ≥ 0.5 m al panel"),
           ("b_quieta_1.5", "Persona quieta", "se detiene a ≥ 2 m"),
           ("c_frente_corre", "Persona de frente corriendo", "fuera de su alcance antes de los 2 m")]
UMBRAL_SEGURO = 0.95


def detiene_con_margen(nombre, r):
    """Panel: holgura de 0.5 m (a cualquier altura: pasarle por encima no cuenta, un muro real puede ser más alto).
    Persona quieta: se detiene a 2 m o más en horizontal (no le pasa por encima). Persona que viene: cuando está a menos
    de 2 m, el dron ya está fuera de su alcance (no hay cómo impedir que le pase por debajo)."""
    if TODOS[nombre][4]:
        return ~r["choque"] & (r["d_min"] >= 0.5)
    if TODOS[nombre][5][2] == 0.0:
        return ~r["choque"] & (r["d_min_h"] >= M.ALCANCE_H + 1.0)
    return ~r["choque"] & (r["d_min"] >= M.ALCANCE_H + 1.0)


def estudio_degradado(n, semilla):
    """Tabla de éxito por condición y escenario, y velocidad máxima segura por condición."""
    tabla, barrido, filas = {}, {}, []
    for ic, c in enumerate(CONDICIONES):
        for j, nom in enumerate(ESCENARIOS):
            sem = semilla + 1000 * j
            s_, _ = correr(nom, n, sem, False, cond=c)
            r, _ = correr(nom, n, sem, True, cf=s_, cond=c)
            tabla[(c.nombre, nom)] = r
            filas.append({"tipo": "escenario", "condicion": c.nombre, "escenario": nom, "v": ESCENARIOS[nom][3], "n": n,
                          "exito": int(r["exito"].sum()), "exito_sin_operador": int((r["exito"] & ~r["parada"]).sum()),
                          "choques": int(r["choque"].sum()), "act_falsas": int(r["falsa"].sum()),
                          "paradas_operador": int(r["parada"].sum())})
        for nom, _t, _crit in BARRIDO:
            for v in VELOCIDADES:
                r, _ = correr(nom, n, semilla + 50000 + int(10 * v), True, cond=c, v=v)
                ok = detiene_con_margen(nom, r)
                barrido[(c.nombre, nom, v)] = (int(ok.sum()), int(r["choque"].sum()))
                filas.append({"tipo": "barrido", "condicion": c.nombre, "escenario": nom, "v": v, "n": n,
                              "exito": int(ok.sum()), "exito_sin_operador": int((ok & ~r["parada"]).sum()),
                              "choques": int(r["choque"].sum()), "act_falsas": 0, "paradas_operador": int(r["parada"].sum())})
        print("  condición %d/%d: %s" % (ic + 1, len(CONDICIONES), c.nombre), flush=True)
    return tabla, barrido, filas


def v_max_segura(barrido, cond, nom, n):
    """Mayor rapidez probada tal que ella y todas las menores se detienen con margen en >= 95 % de los vuelos."""
    vmax = 0.0
    for v in VELOCIDADES:
        if barrido[(cond, nom, v)][0] < UMBRAL_SEGURO * n:
            break
        vmax = v
    return vmax


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, c - h), min(1.0, c + h)


def media_ic(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return "—"
    if len(x) == 1:
        return "%.2f" % x[0]
    h = 1.96 * x.std(ddof=1) / np.sqrt(len(x))
    return "%.2f [%.2f, %.2f]" % (x.mean(), x.mean() - h, x.mean() + h)


def pct(k, n, dec=0):
    p, a, b = wilson(k, n)
    f = "%%.%df" % dec
    return (f + " %% [" + f + ", " + f + "]") % (100 * p, 100 * a, 100 * b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="vuelos por variante")
    ap.add_argument("--semilla", type=int, default=2026)
    ap.add_argument("--sin-informe", action="store_true", help="solo imprime (para las pruebas)")
    ap.add_argument("--sin-degradadas", action="store_true", help="omite el estudio de condiciones degradadas (~6 min)")
    args = ap.parse_args()
    t0 = time.time()
    filas, con, sin = [], {}, {}
    replay = []
    for j, nom in enumerate(ESCENARIOS):
        sem = args.semilla + 1000 * j
        sin[nom], _ = correr(nom, args.n, sem, False)
        con[nom], cuadros = correr(nom, args.n, sem, True, grabar=True, cf=sin[nom])
        replay.append((nom, cuadros))
        r = con[nom]
        for i in range(args.n):
            filas.append({"escenario": nom, "grupo": r["grupo"], "vuelo": i, "semilla": sem, "debe_activar": int(r["debe"]),
                          "exito": int(r["exito"][i]), "activado": int(r["activo"][i]), "act_verdadera": int(r["verdadera"][i]),
                          "act_falsa": int(r["falsa"][i]), "riesgo_real": int(r["hubo_riesgo"][i]), "eventos_riesgo": int(r["n_ev"][i]),
                          "choque": int(r["choque"][i]), "parada_operador": int(r["parada"][i]),
                          "lat_riesgo_comando_s": _f(r["lat_cmd"][i]), "lat_comando_frenado_s": _f(r["lat_freno"][i]),
                          "lat_comando_fuera_alcance_s": _f(r["lat_fuera"][i]), "dist_min_m": _f(r["d_min"][i]),
                          "z_final_m": _f(r["z_max"][i]), "seguro_sin_sistema": int(sin[nom]["seguro"][i]),
                          "choque_sin_sistema": int(sin[nom]["choque"][i]), "parada_sin_sistema": int(sin[nom]["parada"][i])})
        print("%-20s éxito %3.0f %% (seguro sin sistema %3.0f %%) | activa %3.0f %% | choque %2.0f %% | parada op. %2.0f %%" % (
            nom, 100 * r["exito"].mean(), 100 * sin[nom]["seguro"].mean(), 100 * r["activo"].mean(), 100 * r["choque"].mean(),
            100 * r["parada"].mean()), flush=True)
    if args.sin_informe:
        return con, sin
    os.makedirs(INFORMES, exist_ok=True)
    ruta_csv = os.path.join(INFORMES, "minimo_tesis_protocolo.csv")
    with open(ruta_csv, "w", newline="", encoding="utf-8") as fh:
        wcsv = csv.DictWriter(fh, list(filas[0]))
        wcsv.writeheader()
        wcsv.writerows(filas)
    deg = None
    if not args.sin_degradadas:
        print("condiciones degradadas y barrido de velocidad...", flush=True)
        deg = estudio_degradado(args.n, args.semilla)
        with open(os.path.join(INFORMES, "minimo_tesis_degradadas.csv"), "w", newline="", encoding="utf-8") as fh:
            wcsv = csv.DictWriter(fh, list(deg[2][0]))
            wcsv.writeheader()
            wcsv.writerows(deg[2])
    _informe(con, sin, args, time.time() - t0, deg)
    _replay(replay)
    print("informe: informes\\minimo_tesis_protocolo.md, CSV y replay (%.0f s)" % (time.time() - t0))
    return con, sin


def _f(x):
    return "" if not np.isfinite(x) else round(float(x), 3)


def _informe(con, sin, args, seg, deg=None):
    n = args.n
    L = ["# Protocolo del comité · mínimo indispensable", "",
         "Generado por `minimo_tesis/protocolo_comite.py` · %d vuelos por variante · semilla base %d · %s · %.0f s" % (
             n, args.semilla, datetime.date.today().isoformat(), seg), "",
         "El piloto avanza de frente en línea recta (o deja el dron quieto en el modo estático). El sistema solo interviene "
         "ante el riesgo definido, con **DETENCIÓN + ASCENSO VERTICAL** a %.2f m, y espera al operador. Sensores con ruido "
         "y retardo de 100 ms; control de ArduPilot modelado (copias congeladas en `minimo_tesis/`). Entre corchetes, el "
         "intervalo de confianza del 95 %% (Wilson para porcentajes; media ± 1.96·σ/√n para tiempos)." % M.Z_SEGURA, "",
         "## Éxito", "",
         "Éxito: si el escenario pide activarse, se activa y no choca; si no lo pide, no se activa y no choca. *Éxito sin "
         "ayuda del operador*: lo mismo y, además, el operador no apretó la parada en ningún momento (la diferencia entre las "
         "dos columnas son los vuelos en que el operador apretó a la vez que el sistema). *Vuelo seguro sin el sistema*: el mismo vuelo con el operador solo, sin choque y sin "
         "que haya tenido que apretar la parada (la parada la aprieta al ver un choque a menos de %.1f s, con %.1f s de "
         "reacción)." % (TTC_OPERADOR, T_REACCION_OP), "",
         "| Escenario | ¿Debe activarse? | Éxito con el sistema | Éxito sin ayuda del operador | Vuelo seguro sin el sistema | Choques con / sin | Paradas del operador con / sin | Operador antes que el sistema |",
         "|---|:---:|---:|---:|---:|---:|---:|---:|"]
    for nom, (g, desc, debe, *_r) in ESCENARIOS.items():
        r, s = con[nom], sin[nom]
        L.append("| %s) %s | %s | %s | %s | %s | %d / %d | %d / %d | %d |" % (
            g, desc, "sí" if debe else "no", pct(r["exito"].sum(), n), pct((r["exito"] & ~r["parada"]).sum(), n),
            pct(s["seguro"].sum(), n),
            r["choque"].sum(), s["choque"].sum(), r["parada"].sum(), s["parada"].sum(), r["op_antes"].sum()))
    L += ["", "## Activaciones y eventos de riesgo", "",
          "Verdadera: se activó y hubo riesgo real (medido con la verdad del simulador, sin ruido). Falsa: se activó sin "
          "riesgo real. Eventos: veces que empieza una situación de riesgo real en el vuelo.", "",
          "| Escenario | Vuelos con riesgo real | Eventos de riesgo (media) | Activaciones verdaderas | Activaciones falsas | Riesgo real sin activación |",
          "|---|---:|---:|---:|---:|---:|"]
    for nom, (g, desc, *_r) in ESCENARIOS.items():
        r = con[nom]
        omit = (r["hubo_riesgo"] & ~r["activo"]).sum()
        L.append("| %s) %s | %d | %.2f | %s | %s | %d |" % (g, desc, r["hubo_riesgo"].sum(), r["n_ev"].mean(),
                                                          pct(r["verdadera"].sum(), n), pct(r["falsa"].sum(), n), omit))
    L += ["", "## Latencias (s)", "",
          "Riesgo → comando: desde que el riesgo es real hasta que el sistema manda detenerse (negativo: se adelantó por la "
          "predicción del acercamiento). Comando → frenado efectivo: hasta que la rapidez de avance cae por debajo de 0.3 m/s. "
          "Comando → fuera de alcance: hasta pasar los %.1f m de altura. Distancia mínima: al panel, la holgura (sin el radio "
          "del dron); a la persona, la horizontal mientras el dron estaba a su alcance (por debajo de %.1f m)." % (
              M.ALCANCE_Z, M.ALCANCE_Z), "",
          "| Escenario | Riesgo → comando | Comando → frenado efectivo | Comando → fuera de alcance | Distancia mínima (m) |",
          "|---|---:|---:|---:|---:|"]
    for nom, (g, desc, debe, *_r) in ESCENARIOS.items():
        r = con[nom]
        a = r["activo"]
        dm = r["d_min"][np.isfinite(r["d_min"])]
        frn = media_ic(r["lat_freno"][a]) if ESCENARIOS[nom][3] > 0 else "— (quieto)"
        L.append("| %s) %s | %s | %s | %s | %s |" % (g, desc, media_ic(r["lat_cmd"][a]), frn,
                                                   media_ic(r["lat_fuera"][a]), media_ic(dm) if len(dm) else "—"))
    tot = sum(con[k]["exito"].sum() for k in con)
    L += ["", "## Resumen", "",
          "- Éxito global con el sistema: %s de %d vuelos. Vuelos seguros sin el sistema (operador solo): %s." % (
              pct(tot, n * len(con), 1), n * len(con), pct(sum(sin[k]["seguro"].sum() for k in sin), n * len(sin))),
          "- Paradas de emergencia del operador con el sistema: %d de %d vuelos (%s); terminaron en choque: %d. Con una "
          "persona que corre hacia el dron el acercamiento es tan rápido que el tope de 8 m de la regla dura deja menos de "
          "2 s, y un operador atento aprieta a la vez que el sistema." % (
              sum(con[k]["parada"].sum() for k in con), n * len(con),
              ", ".join("%s: %d" % (k, con[k]["parada"].sum()) for k in con if con[k]["parada"].any()) or "ninguna",
              sum((con[k]["parada"] & con[k]["choque"]).sum() for k in con)),
          "- Activaciones falsas en los escenarios que no deben activarse (d y paso de lado): %d de %d." % (
              sum(con[k]["falsa"].sum() for k, e in ESCENARIOS.items() if not e[2]),
              n * sum(1 for e in ESCENARIOS.values() if not e[2])),
          ""] + (_seccion_degradadas(deg, n) if deg else []) + _seccion_campo() + ["## Límites del protocolo", "",
          "- Una sola persona o un solo panel por vuelo, suelo plano, panel de 2.6 m (por debajo del rayo del LiDAR desde "
          "2.3 m) y viento suave. No hay lluvia, noche ni oclusiones parciales por otros objetos.",
          "- El detector es un modelo estadístico de YOLO (probabilidad por distancia, ruido, estatura supuesta de 1.72 m y "
          "caja cortada); no son imágenes reales. La validación de campo debe repetir los escenarios a, b y d.",
          "- La parada del operador es un modelo (ve el choque a 2 s y reacciona en 0.7 s).",
          "", "Datos crudos: `minimo_tesis_protocolo.csv` (un renglón por vuelo). Repetición en el visor: selector "
          "\"Mínimo indispensable · protocolo del comité\"."]
    with open(os.path.join(INFORMES, "minimo_tesis_protocolo.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def _seccion_degradadas(deg, n):
    tabla, barrido, _ = deg
    noms = [c.nombre for c in CONDICIONES]
    L = ["## Condiciones degradadas", "",
         "Los mismos escenarios con una degradación a la vez y una combinada, %d vuelos cada uno, SIN reajustar el sistema "
         "(sus umbrales suponen 100 ms de latencia y sensores nominales). Recall de YOLO: tope de la probabilidad de "
         "detección por cuadro. Oclusión: algo tapa el resto del cuerpo y la caja sale cortada (la distancia sale de los "
         "hombros). LiDAR: ruido ×3 y 5 %% de lecturas sin retorno. Viento: de cola (empuja hacia el obstáculo), con "
         "ráfagas de ±1 m/s." % n, "",
         "### Éxito por escenario (%)", "",
         "| Escenario | " + " | ".join("C%d" % k for k in range(len(noms))) + " |",
         "|---|" + "---:|" * len(noms)]
    for nom, (g, desc, *_r) in ESCENARIOS.items():
        celdas = []
        for c in noms:
            r = tabla[(c, nom)]
            txt = "%.0f" % (100 * r["exito"].mean())
            if r["choque"].any():
                txt += " (%d ch.)" % r["choque"].sum()
            if r["falsa"].any():
                txt += " (%d f.)" % r["falsa"].sum()
            celdas.append(txt)
        L.append("| %s) %s | %s |" % (g, desc, " | ".join(celdas)))
    L += ["", "Condiciones: " + "; ".join("**C%d** %s" % (k, c) for k, c in enumerate(noms)) + ". "
          "(ch.: vuelos con choque; f.: activaciones falsas.)", "",
          "### Hasta dónde funciona: velocidad de avance máxima segura (m/s)", "",
          "Barrido de 1 a %d m/s, %d vuelos por velocidad. Segura: esa velocidad y todas las menores cumplen el criterio en "
          "al menos el %.0f %% de los vuelos. El criterio es **detenerse con margen**, más exigente que no chocar: panel, "
          "holgura de 0.5 m sin pasarle por encima (un muro real puede ser más alto); persona quieta, detenerse a 2 m o más; "
          "persona que corre hacia el dron (que la velocidad es del dron), estar fuera de su alcance antes de que llegue a 2 m. "
          "El dron parte de más lejos para llegar a crucero antes del alcance útil del LiDAR." % (
              VELOCIDADES[-1], n, 100 * UMBRAL_SEGURO), "",
          "| Condición | " + " | ".join(t for _n, t, _c in BARRIDO) + " | Primera falla (vuelos con margen / choques) |",
          "|---|" + "---:|" * len(BARRIDO) + "---|"]
    for k, c in enumerate(noms):
        vs, fallas = [], []
        for nom, t, _crit in BARRIDO:
            vm = v_max_segura(barrido, c, nom, n)
            vs.append("%.0f" % vm if vm < VELOCIDADES[-1] else "≥ %.0f" % vm)
            if vm < VELOCIDADES[-1]:
                vf = vm + 1.0
                ok, ch = barrido[(c, nom, vf)]
                fallas.append("%s a %.0f m/s: %d/%d, %d ch." % (t.lower(), vf, ok, n, ch))
        L.append("| C%d %s | %s | %s |" % (k, c, " | ".join(vs), "; ".join(fallas) or "—"))
    L += ["", "### Lectura", "",
          "- **A las velocidades del protocolo (hasta 4 m/s) ninguna degradación realista lo hace fallar.** No es "
          "casualidad: el riesgo se evalúa 10 veces por segundo durante los ~2 s que la persona está entre 8 m y el punto de "
          "frenado, así que perder el 30 % de los cuadros (recall 0.70) casi nunca deja sin detección más de 0.3 s; y el "
          "LiDAR toca el panel en decenas de lecturas seguidas, así que un 5 % sin retorno no cambia nada. Por eso los "
          "límites se buscan subiendo la velocidad y con las condiciones extremas.",
          "- **Panel:** el límite lo pone el alcance útil del LiDAR. Con la cámara a −5° desde 2.3 m el rayo toca el suelo a "
          "~26 m, y por encima de ~11 m/s la distancia de frenado más el margen no cabe en ese alcance. La latencia de "
          "300 ms lo baja a 10 m/s.",
          "- **Persona quieta:** el límite (4 m/s) lo pone la regla dura de los 8 m, no la percepción: aunque la vea desde "
          "lejos, el sistema no se activa antes de los 8 m, y por encima de 4 m/s no alcanza a detenerse a 2 m (sube y le "
          "pasa por encima, fuera de su alcance, sin chocar, pero no se detiene con margen). El viento de cola lo empeora "
          "(menos vuelos con margen a 5 m/s). Si el comité acepta activarse antes con una persona inmóvil al frente, "
          "este límite sube.",
          "- **Persona que corre hacia el dron:** lo que más pesa es la latencia (de 10 m/s con 100 ms a 7 m/s con 300 ms).",
          "- **Condiciones extremas (C11-C13), donde se rompe:** con recall 0.40 o latencia de 500 ms aparecen las primeras "
          "fallas con la persona que corre hacia el dron (velocidad segura 7 y 5 m/s). Con solo cabeza y hombros a la vista "
          "(15 % del alto) la detección llega tarde incluso a 1 m/s y aparecen choques (2 de 100 en el barrido; en la tabla "
          "de escenarios, con otras semillas, 0 de 100: el mismo orden de magnitud). Ese es el límite de la percepción: el "
          "sistema necesita ver al menos un tercio del cuerpo.",
          "- **Recomendación operativa:** limitar en ArduPilot la velocidad de avance del piloto (LOIT_SPEED) a la menor "
          "velocidad segura de la condición esperada; con personas en la zona, 4 m/s.", ""]
    return L


def _seccion_campo():
    return ["## Cómo se reproduce en campo", "",
            "El mismo protocolo, con el dron real, en un campo abierto y plano, sin público y con la geocerca de ArduPilot "
            "activa:", "",
            "1. **Panel (a):** un panel de 2 × 2.6 m (cartón pluma o lona sobre un marco) a 20 m del punto de partida. El "
            "piloto avanza en línea recta a 1, 2 y 3 m/s (velocidad limitada con LOIT_SPEED), 10 repeticiones por velocidad.",
            "2. **Persona quieta (b):** primero un maniquí o una silueta de 1.7 m en el lugar del panel. Una persona real solo "
            "después de que (a) y (b) con maniquí den 10 de 10, y siempre con la parada (CH8) en la mano del operador.",
            "3. **Persona que se acerca (c, e):** un voluntario camina hacia el dron, que vuela en estático a 2.3 m o "
            "avanza a 1 m/s; se empieza desde 15 m, 10 repeticiones. Correr hacia el dron solo con maniquí sobre un carro.",
            "4. **Persona que cruza lejos (d):** cruza a 12 m al frente, caminando y trotando, 10 repeticiones de cada una.",
            "5. **Condiciones:** repetir (a) y (b) con sol de frente y con viento de más de 3 m/s, si se dan.", "",
            "Qué se mide con el registro de la Jetson (una línea por cuadro con la marca de tiempo del reloj del sistema): "
            "detección de YOLO (caja, confianza, distancia estimada), lectura del LiDAR, decisión de riesgo y comando enviado "
            "por MAVLink; y del log de ArduPilot (DataFlash): velocidad, altura, actitud y canal CH8. Con eso se calculan "
            "las mismas métricas: éxito, activaciones verdaderas y falsas, latencia riesgo → comando (Jetson) y comando → "
            "frenado efectivo (DataFlash), distancia mínima (marcas en el suelo y video lateral, o RTK si se dispone) e "
            "intervenciones del operador (CH8). Con 10 repeticiones, 10 de 10 tiene un intervalo de confianza del 95 % de "
            "[72 %, 100 %]: el campo muestra que funciona y valida la latencia y la distancia de frenado; la tasa fina la "
            "da la simulación.", ""]


def _replay(replay):
    """Un vuelo de cada variante, seguidos, en el formato de la misión del visor (fase 1: piloto al mando)."""
    # el escenario del panel se corre DY_PANEL en y para que el panel no quede encima de las personas de los demás
    cuadros = []
    for nom, cs in replay:
        if ESCENARIOS[nom][4]:
            for c in cs:
                c["d"][1] = round(c["d"][1] + DY_PANEL, 3)
                c["lh"][1] = round(c["lh"][1] + DY_PANEL, 2)
        cuadros += cs
    datos = {"iteracion": 0, "pasos": 0, "adversaria": False, "mision": False, "guion": None, "resultado": "protocolo",
             "maniobras": 0, "dt": M.DT, "obst": [], "paneles": [[PANEL[0], PANEL[1] + DY_PANEL, PANEL[2], PANEL[3] + DY_PANEL, PANEL[4]]], "version": "Mínimo indispensable",
             "autor": "Brahian Andrés Orrego Osorio", "escenarios": [n for n, _ in replay],
             "inicio": list(np.cumsum([0] + [len(c) for _, c in replay[:-1]]).astype(int).tolist()), "cuadros": cuadros}
    os.makedirs(os.path.join(AQUI, "replay"), exist_ok=True)
    with open(os.path.join(AQUI, "replay", "replay_protocolo.json"), "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
