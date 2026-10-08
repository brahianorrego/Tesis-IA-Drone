# -*- coding: utf-8 -*-
"""
Fase 2 de la misión (IA activada en la zona de búsqueda), vectorizada en NumPy.

EL JUEGO ES EL DRON CONTRA EL LADRÓN, como el escondite de OpenAI (Baker et al., 2020):
  * DRON: busca al ladrón (paneo y desplazándose), lo MANTIENE EN LA VISTA y lo esquiva si se
    le viene encima. Nunca se le acerca a menos de 8 m por su cuenta.
  * LADRÓN (IA adversaria): gana si se sale de la vista del dron (por ejemplo, detrás de un
    panel) o si lo alcanza.
  * PEATONES (0 a 2 por partida, guionados): no juegan; son obstáculos móviles que el dron
    debe detectar y esquivar sin perder de vista al ladrón.
  * PANELES (2 por partida): muros de 2.6 m que tapan la cámara y el LiDAR. Nadie los atraviesa;
    el dron puede verlos por encima si sube.

El dron NO ve el mundo: ve lo mismo que el dron real (cámara de 38.9°, YOLO con ruido y
pérdidas, LiDAR frontal, 100 ms de retraso) más lo que la Pixhawk sabe (posición GPS, rumbo,
altura). Sus acciones pasan por el mismo árbitro de seguridad de vuelo_evasion.py.

Convenciones: plano XY del mundo en metros, z hacia arriba. Rumbo psi del dron medido
antihorario desde +X. Ángulo de una persona respecto a la nariz: positivo = a la DERECHA.
La fase 1 (vuelo del piloto con protección frontal) es una regla fija: ver mision.py.

IDENTIDAD DEL OBJETIVO (v4). YOLO solo dice "persona"; no sabe quién es el ladrón. Como en un
operativo real, el sistema no decide quién es sospechoso:
  1. DESIGNACIÓN: el operador (policía) toca en la estación de tierra la caja del sospechoso.
     Se modela como N_DESIGNA cuadros seguidos viéndolo (el tiempo de reacción del operador).
  2. SEGUIMIENTO: el tracker (ByteTrack/BoT-SORT de YOLO) conserva el ID mientras lo ve y hasta
     T_TRACKER segundos después de perderlo (oclusiones cortas).
  3. RE-IDENTIFICACIÓN: si lo pierde más tiempo, al reaparecer hay que confirmar que es él por su
     apariencia (ReID): N_REID cuadros seguidos, con menos acierto cuanto más lejos esté.
  Mientras no esté confirmado, el ladrón es para el dron "una persona más" (un obstáculo). El dron
  NUNCA cambia de objetivo por su cuenta: los demás son peatones a esquivar.

ÁRBITRO (v4). Solo deja esquivar si hay una amenaza real (alguien a menos de D_CRITICA, o a menos
de D_AMENAZA y acercándose). El giro sobre su eje es independiente: un peatón que aparece en la
cámara sin peligro no interrumpe el paneo, y el dron puede seguir rotando mientras esquiva.
"""
import numpy as np

# ----------------------------------------------------------------------------- parámetros
DT = 0.1
HFOV = 38.9
VFOV = 29.7
ALTO_IMG = 480.0
ALTURA_PERSONA = 1.70
RADIO_PERSONA = 0.25

# Árbitro (config.py del dron)
N_CONFIRMACION = 3
DURACION_EVASION = 1.5
ENFRIAMIENTO = 1.0
VEL_LATERAL = 1.5
VEL_ASCENSO = 0.7
TAU_DRON = 0.35
ACC_MAX_DRON = 3.0
# Giro: con 30°/s el ladrón se salía de la vista con dos pasos laterales; un cuadricóptero gira
# sin problema a 60°/s (llevar estos valores también a config.py del dron)
YAW_KP, YAW_MAX, YAW_ZONA = 2.5, 60.0, 2.0
YAW_BUSQUEDA = 20.0
YAW_GIRO_IA = 60.0
VEL_AVANCE = 1.5               # AVANZAR: busca desplazándose o sigue al ladrón (nunca a < 8 m de él)
DIST_MIN_SEGUIR = 8.0
DIST_PROTECCION_FRONTAL = 3.0  # el LiDAR bloquea el avance si hay algo a menos de 3 m al frente
D_CRITICA, D_AMENAZA, V_ACERCA = 3.0, 8.0, 0.4   # amenaza: < 3 m, o < 8 m acercándose a más de 0.4 m/s

# identidad del objetivo
N_DESIGNA = 8                  # cuadros (0.8 s) que tarda el operador en designar al sospechoso
T_TRACKER = 1.0                # s que el tracker conserva el ID sin verlo
N_REID = 4                     # cuadros seguidos confirmando la apariencia para re-adquirirlo
Z_NOMINAL, Z_MIN, Z_MAX = 2.3, 1.8, 5.0
VEL_REGRESO_Z = 0.3

# Personas
N_PERS = 3                     # 0 = ladrón, 1-2 = peatones
VEL_CAMINAR, VEL_CORRER = 1.4, 3.3
TAU_PERSONA = 0.3
STAMINA_MAX = 2.0
ALCANCE_H = 1.0
ALCANCE_Z = 2.6

# Paneles
N_PANELES = 2
ALTO_PANEL = 2.6
RADIO_DRON = 0.4

ARENA = 25.0
DURACION_EPISODIO = 40.0
PASOS_EPISODIO = int(DURACION_EPISODIO / DT)

# Recompensas
R_COLISION = -10.0
R_CHOQUE_PANEL = -5.0
R_GEOCERCA = -5.0
R_MANIOBRA = {1: -0.15, 2: -0.15, 3: -0.30}
R_ALTURA = -0.01
R_VISTA = 0.03                 # OBJETIVO PRINCIPAL: por cada paso con el ladrón en la vista
# Guía de búsqueda (reward shaping basado en potencial, Ng et al. 1999): premia acercar la nariz y la
# distancia al ladrón. Usa su posición real, pero SOLO para calificar: no es una entrada del dron.
# Al ser F = gamma*Phi(s') - Phi(s), no cambia cuál es la mejor estrategia; solo acelera el aprendizaje.
GAMMA_GUIA = 0.99
K_GUIA_ANG, K_GUIA_DIST = 0.3, 0.03

CLASES = ["MANTENER", "EVADIR_IZQ", "EVADIR_DER", "DETENER_ASCENDER", "GIRAR_IZQ", "GIRAR_DER", "AVANZAR"]
OFFSETS_PERSONA = np.radians([0, 30, -30, 60, -60, 90, -90, 180])
N_ACC_PERSONA = len(OFFSETS_PERSONA) * 2 + 1
GUIONES = ["cruce", "directo", "quieto", "alejarse", "acercar_y_parar", "trotar_directo", "deambular"]

OBS_DRON = 21
OBS_PERSONA = 22

VIGILANDO, EVADIENDO, ENFRIANDO = 0, 1, 2


def envolver(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def cruce_segmentos(p, q, a, b):
    """p,q: (..., 2) segmento de vista; a,b: (..., 2) panel. Devuelve (corta, t en [0,1] sobre p->q)."""
    r = q - p
    s = b - a
    den = r[..., 0] * s[..., 1] - r[..., 1] * s[..., 0]
    den_s = np.where(np.abs(den) < 1e-9, 1e-9, den)
    qp = a - p
    t = (qp[..., 0] * s[..., 1] - qp[..., 1] * s[..., 0]) / den_s
    u = (qp[..., 0] * r[..., 1] - qp[..., 1] * r[..., 0]) / den_s
    corta = (np.abs(den) > 1e-9) & (t > 0) & (t < 1) & (u >= 0) & (u <= 1)
    return corta, t


def dist_punto_segmento(p, a, b):
    """p: (..., 2); a,b: (..., 2). Devuelve (distancia, punto más cercano)."""
    ab = b - a
    t = np.clip(((p - a) * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-9), 0, 1)
    c = a + ab * t[..., None]
    return np.linalg.norm(p - c, axis=-1), c


class EntornoDronPersona(object):

    def __init__(self, n, semilla=0):
        self.n = n
        self.rng = np.random.default_rng(semilla)
        z = lambda *s: np.zeros((n,) + s)
        self.dx, self.dy, self.dz, self.dvx, self.dvy, self.dvz, self.psi = z(), z(), z(), z(), z(), z(), z()
        self.estado = np.zeros(n, int)
        self.t_estado = z()
        self.clase = np.zeros(n, int)
        self.cand = np.zeros(n, int)
        self.cand_n = np.zeros(n, int)
        self.t_sin_ver = z()
        self.ult_rumbo = z()             # rumbo en el mundo donde vio al ladrón por última vez
        self.ult_dist = z()
        self.visto_alguna = np.zeros(n, bool)
        self.designado = np.zeros(n, bool)   # el operador ya designó al sospechoso
        self.n_conf = np.zeros(n, int)       # cuadros seguidos confirmando su identidad
        self.lock = np.zeros(n, bool)        # objetivo a la vista con la identidad confirmada
        self.giro_mem = z()                  # giro de búsqueda en curso (°/s)
        self.amenaza = np.zeros(n, bool)
        self.ids = np.zeros((n, N_PERS), int)  # ID del tracker de cada persona (solo para el visor)
        # personas
        self.px, self.py, self.pvx, self.pvy = z(N_PERS), z(N_PERS), z(N_PERS), z(N_PERS)
        self.activa = np.zeros((n, N_PERS), bool)
        self.guion = np.zeros((n, N_PERS), int)
        self.g_dirx, self.g_diry, self.g_vel, self.g_parar = z(N_PERS), z(N_PERS), z(N_PERS), z(N_PERS)
        self.g_wx, self.g_wy = z(N_PERS), z(N_PERS)
        self.stamina = z()
        self.corriendo = np.zeros(n, bool)
        # paneles: extremos A y B y su altura (en la misión se agregan como segmentos los obstáculos del camino)
        self.pa, self.pb = z(N_PANELES, 2), z(N_PANELES, 2)
        self.ph = np.full((n, N_PANELES), ALTO_PANEL)
        # sensores
        self.vis_prev = np.zeros((n, N_PERS), bool)
        self.dist_prev, self.ang_prev, self.vac, self.vlat = z(N_PERS), z(N_PERS), z(N_PERS), z(N_PERS)
        self.obs_retraso = np.zeros((n, OBS_DRON))
        self.info_sensor = {}
        self.yaw_dps = z()
        self.lidar = np.full(n, 20.0)
        self.t = np.zeros(n, int)
        self.phi = z()
        self.reset(np.ones(n, bool))
        self._sensores()
        self.vis_prev[:] = False
        self.obs_retraso[:] = 0.0

    # ------------------------------------------------------------------ reinicio
    def reset(self, m):
        k = int(m.sum())
        if k == 0:
            return
        r = self.rng
        idx = np.where(m)[0]
        self.dx[m], self.dy[m] = r.uniform(-12, 12, k), r.uniform(-12, 12, k)
        self.dz[m] = r.uniform(2.0, 2.6, k)
        self.dvx[m] = self.dvy[m] = self.dvz[m] = 0.0
        self.psi[m] = r.uniform(-np.pi, np.pi, k)
        self.estado[m] = VIGILANDO
        self.t_estado[m] = 0.0
        self.cand[m] = 0
        self.cand_n[m] = 0
        self.t_sin_ver[m] = 0.0
        self.ult_rumbo[m] = 0.0
        self.ult_dist[m] = 0.0
        self.visto_alguna[m] = False
        self.designado[m] = False
        self.n_conf[m] = 0
        self.lock[m] = False
        self.giro_mem[m] = 0.0
        self.amenaza[m] = False
        for i in idx:
            self.ids[i] = r.choice(np.arange(1, 60), N_PERS, replace=False)
        # paneles: lejos del dron, en cualquier orientación
        for i in idx:
            for j in range(N_PANELES):
                c = r.uniform(-17, 17, 2)
                for _ in range(20):
                    if np.hypot(c[0] - self.dx[i], c[1] - self.dy[i]) > 5:
                        break
                    c = r.uniform(-17, 17, 2)
                ang = r.uniform(0, np.pi)
                L = r.uniform(4.0, 6.5)
                u = np.array([np.cos(ang), np.sin(ang)]) * L / 2
                self.pa[i, j], self.pb[i, j] = c - u, c + u
        # ladrón: a 8-20 m; 30% dentro del campo de visión
        u = r.random(k)
        rel = np.where(u < 0.3, r.uniform(-0.26, 0.26, k), r.uniform(-np.pi, np.pi, k))
        d0 = r.uniform(8, 20, k)
        b = self.psi[m] - rel
        self.px[m, 0] = np.clip(self.dx[m] + d0 * np.cos(b), -ARENA + 1, ARENA - 1)
        self.py[m, 0] = np.clip(self.dy[m] + d0 * np.sin(b), -ARENA + 1, ARENA - 1)
        self.activa[m, 0] = True
        self.stamina[m] = STAMINA_MAX
        self.corriendo[m] = False
        # peatones: 0, 1 o 2 por partida
        npea = r.choice([0, 1, 2], size=k, p=[0.3, 0.4, 0.3])
        for a, i in enumerate(idx):
            for j in (1, 2):
                act = j <= npea[a]
                self.activa[i, j] = act
                if act:
                    self._preparar_peaton(i, j)
                else:
                    self.px[i, j] = self.py[i, j] = 999.0
        self.pvx[m] = self.pvy[m] = 0.0
        self.vis_prev[m] = False
        self.vac[m] = self.vlat[m] = 0.0
        self.obs_retraso[m] = 0.0
        self.t[m] = 0
        self.phi[m] = self._potencial()[m]

    def _potencial(self):
        rx, ry = self.px[:, 0] - self.dx, self.py[:, 0] - self.dy
        err = np.abs(envolver(np.arctan2(ry, rx) - self.psi))
        return -K_GUIA_ANG * err / np.pi - K_GUIA_DIST * np.maximum(np.hypot(rx, ry) - 12.0, 0.0)

    def _preparar_peaton(self, i, j):
        r = self.rng
        g = int(r.integers(0, len(GUIONES)))
        self.guion[i, j] = g
        rel = r.uniform(-0.5, 0.5) if g in (1, 5) else r.uniform(-np.pi, np.pi)
        d0 = r.uniform(8, 18)
        b = self.psi[i] - rel
        self.px[i, j], self.py[i, j] = self.dx[i] + d0 * np.cos(b), self.dy[i] + d0 * np.sin(b)
        hx, hy = self.dx[i] - self.px[i, j], self.dy[i] - self.py[i, j]
        dist = max(np.hypot(hx, hy), 1e-6)
        ux, uy = hx / dist, hy / dist
        self.g_vel[i, j] = r.uniform(1.0, 1.6)
        self.g_parar[i, j] = 0.0
        self.g_dirx[i, j], self.g_diry[i, j] = 0.0, 0.0
        if g == 0:
            off = r.uniform(2.0, 10.0) * r.choice([-1, 1])
            cx, cy = self.dx[i] - uy * off, self.dy[i] + ux * off
            s = r.choice([-1, 1])
            L = r.uniform(8, 14)
            self.px[i, j], self.py[i, j] = cx - s * ux * L, cy - s * uy * L
            self.g_dirx[i, j], self.g_diry[i, j] = s * ux, s * uy
        elif g in (1, 5):
            self.g_dirx[i, j], self.g_diry[i, j] = ux, uy
            if g == 5:
                self.g_vel[i, j] = r.uniform(2.3, 3.0)
        elif g == 2:
            self.g_vel[i, j] = 0.0
            d = r.uniform(3.0, 12.0)
            self.px[i, j], self.py[i, j] = self.dx[i] - ux * d, self.dy[i] - uy * d
        elif g == 3:
            d = r.uniform(3.0, 8.0)
            self.px[i, j], self.py[i, j] = self.dx[i] - ux * d, self.dy[i] - uy * d
            self.g_dirx[i, j], self.g_diry[i, j] = -ux, -uy
        elif g == 4:
            self.g_dirx[i, j], self.g_diry[i, j] = ux, uy
            self.g_parar[i, j] = r.uniform(3.0, 6.0)
        else:
            self.g_wx[i, j], self.g_wy[i, j] = r.uniform(-15, 15), r.uniform(-15, 15)
        self.px[i, j] = np.clip(self.px[i, j], -ARENA, ARENA)
        self.py[i, j] = np.clip(self.py[i, j], -ARENA, ARENA)

    # ------------------------------------------------------------------ geometría
    def _vista_bloqueada(self, qx, qy, qz):
        """¿Algún panel tapa la línea de vista del dron a (qx,qy,qz)? Formas (n, P)."""
        p = np.broadcast_to(np.stack([self.dx, self.dy], -1)[:, None, :], qx.shape + (2,))
        q = np.stack([qx, qy], -1)
        z = np.broadcast_to(self.dz[:, None], qx.shape)
        bloq = np.zeros(qx.shape, bool)
        for j in range(self.pa.shape[1]):
            a = np.broadcast_to(self.pa[:, j][:, None, :], q.shape)
            b = np.broadcast_to(self.pb[:, j][:, None, :], q.shape)
            corta, t = cruce_segmentos(p, q, a, b)
            h = z + (qz - z) * t
            bloq |= corta & (h < self.ph[:, j][:, None])
        return bloq

    def _lidar_frontal(self):
        """Distancia al panel que tenga al frente (a la altura del dron), hasta 20 m."""
        p = np.stack([self.dx, self.dy], -1)
        q = p + 20.0 * np.stack([np.cos(self.psi), np.sin(self.psi)], -1)
        d = np.full(self.n, 20.0)
        for j in range(self.pa.shape[1]):
            corta, t = cruce_segmentos(p, q, self.pa[:, j], self.pb[:, j])
            d = np.where(corta & (self.dz < self.ph[:, j]), np.minimum(d, 20.0 * t), d)
        return d

    # ------------------------------------------------------------------ sensores
    def _sensores(self):
        r = self.rng
        n = self.n
        rx, ry = self.px - self.dx[:, None], self.py - self.dy[:, None]
        dh = np.hypot(rx, ry)
        bearing = np.arctan2(ry, rx)
        ang = np.degrees(envolver(self.psi[:, None] - bearing))
        dz = self.dz[:, None]
        elev = np.degrees(np.arctan2(dz - 0.9, dh))
        extension = np.degrees(np.arctan2(dz, dh) - np.arctan2(dz - ALTURA_PERSONA, dh))
        h_norm = np.minimum(extension, VFOV) / VFOV
        w_norm = np.minimum(np.degrees(2 * np.arctan2(RADIO_PERSONA, dh)) / HFOV, 1.0)
        p_det = np.where(dh < 20, 0.97, np.clip(0.97 - (dh - 20) * 0.06, 0, 1))
        tapada = self._vista_bloqueada(self.px, self.py, np.full(self.px.shape, 1.0)) & self.activa
        visible = (self.activa & (np.abs(ang) < HFOV / 2 - 0.5) & (dh < 35) & (elev < 45 + VFOV / 2)
                   & ~tapada & (r.random((n, N_PERS)) < p_det))
        ang_m = ang + r.normal(0, 0.3, (n, N_PERS))
        h_m = h_norm * (1 + r.normal(0, 0.03, (n, N_PERS)))
        area = h_m * w_norm
        f_px = (ALTO_IMG / 2) / np.tan(np.radians(VFOV / 2))
        d_bbox = ALTURA_PERSONA * f_px / np.maximum(h_m * ALTO_IMG, 1.0)
        semiancho = np.degrees(np.arctan2(RADIO_PERSONA, np.maximum(dh, 0.3)))
        laser = visible & (np.abs(ang) < 0.8 * semiancho + 0.3)
        d_lidar = np.hypot(dh, dz - 1.1) + r.normal(0, 0.02, (n, N_PERS))
        dist = np.where(laser, d_lidar, np.minimum(d_bbox, 30.0))
        sigue = visible & self.vis_prev
        a = 0.3
        vac_i = -(dist - self.dist_prev) / DT
        vlat_i = (ang_m - self.ang_prev) / DT + self.yaw_dps[:, None]
        self.vac = np.where(sigue, (1 - a) * self.vac + a * np.clip(vac_i, -8, 8), 0.0)
        self.vlat = np.where(sigue, (1 - a) * self.vlat + a * np.clip(vlat_i, -90, 90), 0.0)
        self.dist_prev = np.where(visible, dist, self.dist_prev)
        self.ang_prev = np.where(visible, ang_m, self.ang_prev)
        self.vis_prev = visible
        # identidad: el operador designa al sospechoso, el tracker conserva el ID y ReID lo recupera
        v0_raw = visible[:, 0]
        d0 = dist[:, 0]
        p_id = np.where(self.designado, np.where(d0 < 12, 0.85, np.where(d0 < 20, 0.6, 0.3)), 1.0)
        self.n_conf = np.where(v0_raw, self.n_conf + (r.random(n) < p_id), 0)
        continuo = self.designado & (self.t_sin_ver <= T_TRACKER)
        v0 = v0_raw & (continuo | (self.n_conf >= np.where(self.designado, N_REID, N_DESIGNA)))
        self.designado |= v0
        self.lock = v0
        # memoria del ladrón (persona 0): dónde lo vio confirmado por última vez

        self.t_sin_ver = np.where(v0, 0.0, self.t_sin_ver + DT)
        self.ult_rumbo = np.where(v0, envolver(self.psi - np.radians(ang_m[:, 0])), self.ult_rumbo)
        self.ult_dist = np.where(v0, dist[:, 0], self.ult_dist)
        self.visto_alguna |= v0
        rel_ult = envolver(self.ult_rumbo - self.psi)
        mem = self.visto_alguna.astype(float)
        # la otra persona visible más cercana (obstáculo); el ladrón sin confirmar cuenta como una más
        cand = visible.copy()
        cand[:, 0] = v0_raw & ~v0
        otros_d = np.where(cand, dist, 99.0)
        jo = np.argmin(otros_d, axis=1)
        sel = lambda arr: np.take_along_axis(arr, jo[:, None], axis=1)[:, 0]
        vo = sel(cand.astype(float))
        self.lidar = self._lidar_frontal()
        v = v0.astype(float)
        obs = np.stack([
            v,
            v * np.minimum(dist[:, 0], 30.0) / 20.0,
            (laser[:, 0] & v0).astype(float),
            v * area[:, 0] * 4.0,
            v * np.clip(ang_m[:, 0], -HFOV / 2, HFOV / 2) / (HFOV / 2),
            v * np.clip(self.vac[:, 0], -5, 5) / 5.0,
            v * np.clip(self.vlat[:, 0], -60, 60) / 30.0,
            self.dz - Z_NOMINAL,
            np.minimum(self.t_sin_ver, 5.0) / 5.0,
            mem * np.sin(rel_ult), mem * np.cos(rel_ult), mem * np.minimum(self.ult_dist, 30.0) / 20.0,
            vo,
            vo * np.minimum(sel(dist), 30.0) / 20.0,
            vo * np.clip(sel(ang_m), -HFOV / 2, HFOV / 2) / (HFOV / 2),
            vo * np.clip(sel(self.vac), -5, 5) / 5.0,
            self.lidar / 20.0,
            self.dx / ARENA, self.dy / ARENA, np.cos(self.psi), np.sin(self.psi),
        ], axis=1)
        self.info_sensor = dict(visible=visible, laser=laser, ang=ang_m, dist=dist, dh=dh, tapada=tapada, lock=v0.copy())
        return obs

    def obs_persona(self):
        """El ladrón ve todo (es humano): el dron, hacia dónde mira, y dónde están los paneles."""
        hx, hy = self.dx - self.px[:, 0], self.dy - self.py[:, 0]
        dh = np.hypot(hx, hy)
        b = np.arctan2(hy, hx)
        c, s = np.cos(-b), np.sin(-b)
        rot = lambda vx, vy: (c * vx - s * vy, s * vx + c * vy)
        dvx, dvy = rot(self.dvx, self.dvy)
        pvx, pvy = rot(self.pvx[:, 0], self.pvy[:, 0])
        mira = envolver(self.psi - (b + np.pi))
        cols = [np.minimum(dh, 30) / 20.0, self.dz - Z_NOMINAL, dvx / 3.0, dvy / 3.0, pvx / 3.0, pvy / 3.0,
                np.cos(mira), np.sin(mira), self.stamina / STAMINA_MAX, (self.estado == EVADIENDO).astype(float),
                self.t / PASOS_EPISODIO, self.info_sensor["visible"][:, 0].astype(float),
                self.info_sensor["tapada"][:, 0].astype(float)]
        for j in range(N_PANELES):
            cx = (self.pa[:, j, 0] + self.pb[:, j, 0]) / 2 - self.px[:, 0]
            cy = (self.pa[:, j, 1] + self.pb[:, j, 1]) / 2 - self.py[:, 0]
            ex, ey = self.pb[:, j, 0] - self.pa[:, j, 0], self.pb[:, j, 1] - self.pa[:, j, 1]
            th = np.arctan2(ey, ex) - b
            qx, qy = rot(cx, cy)
            cols += [np.clip(qx / 20.0, -2, 2), np.clip(qy / 20.0, -2, 2), np.cos(2 * th), np.sin(2 * th)]
        cols.append(np.minimum(dh, 30) / 30.0)
        return np.stack(cols, axis=1)

    def obs_dron(self):
        return self.obs_retraso.copy()

    def mascara_decision(self):
        return self.estado == VIGILANDO

    # ------------------------------------------------------------------ paso
    def step(self, acc_dron, acc_persona, auto_reset=True):
        n = self.n
        r = self.rng
        rew_d = np.zeros(n)
        decide = self.mascara_decision()
        o = self.obs_retraso
        ve = o[:, 0] > 0.5                                           # objetivo confirmado a la vista
        # ---- amenaza real: alguien muy cerca, o cerca y acercándose ----
        d_l, v_l, d_p, v_p = o[:, 1] * 20.0, o[:, 5] * 5.0, o[:, 13] * 20.0, o[:, 15] * 5.0
        self.amenaza = ((ve & ((d_l < D_CRITICA) | ((d_l < D_AMENAZA) & (v_l > V_ACERCA))))
                        | ((o[:, 12] > 0.5) & ((d_p < D_CRITICA) | ((d_p < D_AMENAZA) & (v_p > V_ACERCA)))))
        # ---- giro de búsqueda: sigue hasta que la IA pida otra cosa; una persona sin peligro no lo corta ----
        self.giro_mem = np.where(decide & (acc_dron == 4), -YAW_GIRO_IA,
                                 np.where(decide & (acc_dron == 5), YAW_GIRO_IA,
                                          np.where(decide & ((acc_dron == 0) | (acc_dron == 6)), 0.0, self.giro_mem)))
        self.giro_mem = np.where(ve, 0.0, self.giro_mem)

        # ---- árbitro: esquivar solo ante una amenaza real ----
        nueva = decide & self.amenaza & (acc_dron > 0) & (acc_dron <= 3)
        mismo = nueva & (acc_dron == self.cand)
        self.cand_n = np.where(mismo, self.cand_n + 1, np.where(nueva, 1, 0))
        self.cand = np.where(nueva, acc_dron, 0)
        self.cand_n = np.where(decide, self.cand_n, 0)
        inicia = decide & (self.cand_n >= N_CONFIRMACION)
        for k, costo in R_MANIOBRA.items():
            rew_d += np.where(inicia & (self.cand == k), costo, 0.0)
        self.clase = np.where(inicia, self.cand, self.clase)
        self.estado = np.where(inicia, EVADIENDO, self.estado)
        self.t_estado = np.where(inicia, 0.0, self.t_estado + DT)
        self.cand = np.where(inicia, 0, self.cand)
        self.cand_n = np.where(inicia, 0, self.cand_n)
        fin_eva = (self.estado == EVADIENDO) & (self.t_estado >= DURACION_EVASION)
        self.estado = np.where(fin_eva, ENFRIANDO, self.estado)
        self.t_estado = np.where(fin_eva, 0.0, self.t_estado)
        fin_enf = (self.estado == ENFRIANDO) & (self.t_estado >= ENFRIAMIENTO)
        self.estado = np.where(fin_enf, VIGILANDO, self.estado)

        # ---- consignas (cuerpo: x adelante, y derecha) ----
        eva = self.estado == EVADIENDO
        lejos = ~ve | (o[:, 1] * 20.0 > DIST_MIN_SEGUIR)            # nunca avanza hacia el ladrón a < 8 m
        cerca_peaton = (o[:, 12] > 0.5) & (o[:, 13] * 20.0 < DIST_MIN_SEGUIR) & (np.abs(o[:, 14]) < 0.5)
        libre = self.lidar > DIST_PROTECCION_FRONTAL                 # protección frontal por LiDAR
        avanza = decide & (acc_dron == 6) & lejos & libre & ~cerca_peaton
        vx_b = np.where(avanza, VEL_AVANCE, 0.0)
        vy_b = np.where(eva & (self.clase == 1), -VEL_LATERAL, np.where(eva & (self.clase == 2), VEL_LATERAL, 0.0))
        vis_s = self.info_sensor["visible"][:, 0]
        nadie_cerca = vis_s & (self.info_sensor["dist"][:, 0] > 8)
        vz_c = np.where(eva & (self.clase == 3), VEL_ASCENSO,
                        np.where((self.estado == VIGILANDO) & nadie_cerca & (self.dz > Z_NOMINAL + 0.05), -VEL_REGRESO_Z, 0.0))
        cps, sps = np.cos(self.psi), np.sin(self.psi)
        vx_c = vx_b * cps + vy_b * sps
        vy_c = vx_b * sps - vy_b * cps
        self.dvx += np.clip((vx_c - self.dvx) * DT / TAU_DRON, -ACC_MAX_DRON * DT, ACC_MAX_DRON * DT) + r.normal(0, 0.02, n)
        self.dvy += np.clip((vy_c - self.dvy) * DT / TAU_DRON, -ACC_MAX_DRON * DT, ACC_MAX_DRON * DT) + r.normal(0, 0.02, n)
        self.dvz += (vz_c - self.dvz) * DT / TAU_DRON
        self.dx += self.dvx * DT
        self.dy += self.dvy * DT
        self.dz = np.clip(self.dz + self.dvz * DT, Z_MIN, Z_MAX)

        # ---- yaw: sigue al ladrón si lo ve; si no, la IA busca (o un giro lento). Es independiente de la
        #      evasión: rotar sobre su eje no lo acerca a nadie, así que sigue girando mientras esquiva ----
        ang_obs = o[:, 4] * HFOV / 2
        tasa = np.clip(YAW_KP * ang_obs, -YAW_MAX, YAW_MAX)
        tasa = np.where(np.abs(ang_obs) < YAW_ZONA, 0.0, tasa)
        busca = np.where(self.giro_mem != 0, self.giro_mem, np.where((self.t_sin_ver > 1.0) & ~avanza, YAW_BUSQUEDA, 0.0))
        self.yaw_dps = np.where(ve, tasa, busca)
        self.psi = envolver(self.psi - np.radians(self.yaw_dps) * DT)

        # ---- ladrón (IA) ----
        hx, hy = self.dx - self.px[:, 0], self.dy - self.py[:, 0]
        b = np.arctan2(hy, hx)
        quieto = acc_persona == N_ACC_PERSONA - 1
        corre_pide = (acc_persona >= len(OFFSETS_PERSONA)) & ~quieto
        off = OFFSETS_PERSONA[acc_persona % len(OFFSETS_PERSONA)]
        self.corriendo = corre_pide & (self.stamina > 0.1)
        vel = np.where(quieto, 0.0, np.where(self.corriendo, VEL_CORRER, VEL_CAMINAR))
        vxp = np.zeros((n, N_PERS))
        vyp = np.zeros((n, N_PERS))
        vxp[:, 0], vyp[:, 0] = vel * np.cos(b + off), vel * np.sin(b + off)
        self.stamina = np.clip(self.stamina + np.where(self.corriendo, -DT, 0.3 * DT), 0, STAMINA_MAX)
        # ---- peatones (guión) ----
        gx, gy = self._velocidad_guion()
        vxp[:, 1:], vyp[:, 1:] = gx, gy
        self.pvx += (vxp - self.pvx) * DT / TAU_PERSONA
        self.pvy += (vyp - self.pvy) * DT / TAU_PERSONA
        self.px = np.where(self.activa, np.clip(self.px + self.pvx * DT, -ARENA, ARENA), self.px)
        self.py = np.where(self.activa, np.clip(self.py + self.pvy * DT, -ARENA, ARENA), self.py)
        # nadie atraviesa los paneles: se empuja fuera del muro
        pp = np.stack([self.px, self.py], -1)
        for j in range(self.pa.shape[1]):
            a = np.broadcast_to(self.pa[:, j][:, None, :], pp.shape)
            bb = np.broadcast_to(self.pb[:, j][:, None, :], pp.shape)
            d, c = dist_punto_segmento(pp, a, bb)
            dentro = d < 0.35
            nrm = (pp - c) / np.maximum(d, 1e-6)[..., None]
            pp = np.where(dentro[..., None], c + nrm * 0.35, pp)
        self.px, self.py = pp[..., 0].copy(), pp[..., 1].copy()

        # ---- eventos ----
        d_all = np.hypot(self.px - self.dx[:, None], self.py - self.dy[:, None])
        al_alcance = self.dz < ALCANCE_Z
        toca = (d_all < ALCANCE_H) & self.activa & al_alcance[:, None]
        choque = toca.any(1)
        lo_alcanza_ladron = toca[:, 0]
        choca_panel = np.zeros(n, bool)
        for j in range(self.pa.shape[1]):
            d, _ = dist_punto_segmento(np.stack([self.dx, self.dy], -1), self.pa[:, j], self.pb[:, j])
            choca_panel |= (d < RADIO_DRON) & (self.dz < self.ph[:, j] + 0.2)
        fuera = (np.abs(self.dx) > ARENA) | (np.abs(self.dy) > ARENA)
        self.t += 1
        tiempo = self.t >= PASOS_EPISODIO
        rew_d += np.where(choque, R_COLISION, 0.0) + np.where(fuera, R_GEOCERCA, 0.0) + np.where(choca_panel, R_CHOQUE_PANEL, 0.0)
        rew_d += R_ALTURA * np.maximum(self.dz - 3.0, 0.0)
        rew_p = np.where(lo_alcanza_ladron, 10.0, 0.0)
        done = choque | fuera | choca_panel | tiempo
        phi_nuevo = self._potencial()
        rew_d += np.where(done, 0.0, GAMMA_GUIA * phi_nuevo - self.phi)
        self.phi = phi_nuevo

        obs_nueva = self._sensores()
        self.obs_retraso = obs_nueva
        visto = self.info_sensor["lock"]
        rew_d += np.where(visto & ~choque, R_VISTA, 0.0)
        rew_p -= np.where(visto, R_VISTA, 0.0)
        info = dict(choque=choque, choque_ladron=lo_alcanza_ladron, choque_peaton=choque & ~lo_alcanza_ladron,
                    panel=choca_panel, fuera=fuera, tiempo=tiempo, inicia=inicia,
                    dist=d_all[:, 0], visto=visto.copy(), peatones=self.activa[:, 1:].sum(1))
        if auto_reset and done.any():
            self.reset(done)
        return rew_d, rew_p, done, info

    def _velocidad_guion(self):
        g = self.guion[:, 1:]
        px, py = self.px[:, 1:], self.py[:, 1:]
        dist_h = np.hypot(self.dx[:, None] - px, self.dy[:, None] - py)
        vx, vy = self.g_dirx[:, 1:] * self.g_vel[:, 1:], self.g_diry[:, 1:] * self.g_vel[:, 1:]
        parar = (g == 4) & (dist_h < self.g_parar[:, 1:])
        vx, vy = np.where(parar, 0.0, vx), np.where(parar, 0.0, vy)
        dm = (g == 6) & self.activa[:, 1:]
        if dm.any():
            wx, wy = self.g_wx[:, 1:] - px, self.g_wy[:, 1:] - py
            wd = np.maximum(np.hypot(wx, wy), 1e-6)
            llego = dm & (wd < 1.0)
            if llego.any():
                k = int(llego.sum())
                gw = self.g_wx[:, 1:].copy()
                gw[llego] = self.rng.uniform(-15, 15, k)
                self.g_wx[:, 1:] = gw
                gw = self.g_wy[:, 1:].copy()
                gw[llego] = self.rng.uniform(-15, 15, k)
                self.g_wy[:, 1:] = gw
            vx = np.where(dm, wx / wd * self.g_vel[:, 1:], vx)
            vy = np.where(dm, wy / wd * self.g_vel[:, 1:], vy)
        act = self.activa[:, 1:]
        return np.where(act, vx, 0.0), np.where(act, vy, 0.0)

    # ------------------------------------------------------------------ para el visor
    def foto(self, i):
        s = self.info_sensor
        pers = []
        for j in range(N_PERS):
            if not self.activa[i, j]:
                continue
            pers.append({"rol": "ladron" if j == 0 else "peaton",
                         "p": [round(float(self.px[i, j]), 3), round(float(self.py[i, j]), 3)],
                         "v": [round(float(self.pvx[i, j]), 2), round(float(self.pvy[i, j]), 2)],
                         "vis": bool(s["visible"][i, j]), "tap": bool(s["tapada"][i, j]), "id": int(self.ids[i, j]),
                         "run": bool(self.corriendo[i]) if j == 0 else bool(self.g_vel[i, j] > 2.0)})
        return {
            "d": [round(float(self.dx[i]), 3), round(float(self.dy[i]), 3), round(float(self.dz[i]), 3), round(float(self.psi[i]), 4)],
            "dv": [round(float(self.dvx[i]), 2), round(float(self.dvy[i]), 2)],
            "pers": pers,
            "p": pers[0]["p"], "pv": pers[0]["v"], "run": pers[0]["run"],
            "est": int(self.estado[i]), "cl": int(self.clase[i]) if self.estado[i] == EVADIENDO else 0,
            "vis": bool(s["lock"][i]), "las": bool(s["laser"][i, 0] and s["lock"][i]),
            "trk": self._estado_tracker(i), "amz": bool(self.amenaza[i]), "giro": round(float(self.giro_mem[i]), 1),
            "dm": round(float(s["dist"][i, 0]), 2), "dh": round(float(s["dh"][i, 0]), 2),
            "ang": round(float(s["ang"][i, 0]), 1), "vac": round(float(self.vac[i, 0]), 2),
            "cand": int(self.cand[i]), "yaw": round(float(self.yaw_dps[i]), 1),
            "lid": round(float(self.lidar[i]), 2), "fase": 2,
        }

    def _estado_tracker(self, i):
        """0 sin designar · 1 objetivo fijado · 2 memoria (tracker) · 3 perdido · 4 re-identificando."""
        if not self.designado[i]:
            return 0
        if self.lock[i]:
            return 1
        if self.info_sensor["visible"][i, 0]:
            return 4
        return 2 if self.t_sin_ver[i] <= T_TRACKER else 3

    def paneles(self, i):
        return [[round(float(self.pa[i, j, 0]), 2), round(float(self.pa[i, j, 1]), 2),
                 round(float(self.pb[i, j, 0]), 2), round(float(self.pb[i, j, 1]), 2), float(self.ph[i, j])] for j in range(N_PANELES)]

    def agregar_cajas(self, cajas):
        """Solo para la misión (n=1): agrega obstáculos como 4 segmentos cada uno. caja = (cx, cy, ancho_x, ancho_y, alto)."""
        segs = []
        for cx, cy, sx, sy, h in cajas:
            x0, x1, y0, y1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2
            segs += [((x0, y0), (x1, y0), h), ((x1, y0), (x1, y1), h), ((x1, y1), (x0, y1), h), ((x0, y1), (x0, y0), h)]
        if not segs:
            return
        a = np.array([[s[0] for s in segs]], float)
        b = np.array([[s[1] for s in segs]], float)
        h = np.array([[s[2] for s in segs]], float)
        self.pa = np.concatenate([self.pa, np.repeat(a, self.n, 0)], 1)
        self.pb = np.concatenate([self.pb, np.repeat(b, self.n, 0)], 1)
        self.ph = np.concatenate([self.ph, np.repeat(h, self.n, 0)], 1)
