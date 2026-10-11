# -*- coding: utf-8 -*-
"""V15 (plan docs/PLAN_V15_CURRICULO.md). Fase A: LiDAR TF03 (30 m, 10 rayos por paso), 360° de entrada bajo y de
búsqueda alto, cansancio del ladrón, cuerpo colombiano y altura segura, muros con grosor, detección por alto y ancho."""
import unittest

import numpy as np

import entorno as E

QUIETO = E.N_ACC_PERSONA - 1


def giro_de_entrada(d_muro, n=4, semilla=0):
    """Dron en (-10, 0) haciendo el 360° de entrada; un muro de 6 m perpendicular a d_muro m. Devuelve el entorno."""
    env = E.EntornoDronPersona(n, semilla=semilla, nivel=2)
    env.dx[:], env.dy[:], env.dz[:], env.psi[:] = -10.0, 0.0, E.Z_ENTRADA, 0.0
    env.dvx[:] = env.dvy[:] = env.dvz[:] = 0.0
    env.ap.sincronizar(env, np.ones(n, bool))
    x = -10.0 + d_muro
    env.pa[:] = (x, -3.0)
    env.pb[:] = (x, 3.0)
    env.activa[:] = False                     # nadie a la vista: la vuelta no se interrumpe
    env.px[:] = env.py[:] = 999.0
    env.reiniciar_mision(np.ones(n, bool))
    env.lid_ok[:] = False
    env.lid_i[:] = 0
    env.lid_psi_prev[:] = env.psi
    env.gimbal[:] = env.gimbal_cmd[:] = env.cam_pitch[:] = E.GIMBAL_ENTRADA
    env.gb.reset(np.ones(n, bool), E.GIMBAL_ENTRADA)
    for _ in range(130):                      # una vuelta a 40°/s son ~9 s
        env.step(np.zeros(n, int), np.full(n, QUIETO), auto_reset=False)
    return env


class TestFaseA(unittest.TestCase):

    def test_constantes(self):
        self.assertEqual(E.LIDAR_MAX, 30.0)
        self.assertEqual(E.RAYOS_POR_PASO, 10)
        self.assertGreaterEqual(E.Z_SEGURA, 3.0)
        # altura segura = alcance saltando del percentil 99 + 0.3 m
        h99 = min(E.ESTATURA_MEDIA + 2.326 * E.ESTATURA_SD, E.ESTATURA_MAX)
        self.assertAlmostEqual(E.Z_SEGURA, round(E.K_ALCANCE_PIE * h99 + E.SALTO_ADULTO[1] + 0.3, 2))
        for z in (E.Z_ATAQUE, E.Z_FLANCO, E.Z_GIRO):
            self.assertGreaterEqual(z, E.Z_SEGURA)
        self.assertEqual((E.Z_ENTRADA, E.GIMBAL_ENTRADA), (2.5, -3.0))
        self.assertGreaterEqual(E.GIMBAL_GIRO, E.GIMBAL_MIN)

    def test_360_de_entrada_mapea_un_muro_a_25_m(self):
        env = giro_de_entrada(25.0)
        for i in range(env.n):
            env._mapear_lidar(i)
            xs = [(env.det_a[i, j, 0] + env.det_b[i, j, 0]) / 2 for j in range(env.det_n[i])]
            self.assertTrue(any(abs(x - 15.0) < 0.6 for x in xs), "no detectó el muro a 25 m: %s" % xs)
            self.assertFalse(env.entrada[i])          # una sola vuelta

    def test_guarda_del_360_de_entrada(self):
        # alguien a menos de 6 m durante la vuelta de entrada: sube a la altura segura
        env = E.EntornoDronPersona(2, semilla=1, nivel=0)
        env.dz[:] = E.Z_ENTRADA
        env.reiniciar_mision(np.ones(2, bool))
        env.ignorado[:, 0] = True                      # el operador ya lo descartó: no se va a verificar
        env.px[:, 0], env.py[:, 0] = env.dx + 4.0 * np.cos(env.psi), env.dy + 4.0 * np.sin(env.psi)
        env.v_forzada[:, 0] = 0.0
        env.cam_pitch[:] = env.gimbal[:] = env.gimbal_cmd[:] = -15.0
        env._sensores()
        for _ in range(40):
            env.step(np.zeros(2, int), np.full(2, QUIETO), auto_reset=False)
        self.assertTrue(env.entrada_alta.all())
        self.assertTrue(np.all(env.dz > E.Z_SEGURA - 0.4))

    def test_estatura_y_alcance(self):
        env = E.EntornoDronPersona(2000, semilla=2)
        est = env.estatura[:, 0]
        self.assertAlmostEqual(est.mean(), E.ESTATURA_MEDIA, delta=0.01)
        self.assertTrue(est.min() >= E.ESTATURA_MIN and est.max() <= E.ESTATURA_MAX)
        np.testing.assert_allclose(env.alc_pie, E.K_ALCANCE_PIE * est)

    def test_cansancio(self):
        env = E.EntornoDronPersona(8, semilla=3, nivel=0)
        env.reserva[:] = 1.0
        env.activa[:, 1:] = False
        env.v_forzada[:, 0] = (4.0, 0.0)               # corre a 4 m/s, por encima de la velocidad crítica
        env.px[:, 0], env.py[:, 0] = -20.0, 0.0
        for _ in range(100):                           # 10 s -> gasta (4 - VC + tensión) x 10 m de D' (D-041)
            env.step(np.zeros(8, int), np.full(8, QUIETO), auto_reset=False)
            env.px[:, 0] = -20.0
        gasto = (4.0 - E.VC_LADRON + E.K_TENSION) * 10.0
        np.testing.assert_allclose(env.reserva, 1.0 - gasto / E.D_PRIMA, atol=0.03)
        self.assertTrue(np.all(env.pulso > 110.0))
        env.v_forzada[:, 0] = (1.0, 0.0)               # caminando se recupera (despacio)
        r0 = env.reserva.copy()
        for _ in range(100):
            env.step(np.zeros(8, int), np.full(8, QUIETO), auto_reset=False)
            env.px[:, 0] = -20.0
        self.assertTrue(np.all(env.reserva > r0))
        env.reserva[:] = 0.0
        env._velocidad_personas(None)
        np.testing.assert_allclose(env.v_corr_ef, E.V_TROTE)     # sin reserva solo trota

    def test_muro_de_canto_y_ancho_del_cuerpo(self):
        # dron en la prolongación del muro mirando a lo largo; el ladrón justo detrás de la punta lejana, en la línea del
        # muro: el muro (0.2 m) es más angosto que sus hombros (0.45 m) y le sobresale por los lados
        env = E.EntornoDronPersona(1, semilla=0, nivel=2)
        env.dx[:], env.dy[:], env.dz[:], env.psi[:] = 0.0, 0.0, 3.3, 0.0
        env.pa[:] = (6.0, 0.0)
        env.pb[:] = (11.0, 0.0)
        env.activa[:] = False
        env.activa[0, 0] = True
        env.px[0, 0], env.py[0, 0] = 11.6, 0.0
        env.cam_pitch[:] = -np.degrees(np.arctan2(3.3 - 1.0, 11.6))
        env._sensores()
        self.assertGreater(env.frac_vis[0, 0], E.P_FRAC[0])
        self.assertLess(env.frac_vis[0, 0], 0.9)           # el centro del cuerpo sí lo tapa el muro

    def test_deteccion_probabilistica(self):
        self.assertLess(E.P_FRAC[0], E.P_FRAC[1])

    def test_gimbal_en_todos_los_niveles(self):
        rng = np.random.default_rng(5)
        for nv in range(E.N_NIVELES):
            env = E.EntornoDronPersona(16, semilla=nv, nivel=nv)
            for _ in range(250):
                env.step(rng.integers(0, len(E.CLASES), env.n), np.full(env.n, QUIETO))
                self.assertTrue(np.all(env.cam_pitch >= E.GIMBAL_MIN - 1e-6))


if __name__ == "__main__":
    unittest.main()


class TestFaseB(unittest.TestCase):
    """Predicción: Kalman, filtro de partículas con información negativa, anti-cenit y distancia adaptativa."""

    def test_kalman_converge_y_rechaza_mediciones_imposibles(self):
        env = E.EntornoDronPersona(1, semilla=0, nivel=0)
        rng = np.random.default_rng(0)
        for k in range(40):                                     # ladrón a 2 m/s en +x, mediciones con 0.2 m de ruido
            x = 0.2 * k
            env._kalman(np.array([True]), np.array([x + rng.normal(0, 0.2)]), np.array([rng.normal(0, 0.2)]), np.array([0.2]))
        self.assertAlmostEqual(env.kf_x[0, 0, 1], 2.0, delta=0.4)
        x0 = env.kf_x[0, 0, 0]
        env._kalman(np.array([True]), np.array([x0 + 12.0]), np.array([0.0]), np.array([0.2]))   # medición absurda
        self.assertLess(abs(env.kf_x[0, 0, 0] - x0), 1.0)
        for _ in range(30):                                     # sin verlo: no se dispara (rapidez humana, en la arena)
            env._kalman(np.array([False]), np.zeros(1), np.zeros(1), np.array([0.2]))
        self.assertLessEqual(np.hypot(env.kf_x[0, 0, 1], env.kf_x[0, 1, 1]), E.V_PF_MAX + 1e-6)
        self.assertLessEqual(abs(env.kf_x[0, 0, 0]), E.ARENA)

    def _nube_con_muro(self):
        """Dron en (0, 0) mirando a +x; muro en x = 6 (de y = -3 a 3); nube repartida a ambos lados del muro."""
        env = E.EntornoDronPersona(1, semilla=1, nivel=1)
        env.dx[:], env.dy[:], env.dz[:], env.psi[:] = 0.0, 0.0, 3.0, 0.0
        env.pa[:] = (6.0, -3.0)
        env.pb[:] = (6.0, 3.0)
        env.ph[:] = 2.6
        env.modo[:] = E.FIJADO
        env.visto_alguna[:] = True
        env.pf_on[:] = True
        rng = np.random.default_rng(1)
        env.pf_x[0] = rng.uniform(2.0, 10.0, E.NP_PF)
        env.pf_y[0] = rng.uniform(-2.5, 2.5, E.NP_PF)
        env.pf_vx[:] = env.pf_vy[:] = 0.0
        env.pf_w[:] = 1.0 / E.NP_PF
        return env

    def test_informacion_negativa_deja_la_masa_detras_del_muro(self):
        env = self._nube_con_muro()
        th = np.radians(-15.0)
        masa = lambda m_: env.pf_w[0][m_(env.pf_x[0], env.pf_y[0])].sum()
        en_cono = lambda x, y: (x > 3.5) & (x < 5.8) & (np.abs(y) < 0.3 * x)      # lo que la cámara ve, sin tapar
        detras = lambda x, y: x > 6.0
        m0 = masa(detras)
        for _ in range(10):                                     # la cámara ve el lado abierto y no detecta a nadie
            env._particulas(np.array([False]), np.array([np.cos(th)]), np.array([np.sin(th)]), np.ones(1), np.zeros(1))
        self.assertLess(masa(en_cono), 0.05)                    # donde mira y no hay nadie, ya no hay hipótesis
        self.assertGreater(masa(detras), m0 + 0.15)             # detrás del muro (no se ve) la masa crece

    def test_las_particulas_no_atraviesan_muros(self):
        env = self._nube_con_muro()
        env.pf_x[0], env.pf_y[0] = 5.8, 0.0
        env.pf_vx[0], env.pf_vy[0] = 4.0, 0.0                   # todas corren hacia el muro
        for _ in range(5):
            env._particulas(np.array([False]), np.ones(1), np.zeros(1), -np.ones(1), np.zeros(1))
        self.assertTrue(np.all(env.pf_x[0] < 6.0))

    def test_anticenit_y_distancia_adaptativa(self):
        # el ladrón corre a 3.4 m/s directo hacia el dron: la separación mínima sube por encima de la zona ciega y la nariz
        # gira hacia el punto de salida cuando va a pasar por debajo
        env = E.EntornoDronPersona(1, semilla=2, nivel=0)
        env.dx[:], env.dy[:], env.dz[:], env.psi[:] = 0.0, 0.0, 2.3, 0.0
        env.dvx[:] = env.dvy[:] = 0.0
        env.ap.sincronizar(env, np.ones(1, bool))
        env.activa[:, 1:] = False
        env.modo[:] = E.FIJADO
        env.visto_alguna[:] = True
        env.px[:, 0], env.py[:, 0] = 6.0, 0.3
        env.v_forzada[:, 0] = (-3.4, 0.0)
        env.l_guion[:] = E.L_GUION_TACTICO
        env.cam_pitch[:] = env.gimbal[:] = env.gimbal_cmd[:] = -15.0
        env.gb.reset(np.ones(1, bool), -15.0)
        vio_sep, vio_acn = 0.0, False
        for _ in range(20):
            env.step(np.zeros(1, int), np.full(1, QUIETO), auto_reset=False)
            vio_sep = max(vio_sep, env.d_sep[0] - env.d_ciego[0])
            vio_acn |= bool(env.anticenit[0])
        self.assertGreater(vio_sep, 1.0)
        self.assertTrue(np.all(env.cam_pitch >= E.GIMBAL_MIN - 1e-6))


class TestFaseC(unittest.TestCase):
    """Identidad: cambio de ID en cruces, RECONFIRMAR con el operador y ninguna persecución equivocada sin dudar."""

    def _cruce(self, parecido, semilla=0, n=64):
        """Ladrón fijado a 8 m caminando a +y; un civil igual de rápido le pasa por delante en la imagen."""
        env = E.EntornoDronPersona(n, semilla=semilla, nivel=0)
        env.dx[:], env.dy[:], env.dz[:], env.psi[:] = 0.0, 0.0, 3.0, 0.0
        env.activa[:] = False
        env.activa[:, :2] = True
        env.px[:, 0], env.py[:, 0] = 8.0, -2.0
        env.px[:, 1], env.py[:, 1] = 7.0, 2.0
        env.v_forzada[:, 0] = (0.0, 1.2)
        env.v_forzada[:, 1] = (0.0, -1.2)
        u = np.zeros(E.DIM_APARIENCIA)
        u[0] = 1.0
        w = np.zeros(E.DIM_APARIENCIA)
        w[1] = 1.0
        env.apariencia[:, 0] = u
        env.apariencia[:, 1] = parecido * u + np.sqrt(1 - parecido ** 2) * w
        env.modo[:] = E.FIJADO
        env.visto_alguna[:] = True
        env.lock[:] = True
        env.trk[:] = 0
        env.cam_pitch[:] = env.gimbal[:] = env.gimbal_cmd[:] = -14.0
        env.gb.reset(np.ones(n, bool), -14.0)
        return env

    def test_cambio_y_reconfirmacion(self):
        env = self._cruce(0.97)
        cambios = reconf = nodet = 0
        for _ in range(80):
            _, _, _, info = env.step(np.zeros(env.n, int), np.full(env.n, QUIETO), auto_reset=False)
            cambios += int(info["cambio"].sum())
            reconf += int(info["reconf"].sum())
            nodet += int(info["cambio_nodet"].sum())
        self.assertGreater(cambios, 0, "con alguien casi igual y el mismo paso, el tracker debería confundirse a veces")
        self.assertGreater(reconf, 0)
        self.assertEqual(nodet, 0)
        self.assertTrue(np.all((env.trk == 0) | (env.modo == E.RECONFIRMAR)))   # el operador lo devolvió al ladrón

    def test_alguien_muy_distinto_casi_no_confunde(self):
        env = self._cruce(0.2)
        cambios = 0
        for _ in range(80):
            _, _, _, info = env.step(np.zeros(env.n, int), np.full(env.n, QUIETO), auto_reset=False)
            cambios += int(info["cambio"].sum())
        self.assertLessEqual(cambios, 2)

    def test_la_red_no_decide_en_reconfirmar(self):
        env = self._cruce(0.97)
        env.modo[:] = E.RECONFIRMAR
        self.assertFalse(env.mascara_decision().any())


class TestFaseD(unittest.TestCase):
    """Secuencia tras el muro y sentido del giro."""

    def test_sentido_del_giro_hacia_la_zona_oculta(self):
        # rumbo +x; la zona oculta a la izquierda (+y) -> gira a la izquierda (-1); a la derecha (-y) -> a la derecha (+1)
        env = E.EntornoDronPersona(2, semilla=0, nivel=1)
        env.psi[:] = 0.0
        env.pf_on[:] = False
        env.int_dx[:], env.int_dy[:] = 0.0, (1.0, -1.0)
        env._girar_hacia_interior(np.ones(2, bool))
        self.assertEqual(env.busca_dir.tolist(), [-1.0, 1.0])
        # con la nube encendida manda la nube (su masa queda a la derecha)
        env.pf_on[:] = True
        env.dx[:], env.dy[:] = 0.0, 0.0
        env.pf_mx[:], env.pf_my[:] = 3.0, -4.0
        env._girar_hacia_interior(np.ones(2, bool))
        self.assertEqual(env.busca_dir.tolist(), [1.0, 1.0])

    def test_punto_de_canto(self):
        env = E.EntornoDronPersona(1, semilla=0, nivel=1)
        env.dx[:], env.dy[:] = -8.0, 0.0
        env.muro_a[0], env.muro_b[0] = (0.0, -3.0), (0.0, 3.0)
        self.assertTrue(env._planear_canto(0))
        P = np.array([env.inv_x[0], env.inv_y[0]])
        self.assertAlmostEqual(abs(P[0]), 0.0, delta=1e-6)                 # en la prolongación del muro
        self.assertAlmostEqual(abs(P[1]), 3.0 + E.A_CANTO, delta=1e-6)    # a A_CANTO de la punta
        mira = np.array([np.cos(env.canto_psi0[0]), np.sin(env.canto_psi0[0])])
        self.assertAlmostEqual(abs(mira[1]), 1.0, delta=1e-6)              # mirando a lo largo del muro
        self.assertEqual(env.paso_muro[0], 3)
        self.assertGreaterEqual(env.canto_gmb[0], E.GIMBAL_MIN)

    def test_canto_desplazamiento_lateral(self):
        # centrado -> DESPL_CANTO hacia el lado de la predicción -> DESPL_CANTO al otro, con la nariz a lo largo del muro
        for lado_pred in (1.0, -1.0):
            env = E.EntornoDronPersona(1, semilla=0, nivel=2)
            env.activa[:] = False
            env.px[:] = env.py[:] = 999.0
            env.pa[:] = env.muro_a[0] = (0.0, -3.0)
            env.pb[:] = env.muro_b[0] = (0.0, 3.0)
            P = np.array([0.0, -3.0 - E.A_CANTO])
            env.dx[:], env.dy[:] = P
            env.pf_on[:] = False
            env.ult_x[:], env.ult_y[:] = -2.0 * lado_pred, 2.0     # mirando hacia +y, la izquierda del muro es -x
            self.assertTrue(env._planear_canto(0))
            self.assertEqual(env.canto_lado[0], lado_pred)
            env.psi[:] = env.canto_psi0
            env.dz[:] = E.Z_SEGURA
            env.ap.sincronizar(env, np.ones(1, bool))
            env.modo[:] = E.MURO_CANTO
            env.canto_t[:] = 0.0
            env.t_modo[:] = 5.0
            nrm = np.array([-np.sin(env.canto_psi0[0]), np.cos(env.canto_psi0[0])])
            lat, err_psi = [], []
            for _ in range(int(E.T_CANTO / E.DT) - 1):
                env.step(np.zeros(1, int), np.full(1, QUIETO), auto_reset=False)
                lat.append(float(np.dot(nrm, [env.dx[0] - P[0], env.dy[0] - P[1]])))
                err_psi.append(abs(float(E.envolver(env.psi[0] - env.canto_psi0[0]))))
            lat = np.array(lat) * lado_pred
            self.assertGreater(lat.max(), 0.8 * E.DESPL_CANTO)                 # primero hacia el lado de la predicción
            self.assertLess(lat.min(), -0.8 * E.DESPL_CANTO)                   # y después al otro
            self.assertLess(int(np.argmax(lat)), int(np.argmin(lat)))
            self.assertLess(max(err_psi), np.radians(5))                      # sin barrido de guiñada

    def test_secuencia_completa_sin_ladron(self):
        # nadie detrás del muro: lado proyectado -> otro extremo -> canto -> 360°, sin chocar
        env = E.EntornoDronPersona(1, semilla=3, nivel=2)
        env.dx[:], env.dy[:], env.dz[:], env.psi[:] = -6.0, 0.0, 3.3, 0.0
        env.lock[:] = False
        env.kf_ok[:] = False
        env.pa[:] = (0.0, -3.0)
        env.pb[:] = (0.0, 3.0)
        env.activa[:] = False
        env.px[:] = env.py[:] = 999.0
        env.modo[:] = E.FIJADO
        env.visto_alguna[:] = True
        env.ult_x[:], env.ult_y[:] = 1.0, 1.0
        env.lid_ok[0, :13] = True
        env.lid_px[0, :13], env.lid_py[0, :13] = 0.0, np.linspace(-3, 3, 13)
        env.lid_i[:] = 13
        env._planear_perdida(0)
        env.modo[:] = E.INVESTIGAR
        vistos = []
        for _ in range(700):
            _, _, done, info = env.step(np.zeros(1, int), np.full(1, QUIETO), auto_reset=False)
            vistos.append(int(env.modo[0]))
            self.assertFalse(info["panel"][0])
            if done[0]:
                break
        for m in (E.INVESTIGAR, E.ASOMO, E.MURO_CANTO):
            self.assertIn(m, vistos)
        i_c = vistos.index(E.MURO_CANTO)
        self.assertIn(E.ASOMO, vistos[i_c:])                                 # después del canto, el 360°


class TestFaseE(unittest.TestCase):
    """Rendición con contador continuo, 5 niveles, ataques desde el nivel 2 y criterios del currículo."""

    def _fijado(self, nivel=0, n=4):
        env = E.EntornoDronPersona(n, semilla=5, nivel=nivel)
        return env

    def test_contador_continuo_pausa_reinicia_y_rinde(self):
        env = self._fijado()
        env.reserva[:] = 0.5                                      # T_rinde = 20 + 50 = 70 s
        env.t_cont[:] = 69.95
        env.modo[:] = E.FIJADO
        env.lock[:] = True
        env.trk[:] = 0
        env.info_sensor["lock"][:] = True
        _, _, done, info = env.step(np.zeros(env.n, int), np.full(env.n, QUIETO), auto_reset=False)
        # el que siguió viéndolo se rinde; la rendición es el éxito de la misión
        rinde = info["exito"]
        self.assertTrue(np.all(rinde == env.rendido))
        # pausa: en PÉRDIDA no suma ni se borra; reinicio: al pasar a la búsqueda vuelve a cero
        env2 = self._fijado()
        env2.t_cont[:] = 30.0
        env2.modo[:] = E.PREDECIR
        env2.lock[:] = False
        env2.t_pred_dur[:] = 99.0
        env2.step(np.zeros(env2.n, int), np.full(env2.n, QUIETO), auto_reset=False)
        self.assertTrue(np.all((env2.t_cont == 30.0) | (env2.modo == E.FIJADO)))
        env2.modo[:] = E.ASOMO
        env2.lock[:] = False
        env2.step(np.zeros(env2.n, int), np.full(env2.n, QUIETO), auto_reset=False)
        self.assertTrue(np.all((env2.t_cont == 0.0) | (env2.modo == E.FIJADO)))

    def test_tope_de_5_minutos(self):
        self.assertEqual(E.PASOS_EPISODIO, int(300.0 / E.DT))
        self.assertEqual((E.T_RINDE_BASE, E.T_RINDE_RESERVA), (20.0, 100.0))

    def test_cinco_niveles(self):
        self.assertEqual(E.N_NIVELES, 5)
        for nv, (muros, civiles, fijado) in enumerate([((0,), (0,), True), ((0,), (1,), True), ((1,), (0,), False),
                                                       ((1,), (1,), False), ((3, 4), (0, 1, 2), False)]):
            env = E.EntornoDronPersona(120, semilla=nv, nivel=nv)
            self.assertTrue(set(len(env.paneles(i)) for i in range(env.n)) <= set(muros), nv)
            self.assertTrue(set(env.activa[:, 1:].sum(1).tolist()) <= set(civiles), nv)
            self.assertEqual(bool((env.modo == E.FIJADO).all()), fijado, nv)
            self.assertEqual(env.obs_persona().shape[1], E.OBS_PERSONA)

    def test_sin_ataques_en_los_niveles_0_y_1(self):
        rng = np.random.default_rng(6)
        for nv in (0, 1):
            env = E.EntornoDronPersona(48, semilla=nv, nivel=nv)
            env.p_cenit = 1.0
            env.reset(np.ones(env.n, bool))
            for _ in range(400):
                env.step(rng.integers(0, len(E.CLASES), env.n), np.full(env.n, QUIETO))
                self.assertFalse(np.any(env.l_modo == E.L_ATACAR))
                self.assertFalse(np.any(env.salto_h > 0))

    def test_criterios_del_curriculo(self):
        from entrenar_master import CRITERIOS, evaluar_criterios
        base = dict(rinde=True, cenit=False, nivel=1, tiempo=False, idok=99.0, desig=100.0, nodet=0, choque=False, readq=5.0)
        ok = [dict(base) for _ in range(100)]
        self.assertTrue(evaluar_criterios(1, ok)[1])
        mal = [dict(base) for _ in range(100)]
        mal[0]["nodet"] = 1                                     # un solo cambio sin detectar bloquea el nivel 1
        self.assertFalse(evaluar_criterios(1, mal)[1])
        self.assertEqual(set(CRITERIOS), {0, 1, 2, 3})
