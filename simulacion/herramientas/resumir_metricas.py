# -*- coding: utf-8 -*-
"""
Resume un entrenamiento del dron en un informe corto (máximo 80 líneas) para diagnosticarlo sin leer logs crudos.

Lee salida/metricas.json (una entrada por iteración = un rollout de 512 entornos x 128 pasos), los logs de
TensorBoard si existen y, si ya se corrió herramientas/evaluar_politica.py --barrido, su tabla de escenarios fijos.
Escribe informes/resumen_<versión>.md con: tasa de éxito, colisiones, duración de episodio, recompensa (total y la
parte que se puede separar), jitter, entropía, uso de las acciones y la tendencia por tramos. Lo que no se registra
lo dice y propone cómo registrarlo en el próximo entrenamiento.

Uso (desde simulacion\\):
  .venv\\Scripts\\python.exe herramientas\\resumir_metricas.py                       (todo lo que lleva la corrida)
  .venv\\Scripts\\python.exe herramientas\\resumir_metricas.py --hasta-pasos 350.64 --version v10-master-350M
"""
import argparse
import csv
import glob
import json
import math
import os
import sys

import numpy as np

SIM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SIM)

from entorno import CLASES, DT, K_DELTA  # noqa: E402

MAX_LINEAS = 80
ENTROPIA_MAX = math.log(len(CLASES))


def promedio(ms, campo, sub="adv", peso="n"):
    """Promedio de un campo ponderado por el número de partidas (o por los segundos con la IA al mando)."""
    v, w = [], []
    for m in ms:
        d = m.get(sub) or {}
        x = d.get(campo)
        if x is None:
            continue
        v.append(x)
        w.append((m.get("adv") or {}).get("n", 0) if peso == "n" else (d.get(peso) or 0) if peso else 1)
    if not v or sum(w) <= 0:
        return None
    return float(np.average(v, weights=w))


def ventana(ms):
    """Indicadores de un grupo de iteraciones."""
    n = sum((m.get("adv") or {}).get("n", 0) for m in ms)
    pasos = sum(m["_dpasos"] for m in ms)
    seg_mando = sum((m.get("control") or {}).get("seg_mando", 0) for m in ms)
    ctrl = promedio(ms, "total", "control", "seg_mando")
    jit = promedio(ms, "jitter", "control", "seg_mando")
    r = {k: promedio(ms, k) for k in ("cumplida", "perdido", "no_encontrado", "alcanzado", "peaton", "panel", "fuera",
                                       "vista", "recompensa", "perdidas", "recuperaciones", "redescubre", "maniobras")}
    r.update(n=n, pasos=pasos,
             dur=(pasos / n * DT) if n else None,                    # duración media estimada = pasos / partidas
             ctrl_ep=(ctrl * seg_mando / n) if (ctrl is not None and n) else None,   # castigo de control por partida
             du=(jit / K_DELTA * DT) if jit is not None else None,   # Σ|Δu| por paso con la IA al mando (3 ejes)
             entropia=promedio(ms, "entropia", "dron", None), nivel=float(np.mean([m["nivel"] for m in ms])),
             acc=np.mean([m["acciones"] for m in ms], 0), acc_b=np.mean([m["acciones_busqueda"] for m in ms], 0))
    return r


def pct(x):
    return "--" if x is None else "%.0f %%" % (100 * x)


def num(x, d=2):
    return "--" if x is None or (isinstance(x, float) and math.isnan(x)) else ("%." + str(d) + "f") % x


def flecha(a, b, mayor_es_mejor=True, umbral=0.02):
    if a is None or b is None:
        return ""
    d = a - b
    if abs(d) < umbral:
        return "="
    return "mejor" if (d > 0) == mayor_es_mejor else "peor"


def tensorboard():
    archivos = [f for f in glob.glob(os.path.join(SIM, "**", "events.out.tfevents.*"), recursive=True) if ".venv" not in f]
    if not archivos:
        return "No hay logs de TensorBoard (SB3 se lanzó sin `tensorboard_log`)."
    try:
        from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    except ImportError:
        return "Hay %d archivos de TensorBoard pero falta el paquete `tensorboard` en el .venv para leerlos." % len(archivos)
    claves = set()
    for f in archivos:
        ea = EventAccumulator(f)
        ea.Reload()
        claves |= set(ea.Tags().get("scalars", []))
    return "TensorBoard: %d archivos; escalares: %s." % (len(archivos), ", ".join(sorted(claves)[:12]))


def evaluacion_fija(hasta):
    """Últimos checkpoints del barrido de escenarios fijos (evaluar_politica.py), si existe."""
    rutas = sorted(glob.glob(os.path.join(SIM, "informes", "barrido_*.csv")), key=os.path.getmtime)
    if not rutas:
        return ["Sin evaluación en escenarios fijos: correr `herramientas/evaluar_politica.py --barrido 25`."]
    filas = [r for r in csv.DictReader(open(rutas[-1], encoding="utf-8")) if int(r["pasos"]) <= hasta]
    if not filas:
        return ["El barrido `%s` no tiene checkpoints hasta este punto." % os.path.basename(rutas[-1])]
    por = {}
    for r in filas:
        por.setdefault(int(r["pasos"]), {})[r["escenario"]] = r
    esc = list(next(iter(por.values())).keys())
    L = ["Fuente: `%s` (política determinista, mismas semillas)." % os.path.basename(rutas[-1]), "",
         "| M pasos | " + " | ".join("cumplida %s" % e for e in esc) + " | alcanzado | jitter cab/yaw/gmb |",
         "|---:|" + "---:|" * (len(esc) + 2)]
    for p in sorted(por)[-5:]:
        d = por[p]
        m = lambda k: np.nanmean([float(d[e][k]) if d[e][k] not in ("", "nan") else np.nan for e in esc])
        L.append("| %s | %s | %s | %s / %s / %s |" % ("base v9" if p == 0 else "%.0f" % (p / 1e6),
                 " | ".join(pct(float(d[e]["cumplida"])) for e in esc), pct(m("alcanzado")),
                 num(m("jit_pitch")), num(m("jit_yaw")), num(m("jit_gimbal"))))
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metricas", default=os.path.join(SIM, "salida", "metricas.json"))
    ap.add_argument("--hasta-pasos", type=float, default=None, help="cortar en estos millones de pasos")
    ap.add_argument("--version", default=None)
    ap.add_argument("--ventana", type=int, default=50, help="iteraciones de la ventana actual (~3.3 M pasos)")
    ap.add_argument("--tramo", type=float, default=50.0, help="M pasos por fila de la tabla de tendencia")
    a = ap.parse_args()

    ms = json.load(open(a.metricas, encoding="utf-8"))
    if a.hasta_pasos:
        ms = [m for m in ms if m["pasos"] <= a.hasta_pasos * 1e6 + 1]
    ant = 0
    for m in ms:
        m["_dpasos"] = m["pasos"] - ant if m["pasos"] > ant else m["pasos"]
        ant = m["pasos"]
    ms = [m for m in ms if m.get("adv")]
    fin = ms[-1]["pasos"]
    version = a.version or "v10-master-%dM" % round(fin / 1e6)
    act, prev, ini = ventana(ms[-a.ventana:]), ventana(ms[-2 * a.ventana:-a.ventana]), ventana(ms[:a.ventana])
    w = a.ventana

    L = ["# Resumen de entrenamiento · %s" % version, "",
         "Corrida: %s · %d iteraciones · %.1f M pasos · motor %s · nivel de currículo actual %.2f." % (
             os.path.relpath(a.metricas, SIM), ms[-1]["it"], fin / 1e6, ms[-1].get("motor", "?"), ms[-1]["nivel"]),
         "Ventana actual = últimas %d iteraciones (%.1f M pasos, %d partidas de entrenamiento, política estocástica)." % (
             w, act["pasos"] / 1e6, act["n"]), "",
         "## Indicadores (ventana actual vs anterior)", "",
         "| Indicador | Actual | Anterior | Inicio de la corrida | Cambio |", "|---|---:|---:|---:|---|"]
    filas = [("Misión cumplida (éxito)", "cumplida", pct, True), ("Perdido (búsqueda agotada)", "perdido", pct, False),
             ("No encontrado", "no_encontrado", pct, False), ("Alcanzado por el ladrón", "alcanzado", pct, False),
             ("Choque con peatón (partidas con peatones)", "peaton", pct, False), ("Choque con panel", "panel", pct, False),
             ("Sale de la geocerca", "fuera", pct, False), ("Tiempo con el objetivo a la vista", "vista", pct, True)]
    for nom, k, fm, mejor in filas:
        L.append("| %s | %s | %s | %s | %s |" % (nom, fm(act[k]), fm(prev[k]), fm(ini[k]), flecha(act[k], prev[k], mejor)))
    for nom, k, d, mejor, u in (("Duración media de la partida (s, estimada)", "dur", 1, None, 1.0),
                                ("Recompensa total por partida", "recompensa", 2, True, 0.3),
                                ("  de ella, castigo de control (jitter + esfuerzo)", "ctrl_ep", 2, True, 0.1),
                                ("Pérdidas del objetivo por partida", "perdidas", 2, False, 0.1),
                                ("Re-adquisiciones por partida", "redescubre", 2, True, 0.1),
                                ("Jitter: Σ|Δu| por paso con la IA al mando (3 ejes)", "du", 3, False, 0.002),
                                ("Entropía de la política (máx. %.2f)" % ENTROPIA_MAX, "entropia", 2, None, 0.02)):
        L.append("| %s | %s | %s | %s | %s |" % (nom, num(act[k], d), num(prev[k], d), num(ini[k], d),
                                                 "" if mejor is None else flecha(act[k], prev[k], mejor, u)))
    L += ["", "Acciones (ventana actual, %): decide con el objetivo fijado / en la búsqueda tras perderlo.", "",
          "| " + " | ".join(c[:9] for c in CLASES) + " |", "|" + "---:|" * len(CLASES),
          "| " + " | ".join("%.0f / %.0f" % (100 * x, 100 * y) for x, y in zip(act["acc"], act["acc_b"])) + " |"]
    muertas = [CLASES[i] for i in range(len(CLASES)) if act["acc_b"][i] < 0.01 and i < 7]
    if muertas:
        L.append("En la búsqueda casi nunca usa: %s." % ", ".join(muertas))

    # tendencia por tramos
    L += ["", "## Tendencia por tramos de %.0f M pasos" % a.tramo, "",
          "| M pasos | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Dur. (s) | Recompensa | Σ|Δu|/paso | Entropía | Nivel |",
          "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    tramos = {}
    for m in ms:
        tramos.setdefault(int(m["pasos"] // (a.tramo * 1e6)), []).append(m)
    for t in sorted(tramos):
        v = ventana(tramos[t])
        L.append("| %.0f-%.0f | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            t * a.tramo, min((t + 1) * a.tramo, fin / 1e6), pct(v["cumplida"]), pct(v["perdido"]), pct(v["alcanzado"]),
            pct(v["panel"]), pct(v["fuera"]), num(v["dur"], 0), num(v["recompensa"], 1), num(v["du"], 3),
            num(v["entropia"], 2), num(v["nivel"], 2)))
    ult = [m for m in ms if m["pasos"] >= fin - 100e6]
    x = np.array([m["pasos"] for m in ult]) / 1e8
    y = np.array([m["adv"]["cumplida"] for m in ult])
    pend = np.polyfit(x, y, 1)[0] if len(ult) > 2 else float("nan")
    L.append("Pendiente de la tasa de cumplidas en los últimos 100 M pasos: %+.1f puntos por cada 100 M (ruido por "
             "iteración ±%.0f puntos)." % (100 * pend, 100 * float(np.std(y))))

    L += ["", "## Escenarios fijos (evaluar_politica.py)", ""] + evaluacion_fija(fin)
    L += ["", "## Lo que no se registra (y cómo registrarlo en el próximo entrenamiento)", "",
          "- %s" % tensorboard(),
          "- Duración real de la partida: aquí se estima como pasos / partidas terminadas. Guardar `ep_len` en "
          "`VecDron.fin` (entrenar_master.py) y su media en `resumen()`.",
          "- Recompensa por componente: solo se separa el castigo de control. Acumular cada término de `rew_d` "
          "(vista, rango, guía, descubre, pierde, maniobra, éxito, fallas, control) en `info[\"r_comp\"]` dentro de "
          "`entorno.step` y promediarlo por partida en `VecDron`.",
          "- Jitter por eje (cabeceo, yaw, gimbal): hoy se guarda la suma de los 3. Devolver `|u - u_prev|` por eje en "
          "`info` y guardar 3 promedios en `m[\"control\"]`. Mientras tanto, el barrido de escenarios fijos sí lo mide.",
          "- Gimbal mínimo alcanzado (regla dura -45°): guardar `min(cam_pitch)` por iteración."]
    if len(L) > MAX_LINEAS:
        L = L[:MAX_LINEAS - 1] + ["(informe recortado a %d líneas)" % MAX_LINEAS]
    os.makedirs(os.path.join(SIM, "informes"), exist_ok=True)
    ruta = os.path.join(SIM, "informes", "resumen_%s.md" % version)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("informe: %s (%d líneas)" % (os.path.relpath(ruta, SIM), len(L)))


if __name__ == "__main__":
    main()
