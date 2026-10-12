# -*- coding: utf-8 -*-
"""V16 (plan docs/PLAN_V16_REALISMO.md, sesión A). Fase A1: partida única de 2 paneles y alturas variables (2.0-3.0 m solo
sin personas conocidas a menos de 8 m; con alguien cerca, nunca por debajo de la altura segura de 3.30 m)."""
import unittest

import numpy as np

import entorno as E

QUIETO = E.N_ACC_PERSONA - 1
LEJOS = np.array([[40.0, 40.0], [41.0, 40.0]])


def corrida(n=48, pasos=1500, semilla=11, acciones=None):
    """Partidas V16 con acciones al azar (o fijas). Devuelve el entorno y una lista de registros por paso."""
    rng = np.random.default_rng(semilla)
    env = E.EntornoDronPersona(n, semilla=semilla, nivel=E.NIVEL_V16)
    reg = []
    for _ in range(pasos):
        a0, z0 = env.alt_obj.copy(), env.dz.copy()
        acc = rng.integers(0, len(E.CLASES), n) if acciones is None else np.full(n, acciones)
        _, _, done, info = env.step(acc, np.full(n, QUIETO), auto_reset=False)
        reg.append(dict(a0=a0, z0=z0, a1=env.alt_obj.copy(), g8=env.gente8.copy(), dz=env.dz.copy(), vz=env.vz_cmd.copy(),
                        done=done.copy()))
        env.reset(done)
    return env, reg


class TestA1Escenario(unittest.TestCase):

    def test_partida_unica_por_defecto(self):
        self.assertEqual(E.EntornoDronPersona.nivel_inicial, E.NIVEL_V16)
        env = E.EntornoDronPersona(300, semilla=1, nivel=E.NIVEL_V16)
        self.assertTrue((env.lvl_ep == E.NIVEL_V16).all())
        for i in range(env.n):
            muros = env.paneles(i)
            self.assertEqual(len(muros), E.MUROS_V16)                 # exactamente 2 paneles distintos
            for ax, ay, bx, by, h in muros:
                self.assertTrue(E.LARGO_MURO_V16[0] - 1e-6 <= np.hypot(bx - ax, by - ay) <= E.LARGO_MURO_V16[1] + 1e-6)
                self.assertEqual(h, E.ALTO_PANEL)
        self.assertTrue(env.tactico.all())                              # siempre el ladrón táctico
        civ = env.activa[:, 1:].sum(1)
        self.assertEqual(set(np.unique(civ).tolist()), {0, 1, 2})
        self.assertTrue((env.guion[:, 1:][env.activa[:, 1:]] == E.G_CIVIL).all())
        d = np.hypot(env.px[:, 1:] - env.dx[:, None], env.py[:, 1:] - env.dy[:, None])[env.activa[:, 1:]]
        self.assertGreater(np.mean(d > E.R_GENTE), 0.97)               # nacen lejos del 360° de entrada bajo
        np.testing.assert_allclose(env.dz, E.Z_V16_ENTRADA)

    def test_civiles_atraviesan_la_zona(self):
        env = E.EntornoDronPersona(64, semilla=2, nivel=E.NIVEL_V16)
        civ = env.activa[:, 1:].copy()
        p0 = np.stack([env.px[:, 1:], env.py[:, 1:]], -1)
        for _ in range(100):
            env.step(np.zeros(env.n, int), np.full(env.n, QUIETO), auto_reset=False)
        avance = np.hypot(*(np.stack([env.px[:, 1:], env.py[:, 1:]], -1) - p0).transpose(2, 0, 1))[civ]
        self.assertGreater(np.median(avance), 6.0)                     # caminan (~1.1-1.5 m/s durante 10 s)


class TestA1Alturas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.env, cls.reg = corrida()

    def test_con_gente_cerca_no_baja_de_la_altura_segura(self):
        # mientras haya una persona conocida a menos de 8 m, la altura objetivo nunca baja y, por debajo de 3.30 m, la
        # consigna vertical nunca es hacia abajo
        n_g8 = 0
        for r in self.reg:
            g = r["g8"] & ~r["done"]
            n_g8 += int(g.sum())
            self.assertTrue(np.all(r["a1"][g] >= np.minimum(r["a0"][g], E.Z_SEGURA) - 1e-9))
            bajo = g & (r["dz"] < E.Z_SEGURA)
            self.assertTrue(np.all(r["vz"][bajo] >= -1e-9), r["vz"][bajo].min() if bajo.any() else 0)
        self.assertGreater(n_g8, 1000)                                  # la prueba sí vio gente cerca

    def test_usa_las_alturas_bajas(self):
        dz = np.concatenate([r["dz"] for r in self.reg])
        self.assertGreater(np.mean(dz < E.Z_SEGURA - 0.1), 0.005)      # sí baja a 2.0-3.0 m sin nadie cerca
        self.assertGreaterEqual(dz.min(), E.Z_V16_INSPECCION - 0.15)

    def test_rampa_sin_escalones(self):
        for r in self.reg:
            d = (r["a1"] - r["a0"])[~r["done"]]
            self.assertTrue(np.all(d >= -E.V_RAMPA_BAJA * E.DT - 1e-9), d.min())
            # hacia arriba la rampa no pasa de la velocidad de subida de ArduPilot, salvo cuando se iguala a la altura
            # real (el árbitro subió esquivando, o un descenso bloqueado: no se acumula error)
            v = ~r["done"]
            tope = np.maximum(r["a0"][v] + E.VEL_SUBIDA_RAPIDA * E.DT, r["z0"][v])
            self.assertTrue(np.all(r["a1"][v] <= tope + 1e-9))

    def test_persona_cerca_desde_el_inicio(self):
        # el dron hace el 360° de entrada a la altura segura y alguien está quieto a 5 m: aunque el giro lo saque del
        # cuadro, el dron no baja de 3.30 m en todo el giro
        n = 8
        env = E.EntornoDronPersona(n, semilla=3, nivel=E.NIVEL_V16)
        todos = np.ones(n, bool)
        env.dx[:], env.dy[:], env.dz[:], env.psi[:] = -10.0, 0.0, E.Z_SEGURA, 0.0
        env.dvx[:] = env.dvy[:] = env.dvz[:] = 0.0
        env.ap.sincronizar(env, todos)
        env.pa[:], env.pb[:] = LEJOS[0], LEJOS[1]
        env.activa[:, 2:] = False
        env.px[:, 2:] = env.py[:, 2:] = 999.0
        env.activa[:, 1] = True
        env.px[:, 1], env.py[:, 1] = -5.0, 0.0
        env.px[:, 0], env.py[:, 0] = 22.0, 22.0
        env.v_forzada[:] = np.nan
        env.v_forzada[:, :2] = 0.0
        env.reiniciar_mision(todos)
        env.alt_obj[:] = E.Z_SEGURA
        env.gimbal[:] = env.gimbal_cmd[:] = env.cam_pitch[:] = -15.0
        env.gb.reset(todos, -15.0)
        env.obs_retraso = env._sensores()
        zmin = 99.0
        for _ in range(200):
            env.step(np.zeros(n, int), np.full(n, QUIETO), auto_reset=False)
            zmin = min(zmin, float(env.dz.min()))
        self.assertGreaterEqual(zmin, E.Z_SEGURA - 0.05)


if __name__ == "__main__":
    unittest.main()
