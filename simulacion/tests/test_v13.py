# -*- coding: utf-8 -*-
"""V13: currículo "Un Solo Muro", GIRO_360 fijo y con RATE_Y_MAX, interrupción táctica, stand-off por FOV y detección
parcial de YOLO (15 % del bounding box)."""
import unittest

import numpy as np

import control
import entorno as E

QUIETO = E.N_ACC_PERSONA - 1


def escena_muro(ph, z=3.0, ladron_x=6.0):
    """Un dron en (0, 0, z) mirando a +X, un muro en x = 5 de altura ph y el ladrón detrás, en (ladron_x, 0)."""
    env = E.EntornoDronPersona(1, semilla=0)
    env.dx[:], env.dy[:], env.dz[:], env.psi[:] = 0.0, 0.0, z, 0.0
    env.pa[:] = (5.0, -3.0)
    env.pb[:] = (5.0, 3.0)
    env.ph[:] = ph
    env.activa[:] = False
    env.activa[:, 0] = True
    env.px[:, 0], env.py[:, 0] = ladron_x, 0.0
    env.cam_pitch[:] = -np.degrees(np.arctan2(z - 0.9, ladron_x))
    return env


class TestV13(unittest.TestCase):

    def test_curriculo_un_solo_muro(self):
        # V14: el "Un Solo Muro" de la V13 ahora son los niveles 1 y 2 del currículo
        env = E.EntornoDronPersona(600, semilla=1, nivel=2)          # V15: un solo muro en los niveles 2 y 3
        self.assertTrue(env.un_muro.all())
        self.assertFalse(E.EntornoDronPersona(50, semilla=1, nivel=E.N_NIVELES - 1).un_muro.any())
        i = np.where(env.un_muro)[0]
        np.testing.assert_allclose(env.pa[i, 1], env.pa[i, 0])
        np.testing.assert_allclose(env.pb[i, 1], env.pb[i, 0])
        self.assertEqual(len(env.paneles(int(i[0]))), 1)          # el visor recibe un solo muro

    def test_stand_off_por_fov(self):
        a, b = E.stand_off_fov()
        self.assertAlmostEqual(np.hypot(a, b), 2.5, delta=0.1)   # ~2.5 m en diagonal a la esquina
        # mirando a lo largo del muro desde ahí, el cono horizontal cubre toda la franja oculta desde la esquina
        semi = np.tan(np.radians(E.HFOV / 2.0))
        self.assertGreaterEqual(a * semi, b - 1e-9)
        self.assertGreaterEqual(a * semi, E.D_ZONA_OCULTA - b - 1e-9)

    def test_rate_y_max(self):
        self.assertEqual(control.AutopilotoArduPilot.RATE_Y_MAX, 120.0)
        self.assertLessEqual(E.YAW_GIRO_360, control.AutopilotoArduPilot.RATE_Y_MAX)
        rng = np.random.default_rng(2)
        env = E.EntornoDronPersona(32, semilla=2)
        for _ in range(400):
            env.step(rng.integers(0, len(E.CLASES), env.n), np.full(env.n, QUIETO))
            self.assertTrue(np.all(np.abs(env.yaw_dps) <= 120.0 + 1e-9))

    def test_deteccion_parcial(self):
        # V15 (plan, sección G): la probabilidad de detección sube con la fracción visible del cuerpo. Muros cada vez más
        # altos delante del ladrón: menos cuerpo visible -> menos detecciones; sin nada visible, ninguna
        res = []
        for ph in (1.4, 1.633, 1.775, 3.5):
            env = escena_muro(ph)
            vistos = 0
            for _ in range(60):
                env._sensores()
                vistos += int(env.info_sensor["visible"][0, 0])
            res.append((env.frac_vis[0, 0], vistos))
        fr = [f for f, _ in res]
        self.assertEqual(fr, sorted(fr, reverse=True))
        self.assertGreater(res[0][1], res[2][1])
        self.assertGreater(res[1][1], 0)
        self.assertLess(res[3][0], E.P_FRAC[0])
        self.assertEqual(res[3][1], 0)

    def test_interrupcion_tactica(self):
        # en cualquier estado de búsqueda, si YOLO ve al ID designado, PERSECUCIÓN en ese mismo paso
        for modo in (E.PREDECIR, E.INVESTIGAR, E.ASOMO, E.SIGUIENTE_OBSTACULO, E.VENTAJA_ALTURA):
            env = E.EntornoDronPersona(8, semilla=3)
            env.modo[:] = modo
            env.lock[:] = False
            env.visto_alguna[:] = True
            env.info_sensor["visible"][:] = False
            env.info_sensor["visible"][:4, 0] = True                 # 0-3 ven al ladrón
            env.info_sensor["visible"][4:, 1] = env.activa[4:, 1]    # 4-7 solo ven a un peatón (si hay)
            env.activa[:, 0] = True
            _, _, done, info = env.step(np.zeros(8, int), np.full(8, QUIETO), auto_reset=False)
            vivos = ~done
            self.assertTrue(np.all(info["interrumpe"][:4] | done[:4]), E.NOMBRE_ESTADO[modo])
            self.assertTrue(np.all((env.modo[:4] == E.FIJADO) | done[:4]), E.NOMBRE_ESTADO[modo])
            self.assertFalse(np.any(info["interrumpe"][4:] & vivos[4:]))

    def test_giro_360_altura_y_gimbal(self):
        rng = np.random.default_rng(4)
        env = E.EntornoDronPersona(96, semilla=4)
        err_g, err_z = [], []
        for _ in range(900):
            env.step(rng.integers(0, len(E.CLASES), env.n), np.full(env.n, QUIETO))
            girando = (env.modo == E.ASOMO) & (env.t_modo > 3.0) & (env.estado == E.VIGILANDO)
            err_g += list(np.abs(env.cam_pitch[girando] - E.GIMBAL_GIRO))
            err_z += list(np.abs(env.dz[girando] - E.Z_GIRO))
        if not err_g:
            self.skipTest("ninguna partida llegó a un GIRO_360 largo")
        self.assertLess(np.median(err_g), 2.0)
        self.assertLess(np.median(err_z), 0.3)


if __name__ == "__main__":
    unittest.main()
