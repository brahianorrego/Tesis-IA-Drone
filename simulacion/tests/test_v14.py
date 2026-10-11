# -*- coding: utf-8 -*-
"""V14: niveles del currículo (generación en reset), repaso, oclusión entre personas, árbitro de progresión y
competencia dron vs ladrón."""
import unittest

import numpy as np

import entorno as E

QUIETO = E.N_ACC_PERSONA - 1


def dentro(env, i):
    return [j for j in range(E.N_PANELES) if np.abs(env.pa[i, j]).max() < E.ARENA + 1]


class TestNiveles(unittest.TestCase):

    def test_generacion_por_nivel(self):
        # V15: 0 duelo abierto, 1 duelo con civil, 2 muro, 3 muro y civil, 4 misión completa (3-4 muros)
        esperado = {0: ((0,), (0,)), 1: ((0,), (1,)), 2: ((1,), (0,)), 3: ((1,), (1,)), 4: ((3, 4), (0, 1, 2))}
        for nv in range(E.N_NIVELES):
            env = E.EntornoDronPersona(200, semilla=nv, nivel=nv)
            self.assertTrue(np.all(env.lvl_ep == nv))
            muros = {len(dentro(env, i)) and len({tuple(np.round(env.pa[i, j], 3)) for j in dentro(env, i)}) for i in range(env.n)}
            self.assertTrue(muros <= set(esperado[nv][0]), (nv, muros))
            self.assertTrue(set(env.activa[:, 1:].sum(1).tolist()) <= set(esperado[nv][1]), nv)
            if nv in (1, 3):
                self.assertTrue(np.all(env.guion[:, 1] == E.G_DISTRACTOR))
            if nv <= 1:
                self.assertTrue(np.all(np.isin(env.l_guion, (E.L_GUION_HUIDA, E.L_GUION_CENIT))))
            self.assertTrue(np.all(env.tactico) if nv < E.N_NIVELES - 1 else not np.all(env.tactico))
        self.assertEqual(len(E.EntornoDronPersona(1, semilla=0, nivel=0).paneles(0)), 0)   # el visor no dibuja muros

    def test_cenit_en_el_nivel_0(self):
        env = E.EntornoDronPersona(1000, semilla=7, nivel=0)
        frac = (env.l_guion == E.L_GUION_CENIT).mean()
        self.assertAlmostEqual(frac, E.P_CENIT_N0, delta=0.06)

    def test_repaso_de_niveles_anteriores(self):
        top = E.N_NIVELES - 1
        env = E.EntornoDronPersona(1000, semilla=8, nivel=top)
        env.p_repaso = 0.25
        env.reset(np.ones(env.n, bool))
        rep = env.lvl_ep < top
        self.assertAlmostEqual(rep.mean(), 0.25, delta=0.05)
        self.assertEqual(set(np.unique(env.lvl_ep[rep])), set(range(top)))

    def test_cada_nivel_corre_sin_valores_raros(self):
        rng = np.random.default_rng(9)
        for nv in range(E.N_NIVELES):
            env = E.EntornoDronPersona(16, semilla=nv, nivel=nv)
            for _ in range(300):
                r, _, done, info = env.step(rng.integers(0, len(E.CLASES), env.n), np.full(env.n, QUIETO))
                self.assertTrue(np.isfinite(r).all() and np.isfinite(env.obs_dron()).all())
                self.assertTrue(np.all(env.cam_pitch >= E.GIMBAL_MIN - 1e-6))     # regla 1 en todos los niveles
                self.assertTrue(np.all(info["nivel_ep"] == nv))

    def test_oclusion_entre_personas(self):
        # dron bajo (1.8 m) mirando a +X; ladrón a 8 m; un civil delante de él (a 6.4 m) lo tapa casi entero. Desde
        # más alto, el dron ve por encima de la cabeza del civil (eso también se comprueba)
        env = E.EntornoDronPersona(1, semilla=0, nivel=0)
        env.dx[:], env.dy[:], env.dz[:], env.psi[:] = 0.0, 0.0, 1.8, 0.0
        env.activa[:] = False
        env.activa[0, :2] = True
        env.px[0, :2], env.py[0, :2] = (8.0, 6.4), (0.0, 0.0)
        env.cam_pitch[:] = -np.degrees(np.arctan2(0.9, 8.0))
        env._sensores()
        self.assertLess(env.frac_vis[0, 0], E.FRAC_DET_MIN)
        env.dz[:] = 6.0
        env.cam_pitch[:] = -np.degrees(np.arctan2(5.1, 8.0))
        env._sensores()
        self.assertGreater(env.frac_vis[0, 0], 0.5)              # desde 6 m lo ve por encima del civil (las piernas no)
        env.dz[:] = 1.8
        env.cam_pitch[:] = -np.degrees(np.arctan2(0.9, 8.0))
        env.py[0, 1] = 2.0                                       # el civil se aparta de la línea de vista
        env._sensores()
        self.assertGreater(env.frac_vis[0, 0], 0.9)


class _VenvFalso(object):
    def __init__(self):
        self.env = E.EntornoDronPersona(2, semilla=0, nivel=0)
        self.fin = []
        self.attrs = {}

    def set_attr(self, k, v):
        self.attrs[k] = v


class _ModeloFalso(object):
    num_timesteps = 0


class TestArbitroDeProgresion(unittest.TestCase):

    def partida(self, nivel, exito, cenit=False, alcanzado=False):
        from entrenar_master import I_ALCANZADO, I_CENIT, I_EXITO, I_NIVEL
        f = [False] * (I_CENIT + 1)
        f[I_EXITO], f[I_ALCANZADO], f[I_NIVEL], f[I_CENIT] = exito, alcanzado, nivel, cenit
        return tuple(f)

    def cargar(self, v, partidas):
        """V15: VecDron guarda junto a cada partida sus datos extra (rendición, cenit, identidad...)."""
        v.fin = partidas
        v.fin_x = [dict(rinde=bool(f[8]), cenit=bool(f[-1]), nivel=int(f[-2]), tiempo=False, idok=100.0, desig=100.0,
                        nodet=0, choque=False, readq=5.0) for f in partidas]

    def test_sube_solo_con_el_umbral_y_los_pasos_minimos(self):
        from entrenar_master import CurriculumCallback
        v = _VenvFalso()
        cb = CurriculumCallback(v, nivel=0, umbral=0.85, ventana=100, min_pasos=1000, paciencia=0)
        cb.model = _ModeloFalso()
        # 100 partidas con 80 % de éxito: no sube
        self.cargar(v, [self.partida(0, i % 5 != 0) for i in range(100)])
        cb.model.num_timesteps = 5000
        cb._on_rollout_end()
        self.assertEqual(cb.nivel, 0)
        # V15: las de cenit sí cuentan (y deben llegar al 70 %); 100 partidas: 40 de cenit con 80 % y 60 normales con 95 %
        # -> 89 % de rendición: sube a 1
        self.cargar(v, [self.partida(0, i % 5 != 4, cenit=True) for i in range(40)]
                    + [self.partida(0, i % 20 != 0) for i in range(60)])
        cb._on_rollout_end()
        self.assertEqual(cb.nivel, 1)
        self.assertEqual(v.env.current_level, 1)
        self.assertEqual(E.EntornoDronPersona.nivel_inicial, 1)
        # en el nivel nuevo hacen falta los pasos mínimos
        self.cargar(v, [self.partida(1, True)] * 100)
        cb.model.num_timesteps = 5500
        cb._on_rollout_end()
        self.assertEqual(cb.nivel, 1)
        E.EntornoDronPersona.nivel_inicial = E.N_NIVELES - 1

    def test_paciencia(self):
        from entrenar_master import CurriculumCallback
        v = _VenvFalso()
        cb = CurriculumCallback(v, nivel=0, umbral=0.85, ventana=100, min_pasos=1000, paciencia=10000)
        cb.model = _ModeloFalso()
        self.cargar(v, [self.partida(0, False)] * 100)
        cb.model.num_timesteps = 20000
        cb._on_rollout_end()
        self.assertEqual(cb.nivel, 1)
        self.assertEqual(cb.historia[-1]["motivo"], "paciencia")
        E.EntornoDronPersona.nivel_inicial = E.N_NIVELES - 1

    def test_competencia(self):
        from entrenar_master import CurriculumCallback
        v = _VenvFalso()
        cb = CurriculumCallback(v, nivel=0, ventana=100, min_pasos=1e9)
        cb.model = _ModeloFalso()
        self.cargar(v, [self.partida(0, True)] * 6 + [self.partida(0, False, alcanzado=True)] * 2 + [self.partida(0, False)] * 2)
        cb._on_rollout_end()
        c = cb.competencia()
        self.assertAlmostEqual(c["dron"], 0.75)
        self.assertAlmostEqual(c["ladron"], 0.25)
        self.assertAlmostEqual(c["otros"], 0.2)
        E.EntornoDronPersona.nivel_inicial = E.N_NIVELES - 1


if __name__ == "__main__":
    unittest.main()
