# -*- coding: utf-8 -*-
"""
Evaluación de una política del dron en ESCENARIOS FIJOS (mismas semillas y mismas trayectorias del ladrón para todos
los modelos), para comparar checkpoints entre sí sin el ruido de las partidas aleatorias del entrenamiento.

Cada partida arranca con el ladrón YA FIJADO (el operador ya hizo clic), a ~5 m delante del dron, así que lo que se
mide es solo lo que decide la política. El ladrón sigue una trayectoria impuesta (v_forzada, el mismo mecanismo de la
misión) con la cinemática humana del entorno; cada semilla cambia un poco su punto de partida y su rapidez, el ruido
de los sensores, el viento y la planta del dron. Sin peatones.

Escenarios:
  abierto        persecución en campo abierto (sin paneles): huye en línea recta y dobla dos veces
  cambio_brusco  corre, da media vuelta de golpe pasando junto al dron y luego gira 90°
  tras_muro      corre a esconderse detrás de un panel de 2.6 m y se queda ahí
  debajo         corre hasta quedar debajo del dron y lo sigue caminando (punto ciego de la cámara; el ladrón
                 aprendido salta si el dron está a menos de 2.9 m de altura)

Política determinista (la acción más probable). Partidas de hasta --max-seg segundos.

Uso (desde simulacion\\):
  .venv\\Scripts\\python.exe herramientas\\evaluar_politica.py --modelo modelos_master\\checkpoints\\dron_master_350639616_steps.zip
  .venv\\Scripts\\python.exe herramientas\\evaluar_politica.py --barrido 25 --version v10-master
      (base_v9 + un checkpoint cada 25 M pasos + el último; tabla de evolución en informes\\)
"""
import argparse
import csv
import glob
import os
import re
import sys
import time

import numpy as np

SIM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SIM)

import entorno as E  # noqa: E402

INFORMES = os.path.join(SIM, "informes")
CHECKPOINTS = os.path.join(SIM, "modelos_master", "checkpoints")
BASE = os.path.join(SIM, "modelos_master", "base_v9.zip")
LEJOS = np.array([[40.0, 40.0], [41.0, 40.0]])          # un panel "retirado" queda fuera de la arena

# Trayectorias del ladrón: (x, y, rapidez). "D" = la posición actual del dron (perseguirlo).
# dron: (x, y, rumbo en grados); ladrón: (x, y) de partida; paneles: lista de (ax, ay, bx, by)
CORRE = E.VEL_CORRER
ESCENARIOS = {
    "abierto": dict(dron=(-18.0, -12.0, 0.0), ladron=(-13.0, -12.0), paneles=[],
                    ruta=[(15.0, -12.0, CORRE), (15.0, 10.0, CORRE), (-10.0, 10.0, 2.5)]),
    "cambio_brusco": dict(dron=(-15.0, 0.0, 0.0), ladron=(-10.0, 0.0), paneles=[],
                          ruta=[(2.0, 0.0, CORRE), (-6.0, -3.0, CORRE), (-6.0, 10.0, CORRE), (6.0, 10.0, 2.0)]),
    "tras_muro": dict(dron=(-15.0, 0.0, 0.0), ladron=(-10.0, 1.0), paneles=[(0.0, -3.0, 0.0, 3.0)],
                      ruta=[(-1.0, 4.5, CORRE), (1.5, 1.0, 2.0)]),
    "debajo": dict(dron=(0.0, 0.0, 0.0), ladron=(6.0, 0.0), paneles=[],
                   ruta=[("D", 6.0, CORRE), ("D", 15.0, E.VEL_CAMINAR)]),
}
RESULTADOS = ["cumplida", "perdido", "alcanzado", "choque_peaton", "panel", "geocerca", "no_encontrado", "tiempo"]


def preparar(env, esc, rng):
    """Deja las n partidas del entorno en el estado inicial del escenario, con el ladrón ya fijado."""
    n = env.n
    todos = np.ones(n, bool)
    dx, dy, rumbo = esc["dron"]
    env.dx[:] = dx + rng.uniform(-0.5, 0.5, n)
    env.dy[:] = dy + rng.uniform(-0.5, 0.5, n)
    env.dz[:] = E.Z_NOMINAL
    env.dvx[:] = env.dvy[:] = env.dvz[:] = 0.0
    env.psi[:] = np.radians(rumbo)
    env.ap.sincronizar(env, todos)
    # paneles
    env.pa[:] = LEJOS[0]
    env.pb[:] = LEJOS[1]
    env.ph[:] = E.ALTO_PANEL
    for j, (ax, ay, bx, by) in enumerate(esc["paneles"]):
        env.pa[:, j] = (ax, ay)
        env.pb[:, j] = (bx, by)
    # personas: solo el ladrón (aprendido = sin cerebro táctico; su movimiento lo impone la ruta)
    env.activa[:] = False
    env.activa[:, 0] = True
    env.px[:, 1:] = env.py[:, 1:] = 999.0
    lx, ly = esc["ladron"]
    env.px[:, 0] = lx + rng.uniform(-1.0, 1.0, n)
    env.py[:, 0] = ly + rng.uniform(-1.0, 1.0, n)
    env.pvx[:] = env.pvy[:] = 0.0
    env.p_rumbo[:, 0] = env.psi
    env.tactico[:] = False
    env.salto_t[:] = env.salto_cd[:] = env.salto_h[:] = 0.0
    env.v_forzada[:] = np.nan
    # misión: ya en FIJADO (el operador confirmó), cámara apuntando al ladrón
    env.reiniciar_mision(todos)
    env.modo[:] = E.FIJADO
    env.visto_alguna[:] = True
    rx, ry = env.px[:, 0] - env.dx, env.py[:, 0] - env.dy
    env.ult_x[:], env.ult_y[:] = env.px[:, 0], env.py[:, 0]
    env.ult_rumbo[:] = np.arctan2(ry, rx)
    env.ult_dist[:] = np.hypot(rx, ry)
    ang = -np.degrees(np.arctan2(E.Z_NOMINAL - 0.9, np.hypot(rx, ry)))
    env.gimbal[:] = env.gimbal_cmd[:] = env.cam_pitch[:] = ang
    env.gb.reset(todos, 0.0)
    env.gb.ang[:] = env.gb.sp[:] = ang
    env.u_prev[:] = 0.0
    env.mando_prev[:] = False
    env.lid_ok[:] = False
    env.lid_i[:] = 0
    env.det_n[:] = 0
    env.vis_prev[:] = False
    env._sensores()
    env.obs_retraso = env._sensores()
    env.phi = env._potencial()


def velocidad_ladron(env, ruta, wp, t_wp, k_vel):
    """Velocidad impuesta al ladrón según su punto de ruta actual (avanza de punto al llegar)."""
    n = env.n
    vx, vy = np.zeros(n), np.zeros(n)
    for i in range(n):
        while wp[i] < len(ruta):
            a, b, v = ruta[wp[i]]
            if a == "D":                                   # perseguir al dron durante b segundos
                tx, ty = env.dx[i], env.dy[i]
                if t_wp[i] >= b:
                    wp[i] += 1
                    t_wp[i] = 0.0
                    continue
            else:
                tx, ty = a, b
                if np.hypot(tx - env.px[i, 0], ty - env.py[i, 0]) < 0.5:
                    wp[i] += 1
                    t_wp[i] = 0.0
                    continue
            d = np.hypot(tx - env.px[i, 0], ty - env.py[i, 0])
            s = min(v * k_vel[i], d / E.DT) if a == "D" else v * k_vel[i]
            if d > 1e-6:
                vx[i], vy[i] = s * (tx - env.px[i, 0]) / d, s * (ty - env.py[i, 0]) / d
            break
        t_wp[i] += E.DT
    return vx, vy


def correr_escenario(modelo, nombre, n, semilla, max_seg, nivel):
    esc = ESCENARIOS[nombre]
    rng = np.random.default_rng(semilla)
    env = E.EntornoDronPersona(n, semilla=semilla)
    env.nivel = nivel
    env.ap.reset(np.ones(n, bool), nivel)
    preparar(env, esc, rng)
    k_vel = rng.uniform(0.9, 1.1, n)
    wp, t_wp = np.zeros(n, int), np.zeros(n)
    acc_p = np.full(n, E.N_ACC_PERSONA - 1)
    vivo = np.ones(n, bool)
    z = lambda: np.zeros(n)
    r_tot, r_ctrl, pasos, visto, pierde, recupera = z(), z(), z(), z(), z(), z()
    t_readq, t_perdida = np.full(n, np.nan), np.full(n, np.nan)
    d_min, z_max = np.full(n, 99.0), z()
    g_min, g_max = np.full(n, 99.0), np.full(n, -99.0)
    dj = np.zeros((n, 3))                                  # Σ|Δu| por eje: cabeceo, guiñada, gimbal
    n_dj = z()
    acciones = np.zeros(len(E.CLASES))
    resultado = np.array(["tiempo"] * n, dtype=object)
    import torch
    for paso in range(int(max_seg / E.DT)):
        obs = env.obs_dron().astype(np.float32)
        with torch.no_grad():
            acc, _ = modelo.predict(obs, deterministic=True)
        acc = np.asarray(acc).astype(int)
        md = env.mascara_decision() & vivo
        acciones += np.bincount(acc[md], minlength=len(E.CLASES))
        vx, vy = velocidad_ladron(env, esc["ruta"], wp, t_wp, k_vel)
        env.v_forzada[:, 0, 0], env.v_forzada[:, 0, 1] = vx, vy
        u_ant, mando_ant = env.u_prev.copy(), env.mando_prev.copy()
        r, _, done, info = env.step(acc, acc_p, auto_reset=False)
        ambos = info["al_mando"] & mando_ant & vivo
        dj[ambos] += np.abs(env.u_prev[ambos] - u_ant[ambos])
        n_dj += ambos
        r_tot += np.where(vivo, r, 0.0)
        r_ctrl -= np.where(vivo, info["jitter"] + info["esfuerzo"], 0.0)
        pasos += vivo
        visto += vivo & info["visto"]
        perdio = vivo & info["pierde"]
        t_perdida = np.where(perdio & np.isnan(t_perdida), (paso + 1) * E.DT, t_perdida)
        pierde += perdio
        readq = vivo & info["descubre"]
        t_readq = np.where(readq & np.isnan(t_readq) & ~np.isnan(t_perdida), (paso + 1) * E.DT - t_perdida, t_readq)
        recupera += readq
        d_min = np.where(vivo, np.minimum(d_min, info["dist"]), d_min)
        z_max = np.where(vivo, np.maximum(z_max, env.dz), z_max)
        g_min = np.where(vivo, np.minimum(g_min, env.cam_pitch), g_min)
        g_max = np.where(vivo, np.maximum(g_max, env.cam_pitch), g_max)
        for i in np.where(done & vivo)[0]:
            resultado[i] = E.resultado_de(info, i)
        vivo &= ~done
        if not vivo.any():
            break
    jit = dj / np.maximum(n_dj, 1)[:, None] * np.array([E.CAB_MAX, E.YAW_MAX, E.GIMBAL_VEL])
    return dict(resultado=resultado, dur=pasos * E.DT, visto=visto / np.maximum(pasos, 1), pierde=pierde,
                recupera=recupera, t_readq=t_readq, d_min=d_min, z_max=z_max, g_min=g_min, g_max=g_max,
                r_tot=r_tot, r_ctrl=r_ctrl, jit=jit, con_jit=n_dj > 0, acciones=acciones / max(acciones.sum(), 1))


def resumir(res):
    """Promedios de un escenario."""
    r = res["resultado"]
    fila = {k: float(np.mean(r == k)) for k in RESULTADOS}
    cj = res["con_jit"]
    fila.update(dur=float(res["dur"].mean()), visto=float(res["visto"].mean()), pierde=float(res["pierde"].mean()),
                recupera=float(res["recupera"].mean()),
                t_readq=float(np.nanmean(res["t_readq"])) if (~np.isnan(res["t_readq"])).any() else float("nan"),
                d_min=float(res["d_min"].mean()), z_max=float(res["z_max"].mean()),
                g_min=float(res["g_min"].min()), g_max=float(res["g_max"].max()),
                r_tot=float(res["r_tot"].mean()), r_ctrl=float(res["r_ctrl"].mean()),
                jit_pitch=float(res["jit"][cj, 0].mean()) if cj.any() else float("nan"),
                jit_yaw=float(res["jit"][cj, 1].mean()) if cj.any() else float("nan"),
                jit_gimbal=float(res["jit"][cj, 2].mean()) if cj.any() else float("nan"),
                acciones=res["acciones"])
    return fila


def evaluar_modelo(ruta, n, semilla, max_seg, nivel, escenarios):
    from stable_baselines3 import PPO
    modelo = PPO.load(ruta, device="cpu")
    out = {}
    for k, nombre in enumerate(escenarios):
        out[nombre] = resumir(correr_escenario(modelo, nombre, n, semilla + 1000 * k, max_seg, nivel))
    return out


def pasos_de(ruta):
    m = re.search(r"_(\d+)_steps\.zip$", ruta)
    return int(m.group(1)) if m else 0


def f(x, d=2):
    return "--" if x is None or (isinstance(x, float) and np.isnan(x)) else ("%." + str(d) + "f") % x


def tabla_modelo(out, titulo):
    L = ["## " + titulo, "",
         "| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | "
         "Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | "
         "Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |",
         "|---|" + "---:|" * 19]
    for nombre, x in out.items():
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s / %s | %s | %s | %s | %s | %s |" % (
            nombre, f(x["cumplida"]), f(x["perdido"]), f(x["alcanzado"]), f(x["panel"]), f(x["geocerca"]), f(x["tiempo"]),
            f(x["dur"], 1), f(x["visto"]), f(x["pierde"]), f(x["recupera"]), f(x["t_readq"], 1), f(x["d_min"], 1),
            f(x["z_max"], 1), f(x["g_min"], 0), f(x["g_max"], 0), f(x["r_tot"], 1), f(x["r_ctrl"], 1),
            f(x["jit_pitch"], 2), f(x["jit_yaw"], 2), f(x["jit_gimbal"], 2)))
    L += ["", "Acciones elegidas con la IA al mando (fracción):", "",
          "| Escenario | " + " | ".join(E.CLASES) + " |", "|---|" + "---:|" * len(E.CLASES)]
    for nombre, x in out.items():
        L.append("| %s | %s |" % (nombre, " | ".join(f(a) for a in x["acciones"])))
    return L


CAMPOS_CSV = ["modelo", "pasos", "escenario"] + RESULTADOS + ["dur", "visto", "pierde", "recupera", "t_readq", "d_min",
                                                             "z_max", "g_min", "g_max", "r_tot", "r_ctrl", "jit_pitch",
                                                             "jit_yaw", "jit_gimbal"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", action="append", help="ruta a un .zip de SB3 (se puede repetir)")
    ap.add_argument("--barrido", type=float, default=0, help="evaluar base_v9 + un checkpoint cada tantos M pasos + el último")
    ap.add_argument("--version", default=None, help="nombre para los informes (por defecto, según el modelo)")
    ap.add_argument("--episodios", type=int, default=50)
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--max-seg", type=float, default=120.0)
    ap.add_argument("--nivel", type=float, default=0.1, help="nivel de currículo fijo (viento y rapidez del ladrón)")
    ap.add_argument("--escenarios", default=",".join(ESCENARIOS))
    ap.add_argument("--hilos", type=int, default=2, help="hilos de torch (el entrenamiento puede estar corriendo)")
    a = ap.parse_args()
    import torch
    torch.set_num_threads(a.hilos)
    os.makedirs(INFORMES, exist_ok=True)
    escenarios = [s for s in a.escenarios.split(",") if s]
    modelos = list(a.modelo or [])
    if a.barrido:
        cks = sorted(glob.glob(os.path.join(CHECKPOINTS, "dron_master_*_steps.zip")), key=pasos_de)
        paso = a.barrido * 1e6
        elegidos, meta = [], paso
        for c in cks:                                  # el checkpoint más cercano a cada múltiplo (25, 50, 75... M)
            if pasos_de(c) >= meta - 0.5e6:
                elegidos.append(c)
                meta = (round(pasos_de(c) / paso) + 1) * paso
        if cks and cks[-1] not in elegidos:
            elegidos.append(cks[-1])
        modelos += ([BASE] if os.path.exists(BASE) else []) + elegidos
    if not modelos:
        ap.error("indica --modelo o --barrido")

    filas, ultimo = [], None
    t0 = time.time()
    for ruta in modelos:
        ti = time.time()
        out = evaluar_modelo(ruta, a.episodios, a.semilla, a.max_seg, a.nivel, escenarios)
        p = pasos_de(ruta)
        for nombre, x in out.items():
            filas.append(dict({k: x[k] for k in CAMPOS_CSV[3:]}, modelo=os.path.basename(ruta), pasos=p, escenario=nombre))
        ultimo = (ruta, out)
        print("%-40s %7.1f M | %s | %.0f s" % (os.path.basename(ruta), p / 1e6,
              " ".join("%s %.2f" % (k, v["cumplida"]) for k, v in out.items()), time.time() - ti), flush=True)

    version = a.version or ("v10-master-%dM" % round(pasos_de(ultimo[0]) / 1e6))
    cab = ["Política determinista · %d partidas por escenario · semillas %d.. · nivel de currículo %.2f · máx. %.0f s · "
           "%s" % (a.episodios, a.semilla, a.nivel, a.max_seg, time.strftime("%Y-%m-%d %H:%M")), ""]
    if len(modelos) == 1:
        L = ["# Evaluación en escenarios fijos · %s" % version, "", "Modelo: `%s`" % os.path.relpath(ultimo[0], SIM)] + [""] + cab
        L += tabla_modelo(ultimo[1], "Resultados por escenario")
    else:
        csv_ruta = os.path.join(INFORMES, "barrido_%s.csv" % version)
        with open(csv_ruta, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, CAMPOS_CSV)
            w.writeheader()
            for fl in filas:
                w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in fl.items()})
        L = ["# Barrido de checkpoints en escenarios fijos · %s" % version, ""] + cab
        L += ["Todos los números: `%s`." % os.path.basename(csv_ruta), "",
              "## Misiones cumplidas por escenario a lo largo del entrenamiento", "",
              "| M pasos | " + " | ".join(escenarios) + " | Media | Alcanzado (media) | Jitter yaw (media) |",
              "|---:|" + "---:|" * (len(escenarios) + 3)]
        por = {}
        for fl in filas:
            por.setdefault((fl["pasos"], fl["modelo"]), {})[fl["escenario"]] = fl
        for (p, _), d in sorted(por.items()):
            c = [d[s]["cumplida"] for s in escenarios]
            L.append("| %s | %s | %s | %s | %s |" % ("base v9" if p == 0 else "%.0f" % (p / 1e6), " | ".join(f(x) for x in c),
                                                     f(np.mean(c)), f(np.mean([d[s]["alcanzado"] for s in escenarios])),
                                                     f(np.nanmean([d[s]["jit_yaw"] for s in escenarios]))))
        L += [""] + tabla_modelo(ultimo[1], "Detalle del último modelo (%s)" % os.path.basename(ultimo[0]))
    ruta_md = os.path.join(INFORMES, ("evaluacion_%s.md" if len(modelos) == 1 else "barrido_%s.md") % version)
    with open(ruta_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("informe: %s (%.0f s)" % (os.path.relpath(ruta_md, SIM), time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
