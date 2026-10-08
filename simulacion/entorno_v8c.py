# -*- coding: utf-8 -*-
"""
Fase 2 de la misión (IA activada en la zona), vectorizada en NumPy · versión 8.

EL JUEGO ES EL DRON CONTRA EL LADRÓN (como el escondite de OpenAI, Baker et al. 2020), con el flujo
de trabajo real entre el dron y el operador policial (humano en el lazo):

  1. BUSCAR (SEARCH): al entrar a la zona el dron gira 360° sobre su eje buscando personas con YOLO y,
     a la vez, MAPEA LOS OBSTÁCULOS CON EL LIDAR (cada impacto del rayo frontal se guarda como un punto;
     los puntos se agrupan en segmentos = paneles). Si la vuelta no encuentra a nadie, hace BÚSQUEDA
     ACTIVA: vuela (por encima de los paneles) a un punto de separación en diagonal a la esquina de cada
     panel detectado, mira hacia su parte trasera y barre 360°, uno por uno. No usa el plano del simulador.
     Los giros son continuos: solo los pausa alguien que rompa el perímetro de colisión (D_PERIMETRO).
  2. VERIFICAR: al detectar a una persona no descartada, el dron queda en hover, la centra y lanza una
     alerta en la estación de tierra. El operador confirma con un CLIC sobre la persona:
       · clic sobre el sospechoso -> lock-on (TARGET_LOCKED).
       · sin clic en T_ESPERA_CLIC -> ese ID queda descartado y la búsqueda sigue donde iba.
  3. FIJADO (TARGET_LOCKED): la política aprendida (PPO) toma el control para mantener ESE ID en la
     vista. Seguimiento horizontal con el yaw (con banda muerta: no corrige mientras el objetivo esté en
     el 20% central del FOV) y vertical con el pitch del gimbal (el dron no sube ni baja para centrarlo).
  4. PROTOCOLO DE PÉRDIDA (determinista): si el tracker suelta el ID (más de T_TRACKER sin verlo),
     INVESTIGAR = si se perdió junto a un panel, FLANQUEO PROFUNDO: rodea la esquina por la que desapareció (sin
     rozarla) y queda DETRÁS del plano del muro, en la zona que estaba oculta; en campo abierto, se detiene
     D_STANDOFF antes de su última posición -> ASOMO (mira hacia allí y hace un paneo dirigido
     de 360° que empieza hacia el interior de la zona oculta, por donde se fue el ladrón) -> VENTAJA DE ALTURA (último recurso) (en vez de rodear el panel, sube rápido a Z_TACTICO
     sobre la zona de pérdida y barre 360° con la cámara inclinada hacia abajo: desde ahí un panel de 2.6 m
     ya no tapa a nadie). Si en cualquier paso YOLO reconfirma el ID (ReID), la IA retoma.
     Al sobrevolar un panel detectado, el gimbal baja a nadir (-85°) para ver su base y luego vuelve.

  5. INTERCEPCIÓN PREDICTIVA: si el objetivo sale del cuadro corriendo (por ejemplo, pasa por debajo del dron), antes
     del protocolo el dron sigue su trayectoria extrapolada T_PREDICCION s con la nariz y el gimbal hacia el punto
     predicho. El protocolo de pérdida usa su último vector de movimiento: el punto de separación queda en la
     esquina por la que escapó y el paneo empieza hacia ese lado.

  PERSECUCIÓN: navegación predictiva (apunta el empuje al punto donde estará el ladrón dentro de T_LEAD s, no a su
  posición actual) con distancia óptima de seguimiento de 3.5 a 5 m (si está a menos de 3.5 m frena; a menos de
  2.5 m retrocede). El dron (VEL_PERSEGUIR) es más rápido en línea recta que el ladrón (VEL_CORRER).
  CINEMÁTICA: las personas tienen aceleración y frenado limitados y no giran en seco: un giro de más de 45° las
  obliga a frenar. El dron se inclina al acelerar (cabeceo = atan(a/g)); el gimbal tarda TAU_ESTAB en compensarlo,
  así que acelerar y frenar a golpes mueve la imagen y puede sacar al objetivo del encuadre.

  LIDAR: un solo rayo rígidamente acoplado al eje de la cámara (yaw del dron + pitch del gimbal). Mide la distancia
  a lo que esté en el centro de la imagen: un panel, una persona o el suelo. Es obstáculo si pega antes de donde
  debería tocar el suelo (la Jetson lo calcula con la altura y el pitch). Si la cámara mira abajo, no hay protección
  frontal. El mapa de paneles se arma solo con impactos de obstáculo que no sean personas.

  MISIÓN CUMPLIDA: mantener el rastreo T_RASTREO s desde el lock-on (con las recuperaciones que hagan falta).
  MISIÓN FALLIDA:  agotar el protocolo de pérdida sin recuperarlo, no fijar al sospechoso antes de
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
TAU_DRON = 0.35
ACC_MAX_DRON = 4.0
TAU_ACTITUD = 0.15             # s que tarda el chasis en inclinarse a la actitud que pide la aceleración
TAU_ESTAB = 0.15               # s que tarda el gimbal en compensar un cambio de cabeceo del chasis
GIMBAL_REL_MIN, GIMBAL_REL_MAX = -100.0, 25.0   # límites mecánicos del gimbal respecto al chasis
G = 9.81
YAW_KP, YAW_MAX, YAW_ZONA = 2.0, 60.0, 2.0
BANDA_MUERTA = 0.10 * HFOV     # ±3.9°: el 20% central del FOV horizontal; ahí el yaw no corrige
BANDA_RECENTRA = 0.04 * HFOV   # si corrige, recentra hasta ±1.6° y se detiene (histéresis, sin vaivén)
YAW_GIRO_IA = 60.0             # giro pedido por la IA con el objetivo perdido
YAW_BUSQUEDA = 40.0            # giro de 360° del modo BUSCAR
YAW_ULTIMO = 30.0              # sin giro pedido: la nariz vuelve al último rumbo conocido del objetivo
ACEL_YAW = 180.0               # °/s²: rampa de la guiñada (rotación continua, sin saltos)
T_GIRO_MIN = 1.5               # un giro iniciado no se corta ni se invierte antes de esto
D_PERIMETRO = 2.0              # solo alguien a menos de esto pausa un giro de búsqueda
VEL_AVANCE = 1.5               # avance a ciegas (objetivo fuera de vista)
VEL_PERSEGUIR = 4.5            # persecución: más rápido que el ladrón corriendo en línea recta
T_LEAD = 1.0                   # navegación predictiva: apunta adonde estará el ladrón dentro de este tiempo
K_RANGO = 1.2
R_OPT_MIN, R_OPT_MAX = 3.5, 5.0  # distancia óptima de seguimiento (el ladrón queda bien encuadrado)
R_RETROCEDE = 2.5              # más cerca que esto, retrocede despacio para no sobrevolarlo
D_PEATON_FRENTE = 4.0          # no persigue si hay un peatón cerca al frente
DIST_PROTECCION_FRONTAL = 3.0  # el LiDAR bloquea el avance si hay algo a menos de esto al frente
D_CRITICA, D_AMENAZA, V_ACERCA = 3.0, 8.0, 0.4
Z_NOMINAL, Z_MIN, Z_MAX = 2.3, 1.8, 7.0
# gimbal (pitch de la cámara; BaseCam por PWM desde AUX1, ±45°): hace el seguimiento VERTICAL
GIMBAL_MIN, GIMBAL_MAX = -90.0, 10.0     # en el dron real hay que ampliar el mapeo PWM a ±90° (hoy ±45°)
GIMBAL_NADIR = -85.0           # al sobrevolar un panel: la cámara mira hacia abajo, a la base del muro
GIMBAL_TACTICO = -65.0         # barrido desde la altura táctica: cubre de ~1 a ~4.6 m alrededor del punto
D_NADIR = 2.5                  # a menos de esto (horizontal) de un panel detectado, sobrevolando, se mira en nadir
GIMBAL_VEL, GIMBAL_KP = 90.0, 4.0
GIMBAL_BANDA = 0.10 * VFOV     # banda muerta vertical (20% central del FOV vertical)
GIMBAL_RECENTRA = 0.04 * VFOV
D_REPOSO = 8.0                 # sin nadie a quien seguir, la cámara mira al suelo a esta distancia
VEL_REGRESO_Z = 0.3

# ----------------------------------------------------------------------------- misión
BUSCAR, VERIFICAR, FIJADO, INVESTIGAR, ASOMO, VENTAJA_ALTURA, PREDECIR = 0, 1, 2, 3, 4, 5, 6
B_GIRO, B_TRANSITO, B_INSPECCION = 0, 1, 2      # subfases de BUSCAR (giro, vuelo a un panel, barrido detrás de él)
T_OPERADOR = (1.0, 2.0)        # s que tarda el operador en responder SÍ / NO
T_VER_MIN = 0.5                # s de video que necesita el operador para decidir (aunque la persona se esconda después)
T_ESPERA_CLIC = 3.0            # sin clic del operador en este tiempo, ese ID queda descartado
T_BUSQUEDA_MAX = 60.0          # sin lock-on en este tiempo: misión fallida (no encontrado)
T_RASTREO = 30.0               # rastreo exigido desde el lock-on: misión cumplida
T_TRACKER = 1.0                # s que el tracker conserva el ID sin verlo
N_REID = 4                     # cuadros confirmando la apariencia para re-adquirirlo
Z_TRANSITO = 3.2               # vuelos de inspección e investigación por encima de los paneles (2.6 m)
Z_TACTICO = 5.5                # ventaja de altura (último recurso): desde aquí un panel de 2.6 m tapa mucho menos
VEL_SUBIDA_RAPIDA = 2.5        # m/s de subida (WPNAV_SPEED_UP por defecto de ArduPilot)
# intercepción predictiva
T_PRED_INI = 0.3               # s sin verlo para empezar a predecir (si iba rápido)
V_PRED_MIN = 0.8               # m/s: más lento que esto no se extrapola (se escondió caminando)
T_PREDICCION = 2.0             # s siguiendo la trayectoria extrapolada
VEL_PRED_MAX = 4.0
YAW_MAX_PRED = 120.0           # °/s de guiñada para re-encuadrarlo
D_APROX = 10.0                 # al fijarlo, si está más lejos que esto, el dron va hacia él de inmediato
YAW_DIRECCIONAL = 60.0         # °/s del paneo dirigido del asomo
# árbitro: esquive reflejo cuando alguien corre hacia el dron
D_REFLEJO = 5.0
V_ATAQUE = 1.5                 # m/s de acercamiento que se considera un ataque
VEL_ESQUIVE_Z = 1.2
TASA_ATAQUE = 0.06             # ataques espontáneos del ladrón por segundo (con el dron cerca y al alcance)
LIDAR_MAX = 20.0
VEL_INVESTIGA = 3.0
T_INVESTIGA_MAX = 12.0
D_LLEGADA = 1.2
D_STANDOFF = 2.5               # separación táctica: no volar a la coordenada exacta ni a la esquina del panel
T_MIRA = 2.0                   # (sin uso en el flanqueo: al llegar detrás del muro rota de inmediato)
# flanqueo profundo: rodear la esquina y quedar detrás del plano del muro
R_ESQUINA = 1.3                # la ruta pasa a esta distancia de la esquina (radio del dron + margen)
MARGEN_ESQUINA = 0.5           # ningún tramo puede pasar a menos de RADIO_DRON + esto de un panel detectado
D_FLANCO = 1.8                 # el punto final queda esto detrás del plano del muro (en la zona que estaba oculta)
OFFSET_EXT = 0.5               # el LiDAR ve el panel un poco más corto: sus extremos se alargan esto
D_LLEGADA_PASO = 0.8           # al pasar a esta distancia de un punto intermedio, sigue con el siguiente
DIST_PROTECCION_VUELO = 1.0    # en el flanqueo el LiDAR solo frena el avance si hay algo a menos de esto
Z_FLANCO = 3.0                 # el flanqueo se vuela fuera del alcance del ladrón (2.6 m) y justo sobre los paneles (2.6 m):
                               # a 2.3 m, al rodear la esquina pasaba junto al escondite y lo tumbaban (42% en las pruebas)
# mapa de obstáculos con el LiDAR (rayo frontal): impactos guardados y su agrupación en paneles
N_LIDAR = 128
D_CLUSTER = 1.0
LARGO_MIN_PANEL = 1.0
K_DET = 4
# guarda del mapa: con el LiDAR solo al frente, en la persecución o la predicción el dron puede moverse hacia un panel
# que no está mirando. Los impactos guardados funcionan como un muro virtual: la velocidad de acercamiento a cada
# punto se limita a la que permite frenar antes de R_PARADA (v <= sqrt(2·A_GUARDA·(d - R_PARADA)))
R_GUARDA = 3.5                 # solo cuentan los impactos a menos de esto
R_PARADA = 0.75                # distancia (centro del dron al panel) donde la velocidad de acercamiento llega a 0
A_GUARDA = 2.4                 # desaceleración de diseño (60% de ACC_MAX_DRON, por el retardo del autopiloto)
R_INSP_HECHO = 2.0             # un panel cuyo centro está a menos de esto de uno ya revisado cuenta como revisado

# ----------------------------------------------------------------------------- personas
N_PERS = 4                     # 0 = ladrón, 1-2 = peatones de la zona, 3 = transeúnte de la ruta (misión)
VEL_CAMINAR, VEL_CORRER = 1.4, 3.3
# cinemática humana: aceleración y frenado limitados; giros con aceleración lateral limitada; un giro de más de
# 45° obliga a frenar hasta V_GIRO_PERSONA (como una persona real que cambia de dirección)
A_ACEL_PERSONA, A_FRENO_PERSONA, A_LAT_PERSONA = 2.5, 5.0, 5.0
OMEGA_PERSONA = 8.0            # rad/s de giro máximo casi detenido
V_GIRO_PERSONA = 1.5
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
PASOS_EPISODIO = int((T_BUSQUEDA_MAX + T_RASTREO + 50.0) / DT)   # tope de seguridad

# ----------------------------------------------------------------------------- recompensas
R_COLISION = -10.0
R_CHOQUE_PANEL = -5.0
R_GEOCERCA = -5.0
R_PERDIDO = -5.0               # misión fallida: protocolo agotado (o nunca se fijó al sospechoso)
R_PIERDE = -1.0                # el tracker suelta el ID: empieza el protocolo de pérdida
R_EXITO = 5.0                  # misión cumplida
R_MANIOBRA = {1: -0.15, 2: -0.15, 3: -0.30}
R_VISTA = 0.03                 # por cada paso con el objetivo fijado a la vista
R_RANGO = 0.02                 # además, si está en la distancia óptima (3.5 a 5 m)
R_MUY_CERCA = -0.02            # y castigo si está a menos de 3 m (se sale del encuadre o lo sobrevuela)
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
        self.yaw_corrige = zb()                          # banda muerta del yaw con histéresis
        self.gimbal = np.full(n, -10.0)                  # pitch del gimbal (°, negativo = hacia abajo)
        self.gmb_corrige, self.gmb_sat_arriba = zb(), zb()
        # máquina de estados de la misión
        self.modo, self.t_modo, self.t_fase2, self.t_fijado = zi(), z(), z(), z()
        self.busca_dir, self.giro_acum = np.ones(n), z()
        self.bfase, self.panel_obj = zi(), zi()          # búsqueda activa tras los paneles
        self.wp_x, self.wp_y, self.t_vuelo, self.t_bloqueo = z(), z(), z(), z()
        self.mira_x, self.mira_y, self.obj_mx, self.obj_my = z(), z(), z(), z()   # a dónde mirar y panel en revisión
        self.insp_x, self.insp_y, self.insp_n = z(8), z(8), zi()                  # centros de paneles ya revisados
        self.inv_x, self.inv_y, self.zc_x, self.zc_y = z(), z(), z(), z()         # punto de separación y zona de pérdida
        self.nadir = zb()
        self.ruta, self.ruta_n, self.ruta_i = z(3, 2), zi(), zi()          # ruta del flanqueo (hasta 3 puntos)
        self.rx, self.ry, self.int_dx, self.int_dy = z(), z(), z(), z()     # punto actual y dirección al interior oculto
        self.vuelo_alto, self.flanco = zb(), zb()
        self.tvx, self.tvy, self.esc_vx, self.esc_vy = z(), z(), z(), z()       # velocidad estimada del objetivo y de escape
        self.pred_x0, self.pred_y0, self.pred_vx, self.pred_vy = z(), z(), z(), z()
        self.aso_gira = zb()
        self.lat_esq, self.reflejo, self.guarda = z(), zb(), zb()
        self.p_rumbo = z(N_PERS)                         # hacia dónde mira y camina cada persona
        self.chasis_pitch, self.chasis_roll, self.err_gmb = z(), z(), z()
        self.cam_pitch = np.full(n, -10.0)               # pitch real de la cámara (gimbal + error de estabilización)
        self.lid_t, self.lid_hx, self.lid_hy, self.lid_hz, self.lid_tipo = np.full(n, LIDAR_MAX), z(), z(), z(), zi()
        # mapa de obstáculos con el LiDAR: impactos guardados (en el plano) y segmentos detectados
        self.lid_px, self.lid_py, self.lid_ok, self.lid_i = z(N_LIDAR), z(N_LIDAR), zb(N_LIDAR), zi()
        self.lid_ult_psi, self.lid_ult_x, self.lid_ult_y = z(), np.full(n, 1e9), np.full(n, 1e9)
        self.det_a, self.det_b, self.det_n = z(K_DET, 2), z(K_DET, 2), zi()
        self.cand, self.t_resp, self.cand_sin_ver = np.full(n, -1), z(), z()
        self.cand_visto, self.cand_rumbo = z(), z()      # s que el operador lo ha visto y último rumbo donde se vio
        self.ignorado = zb(N_PERS)                       # IDs que el operador descartó ("NO ES")
        self.evento_op = zi()                            # 1 = el operador dijo SÍ, 2 = dijo NO (en ese paso)
        self.zona = np.tile([-18.0, 18.0, -18.0, 18.0], (n, 1))     # x0, x1, y0, y1 de la zona de búsqueda
        # objetivo
        self.lock, self.n_conf = zb(), zi()
        self.t_sin_ver, self.ult_rumbo, self.ult_dist = z(), z(), z()
        self.ult_x, self.ult_y = z(), z()                # última posición (X, Y) conocida del objetivo
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
        self.bfase[m] = B_GIRO
        self.panel_obj[m] = 0
        self.insp_n[m] = 0
        self.nadir[m] = False
        self.ruta_n[m] = self.ruta_i[m] = 0
        self.vuelo_alto[m] = self.flanco[m] = False
        self.tvx[m] = self.tvy[m] = self.esc_vx[m] = self.esc_vy[m] = 0.0
        self.aso_gira[m] = False
        self.lat_esq[m] = 0.0
        self.reflejo[m] = False
        self.t_vuelo[m] = self.t_bloqueo[m] = 0.0
        self.yaw_corrige[m] = self.gmb_corrige[m] = self.gmb_sat_arriba[m] = False
        self.ult_x[m] = self.ult_y[m] = 0.0
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
        self.chasis_pitch[m] = self.chasis_roll[m] = self.err_gmb[m] = 0.0
        self.cam_pitch[m] = -10.0
        self.gimbal[m] = -10.0
        self.clase[m] = 0
        self.amenaza[m] = self.perimetro[m] = False
        self.zona[m] = [-18.0, 18.0, -18.0, 18.0]
        self.reiniciar_mision(m)
        self.ult_rumbo[m] = self.ult_dist[m] = 0.0
        self.lid_ok[m] = False
        self.lid_i[m] = 0
        self.lid_ult_x[m] = self.lid_ult_y[m] = 1e9
        self.det_n[m] = 0
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
        self.p_rumbo[m] = r.uniform(-np.pi, np.pi, (k, N_PERS))
        self.vis_prev[m] = False
        self.vac[m] = self.vlat[m] = 0.0
        self.obs_retraso[m] = 0.0
        self.phi[m] = self._potencial()[m]

    def _potencial(self):
        rx, ry = self.px[:, 0] - self.dx, self.py[:, 0] - self.dy
        err = np.abs(envolver(np.arctan2(ry, rx) - self.psi))
        phi = -K_GUIA_ANG * err / np.pi - K_GUIA_DIST * np.maximum(np.hypot(rx, ry) - R_OPT_MAX, 0.0)
        return np.where(self.modo >= FIJADO, phi, 0.0)

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

    def _lidar_camara(self):
        """Un rayo por el eje óptico (yaw del dron + pitch del gimbal) hasta lo primero que toca: suelo, panel u
        obstáculo (planos verticales de altura ph) o persona (cilindro). Devuelve distancia, punto y tipo (1 suelo,
        2 obstáculo, 3 persona) e índice de la persona tocada."""
        n = self.n
        th = np.radians(self.cam_pitch)
        ct, st = np.cos(th), np.sin(th)
        cps, sps = np.cos(self.psi), np.sin(self.psi)
        t = np.full(n, LIDAR_MAX)
        tipo = np.zeros(n, int)
        jp = np.full(n, -1)
        tg = np.where(st < -1e-3, self.dz / np.maximum(-st, 1e-3), np.inf)
        g = tg < t
        t, tipo = np.where(g, tg, t), np.where(g, 1, tipo)
        ch = np.maximum(ct, 1e-3)
        p = np.stack([self.dx, self.dy], -1)
        q = p + LIDAR_MAX * np.stack([cps, sps], -1)
        for j in range(self.pa.shape[1]):
            corta, u = cruce_segmentos(p, q, self.pa[:, j], self.pb[:, j])
            tj = u * LIDAR_MAX / ch
            zj = self.dz + tj * st
            hit = corta & (ct > 1e-3) & (zj >= 0) & (zj <= self.ph[:, j]) & (tj < t)
            t, tipo = np.where(hit, tj, t), np.where(hit, 2, tipo)
        rx, ry = self.px - self.dx[:, None], self.py - self.dy[:, None]
        s_p = rx * cps[:, None] + ry * sps[:, None]
        perp = np.abs(-rx * sps[:, None] + ry * cps[:, None])
        tp = s_p / ch[:, None]
        zp = self.dz[:, None] + tp * st[:, None]
        hitp = self.activa & (s_p > 0.2) & (perp < RADIO_PERSONA) & (zp >= 0) & (zp <= ALTURA_PERSONA) & (tp < t[:, None])
        if hitp.any():
            tpm = np.where(hitp, tp, np.inf)
            jj = np.argmin(tpm, 1)
            tmin = tpm[np.arange(n), jj]
            hp = np.isfinite(tmin)
            t, tipo, jp = np.where(hp, tmin, t), np.where(hp, 3, tipo), np.where(hp, jj, -1)
        return t, tipo, jp, self.dx + t * ct * cps, self.dy + t * ct * sps, self.dz + t * st

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
        a_c = np.degrees(np.arctan2(dz - 0.9, dh))       # ángulo bajo el horizonte del centro de la persona
        # pirámide de visión de la cámara (rumbo del dron + pitch del gimbal): se ve a la persona si su torso o su
        # cabeza caen dentro. Vale también mirando en nadir, donde el rumbo ya no dice nada.
        th = np.radians(self.cam_pitch)[:, None]
        cps, sps, ct, st = np.cos(self.psi)[:, None], np.sin(self.psi)[:, None], np.cos(th), np.sin(th)

        def en_camara(h):
            vz = h - dz
            xf = rx * cps * ct + ry * sps * ct + vz * st
            xr = rx * sps - ry * cps
            xu = -rx * cps * st - ry * sps * st + vz * ct
            return ((xf > 0.3) & (np.abs(xr) < xf * np.tan(np.radians(HFOV / 2 - 0.5)))
                    & (np.abs(xu) < xf * np.tan(np.radians(VFOV / 2))))
        en_cam = en_camara(0.9) | en_camara(1.5)
        d_inclinada = np.hypot(dh, dz - 0.9)
        extension = np.degrees(np.arctan2(dz, dh) - np.arctan2(dz - ALTURA_PERSONA, dh))
        h_norm = np.minimum(extension, VFOV) / VFOV
        ancho_deg = np.degrees(2 * np.arctan2(RADIO_PERSONA, np.maximum(dh, 0.2)))
        w_norm = np.minimum(ancho_deg / HFOV, 1.0)
        p_det = np.where(d_inclinada < 20, 0.97, np.clip(0.97 - (d_inclinada - 20) * 0.06, 0, 1))
        # un panel tapa a la persona si cubre el torso y la cabeza; si solo asoma la cabeza, YOLO la detecta peor
        tap_c = self._vista_bloqueada(self.px, self.py, np.full(self.px.shape, 1.0)) & self.activa
        tap_h = self._vista_bloqueada(self.px, self.py, np.full(self.px.shape, 1.6)) & self.activa
        tapada = tap_c & tap_h
        p_det = np.where(tap_c & ~tap_h, 0.6 * p_det, p_det)
        visible = self.activa & en_cam & (d_inclinada < 35) & ~tapada & (r.random((n, N_PERS)) < p_det)
        elev_m = a_c + r.normal(0, 0.3, (n, N_PERS))
        ang_m = ang + r.normal(0, 0.3, (n, N_PERS))
        h_m = h_norm * (1 + r.normal(0, 0.03, (n, N_PERS)))
        area = h_m * w_norm
        f_px = (ALTO_IMG / 2) / np.tan(np.radians(VFOV / 2))
        d_alto = ALTURA_PERSONA * f_px / np.maximum(h_m * ALTO_IMG, 1.0)
        # muy cerca la persona no cabe de alto en la imagen: la distancia sale del ancho de la caja
        d_ancho = RADIO_PERSONA / np.tan(np.radians(ancho_deg * (1 + r.normal(0, 0.05, (n, N_PERS))) / 2))
        d_bbox = np.where(h_norm >= 0.99, d_ancho, d_alto)
        # LiDAR acoplado a la cámara: solo mide la distancia a la persona si está en el centro de la imagen
        t_l, tipo_l, jp_l, hx_l, hy_l, hz_l = self._lidar_camara()
        laser = visible & (jp_l[:, None] == np.arange(N_PERS)[None, :])
        d_lidar = t_l[:, None] + r.normal(0, 0.02, (n, N_PERS))
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
        fij = self.modo >= FIJADO                       # ya designado (rastreando o en el protocolo de pérdida)
        v0_raw = visible[:, 0]
        d0 = dist[:, 0]
        p_id = np.where(d0 < 12, 0.85, np.where(d0 < 20, 0.6, 0.3))
        self.n_conf = np.where(v0_raw & fij, self.n_conf + (r.random(n) < p_id), 0)
        continuo = self.t_sin_ver <= T_TRACKER
        v0 = v0_raw & fij & (continuo | (self.n_conf >= N_REID))
        lock_antes = self.lock.copy()
        self.lock = v0
        self.t_sin_ver = np.where(v0 | ~fij, 0.0, self.t_sin_ver + DT)
        # memoria del objetivo: dónde lo vio confirmado por última vez
        self.ult_rumbo = np.where(v0, envolver(self.psi - np.radians(ang_m[:, 0])), self.ult_rumbo)
        self.ult_dist = np.where(v0, dist[:, 0], self.ult_dist)
        dh_est = np.sqrt(np.maximum(dist[:, 0] ** 2 - (self.dz - 0.9) ** 2, 0.25))
        rumbo_w = self.psi - np.radians(ang_m[:, 0])
        ux_n = np.clip(self.dx + dh_est * np.cos(rumbo_w), -ARENA + 1, ARENA - 1)
        uy_n = np.clip(self.dy + dh_est * np.sin(rumbo_w), -ARENA + 1, ARENA - 1)
        # velocidad del objetivo (X/Y) estimada con sus posiciones mientras está fijado: su último vector de movimiento
        seguido = v0 & lock_antes
        vx_i = np.clip((ux_n - self.ult_x) / DT, -5, 5)
        vy_i = np.clip((uy_n - self.ult_y) / DT, -5, 5)
        self.tvx = np.where(seguido, 0.75 * self.tvx + 0.25 * vx_i, self.tvx)
        self.tvy = np.where(seguido, 0.75 * self.tvy + 0.25 * vy_i, self.tvy)
        self.ult_x = np.where(v0, ux_n, self.ult_x)
        self.ult_y = np.where(v0, uy_n, self.ult_y)
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
        # obstáculo = el rayo pega antes de donde debería tocar el suelo (la Jetson lo sabe por su altura y el pitch)
        sg = np.sin(np.radians(self.cam_pitch))
        t_suelo = np.where(sg < -1e-3, self.dz / np.maximum(-sg, 1e-3), np.inf)
        obst = t_l < np.minimum(t_suelo - 0.4, LIDAR_MAX - 0.1)
        self.lidar = np.where(obst, t_l * np.cos(np.radians(self.cam_pitch)), LIDAR_MAX)     # distancia horizontal al obstáculo
        self.lid_t, self.lid_hx, self.lid_hy, self.lid_hz, self.lid_tipo = t_l, hx_l, hy_l, hz_l, tipo_l
        # mapa con el LiDAR: cada impacto en un obstáculo (que no sea una persona en el centro de la imagen) se guarda
        # como un punto del plano, si el dron giró o se movió desde el último
        nuevo = obst & (jp_l < 0) & ((np.abs(envolver(self.psi - self.lid_ult_psi)) > np.radians(3))
                                     | (np.hypot(self.dx - self.lid_ult_x, self.dy - self.lid_ult_y) > 0.5))
        if nuevo.any():
            k = np.where(nuevo)[0]
            ranura = self.lid_i[k] % N_LIDAR
            rr = self.lidar[k] + r.normal(0, 0.05, len(k))          # distancia horizontal con ruido
            self.lid_px[k, ranura] = self.dx[k] + rr * np.cos(self.psi[k])
            self.lid_py[k, ranura] = self.dy[k] + rr * np.sin(self.psi[k])
            self.lid_ok[k, ranura] = True
            self.lid_i[k] += 1
            self.lid_ult_psi[k], self.lid_ult_x[k], self.lid_ult_y[k] = self.psi[k], self.dx[k], self.dy[k]
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
        self.info_sensor = dict(visible=visible, laser=laser, ang=ang_m, dist=dist, dh=dh, tapada=tapada, lock=v0.copy(),
                                elev=elev_m)
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

    # ------------------------------------------------------------------ mapa de obstáculos con el LiDAR
    def _mapear_lidar(self, i):
        """Agrupa los impactos del LiDAR del entorno i en segmentos: los paneles tal como los vio el dron.
        No usa el plano del simulador, solo lo que midió el LiDAR (un rayo frontal) al girar o volar bajo."""
        ok = self.lid_ok[i]
        self.det_n[i] = 0
        if ok.sum() < 3:
            return
        P = np.stack([self.lid_px[i, ok], self.lid_py[i, ok]], -1)
        m = len(P)
        ady = np.hypot(P[:, None, 0] - P[None, :, 0], P[:, None, 1] - P[None, :, 1]) < D_CLUSTER
        grupo = -np.ones(m, int)
        g = 0
        for s0 in range(m):
            if grupo[s0] >= 0:
                continue
            pila = [s0]
            grupo[s0] = g
            while pila:
                q = pila.pop()
                for v in np.where(ady[q] & (grupo < 0))[0]:
                    grupo[v] = g
                    pila.append(v)
            g += 1
        x0, x1, y0, y1 = self.zona[i]
        segs = []
        for k in range(g):
            Q = P[grupo == k]
            if len(Q) < 3:
                continue
            dq = np.hypot(Q[:, None, 0] - Q[None, :, 0], Q[:, None, 1] - Q[None, :, 1])
            a, b = np.unravel_index(np.argmax(dq), dq.shape)
            c = (Q[a] + Q[b]) / 2
            if dq[a, b] >= LARGO_MIN_PANEL and x0 - 1 <= c[0] <= x1 + 1 and y0 - 1 <= c[1] <= y1 + 1:
                segs.append((dq[a, b], Q[a], Q[b]))
        segs.sort(key=lambda t: -t[0])
        for j, (_, A, B) in enumerate(segs[:K_DET]):
            self.det_a[i, j], self.det_b[i, j] = A, B
        self.det_n[i] = min(len(segs), K_DET)

    def _flanqueo(self, i, j, D, U=None):
        """FLANQUEO PROFUNDO del panel detectado j: rodea la esquina por la que desapareció el ladrón (la más cercana a
        su última posición U; sin U, la más cercana al dron) y termina DETRÁS del plano del muro, en la zona que estaba
        oculta: E + 0.8·afuera + D_FLANCO·atrás. Para no rozar la esquina, la ruta pasa por puntos a R_ESQUINA de ella
        (en diagonal por delante y de costado), y los extremos detectados se alargan OFFSET_EXT. Devuelve (ruta,
        dirección hacia el interior de la zona oculta, centro del panel)."""
        A, B = self.det_a[i, j], self.det_b[i, j]
        M = (A + B) / 2
        u = (B - A) / max(np.hypot(*(B - A)), 1e-6)
        nrm = np.array([-u[1], u[0]])
        A_e, B_e = A - u * OFFSET_EXT, B + u * OFFSET_EXT
        ref = D if U is None else U
        E, afuera = (A_e, -u) if np.hypot(*(A_e - ref)) <= np.hypot(*(B_e - ref)) else (B_e, u)
        lado = np.sign(np.dot(D - M, nrm)) or 1.0
        frente, atras = lado * nrm, -lado * nrm
        puntos = []
        if np.dot(D - M, frente) > 0:                                # todavía está del lado visible del muro
            if np.dot(D - E, afuera) < 0.3 * R_ESQUINA:               # y no ha pasado la esquina
                puntos.append(E + R_ESQUINA * (afuera + frente) / np.sqrt(2))
            puntos.append(E + R_ESQUINA * afuera)
        puntos.append(E + 0.8 * afuera + D_FLANCO * atras)
        x0, x1, y0, y1 = self.zona[i]
        puntos = [np.array([np.clip(p[0], max(x0 + 0.5, -ARENA + 1.5), min(x1 - 0.5, ARENA - 1.5)),
                            np.clip(p[1], max(y0 + 0.5, -ARENA + 1.5), min(y1 - 0.5, ARENA - 1.5))]) for p in puntos]
        return puntos, -afuera, M

    def _ruta_segura(self, i, D, puntos):
        """¿Todos los tramos pasan a más de RADIO_DRON + MARGEN_ESQUINA de los paneles que vio el LiDAR?"""
        pts = [D] + list(puntos)
        for a, b in zip(pts, pts[1:]):
            for t in np.linspace(0.0, 1.0, 12):
                p = a + (b - a) * t
                for j in range(self.det_n[i]):
                    if dist_punto_segmento(p, self.det_a[i, j], self.det_b[i, j])[0] < RADIO_DRON + MARGEN_ESQUINA:
                        return False
        return True

    def _poner_ruta(self, i, puntos, interior, flanco):
        """Carga la ruta. Si algún tramo pasaría pegado a un panel, se vuela por encima (Z_TRANSITO) para no chocar."""
        D = np.array([self.dx[i], self.dy[i]])
        self.ruta_n[i], self.ruta_i[i] = len(puntos), 0
        for k, p in enumerate(puntos):
            self.ruta[i, k] = p
        self.rx[i], self.ry[i] = puntos[0]
        self.vuelo_alto[i] = not self._ruta_segura(i, D, puntos)
        self.int_dx[i], self.int_dy[i] = interior / max(np.hypot(*interior), 1e-6)
        self.flanco[i] = flanco
        self.t_bloqueo[i] = 0.0

    def _seguir_ruta(self, activa):
        """Al llegar a un punto intermedio pasa al siguiente. Devuelve si el punto actual es el último."""
        ar = np.arange(self.n)
        ri = np.clip(self.ruta_i, 0, 2)
        _, d = self._ir_a(self.ruta[ar, ri, 0], self.ruta[ar, ri, 1])
        pasa = activa & (self.ruta_i < self.ruta_n - 1) & (d < D_LLEGADA_PASO)
        self.ruta_i = self.ruta_i + pasa.astype(int)
        ri = np.clip(self.ruta_i, 0, 2)
        self.rx = np.where(activa, self.ruta[ar, ri, 0], self.rx)
        self.ry = np.where(activa, self.ruta[ar, ri, 1], self.ry)
        return self.ruta_i >= self.ruta_n - 1

    def _girar_hacia_interior(self, mask):
        """Sentido del primer giro al llegar: hacia el interior de la zona oculta. Si queda a la izquierda de la nariz,
        gira a la izquierda (yaw negativo); si a la derecha, a la derecha. Es la regla izquierda-derecha: si el ladrón
        entró por el borde izquierdo moviéndose hacia la derecha, el dron rodea esa esquina y rota a la derecha."""
        cruz = np.cos(self.psi) * self.int_dy - np.sin(self.psi) * self.int_dx
        self.busca_dir = np.where(mask, np.where(cruz > 0, -1.0, 1.0), self.busca_dir)

    def _planear_inspeccion(self, i):
        """Búsqueda activa: el siguiente panel que vio el LiDAR y que aún no se revisó, con flanqueo profundo para
        quedar detrás de él; si el LiDAR no vio ninguno, mira desde el centro de la zona; si ya revisó todos, vuelve a
        girar (y a mapear) donde está."""
        self._mapear_lidar(i)
        D = np.array([self.dx[i], self.dy[i]])
        hechos = np.stack([self.insp_x[i, :self.insp_n[i]], self.insp_y[i, :self.insp_n[i]]], -1)
        mejor = None
        for j in range(self.det_n[i]):
            puntos, interior, M = self._flanqueo(i, j, D)
            if len(hechos) and np.min(np.hypot(*(hechos - M).T)) < R_INSP_HECHO:
                continue
            largo = sum(np.hypot(*(b - a)) for a, b in zip([D] + puntos, puntos))
            if mejor is None or largo < mejor[0]:
                mejor = (largo, j, puntos, interior, M)
        if mejor is None:
            if self.det_n[i] > 0 or np.hypot(self.zona[i, :2].mean() - D[0], self.zona[i, 2:].mean() - D[1]) < 3.0:
                self.insp_n[i] = 0                      # ronda completa: gira y mapea otra vez desde aquí
                self.bfase[i] = B_GIRO
                self.giro_acum[i] = 0.0
                return
            c = np.array([self.zona[i, :2].mean(), self.zona[i, 2:].mean()])
            mejor = (0.0, -1, [c], np.array([1.0, 0.0]), c)
        _, j, puntos, interior, M = mejor
        self._poner_ruta(i, puntos, interior, j >= 0)
        self.panel_obj[i] = j
        self.wp_x[i], self.wp_y[i] = puntos[-1]
        self.mira_x[i], self.mira_y[i] = M
        self.obj_mx[i], self.obj_my[i] = M
        self.bfase[i] = B_TRANSITO
        self.giro_acum[i] = self.t_vuelo[i] = 0.0

    def _planear_perdida(self, i):
        """Protocolo de pérdida. Si lo perdió junto a un panel (visto por el LiDAR): FLANQUEO PROFUNDO por la esquina
        por la que desapareció, hasta quedar detrás del muro. En campo abierto: se detiene D_STANDOFF antes de su última
        posición y el giro empezará hacia donde iba. La zona de pérdida (maniobra de altura) es el panel o la última posición."""
        self._mapear_lidar(i)
        D = np.array([self.dx[i], self.dy[i]])
        U = np.array([self.ult_x[i], self.ult_y[i]])
        jb, db = -1, 3.0
        for j in range(self.det_n[i]):
            dj, _ = dist_punto_segmento(U, self.det_a[i, j], self.det_b[i, j])
            if dj < db:
                jb, db = j, float(dj)
        esc = np.array([self.esc_vx[i], self.esc_vy[i]])
        if jb >= 0:
            puntos, interior, Zc = self._flanqueo(i, jb, D, U)
        else:
            v = U - D
            dv = np.hypot(*v)
            puntos = [U - D_STANDOFF * v / dv if dv > D_STANDOFF else D.copy()]
            interior = esc if np.hypot(*esc) > V_PRED_MIN else (v if dv > 1e-6 else np.array([1.0, 0.0]))
            Zc = U
        self._poner_ruta(i, puntos, interior, jb >= 0)
        self.inv_x[i], self.inv_y[i] = puntos[-1]
        self.mira_x[i], self.mira_y[i] = U
        self.zc_x[i], self.zc_y[i] = Zc

    def _guarda_mapa(self, vx, vy):
        """Muro virtual con los impactos guardados del LiDAR (sin red neuronal: n x N_LIDAR distancias). Por debajo de
        la altura de tránsito, quita a la consigna la parte de la velocidad hacia el obstáculo que excede la que
        permite frenar a tiempo; la parte tangencial se conserva (se desliza a lo largo del muro)."""
        bajo = self.dz < Z_TRANSITO - 0.1
        rx, ry = self.lid_px - self.dx[:, None], self.lid_py - self.dy[:, None]
        d = np.hypot(rx, ry)
        cerca = self.lid_ok & (d < R_GUARDA) & bajo[:, None]
        ux, uy = rx / np.maximum(d, 1e-6), ry / np.maximum(d, 1e-6)
        v_max = np.sqrt(2.0 * A_GUARDA * np.maximum(d - R_PARADA, 0.0))
        activa = np.zeros(self.n, bool)
        for _ in range(2):                                   # dos pasadas: en una esquina hay dos muros
            exceso = np.where(cerca, vx[:, None] * ux + vy[:, None] * uy - v_max, 0.0)
            k = np.argmax(exceso, 1)
            e = np.take_along_axis(exceso, k[:, None], 1)[:, 0]
            sel = e > 0
            vx = np.where(sel, vx - e * np.take_along_axis(ux, k[:, None], 1)[:, 0], vx)
            vy = np.where(sel, vy - e * np.take_along_axis(uy, k[:, None], 1)[:, 0], vy)
            activa |= sel
        return vx, vy, activa

    def _dist_paneles_detectados(self):
        """Distancia horizontal del dron al panel más cercano que haya visto el LiDAR."""
        D = np.stack([self.dx, self.dy], -1)
        d = np.full(self.n, np.inf)
        for j in range(K_DET):
            dj, _ = dist_punto_segmento(D, self.det_a[:, j], self.det_b[:, j])
            d = np.where(j < self.det_n, np.minimum(d, dj), d)
        return d

    # ------------------------------------------------------------------ paso
    def _ir_a(self, tx, ty):
        """Error de rumbo (rad, + = a la izquierda) y distancia horizontal a un punto."""
        return envolver(np.arctan2(ty - self.dy, tx - self.dx) - self.psi), np.hypot(tx - self.dx, ty - self.dy)

    def step(self, acc_dron, acc_persona, auto_reset=True):
        n = self.n
        r = self.rng
        rew_d = np.zeros(n)
        o = self.obs_retraso
        s = self.info_sensor
        vis, dist_s, ang_s, elev_s = s["visible"] & self.activa, s["dist"], s["ang"], s["elev"]
        self.t_modo += DT
        self.t_fase2 += DT

        # ================= máquina de estados de la misión =================
        # BUSCAR (cualquier subfase) -> VERIFICAR: alguien detectado que no haya sido descartado
        cands = vis & ~self.ignorado
        j_c = np.argmin(np.where(cands, dist_s, 99.0), 1)
        ini_ver = (self.modo == BUSCAR) & cands.any(1)
        self.cand = np.where(ini_ver, j_c, self.cand)
        self.t_resp = np.where(ini_ver, r.uniform(T_OPERADOR[0], T_OPERADOR[1], n), self.t_resp)
        self.cand_sin_ver = np.where(ini_ver, 0.0, self.cand_sin_ver)
        self.cand_visto = np.where(ini_ver, 0.0, self.cand_visto)
        self.modo = np.where(ini_ver, VERIFICAR, self.modo)
        self.t_modo = np.where(ini_ver, 0.0, self.t_modo)
        # VERIFICAR: hover con la persona centrada y alerta en la estación de tierra. El operador confirma con
        # un CLIC sobre la persona (solo sobre el sospechoso). Si nadie confirma en T_ESPERA_CLIC, ese ID queda
        # descartado y la búsqueda sigue donde iba. Decide con lo que alcanzó a ver (al menos T_VER_MIN s).
        ver = (self.modo == VERIFICAR) & ~ini_ver
        ci = np.clip(self.cand, 0, N_PERS - 1)
        c_vis = np.take_along_axis(vis, ci[:, None], 1)[:, 0]
        c_ang = np.take_along_axis(ang_s, ci[:, None], 1)[:, 0]
        self.cand_visto = np.where(ver & c_vis, self.cand_visto + DT, self.cand_visto)
        self.cand_rumbo = np.where((ver | ini_ver) & c_vis, envolver(self.psi - np.radians(c_ang)), self.cand_rumbo)
        self.cand_sin_ver = np.where(ver & ~c_vis, self.cand_sin_ver + DT, np.where(ver, 0.0, self.cand_sin_ver))
        suficiente = self.cand_visto >= T_VER_MIN
        lock_on = ver & suficiente & (self.t_modo >= self.t_resp) & (self.cand == 0)          # clic del operador
        descarta = ver & suficiente & (self.t_modo >= T_ESPERA_CLIC) & (self.cand != 0)      # nadie lo confirma
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
        # INTERCEPCIÓN PREDICTIVA: si sale del cuadro corriendo (por ejemplo, pasa por debajo del dron), no se queda
        # en hover: sigue su trayectoria extrapolada T_PREDICCION s mientras el gimbal intenta re-encuadrarlo
        rapido = np.hypot(self.tvx, self.tvy) > V_PRED_MIN
        a_pred = (self.modo == FIJADO) & (self.t_sin_ver > T_PRED_INI) & rapido
        self.pred_x0 = np.where(a_pred, self.ult_x, self.pred_x0)
        self.pred_y0 = np.where(a_pred, self.ult_y, self.pred_y0)
        self.pred_vx = np.where(a_pred, self.tvx, self.pred_vx)
        self.pred_vy = np.where(a_pred, self.tvy, self.pred_vy)
        self.esc_vx = np.where(a_pred, self.tvx, self.esc_vx)
        self.esc_vy = np.where(a_pred, self.tvy, self.esc_vy)
        self.modo = np.where(a_pred, PREDECIR, self.modo)
        self.t_modo = np.where(a_pred, 0.0, self.t_modo)
        fin_pred = (self.modo == PREDECIR) & (self.t_modo > T_PREDICCION) & ~self.lock
        # PROTOCOLO DE PÉRDIDA: el tracker soltó el ID (iba lento, o la predicción no lo recuperó)
        lento = (self.modo == FIJADO) & (self.t_sin_ver > T_TRACKER)
        self.esc_vx = np.where(lento, self.tvx, self.esc_vx)
        self.esc_vy = np.where(lento, self.tvy, self.esc_vy)
        perdida = a_pred | lento                            # el objetivo acaba de salir de la vista
        pierde = lento | fin_pred
        for i in np.where(pierde)[0]:
            self._planear_perdida(i)
        self.modo = np.where(pierde, INVESTIGAR, self.modo)
        self.t_modo = np.where(pierde, 0.0, self.t_modo)
        self.t_bloqueo = np.where(pierde, 0.0, self.t_bloqueo)
        # en cualquier paso del protocolo, si YOLO vuelve a confirmar el ID (ReID), la IA retoma el control
        recupera = (self.modo >= INVESTIGAR) & self.lock & ~pierde
        self.modo = np.where(recupera, FIJADO, self.modo)
        self.t_modo = np.where(recupera, 0.0, self.t_modo)
        self.giro_mem = np.where(recupera, 0.0, self.giro_mem)
        # INVESTIGAR (flanqueo o punto de separación) -> ASOMO (giro hacia el interior oculto) -> VENTAJA DE ALTURA -> fallida
        ultimo_u = self._seguir_ruta(self.modo == INVESTIGAR)
        err_u, d_u = self._ir_a(self.rx, self.ry)
        llega_u = (self.modo == INVESTIGAR) & ultimo_u & ((d_u < D_LLEGADA) | (self.t_bloqueo > 1.0) | (self.t_modo > T_INVESTIGA_MAX))
        self._girar_hacia_interior(llega_u)
        fin_asomo = (self.modo == ASOMO) & self.aso_gira & (self.giro_acum >= 360.0)
        agotado = (self.modo == VENTAJA_ALTURA) & (self.giro_acum >= 360.0)
        self.modo = np.where(llega_u, ASOMO, np.where(fin_asomo, VENTAJA_ALTURA, self.modo))
        self.t_modo = np.where(llega_u | fin_asomo, 0.0, self.t_modo)
        self.giro_acum = np.where(llega_u | fin_asomo, 0.0, self.giro_acum)
        self.aso_gira = np.where(llega_u, True, self.aso_gira)          # al llegar detrás del muro rota de inmediato
        self.t_bloqueo = np.where(fin_asomo, 0.0, self.t_bloqueo)
        # BÚSQUEDA ACTIVA: giro de 360° mapeando con el LiDAR -> revisar detrás de cada panel detectado, uno por uno
        busc = self.modo == BUSCAR
        fin_giro = busc & (self.bfase == B_GIRO) & (self.giro_acum >= 360.0)
        fin_insp = busc & (self.bfase == B_INSPECCION) & (self.giro_acum >= 360.0)
        for i in np.where(fin_insp)[0]:
            if self.insp_n[i] < self.insp_x.shape[1]:
                self.insp_x[i, self.insp_n[i]], self.insp_y[i, self.insp_n[i]] = self.obj_mx[i], self.obj_my[i]
                self.insp_n[i] += 1
        for i in np.where(fin_giro | fin_insp)[0]:
            self._planear_inspeccion(i)
        tran = busc & (self.bfase == B_TRANSITO)
        ultimo_w = self._seguir_ruta(tran)
        err_w, d_w = self._ir_a(self.rx, self.ry)
        self.t_vuelo = np.where(tran | (busc & (self.bfase == B_INSPECCION)), self.t_vuelo + DT, self.t_vuelo)
        llega_w = tran & ultimo_w & ((d_w < D_LLEGADA) | (self.t_bloqueo > 1.0) | (self.t_vuelo > T_INVESTIGA_MAX))
        self._girar_hacia_interior(llega_w)
        self.bfase = np.where(llega_w, B_INSPECCION, self.bfase)
        self.giro_acum = np.where(llega_w, 0.0, self.giro_acum)
        self.t_vuelo = np.where(llega_w, T_MIRA, self.t_vuelo)              # detrás del muro: rota de inmediato

        busc, ver, fij = self.modo == BUSCAR, self.modo == VERIFICAR, self.modo == FIJADO
        inv, aso, alt, pred = self.modo == INVESTIGAR, self.modo == ASOMO, self.modo == VENTAJA_ALTURA, self.modo == PREDECIR
        tran = busc & (self.bfase == B_TRANSITO)
        insp = busc & (self.bfase == B_INSPECCION)
        decide = fij & (self.estado == VIGILANDO)
        ve = (o[:, 0] > 0.5) & fij

        # ================= árbitro: amenaza real y perímetro de colisión =================
        d_l, v_l, d_p, v_p = o[:, 1] * 20.0, o[:, 5] * 5.0, o[:, 13] * 20.0, o[:, 15] * 5.0
        self.amenaza = ((ve & ((d_l < D_CRITICA) | ((d_l < D_AMENAZA) & (v_l > V_ACERCA))))
                        | ((o[:, 12] > 0.5) & ((d_p < D_CRITICA) | ((d_p < D_AMENAZA) & (v_p > V_ACERCA)))))
        self.perimetro = (vis & (dist_s < D_PERIMETRO)).any(1)
        # la maniobra la elige la IA en FIJADO y una regla fija en los modos automáticos
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
        # ESQUIVE REFLEJO: alguien corre hacia el dron (intenta tumbarlo). El árbitro no espera a la IA ni a la regla:
        # sube y se aparta hacia el lado contrario de inmediato, en cualquier modo
        ataque_j = vis & (dist_s < D_REFLEJO) & (self.vac > V_ATAQUE)
        ja = np.argmin(np.where(ataque_j, dist_s, 99.0), 1)
        ang_a = np.take_along_axis(ang_s, ja[:, None], 1)[:, 0]
        reflejo = ataque_j.any(1) & (self.estado != EVADIENDO)
        self.estado = np.where(reflejo, EVADIENDO, self.estado)
        self.clase = np.where(reflejo, 3, self.clase)
        self.t_estado = np.where(reflejo, 0.0, self.t_estado)
        self.lat_esq = np.where(reflejo, np.where(ang_a > 0, -VEL_LATERAL, VEL_LATERAL),
                                np.where(self.estado == EVADIENDO, self.lat_esq, 0.0))
        self.reflejo = (self.estado == EVADIENDO) & (self.lat_esq != 0)
        inicia = inicia | reflejo

        # ================= consignas de velocidad (cuerpo: x adelante, y derecha) =================
        eva = self.estado == EVADIENDO
        cerca_peaton = (o[:, 12] > 0.5) & (o[:, 13] * 20.0 < D_PEATON_FRENTE) & (np.abs(o[:, 14]) < 0.5)
        libre = self.lidar > DIST_PROTECCION_FRONTAL
        # PERSECUCIÓN con el objetivo a la vista: la acción AVANZAR (y, apenas el operador confirma el ID, el
        # acercamiento automático si está lejos) usa navegación predictiva + distancia óptima de seguimiento
        aprox = decide & ve & (o[:, 1] * 20.0 > D_APROX)
        persigue = ((decide & ve & (acc_dron == 6)) | aprox) & ~cerca_peaton
        d_obj = np.sqrt(np.maximum((o[:, 1] * 20.0) ** 2 - (self.dz - 0.9) ** 2, 0.0))       # distancia horizontal medida
        v_rango = np.where(d_obj > R_OPT_MAX, np.minimum(K_RANGO * (d_obj - R_OPT_MAX) + 0.5, VEL_PERSEGUIR),
                           np.where(d_obj >= R_OPT_MIN, 0.0, np.where(d_obj >= R_RETROCEDE, 0.0, -0.6)))
        lx, ly = self.ult_x + self.tvx * T_LEAD, self.ult_y + self.tvy * T_LEAD          # dónde estará en T_LEAD s
        _, d_lead = self._ir_a(lx, ly)
        ux_l, uy_l = (lx - self.dx) / np.maximum(d_lead, 1e-6), (ly - self.dy) / np.maximum(d_lead, 1e-6)
        al_frente_l = (ux_l * np.cos(self.psi) + uy_l * np.sin(self.psi)) > np.cos(np.radians(35))
        v_rango = np.where(persigue & al_frente_l & ~libre & (v_rango > 0), 0.0, v_rango)       # el LiDAR ve un obstáculo
        # avance a ciegas (objetivo fuera de vista, dentro de la memoria del tracker): hacia donde mira, con el LiDAR
        avanza_ia = decide & ~ve & (acc_dron == 6) & libre & ~cerca_peaton
        # vuelos deterministas: al punto de inspección, al punto de separación o a la zona de pérdida (la maniobra
        # de altura). Apunta, gana la altura de tránsito (por encima de los paneles) y avanza con el LiDAR.
        err_z, d_z = self._ir_a(self.zc_x, self.zc_y)
        en_estacion = alt & ((d_z < 0.8) | (self.t_bloqueo > 1.0))
        vuela = tran | inv | (alt & ~en_estacion)
        err_v = np.where(inv, err_u, np.where(alt, err_z, err_w))
        d_v = np.where(inv, d_u, np.where(alt, d_z, d_w))
        alineado = np.abs(err_v) < np.radians(12)
        # el flanqueo se vuela a Z_FLANCO (fuera del alcance del ladrón); a Z_TRANSITO si la ruta no tenía margen
        arriba = np.where(self.vuelo_alto | alt, self.dz > Z_TRANSITO - 0.25, self.dz > Z_FLANCO - 0.25)
        libre_v = self.lidar > DIST_PROTECCION_VUELO
        self.t_bloqueo = np.where(vuela & alineado & arriba & ~libre_v, self.t_bloqueo + DT, 0.0)
        avanza_det = vuela & alineado & arriba & libre_v & ~self.perimetro
        vx_b = np.where(eva, 0.0, np.where(avanza_ia, VEL_AVANCE, np.where(avanza_det, np.minimum(VEL_INVESTIGA, 0.8 * d_v + 0.3), 0.0)))
        vy_b = np.where(eva & (self.clase == 1), -VEL_LATERAL, np.where(eva & (self.clase == 2), VEL_LATERAL,
                                                                        np.where(self.reflejo, self.lat_esq, 0.0)))
        # altura: la nominal para rastrear y verificar; por encima de los paneles en los vuelos de búsqueda; la
        # maniobra de VENTAJA DE ALTURA sube rápido a Z_TACTICO. El seguimiento vertical lo hace el gimbal; el dron
        # solo cambia de altura por eso si el gimbal se satura (objetivo mucho más alto).
        busqueda_det = inv | aso | (busc & (self.bfase != B_GIRO))
        z_obj = np.where(alt, Z_TACTICO, np.where(busqueda_det, np.where(self.vuelo_alto, Z_TRANSITO, Z_FLANCO), Z_NOMINAL))
        z_obj = np.where(self.gmb_sat_arriba, np.minimum(self.dz + 0.5, Z_MAX), z_obj)
        # despeje: nunca bajar sobre un panel que haya visto el LiDAR (no se sabe su altura: se respeta la de tránsito)
        d_pan = self._dist_paneles_detectados()
        z_obj = np.where(d_pan < RADIO_DRON + 0.3, np.maximum(z_obj, Z_TRANSITO), z_obj)
        alguien_cerca = (vis & (dist_s < 6.0)).any(1)
        vz_auto = np.clip(0.8 * (z_obj - self.dz), -0.4, np.where(alt, VEL_SUBIDA_RAPIDA, 0.6))
        vz_auto = np.where((vz_auto < 0) & alguien_cerca, 0.0, vz_auto)       # no baja con alguien cerca
        vz_c = np.where(eva & (self.clase == 3), np.where(self.reflejo, VEL_ESQUIVE_Z, VEL_ASCENSO),
                        np.where(self.estado == VIGILANDO, vz_auto, 0.0))
        cps, sps = np.cos(self.psi), np.sin(self.psi)
        vx_c = vx_b * cps + vy_b * sps
        vy_c = vx_b * sps - vy_b * cps
        # predicción: vuela en la misma dirección que llevaba el ladrón (a su velocidad, con tope); si va hacia donde
        # mira la cámara y el LiDAR ve un obstáculo cerca, no avanza (hacia otros lados no hay protección)
        vmod = np.hypot(self.pred_vx, self.pred_vy)
        mueve_al_frente = np.abs(envolver(np.arctan2(self.pred_vy, self.pred_vx) - self.psi)) < np.radians(35)
        v_pred = np.where(pred & ~eva & ~(mueve_al_frente & ~libre), np.minimum(vmod, VEL_PRED_MAX), 0.0)
        vx_c = np.where(pred, v_pred * self.pred_vx / np.maximum(vmod, 1e-6), vx_c)
        vy_c = np.where(pred, v_pred * self.pred_vy / np.maximum(vmod, 1e-6), vy_c)
        # navegación predictiva: el empuje apunta al punto de intercepción (corta en las esquinas, no lo persigue por detrás)
        vx_c = np.where(persigue & ~eva, v_rango * ux_l, vx_c)
        vy_c = np.where(persigue & ~eva, v_rango * uy_l, vy_c)
        vx_c, vy_c, self.guarda = self._guarda_mapa(vx_c, vy_c)
        dvx0, dvy0 = self.dvx.copy(), self.dvy.copy()
        # aceleración horizontal limitada como vector (un multirrotor no puede inclinarse más en diagonal)
        ddx, ddy = (vx_c - self.dvx) * DT / TAU_DRON, (vy_c - self.dvy) * DT / TAU_DRON
        esc_a = np.minimum(1.0, ACC_MAX_DRON * DT / np.maximum(np.hypot(ddx, ddy), 1e-9))
        self.dvx += ddx * esc_a + r.normal(0, 0.02, n)
        self.dvy += ddy * esc_a + r.normal(0, 0.02, n)
        self.dvz += (vz_c - self.dvz) * DT / TAU_DRON
        self.dx += self.dvx * DT
        self.dy += self.dvy * DT
        self.dz = np.clip(self.dz + self.dvz * DT, Z_MIN, Z_MAX)
        # dinámica de cabeceo del multirrotor: para acelerar se inclina (cabeceo = -atan(a/g), nariz abajo hacia
        # adelante). El cambio de inclinación entra a la cámara como error y el gimbal lo corrige en TAU_ESTAB.
        ax, ay = (self.dvx - dvx0) / DT, (self.dvy - dvy0) / DT
        a_f = ax * np.cos(self.psi) + ay * np.sin(self.psi)
        a_l = ax * np.sin(self.psi) - ay * np.cos(self.psi)
        cab = self.chasis_pitch + (-np.degrees(np.arctan(a_f / G)) - self.chasis_pitch) * DT / TAU_ACTITUD
        self.err_gmb += (cab - self.chasis_pitch) - self.err_gmb * DT / TAU_ESTAB
        self.chasis_pitch = cab
        self.chasis_roll += (np.degrees(np.arctan(a_l / G)) - self.chasis_roll) * DT / TAU_ACTITUD

        # ================= guiñada: seguimiento HORIZONTAL (independiente de la evasión) =================
        # banda muerta: mientras el objetivo esté en el 20% central del FOV horizontal, el yaw queda en 0; si sale
        # de esa franja corrige hasta dejarlo bien centrado (histéresis) y se detiene. Igual al verificar.
        ci = np.clip(self.cand, 0, N_PERS - 1)
        ang_c = np.take_along_axis(ang_s, ci[:, None], 1)[:, 0]
        c_vis = np.take_along_axis(vis, ci[:, None], 1)[:, 0] & ver
        ang_t = np.where(fij, o[:, 4] * HFOV / 2, ang_c)
        hay_t = np.where(fij, ve, c_vis)
        self.yaw_corrige = hay_t & np.where(np.abs(ang_t) > BANDA_MUERTA, True,
                                            np.where(np.abs(ang_t) < BANDA_RECENTRA, False, self.yaw_corrige))
        tasa_t = np.where(self.yaw_corrige, np.clip(YAW_KP * ang_t, -YAW_MAX, YAW_MAX), 0.0)
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
        yaw_fij = np.where(ve, tasa_t, np.where(self.giro_mem != 0, self.giro_mem, hacia_ult))
        rel_c = np.degrees(envolver(self.cand_rumbo - self.psi))
        yaw_ver = np.where(c_vis, tasa_t, np.where(np.abs(rel_c) > YAW_ZONA, np.clip(-1.5 * rel_c, -YAW_ULTIMO, YAW_ULTIMO), 0.0))
        yaw_vuelo = np.clip(-2.0 * np.degrees(err_v), -YAW_MAX, YAW_MAX)
        # mirar: detrás del panel al llegar a inspeccionarlo; en el ASOMO, primero hacia la última posición
        err_m, d_m = self._ir_a(self.mira_x, self.mira_y)
        yaw_mira = np.clip(-2.0 * np.degrees(err_m), -YAW_MAX, YAW_MAX)
        mirando = (aso & ~self.aso_gira) | (insp & (self.t_vuelo < T_MIRA))
        a_nominal = self.dz < Z_NOMINAL + 0.3
        barre = ((busc & (self.bfase == B_GIRO) & a_nominal) | (insp & (self.t_vuelo >= T_MIRA)) | (aso & self.aso_gira)
                 | (en_estacion & (self.dz >= Z_TACTICO - 0.2)))
        # predicción: la nariz va hacia el punto extrapolado, con la guiñada rápida del autopiloto
        tp = self.t_modo + T_PRED_INI
        px_p, py_p = self.pred_x0 + self.pred_vx * tp, self.pred_y0 + self.pred_vy * tp
        err_p, d_pp = self._ir_a(px_p, py_p)
        yaw_pred = np.clip(-2.5 * np.degrees(err_p), -YAW_MAX_PRED, YAW_MAX_PRED)
        vel_barrido = np.where(aso, YAW_DIRECCIONAL, YAW_BUSQUEDA)
        yaw_cmd = np.where(fij, yaw_fij, np.where(ver, yaw_ver, np.where(pred, yaw_pred, np.where(vuela, yaw_vuelo,
                           np.where(mirando, yaw_mira, np.where(barre, self.busca_dir * vel_barrido, 0.0))))))
        # perímetro de colisión: solo alguien a menos de D_PERIMETRO pausa un giro de búsqueda
        de_busqueda = barre | (fij & (self.giro_mem != 0))
        yaw_cmd = np.where(de_busqueda & self.perimetro, 0.0, yaw_cmd)
        self.yaw_dps += np.clip(yaw_cmd - self.yaw_dps, -ACEL_YAW * DT, ACEL_YAW * DT)
        self.psi = envolver(self.psi - np.radians(self.yaw_dps) * DT)
        self.giro_acum = np.where(barre, self.giro_acum + np.abs(self.yaw_dps) * DT, self.giro_acum)

        # ================= gimbal (pitch): seguimiento VERTICAL con la cámara, no con el dron =================
        # foco: el objetivo fijado, la persona que se verifica o, ante una amenaza, la persona detectada más cercana
        j_cerca = np.argmin(np.where(vis, dist_s, 99.0), 1)
        foco = np.where(fij & self.lock, 0, np.where(c_vis, ci, np.where(self.amenaza & vis.any(1), j_cerca, -1)))
        tiene = foco >= 0
        e_f = np.take_along_axis(elev_s, np.clip(foco, 0, N_PERS - 1)[:, None], 1)[:, 0]
        off_v = e_f + self.cam_pitch                # > 0: la persona está por debajo del centro de la imagen
        self.gmb_corrige = tiene & np.where(np.abs(off_v) > GIMBAL_BANDA, True,
                                            np.where(np.abs(off_v) < GIMBAL_RECENTRA, False, self.gmb_corrige))
        tasa_g = np.where(self.gmb_corrige, np.clip(-GIMBAL_KP * off_v, -GIMBAL_VEL, GIMBAL_VEL), 0.0)
        # sin foco, ángulo de escaneo según el modo: al frente hacia el destino en los vuelos, al punto que mira en el
        # asomo y la inspección, -65° para el barrido desde la altura, y NADIR (-85°) al pasar por encima de un panel
        # detectado, para ver su base; al dejarlo atrás vuelve al escaneo normal
        d_mira_g = np.where(pred, np.maximum(d_pp, 0.3), np.where(vuela, np.maximum(d_v, 6.0), np.where(mirando, np.maximum(d_m, 2.0), D_REPOSO)))
        meta = -np.degrees(np.arctan2(self.dz - 0.9, d_mira_g))
        meta = np.where(en_estacion & (self.dz >= Z_TACTICO - 0.2), GIMBAL_TACTICO, meta)
        sobrevuela = (vuela | alt) & (self.dz > Z_TRANSITO - 0.3) & (d_pan < D_NADIR)
        meta = np.where(sobrevuela & ~(en_estacion & (self.dz >= Z_TACTICO - 0.2)), GIMBAL_NADIR, meta)
        self.nadir = sobrevuela & ~tiene
        tasa_g = np.where(tiene, tasa_g, np.clip(3.0 * (meta - self.gimbal), -GIMBAL_VEL, GIMBAL_VEL))
        self.gimbal = np.clip(self.gimbal + tasa_g * DT, GIMBAL_MIN, GIMBAL_MAX)
        # la cámara apunta donde el gimbal manda más el error que aún no compensa; y no puede salirse de sus
        # límites mecánicos respecto al chasis inclinado
        self.cam_pitch = np.clip(self.gimbal + self.err_gmb, self.chasis_pitch + GIMBAL_REL_MIN, self.chasis_pitch + GIMBAL_REL_MAX)
        self.gmb_sat_arriba = tiene & (-e_f > GIMBAL_MAX + 1.0)

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
        designado = self.modo >= FIJADO
        self.t_fijado = np.where(designado, self.t_fijado + DT, self.t_fijado)
        perdido = agotado                                   # se agotó el protocolo de búsqueda
        no_encontrado = (self.modo <= VERIFICAR) & (self.t_fase2 >= T_BUSQUEDA_MAX)
        falla = choque | fuera | choca_panel | perdido | no_encontrado
        exito = (self.modo == FIJADO) & (self.t_fijado >= T_RASTREO) & ~falla
        tiempo = self.t >= PASOS_EPISODIO
        rew_d += np.where(choque, R_COLISION, 0.0) + np.where(fuera, R_GEOCERCA, 0.0) + np.where(choca_panel, R_CHOQUE_PANEL, 0.0)
        rew_d += np.where(perdido | no_encontrado, R_PERDIDO, 0.0) + np.where(exito, R_EXITO, 0.0)
        rew_d += np.where(perdida, R_PIERDE, 0.0)
        rew_p = np.where(lo_alcanza_ladron, 10.0, 0.0) + np.where(perdido | no_encontrado, 5.0, 0.0) + np.where(perdida, 1.0, 0.0)
        done = falla | exito | tiempo
        phi_nuevo = self._potencial()
        rew_d += np.where(done, 0.0, GAMMA_GUIA * phi_nuevo - self.phi)
        self.phi = phi_nuevo

        self.obs_retraso = self._sensores()
        visto = self.info_sensor["lock"]
        rew_d += np.where(visto & ~choque, R_VISTA, 0.0)
        d_h0 = np.hypot(self.px[:, 0] - self.dx, self.py[:, 0] - self.dy)
        rew_d += np.where(visto & (d_h0 >= R_OPT_MIN) & (d_h0 <= R_OPT_MAX), R_RANGO, 0.0)
        rew_d += np.where(visto & (d_h0 < 3.0), R_MUY_CERCA, 0.0)
        rew_p -= np.where(visto, R_VISTA, 0.0)
        info = dict(choque=choque, choque_ladron=lo_alcanza_ladron, choque_peaton=choque & ~lo_alcanza_ladron,
                    panel=choca_panel, fuera=fuera, tiempo=tiempo, perdido=perdido, no_encontrado=no_encontrado,
                    exito=exito, inicia=inicia, pierde=perdida, recupera=recupera, reflejo=reflejo, dist=d_all[:, 0], visto=visto.copy(),
                    fijado=designado.copy(), peatones=self.activa[:, 1:].sum(1))
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
        # cinemática humana: no gira en seco (aceleración lateral limitada), acelera y frena con límites, y si quiere
        # girar más de 45° tiene que frenar primero (como una persona real que cambia de dirección corriendo)
        s_d = np.hypot(vxp, vyp)
        h_d = np.arctan2(vyp, vxp)
        v_act = np.hypot(self.pvx, self.pvy)
        dif = envolver(h_d - self.p_rumbo)
        giro = np.minimum(OMEGA_PERSONA, A_LAT_PERSONA / np.maximum(v_act, 0.3)) * DT
        self.p_rumbo = np.where(s_d > 0.05, envolver(self.p_rumbo + np.clip(dif, -giro, giro)), self.p_rumbo)
        brusco = np.abs(dif) > np.radians(45)
        s_obj = np.where(brusco, np.minimum(s_d, V_GIRO_PERSONA), s_d)
        v_act = v_act + np.clip(s_obj - v_act, -A_FRENO_PERSONA * DT, A_ACEL_PERSONA * DT)
        self.pvx, self.pvy = v_act * np.cos(self.p_rumbo), v_act * np.sin(self.p_rumbo)
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
        puede_atacar = puede_atacar | ((dd < 12.0) & (self.dz < ALCANCE_Z + 0.3) & (self.stamina > 1.0))
        a_cambia = (fin_esc & (u >= 0.5) & (u < 0.8)) | cambia_vis
        a_ataca = fin_esc & (u >= 0.8) & puede_atacar
        # además, de vez en cuando corre a tumbar el dron desde donde esté (si lo tiene cerca y al alcance)
        a_ataca |= (((m == L_ESCONDIDO) | (m == L_ASOMARSE) | (m == L_CUBRIRSE)) & puede_atacar & (dd < 12.0)
                    & (r.random(n) < TASA_ATAQUE * DT) & ~fin_esc)
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
        """0 búsqueda · 5 verificando (operador) · 1 objetivo fijado · 2 memoria · 3 perdido (protocolo) · 4 re-identificando."""
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
        m_ = self.modo[i]
        tp = self.t_modo[i] + T_PRED_INI
        wx, wy = ((self.inv_x[i], self.inv_y[i]) if m_ in (INVESTIGAR, ASOMO) else
                  (self.zc_x[i], self.zc_y[i]) if m_ == VENTAJA_ALTURA else
                  (self.pred_x0[i] + self.pred_vx[i] * tp, self.pred_y0[i] + self.pred_vy[i] * tp) if m_ == PREDECIR else
                  (self.wp_x[i], self.wp_y[i]))
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
            "per": bool(self.perimetro[i]), "giro": round(float(self.giro_mem[i]), 1), "rep": bool(self.bfase[i] == B_TRANSITO),
            "bf": int(self.bfase[i]), "pj": int(self.panel_obj[i]), "ninsp": int(self.insp_n[i]),
            "wx": round(float(wx), 2), "wy": round(float(wy), 2),
            "mx": round(float(self.mira_x[i]), 2), "my": round(float(self.mira_y[i]), 2), "nadir": bool(self.nadir[i]),
            "ev": [round(float(self.esc_vx[i]), 2), round(float(self.esc_vy[i]), 2)], "bd": int(self.busca_dir[i]),
            "rfx": bool(self.reflejo[i]), "gd": bool(self.guarda[i]), "lt": int(self.lid_tipo[i]), "flq": bool(self.flanco[i]), "va": bool(self.vuelo_alto[i]),
            "ruta": ([[round(float(self.ruta[i, k, 0]), 2), round(float(self.ruta[i, k, 1]), 2)] for k in range(int(self.ruta_i[i]), int(self.ruta_n[i]))]
                     if (m_ == INVESTIGAR or (m_ == BUSCAR and self.bfase[i] == B_TRANSITO)) else []),
            "lh": [round(float(self.lid_hx[i]), 2), round(float(self.lid_hy[i]), 2), round(float(self.lid_hz[i]), 2)],
            "det": [[round(float(v), 2) for v in (*self.det_a[i, j], *self.det_b[i, j])] for j in range(int(self.det_n[i]))],
            "ux": round(float(self.ult_x[i]), 2), "uy": round(float(self.ult_y[i]), 2),
            "gmb": round(float(self.cam_pitch[i]), 1), "yc": bool(self.yaw_corrige[i]),
            "cp": round(float(self.chasis_pitch[i]), 1), "cr": round(float(self.chasis_roll[i]), 1),
            "eg": round(float(self.err_gmb[i]), 1),
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
