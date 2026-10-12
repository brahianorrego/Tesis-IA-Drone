# -*- coding: utf-8 -*-
"""
Entorno multiagente dron vs persona (vectorizado en NumPy, N partidas en paralelo).

Fase 2 de la misión (IA activada en la zona de búsqueda). Dos agentes con objetivos opuestos,
como el escondite de OpenAI (Baker et al., 2020):
  * DRON: busca a la persona (paneo), la MANTIENE EN LA VISTA y la esquiva si se le viene
    encima; sin maniobrar de más ni subir sin necesidad. Puede seguirla, pero nunca a menos de 8 m.
  * PERSONA: en las partidas "adversarias" (el ladrón) aprende a salirse de la vista del dron o
    a alcanzarlo; en las "guionadas" es un peatón normal (cruza, pasa, se queda quieto, se aleja...).
La fase 1 (vuelo del piloto con protección frontal por LiDAR) es una regla fija, no aprendida:
ver mision.py.

El dron NO ve el mundo: ve lo mismo que el dron real, a través de un modelo de sus sensores
(cámara de 38.9°, YOLO con ruido y pérdidas, LiDAR que solo mide si apunta a la persona,
distancia por tamaño del bbox que sobreestima de cerca, 100 ms de retraso). Sus acciones son
las 4 clases del árbitro real, con la misma confirmación (3 ciclos), duración (1.5 s) y
freno (1 s). El giro hacia la persona (yaw) es el mismo controlador de vuelo_evasion.py.

Convenciones: plano XY del mundo en metros, z hacia arriba. Rumbo psi del dron medido
antihorario desde +X. Ángulo de la persona respecto a la nariz: positivo = a la DERECHA
(igual que angulo_persona_deg en el dron real).
"""
import numpy as np

# ----------------------------------------------------------------------------- parámetros
DT = 0.1                      # CONTROL_HZ = 10
HFOV = 38.9                   # medido en la cámara real (grados)
VFOV = 29.7
ALTO_IMG = 480.0
ALTURA_PERSONA = 1.70
RADIO_PERSONA = 0.25

# Árbitro (config.py del dron)
N_CONFIRMACION = 3
DURACION_EVASION = 1.5
ENFRIAMIENTO = 1.0
VEL_LATERAL = 1.5             # m/s de la evasión lateral
VEL_ASCENSO = 0.7
TAU_DRON = 0.35               # respuesta de velocidad de ArduCopter (s)
ACC_MAX_DRON = 3.0
# Giro: con 30 grados/s la persona se salía del campo de visión con dos pasos laterales; un
# cuadricóptero gira sin problema a 60 grados/s (llevar estos valores también a config.py del dron)
YAW_KP, YAW_MAX, YAW_ZONA = 2.5, 60.0, 2.0
YAW_BUSQUEDA = 20.0           # giro lento automático si no ve a nadie por >1 s
YAW_GIRO_IA = 60.0            # acciones GIRAR_IZQ/GIRAR_DER: la IA busca activamente cuando no ve a nadie
VEL_SEGUIR = 1.5              # acción SEGUIR: avanza hacia donde mira (la persona), solo si está a > 8 m
DIST_MIN_SEGUIR = 8.0
Z_NOMINAL, Z_MIN, Z_MAX = 2.3, 1.8, 5.0
VEL_REGRESO_Z = 0.3           # baja despacio a la altura de misión si no hay nadie cerca

# Persona
VEL_CAMINAR, VEL_CORRER = 1.4, 3.3
TAU_PERSONA = 0.3
STAMINA_MAX = 2.0             # segundos de carrera seguidos
ALCANCE_H = 1.0               # radio horizontal de "alcanzado" (cuerpo + brazo + hélices)
ALCANCE_Z = 2.6               # por encima de esta altura la persona ya no alcanza al dron

ARENA = 25.0                  # zona de búsqueda (geocerca): |x|,|y| <= 25 m, para dron y persona
DURACION_EPISODIO = 30.0
PASOS_EPISODIO = int(DURACION_EPISODIO / DT)
FRACCION_ADVERSARIA = 0.5

# Recompensas del dron
R_COLISION = -10.0
R_GEOCERCA = -5.0
R_MANIOBRA = {1: -0.15, 2: -0.15, 3: -0.30}
R_CERCANIA = -0.05            # por paso, escalado, si la persona está a < 3 m y al alcance
R_ALTURA = -0.01              # por paso y por metro sobre 3 m
R_VISTA = 0.03                # OBJETIVO PRINCIPAL: por cada paso con la persona en la vista (30 s = +9)

# Acciones
CLASES = ["MANTENER", "EVADIR_IZQ", "EVADIR_DER", "DETENER_ASCENDER", "GIRAR_IZQ", "GIRAR_DER", "SEGUIR"]
OFFSETS_PERSONA = np.radians([0, 30, -30, 60, -60, 90, -90, 180])
N_ACC_PERSONA = len(OFFSETS_PERSONA) * 2 + 1   # 8 direcciones x {caminar, correr} + quieto

GUIONES = ["cruce", "directo", "quieto", "alejarse", "acercar_y_parar", "trotar_directo", "deambular"]

OBS_DRON = 9
OBS_PERSONA = 11

VIGILANDO, EVADIENDO, ENFRIANDO = 0, 1, 2


def envolver(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


class EntornoDronPersona(object):

    def __init__(self, n, semilla=0, fraccion_adversaria=FRACCION_ADVERSARIA):
        self.n = n
        self.rng = np.random.default_rng(semilla)
        self.frac_adv = fraccion_adversaria
        z = lambda: np.zeros(n)
        # dron
        self.dx, self.dy, self.dz, self.dvx, self.dvy, self.dvz, self.psi = z(), z(), z(), z(), z(), z(), z()
        self.estado = np.zeros(n, int)
        self.t_estado = z()
        self.clase = np.zeros(n, int)
        self.cand = np.zeros(n, int)
        self.cand_n = np.zeros(n, int)
        self.t_sin_ver = z()
        # persona
        self.px, self.py, self.pvx, self.pvy, self.stamina = z(), z(), z(), z(), z()
        self.adversaria = np.zeros(n, bool)
        self.guion = np.zeros(n, int)
        self.g_dirx, self.g_diry, self.g_vel, self.g_parar = z(), z(), z(), z()
        self.g_wx, self.g_wy = z(), z()
        self.corriendo = np.zeros(n, bool)
        # sensores (estado de filtros) y retraso de 1 paso
        self.vis_prev = np.zeros(n, bool)
        self.dist_prev, self.ang_prev, self.vac, self.vlat = z(), z(), z(), z()
        self.obs_retraso = np.zeros((n, OBS_DRON))
        self.info_sensor = {}
        self.yaw_dps = z()
        self.t = np.zeros(n, int)
        self.d_prev = z()
        self.reset(np.ones(n, bool))
        self._sensores()                 # llena info_sensor; la primera observación sigue "a ciegas"
        self.vis_prev[:] = False
        self.obs_retraso[:] = 0.0

    # ------------------------------------------------------------------ reinicio
    def reset(self, m):
        k = int(m.sum())
        if k == 0:
            return
        r = self.rng
        self.dx[m], self.dy[m] = r.uniform(-3, 3, k), r.uniform(-3, 3, k)
        self.dz[m] = r.uniform(2.0, 2.6, k)
        self.dvx[m] = self.dvy[m] = self.dvz[m] = 0.0
        self.psi[m] = r.uniform(-np.pi, np.pi, k)
        self.estado[m] = VIGILANDO
        self.t_estado[m] = 0.0
        self.cand[m] = 0
        self.cand_n[m] = 0
        self.t_sin_ver[m] = 0.0
        self.adversaria[m] = r.random(k) < self.frac_adv
        self.guion[m] = r.integers(0, len(GUIONES), k)
        # persona: en cualquier lugar de la zona; solo 30% arranca dentro del campo de visión,
        # así que casi siempre hay que buscarla primero (paneo)
        u = r.random(k)
        rel = np.where(u < 0.3, r.uniform(-0.26, 0.26, k), r.uniform(-np.pi, np.pi, k))
        # los peatones que caminan derecho hacia el dron vienen de frente (alcance frontal de la tesis)
        de_frente = ~self.adversaria[m] & np.isin(self.guion[m], (1, 5))
        rel = np.where(de_frente, r.uniform(-0.5, 0.5, k), rel)
        d0 = r.uniform(8, 20, k)
        b = self.psi[m] - rel
        self.px[m] = self.dx[m] + d0 * np.cos(b)
        self.py[m] = self.dy[m] + d0 * np.sin(b)
        self.pvx[m] = self.pvy[m] = 0.0
        self.stamina[m] = STAMINA_MAX
        self.corriendo[m] = False
        self._preparar_guion(m)
        self.vis_prev[m] = False
        self.vac[m] = self.vlat[m] = 0.0
        self.obs_retraso[m] = 0.0
        self.t[m] = 0
        self.d_prev[m] = np.hypot(self.px[m] - self.dx[m], self.py[m] - self.dy[m])

    def _preparar_guion(self, m):
        r = self.rng
        idx = np.where(m)[0]
        for i in idx:
            g = self.guion[i]
            hx, hy = self.dx[i] - self.px[i], self.dy[i] - self.py[i]
            dist = max(np.hypot(hx, hy), 1e-6)
            ux, uy = hx / dist, hy / dist
            self.g_vel[i] = r.uniform(1.0, 1.6)
            self.g_parar[i] = 0.0
            if g == 0:          # cruce: pasa de lado a 2-10 m del dron
                off = r.uniform(2.0, 10.0) * r.choice([-1, 1])
                cx, cy = self.dx[i] - uy * off, self.dy[i] + ux * off
                s = r.choice([-1, 1])
                L = r.uniform(8, 14)
                self.px[i], self.py[i] = cx - s * ux * L, cy - s * uy * L
                self.g_dirx[i], self.g_diry[i] = s * ux, s * uy
            elif g in (1, 5):   # directo (caminando / trotando): línea recta por donde está el dron
                self.g_dirx[i], self.g_diry[i] = ux, uy
                if g == 5:
                    self.g_vel[i] = r.uniform(2.3, 3.0)
            elif g == 2:        # quieto
                self.g_vel[i] = 0.0
                d = r.uniform(2.0, 12.0)
                self.px[i], self.py[i] = self.dx[i] - ux * d, self.dy[i] - uy * d
                self.g_dirx[i] = self.g_diry[i] = 0.0
            elif g == 3:        # alejarse
                d = r.uniform(3.0, 8.0)
                self.px[i], self.py[i] = self.dx[i] - ux * d, self.dy[i] - uy * d
                self.g_dirx[i], self.g_diry[i] = -ux, -uy
            elif g == 4:        # acercarse y detenerse a 3-6 m
                self.g_dirx[i], self.g_diry[i] = ux, uy
                self.g_parar[i] = r.uniform(3.0, 6.0)
            else:               # deambular entre puntos al azar
                self.g_wx[i], self.g_wy[i] = r.uniform(-12, 12), r.uniform(-12, 12)

    # ------------------------------------------------------------------ sensores
    def _sensores(self):
        """Lo que entregaría el pipeline real (YOLO + LiDAR + fusión de comun.py)."""
        r = self.rng
        n = self.n
        rx, ry = self.px - self.dx, self.py - self.dy
        dh = np.hypot(rx, ry)
        bearing = np.arctan2(ry, rx)
        ang = np.degrees(envolver(self.psi - bearing))            # + = derecha
        # geometría vertical: el gimbal sigue a la persona en pitch (rango -45..+20)
        elev_cent = np.degrees(np.arctan2(self.dz - 0.9, dh))
        extension = np.degrees(np.arctan2(self.dz, dh) - np.arctan2(self.dz - ALTURA_PERSONA, dh))
        h_norm = np.minimum(extension, VFOV) / VFOV
        w_norm = np.minimum(np.degrees(2 * np.arctan2(RADIO_PERSONA, dh)) / HFOV, 1.0)
        p_det = np.where(dh < 20, 0.97, np.clip(0.97 - (dh - 20) * 0.06, 0, 1))
        visible = ((np.abs(ang) < HFOV / 2 - 0.5) & (dh < 35) & (elev_cent < 45 + VFOV / 2)
                   & (r.random(n) < p_det))
        ang_m = ang + r.normal(0, 0.3, n)
        h_m = h_norm * (1 + r.normal(0, 0.03, n))
        area = h_m * w_norm
        f_px = (ALTO_IMG / 2) / np.tan(np.radians(VFOV / 2))
        d_bbox = ALTURA_PERSONA * f_px / np.maximum(h_m * ALTO_IMG, 1.0)
        semiancho = np.degrees(np.arctan2(RADIO_PERSONA, np.maximum(dh, 0.3)))
        laser = visible & (np.abs(ang) < 0.8 * semiancho + 0.3)
        d_lidar = np.hypot(dh, self.dz - 1.1) + r.normal(0, 0.02, n)
        dist = np.where(laser, d_lidar, np.minimum(d_bbox, 30.0))
        # velocidades: acercamiento (m/s, + = se acerca) y lateral en el mundo (deg/s, + = a la derecha)
        nuevo = visible & ~self.vis_prev
        sigue = visible & self.vis_prev
        vac_i = -(dist - self.dist_prev) / DT
        vlat_i = (ang_m - self.ang_prev) / DT + self.yaw_dps
        a = 0.3
        self.vac = np.where(sigue, (1 - a) * self.vac + a * np.clip(vac_i, -8, 8), 0.0)
        self.vlat = np.where(sigue, (1 - a) * self.vlat + a * np.clip(vlat_i, -90, 90), 0.0)
        self.dist_prev = np.where(visible, dist, self.dist_prev)
        self.ang_prev = np.where(visible, ang_m, self.ang_prev)
        self.vis_prev = visible
        self.t_sin_ver = np.where(visible, 0.0, self.t_sin_ver + DT)
        v = visible.astype(float)
        obs = np.stack([
            v,
            v * np.minimum(dist, 30.0) / 20.0,
            laser.astype(float),
            v * area * 4.0,
            v * np.clip(ang_m, -HFOV / 2, HFOV / 2) / (HFOV / 2),
            v * np.clip(self.vac, -5, 5) / 5.0,
            v * np.clip(self.vlat, -60, 60) / 30.0,
            self.dz - Z_NOMINAL,
            np.minimum(self.t_sin_ver, 3.0) / 3.0,
        ], axis=1)
        self.info_sensor = dict(visible=visible, laser=laser, ang=ang_m, dist=dist, dh=dh,
                                fuente=np.where(laser, 1, 0), vac=self.vac, vlat=self.vlat)
        return obs

    def obs_persona(self):
        """La persona ve todo (es humana): posición, velocidad y hacia dónde mira el dron."""
        hx, hy = self.dx - self.px, self.dy - self.py
        dh = np.hypot(hx, hy)
        b = np.arctan2(hy, hx)
        c, s = np.cos(-b), np.sin(-b)
        rot = lambda vx, vy: (c * vx - s * vy, s * vx + c * vy)
        dvx, dvy = rot(self.dvx, self.dvy)
        pvx, pvy = rot(self.pvx, self.pvy)
        mira = envolver(self.psi - (b + np.pi))          # 0 = el dron la está mirando
        return np.stack([
            np.minimum(dh, 30) / 20.0, self.dz - Z_NOMINAL,
            dvx / 3.0, dvy / 3.0, pvx / 3.0, pvy / 3.0,
            np.cos(mira), np.sin(mira),
            self.stamina / STAMINA_MAX, (self.estado == EVADIENDO).astype(float),
            self.t / PASOS_EPISODIO,
        ], axis=1)

    def obs_dron(self):
        return self.obs_retraso.copy()

    def mascara_decision(self):
        """La IA decide siempre que el árbitro está vigilando. Evadir (1-3) solo tiene efecto
        con una persona detectada (como en el árbitro real); girar (4-5) solo sin persona."""
        return self.estado == VIGILANDO

    # ------------------------------------------------------------------ paso
    def step(self, acc_dron, acc_persona, auto_reset=True):
        n = self.n
        r = self.rng
        rew_d = np.zeros(n)
        decide = self.mascara_decision()
        ve = self.obs_retraso[:, 0] > 0.5
        giro_ia = np.where(decide & ~ve & (acc_dron == 4), -YAW_GIRO_IA,
                           np.where(decide & ~ve & (acc_dron == 5), YAW_GIRO_IA, 0.0))

        # ---- árbitro (misma lógica que Arbitro.paso) ----
        nueva = decide & ve & (acc_dron > 0) & (acc_dron <= 3)
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

        # ---- consignas del dron (marco del cuerpo: x adelante, y derecha) ----
        eva = self.estado == EVADIENDO
        lejos = self.obs_retraso[:, 1] * 20.0 > DIST_MIN_SEGUIR
        vx_b = np.where(decide & ve & lejos & (acc_dron == 6), VEL_SEGUIR, 0.0)
        vy_b = np.where(eva & (self.clase == 1), -VEL_LATERAL, np.where(eva & (self.clase == 2), VEL_LATERAL, 0.0))
        dh_real = np.hypot(self.px - self.dx, self.py - self.dy)
        # Baja a la altura de misión SOLO si ve que la persona está lejos. Si no la ve, se
        # queda arriba (lo seguro): si bajara al perderla de vista, la persona aprende a
        # esperar justo debajo, donde la cámara no alcanza a mirar.
        vis_s = self.info_sensor.get("visible", np.zeros(n, bool))
        nadie_cerca = vis_s & (self.info_sensor.get("dist", np.full(n, 99.0)) > 8)
        vz_c = np.where(eva & (self.clase == 3), VEL_ASCENSO,
                        np.where((self.estado == VIGILANDO) & nadie_cerca & (self.dz > Z_NOMINAL + 0.05), -VEL_REGRESO_Z, 0.0))
        cps, sps = np.cos(self.psi), np.sin(self.psi)
        vx_c = vx_b * cps + vy_b * sps                # adelante = (cos psi, sin psi)
        vy_c = vx_b * sps - vy_b * cps                # derecha del cuerpo = (sin psi, -cos psi)
        dvx = np.clip((vx_c - self.dvx) * DT / TAU_DRON, -ACC_MAX_DRON * DT, ACC_MAX_DRON * DT)
        dvy = np.clip((vy_c - self.dvy) * DT / TAU_DRON, -ACC_MAX_DRON * DT, ACC_MAX_DRON * DT)
        self.dvx += dvx + r.normal(0, 0.02, n)       # algo de viento
        self.dvy += dvy + r.normal(0, 0.02, n)
        self.dvz += (vz_c - self.dvz) * DT / TAU_DRON
        self.dx += self.dvx * DT
        self.dy += self.dvy * DT
        self.dz = np.clip(self.dz + self.dvz * DT, Z_MIN, Z_MAX)

        # ---- yaw: seguir a la persona (vigilando) o buscar despacio si no ve a nadie ----
        vis_obs = self.obs_retraso[:, 0] > 0.5
        ang_obs = self.obs_retraso[:, 4] * HFOV / 2
        tasa = np.clip(YAW_KP * ang_obs, -YAW_MAX, YAW_MAX)
        tasa = np.where(np.abs(ang_obs) < YAW_ZONA, 0.0, tasa)
        vig = self.estado == VIGILANDO
        busca = np.where(giro_ia != 0, giro_ia, np.where(self.t_sin_ver > 1.0, YAW_BUSQUEDA, 0.0))
        self.yaw_dps = np.where(vig & vis_obs, tasa, np.where(vig, busca, 0.0))
        self.psi = envolver(self.psi - np.radians(self.yaw_dps) * DT)

        # ---- persona ----
        hx, hy = self.dx - self.px, self.dy - self.py
        dist_h = np.maximum(np.hypot(hx, hy), 1e-6)
        b = np.arctan2(hy, hx)
        quieto = acc_persona == N_ACC_PERSONA - 1
        corre_pide = (acc_persona >= len(OFFSETS_PERSONA)) & ~quieto
        off = OFFSETS_PERSONA[np.minimum(acc_persona % len(OFFSETS_PERSONA), len(OFFSETS_PERSONA) - 1)]
        self.corriendo = corre_pide & (self.stamina > 0.1)
        vel = np.where(quieto, 0.0, np.where(self.corriendo, VEL_CORRER, VEL_CAMINAR))
        dir_a = b + off
        vxa, vya = vel * np.cos(dir_a), vel * np.sin(dir_a)
        vxg, vyg = self._velocidad_guion(dist_h, hx, hy)
        adv = self.adversaria
        vx_p = np.where(adv, vxa, vxg)
        vy_p = np.where(adv, vya, vyg)
        self.corriendo = np.where(adv, self.corriendo, False)
        self.stamina = np.clip(self.stamina + np.where(self.corriendo, -DT, 0.3 * DT), 0, STAMINA_MAX)
        self.pvx += (vx_p - self.pvx) * DT / TAU_PERSONA
        self.pvy += (vy_p - self.pvy) * DT / TAU_PERSONA
        self.px = np.clip(self.px + self.pvx * DT, -ARENA, ARENA)
        self.py = np.clip(self.py + self.pvy * DT, -ARENA, ARENA)

        # ---- eventos y recompensas ----
        d = np.hypot(self.px - self.dx, self.py - self.dy)
        al_alcance = self.dz < ALCANCE_Z
        choque = (d < ALCANCE_H) & al_alcance
        fuera = (np.abs(self.dx) > ARENA) | (np.abs(self.dy) > ARENA)
        self.t += 1
        tiempo = self.t >= PASOS_EPISODIO
        rew_d += np.where(choque, R_COLISION, 0.0) + np.where(fuera, R_GEOCERCA, 0.0)
        rew_d += np.where((d < 3.0) & al_alcance, R_CERCANIA * (3.0 - d) / 3.0, 0.0)
        rew_d += R_ALTURA * np.maximum(self.dz - 3.0, 0.0)
        # la persona adversaria (el "ladrón") gana si se sale de la vista o si alcanza al dron
        rew_p = np.where(choque, 10.0, 0.0)
        self.d_prev = d
        done = choque | fuera | tiempo

        # ---- sensores con 100 ms de retraso ----
        obs_nueva = self._sensores()
        self.obs_retraso = obs_nueva
        visto = self.info_sensor["visible"]
        rew_d += np.where(visto & ~choque, R_VISTA, 0.0)
        rew_p -= np.where(visto, R_VISTA, 0.0)
        info = dict(choque=choque, fuera=fuera, tiempo=tiempo, inicia=inicia, clase_ini=np.where(inicia, self.clase, 0),
                    adversaria=self.adversaria.copy(), dist=d, visto=visto.copy())
        if auto_reset and done.any():
            self.reset(done)
        return rew_d, rew_p, done, info

    def _velocidad_guion(self, dist_h, hx, hy):
        g = self.guion
        vx, vy = self.g_dirx * self.g_vel, self.g_diry * self.g_vel
        parar = (g == 4) & (dist_h < self.g_parar)
        vx, vy = np.where(parar, 0.0, vx), np.where(parar, 0.0, vy)
        dm = g == 6
        if dm.any():
            wx, wy = self.g_wx - self.px, self.g_wy - self.py
            wd = np.maximum(np.hypot(wx, wy), 1e-6)
            llego = dm & (wd < 1.0)
            if llego.any():
                k = int(llego.sum())
                self.g_wx[llego] = self.rng.uniform(-12, 12, k)
                self.g_wy[llego] = self.rng.uniform(-12, 12, k)
            vx = np.where(dm, wx / wd * self.g_vel, vx)
            vy = np.where(dm, wy / wd * self.g_vel, vy)
        return vx, vy

    # ------------------------------------------------------------------ para el visor
    def foto(self, i):
        s = self.info_sensor
        return {
            "d": [round(float(self.dx[i]), 3), round(float(self.dy[i]), 3), round(float(self.dz[i]), 3), round(float(self.psi[i]), 4)],
            "p": [round(float(self.px[i]), 3), round(float(self.py[i]), 3)],
            "pv": [round(float(self.pvx[i]), 2), round(float(self.pvy[i]), 2)],
            "est": int(self.estado[i]), "cl": int(self.clase[i]) if self.estado[i] == EVADIENDO else 0,
            "vis": bool(s["visible"][i]), "las": bool(s["laser"][i]),
            "dm": round(float(s["dist"][i]), 2), "dh": round(float(s["dh"][i]), 2),
            "ang": round(float(s["ang"][i]), 1), "vac": round(float(s["vac"][i]), 2),
            "run": bool(self.corriendo[i]), "cand": int(self.cand[i]), "yaw": round(float(self.yaw_dps[i]), 1),
        }
