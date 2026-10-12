// Vista previa de escenarios futuros (fase B4 del plan V16): hangar con columnas, vigas, cajas, estanterías y una
// oficina; y campo con árboles, arbustos y piedras. NO están entrenados: solo se muestran para planear la V17+.
// Cada escenario trae una escena de ejemplo (dron y personas con recorridos fijos) que pasa por las mismas cámaras,
// cajas de YOLO e interfaz que una repetición; la cámara externa queda libre para recorrerlo.
import * as THREE from "three";
import { Mundo, juegoTexturas } from "./escena.js";
import { mundo, azar, uvMetros, lerp, angNorm, CAM, vfovDe } from "./util.js";

const gris = c => new THREE.MeshStandardMaterial({ color: c, roughness: 0.6, metalness: 0.5 });

export class Previa {
  constructor(M) {
    this.M = M;
    this.grupos = { hangar: this.crearHangar(), campo: this.crearCampo() };
    Object.values(this.grupos).forEach(g => { g.visible = false; M.escena.add(g); });
    this.activo = null;
    this.ray = new THREE.Raycaster();
  }

  activar(nombre) {
    Object.entries(this.grupos).forEach(([k, g]) => { g.visible = k === nombre; });
    this.M.decorado.visible = nombre !== "hangar";
    this.activo = nombre;
    this.M.renderer.shadowMap.needsUpdate = true;
    return new PartidaPrevia(nombre, this);
  }
  desactivar() {
    Object.values(this.grupos).forEach(g => { g.visible = false; });
    this.M.decorado.visible = true;
    this.activo = null;
  }

  // ------------------------------------------------------------------------------------------------ hangar
  crearHangar() {
    const g = new THREE.Group(), r = azar(77);
    const A = 40, B = 30, H = 9.5;               // largo (x), ancho (y), alto
    const add = (m, sombra = true) => { m.castShadow = sombra; m.receiveShadow = true; g.add(m); return m; };
    // piso de concreto pulido
    const tp = juegoTexturas(this.M.renderer, "concreto_piso", 1);
    const piso = new THREE.Mesh(uvMetros(new THREE.BoxGeometry(A + 30, 0.1, B + 30), 3), new THREE.MeshStandardMaterial({ ...tp, roughness: 0.75 }));
    piso.position.y = -0.05;
    add(piso, false);
    // pintura de seguridad en el piso (franjas amarillas de los pasillos)
    const franja = new THREE.MeshStandardMaterial({ color: 0xd8b02a, roughness: 0.6 });
    [[-6.5, 0], [6.5, 0]].forEach(([y]) => { const m = new THREE.Mesh(new THREE.BoxGeometry(A - 4, 0.012, 0.12), franja); m.position.copy(mundo(0, y, 0.006)); add(m, false); });
    // cerramiento de lámina (con portón abierto en el lado sur) y techo con claraboyas
    const lam = new THREE.MeshStandardMaterial({ color: 0x8c949b, roughness: 0.45, metalness: 0.6, side: THREE.DoubleSide });
    const pared = (x1, y1, x2, y2, h, z0 = 0) => {
      const L = Math.hypot(x2 - x1, y2 - y1), m = new THREE.Mesh(new THREE.BoxGeometry(L, h, 0.15), lam);
      m.position.copy(mundo((x1 + x2) / 2, (y1 + y2) / 2, z0 + h / 2)); m.rotation.y = Math.atan2(y2 - y1, x2 - x1);
      return add(m);
    };
    pared(-A / 2, B / 2, A / 2, B / 2, H); pared(-A / 2, -B / 2, -A / 2, B / 2, H); pared(A / 2, -B / 2, A / 2, B / 2, H);
    pared(-A / 2, -B / 2, -8, -B / 2, H); pared(8, -B / 2, A / 2, -B / 2, H); pared(-8, -B / 2, 8, -B / 2, H - 6, 6);    // portón de 16 m
    // estructura: columnas de perfil I cada 8 m (bordes y dos filas interiores) y vigas de cubierta
    const acero = gris(0x3f6f8f), perfil = (h) => {
      const p = new THREE.Group();
      const ala = new THREE.BoxGeometry(0.3, h, 0.02), alma = new THREE.BoxGeometry(0.02, h, 0.3);
      [-0.15, 0.15].forEach(z => { const m = new THREE.Mesh(ala, acero); m.position.set(0, h / 2, z); m.castShadow = m.receiveShadow = true; p.add(m); });
      const m = new THREE.Mesh(alma, acero); m.position.set(0, h / 2, 0); m.castShadow = true; p.add(m);
      return p;
    };
    for (let x = -A / 2 + 4; x <= A / 2 - 4; x += 8) {
      [-B / 2 + 0.4, -5, 5, B / 2 - 0.4].forEach(y => { const c = perfil(H); c.position.copy(mundo(x, y)); g.add(c); });
      // viga reticulada de lado a lado
      const viga = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.5, B), acero);
      viga.position.copy(mundo(x, 0, H - 0.4)); add(viga);
      for (let k = -B / 2; k < B / 2; k += 1.5) {
        const d = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.2, 0.06), acero);
        d.position.copy(mundo(x, k + 0.75, H - 1.2)); d.rotation.x = 0.9 * (Math.floor(k / 1.5) % 2 ? 1 : -1); add(d, false);
      }
      const cordon = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.15, B), acero); cordon.position.copy(mundo(x, 0, H - 1.9)); add(cordon, false);
    }
    // techo: láminas con franjas de claraboya (entra el sol)
    for (let y = -B / 2; y < B / 2; y += 5) {
      const m = new THREE.Mesh(new THREE.BoxGeometry(A, 0.08, 3.6), lam);
      m.position.copy(mundo(0, y + 1.8, H)); add(m);
    }
    // estanterías industriales (marcos naranja, travesaños azules) con cajas y estibas
    const naranja = gris(0xd96a1c), azul = gris(0x1f4f9a);
    const carton = [0xa47b4f, 0x8f6a43, 0xb88d5d, 0x7d5f3e].map(c => new THREE.MeshStandardMaterial({ color: c, roughness: 0.9 }));
    const madera = new THREE.MeshStandardMaterial({ color: 0x9a7a52, roughness: 0.85 });
    const estante = (x0, y0, largo) => {
      for (let k = 0; k <= largo; k += 2.7) [0, 1.1].forEach(dy => {
        const m = new THREE.Mesh(new THREE.BoxGeometry(0.09, 4.5, 0.09), naranja); m.position.copy(mundo(x0 + k, y0 + dy, 2.25)); add(m);
      });
      [0.15, 1.6, 3.05, 4.4].forEach(z => [0, 1.1].forEach(dy => {
        const m = new THREE.Mesh(new THREE.BoxGeometry(largo, 0.12, 0.06), azul); m.position.copy(mundo(x0 + largo / 2, y0 + dy, z)); add(m);
      }));
      [0.2, 1.65, 3.1].forEach(z => { for (let k = 0.2; k < largo - 0.8; k += 0.9 + r() * 0.3) {
        if (r() < 0.2) continue;
        const w = 0.6 + r() * 0.35, h = 0.4 + r() * 0.8, m = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.9), carton[Math.floor(r() * 4)]);
        m.position.copy(mundo(x0 + k + w / 2, y0 + 0.55, z + 0.08 + h / 2)); add(m);
      } });
    };
    estante(-14, 9, 16.2); estante(-14, -10.1, 16.2); estante(6, 9, 10.8);
    // cajas sueltas y estibas en el centro (para esconderse)
    const caja = (x, y, w, d, h, rot = 0, mat = carton[0]) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); m.position.copy(mundo(x, y, h / 2)); m.rotation.y = rot; return add(m); };
    [[4, -2, 1.2, 1.2, 1.2], [5.3, -2.2, 1.0, 1.0, 1.0], [4.6, -0.9, 1.1, 1.1, 0.9], [4.5, -2.0, 1.0, 1.0, 1.0, 0, 2.2], [-3, 3, 2.4, 1.2, 1.4],
     [-8, -2, 1.2, 1.2, 1.2], [-8.2, -0.7, 1.2, 1.2, 1.2], [12, 3, 1.0, 1.0, 1.6], [13.2, 3.2, 1.0, 1.0, 1.0], [-15, 0, 2.0, 1.0, 0.9]].forEach(([x, y, w, d, h, rot, z0]) => {
      const m = caja(x, y, w, d, h, (rot || 0) + (r() - 0.5) * 0.3, carton[Math.floor(r() * 4)]);
      if (z0) m.position.y = z0 + h / 2 - 1.0;
    });
    // estibas de madera
    [[0, -9], [1.4, -9], [-1.4, -9]].forEach(([x, y]) => caja(x, y, 1.2, 1.0, 0.14, 0, madera));
    // oficina (habitación) en la esquina noreste, con puerta y ventana
    const muroOf = new THREE.MeshStandardMaterial({ color: 0xd9d5cc, roughness: 0.9 });
    const muro = (x1, y1, x2, y2, h = 3, z0 = 0) => {
      const L = Math.hypot(x2 - x1, y2 - y1), m = new THREE.Mesh(new THREE.BoxGeometry(L, h, 0.12), muroOf);
      m.position.copy(mundo((x1 + x2) / 2, (y1 + y2) / 2, z0 + h / 2)); m.rotation.y = Math.atan2(y2 - y1, x2 - x1); return add(m);
    };
    muro(12, 5, 12, 14.6); muro(12, 5, 15, 5); muro(16.2, 5, 19.6, 5); muro(15, 5, 16.2, 5, 0.9, 2.1);   // puerta de 1.2 m
    muro(12, 8, 12, 11, 1.0, 0); muro(12, 8, 12, 11, 0.6, 2.4);
    caja(17.5, 12.5, 1.6, 0.8, 0.75, 0, madera); caja(13.5, 13.5, 0.5, 0.5, 0.45, 0, gris(0x333333));
    // luces del techo (cálidas) e interior más oscuro
    for (let x = -12; x <= 12; x += 12) for (let y = -6; y <= 6; y += 12) {
      const l = new THREE.PointLight(0xffe6c4, 25, 22, 2); l.position.copy(mundo(x, y, H - 2.2)); g.add(l);
      const lamp = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.45, 0.25, 16), new THREE.MeshStandardMaterial({ color: 0x222222, emissive: 0xfff0d8, emissiveIntensity: 1.5 }));
      lamp.position.copy(mundo(x, y, H - 2.0)); g.add(lamp);
    }
    // obstáculos para el mapa pequeño (segmentos)
    g.userData.segmentos = [[-14, 9, 2.2, 9], [-14, -10.1, 2.2, -10.1], [6, 9, 16.8, 9], [12, 5, 12, 14.6], [12, 5, 19.6, 5],
                            [-A / 2, -B / 2, -A / 2, B / 2], [A / 2, -B / 2, A / 2, B / 2], [-A / 2, B / 2, A / 2, B / 2], [-A / 2, -B / 2, -8, -B / 2], [8, -B / 2, A / 2, -B / 2]];
    g.userData.cajas = [[4.6, -1.6], [-3, 3], [-8.1, -1.3], [12.5, 3.1]];
    return g;
  }

  // ------------------------------------------------------------------------------------------------ campo con árboles
  crearCampo() {
    const g = new THREE.Group(), r = azar(9);
    const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 });
    const variantes = [0, 1, 2, 1].map(t => Mundo.geometriaArbol(r, t));
    const pos = [];
    while (pos.length < 46) {
      const x = (r() - 0.5) * 46, y = (r() - 0.5) * 46;
      if (Math.hypot(x, y) < 4 || pos.some(([a, b]) => Math.hypot(a - x, b - y) < 3.2)) continue;      // claro en el centro
      pos.push([x, y]);
    }
    variantes.forEach((geo, v) => {
      const mios = pos.filter((_, k) => k % variantes.length === v);
      const im = new THREE.InstancedMesh(geo, mat, mios.length);
      const m4 = new THREE.Matrix4(), q = new THREE.Quaternion();
      mios.forEach(([x, y], k) => {
        const s = 0.7 + r() * 0.5;
        q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), r() * 6.28);
        m4.compose(mundo(x, y), q, new THREE.Vector3(s, s, s));
        im.setMatrixAt(k, m4);
      });
      im.castShadow = im.receiveShadow = true;
      g.add(im);
    });
    // arbustos y piedras
    const arb = new THREE.MeshStandardMaterial({ color: 0x2c4a1e, roughness: 0.95 }), roca = new THREE.MeshStandardMaterial({ color: 0x7a776f, roughness: 0.9 });
    for (let k = 0; k < 40; k++) {
      const x = (r() - 0.5) * 44, y = (r() - 0.5) * 44;
      const esArb = r() < 0.7, s = esArb ? 0.5 + r() * 0.6 : 0.25 + r() * 0.4;
      const geo = esArb ? new THREE.IcosahedronGeometry(s, 2) : new THREE.DodecahedronGeometry(s, 0);
      const m = new THREE.Mesh(geo, esArb ? arb : roca);
      m.position.copy(mundo(x, y, esArb ? s * 0.55 : s * 0.4)); m.scale.set(1.3, esArb ? 0.75 : 0.6, 1.1); m.rotation.y = r() * 6;
      m.castShadow = m.receiveShadow = true;
      g.add(m);
    }
    // tronco caído
    const tronco = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.32, 5, 10), new THREE.MeshStandardMaterial({ color: 0x4a3828, roughness: 0.95 }));
    tronco.rotation.z = Math.PI / 2; tronco.rotation.y = 0.4; tronco.position.copy(mundo(-5, 6, 0.3)); tronco.castShadow = tronco.receiveShadow = true;
    g.add(tronco);
    g.userData.segmentos = [];
    g.userData.arboles = pos;
    return g;
  }

  // ¿se ve el punto desde la cámara? (rayo contra el escenario de la vista previa)
  visible(desde, hasta) {
    const g = this.grupos[this.activo];
    if (!g) return true;
    const d = hasta.clone().sub(desde), L = d.length();
    this.ray.set(desde, d.normalize());
    this.ray.far = L - 0.2;
    return this.ray.intersectObject(g, true).length === 0;
  }
}

// ------------------------------------------------------------------------------------------------ escena de ejemplo
// Recorridos fijos (t, x, y) que se repiten; la "partida" tiene la misma forma que datos.js -> Partida.muestra()
function recorrido(pts, t) {
  const T = pts[pts.length - 1][0], u = ((t % T) + T) % T;
  for (let k = 0; k < pts.length - 1; k++) {
    const a = pts[k], b = pts[k + 1];
    if (u >= a[0] && u <= b[0]) {
      const f = (u - a[0]) / Math.max(b[0] - a[0], 1e-6);
      return { x: lerp(a[1], b[1], f), y: lerp(a[2], b[2], f), vx: (b[1] - a[1]) / Math.max(b[0] - a[0], 1e-6), vy: (b[2] - a[2]) / Math.max(b[0] - a[0], 1e-6), k };
    }
  }
  return { x: pts[0][1], y: pts[0][2], vx: 0, vy: 0, k: 0 };
}
const ESCENAS = {
  hangar: {
    titulo: "Vista previa · hangar (no entrenado)",
    dron: [[0, -2, -12], [10, 4, -10.5], [20, 3, -11.5], [30, -4, -11], [40, -10, -12], [50, -2, -12]],     // por el pasillo, lejos de las columnas
    gente: [
      { id: 3, rol: "ladron", est: 1.74, pts: [[0, 6.6, -1.5], [60, 6.6, -1.5]], pos: 1, mira: 0.2 },          // agachado detrás de las cajas
      { id: 8, rol: "peaton", est: 1.68, pts: [[0, -12, 7.6], [12, 4, 7.6], [14, 4, 7.6], [26, -12, 7.6], [28, -12, 7.6]], pos: 0 },   // operario entre estanterías
      { id: 11, rol: "peaton", est: 1.77, pts: [[0, -8, -5.45], [60, -8, -5.45]], pos: 2, mira: -Math.PI / 2 },   // recostado en una columna
      { id: 14, rol: "peaton", est: 1.62, pts: [[0, 2, -8.6], [60, 2, -8.6]], pos: 0, civ: 4 },                 // graba al dron
    ],
  },
  campo: {
    titulo: "Vista previa · campo con árboles (no entrenado)",
    dron: [[0, -18, -18], [15, -8, -6], [30, 0, 2], [45, 10, 8], [60, -6, 14], [75, -18, -18]],
    gente: [
      { id: 3, rol: "ladron", est: 1.72, pts: [[0, -6, 4], [20, 2, 6.5], [22, 2, 6.5], [42, -6, 4]], pos: 3 },     // gatea entre los arbustos
      { id: 5, rol: "peaton", est: 1.7, pts: [[0, 12, -14], [30, -10, 12], [32, -10, 12], [62, 12, -14]], pos: 0 },
      { id: 9, rol: "peaton", est: 1.8, pts: [[0, 3, -3], [75, 3, -3]], pos: 0, civ: 1 },                          // mira el dron
    ],
  },
};

export class PartidaPrevia {
  constructor(nombre, previa) {
    const E = ESCENAS[nombre];
    this.E = E;
    this.previa = previa;
    this.dt = 0.1;
    this.total = E.dron[E.dron.length - 1][0];
    this.C = new Array(Math.round(this.total / this.dt) + 1).fill({});
    this.paneles = (previa.grupos[nombre].userData.segmentos || []).map(s => [...s, 3]);
    this.eventos = [];
    this.clics = [];
    this.v16 = true;
    this.previa_ = true;
    this.d = { titulo: E.titulo, version: "vista previa", resultado: null };
    this.ruta = "previa:" + nombre;
  }
  muestra(t) {
    // el dron sigue su recorrido apuntando la cámara hacia el sospechoso
    const E = this.E, d = recorrido(E.dron, t), ql = recorrido(E.gente[0].pts, t);
    const psiObj = Math.atan2(ql.y - d.y, ql.x - d.x);
    this.psi = this.psi === undefined ? psiObj : this.psi + angNorm(psiObj - this.psi) * 0.05;
    const z = 3.3, cam = mundo(d.x, d.y, z - 0.12);
    const personas = E.gente.map(g => {
      const q = recorrido(g.pts, t);
      const p = { clave: "id" + g.id, rol: g.rol, id: g.id, est: g.est, x: q.x, y: q.y, vx: q.vx, vy: q.vy, pos: g.pos, pt: 1,
                  mira: g.mira !== undefined ? g.mira : (Math.hypot(q.vx, q.vy) > 0.2 ? undefined : Math.atan2(d.y - q.y, d.x - q.x)),
                  civ: g.civ ?? (g.rol === "peaton" ? 0 : null), salto: [0, 2.27, 0], fv: 1 };
      // visible: dentro del campo de la cámara y sin nada en medio (pecho y cabeza)
      const alto = g.est * [1, 0.67, 1, 0.35][g.pos];
      const dx = q.x - d.x, dy = q.y - d.y, h = Math.hypot(dx, dy);
      const az = Math.abs(angNorm(Math.atan2(dy, dx) - this.psi)) * 180 / Math.PI, el = Math.atan2(alto * 0.6 - z, h) * 180 / Math.PI;
      const enCuadro = az < CAM.hfov / 2 && Math.abs(el - this.gmb(h)) < vfovDe(CAM.hfov, 4 / 3) / 2 && h < 30;
      p.vis = enCuadro && (this.previa.visible(cam, mundo(q.x, q.y, alto * 0.9)) || this.previa.visible(cam, mundo(q.x, q.y, alto * 0.5)));
      return p;
    });
    const lad = personas[0];
    return {
      k: Math.floor(t / this.dt), f: 0, t, fase: 2, modo: lad.vis ? 2 : 3, trk: lad.vis ? 1 : 3, vis: lad.vis, est: 0,
      x: d.x, y: d.y, z, psi: this.psi, cp: -Math.hypot(d.vx, d.vy) * 1.5, cr: 0, gmb: this.gmb(Math.hypot(lad.x - d.x, lad.y - d.y)),
      vx: d.vx, vy: d.vy, altObj: z, personas, tf: t * 0.6, tsv: 0, eb: "PERSECUCION", ux: lad.x, uy: lad.y, conf: 0.9, bat: 100 - t / 9,
    };
  }
  gmb(h) { return Math.max(-45, Math.min(15, Math.atan2(1.0 - 3.18, Math.max(h, 0.5)) * 180 / Math.PI)); }
}
