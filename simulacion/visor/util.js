// Utilidades comunes del visor V16.
import * as THREE from "three";

// Ejes: la simulación usa (x, y) en el piso y z hacia arriba; three.js usa y hacia arriba. psi = 0 mira a +x.
export const mundo = (x, y, z = 0) => new THREE.Vector3(x, z, -y);
export const enMundo = (v, x, y, z = 0) => v.set(x, z, -y);
export const lerp = (a, b, f) => a + (b - a) * f;
export const limitar = (v, a, b) => Math.max(a, Math.min(b, v));
export const suave = t => t * t * (3 - 2 * t);
export const suave5 = t => t * t * t * (t * (t * 6 - 15) + 10);
export const angNorm = a => Math.atan2(Math.sin(a), Math.cos(a));
export function lerpAng(a, b, f) { return a + angNorm(b - a) * f; }
export const $ = id => document.getElementById(id);
export const pad2 = n => String(n).padStart(2, "0");
export const relojTxt = t => pad2(Math.floor(t / 60)) + ":" + pad2(Math.floor(t % 60));

// Reglas duras que el visor también respeta al dibujar (CLAUDE.md, regla 1)
export const GIMBAL_MIN = -45, GIMBAL_MAX = 15;
// Cámaras reales (plan V16, sección 4 y 5; jetson/config.py)
export const CAM = { hfov: 38.9, ancho: 640, alto: 480 };
export const CAM_PISO = { hfov: 62.2, vfov: 48.8, pitch: -90, ancho: 640, alto: 480 };
export const vfovDe = (hfov, aspecto) => 2 * Math.atan(Math.tan(hfov * Math.PI / 360) / aspecto) * 180 / Math.PI;

// Generador pseudoaleatorio con semilla (las personas y los árboles salen iguales en cada carga)
export function azar(semilla) {
  let s = semilla >>> 0 || 1;
  return () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 1e6) / 1e6; };
}

// UV en metros según la normal (proyección por caras): las texturas no se estiran con el tamaño del objeto
export function uvMetros(geo, metrosPorTile = 2) {
  const p = geo.attributes.position, n = geo.attributes.normal, uv = new Float32Array(p.count * 2);
  for (let i = 0; i < p.count; i++) {
    const nx = Math.abs(n.getX(i)), ny = Math.abs(n.getY(i)), nz = Math.abs(n.getZ(i));
    let u, v;
    if (ny >= nx && ny >= nz) { u = p.getX(i); v = p.getZ(i); }
    else if (nx >= nz) { u = p.getZ(i); v = p.getY(i); }
    else { u = p.getX(i); v = p.getY(i); }
    uv[2 * i] = u / metrosPorTile; uv[2 * i + 1] = v / metrosPorTile;
  }
  geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  return geo;
}
