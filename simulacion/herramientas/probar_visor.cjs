// Prueba del visor V16 en un navegador sin pantalla (Chromium + Playwright): abre la página, espera a que cargue,
// toma capturas en varios instantes, mide los cuadros por segundo y lista los errores de la consola.
// Uso (con el servidor del visor corriendo en el puerto 8765):
//   NODE_PATH=$(npm root -g) node herramientas/probar_visor.cjs [salida_dir] [repeticion] [t1,t2,...] [ancho]x[alto]
// Ojo: sin tarjeta gráfica (render por software) los cuadros por segundo son mucho menores que en el portátil.
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

(async () => {
  const salida = process.argv[2] || "capturas";
  const rep = process.argv[3] || "replays_prueba/demo_v16_mision.json";
  const tiempos = (process.argv[4] || "3,12,24,36,42.5,43,60").split(",").map(Number);
  const [W, H] = (process.argv[5] || "1600x900").split("x").map(Number);
  const extra = process.argv[6] || "";
  fs.mkdirSync(salida, { recursive: true });
  const nav = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  const pag = await nav.newPage({ viewport: { width: W, height: H } });
  const errores = [];
  pag.on("console", m => { if (m.type() === "error" || m.type() === "warning") errores.push(`[${m.type()}] ${m.text()}`); });
  pag.on("pageerror", e => errores.push("[pageerror] " + e.message));
  await pag.goto(`http://127.0.0.1:8765/index.html?r=${encodeURIComponent(rep)}${extra}`);
  await pag.waitForFunction(() => document.getElementById("cargando").style.display === "none", null, { timeout: 120000 });
  // detiene el reloj y salta a cada instante para la captura
  for (const tt of tiempos) {
    await pag.evaluate(tt => window.__v16 && window.__v16.irA(tt), tt);
    await pag.waitForTimeout(1500);
    await pag.screenshot({ path: path.join(salida, `t${String(tt).replace(".", "_")}.png`) });
  }
  const fps = await pag.evaluate(() => window.__v16 ? window.__v16.fps() : null);
  console.log("cuadros por segundo (render por software):", fps && fps.toFixed(1));
  console.log(errores.length ? errores.slice(0, 30).join("\n") : "sin errores en la consola");
  await nav.close();
})().catch(e => { console.error(e); process.exit(1); });
