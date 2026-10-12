# -*- coding: utf-8 -*-
"""Pruebas del visor V16 (sesión B): recursos, módulos, servidor y repeticiones de prueba con el contrato de foto()."""
import json
import math
import os
import re
import subprocess
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.normpath(os.path.join(AQUI, ".."))
sys.path.insert(0, SIM)


class TestRecursos(unittest.TestCase):
    def test_three_y_complementos(self):
        for r in ["recursos/three/three.module.min.js", "recursos/three/three.core.min.js",
                  "recursos/three/addons/controls/OrbitControls.js", "recursos/three/addons/loaders/HDRLoader.js",
                  "recursos/three/addons/utils/BufferGeometryUtils.js", "recursos/cielo/spruit_sunrise_1k.hdr",
                  "recursos/LICENCIAS.md"]:
            self.assertTrue(os.path.isfile(os.path.join(SIM, r)), r)

    def test_texturas(self):
        for n in ["pasto", "tierra", "concreto_muro", "concreto_piso"]:
            for s in ["color", "normal", "rugosidad"]:
                self.assertTrue(os.path.isfile(os.path.join(SIM, "recursos/texturas/%s_%s.jpg" % (n, s))), n + s)

    def test_importaciones_resuelven(self):
        """Cada import de visor/*.js apunta a un archivo que existe (con el importmap de index.html)."""
        html = open(os.path.join(SIM, "index.html"), encoding="utf-8").read()
        mapa = json.loads(re.search(r'<script type="importmap">(.*?)</script>', html, re.S).group(1))["imports"]
        self.assertIn('src="visor/principal.js"', html)
        for f in os.listdir(os.path.join(SIM, "visor")):
            if not f.endswith(".js"):
                continue
            txt = open(os.path.join(SIM, "visor", f), encoding="utf-8").read()
            for m in re.finditer(r'from\s+"([^"]+)"', txt):
                ruta = m.group(1)
                if ruta == "three":
                    destino = os.path.join(SIM, mapa["three"])
                elif ruta.startswith("three/addons/"):
                    destino = os.path.join(SIM, mapa["three/addons/"], ruta[len("three/addons/"):])
                else:
                    destino = os.path.join(SIM, "visor", ruta)
                self.assertTrue(os.path.isfile(os.path.normpath(destino)), "%s importa %s" % (f, ruta))

    def test_gimbal_en_el_visor(self):
        """Regla dura 1 también al dibujar: el visor limita el gimbal a -45..+15."""
        util = open(os.path.join(SIM, "visor", "util.js"), encoding="utf-8").read()
        self.assertIn("GIMBAL_MIN = -45, GIMBAL_MAX = 15", util)
        dron = open(os.path.join(SIM, "visor", "dron.js"), encoding="utf-8").read()
        self.assertIn("limitar(e.gmb ?? -10, GIMBAL_MIN, GIMBAL_MAX)", dron)

    def test_servidor_tipos(self):
        import servidor_visor
        self.assertEqual(servidor_visor.TIPOS[".js"], "text/javascript")


class TestRepeticionPrueba(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, os.path.join(SIM, "herramientas", "repeticion_prueba_v16.py")], check=True,
                       stdout=subprocess.DEVNULL)
        with open(os.path.join(SIM, "replays_prueba", "demo_v16_mision.json"), encoding="utf-8") as f:
            cls.d = json.load(f)

    def test_contrato_v16(self):
        for c in self.d["cuadros"]:
            self.assertIn("alt_obj", c)
            self.assertIn("cam_piso", c)
            for p in c["pers"]:
                for k in ("pos", "pt", "salto", "mira", "civ"):
                    self.assertIn(k, p)
                self.assertIn(p["pos"], (0, 1, 2, 3))
                self.assertTrue(0.0 <= p["pt"] <= 1.0)
                self.assertIn(p["salto"][0], (0, 1, 2, 3, 4))
                if p["rol"] == "peaton":
                    self.assertIn(p["civ"], (0, 1, 2, 3, 4))

    def test_reglas_duras(self):
        for c in self.d["cuadros"]:
            self.assertTrue(-45.0 <= c["gmb"] <= 15.0)
            cerca = any(math.hypot(p["p"][0] - c["d"][0], p["p"][1] - c["d"][1]) < 8.0 for p in c["pers"])
            if cerca:
                self.assertGreaterEqual(c["alt_obj"], 3.30)
            self.assertLessEqual(max(abs(c["d"][0]), abs(c["d"][1])), 25.0)

    def test_hay_todo_lo_que_hay_que_dibujar(self):
        posturas = {p["pos"] for c in self.d["cuadros"] for p in c["pers"] if p["rol"] == "ladron"}
        self.assertEqual(posturas, {0, 1, 2, 3})
        self.assertEqual({p["salto"][0] for c in self.d["cuadros"] for p in c["pers"]}, {0, 1, 2, 3, 4})
        self.assertEqual({p["civ"] for c in self.d["cuadros"] for p in c["pers"] if p["rol"] == "peaton"}, {0, 1, 2, 3, 4})
        self.assertTrue(any(c["cam_piso"] for c in self.d["cuadros"]))
        self.assertTrue(any(c["op"] == 1 for c in self.d["cuadros"]))


if __name__ == "__main__":
    unittest.main()
