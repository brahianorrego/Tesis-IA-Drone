// Interfaz de la estación de tierra: telemetría del pie, línea de tiempo, avisos, mapa pequeño y modo ingeniería.
// La regla: en la pantalla principal solo lo que el operador verá en vuelo; lo técnico, en el panel de ingeniería.
import { $, pad2, relojTxt, limitar, CAM } from "./util.js";

const COLOR = { ok: "#3cc46e", aviso: "#f0a623", peligro: "#ec4d4d", info: "#6aa9d8", suave: "#8b949e" };
const POSTURA = ["de pie", "agachado", "recostado en el muro", "gateando"];
const CIVIL = ["transita", "mira el dron", "esquiva", "se va", "graba con el celular"];
const MODOS = ["BUSCANDO", "CONFIRMAR", "SIGUIENDO", "BÚSQUEDA", "BÚSQUEDA", "BÚSQUEDA", "BÚSQUEDA", "BÚSQUEDA IA", "BÚSQUEDA",
               "CONFIRMAR", "BÚSQUEDA"];
const ESTADO_TXT = { BUSCAR: "busca personas", VERIFICAR: "espera la confirmación", PERSECUCION: "persecución", FLANQUEO_PROFUNDO: "flanqueo del muro",
                     GIRO_360: "giro de 360°", ALTURA_TACTICA: "altura táctica", PERDIDA: "pérdida: sigue su vector", BUSQUEDA_IA: "búsqueda por IA",
                     SIGUIENTE_OBSTACULO: "siguiente obstáculo", RECONFIRMAR: "reconfirmar identidad", MURO_DE_CANTO: "muro de canto" };

export class Interfaz {
  constructor() {
    this.ultimoDom = 0;
    this.avisoHasta = 0;
    this.mapa = $("mapa");
    this.gm = this.mapa.getContext("2d");
    this.rastro = [];
  }

  ponerPartida(P) {
    this.P = P;
    this.rastro = [];
    const N = Math.max(1, P.C.length - 1);
    $("marcas").innerHTML = P.eventos.filter(e => e.marca).map(e =>
      `<div class="ev" style="left:${100 * e.k / N}%;background:${COLOR[e.tipo] || COLOR.suave}" title="${e.txt}"></div>`).join("");
    $("bitacora").innerHTML = "";
    this.kBitacora = -1;
    this.custodia = 0;
  }

  aviso(txt, tipo = "aviso", seg = 3.5) {
    const a = $("aviso");
    a.textContent = txt;
    a.style.setProperty("--c", COLOR[tipo] || COLOR.aviso);
    a.classList.add("ver");
    this.avisoHasta = performance.now() + seg * 1000;
  }

  // ------------------------------------------------------------------------------------------- cada cuadro
  actualizar(e, t, ahora, extra = {}) {
    if (ahora > this.avisoHasta) $("aviso").classList.remove("ver");
    const P = this.P;
    $("hecho").style.width = (100 * t / Math.max(P.total, 1e-6)) + "%";
    if (ahora - this.ultimoDom < 90) return;        // el texto se refresca ~10 veces por segundo
    this.ultimoDom = ahora;
    $("reloj").textContent = `${relojTxt(t)} / ${relojTxt(P.total)}`;
    this.telemetria(e, t);
    this.ingenieria(e, extra);
    this.dibujarMapa(e);
    // bitácora: los eventos que ya pasaron
    const k = e.k;
    if (k !== this.kBitacora) {
      const evs = P.eventos.filter(v => v.k <= k);
      $("bitacora").innerHTML = evs.slice(-40).reverse().map(v => `<div><b>${relojTxt(v.k * P.dt)}</b><span style="color:${COLOR[v.tipo] || COLOR.suave}">${v.txt}</span></div>`).join("");
      this.kBitacora = k;
    }
  }

  telemetria(e, t) {
    const lad = e.personas.find(p => p.rol === "ladron");
    // modo de vuelo
    const modo = e.fase === 1 ? "MANUAL" : e.est === 1 ? "GUIDED · ESQUIVA" : e.rinde ? "GUIDED · CUSTODIA" : "GUIDED · " + (MODOS[e.modo] || "AUTO");
    $("d-modo").innerHTML = modo.replace(" · ", ` <small>·</small> `);
    $("d-modo").style.color = e.est === 1 ? COLOR.peligro : e.modo === 1 || e.modo === 9 ? COLOR.aviso : "";
    $("d-alt").innerHTML = `${e.z.toFixed(2)} m` + (e.altObj !== null ? ` <small>→ ${e.altObj.toFixed(1)}</small>` : "");
    const bat = e.bat !== undefined ? e.bat : limitar(100 - 100 * (e.t2 ?? t) / 900, 0, 100);
    const colB = bat < 25 ? COLOR.peligro : bat < 45 ? COLOR.aviso : COLOR.ok;
    $("d-bat").innerHTML = `<span class="bateria" style="color:${colB}"><i style="width:${bat * 0.22}px"></i></span>${bat.toFixed(0)} %` + (e.bat === undefined ? " <small>est.</small>" : "");
    $("d-vel").innerHTML = `${Math.hypot(e.vx, e.vy).toFixed(1)} <small>m/s</small>`;
    $("d-gmb").innerHTML = `${e.gmb.toFixed(0)}°`;
    // objetivo: lo que sabe el operador
    let txt = "Sin designar", col = COLOR.suave;
    const id = lad && lad.id !== undefined ? "ID " + pad2(lad.id) : "objetivo";
    if (e.fase === 2) {
      if (e.rinde) { txt = `${id} · se rindió`; col = COLOR.ok; }
      else if (e.modo === 0) { txt = "Buscando personas"; }
      else if (e.modo === 1) { txt = `${id} en cámara · ¿es el sospechoso?`; col = COLOR.aviso; }
      else if (e.modo === 9) { txt = `${id} · ¿sigue siendo él?`; col = COLOR.aviso; }
      else if (e.modo === 2) {
        const d = lad ? Math.hypot(lad.x - e.x, lad.y - e.y) : 0;
        const piso = (e.cam_piso || []).some(q => lad && q.id === lad.id) && !e.vis;
        txt = `${id} · ${piso ? "debajo (cámara al piso)" : "a la vista"} · ${d.toFixed(1)} m`; col = COLOR.ok;
      } else { txt = `${id} · fuera de vista · buscando ${e.tsv ? `(${e.tsv.toFixed(0)} s)` : ""}`; col = COLOR.aviso; }
    } else if (e.bloq) { txt = "Obstáculo al frente: avance bloqueado"; col = COLOR.peligro; }
    $("d-obj-b").textContent = txt;
    $("d-obj-b").style.color = col;
    $("d-cus").innerHTML = e.tf !== undefined ? relojTxt(e.tf) : "–";
  }

  ingenieria(e, extra) {
    if (!$("ingenieria").classList.contains("abierto")) return;
    const kv = (a, b, c) => `<span>${a}</span><b${c ? ` style="color:${c}"` : ""}>${b}</b>`;
    $("i-fps").textContent = extra.fps ? `${extra.fps.toFixed(0)} cps · ${extra.calidad}` : "–";
    $("i-estado").innerHTML = kv("Estado de la búsqueda", e.eb ? (ESTADO_TXT[e.eb] || e.eb) : "–")
      + kv("Modo del entorno", e.modo ?? "–") + kv("Tracker", ["búsqueda", "fijado", "memoria", "perdido", "re-identificando", "verificando"][e.trk] || "–")
      + kv("Sin ver al objetivo", e.tsv !== undefined ? e.tsv.toFixed(1) + " s" : "–") + kv("Confianza ReID", e.conf !== undefined ? e.conf.toFixed(2) : "–")
      + kv("Altura objetivo", e.altObj !== null ? e.altObj.toFixed(2) + " m" : "no viene (V15)")
      + kv("Gimbal (−45° a +15°)", e.gmb.toFixed(1) + "°") + kv("Chasis cabeceo / alabeo", `${e.cp.toFixed(1)}° / ${e.cr.toFixed(1)}°`)
      + kv("LiDAR TF03", e.lid !== undefined ? e.lid.toFixed(1) + " m" : "–")
      + kv("Repetición", this.P.v16 ? "con campos V16" : "formato V15");
    $("i-arbitro").innerHTML = kv("Amenaza", e.amz ? "SÍ" : "no", e.amz ? COLOR.peligro : "") + kv("Esquive reflejo", e.rfx ? "SÍ" : "no", e.rfx ? COLOR.peligro : "")
      + kv("Evasión autorizada", e.est === 1 ? "SÍ" : "no", e.est === 1 ? COLOR.aviso : "") + kv("Bloqueo frontal", e.bloq ? "SÍ" : "no", e.bloq ? COLOR.peligro : "")
      + kv("Punto ciego", e.ciego ? `retrocede a ${(e.dcg ?? 0).toFixed(1)} m` : "no");
    $("i-personas").innerHTML = e.personas.map(p => {
      const d = Math.hypot(p.x - e.x, p.y - e.y);
      const s = p.salto && p.salto[0] ? ` · salto ${["", "impulso", "vuelo", "aterrizaje", "recuperación"][p.salto[0]]} (mano ${p.salto[1].toFixed(2)} m)` : "";
      return kv(`${p.rol === "ladron" ? "Sospechoso" : "Civil"} ${p.id !== undefined ? pad2(p.id) : ""}`,
        `${p.pos !== undefined ? POSTURA[p.pos] : "de pie"}${p.civ !== undefined && p.civ !== null ? " · " + CIVIL[p.civ] : ""}${s} · ${d.toFixed(1)} m · ${p.vis ? "visto" : "oculto"}`,
        p.vis ? "" : COLOR.suave);
    }).join("");
    const rc = e.r_comp;
    $("i-recompensa").innerHTML = rc ? Object.entries(rc).map(([a, b]) => kv(a, (+b).toFixed(3))).join("") : kv("Componentes", "no vienen en esta repetición");
  }

  // ------------------------------------------------------------------------------------------- mapa pequeño
  // Lo que sabe el operador: paneles, el dron con lo que mira la cámara, el objetivo cuando se ve (o su última posición).
  dibujarMapa(e) {
    const c = this.mapa, g = this.gm, r = c.getBoundingClientRect(), dpr = Math.min(devicePixelRatio, 2);
    if (c.width !== Math.round(r.width * dpr) || c.height !== Math.round(r.height * dpr)) { c.width = Math.round(r.width * dpr); c.height = Math.round(r.height * dpr); }
    const W = c.width, H = c.height;
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.fillStyle = "#121519"; g.fillRect(0, 0, W, H);
    if (W < 20 || H < 20) return;
    const R = 16, esc = Math.min(W, H) / (2 * R) * 0.95, ox = e.x, oy = e.y;     // centrado en el dron, 32 m de lado
    const X = x => W / 2 + (x - ox) * esc, Y = y => H / 2 - (y - oy) * esc;
    // cuadrícula de 5 m
    g.strokeStyle = "#1c2026"; g.lineWidth = 1;
    for (let k = Math.ceil((ox - W / esc) / 5) * 5; k < ox + W / esc; k += 5) { g.beginPath(); g.moveTo(X(k), 0); g.lineTo(X(k), H); g.stroke(); }
    for (let k = Math.ceil((oy - H / esc) / 5) * 5; k < oy + H / esc; k += 5) { g.beginPath(); g.moveTo(0, Y(k)); g.lineTo(W, Y(k)); g.stroke(); }
    // geocerca
    g.strokeStyle = "rgba(240,166,35,.55)"; g.setLineDash([6 * dpr, 4 * dpr]); g.lineWidth = 1.5 * dpr;
    g.strokeRect(X(-25), Y(25), 50 * esc, 50 * esc); g.setLineDash([]);
    // paneles
    g.strokeStyle = "#aeb4ba"; g.lineWidth = Math.max(2, 0.2 * esc); g.lineCap = "butt";
    (this.P.paneles || []).forEach(([x1, y1, x2, y2]) => { g.beginPath(); g.moveTo(X(x1), Y(y1)); g.lineTo(X(x2), Y(y2)); g.stroke(); });
    // rastro del dron
    if (!this.rastro.length || Math.hypot(this.rastro[this.rastro.length - 1][0] - e.x, this.rastro[this.rastro.length - 1][1] - e.y) > 0.3) this.rastro.push([e.x, e.y]);
    if (this.rastro.length > 400) this.rastro.shift();
    g.strokeStyle = "rgba(106,169,216,.35)"; g.lineWidth = 1.2 * dpr; g.beginPath();
    this.rastro.forEach(([x, y], i) => i ? g.lineTo(X(x), Y(y)) : g.moveTo(X(x), Y(y))); g.stroke();
    // campo de visión de la cámara
    const hf = CAM.hfov / 2 * Math.PI / 180, alc = 10 * esc, cx = X(e.x), cy = Y(e.y);
    g.fillStyle = "rgba(106,169,216,.13)"; g.beginPath(); g.moveTo(cx, cy);
    g.arc(cx, cy, alc, -(e.psi + hf), -(e.psi - hf)); g.closePath(); g.fill();
    // personas que el sistema ve (detecciones), y el objetivo (visto o última posición conocida)
    e.personas.forEach(p => {
      const visto = p.vis || (e.cam_piso || []).some(q => q.id === p.id);
      const esObj = p.rol === "ladron" && e.modo >= 2;
      if (!visto && !esObj) return;
      const px = esObj && !visto && e.ux !== undefined ? e.ux : p.x, py = esObj && !visto && e.uy !== undefined ? e.uy : p.y;
      g.fillStyle = esObj ? (visto ? COLOR.ok : "rgba(240,166,35,.9)") : "rgba(200,205,210,.75)";
      g.beginPath(); g.arc(X(px), Y(py), (esObj ? 5 : 3.5) * dpr, 0, 6.3); g.fill();
      if (esObj && !visto) { g.strokeStyle = COLOR.aviso; g.beginPath(); g.arc(X(px), Y(py), 9 * dpr, 0, 6.3); g.stroke(); }
    });
    // dron
    g.save(); g.translate(cx, cy); g.rotate(-e.psi);
    g.fillStyle = "#e9edf1"; g.beginPath(); g.moveTo(9 * dpr, 0); g.lineTo(-6 * dpr, 5.5 * dpr); g.lineTo(-3 * dpr, 0); g.lineTo(-6 * dpr, -5.5 * dpr); g.closePath(); g.fill();
    g.restore();
    // escala y norte
    g.fillStyle = "#6b737d"; g.font = `${10 * dpr}px Segoe UI, sans-serif`;
    g.fillText("N ↑ · cuadros de 5 m", 8 * dpr, H - 8 * dpr);
  }
}
