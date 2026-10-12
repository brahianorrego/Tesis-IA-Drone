// Visor V16 · estación de tierra (sesión B del plan docs/PLAN_V16_REALISMO.md).
// Un solo lienzo WebGL dibuja varias vistas en los marcos de la página: la cámara del dron, la vista externa y la cámara
// al piso. El reproductor avanza la partida; las figuras y el dron se interpolan entre cuadros.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { Mundo, CAPA_AYUDAS } from "./escena.js";
import { Dron } from "./dron.js";
import { Partida, listarRepeticiones, cargarJSON } from "./datos.js";
import { Personas } from "./personas.js";
import { Interfaz } from "./interfaz.js";
import { $, mundo, lerp, limitar, angNorm } from "./util.js";

// ------------------------------------------------------------------------------------------------ calidad y render
const CALIDAD = {
  alta: { pr: Math.min(devicePixelRatio, 1.5), sombras: 2048 },
  media: { pr: 1, sombras: 1024 },
  baja: { pr: 0.75, sombras: 512 },
};
let calidadSel = "auto", calidad = "alta";
try { calidadSel = localStorage.getItem("v16-calidad") || "auto"; } catch (e) {}
if (calidadSel !== "auto") calidad = calidadSel;

const renderer = new THREE.WebGLRenderer({ canvas: $("lienzo"), antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(CALIDAD[calidad].pr);
renderer.setSize(innerWidth, innerHeight, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.92;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.shadowMap.autoUpdate = false;           // una sola vez por cuadro, aunque se dibujen 3 vistas

export const M = new Mundo(renderer);
M.calidadSombras(CALIDAD[calidad].sombras);
const dron = new Dron();
M.escena.add(dron.raiz);
export const personas = new Personas(M.escena);
const ui = new Interfaz();

const camExt = new THREE.PerspectiveCamera(42, 16 / 9, 0.05, 900);
camExt.layers.enable(CAPA_AYUDAS);
camExt.position.set(-24, 8, 24);
let controles = new OrbitControls(camExt, $("v-1"));
controles.enableDamping = true;
controles.maxPolarAngle = Math.PI * 0.495;
controles.minDistance = 1.0;

// ------------------------------------------------------------------------------------------------ vistas
// "grande" = qué se ve en el marco grande: la cámara del dron (como en vuelo) o la vista externa
const vistas = { grande: "camara", chica: "externa" };
let modoCam = "cine";
function marcoDe(tipo) { return vistas.grande === tipo ? $("v-grande") : tipo === vistas.chica ? $("v-1") : null; }
function intercambiar() {
  [vistas.grande, vistas.chica] = [vistas.chica, vistas.grande];
  controles.disconnect();
  controles.connect(marcoDe("externa"));
  rotular();
}
function rotular() {
  const tCam = `Cámara del dron <span>· 38.9° · 640 × 480 · gimbal</span>`, tExt = `Vista externa <span>· simulación</span>`;
  $("t-grande").innerHTML = vistas.grande === "camara" ? tCam : tExt;
  $("t-1").innerHTML = vistas.chica === "camara" ? tCam : tExt;
  $("modos-ext").style.display = vistas.chica === "externa" ? "flex" : "none";
}
$("v-1").addEventListener("click", ev => { if (!ev.target.closest("button")) intercambiar(); });
document.querySelectorAll("[data-cam]").forEach(b => b.addEventListener("click", ev => {
  ev.stopPropagation();
  modoCam = b.dataset.cam;
  document.querySelectorAll("[data-cam]").forEach(x => x.classList.toggle("activo", x === b));
  if (modoCam === "arriba") { camExt.position.copy(mundo(estado ? estado.x : 0, estado ? estado.y - 6 : -6, 42)); }
}));
rotular();

function rectDe(el) {
  const r = el.getBoundingClientRect();
  return { x: r.left, y: innerHeight - r.bottom, w: r.width, h: r.height };
}
function dibujar(camara, r) {
  if (r.w < 4 || r.h < 4) return;
  renderer.setViewport(r.x, r.y, r.w, r.h);
  renderer.setScissor(r.x, r.y, r.w, r.h);
  renderer.render(M.escena, camara);
}
// la imagen de una cámara real (4:3) se encaja sin deformarse dentro del marco
export function encajar(r, aspecto) {
  let w = r.w, h = w / aspecto;
  if (h > r.h) { h = r.h; w = h * aspecto; }
  return { x: r.x + (r.w - w) / 2, y: r.y + (r.h - h) / 2, w, h };
}
// fase B1: las cámaras del dron se dibujan directo; la fase B3 las reemplaza por la imagen del sensor (camaras.js)
export const camarasDron = {
  principal: (r) => { const c = encajar(r, 4 / 3); dibujar(dron.camara, c); return c; },
  piso: (r) => { const c = encajar(r, 4 / 3); dibujar(dron.camaraPiso, c); return c; },
};
export { dron, renderer, camExt, ui };

// ------------------------------------------------------------------------------------------------ reproducción
let P = null, t = 0, pausa = false, vel = 1, estado = null, cargandoSig = false, esperaClic = null, confirmados = new Set();
let operadorManual = true, lenta = true, ayudas = true;
const tiemposSalto = [];
export const repro = {
  get partida() { return P; }, get t() { return t; }, get estado() { return estado; },
  get esperaClic() { return esperaClic; }, get operadorManual() { return operadorManual; },
  confirmar() {                       // el operador hizo clic sobre el sospechoso
    if (esperaClic === null) return;
    confirmados.add(esperaClic);
    esperaClic = null;
    $("confirmar").classList.remove("ver");
    ui.aviso("Sospechoso confirmado por el operador", "ok", 2.5);
  },
};

async function cargarPartida(ruta) {
  try {
    const datos = await cargarJSON(ruta);
    P = new Partida(datos, ruta);
  } catch (e) {
    ui.aviso("No se encontró la repetición " + ruta, "peligro", 5);
    return;
  }
  t = 0; esperaClic = null; confirmados = new Set();
  M.ponerParedes(P.paneles);
  personas.limpiar();
  ui.ponerPartida(P);
  tiemposSalto.length = 0;
  P.eventos.filter(v => v.salto).forEach(v => tiemposSalto.push(v.k * P.dt));
  M.renderer.shadowMap.needsUpdate = true;
  document.title = "DRON-IA · " + (P.d.titulo || P.d.version || "Estación de tierra");
}

async function llenarSelector() {
  const sel = $("selector"), actual = sel.value;
  const grupos = await listarRepeticiones();
  sel.innerHTML = grupos.map(g => `<optgroup label="${g.grupo}">${g.opciones.map(o => `<option value="${o.valor}">${o.texto}</option>`).join("")}</optgroup>`).join("");
  const valores = [...sel.options].map(o => o.value);
  const pedido = new URLSearchParams(location.search).get("r");
  if (actual && valores.includes(actual)) sel.value = actual;
  else if (pedido) sel.value = pedido;
  else if (valores.includes("replays_prueba/demo_v16_mision.json") && !valores.some(v => v.startsWith("salida/replay_v16"))) sel.value = "replays_prueba/demo_v16_mision.json";
  return sel.value;
}
$("selector").addEventListener("change", e => cargarPartida(e.target.value));

function alternarPausa() { pausa = !pausa; $("b-pausa").textContent = pausa ? "▶" : "❚❚"; $("b-pausa").classList.toggle("activo", pausa); }
$("b-pausa").addEventListener("click", alternarPausa);
$("velocidad").addEventListener("change", e => vel = +e.target.value);
$("pista").addEventListener("click", ev => {
  if (!P) return;
  const r = ev.currentTarget.getBoundingClientRect();
  t = limitar((ev.clientX - r.left) / r.width, 0, 1) * P.total;
  confirmados = new Set([...confirmados].filter(k => k * P.dt < t));
  esperaClic = null; $("confirmar").classList.remove("ver");
  ui.rastro = [];
});
$("b-operador").addEventListener("click", ev => {
  operadorManual = !operadorManual;
  ev.currentTarget.textContent = operadorManual ? "Operador: manual" : "Operador: automático";
  ev.currentTarget.classList.toggle("activo", operadorManual);
  if (!operadorManual) repro.confirmar();
});
$("b-ing").addEventListener("click", () => { $("ingenieria").classList.toggle("abierto"); $("b-ing").classList.toggle("activo"); });
$("b-ayudas").addEventListener("click", ev => { ayudas = !ayudas; ev.currentTarget.classList.toggle("activo", ayudas); ayudas ? camExt.layers.enable(CAPA_AYUDAS) : camExt.layers.disable(CAPA_AYUDAS); });
$("b-lenta").addEventListener("click", ev => { lenta = !lenta; ev.currentTarget.classList.toggle("activo", lenta); });
$("calidad").value = calidadSel;
$("calidad").addEventListener("change", ev => {
  calidadSel = ev.target.value;
  try { localStorage.setItem("v16-calidad", calidadSel); } catch (e) {}
  ponerCalidad(calidadSel === "auto" ? "alta" : calidadSel);
  fpsHist.length = 0;
});
$("cielo").addEventListener("change", ev => M.ponerCielo(ev.target.value));
addEventListener("keydown", ev => {
  if (ev.target.tagName === "SELECT") return;
  if (ev.code === "Space") { ev.preventDefault(); alternarPausa(); }
  if (ev.code === "KeyI") $("b-ing").click();
  if (ev.code === "KeyV") intercambiar();
});
function ponerCalidad(q) {
  calidad = q;
  renderer.setPixelRatio(CALIDAD[q].pr);
  renderer.setSize(innerWidth, innerHeight, false);
  M.calidadSombras(CALIDAD[q].sombras);
}
addEventListener("resize", () => renderer.setSize(innerWidth, innerHeight, false));

// ------------------------------------------------------------------------------------------------ cámara externa
const mira = new THREE.Vector3(), deseo = new THREE.Vector3(), miraDeseo = new THREE.Vector3();
let ladoCine = 1;
function saltoCerca(tt) { return tiemposSalto.find(ts => tt > ts - 1.4 && tt < ts + 2.6); }
function moverCamaraExterna(e, dt) {
  const pd = mundo(e.x, e.y, e.z);
  const lad = e.personas.find(p => p.rol === "ladron");
  const pl = lad ? mundo(lad.x, lad.y, 1.0) : pd.clone().setY(0);
  const k = 1 - Math.exp(-dt * 2.2);
  if (modoCam === "libre") { controles.update(); return; }
  if (modoCam === "arriba") {
    deseo.copy(pd).add(new THREE.Vector3(0, 38, 9));
    camExt.position.lerp(deseo, k); mira.lerp(pd.clone().setY(0), k); camExt.lookAt(mira);
    controles.target.copy(mira);
    return;
  }
  if (modoCam === "seguir") {
    deseo.copy(pd).add(new THREE.Vector3(-Math.cos(e.psi) * 4.2, 1.4, Math.sin(e.psi) * 4.2));
    miraDeseo.copy(pd).add(new THREE.Vector3(Math.cos(e.psi) * 4, -1.2, -Math.sin(e.psi) * 4));
  } else {
    // automática: de lado respecto a la línea dron-sospechoso, con los dos en cuadro
    const ts = saltoCerca(t);
    const eje = new THREE.Vector3().subVectors(pl, pd).setY(0);
    const sep = Math.max(eje.length(), 1.5);
    eje.normalize();
    const lado = new THREE.Vector3(-eje.z, 0, eje.x);
    const aCam = new THREE.Vector3().subVectors(camExt.position, pd).setY(0);
    if (aCam.dot(lado) * ladoCine < -2) ladoCine *= -1;      // no cruzar el eje salvo que ya esté del otro lado
    const centro = pd.clone().lerp(pl, 0.5);
    if (ts !== undefined && lad) {
      // salto: plano bajo y cercano, de lado, mirando entre la mano y el dron
      const pj = mundo(lad.x, lad.y, 0);
      deseo.copy(pj).addScaledVector(lado, ladoCine * 4.6).addScaledVector(eje, -1.2).setY(0.75);
      miraDeseo.copy(pj).lerp(pd, 0.55).setY(lerp(1.2, e.z, 0.5));
    } else {
      const dist = 5.5 + sep * 0.9;
      deseo.copy(centro).addScaledVector(lado, ladoCine * dist).addScaledVector(eje, -dist * 0.35).setY(2.2 + sep * 0.22);
      miraDeseo.copy(centro).setY(lerp(1.0, e.z, 0.45));
    }
    // no meter la cámara dentro de un muro ni bajo el piso
    deseo.y = Math.max(deseo.y, 0.4);
  }
  camExt.position.lerp(deseo, k);
  mira.lerp(miraDeseo, k * 1.4);
  camExt.lookAt(mira);
  controles.target.copy(mira);
}

// ------------------------------------------------------------------------------------------------ bucle
const fpsHist = [];
let tPrevio = performance.now(), cuentaFps = 0, tFps = performance.now(), fps = 60;
const foco = new THREE.Vector3();
function bucle(ahora) {
  requestAnimationFrame(bucle);
  const dtReal = Math.min((ahora - tPrevio) / 1000, 0.1);
  tPrevio = ahora;
  cuentaFps++;
  if (ahora - tFps > 1000) {
    fps = cuentaFps * 1000 / (ahora - tFps); cuentaFps = 0; tFps = ahora;
    fpsHist.push(fps);
    if (calidadSel === "auto" && fpsHist.length >= 4) {
      const media = fpsHist.slice(-4).reduce((a, b) => a + b) / 4;
      if (media < 26 && calidad !== "baja") { ponerCalidad(calidad === "alta" ? "media" : "baja"); fpsHist.length = 0; }
    }
  }
  if (!P || !P.C.length) return;
  // ---- avance del tiempo (cámara lenta durante el salto; espera del clic del operador en modo manual)
  let factor = vel;
  if (lenta && tiemposSalto.some(ts => t > ts - 0.25 && t < ts + 1.9)) factor *= 0.3;
  if (!pausa && esperaClic === null) {
    const tn = t + dtReal * factor;
    const kc = operadorManual ? P.clics.find(k => !confirmados.has(k) && (k + 0.5) * P.dt >= t && (k + 0.5) * P.dt <= tn) : undefined;
    if (kc !== undefined) { t = (kc + 0.5) * P.dt; esperaClic = kc; $("confirmar").classList.add("ver"); }
    else t = tn;
  }
  if (t >= P.total) {
    t = P.total;
    if (!cargandoSig && !pausa) {
      cargandoSig = true;
      setTimeout(async () => { await cargarPartida($("selector").value); cargandoSig = false; }, 4000);
    }
  }
  const e = estado = P.muestra(t);
  const dtSim = pausa || esperaClic !== null ? 0 : dtReal * factor;
  // avisos de eventos que acaban de pasar
  if (bucle.kPrev !== undefined && e.k > bucle.kPrev) P.eventos.filter(v => v.k > bucle.kPrev && v.k <= e.k && v.marca).forEach(v => ui.aviso(v.txt, v.tipo));
  bucle.kPrev = e.k;
  // ---- mundo
  dron.actualizar(e, dtSim, ahora);
  personas.actualizar(e, dtSim, { dron: dron.raiz.position, ahora, t });
  foco.copy(dron.raiz.position).setY(0);
  const lad = e.personas.find(p => p.rol === "ladron");
  if (lad) foco.lerp(mundo(lad.x, lad.y), 0.5);
  M.actualizarSol(foco);
  moverCamaraExterna(e, dtReal);
  // ---- dibujo: fondo, y cada vista en su marco
  renderer.setScissorTest(false);
  renderer.setClearColor(0x0d0f12, 1);
  renderer.clear();
  renderer.setScissorTest(true);
  renderer.shadowMap.needsUpdate = true;
  const rExt = rectDe(marcoDe("externa"));
  camExt.aspect = rExt.w / Math.max(rExt.h, 1);
  camExt.updateProjectionMatrix();
  dibujar(camExt, rExt);
  renderer.shadowMap.needsUpdate = false;
  bucle.rCam = camarasDron.principal(rectDe(marcoDe("camara")), e, dtReal);
  bucle.rPiso = camarasDron.piso(rectDe($("v-piso")), e, dtReal);
  ui.actualizar(e, t, ahora, { fps, calidad });
  if (bucle.alDibujar) bucle.alDibujar(e, dtReal);
}
export { bucle };

// ------------------------------------------------------------------------------------------------ arranque
export async function arrancar() {
  await M.ponerCielo("amanecer");
  const ruta = await llenarSelector();
  if (ruta) await cargarPartida(ruta);
  $("cargando").style.display = "none";
  requestAnimationFrame(bucle);
  setInterval(llenarSelector, 30000);          // aparecen las repeticiones nuevas del entrenamiento
}
// gancho para la prueba automática (herramientas/probar_visor.cjs)
window.__v16 = {
  irA(tt) { t = tt; esperaClic = null; confirmados = new Set(P ? P.clics : []); if (!pausa) alternarPausa(); },
  fps: () => fps,
  vista(tipo) { if (vistas.grande !== tipo) intercambiar(); },
  modo(m) { const b = document.querySelector(`[data-cam="${m}"]`); if (b) b.click(); },
};
if (!window.__V16_SIN_ARRANQUE) arrancar();
