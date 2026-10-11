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
        self.assertEqual(E.T_MISION_PERDIDA, 90.0)          # V12: MISIÓN_PERDIDA tras 90 s sin recuperarlo

    def test_formula_del_punto_ciego(self):
        # V12: d = h / tan(45° + VFOV/2) + margen (el gimbal no baja de -45°, así que debajo hay una zona ciega)
        for h in (2.3, 3.0, 5.5):
            esperado = h / np.tan(np.radians(45.0 + E.VFOV / 2.0)) + E.MARGEN_CIEGO
            self.assertAlmostEqual(float(E.d_punto_ciego(h)), esperado, places=9)
        self.assertAlmostEqual(-E.GIMBAL_MIN + E.VFOV / 2.0, 59.85, places=6)

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
        cls.ia_fuera_de_persecucion = 0     # pasos con la red al mando fuera de FIJADO (PERDIDA_IA = False: debe ser 0)
        cls.modos_vistos = set()
        cls.gmb_min_info = 99.0
        cls.reconf_a_fijado = []       # V15: (t en RECONFIRMAR, tiempo de respuesta del operador, persona seguida después)
        for _ in range(600):
            modo0, cand0 = env.modo.copy(), env.cand.copy()
            tm0, tr0 = env.t_modo.copy(), env.t_resp.copy()
            acc = acciones_aleatorias(rng, env.n, sesgo_gimbal_abajo=0.4)
            ap = np.where(rng.random(env.n) < 0.5, rng.integers(0, E.N_ACC_PERSONA, env.n), ap_p)
            _, _, done, info = env.step(acc, ap, auto_reset=False)
            cls.inicia_sin_amenaza += int((info["inicia"] & ~(env.amenaza | info["reflejo"])).sum())
            cls.ia_fuera_de_persecucion += int((info["al_mando"] & (modo0 != E.FIJADO)).sum())
            cls.modos_vistos |= set(np.unique(env.modo).tolist())
            cls.gmb_min_info = min(cls.gmb_min_info, float(info["gmb_min"].min()))
            for arr in (env.cam_pitch, env.gimbal, env.gimbal_cmd):
                cls.g_min, cls.g_max = min(cls.g_min, arr.min()), max(cls.g_max, arr.max())
            for i in np.where(~done & (env.modo != modo0))[0]:
                cls.transiciones.append((modo0[i], env.modo[i], cand0[i]))
                if modo0[i] == E.RECONFIRMAR and env.modo[i] == E.FIJADO:
                    cls.reconf_a_fijado.append((tm0[i] + E.DT, tr0[i], env.trk[i]))
            env.reset(done)

    def test_gimbal_dentro_de_limites(self):
        self.assertGreaterEqual(self.g_min, E.GIMBAL_MIN - EPS)
        self.assertLessEqual(self.g_max, E.GIMBAL_MAX + EPS)

    def test_gimbal_minimo_registrado(self):
        self.assertGreaterEqual(self.gmb_min_info, E.GIMBAL_MIN - EPS)

    def test_barrera_de_45_con_comandos_forzados(self):
        # se fuerza el comando del gimbal muy por debajo del límite y el chasis cabeceando fuerte: la cámara no pasa de -45°
        env = E.EntornoDronPersona(16, semilla=4)
        ap = np.full(env.n, E.N_ACC_PERSONA - 1)
        for k in range(200):
            env.gimbal_cmd[:] = -120.0
            env.chasis_pitch[:] = 25.0 if k % 2 else -25.0
            env.step(np.full(env.n, 9), ap)
            for arr in (env.cam_pitch, env.gimbal):
                self.assertTrue(np.all(arr >= E.GIMBAL_MIN - EPS), float(arr.min()))

    def test_perdida_ia_desactivada(self):
        # regla 3: la red solo decide en PERSECUCIÓN (FIJADO); jamás hay BÚSQUEDA_IA
        self.assertEqual(self.ia_fuera_de_persecucion, 0)
        self.assertNotIn(E.BUSQUEDA_IA, self.modos_vistos)

    def test_secuencia_de_la_busqueda(self):
        # V12: la máquina de estados solo avanza en el orden previsto (o vuelve a PERSECUCIÓN con un ReID)
        F, P, I, A, S, H = E.FIJADO, E.PREDECIR, E.INVESTIGAR, E.ASOMO, E.SIGUIENTE_OBSTACULO, E.VENTAJA_ALTURA
        permitidas = {(F, P), (P, I), (I, A), (A, S), (A, H), (S, A), (H, S)}
        # V15 · fase C: PERSECUCIÓN -> RECONFIRMAR (duda de identidad) y, si el operador dice "no es él", a la PÉRDIDA
        R = E.RECONFIRMAR
        permitidas |= {(F, R), (R, P)}
        # V15 · fase D (D2, secuencia tras el muro): GIRO_360 -> otro extremo (FLANQUEO) -> GIRO_360 -> MURO_DE_CANTO -> GIRO_360
        C = E.MURO_CANTO
        permitidas |= {(A, I), (A, C), (C, A)}
        for a, b, _ in self.transiciones:
            if a in (F, P, I, A, S, H, R, C) and b != F:
                self.assertIn((a, b), permitidas, "transición no prevista %s -> %s" % (E.NOMBRE_ESTADO[a], E.NOMBRE_ESTADO[b]))

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
            self.assertIn(antes, (E.VERIFICAR, E.INVESTIGAR, E.ASOMO, E.VENTAJA_ALTURA, E.PREDECIR, E.BUSQUEDA_IA,
                                  E.SIGUIENTE_OBSTACULO, E.RECONFIRMAR, E.MURO_CANTO))
            if antes == E.VERIFICAR:
                self.assertEqual(cand, 0, "se fijó a alguien que no es el sospechoso")
        # V15 · fase C: de RECONFIRMAR solo se vuelve a PERSECUCIÓN con la respuesta del operador (después de su tiempo de
        # respuesta) y siempre con la persona correcta (la que él designó): la IA nunca decide la identidad
        for t_en, t_resp, trk in self.reconf_a_fijado:
            self.assertGreaterEqual(t_en + 1e-9, t_resp)
            self.assertEqual(trk, 0)

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
