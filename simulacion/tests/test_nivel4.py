# -*- coding: utf-8 -*-
"""Ajustes del nivel 4 (diagnóstico del supervisor, aprobados por Brahian): C1 pausa de 4 s del contador, C2 tope terminal
y éxito por tiempo restante, C3 métricas de custodia y de búsqueda."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import entorno as E  # noqa: E402
import entrenar_master as M  # noqa: E402


def avanzar(env, vista, modo, pasos):
    """Pasos del contador con el ladrón a la vista o no, en el estado `modo`."""
    for _ in range(pasos):
        env.modo[:] = modo
        env._contador(np.full(env.n, vista), np.ones(env.n, bool))


class TestC1Pausa(unittest.TestCase):
    def test_re_adquirido_antes_de_4_s_el_contador_se_pausa(self):
        env = E.EntornoDronPersona(1, semilla=0, nivel=4)
        avanzar(env, True, E.FIJADO, 100)                         # 10 s a la vista
        self.assertAlmostEqual(env.t_cont[0], 10.0, places=6)
        avanzar(env, False, E.INVESTIGAR, 35)                     # 3.5 s buscándolo: se pausa, no se borra
        self.assertAlmostEqual(env.t_cont[0], 10.0, places=6)
        avanzar(env, True, E.FIJADO, 10)                          # lo re-adquiere: sigue sumando desde 10 s
        self.assertAlmostEqual(env.t_cont[0], 11.0, places=6)

    def test_pasados_4_s_se_reinicia_como_antes(self):
        env = E.EntornoDronPersona(1, semilla=0, nivel=4)
        avanzar(env, True, E.FIJADO, 100)
        avanzar(env, False, E.ASOMO, int(E.T_PAUSA_REID / E.DT) + 2)
        self.assertEqual(env.t_cont[0], 0.0)
        self.assertAlmostEqual(env.racha_max[0], 10.0, places=6)     # C3: la mejor racha queda registrada

    def test_pausa_es_de_4_s(self):
        self.assertEqual(E.T_PAUSA_REID, 4.0)                    # decisión de Brahian (no 8)


class TestC2Recompensa(unittest.TestCase):
    def test_exito_vale_mas_cuanto_antes(self):
        self.assertEqual(E.R_EXITO_RESTANTE, 0.25)
        self.assertEqual(E.R_TOPE, -5.0)

    def test_tope_terminal_y_cobrado(self):
        env = E.EntornoDronPersona(2, semilla=1, nivel=0)
        env.t = E.PASOS_EPISODIO - 1                               # el próximo paso llega al tope
        env.t_cont[:] = 0.0
        _, _, done, info = env.step(np.zeros(2, int), np.full(2, E.N_ACC_PERSONA - 1), auto_reset=False)
        sin_falla = ~(info["choque"] | info["fuera"] | info["panel"] | info["perdido"] | info["no_encontrado"] | info["exito"])
        self.assertTrue(done.all())
        self.assertTrue((info["tope"] == sin_falla).all())
        i_f = E.R_COMP.index("fallas")
        self.assertTrue((info["r_comp"][sin_falla, i_f] <= E.R_TOPE + 1e-9).all())

    def test_master_no_trunca_el_tope(self):
        with open(M.__file__, encoding="utf-8") as fh:
            txt = fh.read()
        self.assertIn('infos[i]["TimeLimit.truncated"] = False', txt)


class TestC3Metricas(unittest.TestCase):
    def test_info_y_resumen_por_nivel(self):
        env = E.EntornoDronPersona(4, semilla=2, nivel=4)
        for _ in range(50):
            _, _, _, info = env.step(np.zeros(4, int), np.full(4, E.N_ACC_PERSONA - 1), auto_reset=False)
        for k in ("tope", "racha", "t_vista_ac", "t_rinde", "t_readq_sum", "n_readq", "t_busq_est", "readq_est"):
            self.assertIn(k, info)
        xs = [dict(rinde=bool(i % 2), tiempo=not (i % 2), vista=60.0 + 10 * i, racha=20.0, trinde=43.0, readq_s=5.0,
                   busq=[0.0] * len(E.NOMBRE_ESTADO), readq_est=[0] * len(E.NOMBRE_ESTADO)) for i in range(4)]
        r = M.resumen_nivel(xs)
        self.assertEqual(r["custodia_60"], 1.0)
        self.assertEqual(r["custodia_90"], 0.5)                   # vista ≥ 90 s (i = 3) o se rindió (i = 1, 3): 2 de 4
        self.assertIn("CUSTODIA", M.texto_resumen_nivel(E.N_NIVELES - 1, r).split("|")[0])   # nivel 4: la custodia primero


if __name__ == "__main__":
    unittest.main()
