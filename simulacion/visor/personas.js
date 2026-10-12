// Personas de la escena: crea, actualiza y retira una figura por cada persona de la repetición.
import * as THREE from "three";
import { mundo } from "./util.js";

class FiguraSimple {          // provisional (fase B1): se reemplaza por el humano con esqueleto en la fase B2
  constructor(p) {
    this.raiz = new THREE.Group();
    const m = new THREE.Mesh(new THREE.CapsuleGeometry(0.2, p.est - 0.4, 4, 12),
      new THREE.MeshStandardMaterial({ color: p.rol === "ladron" ? 0x3b3f46 : 0x6d7f95, roughness: 0.8 }));
    m.position.y = p.est / 2;
    m.castShadow = true;
    this.raiz.add(m);
  }
  actualizar(p) {
    this.raiz.position.copy(mundo(p.x, p.y));
    if (Math.hypot(p.vx, p.vy) > 0.2) this.raiz.rotation.y = Math.atan2(p.vy, p.vx) + Math.PI / 2;
  }
}

export class Personas {
  constructor(escena, Clase = FiguraSimple) {
    this.escena = escena;
    this.Clase = Clase;
    this.mapa = new Map();
  }
  limpiar() {
    this.mapa.forEach(f => { this.escena.remove(f.raiz); f.liberar && f.liberar(); });
    this.mapa.clear();
  }
  actualizar(e, dt, ctx) {
    const vivos = new Set();
    e.personas.forEach(p => {
      let f = this.mapa.get(p.clave);
      if (!f) { f = new this.Clase(p); this.mapa.set(p.clave, f); this.escena.add(f.raiz); }
      f.raiz.visible = true;
      f.actualizar(p, dt, ctx);
      vivos.add(p.clave);
    });
    this.mapa.forEach((f, k) => { if (!vivos.has(k)) f.raiz.visible = false; });
  }
  figura(clave) { return this.mapa.get(clave); }
}
