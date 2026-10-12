# -*- coding: utf-8 -*-
"""
Repeticiones de PRUEBA para el visor V16 (sesión B), mientras la sesión A publica su contrato de foto().

No es una partida de la IA: es una coreografía escrita a mano con la geometría de la V16 (misión completa con 2
paneles, alturas variables, ladrón con posturas y salto, civiles con máquina de estados) para poder construir y revisar
el visor. Lleva los campos de siempre (los que lee el visor V15) y los campos nuevos del plan V16 (sección 3, fase A5):

  por persona:  pos   postura: 0 de pie, 1 agachado, 2 recostado de espalda contra la pared, 3 gateando
                pt    avance de la transición hacia `pos`, 0-1 (1 = postura completa)
                salto [fase, altura de la mano (m), avance de la fase 0-1]
                      fase: 0 nada, 1 impulso, 2 vuelo, 3 aterrizaje, 4 recuperación
                mira  hacia dónde mira (rad, mismo ángulo que psi del dron: 0 = +x, antihorario)
                civ   estado del civil: 0 transita, 1 mira el dron, 2 esquiva, 3 se va, 4 graba con el celular
                      (None en el ladrón)
  por cuadro:   alt_obj   altura objetivo del dron (m)
                cam_piso  detecciones de la cámara al piso: [{"id", "bb": [x0, y0, x1, y1] normalizados, "cf"}]
                bat       batería (%), propuesta del visor

Uso (desde simulacion/):  python herramientas/repeticion_prueba_v16.py
Salida: replays_prueba/demo_v16_mision.json (misión de ~70 s), demo_v16_salto.json (el ataque con salto, ~14 s) y\nlista.json (lo que muestra el selector del visor)
"""
import json
import math
import os

import numpy as np

DT = 0.1
T_FIN = 70.0
AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "..", "replays_prueba")

# --- geometría de la V16: 2 paneles de 2.6 m de alto ([x1, y1, x2, y2, alto])
PANELES = [[-4.0, 5.1, 1.5, 5.1, 2.6], [7.0, -5.0, 7.0, 0.0, 2.6]]
GIMBAL_MIN, GIMBAL_MAX = -45.0, 15.0          # regla dura 1
HFOV, VFOV = 38.9, 29.7                       # cámara principal (640 x 480)
PISO_HFOV, PISO_VFOV = 62.2, 48.8             # IMX219 recta hacia abajo
ALT_SEGURA = 3.30                             # D-043: con alguien a < 8 m
ALCANCE_DE_PIE = 1.33                         # alcance de la mano con el brazo arriba = 1.33 x estatura
ALTO_POSTURA = {0: 1.0, 1: 0.67, 2: 1.0, 3: 0.35}   # fracción de la estatura que queda a la vista

# --- coreografía del ladrón: (t, x, y, postura). Entre puntos se mueve en línea recta.
LADRON = [
    (0.0, -2.0, 1.0, 0), (8.0, -0.6, 1.8, 0), (10.0, -0.6, 1.8, 0),
    (12.2, -1.0, 5.6, 0),                                  # corre a esconderse detrás del panel 1
    (13.0, -1.0, 5.6, 1), (19.0, -3.2, 5.5, 1),            # agachado, camina agachado hacia el oeste
    (19.8, -3.2, 5.5, 3), (27.0, 0.8, 5.5, 3),             # se tira al piso y gatea hacia el este
    (27.8, 0.8, 5.55, 0), (29.0, 5.5, 1.5, 0), (29.6, 7.6, 0.6, 0), (30.3, 7.42, -2.0, 0),   # corre al panel 2
    (31.1, 7.42, -2.0, 2), (40.2, 7.42, -2.0, 2),          # recostado de espalda contra la cara este, se asoma
    (40.8, 7.6, -1.6, 0), (42.35, 10.55, 2.85, 0),         # sale y carga contra el dron
    (43.15, 11.2, 3.6, 0), (44.3, 11.5, 3.9, 0),           # salto (vuelo) y aterrizaje
    (47.0, 13.5, 7.5, 0), (53.0, 17.0, 13.5, 0), (59.0, 18.3, 15.8, 0), (T_FIN, 18.3, 15.8, 0),
]
SALTO = {"impulso": (42.05, 42.35), "vuelo": (42.35, 43.0), "aterrizaje": (43.0, 43.3), "recuperacion": (43.3, 44.2),
         "salto_alto": 0.62}
T_RINDE = 61.0

# --- civiles: puntos (t, x, y, estado civ). Antes del primer punto o después del último no están en la zona.
CIVILES = [
    {"id": 7, "est": 1.66, "pts": [(3.0, -24.0, 13.0, 0), (14.0, -10.0, 13.5, 0), (15.2, -9.6, 13.6, 1), (24.0, -9.6, 13.6, 4),
                                   (32.0, -9.6, 13.6, 4), (33.5, -10.2, 14.3, 3), (46.0, -21.0, 24.0, 3), (50.0, -24.5, 27.5, 3)]},
    {"id": 12, "est": 1.79, "pts": [(14.0, 19.0, -24.0, 0), (34.0, 16.0, -2.5, 0), (35.5, 15.8, -1.2, 1), (40.6, 15.8, -1.2, 1),
                                    (41.6, 17.6, -0.6, 2), (43.4, 18.4, -0.2, 2), (44.0, 18.4, -0.2, 1), (48.0, 18.4, -0.2, 1),
                                    (58.0, 22.0, -9.0, 3), (63.0, 26.5, -13.0, 3)]},
]

# --- dron: puntos objetivo (t, x, y) y altura por tramo; el filtro de 2.º orden los suaviza
DRON = [(0.0, -16.0, -14.0), (6.0, -13.0, -11.0), (9.0, -8.0, -6.5), (12.0, -4.0, -2.5), (15.0, -6.8, 2.0),
        (18.0, -7.3, 6.2), (21.0, -6.0, 8.8), (24.0, -3.2, 9.4), (27.0, -1.0, 9.6), (29.0, 2.0, 7.5), (31.0, 4.5, 5.0),
        (33.0, 6.0, 5.2), (35.0, 7.0, 6.4), (37.0, 8.1, 6.0), (40.5, 9.6, 1.8), (42.0, 10.6, 2.9), (43.0, 11.4, 3.7),
        (44.5, 12.0, 4.3)]
T_SEGUIR = 45.0                               # desde aquí lo sigue a 4.5 m
ALT_TRAMOS = [(0.0, 2.0), (2.5, 2.5), (5.0, 3.0), (6.5, 3.0)]   # sin nadie cerca: 2.0 -> 2.5 -> 3.0 (decisión 3)
T_GIRO_360 = (1.0, 5.0)                       # 360° de entrada


def interp(pts, t, k0=1):
    """Interpolación lineal de una lista de tuplas (t, ...) en el instante t."""
    if t <= pts[0][0]:
        return pts[0][k0:]
    for a, b in zip(pts, pts[1:]):
        if a[0] <= t <= b[0]:
            f = (t - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 1.0
            return tuple(a[k] + (b[k] - a[k]) * f for k in range(k0, len(a)))
    return pts[-1][k0:]


def tramo(pts, t):
    """El punto de partida del tramo en el que cae t (para los valores discretos: postura, estado del civil)."""
    ult = pts[0]
    for p in pts:
        if p[0] <= t + 1e-9:
            ult = p
    return ult


def suavizar(arr, n):
    if n <= 1:
        return arr
    k = np.ones(n) / n
    pad = np.pad(arr, ((n // 2, n - 1 - n // 2), (0, 0)), mode="edge")
    return np.stack([np.convolve(pad[:, j], k, mode="valid") for j in range(arr.shape[1])], 1)


def ang_dif(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def bloqueado(c, p):
    """¿Algún panel tapa la línea de la cámara c=(x,y,z) al punto p=(x,y,z)?"""
    for x1, y1, x2, y2, h in PANELES:
        dx, dy = p[0] - c[0], p[1] - c[1]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-9:
            continue
        s = ((x1 - c[0]) * ey - (y1 - c[1]) * ex) / den        # a lo largo del rayo
        u = ((x1 - c[0]) * dy - (y1 - c[1]) * dx) / den        # a lo largo del panel
        if 0 < s < 1 and 0 <= u <= 1 and c[2] + (p[2] - c[2]) * s < h:
            return True
    return False


def fraccion_visible(cam, yaw, pitch, x, y, alto):
    """Fracción del cuerpo (12 muestras a lo alto) dentro de la imagen y sin tapar, como el entorno (V13)."""
    ok = 0
    for k in range(12):
        z = alto * (k + 0.5) / 12
        dx, dy, dz = x - cam[0], y - cam[1], z - cam[2]
        h = math.hypot(dx, dy)
        az = math.degrees(ang_dif(math.atan2(dy, dx), yaw))
        el = math.degrees(math.atan2(dz, h)) - pitch
        if abs(az) < HFOV / 2 and abs(el) < VFOV / 2 and h < 30 and not bloqueado(cam, (x, y, z)):
            ok += 1
    return ok / 12


def caja_piso(dron, psi, x, y, alto):
    """Caja normalizada de una persona en la cámara al piso (recta hacia abajo, fija al chasis), o None."""
    th, tv = math.tan(math.radians(PISO_HFOV / 2)), math.tan(math.radians(PISO_VFOV / 2))
    us, vs = [], []
    for z in (0.0, alto):
        h = dron[2] - 0.15 - z
        if h <= 0.2:
            return None
        dx, dy = x - dron[0], y - dron[1]
        adel = dx * math.cos(psi) + dy * math.sin(psi)          # hacia la nariz = arriba en la imagen
        der = dx * math.sin(psi) - dy * math.cos(psi)
        for r in (-0.25, 0.25):
            us.append(0.5 + (der + r) / h / th / 2)
            vs.append(0.5 - (adel + r) / h / tv / 2)
    x0, x1, y0, y1 = min(us), max(us), min(vs), max(vs)
    if x1 < 0 or x0 > 1 or y1 < 0 or y0 > 1:
        return None
    return [round(max(x0, 0), 3), round(max(y0, 0), 3), round(min(x1, 1), 3), round(min(y1, 1), 3)]


def generar():
    T = np.arange(0.0, T_FIN + 1e-9, DT)
    n = len(T)
    est_l = 1.71

    # ---------------- ladrón
    lp = np.array([interp(LADRON, t)[:2] for t in T])
    lp = suavizar(lp, 3)
    lv = np.gradient(lp, DT, axis=0)
    l_pos = [int(tramo(LADRON, t)[3]) for t in T]
    # avance de la transición: 0.8 s desde que cambia la postura
    l_pt, t_cambio = [], 0.0
    for k, t in enumerate(T):
        if k and l_pos[k] != l_pos[k - 1]:
            t_cambio = t
        l_pt.append(round(min(1.0, (t - t_cambio) / 0.8), 2) if k else 1.0)

    # ---------------- dron: objetivo, filtro de 2.º orden, altura con rampa
    d = np.zeros((n, 3))
    v = np.zeros(3)
    pos = np.array([DRON[0][1], DRON[0][2], 2.0])
    psi, gmb = math.radians(45.0), -10.0
    psis, gmbs, vis_l, fv_l, alt_objs, piso_l = [], [], [], [], [], []
    w = 1.5
    for k, t in enumerate(T):
        if t < T_SEGUIR:
            obj = np.array(interp(DRON, t))
        else:
            dl = lp[k] - pos[:2]
            dist = max(np.linalg.norm(dl), 1e-6)
            obj = lp[k] - dl / dist * 4.5
        civs = [civ_xy(c_, t) for c_ in CIVILES]
        cerca = np.hypot(*(lp[k] - pos[:2])) < 8.0 or any(
            c is not None and math.hypot(c[0] - pos[0], c[1] - pos[1]) < 8.0 for c in civs)
        a_obj = ALT_SEGURA if (cerca or t >= 8.0) else interp(ALT_TRAMOS, t)[0]
        if 41.4 <= t <= 44.6:
            a_obj = 3.8                                         # el árbitro sube ante el ataque
        acc = w * w * (obj - pos[:2]) - 2 * w * v[:2]
        acc = np.clip(acc, -3.0, 3.0)
        v[:2] += acc * DT
        sp = np.linalg.norm(v[:2])
        if sp > 5.0:
            v[:2] *= 5.0 / sp
        pos[:2] += v[:2] * DT
        vz = np.clip((a_obj - pos[2]) * 1.2, -0.6, 1.0)          # rampa: sin escalones
        pos[2] += vz * DT
        v[2] = vz
        d[k] = pos
        alt_objs.append(a_obj)
        # rumbo: giro de 360° de entrada; luego hacia el ladrón (o su última posición conocida)
        if T_GIRO_360[0] <= t < T_GIRO_360[1]:
            psi += math.radians(90.0) * DT
        else:
            if 34.0 <= t < 37.0:
                deseado = math.atan2(-2.0 - pos[1], 7.2 - pos[0])     # muro de canto: mira a lo largo del panel
            else:
                deseado = math.atan2(lp[k][1] - pos[1], lp[k][0] - pos[0])
            psi += float(np.clip(ang_dif(deseado, psi), -math.radians(9.0), math.radians(9.0)))
        psi = (psi + math.pi) % (2 * math.pi) - math.pi
        alto_l = est_l * ALTO_POSTURA[l_pos[k]] if l_pt[k] >= 1 else est_l * 0.8
        h = math.hypot(lp[k][0] - pos[0], lp[k][1] - pos[1])
        g_des = math.degrees(math.atan2(alto_l * 0.55 - (pos[2] - 0.12), h))
        g_des = min(max(g_des, GIMBAL_MIN), GIMBAL_MAX)
        gmb += float(np.clip(g_des - gmb, -6.0, 6.0))
        gmb = min(max(gmb, GIMBAL_MIN), GIMBAL_MAX)
        psis.append(psi)
        gmbs.append(gmb)
        fv = fraccion_visible((pos[0], pos[1], pos[2] - 0.12), psi, gmb, lp[k][0], lp[k][1], alto_l)
        fv_l.append(fv)
        vis_l.append(fv >= 0.15)
        piso_l.append(caja_piso(pos, psi, lp[k][0], lp[k][1], alto_l) is not None)
    dv = np.gradient(d, DT, axis=0)
    acc = np.gradient(dv, DT, axis=0)

    # ---------------- modos del dron (máquina de estados de la V15) a partir de lo que ve
    cuadros = []
    custodia, visto_antes, t_perdido, t_cont, t_rid = 0.0, False, None, 0.0, -9.0
    for k, t in enumerate(T):
        vis = vis_l[k]
        visto = vis or piso_l[k]                                 # la cámara al piso cubre el punto ciego bajo el dron
        confirmado = t >= 9.0
        if t < 6.0:
            modo = 0
        elif not confirmado:
            modo = 1
        elif visto:
            modo = 2
        else:
            if t_perdido is None:
                t_perdido = t
            tp = t - t_perdido
            modo = 10 if 34.0 <= t < 37.5 else (6 if tp < 2.0 else 3)
        if visto and t_perdido is not None and confirmado:
            t_perdido, t_rid = None, t
        if confirmado and visto:
            custodia += DT
            t_cont += DT
        elif confirmado:
            t_cont = 0.0
        trk = (0 if t < 6.0 else 5) if not confirmado else (4 if visto and t - t_rid < 0.6 else 1 if visto else 3)
        rinde = t >= T_RINDE
        psi = psis[k]
        # chasis: cabeceo y alabeo por la aceleración (convención del entorno: grados)
        a_adel = acc[k, 0] * math.cos(psi) + acc[k, 1] * math.sin(psi)
        a_der = acc[k, 0] * math.sin(psi) - acc[k, 1] * math.cos(psi)
        cp = round(-math.degrees(math.atan2(a_adel, 9.81)), 1)
        cr = round(math.degrees(math.atan2(a_der, 9.81)), 1)

        # ---- salto
        fase, avance = 0, 0.0
        for nf, (nombre, (t0, t1)) in enumerate([(q, SALTO[q]) for q in ("impulso", "vuelo", "aterrizaje", "recuperacion")]):
            if t0 <= t < t1:
                fase, avance = nf + 1, (t - t0) / (t1 - t0)
        h_mano = est_l * ALCANCE_DE_PIE
        if fase == 1:
            h_mano = est_l * (1.18 - 0.25 * math.sin(math.pi * min(avance * 1.3, 1)))     # se agacha y lleva el brazo atrás
        elif fase == 2:
            h_mano = est_l * ALCANCE_DE_PIE + SALTO["salto_alto"] * 4 * avance * (1 - avance) + 0.05 * (1 - avance)
        elif fase == 3:
            h_mano = est_l * (1.2 - 0.2 * math.sin(math.pi * avance))
        salto = [fase, round(h_mano, 2), round(avance, 2)]

        ladron_mira = math.atan2(lv[k][1], lv[k][0]) if np.hypot(*lv[k]) > 0.3 else None
        if l_pos[k] == 2:
            ladron_mira = 0.0                                    # espalda contra la cara este del panel 2
        if ladron_mira is None or rinde:
            ladron_mira = math.atan2(d[k][1] - lp[k][1], d[k][0] - lp[k][0])
        v_l = float(np.hypot(*lv[k]))
        pers = [{
            "rol": "ladron", "p": [round(float(lp[k][0]), 3), round(float(lp[k][1]), 3)],
            "v": [round(float(lv[k][0]), 2), round(float(lv[k][1]), 2)], "vis": bool(vis), "tap": bool(not vis and fv_l[k] == 0),
            "id": 3, "sz": round(max(0.0, h_mano - est_l * ALCANCE_DE_PIE), 2) if fase == 2 else 0.0, "fv": round(fv_l[k], 2),
            "est": est_l, "res": round(max(0.0, 1 - t / 60), 3), "hr": round(95 + 70 * min(1, v_l / 5) + 20 * (fase > 0)),
            "ign": False, "cand": bool(6.0 <= t < 9.0), "run": bool(v_l > 2.5),
            "pos": l_pos[k], "pt": l_pt[k], "salto": salto, "mira": round(ladron_mira, 3), "civ": None,
            "rinde": bool(rinde)}]
        for c_ in CIVILES:
            xy = civ_xy(c_, t)
            if xy is None:
                continue
            xy2 = civ_xy(c_, t + DT) or xy
            vx, vy = (xy2[0] - xy[0]) / DT, (xy2[1] - xy[1]) / DT
            ec = int(tramo(c_["pts"], t)[3])
            if ec in (1, 4) or math.hypot(vx, vy) < 0.2:
                mira = math.atan2(d[k][1] - xy[1], d[k][0] - xy[0])
            else:
                mira = math.atan2(vy, vx)
            fvc = fraccion_visible((d[k][0], d[k][1], d[k][2] - 0.12), psis[k], gmbs[k], xy[0], xy[1], c_["est"])
            pers.append({"rol": "peaton", "p": [round(xy[0], 3), round(xy[1], 3)], "v": [round(vx, 2), round(vy, 2)],
                         "vis": bool(fvc >= 0.15), "tap": False, "id": c_["id"], "sz": 0.0, "fv": round(fvc, 2), "est": c_["est"],
                         "res": None, "hr": None, "ign": False, "cand": False, "run": bool(math.hypot(vx, vy) > 2.2),
                         "pos": 0, "pt": 1.0, "salto": [0, round(c_["est"] * ALCANCE_DE_PIE, 2), 0.0], "mira": round(mira, 3),
                         "civ": ec})

        # ---- cámara al piso
        piso = []
        for p_ in pers:
            alto = p_["est"] * ALTO_POSTURA[p_["pos"]]
            bb = caja_piso(d[k], psi, p_["p"][0], p_["p"][1], alto)
            if bb:
                piso.append({"id": p_["id"], "bb": bb, "cf": round(0.55 + 0.3 * (bb[2] - bb[0] > 0.12), 2)})

        dist = math.hypot(lp[k][0] - d[k][0], lp[k][1] - d[k][1])
        amz = bool(40.9 <= t <= 44.6)
        evade = bool(41.4 <= t <= 44.6)
        eb = ["BUSCAR", "VERIFICAR", "PERSECUCION", "FLANQUEO_PROFUNDO", "GIRO_360", "ALTURA_TACTICA", "PERDIDA",
              "BUSQUEDA_IA", "SIGUIENTE_OBSTACULO", "RECONFIRMAR", "MURO_DE_CANTO"][modo]
        cuadros.append({
            "fase": 2, "d": [round(float(d[k][0]), 3), round(float(d[k][1]), 3), round(float(d[k][2]), 3), round(psi, 4)],
            "dv": [round(float(dv[k][0]), 2), round(float(dv[k][1]), 2)], "pers": pers,
            "p": pers[0]["p"], "pv": pers[0]["v"], "run": pers[0]["run"],
            "est": 1 if evade else 0, "cl": 3 if evade else 0, "vis": bool(vis and confirmado), "las": bool(vis and confirmado),
            "dm": round(dist, 2) if vis else 99.0, "dh": round(dist, 2), "ang": 0.0, "vac": 0.0,
            "yaw": round(math.degrees(ang_dif(psis[k], psis[k - 1])) / DT, 1) if k else 0.0, "lid": 30.0, "modo": modo,
            "trk": trk, "amz": amz, "per": False, "rfx": bool(41.4 <= t <= 43.6), "gd": False, "ciego": False,
            "gmb": round(gmbs[k], 1), "cp": cp, "cr": cr, "eg": 0.0, "op": 1 if abs(t - 9.0) < DT / 2 else 0,
            "t2": round(t, 1), "tf": round(custodia, 1), "tc": round(t_cont, 1), "trd": 30.0, "rinde": bool(rinde),
            "tsv": round(t - t_perdido, 1) if t_perdido is not None else 0.0, "eb": eb, "conf": 0.93 if vis else 0.0,
            "ux": round(float(lp[k][0]), 2), "uy": round(float(lp[k][1]), 2), "wx": 0.0, "wy": 0.0, "nube": [], "det": [],
            # ---- contrato V16
            "alt_obj": round(alt_objs[k], 2), "cam_piso": piso, "bat": round(100 - 100 * t / 900, 1),
        })
    return cuadros


def civ_xy(c_, t):
    pts = c_["pts"]
    if t < pts[0][0] or t > pts[-1][0]:
        return None
    x, y, _ = interp(pts, t)
    return (x, y)


def guardar(nombre, cuadros, extra):
    os.makedirs(SALIDA, exist_ok=True)
    out = {"iteracion": 0, "pasos": 0, "adversaria": True, "mision": False, "guion": None, "resultado": "cumplida",
           "maniobras": 1, "dt": DT, "obst": [], "paneles": PANELES, "version": "V16 · repetición de prueba del visor",
           "autor": "Brahian Andrés Orrego Osorio", "prueba": True,
           "nota": "Coreografía escrita a mano (herramientas/repeticion_prueba_v16.py) para construir el visor: "
                   "no es una partida de la IA.", "t_mision_perdida": 90, "cuadros": cuadros}
    out.update(extra)
    ruta = os.path.join(SALIDA, nombre)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("  %s: %d cuadros, %.0f KB" % (nombre, len(cuadros), os.path.getsize(ruta) / 1024))


def main():
    cuadros = generar()
    print("Repeticiones de prueba en", os.path.normpath(SALIDA))
    guardar("demo_v16_mision.json", cuadros, {"titulo": "Misión de prueba · 2 paneles, posturas y salto"})
    k0, k1 = int(37.0 / DT), int(51.0 / DT)
    guardar("demo_v16_salto.json", cuadros[k0:k1], {"titulo": "Prueba · el ladrón salta para agarrar el dron",
                                                     "resultado": "salto"})
    lista = [{"archivo": "demo_v16_mision.json", "titulo": "Misión de prueba · 2 paneles, posturas y salto (70 s)"},
             {"archivo": "demo_v16_salto.json", "titulo": "Prueba · el ladrón salta para agarrar el dron (14 s)"}]
    with open(os.path.join(SALIDA, "lista.json"), "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
