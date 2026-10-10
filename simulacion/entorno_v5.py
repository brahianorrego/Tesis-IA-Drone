# -*- coding: utf-8 -*-
"""
Fase 2 de la misión (IA activada en la zona), vectorizada en NumPy · versión 5.

EL JUEGO ES EL DRON CONTRA EL LADRÓN (como el escondite de OpenAI, Baker et al. 2020), con el flujo
de trabajo real entre el dron y el operador policial (humano en el lazo):

  1. BUSCAR (SEARCH): al entrar a la zona el dron gira 360° sobre su eje buscando personas con YOLO.
     Si completa la vuelta sin candidatos, se reposiciona (patrulla) y vuelve a girar. El giro es
     continuo: solo lo pausa alguien que rompa el perímetro de colisión (D_PERIMETRO).
  2. VERIFICAR: al detectar a una persona que el operador no haya descartado, el dron queda en hover,
     la centra en la cámara y avisa al operador, que responde en 1 a 2 s:
       · "NO ES"  -> ese ID queda descartado para toda la misión y el dron retoma el giro.
       · "SÍ ES"  -> lock-on (TARGET_LOCKED).
  3. FIJADO (TARGET_LOCKED): la política aprendida (PPO) toma el control para mantener ESE ID en la
     vista. El tracker conserva el ID T_TRACKER s sin verlo; después hay que re-identificarlo por
     apariencia (ReID). Nunca cambia de objetivo por su cuenta: los demás son obstáculos.

  MISIÓN CUMPLIDA: mantener el rastreo T_RASTREO s desde el lock-on.
  MISIÓN FALLIDA:  perder al objetivo más de T_PERDIDA_MAX s seguidos, no fijarlo antes de
                   T_BUSQUEDA_MAX, chocar con alguien o con un obstáculo, o salir de la geocerca.
  Sobrevivir y esquivar es obligatorio, pero no basta: el objetivo es el rastreo.

ÁRBITRO DE SEGURIDAD: solo se esquiva ante una amenaza real (persona a < D_CRITICA, o a < D_AMENAZA
acercándose). La guiñada es independiente de la evasión y tiene rampa de aceleración (como
ATC_ACCEL_Y_MAX de ArduPilot). Un giro iniciado (búsqueda o pedido por la IA) no se corta ni se
invierte antes de T_GIRO_MIN, y ninguna detección de peatones lo interrumpe salvo el perímetro.

LADRÓN: táctico (se cubre detrás de los paneles del lado opuesto al dron, sigue la sombra del panel
si el dron se mueve, se asoma de vez en cuando, cambia de cubierta y a veces carga contra el dron) o,
en una fracción de las partidas de entrenamiento, la política aprendida por autojuego.
PEATONES: 0 a 2 en la zona, guionados (casi siempre deambulando). Todos existen desde el reinicio.

El dron NO ve el mundo: ve lo mismo que el dron real (cámara de 38.9°, YOLO con ruido y pérdidas,
LiDAR frontal, 100 ms de retraso) más lo que la Pixhawk sabe (posición GPS, rumbo, altura).

Convenciones: plano XY en metros, z hacia arriba. Rumbo psi antihorario desde +X. Ángulo de una
persona respecto a la nariz: positivo = a la DERECHA. Guiñada en °/s: positiva = hacia la derecha.
La fase 1 (vuelo del piloto con bloqueo frontal) está en mision.py.
"""
import numpy as np

# ----------------------------------------------------------------------------- sensores
DT = 0.1
HFOV = 38.9
VFOV = 29.7
ALTO_IMG = 480.0
ALTURA_PERSONA = 1.70
RADIO_PERSONA = 0.25

# ----------------------------------------------------------------------------- dron
N_CONFIRMACION = 3
DURACION_EVASION = 1.5
ENFRIAMIENTO = 1.0
VEL_LATERAL = 1.5
VEL_ASCENSO = 0.7
VEL_SUBIR_VER = 0.5            # "subir" sin amenaza: gana altura para ver por encima de los paneles
TAU_DRON = 0.35
ACC_MAX_DRON = 3.0
YAW_KP, YAW_MAX, YAW_ZONA = 2.5, 60.0, 2.0
YAW_GIRO_IA = 60.0             # giro pedido por la IA con el objetivo perdido
YAW_BUSQUEDA = 40.0            # giro de 360° del modo BUSCAR
YAW_ULTIMO = 30.0              # sin giro pedido: la nariz vuelve al último rumbo conocido del objetivo
ACEL_YAW = 180.0               # °/s²: rampa de la guiñada (rotación continua, sin saltos)
T_GIRO_MIN = 1.5               # un giro iniciado no se corta ni se invierte antes de esto
D_PERIMETRO = 2.0              # solo alguien a menos de esto pausa un giro de búsqueda
VEL_AVANCE = 1.5
DIST_MIN_SEGUIR = 8.0          # nunca se acerca al objetivo a menos de esto por su cuenta
DIST_PROTECCION_FRONTAL = 3.0  # el LiDAR bloquea el avance si hay algo a menos de esto al frente
D_CRITICA, D_AMENAZA, V_ACERCA = 3.0, 8.0, 0.4
Z_NOMINAL, Z_MIN, Z_MAX = 2.3, 1.8, 5.0
VEL_REGRESO_Z = 0.3

# ----------------------------------------------------------------------------- misión
BUSCAR, VERIFICAR, FIJADO = 0, 1, 2
T_OPERADOR = (1.0, 2.0)        # s que tarda el operador en responder SÍ / NO
T_VER_MIN = 0.5                # s de video que necesita el operador para decidir (aunque la persona se esconda después)
T_BUSQUEDA_MAX = 30.0          # sin lock-on en este tiempo: misión fallida (no encontrado)
T_PERDIDA_MAX = 6.0            # objetivo fijado fuera de vista más de esto, seguido: misión fallida
T_RASTREO = 30.0               # rastreo exigido desde el lock-on: misión cumplida
T_TRACKER = 1.0                # s que el tracker conserva el ID sin verlo
N_REID = 4                     # cuadros confirmando la apariencia para re-adquirirlo
RADIO_PATRULLA = 7.0           # reposición de la búsqueda alrededor del centro de la zona
T_REPOSICION = 6.0

# ----------------------------------------------------------------------------- personas
N_PERS = 4                     # 0 = ladrón, 1-2 = peatones de la zona, 3 = transeúnte de la ruta (misión)
VEL_CAMINAR, VEL_CORRER = 1.4, 3.3
TAU_PERSONA = 0.3
STAMINA_MAX = 2.0
ALCANCE_H = 1.0
ALCANCE_Z = 2.6
FRAC_LADRON_RL = 0.3           # partidas de entrenamiento con el ladrón aprendido (autojuego)
L_DEAMBULAR, L_CUBRIRSE, L_ESCONDIDO, L_ASOMARSE, L_ATACAR = 0, 1, 2, 3, 4
T_ESCONDIDO = (2.0, 6.0)
T_ASOMARSE = (1.5, 3.0)
T_ATAQUE = 3.0

# ----------------------------------------------------------------------------- escenario
N_PANELES = 2
ALTO_PANEL = 2.6
RADIO_DRON = 0.4
ARENA = 25.0
PASOS_EPISODIO = int((T_BUSQUEDA_MAX + T_RASTREO + 5.0) / DT)   # tope de seguridad

# ----------------------------------------------------------------------------- recompensas
R_COLISION = -10.0
R_CHOQUE_PANEL = -5.0
R_GEOCERCA = -5.0
R_PERDIDO = -5.0               # misión fallida por perder (o no encontrar) al objetivo
R_EXITO = 5.0                  # misión cumplida
R_MANIOBRA = {1: -0.15, 2: -0.15, 3: -0.30}
R_ALTURA = -0.01
R_VISTA = 0.03                 # por cada paso con el objetivo fijado a la vista
# Guía (reward shaping basado en potencial, Ng et al. 1999), solo en FIJADO: premia apuntar la nariz al
# objetivo y no alejarse de él. Usa su posición real SOLO para calificar; no es una entrada del dron.
GAMMA_GUIA = 0.99
K_GUIA_ANG, K_GUIA_DIST = 0.3, 0.03

CLASES = ["MANTENER", "EVADIR_IZQ", "EVADIR_DER", "DETENER_ASCENDER", "GIRAR_IZQ", "GIRAR_DER", "AVANZAR"]
OFFSETS_PERSONA = np.radians([0, 30, -30, 60, -60, 90, -90, 180])
N_ACC_PERSONA = len(OFFSETS_PERSONA) * 2 + 1
GUIONES = ["cruce", "directo", "quieto", "alejarse", "acercar_y_parar", "trotar_directo", "deambular"]
P_GUION = [0.15, 0.10, 0.10, 0.05, 0.05, 0.05, 0.50]

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
    t = np.clip(np.sum((p - a) * ab, -1) / np.maximum(np.sum(ab * ab, -1), 1e-9), 0, 1)
    c = a + t[..., None] * ab
    return np.hypot(p[..., 0] - c[..., 0], p[..., 1] - c[..., 1]), c


def resultado_de(info, i):
    """Código del final de la partida i."""
    for clave, nombre in (("choque_ladron", "alcanzado"), ("choque_peaton", "choque_peaton"), ("panel", "panel"),
                          ("fuera", "geocerca"), ("perdido", "perdido"), ("no_encontrado", "no_encontrado"),
                          ("exito", "cumplida")):
        if info[clave][i]:
            return nombre
    return "tiempo"


class EntornoDronPersona(object):

    def __init__(self, n, semilla=0):
        self.n = n
        self.rng = np.random.default_rng(semilla)
        z = lambda *s: np.zeros((n,) + s)
        zi = lambda *s: np.zeros((n,) + s, int)
        zb = lambda *s: np.zeros((n,) + s, bool)
        # dron
        self.dx, self.dy, self.dz, self.dvx, self.dvy, self.dvz, self.psi = z(), z(), z(), z(), z(), z(), z()
        self.yaw_dps = z()
        self.estado, self.t_estado, self.clase = zi(), z(), zi()
        self.ev_cand, self.ev_cand_n = zi(), zi()        # maniobra candidata y cuadros seguidos pidiéndola
        self.giro_mem, self.giro_t = z(), z()            # giro de la IA en curso (°/s) y desde cuándo
        self.amenaza, self.perimetro = zb(), zb()
        # máquina de estados de la misión
        self.modo, self.t_modo, self.t_fase2, self.t_fijado = zi(), z(), z(), z()
        self.busca_dir, self.giro_acum = np.ones(n), z()
        self.rep, self.rep_x, self.rep_y, self.rep_t = zb(), z(), z(), z()
        self.cand, self.t_resp, self.cand_sin_ver = np.full(n, -1), z(), z()
        self.cand_visto, self.cand_rumbo = z(), z()      # s que el operador lo ha visto y último rumbo donde se vio
        self.ignorado = zb(N_PERS)                       # IDs que el operador descartó ("NO ES")
        self.evento_op = zi()                            # 1 = el operador dijo SÍ, 2 = dijo NO (en ese paso)
        self.zona = np.tile([-18.0, 18.0, -18.0, 18.0], (n, 1))     # x0, x1, y0, y1 de la zona de búsqueda
        # objetivo
        self.lock, self.n_conf = zb(), zi()
        self.t_sin_ver, self.ult_rumbo, self.ult_dist = z(), z(), z()
        self.visto_alguna = zb()
        # personas
        self.px, self.py, self.pvx, self.pvy = z(N_PERS), z(N_PERS), z(N_PERS), z(N_PERS)
        self.activa = zb(N_PERS)
        self.guion = zi(N_PERS)
        self.g_dirx, self.g_diry, self.g_vel, self.g_parar = z(N_PERS), z(N_PERS), z(N_PERS), z(N_PERS)
        self.g_wx, self.g_wy = z(N_PERS), z(N_PERS)
        self.g_lim = np.tile([-15.0, 15.0, -15.0, 15.0], (n, N_PERS, 1))   # dónde deambula cada persona
        self.v_forzada = np.full((n, N_PERS, 2), np.nan)                  # velocidad impuesta (misión, fase 1)
        self.ids = zi(N_PERS)
        self.stamina = z()
        self.corriendo = zb()
        # ladrón táctico
        self.tactico = zb()
        self.l_modo, self.l_t, self.l_panel, self.l_alerta_t, self.l_expuesto = zi(), z(), zi(), z(), z()
        # paneles: extremos A y B y su altura (en la misión se agregan como segmentos los obstáculos del camino)
        self.pa, self.pb = z(N_PANELES, 2), z(N_PANELES, 2)
        self.ph = np.full((n, N_PANELES), ALTO_PANEL)
        # sensores
        self.vis_prev = zb(N_PERS)
        self.dist_prev, self.ang_prev, self.vac, self.vlat = z(N_PERS), z(N_PERS), z(N_PERS), z(N_PERS)
        self.obs_retraso = np.zeros((n, OBS_DRON))
        self.info_sensor = {}
        self.lidar = np.full(n, 20.0)
        self.t = zi()
        self.phi = z()
        self.reset(np.ones(n, bool))
        self._sensores()
        self.vis_prev[:] = False
        self.obs_retraso[:] = 0.0

    # ------------------------------------------------------------------ reinicio
    def reiniciar_mision(self, m):
        """Arranca la fase 2 (IA activada) en modo BUSCAR."""
        k = int(m.sum())
        if k == 0:
            return
        self.modo[m] = BUSCAR
        self.t_modo[m] = self.t_fase2[m] = self.t_fijado[m] = 0.0
        self.busca_dir[m] = self.rng.choice([-1.0, 1.0], k)
        self.giro_acum[m] = 0.0
        self.rep[m] = False
        self.rep_t[m] = 0.0
        self.cand[m] = -1
        self.t_resp[m] = self.cand_sin_ver[m] = self.cand_visto[m] = 0.0
        self.ignorado[m] = False
        self.evento_op[m] = 0
        self.lock[m] = False
        self.n_conf[m] = 0
        self.t_sin_ver[m] = 0.0
        self.giro_mem[m] = self.giro_t[m] = 0.0
        self.estado[m] = VIGILANDO
        self.t_estado[m] = 0.0
        self.ev_cand[m] = self.ev_cand_n[m] = 0
        self.t[m] = 0

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
        self.yaw_dps[m] = 0.0
        self.clase[m] = 0
        self.amenaza[m] = self.perimetro[m] = False
        self.zona[m] = [-18.0, 18.0, -18.0, 18.0]
        self.reiniciar_mision(m)
        self.ult_rumbo[m] = self.ult_dist[m] = 0.0
        self.visto_alguna[m] = False
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
        # ladrón: a 8-20 m (30% dentro del campo de visión); al principio no ha notado al dron
        u = r.random(k)
        rel = np.where(u < 0.3, r.uniform(-0.26, 0.26, k), r.uniform(-np.pi, np.pi, k))
        d0 = r.uniform(8, 20, k)
        b = self.psi[m] - rel
        self.px[m, 0] = np.clip(self.dx[m] + d0 * np.cos(b), -ARENA + 1, ARENA - 1)
        self.py[m, 0] = np.clip(self.dy[m] + d0 * np.sin(b), -ARENA + 1, ARENA - 1)
        self.activa[m, 0] = True
        self.stamina[m] = STAMINA_MAX
        self.corriendo[m] = False
        self.tactico[m] = r.random(k) >= FRAC_LADRON_RL
        self.l_modo[m] = L_DEAMBULAR
        self.l_alerta_t[m] = r.uniform(2.0, 8.0, k)
        self.l_t[m] = self.l_expuesto[m] = 0.0
        self.l_panel[m] = 0
        self.g_lim[m] = [-18.0, 18.0, -18.0, 18.0]
        self.g_wx[m, 0], self.g_wy[m, 0] = r.uniform(-15, 15, k), r.uniform(-15, 15, k)
        self.v_forzada[m] = np.nan
        # peatones de la zona: 0, 1 o 2 (el 3 es el transeúnte de la ruta, solo en la misión)
        npea = r.choice([0, 1, 2], size=k, p=[0.3, 0.4, 0.3])
        for a, i in enumerate(idx):
            for j in range(1, N_PERS):
                act = j <= npea[a]
                self.activa[i, j] = act
                if act:
                    self._preparar_peaton(i, j)
                else:
                    self.px[i, j] = self.py[i, j] = 999.0
            self.ids[i] = r.choice(np.arange(1, 60), N_PERS, replace=False)
        self.pvx[m] = self.pvy[m] = 0.0
        self.vis_prev[m] = False
        self.vac[m] = self.vlat[m] = 0.0
        self.obs_retraso[m] = 0.0
        self.phi[m] = self._potencial()[m]

    def _potencial(self):
        rx, ry = self.px[:, 0] - self.dx, self.py[:, 0] - self.dy
        err = np.abs(envolver(np.arctan2(ry, rx) - self.psi))
        phi = -K_GUIA_ANG * err / np.pi - K_GUIA_DIST * np.maximum(np.hypot(rx, ry) - 12.0, 0.0)
        return np.where(self.modo == FIJADO, phi, 0.0)

    def _preparar_peaton(self, i, j):
        r = self.rng
        g = int(r.choice(len(GUIONES), p=P_GUION))
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
        self.g_lim[i, j] = self.zona[i]
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
            x0, x1, y0, y1 = self.g_lim[i, j]
            self.g_wx[i, j], self.g_wy[i, j] = r.uniform(x0, x1), r.uniform(y0, y1)
            self.g_vel[i, j] = r.uniform(0.8, 1.4)
        self.px[i, j] = np.clip(self.px[i, j], -ARENA + 0.5, ARENA - 0.5)
        self.py[i, j] = np.clip(self.py[i, j], -ARENA + 0.5, ARENA - 0.5)

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
        ancho_deg = np.degrees(2 * np.arctan2(RADIO_PERSONA, np.maximum(dh, 0.2)))
        w_norm = np.minimum(ancho_deg / HFOV, 1.0)
        p_det = np.where(dh < 20, 0.97, np.clip(0.97 - (dh - 20) * 0.06, 0, 1))
        tapada = self._vista_bloqueada(self.px, self.py, np.full(self.px.shape, 1.0)) & self.activa
        visible = (self.activa & (np.abs(ang) < HFOV / 2 - 0.5) & (dh < 35) & (elev < 45 + VFOV / 2)
                   & ~tapada & (r.random((n, N_PERS)) < p_det))
        ang_m = ang + r.normal(0, 0.3, (n, N_PERS))
        h_m = h_norm * (1 + r.normal(0, 0.03, (n, N_PERS)))
        area = h_m * w_norm
        f_px = (ALTO_IMG / 2) / np.tan(np.radians(VFOV / 2))
        d_alto = ALTURA_PERSONA * f_px / np.maximum(h_m * ALTO_IMG, 1.0)
        # muy cerca la persona no cabe de alto en la imagen: la distancia sale del ancho de la caja
        d_ancho = RADIO_PERSONA / np.tan(np.radians(ancho_deg * (1 + r.normal(0, 0.05, (n, N_PERS))) / 2))
        d_bbox = np.where(h_norm >= 0.99, d_ancho, d_alto)
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
        # identidad: solo hay objetivo después del "SÍ ES" del operador; el tracker conserva el ID T_TRACKER
        # segundos y, pasado ese tiempo, hay que re-identificarlo por apariencia
        fij = self.modo == FIJADO
        v0_raw = visible[:, 0]
        d0 = dist[:, 0]
        p_id = np.where(d0 < 12, 0.85, np.where(d0 < 20, 0.6, 0.3))
        self.n_conf = np.where(v0_raw & fij, self.n_conf + (r.random(n) < p_id), 0)
        continuo = self.t_sin_ver <= T_TRACKER
        v0 = v0_raw & fij & (continuo | (self.n_conf >= N_REID))
        self.lock = v0
        self.t_sin_ver = np.where(v0 | ~fij, 0.0, self.t_sin_ver + DT)
        # memoria del objetivo: dónde lo vio confirmado por última vez
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
        """La política del dron solo decide con el objetivo fijado y fuera de una maniobra."""
        return (self.modo == FIJADO) & (self.estado == VIGILANDO)

    # ------------------------------------------------------------------ paso
    def step(self, acc_dron, acc_persona, auto_reset=True):
        n = self.n
        r = self.rng
        rew_d = np.zeros(n)
        o = self.obs_retraso
        s = self.info_sensor
        vis, dist_s, ang_s = s["visible"] & self.activa, s["dist"], s["ang"]
        self.t_modo += DT
        self.t_fase2 += DT

        # ================= máquina de estados de la misión =================
        # BUSCAR -> VERIFICAR: alguien detectado que el operador no haya descartado
        cands = vis & ~self.ignorado
        j_c = np.argmin(np.where(cands, dist_s, 99.0), 1)
        ini_ver = (self.modo == BUSCAR) & cands.any(1)
        self.cand = np.where(ini_ver, j_c, self.cand)
        self.t_resp = np.where(ini_ver, r.uniform(T_OPERADOR[0], T_OPERADOR[1], n), self.t_resp)
        self.cand_sin_ver = np.where(ini_ver, 0.0, self.cand_sin_ver)
        self.cand_visto = np.where(ini_ver, 0.0, self.cand_visto)
        self.modo = np.where(ini_ver, VERIFICAR, self.modo)
        self.t_modo = np.where(ini_ver, 0.0, self.t_modo)
        self.rep &= ~ini_ver
        # VERIFICAR: hover con la persona centrada; el operador responde con lo que alcanzó a ver (si la vio
        # al menos T_VER_MIN s, decide aunque después se esconda; si no, el dron retoma la búsqueda)
        ver = (self.modo == VERIFICAR) & ~ini_ver
        ci = np.clip(self.cand, 0, N_PERS - 1)
        c_vis = np.take_along_axis(vis, ci[:, None], 1)[:, 0]
        c_ang = np.take_along_axis(ang_s, ci[:, None], 1)[:, 0]
        self.cand_visto = np.where(ver & c_vis, self.cand_visto + DT, self.cand_visto)
        self.cand_rumbo = np.where((ver | ini_ver) & c_vis, envolver(self.psi - np.radians(c_ang)), self.cand_rumbo)
        self.cand_sin_ver = np.where(ver & ~c_vis, self.cand_sin_ver + DT, np.where(ver, 0.0, self.cand_sin_ver))
        suficiente = self.cand_visto >= T_VER_MIN
        responde = ver & suficiente & (self.t_modo >= self.t_resp)
        lock_on = responde & (self.cand == 0)
        descarta = responde & (self.cand != 0)
        se_fue = ver & ~suficiente & (self.cand_sin_ver > T_TRACKER)
        if descarta.any():
            k = np.where(descarta)[0]
            self.ignorado[k, self.cand[k]] = True
        self.evento_op = np.where(lock_on, 1, np.where(descarta, 2, 0))
        vuelve = descarta | se_fue
        self.modo = np.where(lock_on, FIJADO, np.where(vuelve, BUSCAR, self.modo))
        self.t_modo = np.where(lock_on | vuelve, 0.0, self.t_modo)
        self.cand = np.where(lock_on | vuelve, -1, self.cand)
        self.t_fijado = np.where(lock_on, 0.0, self.t_fijado)
        self.t_sin_ver = np.where(lock_on, self.cand_sin_ver, self.t_sin_ver)      # el tracker ya lleva ese tiempo sin verlo
        self.ult_rumbo = np.where(lock_on, self.cand_rumbo, self.ult_rumbo)
        self.visto_alguna |= lock_on
        self.giro_mem = np.where(lock_on, 0.0, self.giro_mem)
        busc, ver, fij = self.modo == BUSCAR, self.modo == VERIFICAR, self.modo == FIJADO
        decide = fij & (self.estado == VIGILANDO)
        ve = (o[:, 0] > 0.5) & fij

        # ================= árbitro: amenaza real y perímetro de colisión =================
        d_l, v_l, d_p, v_p = o[:, 1] * 20.0, o[:, 5] * 5.0, o[:, 13] * 20.0, o[:, 15] * 5.0
        self.amenaza = ((ve & ((d_l < D_CRITICA) | ((d_l < D_AMENAZA) & (v_l > V_ACERCA))))
                        | ((o[:, 12] > 0.5) & ((d_p < D_CRITICA) | ((d_p < D_AMENAZA) & (v_p > V_ACERCA)))))
        self.perimetro = (vis & (dist_s < D_PERIMETRO)).any(1)
        # la maniobra la elige la IA en FIJADO y una regla fija en BUSCAR/VERIFICAR
        regla = np.where(d_p < D_CRITICA, 3, np.where(o[:, 14] > 0, 1, 2))
        acc_ev = np.where(fij, acc_dron, regla)
        puede = self.estado == VIGILANDO
        nueva = puede & self.amenaza & (acc_ev >= 1) & (acc_ev <= 3)
        mismo = nueva & (acc_ev == self.ev_cand)
        self.ev_cand_n = np.where(mismo, self.ev_cand_n + 1, np.where(nueva, 1, 0))
        self.ev_cand = np.where(nueva, acc_ev, 0)
        inicia = puede & (self.ev_cand_n >= N_CONFIRMACION)
        for k, costo in R_MANIOBRA.items():
            rew_d += np.where(inicia & fij & (self.ev_cand == k), costo, 0.0)
        self.clase = np.where(inicia, self.ev_cand, self.clase)
        self.estado = np.where(inicia, EVADIENDO, self.estado)
        self.t_estado = np.where(inicia, 0.0, self.t_estado + DT)
        self.ev_cand = np.where(inicia, 0, self.ev_cand)
        self.ev_cand_n = np.where(inicia, 0, self.ev_cand_n)
        fin_eva = (self.estado == EVADIENDO) & (self.t_estado >= DURACION_EVASION)
        self.estado = np.where(fin_eva, ENFRIANDO, self.estado)
        self.t_estado = np.where(fin_eva, 0.0, self.t_estado)
        fin_enf = (self.estado == ENFRIANDO) & (self.t_estado >= ENFRIAMIENTO)
        self.estado = np.where(fin_enf, VIGILANDO, self.estado)

        # ================= consignas de velocidad (cuerpo: x adelante, y derecha) =================
        eva = self.estado == EVADIENDO
        lejos = ~ve | (o[:, 1] * 20.0 > DIST_MIN_SEGUIR)
        cerca_peaton = (o[:, 12] > 0.5) & (o[:, 13] * 20.0 < DIST_MIN_SEGUIR) & (np.abs(o[:, 14]) < 0.5)
        libre = self.lidar > DIST_PROTECCION_FRONTAL
        avanza_ia = decide & (acc_dron == 6) & lejos & libre & ~cerca_peaton
        # reposición de la búsqueda: apuntar al punto de patrulla y avanzar con la protección del LiDAR
        rep_err = envolver(np.arctan2(self.rep_y - self.dy, self.rep_x - self.dx) - self.psi)
        rep_d = np.hypot(self.rep_x - self.dx, self.rep_y - self.dy)
        alineado = np.abs(rep_err) < np.radians(10)
        self.rep_t = np.where(busc & self.rep, self.rep_t + DT, 0.0)
        fin_rep = busc & self.rep & ((rep_d < 1.0) | (self.rep_t > T_REPOSICION) | (alineado & ~libre))
        self.rep = self.rep & ~fin_rep & busc
        self.giro_acum = np.where(fin_rep, 0.0, self.giro_acum)
        avanza_rep = busc & self.rep & alineado & libre & ~self.perimetro
        avanza = (avanza_ia | avanza_rep) & ~eva
        vx_b = np.where(avanza, VEL_AVANCE, 0.0)
        vy_b = np.where(eva & (self.clase == 1), -VEL_LATERAL, np.where(eva & (self.clase == 2), VEL_LATERAL, 0.0))
        subir_ver = decide & (acc_dron == 3) & ~self.amenaza & (self.dz < Z_MAX)
        alguien_cerca = (vis & (dist_s < 6.0)).any(1)
        baja = (self.estado == VIGILANDO) & ~subir_ver & ~alguien_cerca & (self.dz > Z_NOMINAL + 0.05)
        vz_c = np.where(eva & (self.clase == 3), VEL_ASCENSO,
                        np.where(subir_ver, VEL_SUBIR_VER, np.where(baja, -VEL_REGRESO_Z, 0.0)))
        cps, sps = np.cos(self.psi), np.sin(self.psi)
        vx_c = vx_b * cps + vy_b * sps
        vy_c = vx_b * sps - vy_b * cps
        self.dvx += np.clip((vx_c - self.dvx) * DT / TAU_DRON, -ACC_MAX_DRON * DT, ACC_MAX_DRON * DT) + r.normal(0, 0.02, n)
        self.dvy += np.clip((vy_c - self.dvy) * DT / TAU_DRON, -ACC_MAX_DRON * DT, ACC_MAX_DRON * DT) + r.normal(0, 0.02, n)
        self.dvz += (vz_c - self.dvz) * DT / TAU_DRON
        self.dx += self.dvx * DT
        self.dy += self.dvy * DT
        self.dz = np.clip(self.dz + self.dvz * DT, Z_MIN, Z_MAX)

        # ================= guiñada (independiente de la evasión) =================
        ang_obs = o[:, 4] * HFOV / 2
        tasa_obj = np.clip(YAW_KP * ang_obs, -YAW_MAX, YAW_MAX)
        tasa_obj = np.where(np.abs(ang_obs) < YAW_ZONA, 0.0, tasa_obj)
        # giro pedido por la IA con el objetivo perdido: se compromete T_GIRO_MIN (sin vaivenes)
        self.giro_t += DT
        pide = decide & ~ve & ((acc_dron == 4) | (acc_dron == 5))
        sentido = np.where(acc_dron == 4, -YAW_GIRO_IA, YAW_GIRO_IA)
        comprometido = (self.giro_mem != 0) & (self.giro_t < T_GIRO_MIN)
        arranca = pide & ((self.giro_mem == 0) | (~comprometido & (np.sign(sentido) != np.sign(self.giro_mem))))
        self.giro_mem = np.where(arranca, sentido, self.giro_mem)
        self.giro_t = np.where(arranca, 0.0, self.giro_t)
        corta = decide & ~comprometido & ((acc_dron == 0) | (acc_dron == 6))
        self.giro_mem = np.where(corta | ve | ~fij, 0.0, self.giro_mem)
        rel_ult = np.degrees(envolver(self.ult_rumbo - self.psi))          # + = a la izquierda
        hacia_ult = np.where(np.abs(rel_ult) < YAW_ZONA, 0.0, np.clip(-1.5 * rel_ult, -YAW_ULTIMO, YAW_ULTIMO))
        yaw_fij = np.where(ve, tasa_obj, np.where(self.giro_mem != 0, self.giro_mem, hacia_ult))
        # BUSCAR: giro de 360° (o apuntar al punto de reposición); VERIFICAR: centrar al candidato
        yaw_rep = np.clip(-2.0 * np.degrees(rep_err), -YAW_BUSQUEDA, YAW_BUSQUEDA)
        yaw_bus = np.where(self.rep, yaw_rep, self.busca_dir * YAW_BUSQUEDA)
        ci = np.clip(self.cand, 0, N_PERS - 1)
        ang_c = np.take_along_axis(ang_s, ci[:, None], 1)[:, 0]
        c_vis = np.take_along_axis(vis, ci[:, None], 1)[:, 0] & ver
        rel_c = np.degrees(envolver(self.cand_rumbo - self.psi))
        yaw_ver = np.where(c_vis, np.where(np.abs(ang_c) > YAW_ZONA, np.clip(YAW_KP * ang_c, -YAW_MAX, YAW_MAX), 0.0),
                           np.where(np.abs(rel_c) > YAW_ZONA, np.clip(-1.5 * rel_c, -YAW_ULTIMO, YAW_ULTIMO), 0.0))
        yaw_cmd = np.where(fij, yaw_fij, np.where(ver, yaw_ver, yaw_bus))
        # perímetro de colisión: solo alguien a menos de D_PERIMETRO pausa un giro de búsqueda
        de_busqueda = (busc & ~self.rep) | (fij & (self.giro_mem != 0))
        yaw_cmd = np.where(de_busqueda & self.perimetro, 0.0, yaw_cmd)
        self.yaw_dps += np.clip(yaw_cmd - self.yaw_dps, -ACEL_YAW * DT, ACEL_YAW * DT)
        self.psi = envolver(self.psi - np.radians(self.yaw_dps) * DT)
        # vuelta completa sin candidatos: reposicionarse alrededor del centro de la zona
        self.giro_acum = np.where(busc & ~self.rep, self.giro_acum + np.abs(self.yaw_dps) * DT, self.giro_acum)
        vuelta = busc & ~self.rep & (self.giro_acum >= 360.0)
        if vuelta.any():
            cx, cy = self.zona[:, :2].mean(1), self.zona[:, 2:].mean(1)
            th = np.arctan2(self.dy - cy, self.dx - cx) + self.busca_dir * 2 * np.pi / 3
            rad = np.minimum(RADIO_PATRULLA, (self.zona[:, 1] - self.zona[:, 0]) / 2 - 2.0)
            self.rep_x = np.where(vuelta, np.clip(cx + rad * np.cos(th), -ARENA + 3, ARENA - 3), self.rep_x)
            self.rep_y = np.where(vuelta, np.clip(cy + rad * np.sin(th), -ARENA + 3, ARENA - 3), self.rep_y)
            self.rep |= vuelta
            self.rep_t = np.where(vuelta, 0.0, self.rep_t)
            self.giro_acum = np.where(vuelta, 0.0, self.giro_acum)

        # ================= personas =================
        self._mover_personas(acc_persona)

        # ================= eventos y fin de la misión =================
        d_all = np.hypot(self.px - self.dx[:, None], self.py - self.dy[:, None])
        toca = (d_all < ALCANCE_H) & self.activa & (self.dz < ALCANCE_Z)[:, None]
        choque = toca.any(1)
        lo_alcanza_ladron = toca[:, 0]
        choca_panel = np.zeros(n, bool)
        for j in range(self.pa.shape[1]):
            d, _ = dist_punto_segmento(np.stack([self.dx, self.dy], -1), self.pa[:, j], self.pb[:, j])
            choca_panel |= (d < RADIO_DRON) & (self.dz < self.ph[:, j] + 0.2)
        fuera = (np.abs(self.dx) > ARENA) | (np.abs(self.dy) > ARENA)
        self.t += 1
        self.t_fijado = np.where(fij, self.t_fijado + DT, self.t_fijado)
        perdido = fij & (self.t_sin_ver > T_PERDIDA_MAX)
        no_encontrado = ~fij & (self.t_fase2 >= T_BUSQUEDA_MAX)
        falla = choque | fuera | choca_panel | perdido | no_encontrado
        exito = fij & (self.t_fijado >= T_RASTREO) & ~falla
        tiempo = self.t >= PASOS_EPISODIO
        rew_d += np.where(choque, R_COLISION, 0.0) + np.where(fuera, R_GEOCERCA, 0.0) + np.where(choca_panel, R_CHOQUE_PANEL, 0.0)
        rew_d += np.where(perdido | no_encontrado, R_PERDIDO, 0.0) + np.where(exito, R_EXITO, 0.0)
        rew_d += np.where(fij, R_ALTURA * np.maximum(self.dz - 3.0, 0.0), 0.0)
        rew_p = np.where(lo_alcanza_ladron, 10.0, 0.0) + np.where(perdido | no_encontrado, 5.0, 0.0)
        done = falla | exito | tiempo
        phi_nuevo = self._potencial()
        rew_d += np.where(done, 0.0, GAMMA_GUIA * phi_nuevo - self.phi)
        self.phi = phi_nuevo

        self.obs_retraso = self._sensores()
        visto = self.info_sensor["lock"]
        rew_d += np.where(visto & ~choque, R_VISTA, 0.0)
        rew_p -= np.where(visto, R_VISTA, 0.0)
        info = dict(choque=choque, choque_ladron=lo_alcanza_ladron, choque_peaton=choque & ~lo_alcanza_ladron,
                    panel=choca_panel, fuera=fuera, tiempo=tiempo, perdido=perdido, no_encontrado=no_encontrado,
                    exito=exito, inicia=inicia, dist=d_all[:, 0], visto=visto.copy(), fijado=fij.copy(),
                    peatones=self.activa[:, 1:].sum(1))
        if auto_reset and done.any():
            self.reset(done)
        return rew_d, rew_p, done, info

    # ------------------------------------------------------------------ personas
    def mover_personas(self):
        """Solo para la misión (fase 1): mueve a las personas con el dron controlado desde afuera."""
        self._mover_personas(None)
        self.obs_retraso = self._sensores()

    def _mover_personas(self, acc_persona):
        vxp, vyp = self._velocidad_personas(acc_persona)
        self.pvx += (vxp - self.pvx) * DT / TAU_PERSONA
        self.pvy += (vyp - self.pvy) * DT / TAU_PERSONA
        self.px = np.where(self.activa, np.clip(self.px + self.pvx * DT, -ARENA, ARENA), self.px)
        self.py = np.where(self.activa, np.clip(self.py + self.pvy * DT, -ARENA, ARENA), self.py)
        # nadie atraviesa los paneles ni los obstáculos: se empuja fuera del muro
        pp = np.stack([self.px, self.py], -1)
        for j in range(self.pa.shape[1]):
            a = np.broadcast_to(self.pa[:, j][:, None, :], pp.shape)
            bb = np.broadcast_to(self.pb[:, j][:, None, :], pp.shape)
            d, c = dist_punto_segmento(pp, a, bb)
            dentro = d < 0.35
            nrm = (pp - c) / np.maximum(d, 1e-6)[..., None]
            pp = np.where(dentro[..., None], c + nrm * 0.35, pp)
        self.px, self.py = pp[..., 0].copy(), pp[..., 1].copy()

    def _velocidad_personas(self, acc_persona):
        n = self.n
        vxp, vyp = np.zeros((n, N_PERS)), np.zeros((n, N_PERS))
        # ladrón aprendido (autojuego)
        if acc_persona is None:
            acc_persona = np.full(n, N_ACC_PERSONA - 1)
        hx, hy = self.dx - self.px[:, 0], self.dy - self.py[:, 0]
        b = np.arctan2(hy, hx)
        quieto = acc_persona == N_ACC_PERSONA - 1
        corre_pide = (acc_persona >= len(OFFSETS_PERSONA)) & ~quieto
        off = OFFSETS_PERSONA[acc_persona % len(OFFSETS_PERSONA)]
        corre_rl = corre_pide & (self.stamina > 0.1)
        vel = np.where(quieto, 0.0, np.where(corre_rl, VEL_CORRER, VEL_CAMINAR))
        vx_rl, vy_rl = vel * np.cos(b + off), vel * np.sin(b + off)
        # ladrón táctico
        vx_t, vy_t, corre_t = self._ladron_tactico()
        vxp[:, 0] = np.where(self.tactico, vx_t, vx_rl)
        vyp[:, 0] = np.where(self.tactico, vy_t, vy_rl)
        self.corriendo = np.where(self.tactico, corre_t, corre_rl)
        self.stamina = np.clip(self.stamina + np.where(self.corriendo, -DT, 0.3 * DT), 0, STAMINA_MAX)
        # peatones (guion)
        gx, gy = self._velocidad_guion()
        vxp[:, 1:], vyp[:, 1:] = gx, gy
        # velocidades impuestas por la misión (el transeúnte que se cruza en la ruta)
        f = ~np.isnan(self.v_forzada[..., 0])
        vxp = np.where(f, np.nan_to_num(self.v_forzada[..., 0]), vxp)
        vyp = np.where(f, np.nan_to_num(self.v_forzada[..., 1]), vyp)
        return vxp, vyp

    def _ladron_tactico(self):
        """Ladrón táctico: se cubre detrás de un panel (del lado opuesto al dron) y sigue su sombra si el dron se
        mueve; de vez en cuando se asoma por un extremo, cambia de cubierta o carga contra el dron."""
        n, r = self.n, self.rng
        P = np.stack([self.px[:, 0], self.py[:, 0]], -1)
        D = np.stack([self.dx, self.dy], -1)
        H = np.zeros((n, N_PANELES, 2))           # escondite detrás de cada panel
        WP = np.zeros((n, N_PANELES, 2))          # siguiente punto de la ruta (rodea el panel si hace falta)
        AS = np.zeros((n, N_PANELES, 2))          # punto para asomarse
        for j in range(N_PANELES):
            A, B = self.pa[:, j], self.pb[:, j]
            M = (A + B) / 2
            L = np.maximum(np.hypot(B[:, 0] - A[:, 0], B[:, 1] - A[:, 1]), 1e-6)
            u = (B - A) / L[:, None]
            nrm = np.stack([-u[:, 1], u[:, 0]], -1)
            lado = np.sign(np.sum((D - M) * nrm, -1))
            lado = np.where(lado == 0, 1.0, lado)[:, None]
            H[:, j] = M - lado * nrm * 0.9
            EA, EB = A - u * 0.9, B + u * 0.9
            corta, _ = cruce_segmentos(P, H[:, j], A, B)
            ca = np.hypot(*(EA - P).T) + np.hypot(*(H[:, j] - EA).T)
            cb = np.hypot(*(EB - P).T) + np.hypot(*(H[:, j] - EB).T)
            WP[:, j] = np.where(corta[:, None], np.where((ca < cb)[:, None], EA, EB), H[:, j])
            cerca_a = (np.hypot(*(A - P).T) < np.hypot(*(B - P).T))[:, None]
            AS[:, j] = np.where(cerca_a, A - u * 1.6, B + u * 1.6) + lado * nrm * 0.8
        lim = ARENA - 1.0
        H, WP, AS = np.clip(H, -lim, lim), np.clip(WP, -lim, lim), np.clip(AS, -lim, lim)
        de = lambda X, j: np.take_along_axis(X, j[:, None, None], 1)[:, 0]
        dH = np.hypot(P[:, None, 0] - H[..., 0], P[:, None, 1] - H[..., 1])
        expuesto = self.info_sensor["visible"][:, 0] if self.info_sensor else np.zeros(n, bool)
        m = self.l_modo.copy()
        self.l_t -= DT
        self.l_alerta_t -= DT
        cerca = np.argmin(dH, 1)
        # nota al dron (lo oye a menos de 12 m) y, tras reaccionar, corre a la cubierta más cercana
        dd = np.hypot(self.dx - P[:, 0], self.dy - P[:, 1])
        oye = (m == L_DEAMBULAR) & (dd < 12.0) & (self.l_alerta_t > 1.5)
        self.l_alerta_t = np.where(oye, r.uniform(0.5, 1.5, n), self.l_alerta_t)
        despierta = (m == L_DEAMBULAR) & (self.l_alerta_t <= 0)
        self.l_panel = np.where(despierta, cerca, self.l_panel)
        m = np.where(despierta, L_CUBRIRSE, m)
        d_h = np.hypot(*(de(H, self.l_panel) - P).T)
        llega = (m == L_CUBRIRSE) & (d_h < 0.5)
        m = np.where(llega, L_ESCONDIDO, m)
        self.l_t = np.where(llega, r.uniform(T_ESCONDIDO[0], T_ESCONDIDO[1], n), self.l_t)
        # escondido: si lo ven más de 1 s cambia de cubierta; al acabar el tiempo se asoma, cambia o carga
        esc = m == L_ESCONDIDO
        self.l_expuesto = np.where(esc & expuesto, self.l_expuesto + DT, 0.0)
        cambia_vis = esc & (self.l_expuesto > 1.0)
        fin_esc = esc & (self.l_t <= 0) & ~cambia_vis
        u = r.random(n)
        puede_atacar = (dd < 10.0) & (self.dz < ALCANCE_Z + 0.3) & (self.stamina > 1.0)
        a_asoma = fin_esc & ((u < 0.5) | ((u >= 0.8) & ~puede_atacar))
        a_cambia = (fin_esc & (u >= 0.5) & (u < 0.8)) | cambia_vis
        a_ataca = fin_esc & (u >= 0.8) & puede_atacar
        m = np.where(a_asoma, L_ASOMARSE, np.where(a_cambia, L_CUBRIRSE, np.where(a_ataca, L_ATACAR, m)))
        otro = (self.l_panel + 1 + r.integers(0, max(N_PANELES - 1, 1), n)) % N_PANELES
        self.l_panel = np.where(a_cambia, otro, self.l_panel)
        self.l_t = np.where(a_asoma, r.uniform(T_ASOMARSE[0], T_ASOMARSE[1], n), np.where(a_ataca, T_ATAQUE, self.l_t))
        # asomarse y atacar terminan: vuelve a cubrirse
        vuelve = (((m == L_ASOMARSE) | (m == L_ATACAR)) & (self.l_t <= 0)) | ((m == L_ATACAR) & (self.stamina < 0.2))
        vuelve &= ~(a_asoma | a_ataca)
        self.l_panel = np.where(vuelve & (m == L_ATACAR), cerca, self.l_panel)
        m = np.where(vuelve, L_CUBRIRSE, m)
        self.l_modo = m
        # hacia dónde camina
        deamb = np.stack([self.g_wx[:, 0], self.g_wy[:, 0]], -1)
        T = np.where((m == L_DEAMBULAR)[:, None], deamb,
                     np.where(((m == L_CUBRIRSE) | (m == L_ESCONDIDO))[:, None], de(WP, self.l_panel),
                              np.where((m == L_ASOMARSE)[:, None], de(AS, self.l_panel), D)))
        vec = T - P
        dist = np.maximum(np.hypot(vec[:, 0], vec[:, 1]), 1e-6)
        d_h = np.hypot(*(de(H, self.l_panel) - P).T)
        quieto = ((m == L_ESCONDIDO) | (m == L_ASOMARSE)) & (dist < 0.35)
        corre = (((m == L_CUBRIRSE) & expuesto) | (m == L_ATACAR) | ((m == L_ESCONDIDO) & (d_h > 2.0))) & (self.stamina > 0.1)
        vel = np.where(quieto, 0.0, np.where(corre, VEL_CORRER, np.where(m == L_DEAMBULAR, 0.9, 1.2)))
        vel = np.minimum(vel, 2.0 * dist)
        # deambulando: nuevo destino al llegar
        llego = (m == L_DEAMBULAR) & (dist < 1.0)
        if llego.any():
            lim0 = self.g_lim[:, 0]
            self.g_wx[:, 0] = np.where(llego, lim0[:, 0] + r.random(n) * (lim0[:, 1] - lim0[:, 0]), self.g_wx[:, 0])
            self.g_wy[:, 0] = np.where(llego, lim0[:, 2] + r.random(n) * (lim0[:, 3] - lim0[:, 2]), self.g_wy[:, 0])
        return vel * vec[:, 0] / dist, vel * vec[:, 1] / dist, corre

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
                lim = self.g_lim[:, 1:]
                nx = lim[..., 0] + self.rng.random(llego.shape) * (lim[..., 1] - lim[..., 0])
                ny = lim[..., 2] + self.rng.random(llego.shape) * (lim[..., 3] - lim[..., 2])
                self.g_wx[:, 1:] = np.where(llego, nx, self.g_wx[:, 1:])
                self.g_wy[:, 1:] = np.where(llego, ny, self.g_wy[:, 1:])
            vx = np.where(dm, wx / wd * self.g_vel[:, 1:], vx)
            vy = np.where(dm, wy / wd * self.g_vel[:, 1:], vy)
        act = self.activa[:, 1:]
        return np.where(act, vx, 0.0), np.where(act, vy, 0.0)

    # ------------------------------------------------------------------ para el visor
    def _estado_tracker(self, i):
        """0 búsqueda · 5 verificando (operador) · 1 objetivo fijado · 2 memoria · 3 perdido · 4 re-identificando."""
        if self.modo[i] == BUSCAR:
            return 0
        if self.modo[i] == VERIFICAR:
            return 5
        if self.lock[i]:
            return 1
        if self.info_sensor["visible"][i, 0]:
            return 4
        return 2 if self.t_sin_ver[i] <= T_TRACKER else 3

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
                         "ign": bool(self.ignorado[i, j]), "cand": bool(self.modo[i] == VERIFICAR and self.cand[i] == j),
                         "run": bool(self.corriendo[i]) if j == 0 else bool(self.g_vel[i, j] > 2.0 and np.isnan(self.v_forzada[i, j, 0]))})
        lad = pers[0]
        return {
            "d": [round(float(self.dx[i]), 3), round(float(self.dy[i]), 3), round(float(self.dz[i]), 3), round(float(self.psi[i]), 4)],
            "dv": [round(float(self.dvx[i]), 2), round(float(self.dvy[i]), 2)],
            "pers": pers, "p": lad["p"], "pv": lad["v"], "run": lad["run"],
            "est": int(self.estado[i]), "cl": int(self.clase[i]) if self.estado[i] == EVADIENDO else 0,
            "vis": bool(s["lock"][i]), "las": bool(s["laser"][i, 0] and s["lock"][i]),
            "dm": round(float(s["dist"][i, 0]), 2), "dh": round(float(s["dh"][i, 0]), 2),
            "ang": round(float(s["ang"][i, 0]), 1), "vac": round(float(self.vac[i, 0]), 2),
            "yaw": round(float(self.yaw_dps[i]), 1), "lid": round(float(self.lidar[i]), 2), "fase": 2,
            "modo": int(self.modo[i]), "trk": self._estado_tracker(i), "amz": bool(self.amenaza[i]),
            "per": bool(self.perimetro[i]), "giro": round(float(self.giro_mem[i]), 1), "rep": bool(self.rep[i]),
            "op": int(self.evento_op[i]), "t2": round(float(self.t_fase2[i]), 1), "tf": round(float(self.t_fijado[i]), 1),
            "tsv": round(float(self.t_sin_ver[i]), 1), "lm": int(self.l_modo[i]), "tac": bool(self.tactico[i]),
        }

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
