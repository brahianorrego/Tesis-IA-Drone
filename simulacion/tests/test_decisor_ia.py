# -*- coding: utf-8 -*-
"""Pruebas del decisor IA del mínimo indispensable (fase G): entradas, exportación a la Jetson, envolvente de reglas duras."""
import json
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from minimo_tesis import decisor_ia as D  # noqa: E402
from minimo_tesis import sistema as M  # noqa: E402


def modelo_chico(umbral=0.5):
    """Un MLP chico entrenado en pocos mundos (la prueba no depende del modelo grande)."""
    from sklearn.neural_network import MLPClassifier
    X, y, _ = D.generar(range(3), n=16, dur=12.0)
    media, desv = X.mean(0), X.std(0) + 1e-6
    clf = MLPClassifier(hidden_layer_sizes=(8,), max_iter=30, random_state=0).fit((X - media) / desv, y)
    return D.Modelo(clf, media, desv, umbral, 1), X, y


def medida(n, lid=30.0, det=False, d=50.0, rumbo=0.0, v_av=0.0, dz=2.3):
    return dict(det=np.full(n, det), d=np.full(n, d), rumbo=np.full(n, rumbo), frac=np.ones(n), lid=np.full(n, lid),
                v_av=np.full(n, v_av), dz=np.full(n, dz), psi=np.zeros(n), alto=np.full(n, 0.3 if det else 0.0),
                ancho=np.full(n, 0.05 if det else 0.0), conf=np.full(n, 0.8 if det else 0.0))


class TestDecisorIA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modelo, cls.X, cls.y = modelo_chico()

    def test_entradas_solo_de_la_jetson(self):
        self.assertEqual(self.X.shape[1], len(D.CARACTERISTICAS))
        self.assertTrue(np.isfinite(self.X).all())
        # las etiquetas salen solas de la verdad del simulador y hay de las dos clases
        self.assertTrue(0.0 < self.y.mean() < 1.0)

    def test_json_igual_que_sklearn(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.modelo.guardar(tmp)
            with open(os.path.join(tmp, "decision.json"), encoding="utf-8") as fh:
                pesos = json.load(fh)
            otro = D.Modelo.cargar(tmp)
        self.assertEqual(pesos["entradas"], D.CARACTERISTICAS)
        p1 = self.modelo.proba(self.X[:500])
        p2 = D.predecir_json(pesos, self.X[:500])
        self.assertLess(np.abs(p1 - p2).max(), 1e-5)                 # NumPy puro = scikit-learn (float32 vs float64)
        self.assertLess(np.abs(otro.proba(self.X[:500]) - p1).max(), 1e-12)

    def test_envolvente_manda_siempre(self):
        nunca = D.Modelo(self.modelo.clf, self.modelo.media, self.modelo.desv, 1.1, 1)   # la IA nunca pide detenerse
        no = np.zeros(1, bool)
        # LiDAR a 2 m avanzando: con envolvente se detiene y sube aunque la IA diga CONTINUAR
        con = D.DecisorIA(1, nunca, con_envolvente=True)
        vx, vy, vz, nuevo = con.actualizar(medida(1, lid=2.0, v_av=2.0), np.full(1, 2.0), no, no, no, np.full(1, 2.3))
        self.assertTrue(nuevo[0] and vx[0] == 0.0 and vz[0] > 0.0)
        # la IA sola no tiene envolvente
        sola = D.DecisorIA(1, nunca, con_envolvente=False)
        vx, _, _, nuevo = sola.actualizar(medida(1, lid=2.0, v_av=2.0), np.full(1, 2.0), no, no, no, np.full(1, 2.3))
        self.assertFalse(nuevo[0])
        self.assertAlmostEqual(vx[0], 2.0)

    def test_arbitro_autoriza_el_ascenso(self):
        siempre = D.Modelo(self.modelo.clf, self.modelo.media, self.modelo.desv, -0.1, 1)  # la IA siempre pide detenerse
        no = np.zeros(1, bool)
        con = D.DecisorIA(1, siempre, con_envolvente=True)
        # persona quieta a 12 m al frente: la IA puede DETENER, pero el árbitro (< 8 m acercándose) no autoriza subir
        for _ in range(3):
            vx, vy, vz, _ = con.actualizar(medida(1, det=True, d=12.0, v_av=0.0), np.zeros(1), no, no, no, np.full(1, 2.3))
        self.assertEqual(vx[0], 0.0)
        self.assertLessEqual(vz[0], 0.0 + 1e-9)
        # sin envolvente sube de una vez
        sola = D.DecisorIA(1, siempre, con_envolvente=False)
        _, _, vz, _ = sola.actualizar(medida(1, det=True, d=12.0), np.zeros(1), no, no, no, np.full(1, 2.3))
        self.assertGreater(vz[0], 0.0)

    def test_operador_manda(self):
        siempre = D.Modelo(self.modelo.clf, self.modelo.media, self.modelo.desv, -0.1, 1)
        si, no = np.ones(1, bool), np.zeros(1, bool)
        d = D.DecisorIA(1, siempre, con_envolvente=True)
        vx, _, _, _ = d.actualizar(medida(1), np.full(1, 1.5), no, si, no, np.full(1, 2.3))   # ANULAR
        self.assertAlmostEqual(vx[0], 1.5)
        d.actualizar(medida(1), np.full(1, 1.5), no, no, si, np.full(1, 2.3))                 # REANUDAR libera
        self.assertFalse(d.interviene[0])

    def test_misma_interfaz_que_las_reglas(self):
        for nombre in ("actualizar",):
            self.assertTrue(hasattr(D.DecisorIA, nombre) and hasattr(M.SistemaMinimo, nombre))


if __name__ == "__main__":
    unittest.main()
