# -*- coding: utf-8 -*-
"""
Entrenamiento de la IA #2 (perceptrón multicapa de scikit-learn). Se ejecuta en el PC.

    python entrenar_mlp.py datos/dataset_*.csv

Genera:
    decision.pkl            modelo (pipeline escalador + MLP) para la Jetson
    decision_pesos.json     los mismos pesos en JSON (respaldo sin pickle)
    resultados_entrenamiento/  reporte.txt, matriz_confusion.png, curva_aprendizaje.png

IMPORTANTE - versiones: un .pkl solo carga bien con la MISMA versión de
scikit-learn (y numpy 1.x vs 2.x) con que se creó. La Jetson con Ubuntu 20.04
usa Python 3.8, cuyo último scikit-learn es 1.3.2. Instale en el PC
scikit-learn==1.3.2 y numpy<2 (ver requirements_pc.txt). Si aun así falla,
el script de vuelo usa decision_pesos.json automáticamente.

Nota metodológica: filas consecutivas de una misma toma son casi idénticas.
Si se reparten al azar entre entrenamiento y prueba, la exactitud sale inflada.
Por eso la prueba se hace con TOMAS completas que el modelo no vio.
"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd

import config as C
from comun import exportar_pesos_json, MLPNumpy


def cargar(patrones):
    rutas = []
    for p in patrones:
        rutas.extend(sorted(glob.glob(p)) or [p])
    tablas = []
    for r in rutas:
        if not os.path.isfile(r):
            sys.exit("No existe %s" % r)
        df = pd.read_csv(r)
        df["archivo"] = os.path.basename(r)
        tablas.append(df)
        print("  %-40s %6d filas" % (os.path.basename(r), len(df)))
    return pd.concat(tablas, ignore_index=True), rutas


def dividir(y, grupos, prueba, semilla):
    """Divide por tomas completas; si hay pocas tomas, cae a división estratificada."""
    from sklearn.model_selection import GroupShuffleSplit, train_test_split
    clases = set(np.unique(y))
    if len(np.unique(grupos)) >= 5:
        for s in range(semilla, semilla + 200):
            gss = GroupShuffleSplit(n_splits=1, test_size=prueba, random_state=s)
            tr, te = next(gss.split(np.zeros(len(y)), y, grupos))
            if set(np.unique(y[tr])) == clases and len(np.unique(y[te])) >= min(2, len(clases)):
                return tr, te, "por tomas (GroupShuffleSplit, semilla %d)" % s
    print("\n  AVISO: menos de 5 tomas útiles o clases mal repartidas entre tomas.\n"
          "  Se usa división estratificada al azar; la exactitud de prueba saldrá OPTIMISTA.\n"
          "  Grabe varias tomas cortas (pulsando R) para una evaluación honesta.\n")
    idx = np.arange(len(y))
    tr, te = train_test_split(idx, test_size=prueba, random_state=semilla, stratify=y)
    return tr, te, "estratificada al azar"


def crear_modelo(capas, alpha, semilla, early_stopping):
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    return Pipeline([
        ("escalador", StandardScaler()),
        ("mlp", MLPClassifier(hidden_layer_sizes=capas, activation="relu", solver="adam",
                              alpha=alpha, learning_rate_init=1e-3, max_iter=3000,
                              early_stopping=early_stopping, validation_fraction=0.15,
                              n_iter_no_change=40, random_state=semilla)),
    ])


def graficar(cm, nombres, mlp, carpeta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    tinta, tinta2, rejilla, serie, fondo = "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6", "#ffffff"
    azul = LinearSegmentedColormap.from_list(
        "azul", ["#fcfcfb", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
    plt.rcParams.update({"font.size": 10, "text.color": tinta, "axes.labelcolor": tinta2,
                         "xtick.color": tinta2, "ytick.color": tinta2})

    # ---- Matriz de confusión (conteos + % por fila) ----
    filas = cm.sum(axis=1, keepdims=True).astype(float)
    frac = np.divide(cm, filas, out=np.zeros_like(cm, dtype=float), where=filas > 0)
    n = len(nombres)
    fig, ax = plt.subplots(figsize=(1.35 * n + 2.2, 1.15 * n + 1.6), dpi=200, facecolor=fondo)
    ax.pcolormesh(frac, cmap=azul, vmin=0, vmax=1, edgecolors=fondo, linewidth=2)
    for i in range(n):
        for j in range(n):
            color = "#ffffff" if frac[i, j] > 0.55 else tinta
            ax.text(j + 0.5, i + 0.5, "%d\n%.0f %%" % (cm[i, j], 100 * frac[i, j]),
                    ha="center", va="center", color=color, fontsize=9)
    ax.set_xticks(np.arange(n) + 0.5)
    ax.set_yticks(np.arange(n) + 0.5)
    ax.set_xticklabels(nombres, rotation=20, ha="right")
    ax.set_yticklabels(nombres)
    ax.invert_yaxis()
    ax.set_xlabel("Clase predicha")
    ax.set_ylabel("Clase real")
    ax.set_title("Matriz de confusión (conjunto de prueba)", loc="left", color=tinta)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(carpeta, "matriz_confusion.png"), facecolor=fondo)
    plt.close(fig)

    # ---- Curva de aprendizaje: dos paneles, cada uno con su propia escala ----
    paneles = [("Pérdida de entrenamiento", mlp.loss_curve_, "%.3f")]
    if getattr(mlp, "validation_scores_", None) is not None:
        paneles.append(("Exactitud de validación interna", mlp.validation_scores_, "%.2f"))
    fig, ejes = plt.subplots(1, len(paneles), figsize=(5.2 * len(paneles), 3.4), dpi=200, facecolor=fondo)
    ejes = np.atleast_1d(ejes)
    for ax, (titulo, datos, fmt) in zip(ejes, paneles):
        x = np.arange(1, len(datos) + 1)
        ax.plot(x, datos, color=serie, linewidth=2)
        ax.annotate(fmt % datos[-1], (x[-1], datos[-1]), xytext=(4, 0), textcoords="offset points",
                    va="center", color=tinta, fontsize=9)
        ax.set_title(titulo, loc="left", color=tinta)
        ax.set_xlabel("Época")
        ax.grid(axis="y", color=rejilla, linewidth=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(rejilla)
    fig.tight_layout()
    fig.savefig(os.path.join(carpeta, "curva_aprendizaje.png"), facecolor=fondo)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Entrena la IA #2 y exporta decision.pkl")
    ap.add_argument("csv", nargs="+", help="uno o varios CSV (acepta comodines: datos/*.csv)")
    ap.add_argument("--salida", default=C.MODELO_PKL)
    ap.add_argument("--capas", default="16,16", help="neuronas por capa oculta, ej. 16,16")
    ap.add_argument("--alpha", type=float, default=1e-3, help="regularización L2")
    ap.add_argument("--prueba", type=float, default=0.25, help="fracción para prueba")
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--incluir-sin-persona", action="store_true",
                    help="usar también filas sin persona (en vuelo esas no pasan por el MLP)")
    ap.add_argument("--solo-lidar", action="store_true",
                    help="usar solo filas donde la distancia vino del LiDAR")
    ap.add_argument("--resultados", default="resultados_entrenamiento")
    a = ap.parse_args()

    import sklearn
    from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                                 classification_report, confusion_matrix)
    import joblib

    capas = tuple(int(c) for c in a.capas.split(",") if c.strip())
    print("scikit-learn %s | numpy %s | Python %s" % (sklearn.__version__, np.__version__, sys.version.split()[0]))
    print("Cargando:")
    df, rutas = cargar(a.csv)
    n0 = len(df)

    # ---------------- Limpieza ----------------
    df = df[df["etiqueta"].notna()]
    if not a.incluir_sin_persona:
        df = df[df["persona"] == 1]
    if a.solo_lidar:
        df = df[df["fuente_distancia"] == "lidar"]
    faltantes = df[C.FEATURES].isna().any(axis=1)
    if faltantes.any():
        print("  %d filas descartadas por datos faltantes en %s" % (faltantes.sum(), C.FEATURES))
    df = df[~faltantes].copy()
    df["etiqueta"] = df["etiqueta"].astype(int)
    df["grupo"] = df["archivo"] + "#" + df["toma"].astype(str)
    print("Filas útiles: %d de %d  |  tomas: %d" % (len(df), n0, df["grupo"].nunique()))
    if len(df) < 50:
        sys.exit("Muy pocas filas para entrenar.")

    print("\nDistribución de clases:")
    conteo = df["etiqueta"].value_counts().sort_index()
    for c, k in conteo.items():
        aviso = "  <- pocas muestras" if k < 50 else ""
        print("  %d %-17s %5d (%4.1f %%)%s" % (c, C.CLASES.get(c, "?"), k, 100.0 * k / len(df), aviso))
    for c in C.CLASES:
        if c not in conteo.index:
            print("  AVISO: no hay ejemplos de la clase %d %s; el modelo nunca la predecirá" % (c, C.CLASES[c]))

    X = df[C.FEATURES].values.astype(float)
    y = df["etiqueta"].values
    grupos = df["grupo"].values
    early = int(conteo.min()) >= 10

    # ---------------- Evaluación honesta ----------------
    tr, te, metodo = dividir(y, grupos, a.prueba, a.semilla)
    print("\nDivisión %s: %d entrenamiento / %d prueba" % (metodo, len(tr), len(te)))
    modelo_eval = crear_modelo(capas, a.alpha, a.semilla, early)
    modelo_eval.fit(X[tr], y[tr])
    pred = modelo_eval.predict(X[te])
    etiquetas = sorted(np.unique(y))
    nombres = [C.CLASES.get(c, str(c)) for c in etiquetas]
    acc = accuracy_score(y[te], pred)
    bacc = balanced_accuracy_score(y[te], pred)
    cm = confusion_matrix(y[te], pred, labels=etiquetas)
    reporte = classification_report(y[te], pred, labels=etiquetas, target_names=nombres,
                                     zero_division=0, digits=3)
    print("\nExactitud: %.3f   Exactitud balanceada: %.3f\n" % (acc, bacc))
    print(reporte)
    print("Matriz de confusión (filas = real, columnas = predicha):")
    print(pd.DataFrame(cm, index=nombres, columns=nombres).to_string())

    # ---------------- Modelo final con todos los datos ----------------
    modelo = crear_modelo(capas, a.alpha, a.semilla, early)
    modelo.fit(X, y)
    paquete = {
        "modelo": modelo,
        "features": list(C.FEATURES),
        "clases": dict(C.CLASES),
        "version_sklearn": sklearn.__version__,
        "version_numpy": np.__version__,
        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
        "archivos": [os.path.basename(r) for r in rutas],
        "n_muestras": int(len(df)),
        "capas": capas,
        "metricas_prueba": {"exactitud": float(acc), "exactitud_balanceada": float(bacc),
                            "division": metodo},
    }
    joblib.dump(paquete, a.salida)
    ruta_json = os.path.join(os.path.dirname(os.path.abspath(a.salida)), os.path.basename(C.MODELO_JSON))
    exportar_pesos_json(modelo, C.FEATURES, C.CLASES, ruta_json)

    # El respaldo JSON debe dar exactamente lo mismo que scikit-learn
    with open(ruta_json) as f:
        dif = np.abs(MLPNumpy(json.load(f)).predict_proba(X) - modelo.predict_proba(X)).max()
    if dif > 1e-6:
        sys.exit("ERROR: los pesos JSON no reproducen el modelo (dif %.2e)" % dif)

    # ---------------- Resultados para el documento ----------------
    if not os.path.isdir(a.resultados):
        os.makedirs(a.resultados)
    graficar(cm, nombres, modelo_eval.named_steps["mlp"], a.resultados)
    with open(os.path.join(a.resultados, "reporte.txt"), "w", encoding="utf-8") as f:
        f.write("Entrenamiento IA #2 - %s\n" % paquete["fecha"])
        f.write("Archivos: %s\n" % ", ".join(paquete["archivos"]))
        f.write("Entradas: %s\n" % C.FEATURES)
        f.write("Arquitectura: %d -> %s -> %d (ReLU, Adam, alpha=%g)\n"
                % (len(C.FEATURES), " -> ".join(str(c) for c in capas), len(etiquetas), a.alpha))
        f.write("Filas útiles: %d | tomas: %d | división: %s\n"
                % (len(df), df["grupo"].nunique(), metodo))
        f.write("scikit-learn %s | numpy %s\n\n" % (sklearn.__version__, np.__version__))
        f.write("Exactitud %.3f | exactitud balanceada %.3f\n\n" % (acc, bacc))
        f.write(reporte + "\n")
        f.write(pd.DataFrame(cm, index=nombres, columns=nombres).to_string() + "\n")

    print("\nModelo guardado: %s  (+ %s, dif JSON %.1e)" % (a.salida, ruta_json, dif))
    print("Gráficas y reporte en %s/" % a.resultados)
    print("Copie decision.pkl y decision_pesos.json a la Jetson (misma carpeta que vuelo_evasion.py).")


if __name__ == "__main__":
    main()
