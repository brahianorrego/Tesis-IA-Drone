# -*- coding: utf-8 -*-
"""
Graba UNA partida real del entorno V16 (simulacion/entorno.py, misión de 2 paneles) para el visor, con la política de
la V15 que está en Git (modelos/dron_politica.json) SIN REENTRENAR, o con un .zip de SB3 (--modelo).

Sirve para revisar el visor con datos de la simulación (no con la coreografía de repeticion_prueba_v16.py). Quita los
campos pesados que el visor V16 no usa (nube de puntos, partículas) para que el archivo quede liviano.

Uso (desde simulacion/):
  .venv/bin/python herramientas/grabar_repeticion_v16.py [--seg 120] [--semilla 3] [--modelo ruta.zip]
Salida: replays_prueba/sim_v16_semillaN.json y una línea en replays_prueba/lista.json
"""
import argparse
import json
import os
import sys

import numpy as np

SIM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SIM)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import entorno as E  # noqa: E402
from medir_v16 import cargar_politica  # noqa: E402

PESADOS = ("nube", "pf", "det", "ruta")
RESULTADOS = {"cumplida": "cumplida", "alcanzado": "alcanzado", "perdido": "perdido", "geocerca": "geocerca"}


def grabar(pol, seg, semilla):
    env = E.EntornoDronPersona(1, semilla=semilla, nivel=E.NIVEL_V16)
    cuadros, resultado = [], "tiempo"
    for _ in range(int(seg / E.DT) + 1):
        f = env.foto(0)
        for k in PESADOS:
            f.pop(k, None)
        cuadros.append(f)
        acc, _ = pol.predict(env.obs_dron().astype(np.float32), deterministic=True)
        _, _, done, info = env.step(np.asarray(acc).astype(int), np.full(1, E.N_ACC_PERSONA - 1), auto_reset=False)
        if done[0]:
            for k, v in info.items():
                if k in RESULTADOS and np.asarray(v).ravel()[:1].any():
                    resultado = RESULTADOS[k]
            break
    return {"iteracion": 0, "pasos": 0, "adversaria": True, "mision": False, "guion": None, "paneles": env.paneles(0),
            "resultado": resultado, "maniobras": 0, "dt": E.DT, "cuadros": cuadros, "version": "V16 · entorno de la sesión A",
            "autor": "Brahian Andrés Orrego Osorio", "prueba": True,
            "nota": "Partida real del entorno V16 con la política de la V15 sin reentrenar (modelos/dron_politica.json)."}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seg", type=float, default=120.0)
    ap.add_argument("--semilla", type=int, default=3)
    ap.add_argument("--modelo", default=None)
    a = ap.parse_args()
    pol = cargar_politica(a.modelo)
    rep = grabar(pol, a.seg, a.semilla)
    carpeta = os.path.join(SIM, "replays_prueba")
    nombre = "sim_v16_semilla%d.json" % a.semilla
    with open(os.path.join(carpeta, nombre), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, separators=(",", ":"))
    ruta_lista = os.path.join(carpeta, "lista.json")
    lista = json.load(open(ruta_lista, encoding="utf-8")) if os.path.exists(ruta_lista) else []
    lista = [x for x in lista if x["archivo"] != nombre]
    lista.append({"archivo": nombre, "titulo": "Entorno V16 (sesión A) · política V15 sin reentrenar · semilla %d (%.0f s)"
                  % (a.semilla, len(rep["cuadros"]) * E.DT)})
    with open(ruta_lista, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=1)
    print("%s: %d cuadros, resultado %s, %.0f KB" % (nombre, len(rep["cuadros"]), rep["resultado"],
                                                    os.path.getsize(os.path.join(carpeta, nombre)) / 1024))


if __name__ == "__main__":
    main()
