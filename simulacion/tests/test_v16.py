# -*- coding: utf-8 -*-
"""V16 (plan docs/PLAN_V16_REALISMO.md, sesión A). Fase A1: partida única de 2 paneles y alturas variables (2.0-3.0 m solo
sin personas conocidas a menos de 8 m; con alguien cerca, nunca por debajo de la altura segura de 3.30 m)."""
import collections
import unittest

import numpy as np

import entorno as E

QUIETO = E.N_ACC_PERSONA - 1
LEJOS = np.array([[40.0, 40.0], [41.0, 40.0]])


def corrida(n=48, pasos=1500, semilla=11, acciones=None):
    """Partidas V16 con acciones al azar (o fijas). Devuelve el entorno y una lista de registros por paso. Las alturas son
    las que cree la Pixhawk (con el error del barómetro, fase A3): es lo que controla la lógica de alturas."""
    rng = np.random.default_rng(semilla)
    env = E.EntornoDronPersona(n, semilla=semilla, nivel=E.NIVEL_V16)
    reg = []
    for _ in range(pasos):
        a0, z0 = env.alt_obj.copy(), env.dz + env.e_baro          # V16 · A3: la altura que cree la Pixhawk
        acc = rng.integers(0, len(E.CLASES), n) if acciones is None else np.full(n, acciones)
        _, _, done, info = env.step(acc, np.full(n, QUIETO), auto_reset=False)
        reg.append(dict(a0=a0, z0=z0, a1=env.alt_obj.copy(), g8=env.gente8.copy(), dz=env.dz + env.e_baro, vz=env.vz_cmd.copy(),
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
        # según su barómetro (A3); si el error lo dejaría por debajo de Z_MIN, en Z_MIN
        np.testing.assert_allclose(env.dz, np.maximum(E.Z_V16_ENTRADA - env.e_baro, E.Z_MIN))

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
        a1 = np.concatenate([r["a1"] for r in self.reg])
        self.assertGreaterEqual(a1.min(), E.Z_V16_INSPECCION - 1e-9)        # nunca se pide menos de 2.0 m
        self.assertGreaterEqual(dz.min(), E.Z_V16_INSPECCION - 0.25)        # (retardo del lazo y deriva del barómetro)

    def test_rampa_sin_escalones(self):
        for r in self.reg:
            d = (r["a1"] - r["a0"])[~r["done"]]
            self.assertTrue(np.all(d >= -E.V_RAMPA_BAJA * E.DT - 1e-9), d.min())
            # hacia arriba la rampa no pasa de la velocidad de subida de ArduPilot, salvo cuando se iguala a la altura
            # real (el árbitro subió esquivando, o un descenso bloqueado: no se acumula error)
            v = ~r["done"]
            # (+0.1 m: lo que puede moverse el error del barómetro en un paso)
            tope = np.maximum(r["a0"][v] + E.VEL_SUBIDA_RAPIDA * E.DT, r["z0"][v] + 0.1)
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
        env.baro_amp[:] = env.e_baro[:] = 0.0                       # aquí se prueba la lógica (el barómetro, aparte)
        env.gimbal[:] = env.gimbal_cmd[:] = env.cam_pitch[:] = -15.0
        env.gb.reset(todos, -15.0)
        env.obs_retraso = env._sensores()
        zmin = 99.0
        for _ in range(200):
            env.step(np.zeros(n, int), np.full(n, QUIETO), auto_reset=False)
            zmin = min(zmin, float((env.dz + env.e_baro).min()))     # la que sostiene la Pixhawk (con el barómetro)
        self.assertGreaterEqual(zmin, E.Z_SEGURA - 0.05)



def una_persona(n=200, semilla=0, postura=E.DE_PIE, dist=8.0, muro=False, z=E.Z_SEGURA):
    """Dron en (0, 0) mirando a +X a la altura z con la cámara apuntando a una persona quieta (el ladrón, sin cerebro
    táctico) a `dist` m en la postura dada; con muro=True, un muro de 6 m entre los dos a 1 m de la persona (la persona
    pegada a él del otro lado). Devuelve el entorno con los sensores ya calculados."""
    env = E.EntornoDronPersona(n, semilla=semilla, nivel=E.NIVEL_V16)
    todos = np.ones(n, bool)
    env.dx[:], env.dy[:], env.dz[:], env.psi[:] = 0.0, 0.0, z, 0.0
    env.pa[:], env.pb[:] = LEJOS[0], LEJOS[1]
    if muro:
        env.pa[:, 0], env.pb[:, 0] = (dist - E.D_RECOSTADO, -3.0), (dist - E.D_RECOSTADO, 3.0)
    env.activa[:] = False
    env.activa[:, 0] = True
    env.tactico[:] = False
    env.px[:, 0], env.py[:, 0] = dist, 0.0
    env.estatura[:] = 1.72
    env.pos[:], env.pos0[:], env.pt[:] = postura, postura, 1.0
    env._avanzar_posturas()
    env.pt[:] = 1.0
    ang = -np.degrees(np.arctan2(z - 0.9, dist))
    env.cam_pitch[:] = env.gimbal[:] = env.gimbal_cmd[:] = ang
    env._sensores()
    return env


class TestA2Posturas(unittest.TestCase):

    def test_alto_y_transicion(self):
        env = una_persona(n=4)
        quien = np.zeros((4, E.N_PERS), bool)
        quien[:, 0] = True
        for nueva, alto in ((E.AGACHADO, 1.15), (E.GATEANDO, 0.6), (E.DE_PIE, 1.72)):
            env._pedir_postura(quien, np.full((4, E.N_PERS), nueva))
            t = 0.0
            while env.pt[0, 0] < 1.0:
                env._avanzar_posturas()
                t += E.DT
            self.assertTrue(0.5 - 1e-9 <= t <= 1.0 + 1e-9, t)          # transiciones de 0.5 a 1 s
            self.assertAlmostEqual(env.alto_ef[0, 0], alto, delta=0.05)

    def test_rapidez_maxima_por_postura(self):
        for postura, vmax in ((E.AGACHADO, 1.0), (E.GATEANDO, 0.65), (E.RECOSTADO, 0.0)):
            env = una_persona(n=4, postura=postura, dist=10.0)
            env.v_forzada[:, 0] = (3.0, 0.0)                               # le piden correr
            vm = 0.0
            for _ in range(30):
                env._mover_personas(None)
                vm = max(vm, float(np.hypot(env.pvx[:, 0], env.pvy[:, 0]).max()))
            self.assertLessEqual(vm, vmax + 1e-6, E.NOMBRE_POSTURA[postura])

    def test_yolo_menos_seguro_agachado_y_gateando(self):
        tasas = []
        for postura in (E.DE_PIE, E.AGACHADO, E.GATEANDO):
            env = una_persona(n=400, postura=postura, dist=10.0)
            v = np.mean([env._sensores() is not None and env.info_sensor["visible_real"][:, 0].mean() for _ in range(5)])
            tasas.append(v)
        self.assertGreater(tasas[0], tasas[1])
        self.assertGreater(tasas[1], tasas[2])

    def test_oclusion_tras_el_muro(self):
        # pegado del otro lado de un muro de 2.6 m, visto desde 3.30 m a 8 m: de pie asoma la cabeza; agachado, recostado
        # (la espalda en la pared) o gateando, casi nada
        fv = {p: float(una_persona(n=8, postura=p, dist=8.0, muro=True).frac_vis[:, 0].mean())
              for p in (E.DE_PIE, E.AGACHADO, E.RECOSTADO, E.GATEANDO)}
        self.assertLess(fv[E.AGACHADO], 0.02)
        self.assertLess(fv[E.GATEANDO], 0.02)
        self.assertLess(fv[E.RECOSTADO], E.P_FRAC[0])                      # casi total: YOLO no la detecta
        self.assertGreaterEqual(fv[E.DE_PIE], fv[E.RECOSTADO])

    def test_el_ladron_usa_las_posturas(self):
        env = E.EntornoDronPersona(64, semilla=4, nivel=E.NIVEL_V16)
        vistas = set()
        for _ in range(1500):
            _, _, done, _ = env.step(np.full(env.n, 6), np.full(env.n, QUIETO))
            vistas |= set(env.pos[:, 0].tolist())
        self.assertEqual(vistas, {E.DE_PIE, E.AGACHADO, E.RECOSTADO, E.GATEANDO})


class TestA2Salto(unittest.TestCase):

    def _saltar(self, z, estatura=1.72, h_salto=None, dist=0.3):
        env = una_persona(n=16, dist=dist, z=z)
        env.estatura[:] = estatura
        env.l_alerta_t[:] = 0.0
        if h_salto is not None:
            class Fija(object):                       # el salto sale siempre de la altura pedida
                def __init__(self, r):
                    self.r = r

                def uniform(self, a, b, size=None):
                    return np.full(size, h_salto)

                def __getattr__(self, k):
                    return getattr(self.r, k)
            env.rng = Fija(env.rng)
        fases, alc, hmax, zmano = [], np.zeros(16, bool), 0.0, 0.0
        quiere = np.ones(16, bool)
        for _ in range(30):
            dh0 = np.hypot(env.dx - env.px[:, 0], env.dy - env.py[:, 0])
            env._salto_v16(np.ones(16, bool), quiere, dh0)
            env._mano_v16()
            fases.append(int(env.salto_f[0]))
            hmax, zmano = max(hmax, float(env.salto_h.max())), max(zmano, float(env.mano[:, 2].max()))
            mano_h = np.hypot(env.mano[:, 0] - env.dx, env.mano[:, 1] - env.dy)
            alc |= (mano_h < E.RADIO_DRON) & (env.mano[:, 2] >= env.dz - E.H_DRON_ABAJO)
        return fases, alc, hmax, zmano

    def test_fases_del_salto(self):
        fases, _, hmax, zmano = self._saltar(2.8, h_salto=0.45)
        sec = [f for k, f in enumerate(fases) if k == 0 or f != fases[k - 1]]
        self.assertEqual(sec[:4], [1, 2, 3, 0])                               # impulso, vuelo, aterrizaje, fin
        self.assertAlmostEqual(hmax, 0.45, delta=0.06)                        # vuelo balístico de la altura del salto
        alc_pie = E.K_ALCANCE_PIE * 1.72
        self.assertLessEqual(zmano, alc_pie + 0.45 + 1e-6)                   # mano = alcance de pie + salto

    def test_alcanza_bajo_y_no_a_la_altura_segura(self):
        _, alc, _, _ = self._saltar(2.6, h_salto=0.35)
        self.assertTrue(alc.all())
        # el más alto (1.88 m) con el mejor salto (0.50 m) no llega a la altura segura
        _, alc, _, zmano = self._saltar(E.Z_SEGURA, estatura=E.ESTATURA_MAX, h_salto=E.SALTO_ADULTO[1])
        self.assertFalse(alc.any())
        self.assertLess(zmano, E.Z_SEGURA - E.H_DRON_ABAJO)


class TestA2Civiles(unittest.TestCase):

    def test_reaccionan_al_dron(self):
        env = E.EntornoDronPersona(96, semilla=6, nivel=E.NIVEL_V16)
        estados = collections.Counter()
        salieron = 0
        for _ in range(2000):
            act0 = env.activa[:, 1:].copy()
            env.step(np.full(env.n, 6), np.full(env.n, QUIETO), auto_reset=False)
            a = env.activa[:, 1:]
            salieron += int((act0 & ~a).sum())
            estados.update(env.c_est[:, 1:][a].tolist())
            # mirando o grabando, de frente al dron
            m = a & ((env.c_est[:, 1:] == E.C_MIRA) | (env.c_est[:, 1:] == E.C_GRABA))
            if m.any():
                b = np.arctan2(env.dy[:, None] - env.py[:, 1:], env.dx[:, None] - env.px[:, 1:])
                self.assertTrue(np.all(np.abs(E.envolver(env.mira_p[:, 1:] - b))[m] < 0.3))
        for c in (E.C_TRANSITA, E.C_MIRA, E.C_ESQUIVA, E.C_ALEJA, E.C_SALE, E.C_GRABA):
            self.assertGreater(estados[c], 0, E.NOMBRE_CIVIL[c])
        self.assertGreater(salieron, 0)

    def test_contrato_foto(self):
        env = E.EntornoDronPersona(2, semilla=0, nivel=E.NIVEL_V16)
        for _ in range(20):
            env.step(np.zeros(2, int), np.full(2, QUIETO))
        f = env.foto(0)
        for k in ("salto", "alt_obj", "cam_piso", "g8", "v16"):
            self.assertIn(k, f)
        for p in f["pers"]:
            for k in ("pos", "pos0", "pt", "mira", "civ", "graba", "alto"):
                self.assertIn(k, p)



class TestA3Sensores(unittest.TestCase):

    def test_tf03_fijo_al_chasis(self):
        # a 2.0 m el TF03 (casi horizontal) ve un muro de 2.6 m a 20 m; a 3.30 m pasa por encima; con el chasis cabeceando
        # 20° hacia abajo toca el suelo y la Jetson lo descarta (no es obstáculo)
        for z, cab, espera in ((2.0, 0.0, True), (E.Z_SEGURA, 0.0, False), (2.0, -20.0, False)):
            env = una_persona(n=4, dist=20.0, z=z)
            env.activa[:, 0] = False
            env.px[:, 0] = env.py[:, 0] = 999.0
            env.pa[:, 0], env.pb[:, 0] = (20.0, -3.0), (20.0, 3.0)
            env.e_baro[:] = 0.0
            env.chasis_pitch[:] = cab
            env._sensores()
            self.assertEqual(bool((env.lidar < E.LIDAR_MAX - 1).all()), espera, (z, cab, env.lidar))

    def test_luna_mide_a_la_persona_centrada(self):
        # el TF-Luna (en el gimbal) da la distancia a la persona centrada solo dentro de su alcance
        cerca = una_persona(n=64, dist=4.0)
        cerca.luna_max[:] = 8.0
        cerca._sensores()
        lejos = una_persona(n=64, dist=12.0)
        lejos.luna_max[:] = 8.0
        lejos._sensores()
        s_c, s_l = cerca.info_sensor, lejos.info_sensor
        self.assertGreater((s_c["laser"][:, 0] & s_c["visible"][:, 0]).mean(), 0.5)
        self.assertFalse(s_l["laser"][:, 0].any())

    def test_camara_al_piso_ve_debajo(self):
        abajo = una_persona(n=200, dist=0.5)
        abajo._sensores()
        lejos = una_persona(n=200, dist=6.0)
        lejos._sensores()
        self.assertGreater(abajo.piso_vis[:, 0].mean(), 0.6)
        self.assertEqual(lejos.piso_vis[:, 0].mean(), 0.0)
        # con el chasis inclinado 20° hacia adelante (frenando), la cámara al piso mira hacia adelante: la ve a 2 m adelante
        inc = una_persona(n=200, dist=2.0)
        inc.chasis_pitch[:] = 20.0
        inc._sensores()
        self.assertGreater(inc.piso_vis[:, 0].mean(), 0.5)

    def test_desenfoque_baja_la_deteccion(self):
        quieto = una_persona(n=2000, dist=10.0)
        gira = una_persona(n=2000, dist=10.0)
        gira.yaw_dps[:] = 120.0
        quieto._sensores()
        gira._sensores()
        pq, pg = quieto.info_sensor["visible_real"][:, 0].mean(), gira.info_sensor["visible_real"][:, 0].mean()
        self.assertLess(pg, pq - 0.15)

    def test_gimbal_mixto(self):
        env = E.EntornoDronPersona(400, semilla=8, nivel=E.NIVEL_V16)
        self.assertTrue(0.4 < env.gb.servo.mean() < 0.6)                    # "mixto": la mitad de las partidas con servo
        self.assertFalse(E.EntornoDronPersona(50, semilla=8, nivel=4).gb.servo.any())   # la V15, con la BaseCam

    def test_deriva_del_gps_corre_el_mundo_recordado(self):
        env = E.EntornoDronPersona(64, semilla=9, nivel=E.NIVEL_V16)
        for _ in range(300):
            env.step(np.full(env.n, 6), np.full(env.n, QUIETO))
        self.assertTrue(np.all(np.abs(env.e_gps) < 3 * E.GPS_DERIVA[1]))
        i = int(np.argmax(env.lid_ok.sum(1)))
        k = np.where(env.lid_ok[i])[0]
        x0, e0 = env.lid_px[i, k].copy(), env.e_gps[i].copy()
        env._deriva_nav()
        np.testing.assert_allclose(env.lid_px[i, k], x0 - (env.e_gps[i, 0] - e0[0]))

    def test_v15_sin_ruido_de_navegacion(self):
        env = E.EntornoDronPersona(16, semilla=1, nivel=4)
        self.assertFalse(env.gps_amp.any() or env.baro_amp.any())


if __name__ == "__main__":
    unittest.main()
