# -*- coding: utf-8 -*-
"""Pruebas del mínimo indispensable (minimo_tesis/): independencia, qué hace y qué NO hace el sistema, y el protocolo."""
import glob
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from minimo_tesis import protocolo_comite as P  # noqa: E402
from minimo_tesis import sensores as S  # noqa: E402
from minimo_tesis import sistema as M  # noqa: E402

AQUI = os.path.join(os.path.dirname(__file__), "..", "minimo_tesis")


def medida(n, lid=30.0, det=False, d=50.0, rumbo=0.0, v_av=0.0, dz=2.3):
    """Medida sintética para la lógica (sin el mundo)."""
    return dict(det=np.full(n, det), d=np.full(n, d), rumbo=np.full(n, rumbo), frac=np.ones(n), lid=np.full(n, lid),
                v_av=np.full(n, v_av), dz=np.full(n, dz), psi=np.zeros(n))


class TestIndependencia(unittest.TestCase):
    def test_no_importa_el_entorno_de_entrenamiento(self):
        # copia congelada: no depende de entorno.py, mision.py ni entrenar_master.py (que cambian con el entrenamiento)
        for ruta in glob.glob(os.path.join(AQUI, "*.py")):
            with open(ruta, encoding="utf-8") as fh:
                txt = fh.read()
            for mod in ("entorno", "mision", "entrenar_master", "entrenar"):
                self.assertNotIn("import %s" % mod, txt, ruta)
                self.assertNotIn("from %s " % mod, txt, ruta)

    def test_gimbal_dentro_del_limite_duro(self):
        g = M.GimbalBaseCam(3, M.GIMBAL_FRONTAL)
        for c in (-120.0, 60.0, M.GIMBAL_FRONTAL):
            for _ in range(80):
                a = g.paso(np.full(3, c), np.full(3, 25.0), M.DT)
                self.assertTrue(((a >= -45.0) & (a <= 15.0)).all())


class TestSistema(unittest.TestCase):
    def test_sin_riesgo_manda_el_piloto(self):
        s = M.SistemaMinimo(2)
        vx, vy, vz, nuevo = s.actualizar(medida(2, v_av=2.0), np.full(2, 2.0), *[np.zeros(2, bool)] * 3, np.full(2, 2.3))
        self.assertTrue(np.allclose(vx, 2.0) and np.allclose(vy, 0.0))
        self.assertFalse(s.interviene.any() or nuevo.any())

    def test_obstaculo_detencion_y_ascenso_sin_esquivar(self):
        s = M.SistemaMinimo(1)
        no = np.zeros(1, bool)
        vx, vy, vz, nuevo = s.actualizar(medida(1, lid=4.0, v_av=3.0), np.full(1, 3.0), no, no, no, np.full(1, 2.3))
        self.assertTrue(nuevo[0] and s.interviene[0] and s.motivo[0] == 1)
        self.assertEqual((vx[0], vy[0]), (0.0, 0.0))                 # detención: nada lateral, nada de navegar
        self.assertGreater(vz[0], 0.0)                                # ascenso vertical
        # retenida: aunque el riesgo desaparezca y el piloto empuje, sigue detenido hasta que el operador reanuda
        vx, vy, vz, _ = s.actualizar(medida(1), np.full(1, 3.0), no, no, no, np.full(1, 2.8))
        self.assertEqual(vx[0], 0.0)
        vx, vy, vz, _ = s.actualizar(medida(1), np.full(1, 3.0), no, no, np.ones(1, bool), np.full(1, 3.3))
        self.assertFalse(s.interviene[0])
        self.assertAlmostEqual(vx[0], 3.0)

    def test_persona_acercandose(self):
        s = M.SistemaMinimo(1)
        no = np.zeros(1, bool)
        for k in range(50):                                           # se acerca a 1.4 m/s desde 12 m
            _, _, _, nuevo = s.actualizar(medida(1, det=True, d=12.0 - 0.14 * k), np.zeros(1), no, no, no, np.full(1, 2.3))
            if s.interviene[0]:
                break
        self.assertTrue(s.interviene[0])
        self.assertEqual(s.motivo[0], 2)
        self.assertLess(np.hypot(s.rel_x[0], s.rel_y[0]), M.D_AMENAZA)   # nunca antes de los 8 m (regla dura)

    def test_operador_manda_siempre(self):
        s = M.SistemaMinimo(1)
        si, no = np.ones(1, bool), np.zeros(1, bool)
        # ANULAR: con riesgo, el piloto conserva el mando
        vx, vy, vz, _ = s.actualizar(medida(1, lid=2.0, v_av=1.0), np.full(1, 1.0), no, si, no, np.full(1, 2.3))
        self.assertAlmostEqual(vx[0], 1.0)
        # PARADA (CH8): frena aunque no haya riesgo
        s2 = M.SistemaMinimo(1)
        vx, vy, vz, _ = s2.actualizar(medida(1), np.full(1, 2.0), si, no, no, np.full(1, 2.3))
        self.assertEqual((vx[0], vy[0], vz[0]), (0.0, 0.0, 0.0))

    def test_desactivado_no_interviene(self):
        s = M.SistemaMinimo(1, activo=False)
        no = np.zeros(1, bool)
        vx, _, _, nuevo = s.actualizar(medida(1, lid=1.0, v_av=2.0), np.full(1, 2.0), no, no, no, np.full(1, 2.3))
        self.assertFalse(nuevo[0])
        self.assertAlmostEqual(vx[0], 2.0)


class TestSensores(unittest.TestCase):
    def test_lidar_ve_el_panel_y_descarta_lo_lejano(self):
        rng = np.random.default_rng(0)
        z = np.zeros(1)
        med, real, que = S.lidar(rng, np.full(1, -5.0), z, np.full(1, 2.3), z, np.full(1, M.GIMBAL_FRONTAL), np.full(1, 99.0),
                                 z, np.full(1, 1.7), np.zeros(1, bool), [P.PANEL])
        self.assertEqual(que[0], 2)
        self.assertAlmostEqual(real[0], 5.0 / np.cos(np.radians(5.0)), delta=0.01)

    def test_retardo_de_100_ms(self):
        w = M.Mundo(1, 0)
        a = w.medir()
        w.paso(np.ones(1), np.zeros(1), np.zeros(1))
        b = w.medir()
        self.assertIs(b, w.cola[0])
        self.assertIsNot(b, w.ultima)                                 # la lógica recibe la medida anterior


class TestProtocolo(unittest.TestCase):
    def test_protocolo_corto(self):
        for nom, e in P.ESCENARIOS.items():
            s, _ = P.correr(nom, 8, 7, False)
            r, cuadros = P.correr(nom, 8, 7, True, grabar=True, cf=s)
            self.assertEqual(r["choque"].sum(), 0, nom)
            if e[2]:
                self.assertTrue(r["activo"].all(), nom)
            else:
                self.assertFalse(r["activo"].any(), nom)              # cruza lejos / pasa de lado: sin falsos positivos
            self.assertTrue(all(c["fase"] == 1 for c in cuadros))     # formato del visor: piloto al mando

    def test_condiciones_degradadas(self):
        # nominal explícito = nominal por defecto (el azar de las degradaciones va aparte)
        a, _ = P.correr("b_quieta_3.0", 6, 5, True)
        b, _ = P.correr("b_quieta_3.0", 6, 5, True, cond=S.Condicion())
        self.assertTrue(np.array_equal(a["d_min_h"], b["d_min_h"]))
        # sin detecciones (recall 0) no hay activación ante la persona: la degradación sí llega a la lógica
        r, _ = P.correr("b_quieta_1.5", 4, 5, True, cond=S.Condicion("ciega", recall=0.0))
        self.assertFalse(r["activo"].any())
        # el retardo configurable cambia la medida que recibe la lógica
        w = M.Mundo(1, 0, cond=S.Condicion(retardo=3))
        ms = [w.medir() for _ in range(5)]
        self.assertIs(ms[-1], w.cola[0])
        self.assertEqual(len(w.cola), 4)

    def test_velocidad_maxima_segura_tiene_limite(self):
        # el barrido debe encontrar dónde deja de detenerse con margen (persona quieta: el tope de 8 m de la regla dura)
        r, _ = P.correr("b_quieta_1.5", 20, 9, True, v=12.0)
        self.assertLess(P.detiene_con_margen("b_quieta_1.5", r).mean(), 0.95)
        r, _ = P.correr("b_quieta_1.5", 20, 9, True, v=2.0)
        self.assertTrue(P.detiene_con_margen("b_quieta_1.5", r).all())

    def test_mismas_semillas_mismos_numeros(self):
        a, _ = P.correr("a_panel_3", 6, 11, True)
        b, _ = P.correr("a_panel_3", 6, 11, True)
        self.assertTrue(np.array_equal(a["d_min"], b["d_min"]))


if __name__ == "__main__":
    unittest.main()
