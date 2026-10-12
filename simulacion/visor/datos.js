// Repeticiones: lista, carga, interpolación entre cuadros (10 Hz -> 60 Hz) y eventos para la bitácora del operador.
// Lee las repeticiones de la V15 (foto() de entorno.py) y los campos nuevos de la V16 (contrato del plan, fase A5):
// pos, pt, salto, mira, civ, alt_obj, cam_piso. Si un campo no viene, se deduce de los demás.
import { lerp, lerpAng } from "./util.js";

export async function cargarJSON(ruta) {
  const r = await fetch(ruta + (ruta.includes("?") ? "&" : "?") + "t=" + Date.now(), { cache: "no-store" });
  if (!r.ok) throw new Error(ruta);
  return r.json();
}

const NIVELES_TXT = ["Duelo abierto", "Muro único", "Ruido visual", "Misión completa", "Misión con ataques"];

// grupos de opciones para el selector: [{grupo, opciones: [{valor, texto, deshabilitada}]}]
export async function listarRepeticiones() {
  const grupos = [];
  let est = null, hitos = [], pruebas = [];
  try { est = await cargarJSON("salida/estado.json"); } catch (e) {}
  try { hitos = await cargarJSON("salida/hitos/lista.json"); } catch (e) {}
  try { pruebas = await cargarJSON("replays_prueba/lista.json"); } catch (e) {}
  if (est) {
    const rn = est.replays_nivel || {}, nombres = est.niveles || NIVELES_TXT, op = [];
    if (est.replay_v16) op.push({ valor: "salida/" + est.replay_v16, texto: "Misión V16 · en vivo" });
    nombres.forEach((nm, k) => { if (rn[k] !== undefined) op.push({ valor: `salida/replay_nivel_${k}.json`, texto: `Nivel ${k} · ${nm} · en vivo (it ${rn[k]})` }); });
    op.push({ valor: "salida/replay_mision.json", texto: "Misión completa · en vivo" + (rn.mision !== undefined ? ` (it ${rn.mision})` : "") });
    grupos.push({ grupo: "Entrenamiento en vivo", opciones: op });
  }
  if (hitos.length) grupos.push({ grupo: "Hitos del entrenamiento", opciones: hitos.slice().reverse().slice(0, 30).map(h => ({
    valor: "salida/hitos/" + h.archivo, texto: `${h.nivel !== undefined && !h.mision ? `Nivel ${h.nivel} · ` : ""}it ${h.it} · ${(h.pasos / 1e6).toFixed(1)} M${h.mision ? " · misión" : ""}` })) });
  if (pruebas.length) grupos.push({ grupo: "V16 · repeticiones de prueba", opciones: pruebas.map(p => ({ valor: "replays_prueba/" + p.archivo, texto: p.titulo })) });
  grupos.push({ grupo: "Proyecto de grado · mínimo indispensable", opciones: [
    ["replay_protocolo", "Protocolo del comité"], ["replay_protocolo_reglas", "Decisor: reglas"], ["replay_protocolo_ia", "Decisor: IA sola"],
    ["replay_protocolo_ia_env", "Decisor: IA + envolvente"], ["replay_protocolo_ia_env_estricta", "Decisor: IA + envolvente estricta"]]
    .map(([a, t]) => ({ valor: `minimo_tesis/replay/${a}.json`, texto: t })) });
  return grupos;
}

// ------------------------------------------------------------------------------------------------ partida
export class Partida {
  constructor(datos, ruta) {
    this.ruta = ruta;
    this.d = datos;
    this.C = datos.cuadros || [];
    this.dt = datos.dt || 0.1;
    this.total = Math.max(0, (this.C.length - 1) * this.dt);
    this.paneles = datos.paneles || [];
    this.obst = datos.obst || [];
    this.v16 = this.C.some(c => (c.pers || []).some(p => p.pos !== undefined) || c.alt_obj !== undefined);
    // normalización de repeticiones viejas: la persona única de la v4, la fase
    this.C.forEach(c => {
      if (!c.pers) c.pers = c.p ? [{ rol: datos.adversaria ? "ladron" : "peaton", p: c.p, v: c.pv || [0, 0], vis: c.vis, run: c.run }] : [];
      if (!c.fase) c.fase = 2;
      c.pers.forEach((p, j) => { if (p.id === undefined) p._k = (p.rol || "p") + j; });
    });
    // clics del operador: el cuadro anterior a op = 1 (en MANUAL la repetición espera el clic ahí)
    this.clics = [];
    this.C.forEach((c, k) => { if (k && c.op === 1) this.clics.push(k - 1); });
    this.eventos = calcularEventos(this);
  }
  clave(p) { return p.id !== undefined ? "id" + p.id : p._k; }

  // estado interpolado en el instante t (s)
  muestra(t) {
    const C = this.C, n = C.length;
    if (!n) return null;
    const kf = Math.max(0, Math.min(t / this.dt, n - 1));
    const k = Math.min(Math.floor(kf), Math.max(n - 2, 0)), f = n > 1 ? kf - k : 0;
    const a = C[k], b = C[Math.min(k + 1, n - 1)];
    const e = Object.assign({}, f < 0.5 ? a : b);
    e.k = k; e.f = f; e.t = t; e.a = a; e.b = b;
    e.x = lerp(a.d[0], b.d[0], f); e.y = lerp(a.d[1], b.d[1], f); e.z = lerp(a.d[2], b.d[2], f);
    e.psi = lerpAng(a.d[3], b.d[3], f);
    e.cp = lerp(a.cp ?? 0, b.cp ?? a.cp ?? 0, f); e.cr = lerp(a.cr ?? 0, b.cr ?? a.cr ?? 0, f);
    e.gmb = lerp(a.gmb ?? -10, b.gmb ?? a.gmb ?? -10, f);
    e.vx = lerp((a.dv || [0, 0])[0], (b.dv || [0, 0])[0], f); e.vy = lerp((a.dv || [0, 0])[1], (b.dv || [0, 0])[1], f);
    e.altObj = a.alt_obj !== undefined ? lerp(a.alt_obj, b.alt_obj ?? a.alt_obj, f) : null;
    const pb = new Map((b.pers || []).map(p => [this.clave(p), p]));
    e.personas = (a.pers || []).map(p => {
      const q = pb.get(this.clave(p)) || p;
      const s = q.salto || p.salto, sa = p.salto;
      return {
        clave: this.clave(p), rol: p.rol, id: p.id, est: p.est || 1.72,
        x: lerp(p.p[0], q.p[0], f), y: lerp(p.p[1], q.p[1], f),
        vx: lerp((p.v || [0, 0])[0], (q.v || [0, 0])[0], f), vy: lerp((p.v || [0, 0])[1], (q.v || [0, 0])[1], f),
        vis: f < 0.5 ? p.vis : q.vis, fv: p.fv, tap: p.tap, cand: p.cand, ign: p.ign, run: p.run,
        pos: (f < 0.5 ? p : q).pos, pt: p.pt !== undefined ? (q.pos === p.pos ? lerp(p.pt, q.pt ?? p.pt, f) : (f < 0.5 ? p.pt : q.pt)) : undefined,
        mira: p.mira !== undefined ? lerpAng(p.mira, q.mira ?? p.mira, f) : undefined,
        civ: (f < 0.5 ? p : q).civ,
        salto: sa ? [(f < 0.5 ? sa : s)[0], lerp(sa[1], s[1], f), sa[0] === s[0] ? lerp(sa[2] ?? 0, s[2] ?? 0, f) : (f < 0.5 ? sa[2] : s[2])] : undefined,
        sz: lerp(p.sz || 0, q.sz || 0, f), rinde: p.rinde ?? a.rinde, conf: p.cf,
      };
    });
    return e;
  }
}

// ------------------------------------------------------------------------------------------------ eventos (bitácora)
const pad2 = n => String(n).padStart(2, "0");
export function calcularEventos(P) {
  const C = P.C, ev = [];
  let ultimaAmz = -1e9;                 // el aviso de amenaza no se repite antes de 5 s
  const lad = c => (c.pers || []).find(p => p.rol === "ladron");
  const idTxt = p => p && p.id !== undefined ? "ID " + pad2(p.id) : "el objetivo";
  C.forEach((c, k) => {
    const p = C[k - 1];
    if (!p) { ev.push({ k, txt: c.fase === 1 ? "Despegue · piloto al mando" : "Sistema activo · buscando personas", tipo: "info" }); return; }
    if (p.fase === 1 && c.fase === 2) ev.push({ k, txt: "Cambio a modo automático (GUIDED)", tipo: "info", marca: true });
    if (c.fase === 1 && c.bloq && !p.bloq) ev.push({ k, txt: "Bloqueo frontal: obstáculo al frente", tipo: "peligro", marca: true });
    if (c.fase !== 2) return;
    const l = lad(c), lp = lad(p);
    if (c.modo === 1 && p.modo !== 1) ev.push({ k, txt: `Persona ${idTxt(l)} en cámara: confirme si es el sospechoso`, tipo: "aviso", marca: true });
    if (c.op === 1) ev.push({ k, txt: `Operador confirmó al sospechoso (${idTxt(l)})`, tipo: "ok", marca: true });
    if (c.op === 2) ev.push({ k, txt: "Operador descartó a la persona", tipo: "info", marca: true });
    if (p.modo === 2 && c.modo >= 3 && c.modo !== 9) ev.push({ k, txt: "Objetivo fuera de vista: búsqueda automática", tipo: "aviso", marca: true });
    if (c.modo === 2 && p.modo >= 3 && p.modo !== 9) ev.push({ k, txt: `Objetivo recuperado (${idTxt(l)})`, tipo: "ok", marca: true });
    if (c.modo === 10 && p.modo !== 10) ev.push({ k, txt: "Revisando detrás del muro (muro de canto)", tipo: "info" });
    if (c.modo === 9 && p.modo !== 9) ev.push({ k, txt: "¿Sigue siendo él? Cruce con otra persona: confirme", tipo: "aviso", marca: true });
    if (c.amz && !p.amz && k - ultimaAmz > 50) { ev.push({ k, txt: "Amenaza: persona cerca y acercándose", tipo: "peligro", marca: true }); ultimaAmz = k; }
    if (c.rfx && !p.rfx) ev.push({ k, txt: "Esquive: el dron sube y se aparta", tipo: "peligro" });
    const s = l && l.salto, sp = lp && lp.salto;
    if ((s && s[0] === 1 && !(sp && sp[0] === 1)) || (!s && l && l.sz > 0 && !(lp && lp.sz > 0)))
      ev.push({ k, txt: "¡Salto! El sospechoso intenta agarrar el dron", tipo: "peligro", marca: true, salto: true });
    if (l && lp && l.pos !== undefined && l.pos !== lp.pos) ev.push({ k, txt: ["Sospechoso de pie", "Sospechoso agachado", "Sospechoso recostado contra el muro", "Sospechoso gateando"][l.pos] || "", tipo: "info" });
    if (c.rinde && !p.rinde) ev.push({ k, txt: "El sospechoso se rinde", tipo: "ok", marca: true });
  });
  const fin = { cumplida: ["Misión cumplida: el sospechoso se rindió", "ok"], perdido: ["Misión perdida: no se recuperó al objetivo", "peligro"],
                alcanzado: ["Misión fallida: alcanzaron al dron", "peligro"], geocerca: ["Misión fallida: salida de la geocerca", "peligro"],
                panel: ["Misión fallida: choque con un obstáculo", "peligro"], choque_peaton: ["Misión fallida: choque con un peatón", "peligro"],
                tiempo: ["Misión fallida: 5 minutos sin rendición", "aviso"] }[P.d.resultado];
  if (fin && C.length > 1) ev.push({ k: C.length - 1, txt: fin[0], tipo: fin[1], marca: true });
  return ev;
}
