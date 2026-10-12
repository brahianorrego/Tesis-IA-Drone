# -*- coding: utf-8 -*-
"""
V16 · fase A4: ¿cada término de la recompensa premia lo que queremos? Corre la misión V16 con varios estilos de pilotaje
fijos (la política V15 sin reentrenar, avanzar siempre, quedarse quieto, acciones al azar) y, por partida, suma cada
componente de la recompensa (info["r_comp"]) y la custodia. Un término sirve si ordena los estilos como la custodia (o, la
suavidad, si castiga al que se mueve a saltos) y si por partida se correlaciona con la custodia.

Uso (desde simulacion/):  .venv/bin/python herramientas/analizar_recompensa_v16.py --n 96 --seg 150
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
from politica_json import PoliticaJSON  # noqa: E402


class Fija(object):
    def __init__(self, accion=None, semilla=0):
        self.a, self.rng = accion, np.random.default_rng(semilla)

    def predict(self, obs, deterministic=True):
        if self.a is None:
            return self.rng.integers(0, len(E.CLASES), len(obs)), None
        return np.full(len(obs), self.a), None


def correr(pol, n, seg, semilla):
    env = E.EntornoDronPersona(n, semilla=semilla, nivel=E.NIVEL_V16)
    comp = np.zeros((n, len(E.R_COMP)))
    jerk = np.zeros(n)
    vivo = np.ones(n, bool)
    fin = []
    for _ in range(int(seg / E.DT)):
        acc, _ = pol.predict(env.obs_dron().astype(np.float32), deterministic=True)
        _, _, done, info = env.step(np.asarray(acc).astype(int), np.full(n, E.N_ACC_PERSONA - 1), auto_reset=False)
        comp += np.where(vivo[:, None], info["r_comp"], 0.0)
        jerk += np.where(vivo, info["jerk"], 0.0)
        for i in np.where(done & vivo)[0]:
            fin.append(i)
        vivo &= ~done
        if not vivo.any():
            break
    vista = env.t_vista_ac.copy()
    return comp, vista, jerk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=96)
    ap.add_argument("--seg", type=float, default=150.0)
    ap.add_argument("--semilla", type=int, default=3)
    a = ap.parse_args()
    estilos = {"V15 sin reentrenar": PoliticaJSON(os.path.join(SIM, "modelos", "dron_politica.json"), E.OBS_DRON),
               "avanzar siempre": Fija(6), "quieto (MANTENER)": Fija(0), "al azar": Fija(None)}
    out, todos = {}, []
    for nombre, pol in estilos.items():
        comp, vista, jerk = correr(pol, a.n, a.seg, a.semilla)
        out[nombre] = {"vista_s": round(float(vista.mean()), 1),
                       **{k: round(float(comp[:, j].mean()), 2) for j, k in enumerate(E.R_COMP)},
                       "multa_sacudida": round(float(-jerk.mean()), 3)}
        todos.append((comp, vista))
    comp = np.concatenate([c for c, _ in todos])
    vista = np.concatenate([v for _, v in todos])
    corr = {k: round(float(np.corrcoef(comp[:, j], vista)[0, 1]), 3) if comp[:, j].std() > 0 else None
            for j, k in enumerate(E.R_COMP)}
    print(json.dumps({"por_estilo": out, "correlacion_con_vista_por_partida": corr}, ensure_ascii=False, indent=1))


if __name__ == "__main__" and "--predictivo" not in sys.argv:
    main()


def predictivo(n=96, seg=150.0, semilla=5, ventana=3.0):
    """¿Predicen los potenciales (coberturas y lado de escape) que el dron NO pierda al ladrón en los próximos `ventana`
    segundos? Con la política V15, en cada paso con el objetivo a la vista se guarda la cobertura, el coseno del lado de
    escape y si en la ventana siguiente el tracker lo soltó (más de 1 s sin verlo). Devuelve la tasa de pérdida por cuartil."""
    pol = PoliticaJSON(os.path.join(SIM, "modelos", "dron_politica.json"), E.OBS_DRON)
    env = E.EntornoDronPersona(n, semilla=semilla, nivel=E.NIVEL_V16)
    k = int(ventana / E.DT)
    reg_c, reg_e, reg_v, pierde = [], [], [], []
    for _ in range(int(seg / E.DT)):
        acc, _ = pol.predict(env.obs_dron().astype(np.float32))
        _, _, done, info = env.step(acc, np.full(n, E.N_ACC_PERSONA - 1), auto_reset=False)
        reg_c.append(env.cob_frac.copy())
        reg_e.append(env.phi_esc.copy() / max(E.K_ESC, 1e-9))
        reg_v.append(info["visto"] & (env.modo == E.FIJADO))
        pierde.append(info["pierde"].copy())
        env.reset(done)
    C, X, V, P = map(np.array, (reg_c, reg_e, reg_v, pierde))
    fut = np.zeros_like(P)
    for t in range(len(P)):
        fut[t] = P[t + 1:t + 1 + k].any(0)
    out = {}
    for nombre, M in (("cobertura", C), ("lado_de_escape", X)):
        x, y = M[V], fut[V]
        q = np.quantile(x, [0.25, 0.5, 0.75])
        cuart = np.digitize(x, q)
        out[nombre] = {"tasa_de_perdida_por_cuartil": [round(float(y[cuart == c].mean()), 4) for c in range(4)],
                       "cortes": [round(float(v), 3) for v in q]}
    return out


if __name__ == "__main__" and "--predictivo" in sys.argv:
    print(json.dumps(predictivo(), ensure_ascii=False))
