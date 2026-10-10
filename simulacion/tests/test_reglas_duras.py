# -*- coding: utf-8 -*-
"""Reglas duras del sistema (CLAUDE.md). Si una de estas pruebas falla, el cambio NO se acepta sin que Brahian lo
decida: no se arregla relajando la prueba."""
import unittest

import numpy as np

import control
import entorno as E

EPS = 1e-6


def acciones_aleatorias(rng, n, sesgo_gimbal_abajo=0.0):
    a = rng.integers(0, len(E.CLASES), n)
    return np.where(rng.random(n) < sesgo_gimbal_abajo, 9, a)


class TestConstantes(unittest.TestCase):

    def test_limites_del_gimbal(self):
        self.assertEqual(E.GIMBAL_MIN, -45.0)   # BaseCam física: nunca por debajo de -45° (D-014)
        self.assertEqual(E.GIMBAL_MAX, 15.0)
        for ang in (E.GIMBAL_NADIR, E.GIMBAL_TACTICO):
            self.assertGreaterEqual(ang, E.GIMBAL_MIN)

    def test_geocerca(self):
        self.assertEqual(E.ARENA, 25.0)
        self.assertLess(E.R_GEOCERCA, 0.0)

    def test_busqueda_tras_la_perdida(self):
        # regla 3 (D-015, v11-hibrido): la búsqueda tras perder el objetivo es determinista (PERDIDA_IA = False)
        self.assertFalse(E.PERDIDA_IA)
        self.assertEqual(E.T_BUSQUEDA_IA, 60.0)

    def test_arbitro(self):
        self.assertEqual(E.D_CRITICA, 3.0)
        self.assertEqual(E.D_AMENAZA, 8.0)
        self.assertEqual(E.DIST_PROTECCION_FRONTAL, 3.0)


class TestDinamica(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Una sola corrida de 64 partidas x 60 s con acciones al azar (y muchas GIMBAL_ABAJO para forzar el límite),
        registrando lo que revisan las pruebas."""
        rng = np.random.default_rng(0)
        env = E.EntornoDronPersona(64, semilla=0)
        ap_p = np.full(env.n, E.N_ACC_PERSONA - 1)
        cls.g_min, cls.g_max = 99.0, -99.0
        cls.transiciones = []          # (modo antes, modo después, candidato antes) en las partidas que siguen
        cls.inicia_sin_amenaza = 0
        for _ in range(600):
            modo0, cand0 = env.modo.copy(), env.cand.copy()
            acc = acciones_aleatorias(rng, env.n, sesgo_gimbal_abajo=0.4)
            ap = np.where(rng.random(env.n) < 0.5, rng.integers(0, E.N_ACC_PERSONA, env.n), ap_p)
            _, _, done, info = env.step(acc, ap, auto_reset=False)
            cls.inicia_sin_amenaza += int((info["inicia"] & ~(env.amenaza | info["reflejo"])).sum())
            for arr in (env.cam_pitch, env.gimbal, env.gimbal_cmd):
                cls.g_min, cls.g_max = min(cls.g_min, arr.min()), max(cls.g_max, arr.max())
            for i in np.where(~done & (env.modo != modo0))[0]:
                cls.transiciones.append((modo0[i], env.modo[i], cand0[i]))
            env.reset(done)

    def test_gimbal_dentro_de_limites(self):
        self.assertGreaterEqual(self.g_min, E.GIMBAL_MIN - EPS)
        self.assertLessEqual(self.g_max, E.GIMBAL_MAX + EPS)

    def test_gimbal_basecam_recorta_comandos_extremos(self):
        gb = control.GimbalBaseCam(4)
        for consigna, d_chasis in ((-120.0, -10.0), (60.0, 10.0)):
            for _ in range(100):
                ang = gb.paso(np.full(4, consigna), np.full(4, d_chasis), E.DT)
                self.assertTrue(np.all(ang >= E.GIMBAL_MIN - EPS) and np.all(ang <= E.GIMBAL_MAX + EPS))

    def test_humano_en_el_lazo(self):
        a_fijado = [(a, c) for a, b, c in self.transiciones if b == E.FIJADO]
        self.assertTrue(any(a == E.VERIFICAR for a, _ in a_fijado), "la prueba no vio ningún lock-on")
        for antes, cand in a_fijado:
            # solo el clic del operador (VERIFICAR, y sobre el sospechoso) o una re-identificación del MISMO objetivo
            self.assertIn(antes, (E.VERIFICAR, E.INVESTIGAR, E.ASOMO, E.VENTAJA_ALTURA, E.PREDECIR, E.BUSQUEDA_IA))
            if antes == E.VERIFICAR:
                self.assertEqual(cand, 0, "se fijó a alguien que no es el sospechoso")

    def test_arbitro_solo_ante_amenaza_real(self):
        self.assertEqual(self.inicia_sin_amenaza, 0)

    def test_geocerca_termina_la_partida(self):
        env = E.EntornoDronPersona(4, semilla=1)
        env.dx[:] = E.ARENA + 0.5
        _, _, done, info = env.step(np.zeros(4, int), np.full(4, E.N_ACC_PERSONA - 1), auto_reset=False)
        self.assertTrue(info["fuera"].all())
        self.assertTrue(done.all())


if __name__ == "__main__":
    unittest.main()
