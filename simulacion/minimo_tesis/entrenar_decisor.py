# -*- coding: utf-8 -*-
"""
Entrena el DECISOR IA del mínimo indispensable (fase G) y lo deja listo para la Jetson.

  1. Datos: vuelos sin intervención en mundos aleatorios (decisor_ia.generar), etiquetas automáticas con la verdad.
     Semillas separadas: entrenamiento 0-299, validación 1000-1059, prueba 2000-2059 (mundos que el modelo nunca vio).
  2. MLPClassifier de scikit-learn (capas 32-16, ReLU), entradas normalizadas.
  3. Umbral y persistencia (cuadros seguidos sobre el umbral) elegidos EN LAZO CERRADO sobre los mundos de VALIDACIÓN:
     el que menos activaciones innecesarias tenga sin dejar pasar más riesgos que las reglas en esos mismos mundos.
     Nunca se ajusta con el protocolo del comité (que es la evaluación).
  4. Métricas de clasificación en la PRUEBA: ROC, precisión-exhaustividad, matriz de confusión -> informes/.
  5. Exporta minimo_tesis/decision.pkl y decision.json.

Uso (desde simulacion\\): .venv\\Scripts\\python.exe -m minimo_tesis.entrenar_decisor        (~15 min)
"""
import argparse
import json
import os
import time

import numpy as np

from . import decisor_ia as D
from . import sensores as S
from . import sistema as M

SIM = os.path.dirname(D.AQUI)
INFORMES = os.path.join(SIM, "informes")
DATOS = os.path.join(D.AQUI, "datos")
SEM_ENT, SEM_VAL, SEM_PRU = range(0, 300), range(1000, 1060), range(2000, 2060)
SEM_LAZO = range(1000, 1030)       # validación en lazo cerrado (umbral y persistencia): 30 mundos, 1920 vuelos


def datos(nombre, semillas):
    os.makedirs(DATOS, exist_ok=True)
    ruta = os.path.join(DATOS, "%s.npz" % nombre)
    if os.path.exists(ruta):
        z = np.load(ruta)
        return z["X"], z["y"], z["g"]
    t0 = time.time()
    X, y, g = D.generar(semillas)
    np.savez_compressed(ruta, X=X, y=y, g=g)
    print("  %s: %d cuadros, %.1f %% con riesgo (%.0f s)" % (nombre, len(y), 100 * y.mean(), time.time() - t0), flush=True)
    return X, y, g


def lazo_cerrado(decisor_fn, semillas, n=64, dur=25.0):
    """Vuelos con el decisor al mando en mundos aleatorios. Devuelve, por vuelo: choque, riesgo no evitado (persona a
    < 2 m o holgura < 0.5 m), activación, y tiempo detenido."""
    out = {"choque": [], "riesgo": [], "activo": [], "t_det": [], "cerca": [], "dmin_p": [], "v": []}
    for sem in semillas:
        w, v, _ = D._mundo_aleatorio(sem, n)
        sis = decisor_fn(n)
        malo = np.zeros(n, bool)
        cerca = np.zeros(n, bool)                       # persona a < 2 m con el dron por debajo de la altura segura
        dmin_p = np.full(n, np.inf)
        act = np.zeros(n, bool)
        t_det = np.zeros(n)
        no = np.zeros(n, bool)
        for _ in range(int(dur / M.DT)):
            m = w.medir()
            vx, vy, vz, nuevo = sis.actualizar(m, v, no, no, no, w.dz)
            act |= nuevo
            t_det += sis.interviene * M.DT
            w.paso(vx, vy, vz)
            dh = np.hypot(w.px - w.dx, w.py - w.dy)
            malo |= w.activa & (dh < D.D_PERSONA_ETIQ) & (w.dz < M.ALCANCE_Z)
            bajo = w.activa & (w.dz < M.Z_SEGURA - 0.05)
            cerca |= bajo & (dh < D.D_PERSONA_ETIQ)
            dmin_p = np.minimum(dmin_p, np.where(bajo, dh, np.inf))
            for ax, ay, bx, by, h in w.paneles:
                malo |= (S.distancia_segmento(w.dx, w.dy, ax, ay, bx, by) - M.RADIO_DRON < D.HOLGURA_PANEL) & (w.dz < h + 0.2)
        out["choque"].append(w.choque_panel | w.choque_persona)
        out["riesgo"].append(malo)
        out["activo"].append(act)
        out["t_det"].append(t_det)
        out["cerca"].append(cerca)
        out["v"].append(v)
        out["dmin_p"].append(dmin_p)
    return {k: np.concatenate(v) for k, v in out.items()}


def main():
    from sklearn.metrics import (average_precision_score, confusion_matrix, precision_recall_curve, roc_auc_score,
                                 roc_curve)
    from sklearn.neural_network import MLPClassifier
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocultas", default="32,16")
    args = ap.parse_args()
    t0 = time.time()
    print("datos (vuelos sin intervención, etiquetas automáticas)...", flush=True)
    Xe, ye, _ = datos("entrenamiento", SEM_ENT)
    Xv, yv, _ = datos("validacion", SEM_VAL)
    Xp, yp, _ = datos("prueba", SEM_PRU)
    media, desv = Xe.mean(0), Xe.std(0) + 1e-6
    capas = tuple(int(c) for c in args.ocultas.split(","))
    clf = MLPClassifier(hidden_layer_sizes=capas, activation="relu", alpha=1e-4, batch_size=512, learning_rate_init=1e-3,
                        max_iter=60, early_stopping=True, validation_fraction=0.1, n_iter_no_change=6, random_state=0)
    import pickle
    cache = os.path.join(DATOS, "clf_%s.pkl" % "-".join(str(c) for c in capas))
    if os.path.exists(cache):
        with open(cache, "rb") as fh:
            clf = pickle.load(fh)
    else:
        clf.fit((Xe - media) / desv, ye)
        with open(cache, "wb") as fh:
            pickle.dump(clf, fh)
    modelo = D.Modelo(clf, media, desv, 0.5, 1)
    pv = modelo.proba(Xv)
    print("MLP %s: %d iteraciones · AUC validación %.4f (%.0f s)" % (capas, clf.n_iter_, roc_auc_score(yv, pv),
                                                                     time.time() - t0), flush=True)
    # umbral y persistencia en lazo cerrado sobre la VALIDACIÓN (no sobre el protocolo)
    base = lazo_cerrado(lambda n: M.SistemaMinimo(n), SEM_LAZO)
    sin = lazo_cerrado(lambda n: M.SistemaMinimo(n, activo=False), SEM_LAZO)
    necesaria = sin["riesgo"]                                   # sin sistema habría habido riesgo en ese vuelo
    print("  reglas en validación: riesgos no evitados %d · choques %d · persona<2m bajo 3.3m %d · activaciones %d "
          "(innecesarias %d) · detenido sin necesidad %.0f s · vuelos con riesgo sin sistema %d de %d" % (
              base["riesgo"].sum(), base["choque"].sum(), base["cerca"].sum(), base["activo"].sum(),
              (base["activo"] & ~necesaria).sum(),
              base["t_det"][~necesaria].sum(), necesaria.sum(), len(necesaria)), flush=True)
    grid = []
    for k in (1, 2):
        for u in (0.3, 0.5, 0.7):
            mod = D.Modelo(clf, media, desv, u, k)
            for env in (True, False):
                r = lazo_cerrado(lambda n: D.DecisorIA(n, mod, con_envolvente=env), SEM_LAZO)
                fila = dict(umbral=u, k=k, envolvente=env, riesgo=int(r["riesgo"].sum()), choque=int(r["choque"].sum()),
                            cerca=int(r["cerca"].sum()),
                            innecesarias=int((r["activo"] & ~necesaria).sum()),
                            t_det_innec=float(r["t_det"][~necesaria].sum()))
                grid.append(fila)
                print("  umbral %.1f k %d %s: riesgos %d choques %d persona<2m bajo 3.3m %d innecesarias %d (detenido sin "
                      "necesidad %.0f s)" % (u, k, "IA+env" if env else "IA sola", fila["riesgo"], fila["choque"],
                                             fila["cerca"], fila["innecesarias"], fila["t_det_innec"]), flush=True)
    innec_reglas = int((base["activo"] & ~necesaria).sum())
    # elección: con envolvente (la que va al dron), no más riesgos que las reglas; luego el mínimo de innecesarias
    cand = [f for f in grid if f["envolvente"] and f["riesgo"] <= base["riesgo"].sum() and f["choque"] <= base["choque"].sum()
            and f["cerca"] <= base["cerca"].sum()]
    if not cand:
        cand = sorted([f for f in grid if f["envolvente"]], key=lambda f: (f["riesgo"], f["choque"]))[:3]
        print("  AVISO: ninguna combinación iguala la seguridad de las reglas en validación; se elige la más segura",
              flush=True)
    mejor = min(cand, key=lambda f: (f["innecesarias"], f["t_det_innec"], f["riesgo"]))
    modelo = D.Modelo(clf, media, desv, mejor["umbral"], mejor["k"])
    modelo.guardar()
    print("elegido: umbral %.1f, %d cuadro(s) seguidos" % (mejor["umbral"], mejor["k"]), flush=True)
    # métricas de clasificación en la PRUEBA
    pp = modelo.proba(Xp)
    fpr, tpr, _ = roc_curve(yp, pp)
    pr, rc, _ = precision_recall_curve(yp, pp)
    cm = confusion_matrix(yp, pp >= modelo.umbral)
    res = dict(capas=list(capas), iteraciones=int(clf.n_iter_), n_ent=int(len(ye)), n_val=int(len(yv)), n_pru=int(len(yp)),
               pos_ent=float(ye.mean()), pos_pru=float(yp.mean()), auc_roc=float(roc_auc_score(yp, pp)),
               auc_pr=float(average_precision_score(yp, pp)), umbral=mejor["umbral"], k=mejor["k"],
               matriz=cm.tolist(), grid=grid, reglas_val=dict(riesgo=int(base["riesgo"].sum()), choque=int(base["choque"].sum()),
                                                              cerca=int(base["cerca"].sum()),
                                                              innecesarias=innec_reglas,
                                                              t_det_innec=float(base["t_det"][~necesaria].sum())),
               vuelos_val=int(len(necesaria)), vuelos_val_con_riesgo=int(necesaria.sum()), seg=time.time() - t0)
    with open(os.path.join(D.AQUI, "decision_entrenamiento.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(10, 4.2))
        ax[0].plot(fpr, tpr, color="#1f77b4")
        ax[0].plot([0, 1], [0, 1], ":", color="gray")
        ax[0].set_title("ROC (prueba) · AUC = %.3f" % res["auc_roc"])
        ax[0].set_xlabel("Tasa de falsos positivos")
        ax[0].set_ylabel("Tasa de verdaderos positivos (exhaustividad)")
        ax[1].plot(rc, pr, color="#d62728")
        ax[1].axhline(yp.mean(), ls=":", color="gray")
        ax[1].set_title("Precisión-exhaustividad (prueba) · AP = %.3f" % res["auc_pr"])
        ax[1].set_xlabel("Exhaustividad")
        ax[1].set_ylabel("Precisión")
        fig.tight_layout()
        fig.savefig(os.path.join(INFORMES, "minimo_tesis_decisor_curvas.png"), dpi=120)
    except Exception as e:                                     # las curvas son un extra; el informe trae los números
        print("  (sin gráfica: %s)" % e)
    print("AUC-ROC prueba %.4f · AP %.4f · matriz %s · %.0f s" % (res["auc_roc"], res["auc_pr"], cm.tolist(),
                                                                  time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
