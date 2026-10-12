# -*- coding: utf-8 -*-
"""
Misión completa para el visor, en dos fases, dentro del mismo salón (alcances de la tesis):

FASE 1 · Piloto al mando, con bloqueo frontal (regla fija, no IA)
  El dron despega en un extremo y el piloto lo lleva en línea recta hacia la mitad del salón.
  Si el LiDAR ve un obstáculo de frente a menos de 3 m, o la cámara ve una persona de frente a
  menos de 6 m, el sistema ANULA el avance: aunque el piloto siga empujando la palanca hacia
  adelante, el dron no avanza. El piloto rodea el obstáculo por un lado (lo lateral es su
  responsabilidad) o espera a que la persona pase. Cada misión trae obstáculos distintos.

FASE 2 · IA activada a la mitad del salón
  El piloto suelta el control (interruptor en posición 3) y la política aprendida (entrenar.py)
  busca al ladrón, lo mantiene en la vista, esquiva a los peatones y lo esquiva a él si se le
  viene encima. Los obstáculos de la fase 1 siguen ahí y también los ve el LiDAR.
"""
import math

import numpy as np

from entorno import ARENA, DT, HFOV, N_PANELES, Z_NOMINAL, EntornoDronPersona, envolver

X_DESPEGUE = -21.0
ENTRADA_IA_X = 0.0               # mitad del salón: aquí el piloto activa la IA
VEL_PILOTO = 2.0
DIST_PROTECCION_LIDAR = 3.0
DIST_PROTECCION_CAMARA = 6.0
T_EMPUJE = 2.0                   # segundos que el piloto sigue empujando contra el bloqueo


def obstaculos_al_azar(rng, y0):
    """2 a 4 obstáculos entre el despegue y la mitad del salón; el primero siempre de frente."""
    obs = []
    xs = sorted(rng.uniform(-16, -4, int(rng.integers(2, 5))))
    for k, x in enumerate(xs):
        tipo = str(rng.choice(["muro", "caja", "columna", "rampa"], p=[0.35, 0.35, 0.15, 0.15])) if k else str(rng.choice(["muro", "caja"]))
        if tipo == "muro":
            largo = rng.uniform(5, 9)
            centro = y0 + rng.uniform(-largo / 2 + 0.8, largo / 2 - 0.8) if k == 0 else y0 + rng.uniform(-8, 8)
            obs.append([round(x, 2), round(centro, 2), 0.6, round(largo, 2), 2.8, "muro"])
        elif tipo == "caja":
            a, b = rng.uniform(1.6, 2.6, 2)
            centro = y0 + rng.uniform(-0.5, 0.5) if k == 0 else y0 + rng.uniform(-7, 7)
            alto = rng.uniform(2.6, 3.0) if k == 0 else rng.uniform(1.0, 2.6)
            obs.append([round(x, 2), round(centro, 2), round(a, 2), round(b, 2), round(alto, 2), "caja"])
        elif tipo == "columna":
            obs.append([round(x, 2), round(y0 + rng.uniform(-6, 6), 2), 0.9, 0.9, 3.4, "columna"])
        else:
            obs.append([round(x, 2), round(y0 + rng.uniform(-7, 7), 2), 2.4, 1.6, 1.1, "rampa"])
    return obs


def _rayo_caja(ox, oy, ux, uy, caja):
    cx, cy, sx, sy = caja[:4]
    x0, x1, y0, y1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2
    tmin, tmax = -1e9, 1e9
    for o, u, a, b in ((ox, ux, x0, x1), (oy, uy, y0, y1)):
        if abs(u) < 1e-9:
            if o < a or o > b:
                return None
        else:
            t1, t2 = (a - o) / u, (b - o) / u
            tmin, tmax = max(tmin, min(t1, t2)), min(tmax, max(t1, t2))
    return tmin if tmax >= max(tmin, 0) and tmin > 0 else None


def lidar_frontal(x, y, z, psi, obst, max_d=40.0):
    ux, uy = math.cos(psi), math.sin(psi)
    hits = [t for t in (_rayo_caja(x, y, ux, uy, c) for c in obst if c[4] > z - 0.3) if t is not None]
    return min(hits + [max_d])


def _libre(x, y, z, psi, obst, ancho=0.8):
    return min(lidar_frontal(x, y + o, z, psi, obst) for o in (-ancho, 0.0, ancho))


def _cuadro(d, dv, pers, msg, lid, est, piloto, bloq):
    p0 = pers[0] if pers else None
    return {"d": [round(d[0], 3), round(d[1], 3), round(d[2], 3), round(d[3], 4)], "dv": [round(dv[0], 2), round(dv[1], 2)],
            "pers": pers, "p": p0["p"] if p0 else [-90.0, -90.0], "pv": p0["v"] if p0 else [0.0, 0.0],
            "est": est, "cl": 0, "vis": bool(p0 and p0["vis"]), "las": False, "dm": 0.0, "dh": 0.0,
            "ang": 0.0, "vac": 0.0, "run": False, "cand": 0, "yaw": 0.0, "fase": 1, "msg": msg,
            "lid": None if lid is None else round(lid, 2), "dec": False, "pr": [],
            "piloto": [round(piloto[0], 2), round(piloto[1], 2)], "bloq": bloq}


def fase1(rng):
    """Piloto al mando con bloqueo frontal. Devuelve los cuadros, los obstáculos y la llegada."""
    y0 = float(rng.uniform(-8, 8))
    obst = obstaculos_al_azar(rng, y0)
    x, y, z, psi = X_DESPEGUE, y0, 0.0, 0.0
    vx = vy = 0.0
    con_peaton = rng.random() < 0.6
    x_peaton = float(rng.uniform(-12, -3))
    peaton = None
    cuadros = []
    estado, t_estado, lado = "despegue", 0.0, 0.0
    t = 0.0
    while t < 120.0:
        t += DT
        t_estado += DT
        lid = lidar_frontal(x, y, z, psi, obst)
        if con_peaton and peaton is None and x > x_peaton - 6.5:
            s = float(rng.choice([-1, 1]))
            peaton = [x_peaton, y + 3.2 * s, 0.0, -1.3 * s]
        ve_p, ang_p, d_p = False, 0.0, 99.0
        if peaton is not None:
            rx, ry = peaton[0] - x, peaton[1] - y
            d_p = math.hypot(rx, ry)
            ang_p = math.degrees(envolver(psi - math.atan2(ry, rx)))
            ve_p = abs(ang_p) < HFOV / 2 and d_p < 30
        persona_de_frente = ve_p and d_p < DIST_PROTECCION_CAMARA and abs(ang_p) < 12
        palanca = (0.0, 0.0)            # (adelante, derecha) que pide el piloto
        ovx = ovy = 0.0
        bloq = False
        if estado == "despegue":
            z = min(z + 0.7 * DT, Z_NOMINAL)
            msg = "Fase 1 · el piloto despega"
            if z >= Z_NOMINAL:
                estado, t_estado = "avance", 0.0
        elif estado == "avance":
            msg = "Fase 1 · el piloto lleva el dron hacia la mitad del salón"
            palanca = (1.0, 0.0)
            if lid < DIST_PROTECCION_LIDAR:
                estado, t_estado = "bloqueo", 0.0
            elif persona_de_frente:
                estado, t_estado = "bloqueo_persona", 0.0
            else:
                ovx = VEL_PILOTO
        elif estado == "bloqueo":
            palanca, bloq = (1.0, 0.0), True
            msg = "BLOQUEO FRONTAL · obstáculo a %.1f m: el piloto sigue empujando hacia adelante, pero el sistema no deja avanzar" % lid
            if t_estado > T_EMPUJE:
                desvio = {}
                for s in (-1.0, 1.0):
                    for k in range(1, 30):
                        if _libre(x, y + s * 0.5 * k, z, psi, obst) > 8.0:
                            desvio[s] = k
                            break
                    else:
                        desvio[s] = 99
                lado = -1.0 if desvio[-1.0] < desvio[1.0] else 1.0 if desvio[1.0] < desvio[-1.0] else float(rng.choice([-1.0, 1.0]))
                estado, t_estado = "desvio", 0.0
        elif estado == "desvio":
            msg = "Fase 1 · el piloto rodea el obstáculo por la %s" % ("derecha" if lado < 0 else "izquierda")
            palanca = (0.0, -lado)
            ovy = lado * 1.2
            if _libre(x, y, z, psi, obst) > 8.0:
                estado, t_estado = "avance", 0.0
        elif estado == "bloqueo_persona":
            palanca, bloq = (1.0, 0.0), True
            msg = "BLOQUEO FRONTAL · persona de frente a %.1f m: el sistema no deja avanzar hasta que pase" % d_p
            if not persona_de_frente and t_estado > 1.0:
                estado, t_estado = "avance", 0.0
        vx += (ovx - vx) * DT / 0.35
        vy += (ovy - vy) * DT / 0.35
        x += vx * DT
        y += vy * DT
        pers = []
        if peaton is not None:
            peaton[0] += peaton[2] * DT
            peaton[1] += peaton[3] * DT
            pers = [{"rol": "peaton", "p": [round(peaton[0], 3), round(peaton[1], 3)], "v": [peaton[2], peaton[3]],
                     "vis": ve_p, "tap": False, "run": False}]
        cuadros.append(_cuadro((x, y, z, psi), (vx, vy), pers, msg, lid if lid < 40 else None,
                               2 if bloq else 0, palanca, bloq))
        if x >= ENTRADA_IA_X:
            cuadros[-1]["msg"] = "Mitad del salón: el piloto activa la IA (interruptor en posición 3) y suelta el control"
            break
    return cuadros, obst, (x, y, z, psi)


def fase2(red_d, red_p, actuar, llegada, obst, semilla, segundos=40.0):
    """IA activada: el dron contra el ladrón, con peatones, paneles y los obstáculos del camino."""
    env = EntornoDronPersona(1, semilla=semilla)
    rng = np.random.default_rng(semilla + 99)
    x, y, z, psi = llegada
    env.dx[:], env.dy[:], env.dz[:], env.psi[:] = x, y, z, psi
    env.dvx[:] = env.dvy[:] = 0.0
    # paneles de la zona en la mitad derecha del salón
    for j in range(N_PANELES):
        c = np.array([rng.uniform(6, 18), rng.uniform(-15, 15)])
        if j and np.hypot(*(c - (env.pa[0, 0] + env.pb[0, 0]) / 2)) < 7:
            c[1] = -c[1]
        ang = rng.uniform(0, np.pi)
        u = np.array([np.cos(ang), np.sin(ang)]) * rng.uniform(4.5, 6.5) / 2
        env.pa[0, j], env.pb[0, j] = c - u, c + u
    env.agregar_cajas([tuple(o[:5]) for o in obst])
    # el ladrón está en algún lugar de la mitad derecha, casi nunca a la vista al llegar
    for _ in range(50):
        px, py = rng.uniform(6, ARENA - 2), rng.uniform(-ARENA + 2, ARENA - 2)
        if math.hypot(px - x, py - y) > 11:
            break
    env.px[0, 0], env.py[0, 0] = px, py
    for j in (1, 2):
        if env.activa[0, j]:
            env._preparar_peaton(0, j)
            env.px[0, j] = abs(env.px[0, j])
    env.obs_retraso[:] = 0.0
    env.vis_prev[:] = False
    env.t_sin_ver[:] = 0.0
    env.visto_alguna[:] = False
    env._sensores()
    env.obs_retraso[:] = 0.0
    paneles = env.paneles(0)
    cuadros, resultado, maniobras, vistos = [], "a salvo", 0, 0
    for _ in range(int(segundos / DT)):
        od, op = env.obs_dron(), env.obs_persona()
        ad, _, _, probs = actuar(red_d, od, codicioso=True)
        ap, _, _, _ = actuar(red_p, op, codicioso=False)
        f = env.foto(0)
        f.update({"fase": 2, "dec": bool(env.mascara_decision()[0]), "pr": [round(float(q), 3) for q in probs[0]],
                  "a": int(ad[0]), "msg": ""})
        cuadros.append(f)
        _, _, done, info = env.step(ad, ap, auto_reset=False)
        maniobras += int(info["inicia"][0])
        vistos += int(info["visto"][0])
        if done[0]:
            resultado = ("alcanzado" if info["choque_ladron"][0] else "choque_peaton" if info["choque_peaton"][0]
                         else "panel" if info["panel"][0] else "geocerca" if info["fuera"][0] else "a salvo")
            break
    return cuadros, paneles, resultado, maniobras, vistos / max(len(cuadros), 1)


def grabar_mision(red_d, red_p, actuar, iteracion, pasos_tot, semilla):
    rng = np.random.default_rng(semilla)
    c1, obst, llegada = fase1(rng)
    c2, paneles, resultado, maniobras, vista = fase2(red_d, red_p, actuar, llegada, obst, semilla)
    return {"iteracion": iteracion, "pasos": pasos_tot, "adversaria": True, "mision": True, "guion": None,
            "resultado": resultado, "maniobras": maniobras, "vista": round(vista, 3), "dt": DT,
            "obst": obst, "paneles": paneles, "despegue": [X_DESPEGUE, c1[0]["d"][1]], "entrada_ia_x": ENTRADA_IA_X,
            "cuadros": c1 + c2}


if __name__ == "__main__":
    for semilla in range(6):
        c, obst, llegada = fase1(np.random.default_rng(semilla))
        eventos = []
        for k, q in enumerate(c):
            m = q["msg"].split(" a ")[0].split(":")[0]
            if not eventos or m != eventos[-1][1]:
                eventos.append((round(k * DT, 1), m))
        print("misión %d · obstáculos %s" % (semilla, [o[5] for o in obst]))
        for e in eventos:
            print("   ", e)
