# -*- coding: utf-8 -*-
"""Las herramientas de evaluación arman bien sus escenarios y resúmenes."""
import os
import sys
import unittest

import numpy as np

import entorno as E

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "herramientas"))
import evaluar_politica as V  # noqa: E402
import resumir_metricas as R  # noqa: E402


class PoliticaQuieta(object):
    def predict(self, obs, deterministic=True):
        return np.zeros(len(obs), int), None


class TestEvaluarPolitica(unittest.TestCase):

    def test_escenarios_arrancan_con_el_ladron_fijado(self):
        for nombre, esc in V.ESCENARIOS.items():
            env = E.EntornoDronPersona(16, semilla=0)
            V.preparar(env, esc, np.random.default_rng(0))
            self.assertTrue((env.modo == E.FIJADO).all(), nombre)
            self.assertGreaterEqual(env.info_sensor["lock"].mean(), 0.7, nombre)
            self.assertFalse(env.activa[:, 1:].any(), nombre)
            self.assertTrue((np.abs(env.px[:, 0]) < E.ARENA).all(), nombre)

    def test_correr_escenario(self):
        res = V.correr_escenario(PoliticaQuieta(), "tras_muro", 4, 0, 5.0, 0.1)
        fila = V.resumir(res)
        self.assertAlmostEqual(sum(fila[k] for k in V.RESULTADOS), 1.0)
        self.assertGreaterEqual(fila["g_min"], E.GIMBAL_MIN - 1e-6)
        self.assertTrue(all(len(v) == 4 for k, v in res.items() if k != "acciones"))


class TestResumirMetricas(unittest.TestCase):

    def test_ventana(self):
        ms = [{"it": i, "pasos": 65536 * i, "_dpasos": 65536, "nivel": 0.1,
               "adv": {"n": 80, "cumplida": 0.5, "perdido": 0.3, "alcanzado": 0.1, "peaton": None, "panel": 0.0,
                       "fuera": 0.0, "vista": 0.2, "recompensa": -5.0, "perdidas": 2.0, "recuperaciones": 1.0,
                       "redescubre": 1.0, "maniobras": 1.0, "no_encontrado": 0.0},
               "control": {"jitter": 0.06, "esfuerzo": 0.04, "total": 0.1, "seg_mando": 5000.0},
               "dron": {"entropia": 1.5}, "acciones": [0.1] * 10, "acciones_busqueda": [0.1] * 10} for i in range(1, 11)]
        v = R.ventana(ms)
        self.assertAlmostEqual(v["cumplida"], 0.5)
        self.assertIsNone(v["peaton"])
        self.assertAlmostEqual(v["dur"], 65536 / 80 * E.DT)
        self.assertAlmostEqual(v["ctrl_ep"], 0.1 * 50000 / 800)


if __name__ == "__main__":
    unittest.main()
