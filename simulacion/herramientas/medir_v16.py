# -*- coding: utf-8 -*-
"""
Medición rápida de la partida V16 (misión completa con 2 paneles) con una política fija: resultados, custodia, rendición,
alturas y suavidad. Sirve para comparar cada cambio de la V16 (fases A1-A5) con y sin él.

Por defecto usa la política de la V15 exportada para la Jetson (modelos/dron_politica.json) SIN REENTRENAR; con --modelo,
un .zip de SB3. Con --set NOMBRE=VALOR se cambia una constante de entorno.py antes de correr (ablaciones), por ejemplo
--set ALTURAS_V16=0.

Uso (desde simulacion/):
  .venv/bin/python herramientas/medir_v16.py --n 256 --seg 300
  .venv/bin/python herramientas/medir_v16.py --set ALTURAS_V16=0
"""
import argparse
import collections
import json
import os
import sys
import time

import numpy as np

SIM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SIM)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import entorno as E  # noqa: E402
from politica_json import PoliticaJSON  # noqa: E402


def cargar_politica(ruta):
    if ruta and ruta.endswith(".zip"):
        from stable_baselines3 import PPO
        return PPO.load(ruta, device="cpu")
    return PoliticaJSON(ruta or os.path.join(SIM, "modelos", "dron_politica.json"), E.OBS_DRON)


def medir(pol, n=256, seg=300.0, semilla=0, nivel=E.NIVEL_V16):
    env = E.EntornoDronPersona(n, semilla=semilla, nivel=nivel)
    res = collections.Counter()
    fin = []
    pasos = int(seg / E.DT) + 5
    t_bajo = t_tot = t_real8 = t_real8_bajo = 0
    jit = np.zeros(3)
    n_jit = 0
    extra = collections.defaultdict(float)
    vivo = np.ones(n, bool)
    posturas = np.zeros(4)
    saltos = 0
    civ = collections.Counter()
    for _ in range(pasos):
        f0 = env.salto_f.copy()
        acc, _ = pol.predict(env.obs_dron().astype(np.float32), deterministic=True)
        u0 = env.u_prev_fis.copy()
        _, _, done, info = env.step(np.asarray(acc).astype(int), np.full(n, E.N_ACC_PERSONA - 1), auto_reset=False)
        dh = np.hypot(env.px - env.dx[:, None], env.py - env.dy[:, None])
        r8 = (env.activa & (dh < E.R_GENTE)).any(1) & vivo
        t_tot += int(vivo.sum())
        t_bajo += int((vivo & (env.dz < E.Z_SEGURA - 0.05)).sum())
        t_real8 += int(r8.sum())
        t_real8_bajo += int((r8 & (env.dz < E.Z_SEGURA - 0.05)).sum())
        posturas += np.bincount(env.pos[vivo, 0], minlength=4)[:4]
        saltos += int((vivo & (env.salto_f == 1) & (f0 == 0)).sum())
        ac = env.activa[:, 1:] & vivo[:, None]
        civ.update(env.c_est[:, 1:][ac].tolist())
        am = info["al_mando"] & vivo
        jit += np.abs(env.u_prev_fis - u0)[am].sum(0)
        n_jit += int(am.sum())
        for k in ("cam_piso_obj", "salto"):
            if k in info:
                extra[k] += float(np.asarray(info[k])[vivo].sum())
        for i in np.where(done & vivo)[0]:
            r_ = E.resultado_de(info, i)
            res[r_] += 1
            fin.append(dict(res=r_, vista=float(info["t_vista_ac"][i]), rinde=bool(info["exito"][i]),
                            t=float(info["t_ep"][i])))
        vivo &= ~done
        if not vivo.any():
            break
    for i in np.where(vivo)[0]:
        res["tiempo"] += 1
        fin.append(dict(res="tiempo", vista=float(env.t_vista_ac[i]), rinde=False, t=float(env.t[i] * E.DT)))
    N = len(fin)
    out = {"n": N, "resultados": {k: round(v / N, 3) for k, v in sorted(res.items())},
           "custodia_60": round(np.mean([f["rinde"] or f["vista"] >= E.CUSTODIA_S[0] for f in fin]), 3),
           "custodia_90": round(np.mean([f["rinde"] or f["vista"] >= E.CUSTODIA_S[1] for f in fin]), 3),
           "vista_media_s": round(float(np.mean([f["vista"] for f in fin])), 1),
           "frac_bajo_330": round(t_bajo / max(t_tot, 1), 4),
           "frac_persona_real_8m": round(t_real8 / max(t_tot, 1), 3),
           "bajo_330_con_persona_real_8m": round(t_real8_bajo / max(t_real8, 1), 4),
           "jitter_por_paso": [round(float(x), 4) for x in jit / max(n_jit, 1)]}
    out["posturas_ladron"] = {E.NOMBRE_POSTURA[k]: round(float(v / max(posturas.sum(), 1)), 3) for k, v in enumerate(posturas)}
    out["saltos_por_partida"] = round(saltos / max(N, 1), 2)
    tc = sum(civ.values())
    out["civiles"] = {E.NOMBRE_CIVIL[k]: round(v / max(tc, 1), 3) for k, v in sorted(civ.items())}
    for k, v in extra.items():
        out[k + "_por_s"] = round(v / max(t_tot, 1) / E.DT, 4)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default=None)
    ap.add_argument("--n", type=int, default=256)
    ap.add_argument("--seg", type=float, default=300.0)
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--nivel", type=int, default=E.NIVEL_V16)
    ap.add_argument("--set", action="append", default=[], help="NOMBRE=VALOR de entorno.py (se puede repetir)")
    a = ap.parse_args()
    for kv in a.set:
        k, v = kv.split("=", 1)
        viejo = getattr(E, k)
        setattr(E, k, type(viejo)(float(v)) if not isinstance(viejo, str) else v)
    t0 = time.time()
    out = medir(cargar_politica(a.modelo), a.n, a.seg, a.semilla, a.nivel)
    out["config"] = {"set": a.set, "nivel": a.nivel, "seg": a.seg, "segundos_reloj": round(time.time() - t0)}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
