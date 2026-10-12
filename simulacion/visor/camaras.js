// Imagen de las cámaras del dron como la del sensor real (fase B3 del plan V16).
// Cada cámara se dibuja en una imagen de su resolución (640 x 480) y pasa por un "revelado" con lo que tiene la cámara
// real: distorsión del lente, aberración cromática, viñeteo, ruido del sensor (más en las sombras), exposición
// automática (lenta, como una webcam) y desenfoque por movimiento cuando la cámara gira. Encima se dibujan las cajas de
// YOLO como en jetson/visor_web.py: rectángulo verde, "ID n  +x.x deg" y la línea de la nariz del dron.
import * as THREE from "three";
import { DataUtils } from "three";
import { limitar, lerp, pad2 } from "./util.js";

const VERT = `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`;
const FRAG = `
precision highp float;
varying vec2 vUv;
uniform sampler2D img;
uniform vec2 res;
uniform float k1, k2, aberracion, vineteo, ruido, exposicion, tiempo, escalaLente;
uniform vec2 estela;                 // desenfoque por movimiento: desplazamiento de la imagen durante la exposición (uv)
vec2 distorsion(vec2 uv) {           // lente con barril: el borde de la salida toma la imagen de más afuera
  vec2 d = uv - 0.5; d.x *= res.x / res.y;
  float r2 = dot(d, d);
  d *= (1.0 + k1 * r2 + k2 * r2 * r2) / escalaLente;     // escalada: las esquinas quedan dentro (sin bordes negros)
  d.x *= res.y / res.x;
  return d + 0.5;
}
float azar(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233)) + tiempo * 43.17) * 43758.5453); }
vec3 aces(vec3 c) {
  const mat3 A = mat3(0.59719, 0.07600, 0.02840, 0.35458, 0.90834, 0.13383, 0.04823, 0.01566, 0.83777);
  const mat3 B = mat3(1.60475, -0.10208, -0.00327, -0.53108, 1.10813, -0.07276, -0.07367, -0.00605, 1.07602);
  c = A * c;
  vec3 a = c * (c + 0.0245786) - 0.000090537, b = c * (0.983729 * c + 0.4329510) + 0.238081;
  return clamp(B * (a / b), 0.0, 1.0);
}
vec3 muestra(vec2 uv) {
  vec2 c = uv - 0.5;
  vec3 col;
  col.r = texture2D(img, 0.5 + c * (1.0 + aberracion)).r;
  col.g = texture2D(img, uv).g;
  col.b = texture2D(img, 0.5 + c * (1.0 - aberracion)).b;
  return col;
}
void main() {
  vec2 uv = distorsion(vUv);
  if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) { gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
  vec3 col = vec3(0.0);
  const int N = 9;
  for (int i = 0; i < N; i++) { float f = float(i) / float(N - 1) - 0.5; col += muestra(uv + estela * f); }
  col /= float(N);
  col *= exposicion;
  vec2 v = vUv - 0.5;
  col *= 1.0 - vineteo * dot(v, v) * 2.2;
  col = aces(col / 0.6);
  // ruido del sensor: luminancia y algo de color, más fuerte en las zonas oscuras
  float l = dot(col, vec3(0.299, 0.587, 0.114));
  float n = (azar(vUv * res) - 0.5) * ruido * (1.4 - l);
  vec3 nc = vec3(azar(vUv * res + 1.3), azar(vUv * res + 2.7), azar(vUv * res + 4.1)) - 0.5;
  col += n + nc * ruido * 0.35;
  col = pow(clamp(col, 0.0, 1.0), vec3(1.0 / 2.2));      // a sRGB
  gl_FragColor = vec4(col, 1.0);
}`;

export class SensorCamara {
  // op: { ancho, alto, k1, k2, aberracion, vineteo, ruido, hfov }
  constructor(renderer, camara, op) {
    this.renderer = renderer;
    this.camara = camara;
    this.op = op;
    this.rt = new THREE.WebGLRenderTarget(op.ancho, op.alto, { type: THREE.HalfFloatType, samples: 4 });
    this.medidor = new THREE.WebGLRenderTarget(16, 12, { type: THREE.HalfFloatType });
    this.lect = new Uint16Array(16 * 12 * 4);
    this.mat = new THREE.ShaderMaterial({
      vertexShader: VERT, fragmentShader: FRAG, depthTest: false, depthWrite: false,
      uniforms: { img: { value: this.rt.texture }, res: { value: new THREE.Vector2(op.ancho, op.alto) }, k1: { value: op.k1 }, k2: { value: op.k2 },
                  aberracion: { value: op.aberracion }, vineteo: { value: op.vineteo }, ruido: { value: op.ruido }, exposicion: { value: 1 },
                  tiempo: { value: 0 }, estela: { value: new THREE.Vector2() }, escalaLente: { value: 1 } },
    });
    const asp = op.ancho / op.alto, rc2 = (asp * asp + 1) / 4;          // radio² de la esquina (en unidades de alto)
    this.escalaLente = 1 + op.k1 * rc2 + op.k2 * rc2 * rc2;
    this.mat.uniforms.escalaLente.value = this.escalaLente;
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.mat);
    this.quad.frustumCulled = false;
    this.escenaQuad = new THREE.Scene();
    this.escenaQuad.add(this.quad);
    this.camQuad = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.expo = 1;
    this.cuadro = 0;
    this.tUltimo = 0;
    this.fps = 30;
    this.qPrevio = null;
    this.fwdPrevio = new THREE.Vector3();
  }

  // dibuja la imagen del sensor en el rectángulo r del lienzo (coordenadas de three: y desde abajo)
  dibujar(escena, r, dt, ahora, cadencia = 30) {
    const R = this.renderer, c = this.camara;
    // la cámara real entrega ~30 cuadros por segundo: solo se vuelve a sacar la foto cuando toca
    const toca = ahora - this.tUltimo >= 1000 / cadencia - 2;
    if (toca) {
      const dtc = this.tUltimo ? (ahora - this.tUltimo) / 1000 : 1 / cadencia;
      this.fps = lerp(this.fps, 1 / Math.max(dtc, 1e-3), 0.1);
      this.tUltimo = ahora;
      c.updateMatrixWorld(true);
      // desenfoque por movimiento: cuánto se corrió la imagen mientras el obturador estuvo abierto (1/60 s)
      const fwd = new THREE.Vector3(0, 0, -1).applyQuaternion(c.getWorldQuaternion(new THREE.Quaternion()));
      if (this.qPrevio) {
        const p = c.getWorldPosition(new THREE.Vector3()).add(this.fwdPrevio).project(c);
        const obturador = Math.min(1, (1 / 60) / Math.max(dtc, 1e-3));
        this.mat.uniforms.estela.value.set(limitar(-p.x * 0.5 * obturador, -0.06, 0.06), limitar(-p.y * 0.5 * obturador, -0.06, 0.06));
      }
      this.fwdPrevio.copy(fwd);
      this.qPrevio = true;
      const capas = c.layers.mask;
      c.layers.set(0);
      R.setRenderTarget(this.rt);
      R.render(escena, c);
      // exposición automática (cada 8 fotos, con la media logarítmica de una imagen chica)
      if (this.cuadro++ % 8 === 0) {
        R.setRenderTarget(this.medidor);
        R.render(escena, c);
        R.readRenderTargetPixels(this.medidor, 0, 0, 16, 12, this.lect);
        let s = 0;
        for (let i = 0; i < 16 * 12; i++) {
          const l = 0.2126 * DataUtils.fromHalfFloat(this.lect[4 * i]) + 0.7152 * DataUtils.fromHalfFloat(this.lect[4 * i + 1]) + 0.0722 * DataUtils.fromHalfFloat(this.lect[4 * i + 2]);
          s += Math.log(1e-4 + Math.max(l, 0));
        }
        this.expoObj = limitar(0.2 / Math.exp(s / (16 * 12)), 0.35, 2.6);
      }
      c.layers.mask = capas;
      R.setRenderTarget(null);
    }
    if (this.expoObj) this.expo = lerp(this.expo, this.expoObj, 1 - Math.exp(-dt / 0.9));
    this.mat.uniforms.exposicion.value = this.expo;
    this.mat.uniforms.tiempo.value = (ahora / 1000) % 100;
    R.setViewport(r.x, r.y, r.w, r.h);
    R.setScissor(r.x, r.y, r.w, r.h);
    R.render(this.escenaQuad, this.camQuad);
  }

  // de un punto del mundo a la imagen de salida (0-1, y hacia abajo), con la misma distorsión del lente
  proyectar(p, v = new THREE.Vector3()) {
    v.copy(p).project(this.camara);
    if (v.z > 1 || Math.abs(v.x) > 1.4 || Math.abs(v.y) > 1.4) return null;     // muy fuera de la imagen: sin lente que valga
    const asp = this.op.ancho / this.op.alto, k1 = this.op.k1, k2 = this.op.k2;
    const sx = v.x * 0.5 * asp, sy = v.y * 0.5;            // fuente, centrada, en unidades de alto
    let ox = sx, oy = sy;
    for (let i = 0; i < 5; i++) { const r2 = ox * ox + oy * oy, f = (1 + k1 * r2 + k2 * r2 * r2) / this.escalaLente; ox = sx / f; oy = sy / f; }
    return { x: ox / asp + 0.5, y: 0.5 - oy };
  }
}

// ------------------------------------------------------------------------------------------------ cajas de YOLO
// puntos del cuerpo para la caja (cabeza, manos, pies, cadera, hombros), en el mundo
const PUNTOS = ["cabeza", "mano_L", "mano_R", "dedos_L", "dedos_R", "pie_L", "pie_R", "cadera", "brazo_L", "brazo_R", "pierna_L", "pierna_R"];
const _v = new THREE.Vector3();
export function cajaDe(sensor, figura) {
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, n = 0;
  const esc = figura.escala || 1;
  PUNTOS.forEach(h => {
    const b = figura.H[h];
    if (!b) return;
    b.getWorldPosition(_v);
    if (h === "cabeza") _v.y += 0.17 * esc;
    if (h === "dedos_L" || h === "dedos_R") _v.y -= 0.02;
    const q = sensor.proyectar(_v);
    if (!q) return;
    n++;
    x0 = Math.min(x0, q.x); x1 = Math.max(x1, q.x); y0 = Math.min(y0, q.y); y1 = Math.max(y1, q.y);
  });
  if (!n) return null;
  // el centro del cuerpo tiene que caer dentro de la imagen (si no, son puntos de alguien fuera de cuadro)
  figura.H.cadera.getWorldPosition(_v);
  const cc = sensor.proyectar(_v);
  if (!cc || cc.x < -0.02 || cc.x > 1.02 || cc.y < -0.1 || cc.y > 1.1) return null;
  const mx = (x1 - x0) * 0.12 + 0.004, my = (y1 - y0) * 0.04 + 0.004;
  x0 -= mx; x1 += mx; y0 -= my; y1 += my;
  if (x1 < 0 || y1 < 0 || x0 > 1 || y0 > 1) return null;
  return { x0: Math.max(0, x0), y0: Math.max(0, y0), x1: Math.min(1, x1), y1: Math.min(1, y1) };
}

// dibuja las detecciones sobre el lienzo 2D que cubre el marco; fr = rectángulo de la imagen dentro del marco (px CSS)
export function dibujarDetecciones(lienzo, fr, dets, op = {}) {
  const dpr = Math.min(devicePixelRatio, 2), r = lienzo.getBoundingClientRect();
  if (lienzo.width !== Math.round(r.width * dpr) || lienzo.height !== Math.round(r.height * dpr)) { lienzo.width = Math.round(r.width * dpr); lienzo.height = Math.round(r.height * dpr); }
  const g = lienzo.getContext("2d");
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.clearRect(0, 0, lienzo.width, lienzo.height);
  if (!fr) return [];
  const ox = (fr.x - r.left) * dpr, oy = (fr.y - r.top) * dpr, W = fr.w * dpr, H = fr.h * dpr;
  const esc = W / 640;                                     // trazos y letras a la escala de la imagen de 640 px
  g.save();
  g.beginPath(); g.rect(ox, oy, W, H); g.clip();
  // la nariz del dron (línea cian vertical al centro), como en el visor de la Jetson
  if (op.nariz) { g.strokeStyle = "rgb(0,255,255)"; g.lineWidth = Math.max(1, esc); g.beginPath(); g.moveTo(ox + W / 2, oy); g.lineTo(ox + W / 2, oy + H); g.stroke(); }
  const cajas = [];
  const tanH = Math.tan((op.hfov || 38.9) * Math.PI / 360);
  dets.forEach(d => {
    const x = ox + d.c.x0 * W, y = oy + d.c.y0 * H, w = (d.c.x1 - d.c.x0) * W, h = (d.c.y1 - d.c.y0) * H;
    const col = d.esperando ? "rgb(255,190,40)" : "rgb(0,255,0)";
    g.strokeStyle = col; g.lineWidth = Math.max(1.5, 2 * esc) * (d.objetivo ? 1.4 : 1);
    if (d.esperando) g.setLineDash([8 * esc, 5 * esc]);
    g.strokeRect(x, y, w, h);
    g.setLineDash([]);
    const ang = Math.atan((2 * ((d.c.x0 + d.c.x1) / 2) - 1) * tanH) * 180 / Math.PI;
    const txt = `ID ${d.id}  ${ang >= 0 ? "+" : ""}${ang.toFixed(1)} deg  ${d.conf.toFixed(2)}`;
    g.font = `${Math.round(15 * esc)}px "Segoe UI", Arial, sans-serif`;
    g.lineWidth = Math.max(2, 3 * esc); g.strokeStyle = "rgba(0,0,0,.55)";
    const ty = Math.max(oy + 15 * esc, y - 6 * esc);
    g.strokeText(txt, x, ty);
    g.fillStyle = col; g.fillText(txt, x, ty);
    if (d.esperando) {
      const t2 = "¿Es el sospechoso? clic aquí";
      g.strokeText(t2, x, y + h + 17 * esc); g.fillText(t2, x, y + h + 17 * esc);
    }
    cajas.push({ id: d.id, clave: d.clave, x0: x / dpr + r.left, y0: y / dpr + r.top, x1: (x + w) / dpr + r.left, y1: (y + h) / dpr + r.top, esperando: d.esperando });
  });
  if (op.fps) {          // como en la Jetson: cuadros por segundo y la imagen que recibe YOLO, en rojo arriba a la izquierda
    g.font = `${Math.round(15 * esc)}px "Segoe UI", Arial, sans-serif`;
    g.fillStyle = "rgb(255,40,40)";
    g.fillText(`${op.fps.toFixed(1)} FPS  YOLO: corregida`, ox + 8 * esc, oy + 22 * esc);
  }
  g.restore();
  return cajas;
}

export const confianza = (p) => {
  if (p.conf !== undefined && p.conf !== null) return p.conf;
  const pos = p.pos ?? 0, fv = p.fv ?? 1;
  return limitar(0.5 + 0.42 * fv - (pos === 1 ? 0.08 : pos === 3 ? 0.2 : pos === 2 ? 0.04 : 0), 0.3, 0.95);
};
export { pad2 };
