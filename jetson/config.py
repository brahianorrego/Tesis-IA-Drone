# -*- coding: utf-8 -*-
"""
Configuración central del sistema de detección de personas y evasión.
Proyecto de grado - Ingeniería Aeronáutica, Universidad de San Buenaventura.

Todos los scripts importan este archivo. Cambie aquí puertos, umbrales y
velocidades; no los "quemen" dentro del código.

Convenciones usadas en todo el proyecto
---------------------------------------
* Ejes del dron (MAVLink, MAV_FRAME_BODY_OFFSET_NED):
    x = adelante (+), y = derecha (+), z = abajo (+)  ->  subir es vz NEGATIVO.
* Gimbal de 2 ejes (pitch y roll): en yaw la cámara va fija a la nariz y el
  dron gira hacia la persona. El rumbo de la persona (angulo_persona_deg) sale
  de la posición del bbox en la imagen: 0 deg = al frente, POSITIVO = a la DERECHA.
* Distancias en centímetros; velocidades del dron en m/s.
"""

# ============================ PUERTOS SERIALES ==============================
# Recomendación: use rutas estables /dev/serial/by-id/... o /dev/serial/by-path/...
# porque /dev/ttyUSB0 y /dev/ttyUSB1 pueden intercambiarse al reiniciar (ver README).
PUERTO_PIXHAWK = "/dev/ttyTHS1"        # UART del header (pines 8/10) -> TELEM2 por el cable TELEM2.2 (sin 5 V)
PUERTO_PIXHAWK_USB = "/dev/serial/by-id/usb-ArduPilot_fmuv3_<NUMERO_DE_SERIE>-if00"  # solo banco/configuración; en vuelo desconectado (retroalimenta 5 V)
BAUD_PIXHAWK = 115200                # SERIAL2_BAUD = 115. A 460800 y 921600 la Pixhawk no entiende lo que transmite la Jetson

PUERTO_LIDAR = "/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0"  # TF03 (adaptador PL2303)
BAUD_LIDAR = 115200                  # valor de fábrica del TF03

PUERTO_GIMBAL = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_<NUMERO_DE_SERIE>-if00"  # BaseCam (mini-USB, CH9102)
BAUD_GIMBAL = 115200                 # valor de fábrica de SimpleBGC

# ================================ CÁMARA ====================================
CAMARA_TIPO = "usb"                  # "csi" (IMX219 por nvarguscamerasrc) o "usb". La CSI se descartó (pantallas verdes)
CAMARA_INDICE = 0                    # sensor-id (CSI) o /dev/videoN (USB)
CAMARA_CSI_DISPOSITIVO = "/dev/video2"   # IMX219 en CAM0 (overlay imx219-A); se usa con CAMARA_TIPO = "csi_v4l2"
CAMARA_CSI_HFOV_DEG = 62.2           # nominal del lente del IMX219: PENDIENTE medirlo como la USB
CAMARA_ANCHO = 640                   # resolución que recibe YOLO
CAMARA_ALTO = 480
CAMARA_FPS = 30
CAMARA_FLIP = 0                      # flip-method de nvvidconv (solo CSI)
# Modo del sensor IMX219. 1640x1232 es campo completo y 4:3 (igual que 640x480),
# así la imagen no se deforma. 1920x1080 recorta el sensor y es 16:9.
CSI_CAPTURA_ANCHO = 1640
CSI_CAPTURA_ALTO = 1232

# Campo de visión horizontal (grados). IMX219 con lente estándar ~62.2 deg.
# Mídalo: ponga un objeto de ancho W a distancia D que llene justo el ancho
# de la imagen -> HFOV = 2*atan(W / (2*D)).
CAMARA_HFOV_DEG = 38.9               # medido 2026-10-07 con la cámara USB Sonix: 94 cm visibles a 133 cm (LiDAR). La IMX219 vieja era 62.2

# ================================= YOLO =====================================
YOLO_MODELO = "yolo26n.engine"       # TensorRT FP16 generado en esta Jetson (2026-10-07). Respaldo: yolo26n.pt
YOLO_CONF_MIN = 0.40
YOLO_IMGSZ = 640
YOLO_TRACKER = "bytetrack.yaml"      # más liviano que botsort
# Bloqueo de objetivo: se sigue el mismo ID aunque otra persona se cruce.
FRAMES_PERDIDA_OBJETIVO = 15         # frames sin ver el ID antes de liberarlo
FACTOR_CAMBIO_OBJETIVO = 1.8         # cambia de ID solo si otra persona es 1.8x más grande (más cerca)

# ================================ LIDAR TF03 ================================
LIDAR_MIN_CM = 10                    # alcance mínimo del TF03
LIDAR_MAX_CM = 18000                 # 180 m. Lecturas >= a esto se tratan como "sin retorno"
LIDAR_FUERZA_MIN = 0                 # 0 = no filtrar por intensidad (el TF03 no la usa igual que el TF-Luna)

# ============================ GIMBAL BASECAM ================================
GIMBAL_PROTOCOLO = 1                 # 1: tramas '>' (suma simple)  2: tramas '$' (CRC16)
GIMBAL_HZ_LECTURA = 25               # consultas de ángulo por segundo
# Fuente del ángulo de paneo:
#  "marco": ángulo cámara respecto al chasis (CMD_GET_ANGLES_EXT). Es el correcto
#           para decidir hacia dónde evadir.
#  "imu":   yaw de la IMU de la cámara (CMD_GET_ANGLES). Deriva con el tiempo; úselo
#           solo si su placa no responde a CMD_GET_ANGLES_EXT.
GIMBAL_FUENTE_PANEO = "marco"
GIMBAL_SIGNO_PANEO = 1               # ponga -1 si al girar el pod a la DERECHA el ángulo baja

# Seguimiento visual: la Jetson ordena al gimbal centrar a la persona.
GIMBAL_TIENE_YAW = False             # gimbal de 2 ejes: solo se comanda pitch; el yaw lo hace el dron
GIMBAL_SEGUIMIENTO = True
GIMBAL_SEGUIR_PITCH = True
GIMBAL_HZ_COMANDO = 15
GIMBAL_KP = 0.6                      # fracción del error angular corregida por comando
GIMBAL_ZONA_MUERTA_DEG = 1.5
GIMBAL_PASO_MAX_DEG = 8.0            # corrección máxima por comando
GIMBAL_VEL_DPS = 90.0                # velocidad de giro pedida al gimbal (deg/s)
GIMBAL_PANEO_LIMITE_DEG = 100.0      # nunca pedir más de +/-100 deg respecto a la nariz
GIMBAL_PITCH_MIN_DEG = -45.0         # pitch "hacia arriba positivo"
GIMBAL_PITCH_MAX_DEG = 20.0
GIMBAL_PITCH_REPOSO_DEG = 0.0
GIMBAL_T_REGRESO_S = 2.0             # sin persona durante este tiempo -> volver al frente
# Signos de comando (se calibran en banco con: python3 gimbal_basecam.py --prueba-signos)
GIMBAL_SIGNO_YAW_CMD = 1             # +1 si aumentar el yaw IMU gira el pod a la derecha
GIMBAL_SIGNO_PITCH_CMD = 1           # +1 si aumentar el pitch IMU sube la cámara

# ======================= FUSIÓN Y ENTRADAS DE LA IA #2 ======================
# Columnas del CSV que entran al perceptrón multicapa (mismo orden en entrenamiento y vuelo).
FEATURES = ["distancia_cm", "area_bbox_norm", "angulo_persona_deg"]
ALTURA_PERSONA_M = 1.70              # para estimar distancia por tamaño cuando el láser no toca a la persona
MARGEN_LASER = 0.10                  # el centro de imagen debe caer dentro del bbox recortado 10 %
DIST_FEATURE_MAX_CM = 3000           # distancias mayores se recortan a 30 m (lejos = "libre")

CLASES = {
    0: "MANTENER",
    1: "EVADIR_IZQ",
    2: "EVADIR_DER",
    3: "DETENER_ASCENDER",
}

# ================================ DATASET ===================================
DATASET_DIR = "datos"
DATASET_HZ = 10                      # filas por segundo mientras graba
DATASET_OBJETIVO_FILAS = 1500

# ============================ MODELO ENTRENADO ==============================
MODELO_PKL = "decision.pkl"
MODELO_JSON = "decision_pesos.json"  # respaldo sin pickle (independiente de versiones)

# ================================= VUELO ====================================
CONTROL_HZ = 10                      # frecuencia de envío de setpoints a la Pixhawk
SYSID_COMPANION = 1                  # mismo sistema que el dron
COMPID_COMPANION = 191               # MAV_COMP_ID_ONBOARD_COMPUTER

VEL_EVASION_LATERAL = 1.0            # m/s para EVADIR_IZQ / EVADIR_DER
VEL_ASCENSO = 0.7                    # m/s para DETENER_ASCENDER
VEL_AVANCE_LIBRE = 0.0               # m/s hacia adelante si no hay nadie (0 = solo mantener)
VEL_MAX_H = 1.5                      # saturación final horizontal (m/s)
VEL_MAX_V = 1.0                      # saturación final vertical (m/s)

# Giro (yaw) hacia la persona: el gimbal es de 2 ejes y la cámara va fija a la nariz,
# así que el dron gira para mantener a la persona centrada (solo en VIGILANDO, nunca evadiendo).
YAW_SEGUIR_PERSONA = True
YAW_KP = 1.5                         # (deg/s) por grado de error: 10 deg fuera del centro -> 15 deg/s
YAW_RATE_MAX_DPS = 30.0              # giro máximo
YAW_ZONA_MUERTA_DEG = 2.0            # no corregir errores menores (evita temblor)

DURACION_EVASION_S = 1.5             # la maniobra se mantiene este tiempo (no oscila)
ENFRIAMIENTO_S = 1.0                 # freno tras cada maniobra
P_MIN = 0.60                         # probabilidad mínima del MLP para evadir
N_CONFIRMACION = 3                   # frames seguidos con la misma clase para evadir

ALT_MIN_OPERACION_M = 2.0            # por debajo: solo mantener, nunca evadir
ALT_MAX_M = 15.0                     # techo para DETENER_ASCENDER
DIST_OBSTACULO_CM = 300              # si el LiDAR ve algo más cerca, no avanza

TIMEOUT_PERCEPCION_S = 0.5           # dato de cámara/YOLO más viejo -> falla
TIMEOUT_LIDAR_S = 0.3
TIMEOUT_GIMBAL_S = 0.5
TIMEOUT_FALLA_PERSISTENTE_S = 2.0    # falla sostenida -> pedir MODO_FALLA
MODO_FALLA = "LOITER"                # "" para no cambiar de modo nunca
TIMEOUT_TELEMETRIA_S = 1.5           # sin HEARTBEAT de la Pixhawk
LOG_DIR = "logs"
