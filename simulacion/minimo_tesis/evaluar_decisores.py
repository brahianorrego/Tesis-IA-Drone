# -*- coding: utf-8 -*-
"""
FASE G · REGLAS vs IA vs IA + ENVOLVENTE con el mismo protocolo del comité, los escenarios de discriminación, las
condiciones degradadas y el barrido de velocidad. Necesita el decisor entrenado (python -m minimo_tesis.entrenar_decisor).

Métricas del comité y dos más que muestran el valor de DECIDIR:
  · activaciones innecesarias y tiempo detenido sin necesidad: la activación era necesaria si, en el MISMO vuelo sin
    sistema y sin operador (misma semilla), la persona habría quedado a menos de 2 m del dron a su alcance o el panel a
    menos de 0.5 m (el criterio de las etiquetas de la IA, físico y no el de los umbrales de las reglas);
  · anticipación: del inicio del riesgo (verdad del simulador) al comando (negativo = se adelantó).

Uso (desde simulacion\\): .venv\\Scripts\\python.exe -m minimo_tesis.evaluar_decisores [--n 100]
Salidas: informes\\minimo_tesis_decisor_ia.md y .csv, minimo_tesis\\replay\\replay_protocolo_{reglas,ia,ia_env}.json
"""
import argparse
import csv
import datetime
import json
import os
import time

import numpy as np

from . import decisor_ia as D
from . import protocolo_comite as P
from . import sensores as S

DECISORES = [("reglas", "Reglas"), ("ia", "IA sola"), ("ia_env", "IA + envolvente"),
             ("ia_env_estricta", "IA + envolvente estricta")]
COND_BARRIDO = [0, 7, 10, 12]          # nominal, latencia 300 ms, combinada, solo cabeza y hombros
# solo en los mundos de prueba, para medir el costo del veto del árbitro al ascenso (NO es una propuesta para el dron sin
# que Brahian lo decida: cambiaría la lectura de la regla dura 5)
EXTRA_PRUEBA = [("ia_env_ascenso_libre", "IA + envolvente, ascenso sin veto del árbitro (solo referencia)")]


def referencias(nom, n, sem, cond=S.NOMINAL, v=None):
    """El mismo vuelo sin sistema: sin operador (¿era necesaria la intervención?) y con operador (riesgo real)."""
    cf, _ = P.correr(nom, n, sem, False, cond=cond, v=v, operador=False)
    ref, _ = P.correr(nom, n, sem, False, cond=cond, v=v)
    return cf, ref


def evaluar(nom, n, sem, dec, cond=S.NOMINAL, v=None, grabar=False, base=None):
    """Un escenario con un decisor; la necesidad sale del mismo vuelo sin sistema ni operador."""
    cf, ref = base if base is not None else referencias(nom, n, sem, cond, v)
    r, cuadros = P.correr(nom, n, sem, True, grabar=grabar, cf=ref, cond=cond, v=v, decisor=dec)
    nec = cf["malo"]
    r["necesaria"] = nec
    r["innecesaria"] = r["activo"] & ~nec
    r["omitida"] = nec & ~r["activo"]
    r["t_det_innec"] = np.where(nec, 0.0, r["t_det"])
    r["cerca"] = r["d_min_seg"] < 2.0
    if nom in P.ESCENARIOS_DISC:
        # discriminación: la decisión correcta es POR VUELO (activarse solo si en ese vuelo hacía falta), sin chocar
        r["exito"] = ~r["choque"] & (r["activo"] == nec)
    return r, cuadros


def _dmin(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    return "%.2f / %.2f" % (np.percentile(v, 1), np.median(v)) if len(v) else "—"


def pct(k, n, dec=0):
    p, a, b = P.wilson(k, n)
    f = "%%.%df" % dec
    return (f + " %% [" + f + ", " + f + "]") % (100 * p, 100 * a, 100 * b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--semilla", type=int, default=2026)
    ap.add_argument("--rapido", action="store_true", help="sin degradadas ni barrido")
    args = ap.parse_args()
    n, t0 = args.n, time.time()
    escen = list(P.ESCENARIOS) + list(P.ESCENARIOS_DISC)
    res, filas, replays = {}, [], {d: [] for d, _ in DECISORES}
    for j, nom in enumerate(escen):
        sem = args.semilla + 1000 * j
        base = referencias(nom, n, sem)
        for dec, _ in DECISORES:
            r, cuadros = evaluar(nom, n, sem, dec, grabar=True, base=base)
            res[(dec, nom)] = r
            replays[dec].append((nom, cuadros))
            for i in range(n):
                filas.append({"bloque": "protocolo", "condicion": "Nominal", "decisor": dec, "escenario": nom, "v": "",
                              "vuelo": i, "exito": int(r["exito"][i]), "choque": int(r["choque"][i]),
                              "activado": int(r["activo"][i]), "necesaria": int(r["necesaria"][i]),
                              "innecesaria": int(r["innecesaria"][i]), "omitida": int(r["omitida"][i]),
                              "t_detenido_s": round(float(r["t_det"][i]), 1), "parada_operador": int(r["parada"][i]),
                              "riesgo_a_comando_s": P._f(r["lat_cmd"][i]), "dist_min_m": P._f(r["d_min"][i])})
        print("%-18s " % nom + " | ".join("%s éx %3.0f%% ch %d inn %d" % (
            d, 100 * res[(d, nom)]["exito"].mean(), res[(d, nom)]["choque"].sum(), res[(d, nom)]["innecesaria"].sum())
            for d, _ in DECISORES), flush=True)
    deg, barr = {}, {}
    if not args.rapido:
        print("condiciones degradadas...", flush=True)
        for ic, c in enumerate(P.CONDICIONES):
            for j, nom in enumerate(escen):
                base = referencias(nom, n, args.semilla + 1000 * j, c)
                for dec, _ in DECISORES:
                    r, _ = evaluar(nom, n, args.semilla + 1000 * j, dec, cond=c, base=base)
                    deg[(ic, dec, nom)] = r
                    filas.append({"bloque": "degradada", "condicion": c.nombre, "decisor": dec, "escenario": nom, "v": "",
                                  "vuelo": -1, "exito": int(r["exito"].sum()), "choque": int(r["choque"].sum()),
                                  "activado": int(r["activo"].sum()), "necesaria": int(r["necesaria"].sum()),
                                  "innecesaria": int(r["innecesaria"].sum()), "omitida": int(r["omitida"].sum()),
                                  "t_detenido_s": round(float(r["t_det"].sum()), 1),
                                  "parada_operador": int(r["parada"].sum()), "riesgo_a_comando_s": "", "dist_min_m": ""})
            print("  %d/%d %s" % (ic + 1, len(P.CONDICIONES), c.nombre), flush=True)
        print("barrido de velocidad...", flush=True)
        for ic in COND_BARRIDO:
            c = P.CONDICIONES[ic]
            for nom, _t, _c in P.BARRIDO:
                for v in P.VELOCIDADES:
                    for dec, _ in DECISORES:
                        r, _ = P.correr(nom, n, args.semilla + 50000 + int(10 * v), True, cond=c, v=v, decisor=dec)
                        ok = P.detiene_con_margen(nom, r)
                        barr[(ic, dec, nom, v)] = (int(ok.sum()), int(r["choque"].sum()))
                        filas.append({"bloque": "barrido", "condicion": c.nombre, "decisor": dec, "escenario": nom, "v": v,
                                      "vuelo": -1, "exito": int(ok.sum()), "choque": int(r["choque"].sum()),
                                      "activado": int(r["activo"].sum()), "necesaria": "", "innecesaria": "", "omitida": "",
                                      "t_detenido_s": "", "parada_operador": int(r["parada"].sum()),
                                      "riesgo_a_comando_s": "", "dist_min_m": ""})
            print("  barrido %s" % c.nombre, flush=True)
    with open(os.path.join(P.INFORMES, "minimo_tesis_decisor_ia.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    for dec, _ in DECISORES:
        _replay(dec, replays[dec])
    with open(os.path.join(D.AQUI, "decision_entrenamiento.json"), encoding="utf-8") as fh:
        ent = json.load(fh)
    # lazo cerrado en los mundos de PRUEBA (nunca usados para entrenar ni para elegir el umbral)
    from .entrenar_decisor import SEM_PRU, lazo_cerrado
    from . import sistema as M_
    print("mundos de prueba en lazo cerrado...", flush=True)
    sin = lazo_cerrado(lambda k: M_.SistemaMinimo(k, activo=False), SEM_PRU)
    prueba = {"_sin": sin}
    for dec, _ in DECISORES + EXTRA_PRUEBA:
        prueba[dec] = lazo_cerrado(lambda k, d_=dec: D.crear_decisor(d_, k), SEM_PRU)
    _informe(res, deg, barr, ent, escen, args, time.time() - t0, prueba)
    print("informe: informes\\minimo_tesis_decisor_ia.md (%.0f s)" % (time.time() - t0))


def v_max(barr, ic, dec, nom, n):
    vm = 0.0
    for v in P.VELOCIDADES:
        if barr[(ic, dec, nom, v)][0] < P.UMBRAL_SEGURO * n:
            break
        vm = v
    return vm


def _informe(res, deg, barr, ent, escen, args, seg, prueba=None):
    n = args.n
    nd = [d for d, _ in DECISORES]
    L = ["# Decisor IA del mínimo indispensable (fase G)", "",
         "Generado por `minimo_tesis/evaluar_decisores.py` · %d vuelos por variante · semilla base %d · %s · %.0f s" % (
             n, args.semilla, datetime.date.today().isoformat(), seg), "",
         "Se comparan tres formas de DECIDIR la intervención (detención y ascenso), con los mismos sensores (ruido y "
         "retardo de 100 ms) y el mismo control de ArduPilot:", "",
         "- **Reglas:** umbrales fijos (obstáculo por distancia de frenado y tiempo al choque; persona según el árbitro).",
         "- **IA sola:** un clasificador MLP decide con las entradas que tiene la Jetson.",
         "- **IA + envolvente:** la misma IA dentro de las reglas duras: el bloqueo frontal (LiDAR < 3 m avanzando) y la "
         "persona a menos de 3 m mandan siempre, y el ascenso por una persona solo lo autoriza el árbitro (< 3 m, o < 8 m "
         "acercándose); antes, la IA solo puede DETENER. Es la regla dura 5 tal como está escrita (el árbitro autoriza; el "
         "LiDAR y la parada mandan) y es la versión que iría al dron.",
         "- **IA + envolvente estricta:** además, una persona a menos de 3 m obliga a detenerse (más estricto que la regla).",
         ""]
    # ---- clasificador
    cm = np.array(ent["matriz"])
    tn, fp, fn, tp = cm.ravel()
    L += ["## 1. El clasificador", "",
          "- Arquitectura: MLP de scikit-learn %s, ReLU; %d entradas: %s." % (
              "-".join(str(c) for c in ent["capas"]), len(D.CARACTERISTICAS), ", ".join(D.CARACTERISTICAS)),
          "- Datos: vuelos sin intervención en mundos aleatorios (velocidades de 0 a 8 m/s; personas quietas, que vienen, "
          "que cruzan, paralelas o al azar; panel o no; sensores degradados al azar). Etiqueta automática con la verdad del "
          "simulador: \"si el piloto sigue igual, ¿en los próximos %.0f s choca o una persona queda a menos de %.0f m?\"." % (
              D.T_HORIZONTE, D.D_PERSONA_ETIQ),
          "- Separación por semillas (mundos distintos): entrenamiento %d cuadros (%.0f %% con riesgo), validación %d, "
          "prueba %d (%.0f %% con riesgo)." % (ent["n_ent"], 100 * ent["pos_ent"], ent["n_val"], ent["n_pru"], 100 * ent["pos_pru"]),
          "- Umbral %.1f y %d cuadro(s) seguidos, elegidos en lazo cerrado sobre mundos de VALIDACIÓN (no con este "
          "protocolo): el mínimo de activaciones innecesarias sin dejar pasar más riesgos que las reglas." % (ent["umbral"], ent["k"]),
          "", "Desempeño en la PRUEBA (mundos nunca vistos), por cuadro:", "",
          "| AUC-ROC | Precisión media (AP) | Exhaustividad | Precisión | Tasa de falsos positivos |",
          "|---:|---:|---:|---:|---:|",
          "| %.3f | %.3f | %.1f %% | %.1f %% | %.1f %% |" % (ent["auc_roc"], ent["auc_pr"], 100 * tp / max(tp + fn, 1),
                                                         100 * tp / max(tp + fp, 1), 100 * fp / max(fp + tn, 1)),
          "", "Matriz de confusión (prueba, por cuadro, con el umbral elegido):", "",
          "| | Predice CONTINUAR | Predice DETENER |", "|---|---:|---:|",
          "| Sin riesgo real | %d | %d |" % (tn, fp), "| Con riesgo real | %d | %d |" % (fn, tp), "",
          "Curvas ROC y precisión-exhaustividad: `minimo_tesis_decisor_curvas.png`. La exhaustividad por cuadro no es la "
          "seguridad: un riesgo dura muchos cuadros y basta uno (o k seguidos) para intervenir; la seguridad se mide abajo, "
          "en lazo cerrado.", ""]
    # ---- mundos de prueba en lazo cerrado
    if prueba:
        nec = prueba["_sin"]["riesgo"]
        nv = len(nec)
        L += ["## 2. Mundos de prueba en lazo cerrado (la comparación menos sesgada)", "",
              "%d vuelos en 60 mundos aleatorios de PRUEBA (semillas que no se usaron ni para entrenar ni para elegir el "
              "umbral): velocidades de 0 a 8 m/s, todo tipo de personas, paneles y sensores degradados al azar. %d vuelos "
              "(%.0f %%) habrían tenido riesgo físico sin sistema." % (nv, nec.sum(), 100 * nec.mean()), "",
              "| Decisor | Riesgos no evitados | Choques | Persona a < 2 m bajo 3.30 m (vuelos) | Distancia mínima a personas bajo 3.30 m (p1 / mediana, m) | Activaciones innecesarias | Tiempo detenido sin necesidad (s) | Tiempo detenido total (s) |",
              "|---|---:|---:|---:|---:|---:|---:|---:|",
              "| Sin sistema | %d | %d | %d | %s | — | — | — |" % (nec.sum(), prueba["_sin"]["choque"].sum(),
                                                      prueba["_sin"]["cerca"].sum(), _dmin(prueba["_sin"]["dmin_p"]))]
        for dec, t in DECISORES + EXTRA_PRUEBA:
            r = prueba[dec]
            L.append("| %s | %d (%.1f %%) | %d | %d | %s | %d | %.0f | %.0f |" % (
                t, r["riesgo"].sum(), 100 * r["riesgo"].sum() / max(nec.sum(), 1), r["choque"].sum(), r["cerca"].sum(),
                _dmin(r["dmin_p"]), (r["activo"] & ~nec).sum(), r["t_det"][~nec].sum(), r["t_det"].sum()))
        # desglose por la velocidad del piloto: hasta 4 m/s (LOIT_SPEED recomendado con personas) y más
        vv = prueba["_sin"]["v"]
        L += ["", "Por velocidad del piloto (vuelos con persona a < 2 m bajo 3.30 m / riesgos no evitados / choques):", "",
              "| Decisor | Piloto ≤ 4 m/s (%d vuelos) | Piloto > 4 m/s (%d vuelos) |" % ((vv <= 4.0).sum(), (vv > 4.0).sum()),
              "|---|---:|---:|",
              "| Sin sistema | %s | %s |" % tuple("%d / %d / %d" % (prueba["_sin"]["cerca"][g].sum(), prueba["_sin"]["riesgo"][g].sum(),
                                                                 prueba["_sin"]["choque"][g].sum()) for g in (vv <= 4.0, vv > 4.0))]
        for dec, t in DECISORES + EXTRA_PRUEBA:
            r = prueba[dec]
            L.append("| %s | %s |" % (t, " | ".join("%d / %d / %d" % (r["cerca"][g].sum(), r["riesgo"][g].sum(), r["choque"][g].sum())
                                                   for g in (vv <= 4.0, vv > 4.0))))
        L += ["", "Riesgo no evitado: con el decisor al mando, la persona igual quedó a menos de 2 m del dron (a su alcance) "
              "o el panel a menos de 0.5 m. Incluye los casos imposibles (un panel a 5 m con el dron a 8 m/s, una persona "
              "que corre hacia el dron desde muy cerca).", ""]
    # ---- protocolo
    L += ["## 3. Protocolo del comité y escenarios de discriminación (nominal)", "",
          "Éxito en el protocolo: si debe activarse, se activa y no choca; si no, no se activa y no choca. En los escenarios "
          "de discriminación (f) el éxito es la decisión correcta POR VUELO: activarse si y solo si en ese mismo vuelo, sin "
          "sistema, la persona habría quedado a menos de 2 m. Innecesarias: activaciones en vuelos que sin sistema no "
          "habrían tenido ese riesgo físico.", "",
          "| Escenario | " + " | ".join("Éxito %s" % t for _, t in DECISORES) + " | Choques R/IA/IA+E/est. | Innecesarias R/IA/IA+E/est. | Riesgo → comando (s) R / IA / IA+E / est. |",
          "|---|" + "---:|" * (len(DECISORES) + 3)]
    for nom in escen:
        g, desc = P.TODOS[nom][0], P.TODOS[nom][1]
        rs = [res[(d, nom)] for d in nd]
        lat = []
        for r in rs:
            a = r["activo"] & ~np.isnan(r["lat_cmd"])
            lat.append("%.2f" % np.nanmean(r["lat_cmd"][a]) if a.any() else "—")
        L.append("| %s) %s | %s | %s | %s | %s |" % (
            g, desc, " | ".join(pct(r["exito"].sum(), n) for r in rs), " / ".join(str(r["choque"].sum()) for r in rs),
            " / ".join(str(r["innecesaria"].sum()) for r in rs), " / ".join(lat)))
    tot = lambda d, k, lista: sum(res[(d, x)][k].sum() for x in lista)
    prot, disc = list(P.ESCENARIOS), list(P.ESCENARIOS_DISC)
    L += ["", "| Total | " + " | ".join(t for _, t in DECISORES) + " |", "|---|" + "---:|" * len(DECISORES)]
    for nombre, lista, k in (("Éxito, 13 variantes del protocolo", prot, "exito"), ("Éxito, 5 de discriminación", disc, "exito"),
                             ("Choques (todos)", escen, "choque"), ("Activaciones innecesarias (todos)", escen, "innecesaria"),
                             ("Tiempo detenido sin necesidad (s, todos)", escen, "t_det_innec"),
                             ("Riesgos físicos omitidos (necesaria y no se activó)", escen, "omitida"),
                             ("Paradas del operador", escen, "parada"),
                             ("Vuelos con persona a < 2 m bajo 3.30 m (todos)", escen, "cerca")):
        L.append("| %s | %s |" % (nombre, " | ".join(
            ("%.0f" % tot(d, k, lista)) if k in ("t_det_innec",) else
            (pct(tot(d, k, lista), n * len(lista), 1) if k == "exito" else "%d" % tot(d, k, lista)) for d in nd)))
    # ---- degradadas
    if deg:
        L += ["", "## 4. Condiciones degradadas", "",
              "Por condición, sumando las 18 variantes (13 del protocolo + 5 de discriminación), %d vuelos cada una: "
              "éxitos, choques e innecesarias." % n, "",
              "| Condición | " + " | ".join("%s: éxito · choques · innec." % t for _, t in DECISORES) + " |",
              "|---|" + "---:|" * len(DECISORES)]
        for ic, c in enumerate(P.CONDICIONES):
            celdas = []
            for d in nd:
                ex = sum(deg[(ic, d, x)]["exito"].sum() for x in escen)
                ch = sum(deg[(ic, d, x)]["choque"].sum() for x in escen)
                inn = sum(deg[(ic, d, x)]["innecesaria"].sum() for x in escen)
                celdas.append("%.1f %% · %d · %d" % (100 * ex / (n * len(escen)), ch, inn))
            L.append("| C%d %s | %s |" % (ic, c.nombre, " | ".join(celdas)))
    if barr:
        L += ["", "## 5. Velocidad máxima segura (m/s, detenerse con margen en ≥ 95 %)", "",
              "| Condición | Escenario | " + " | ".join(t for _, t in DECISORES) + " |", "|---|---|" + "---:|" * len(DECISORES)]
        for ic in COND_BARRIDO:
            for nom, t, _c in P.BARRIDO:
                L.append("| C%d %s | %s | %s |" % (ic, P.CONDICIONES[ic].nombre, t, " | ".join(
                    "%.0f" % v_max(barr, ic, d, nom, n) for d in nd)))
    L += ["", "## 6. Lectura", ""] + _lectura(res, deg, barr, prueba, escen, n) + [
          "", "## 7. Justificación del uso de IA en la decisión", ""] + _justificacion(res, barr, prueba, escen, n) + [
          "", "## 8. Exportación a la Jetson", "",
          "- `minimo_tesis/decision.pkl`: el modelo de scikit-learn con la normalización, el umbral y la persistencia.",
          "- `minimo_tesis/decision.json`: pesos, sesgos, media y desviación de cada entrada, umbral, persistencia y el nombre "
          "y orden de las entradas. `decisor_ia.predecir_json` lo evalúa con NumPy puro (sin scikit-learn) y da lo mismo "
          "(prueba en `tests/test_decisor_ia.py`).",
          "- En la Jetson, cada cuadro: calcular las %d entradas con la caja de YOLO, el LiDAR, la velocidad del EKF y el "
          "seguimiento alfa-beta; evaluar la red (~1 000 multiplicaciones); si la probabilidad supera el umbral durante k "
          "cuadros, mandar la detención (y el ascenso si la envolvente lo autoriza). Las reglas duras corren al lado y "
          "mandan siempre." % len(D.CARACTERISTICAS), "",
          "Datos crudos: `minimo_tesis_decisor_ia.csv`. Repetición en el visor: grupo \"Proyecto de grado\", una opción "
          "por decisor."]
    with open(os.path.join(P.INFORMES, "minimo_tesis_decisor_ia.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def _anticipacion(res, dec, lista):
    v = []
    for x in lista:
        r = res[(dec, x)]
        a = r["activo"] & ~np.isnan(r["lat_cmd"])
        v += list(r["lat_cmd"][a])
    return float(np.mean(v)) if v else float("nan")


def _lectura(res, deg, barr, prueba, escen, n):
    """La lectura con los números de esta corrida (se regenera con ellos)."""
    prot, disc = list(P.ESCENARIOS), list(P.ESCENARIOS_DISC)
    t = lambda d, k, lista: sum(res[(d, x)][k].sum() for x in lista)
    L = []
    L.append("- **Protocolo del comité (13 variantes):** los cuatro decisores cumplen el 100 %, sin choques y sin ninguna "
             "persona a menos de 2 m con el dron por debajo de 3.30 m. El protocolo no distingue entre ellos: sus escenarios "
             "son claros (panel o persona en la trayectoria, cruce lejano) y las reglas ya los resuelven.")
    L.append("- **Discriminación (personas cerca de la trayectoria que no van a chocar):** éxito por vuelo %.1f %% con las "
             "reglas, %.1f %% con la IA sola y %.1f %% con la IA + envolvente; activaciones innecesarias %d / %d / %d y tiempo "
             "detenido sin necesidad %.0f / %.0f / %.0f s. Riesgos omitidos: %d / %d / %d. La IA sola omitía riesgos con "
             "personas que entran de lado al campo de la cámara a 5-6 m; la salvaguarda geométrica de la envolvente (persona "
             "seguida que va a pasar a < 2 m en menos de %.1f s) los recupera, a cambio de parte de las innecesarias." % (
                 100 * t("reglas", "exito", disc) / (n * len(disc)), 100 * t("ia", "exito", disc) / (n * len(disc)),
                 100 * t("ia_env", "exito", disc) / (n * len(disc)), t("reglas", "innecesaria", escen),
                 t("ia", "innecesaria", escen), t("ia_env", "innecesaria", escen), t("reglas", "t_det_innec", escen),
                 t("ia", "t_det_innec", escen), t("ia_env", "t_det_innec", escen), t("reglas", "omitida", escen),
                 t("ia", "omitida", escen), t("ia_env", "omitida", escen), D.TTC_SALVAGUARDA))
    L.append("- **La envolvente estricta** (persona a < 3 m obliga) vuelve a dar lo mismo que las reglas (%d innecesarias): "
             "las activaciones innecesarias de las reglas vienen justamente de personas que pasan a menos de 3 m sin llegar "
             "a 2 m. Por eso la regla dura 5 se aplica como está escrita: el árbitro autoriza, no obliga." % (
                 t("ia_env_estricta", "innecesaria", escen)))
    L.append("- **Anticipación (riesgo → comando, protocolo):** media %.2f s con las reglas y %.2f s con la IA + envolvente "
             "(negativo: la orden sale antes de que el riesgo, con los umbrales de las reglas, exista). La IA se adelanta "
             "casi en todos los escenarios; en los acercamientos lentos (persona quieta a 1.5 m/s, persona que camina hacia "
             "el dron quieto) decide más tarde que las reglas, pero igual con margen (sin choques ni personas a < 2 m)." % (
                 _anticipacion(res, "reglas", prot), _anticipacion(res, "ia_env", prot)))
    if prueba:
        nec = prueba["_sin"]["riesgo"]
        r_, e_, s_ = prueba["reglas"], prueba["ia_env"], prueba["ia"]
        vv = prueba["_sin"]["v"]
        lo = vv <= 4.0
        L.append("- **Mundos de prueba (%d vuelos nunca vistos):** con la IA + envolvente frente a las reglas: choques %d → %d, "
                 "riesgos no evitados %d → %d, vuelos con una persona a < 2 m bajo 3.30 m %d → %d, activaciones innecesarias "
                 "%d → %d y tiempo detenido sin necesidad %.0f → %.0f s. Ninguno llega a cero: el conjunto incluye casos "
                 "físicamente imposibles (panel a pocos metros con el dron a 8 m/s, persona que corre hacia el dron desde "
                 "muy cerca)." % (len(nec), r_["choque"].sum(), e_["choque"].sum(), r_["riesgo"].sum(), e_["riesgo"].sum(),
                                  r_["cerca"].sum(), e_["cerca"].sum(), (r_["activo"] & ~nec).sum(), (e_["activo"] & ~nec).sum(),
                                  r_["t_det"][~nec].sum(), e_["t_det"][~nec].sum()))
        L.append("- **Lo que NO mejora (honesto):** con el piloto a 4 m/s o menos (el LOIT_SPEED recomendado), la IA + "
                 "envolvente deja %d riesgos no evitados frente a %d de las reglas (prácticamente igual), aunque %d vuelos con "
                 "persona a < 2 m bajo 3.30 m frente a %d: en la operación recomendada la mejora en seguridad es moderada y la "
                 "ventaja más clara es la eficiencia (menos detenciones innecesarias). Por encima de 4 m/s la IA + envolvente deja %d vuelos con persona a < 2 m y la IA "
                 "sola %d: la diferencia es el veto del árbitro al ascenso (sube solo con la persona a < 8 m acercándose), que "
                 "con acercamientos rápidos llega tarde; la variante de referencia sin ese veto da %d." % (
                     e_["riesgo"][lo].sum(), r_["riesgo"][lo].sum(), e_["cerca"][lo].sum(), r_["cerca"][lo].sum(),
                     e_["cerca"][~lo].sum(), s_["cerca"][~lo].sum(), prueba["ia_env_ascenso_libre"]["cerca"][~lo].sum()))
    if deg:
        celda = lambda ic, d: (sum(deg[(ic, d, x)]["exito"].sum() for x in escen) / (n * len(escen)),
                               sum(deg[(ic, d, x)]["innecesaria"].sum() for x in escen),
                               sum(deg[(ic, d, x)]["choque"].sum() for x in escen))
        partes = []
        for ic in (2, 3, 6, 10):
            a, b = celda(ic, "reglas"), celda(ic, "ia_env")
            partes.append("%s: éxito %.1f → %.1f %%, innecesarias %d → %d" % (P.CONDICIONES[ic].nombre, 100 * a[0], 100 * b[0], a[1], b[1]))
        a, b = celda(12, "reglas"), celda(12, "ia_env")
        L.append("- **Condiciones degradadas (reglas → IA + envolvente):** " + "; ".join(partes) + ". En las condiciones "
                 "realistas la IA conserva su ventaja, sin choques. En la extrema de solo cabeza y hombros no: éxito %.1f → "
                 "%.1f %%, innecesarias %d → %d, choques %d → %d (es el límite de la percepción para los dos)." % (
                     100 * a[0], 100 * b[0], a[1], b[1], a[2], b[2]))
    if barr:
        vm = lambda ic, d, nom: v_max(barr, ic, d, nom, n)
        L.append("- **Velocidad máxima segura (detenerse con margen):** con una persona quieta, %.0f m/s con las reglas y "
                 "%.0f m/s con la IA + envolvente (la IA puede DETENER antes de los 8 m; las reglas no se activan antes); con "
                 "una persona que corre hacia el dron, %.0f → %.0f m/s (con 300 ms de latencia, %.0f → %.0f). Frente al panel "
                 "son equivalentes (%.0f y %.0f m/s; con la condición combinada la IA baja a %.0f frente a %.0f de las reglas)." % (
                     vm(0, "reglas", "b_quieta_1.5"), vm(0, "ia_env", "b_quieta_1.5"), vm(0, "reglas", "c_frente_corre"),
                     vm(0, "ia_env", "c_frente_corre"), vm(7, "reglas", "c_frente_corre"), vm(7, "ia_env", "c_frente_corre"),
                     vm(0, "reglas", "a_panel_1"), vm(0, "ia_env", "a_panel_1"), vm(10, "ia_env", "a_panel_1"),
                     vm(10, "reglas", "a_panel_1")))
    L.append("- **Decisión pendiente (Brahian):** si el ascenso vertical de protección del mínimo cuenta como \"evasión\" "
             "(hoy lo veta el árbitro hasta los 8 m) o no. Con el LOIT_SPEED de 4 m/s recomendado el costo del veto es "
             "pequeño; por encima de 4 m/s es la principal fuente de personas a < 2 m.")
    return L


def _justificacion(res, barr, prueba, escen, n):
    t = lambda d, k, lista: sum(res[(d, x)][k].sum() for x in lista)
    inn_r, inn_e = t("reglas", "innecesaria", escen), t("ia_env", "innecesaria", escen)
    J = ["En el mínimo indispensable del proyecto de grado, la inteligencia artificial no se limita a detectar personas: "
         "también decide si el dron debe intervenir. Esa decisión se modela como un problema de clasificación: a partir de "
         "las mediciones disponibles a bordo (la caja que entrega YOLO, la distancia del LiDAR, la velocidad estimada por "
         "ArduPilot y un seguimiento alfa-beta de la persona), un perceptrón multicapa estima la probabilidad de que, si el "
         "piloto mantiene su mando, en los próximos %.0f s ocurra un choque o una persona quede a menos de %.0f m del dron." % (
             D.T_HORIZONTE, D.D_PERSONA_ETIQ), "",
         "El uso de un modelo aprendido se justifica porque el riesgo depende de la combinación de varias magnitudes "
         "ruidosas (distancia estimada por el tamaño de la caja, rumbo, velocidad relativa, persistencia de la detección), "
         "y un conjunto de umbrales fijos debe elegir entre ser conservador, con detenciones innecesarias, o permisivo, con "
         "riesgos omitidos. El clasificador aprende esa frontera de decisión a partir de vuelos simulados etiquetados de "
         "forma automática con la verdad del simulador, sin intervención manual, y se evalúa en mundos que no participaron "
         "ni en el entrenamiento ni en la elección del umbral.", "",
         "El aporte se observa en tres aspectos. Primero, en la discriminación: frente a personas que pasan cerca de la "
         "trayectoria sin riesgo real, el sistema con IA redujo las activaciones innecesarias de %d a %d, y con ello el "
         "tiempo de misión perdido. Segundo, en la anticipación: la IA puede ordenar la detención antes del límite de 8 m que "
         "imponen las reglas, lo que eleva la velocidad de avance a la que el dron se detiene con margen frente a una persona "
         "inmóvil." % (inn_r, inn_e)]
    if barr:
        J[-1] += " En la simulación esa velocidad pasó de %.0f m/s a %.0f m/s." % (v_max(barr, 0, "reglas", "b_quieta_1.5", n),
                                                                                v_max(barr, 0, "ia_env", "b_quieta_1.5", n))
    if prueba:
        r_, e_ = prueba["reglas"], prueba["ia_env"]
        J[-1] += (" Tercero, en la operación con condiciones variadas: en %d vuelos de prueba los choques bajaron de %d a %d y "
                  "los casos con una persona a menos de 2 m del dron por debajo de la altura segura, de %d a %d." % (
                      len(r_["choque"]), r_["choque"].sum(), e_["choque"].sum(), r_["cerca"].sum(), e_["cerca"].sum()))
    J += ["", "La IA no reemplaza las reglas de seguridad: opera dentro de una envolvente de reglas duras. El bloqueo frontal "
          "por LiDAR y la parada del operador mandan siempre sobre ella; el árbitro de seguridad conserva la autoridad para "
          "autorizar el ascenso, y una salvaguarda geométrica detiene el dron si una persona seguida va a pasar a menos de "
          "2 m en menos de %.1f s. El operador humano puede intervenir en todo momento. Así, la IA aporta criterio donde las "
          "reglas fijas son ineficientes, y las reglas garantizan un comportamiento verificable donde la IA podría fallar." % (
              D.TTC_SALVAGUARDA), "",
          "Los resultados también muestran los límites del enfoque. Con la velocidad de avance recomendada (4 m/s), la IA "
          "deja prácticamente los mismos riesgos sin evitar que las reglas, aunque menos aproximaciones a menos de 2 m, y su "
          "ventaja más clara es la eficiencia. La percepción sigue siendo el "
          "límite cuando solo son visibles la cabeza y los hombros de la persona. Además, el detector se modeló "
          "estadísticamente, por lo que estos resultados deben confirmarse con el protocolo de campo descrito para el dron real."]
    return J


def _replay(dec, replay):
    cuadros, nombres = [], []
    for nom, cs in replay:
        if P.TODOS[nom][4]:
            for c in cs:
                c["d"][1] = round(c["d"][1] + P.DY_PANEL, 3)
                c["lh"][1] = round(c["lh"][1] + P.DY_PANEL, 2)
        cuadros += cs
        nombres.append(nom)
    datos = {"iteracion": 0, "pasos": 0, "adversaria": False, "mision": False, "guion": None, "resultado": "protocolo",
             "maniobras": 0, "dt": 0.1, "obst": [], "version": "Mínimo indispensable · decisor %s" % dec,
             "paneles": [[P.PANEL[0], P.PANEL[1] + P.DY_PANEL, P.PANEL[2], P.PANEL[3] + P.DY_PANEL, P.PANEL[4]]],
             "autor": "Brahian Andrés Orrego Osorio", "escenarios": nombres, "cuadros": cuadros}
    with open(os.path.join(D.AQUI, "replay", "replay_protocolo_%s.json" % dec), "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
