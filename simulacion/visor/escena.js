// Mundo 3D del visor V16 (fase B1): cielo HDRI, sol con sombras, niebla, piso de pasto, muros de concreto y árboles.
// Todo lo que no existe en el mundo real (geocerca, rastros, autoría en el piso) va en la capa de AYUDAS: la ve solo la
// vista externa, nunca las cámaras del dron.
import * as THREE from "three";
import { HDRLoader } from "three/addons/loaders/HDRLoader.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { mundo, azar, uvMetros, RAIZ } from "./util.js";

export const CAPA_AYUDAS = 1;
const ARENA = 25;

export const CIELOS = {
  amanecer: { archivo: RAIZ + "recursos/cielo/spruit_sunrise_1k.hdr", azimut: 36, elev: 28, sol: 3.1, color: 0xfff1e4, niebla: 0xb9c3c9, rot: 0 },
  mediodia: { archivo: RAIZ + "recursos/cielo/quarry_01_1k.hdr", azimut: 30, elev: 52, sol: 3.6, color: 0xfff4e6, niebla: 0xc6d2dc, rot: 0 },
};

function cargarTex(cargador, ruta, srgb, rep, aniso) {
  const t = cargador.load(ruta);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(rep, rep);
  t.anisotropy = aniso;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
export function juegoTexturas(renderer, nombre, rep = 1) {
  const c = new THREE.TextureLoader(), a = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const r = `${RAIZ}recursos/texturas/${nombre}`;
  return { map: cargarTex(c, r + "_color.jpg", true, rep, a), normalMap: cargarTex(c, r + "_normal.jpg", false, rep, a),
           roughnessMap: cargarTex(c, r + "_rugosidad.jpg", false, rep, a) };
}

// ruido suave de valor (para variar el color del pasto a gran escala y que no se note la repetición)
function ruido2(x, y, s) {
  const h = (i, j) => { const v = Math.sin(i * 127.1 + j * 311.7 + s * 74.7) * 43758.5453; return v - Math.floor(v); };
  const i = Math.floor(x), j = Math.floor(y), fx = x - i, fy = y - j, u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
  return (h(i, j) * (1 - u) + h(i + 1, j) * u) * (1 - v) + (h(i, j + 1) * (1 - u) + h(i + 1, j + 1) * u) * v;
}

export class Mundo {
  constructor(renderer) {
    this.renderer = renderer;
    this.escena = new THREE.Scene();
    this.ayudas = new THREE.Group();
    this.escena.add(this.ayudas);
    this.muros = new THREE.Group();
    this.escena.add(this.muros);
    this.decorado = new THREE.Group();        // piso, árboles: se oculta en la vista previa del hangar
    this.escena.add(this.decorado);
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.foco = new THREE.Vector3();
    this.texMuro = juegoTexturas(renderer, "concreto_muro");
    this.matMuro = new THREE.MeshStandardMaterial({ ...this.texMuro, vertexColors: true, roughness: 1, normalScale: new THREE.Vector2(0.8, 0.8) });
    this.crearSol();
    this.crearPiso();
    this.crearArboles();
    this.crearAyudas();
  }

  async ponerCielo(nombre = "amanecer") {
    const c = CIELOS[nombre];
    this.cielo = c;
    const hdr = await new HDRLoader().loadAsync(c.archivo);
    hdr.mapping = THREE.EquirectangularReflectionMapping;
    const env = this.pmrem.fromEquirectangular(hdr).texture;
    if (this.escena.environment) this.escena.environment.dispose();
    if (this.escena.background) this.escena.background.dispose();
    this.escena.background = hdr;
    this.escena.environment = env;
    this.escena.environmentIntensity = 0.62;
    this.escena.backgroundIntensity = 1.0;
    this.escena.fog = new THREE.Fog(c.niebla, 70, 330);
    const az = c.azimut * Math.PI / 180, el = c.elev * Math.PI / 180;
    // en el mapa equirectangular de three.js la dirección (cos az, ·, sin az) cae donde está el sol de la foto
    this.dirSol = new THREE.Vector3(Math.cos(az) * Math.cos(el), Math.sin(el), Math.sin(az) * Math.cos(el)).normalize();
    this.sol.color.set(c.color);
    this.sol.intensity = c.sol;
    this.actualizarSol(this.foco);
  }

  crearSol() {
    const s = new THREE.DirectionalLight(0xffffff, 3);
    s.castShadow = true;
    s.shadow.mapSize.set(2048, 2048);
    const sc = s.shadow.camera;
    sc.left = sc.bottom = -16; sc.right = sc.top = 16; sc.near = 1; sc.far = 120;
    s.shadow.bias = -0.0004;
    s.shadow.normalBias = 0.03;
    s.shadow.radius = 3;
    this.escena.add(s, s.target);
    this.sol = s;
    this.dirSol = new THREE.Vector3(0.5, 0.6, 0.4).normalize();
  }
  calidadSombras(n) {
    this.sol.shadow.mapSize.set(n, n);
    if (this.sol.shadow.map) { this.sol.shadow.map.dispose(); this.sol.shadow.map = null; }
  }
  // la caja de sombras sigue a la acción (al dron y al objetivo): sombras nítidas donde se mira
  actualizarSol(foco) {
    this.foco.copy(foco);
    const p = this.foco.clone();
    p.x = Math.round(p.x * 4) / 4; p.z = Math.round(p.z * 4) / 4;   // en pasos de la textura de sombras: sin parpadeo
    this.sol.target.position.copy(p);
    this.sol.position.copy(p).addScaledVector(this.dirSol, 60);
  }

  crearPiso() {
    const tam = 640, seg = 160;
    const geo = new THREE.PlaneGeometry(tam, tam, seg, seg);
    geo.rotateX(-Math.PI / 2);
    const pos = geo.attributes.position, col = new Float32Array(pos.count * 3);
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), z = pos.getZ(i);
      const n = 0.55 * ruido2(x / 23, z / 23, 1) + 0.3 * ruido2(x / 7, z / 7, 2) + 0.15 * ruido2(x / 61, z / 61, 3);
      const seco = Math.max(0, ruido2(x / 31, z / 31, 4) - 0.55) * 1.6;
      col[3 * i] = 0.78 + 0.34 * n + 0.25 * seco; col[3 * i + 1] = 0.80 + 0.28 * n + 0.12 * seco; col[3 * i + 2] = 0.78 + 0.22 * n;
    }
    geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
    const t = juegoTexturas(this.renderer, "pasto", tam / 3.5);
    const piso = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ ...t, vertexColors: true, roughness: 1, normalScale: new THREE.Vector2(1.2, 1.2) }));
    piso.receiveShadow = true;
    piso.name = "piso";
    this.decorado.add(piso);
    this.piso = piso;
    // parches de tierra pisada (manchas suaves, sin bordes)
    const tt = juegoTexturas(this.renderer, "tierra", 2);
    const alfa = this.texturaMancha(17);
    const matT = new THREE.MeshStandardMaterial({ ...tt, alphaMap: alfa, transparent: true, depthWrite: false, roughness: 1,
                                                  polygonOffset: true, polygonOffsetFactor: -2 });
    this.matTierra = matT;
    const r = azar(5);
    for (let k = 0; k < 14; k++) {
      const s = 3 + r() * 6, m = new THREE.Mesh(new THREE.PlaneGeometry(s * (1 + r()), s), matT);
      m.rotation.set(-Math.PI / 2, 0, r() * 6.28);
      m.position.set((r() - 0.5) * 46, 0.01, (r() - 0.5) * 46);
      m.receiveShadow = true;
      this.decorado.add(m);
    }
  }
  texturaMancha(semilla) {
    const N = 256, cv = document.createElement("canvas");
    cv.width = cv.height = N;
    const g = cv.getContext("2d"), img = g.createImageData(N, N);
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      const dx = (x - N / 2) / (N / 2), dy = (y - N / 2) / (N / 2), r = Math.hypot(dx, dy);
      const n = ruido2(x / 18, y / 18, semilla) * 0.6 + ruido2(x / 6, y / 6, semilla + 1) * 0.4;
      const a = Math.max(0, Math.min(1, (1 - r) * 2.2 - 0.5 + (n - 0.5) * 1.2));
      const i = 4 * (y * N + x);
      img.data[i] = img.data[i + 1] = img.data[i + 2] = a * 255; img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
    return new THREE.CanvasTexture(cv);
  }

  // paneles de la partida: [x1, y1, x2, y2, alto]; 0.2 m de espesor (V15 · fase A)
  ponerParedes(paneles) {
    while (this.muros.children.length) { const m = this.muros.children.pop(); m.geometry.dispose(); }
    (paneles || []).forEach(([x1, y1, x2, y2, h]) => {
      const L = Math.hypot(x2 - x1, y2 - y1);
      if (L < 0.05) return;
      const geo = new THREE.BoxGeometry(L, h, 0.2, Math.max(2, Math.round(L * 2)), 12, 1);
      geo.translate(0, h / 2, 0);
      uvMetros(geo, 2.2);
      // suciedad: salpicaduras abajo y escurrimiento en la parte de arriba
      const p = geo.attributes.position, col = new Float32Array(p.count * 3);
      for (let i = 0; i < p.count; i++) {
        const y = p.getY(i), x = p.getX(i);
        let f = 1 - 0.38 * Math.exp(-y / 0.28) - 0.1 * Math.exp(-(h - y) / 0.12);
        f *= 0.92 + 0.12 * ruido2(x * 0.9, y * 0.6, 9);
        col[3 * i] = f; col[3 * i + 1] = f * 0.99; col[3 * i + 2] = f * 0.96;
      }
      geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
      const m = new THREE.Mesh(geo, this.matMuro);
      const c = mundo((x1 + x2) / 2, (y1 + y2) / 2);
      m.position.copy(c);
      m.rotation.y = Math.atan2(y2 - y1, x2 - x1);
      m.castShadow = m.receiveShadow = true;
      m.userData.muro = [x1, y1, x2, y2, h];
      this.muros.add(m);
      // tierra pisada al pie del muro
      const base = new THREE.Mesh(new THREE.PlaneGeometry(L + 2.2, 2.6), this.matTierra);
      base.rotation.set(-Math.PI / 2, 0, m.rotation.y);
      base.position.copy(c).setY(0.012);
      base.receiveShadow = true;
      this.muros.add(base);
    });
  }

  // ---------------------------------------------------------------------------------------------- árboles
  static geometriaArbol(r, tipo) {
    const partes = [];
    const alto = tipo === 2 ? 4.5 + r() * 2.5 : 6.5 + r() * 6;
    const hTronco = alto * (tipo === 2 ? 0.35 : 0.45);
    // tronco algo torcido, más ancho en la base, y dos o tres ramas gruesas hacia la copa
    const tronco = new THREE.CylinderGeometry(0.1 + r() * 0.06, 0.2 + r() * 0.1, hTronco, 8, 6);
    tronco.translate(0, hTronco / 2, 0);
    const tp = tronco.attributes.position, fx = (r() - 0.5) * 0.5, fz = (r() - 0.5) * 0.5;
    for (let i = 0; i < tp.count; i++) { const y = tp.getY(i) / hTronco; tp.setX(i, tp.getX(i) + fx * y * y); tp.setZ(i, tp.getZ(i) + fz * y * y); }
    tronco.computeVertexNormals();
    pintar(tronco, [0.07, 0.05, 0.035], 0.15, r);
    partes.push(tronco);
    for (let k = 0; k < 3; k++) {
      const largo = alto * 0.3, rama = new THREE.CylinderGeometry(0.04, 0.08, largo, 6, 1);
      rama.translate(0, largo / 2, 0);
      rama.rotateZ(0.5 + r() * 0.4); rama.rotateY(k * 2.1 + r());
      rama.translate(fx, hTronco * 0.9, fz);
      pintar(rama, [0.07, 0.05, 0.035], 0.15, r);
      partes.push(rama);
    }
    // copa: muchas masas de hojas con normales redondeadas (sombreado suave, sin facetas) y más oscuras por dentro
    const nCopa = tipo === 2 ? 7 : 10 + Math.floor(r() * 6);
    const ancho = tipo === 2 ? 1.6 : 2.4 + r() * 1.2;
    const verdes = [[0.10, 0.17, 0.06], [0.13, 0.21, 0.07], [0.09, 0.15, 0.06], [0.16, 0.22, 0.09]];
    const yC = hTronco + (alto - hTronco) * 0.45;
    for (let k = 0; k < nCopa; k++) {
      const rad = ancho * (0.38 + r() * 0.3);
      const g = new THREE.IcosahedronGeometry(rad, 3);
      const a = r() * 6.28, rr = ancho * Math.sqrt(r()) * 0.75, dy = (r() - 0.35) * (alto - hTronco) * 0.7;
      const cx = Math.cos(a) * rr + fx, cy = yC + dy, cz = Math.sin(a) * rr + fz;
      const p = g.attributes.position, nor = new Float32Array(p.count * 3), col = new Float32Array(p.count * 3);
      const base = verdes[Math.floor(r() * verdes.length)];
      for (let i = 0; i < p.count; i++) {
        const v = new THREE.Vector3().fromBufferAttribute(p, i), n = v.clone().normalize();
        const d = 1 + 0.16 * Math.sin(n.x * 9 + k) * Math.sin(n.y * 8 + 1) * Math.cos(n.z * 10 + k * 2);
        p.setXYZ(i, v.x * d + cx, v.y * d * 0.85 + cy, v.z * d + cz);
        // normal "de nube": desde el centro de toda la copa (luz suave como en un árbol real)
        const m = new THREE.Vector3(v.x * d + cx - fx, (v.y * d * 0.85 + cy - yC) * 1.2, v.z * d + cz - fz).normalize().lerp(n, 0.35).normalize();
        nor[3 * i] = m.x; nor[3 * i + 1] = m.y; nor[3 * i + 2] = m.z;
        const sombra = 0.55 + 0.45 * Math.max(0, Math.min(1, (m.y + 1) / 1.6)), ruido = 0.85 + 0.3 * ((Math.sin(i * 12.9898) * 43758.5) % 1 + 1) % 1;
        col[3 * i] = base[0] * sombra * ruido; col[3 * i + 1] = base[1] * sombra * ruido; col[3 * i + 2] = base[2] * sombra * ruido;
      }
      g.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
      g.setAttribute("color", new THREE.BufferAttribute(col, 3));
      g.deleteAttribute("uv");
      partes.push(g);
    }
    return mergeGeometries(partes.map(p => p.index ? p.toNonIndexed() : p));
  }
  crearArboles() {
    const r = azar(42), mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 });
    const variantes = [0, 1, 1, 2].map(t => Mundo.geometriaArbol(r, t));
    const pos = [];
    for (let k = 0; k < 150; k++) {         // franja de árboles fuera de la arena (más allá de 34 m)
      const a = r() * 6.28, d = 34 + Math.pow(r(), 1.6) * 140;
      pos.push([Math.cos(a) * d, Math.sin(a) * d]);
    }
    variantes.forEach((g, v) => {
      const mios = pos.filter((_, k) => k % variantes.length === v);
      const im = new THREE.InstancedMesh(g, mat, mios.length);
      const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Vector3();
      mios.forEach(([x, z], k) => {
        const s = 0.8 + r() * 0.5;
        q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), r() * 6.28);
        m4.compose(new THREE.Vector3(x, 0, z), q, e.set(s, s * (0.85 + r() * 0.3), s));
        im.setMatrixAt(k, m4);
      });
      im.castShadow = true; im.receiveShadow = true;
      this.decorado.add(im);
    });
  }

  // ---------------------------------------------------------------------------------------------- ayudas (solo vista externa)
  crearAyudas() {
    const L = ARENA, pts = [[-L, -L], [L, -L], [L, L], [-L, L], [-L, -L]].map(([x, y]) => mundo(x, y, 0.03));
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const geoc = new THREE.Line(geo, new THREE.LineDashedMaterial({ color: 0xffb347, dashSize: 1.2, gapSize: 0.8, transparent: true, opacity: 0.75 }));
    geoc.computeLineDistances();
    this.ayudas.add(geoc);
    // autoría: grabada en el piso en la franja sur (como en el visor V15), solo en la vista externa
    const cv = document.createElement("canvas");
    cv.width = 2048; cv.height = 200;
    const g = cv.getContext("2d");
    g.font = "600 120px Segoe UI, Roboto, sans-serif";
    g.textAlign = "center"; g.textBaseline = "middle";
    g.fillStyle = "rgba(255,255,255,0.9)";
    g.fillText("BRAHIAN ORREGO", 1024, 100);
    const t = new THREE.CanvasTexture(cv);
    t.colorSpace = THREE.SRGBColorSpace;
    const placa = new THREE.Mesh(new THREE.PlaneGeometry(16, 1.56), new THREE.MeshBasicMaterial({ map: t, transparent: true, opacity: 0.45, depthWrite: false }));
    placa.rotation.x = -Math.PI / 2;
    placa.position.copy(mundo(0, -L - 2.2, 0.02));
    this.ayudas.add(placa);
    this.ayudas.traverse(o => o.layers.set(CAPA_AYUDAS));
  }
}

function pintar(geo, rgb, varia = 0.08, r = Math.random) {
  const n = geo.attributes.position.count, c = new Float32Array(n * 3);
  const f = 1 + (r() - 0.5) * varia;
  for (let i = 0; i < n; i++) {
    const g = f * (1 + (Math.random() - 0.5) * varia * 0.6);
    c[3 * i] = rgb[0] * g; c[3 * i + 1] = rgb[1] * g; c[3 * i + 2] = rgb[2] * g;
  }
  geo.setAttribute("color", new THREE.BufferAttribute(c, 3));
  if (geo.attributes.uv) geo.deleteAttribute("uv");
}
