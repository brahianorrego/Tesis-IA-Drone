# -*- coding: utf-8 -*-
"""
Misión completa para el visor, en dos fases, dentro del mismo salón · versión 5.

TODOS LOS ACTORES EXISTEN DESDE EL PRIMER CUADRO (nadie aparece de la nada):
  · el ladrón está en la zona IA (robando: deambula) y se pone alerta cuando oye llegar al dron;
  · en la zona deambulan 0, 1 o 2 peatones;
  · en la ruta siempre hay un transeúnte que se cruza delante del dron (prueba de bloqueo obligatoria).

FASE 1 · Piloto al mando, con bloqueo frontal (regla fija, no IA)
  El dron despega en un extremo y el piloto lo lleva en línea recta hacia la mitad del salón.
  Si el LiDAR ve un obstáculo de frente a menos de 3 m, o la cámara ve una persona de frente a
  menos de 6 m, el sistema ANULA el avance: aunque el piloto siga empujando la palanca hacia
  adelante, el dron no avanza. El piloto rodea el obstáculo por un lado (lo lateral es su
  responsabilidad) o espera a que la persona pase. Cada misión trae obstáculos distintos.

FASE 2 · IA activada a la mitad del salón (ver entorno.py)
  BUSCAR (giro de 360° y, si no hay nadie, revisar detrás de cada panel) -> VERIFICAR (hover + alerta; el
  operador confirma con un clic sobre el sospechoso) -> FIJADO (la política aprendida rastrea a ese ID; yaw con
  banda muerta y gimbal para lo vertical). Si lo pierde: con PERDIDA_IA la política lo busca (BUSQUEDA_IA); si no,
  el protocolo determinista INVESTIGAR (flanqueo) -> ASOMO -> VENTAJA DE ALTURA.
"""
import math

import numpy as np

from entorno import (DT, GUIONES, L_DEAMBULAR, N_PANELES, PASOS_EPISODIO, T_BUSQUEDA_MAX, T_ESPERA_CLIC,
                     T_RASTREO, Z_NOMINAL, Z_TACTICO, Z_TRANSITO, EntornoDronPersona, dist_punto_segmento, resultado_de)

X_DESPEGUE = -21.0
ENTRADA_IA_X = 0.0               # mitad del salón: aquí el piloto activa la IA
VEL_PILOTO = 2.0
DIST_PROTECCION_LIDAR = 3.0
DIST_PROTECCION_CAMARA = 6.0
T_EMPUJE = 2.0                   # segundos que el piloto sigue empujando contra el bloqueo
ZONA = (3.0, 23.0, -22.0, 22.0)  # zona IA: mitad derecha del salón
RUTA = (-24.0, -3.0, -22.0, 22.0)  # por donde deambula el transeúnte después de cruzar
ESPERA_CARRIL = 1.6              # el transeúnte espera a esta distancia del carril hasta que llega el dron
ADELANTE_CRUCE = 6.0             # se mantiene unos metros por delante del dron, por la orilla


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


def _lejos_de_paneles(env, x, y, margen):
    for j in range(env.pa.shape[1]):
        d, _ = dist_punto_segmento(np.array([x, y]), env.pa[0, j], env.pb[0, j])
        if d < margen:
            return False
    return True


def _punto_libre(env, rng, lim, margen=1.5, evitar=()):
    for _ in range(80):
        x, y = rng.uniform(lim[0] + 1, lim[1] - 1), rng.uniform(lim[2] + 1, lim[3] - 1)
        if _lejos_de_paneles(env, x, y, margen) and all(math.hypot(x - a, y - b) > 3.0 for a, b in evitar):
            return x, y
    return x, y


def preparar(rng, semilla):
    """Crea el salón con TODOS sus actores ya en su lugar (y moviéndose desde el primer cuadro)."""
    y0 = float(rng.uniform(-8, 8))
    obst = obstaculos_al_azar(rng, y0)
    env = EntornoDronPersona(1, semilla=semilla)
    env.zona[0] = ZONA
    # paneles de la zona, en la mitad derecha del salón
    for j in range(N_PANELES):
        c = np.array([rng.uniform(6, 18), rng.uniform(-15, 15)])
        if j and np.hypot(*(c - (env.pa[0, 0] + env.pb[0, 0]) / 2)) < 7:
            c[1] = -c[1]
        ang = rng.uniform(0, np.pi)
        u = np.array([np.cos(ang), np.sin(ang)]) * rng.uniform(4.5, 6.5) / 2
        env.pa[0, j], env.pb[0, j] = c - u, c + u
    env.agregar_cajas([tuple(o[:5]) for o in obst])
    # el dron en el punto de despegue
    env.dx[:], env.dy[:], env.dz[:], env.psi[:] = X_DESPEGUE, y0, 0.0, 0.0
    env.dvx[:] = env.dvy[:] = env.dvz[:] = 0.0
    # ladrón: en la zona, robando (deambula) hasta que oye llegar al dron
    lx, ly = _punto_libre(env, rng, (8.0, ZONA[1], ZONA[2], ZONA[3]))
    env.px[0, 0], env.py[0, 0] = lx, ly
    env.tactico[:] = True
    env.l_modo[:] = L_DEAMBULAR
    env.l_alerta_t[:] = 1e9
    env.g_lim[0, 0] = ZONA
    env.g_wx[0, 0], env.g_wy[0, 0] = _punto_libre(env, rng, ZONA)
    # peatones de la zona: 0, 1 o 2, deambulando
    k = int(rng.choice([0, 1, 2], p=[0.3, 0.4, 0.3]))
    ocupados = [(lx, ly)]
    for j in (1, 2):
        env.activa[0, j] = j <= k
        if j <= k:
            env.guion[0, j] = GUIONES.index("deambular")
            env.g_lim[0, j] = ZONA
            env.px[0, j], env.py[0, j] = _punto_libre(env, rng, ZONA, evitar=ocupados)
            ocupados.append((env.px[0, j], env.py[0, j]))
            env.g_wx[0, j], env.g_wy[0, j] = _punto_libre(env, rng, ZONA)
            env.g_vel[0, j] = rng.uniform(0.8, 1.3)
        else:
            env.px[0, j] = env.py[0, j] = 999.0
    # transeúnte de la ruta: cruza el carril del dron en un hueco entre obstáculos
    huecos = [xc for xc in np.arange(-13.0, -2.4, 0.5)
              if all(abs(xc - o[0]) > o[2] / 2 + 2.0 for o in obst)]
    x_c = float(rng.choice(huecos)) if huecos else -2.5
    s = float(rng.choice([-1.0, 1.0]))
    env.activa[0, 3] = True
    env.guion[0, 3] = GUIONES.index("deambular")
    env.g_lim[0, 3] = RUTA
    env.g_vel[0, 3] = 1.2
    env.px[0, 3], env.py[0, 3] = x_c, y0 + s * rng.uniform(6.0, 9.0)
    env.pvx[:] = env.pvy[:] = 0.0
    env.reiniciar_mision(np.ones(1, bool))
    env.obs_retraso = env._sensores()
    return env, obst, y0, (x_c, s)


def _cuadro_fase1(env, msg, lid, piloto, bloq):
    f = env.foto(0)
    f.update({"fase": 1, "msg": msg, "lid": None if lid is None else round(lid, 2), "dec": False, "pr": [],
              "piloto": [round(piloto[0], 2), round(piloto[1], 2)], "bloq": bloq, "est": 2 if bloq else 0, "cl": 0,
              "vis": False, "las": False})
    return f


def fase1(env, rng, obst, y0, ruta):
    """Piloto al mando con bloqueo frontal. Las personas se mueven en el mismo entorno que usará la fase 2."""
    x_c, s = ruta
    x, y, z, psi = X_DESPEGUE, y0, 0.0, 0.0
    vx = vy = 0.0
    cuadros = []
    estado, t_estado, lado = "despegue", 0.0, 0.0
    etapa = 0                       # transeúnte: 0 camina por la orilla delante del dron, 1 cruza, 2 sigue su camino
    cruza_dir = -s
    t = 0.0
    while t < 120.0:
        t += DT
        t_estado += DT
        lid = float(env.lidar[0])           # LiDAR acoplado a la cámara (que en esta fase mira casi al frente)
        # ¿hay una persona de frente? (lo que ve la cámara del dron en el cuadro anterior)
        sen = env.info_sensor
        vis = sen["visible"][0] & env.activa[0]
        frente = vis & (sen["dist"][0] < DIST_PROTECCION_CAMARA) & (np.abs(sen["ang"][0]) < 12)
        persona_de_frente = bool(frente.any())
        d_p = float(sen["dist"][0][frente].min()) if persona_de_frente else 99.0
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
                for sd in (-1.0, 1.0):
                    for k in range(1, 30):
                        if _libre(x, y + sd * 0.5 * k, z, psi, obst) > 8.0:
                            desvio[sd] = k
                            break
                    else:
                        desvio[sd] = 99
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
        # el transeúnte camina por la orilla unos metros delante del dron y cruza el carril por delante en
        # un tramo libre (sin obstáculo entre ambos), así la prueba de bloqueo por persona siempre ocurre
        if etapa < 2:
            p3x, p3y = env.px[0, 3], env.py[0, 3]
            if etapa == 0:
                lado_p = 1.0 if p3y >= y else -1.0
                tx, ty = min(max(x_c, x + ADELANTE_CRUCE), 2.0), y + lado_p * ESPERA_CARRIL
                vec = np.array([tx - p3x, ty - p3y])
                dv = float(np.hypot(*vec))
                env.v_forzada[0, 3] = vec / max(dv, 1e-6) * min(1.5, 1.5 * dv)
                delante = p3x - x
                if (estado == "avance" and 3.5 < delante < 7.5 and lid > delante + 0.5 and abs(p3y - y) < 2.6
                        and t_estado > 0.5):
                    etapa, cruza_dir = 1, -lado_p
            if etapa == 1:
                env.v_forzada[0, 3] = (0.0, cruza_dir * 1.3)
                if (p3y - y) * cruza_dir > 6.0:
                    etapa = 2
                    env.v_forzada[0, 3] = np.nan
                    env.g_wx[0, 3] = p3x + rng.uniform(-4, 4)
                    env.g_wy[0, 3] = float(np.clip(p3y + cruza_dir * 8, RUTA[2] + 1, RUTA[3] - 1))
        env.dx[:], env.dy[:], env.dz[:], env.psi[:] = x, y, z, psi
        env.dvx[:], env.dvy[:] = vx, vy
        env.gimbal[:] = -3.0     # fase 1: la cámara, y con ella el LiDAR, mira casi al frente (protección frontal)
        env.mover_personas()
        cuadros.append(_cuadro_fase1(env, msg, lid if lid < 40 else None, palanca, bloq))
        if x >= ENTRADA_IA_X:
            cuadros[-1]["msg"] = "Mitad del salón: el piloto activa la IA (interruptor en posición 3) y suelta el control"
            break
    return cuadros, (x, y, z, psi, vx, vy)


def fase2(env, red_d, red_p, actuar, llegada, rng):
    """IA activada: BUSCAR -> VERIFICAR (operador) -> FIJADO, con los mismos actores que en la fase 1."""
    x, y, z, psi, vx, vy = llegada
    env.dx[:], env.dy[:], env.dz[:], env.psi[:] = x, y, z, psi
    env.dvx[:], env.dvy[:], env.dvz[:] = vx, vy, 0.0
    env.yaw_dps[:] = 0.0
    env.reiniciar_mision(np.ones(1, bool))
    if not np.isnan(env.v_forzada[0, 3, 0]):          # el transeúnte termina de cruzar y sigue su camino solo
        env.v_forzada[0, 3] = np.nan
        env.g_wx[0, 3], env.g_wy[0, 3] = _punto_libre(env, rng, RUTA)
    if env.l_alerta_t[0] > 100:               # todavía no lo ha notado: lo notará en unos segundos (o antes si el dron se acerca)
        env.l_alerta_t[0] = rng.uniform(3.0, 7.0)
    env.obs_retraso = env._sensores()
    env.phi = env._potencial()
    cuadros, resultado, maniobras, vistos = [], "tiempo", 0, 0
    for _ in range(PASOS_EPISODIO + 5):
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
            resultado = resultado_de(info, 0)
            f = env.foto(0)
            f.update({"fase": 2, "dec": False, "pr": cuadros[-1]["pr"], "a": cuadros[-1]["a"], "msg": ""})
            cuadros.append(f)
            break
    return cuadros, resultado, maniobras, vistos / max(len(cuadros), 1)


def grabar_mision(red_d, red_p, actuar, iteracion, pasos_tot, semilla):
    rng = np.random.default_rng(semilla)
    env, obst, y0, ruta = preparar(rng, semilla)
    paneles = env.paneles(0)
    c1, llegada = fase1(env, rng, obst, y0, ruta)
    c2, resultado, maniobras, vista = fase2(env, red_d, red_p, actuar, llegada, rng)
    return {"iteracion": iteracion, "pasos": pasos_tot, "adversaria": True, "mision": True, "guion": None,
            "resultado": resultado, "maniobras": maniobras, "vista": round(vista, 3), "dt": DT,
            "obst": obst, "paneles": paneles, "despegue": [X_DESPEGUE, y0], "entrada_ia_x": ENTRADA_IA_X,
            "t_rastreo": T_RASTREO, "t_busqueda": T_BUSQUEDA_MAX, "t_clic": T_ESPERA_CLIC,
            "z_transito": Z_TRANSITO, "z_alto": Z_TACTICO,
            "cuadros": c1 + c2}
