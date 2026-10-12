# -*- coding: utf-8 -*-
"""
Fase 2 de la misión (IA activada en la zona), vectorizada en NumPy · V15 (plan docs/PLAN_V15_CURRICULO.md).

V15 · FASE A (sensores y mundo): LiDAR TF03 a 30 m con 10 rayos por paso (100 Hz); 360° de entrada BAJO (2.5 m, cámara
-3°, con guarda) y 360° de búsqueda ALTO (altura segura); cansancio del ladrón (velocidad crítica + reserva D' + pulso);
cuerpo de las personas con estadística colombiana y altura segura del dron sacada del alcance saltando; muros con grosor;
detección parcial probabilística por alto y ancho del cuerpo.
V15 · FASE B (predicción): filtro de KALMAN (posición, velocidad y aceleración) con el ladrón a la vista; FILTRO DE
PARTÍCULAS (NP_PF hipótesis con la cinemática humana, que no atraviesan muros) sin verlo, con INFORMACIÓN NEGATIVA (las
que la cámara ve vacías se borran): lo que sobrevive es "detrás del muro", "debajo de mí" o "siguió por allá". La búsqueda
usa la nube (muro, esquina y sentido del giro); REFLEJO ANTI-CENIT predictivo (gira hacia el punto de salida) y
DISTANCIA ADAPTATIVA (si el ladrón se acerca rápido, la separación sube a la que permite frenar sin que se meta debajo).
V15 · FASE C (identidad): cuando el objetivo y otra persona se superponen en la imagen, el tracker puede CAMBIARSE de
persona (más si visten parecido y se mueven parecido). La percepción del dron sigue a quien el tracker cree que es el
objetivo (columna 0 = la persona seguida), así que un cambio no detectado lo hace seguir a otro. Tras un cruce, si la
apariencia no cuadra, si se cruzó con alguien parecido o si el Kalman rechaza mediciones, pasa a RECONFIRMAR: hover con
el objetivo en cuadro y pregunta al operador (humano en el lazo: decide él, nunca la IA).
V15 · FASE D (secuencia tras el muro, D2): 1) detrás del muro por el lado por donde se proyectó que se escondió, con un
barrido de GIRO_LADO hacia ese lado; 2) si no está, al OTRO extremo del muro y lo mismo; 3) si no está, MURO DE CANTO: en
la prolongación del muro, a A_CANTO de una punta, mirando a lo largo (de canto el muro es un palito y se ven las dos
caras), 1 m al lado de la predicción y 1 m al otro en una pasada; 4) si no, 360° de búsqueda y lo de siempre. En cualquier paso, si lo ve,
PERSECUCIÓN (interrupción táctica).
V15 · FASE E: la misión se cumple cuando el ladrón SE RINDE: un CONTADOR CONTINUO suma mientras lo sigue a la vista, se
pausa en parpadeos, memoria del tracker, PÉRDIDA y RECONFIRMAR, y vuelve a cero al pasar a la búsqueda (flanqueo, giros,
siguiente obstáculo, altura, canto). Se rinde a los T_rinde = 20 s + 100 s x reserva. Tope de 5 minutos: sin rendición
pierde el dron. Currículo de 5 niveles: 0 duelo abierto, 1 duelo con civil, 2 muro, 3 muro y civil, 4 misión completa
(3-4 muros). En los niveles 0 y 1 el ladrón solo huye y se esconde; ataca desde el 2.

V14 · CURRÍCULO PROGRESIVO: cada partida se genera en un NIVEL (current_level lo sube el entrenamiento cuando el dron
domina el actual; una fracción p_repaso de partidas repasa niveles ya superados para que no los olvide):
  0 DUELO ABIERTO     sin muros ni civiles; el ladrón huye en zigzag y a veces se mete debajo del dron (cenit)
  1 MURO ÚNICO        un muro central; el ladrón táctico se esconde detrás cruzando por sus bordes
  2 RUIDO VISUAL      un muro y un civil que se cruza una y otra vez en la línea de vista dron-ladrón
  3 MISIÓN COMPLETA   el escenario de siempre (2 muros, 0-2 peatones, ladrón táctico o aprendido, intensidad variable)

V13 · sobre la V12: (1) CURRÍCULO: una fracción de las partidas es el escenario simplificado "Un Solo Muro"; (2) GIRO_360
a 2.5 m con el gimbal en 0° (el LiDAR y la cámara barren el horizonte) a 90°/s, con el tope RATE_Y_MAX = 120°/s de la
Pixhawk; (3) INTERRUPCIÓN TÁCTICA: si YOLO detecta al ID designado en cualquier estado de búsqueda, se pasa a PERSECUCIÓN
en ese mismo cuadro; (4) STAND-OFF trigonométrico: el punto de flanqueo se calcula con el FOV para que el cono de la
cámara cubra la franja oculta detrás del muro; (5) DETECCIÓN PARCIAL: basta que asome el 15 % del bounding box.

V12 · CONTROL JERÁRQUICO HÍBRIDO (sobre la base v8-v11 que se describe más abajo):
  · Capa física (no aprende): PID de ArduPilot y del gimbal BaseCam (control.py). La red no estabiliza nada.
  · Capa táctica (aprende): la política PPO decide SOLO con el objetivo fijado (PERSECUCIÓN) y solo se le cobra el
    jitter de lo que ella misma comanda (avance, giro pedido); lo que mueve el seguimiento automático no es su culpa.
  · Capa determinista (reglas auditables): REFLEJO DE PUNTO CIEGO (si el objetivo va a quedar debajo del dron, fuera del
    cuadro con el gimbal en su tope de -45°, retrocede d = h / tan(45° + VFOV/2) + margen) y la BÚSQUEDA CON MEMORIA
    ESPACIAL: PERSECUCIÓN -> PÉRDIDA -> FLANQUEO_PROFUNDO -> GIRO_360 -> SIGUIENTE_OBSTÁCULO -> ... -> ALTURA_TÁCTICA ->
    MISIÓN_PERDIDA (T_MISION_PERDIDA s), usando la nube de puntos del LiDAR (raycasting) para elegir muros y rutas.

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

from control import AutopilotoArduPilot, GimbalBaseCam

# ----------------------------------------------------------------------------- sensores
DT = 0.1
HFOV = 38.9
VFOV = 29.7
ALTO_IMG = 480.0
ALTURA_PERSONA = 1.72            # V15: estatura que SUPONE la Jetson para estimar la distancia por el bbox (la media)
# V15 · CUERPO DE UNA PERSONA COLOMBIANA (D7): estatura de cada persona ~ N(1.72, 0.07) m entre 1.58 y 1.88 (NCD-RisC
# 2019: hombres 171.9 cm). Alcance de pie (brazo arriba) = 1.33 x estatura; salto de un adulto no entrenado 0.30-0.50 m;
# hombros 0.45 m. La ALTURA SEGURA del dron sale del alcance saltando del percentil 99 + 0.3 m de margen.
ESTATURA_MEDIA, ESTATURA_SD, ESTATURA_MIN, ESTATURA_MAX = 1.72, 0.07, 1.58, 1.88
K_ALCANCE_PIE = 1.33
SALTO_ADULTO = (0.30, 0.50)
ANCHO_HOMBROS = 0.45
Z_SEGURA = round(max(3.0, K_ALCANCE_PIE * min(ESTATURA_MEDIA + 2.326 * ESTATURA_SD, ESTATURA_MAX) + SALTO_ADULTO[1] + 0.3), 2)
RADIO_PERSONA = 0.25

# ----------------------------------------------------------------------------- dron
N_CONFIRMACION = 3
DURACION_EVASION = 1.5
ENFRIAMIENTO = 1.0
VEL_LATERAL = 1.5
VEL_ASCENSO = 0.7
TAU_DRON = 0.35
ACC_MAX_DRON = 4.0
J_MAX_DRON = 5.0               # m/s³: limitador de jerk del autopiloto (como PSC_JERK_XY de ArduPilot, 5 por defecto)
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
Z_NOMINAL, Z_MIN, Z_MAX = Z_SEGURA, 1.8, 7.0   # V15: la altura nominal (seguir, verificar) es la segura (3.30 m)
Z_REF_OBS = 2.3                # referencia de altura en las observaciones (la de la V14: las redes ya entrenadas la usan)
Z_PILOTO = 2.3                 # altura del vuelo manual del piloto en la fase 1 de la misión (antes de fijar)
# gimbal (pitch de la cámara; BaseCam por PWM desde AUX1, ±45°): hace el seguimiento VERTICAL
# LÍMITE FÍSICO DURO del pitch de la cámara (v9): nunca por debajo de -45° ni por encima de +15°, pase lo que pase
# (comando, filtro, cabeceo del chasis). En el dron real: pwm = 1500 + θ·500/45 con el mismo recorte (la BaseCam física solo cubre ±45°).
GIMBAL_MIN, GIMBAL_MAX = -45.0, 15.0
GIMBAL_NADIR = -45.0           # al sobrevolar un panel (recortado al límite duro)
GIMBAL_TACTICO = -45.0         # barrido desde la altura táctica (recortado al límite duro)
D_NADIR = 2.5                  # a menos de esto (horizontal) de un panel detectado, sobrevolando, se mira en nadir
GIMBAL_VEL, GIMBAL_KP = 30.0, 4.0   # v9: los motores brushless del gimbal giran a lo sumo 30°/s
# filtro físico del gimbal: EMA en la salida del actuador (el ángulo que se manda por PWM). Cada paso de 0.1 s la
# cámara recorre solo ALPHA_GIMBAL de lo que le falta (constante de tiempo ~0.45 s): no puede saltar de un cuadro al
# siguiente, elija lo que elija la política. El comando no se adelanta más de G_ADELANTO al ángulo físico (anti-windup).
ALPHA_GIMBAL = 0.2
G_ADELANTO = 15.0
GIMBAL_VEL_FISICA = 30.0       # °/s máximos del ángulo físico a la salida del EMA (aunque el comando sea extremo)
GIMBAL_BANDA = 0.10 * VFOV     # banda muerta vertical (20% central del FOV vertical)
GIMBAL_RECENTRA = 0.04 * VFOV
D_REPOSO = 8.0                 # sin nadie a quien seguir, la cámara mira al suelo a esta distancia
VEL_REGRESO_Z = 0.3

# ----------------------------------------------------------------------------- misión
BUSCAR, VERIFICAR, FIJADO, INVESTIGAR, ASOMO, VENTAJA_ALTURA, PREDECIR = 0, 1, 2, 3, 4, 5, 6
BUSQUEDA_IA = 7                # pérdida del objetivo con la política al mando (aprendizaje end-to-end)
# PÉRDIDA POR APRENDIZAJE: al perder el objetivo la política conserva el control de motores y gimbal (BUSQUEDA_IA) en
# vez del protocolo determinista (PREDECIR -> INVESTIGAR/flanqueo profundo -> ASOMO -> VENTAJA_ALTURA). Ve la última
# posición conocida, el tiempo sin verlo y el mapa del LiDAR, y aprende a buscar por el bono de re-adquisición.
# v11-hibrido: PERDIDA_IA = False (decisión D-015). Con True la política busca por aprendizaje y se compara con el protocolo.
PERDIDA_IA = False
# V12 · BÚSQUEDA DETERMINISTA CON MEMORIA ESPACIAL (SLAM). Estados en orden, con histéresis (tiempo mínimo en cada uno y
# ReID de N_REID cuadros para volver), así no oscila entre estados:
#   PERSECUCIÓN (FIJADO: la IA al mando) -> PÉRDIDA (PREDECIR: no se ve hace T_PRED_INI si corría o T_TRACKER si iba
#   lento; sigue su vector de escape) -> FLANQUEO_PROFUNDO (INVESTIGAR: detrás del muro donde se lo vio por última vez)
#   -> GIRO_360 (ASOMO: barrido que además completa el mapa del LiDAR) -> SIGUIENTE_OBSTÁCULO (el siguiente panel de la
#   memoria, sin revisar) -> GIRO_360 -> ... -> ALTURA_TÁCTICA (VENTAJA_ALTURA, gimbal en -45°) -> otra ronda con el
#   mapa ampliado -> MISIÓN_PERDIDA a los T_MISION_PERDIDA s sin recuperarlo.
SIGUIENTE_OBSTACULO = 8
RECONFIRMAR = 9                # V15 · fase C: duda de identidad, el operador confirma
MURO_CANTO = 10                # V15 · fase D: mirar el muro de canto corriéndose 1 m a cada lado (D-044)
NOMBRE_ESTADO = ["BUSCAR", "VERIFICAR", "PERSECUCION", "FLANQUEO_PROFUNDO", "GIRO_360", "ALTURA_TACTICA", "PERDIDA",
                 "BUSQUEDA_IA", "SIGUIENTE_OBSTACULO", "RECONFIRMAR", "MURO_DE_CANTO"]
BUSQUEDA_ESTADOS = (PREDECIR, INVESTIGAR, ASOMO, SIGUIENTE_OBSTACULO, VENTAJA_ALTURA, MURO_CANTO, RECONFIRMAR)   # C3
T_PERDIDA_LENTO = 1.0          # objetivo lento: s en PÉRDIDA (siguiendo su vector) antes del flanqueo
T_HISTERESIS = 1.0             # s mínimos en un estado de búsqueda antes de pasar al siguiente
T_MISION_PERDIDA = 90.0        # s sin recuperarlo desde que se perdió -> MISIÓN PERDIDA
K_OFFSET = (1.0, 1.5, 2.0)
# V13 · CURRÍCULO (entrenamiento modular): fracción de partidas con UN SOLO MURO (el segundo panel se superpone al
# primero). Baja del 30 % (nivel 0) al 10 % (nivel 1) a medida que el dron domina el flanqueo básico.
P_UN_MURO = (0.30, 0.10)          # (V13; en la V14 lo reemplazan los niveles del currículo)
# V14 · NIVELES DEL CURRÍCULO
NIVELES = ["Duelo abierto", "Duelo con civil", "Muro", "Muro y civil", "Misión completa"]     # V15 (D1)
NIVEL_ATAQUE = 2               # V15 (D6): desde este nivel el ladrón ataca (en 0 y 1 solo huye y se esconde)
MUROS_N4 = (3, 4)              # muros de la misión completa
# V15 · fase E: guardas de velocidad para partidas largas
MARGEN_CERCA = 1.5
A_CERCA, T_LAG_CERCA = 1.5, 0.5   # frenado efectivo del dron (cascada con jerk limitado) y su retardo, medidos             # geocerca tipo ArduPilot (FENCE + AVOID): frena para no pasar de ARENA - esto
R_PERSONA_MEM, T_PERSONA_MEM = 2.5, 3.0   # no se mueve hacia alguien visto hace menos de T_PERSONA_MEM s a menos de esto
N_NIVELES = len(NIVELES)
P_CENIT_N0 = 0.3               # nivel 0: partidas en que el ladrón intenta meterse debajo del dron (el resto huye)
L_GUION_TACTICO, L_GUION_HUIDA, L_GUION_CENIT = 0, 1, 2
P_REVERSA = 0.25               # huida: probabilidad de que el siguiente cambio de rumbo sea un giro de 180° (cambio brusco)
T_RUMBO_HUIDA = (2.5, 5.0)     # s entre cambios de rumbo de la huida en zigzag
ANCHO_DISTRACTOR = 3.0         # m a cada lado de la línea de vista que recorre el civil distractor (nivel 2)
F_CRUCE_DISTRACTOR = 0.65      # cruza la línea de vista a este tanto del camino dron -> ladrón (más cerca del ladrón)
D_RESPETO_CIVIL = 3.0          # un civil real no camina hacia un dron: su recorrido queda a más de esto del dron
LEJOS_PANEL = 60.0             # nivel 0: los paneles quedan fuera de la arena (el LiDAR no llega)
# V13 · GIRO_360 óptimo: altura y pitch FIJOS durante todo el giro; gira a YAW_GIRO_360 (9°/cuadro a 10 Hz: cada persona
# queda ~4 cuadros en el FOV horizontal de 38.9°, sin desenfoque), nunca más rápido que RATE_Y_MAX (control.py).
# Pedido original: 2.5 m y gimbal en 0°. Medido con la política de la V12 (192 entornos x 150 s, misma semilla):
#     2.5 m / 0°   -> cumplida 39 %, ALCANZADO 48 %  (dentro del salto del ladrón, 2.5-2.7 m, y por debajo de Z_ATAQUE;
#                                                     con la cámara horizontal no ve a nadie a menos de ~4 m)
#     3.0 m / 0°   -> cumplida 56 %, alcanzado 17 %  (el rayo del LiDAR pasa por encima de los muros de 2.6 m: no mapea)
#     3.0 m / -15° -> cumplida 67 %, alcanzado 18 %, panel 3 %  (el borde superior de la imagen queda en el horizonte; el
#                                                     LiDAR toca los muros entre 1.5 y 11 m; ve personas desde 2.7 m)
# Se dejan los valores de la última fila. Para el pedido original exacto: Z_GIRO = 2.5 y GIMBAL_GIRO = 0.0.
Z_GIRO = 3.0
GIMBAL_GIRO = -15.0
# V15 (D5): el 360° de BÚSQUEDA va a la altura segura. Cámara a -12° (fase D): con -8° (fase A) no ve a nadie a menos de
# ~4.4 m, justo donde queda el ladrón escondido detrás de un muro visto desde el punto de flanqueo; a -12° mapea muros de
# 3.3 a 15.5 m (los lejanos ya los mapeó la vuelta de entrada) y ve cabezas desde 3.6 m. Comparado en
# informes/evaluacion_v15-fase-A.md (-8 vs -15 en los niveles: igual) y evaluacion_v15-fase-D.md (-8/-12/-15 tras el muro)
Z_GIRO = Z_SEGURA
GIMBAL_GIRO = -12.0
YAW_GIRO_360 = 90.0
T_ESPERA_GIRO = 2.0
R_DESPEJE = 1.2                # V13: a menos de esto (horizontal) de un muro o de un punto de la nube no baja de Z_TRANSITO            # si no puede bajar a Z_GIRO (alguien cerca, despeje), empieza a girar igual a los 2 s
# V13 · INTERRUPCIÓN TÁCTICA: en cualquier estado de búsqueda, la detección de YOLO del ID designado cancela la búsqueda
INTERRUPCION = True
# V13 · STAND-OFF TRIGONOMÉTRICO: detrás del muro hay una franja oculta de D_ZONA_OCULTA de fondo (donde se agacha
# alguien pegado a la pared). Para que el cono horizontal de la cámara la cubra entera mirando a lo largo del muro desde
# su esquina, el punto queda a b = D_ZONA_OCULTA/2 detrás del plano del muro y a a = b / tan(HFOV/2 - margen) por fuera
# de la esquina: ~2.4 m y 0.8 m (2.5 m en diagonal).
D_ZONA_OCULTA = 1.6
MARGEN_FOV = 1.0               # ° que se quitan al semiángulo del FOV (el borde de la imagen detecta peor)     # offset táctico en la esquina: se prueban separaciones crecientes antes de volar por encima
T_BUSQUEDA_IA = 60.0           # s buscando sin re-adquirirlo -> misión fallida (v9: 20 -> 60 s, margen para revisar
                               # varios muros como un operador real; perderlo ya no termina la misión)
VEL_IA_AVANCE, VEL_IA_LATERAL = 3.0, 1.5     # m/s de las consignas de avance y desplazamiento lateral
PASO_Z_IA, PASO_GIMBAL_IA = 0.15, 3.0        # por paso (0.1 s): 1.5 m/s de subida/bajada y 30°/s del gimbal
N_SECT, R_SECT = 8, 8.0        # mapa local del LiDAR para la IA: 8 sectores alrededor del dron, hasta 8 m
# MAPA DESCUBIERTO (nube de puntos persistente, SLAM básico): los impactos del LiDAR en coordenadas absolutas (X, Y) se
# guardan toda la misión (giro de 360° incluido) y entran a la red como una grilla de ocupación de GRID_N x GRID_N celdas
# de GRID_CELDA m alrededor del dron, alineada con su rumbo (filas: atrás -> adelante; columnas: derecha -> izquierda)
GRID_N, GRID_CELDA = 12, 1.5
D_DEDUP_LIDAR = 0.3            # un impacto a menos de esto de uno ya guardado no se repite (el mapa no se satura)
B_GIRO, B_TRANSITO, B_INSPECCION = 0, 1, 2      # subfases de BUSCAR (giro, vuelo a un panel, barrido detrás de él)
T_OPERADOR = (1.0, 2.0)        # s que tarda el operador en responder SÍ / NO
T_VER_MIN = 0.5                # s de video que necesita el operador para decidir (aunque la persona se esconda después)
T_ESPERA_CLIC = 3.0            # sin clic del operador en este tiempo, ese ID queda descartado
T_BUSQUEDA_MAX = 60.0          # sin lock-on en este tiempo: misión fallida (no encontrado)
T_RASTREO = 30.0               # (hasta la V14: rastreo acumulado para cumplir; la V15 usa la rendición)
# V15 · FASE E · RENDICIÓN (D3): el contador continuo llega a T_RINDE_BASE + T_RINDE_RESERVA x reserva del ladrón
T_RINDE_BASE, T_RINDE_RESERVA = 20.0, 100.0
# D-041 (arquitecto; idea de Brahian: "que el dron sea tan lógico que el ladrón se dé por vencido"): MORAL del ladrón.
# Cada vez que el dron lo vuelve a encontrar tras esconderse (el mismo evento que cobra R_DESCUBRE) su moral baja
# x K_MORAL (mínimo MORAL_MIN); T_rinde = T_RINDE_BASE + T_RINDE_RESERVA x reserva x moral.
K_MORAL, MORAL_MIN = 0.8, 0.3
# C1 (diagnóstico del nivel 4; Brahian eligió 4 s, no 8: más tiempo premiaría que el ladrón se muestre por error): si el dron
# lo re-adquiere a lo sumo T_PAUSA_REID s después de perderlo, el contador continuo se PAUSA aunque haya pasado a un estado
# de búsqueda; pasado ese tiempo vuelve a cero como antes
T_PAUSA_REID = 4.0
# C3: custodia (caso policial: no perderlo hasta que llegue la patrulla): vista acumulada en la partida de 5 min de al
# menos estos segundos, o el ladrón se rindió
CUSTODIA_S = (60.0, 90.0)
T_TRACKER = 1.0                # s que el tracker conserva el ID sin verlo
N_REID = 4                     # cuadros confirmando la apariencia para re-adquirirlo
# V13 · DETECCIÓN PARCIAL: YOLO detecta a una persona aunque solo asome la cabeza. Se muestrea su cuerpo en N_MUESTRAS
# alturas; si al menos FRAC_DET_MIN de su bounding box queda dentro de la imagen y sin tapar por un muro, cuenta
N_MUESTRAS_PERSONA = 8         # V15: 8 alturas x 3 anchos (antes 12 alturas): misma resolución, menos cómputo
FRAC_DET_MIN = 0.15
Z_TRANSITO = max(3.2, Z_SEGURA)  # vuelos de inspección e investigación por encima de los paneles (V15: y del salto)
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
# v9: ATAQUE DEL LADRÓN ACORRALADO Y SALTO. Si el dron baja de Z_ATAQUE y el ladrón está acorralado (el dron cerca y su
# huida bloqueada por un muro o el borde a menos de 2 m), corre hacia el dron (TASA_ACORRALADO por s) y, a menos de
# D_SALTO, salta: alcance de pie ALCANCE_PIE (brazo arriba) y en el salto entre 2.5 y 2.7 m durante T_SALTO.
Z_ATAQUE = Z_SEGURA            # V15: por debajo de la altura segura el ladrón puede intentar alcanzarlo
TASA_ACORRALADO = 0.8
D_ACORRALADO = 8.0
D_SALTO = 1.4
ALCANCE_PIE = 2.2
ALCANCE_SALTO = (2.5, 2.7)
T_SALTO, T_RECARGA_SALTO = 0.5, 1.5
# V12 · REFLEJO DE PUNTO CIEGO. Con el gimbal en su tope físico (-45°) el borde inferior de la imagen mira a
# -(45° + VFOV/2) = -59.9°: a una altura h, todo lo que esté a menos de d = h / tan(45° + VFOV/2) en horizontal queda
# DEBAJO del cuadro. Si el objetivo (su posición o su vector de escape) entra en esa zona, el dron da un paso táctico hacia
# atrás hasta d + MARGEN_CIEGO y gira hacia él si salió del cuadro. Histéresis: se apaga a d + MARGEN_CIEGO + HIST_CIEGO.
MARGEN_CIEGO = 1.0
HIST_CIEGO = 0.5
VEL_CIEGO = 4.5                # m/s máximos del reflejo (retroceso + la velocidad del objetivo; = VEL_PERSEGUIR)
T_CIEGO_EXTRA = 2.0            # la PÉRDIDA se alarga hasta esto mientras el reflejo siga apartando al dron
K_CIEGO = 1.5
LIDAR_MAX = 30.0               # V15: TF03-100, 30 m con objetivo oscuro (10 %) a pleno sol (antes 20 m)
RAYOS_POR_PASO = 10            # V15: el TF03 mide a 100 Hz: 10 rayos en cada paso de 0.1 s, repartidos en el giro
# V15 · MUROS CON GROSOR (antes eran líneas): tapan la vista y chocan como una caja de este grosor
GROSOR_MURO = 0.2
# V15 · DETECCIÓN PARCIAL PROBABILÍSTICA: el cuerpo se muestrea en alto (N_MUESTRAS_PERSONA) y ancho (OFFS_ANCHO); la
# probabilidad de detección sube de 0 (P_FRAC[0] visible) a la de la persona entera (P_FRAC[1] visible)
OFFS_ANCHO = (-1.0, -0.55, 0.0, 0.55, 1.0)      # columnas, en fracciones del medio ancho del cuerpo a cada altura


def medio_ancho(fh):
    """Medio ancho del cuerpo según la fracción de la estatura: piernas juntas (~0.26 m), torso con los hombros
    (ANCHO_HOMBROS = 0.45 m) y cabeza (~0.18 m)."""
    return np.where(fh < 0.5, 0.13, np.where(fh < 0.85, ANCHO_HOMBROS / 2, 0.09))
P_FRAC = (0.05, 0.35)
# V15 · CANSANCIO DEL LADRÓN (velocidad crítica de Monod y Scherrer; balance de la reserva W' de Skiba et al. 2012):
# por encima de VC gasta la reserva D'; por debajo la recupera despacio. Con la reserva baja ya no esprinta (trota), se
# esconde más y ataca menos. El PULSO es para el visor y la narrativa: el dron no lo observa.
# D-041 (arquitecto): adulto no entrenado y bajo tensión. VC 3.0 -> 2.5 m/s, D' 150 -> 120 m; la tensión de huir gasta
# reserva (K_TENSION m/s equivalentes mientras está alerta y moviéndose) y, expuesto a la cámara mientras cambia de
# cubierta, ESPRINTA a V_SPRINT (ráfagas limitadas por la stamina de 2 s), como alguien que huye de verdad.
VC_LADRON = 2.5                # m/s
D_PRIMA = 120.0                # m
K_TENSION = 0.12               # m/s de gasto extra por la tensión (alerta y moviéndose)
V_SPRINT = (4.2, 5.0)          # m/s del esprint (por partida); solo con reserva > 0.25
TAU_RECUPERA = 400.0           # s de la recuperación exponencial de la reserva
V_TROTE = 2.5                  # m/s: sin reserva solo trota
PULSO_REPOSO, PULSO_ESTRES, PULSO_MAX, TAU_PULSO = 70.0, 30.0, 190.0, 30.0
# V15 · 360° (D5): el de ENTRADA (el primero, al llegar a la zona) BAJO para mapear todos los muros de 0 a 30 m; si
# alguien entra a menos de R_GUARDA_ENTRADA o se acerca rápido, sube a la altura segura y termina la vuelta arriba
Z_ENTRADA, GIMBAL_ENTRADA, R_GUARDA_ENTRADA = 2.5, -3.0, 6.0
D_NACE_CIVIL = 6.5            # D-041: distancia mínima del dron a la que nace un civil
# V15 · FASE B · predicción
KF_Q = 8.0                     # densidad del jerk del modelo de aceleración del Kalman ((m/s³)²·s): una persona cambia
                               # de aceleración rápido (frenazos, cortes)
NP_PF = 200                    # partículas por dron
A_PF, V_PF_MAX = 2.0, 4.0      # aceleración aleatoria (m/s²) y rapidez máxima (m/s) de cada hipótesis
W_VISTO = 0.05                 # peso que conserva una partícula que la cámara ve sin que YOLO detecte a nadie
N_PF_VISOR = 40                # partículas que se mandan al visor (muestra)
MASA_MURO = 0.25               # masa mínima detrás de un muro para elegirlo por probabilidad
MASA_DIRECTO = 0.6             # (fase D) con esta masa detrás de un muro conocido, la PÉRDIDA pasa directo al flanqueo
A_FRENO_DRON = 2.5             # m/s² con que el dron iguala la velocidad de un ladrón que se le acerca (jerk incluido)
T_LAG_DRON = 0.5               # s de retardo hasta empezar a apartarse
D_SEP_MAX = 7.0                # tope de la separación adaptativa
T_CENIT = 1.2                  # s: si va a entrar a la zona ciega antes de esto, gira hacia el punto de salida
# V15 · FASE C · identidad
DIM_APARIENCIA = 8             # vector de apariencia de cada persona (ropa, contextura): lo que compara el ReID
SIM_CIVIL = (0.2, 0.97)        # parecido (coseno) de un civil con el ladrón: a veces visten casi igual
P_CAMBIO = 0.3                 # probabilidad por cuadro de saltar a otra persona superpuesta, con parecido y movimiento iguales
V_DIF_ID = 2.0                 # m/s de diferencia de velocidad que hacen el cambio casi imposible (el Kalman los separa)
T_CRUCE = 3.0                  # s después de un cruce en que se vigila la identidad
UMBRAL_SIM = 0.85              # ReID (promediado): por debajo de esto, "no se parece a quien designó el operador"
UMBRAL_PARECIDO = 0.8          # cruzarse con alguien así de parecido obliga a reconfirmar
DUDA_KALMAN = True             # también duda si, tras un cruce, el Kalman rechaza mediciones
# V15 · FASE D · secuencia tras el muro
GIRO_LADO = 180.0              # ° del barrido detrás del muro (pasos 1 y 2), empezando hacia la zona oculta
A_CANTO = 6.0                  # m del punto de canto a la punta del muro (ve las dos caras a la vez)
# V15 · canto con desplazamiento lateral: de canto puro a 6 m al ladrón detrás de la punta le asoma poco (cálculo 2D: 24 %
# del cuerpo con muro de 4 m, 7 % con 6.5 m); corriéndose ~1 m a un lado se ve ~1/3. Secuencia de una sola pasada, con la
# nariz siempre a lo largo del muro: centrado -> DESPL_CANTO a un lado (primero el que diga la predicción) -> al otro.
DESPL_CANTO, VEL_CANTO, T_ALINEA_CANTO = 1.0, 1.0, 1.5      # m a cada lado, m/s de tope lateral, s centrado
T_LADO1_CANTO, T_LADO2_CANTO = 2.5, 3.0                     # s hacia el primer lado (1 m) y hacia el otro (2 m)
T_CANTO = T_ALINEA_CANTO + T_LADO1_CANTO + T_LADO2_CANTO
VEL_INVESTIGA = 4.0            # V15 · fase D: 3.0 -> 4.0 m/s (la guarda del mapa frena cerca de los muros)
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
Z_FLANCO = Z_SEGURA            # (V15: altura segura) el flanqueo se vuela fuera del alcance del ladrón (2.6 m) y justo sobre los paneles (2.6 m):
                               # a 2.3 m, al rodear la esquina pasaba junto al escondite y lo tumbaban (42% en las pruebas)
# mapa de obstáculos con el LiDAR (rayo frontal): impactos guardados y su agrupación en paneles
N_LIDAR = 512                  # v9: 128 -> 512 puntos (mapa descubierto de toda la misión)
D_CLUSTER = 1.0
LARGO_MIN_PANEL = 1.0
K_DET = 4
# guarda del mapa: con el LiDAR solo al frente, en la persecución o la predicción el dron puede moverse hacia un panel
# que no está mirando. Los impactos guardados funcionan como un muro virtual: la velocidad de acercamiento a cada
# punto se limita a la que permite frenar antes de R_PARADA contando el tiempo que tarda en llegar a esa
# desaceleración por el limitador de jerk: v²/(2·A_GUARDA) + v·T_GUARDA <= d - R_PARADA
R_GUARDA = 6.0                 # solo cuentan los impactos a menos de esto (a 4.5 m/s hacen falta ~6 m para frenar)
T_GUARDA = 0.2                 # s de retardo base; se suma el de pasar de la aceleración actual hacia el punto a frenar
                               # con el limitador de jerk: (A_GUARDA + a_hacia) / (2·J_MAX_DRON)
R_PARADA = 0.75 + 0.1          # distancia (centro del dron al eje del panel) donde la velocidad de acercamiento llega a 0 (V15: + medio grosor del muro)
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
# MODELO BIOMECÁNICO (versión master): (1) círculo de fricción: la aceleración horizontal total del pie contra el piso
# no supera MU_PISO·g, así que el giro (a_lat = v·ω) y la aceleración longitudinal se reparten ese presupuesto; el
# radio de giro mínimo es r = v² / (MU_PISO·g): a toda carrera no puede girar 90° en el sitio, tiene que frenar.
# (2) propulsión tipo Hill/Furusawa: arranca con A_PROPULSION y la fuerza cae con la velocidad (v(t) = V_TOPE·(1-e^-t/τ)):
# nadie pasa de 0 a 3 m/s en una décima. (3) para cambiar mucho de rumbo baja la velocidad de forma continua.
MU_PISO = 0.6
A_PROPULSION = 4.0
V_TOPE_HUMANO = 5.0
# PATHFINDING: grafo de visibilidad con las esquinas de cada muro alargadas E_NODO (ruta más corta exacta entre muros)
E_NODO = 0.9
STAMINA_MAX = 2.0
ALCANCE_H = 1.0
ALCANCE_Z = 2.6
FRAC_LADRON_RL = 0.3           # partidas de entrenamiento con el ladrón aprendido (autojuego)
L_DEAMBULAR, L_CUBRIRSE, L_ESCONDIDO, L_ASOMARSE, L_ATACAR = 0, 1, 2, 3, 4
T_ESCONDIDO = (2.0, 6.0)
T_ASOMARSE = (1.5, 3.0)
T_ATAQUE = 3.0
# v9: NAVEGACIÓN POR CAMPOS POTENCIALES (APF) de las personas: sienten cada muro a menos de R_APF con un peso
# w = (1/d - 1/R_APF) / (1/D_MIN_APF - 1/R_APF) (0 lejos, 1 pegadas); la parte del movimiento hacia el muro se frena
# y se convierte en flujo tangencial (K_TAN_APF) hacia donde ya iban o hacia el extremo más cercano
R_APF = 2.0
D_MIN_APF = 0.45
K_TAN_APF = 1.0

# ----------------------------------------------------------------------------- escenario
N_PANELES = 4                  # V15: hasta 4 muros (nivel 4); en los demás niveles los que sobran se superponen
ALTO_PANEL = 2.6
RADIO_DRON = 0.4
ARENA = 25.0
PASOS_EPISODIO = int(300.0 / DT)   # V15: tope de 5 minutos; sin rendición, pierde el dron

# ----------------------------------------------------------------------------- recompensas
R_COLISION = -10.0
R_CHOQUE_PANEL = -5.0
R_GEOCERCA = -5.0
R_PERDIDO = -5.0               # misión fallida: protocolo agotado (o nunca se fijó al sospechoso)
R_PIERDE = -8.0                # el tracker suelta el ID (igual y opuesto a R_DESCUBRE: perderlo a propósito para
                               # cobrar el bono no rinde)
R_DESCUBRE = 8.0               # V12: DISCOVERY BONUS masivo (3 -> 8, más que el éxito): el ladrón vuelve a entrar en el FOV
                               # después de haber estado oculto más de T_OCULTO_DESC; una vez por ocultamiento.
T_OCULTO_DESC = 1.0
R_EXITO = 5.0                  # misión cumplida (base)
R_EXITO_RESTANTE = 0.25        # C2: + esto por cada segundo que falte para el tope: rendirlo antes nunca vale menos que
                               # seguir mirando (0.25/s ≈ lo que cobra mirando con ~50 % de vista)
R_TOPE = -5.0                  # C2: el tope de 5 min sin rendición es TERMINAL (pierde el dron) y cuesta esto
R_MANIOBRA = {1: -0.15, 2: -0.15, 3: -0.30}
R_VISTA = 0.03                 # por cada paso con el objetivo fijado a la vista
R_RANGO = 0.02                 # además, si está en la distancia óptima (3.5 a 5 m)
R_MUY_CERCA = -0.02            # y castigo si está a menos de 3 m (se sale del encuadre o lo sobrevuela)
# SUAVIDAD DEL CONTROL (reward shaping): la política aprende sola a no volar de forma errática, en vez de depender solo
# de filtros fijos. Cuenta únicamente con la IA al mando (FIJADO y sin maniobra). Los tres comandos que salen de la
# Jetson, normalizados a su máximo: cabeceo del chasis (la actitud que el autopiloto debe tomar para la velocidad
# pedida), guiñada del dron y velocidad del pitch del gimbal.
# v9: multa severa (x15 y x10 respecto de v8, 0.01 y 0.003): con el bono de re-adquisición de +3 la política v8
# prefería pagar la multa y moverse a saltos (jitter 0.042/s, esfuerzo 0.014/s con la IA al mando)
K_DELTA = 0.15                 # derivada: K·Σ|u(t) - u(t-1)| (un salto de extremo a extremo en un eje = 2 -> -0.30)
K_ESFUERZO = 0.03              # esfuerzo: K·Σ|u(t)|, continuo (con el ladrón centrado y vuelo estable vale 0)
CAB_MAX = float(np.degrees(np.arctan(ACC_MAX_DRON / G)))     # 22.2°: el cabeceo a la aceleración máxima
# Guía (reward shaping basado en potencial, Ng et al. 1999), solo en FIJADO: premia apuntar la nariz al
# objetivo y no alejarse de él. Usa su posición real SOLO para calificar; no es una entrada del dron.
GAMMA_GUIA = 0.99
K_GUIA_ANG, K_GUIA_DIST = 0.3, 0.03
# V12 · recompensa por componente (info["r_comp"], columnas en este orden; su suma es la recompensa del dron)
R_COMP = ["vista", "guia", "descubre", "pierde", "maniobra", "exito", "fallas", "control"]
EJES_U = ["cabeceo", "guinada", "gimbal"]

# en BUSQUEDA_IA las acciones son consignas que persisten: AVANZAR / EVADIR_IZQ / EVADIR_DER / MANTENER fijan la
# velocidad horizontal (adelante, lateral, hover), DETENER_ASCENDER y DESCENDER mueven la altura objetivo, GIRAR_* giran
# mientras se eligen y GIMBAL_* mueven el pitch de la cámara. Con el objetivo fijado, 7-9 no tienen efecto.
CLASES = ["MANTENER", "EVADIR_IZQ", "EVADIR_DER", "DETENER_ASCENDER", "GIRAR_IZQ", "GIRAR_DER", "AVANZAR",
          "DESCENDER", "GIMBAL_ARRIBA", "GIMBAL_ABAJO"]
OFFSETS_PERSONA = np.radians([0, 30, -30, 60, -60, 90, -90, 180])
N_ACC_PERSONA = len(OFFSETS_PERSONA) * 2 + 1
GUIONES = ["cruce", "directo", "quieto", "alejarse", "acercar_y_parar", "trotar_directo", "deambular", "distractor"]
P_GUION = [0.15, 0.10, 0.10, 0.05, 0.05, 0.05, 0.50, 0.0]
G_DISTRACTOR = 7               # V14 (nivel 2): civil que cruza una y otra vez la línea de vista dron-ladrón

OBS_DRON = 21 + 7 + N_SECT + 2 + 10 + GRID_N * GRID_N
# + memoria espacial (perdido, última posición x/y, tiempo sin verlo, gimbal, su último vector de movimiento x/y)
# + sectores del LiDAR + v9: dónde estaría ahora el ladrón si siguió igual (x/y), estado propio del dron (velocidad,
# aceleración, vertical, guiñada, consignas de la búsqueda) y la grilla del mapa descubierto
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


def stand_off_fov():
    """(a, b): distancia por fuera de la esquina y por detrás del plano del muro del punto de flanqueo V13."""
    b = D_ZONA_OCULTA / 2.0
    return b / np.tan(np.radians(HFOV / 2.0 - MARGEN_FOV)), b


def d_punto_ciego(h):
    """Radio horizontal de la zona ciega debajo del dron a la altura h (gimbal en su tope de -45°) más el margen."""
    return h / np.tan(np.radians(-GIMBAL_MIN + VFOV / 2.0)) + MARGEN_CIEGO


def dist_nube_segmento(P, a, b):
    """RAYCASTING sobre la nube de puntos: distancia mínima de los puntos P (m, 2) del LiDAR al tramo a->b."""
    if len(P) == 0:
        return np.inf
    return float(dist_punto_segmento(P, a[None], b[None])[0].min())


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

    # V14: nivel del currículo con que nacen los entornos nuevos (el entrenamiento lo actualiza para que las repeticiones
    # se graben en el nivel actual) y fracción de repaso de niveles anteriores (solo la usa el entorno de entrenamiento)
    nivel_inicial = N_NIVELES - 1
    p_repaso_inicial = 0.0

    def __init__(self, n, semilla=0, nivel=None):
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
        self.gimbal = np.full(n, -10.0)                  # pitch del gimbal (°, negativo = hacia abajo): ángulo físico
        self.gimbal_cmd = np.full(n, -10.0)              # lo que pide la lógica o la IA (antes del filtro EMA)
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
        self.u_prev, self.mando_prev = z(3), zb()
        self.acc_x, self.acc_y = z(), z()                # aceleración horizontal real (limitada en jerk)
        self.salto_t, self.salto_cd, self.salto_alc, self.salto_h = z(), z(), z(), z()   # salto del ladrón
        self.v_ia_f, self.v_ia_l, self.z_ia, self.g_ia = z(), z(), z(), z()     # consignas de la búsqueda por IA
        self.arm_desc, self.descubre = zb(), zb()                               # bono de re-adquisición armado / cobrado
        # V12: tiempo oculto (discovery), tiempo desde la pérdida (90 s), duración de la PÉRDIDA, reflejo de punto ciego,
        # mínimo del gimbal en la partida y comandos completos del paso anterior (jitter físico por eje)
        self.t_oculto, self.t_perdida, self.t_pred_dur = z(), z(), np.full(n, T_PREDICCION)
        self.ciego, self.d_ciego, self.gmb_min_ep, self.u_prev_fis = zb(), z(), np.full(n, -10.0), z(3)
        self.un_muro = zb()                              # V13: partida del currículo "Un Solo Muro"
        # V14 · currículo: nivel del entrenamiento, nivel de cada partida, repaso y guiones del ladrón y del civil
        self.current_level = int(EntornoDronPersona.nivel_inicial if nivel is None else nivel)
        self.p_repaso = float(EntornoDronPersona.p_repaso_inicial)
        self.p_cenit = P_CENIT_N0
        self.lvl_ep = np.full(n, self.current_level)
        self.l_guion, self.l_ang, self.l_tg = zi(), z(), z()
        # V15 · fase A: cuerpo de cada persona, cansancio del ladrón, 360° de entrada y rumbo del rayo anterior
        self.estatura = np.full((n, N_PERS), ESTATURA_MEDIA)
        self.alc_pie = np.full(n, K_ALCANCE_PIE * ESTATURA_MEDIA)
        self.reserva, self.pulso = np.ones(n), np.full(n, PULSO_REPOSO)
        self.v_corr_ef = np.full(n, VEL_CORRER)
        self.entrada, self.entrada_alta = zb(), zb()
        self.lid_psi_prev = z()
        # V15 · fase B: Kalman (por eje: posición, velocidad, aceleración) y filtro de partículas
        self.kf_x, self.kf_P, self.kf_ok = np.zeros((n, 2, 3)), np.tile(np.eye(3), (n, 2, 1, 1)), zb()
        self.pf_x, self.pf_y, self.pf_vx, self.pf_vy = z(NP_PF), z(NP_PF), z(NP_PF), z(NP_PF)
        self.pf_w, self.pf_on = np.full((n, NP_PF), 1.0 / NP_PF), zb()
        self.kf_fuera = zi()                           # mediciones seguidas rechazadas por la compuerta del Kalman
        # V15 · fase C: persona seguida por el tracker (0 = el ladrón de verdad), apariencias, ReID y cruces
        self.trk = zi()
        self.apariencia = np.zeros((n, N_PERS, DIM_APARIENCIA))
        self.apariencia[..., 0] = 1.0
        self.sim_med, self.t_cruce, self.sim_cruce = np.ones(n), np.full(n, 99.0), z()
        self.cruce_x, self.cruce_y = z(), z()
        self.mal, self.mal_det = zb(), zb()
        self.duda_pend = zb()                          # cruce que no se pudo verificar: reconfirmar al volver a fijarlo
        self.t_mal = z()                               # s persiguiendo a la persona equivocada sin dudar (métrica)
        # V15 · fase D: muro de la secuencia, paso (0 ninguno, 1 lado proyectado, 2 otro extremo, 3 de canto) y canto
        self.muro_a, self.muro_b, self.paso_muro = z(2), z(2), zi()
        self.canto_t, self.canto_psi0, self.canto_gmb = np.full(n, -1.0), z(), z()
        self.canto_lado = np.ones(n)                 # V15: primer lado del desplazamiento (+1 izquierda del muro, -1 derecha)
        # V15 · fase E: contador continuo de seguimiento y rendición
        self.t_cont, self.rendido = z(), zb()
        # C1 y C3: tiempo desde la última vez a la vista, mejor racha del contador, vista acumulada, tiempo por estado de
        # búsqueda y en qué estado se re-adquirió
        self.t_desde_vista, self.racha_max, self.t_vista_ac = z(), z(), z()
        self.t_readq_sum, self.n_readq = z(), z()
        self.t_busq_est = np.zeros((n, len(NOMBRE_ESTADO)))
        self.readq_est = np.zeros((n, len(NOMBRE_ESTADO)))
        self.ult_busq = np.full(n, PREDECIR)
        self.moral = np.ones(n)
        self.pm_x, self.pm_y, self.pm_t = z(N_PERS), z(N_PERS), np.full((n, N_PERS), 99.0)   # última vez que vio a cada uno
        self.ev_cambio, self.ev_nodet = zb(), zb()
        self.pf_mx, self.pf_my = z(), z()
        self.anticenit, self.d_sep = zb(), z()
        self.g_lado = np.ones((n, N_PERS))
        self.g_pausa = np.zeros((n, N_PERS))                # D-041: descanso del civil distractor entre cruces
        self.conocido = np.zeros((n, N_PERS), bool)         # D-041: civiles que el operador ya distinguió del ladrón
        self.cruce_con = np.zeros((n, N_PERS), bool)        # con quién fue el último cruce
        self.frac_vis = z(N_PERS)                        # V13: fracción del bounding box visible (detección parcial)
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
        # controladores de bajo nivel del hardware (control.py): la política solo da consignas
        self.ap = AutopilotoArduPilot(n, self.rng)
        self.gb = GimbalBaseCam(n)
        # CURRÍCULO: 0 = condiciones suaves, 1 = las más exigentes (lo sube el entrenamiento según el desempeño)
        self.nivel = 0.0
        self.v_sprint = np.full(n, V_SPRINT[0])           # D-041: rapidez de esprint del ladrón (por partida)
        self.v_correr = np.full(n, VEL_CORRER)            # rapidez de carrera del ladrón (aleatoria por partida)
        self.k_ataque = np.ones(n)                        # agresividad del ladrón (aleatoria por partida)
        self.lm_i = np.zeros(n, int)                      # SLAM: hasta dónde se exportó la nube de puntos al visor
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
        self.v_ia_f[m] = self.v_ia_l[m] = 0.0
        self.arm_desc[m] = self.descubre[m] = False
        self.t_oculto[m] = self.t_perdida[m] = 0.0
        self.ciego[m] = False
        if hasattr(self, "entrada"):
            self.entrada[m], self.entrada_alta[m] = True, False      # V15: el primer 360° de la zona es el de entrada
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
        if hasattr(self, "ap"):
            self.ap.sincronizar(self, m)          # la referencia del autopiloto arranca desde la velocidad actual

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
        self.acc_x[m] = self.acc_y[m] = 0.0
        self.salto_t[m] = self.salto_cd[m] = self.salto_h[m] = 0.0
        self.u_prev[m], self.mando_prev[m] = 0.0, False
        self.v_ia_f[m] = self.v_ia_l[m] = 0.0
        self.arm_desc[m] = self.descubre[m] = False
        self.cam_pitch[m] = -10.0
        self.gmb_min_ep[m] = -10.0
        self.u_prev_fis[m] = 0.0
        self.gimbal[m] = -10.0
        self.gimbal_cmd[m] = -10.0
        if hasattr(self, "ap"):
            self.ap.reset(m, self.nivel)
            self.gb.reset(m, -10.0)
            # ALEATORIZACIÓN DEL DOMINIO (generalización): cada partida un ladrón distinto, más rápido y agresivo a
            # medida que sube el nivel del currículo
            self.v_correr[m] = r.uniform(3.0, 3.4, k) + 0.4 * self.nivel
            self.v_sprint[m] = r.uniform(V_SPRINT[0], V_SPRINT[1], k)
            self.k_ataque[m] = r.uniform(0.5, 1.0, k) + 0.5 * self.nivel
            self.lm_i[m] = 0
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
        # V14 · NIVEL DE CADA PARTIDA: el actual del currículo o, con probabilidad p_repaso, uno ya superado (repaso)
        cl = int(np.clip(getattr(self, "current_level", N_NIVELES - 1), 0, N_NIVELES - 1))
        lv = np.full(k, cl)
        if cl > 0 and getattr(self, "p_repaso", 0.0) > 0:
            rep = r.random(k) < self.p_repaso
            lv = np.where(rep, r.integers(0, cl, k), lv)
        self.lvl_ep[m] = lv
        # niveles 1 y 2: UN muro (los demás paneles se superponen al primero; el ladrón no tiene otra cubierta), cerca
        # del centro de la zona; nivel 0: sin muros (fuera de la arena, donde el LiDAR no llega)
        for a, i in enumerate(idx):
            if lv[a] == N_NIVELES - 1:
                # V15 · nivel 4: 3 o 4 muros separados entre sí (los que sobran se superponen al último)
                nm = int(r.integers(MUROS_N4[0], MUROS_N4[1] + 1))
                cs = []
                for j in range(nm):
                    for _ in range(40):
                        c = r.uniform(-17, 17, 2)
                        if (np.hypot(c[0] - self.dx[i], c[1] - self.dy[i]) > 5
                                and all(np.hypot(*(c - c2)) > 6.0 for c2 in cs)):
                            break
                    cs.append(c)
                    ang = r.uniform(0, np.pi)
                    u = np.array([np.cos(ang), np.sin(ang)]) * r.uniform(4.0, 6.5) / 2
                    self.pa[i, j], self.pb[i, j] = c - u, c + u
                self.pa[i, nm:], self.pb[i, nm:] = self.pa[i, nm - 1], self.pb[i, nm - 1]
            elif lv[a] in (2, 3):
                c = r.uniform(-6, 6, 2)
                for _ in range(20):
                    if np.hypot(c[0] - self.dx[i], c[1] - self.dy[i]) > 5:
                        break
                    c = r.uniform(-6, 6, 2)
                ang = r.uniform(0, np.pi)
                u = np.array([np.cos(ang), np.sin(ang)]) * r.uniform(4.0, 6.5) / 2
                self.pa[i, :], self.pb[i, :] = c - u, c + u
            elif lv[a] in (0, 1):
                for j in range(N_PANELES):
                    self.pa[i, j] = (LEJOS_PANEL + 3 * j, LEJOS_PANEL)
                    self.pb[i, j] = (LEJOS_PANEL + 3 * j + 1, LEJOS_PANEL)
        self.un_muro[m] = (lv == 2) | (lv == 3)
        # ladrón: a 8-20 m (30% dentro del campo de visión); al principio no ha notado al dron
        u = r.random(k)
        rel = np.where(u < 0.3, r.uniform(-0.26, 0.26, k), r.uniform(-np.pi, np.pi, k))
        d0 = r.uniform(8, 20, k)
        b = self.psi[m] - rel
        self.px[m, 0] = np.clip(self.dx[m] + d0 * np.cos(b), -ARENA + 1, ARENA - 1)
        self.py[m, 0] = np.clip(self.dy[m] + d0 * np.sin(b), -ARENA + 1, ARENA - 1)
        self.activa[m, 0] = True
        self.stamina[m] = STAMINA_MAX
        # V15: cuerpo (estatura de cada persona), alcance del ladrón, reserva casi llena y pulso alto por la tensión
        self.estatura[m] = np.clip(r.normal(ESTATURA_MEDIA, ESTATURA_SD, (k, N_PERS)), ESTATURA_MIN, ESTATURA_MAX)
        self.alc_pie[m] = K_ALCANCE_PIE * self.estatura[m, 0]
        self.reserva[m] = r.uniform(0.9, 1.0, k)
        self.moral[m] = 1.0
        self.pulso[m] = r.uniform(100.0, 110.0, k)
        self.lid_psi_prev[m] = self.psi[m]
        self.kf_ok[m] = self.pf_on[m] = self.anticenit[m] = False
        self.kf_fuera[m] = 0
        # apariencias: la del ladrón al azar; cada civil se le parece con coseno entre SIM_CIVIL[0] y SIM_CIVIL[1]
        u = r.normal(0, 1, (k, DIM_APARIENCIA))
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        ap_ = np.zeros((k, N_PERS, DIM_APARIENCIA))
        ap_[:, 0] = u
        for j in range(1, N_PERS):
            w_ = r.normal(0, 1, (k, DIM_APARIENCIA))
            w_ -= (w_ * u).sum(1, keepdims=True) * u
            w_ /= np.linalg.norm(w_, axis=1, keepdims=True)
            c_ = r.uniform(SIM_CIVIL[0], SIM_CIVIL[1], k)[:, None]
            ap_[:, j] = c_ * u + np.sqrt(1 - c_ ** 2) * w_
        self.apariencia[m] = ap_
        self.trk[m] = 0
        self.sim_med[m], self.t_cruce[m], self.sim_cruce[m] = 1.0, 99.0, 0.0
        self.mal[m] = self.mal_det[m] = False
        self.duda_pend[m] = False
        self.paso_muro[m] = 0
        self.canto_t[m] = -1.0
        self.t_cont[m] = 0.0
        self.rendido[m] = False
        self.t_desde_vista[m] = self.racha_max[m] = self.t_vista_ac[m] = 0.0
        self.t_readq_sum[m] = self.n_readq[m] = 0.0
        self.t_busq_est[m] = 0.0
        self.readq_est[m] = 0.0
        self.ult_busq[m] = PREDECIR
        self.pm_t[m] = 99.0

        self.corriendo[m] = False
        # niveles 0-2: ladrón táctico con guion (el aprendido solo en la misión completa)
        self.tactico[m] = (r.random(k) >= FRAC_LADRON_RL) | (lv < N_NIVELES - 1)
        self.l_guion[m] = np.where(lv <= 1, np.where(r.random(k) < self.p_cenit, L_GUION_CENIT, L_GUION_HUIDA), L_GUION_TACTICO)
        self.l_ang[m] = 0.0
        self.l_tg[m] = 0.0
        self.l_modo[m] = L_DEAMBULAR
        self.l_alerta_t[m] = r.uniform(2.0, 8.0, k)
        self.l_t[m] = self.l_expuesto[m] = 0.0
        self.l_panel[m] = 0
        self.g_lim[m] = [-18.0, 18.0, -18.0, 18.0]
        self.g_wx[m, 0], self.g_wy[m, 0] = r.uniform(-15, 15, k), r.uniform(-15, 15, k)
        self.v_forzada[m] = np.nan
        # peatones de la zona: 0, 1 o 2 (el 3 es el transeúnte de la ruta, solo en la misión)
        self.conocido[m] = False
        self.cruce_con[m] = False
        self.g_pausa[m] = 0.0
        npea = r.choice([0, 1, 2], size=k, p=[0.3, 0.4, 0.3])
        npea = np.where((lv == 1) | (lv == 3), 1, np.where(lv <= 2, 0, npea))     # V15: civiles según el nivel
        for a, i in enumerate(idx):
            for j in range(1, N_PERS):
                act = j <= npea[a]
                self.activa[i, j] = act
                if act:
                    self._preparar_peaton(i, j)
                    # D-041: ningún civil nace a menos de D_NACE_CIVIL del dron (el 360° de entrada es bajo)
                    ex_, ey_ = self.px[i, j] - self.dx[i], self.py[i, j] - self.dy[i]
                    de0 = max(np.hypot(ex_, ey_), 1e-6)
                    if de0 < D_NACE_CIVIL:
                        self.px[i, j] = np.clip(self.dx[i] + ex_ / de0 * D_NACE_CIVIL, -ARENA + 1, ARENA - 1)
                        self.py[i, j] = np.clip(self.dy[i] + ey_ / de0 * D_NACE_CIVIL, -ARENA + 1, ARENA - 1)
                    if lv[a] in (1, 3):                  # V15 niveles 1 y 3: el civil es un distractor en la línea de vista
                        self.guion[i, j] = G_DISTRACTOR
                        self.g_vel[i, j] = r.uniform(1.0, 1.5)
                        self.g_lado[i, j] = r.choice([-1.0, 1.0])
                        self.g_pausa[i, j] = r.uniform(0.0, 10.0)
                else:
                    self.px[i, j] = self.py[i, j] = 999.0
            self.ids[i] = r.choice(np.arange(1, 60), N_PERS, replace=False)
        self.pvx[m] = self.pvy[m] = 0.0
        self.p_rumbo[m] = r.uniform(-np.pi, np.pi, (k, N_PERS))
        self.vis_prev[m] = False
        self.vac[m] = self.vlat[m] = 0.0
        self.obs_retraso[m] = 0.0
        # V15 · niveles 0 y 1: "dron en el aire con el objetivo ya fijado": el ladrón aparece en cuadro a 6-12 m, ya
        # alerta, y el operador ya lo confirmó
        fij0 = np.where(m)[0][lv <= 1]
        if len(fij0):
            kk = len(fij0)
            rel0 = r.uniform(-0.2, 0.2, kk)
            d00 = r.uniform(6.0, 12.0, kk)
            b0 = self.psi[fij0] - rel0
            self.px[fij0, 0] = np.clip(self.dx[fij0] + d00 * np.cos(b0), -ARENA + 1, ARENA - 1)
            self.py[fij0, 0] = np.clip(self.dy[fij0] + d00 * np.sin(b0), -ARENA + 1, ARENA - 1)
            self.modo[fij0] = FIJADO
            self.visto_alguna[fij0] = True
            self.lock[fij0] = True
            self.trk[fij0] = 0
            self.l_alerta_t[fij0] = 0.0
            self.dz[fij0] = Z_NOMINAL                    # V15: ya en el aire a la altura segura
            a0 = -np.degrees(np.arctan2(self.dz[fij0] - 0.9, d00))
            self.cam_pitch[fij0] = self.gimbal[fij0] = self.gimbal_cmd[fij0] = a0
            if hasattr(self, "gb"):
                self.gb.ang[fij0] = self.gb.sp[fij0] = a0
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
        self.g_vel[i, j] = r.uniform(0.8, 1.6 + 0.6 * self.nivel)       # peatones con rapidez variable (currículo)
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

    def _caras_muro(self, j):
        """V15: las 4 caras del muro j como segmentos (los dos lados a +-GROSOR_MURO/2 y las dos puntas). (n, 2) cada uno."""
        a, b = self.pa[:, j], self.pb[:, j]
        u = (b - a) / np.maximum(np.hypot(*(b - a).T), 1e-6)[:, None]
        g = np.stack([-u[:, 1], u[:, 0]], -1) * (GROSOR_MURO / 2)
        return [(a + g, b + g), (a - g, b - g), (a + g, a - g), (b + g, b - g)]

    def _vista_bloqueada_alturas(self, hs, qx=None, qy=None):
        """¿Algún muro tapa la línea de vista del dron a cada punto (qx, qy) de cada persona a cada altura hs? (n, P, K).
        V15: hs puede ser (K,) o (n, P, K) (estatura de cada persona) y los muros tienen grosor (4 caras). El cruce no
        depende de la altura: se calcula una vez por cara y se evalúan todas las alturas juntas."""
        qx = self.px if qx is None else qx
        qy = self.py if qy is None else qy
        hs = np.asarray(hs)
        hs3 = hs[None, None, :] if hs.ndim == 1 else hs
        p = np.broadcast_to(np.stack([self.dx, self.dy], -1)[:, None, :], qx.shape + (2,))
        q = np.stack([qx, qy], -1)
        z = self.dz[:, None, None]
        bloq = np.zeros(qx.shape + (hs3.shape[-1],), bool)
        for j in range(self.pa.shape[1]):
            for a_, b_ in self._caras_muro(j):
                a = np.broadcast_to(a_[:, None, :], q.shape)
                b = np.broadcast_to(b_[:, None, :], q.shape)
                corta, t = cruce_segmentos(p, q, a, b)
                h = z + (hs3 - z) * t[..., None]
                bloq |= corta[..., None] & (h < self.ph[:, j][:, None, None])
        return bloq

    def _libre_pares(self, e, pj, qx, qy, hs, caras):
        """V15 (rápido): para M pares (entorno e, persona pj), ¿qué muestras (punto qx, qy a las alturas hs (M, K)) ve el
        dron sin que las tape un muro (con grosor) ni otra persona? (M, K)"""
        D = np.stack([self.dx[e], self.dy[e]], -1)[:, None, :]                # (M, 1, 2)
        q = np.stack([qx, qy], -1)                                             # (M, K, 2): cada muestra en su punto
        z = self.dz[e][:, None]
        bloq = np.zeros(hs.shape, bool)
        # descarte rápido: solo los pares con algún muro cerca de la línea de vista al centro de la persona
        P0 = np.stack([self.px[e, pj], self.py[e, pj]], -1)
        D0 = D[:, 0]
        cerca_m = np.zeros((len(e), self.pa.shape[1]), bool)
        for j in range(self.pa.shape[1]):
            A_, B_ = self.pa[e, j], self.pb[e, j]
            cerca_m[:, j] = (cruce_segmentos(D0, P0, A_, B_)[0] | (dist_punto_segmento(A_, D0, P0)[0] < 0.8)
                             | (dist_punto_segmento(B_, D0, P0)[0] < 0.8))
        for a_, b_, j in caras:
            fil = np.where(cerca_m[:, j])[0]
            if len(fil) == 0:
                continue
            corta, t = cruce_segmentos(D[fil], q[fil], a_[e[fil]][:, None, :], b_[e[fil]][:, None, :])     # (m, K)
            if corta.any():
                h = z[fil] + (hs[fil] - z[fil]) * t
                bloq[fil] |= corta & (h < self.ph[e[fil], j][:, None])
        # personas: solo los pares con otra persona activa cerca de la línea de vista
        Qc = np.stack([self.px[e], self.py[e]], -1)                            # (M, P, 2)
        otra = self.activa[e] & (np.arange(N_PERS)[None, :] != pj[:, None])
        dq = dist_punto_segmento(Qc, D0[:, None, :], P0[:, None, :])[0]
        fil = np.where((otra & (dq < RADIO_PERSONA + 0.3)).any(1))[0]
        if len(fil) == 0:
            return ~bloq
        e, pj, D, q, z = e[fil], pj[fil], D[fil], q[fil], z[fil]
        sub = bloq[fil]
        Q = np.stack([self.px[e], self.py[e]], -1)[:, :, None, :]             # (m, P, 1, 2)
        ab = (q - D)[:, None]                                                  # (M, 1, K, 2)
        L2 = np.maximum((ab ** 2).sum(-1), 1e-9)
        t = np.clip(((Q - D[:, None]) * ab).sum(-1) / L2, 0.0, 1.0)            # (M, P, K)
        cx, cy = D[:, None, :, 0] + t * ab[..., 0], D[:, None, :, 1] + t * ab[..., 1]
        delante = ((np.hypot(Q[..., 0] - cx, Q[..., 1] - cy) < RADIO_PERSONA + 0.05) & self.activa[e][..., None]
                   & (np.arange(N_PERS)[None, :, None] != pj[:, None, None]) & (t > 0.02) & (t < 0.95))
        if delante.any():
            hl = z[:, None] + (hs[fil][:, None, :] - z[:, None]) * t           # (m, P, K)
            sub |= (delante & (hl <= self.estatura[e][..., None])).any(1)
            bloq[fil] = sub
        return ~bloq

    def _rayos_pares(self, e, psi):
        """V15 (rápido): rayos del LiDAR solo para los entornos e (con rumbos psi): distancia y persona tocada."""
        th = np.radians(self.cam_pitch[e])
        ct, st = np.cos(th), np.sin(th)
        cps, sps = np.cos(psi), np.sin(psi)
        t = np.full(len(e), LIDAR_MAX)
        tg = np.where(st < -1e-3, self.dz[e] / np.maximum(-st, 1e-3), np.inf)
        t = np.minimum(t, tg)
        ch = np.maximum(ct, 1e-3)
        p = np.stack([self.dx[e], self.dy[e]], -1)
        q = p + LIDAR_MAX * np.stack([cps, sps], -1)
        for j in range(self.pa.shape[1]):
            corta, u = cruce_segmentos(p, q, self.pa[e, j], self.pb[e, j])
            tj = u * LIDAR_MAX / ch
            zj = self.dz[e] + tj * st
            t = np.where(corta & (ct > 1e-3) & (zj >= 0) & (zj <= self.ph[e, j]) & (tj < t), tj, t)
        rx, ry = self.px[e] - self.dx[e][:, None], self.py[e] - self.dy[e][:, None]
        s_p = rx * cps[:, None] + ry * sps[:, None]
        perp = np.abs(-rx * sps[:, None] + ry * cps[:, None])
        tp = s_p / ch[:, None]
        zp = self.dz[e][:, None] + tp * st[:, None]
        hitp = self.activa[e] & (s_p > 0.2) & (perp < RADIO_PERSONA) & (zp >= 0) & (zp <= self.estatura[e]) & (tp < t[:, None])
        return t, hitp.any(1)

    def _tapada_por_personas(self, hs, qx=None, qy=None):
        """V14: oclusión entre personas. La muestra a la altura hs de la persona p queda tapada si la línea de vista del
        dron pasa por el cuerpo (cilindro de RADIO_PERSONA y ALTURA_PERSONA) de otra persona q que esté delante. (n, P, K)"""
        qx = self.px if qx is None else qx
        qy = self.py if qy is None else qy
        hs = np.asarray(hs)
        hs4 = hs[None, None, None, :] if hs.ndim == 1 else hs[:, :, None, :]     # (n, P, 1, K)
        D = np.stack([self.dx, self.dy], -1)[:, None, None, :]                   # (n, 1, 1, 2)
        Pt = np.stack([qx, qy], -1)[:, :, None, :]                                # (n, P, 1, 2): objetivo
        Q = np.stack([self.px, self.py], -1)[:, None, :, :]                       # (n, 1, Q, 2): quien tapa
        ab = Pt - D
        L2 = np.maximum((ab ** 2).sum(-1), 1e-9)
        t = np.clip(((Q - D) * ab).sum(-1) / L2, 0.0, 1.0)                        # (n, P, Q)
        cx, cy = D[..., 0] + t * ab[..., 0], D[..., 1] + t * ab[..., 1]
        cerca = np.hypot(Q[..., 0] - cx, Q[..., 1] - cy) < RADIO_PERSONA + 0.05
        otro = ~np.eye(N_PERS, dtype=bool)[None] & self.activa[:, None, :] & self.activa[:, :, None]
        delante = cerca & otro & (t > 0.02) & (t < 0.95)
        z = self.dz[:, None, None, None]
        h_linea = z + (hs4 - z) * t[..., None]                                  # (n, P, Q, K) altura de la vista en q
        return (delante[..., None] & (h_linea <= self.estatura[:, None, :, None])).any(2)

    def _lidar_camara(self, psi=None):
        """Un rayo por el eje óptico (yaw del dron + pitch del gimbal) hasta lo primero que toca: suelo, panel u
        obstáculo (planos verticales de altura ph) o persona (cilindro). Devuelve distancia, punto y tipo (1 suelo,
        2 obstáculo, 3 persona) e índice de la persona tocada."""
        n = self.n
        th = np.radians(self.cam_pitch)
        ct, st = np.cos(th), np.sin(th)
        psi = self.psi if psi is None else psi
        cps, sps = np.cos(psi), np.sin(psi)
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
        hitp = self.activa & (s_p > 0.2) & (perp < RADIO_PERSONA) & (zp >= 0) & (zp <= self.estatura) & (tp < t[:, None])
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
        extension = np.degrees(np.arctan2(dz, dh) - np.arctan2(dz - self.estatura, dh))       # V15: estatura real
        h_norm = np.minimum(extension, VFOV) / VFOV
        ancho_deg = np.degrees(2 * np.arctan2(RADIO_PERSONA, np.maximum(dh, 0.2)))
        w_norm = np.minimum(ancho_deg / HFOV, 1.0)
        p_det = np.where(d_inclinada < 20, 0.97, np.clip(0.97 - (d_inclinada - 20) * 0.06, 0, 1))
        # V13 · DETECCIÓN PARCIAL: el cuerpo se muestrea en N_MUESTRAS_PERSONA alturas; una muestra cuenta si cae dentro
        # de la imagen y ningún muro la tapa. Si al menos FRAC_DET_MIN del bounding box asoma, YOLO la detecta (con la
        # misma probabilidad que entera: a YOLO le basta la cabeza y los hombros)
        # V15: muestras en ALTO (fracciones de la estatura de cada persona) y en ANCHO (a lo largo de los hombros,
        # perpendicular a la línea de vista): así un cuerpo que asoma de costado detrás de un muro de canto también cuenta
        hs = (np.arange(N_MUESTRAS_PERSONA) + 0.5) / N_MUESTRAS_PERSONA
        hs3 = hs[None, None, :] * self.estatura[..., None]                     # (n, P, K)
        ux_l, uy_l = rx / np.maximum(dh, 1e-6), ry / np.maximum(dh, 1e-6)
        mw = medio_ancho(hs)                                                     # (K,)
        caras = [(a_, b_, j) for j in range(self.pa.shape[1]) for a_, b_ in self._caras_muro(j)]
        es_ladron = (np.arange(N_PERS) == 0)[None, :]
        # todas las columnas del ancho juntas: (n, P, C*K)
        wk = (np.asarray(OFFS_ANCHO)[:, None] * mw[None, :]).reshape(-1)       # (C*K,) desplazamiento lateral
        nc = len(OFFS_ANCHO)
        hsc = np.tile(hs3, (1, 1, nc))                                         # (n, P, C*K) alturas
        qx = self.px[..., None] - uy_l[..., None] * wk
        qy = self.py[..., None] + ux_l[..., None] * wk
        rxw, ryw = qx - self.dx[:, None, None], qy - self.dy[:, None, None]
        vz = hsc - dz[..., None]
        c3, s3, ct3, st3 = cps[..., None], sps[..., None], ct[..., None], st[..., None]
        xf = rxw * c3 * ct3 + ryw * s3 * ct3 + vz * st3
        xr = rxw * s3 - ryw * c3
        xu = -rxw * c3 * st3 - ryw * s3 * st3 + vz * ct3
        dentro = ((xf > 0.3) & (np.abs(xr) < xf * np.tan(np.radians(HFOV / 2 - 0.5)))
                  & (np.abs(xu) < xf * np.tan(np.radians(VFOV / 2))))
        # la oclusión (muros con grosor y otras personas) solo se calcula para los pares dron-persona que caen en la
        # imagen; para el ladrón, también fuera de ella (su red observa si está tapado)
        necesita = self.activa & (dentro.any(-1) | es_ladron)
        e_, j_ = np.nonzero(necesita)
        libre = np.zeros(dentro.shape, bool)
        if len(e_):
            libre[e_, j_] = self._libre_pares(e_, j_, qx[e_, j_], qy[e_, j_], hsc[e_, j_], caras)
        self.frac_vis = np.where(self.activa, (dentro & libre).mean(-1), 0.0)
        tapada = necesita & (libre.mean(-1) < FRAC_DET_MIN)                     # el muro tapa más del 85 %
        # probabilidad de detección: la de la persona entera por la distancia, por una rampa según lo que asoma
        p_frac = np.clip((self.frac_vis - P_FRAC[0]) / (P_FRAC[1] - P_FRAC[0]), 0.0, 1.0)
        visible = (self.activa & (self.frac_vis >= P_FRAC[0]) & (d_inclinada < 35)
                   & (r.random((n, N_PERS)) < p_det * p_frac))
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
        # V15 · FASE C: el tracker puede cambiarse de persona en un cruce; después, la percepción del dron se reordena para
        # que la columna 0 sea la persona que sigue (que puede no ser el ladrón)
        self.ev_cambio[:] = False
        self.ev_nodet[:] = False
        self._modelo_id(visible, ang, ancho_deg)
        vis_real, tap_real = visible, tapada
        vac_d, vlat_d = self.vac, self.vlat
        sw = np.where(self.trk != 0)[0]
        if len(sw):
            tj = self.trk[sw]

            def pm(a_):
                b_ = a_.copy()
                b_[sw, 0], b_[sw, tj] = a_[sw, tj], a_[sw, 0]
                return b_
            visible, laser, ang_m, dist, dh, tapada, elev_m, area = map(pm, (visible, laser, ang_m, dist, dh, tapada, elev_m, area))
            vac_d, vlat_d = pm(self.vac), pm(self.vlat)
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
        # ReID: parecido de la persona seguida con la que designó el operador (el ladrón); peor de lejos
        s_m = (self.apariencia[np.arange(n), self.trk] * self.apariencia[:, 0]).sum(-1)
        s_m = s_m + r.normal(0, 1, n) * (0.03 + 0.01 * np.minimum(d0, 30.0))
        s_m = np.clip(s_m, 0.0, 1.0)
        self.sim_med = np.where(v0, 0.8 * self.sim_med + 0.2 * s_m, self.sim_med)
        self.t_sin_ver = np.where(v0 | ~fij, 0.0, self.t_sin_ver + DT)
        # memoria del objetivo: dónde lo vio confirmado por última vez
        self.ult_rumbo = np.where(v0, envolver(self.psi - np.radians(ang_m[:, 0])), self.ult_rumbo)
        self.ult_dist = np.where(v0, dist[:, 0], self.ult_dist)
        dh_est = np.sqrt(np.maximum(dist[:, 0] ** 2 - (self.dz - 0.9) ** 2, 0.25))
        # V15: mirando hacia abajo, la distancia por geometría (altura del dron y ángulo bajo el horizonte, suelo plano)
        # es mucho mejor que la del bbox (que llega cortado por el borde de la imagen cuando la persona está debajo)
        el0 = elev_m[:, 0]
        geo = el0 > 12.0
        dh_est = np.where(geo, (self.dz - 0.9) / np.tan(np.radians(np.clip(el0, 1.0, 89.0))), dh_est)
        rumbo_w = self.psi - np.radians(ang_m[:, 0])
        ux_n = np.clip(self.dx + dh_est * np.cos(rumbo_w), -ARENA + 1, ARENA - 1)
        uy_n = np.clip(self.dy + dh_est * np.sin(rumbo_w), -ARENA + 1, ARENA - 1)
        # V15 · KALMAN: posición, velocidad y aceleración del objetivo con su medición (bbox + ángulos; el LiDAR si lo toca)
        sig = np.where(laser[:, 0], 0.1, 0.15 + 0.05 * np.minimum(dist[:, 0], 30.0))
        # mirando muy abajo (la persona casi debajo) el bbox mide mal la distancia: la medición vale mucho menos
        sig = np.where(geo & ~laser[:, 0], 0.1 + 0.03 * dh_est, sig)
        self._kalman(v0, ux_n, uy_n, sig)
        self.tvx = np.where(self.kf_ok, self.kf_x[:, 0, 1], self.tvx)
        self.tvy = np.where(self.kf_ok, self.kf_x[:, 1, 1], self.tvy)
        self.ult_x = np.where(v0, self.kf_x[:, 0, 0], self.ult_x)
        self.ult_y = np.where(v0, self.kf_x[:, 1, 0], self.ult_y)
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
        # como un punto del plano. V15: 10 rayos por paso (100 Hz del TF03) repartidos en el giro de ese paso; el último
        # es el de ahora. Los puntos repetidos los filtra D_DEDUP_LIDAR.
        dpsi = envolver(self.psi - self.lid_psi_prev)
        gira = np.abs(dpsi) > np.radians(1.0)
        eg = np.where(gira)[0]
        if len(eg):
            nk = RAYOS_POR_PASO - 1
            e_r = np.repeat(eg, nk)
            f_r = np.tile(np.arange(1, RAYOS_POR_PASO) / RAYOS_POR_PASO, len(eg))
            psi_r = envolver(self.lid_psi_prev[e_r] + dpsi[e_r] * f_r)
            t_r, pers_r = self._rayos_pares(e_r, psi_r)
            ok_r = (t_r < np.minimum(t_suelo[e_r] - 0.4, LIDAR_MAX - 0.1)) & ~pers_r
            h_r = t_r * np.cos(np.radians(self.cam_pitch[e_r]))
            for kk in range(nk):                                   # en orden: el filtro de repetidos ve los anteriores
                sel_ = np.arange(kk, len(e_r), nk)
                sel_ = sel_[ok_r[sel_]]
                self._guardar_idx(e_r[sel_], h_r[sel_], psi_r[sel_])
        self._guardar_impactos(obst & (jp_l < 0), self.lidar, self.psi)
        self.lid_psi_prev = self.psi.copy()
        v = v0.astype(float)
        cps_, sps_ = np.cos(self.psi), np.sin(self.psi)
        rxu, ryu = self.ult_x - self.dx, self.ult_y - self.dy
        # V15 · FILTRO DE PARTÍCULAS sin verlo (información negativa con lo que la cámara ve en este cuadro)
        self._particulas(visible[:, 0], ct[:, 0], st[:, 0], cps[:, 0], sps[:, 0])
        # dónde cree el dron que estaba el objetivo durante el cruce (por si el operador dice "no es él")
        self.cruce_x = np.where(self.t_cruce == 0.0, self.kf_x[:, 0, 0], self.cruce_x)
        self.cruce_y = np.where(self.t_cruce == 0.0, self.kf_x[:, 1, 0], self.cruce_y)
        # "dónde estaría ahora": la media de la nube sin verlo; el Kalman con el objetivo a la vista
        kx = np.where(self.kf_ok, self.kf_x[:, 0, 0], self.ult_x)
        ky = np.where(self.kf_ok, self.kf_x[:, 1, 0], self.ult_y)
        rxp = np.where(self.pf_on, self.pf_mx, kx) - self.dx
        ryp = np.where(self.pf_on, self.pf_my, ky) - self.dy
        obs = np.stack([
            v,
            v * np.minimum(dist[:, 0], 30.0) / 20.0,
            (laser[:, 0] & v0).astype(float),
            v * area[:, 0] * 4.0,
            v * np.clip(ang_m[:, 0], -HFOV / 2, HFOV / 2) / (HFOV / 2),
            v * np.clip(vac_d[:, 0], -5, 5) / 5.0,
            v * np.clip(vlat_d[:, 0], -60, 60) / 30.0,
            self.dz - Z_REF_OBS,
            np.minimum(self.t_sin_ver, 5.0) / 5.0,
            mem * np.sin(rel_ult), mem * np.cos(rel_ult), mem * np.minimum(self.ult_dist, 30.0) / 20.0,
            vo,
            vo * np.minimum(sel(dist), 30.0) / 20.0,
            vo * np.clip(sel(ang_m), -HFOV / 2, HFOV / 2) / (HFOV / 2),
            vo * np.clip(sel(vac_d), -5, 5) / 5.0,
            self.lidar / 20.0,
            self.dx / ARENA, self.dy / ARENA, np.cos(self.psi), np.sin(self.psi),
            # memoria espacial para buscar: perdido (1 = escondido, la IA busca), última posición conocida en el marco
            # del dron (x adelante, y izquierda), tiempo sin verlo, pitch del gimbal y su último vector de movimiento
            (self.modo == BUSQUEDA_IA).astype(float),
            mem * np.clip((rxu * cps_ + ryu * sps_) / 20.0, -1.5, 1.5),
            mem * np.clip((-rxu * sps_ + ryu * cps_) / 20.0, -1.5, 1.5),
            np.minimum(self.t_sin_ver, T_BUSQUEDA_IA) / T_BUSQUEDA_IA,
            self.gimbal / 90.0,
            mem * np.clip((self.tvx * cps_ + self.tvy * sps_) / 5.0, -1, 1),
            mem * np.clip((-self.tvx * sps_ + self.tvy * cps_) / 5.0, -1, 1),
            *self._sectores_lidar().T,
            # predicción a un paso: dónde estaría ahora el ladrón si siguió con su último vector (hasta 2 s)
            mem * np.clip((rxp * cps_ + ryp * sps_) / 20.0, -1.5, 1.5),
            mem * np.clip((-rxp * sps_ + ryp * cps_) / 20.0, -1.5, 1.5),
            # estado propio (para anticipar frenadas y no forzar motores ni gimbal)
            (self.dvx * cps_ + self.dvy * sps_) / 5.0, (self.dvx * sps_ - self.dvy * cps_) / 5.0,
            (self.acc_x * cps_ + self.acc_y * sps_) / ACC_MAX_DRON, (self.acc_x * sps_ - self.acc_y * cps_) / ACC_MAX_DRON,
            self.dvz / 2.0, self.yaw_dps / 60.0,
            self.v_ia_f / VEL_IA_AVANCE, self.v_ia_l / VEL_IA_LATERAL, np.clip((self.z_ia - self.dz) / 2.0, -1, 1),
            np.clip((self.g_ia - self.gimbal) / 30.0, -1, 1),
            *self._grilla_mapa().T,
        ], axis=1)
        self.info_sensor = dict(visible=visible, laser=laser, ang=ang_m, dist=dist, dh=dh, tapada=tapada, lock=v0.copy(),
                                elev=elev_m, vac=vac_d, visible_real=vis_real, tapada_real=tap_real)
        return obs

    # ------------------------------------------------------------------ V15 · fase B: predicción
    def _modelo_id(self, visible, ang, ancho_deg):
        """V15 · fase C: CRUCES y CAMBIO DE ID. Con el objetivo designado, si otra persona visible se superpone en la
        imagen con la persona seguida, el tracker puede saltar a ella con probabilidad P_CAMBIO · parecido² · (movimiento
        parecido). Registra los cruces (para vigilar la identidad después) y los cambios sin detectar (métrica)."""
        n = self.n
        r = self.rng
        ar = np.arange(n)
        desig = (self.modo >= FIJADO) & (self.modo != BUSQUEDA_IA)
        t = self.trk
        at, wt = ang[ar, t], ancho_deg[ar, t]
        otro = visible & (np.arange(N_PERS)[None, :] != t[:, None])
        solapa = desig[:, None] & otro & (np.abs(ang - at[:, None]) < (wt[:, None] + ancho_deg) / 2 + 1.0)
        hubo = solapa.any(1)
        nuevo_cruce = hubo & (self.t_cruce > 0.5)
        self.sim_cruce = np.where(nuevo_cruce, 0.0, self.sim_cruce)
        self.cruce_con = np.where(nuevo_cruce[:, None], False, self.cruce_con) | solapa
        sim_tpl = (self.apariencia * self.apariencia[:, 0:1]).sum(-1)              # parecido de cada uno con el designado
        self.sim_cruce = np.where(hubo, np.maximum(self.sim_cruce, np.where(solapa & ~self.conocido, sim_tpl, 0.0).max(1)), self.sim_cruce)
        self.t_cruce = np.where(hubo, 0.0, self.t_cruce + DT)
        # probabilidad de saltar a cada persona superpuesta
        sim_tj = np.clip((self.apariencia * self.apariencia[ar, t][:, None, :]).sum(-1), 0.0, 1.0)
        dv = np.hypot(self.pvx - self.pvx[ar, t][:, None], self.pvy - self.pvy[ar, t][:, None])
        p = np.where(solapa, P_CAMBIO * sim_tj ** 2 * np.clip(1.0 - dv / V_DIF_ID, 0.15, 1.0), 0.0)
        jm = np.argmax(p, 1)
        salta = r.random(n) < p[ar, jm]
        nuevo = np.where(salta, jm, t)
        a_mal = salta & (nuevo != 0)
        self.mal_det = np.where(a_mal & ~self.mal, False, self.mal_det)
        self.mal = np.where(salta, nuevo != 0, self.mal)
        self.trk = nuevo
        # MÉTRICA: un cambio cuenta cuando el cruce terminó (0.5 s sin superposición) y el tracker quedó en otra persona
        # (los saltos de ida y vuelta mientras están superpuestos son el tracker reasociando); queda SIN DETECTAR si pasa
        # la ventana T_CRUCE sin que el dron dude
        fin_cruce = (self.t_cruce >= 0.5) & (self.t_cruce - DT < 0.5)
        self.ev_cambio |= fin_cruce & self.mal
        # sin detectar = sigue (fijado y viéndolo) a la persona equivocada pasada la ventana del cruce sin haber dudado
        persigue_mal = self.mal & ~self.mal_det & (self.modo == FIJADO) & self.lock & (self.t_cruce >= T_CRUCE)
        self.t_mal = np.where(persigue_mal, self.t_mal + DT, 0.0)
        nodet = self.t_mal >= 1.0                      # más de 1 s persiguiéndolo sin haber dudado
        self.ev_nodet |= nodet
        self.mal_det |= nodet                          # se cuenta una sola vez por cambio

    def _kalman(self, v0, zx, zy, sig):
        """Kalman de aceleración constante por eje (x, y). Predice siempre; corrige con la medición cuando lo ve fijado."""
        dt = DT
        F = np.array([[1.0, dt, dt * dt / 2], [0.0, 1.0, dt], [0.0, 0.0, 1.0]])
        Q = KF_Q * np.array([[dt ** 5 / 20, dt ** 4 / 8, dt ** 3 / 6], [dt ** 4 / 8, dt ** 3 / 3, dt ** 2 / 2],
                             [dt ** 3 / 6, dt ** 2 / 2, dt]])
        x = np.einsum("ij,naj->nai", F, self.kf_x)
        P = np.einsum("ij,najk,lk->nail", F, self.kf_P, F) + Q
        ini = v0 & ~self.kf_ok
        if ini.any():
            x[ini, :, 0] = np.stack([zx, zy], -1)[ini]
            x[ini, :, 1:] = 0.0
            P[ini] = np.diag([1.0, 4.0, 9.0])
            P[ini, :, 0, 0] = (sig[ini] ** 2)[:, None]
        upd = v0 & self.kf_ok
        if upd.any():
            z_ = np.stack([zx, zy], -1)                                          # (n, 2)
            S_ = P[..., 0, 0] + (sig ** 2)[:, None]                               # (n, 2)
            K = P[..., :, 0] / S_[..., None]                                      # (n, 2, 3)
            inn = z_ - x[..., 0]
            # COMPUERTA: una medición imposible (lejos de lo predicho) se descarta; tres seguidas reinician el filtro
            raro = (np.abs(inn) / np.sqrt(S_) > 4.0).any(1) & (np.hypot(*inn.T) > 1.0)
            self.kf_fuera = np.where(upd & raro, self.kf_fuera + 1, 0)
            reini = upd & (self.kf_fuera >= 3)
            upd = upd & ~raro
            x = np.where(upd[:, None, None], x + K * inn[..., None], x)
            P = np.where(upd[:, None, None, None], P - K[..., :, None] * P[..., 0, None, :], P)
            if reini.any():
                x[reini, :, 0] = z_[reini]
                x[reini, :, 1:] = 0.0
                P[reini] = np.diag([1.0, 4.0, 9.0])
                self.kf_fuera[reini] = 0
        # sin corregir (no lo ve): la aceleración se apaga y la rapidez no pasa de la de una persona; dentro de la arena
        x[..., 2] = np.where(v0[:, None], x[..., 2], 0.7 * x[..., 2])
        vm = np.hypot(x[:, 0, 1], x[:, 1, 1])
        x[..., 1] *= np.minimum(1.0, V_PF_MAX / np.maximum(vm, 1e-6))[:, None]
        x[..., 2] = np.clip(x[..., 2], -6.0, 6.0)
        x[..., 0] = np.clip(x[..., 0], -ARENA, ARENA)
        self.kf_x, self.kf_P = x, P
        self.kf_ok |= v0

    def _particulas(self, vis0, ct, st, cps, sps):
        """Filtro de partículas del objetivo sin verlo. Se enciende cuando el objetivo designado sale de la vista (a partir
        del Kalman) y se apaga al volver a verlo. Cada cuadro: movimiento humano (sin atravesar muros) e INFORMACIÓN
        NEGATIVA: las hipótesis que la cámara ve (en cuadro, sin tapar y a menos de 30 m) sin que YOLO detecte a nadie
        pierden casi todo su peso. Remuestreo sistemático cuando la nube degenera."""
        r = self.rng
        seguir = self.visto_alguna & (self.modo >= FIJADO)
        self.pf_on &= seguir & ~vis0
        ini = seguir & ~vis0 & ~self.pf_on & self.kf_ok
        e = np.where(ini)[0]
        if len(e):
            sp = np.clip(np.sqrt(np.maximum(self.kf_P[e, :, 0, 0].mean(1), 0.0)) + 0.3, 0.3, 3.0)[:, None]
            self.pf_x[e] = self.kf_x[e, 0, 0][:, None] + r.normal(0, 1, (len(e), NP_PF)) * sp
            self.pf_y[e] = self.kf_x[e, 1, 0][:, None] + r.normal(0, 1, (len(e), NP_PF)) * sp
            self.pf_vx[e] = self.kf_x[e, 0, 1][:, None] + r.normal(0, 0.8, (len(e), NP_PF))
            self.pf_vy[e] = self.kf_x[e, 1, 1][:, None] + r.normal(0, 0.8, (len(e), NP_PF))
            self.pf_w[e] = 1.0 / NP_PF
            self.pf_on[e] = True
        e = np.where(self.pf_on)[0]
        if len(e) == 0:
            return
        m = len(e)
        x, y, vx, vy, w = self.pf_x[e], self.pf_y[e], self.pf_vx[e], self.pf_vy[e], self.pf_w[e]
        vx = vx + r.normal(0, A_PF * DT, (m, NP_PF))
        vy = vy + r.normal(0, A_PF * DT, (m, NP_PF))
        vm = np.hypot(vx, vy)
        k_ = np.minimum(1.0, V_PF_MAX / np.maximum(vm, 1e-6))
        vx, vy = vx * k_, vy * k_
        nx, ny = x + vx * DT, y + vy * DT
        P0, P1 = np.stack([x, y], -1), np.stack([nx, ny], -1)
        bloq = np.zeros((m, NP_PF), bool)
        for j in range(self.pa.shape[1]):
            bloq |= cruce_segmentos(P0, P1, self.pa[e, j][:, None, :], self.pb[e, j][:, None, :])[0]
        nx, ny = np.where(bloq, x, nx), np.where(bloq, y, ny)
        vx, vy = np.where(bloq, -0.3 * vx, vx), np.where(bloq, -0.3 * vy, vy)
        lim = ARENA - 0.5
        fuera_x, fuera_y = np.abs(nx) > lim, np.abs(ny) > lim
        nx, ny = np.clip(nx, -lim, lim), np.clip(ny, -lim, lim)
        vx, vy = np.where(fuera_x, 0.0, vx), np.where(fuera_y, 0.0, vy)
        # información negativa: ¿la cámara ve el torso o la cabeza de alguien parado en cada hipótesis?
        rx, ry = nx - self.dx[e][:, None], ny - self.dy[e][:, None]
        c_, s_, ct_, st_ = cps[e][:, None], sps[e][:, None], ct[e][:, None], st[e][:, None]
        en_cam = np.zeros((m, NP_PF), bool)
        for h in (1.0, 1.55):
            vz = h - self.dz[e][:, None]
            xf = rx * c_ * ct_ + ry * s_ * ct_ + vz * st_
            xr = rx * s_ - ry * c_
            xu = -rx * c_ * st_ - ry * s_ * st_ + vz * ct_
            en_cam |= ((xf > 0.3) & (np.abs(xr) < xf * np.tan(np.radians(HFOV / 2 - 1.0)))
                       & (np.abs(xu) < xf * np.tan(np.radians(VFOV / 2))) & (xf < LIDAR_MAX))
        if en_cam.any():
            D = np.stack([self.dx[e], self.dy[e]], -1)[:, None, :]
            tapa = np.zeros((m, NP_PF), bool)
            for j in range(self.pa.shape[1]):
                corta, t = cruce_segmentos(D, np.stack([nx, ny], -1), self.pa[e, j][:, None, :], self.pb[e, j][:, None, :])
                h_l = self.dz[e][:, None] + (1.3 - self.dz[e][:, None]) * t
                tapa |= corta & (h_l < self.ph[e, j][:, None])
            w = w * np.where(en_cam & ~tapa, W_VISTO, 1.0)
        sw = w.sum(1)
        muertas = sw < 1e-9
        if muertas.any():                     # nada sobrevivió: vuelve a esparcir la nube alrededor de su última media
            k = np.where(muertas)[0]
            nx[k] = self.pf_mx[e[k]][:, None] + r.normal(0, 4.0, (len(k), NP_PF))
            ny[k] = self.pf_my[e[k]][:, None] + r.normal(0, 4.0, (len(k), NP_PF))
            vx[k] = vy[k] = 0.0
            w[k] = 1.0
            sw = w.sum(1)
        w = w / sw[:, None]
        ess = 1.0 / (w ** 2).sum(1)
        rs = np.where(ess < NP_PF / 2)[0]
        if len(rs):
            cs = np.cumsum(w[rs], 1)
            cs[:, -1] = 1.0
            u = (r.random(len(rs))[:, None] + np.arange(NP_PF)[None, :]) / NP_PF
            off = np.arange(len(rs))[:, None] * 2.0
            idx = np.searchsorted((cs + off).ravel(), (u + off).ravel()).reshape(len(rs), NP_PF) - np.arange(len(rs))[:, None] * NP_PF
            idx = np.clip(idx, 0, NP_PF - 1)
            g = lambda a: np.take_along_axis(a[rs], idx, 1)
            nx[rs], ny[rs], vx[rs], vy[rs] = g(nx) + r.normal(0, 0.05, idx.shape), g(ny) + r.normal(0, 0.05, idx.shape), g(vx), g(vy)
            w[rs] = 1.0 / NP_PF
        self.pf_x[e], self.pf_y[e], self.pf_vx[e], self.pf_vy[e], self.pf_w[e] = nx, ny, vx, vy, w
        self.pf_mx[e], self.pf_my[e] = (w * nx).sum(1), (w * ny).sum(1)

    def _masa_tras_muros(self, i):
        """Para el entorno i: masa de la nube detrás de cada muro detectado (la recta dron -> partícula lo cruza) y su
        centroide. Devuelve (masas (K_DET,), centroides (K_DET, 2))."""
        masas, cen = np.zeros(K_DET), np.zeros((K_DET, 2))
        if not self.pf_on[i]:
            return masas, cen
        D = np.array([self.dx[i], self.dy[i]])
        P = np.stack([self.pf_x[i], self.pf_y[i]], -1)
        w = self.pf_w[i]
        for j in range(self.det_n[i]):
            corta, _ = cruce_segmentos(np.broadcast_to(D, P.shape), P, self.det_a[i, j], self.det_b[i, j])
            masas[j] = w[corta].sum()
            if masas[j] > 0:
                cen[j] = (w[corta, None] * P[corta]).sum(0) / masas[j]
        return masas, cen

    def _guardar_impactos(self, nuevo, horiz, psi):
        """Guarda en la nube los impactos de obstáculo de un rayo (distancia horizontal horiz, rumbo psi), salvo los que
        caen a menos de D_DEDUP_LIDAR de un punto ya guardado."""
        if nuevo.any():
            k = np.where(nuevo)[0]
            self._guardar_idx(k, horiz[k], psi[k])

    def _guardar_idx(self, k, horiz, psi):
        """Guarda un impacto por entorno k (distancia horizontal horiz y rumbo psi ya indexados por k)."""
        if len(k) == 0:
            return
        rr = horiz + self.rng.normal(0, 0.05, len(k))             # distancia horizontal con ruido
        qx, qy = self.dx[k] + rr * np.cos(psi), self.dy[k] + rr * np.sin(psi)
        dmin = np.where(self.lid_ok[k], np.hypot(self.lid_px[k] - qx[:, None], self.lid_py[k] - qy[:, None]), np.inf).min(1)
        k, qx, qy = k[dmin > D_DEDUP_LIDAR], qx[dmin > D_DEDUP_LIDAR], qy[dmin > D_DEDUP_LIDAR]
        ranura = self.lid_i[k] % N_LIDAR
        self.lid_px[k, ranura], self.lid_py[k, ranura] = qx, qy
        self.lid_ok[k, ranura] = True
        self.lid_i[k] += 1
        if len(k):
            self.lid_ult_psi[k], self.lid_ult_x[k], self.lid_ult_y[k] = self.psi[k], self.dx[k], self.dy[k]

    def _puntos_mapa(self):
        """Los impactos guardados como listas planas (entorno, x, y): solo los que existen, no las 512 ranuras."""
        e, k = np.nonzero(self.lid_ok)
        return e, self.lid_px[e, k], self.lid_py[e, k]

    def _grilla_mapa(self):
        """MAPA DESCUBIERTO para la red: grilla de ocupación GRID_N x GRID_N (celdas de GRID_CELDA m) centrada en el dron
        y alineada con su rumbo, hecha con TODOS los impactos guardados del LiDAR (coordenadas absolutas). 0 = libre o
        sin explorar, 0.5 = un impacto, 1 = dos o más. Así la política conoce el laberinto aunque no lo esté mirando."""
        e, x, y = self._puntos_mapa()
        rx, ry = x - self.dx[e], y - self.dy[e]
        c, s_ = np.cos(self.psi[e]), np.sin(self.psi[e])
        f, l = rx * c + ry * s_, -rx * s_ + ry * c
        medio = GRID_N * GRID_CELDA / 2.0
        i = np.floor((f + medio) / GRID_CELDA).astype(int)
        j = np.floor((medio - l) / GRID_CELDA).astype(int)
        ok = (i >= 0) & (i < GRID_N) & (j >= 0) & (j < GRID_N)
        idx = (e[ok] * GRID_N + i[ok]) * GRID_N + j[ok]
        g = np.bincount(idx, minlength=self.n * GRID_N * GRID_N).reshape(self.n, GRID_N * GRID_N)
        return np.minimum(g, 2) / 2.0

    def _sectores_lidar(self):
        """Mapa local para la IA con los impactos guardados del LiDAR: en N_SECT sectores alrededor del dron (marco del
        cuerpo), la cercanía del obstáculo más próximo (0 = nada a menos de R_SECT, 1 = pegado). Sin red extra."""
        e, x, y = self._puntos_mapa()
        rx, ry = x - self.dx[e], y - self.dy[e]
        d = np.hypot(rx, ry)
        ang = envolver(np.arctan2(ry, rx) - self.psi[e])
        k = np.clip(((ang + np.pi) / (2 * np.pi) * N_SECT).astype(int), 0, N_SECT - 1)
        dmin = np.full(self.n * N_SECT, np.inf)
        np.minimum.at(dmin, e * N_SECT + k, d)
        return 1.0 - np.minimum(dmin.reshape(self.n, N_SECT), R_SECT) / R_SECT

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
        cols = [np.minimum(dh, 30) / 20.0, self.dz - Z_REF_OBS, dvx / 3.0, dvy / 3.0, pvx / 3.0, pvy / 3.0,
                np.cos(mira), np.sin(mira), self.stamina / STAMINA_MAX, (self.estado == EVADIENDO).astype(float),
                self.t / PASOS_EPISODIO, self.info_sensor["visible_real"][:, 0].astype(float),
                self.info_sensor["tapada_real"][:, 0].astype(float)]
        # V15: la red del ladrón (congelada) observa 2 muros: los 2 más cercanos a él
        cen = (self.pa[:, :N_PANELES] + self.pb[:, :N_PANELES]) / 2
        orden = np.argsort(np.hypot(cen[..., 0] - self.px[:, 0:1], cen[..., 1] - self.py[:, 0:1]), 1)[:, :2]
        ar_ = np.arange(self.n)
        for jj in range(2):
            j = orden[:, jj]
            cx = (self.pa[ar_, j, 0] + self.pb[ar_, j, 0]) / 2 - self.px[:, 0]
            cy = (self.pa[ar_, j, 1] + self.pb[ar_, j, 1]) / 2 - self.py[:, 0]
            ex, ey = self.pb[ar_, j, 0] - self.pa[ar_, j, 0], self.pb[ar_, j, 1] - self.pa[ar_, j, 1]
            th = np.arctan2(ey, ex) - b
            qx, qy = rot(cx, cy)
            cols += [np.clip(qx / 20.0, -2, 2), np.clip(qy / 20.0, -2, 2), np.cos(2 * th), np.sin(2 * th)]
        cols.append(np.minimum(dh, 30) / 30.0)
        return np.stack(cols, axis=1)

    def obs_dron(self):
        return self.obs_retraso.copy()

    def mascara_decision(self):
        """La política del dron decide con el objetivo fijado y, con PERDIDA_IA, también al buscarlo tras perderlo;
        nunca durante una maniobra del árbitro."""
        return ((self.modo == FIJADO) | (self.modo == BUSQUEDA_IA)) & (self.estado == VIGILANDO)

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

    def _flanqueo(self, i, j, D, U=None, k=1.0, AB=None):
        """FLANQUEO PROFUNDO del panel detectado j: rodea la esquina por la que desapareció el ladrón (la más cercana a
        su última posición U; sin U, la más cercana al dron) y termina DETRÁS del plano del muro, en la zona que estaba
        oculta: E + 0.8·afuera + D_FLANCO·atrás. Para no rozar la esquina, la ruta pasa por puntos a R_ESQUINA de ella
        (en diagonal por delante y de costado), y los extremos detectados se alargan OFFSET_EXT. Devuelve (ruta,
        dirección hacia el interior de la zona oculta, centro del panel)."""
        A, B = (self.det_a[i, j], self.det_b[i, j]) if AB is None else AB
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
            if np.dot(D - E, afuera) < 0.3 * R_ESQUINA * k:           # y no ha pasado la esquina
                puntos.append(E + R_ESQUINA * k * (afuera + frente) / np.sqrt(2))
            puntos.append(E + R_ESQUINA * k * afuera)
        # V13 · STAND-OFF por FOV: a por fuera de la esquina y b detrás del plano (el cono cubre la franja oculta)
        a_so, b_so = stand_off_fov()
        puntos.append(E + a_so * afuera + b_so * atras)
        x0, x1, y0, y1 = self.zona[i]
        puntos = [np.array([np.clip(p[0], max(x0 + 0.5, -ARENA + 1.5), min(x1 - 0.5, ARENA - 1.5)),
                            np.clip(p[1], max(y0 + 0.5, -ARENA + 1.5), min(y1 - 0.5, ARENA - 1.5))]) for p in puntos]
        return puntos, -afuera, M

    def _flanqueo_seguro(self, i, j, D, U=None, AB=None):
        """V12 · OFFSET TÁCTICO: prueba separaciones crecientes de la esquina (K_OFFSET) hasta que la ruta pase lejos de
        los paneles detectados y de cada punto de la nube (raycasting). Si ninguna sirve, la más amplia (se vuela por encima)."""
        for k in K_OFFSET:
            puntos, interior, M = self._flanqueo(i, j, D, U, k, AB)
            if self._ruta_segura(i, D, puntos):
                break
        return puntos, interior, M

    def _ruta_segura(self, i, D, puntos):
        """¿Todos los tramos pasan a más de RADIO_DRON + MARGEN_ESQUINA de los paneles que vio el LiDAR y de los puntos
        sueltos de su nube (V12: raycasting también contra la nube, que ve esquinas que aún no forman un panel)?"""
        pts = [D] + list(puntos)
        ok = self.lid_ok[i]
        nube = np.stack([self.lid_px[i, ok], self.lid_py[i, ok]], -1)
        for a, b in zip(pts, pts[1:]):
            if dist_nube_segmento(nube, np.asarray(a, float), np.asarray(b, float)) < RADIO_DRON + MARGEN_ESQUINA:
                return False
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
        # V15: con la nube encendida, el giro empieza hacia donde está su masa (que hoy no se ve)
        idx_ = np.where(self.pf_on, self.pf_mx - self.dx, self.int_dx)
        idy_ = np.where(self.pf_on, self.pf_my - self.dy, self.int_dy)
        cruz = np.cos(self.psi) * idy_ - np.sin(self.psi) * idx_
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
        # V15: con la nube, el muro con más masa detrás y el lado (esquina) por donde se proyecta que se escondió
        masas, cen = self._masa_tras_muros(i)
        if self.det_n[i] and masas.max() >= MASA_MURO:
            jm = int(np.argmax(masas))
            puntos, interior, Zc = self._flanqueo_seguro(i, jm, D, cen[jm])
            self.muro_a[i], self.muro_b[i], self.paso_muro[i] = self.det_a[i, jm], self.det_b[i, jm], 1
            self._poner_ruta(i, puntos, interior, True)
            self.inv_x[i], self.inv_y[i] = puntos[-1]
            self.mira_x[i], self.mira_y[i] = cen[jm]
            self.zc_x[i], self.zc_y[i] = Zc
            self.obj_mx[i], self.obj_my[i] = Zc
            self.insp_n[i] = 0
            return
        if self.pf_on[i]:
            U = np.array([self.pf_mx[i], self.pf_my[i]])
        jb, db = -1, 3.0
        for j in range(self.det_n[i]):
            dj, _ = dist_punto_segmento(U, self.det_a[i, j], self.det_b[i, j])
            if dj < db:
                jb, db = j, float(dj)
        if jb < 0:
            # V12 · RAYCASTING: si la recta dron -> última posición cruza un panel del mapa, se escondió detrás de ése
            dc = np.inf
            for j in range(self.det_n[i]):
                corta, t = cruce_segmentos(D, U, self.det_a[i, j], self.det_b[i, j])
                if corta and t < dc:
                    jb, dc = j, float(t)
        esc = np.array([self.esc_vx[i], self.esc_vy[i]])
        self.paso_muro[i] = 0
        if jb >= 0:
            puntos, interior, Zc = self._flanqueo_seguro(i, jb, D, U)
            self.muro_a[i], self.muro_b[i], self.paso_muro[i] = self.det_a[i, jb], self.det_b[i, jb], 1
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
        self.obj_mx[i], self.obj_my[i] = Zc                  # zona que se revisa (memoria de la búsqueda)
        self.insp_n[i] = 0

    def _planear_siguiente(self, i):
        """V12 · SIGUIENTE_OBSTÁCULO: con la memoria espacial (los paneles que el LiDAR armó con su nube de puntos), el
        panel aún no revisado de menor costo = largo de la ruta de flanqueo + distancia de su centro a la última posición
        conocida (el ladrón no se teletransporta). Prepara la ruta para quedar detrás de él. False si no queda ninguno."""
        self._mapear_lidar(i)
        D = np.array([self.dx[i], self.dy[i]])
        U = np.array([self.ult_x[i], self.ult_y[i]])
        hechos = np.stack([self.insp_x[i, :self.insp_n[i]], self.insp_y[i, :self.insp_n[i]]], -1)
        masas, _ = self._masa_tras_muros(i)          # V15: prefiere los muros con más probabilidad detrás
        if self.pf_on[i]:
            U = np.array([self.pf_mx[i], self.pf_my[i]])
        mejor = None
        for j in range(self.det_n[i]):
            M = (self.det_a[i, j] + self.det_b[i, j]) / 2
            if len(hechos) and np.min(np.hypot(*(hechos - M).T)) < R_INSP_HECHO:
                continue
            puntos, interior, M = self._flanqueo_seguro(i, j, D)
            costo = sum(np.hypot(*(b - a)) for a, b in zip([D] + puntos, puntos)) + np.hypot(*(M - U)) - 30.0 * masas[j]
            if mejor is None or costo < mejor[0]:
                mejor = (costo, puntos, interior, M)
        if mejor is None:
            return False
        _, puntos, interior, M = mejor
        self._poner_ruta(i, puntos, interior, True)
        self.inv_x[i], self.inv_y[i] = puntos[-1]
        self.mira_x[i], self.mira_y[i] = M
        self.obj_mx[i], self.obj_my[i] = M
        return True

    def _planear_otro_extremo(self, i):
        """Paso 2 de la secuencia: detrás del mismo muro, por el extremo contrario al que acaba de revisar."""
        D = np.array([self.dx[i], self.dy[i]])
        A, B = self.muro_a[i].copy(), self.muro_b[i].copy()
        lejos = A if np.hypot(*(A - D)) > np.hypot(*(B - D)) else B
        puntos, interior, M = self._flanqueo_seguro(i, -1, D, lejos, AB=(A, B))
        self._poner_ruta(i, puntos, interior, True)
        self.inv_x[i], self.inv_y[i] = puntos[-1]
        self.mira_x[i], self.mira_y[i] = M
        self.paso_muro[i] = 2

    def _planear_canto(self, i):
        """Paso 3: el punto en la prolongación del muro, a A_CANTO de una punta (dentro de la arena y, si se puede, con la
        ruta libre según la nube), mirando a lo largo del muro. False si no hay ninguno dentro de la arena."""
        D = np.array([self.dx[i], self.dy[i]])
        A, B = self.muro_a[i].copy(), self.muro_b[i].copy()
        L = max(np.hypot(*(B - A)), 1e-6)
        opciones = []
        for T, O in ((A, B), (B, A)):
            P = T + (T - O) / L * A_CANTO
            if np.all(np.abs(P) < ARENA - 1.5):
                opciones.append((not self._ruta_segura(i, D, [P]), np.hypot(*(P - D)), P, T, O))
        if not opciones:
            return False
        opciones.sort(key=lambda o: (o[0], o[1]))
        _, _, P, T, O = opciones[0]
        self._poner_ruta(i, [P], O - T, False)
        self.inv_x[i], self.inv_y[i] = P
        self.mira_x[i], self.mira_y[i] = O
        self.canto_psi0[i] = np.arctan2(O[1] - T[1], O[0] - T[0])
        self.canto_gmb[i] = -np.degrees(np.arctan2(Z_SEGURA - 1.2, A_CANTO + L / 2))
        # primer lado: hacia donde la predicción pone al ladrón (media de la nube; si no hay nube, la última posición)
        X = np.array([self.pf_mx[i], self.pf_my[i]]) if self.pf_on[i] else np.array([self.ult_x[i], self.ult_y[i]])
        nrm = np.array([-np.sin(self.canto_psi0[i]), np.cos(self.canto_psi0[i])])
        self.canto_lado[i] = 1.0 if float(np.dot(nrm, X - T)) >= 0 else -1.0
        self.canto_t[i] = -1.0
        self.paso_muro[i] = 3
        return True

    def _marcar_revisado(self, i):
        if self.insp_n[i] < self.insp_x.shape[1]:
            self.insp_x[i, self.insp_n[i]], self.insp_y[i, self.insp_n[i]] = self.obj_mx[i], self.obj_my[i]
            self.insp_n[i] += 1

    def _guarda_mapa(self, vx, vy):
        """Muro virtual con los impactos guardados del LiDAR (sin red neuronal: solo distancias a los puntos). Por debajo
        de la altura de tránsito, quita a la consigna la parte de la velocidad hacia el obstáculo que excede la que
        permite frenar a tiempo; la parte tangencial se conserva (se desliza a lo largo del muro)."""
        e, x, y = self._puntos_mapa()
        rx, ry = x - self.dx[e], y - self.dy[e]
        d = np.hypot(rx, ry)
        cerca = (d < R_GUARDA) & (self.dz[e] < Z_TRANSITO - 0.1)
        e, rx, ry, d = e[cerca], rx[cerca], ry[cerca], d[cerca]
        ux, uy = rx / np.maximum(d, 1e-6), ry / np.maximum(d, 1e-6)
        # el autopiloto tarda en invertir la aceleración (jerk limitado): si ya acelera hacia el punto, frena más tarde
        a_hacia = np.maximum(self.acc_x[e] * ux + self.acc_y[e] * uy, 0.0)
        at = A_GUARDA * (T_GUARDA + (A_GUARDA + a_hacia) / (2.0 * J_MAX_DRON))
        v_max = -at + np.sqrt(at * at + 2.0 * A_GUARDA * np.maximum(d - R_PARADA, 0.0))
        activa = np.zeros(self.n, bool)
        for _ in range(2):                                   # dos pasadas: en una esquina hay dos muros
            exceso = vx[e] * ux + vy[e] * uy - v_max
            emax = np.zeros(self.n)
            np.maximum.at(emax, e, exceso)
            peor = (exceso > 0) & (exceso >= emax[e])
            ee, primero = np.unique(e[peor], return_index=True)
            if len(ee) == 0:
                break
            q = np.nonzero(peor)[0][primero]
            vx[ee] -= exceso[q] * ux[q]
            vy[ee] -= exceso[q] * uy[q]
            activa[ee] = True
        return vx, vy, activa

    def _guarda_personas_y_cerca(self, vx, vy):
        """V15 · fase E. (1) Personas: no se acerca a quien vio hace menos de T_PERSONA_MEM s (su última posición, que
        puede estar a la espalda de la cámara) más allá de lo que permite frenar a R_PERSONA_MEM. (2) GEOCERCA como
        ArduPilot (FENCE + AVOID): la velocidad hacia el borde se limita a la que permite frenar antes de ARENA - MARGEN."""
        s = self.info_sensor
        vr = s["visible_real"]
        self.pm_x = np.where(vr, self.px, self.pm_x)
        self.pm_y = np.where(vr, self.py, self.pm_y)
        self.pm_t = np.where(vr, 0.0, self.pm_t + DT)
        rx, ry = self.pm_x - self.dx[:, None], self.pm_y - self.dy[:, None]
        d = np.maximum(np.hypot(rx, ry), 1e-6)
        otro = (np.arange(N_PERS)[None, :] != 0) & self.activa & (self.pm_t < T_PERSONA_MEM) & (d < 6.0)
        ux, uy = rx / d, ry / d
        v_max = np.sqrt(2.0 * A_FRENO_DRON * np.maximum(d - R_PERSONA_MEM, 0.0))
        for j in range(1, N_PERS):
            hacia = vx * ux[:, j] + vy * uy[:, j]
            exc = np.where(otro[:, j], np.maximum(hacia - v_max[:, j], 0.0), 0.0)
            vx, vy = vx - exc * ux[:, j], vy - exc * uy[:, j]
        # si ya va hacia el borde más rápido de lo permitido (el autopiloto sigue la consigna con retardo), pide frenar
        # hacia adentro en proporción al exceso
        for pos, v, vr_ in ((self.dx, vx, self.dvx), (self.dy, vy, self.dvy)):
            sg = np.sign(pos)
            margen = np.maximum(ARENA - MARGEN_CERCA - np.abs(pos), 0.0)
            at_ = A_CERCA * T_LAG_CERCA
            vm = -at_ + np.sqrt(at_ ** 2 + 2.0 * A_CERCA * margen)
            tope = vm - 1.5 * np.maximum(vr_ * sg - vm, 0.0)
            v -= sg * np.maximum(v * sg - tope, 0.0)
        return vx, vy

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
        rc = {k: np.zeros(n) for k in R_COMP}            # V12: recompensa por componente
        o = self.obs_retraso
        s = self.info_sensor
        vis, dist_s, ang_s, elev_s = s["visible"] & self.activa, s["dist"], s["ang"], s["elev"]
        mando0 = self.mascara_decision()
        self.t_modo += DT
        self.t_fase2 += DT
        en_busqueda = np.isin(self.modo, (PREDECIR, INVESTIGAR, ASOMO, SIGUIENTE_OBSTACULO, VENTAJA_ALTURA, MURO_CANTO))
        self.t_perdida = np.where(en_busqueda, self.t_perdida + DT, self.t_perdida)

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
        self.trk = np.where(lock_on, 0, self.trk)              # V15: el operador designó al ladrón de verdad
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
        # V15 · FASE C · RECONFIRMAR: tras un cruce (ya separados), si la apariencia no cuadra, si se cruzó con alguien
        # parecido o si el Kalman rechaza mediciones, el dron se queda en hover con el objetivo en cuadro y pregunta al
        # operador. El operador hace clic sobre el ladrón si lo ve; si no lo ve y el dron seguía a otro, "no es él": el dron
        # vuelve a buscarlo desde donde estaba en el cruce. Decide el humano, nunca la IA.
        tras_cruce = (self.t_cruce > 0.3) & (self.t_cruce < T_CRUCE)
        sospecha = tras_cruce & ((self.sim_cruce > UMBRAL_PARECIDO) | ((self.kf_fuera >= 1) & DUDA_KALMAN))
        puede_ver = (self.modo == FIJADO) & self.lock           # también esquivando: el árbitro sigue mandando en la velocidad
        # si tras un cruce no lo pudo verificar (lo perdió de vista, estaba esquivando), queda pendiente
        self.duda_pend |= tras_cruce & ~puede_ver
        # D-041: MEMORIA DE APARIENCIA. Con un civil que el operador ya distinguió, el dron guarda su apariencia: tras un
        # cruce compara a quien sigue contra el ladrón Y contra ese civil (con el ruido del ReID); si se parece más al
        # civil, duda. Así un civil conocido no obliga a preguntar en cada cruce, pero un cambio hacia él no pasa sin
        # detectar.
        ar_ = np.arange(n)
        tk = self.trk
        al_conocido = tras_cruce & (tk != 0) & self.conocido[ar_, tk]
        if al_conocido.any():                    # (solo se sortea ruido si hace falta: no altera el resto de la partida)
            d_tk = np.hypot(self.px[ar_, tk] - self.dx, self.py[ar_, tk] - self.dy)
            sd_ = 0.03 + 0.01 * d_tk
            sim_lad = (self.apariencia[ar_, tk] * self.apariencia[ar_, 0]).sum(-1) + r.normal(0.0, 1.0, n) * sd_
            sim_civ = 1.0 + r.normal(0.0, 1.0, n) * sd_
            al_conocido &= sim_civ > sim_lad
        duda = puede_ver & ((self.sim_med < UMBRAL_SIM) | sospecha | self.duda_pend | al_conocido)
        self.modo = np.where(duda, RECONFIRMAR, self.modo)
        self.t_modo = np.where(duda, 0.0, self.t_modo)
        self.t_resp = np.where(duda, r.uniform(T_OPERADOR[0], T_OPERADOR[1], n), self.t_resp)
        ev_reconf, ev_det = duda.copy(), duda & self.mal
        self.mal_det |= ev_det
        rcf0 = self.modo == RECONFIRMAR
        responde = rcf0 & ~duda & (self.t_modo >= self.t_resp)
        lo_ve = s["visible_real"][:, 0]
        si_es = responde & lo_ve
        no_es = (responde & ~lo_ve & (self.trk != 0)) | (rcf0 & (self.t_modo >= T_ESPERA_CLIC) & ~si_es)
        sigue_igual = responde & ~lo_ve & (self.trk == 0)
        corrige = (si_es | no_es) & (self.trk != 0)
        self.kf_ok = np.where(corrige, False, self.kf_ok)
        self.conocido |= (si_es | no_es)[:, None] & self.cruce_con
        self.trk = np.where(si_es | no_es, 0, self.trk)
        self.mal = np.where(si_es | no_es, False, self.mal)
        self.sim_med = np.where(si_es | no_es, 1.0, self.sim_med)
        self.t_cruce = np.where(si_es | no_es | sigue_igual, 99.0, self.t_cruce)
        self.sim_cruce = np.where(si_es | no_es | sigue_igual, 0.0, self.sim_cruce)
        self.duda_pend = np.where(si_es | no_es | sigue_igual | duda, False, self.duda_pend)
        self.lock = np.where(si_es, True, np.where(no_es, False, self.lock))
        self.n_conf = np.where(si_es, N_REID, self.n_conf)
        self.t_sin_ver = np.where(si_es, 0.0, self.t_sin_ver)
        # "no es él": vuelve a buscarlo desde el cruce (el Kalman y la nube arrancan ahí)
        nx_ = np.where(no_es)[0]
        if len(nx_):
            self.kf_x[nx_] = 0.0
            self.kf_x[nx_, 0, 0], self.kf_x[nx_, 1, 0] = self.cruce_x[nx_], self.cruce_y[nx_]
            self.kf_P[nx_] = np.diag([4.0, 4.0, 9.0])
            self.kf_ok[nx_] = True
            self.pf_on[nx_] = False
            self.ult_x[nx_], self.ult_y[nx_] = self.cruce_x[nx_], self.cruce_y[nx_]
            self.t_sin_ver[nx_] = T_TRACKER + 0.1
        self.modo = np.where(si_es | sigue_igual, FIJADO, np.where(no_es, PREDECIR, self.modo))
        self.pred_x0 = np.where(no_es, self.cruce_x, self.pred_x0)
        self.pred_y0 = np.where(no_es, self.cruce_y, self.pred_y0)
        self.pred_vx = np.where(no_es, 0.0, self.pred_vx)
        self.pred_vy = np.where(no_es, 0.0, self.pred_vy)
        self.t_pred_dur = np.where(no_es, T_PERDIDA_LENTO, self.t_pred_dur)
        self.t_modo = np.where(si_es | no_es | sigue_igual, 0.0, self.t_modo)
        # V13 · INTERRUPCIÓN TÁCTICA: en cualquier estado de la búsqueda determinista (PÉRDIDA, FLANQUEO, GIRO_360,
        # SIGUIENTE_OBSTÁCULO, ALTURA_TÁCTICA), si YOLO detecta al ID designado en este cuadro se cancela la búsqueda y se
        # pasa a PERSECUCIÓN de inmediato (sin esperar los N_REID cuadros de re-identificación: el tracker lo sigue desde
        # aquí). Solo el ID designado interrumpe: los peatones nunca (humano en el lazo).
        en_busq0 = np.isin(self.modo, (PREDECIR, INVESTIGAR, ASOMO, SIGUIENTE_OBSTACULO, VENTAJA_ALTURA, MURO_CANTO))
        interrumpe = en_busq0 & vis[:, 0] & INTERRUPCION
        self.modo = np.where(interrumpe, FIJADO, self.modo)
        self.t_modo = np.where(interrumpe, 0.0, self.t_modo)
        self.t_perdida = np.where(interrumpe, 0.0, self.t_perdida)
        self.t_sin_ver = np.where(interrumpe, 0.0, self.t_sin_ver)
        self.giro_mem = np.where(interrumpe, 0.0, self.giro_mem)
        self.aso_gira = np.where(interrumpe, False, self.aso_gira)
        self.ruta_n = np.where(interrumpe, 0, self.ruta_n)
        self.n_conf = np.where(interrumpe, N_REID, self.n_conf)
        self.lock = self.lock | interrumpe
        # INTERCEPCIÓN PREDICTIVA: si sale del cuadro corriendo (por ejemplo, pasa por debajo del dron), no se queda
        # en hover: sigue su trayectoria extrapolada T_PREDICCION s mientras el gimbal intenta re-encuadrarlo
        rapido = np.hypot(self.tvx, self.tvy) > V_PRED_MIN
        a_pred = (self.modo == FIJADO) & (self.t_sin_ver > T_PRED_INI) & rapido & (not PERDIDA_IA)
        self.pred_x0 = np.where(a_pred, self.ult_x, self.pred_x0)
        self.pred_y0 = np.where(a_pred, self.ult_y, self.pred_y0)
        self.pred_vx = np.where(a_pred, self.tvx, self.pred_vx)
        self.pred_vy = np.where(a_pred, self.tvy, self.pred_vy)
        self.esc_vx = np.where(a_pred, self.tvx, self.esc_vx)
        self.esc_vy = np.where(a_pred, self.tvy, self.esc_vy)
        self.modo = np.where(a_pred, PREDECIR, self.modo)
        self.t_modo = np.where(a_pred, 0.0, self.t_modo)
        # PROTOCOLO DE PÉRDIDA: el tracker soltó el ID (iba lento, o la predicción no lo recuperó)
        lento = (self.modo == FIJADO) & (self.t_sin_ver > T_TRACKER) & ~a_pred
        self.esc_vx = np.where(lento, self.tvx, self.esc_vx)
        self.esc_vy = np.where(lento, self.tvy, self.esc_vy)
        # V12: el objetivo lento también pasa por PÉRDIDA (T_PERDIDA_LENTO siguiendo su vector) antes de flanquear
        a_lento = lento & (not PERDIDA_IA)
        self.pred_x0 = np.where(a_lento, self.ult_x, self.pred_x0)
        self.pred_y0 = np.where(a_lento, self.ult_y, self.pred_y0)
        self.pred_vx = np.where(a_lento, self.tvx, self.pred_vx)
        self.pred_vy = np.where(a_lento, self.tvy, self.pred_vy)
        self.modo = np.where(a_lento, PREDECIR, self.modo)
        self.t_modo = np.where(a_lento, 0.0, self.t_modo)
        self.t_pred_dur = np.where(a_pred, T_PREDICCION, np.where(a_lento, T_PERDIDA_LENTO, self.t_pred_dur))
        self.t_perdida = np.where(a_pred | a_lento, 0.0, self.t_perdida)
        fin_pred = ((self.modo == PREDECIR) & (self.t_modo > self.t_pred_dur + np.where(self.ciego, T_CIEGO_EXTRA, 0.0))
                    & ~self.lock)
        # V15 · fase D: al entrar a la PÉRDIDA agrupa el mapa del LiDAR; si la nube ya pone al ladrón detrás de un muro
        # conocido (masa >= MASA_DIRECTO), no espera el resto de la predicción: va directo a la secuencia tras el muro
        for i in np.where(a_pred | a_lento)[0]:
            self._mapear_lidar(i)
        for i in np.where((self.modo == PREDECIR) & self.pf_on & (self.t_modo >= 0.5) & ~fin_pred & ~self.lock
                          & (self.det_n > 0))[0]:
            if self._masa_tras_muros(i)[0].max() >= MASA_DIRECTO:
                fin_pred[i] = True
        perdida = a_pred | lento                            # el objetivo acaba de salir de la vista
        pierde = fin_pred | (lento & PERDIDA_IA)
        if PERDIDA_IA:
            # la IA sigue al mando y hereda el estado físico del paso anterior como consignas iniciales: la velocidad
            # que llevaba (en su marco; sin frenazo que incline el chasis y sacuda la cámara), su altura y el ángulo
            # del gimbal. La pérdida arma el bono de re-adquisición
            self.modo = np.where(pierde, BUSQUEDA_IA, self.modo)
            cps0, sps0 = np.cos(self.psi), np.sin(self.psi)
            self.v_ia_f = np.where(pierde, np.clip(self.dvx * cps0 + self.dvy * sps0, -VEL_IA_AVANCE, VEL_IA_AVANCE), self.v_ia_f)
            self.v_ia_l = np.where(pierde, np.clip(self.dvx * sps0 - self.dvy * cps0, -VEL_IA_LATERAL, VEL_IA_LATERAL), self.v_ia_l)
            self.z_ia = np.where(pierde, self.dz, self.z_ia)
            self.g_ia = np.where(pierde, self.gimbal, self.g_ia)
            self.gimbal_cmd = np.where(pierde, self.gimbal, self.gimbal_cmd)
            # (el bono y la multa los arma el reloj de ocultamiento, más abajo)
        else:
            for i in np.where(pierde)[0]:
                self._planear_perdida(i)
            self.modo = np.where(pierde, INVESTIGAR, self.modo)
        self.t_modo = np.where(pierde, 0.0, self.t_modo)
        self.t_bloqueo = np.where(pierde, 0.0, self.t_bloqueo)
        # en cualquier paso del protocolo, si YOLO vuelve a confirmar el ID (ReID), la IA retoma el control
        recupera = ((self.modo >= INVESTIGAR) & (self.modo != RECONFIRMAR) & self.lock & ~pierde) | interrumpe
        self.t_perdida = np.where(recupera, 0.0, self.t_perdida)
        self.modo = np.where(recupera, FIJADO, self.modo)
        self.t_modo = np.where(recupera, 0.0, self.t_modo)
        self.giro_mem = np.where(recupera, 0.0, self.giro_mem)
        # FLANQUEO_PROFUNDO / SIGUIENTE_OBSTÁCULO (rutas) -> GIRO_360 -> SIGUIENTE_OBSTÁCULO ... -> ALTURA_TÁCTICA -> ronda
        # nueva. Cada paso exige T_HISTERESIS s en el estado (sin oscilaciones); MISIÓN_PERDIDA la da el reloj de 90 s.
        en_ruta = (self.modo == INVESTIGAR) | (self.modo == SIGUIENTE_OBSTACULO)
        canto = self.modo == MURO_CANTO
        ultimo_u = self._seguir_ruta(en_ruta | (canto & (self.canto_t < 0)))
        err_u, d_u = self._ir_a(self.rx, self.ry)
        llega_u = (en_ruta & ultimo_u & (self.t_modo >= T_HISTERESIS)
                   & ((d_u < D_LLEGADA) | (self.t_bloqueo > 1.0) | (self.t_modo > T_INVESTIGA_MAX)))
        self._girar_hacia_interior(llega_u)
        # V15 · fase D: detrás del muro (pasos 1 y 2) el barrido es de GIRO_LADO, hacia la zona oculta
        lim_giro = np.where((self.paso_muro == 1) | (self.paso_muro == 2), GIRO_LADO, 360.0)
        fin_asomo = (self.modo == ASOMO) & self.aso_gira & (self.giro_acum >= lim_giro) & (self.t_modo >= T_HISTERESIS)
        # MURO DE CANTO: llega al punto, se alinea a lo largo del muro y hace un solo barrido izquierda-derecha
        llega_c = canto & (self.canto_t < 0) & ultimo_u & (self.t_modo >= T_HISTERESIS) & (
            (d_u < D_LLEGADA) | (self.t_bloqueo > 1.0) | (self.t_modo > T_INVESTIGA_MAX))
        self.canto_t = np.where(llega_c, 0.0, np.where(canto & (self.canto_t >= 0), self.canto_t + DT, self.canto_t))
        fin_canto = canto & (self.canto_t >= T_CANTO)
        fin_alt = (self.modo == VENTAJA_ALTURA) & (self.giro_acum >= 360.0)
        nuevo = np.full(n, -1)
        for i in np.where(fin_asomo | fin_alt)[0]:
            if fin_asomo[i] and self.paso_muro[i] == 1:          # paso 2: el otro extremo del mismo muro
                self._planear_otro_extremo(i)
                nuevo[i] = INVESTIGAR
                continue
            if fin_asomo[i] and self.paso_muro[i] == 2:          # paso 3: mirar el muro de canto
                if self._planear_canto(i):
                    nuevo[i] = MURO_CANTO
                    continue
            self.paso_muro[i] = 0
            if fin_alt[i]:
                self.insp_n[i] = 0                     # ronda nueva con el mapa que se amplió desde la altura
            else:
                self._marcar_revisado(i)
            nuevo[i] = SIGUIENTE_OBSTACULO if self._planear_siguiente(i) else VENTAJA_ALTURA
        # paso 4: después del canto, 360° de búsqueda (alto) y luego lo de siempre
        self.paso_muro = np.where(fin_canto, 0, self.paso_muro)
        nuevo = np.where(fin_canto, ASOMO, nuevo)
        cambia = nuevo >= 0
        self.modo = np.where(llega_u, ASOMO, np.where(cambia, nuevo, self.modo))
        self.t_modo = np.where(llega_u | cambia, 0.0, self.t_modo)
        self.giro_acum = np.where(llega_u | cambia, 0.0, self.giro_acum)
        self.aso_gira = np.where(llega_u | fin_canto, True, self.aso_gira)          # al llegar detrás del muro rota de inmediato
        self._girar_hacia_interior(fin_canto)
        self.canto_t = np.where(cambia & (nuevo == MURO_CANTO), -1.0, self.canto_t)
        self.t_bloqueo = np.where(cambia, 0.0, self.t_bloqueo)
        # BÚSQUEDA ACTIVA: giro de 360° mapeando con el LiDAR -> revisar detrás de cada panel detectado, uno por uno
        busc = self.modo == BUSCAR
        fin_giro = busc & (self.bfase == B_GIRO) & (self.giro_acum >= 360.0)
        self.entrada &= busc & (self.bfase == B_GIRO) & ~fin_giro          # V15: el 360° de entrada es una sola vuelta
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
        inv = inv | (self.modo == SIGUIENTE_OBSTACULO)              # mismo vuelo por ruta (otro destino)
        cnt = self.modo == MURO_CANTO
        inv = inv | (cnt & (self.canto_t < 0))                      # V15: el vuelo al punto de canto también
        tran = busc & (self.bfase == B_TRANSITO)
        insp = busc & (self.bfase == B_INSPECCION)
        decide = fij & (self.estado == VIGILANDO)
        bia = self.modo == BUSQUEDA_IA
        decide_b = bia & (self.estado == VIGILANDO)
        # BÚSQUEDA POR IA: cada acción cambia una consigna que persiste hasta que otra acción la cambie
        a_ = np.where(decide_b, acc_dron, -1)
        self.v_ia_f = np.where(a_ == 6, VEL_IA_AVANCE, np.where((a_ >= 0) & (a_ <= 2), 0.0, self.v_ia_f))
        self.v_ia_l = np.where(a_ == 1, -VEL_IA_LATERAL, np.where(a_ == 2, VEL_IA_LATERAL,
                                                                 np.where((a_ == 0) | (a_ == 6), 0.0, self.v_ia_l)))
        self.z_ia = np.clip(self.z_ia + np.where(a_ == 3, PASO_Z_IA, np.where(a_ == 7, -PASO_Z_IA, 0.0)), Z_NOMINAL, Z_MAX)
        self.g_ia = np.clip(self.g_ia + np.where(a_ == 8, PASO_GIMBAL_IA, np.where(a_ == 9, -PASO_GIMBAL_IA, 0.0)),
                            GIMBAL_MIN, GIMBAL_MAX)
        yaw_ia = np.where(a_ == 4, -YAW_GIRO_IA, np.where(a_ == 5, YAW_GIRO_IA, 0.0))
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
            rc["maniobra"] += np.where(inicia & fij & (self.ev_cand == k), costo, 0.0)
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
        ataque_j = vis & (dist_s < D_REFLEJO) & (s["vac"] > V_ATAQUE)
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
        alineado = np.abs(err_v) < np.radians(20)             # V15 · fase D: avanza con hasta 20° de error (antes 12°)
        # el flanqueo se vuela a Z_FLANCO (fuera del alcance del ladrón); a Z_TRANSITO si la ruta no tenía margen
        arriba = np.where(self.vuelo_alto | alt, self.dz > Z_TRANSITO - 0.25, self.dz > Z_FLANCO - 0.25)
        libre_v = self.lidar > DIST_PROTECCION_VUELO
        self.t_bloqueo = np.where(vuela & alineado & arriba & ~libre_v, self.t_bloqueo + DT, 0.0)
        avanza_det = vuela & alineado & arriba & libre_v & ~self.perimetro
        vx_b = np.where(eva, 0.0, np.where(avanza_ia, VEL_AVANCE, np.where(avanza_det, np.minimum(VEL_INVESTIGA, 0.8 * d_v + 0.3), 0.0)))
        vy_b = np.where(eva & (self.clase == 1), -VEL_LATERAL, np.where(eva & (self.clase == 2), VEL_LATERAL,
                                                                        np.where(self.reflejo, self.lat_esq, 0.0)))
        # búsqueda por IA: sus consignas; el LiDAR (rayo de la cámara) y el perímetro solo frenan el avance
        frena_ia = ~libre_v | cerca_peaton | self.perimetro
        vx_b = np.where(bia & ~eva, np.where(frena_ia, np.minimum(self.v_ia_f, 0.0), self.v_ia_f), vx_b)
        vy_b = np.where(bia & ~eva, self.v_ia_l, vy_b)
        # altura: la nominal para rastrear y verificar; por encima de los paneles en los vuelos de búsqueda; la
        # maniobra de VENTAJA DE ALTURA sube rápido a Z_TACTICO. El seguimiento vertical lo hace el gimbal; el dron
        # solo cambia de altura por eso si el gimbal se satura (objetivo mucho más alto).
        busqueda_det = inv | aso | cnt | (busc & (self.bfase != B_GIRO))
        z_obj = np.where(alt, Z_TACTICO, np.where(busqueda_det, np.where(self.vuelo_alto, Z_TRANSITO, Z_FLANCO), Z_NOMINAL))
        z_obj = np.where(aso, Z_GIRO, z_obj)                        # V15: GIRO_360 de búsqueda a la altura segura
        # V15 · 360° DE ENTRADA: bajo (Z_ENTRADA) para mapear todos los muros; guarda: si alguien entra a menos de
        # R_GUARDA_ENTRADA o se acerca rápido, sube a la altura segura y termina la vuelta arriba
        giro_ent = busc & (self.bfase == B_GIRO) & self.entrada
        # D-041: también con las personas RECORDADAS (vistas hace < T_PERSONA_MEM s, aunque ya no estén en cuadro)
        mem_cerca = (self.activa & (self.pm_t < T_PERSONA_MEM)
                     & (np.hypot(self.pm_x - self.dx[:, None], self.pm_y - self.dy[:, None]) < R_GUARDA_ENTRADA)).any(1)
        self.entrada_alta |= giro_ent & ((vis & ((dist_s < R_GUARDA_ENTRADA) | (s["vac"] > 1.0))).any(1) | mem_cerca)
        z_obj = np.where(giro_ent, np.where(self.entrada_alta, Z_SEGURA, Z_ENTRADA), z_obj)
        # V15 · fase B: si el ladrón va a pasar por debajo (anti-cenit) o ya está en la zona ciega, el dron sube a la altura
        # segura mientras se aparta: así, aunque la cámara lo pierda un momento, no lo puede alcanzar con el brazo ni saltando
        z_obj = np.where(self.anticenit | self.ciego, np.maximum(z_obj, Z_SEGURA), z_obj)
        z_obj = np.where(bia, self.z_ia, z_obj)                               # la IA elige su altura
        z_obj = np.where(self.gmb_sat_arriba, np.minimum(self.dz + 0.5, Z_MAX), z_obj)
        # despeje: nunca bajar sobre un panel que haya visto el LiDAR (no se sabe su altura: se respeta la de tránsito)
        d_pan = self._dist_paneles_detectados()
        # V13: despeje más amplio (R_DESPEJE) y también contra los puntos sueltos de la nube (muros aún sin agrupar): tras
        # una interrupción táctica volando por encima de un muro, no baja encima de él
        e_, x_, y_ = self._puntos_mapa()
        d_nube = np.full(n, np.inf)
        np.minimum.at(d_nube, e_, np.hypot(x_ - self.dx[e_], y_ - self.dy[e_]))
        z_obj = np.where(np.minimum(d_pan, d_nube) < R_DESPEJE, np.maximum(z_obj, Z_TRANSITO), z_obj)
        alguien_cerca = (vis & (dist_s < 6.0)).any(1)
        # V15 · fase D: en los vuelos de búsqueda la altura se toma con más ganancia (sube 1 m en ~0.7 s, no en ~1.7 s)
        vz_auto = np.clip(np.where(inv | aso | cnt, 2.0, 0.8) * (z_obj - self.dz), np.where(bia, -1.0, -0.4),
                          np.where(alt | bia | (giro_ent & self.entrada_alta) | self.anticenit | self.ciego | inv | aso,
                                   VEL_SUBIDA_RAPIDA, 0.6))
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
        # V15: con la nube, la PÉRDIDA va hacia su media (sin acercarse a menos de 4 m: desde ahí la ve)
        gx_, gy_ = self.pf_mx - self.dx, self.pf_my - self.dy
        gd_ = np.maximum(np.hypot(gx_, gy_), 1e-6)
        vg_ = np.where(pred & ~eva & self.pf_on, np.clip(0.8 * (gd_ - 4.0), 0.0, VEL_PRED_MAX), 0.0)
        # si un muro del mapa queda entre el dron y la nube, no avanza: solo la mira (el flanqueo rodeará el muro)
        Dp_ = np.stack([self.dx, self.dy], -1)
        Gp_ = np.stack([self.pf_mx, self.pf_my], -1)
        tras_muro = np.zeros(n, bool)
        for j in range(K_DET):
            tras_muro |= (j < self.det_n) & cruce_segmentos(Dp_, Gp_, self.det_a[:, j], self.det_b[:, j])[0]
        vg_ = np.where(tras_muro, 0.0, vg_)
        # y, como la persecución original, respeta el bloqueo frontal del LiDAR (la cámara mira hacia la nube)
        vg_ = np.where(~libre, 0.0, vg_)
        vx_c = np.where(pred & self.pf_on, vg_ * gx_ / gd_, vx_c)
        vy_c = np.where(pred & self.pf_on, vg_ * gy_ / gd_, vy_c)
        # navegación predictiva: el empuje apunta al punto de intercepción (corta en las esquinas, no lo persigue por detrás)
        vx_c = np.where(persigue & ~eva, v_rango * ux_l, vx_c)
        vy_c = np.where(persigue & ~eva, v_rango * uy_l, vy_c)
        # V15 · MURO DE CANTO: centrado -> DESPL_CANTO al primer lado -> DESPL_CANTO al otro (una pasada, lateral)
        en_cnt = cnt & (self.canto_t >= 0) & ~eva
        tc_ = self.canto_t - T_ALINEA_CANTO
        off_c = np.where(tc_ < 0, 0.0, np.where(tc_ < T_LADO1_CANTO, 1.0, -1.0)) * self.canto_lado * DESPL_CANTO
        ox_ = self.inv_x - np.sin(self.canto_psi0) * off_c - self.dx
        oy_ = self.inv_y + np.cos(self.canto_psi0) * off_c - self.dy
        od_ = np.maximum(np.hypot(ox_, oy_), 1e-6)
        vo_ = np.minimum(VEL_CANTO, 1.5 * od_)
        vx_c = np.where(en_cnt, vo_ * ox_ / od_, vx_c)
        vy_c = np.where(en_cnt, vo_ * oy_ / od_, vy_c)
        # ================= V12 · REFLEJO DE PUNTO CIEGO =================
        # vector de escape: con el objetivo a la vista, dónde estará dentro de T_LEAD s; en la PÉRDIDA, el punto predicho
        # que avanza con el tiempo. Si él (o su posición) cae en la zona ciega debajo del dron, paso táctico hacia atrás,
        # alejándose de ese punto, hasta d = h/tan(45°+VFOV/2) + margen, sumando la velocidad del objetivo (sigue con él
        # a esa distancia en vez de quedar encima). Durante una evasión del árbitro el retroceso se SUMA al esquive (sigue
        # subiendo y apartándose de lado, y además se aleja del punto donde el objetivo quedaría debajo).
        self.d_ciego = d_punto_ciego(self.dz)
        tp_c = self.t_modo + T_PRED_INI
        px_c = np.where(pred, np.where(self.pf_on, self.pf_mx, self.pred_x0 + self.pred_vx * tp_c), self.ult_x + self.tvx * T_LEAD)
        py_c = np.where(pred, np.where(self.pf_on, self.pf_my, self.pred_y0 + self.pred_vy * tp_c), self.ult_y + self.tvy * T_LEAD)
        hx_c, hy_c = self.dx - px_c, self.dy - py_c
        d_esc = np.hypot(hx_c, hy_c)
        d_c = np.where(pred, d_esc, np.minimum(d_esc, np.hypot(self.dx - self.ult_x, self.dy - self.ult_y)))
        puede_c = fij | pred
        # V15 · DISTANCIA ADAPTATIVA: si se acerca a más de 1 m/s (Kalman, relativo al dron), la separación mínima es la
        # zona ciega + lo que se cierra antes de igualarle la velocidad (v²/2a + v·retardo), hasta D_SEP_MAX (~6 m)
        ux_k, uy_k = -hx_c / np.maximum(d_esc, 1e-6), -hy_c / np.maximum(d_esc, 1e-6)
        v_cierra = -((self.tvx - self.dvx) * ux_k + (self.tvy - self.dvy) * uy_k)
        v_cierra = np.where(ve & self.kf_ok, v_cierra, 0.0)
        self.d_sep = np.where(v_cierra > 1.0, np.minimum(self.d_ciego + v_cierra ** 2 / (2 * A_FRENO_DRON)
                                                        + v_cierra * T_LAG_DRON, D_SEP_MAX), self.d_ciego)
        self.ciego = puede_c & np.where(self.ciego, d_c < self.d_sep + HIST_CIEGO, d_c < self.d_sep)
        v_c = np.clip(K_CIEGO * (self.d_sep + HIST_CIEGO - d_c) + 0.5 + np.maximum(v_cierra, 0.0), 0.0, VEL_CIEGO)
        sin_dir = d_esc < 0.2                                  # justo encima: retrocede por la cola
        ux_c = np.where(sin_dir, -np.cos(self.psi), hx_c / np.maximum(d_esc, 1e-6))
        uy_c = np.where(sin_dir, -np.sin(self.psi), hy_c / np.maximum(d_esc, 1e-6))
        # V15: cerca del borde de la arena el retroceso se curva hacia la tangente que va al centro (rodea al ladrón en vez
        # de huir en línea recta contra la geocerca)
        borde = np.minimum(ARENA - np.abs(self.dx), ARENA - np.abs(self.dy))
        mezcla = np.clip((8.0 - borde) / 6.0, 0.0, 1.0)
        t1x, t1y = -uy_c, ux_c
        haz = np.where(t1x * -self.dx + t1y * -self.dy >= 0, 1.0, -1.0)
        ux_c, uy_c = (1 - mezcla) * ux_c + mezcla * haz * t1x, (1 - mezcla) * uy_c + mezcla * haz * t1y
        nu_ = np.maximum(np.hypot(ux_c, uy_c), 1e-6)
        ux_c, uy_c = ux_c / nu_, uy_c / nu_
        ffx, ffy = np.where(pred, self.pred_vx, self.tvx), np.where(pred, self.pred_vy, self.tvy)
        vcx, vcy = v_c * ux_c + ffx + np.where(eva, vx_c, 0.0), v_c * uy_c + ffy + np.where(eva, vy_c, 0.0)
        k_c = VEL_CIEGO / np.maximum(np.hypot(vcx, vcy), VEL_CIEGO)
        vcx, vcy = vcx * k_c, vcy * k_c
        # contra el borde de la geocerca no retrocede hacia afuera: se desliza por el borde. V15: con la distancia de
        # frenado (a 4.5 m/s y jerk limitado hacen falta varios metros), no con la posición actual
        xs = self.dx + self.dvx * np.abs(self.dvx) / (2 * A_FRENO_DRON)
        ys = self.dy + self.dvy * np.abs(self.dvy) / (2 * A_FRENO_DRON)
        vcx = np.where((np.abs(xs) > ARENA - 1.5) & (vcx * self.dx > 0), 0.0, vcx)
        vcy = np.where((np.abs(ys) > ARENA - 1.5) & (vcy * self.dy > 0), 0.0, vcy)
        vx_c = np.where(self.ciego, vcx, vx_c)
        vy_c = np.where(self.ciego, vcy, vy_c)
        vx_c, vy_c, self.guarda = self._guarda_mapa(vx_c, vy_c)
        vx_c, vy_c = self._guarda_personas_y_cerca(vx_c, vy_c)
        # ================= consignas -> MAVLink (GUIDED) -> ArduPilot: cascada de PID del autopiloto =================
        # la Jetson manda velocidad X/Y/Z; la Pixhawk la convierte en inclinación (roll/pitch) y la estabiliza con sus
        # propios PID (control.AutopilotoArduPilot). Devuelve el cabeceo que pedía la consigna en bruto (suavidad)
        dvx0, dvy0, ch_p0 = self.dvx.copy(), self.dvy.copy(), self.chasis_pitch.copy()
        cab_cmd = self.ap.paso(self, vx_c, vy_c, vz_c, DT)
        self.dx += 0.5 * (dvx0 + self.dvx) * DT
        self.dy += 0.5 * (dvy0 + self.dvy) * DT
        self.dz = np.clip(self.dz + self.dvz * DT, Z_MIN, Z_MAX)

        # ================= guiñada: seguimiento HORIZONTAL (independiente de la evasión) =================
        # banda muerta: mientras el objetivo esté en el 20% central del FOV horizontal, el yaw queda en 0; si sale
        # de esa franja corrige hasta dejarlo bien centrado (histéresis) y se detiene. Igual al verificar.
        ci = np.clip(self.cand, 0, N_PERS - 1)
        ang_c = np.take_along_axis(ang_s, ci[:, None], 1)[:, 0]
        c_vis = np.take_along_axis(vis, ci[:, None], 1)[:, 0] & ver
        rcf = self.modo == RECONFIRMAR
        ang_t = np.where(fij | rcf, o[:, 4] * HFOV / 2, ang_c)
        hay_t = np.where(fij | rcf, (o[:, 0] > 0.5) & (fij | rcf), c_vis)
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
        yaw_vuelo = np.clip(-2.5 * np.degrees(err_v), -YAW_MAX_PRED, YAW_MAX_PRED)   # V15 · fase D: hasta 120°/s (RATE_Y_MAX)
        # mirar: detrás del panel al llegar a inspeccionarlo; en el ASOMO, primero hacia la última posición
        err_m, d_m = self._ir_a(self.mira_x, self.mira_y)
        yaw_mira = np.clip(-2.0 * np.degrees(err_m), -YAW_MAX, YAW_MAX)
        mirando = (aso & ~self.aso_gira) | (insp & (self.t_vuelo < T_MIRA))
        a_nominal = self.dz < Z_NOMINAL + 0.3
        # V13: el GIRO_360 empieza al llegar a Z_GIRO (o a los T_ESPERA_GIRO s si no puede bajar)
        listo_giro = (np.abs(self.dz - Z_GIRO) < 0.2) | (self.t_modo > T_ESPERA_GIRO)
        barre = ((busc & (self.bfase == B_GIRO) & (a_nominal | self.entrada_alta)) | (insp & (self.t_vuelo >= T_MIRA)) | (aso & self.aso_gira & listo_giro)
                 | (en_estacion & (self.dz >= Z_TACTICO - 0.2)))
        # predicción: la nariz va hacia el punto extrapolado, con la guiñada rápida del autopiloto
        tp = self.t_modo + T_PRED_INI
        px_p = np.where(self.pf_on, self.pf_mx, self.pred_x0 + self.pred_vx * tp)
        py_p = np.where(self.pf_on, self.pf_my, self.pred_y0 + self.pred_vy * tp)
        err_p, d_pp = self._ir_a(px_p, py_p)
        yaw_pred = np.clip(-2.5 * np.degrees(err_p), -YAW_MAX_PRED, YAW_MAX_PRED)
        vel_barrido = np.where(aso, YAW_GIRO_360, YAW_BUSQUEDA)
        yaw_cmd = np.where(fij, yaw_fij, np.where(rcf, tasa_t, np.where(ver, yaw_ver, np.where(pred, yaw_pred, np.where(vuela, yaw_vuelo,
                           np.where(mirando, yaw_mira, np.where(barre, self.busca_dir * vel_barrido, 0.0)))))))
        # perímetro de colisión: solo alguien a menos de D_PERIMETRO pausa un giro de búsqueda
        de_busqueda = barre | (fij & (self.giro_mem != 0))
        yaw_cmd = np.where(de_busqueda & self.perimetro, 0.0, yaw_cmd)
        yaw_cmd = np.where(bia, yaw_ia, yaw_cmd)
        # V15 · MURO DE CANTO: la nariz siempre a lo largo del muro (el desplazamiento es lateral, sin barrido de guiñada)
        err_cn = envolver(self.canto_psi0 - self.psi)
        yaw_cmd = np.where(cnt & (self.canto_t >= 0), np.clip(-3.0 * np.degrees(err_cn), -YAW_MAX, YAW_MAX), yaw_cmd)
        # reflejo de punto ciego con el objetivo fuera del cuadro: giro hacia su vector de escape para volver a meterlo
        err_c, _ = self._ir_a(px_c, py_c)
        yaw_cmd = np.where(self.ciego & fij & ~ve, np.clip(-2.5 * np.degrees(err_c), -YAW_MAX_PRED, YAW_MAX_PRED), yaw_cmd)
        # V15 · REFLEJO ANTI-CENIT PREDICTIVO: si el Kalman dice que va a pasar por debajo (entra a la zona ciega en menos
        # de T_CENIT s), la nariz gira YA hacia el punto por donde va a salir (a la tasa máxima de la Pixhawk)
        r0x, r0y = self.kf_x[:, 0, 0] - self.dx, self.kf_x[:, 1, 0] - self.dy
        vrx, vry = self.tvx - self.dvx, self.tvy - self.dvy
        a2 = np.maximum(vrx ** 2 + vry ** 2, 1e-6)
        b2 = 2 * (r0x * vrx + r0y * vry)
        rc_ = self.d_ciego
        disc = b2 ** 2 - 4 * a2 * (r0x ** 2 + r0y ** 2 - rc_ ** 2)
        raiz = np.sqrt(np.maximum(disc, 0.0))
        t_in, t_out = (-b2 - raiz) / (2 * a2), (-b2 + raiz) / (2 * a2)
        self.anticenit = (fij & ve & self.kf_ok & (disc > 0) & (t_out > 0) & (t_in < T_CENIT) & (a2 > 1.0))
        ex_, ey_ = self.kf_x[:, 0, 0] + self.tvx * t_out, self.kf_x[:, 1, 0] + self.tvy * t_out
        err_s, _ = self._ir_a(ex_, ey_)
        yaw_cmd = np.where(self.anticenit, np.clip(-2.5 * np.degrees(err_s), -YAW_MAX_PRED, YAW_MAX_PRED), yaw_cmd)
        self.ap.guinada(self, yaw_cmd, DT)                 # tasa de guiñada (ATC_RAT_YAW, aceleración limitada)
        self.psi = envolver(self.psi - np.radians(self.yaw_dps) * DT)
        self.giro_acum = np.where(barre, self.giro_acum + np.abs(self.yaw_dps) * DT, self.giro_acum)

        # ================= gimbal (pitch): seguimiento VERTICAL con la cámara, no con el dron =================
        # foco: el objetivo fijado, la persona que se verifica o, ante una amenaza, la persona detectada más cercana
        j_cerca = np.argmin(np.where(vis, dist_s, 99.0), 1)
        foco = np.where((fij | (self.modo == RECONFIRMAR)) & self.lock, 0, np.where(c_vis, ci, np.where(self.amenaza & vis.any(1), j_cerca, -1)))
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
        meta = np.where(bia, self.g_ia, meta)                                 # la IA apunta la cámara
        # objetivo fijado pero fuera de cuadro (memoria del tracker): la cámara se queda donde estaba, no vuelve de
        # golpe al ángulo de reposo (era el latigazo antes de la búsqueda por IA)
        meta = np.where(fij & ~tiene, self.gimbal_cmd, meta)
        # V12: punto ciego sin foco -> la cámara apunta a su vector de escape; ALTURA_TÁCTICA -> -45° (todo el suelo posible)
        meta = np.where(self.ciego & ~tiene, -np.degrees(np.arctan2(self.dz - 0.9, np.maximum(d_c, 0.3))), meta)
        meta = np.where(alt & ~tiene, GIMBAL_TACTICO, meta)
        meta = np.where(aso & ~tiene, GIMBAL_GIRO, meta)              # V13: GIRO_360 con la cámara en el horizonte
        meta = np.where((self.modo == MURO_CANTO) & (self.canto_t >= 0) & ~tiene, self.canto_gmb, meta)   # V15: de canto
        meta = np.where(giro_ent & ~tiene, np.where(self.entrada_alta, GIMBAL_GIRO, GIMBAL_ENTRADA), meta)    # V15
        tasa_g = np.where(tiene, tasa_g, np.clip(3.0 * (meta - self.gimbal_cmd), -GIMBAL_VEL, GIMBAL_VEL))
        self.gimbal_cmd = np.clip(self.gimbal_cmd + tasa_g * DT, np.maximum(GIMBAL_MIN, self.gimbal - G_ADELANTO),
                                  np.minimum(GIMBAL_MAX, self.gimbal + G_ADELANTO))
        # ================= Jetson -> PWM (AUX1) -> gimbal BaseCam =================
        # consigna filtrada (EMA) -> PID de ángulo del gimbal -> motor brushless (30°/s, -45°..+15°); su IMU compensa
        # el cabeceo del chasis con retardo (control.GimbalBaseCam)
        self.cam_pitch = self.gb.paso(self.gimbal_cmd, self.chasis_pitch - ch_p0, DT)
        self.gimbal, self.err_gmb = self.gb.ang.copy(), self.gb.err.copy()
        # BARRERA DURA (regla 1, D-014): pase lo que pase, la cámara no baja de -45° ni sube de +15°
        self.cam_pitch = np.clip(self.cam_pitch, GIMBAL_MIN, GIMBAL_MAX)
        self.gimbal = np.clip(self.gimbal, GIMBAL_MIN, GIMBAL_MAX)
        self.gmb_min_ep = np.minimum(self.gmb_min_ep, self.cam_pitch)
        self.gmb_sat_arriba = tiene & (-e_f > GIMBAL_MAX + 1.0)

        # ================= suavidad del control (reward shaping) =================
        # u = comandos normalizados (cabeceo, guiñada, gimbal) antes de los filtros de rampa. Derivada: solo si la IA
        # estuvo al mando en este paso y en el anterior (un cambio de modo no es culpa de la política).
        mando = mando0 & (decide | decide_b)
        u = np.clip(np.stack([cab_cmd / CAB_MAX, yaw_cmd / YAW_MAX, tasa_g / GIMBAL_VEL], -1), -1.0, 1.0)
        # V12 · MULTA SOLO A LO QUE COMANDA LA RED. Con el objetivo fijado, la guiñada (banda muerta) y el gimbal los mueve
        # el seguimiento determinista, y el acercamiento, el retroceso y el reflejo de punto ciego son automáticos: no
        # se le cobran. Se le cobra el cabeceo de un AVANZAR que ella eligió y el giro que ella pidió con el objetivo
        # fuera del cuadro; en la búsqueda por IA (PERDIDA_IA) todo es suyo.
        m_ia = np.stack([(decide & (acc_dron == 6) & ~aprox & ~self.ciego) | decide_b,
                         (decide & ~ve & (self.giro_mem != 0) & ~self.ciego) | decide_b, decide_b], -1)
        u_ia = np.where(m_ia, u, 0.0)
        pen_delta = np.where(mando & self.mando_prev, K_DELTA * np.abs(u_ia - self.u_prev).sum(1), 0.0)
        pen_esfuerzo = np.where(mando, K_ESFUERZO * np.abs(u_ia).sum(1), 0.0)
        rc["control"] -= pen_delta + pen_esfuerzo
        # jitter FÍSICO por eje (todo lo que se movió, lo comande quien lo comande), solo para el registro
        du = np.where((mando & self.mando_prev)[:, None], np.abs(u - self.u_prev_fis), 0.0)
        self.u_prev, self.u_prev_fis, self.mando_prev = u_ia, u, mando

        # ================= personas =================
        self._mover_personas(acc_persona)

        # V15 · CANSANCIO Y PULSO del ladrón con su rapidez real de este paso
        v0p = np.hypot(self.pvx[:, 0], self.pvy[:, 0])
        sobre = np.maximum(v0p - VC_LADRON, 0.0)
        alerta = ~self.tactico | (self.l_alerta_t <= 0)
        gasto = sobre + K_TENSION * (alerta & (v0p > 1.0))
        self.reserva = np.clip(self.reserva - gasto * DT / D_PRIMA
                               + np.where(sobre <= 0, (1.0 - self.reserva) * DT / TAU_RECUPERA, 0.0), 0.0, 1.0)
        hr_obj = np.minimum(PULSO_REPOSO + PULSO_ESTRES * alerta + 18.0 * v0p + 60.0 * (1.0 - self.reserva), PULSO_MAX)
        self.pulso = self.pulso + (hr_obj - self.pulso) * DT / TAU_PULSO

        # ================= eventos y fin de la misión =================
        d_all = np.hypot(self.px - self.dx[:, None], self.py - self.dy[:, None])
        # peatones: burbuja de seguridad ALCANCE_Z; ladrón: su alcance real (de pie con el brazo arriba, o en el salto)
        alcance = np.full(d_all.shape, ALCANCE_Z)
        alcance[:, 0] = self.alc_pie + self.salto_h                     # V15: según la estatura del ladrón
        toca = (d_all < ALCANCE_H) & self.activa & (self.dz[:, None] < alcance)
        choque = toca.any(1)
        lo_alcanza_ladron = toca[:, 0]
        choca_panel = np.zeros(n, bool)
        for j in range(self.pa.shape[1]):
            d, _ = dist_punto_segmento(np.stack([self.dx, self.dy], -1), self.pa[:, j], self.pb[:, j])
            choca_panel |= (d < RADIO_DRON + GROSOR_MURO / 2) & (self.dz < self.ph[:, j] + 0.2)
        fuera = (np.abs(self.dx) > ARENA) | (np.abs(self.dy) > ARENA)
        self.t += 1
        designado = self.modo >= FIJADO
        # v9: cuenta solo el tiempo RASTREÁNDOLO de verdad (FIJADO): la misión se cumple al acumular T_RASTREO s de
        # rastreo, aunque en el medio lo haya perdido y lo haya vuelto a encontrar
        self.t_fijado = np.where((self.modo == FIJADO) & (self.trk == 0), self.t_fijado + DT, self.t_fijado)
        en_busqueda = np.isin(self.modo, (PREDECIR, INVESTIGAR, ASOMO, SIGUIENTE_OBSTACULO, VENTAJA_ALTURA, MURO_CANTO))
        agotado = en_busqueda & (self.t_perdida >= T_MISION_PERDIDA)       # V12: MISIÓN_PERDIDA tras 90 s sin recuperarlo
        perdido = agotado | (bia & (self.t_modo >= T_BUSQUEDA_IA))      # se agotó la búsqueda determinista o la de la IA
        no_encontrado = (self.modo <= VERIFICAR) & (self.t_fase2 >= T_BUSQUEDA_MAX)
        falla = choque | fuera | choca_panel | perdido | no_encontrado
        # V15 · RENDICIÓN: contador continuo con el ladrón (el de verdad) fijado y a la vista; se pausa sin verlo mientras
        # el dron todavía sabe dónde está (memoria, PÉRDIDA, RECONFIRMAR) y vuelve a cero al pasar a la búsqueda
        a_la_vista = (self.modo == FIJADO) & self.lock & (self.trk == 0)
        self._contador(a_la_vista, designado)
        self.rendido = self.t_cont >= T_RINDE_BASE + T_RINDE_RESERVA * self.reserva * self.moral
        exito = self.rendido & ~falla
        tiempo = self.t >= PASOS_EPISODIO
        rc["fallas"] += np.where(choque, R_COLISION, 0.0) + np.where(fuera, R_GEOCERCA, 0.0) + np.where(choca_panel, R_CHOQUE_PANEL, 0.0)
        rc["fallas"] += np.where(perdido | no_encontrado, R_PERDIDO, 0.0)
        rc["exito"] += np.where(exito, R_EXITO + R_EXITO_RESTANTE * np.maximum(PASOS_EPISODIO - self.t, 0) * DT, 0.0)
        tope = tiempo & ~falla & ~exito
        rc["fallas"] += np.where(tope, R_TOPE, 0.0)                       # C2: perder por tiempo cuesta
        rew_p = np.where(lo_alcanza_ladron, 10.0, 0.0) + np.where(perdido | no_encontrado, 5.0, 0.0) + np.where(perdida, 1.0, 0.0)
        done = falla | exito | tiempo
        phi_nuevo = self._potencial()
        rc["guia"] += np.where(done, 0.0, GAMMA_GUIA * phi_nuevo - self.phi)
        self.phi = phi_nuevo

        self.obs_retraso = self._sensores()
        visto = self.info_sensor["lock"] & (self.trk == 0)          # V15: solo con la persona correcta
        rc["vista"] += np.where(visto & ~choque, R_VISTA, 0.0)
        self.t_vista_ac += np.where(visto, DT, 0.0)
        d_h0 = np.hypot(self.px[:, 0] - self.dx, self.py[:, 0] - self.dy)
        rc["vista"] += np.where(visto & (d_h0 >= R_OPT_MIN) & (d_h0 <= R_OPT_MAX), R_RANGO, 0.0)
        rc["vista"] += np.where(visto & (d_h0 < 3.0), R_MUY_CERCA, 0.0)
        rew_p -= np.where(visto, R_VISTA, 0.0)
        # DISCOVERY (V12): el ladrón vuelve a entrar en el FOV (detectado, sin tapar) después de haber estado oculto más de
        # T_OCULTO_DESC con el objetivo ya designado. Se paga una vez por ocultamiento, a la táctica que lo logró
        vis0 = self.info_sensor["visible_real"][:, 0]
        self.t_oculto = np.where(vis0, 0.0, self.t_oculto + DT)
        # la multa R_PIERDE se cobra en el mismo instante en que se arma el bono (oculto más de T_OCULTO_DESC): igual y
        # opuesta, así perderlo a propósito para cobrar el bono no rinde; un parpadeo de menos de 1 s no se multa
        arma = designado & (self.t_oculto > T_OCULTO_DESC) & ~self.arm_desc & ~done
        rc["pierde"] += np.where(arma, R_PIERDE, 0.0)
        self.arm_desc |= arma
        self.descubre = self.arm_desc & vis0
        self.moral = np.where(self.descubre, np.maximum(self.moral * K_MORAL, MORAL_MIN), self.moral)
        rc["descubre"] += np.where(self.descubre, R_DESCUBRE, 0.0)
        self.arm_desc &= ~self.descubre
        rew_d = sum(rc[k] for k in R_COMP)
        info = dict(choque=choque, choque_ladron=lo_alcanza_ladron, choque_peaton=choque & ~lo_alcanza_ladron,
                    panel=choca_panel, fuera=fuera, tiempo=tiempo, perdido=perdido, no_encontrado=no_encontrado,
                    exito=exito, inicia=inicia, pierde=perdida, recupera=recupera, reflejo=reflejo, dist=d_all[:, 0], visto=visto.copy(),
                    fijado=designado.copy(), peatones=self.activa[:, 1:].sum(1),
                    jitter=pen_delta, esfuerzo=pen_esfuerzo, al_mando=mando, descubre=self.descubre.copy(),
                    busqueda_ia=bia & mando, salto=self.salto_h > 0,
                    # V12: registro completo
                    t_ep=self.t * DT, r_comp=np.stack([rc[k] for k in R_COMP], 1), du=du, gmb_min=self.gmb_min_ep.copy(),
                    ciego=self.ciego.copy(), estado_busq=self.modo.copy(), t_perdida=self.t_perdida.copy(),
                    un_muro=self.un_muro.copy(), interrumpe=interrumpe, nivel_ep=self.lvl_ep.copy(),
                    # V15 · fase C: identidad
                    id_ok=designado & (self.trk == 0), cambio=self.ev_cambio.copy(), reconf=ev_reconf, cambio_det=ev_det,
                    cambio_nodet=self.ev_nodet.copy(),
                    cenit_ep=self.l_guion == L_GUION_CENIT,
                    # C3: custodia y búsqueda (para el resumen por nivel)
                    tope=tope, racha=self.racha_max.copy(), t_vista_ac=self.t_vista_ac.copy(),
                    t_rinde=T_RINDE_BASE + T_RINDE_RESERVA * self.reserva * self.moral,
                    t_readq_sum=self.t_readq_sum.copy(), n_readq=self.n_readq.copy(),
                    t_busq_est=self.t_busq_est.copy(), readq_est=self.readq_est.copy())
        if auto_reset and done.any():
            self.reset(done)
        return rew_d, rew_p, done, info

    def _contador(self, a_la_vista, designado):
        """V15 · contador continuo hacia la rendición (C1: pausa de T_PAUSA_REID s) y métricas de búsqueda (C3)."""
        reinicia = np.isin(self.modo, (INVESTIGAR, ASOMO, SIGUIENTE_OBSTACULO, VENTAJA_ALTURA, MURO_CANTO, BUSQUEDA_IA))
        # C3: re-adquisición (vuelve a estar a la vista tras perderlo): cuánto tardó y desde qué estado de búsqueda
        readq = a_la_vista & (self.t_desde_vista > T_OCULTO_DESC) & designado & (self.racha_max > 0)   # pérdidas > 1 s
        self.t_readq_sum += np.where(readq, self.t_desde_vista, 0.0)
        self.n_readq += readq
        if readq.any():
            ir = np.where(readq)[0]
            self.readq_est[ir, self.ult_busq[ir]] += 1
        en_b = np.isin(self.modo, BUSQUEDA_ESTADOS)
        self.ult_busq = np.where(en_b, self.modo, np.where(a_la_vista, PREDECIR, self.ult_busq))
        if en_b.any():
            ib = np.where(en_b)[0]
            self.t_busq_est[ib, self.modo[ib]] += DT
        # C1: la pausa dura T_PAUSA_REID s desde que lo perdió; después, la búsqueda lo reinicia como antes
        self.t_desde_vista = np.where(a_la_vista, 0.0, self.t_desde_vista + DT)
        reinicia &= self.t_desde_vista > T_PAUSA_REID
        self.t_cont = np.where(a_la_vista, self.t_cont + DT, np.where(reinicia, 0.0, self.t_cont))
        self.racha_max = np.maximum(self.racha_max, self.t_cont)

    # ------------------------------------------------------------------ personas
    def mover_personas(self):
        """Solo para la misión (fase 1): mueve a las personas con el dron controlado desde afuera."""
        self._mover_personas(None)
        self.obs_retraso = self._sensores()

    def _mover_personas(self, acc_persona):
        vxp, vyp = self._velocidad_personas(acc_persona)
        libre = np.isnan(self.v_forzada[..., 0])              # las velocidades impuestas por la misión no se tocan
        vxs, vys = self._campo_potencial(vxp, vyp)
        vxp, vyp = np.where(libre, vxs, vxp), np.where(libre, vys, vyp)
        # cinemática humana: no gira en seco (aceleración lateral limitada), acelera y frena con límites, y si quiere
        # girar más de 45° tiene que frenar primero (como una persona real que cambia de dirección corriendo)
        s_d = np.hypot(vxp, vyp)
        h_d = np.arctan2(vyp, vxp)
        v_act = np.hypot(self.pvx, self.pvy)
        dif = envolver(h_d - self.p_rumbo)
        a_fric = MU_PISO * G
        # giro: ω <= a_fric / v (radio de giro r = v²/a_fric, crece con la velocidad); casi parado pivota hasta OMEGA
        w_max = np.minimum(OMEGA_PERSONA, 0.85 * a_fric / np.maximum(v_act, 0.3))
        giro = np.clip(dif, -w_max * DT, w_max * DT)
        self.p_rumbo = np.where(s_d > 0.05, envolver(self.p_rumbo + giro), self.p_rumbo)
        a_lat = v_act * np.abs(giro) / DT
        # para cambiar mucho de rumbo baja la velocidad de forma continua (180° -> hasta V_GIRO_PERSONA)
        s_obj = np.where(np.abs(dif) > 0.35, np.maximum(np.minimum(s_d, V_GIRO_PERSONA), s_d * (1.0 + np.cos(dif)) / 2.0), s_d)
        # aceleración longitudinal dentro de lo que el giro deja del círculo de fricción; propulsión que cae con v
        a_resto = np.sqrt(np.maximum(a_fric ** 2 - a_lat ** 2, 0.0))
        a_mas = np.minimum(A_PROPULSION * np.maximum(1.0 - v_act / V_TOPE_HUMANO, 0.15), a_resto)
        a_menos = np.minimum(A_FRENO_PERSONA, a_resto + 0.5)
        v_act = v_act + np.clip(s_obj - v_act, -a_menos * DT, a_mas * DT)
        self.pvx, self.pvy = v_act * np.cos(self.p_rumbo), v_act * np.sin(self.p_rumbo)
        self.px = np.where(self.activa, np.clip(self.px + self.pvx * DT, -ARENA, ARENA), self.px)
        self.py = np.where(self.activa, np.clip(self.py + self.pvy * DT, -ARENA, ARENA), self.py)
        # nadie atraviesa los paneles ni los obstáculos: se empuja fuera del muro y, como en un contacto real, se
        # anula la parte de su velocidad que va contra el muro (se desliza a lo largo de él en vez de empujarlo)
        pp = np.stack([self.px, self.py], -1)
        pv = np.stack([self.pvx, self.pvy], -1)
        for j in range(self.pa.shape[1]):
            a = np.broadcast_to(self.pa[:, j][:, None, :], pp.shape)
            bb = np.broadcast_to(self.pb[:, j][:, None, :], pp.shape)
            d, c = dist_punto_segmento(pp, a, bb)
            dentro = d < 0.35
            nrm = (pp - c) / np.maximum(d, 1e-6)[..., None]
            pp = np.where(dentro[..., None], c + nrm * 0.35, pp)
            contra = np.minimum(np.sum(pv * nrm, -1), 0.0)
            pv = np.where(dentro[..., None], pv - contra[..., None] * nrm, pv)
        self.px, self.py = pp[..., 0].copy(), pp[..., 1].copy()
        self.pvx, self.pvy = pv[..., 0].copy(), pv[..., 1].copy()
        desliza = np.hypot(self.pvx, self.pvy) > 0.05
        self.p_rumbo = np.where(desliza, np.arctan2(self.pvy, self.pvx), self.p_rumbo)
        # SALTO del ladrón: atacando (o el ladrón aprendido) con el dron a menos de D_SALTO y al alcance de un salto
        dh0 = np.hypot(self.dx - self.px[:, 0], self.dy - self.py[:, 0])
        quiere = np.where(self.tactico, self.l_modo == L_ATACAR, True) & (self.lvl_ep >= NIVEL_ATAQUE)
        salta = (quiere & self.activa[:, 0] & (self.salto_t <= 0) & (self.salto_cd <= 0) & (dh0 < D_SALTO)
                 & (self.dz < self.alc_pie + SALTO_ADULTO[1] + 0.2))
        self.salto_alc = np.where(salta, self.alc_pie + self.rng.uniform(SALTO_ADULTO[0], SALTO_ADULTO[1], self.n), self.salto_alc)
        self.salto_t = np.where(salta, T_SALTO, np.maximum(self.salto_t - DT, 0.0))
        self.salto_cd = np.where(salta, T_RECARGA_SALTO, np.maximum(self.salto_cd - DT, 0.0))
        tau = 1.0 - self.salto_t / T_SALTO
        self.salto_h = np.where(self.salto_t > 0, (self.salto_alc - self.alc_pie) * 4.0 * tau * (1.0 - tau), 0.0)

    def _ruta(self, P, T):
        """PATHFINDING por grafo de visibilidad (equivale a A* exacto entre muros finos). Nodos: las esquinas de cada
        muro alargadas E_NODO, más el origen P y el destino T; dos nodos se conectan si ningún muro corta la recta.
        Floyd-Warshall vectorizado (son pocos nodos) da las distancias; el siguiente punto es el vecino visible de P
        que minimiza (P->vecino) + (vecino->T). P, T: (n, k, 2). Devuelve (siguiente punto, largo de la ruta).
        V15 (velocidad): si la recta P->T no cruza ningún muro, la ruta más corta es esa recta; el grafo solo se arma
        para los entornos donde algún tramo directo choca con un muro (el resultado es el mismo)."""
        n, k = P.shape[:2]
        cruza = np.zeros((n, k), bool)
        for j in range(self.pa.shape[1]):
            cruza |= cruce_segmentos(P, T, self.pa[:, j][:, None, :], self.pb[:, j][:, None, :])[0]
        sig = T.copy()
        largo = np.hypot(*(T - P).transpose(2, 0, 1))
        e = np.where(cruza.any(1))[0]
        if len(e):
            sig[e], largo[e] = self._ruta_grafo(P[e], T[e], self.pa[e], self.pb[e])
        return sig, largo

    def _ruta_grafo(self, P, T, A, B):
        """El grafo de visibilidad de _ruta para un subconjunto de entornos (A, B: sus muros)."""
        n, k = P.shape[:2]
        S = A.shape[1]
        u = (B - A) / np.maximum(np.hypot(*(B - A).transpose(2, 0, 1)), 1e-6)[..., None]
        nodos = np.clip(np.concatenate([A - u * E_NODO, B + u * E_NODO], 1), -ARENA + 0.5, ARENA - 0.5)   # (n, 2S, 2)
        K = 2 * S + 2
        Q = np.concatenate([np.broadcast_to(nodos[:, None], (n, k, 2 * S, 2)), P[:, :, None], T[:, :, None]], 2)
        Qa, Qb = Q[:, :, :, None, :], Q[:, :, None, :, :]
        tapa = np.zeros((n, k, K, K), bool)
        for j in range(S):
            a_ = A[:, j][:, None, None, None, :]
            b_ = B[:, j][:, None, None, None, :]
            tapa |= cruce_segmentos(np.broadcast_to(Qa, (n, k, K, K, 2)), np.broadcast_to(Qb, (n, k, K, K, 2)), a_, b_)[0]
        d = np.hypot(*(Qb - Qa).transpose(4, 0, 1, 2, 3))
        W = np.where(tapa, np.inf, d)
        D = W.copy()
        for m in range(K):
            D = np.minimum(D, D[..., :, m:m + 1] + D[..., m:m + 1, :])
        iP, iT = K - 2, K - 1
        costo = W[:, :, iP, :] + D[:, :, :, iT]                          # (n, k, K): por cada primer salto
        costo[:, :, iP] = np.inf
        mejor = np.argmin(costo, -1)
        largo = np.take_along_axis(costo, mejor[..., None], -1)[..., 0]
        sig = np.take_along_axis(Q, mejor[..., None, None].repeat(2, -1), 2)[:, :, 0]
        sin_ruta = ~np.isfinite(largo)
        return np.where(sin_ruta[..., None], T, sig), np.where(sin_ruta, np.hypot(*(T - P).transpose(2, 0, 1)), largo)

    def _campo_potencial(self, vx, vy):
        """NAVEGACIÓN POR CAMPOS POTENCIALES (APF) de las personas (ladrón y peatones). Cada panel a menos de R_APF
        genera un campo que crece al acercarse: la parte del movimiento que va hacia el muro se frena y se convierte en
        flujo tangencial (componente rotacional, para no quedar trabadas de frente), hacia donde ya iban a lo largo del
        muro o hacia el extremo más cercano. Se suma el aporte de todos los paneles y se conserva la rapidez deseada:
        rodean el muro con fluidez. Quietas no hay empuje, así que pueden apoyarse contra el muro para esconderse."""
        sp = np.hypot(vx, vy)
        P = np.stack([self.px, self.py], -1)                           # (n, N_PERS, 2)
        v = np.stack([vx, vy], -1)
        dv = np.zeros_like(v)
        k_w = 1.0 / D_MIN_APF - 1.0 / R_APF
        for j in range(self.pa.shape[1]):
            A = np.broadcast_to(self.pa[:, j][:, None, :], P.shape)
            B = np.broadcast_to(self.pb[:, j][:, None, :], P.shape)
            d, c = dist_punto_segmento(P, A, B)
            nr = (P - c) / np.maximum(d, 1e-6)[..., None]              # del muro hacia la persona
            ab = B - A
            L = np.maximum(np.hypot(ab[..., 0], ab[..., 1]), 1e-6)
            u = ab / L[..., None]
            w = np.clip((1.0 / np.maximum(d, D_MIN_APF) - 1.0 / R_APF) / k_w, 0.0, 1.0)
            hacia = np.maximum(-np.sum(v * nr, -1), 0.0)               # rapidez hacia el muro
            vt = np.sum(v * u, -1)
            frac = np.sum((P - A) * u, -1) / L
            sentido = np.where(np.abs(vt) > 0.3 * sp, np.sign(vt), np.where(frac < 0.5, -1.0, 1.0))
            dv += (w * hacia)[..., None] * (nr + K_TAN_APF * sentido[..., None] * u)
        v2 = v + dv
        n2 = np.hypot(v2[..., 0], v2[..., 1])
        v2 = np.where((n2 > 1e-6)[..., None], v2 / np.maximum(n2, 1e-6)[..., None] * sp[..., None], v)
        return v2[..., 0], v2[..., 1]

    def _velocidad_personas(self, acc_persona):
        n = self.n
        # V15 · CANSANCIO: la rapidez de carrera cae hacia el trote a medida que se vacía la reserva
        self.v_corr_ef = V_TROTE + (self.v_correr - V_TROTE) * np.clip(self.reserva / 0.25, 0.0, 1.0)
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
        vel = np.where(quieto, 0.0, np.where(corre_rl, self.v_corr_ef, VEL_CAMINAR))
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
        expuesto = self.info_sensor["visible_real"][:, 0] if self.info_sensor else np.zeros(n, bool)
        m = self.l_modo.copy()
        self.l_t -= DT
        self.l_alerta_t -= DT
        # PUNTO CIEGO: la cubierta (detrás del panel, del lado opuesto al dron) a la que llega antes caminando
        _, largo_h = self._ruta(np.repeat(P[:, None], N_PANELES, 1), H)
        cerca = np.argmin(largo_h, 1)
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
        self.l_t = np.where(llega, r.uniform(T_ESCONDIDO[0], T_ESCONDIDO[1], n) * (2.0 - self.reserva), self.l_t)   # V15: cansado se esconde más
        # escondido: si lo ven más de 1 s cambia de cubierta; al acabar el tiempo se asoma, cambia o carga
        esc = m == L_ESCONDIDO
        self.l_expuesto = np.where(esc & expuesto, self.l_expuesto + DT, 0.0)
        cambia_vis = esc & (self.l_expuesto > 1.0)
        fin_esc = esc & (self.l_t <= 0) & ~cambia_vis
        u = r.random(n)
        puede_atacar = (dd < 10.0) & (self.dz < Z_ATAQUE) & (self.stamina > 1.0) & (self.reserva > 0.15)
        a_asoma = fin_esc & ((u < 0.5) | ((u >= 0.8) & ~puede_atacar))
        puede_atacar = puede_atacar | ((dd < 12.0) & (self.dz < Z_ATAQUE) & (self.stamina > 1.0))
        a_cambia = (fin_esc & (u >= 0.5) & (u < 0.8)) | cambia_vis
        a_ataca = fin_esc & (u >= 0.8) & puede_atacar
        # además, de vez en cuando corre a tumbar el dron desde donde esté (si lo tiene cerca y al alcance)
        a_ataca |= (((m == L_ESCONDIDO) | (m == L_ASOMARSE) | (m == L_CUBRIRSE)) & puede_atacar & (dd < 12.0)
                    & (r.random(n) < TASA_ATAQUE * self.reserva * DT) & ~fin_esc)
        # ACORRALADO: el dron bajo (< Z_ATAQUE) y cerca, y su huida (alejarse del dron) bloqueada por un muro o el borde a
        # menos de 2 m -> corre hacia el dron para saltarle
        hu = (P - D) / np.maximum(dd, 1e-6)[:, None]
        Q = P + 2.0 * hu
        bloqueada = (np.abs(Q) > ARENA - 0.5).any(1)
        for j in range(self.pa.shape[1]):
            bloqueada |= cruce_segmentos(P, Q, self.pa[:, j], self.pb[:, j])[0]
        acorralado = (dd < D_ACORRALADO) & (self.dz < Z_ATAQUE) & bloqueada & (self.stamina > 1.0)
        a_ataca |= ((m != L_ATACAR) & acorralado & (r.random(n) < TASA_ACORRALADO * self.k_ataque * DT) & ~fin_esc)
        a_ataca &= self.lvl_ep >= NIVEL_ATAQUE                       # V15 (D6): en los niveles 0 y 1 no ataca
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
                     np.where(((m == L_CUBRIRSE) | (m == L_ESCONDIDO))[:, None], de(H, self.l_panel),
                              np.where((m == L_ASOMARSE)[:, None], de(AS, self.l_panel), D)))
        # V14 · GUIONES DEL NIVEL 0 (cuando ya notó al dron): HUIDA en zigzag (cambia de rumbo cada 2.5-5 s; a veces da
        # media vuelta y pasa junto al dron) o CENIT (corre a meterse debajo del dron y lo sigue; salta si puede)
        gh = (self.l_guion == L_GUION_HUIDA) & (self.l_alerta_t <= 0)
        gc = (self.l_guion == L_GUION_CENIT) & (self.l_alerta_t <= 0)
        self.l_tg = self.l_tg - DT
        nuevo_r = gh & (self.l_tg <= 0)
        self.l_ang = np.where(nuevo_r, np.where(r.random(n) < P_REVERSA, np.pi, r.uniform(-1.75, 1.75, n)), self.l_ang)
        self.l_tg = np.where(nuevo_r, r.uniform(T_RUMBO_HUIDA[0], T_RUMBO_HUIDA[1], n), self.l_tg)
        ca, sa = np.cos(self.l_ang), np.sin(self.l_ang)
        T_h = np.clip(P + 6.0 * np.stack([hu[:, 0] * ca - hu[:, 1] * sa, hu[:, 0] * sa + hu[:, 1] * ca], -1),
                      -(ARENA - 1.5), ARENA - 1.5)
        T = np.where(gh[:, None], T_h, np.where(gc[:, None], D, T))
        m = np.where(gc & (dd < 2.0 * D_SALTO) & (self.lvl_ep >= NIVEL_ATAQUE), L_ATACAR, np.where(gh | gc, L_DEAMBULAR, m))
        self.l_modo = m
        # camina hacia el siguiente punto de la ruta más corta (rodea los muros por sus esquinas); frena cerca del destino
        W, _ = self._ruta(P[:, None], T[:, None])
        vec_t = T - P
        dist = np.maximum(np.hypot(vec_t[:, 0], vec_t[:, 1]), 1e-6)
        vec = W[:, 0] - P
        d_w = np.maximum(np.hypot(vec[:, 0], vec[:, 1]), 1e-6)
        d_h = np.hypot(*(de(H, self.l_panel) - P).T)
        quieto = ((m == L_ESCONDIDO) | (m == L_ASOMARSE)) & (dist < 0.35)
        corre = (((m == L_CUBRIRSE) & expuesto) | (m == L_ATACAR) | ((m == L_ESCONDIDO) & (d_h > 2.0))) & (self.stamina > 0.1)
        vel = np.where(quieto, 0.0, np.where(corre, self.v_corr_ef, np.where(m == L_DEAMBULAR, 0.9, 1.2)))
        # D-041: expuesto mientras cambia de cubierta -> esprint (si le queda reserva)
        esprinta = corre & (m == L_CUBRIRSE) & expuesto & (self.reserva > 0.25)
        vel = np.where(esprinta, self.v_sprint, vel)
        corre_g = np.where(gc, dist > 1.0, dd < 10.0) & (self.stamina > 0.1)
        corre = np.where(gh | gc, corre_g, corre)
        vel = np.where(gh | gc, np.where(corre_g, self.v_corr_ef, VEL_CAMINAR), vel)
        vel = np.minimum(vel, 2.0 * dist)
        # deambulando: nuevo destino al llegar
        llego = (m == L_DEAMBULAR) & (dist < 1.0)
        if llego.any():
            lim0 = self.g_lim[:, 0]
            self.g_wx[:, 0] = np.where(llego, lim0[:, 0] + r.random(n) * (lim0[:, 1] - lim0[:, 0]), self.g_wx[:, 0])
            self.g_wy[:, 0] = np.where(llego, lim0[:, 2] + r.random(n) * (lim0[:, 3] - lim0[:, 2]), self.g_wy[:, 0])
        return vel * vec[:, 0] / d_w, vel * vec[:, 1] / d_w, corre

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
            Wp, _ = self._ruta(np.stack([px, py], -1), np.stack([self.g_wx[:, 1:], self.g_wy[:, 1:]], -1))
            rx_, ry_ = Wp[..., 0] - px, Wp[..., 1] - py
            rd_ = np.maximum(np.hypot(rx_, ry_), 1e-6)
            vx = np.where(dm, rx_ / rd_ * self.g_vel[:, 1:], vx)
            vy = np.where(dm, ry_ / rd_ * self.g_vel[:, 1:], vy)
        # V14 · DISTRACTOR (nivel 2): va y viene cruzando la línea de vista dron-ladrón (al 65 % del camino), sin acercarse
        # al dron a menos de D_RESPETO_CIVIL: tapa al ladrón y obliga a seguir el ID correcto, no a esquivarlo
        ds = (g == G_DISTRACTOR) & self.activa[:, 1:]
        if ds.any():
            ux, uy = self.px[:, 0] - self.dx, self.py[:, 0] - self.dy
            lu = np.maximum(np.hypot(ux, uy), 1e-6)
            nx, ny = (-uy / lu)[:, None], (ux / lu)[:, None]
            f_ = F_CRUCE_DISTRACTOR
            mx, my = (self.dx + f_ * ux)[:, None], (self.dy + f_ * uy)[:, None]
            lado = self.g_lado[:, 1:]
            # D-041: tras cada cruce descansa 15-30 s apartado (3x más lejos de la línea de vista) y luego vuelve a cruzar
            pausa_prev = self.g_pausa[:, 1:].copy()
            self.g_pausa[:, 1:] = np.where(ds, np.maximum(pausa_prev - DT, 0.0), pausa_prev)
            termina = ds & (pausa_prev > 0) & (self.g_pausa[:, 1:] <= 0)
            lado = np.where(termina, -lado, lado)
            self.g_lado[:, 1:] = lado
            f_lado = np.where(self.g_pausa[:, 1:] > 0, 3.0, 1.0)
            tx = mx + nx * ANCHO_DISTRACTOR * lado * f_lado
            ty = my + ny * ANCHO_DISTRACTOR * lado * f_lado
            ex, ey = tx - self.dx[:, None], ty - self.dy[:, None]
            de_ = np.maximum(np.hypot(ex, ey), 1e-6)
            k_ = np.maximum(D_RESPETO_CIVIL / de_, 1.0)
            tx = np.clip(self.dx[:, None] + ex * k_, -ARENA + 1, ARENA - 1)
            ty = np.clip(self.dy[:, None] + ey * k_, -ARENA + 1, ARENA - 1)
            llega = ds & (np.hypot(tx - px, ty - py) < 0.8) & (self.g_pausa[:, 1:] <= 0) & ~termina
            self.g_pausa[:, 1:] = np.where(llega, self.rng.uniform(15.0, 30.0, llega.shape), self.g_pausa[:, 1:])
            Wd, _ = self._ruta(np.stack([px, py], -1), np.stack([tx, ty], -1))
            rx_, ry_ = Wd[..., 0] - px, Wd[..., 1] - py
            rd_ = np.maximum(np.hypot(rx_, ry_), 1e-6)
            # si de todos modos quedó a menos de 2.5 m del dron (el dron se le acercó), se aparta
            ax_, ay_ = px - self.dx[:, None], py - self.dy[:, None]
            ad_ = np.maximum(np.hypot(ax_, ay_), 1e-6)
            aparta = ds & (ad_ < D_RESPETO_CIVIL - 0.5)
            rx_, ry_, rd_ = np.where(aparta, ax_, rx_), np.where(aparta, ay_, ry_), np.where(aparta, ad_, rd_)
            vx = np.where(ds, rx_ / rd_ * self.g_vel[:, 1:], vx)
            vy = np.where(ds, ry_ / rd_ * self.g_vel[:, 1:], vy)
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

    def puntos_nuevos(self, i):
        """SLAM: los puntos de la nube agregados desde la última foto del entorno i (el visor los acumula)."""
        k0, k1 = int(self.lm_i[i]), int(self.lid_i[i])
        k0 = max(k0, k1 - N_LIDAR)
        self.lm_i[i] = k1
        return [[round(float(self.lid_px[i, k % N_LIDAR]), 2), round(float(self.lid_py[i, k % N_LIDAR]), 2)]
                for k in range(k0, k1) if self.lid_ok[i, k % N_LIDAR]]

    def fijar_gimbal(self, angulo):
        """Fija el gimbal (misión, fase 1): comando, consigna, ángulo físico y cámara iguales, sin saltos."""
        self.gimbal[:] = self.gimbal_cmd[:] = self.cam_pitch[:] = angulo
        self.gb.fijar(angulo)
        self.err_gmb[:] = 0.0

    def foto(self, i):
        s = self.info_sensor
        pers = []
        for j in range(N_PERS):
            if not self.activa[i, j]:
                continue
            pers.append({"rol": "ladron" if j == 0 else "peaton",
                         "p": [round(float(self.px[i, j]), 3), round(float(self.py[i, j]), 3)],
                         "v": [round(float(self.pvx[i, j]), 2), round(float(self.pvy[i, j]), 2)],
                         "vis": bool(s["visible_real"][i, j]), "tap": bool(s["tapada_real"][i, j]), "id": int(self.ids[i, j]),
                         "sz": round(float(self.salto_h[i]), 2) if j == 0 else 0.0, "fv": round(float(self.frac_vis[i, j]), 2), "est": round(float(self.estatura[i, j]), 2),
                         "res": round(float(self.reserva[i]), 3) if j == 0 else None, "hr": round(float(self.pulso[i])) if j == 0 else None,
                         "ign": bool(self.ignorado[i, j]), "cand": bool(self.modo[i] == VERIFICAR and self.cand[i] == j),
                         "run": bool(self.corriendo[i]) if j == 0 else bool(self.g_vel[i, j] > 2.0 and np.isnan(self.v_forzada[i, j, 0]))})
        lad = pers[0]
        m_ = self.modo[i]
        tp = self.t_modo[i] + T_PRED_INI
        wx, wy = ((self.inv_x[i], self.inv_y[i]) if m_ in (INVESTIGAR, ASOMO, SIGUIENTE_OBSTACULO) else
                  (self.zc_x[i], self.zc_y[i]) if m_ == VENTAJA_ALTURA else
                  (self.pred_x0[i] + self.pred_vx[i] * tp, self.pred_y0[i] + self.pred_vy[i] * tp) if m_ == PREDECIR else
                  (self.ult_x[i], self.ult_y[i]) if m_ == BUSQUEDA_IA else
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
            "rfx": bool(self.reflejo[i]), "gd": bool(self.guarda[i]), "nube": self.puntos_nuevos(i), "dsc": bool(self.descubre[i]),
            "zia": round(float(self.z_ia[i]), 2), "gia": round(float(self.g_ia[i]), 1), "lt": int(self.lid_tipo[i]), "flq": bool(self.flanco[i]), "va": bool(self.vuelo_alto[i]),
            "ruta": ([[round(float(self.ruta[i, k, 0]), 2), round(float(self.ruta[i, k, 1]), 2)] for k in range(int(self.ruta_i[i]), int(self.ruta_n[i]))]
                     if (m_ in (INVESTIGAR, SIGUIENTE_OBSTACULO) or (m_ == BUSCAR and self.bfase[i] == B_TRANSITO)) else []),
            "lh": [round(float(self.lid_hx[i]), 2), round(float(self.lid_hy[i]), 2), round(float(self.lid_hz[i]), 2)],
            "det": [[round(float(v), 2) for v in (*self.det_a[i, j], *self.det_b[i, j])] for j in range(int(self.det_n[i]))],
            "ux": round(float(self.ult_x[i]), 2), "uy": round(float(self.ult_y[i]), 2),
            "gmb": round(float(self.cam_pitch[i]), 1), "yc": bool(self.yaw_corrige[i]),
            "cp": round(float(self.chasis_pitch[i]), 1), "cr": round(float(self.chasis_roll[i]), 1),
            "eg": round(float(self.err_gmb[i]), 1),
            "op": int(self.evento_op[i]), "t2": round(float(self.t_fase2[i]), 1), "tf": round(float(self.t_fijado[i]), 1),
            "tc": round(float(self.t_cont[i]), 1), "trd": round(float(T_RINDE_BASE + T_RINDE_RESERVA * self.reserva[i] * self.moral[i]), 1), "mor": round(float(self.moral[i]), 2),
            "rinde": bool(self.rendido[i]),
            "tsv": round(float(self.t_sin_ver[i]), 1), "lm": int(self.l_modo[i]), "tac": bool(self.tactico[i]),
            # V12: máquina de estados de la búsqueda, reflejo de punto ciego y datos brutos del LiDAR
            "eb": NOMBRE_ESTADO[m_] if 0 <= m_ < len(NOMBRE_ESTADO) else str(m_), "tpd": round(float(self.t_perdida[i]), 1),
            "ciego": bool(self.ciego[i]), "dcg": round(float(self.d_ciego[i]), 2), "npts": int(self.lid_ok[i].sum()),
            "ldt": round(float(self.lid_t[i]), 2),
            "ent": bool(self.entrada[i]), "enta": bool(self.entrada_alta[i]),
            "kf": ([round(float(v), 2) for v in (self.kf_x[i, 0, 0], self.kf_x[i, 1, 0], self.kf_x[i, 0, 1], self.kf_x[i, 1, 1],
                                                  np.sqrt(max(self.kf_P[i, :, 0, 0].mean(), 0.0)))] if self.kf_ok[i] else None),
            "pf": ([[round(float(self.pf_x[i, k]), 1), round(float(self.pf_y[i, k]), 1)]
                    for k in np.linspace(0, NP_PF - 1, N_PF_VISOR).astype(int)] if self.pf_on[i] else []),
            "pfm": [round(float(self.pf_mx[i]), 2), round(float(self.pf_my[i]), 2)] if self.pf_on[i] else None,
            "acn": bool(self.anticenit[i]), "dsep": round(float(self.d_sep[i]), 2),
            "trkp": int(self.trk[i]), "conf": round(float(self.sim_med[i]), 2), "rcf": bool(self.modo[i] == RECONFIRMAR),
            "pm": int(self.paso_muro[i]), "cnt": ([round(float(self.inv_x[i]), 2), round(float(self.inv_y[i]), 2),
                                                   round(float(self.canto_psi0[i]), 3)] if self.modo[i] == MURO_CANTO else None),
            "niv": int(self.lvl_ep[i]), "nivc": int(self.current_level), "lgu": int(self.l_guion[i]),
            "um": bool(np.allclose(self.pa[i, 1:N_PANELES], self.pa[i, 0]) and np.allclose(self.pb[i, 1:N_PANELES], self.pb[i, 0])),
        }

    def paneles(self, i):
        """Los paneles para el visor (V13: los superpuestos del currículo "Un Solo Muro" se mandan una sola vez)."""
        out = []
        for j in range(N_PANELES):
            p = [round(float(self.pa[i, j, 0]), 2), round(float(self.pa[i, j, 1]), 2),
                 round(float(self.pb[i, j, 0]), 2), round(float(self.pb[i, j, 1]), 2), float(self.ph[i, j])]
            if p not in out and max(abs(v) for v in p[:4]) < ARENA + 1:     # V14: sin los muros retirados (nivel 0)
                out.append(p)
        return out

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
