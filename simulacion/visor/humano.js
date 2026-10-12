// Persona con esqueleto y animación procedural (fase B2 del plan V16).
//
// Cuerpo: malla con piel (SkinnedMesh) sobre 22 huesos, con proporciones humanas reales para 1.72 m; se escala a la
// estatura de cada persona. Ropa, piel y pelo cambian según el ID (siempre igual para la misma persona).
// Animación: cada postura (de pie/caminar/correr, agachado, recostado contra la pared, gateando) y cada acción (salto
// para agarrar el dron, mirar arriba, grabar con el celular, esquivar, rendirse) produce una "pose objetivo": dónde va
// la cadera, cómo se dobla la columna y dónde van los pies y las manos. Las poses se MEZCLAN con pesos que cambian
// suave (transiciones, no saltos de pose) y brazos y piernas se resuelven con cinemática inversa de 2 huesos. Los pies
// avanzan con la distancia recorrida: en el apoyo quedan quietos en el piso (no patinan).
//
// Ejes locales de la persona: mira hacia +z, su izquierda es +x, y hacia arriba. Unidades: metros de una persona de 1.72 m.
import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { mundo, lerp, limitar, suave, suave5, angNorm, azar } from "./util.js";

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const ALTO_BASE = 1.72;

// ------------------------------------------------------------------------------------------------ esqueleto (reposo)
// [nombre, padre, posición absoluta en reposo]
const HUESOS = [
  ["cadera", null, V(0, 0.98, 0)],
  ["columna", "cadera", V(0, 1.09, 0.005)],
  ["pecho", "columna", V(0, 1.27, 0.01)],
  ["cuello", "pecho", V(0, 1.465, -0.005)],
  ["cabeza", "cuello", V(0, 1.565, 0.0)],
  ["clav_L", "pecho", V(0.035, 1.425, 0.0)],
  ["brazo_L", "clav_L", V(0.185, 1.425, -0.01)],
  ["antebrazo_L", "brazo_L", V(0.205, 1.11, -0.025)],
  ["mano_L", "antebrazo_L", V(0.215, 0.85, 0.0)],
  ["clav_R", "pecho", V(-0.035, 1.425, 0.0)],
  ["brazo_R", "clav_R", V(-0.185, 1.425, -0.01)],
  ["antebrazo_R", "brazo_R", V(-0.205, 1.11, -0.025)],
  ["mano_R", "antebrazo_R", V(-0.215, 0.85, 0.0)],
  ["muslo_L", "cadera", V(0.09, 0.93, 0.0)],
  ["pierna_L", "muslo_L", V(0.095, 0.505, 0.012)],
  ["pie_L", "pierna_L", V(0.10, 0.085, -0.01)],
  ["dedos_L", "pie_L", V(0.10, 0.02, 0.135)],
  ["muslo_R", "cadera", V(-0.09, 0.93, 0.0)],
  ["pierna_R", "muslo_R", V(-0.095, 0.505, 0.012)],
  ["pie_R", "pierna_R", V(-0.10, 0.085, -0.01)],
  ["dedos_R", "pie_R", V(-0.10, 0.02, 0.135)],
];
const REPOSO = Object.fromEntries(HUESOS.map(([n, , p]) => [n, p]));
const IDX = Object.fromEntries(HUESOS.map(([n], i) => [n, i]));
const PUNTA_MANO = { L: V(0.22, 0.67, 0.01), R: V(-0.22, 0.67, 0.01) };
const LARGO = {
  muslo: REPOSO.muslo_L.distanceTo(REPOSO.pierna_L), pierna: REPOSO.pierna_L.distanceTo(REPOSO.pie_L),
  brazo: REPOSO.brazo_L.distanceTo(REPOSO.antebrazo_L), antebrazo: REPOSO.antebrazo_L.distanceTo(REPOSO.mano_L),
};
const ALTURA_TOBILLO = 0.085;

// segmentos para los pesos de la piel (de dónde a dónde "manda" cada hueso)
const SEGMENTO = {
  cadera: [V(0, 0.84, -0.01), V(0, 1.03, 0)], columna: [V(0, 1.03, 0), V(0, 1.24, 0.01)], pecho: [V(0, 1.24, 0.01), V(0, 1.44, 0)],
  cuello: [V(0, 1.45, -0.005), V(0, 1.57, 0)], cabeza: [V(0, 1.57, 0.01), V(0, 1.72, 0.01)],
  clav_L: [V(0.03, 1.425, 0), V(0.17, 1.43, -0.01)], clav_R: [V(-0.03, 1.425, 0), V(-0.17, 1.43, -0.01)],
  dedos_L: [V(0.1, 0.02, 0.135), V(0.1, 0.02, 0.2)], dedos_R: [V(-0.1, 0.02, 0.135), V(-0.1, 0.02, 0.2)],
};
["L", "R"].forEach(s => {
  SEGMENTO["brazo_" + s] = [REPOSO["brazo_" + s], REPOSO["antebrazo_" + s]];
  SEGMENTO["antebrazo_" + s] = [REPOSO["antebrazo_" + s], REPOSO["mano_" + s]];
  SEGMENTO["mano_" + s] = [REPOSO["mano_" + s], PUNTA_MANO[s]];
  SEGMENTO["muslo_" + s] = [REPOSO["muslo_" + s], REPOSO["pierna_" + s]];
  SEGMENTO["pierna_" + s] = [REPOSO["pierna_" + s], REPOSO["pie_" + s]];
  SEGMENTO["pie_" + s] = [REPOSO["pie_" + s], REPOSO["dedos_" + s]];
});
const _ab = new THREE.Vector3(), _ap = new THREE.Vector3();
function distSeg(p, [a, b]) {
  _ab.subVectors(b, a); _ap.subVectors(p, a);
  const t = limitar(_ap.dot(_ab) / Math.max(_ab.lengthSq(), 1e-9), 0, 1);
  return _ap.addScaledVector(_ab, -t).length();
}
// pesos automáticos: los 3 huesos más cercanos de la lista, con caída fuerte (articulaciones suaves)
function pesar(geo, candidatos, exponente = 7) {
  const p = geo.attributes.position, n = p.count, si = new Uint16Array(n * 4), sw = new Float32Array(n * 4), v = new THREE.Vector3();
  for (let i = 0; i < n; i++) {
    v.fromBufferAttribute(p, i);
    const d = candidatos.map(b => [b, Math.pow(1 / Math.max(distSeg(v, SEGMENTO[b]), 0.004), exponente)]).sort((a, b) => b[1] - a[1]).slice(0, 3);
    const tot = d.reduce((s, x) => s + x[1], 0);
    d.forEach(([b, w], k) => { si[4 * i + k] = IDX[b]; sw[4 * i + k] = w / tot; });
  }
  geo.setAttribute("skinIndex", new THREE.Uint16BufferAttribute(si, 4));
  geo.setAttribute("skinWeight", new THREE.Float32BufferAttribute(sw, 4));
  return geo;
}

// ------------------------------------------------------------------------------------------------ geometría del cuerpo
// tubo a lo largo de una línea quebrada con sección elíptica: puntos [V], radios [[rx, rz]] (rx lateral)
function tubo(puntos, radios, seg = 14, tapas = true, aplanar = null) {
  const N = puntos.length, pos = [], idx = [];
  const ref = V(0, 0, 1);
  for (let k = 0; k < N; k++) {
    const a = puntos[Math.max(k - 1, 0)], b = puntos[Math.min(k + 1, N - 1)];
    const t = V(0, 0, 0).subVectors(b, a).normalize();
    let x = V(0, 0, 0).crossVectors(ref, t);
    if (x.lengthSq() < 1e-6) x.set(1, 0, 0);
    x.normalize();
    const z = V(0, 0, 0).crossVectors(t, x).normalize();
    const [rx, rz] = radios[k];
    for (let j = 0; j < seg; j++) {
      const ang = (j / seg) * Math.PI * 2;
      let cx = Math.cos(ang) * rx, cz = Math.sin(ang) * rz;
      if (aplanar) [cx, cz] = aplanar(cx, cz, k / (N - 1), ang);
      pos.push(puntos[k].x + x.x * cx + z.x * cz, puntos[k].y + x.y * cx + z.y * cz, puntos[k].z + x.z * cx + z.z * cz);
    }
  }
  for (let k = 0; k < N - 1; k++) for (let j = 0; j < seg; j++) {
    const a = k * seg + j, b = k * seg + (j + 1) % seg, c = (k + 1) * seg + j, d = (k + 1) * seg + (j + 1) % seg;
    idx.push(a, c, b, b, c, d);
  }
  if (tapas) {
    [0, N - 1].forEach((k, e) => {
      const c = pos.length / 3;
      pos.push(puntos[k].x, puntos[k].y, puntos[k].z);
      for (let j = 0; j < seg; j++) {
        const a = k * seg + j, b = k * seg + (j + 1) % seg;
        e ? idx.push(c, a, b) : idx.push(c, b, a);
      }
    });
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}
// torso por secciones horizontales tipo superelipse: [y, medio ancho, medio fondo, desplazamiento z]
function torso(secciones, ancho, seg = 30) {
  const pos = [], idx = [], N = secciones.length;
  secciones.forEach(([y, w, d, dz]) => {
    for (let j = 0; j < seg; j++) {
      const a = (j / seg) * Math.PI * 2, c = Math.cos(a), s = Math.sin(a);
      const e = 2.6, cx = Math.sign(c) * Math.pow(Math.abs(c), 2 / e), sz = Math.sign(s) * Math.pow(Math.abs(s), 2 / e);
      // espalda más plana que el pecho
      const fondo = s < 0 ? d * 0.92 : d;
      pos.push(cx * w * ancho, y, sz * fondo * ancho + dz);
    }
  });
  for (let k = 0; k < N - 1; k++) for (let j = 0; j < seg; j++) {
    const a = k * seg + j, b = k * seg + (j + 1) % seg, c = (k + 1) * seg + j, d = (k + 1) * seg + (j + 1) % seg;
    idx.push(a, b, c, b, d, c);
  }
  [0, N - 1].forEach((k, e) => {
    const c = pos.length / 3;
    pos.push(0, secciones[k][0], secciones[k][3]);
    for (let j = 0; j < seg; j++) { const a = k * seg + j, b = k * seg + (j + 1) % seg; e ? idx.push(c, a, b) : idx.push(c, b, a); }
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}
function elipsoide(c, r, ws = 20, hs = 14) {
  const g = new THREE.SphereGeometry(1, ws, hs);
  g.scale(r.x, r.y, r.z);
  g.translate(c.x, c.y, c.z);
  g.deleteAttribute("uv");
  return g;
}

// ropa y piel según el ID (Colombia: tonos de piel trigueños, pelo oscuro)
const PIELES = [0xb48a70, 0x9c7259, 0xc59a80, 0x7e5843, 0xcfa991, 0x8c6650];
const CAMISAS = [0x2c4f7c, 0x8a2f2f, 0xd9d4c7, 0x3d5a40, 0xc9a227, 0x5e4b7a, 0x2b2b2b, 0xa65e2e, 0x6f8fa8, 0xe8e8e8];
const PANTALONES = [0x2a3a5a, 0x1f2a40, 0x3a3a3a, 0x6b5b45, 0x4a4f3a, 0x23262b];
const ZAPATOS = [0xeeeeee, 0x2a2a2a, 0x5a3a24, 0x7a7f86];
const PELOS = [0x1a1410, 0x24180f, 0x0f0c0a, 0x3a2716];

function vestuario(p) {
  const r = azar(1000 + (p.id ?? 7) * 7919);
  const ladron = p.rol === "ladron";
  return {
    piel: PIELES[Math.floor(r() * PIELES.length)],
    camisa: ladron ? 0x26292e : CAMISAS[Math.floor(r() * CAMISAS.length)],
    pantalon: ladron ? 0x1d2433 : PANTALONES[Math.floor(r() * PANTALONES.length)],
    zapatos: ladron ? 0x3a3d42 : ZAPATOS[Math.floor(r() * ZAPATOS.length)],
    pelo: PELOS[Math.floor(r() * PELOS.length)],
    mangaLarga: ladron || r() < 0.35,
    capucha: ladron,
    gorra: !ladron && r() < 0.3,
    gorraColor: CAMISAS[Math.floor(r() * CAMISAS.length)],
    ancho: 0.93 + r() * 0.16,
    barriga: !ladron && r() < 0.3 ? 0.012 + r() * 0.02 : 0,
    mujer: !ladron && r() < 0.45,
    semilla: r(),
  };
}

function construirMalla(ves) {
  const A = ves.ancho, B = ves.barriga, mu = ves.mujer ? 1 : 0;
  const partes = [], mats = [];
  const poner = (g, mat, cand) => { pesar(g, cand); partes.push(g); mats.push(mat); };
  // -------- torso: pantalón (abajo) y camisa (arriba)
  const caderaW = 0.165 + 0.012 * mu, hombroW = 0.168 - 0.014 * mu;
  const abajo = [[0.80, 0.11, 0.085, -0.01], [0.84, 0.15, 0.105, -0.015], [0.90, caderaW, 0.115, -0.018], [0.96, caderaW - 0.005, 0.112, -0.01],
                 [1.03, 0.150, 0.102 + B, 0.0 + B * 0.6]];
  const arriba = [[1.01, 0.152, 0.104 + B, B * 0.6], [1.07, 0.142 - 0.008 * mu, 0.097 + B * 1.2, 0.006 + B], [1.13, 0.146 - 0.01 * mu, 0.10 + B * 0.8, 0.01 + B * 0.6],
                  [1.20, 0.158 - 0.004 * mu, 0.11 + 0.008 * mu, 0.014], [1.27, 0.170 - 0.006 * mu, 0.118 + 0.01 * mu, 0.016], [1.33, hombroW - 0.006, 0.117, 0.012],
                  [1.39, hombroW, 0.107, 0.004], [1.43, hombroW - 0.015, 0.09, -0.004], [1.455, 0.115, 0.07, -0.008], [1.475, 0.07, 0.058, -0.008]];
  poner(torso(abajo, A), "pantalon", ["cadera", "columna", "muslo_L", "muslo_R"]);
  poner(torso(arriba, A), "camisa", ["cadera", "columna", "pecho", "cuello", "clav_L", "clav_R", "brazo_L", "brazo_R"]);
  // -------- cuello y cabeza
  poner(tubo([V(0, 1.44, -0.005), V(0, 1.53, 0.0), V(0, 1.585, 0.01)], [[0.052, 0.055], [0.05, 0.052], [0.052, 0.05]], 14), "piel", ["pecho", "cuello", "cabeza"]);
  const cabeza = elipsoide(V(0, 1.635, 0.012), V(0.077, 0.102, 0.094), 28, 20);
  poner(cabeza, "piel", ["cabeza", "cuello"]);
  poner(elipsoide(V(0, 1.585, 0.042), V(0.058, 0.05, 0.055), 18, 12), "piel", ["cabeza"]);          // mandíbula
  poner(elipsoide(V(0, 1.632, 0.104), V(0.014, 0.024, 0.018), 10, 8), "piel", ["cabeza"]);          // nariz
  [-1, 1].forEach(s => poner(elipsoide(V(0.077 * s, 1.632, 0.004), V(0.012, 0.03, 0.02), 10, 8), "piel", ["cabeza"]));   // orejas
  [-1, 1].forEach(s => poner(elipsoide(V(0.031 * s, 1.648, 0.088), V(0.012, 0.008, 0.006), 10, 6), "ojos", ["cabeza"]));
  // pelo: un casco algo más grande que la cabeza; lo que queda bajo la línea del pelo se esconde dentro
  const pelo = elipsoide(V(0, 1.642, 0.006), V(0.083, 0.108, 0.1), 28, 20), pp = pelo.attributes.position;
  for (let i = 0; i < pp.count; i++) {
    const vy = pp.getY(i) - 1.642, vz = pp.getZ(i) - 0.006, s = limitar(-vz / 0.1, -1, 1);
    const umbral = lerp(0.05, mu ? -0.13 : -0.055, (s + 1) / 2);
    if (vy < umbral) { pp.setX(i, pp.getX(i) * 0.8); pp.setY(i, (pp.getY(i) - 1.642) * 0.8 + 1.642); pp.setZ(i, vz * 0.8 + 0.006); }
  }
  pelo.computeVertexNormals();
  poner(pelo, "pelo", ["cabeza"]);
  if (ves.capucha) {
    const cap = elipsoide(V(0, 1.625, -0.012), V(0.1, 0.122, 0.112), 28, 20), cp = cap.attributes.position;
    for (let i = 0; i < cp.count; i++) {      // abierta adelante: la cara queda a la vista
      const vz = cp.getZ(i) + 0.012, vy = cp.getY(i) - 1.625;
      if (vz > 0.035 && vy > -0.09) { cp.setZ(i, lerp(cp.getZ(i), -0.02, 0.8)); cp.setX(i, cp.getX(i) * 0.85); }
    }
    cap.computeVertexNormals();
    poner(cap, "camisa", ["cabeza", "cuello"]);
  }
  if (ves.gorra) {
    poner(elipsoide(V(0, 1.68, 0.006), V(0.088, 0.055, 0.1), 24, 12), "gorra", ["cabeza"]);
    poner(elipsoide(V(0, 1.668, 0.11), V(0.075, 0.008, 0.06), 16, 6), "gorra", ["cabeza"]);
  }
  // -------- brazos (manga, antebrazo, mano)
  ["L", "R"].forEach(s => {
    const sx = s === "L" ? 1 : -1, h = REPOSO["brazo_" + s], c = REPOSO["antebrazo_" + s], m = REPOSO["mano_" + s];
    const sh = A * (1 - 0.1 * mu);
    const finManga = ves.mangaLarga ? 1.0 : 0.55;
    // el hombro: el tubo del brazo nace dentro del torso, redondeado (sin "hombreras")
    const pBrazo = [h.clone().add(V(-0.03 * sx, 0.035, 0)), h.clone().add(V(-0.005 * sx, 0.012, 0)), h.clone().lerp(c, 0.3), h.clone().lerp(c, 0.72), c.clone()];
    const rBrazo = [[0.035 * sh, 0.04 * sh], [0.054 * sh, 0.056 * sh], [0.05 * sh, 0.05 * sh], [0.043 * sh, 0.044 * sh], [0.039 * sh, 0.04 * sh]];
    if (ves.mangaLarga) {
      poner(tubo(pBrazo.concat([c.clone().lerp(m, 0.5), m.clone().add(V(0, 0.015, 0))]), rBrazo.concat([[0.04 * sh, 0.037 * sh], [0.034 * sh, 0.032 * sh]]), 14),
        "camisa", ["brazo_" + s, "antebrazo_" + s, "mano_" + s, "clav_" + s]);
      poner(tubo([m.clone().add(V(0, 0.03, 0)), m.clone()], [[0.027, 0.023], [0.026, 0.022]], 12), "piel", ["mano_" + s, "antebrazo_" + s]);
    } else {
      const corte = h.clone().lerp(c, finManga);
      poner(tubo([pBrazo[0], pBrazo[1], pBrazo[2], corte], [rBrazo[0], rBrazo[1], [rBrazo[2][0] * 1.08, rBrazo[2][1] * 1.08], [0.052 * sh, 0.052 * sh]], 14), "camisa", ["brazo_" + s, "clav_" + s]);
      poner(tubo([h.clone().lerp(c, 0.4), h.clone().lerp(c, 0.75), c, c.clone().lerp(m, 0.35), m.clone()],
        [[0.046, 0.046], [0.04, 0.041], [0.035, 0.037], [0.037, 0.035], [0.026, 0.022]], 14), "piel", ["brazo_" + s, "antebrazo_" + s, "mano_" + s]);
    }
    // mano: palma aplanada y pulgar
    const pm = m.clone().add(V(0.004 * sx, -0.06, 0.002));
    poner(elipsoide(pm, V(0.017, 0.052, 0.04), 14, 10), "piel", ["mano_" + s, "antebrazo_" + s]);
    poner(elipsoide(m.clone().add(V(0.0, -0.125, 0.004)), V(0.013, 0.045, 0.034), 12, 8), "piel", ["mano_" + s]);
    poner(elipsoide(m.clone().add(V(-0.004 * sx, -0.05, 0.036)), V(0.01, 0.03, 0.01), 8, 6), "piel", ["mano_" + s]);
  });
  // -------- piernas y zapatos
  ["L", "R"].forEach(s => {
    const sx = s === "L" ? 1 : -1, c = REPOSO["muslo_" + s], r = REPOSO["pierna_" + s], t = REPOSO["pie_" + s];
    const a = A * (1 + 0.04 * mu);
    poner(tubo([c.clone().add(V(-0.005 * sx, 0.06, 0)), c.clone().lerp(r, 0.3), c.clone().lerp(r, 0.7), r.clone(), r.clone().lerp(t, 0.3), r.clone().lerp(t, 0.72), t.clone().add(V(0, 0.02, 0))],
      [[0.092 * a, 0.098 * a], [0.08 * a, 0.085 * a], [0.062 * a, 0.066 * a], [0.052, 0.055], [0.058, 0.06], [0.044, 0.046], [0.04, 0.04]], 16),
      "pantalon", ["muslo_" + s, "pierna_" + s, "cadera", "pie_" + s]);
    // zapato: secciones a lo largo de z, del talón a la punta
    const sec = [[-0.055, 0.032, 0.038, 0.035], [-0.03, 0.045, 0.062, 0.047], [0.02, 0.048, 0.062, 0.05], [0.08, 0.052, 0.05, 0.03], [0.14, 0.048, 0.04, 0.024], [0.18, 0.03, 0.03, 0.02]];
    const pts = sec.map(([z, , hy]) => V(t.x, 0.0 + hy / 2 + 0.002, t.z + z)), rad = sec.map(([, w, hy]) => [w, hy / 2 + 0.004]);
    poner(tubo(pts, rad, 14, true, (cx, cz) => [cx, cz < 0 ? cz * 0.6 : cz]), "zapatos", ["pie_" + s, "dedos_" + s, "pierna_" + s]);
  });
  // -------- unir todo con grupos por material
  const orden = ["piel", "camisa", "pantalon", "zapatos", "pelo", "ojos", "gorra"];
  const porMat = orden.map(m => partes.filter((_, k) => mats[k] === m)).map(l => l.length ? mergeGeometries(l.map(g => g.index ? g : g)) : null);
  const usados = orden.filter((_, k) => porMat[k]);
  const geo = mergeGeometries(porMat.filter(Boolean), true);
  return { geo, materiales: usados };
}

// ------------------------------------------------------------------------------------------------ pose y mezcla
class Pose {
  constructor() {
    this.cadera = V(0, 0.98, 0); this.qCadera = new THREE.Quaternion();
    this.qCol = new THREE.Quaternion(); this.qPecho = new THREE.Quaternion(); this.qCuello = new THREE.Quaternion(); this.qCabeza = new THREE.Quaternion();
    this.pieL = V(0.1, ALTURA_TOBILLO, 0); this.pieR = V(-0.1, ALTURA_TOBILLO, 0);
    this.qPieL = new THREE.Quaternion(); this.qPieR = new THREE.Quaternion();
    this.rodL = V(0, 0, 1); this.rodR = V(0, 0, 1);
    // manos: en el sistema del PECHO (relativas al hombro) o absolutas en el sistema local de la persona
    this.manoL = V(0.02, -0.55, 0.03); this.manoR = V(-0.02, -0.55, 0.03);
    this.manoLa = V(0.2, 0.85, 0.05); this.manoRa = V(-0.2, 0.85, 0.05); this.absL = 0; this.absR = 0;
    this.codoL = V(0.4, -0.2, -1); this.codoR = V(-0.4, -0.2, -1);
    this.qManoL = new THREE.Quaternion(); this.qManoR = new THREE.Quaternion();
    this.celular = 0; this.manosArriba = 0;
  }
}
const CAMPOS_V = ["cadera", "pieL", "pieR", "rodL", "rodR", "codoL", "codoR"];
const CAMPOS_Q = ["qCadera", "qCol", "qPecho", "qCuello", "qCabeza", "qPieL", "qPieR", "qManoL", "qManoR"];
function mezclar(dst, src, w) {           // dst = dst·(1-w) + src·w
  CAMPOS_V.forEach(k => dst[k].lerp(src[k], w));
  // manos: cada espacio (relativo al hombro / absoluto) se mezcla solo con las poses que lo usan
  ["L", "R"].forEach(s => {
    const a = "abs" + s;
    if (src[a] < 0.5) dst["mano" + s].lerp(src["mano" + s], w);
    if (src[a] > 0.5) { if (dst[a] < 0.01) dst["mano" + s + "a"].copy(src["mano" + s + "a"]); else dst["mano" + s + "a"].lerp(src["mano" + s + "a"], w); }
  });
  CAMPOS_Q.forEach(k => dst[k].slerp(src[k], w));
  dst.absL = lerp(dst.absL, src.absL, w); dst.absR = lerp(dst.absR, src.absR, w);
  dst.celular = lerp(dst.celular, src.celular, w);
  return dst;
}
const qE = (x, y, z, orden = "YXZ") => new THREE.Quaternion().setFromEuler(new THREE.Euler(x, y, z, orden));
const D = Math.PI / 180;

// ------------------------------------------------------------------------------------------------ IK de 2 huesos
const _m1 = new THREE.Matrix4(), _m2 = new THREE.Matrix4();
function marco(dir, n, m) {
  const y = dir.clone().normalize(), x = n.clone().addScaledVector(y, -n.dot(y)).normalize(), z = V(0, 0, 0).crossVectors(x, y);
  return m.makeBasis(x, y, z);
}
// devuelve las rotaciones "de mundo" (en el sistema local de la persona) del hueso superior e inferior
function ik2(raiz, objetivo, a, b, polo, restU, restL, nRest) {
  const d = V(0, 0, 0).subVectors(objetivo, raiz);
  let c = d.length();
  c = limitar(c, Math.abs(a - b) + 1e-3, (a + b) * 0.9995);
  const dn = d.normalize();
  const flex = polo.clone().addScaledVector(dn, -polo.dot(dn));
  if (flex.lengthSq() < 1e-8) flex.set(0, 0, 1).addScaledVector(dn, -dn.z);
  flex.normalize();
  const cosA = limitar((a * a + c * c - b * b) / (2 * a * c), -1, 1), sinA = Math.sqrt(1 - cosA * cosA);
  const codo = raiz.clone().addScaledVector(dn, a * cosA).addScaledVector(flex, a * sinA);
  const fin = raiz.clone().addScaledVector(dn, c);
  const n = V(0, 0, 0).crossVectors(dn, flex).normalize();
  const dU = V(0, 0, 0).subVectors(codo, raiz), dL = V(0, 0, 0).subVectors(fin, codo);
  const qU = new THREE.Quaternion().setFromRotationMatrix(marco(dU, n, _m1).multiply(_m2.copy(marco(restU, nRest, _m2)).invert()));
  const qL = new THREE.Quaternion().setFromRotationMatrix(marco(dL, n, _m1).multiply(_m2.copy(marco(restL, nRest, _m2)).invert()));
  return { qU, qL, codo, fin };
}
const REST_DIR = {};
["L", "R"].forEach(s => {
  REST_DIR["muslo_" + s] = V(0, 0, 0).subVectors(REPOSO["pierna_" + s], REPOSO["muslo_" + s]).normalize();
  REST_DIR["pierna_" + s] = V(0, 0, 0).subVectors(REPOSO["pie_" + s], REPOSO["pierna_" + s]).normalize();
  REST_DIR["brazo_" + s] = V(0, 0, 0).subVectors(REPOSO["antebrazo_" + s], REPOSO["brazo_" + s]).normalize();
  REST_DIR["antebrazo_" + s] = V(0, 0, 0).subVectors(REPOSO["mano_" + s], REPOSO["antebrazo_" + s]).normalize();
});
const N_REST_PIERNA = V(-1, 0, 0);                 // la rodilla se dobla hacia adelante (+z)
const N_REST_BRAZO = V(1, 0, 0);                   // el codo se dobla hacia atrás (-z)

// ------------------------------------------------------------------------------------------------ la persona
export class Humano {
  constructor(p) {
    this.p0 = p;
    this.ves = vestuario(p);
    this.raiz = new THREE.Group();
    const { geo, materiales } = construirMalla(this.ves);
    const ves = this.ves;
    const color = { piel: ves.piel, camisa: ves.camisa, pantalon: ves.pantalon, zapatos: ves.zapatos, pelo: ves.pelo, ojos: 0x1a1512, gorra: ves.gorraColor };
    const rug = { piel: 0.55, camisa: 0.85, pantalon: 0.8, zapatos: 0.6, pelo: 0.75, ojos: 0.2, gorra: 0.8 };
    this.mats = materiales.map(m => new THREE.MeshStandardMaterial({ color: color[m], roughness: rug[m], metalness: 0 }));
    // huesos
    this.huesos = [];
    HUESOS.forEach(([n, padre, p0]) => {
      const b = new THREE.Bone();
      b.name = n;
      b.position.copy(padre ? p0.clone().sub(REPOSO[padre]) : p0);
      if (padre) this.huesos[IDX[padre]].add(b);
      this.huesos.push(b);
    });
    this.H = Object.fromEntries(HUESOS.map(([n], i) => [n, this.huesos[i]]));
    this.malla = new THREE.SkinnedMesh(geo, this.mats);
    this.malla.add(this.huesos[0]);
    this.malla.bind(new THREE.Skeleton(this.huesos));
    this.malla.castShadow = true;
    this.malla.receiveShadow = true;
    this.malla.frustumCulled = false;
    this.raiz.add(this.malla);
    // celular (solo se ve cuando graba)
    this.celular = new THREE.Mesh(new THREE.BoxGeometry(0.075, 0.15, 0.009), new THREE.MeshStandardMaterial({ color: 0x111317, roughness: 0.3, metalness: 0.5 }));
    this.celular.position.set(0.0, -0.1, 0.04);
    this.celular.visible = false;
    this.H.mano_R.add(this.celular);
    // estado de la animación
    this.escala = (p.est || ALTO_BASE) / ALTO_BASE;
    this.raiz.scale.setScalar(this.escala);
    this.yaw = null;
    this.fase = Math.random();
    this.vel = V(0, 0, 0);                 // velocidad suavizada (mundo three)
    this.pesos = { pie: 1, agachado: 0, recostado: 0, gateo: 0 };
    this.capas = { salto: 0, mira: 0, chisme: 0, graba: 0, esquiva: 0, rinde: 0 };
    this.cabezaMira = V(0, 1.6, 2);
    this.posAnterior = 0;
    this.salto = { fase: 0, anclaL: null, anclaR: null, t: 0, avance: 0, h: 2.3 };
    this.asomo = { t: 2 + Math.random() * 3, lado: 1, activo: 0 };
    this.mano = new THREE.Vector3();
    this.rasgo = { balanceo: 0.8 + ves.semilla * 0.4, cabezaT: ves.semilla * 10 };
  }
  liberar() { this.malla.geometry.dispose(); this.mats.forEach(m => m.dispose()); }

  // posición de la mano derecha en el mundo (para la prueba del salto y la cámara)
  manoMundo(v = new THREE.Vector3()) { return this.H.mano_R.getWorldPosition(v); }

  actualizar(p, dt, ctx) {
    // dt: tiempo de la partida (marcha, salto); dtR: reloj real (las mezclas de postura siguen aunque esté en pausa)
    const dtR = Math.max(dt, ctx.dtReal || 0);
    // ---------------------------------------------------------------- posición, rumbo y velocidad
    this.raiz.position.copy(mundo(p.x, p.y, 0));
    const vMundo = V(p.vx, 0, -p.vy);
    if (this.yaw === null) this.vel.copy(vMundo);          // la primera vez arranca con su velocidad y su rumbo
    const k = 1 - Math.exp(-dt / 0.18);
    this.vel.lerp(vMundo, dt > 0 ? k : 0);
    const rapidez = this.vel.length();
    let yawObj = this.yaw ?? 0;
    if (p.mira !== undefined && p.mira !== null) yawObj = p.mira + Math.PI / 2;
    else if (rapidez > 0.3) yawObj = Math.atan2(this.vel.x, this.vel.z);
    if (this.yaw === null) this.yaw = yawObj;
    const giro = angNorm(yawObj - this.yaw);
    const maxG = (rapidez > 2.5 ? 5 : 3.2) * dtR;
    this.yaw += limitar(giro * (1 - Math.exp(-dtR / 0.12)), -maxG, maxG);
    this.raiz.rotation.y = this.yaw;
    this.raiz.updateMatrixWorld(true);
    // velocidad y dirección del movimiento en el sistema de la persona
    const cy = Math.cos(-this.yaw), sy = Math.sin(-this.yaw);
    const mLoc = V(this.vel.x * cy + this.vel.z * sy, 0, -this.vel.x * sy + this.vel.z * cy).divideScalar(this.escala);
    const v = mLoc.length();
    const dir = v > 0.05 ? mLoc.clone().normalize() : V(0, 0, 1);
    // ---------------------------------------------------------------- pesos de las posturas (transición mezclada)
    const pos = p.pos ?? 0;
    const objetivo = { pie: pos === 0 ? 1 : 0, agachado: pos === 1 ? 1 : 0, recostado: pos === 2 ? 1 : 0, gateo: pos === 3 ? 1 : 0 };
    if (pos !== this.posAnterior) { this.desdePos = this.posAnterior; this.posAnterior = pos; }
    if (p.pt !== undefined && p.pt < 1 && this.desdePos !== undefined && this.desdePos !== pos) {
      const w = suave(p.pt);           // la transición la marca la simulación (0.5-1 s)
      Object.keys(this.pesos).forEach(kk => { this.pesos[kk] = 0; });
      this.pesos[["pie", "agachado", "recostado", "gateo"][this.desdePos]] = 1 - w;
      this.pesos[["pie", "agachado", "recostado", "gateo"][pos]] = w;
    } else {
      const kp = 1 - Math.exp(-dtR / 0.22);
      Object.keys(this.pesos).forEach(kk => { this.pesos[kk] = lerp(this.pesos[kk], objetivo[kk], kp); });
    }
    // capas: salto, mirar el dron, grabar, esquivar, rendirse
    const s = p.salto, fs = s ? s[0] : (p.sz > 0.05 ? 2 : 0);
    const dronL = this.raiz.worldToLocal(ctx.dron.clone());
    const distDron = Math.hypot(dronL.x, dronL.z);
    const civ = p.civ;
    const cObj = {
      salto: fs > 0 ? 1 : 0,
      mira: (civ === 1 || civ === 4 || p.rinde || (p.rol === "ladron" && pos !== 3 && distDron < 14)) ? 1 : civ === 3 ? 0.4 : civ === 2 ? 1 : 0.15,
      chisme: civ === 1 ? 1 : 0, graba: civ === 4 ? 1 : 0, esquiva: civ === 2 ? 1 : 0, rinde: p.rinde ? 1 : 0,
    };
    const kc = 1 - Math.exp(-dtR / 0.25);
    Object.keys(this.capas).forEach(kk => { this.capas[kk] = kk === "salto" ? (cObj.salto ? 1 : lerp(this.capas.salto, 0, 1 - Math.exp(-dtR / 0.3))) : lerp(this.capas[kk], cObj[kk], kc); });
    // ---------------------------------------------------------------- fase de la marcha (con la distancia: los pies no patinan)
    const zancada = this.pesos.gateo * 0.5 + this.pesos.agachado * (0.65 + 0.45 * v) + (this.pesos.pie + this.pesos.recostado) * (0.85 + 0.42 * v);
    if (v > 0.08) this.fase = (this.fase + v * dt / Math.max(zancada, 0.3)) % 1;
    this.t = (this.t || 0) + dt;
    const C = { v, dir, fase: this.fase, t: this.t, dt, dronL, distDron, p, ctx };
    // ---------------------------------------------------------------- poses por postura y mezcla
    const pose = new Pose();
    let acum = 0;
    const gen = { pie: this.posePie, agachado: this.poseAgachado, recostado: this.poseRecostado, gateo: this.poseGateo };
    Object.entries(this.pesos).forEach(([kk, w]) => {
      if (w < 0.002) return;
      const q = gen[kk].call(this, C);
      if (!acum) { mezclar(pose, q, 1); acum = w; return; }
      acum += w;
      mezclar(pose, q, w / acum);
    });
    // capas de acción encima de la postura
    if (this.capas.esquiva > 0.01) mezclar(pose, this.poseEsquiva(C, pose), this.capas.esquiva * 0.75);
    if (this.capas.chisme > 0.01) mezclar(pose, this.poseChisme(C, pose), this.capas.chisme);
    if (this.capas.graba > 0.01) mezclar(pose, this.poseGraba(C, pose), this.capas.graba);
    if (this.capas.rinde > 0.01) mezclar(pose, this.poseRinde(C, pose), this.capas.rinde);
    if (this.capas.salto > 0.01) mezclar(pose, this.poseSalto(C, pose, s, p), this.capas.salto);
    else this.salto.fase = 0;
    // mirar: la cabeza (y algo del pecho) sigue al dron o a donde va
    this.mirar(pose, C);
    this.aplicar(pose);
    this.celular.visible = pose.celular > 0.5;
  }

  // ------------------------------------------------------------------------------------------- generadores de pose
  marcha(C, o) {
    // o: alturas y amplitudes de la marcha según la postura
    const P = new Pose(), { v, dir, fase } = C;
    const corre = limitar((v - 2.0) / 2.5, 0, 1), anda = limitar(v / 0.6, 0, 1);
    const L = o.zancada(v), beta = lerp(o.apoyoAndar, o.apoyoCorrer, corre);
    const lado = V(dir.z, 0, -dir.x);
    const pies = [];
    [0, 0.5].forEach((desf, i) => {
      const ph = (fase + desf) % 1;
      let sAlong, alto = 0, cabeceo = 0;
      // el pie apoya un poco adelante de la cadera y despega más atrás (como en la marcha real)
      const adel = beta * L * lerp(0.46, 0.4, corre), atras = beta * L - adel;
      if (ph < beta) {                       // apoyo: el pie va hacia atrás a la velocidad del cuerpo (no patina)
        const u = ph / beta;
        sAlong = lerp(adel, -atras, u);
        cabeceo = u < 0.15 ? lerp(-12, 0, u / 0.15) * D * anda : u > 0.6 ? lerp(0, 38 + 22 * corre, (u - 0.6) / 0.4) * D * anda : 0;
        alto = u > 0.6 ? 0.13 * Math.sin(cabeceo) : u < 0.15 ? 0.02 * (1 - u / 0.15) * anda : 0;      // talón arriba al despegar
      } else {                               // vuelo: arco hacia adelante, levanta más al correr
        const u = (ph - beta) / (1 - beta);
        sAlong = lerp(-atras, adel, suave(u));
        const pico = lerp(0.5, 0.32, corre);
        alto = (o.levante + o.levanteCorrer * corre) * Math.sin(Math.PI * Math.pow(u, pico / 0.5 * 0.9 + 0.1)) * anda;
        cabeceo = lerp(45 * corre + 20, -15, u) * D * anda;
      }
      const sx = i === 0 ? 1 : -1, ancho = lerp(o.ancho, o.ancho * 0.55, corre) * sx;
      const pPie = V(0, 0, 0).addScaledVector(dir, sAlong * anda).addScaledVector(lado, ancho);
      pPie.x += sx * 0.01; pPie.y = ALTURA_TOBILLO + alto;
      pies.push([pPie, cabeceo, ph]);
    });
    P.pieL.copy(pies[0][0]); P.pieR.copy(pies[1][0]);
    let giroPie = Math.atan2(dir.x, dir.z);
    if (Math.abs(giroPie) > Math.PI / 2) giroPie = angNorm(giroPie + Math.PI);      // hacia atrás: el pie no se da vuelta
    giroPie = limitar(giroPie, -45 * D, 45 * D) * anda;
    P.qPieL = qE(pies[0][1], giroPie + 6 * D, 0); P.qPieR = qE(pies[1][1], giroPie - 6 * D, 0);
    // cadera: baja al correr, sube y baja dos veces por ciclo; gira con la pierna que avanza
    const ciclo = 2 * Math.PI * fase;
    // la cadera queda más alta a mitad del apoyo y más baja con los dos pies en el piso (al correr, alta en el vuelo)
    const rebote = lerp(0.02, 0.04, corre) * Math.cos(4 * Math.PI * (fase - beta / 2) + corre * Math.PI * 0.9) * anda;
    P.cadera.set(0.012 * Math.sin(ciclo) * anda * (1 - corre), o.altura - lerp(0.04, 0.075, corre) * anda + rebote, 0.02 * corre);
    const inclina = (o.inclina + 14 * corre + 3 * anda) * D;
    const girar = Math.sin(ciclo) * lerp(5, 10, corre) * D * anda;
    P.qCadera = qE(inclina * 0.4, girar, -Math.sin(ciclo) * 3 * D * anda);
    P.qCol = qE(inclina * 0.3, -girar * 0.6, 0);
    P.qPecho = qE(inclina * 0.3, -girar * 0.9, Math.sin(ciclo) * 2 * D * anda);
    // brazos: van al contrario de las piernas; al correr el codo se dobla ~90°
    const amp = lerp(18, 55, corre) * anda * this.rasgo.balanceo;
    [["L", 1, Math.PI], ["R", -1, 0]].forEach(([s_, sx, desf]) => {
      const ang = (Math.sin(ciclo + desf) * amp + 4) * D;
      const flexion = lerp(0.04, 0.28, corre) + 0.05 * anda;
      const largo = LARGO.brazo + LARGO.antebrazo;
      const mano = V(0.03 * sx + 0.04 * corre * -sx, -Math.cos(ang) * largo * (1 - flexion), Math.sin(ang) * largo * (1 - flexion) + flexion * 0.22);
      P["mano" + s_].copy(mano);
      P["codo" + s_].set(0.35 * sx, -0.1, -1);
    });
    P.rodL.set(0.08, 0, 1); P.rodR.set(-0.08, 0, 1);
    return P;
  }
  posePie(C) {
    const P = this.marcha(C, { altura: 0.98, inclina: 0, zancada: v => 0.85 + 0.42 * v, apoyoAndar: 0.62, apoyoCorrer: 0.36,
                              levante: 0.11, levanteCorrer: 0.2, ancho: 0.1 });
    // quieto: respiración y cambio de peso lento
    const quieto = 1 - limitar(C.v / 0.4, 0, 1);
    if (quieto > 0) {
      const t = C.t + this.rasgo.cabezaT, apoyo = Math.sin(t * 0.35) * 0.5;
      P.cadera.x += 0.03 * apoyo * quieto;
      P.cadera.y -= 0.005 * quieto;
      P.qPecho.multiply(qE(Math.sin(t * 1.6) * 1.2 * D * quieto, 0, 0));
      P.qCadera.multiply(qE(0, 0, -apoyo * 3 * D * quieto));
      P.pieL.x += 0.02 * quieto; P.pieR.x -= 0.02 * quieto;
    }
    return P;
  }
  poseAgachado(C) {
    const P = this.marcha(C, { altura: 0.64, inclina: 26, zancada: v => 0.65 + 0.45 * v, apoyoAndar: 0.7, apoyoCorrer: 0.6,
                              levante: 0.07, levanteCorrer: 0.03, ancho: 0.12 });
    P.qCadera.multiply(qE(14 * D, 0, 0));
    P.qCuello = qE(-22 * D, 0, 0);
    P.rodL.set(0.15, 0, 1); P.rodR.set(-0.15, 0, 1);
    // manos adelante, sobre las rodillas (listo para moverse): en el sistema del pecho, que va inclinado ~40°
    const t = C.t;
    P.manoL.set(0.06, -0.1, 0.4 + 0.02 * Math.sin(t)); P.manoR.set(-0.06, -0.12, 0.38);
    P.codoL.set(0.8, 0, -0.5); P.codoR.set(-0.8, 0, -0.5);
    return P;
  }
  poseGateo(C) {
    const P = new Pose(), { v, fase } = C, anda = limitar(v / 0.15, 0, 1);
    // en cuatro patas: cadera a ~0.5 m, tronco casi horizontal, rodillas y manos en el piso, gateo cruzado
    P.cadera.set(0, 0.5, -0.2);
    P.qCadera = qE(76 * D, Math.sin(2 * Math.PI * fase) * 6 * D * anda, 0);
    P.qCol = qE(-4 * D, 0, 0);
    P.qPecho = qE(-6 * D, -Math.sin(2 * Math.PI * fase) * 5 * D * anda, 0);
    P.qCuello = qE(-48 * D, 0, 0);
    P.qCabeza = qE(-10 * D, 0, 0);
    const L = 0.5, beta = 0.7;
    const paso = (ph) => {
      if (ph < beta) return [lerp(beta * L / 2, -beta * L / 2, ph / beta), 0];
      const u = (ph - beta) / (1 - beta);
      return [lerp(-beta * L / 2, beta * L / 2, suave(u)), Math.sin(Math.PI * u)];
    };
    // rodillas (el tobillo va detrás, con la espinilla sobre el piso); manos bajo los hombros
    [["L", 1, 0.5], ["R", -1, 0]].forEach(([s_, sx, desf]) => {
      const [sp, sh] = paso((fase + desf) % 1);
      P["pie" + s_].set(0.11 * sx, 0.09 + 0.04 * sh * anda, -0.62 + sp * anda);
      P["rod" + s_].set(0.1 * sx, -1, 0.35);
      P["qPie" + s_] = qE(70 * D, 0, 0);
      const [mp, mh] = paso((fase + desf + 0.5) % 1);
      // la mano, absoluta: en el piso delante de la cadera
      P["mano" + s_ + "a"].set(0.17 * sx, 0.03 + 0.07 * mh * anda, 0.36 + mp * anda);
      P["abs" + s_] = 1;
      P["codo" + s_].set(0.6 * sx, 0, -1);
    });
    return P;
  }
  poseRecostado(C) {
    // de espaldas contra el muro: pies adelantados, espalda apoyada, un pie contra la pared; se asoma cada tanto
    const P = new Pose(), t = C.t;
    P.cadera.set(0, 0.93, 0.03);
    P.qCadera = qE(-4 * D, 0, 0);
    P.qCol = qE(-3 * D, 0, 0);
    P.qPecho = qE(-5 * D, 0, 0);
    P.pieL.set(0.13, ALTURA_TOBILLO, 0.28);
    P.pieR.set(-0.12, 0.36, -0.12);              // planta contra la pared, rodilla doblada
    P.qPieR = qE(-55 * D, -10 * D, 0);
    P.qPieL = qE(0, 8 * D, 0);
    P.rodL.set(0.1, 0, 1); P.rodR.set(-0.2, 0.3, 1);
    P.manoL.set(0.05, -0.5, -0.08); P.manoR.set(-0.05, -0.5, -0.08);
    P.codoL.set(1, 0, 0.2); P.codoR.set(-1, 0, 0.2);
    // asomarse: inclina el tronco hacia el borde del muro y gira la cabeza
    const a = this.asomo;
    a.t -= C.dt;
    if (a.t <= 0) { a.activo = a.activo ? 0 : 1; a.t = a.activo ? 1.4 + Math.random() : 2.5 + Math.random() * 3; if (a.activo) a.lado = this.ladoAsomo(C); }
    a.peso = lerp(a.peso || 0, a.activo, 1 - Math.exp(-C.dt / 0.3));
    const w = a.peso, ld = a.lado;
    P.cadera.x += 0.06 * ld * w;
    P.qCol.multiply(qE(0, 0, -9 * ld * w * D));
    P.qPecho.multiply(qE(0, 12 * ld * w * D, -10 * ld * w * D));
    P.qCuello = qE(0, 35 * ld * w * D, -6 * ld * w * D);
    P.qCabeza = qE(-4 * D, 40 * ld * w * D, 0);
    this.asomando = w;
    return P;
  }
  ladoAsomo(C) {
    // el borde del muro más cercano, visto desde la persona
    const muros = C.ctx.muros || [];
    let mejor = null, dm = 1e9;
    const px = C.p.x, py = C.p.y;
    muros.forEach(([x1, y1, x2, y2]) => [[x1, y1], [x2, y2]].forEach(([x, y]) => { const d = Math.hypot(x - px, y - py); if (d < dm) { dm = d; mejor = [x, y]; } }));
    if (!mejor) return Math.random() < 0.5 ? -1 : 1;
    const loc = this.raiz.worldToLocal(mundo(mejor[0], mejor[1], 0));
    return loc.x >= 0 ? 1 : -1;
  }
  poseEsquiva(C, base) {
    // sobresalto: se encoge, levanta los brazos para cubrirse y se inclina lejos del dron
    const P = new Pose();
    mezclar(P, base, 1);
    const lejos = C.dronL.x > 0 ? -1 : 1;
    P.cadera.y -= 0.05;
    P.qCol.multiply(qE(8 * D, 0, 8 * lejos * D));
    P.manoL.set(-0.05, -0.12, 0.25); P.manoR.set(0.05, -0.1, 0.22);
    P.absL = 0; P.absR = 0;
    P.codoL.set(1, -0.3, -0.2); P.codoR.set(-1, -0.3, -0.2);
    return P;
  }
  poseChisme(C, base) {
    // el civil se queda mirando el dron ("chismoseando"): visera con la mano, brazos cruzados o manos en la cintura
    const P = new Pose();
    mezclar(P, base, 1);
    const tipo = Math.floor(this.ves.semilla * 3);
    if (tipo === 0) {
      P.manoR.set(0.05, 0.2, 0.22); P.codoR.set(-1, -0.3, 0.2);          // visera sobre los ojos
      P.manoL.set(0.0, -0.5, 0.06);
    } else if (tipo === 1) {
      P.manoL.set(-0.2, -0.28, 0.17); P.manoR.set(0.2, -0.26, 0.15);      // brazos cruzados
      P.codoL.set(0.6, -1, 0); P.codoR.set(-0.6, -1, 0);
    } else {
      P.manoL.set(-0.03, -0.42, -0.02); P.manoR.set(0.03, -0.42, -0.02);  // manos en la cintura
      P.codoL.set(1, -0.2, -0.2); P.codoR.set(-1, -0.2, -0.2);
    }
    P.absL = P.absR = 0;
    P.cadera.x += 0.03;                                                   // carga el peso en una pierna
    P.qCadera.multiply(qE(0, 0, -3 * D));
    return P;
  }
  poseGraba(C, base) {
    // graba con el celular: la mano derecha (y la izquierda de apoyo) frente a la cara, apuntando al dron
    const P = new Pose();
    mezclar(P, base, 1);
    // a la altura de los ojos, 30 cm adelante en la dirección del dron, un poco más alto si el dron está alto
    const ojo = V(0, 1.6, 0.08), haciaDron = C.dronL.clone().sub(ojo);
    const subir = limitar(Math.atan2(haciaDron.y, Math.hypot(haciaDron.x, haciaDron.z)) / (60 * D), 0, 1);
    haciaDron.y = 0; haciaDron.normalize();
    const m = ojo.clone().addScaledVector(haciaDron, 0.3).add(V(0, 0.02 + 0.1 * subir, 0));
    P.manoRa.copy(m).add(V(-0.02, 0.05, 0)); P.absR = 1;
    P.manoLa.copy(m).add(V(0.05, 0.02, -0.02)); P.absL = 1;
    P.codoR.set(-1, -0.5, -0.3); P.codoL.set(1, -0.5, -0.3);
    P.celular = 1;
    return P;
  }
  poseRinde(C, base) {
    const P = new Pose();
    mezclar(P, base, 1);
    // manos arriba a los lados de la cabeza, codos abiertos y doblados
    P.manoL.set(0.2, 0.4, 0.06); P.manoR.set(-0.2, 0.4, 0.06);
    P.absL = 0; P.absR = 0;
    P.codoL.set(1, -0.8, 0); P.codoR.set(-1, -0.8, 0);
    P.qPecho.multiply(qE(-4 * D, 0, 0));
    return P;
  }

  // -------------------------------------------------------------------------------- el salto para agarrar el dron
  // Fases: 1 impulso (se agacha, brazos atrás, y estalla hacia arriba), 2 vuelo (cuerpo extendido, brazo derecho
  // estirado hacia el dron, piernas recogidas en el punto alto), 3 aterrizaje (amortigua con las rodillas),
  // 4 recuperación (se para sin dejar de mirar el dron). La altura de la mano viene de la simulación.
  poseSalto(C, base, s, p) {
    const P = new Pose(), S = this.salto;
    mezclar(P, base, 1);
    let fase = s ? s[0] : (p.sz > 0.05 ? 2 : 0), avance = s && s[2] !== undefined ? s[2] : null;
    const hMano = s ? s[1] : 2.27 + (p.sz || 0) * 1.0;
    if (fase !== S.fase) {
      // anclar los pies en el mundo al empezar el impulso y al aterrizar
      if (fase === 1 || fase === 3) {
        S.anclaL = this.raiz.localToWorld(V(0.11, ALTURA_TOBILLO, fase === 1 ? 0.05 : 0.12));
        S.anclaR = this.raiz.localToWorld(V(-0.11, ALTURA_TOBILLO, fase === 1 ? -0.12 : -0.02));
      }
      S.fase = fase; S.t = 0;
    }
    S.t += C.dt;
    const DUR = [0, 0.3, 0.6, 0.3, 0.9];
    const u = limitar(avance !== null ? avance : S.t / DUR[fase || 1], 0, 1);
    const d = C.dronL, hd = Math.hypot(d.x, d.z);
    const dirDron = hd > 0.05 ? V(d.x / hd, 0, d.z / hd) : V(0, 0, 1);
    const pieLoc = a => a ? this.raiz.worldToLocal(a.clone()) : null;
    const escalaH = 1 / this.escala;
    // brazo que agarra: el derecho, hacia el dron (o hacia arriba si el dron queda lejos)
    const hombroR = V(-0.185, 1.425, 0);
    const alcance = LARGO.brazo + LARGO.antebrazo + 0.17;
    if (fase === 1) {
      // contramovimiento: baja rápido (0-60 %), estalla (60-100 %): talones arriba, brazos de atrás hacia arriba
      const baja = u < 0.6 ? suave(u / 0.6) : 1 - suave5((u - 0.6) / 0.4);
      const sube = u < 0.6 ? 0 : suave((u - 0.6) / 0.4);
      P.cadera.set(0, lerp(0.98, 0.7, baja) + 0.08 * sube, lerp(0, -0.08, baja));
      P.qCadera = qE(lerp(0, 32, baja) * D - 6 * sube * D, 0, 0);
      P.qCol = qE(lerp(0, 10, baja) * D, 0, 0);
      P.qPecho = qE(lerp(0, 8, baja) * D - 10 * sube * D, -8 * baja * D, 0);
      P.qCuello = qE(lerp(-10, -40, u) * D, 0, 0);
      const aL = pieLoc(S.anclaL), aR = pieLoc(S.anclaR);
      if (aL) { P.pieL.copy(aL); P.pieR.copy(aR); }
      P.pieL.y = P.pieR.y = ALTURA_TOBILLO + 0.1 * sube;
      P.qPieL = qE(45 * sube * D, 6 * D, 0); P.qPieR = qE(45 * sube * D, -6 * D, 0);
      P.rodL.set(0.15, 0, 1); P.rodR.set(-0.15, 0, 1);
      // brazos: atrás abajo en el fondo; luego lanzados adelante y arriba
      const atras = baja * (1 - sube);
      P.manoL.set(0.05, lerp(-0.55, 0.1, sube), lerp(-0.3 * atras, 0.35, sube)); P.manoR.set(-0.05, lerp(-0.55, 0.25, sube), lerp(-0.32 * atras, 0.3, sube));
      P.absL = P.absR = 0;
      P.codoL.set(0.3, 0, -1); P.codoR.set(-0.3, 0, -1);
    } else if (fase === 2) {
      // vuelo: la cadera queda donde la altura de la mano lo exige, con el brazo extendido al dron
      const objMano = d.clone();
      const deHombro = objMano.clone().sub(hombroR);
      if (deHombro.length() > alcance) objMano.copy(hombroR).addScaledVector(deHombro.normalize(), alcance);
      const elev = Math.atan2(objMano.y - hombroR.y, Math.hypot(objMano.x - hombroR.x, objMano.z - hombroR.z));
      const sobreCadera = (1.425 - 0.98) + alcance * Math.max(Math.sin(Math.max(elev, 50 * D)), 0.7);
      const yC = hMano * escalaH - sobreCadera;
      const apice = Math.sin(Math.PI * u);
      P.cadera.set(dirDron.x * 0.08 * u, Math.max(yC, 0.98), dirDron.z * 0.08 * u);
      // cuerpo arqueado y girado hacia el dron, piernas recogidas en el punto alto
      const giro = Math.atan2(dirDron.x, dirDron.z);
      P.qCadera = qE(-8 * D * apice, giro * 0.3, 0);
      P.qCol = qE(-6 * D, giro * 0.25, 6 * D);
      P.qPecho = qE(-6 * D, giro * 0.25, 10 * D);
      P.qCuello = qE(-24 * D, giro * 0.1, 0);
      P.qCabeza = qE(-14 * D, 0, 0);
      const recoge = Math.sin(Math.PI * limitar(u * 1.1, 0, 1));
      const yPie = P.cadera.y - (LARGO.muslo + LARGO.pierna) * lerp(0.98, 0.72, recoge);
      P.pieL.set(0.12, yPie + 0.06 * recoge, -0.05 - 0.15 * recoge); P.pieR.set(-0.1, yPie - 0.02, 0.05 - 0.22 * recoge);
      P.qPieL = qE(lerp(55, 30, recoge) * D, 6 * D, 0); P.qPieR = qE(lerp(60, 25, recoge) * D, -6 * D, 0);
      P.rodL.set(0.15, 0.2, 1); P.rodR.set(-0.15, 0.2, 1);
      // la mano derecha va al dron (con la cadera ya ubicada, objetivo absoluto); la izquierda arriba para equilibrio
      P.manoRa.copy(objMano); P.absR = 1;
      P.codoR.set(-0.6, -0.2, -0.6);
      P.manoL.set(0.12, 0.35 - 0.3 * u, 0.25); P.absL = 0;
      P.codoL.set(0.8, -0.3, -0.4);
      P.qManoR = qE(-20 * D, 0, 0);
    } else if (fase === 3) {
      // aterrizaje: pies anclados, rodillas absorben, brazos adelante para el equilibrio
      const amort = Math.sin(Math.PI * Math.min(u * 1.2, 1));
      P.cadera.set(0, lerp(0.86, 0.68, amort), -0.04 * amort);
      P.qCadera = qE(lerp(5, 30, amort) * D, 0, 0);
      P.qCol = qE(10 * amort * D, 0, 0);
      P.qPecho = qE(5 * amort * D, 0, 0);
      P.qCuello = qE(-35 * D, 0, 0);
      const aL = pieLoc(S.anclaL), aR = pieLoc(S.anclaR);
      if (aL) { P.pieL.copy(aL).setY(ALTURA_TOBILLO); P.pieR.copy(aR).setY(ALTURA_TOBILLO); }
      P.qPieL = qE(0, 8 * D, 0); P.qPieR = qE(0, -8 * D, 0);
      P.rodL.set(0.25, 0, 1); P.rodR.set(-0.25, 0, 1);
      P.manoL.set(0.15, -0.25, 0.35); P.manoR.set(-0.15, -0.2, 0.32); P.absL = P.absR = 0;
      P.codoL.set(1, 0, -0.5); P.codoR.set(-1, 0, -0.5);
    } else if (fase === 4) {
      // recuperación: de la postura de aterrizaje a la de la persona (base), mirando el dron
      const w = suave(u);
      const R = new Pose();
      R.cadera.set(0, 0.7, -0.04); R.qCadera = qE(28 * D, 0, 0); R.qCol = qE(8 * D, 0, 0); R.qCuello = qE(-35 * D, 0, 0);
      const aL = pieLoc(S.anclaL), aR = pieLoc(S.anclaR);
      R.pieL.copy(aL || base.pieL).setY(ALTURA_TOBILLO); R.pieR.copy(aR || base.pieR).setY(ALTURA_TOBILLO);
      R.rodL.set(0.25, 0, 1); R.rodR.set(-0.25, 0, 1);
      R.manoL.set(0.15, -0.3, 0.3); R.manoR.set(-0.15, -0.3, 0.3);
      R.codoL.set(1, 0, -0.5); R.codoR.set(-1, 0, -0.5);
      mezclar(R, base, w);
      return R;
    }
    return P;
  }

  mirar(P, C) {
    const w = this.capas.mira * (1 - 0.7 * this.pesos.gateo) * (this.asomando ? 1 - this.asomando : 1);
    if (w < 0.01 && this.capas.salto < 0.01) return;
    // hacia el dron, desde la cabeza; se reparte entre pecho, cuello y cabeza
    const cabeza = V(P.cadera.x, P.cadera.y + 0.66, P.cadera.z);
    const d = C.dronL.clone().sub(cabeza);
    const yawRel = limitar(Math.atan2(d.x, d.z), -100 * D, 100 * D);
    const pitch = limitar(Math.atan2(d.y, Math.hypot(d.x, d.z)), -30 * D, 70 * D);
    const ww = Math.max(w * (1 - 0.6 * limitar(C.v / 2, 0, 1)), this.capas.salto * 0.3);      // corriendo, solo mira de reojo
    P.qPecho.multiply(qE(-pitch * 0.1 * ww, yawRel * 0.25 * ww, 0));
    P.qCuello.multiply(qE(-pitch * 0.38 * ww, yawRel * 0.35 * ww, 0));
    P.qCabeza.multiply(qE(-pitch * 0.35 * ww, yawRel * 0.4 * ww, 0));
  }

  // ------------------------------------------------------------------------------------------- aplicar al esqueleto
  aplicar(P) {
    const H = this.H;
    H.cadera.position.copy(P.cadera);
    H.cadera.quaternion.copy(P.qCadera);
    H.columna.quaternion.copy(P.qCol);
    H.pecho.quaternion.copy(P.qPecho);
    H.cuello.quaternion.copy(P.qCuello);
    H.cabeza.quaternion.copy(P.qCabeza);
    // cinemática directa del tronco (en el sistema de la persona)
    const qC = P.qCadera.clone(), qCol = qC.clone().multiply(P.qCol), qPe = qCol.clone().multiply(P.qPecho);
    const pCol = P.cadera.clone().add(H.columna.position.clone().applyQuaternion(qC));
    const pPe = pCol.clone().add(H.pecho.position.clone().applyQuaternion(qCol));
    // piernas
    ["L", "R"].forEach(s => {
      const muslo = H["muslo_" + s], pierna = H["pierna_" + s], pie = H["pie_" + s];
      const raiz = P.cadera.clone().add(muslo.position.clone().applyQuaternion(qC));
      const obj = P["pie" + s].clone();
      obj.y = Math.max(obj.y, 0.06);
      const polo = P["rod" + s].clone().normalize();
      const r = ik2(raiz, obj, LARGO.muslo, LARGO.pierna, polo, REST_DIR["muslo_" + s], REST_DIR["pierna_" + s], N_REST_PIERNA);
      muslo.quaternion.copy(qC.clone().invert().multiply(r.qU));
      pierna.quaternion.copy(r.qU.clone().invert().multiply(r.qL));
      pie.quaternion.copy(r.qL.clone().invert().multiply(P["qPie" + s]));
    });
    // brazos: el hombro sale de la clavícula (que sube un poco con el brazo levantado)
    ["L", "R"].forEach(s => {
      const sx = s === "L" ? 1 : -1, clav = H["clav_" + s], brazo = H["brazo_" + s], ante = H["antebrazo_" + s], mano = H["mano_" + s];
      const pClav = pPe.clone().add(clav.position.clone().applyQuaternion(qPe));
      const rel = pClav.clone().add(brazo.position.clone().applyQuaternion(qPe)).add(P["mano" + s].clone().applyQuaternion(qPe));
      const obj = rel.lerp(P["mano" + s + "a"], limitar(P["abs" + s], 0, 1));
      // levantar el brazo sube la clavícula
      const arriba = limitar((obj.y - pClav.y) / 0.5, 0, 1);
      const qClav = qE(0, 0, sx * 14 * arriba * D);
      clav.quaternion.copy(qClav);
      const qClW = qPe.clone().multiply(qClav);
      const raiz = pClav.clone().add(brazo.position.clone().applyQuaternion(qClW));
      const polo = P["codo" + s].clone().applyQuaternion(qPe).normalize();
      const r = ik2(raiz, obj, LARGO.brazo, LARGO.antebrazo, polo, REST_DIR["brazo_" + s], REST_DIR["antebrazo_" + s], N_REST_BRAZO);
      brazo.quaternion.copy(qClW.clone().invert().multiply(r.qU));
      ante.quaternion.copy(r.qU.clone().invert().multiply(r.qL));
      mano.quaternion.copy(P["qMano" + s]);
    });
  }
}
