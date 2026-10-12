# -*- coding: utf-8 -*-
"""
Misión completa para el visor, en dos fases (alcances de la tesis):

FASE 1 · Vuelo del piloto con protección frontal (regla fija, no IA)
  El piloto despega y avanza en línea recta hacia la zona de búsqueda. Si el LiDAR ve un
  obstáculo de frente a menos de 3 m, o la cámara ve una persona de frente a menos de 6 m,
  el sistema le quita el avance al piloto y frena. Con un muro, el piloto se desplaza a un
  lado y sigue; con una persona, espera a que pase. Lo que está a los lados es
  responsabilidad del piloto (la tesis limita la protección al frente).

FASE 2 · IA activada en la zona
  La política aprendida (entrenar.py) toma el control: hace el paneo para buscar, mantiene a la
  persona en la vista y la esquiva si se le viene encima. La persona es el "ladrón" (IA adversaria).
"""
import math

import numpy as np

from entorno import (ALTURA_PERSONA, DT, HFOV, Z_NOMINAL, EntornoDronPersona, envolver)

DESPEGUE = (-42.0, 0.0)
ENTRADA_ZONA_X = -22.0           # al cruzar esta línea, el piloto activa la IA (interruptor en posición 3)
VEL_PILOTO = 2.0
DIST_PROTECCION_LIDAR = 3.0
DIST_PROTECCION_CAMARA = 6.0
# obstáculos del trayecto: (centro x, centro y, ancho x, ancho y, alto)
OBSTACULOS = [(-33.0, 1.0, 0.6, 9.0, 3.0), (-28.0, 7.0, 2.0, 2.0, 1.2), (-38.0, -7.0, 1.5, 1.5, 1.0)]


def _rayo_caja(ox, oy, ux, uy, caja):
    cx, cy, sx, sy, _ = caja
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


def lidar_frontal(x, y, psi, obst, max_d=40.0):
    ux, uy = math.cos(psi), math.sin(psi)
    hits = [t for t in (_rayo_caja(x, y, ux, uy, c) for c in obst) if t is not None]
    return min(hits + [max_d])


def _cuadro(d, p, pv, fase, msg, lid=None, vis=False, ang=0.0, dh=0.0, est=0, yaw=0.0):
    return {"d": [round(d[0], 3), round(d[1], 3), round(d[2], 3), round(d[3], 4)],
            "p": [round(p[0], 3), round(p[1], 3)], "pv": [round(pv[0], 2), round(pv[1], 2)],
            "est": est, "cl": 0, "vis": vis, "las": False, "dm": round(dh, 2), "dh": round(dh, 2),
            "ang": round(ang, 1), "vac": 0.0, "run": False, "cand": 0, "yaw": yaw,
            "fase": fase, "msg": msg, "lid": None if lid is None else round(lid, 2), "dec": False, "pr": []}


def fase1():
    """Vuelo del piloto con protección frontal. Devuelve los cuadros y el estado de llegada."""
    x, y, z, psi = DESPEGUE[0], DESPEGUE[1], 0.0, 0.0
    vx = vy = 0.0
    cuadros = []
    # peatón que cruzará el trayecto más adelante
    peaton = None
    estado, t_estado, lado = "despegue", 0.0, 0.0
    t = 0.0
    while t < 90.0:
        t += DT
        t_estado += DT
        lid = lidar_frontal(x, y, psi, OBSTACULOS)
        if peaton is None and x > -31.0:
            peaton = [-24.0, y + 3.0, 0.0, -1.3]
        # cámara: ¿una persona de frente y cerca?
        ve_persona, ang_p, d_p = False, 0.0, 99.0
        if peaton is not None:
            rx, ry = peaton[0] - x, peaton[1] - y
            d_p = math.hypot(rx, ry)
            ang_p = math.degrees(envolver(psi - math.atan2(ry, rx)))
            ve_persona = abs(ang_p) < HFOV / 2 and d_p < 30
        persona_de_frente = ve_persona and d_p < DIST_PROTECCION_CAMARA and abs(ang_p) < 12
        objetivo_vx = objetivo_vy = 0.0
        if estado == "despegue":
            z = min(z + 0.7 * DT, Z_NOMINAL)
            msg = "Fase 1 · el piloto despega"
            if z >= Z_NOMINAL:
                estado, t_estado = "avance", 0.0
        elif estado == "avance":
            msg = "Fase 1 · el piloto avanza en línea recta hacia la zona"
            if lid < DIST_PROTECCION_LIDAR:
                estado, t_estado = "freno_muro", 0.0
            elif persona_de_frente:
                estado, t_estado = "freno_persona", 0.0
            else:
                objetivo_vx = VEL_PILOTO
        elif estado == "freno_muro":
            msg = "Protección frontal · LiDAR: obstáculo a %.1f m, se frena el avance" % lid
            if t_estado > 1.5:
                # el piloto se desplaza hacia el lado con el camino libre
                libre_der = lidar_frontal(x, y - 6.0, psi, OBSTACULOS)
                libre_izq = lidar_frontal(x, y + 6.0, psi, OBSTACULOS)
                lado = -1.0 if libre_der >= libre_izq else 1.0
                estado, t_estado = "desvio", 0.0
        elif estado == "desvio":
            msg = "Fase 1 · el piloto se desplaza a la %s del obstáculo" % ("derecha" if lado < 0 else "izquierda")
            objetivo_vy = lado * 1.2
            libre = min(lidar_frontal(x, y + o, psi, OBSTACULOS) for o in (-0.8, 0.0, 0.8))
            if libre > 8.0:
                estado, t_estado = "avance", 0.0
        elif estado == "freno_persona":
            msg = "Protección frontal · cámara: persona de frente a %.1f m, se frena el avance" % d_p
            if not persona_de_frente and t_estado > 1.0:
                estado, t_estado = "avance", 0.0
        vx += (objetivo_vx - vx) * DT / 0.35
        vy += (objetivo_vy - vy) * DT / 0.35
        x += vx * DT
        y += vy * DT
        if peaton is not None:
            peaton[0] += peaton[2] * DT
            peaton[1] += peaton[3] * DT
        p = (peaton[0], peaton[1]) if peaton is not None else (-60.0, -60.0)
        pv = (peaton[2], peaton[3]) if peaton is not None else (0.0, 0.0)
        cuadros.append(_cuadro((x, y, z, psi), p, pv, 1, msg, lid=lid if lid < 40 else None,
                               vis=ve_persona, ang=ang_p, dh=d_p if peaton else 0.0,
                               est=0 if estado in ("avance", "despegue", "desvio") else 2))
        if x >= ENTRADA_ZONA_X:
            cuadros[-1]["msg"] = "Llega a la zona: el piloto activa la IA (interruptor en posición 3)"
            break
    return cuadros, (x, y, z, psi)


def fase2(red_d, red_p, actuar, llegada, semilla, segundos=30.0):
    """IA activada: la política del dron contra el 'ladrón' (persona adversaria)."""
    env = EntornoDronPersona(1, semilla=semilla, fraccion_adversaria=1.0)
    rng = np.random.default_rng(semilla)
    x, y, z, psi = llegada
    env.dx[:], env.dy[:], env.dz[:], env.psi[:] = x, y, z, psi
    env.dvx[:] = env.dvy[:] = 0.0
    # el ladrón está en algún lugar de la zona, casi nunca a la vista al llegar
    ang = rng.uniform(-math.pi, math.pi)
    d = rng.uniform(12, 20)
    env.px[:] = np.clip(x + 18 + d * math.cos(ang), -24, 24)
    env.py[:] = np.clip(y + d * math.sin(ang), -24, 24)
    env.obs_retraso[:] = 0.0
    env.vis_prev[:] = False
    env.t_sin_ver[:] = 0.0
    cuadros, resultado, maniobras, vistos = [], "tiempo", 0, 0
    for _ in range(int(segundos / DT)):
        od, op = env.obs_dron(), env.obs_persona()
        ad, _, _, probs = actuar(red_d, od, codicioso=True)
        ap, _, _, _ = actuar(red_p, op, codicioso=False)
        f = env.foto(0)
        f.update({"fase": 2, "dec": bool(env.mascara_decision()[0]), "pr": [round(float(q), 3) for q in probs[0]],
                  "a": int(ad[0]), "lid": None, "msg": ""})
        cuadros.append(f)
        _, _, done, info = env.step(ad, ap, auto_reset=False)
        maniobras += int(info["inicia"][0])
        vistos += int(env.info_sensor["visible"][0])
        if done[0]:
            resultado = "alcanzado" if info["choque"][0] else ("geocerca" if info["fuera"][0] else "a salvo")
            break
    if resultado == "tiempo":
        resultado = "a salvo"
    return cuadros, resultado, maniobras, vistos / max(len(cuadros), 1)


def grabar_mision(red_d, red_p, actuar, iteracion, pasos_tot, semilla):
    c1, llegada = fase1()
    c2, resultado, maniobras, vista = fase2(red_d, red_p, actuar, llegada, semilla)
    return {"iteracion": iteracion, "pasos": pasos_tot, "adversaria": True, "mision": True, "guion": None,
            "resultado": resultado, "maniobras": maniobras, "vista": round(vista, 3), "dt": DT,
            "obst": [list(c) for c in OBSTACULOS], "despegue": list(DESPEGUE), "entrada_zona_x": ENTRADA_ZONA_X,
            "cuadros": c1 + c2}


if __name__ == "__main__":
    c, llegada = fase1()
    eventos = []
    for k, q in enumerate(c):
        if not eventos or q["msg"] != eventos[-1][1]:
            eventos.append((round(k * DT, 1), q["msg"], q["d"][:2]))
    for e in eventos:
        print(e)
    print("llegada", [round(v, 2) for v in llegada], "duración %.1f s" % (len(c) * DT))
