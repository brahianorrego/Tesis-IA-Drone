# -*- coding: utf-8 -*-
"""
Experimento comparativo para la tesis: ¿la IA aprendida es mejor que reglas escritas a mano?
Objetivo de la fase 2: mantener a la persona en la vista sin ser alcanzado y sin maniobrar de más.

Compara, en las mismas situaciones simuladas (mismas semillas):
  * Aleatorio                 (referencia mínima)
  * Regla: umbral de distancia  (esquiva al lado contrario si < 4 m, sube si < 2.5 m)
  * Regla: subir si < 8 m       (la mejor regla simple del experimento 1)
  * Regla: vigilante            (paneo si no la ve, la sigue si se aleja > 12 m, sube si < 5 m)
  * IA (PPO)                  (la política del dron entrenada por refuerzo)

contra la persona adversaria entrenada y contra cada tipo de peatón normal. Mide la
fracción de partidas en que el dron es alcanzado, las maniobras por partida y las
maniobras innecesarias (peatones quietos, que se alejan o que se detienen antes).

Uso:  python evaluar.py [--partidas 2000]   -> imprime la tabla y guarda salida/evaluacion.json
"""
import argparse
import json
import os

import numpy as np
import torch

from entorno import CLASES, GUIONES, N_ACC_PERSONA, OBS_DRON, OBS_PERSONA, EntornoDronPersona
from entrenar import MODELOS, SALIDA, ActorCritico, actuar, guardar_json

INOFENSIVOS = {"quieto", "alejarse", "acercar_y_parar"}


def regla_umbral(o):
    vis, d, ang = o[:, 0] > 0.5, o[:, 1] * 20, o[:, 4]
    lado = np.where(ang > 0, 1, 2)                 # persona a la derecha -> esquivar a la izquierda
    return np.where(vis & (d < 2.5), 3, np.where(vis & (d < 4.0), lado, np.where(~vis, 5, 0)))


def regla_subir(o):
    vis, d = o[:, 0] > 0.5, o[:, 1] * 20
    return np.where(vis & (d < 8.0), 3, np.where(~vis, 5, 0))


def regla_vigilante(o):
    vis, d = o[:, 0] > 0.5, o[:, 1] * 20
    return np.where(~vis, 5, np.where(d < 5.0, 3, np.where(d > 12.0, 6, 0)))


def evaluar(politica, red_p, partidas, adversaria, guion=None, semilla=123):
    n = 256
    env = EntornoDronPersona(n, semilla=semilla, fraccion_adversaria=1.0 if adversaria else 0.0)
    if guion is not None:
        env.guion[:] = GUIONES.index(guion)
        env._preparar_guion(np.ones(n, bool))
    resultados = []
    maniobras = np.zeros(n)
    dmin = np.full(n, 99.0)
    vis = np.zeros(n)
    largo = np.zeros(n)
    rng = np.random.default_rng(semilla)
    while len(resultados) < partidas:
        od = env.obs_dron()
        ad = politica(od, rng)
        ap, _, _, _ = actuar(red_p, env.obs_persona())
        guion_antes = env.guion.copy()
        _, _, done, info = env.step(ad, ap)
        maniobras += info["inicia"]
        dmin = np.minimum(dmin, info["dist"])
        vis += info["visto"]
        largo += 1
        for i in np.where(done)[0]:
            resultados.append((bool(info["choque"][i]), maniobras[i], dmin[i], vis[i] / largo[i]))
        maniobras[done] = 0.0
        dmin[done] = 99.0
        vis[done] = 0.0
        largo[done] = 0.0
        if guion is not None and done.any():
            env.guion[done] = GUIONES.index(guion)
            env._preparar_guion(done)
    r = resultados[:partidas]
    arr = np.array(r, float)
    return {"alcanzado": float(arr[:, 0].mean()), "maniobras": float(arr[:, 1].mean()),
            "dist_min": float(np.median(arr[:, 2])), "vista": float(arr[:, 3].mean()), "partidas": len(r)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--partidas", type=int, default=2000)
    a = ap.parse_args()
    ck = torch.load(os.path.join(MODELOS, "ultimo.pt"), weights_only=False)
    red_d, red_p = ActorCritico(OBS_DRON, len(CLASES)), ActorCritico(OBS_PERSONA, N_ACC_PERSONA)
    red_d.load_state_dict(ck["dron"])
    red_p.load_state_dict(ck["persona"])
    politicas = {
        "Aleatorio": lambda o, rng: rng.integers(0, len(CLASES), len(o)),
        "Regla: umbral de distancia": lambda o, rng: regla_umbral(o),
        "Regla: subir si < 8 m": lambda o, rng: regla_subir(o),
        "Regla: vigilante": lambda o, rng: regla_vigilante(o),
        "IA (PPO)": lambda o, rng: actuar(red_d, o, codicioso=True)[0],
    }
    escenarios = [("adversaria", True, None)] + [(g, False, g) for g in GUIONES]
    tabla = {}
    for nombre, pol in politicas.items():
        tabla[nombre] = {}
        for esc, adv, g in escenarios:
            tabla[nombre][esc] = evaluar(pol, red_p, a.partidas if adv else a.partidas // 4, adv, g)
        inof = [tabla[nombre][g] for g in INOFENSIVOS]
        tabla[nombre]["maniobras_innecesarias"] = float(np.mean([x["maniobras"] for x in inof]))
        peligrosos = [tabla[nombre][g]["alcanzado"] for g in ("directo", "trotar_directo")]
        tabla[nombre]["alcanzado_peatones_directos"] = float(np.mean(peligrosos))
        tabla[nombre]["vista_peatones"] = float(np.mean([tabla[nombre][g]["vista"] for g in GUIONES]))
    print("\nEvaluación con la política de la iteración %d (%.1f M pasos)\n" % (ck["iteracion"], ck["pasos"] / 1e6))
    print("%-28s %14s %14s %14s %14s %16s" % ("", "ladrón: vista", "ladrón: alcanza", "peatón: vista", "peatón directo", "maniobras innec."))
    for nombre, t in tabla.items():
        print("%-28s %13.0f%% %14.0f%% %13.0f%% %13.0f%% %16.2f" % (nombre, 100 * t["adversaria"]["vista"], 100 * t["adversaria"]["alcanzado"],
              100 * t["vista_peatones"], 100 * t["alcanzado_peatones_directos"], t["maniobras_innecesarias"]))
    guardar_json(os.path.join(SALIDA, "evaluacion.json"), {"iteracion": ck["iteracion"], "pasos": ck["pasos"], "tabla": tabla})


if __name__ == "__main__":
    main()
