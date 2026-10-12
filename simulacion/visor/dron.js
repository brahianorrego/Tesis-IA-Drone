// Dron del proyecto (marco de 450 mm, Pixhawk, Jetson, GPS, gimbal de pitch con la cámara y el TF-Luna; TF03 fijo al
// chasis mirando al frente, como recomienda el plan V16, sección 6). Lleva las dos cámaras reales:
//  - principal: en el gimbal, HFOV 38.9°, 640 x 480; el gimbal compensa el cabeceo del chasis y nunca baja de -45°
//  - al piso: IMX219 fija al chasis, recta hacia abajo (CAM_PISO.pitch = -90°)
import * as THREE from "three";
import { mundo, limitar, lerp, GIMBAL_MIN, GIMBAL_MAX, CAM, CAM_PISO, vfovDe } from "./util.js";

const negro = new THREE.MeshStandardMaterial({ color: 0x17191c, roughness: 0.55, metalness: 0.2 });
const carbono = new THREE.MeshStandardMaterial({ color: 0x0f1012, roughness: 0.35, metalness: 0.4 });
const gris = new THREE.MeshStandardMaterial({ color: 0x6b7178, roughness: 0.4, metalness: 0.7 });
const rojo = new THREE.MeshStandardMaterial({ color: 0xb3241e, roughness: 0.5 });
const blanco = new THREE.MeshStandardMaterial({ color: 0xd9dcdf, roughness: 0.6 });
const verdePCB = new THREE.MeshStandardMaterial({ color: 0x1f5135, roughness: 0.6 });

function caja(w, h, d, mat, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  m.castShadow = true;
  return m;
}
function pon(m, x, y, z) { m.position.set(x, y, z); return m; }
function cil(r1, r2, h, mat, seg = 16) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r1, r2, h, seg), mat);
  m.castShadow = true;
  return m;
}

export class Dron {
  constructor() {
    this.raiz = new THREE.Group();                // posición y rumbo (psi)
    this.chasis = new THREE.Group();              // cabeceo y alabeo (cp, cr)
    this.raiz.add(this.chasis);
    const c = this.chasis;
    // placas centrales, brazos y motores
    c.add(caja(0.17, 0.004, 0.17, carbono, 0, 0.0, 0), caja(0.15, 0.004, 0.15, carbono, 0, 0.045, 0));
    for (let k = 0; k < 4; k++) c.add(pon(cil(0.005, 0.005, 0.045, gris, 6), [0.065, -0.065][k % 2], 0.022, [0.065, -0.065][k >> 1]));
    this.rotores = [];
    const radio = 0.225;
    [[1, 1], [1, -1], [-1, -1], [-1, 1]].forEach(([sx, sz], k) => {
      const a = new THREE.Vector3(sx, 0, sz).normalize().multiplyScalar(radio);
      const brazo = caja(radio, 0.022, 0.03, sx > 0 ? rojo : blanco);
      brazo.position.set(a.x / 2, 0.012, a.z / 2);
      brazo.rotation.y = -Math.atan2(a.z, a.x);
      c.add(brazo);
      const motor = cil(0.016, 0.018, 0.03, gris);
      motor.position.set(a.x, 0.035, a.z);
      c.add(motor);
      const rotor = new THREE.Group();
      rotor.position.set(a.x, 0.055, a.z);
      const pala = caja(0.254, 0.003, 0.022, negro);
      pala.rotation.x = 0.12;
      rotor.add(pala);
      const disco = new THREE.Mesh(new THREE.CircleGeometry(0.127, 32), new THREE.MeshBasicMaterial({ color: 0x222222, transparent: true, opacity: 0.18, depthWrite: false, side: THREE.DoubleSide }));
      disco.rotation.x = -Math.PI / 2;
      rotor.add(disco);
      c.add(rotor);
      this.rotores.push({ rotor, sentido: k % 2 ? 1 : -1 });
      // patas del tren de aterrizaje bajo los brazos traseros y delanteros
      const pata = cil(0.006, 0.006, 0.17, negro, 6);
      pata.position.set(a.x * 0.45, -0.085, a.z * 0.45);
      c.add(pata);
    });
    // Pixhawk, Jetson (disipador y ventilador), GPS en mástil, batería debajo
    c.add(caja(0.08, 0.016, 0.05, negro, -0.01, 0.055, 0));
    c.add(caja(0.10, 0.03, 0.08, verdePCB, -0.005, 0.078, 0));
    c.add(caja(0.09, 0.012, 0.07, gris, -0.005, 0.098, 0));
    c.add(pon(cil(0.006, 0.006, 0.12, gris, 6), -0.06, 0.11, 0));
    c.add(pon(cil(0.035, 0.035, 0.014, blanco, 20), -0.06, 0.175, 0));
    c.add(caja(0.15, 0.035, 0.065, new THREE.MeshStandardMaterial({ color: 0x2c3e66, roughness: 0.5 }), -0.01, -0.025, 0));
    // TF03 (LiDAR de frenado) fijo al chasis, horizontal, en la nariz
    this.tf03 = caja(0.08, 0.044, 0.044, negro, 0.11, 0.0, 0);
    c.add(this.tf03);
    c.add(caja(0.004, 0.03, 0.03, new THREE.MeshStandardMaterial({ color: 0x223355, roughness: 0.1, metalness: 0.5 }), 0.152, 0.0, 0));
    // gimbal de pitch bajo la nariz: cámara principal + TF-Luna coaxial
    this.gimbal = new THREE.Group();
    this.gimbal.position.set(0.10, -0.06, 0);
    c.add(this.gimbal);
    c.add(caja(0.012, 0.05, 0.075, negro, 0.10, -0.035, 0));        // horquilla
    const cuerpoCam = caja(0.045, 0.035, 0.045, negro);
    this.gimbal.add(cuerpoCam);
    const lente = cil(0.012, 0.012, 0.012, new THREE.MeshStandardMaterial({ color: 0x0a0d12, roughness: 0.05, metalness: 0.6 }), 16);
    lente.rotation.z = Math.PI / 2; lente.position.x = 0.028;
    this.gimbal.add(lente);
    this.gimbal.add(caja(0.015, 0.021, 0.035, new THREE.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 }), 0.012, 0.03, 0));   // TF-Luna
    // cámara principal (mira a +x del dron)
    this.camara = new THREE.PerspectiveCamera(vfovDe(CAM.hfov, CAM.ancho / CAM.alto), CAM.ancho / CAM.alto, 0.05, 400);
    this.camara.rotation.y = -Math.PI / 2;
    this.camara.position.x = 0.035;
    this.gimbal.add(this.camara);
    // cámara al piso (IMX219): fija bajo el chasis; arriba en la imagen = nariz del dron
    this.camaraPiso = new THREE.PerspectiveCamera(CAM_PISO.vfov, CAM_PISO.ancho / CAM_PISO.alto, 0.05, 200);
    this.montajePiso = new THREE.Group();
    this.montajePiso.position.set(0.02, -0.048, 0);
    this.montajePiso.rotation.z = (CAM_PISO.pitch + 90) * Math.PI / 180;     // -90 = recta hacia abajo
    c.add(this.montajePiso);
    this.camaraPiso.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(
      new THREE.Vector3(0, 0, 1), new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0)));
    this.montajePiso.add(this.camaraPiso);
    c.add(caja(0.03, 0.012, 0.03, negro, 0.02, -0.044, 0));
    // luces de navegación (verde a la derecha, roja a la izquierda) y estrobo
    const luz = (col, x, z) => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.008, 8, 6), new THREE.MeshBasicMaterial({ color: col })); m.position.set(x, 0.02, z); c.add(m); return m; };
    luz(0x33ff66, 0.16, 0.16); luz(0xff3333, 0.16, -0.16);
    this.estrobo = luz(0xffffff, -0.05, 0);
    this.raiz.traverse(o => { if (o.isMesh && o.material !== negro) o.receiveShadow = false; });
    this.gimbalGrados = -10;
  }

  // estado: x, y, z, psi (rad), cp, cr (grados), gmb (grados)
  actualizar(e, dt, ahora) {
    this.raiz.position.copy(mundo(e.x, e.y, e.z));
    this.raiz.rotation.y = e.psi;
    this.chasis.rotation.z = (e.cp || 0) * Math.PI / 180;
    this.chasis.rotation.x = (e.cr || 0) * Math.PI / 180;
    // regla dura 1: el gimbal no baja de -45° pase lo que pase (comando, filtro o cabeceo del chasis)
    const g = limitar(e.gmb ?? -10, GIMBAL_MIN, GIMBAL_MAX);
    this.gimbalGrados = g;
    this.gimbal.rotation.z = g * Math.PI / 180 - this.chasis.rotation.z;
    this.rotores.forEach(r => r.rotor.rotation.y += r.sentido * dt * 31);
    this.estrobo.visible = Math.floor(ahora / 90) % 14 === 0;
  }
}
