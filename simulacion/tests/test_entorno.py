# -*- coding: utf-8 -*-
"""El entorno arranca, un episodio corto corre sin valores raros y el entrenamiento master puede usarlo."""
import json
import os
import unittest

import numpy as np

import entorno as E

SIM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAVES_INFO = ["choque", "choque_ladron", "choque_peaton", "panel", "fuera", "tiempo", "perdido", "no_encontrado", "exito",
               "inicia", "pierde", "recupera", "reflejo", "dist", "visto", "fijado", "peatones", "jitter", "esfuerzo",
               "al_mando", "descubre", "busqueda_ia", "salto"]


class TestEntorno(unittest.TestCase):

    def test_arranca(self):
        env = E.EntornoDronPersona(8, semilla=0)
        self.assertEqual(env.obs_dron().shape, (8, E.OBS_DRON))
        self.assertEqual(env.obs_persona().shape, (8, E.OBS_PERSONA))
        self.assertEqual(E.OBS_DRON, 192)
        self.assertEqual(len(E.CLASES), 10)
        self.assertTrue(np.isfinite(env.obs_dron()).all())

    def test_episodio_corto(self):
        rng = np.random.default_rng(3)
        env = E.EntornoDronPersona(16, semilla=3)
        terminadas = 0
        for _ in range(400):
            acc = rng.integers(0, len(E.CLASES), env.n)
            ap = rng.integers(0, E.N_ACC_PERSONA, env.n)
            r, rp, done, info = env.step(acc, ap)
            self.assertTrue(np.isfinite(r).all() and np.isfinite(rp).all())
            self.assertTrue(np.isfinite(env.obs_dron()).all())
            terminadas += int(done.sum())
        for k in CLAVES_INFO:
            self.assertIn(k, info)
        self.assertTrue(((np.abs(env.dx) <= E.ARENA + 1) & (np.abs(env.dy) <= E.ARENA + 1)).all())
        self.assertGreater(terminadas, 0)

    def test_vecenv_del_master(self):
        from entrenar import ActorCritico
        from entrenar_master import VecDron
        red_p = ActorCritico(E.OBS_PERSONA, E.N_ACC_PERSONA)
        v = VecDron(8, 0, red_p)
        obs = v.reset()
        self.assertEqual(obs.shape, (8, E.OBS_DRON))
        for _ in range(50):
            v.step_async(np.zeros(8, int))
            obs, r, done, infos = v.step_wait()
        self.assertEqual(obs.dtype, np.float32)
        self.assertEqual(len(infos), 8)


class TestPolitica(unittest.TestCase):

    def test_pesos_para_la_jetson(self):
        ruta = os.path.join(SIM, "modelos", "dron_politica.json")
        with open(ruta, encoding="utf-8") as fh:
            p = json.load(fh)
        capas = p["capas"]
        self.assertEqual(len(capas), 3)
        dims = [np.array(c["W"]).shape for c in capas]
        self.assertEqual(dims, [(128, E.OBS_DRON), (128, 128), (len(E.CLASES), 128)])
        self.assertEqual(p["clases"], E.CLASES)
        x = np.random.default_rng(0).normal(size=E.OBS_DRON)
        for i, c in enumerate(capas):
            x = np.array(c["W"]) @ x + np.array(c["b"])
            if i < 2:
                x = np.tanh(x)
        self.assertTrue(np.isfinite(x).all())

    def test_modelo_sb3_carga_y_decide(self):
        ruta = os.path.join(SIM, "modelos_master", "base_v9.zip")     # ultimo.zip cambia mientras se entrena
        if not os.path.exists(ruta):
            self.skipTest("no hay modelos SB3 (no van en Git)")
        from stable_baselines3 import PPO
        m = PPO.load(ruta, device="cpu")
        env = E.EntornoDronPersona(4, semilla=0)
        acc, _ = m.predict(env.obs_dron().astype(np.float32), deterministic=True)
        self.assertEqual(acc.shape, (4,))
        self.assertTrue(((acc >= 0) & (acc < len(E.CLASES))).all())


if __name__ == "__main__":
    unittest.main()
