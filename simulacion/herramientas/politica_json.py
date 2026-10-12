# -*- coding: utf-8 -*-
"""
La política exportada para la Jetson (modelos/dron_politica.json: las capas del actor, tanh) como política de referencia
SIN REENTRENAR, para medir los cambios de la V16 en la nube, donde no están los modelos .zip de SB3.

Si la V16 agrega entradas nuevas a la observación (OBS_DRON crece), las columnas que faltan se completan con ceros: la red
de la V15 las ignora y se comporta igual que antes (es la misma idea del arranque de la V16 desde la V15).

Uso:  from politica_json import PoliticaJSON
      pol = PoliticaJSON("modelos/dron_politica.json")
      acc, _ = pol.predict(obs, deterministic=True)        # misma interfaz que un modelo SB3
"""
import json

import numpy as np


class PoliticaJSON(object):

    def __init__(self, ruta, n_obs=None):
        d = json.load(open(ruta, encoding="utf-8"))
        self.capas = [(np.asarray(c["W"], np.float64), np.asarray(c["b"], np.float64)) for c in d["capas"]]
        self.pasos = d.get("pasos")
        n_in = self.capas[0][0].shape[1]
        if n_obs is not None and n_obs > n_in:          # entradas nuevas: pesos en cero (no cambian la salida)
            W, b = self.capas[0]
            self.capas[0] = (np.concatenate([W, np.zeros((W.shape[0], n_obs - n_in))], 1), b)
        self.n_in = self.capas[0][0].shape[1]

    def logits(self, obs):
        x = np.asarray(obs, np.float64)[:, :self.n_in]
        for k, (W, b) in enumerate(self.capas):
            x = x @ W.T + b
            if k < len(self.capas) - 1:
                x = np.tanh(x)
        return x

    def predict(self, obs, deterministic=True, rng=None):
        lg = self.logits(obs)
        if deterministic:
            return np.argmax(lg, 1), None
        p = np.exp(lg - lg.max(1, keepdims=True))
        p /= p.sum(1, keepdims=True)
        rng = rng or np.random.default_rng()
        return (p.cumsum(1) > rng.random((len(p), 1))).argmax(1), None
