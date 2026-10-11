# -*- coding: utf-8 -*-
"""
Script de vuelo (ArduCopter, modo GUIDED):
  IA #1 (YOLO) + LiDAR + gimbal  ->  IA #2 (MLP)  ->  ÁRBITRO DE SEGURIDAD  ->  MAVLink

REGLAS DE SEGURIDAD (qué garantiza el código)
  1. El piloto manda. El script NUNCA arma, NUNCA despega y NUNCA pone GUIDED por
     su cuenta (salvo --sitl-despegue, que solo funciona contra el simulador).
     El piloto despega en STABILIZE/LOITER y pasa a GUIDED con el interruptor de
     modos. Para recuperar el control basta cambiar a otro modo: el script lo
     detecta, deja de enviar comandos y no vuelve a pedir GUIDED.
  2. El MLP propone, el árbitro decide: evadir exige probabilidad >= P_MIN durante
     N_CONFIRMACION frames seguidos; frenar es inmediato. La maniobra dura un tiempo
     fijo (no oscila izquierda/derecha) y termina con un freno.
  3. Nunca se avanza hacia una persona detectada (vx <= 0 siempre que hay persona).
  4. Si falta un dato (cámara, YOLO, LiDAR, gimbal) el dron se detiene; si la falla
     dura más de TIMEOUT_FALLA_PERSISTENTE_S se pide MODO_FALLA (LOITER) para
     devolver las palancas al piloto.
  5. Techo ALT_MAX_M para ascender y altura mínima ALT_MIN_OPERACION_M para evadir.
  6. Respaldo del autopiloto: si deja de recibir setpoints, ArduCopter frena solo
     tras GUID_TIMEOUT (3 s por defecto). Configure además la geocerca (README).

USO
  Banco, sin hélices y sin enviar nada a la Pixhawk (ver qué decidiría):
      python3 vuelo_evasion.py --simulacion --sin-pixhawk --ventana
  Simulador ArduPilot SITL en el PC, con sensores sintéticos:
      python3 vuelo_evasion.py --conexion udp:127.0.0.1:14551 --sensores-falsos --sitl-despegue 5
  Vuelo real:
      python3 vuelo_evasion.py
"""
import argparse
import csv
import math
import os
import signal
import sys
import threading
import time
from collections import namedtuple

import config as C
from comun import ModeloDecision, construir_muestra, vector_features, dibujar_hud

INACTIVO, VIGILANDO, EVADIENDO, ENFRIANDO, FALLA, ALTITUD_BAJA = (
    "INACTIVO", "VIGILANDO", "EVADIENDO", "ENFRIANDO", "FALLA", "ALTITUD_BAJA")

Percepcion = namedtuple(
    "Percepcion",
    "t n persona track_id clase prob probs distancia_cm fuente area paneo lidar_cm lidar_ok "
    "sensores_ok problemas lat_ms frame det muestra")

Salida = namedtuple("Salida", "vx vy vz estado motivo enviar pedir_modo_falla")


# ==========================================================================
# Percepción + IA #2 en su propio hilo
# ==========================================================================
class HiloPercepcion(threading.Thread):

    def __init__(self, fuente, modelo, cfg, usar_lidar, usar_gimbal):
        threading.Thread.__init__(self, name="percepcion", daemon=True)
        self.fuente = fuente
        self.modelo = modelo
        self.c = cfg
        self.usar_lidar = usar_lidar
        self.usar_gimbal = usar_gimbal
        self._lock = threading.Lock()
        self._ultima = None
        self.activo = True
        self.error = None

    def ultima(self):
        with self._lock:
            return self._ultima

    def run(self):
        n = 0
        try:
            while self.activo:
                r = self.fuente.obtener(timeout=0.5)
                if r is None:
                    if getattr(self.fuente, "fin", False):
                        self.activo = False
                    continue
                frame, det, lec, est = r
                t = time.time()
                m = construir_muestra(det, lec, est, self.c, t)
                problemas = []
                if self.usar_lidar and (lec is None or t - lec.t > self.c.TIMEOUT_LIDAR_S):
                    problemas.append("lidar")
                if self.usar_gimbal and (est is None or t - est.t > self.c.TIMEOUT_GIMBAL_S):
                    problemas.append("gimbal")
                clase, prob, probs = None, 0.0, {}
                if det.persona:
                    X = vector_features(m, self.c.FEATURES)
                    if X is None:
                        problemas.append("entradas IA")
                    else:
                        clase, prob, probs = self.modelo.predecir(X)
                n += 1
                p = Percepcion(det.t_frame, n, det.persona, det.track_id, clase, prob, probs,
                               m["distancia_cm"], m["fuente_distancia"], m["area_bbox_norm"],
                               m["angulo_persona_deg"], m["lidar_cm"], bool(m["lidar_valido"]),
                               not problemas, ",".join(problemas), det.lat_ms, frame, det, m)
                with self._lock:
                    self._ultima = p
        except Exception as e:  # el árbitro verá la percepción envejecer y frenará
            self.error = e
            print("[PERCEPCION] error fatal: %r" % e)


# ==========================================================================
# Árbitro de seguridad (lógica pura: se prueba sin hardware)
# ==========================================================================
class Arbitro(object):

    def __init__(self, cfg):
        self.c = cfg
        self.estado = INACTIVO
        self.clase_evasion = None
        self.t_evasion = 0.0
        self.t_enfriamiento = 0.0
        self.t_falla = None
        self.modo_falla_pedido = False
        self._cand = None
        self._cand_n = 0
        self._ultimo_n = -1

    def _olvidar_candidato(self):
        self._cand, self._cand_n = None, 0

    def _vector(self, clase, alt):
        c = self.c
        if clase == 1:
            return 0.0, -c.VEL_EVASION_LATERAL, 0.0
        if clase == 2:
            return 0.0, c.VEL_EVASION_LATERAL, 0.0
        if clase == 3:                                    # frenar y subir (NED: subir = vz < 0)
            return 0.0, 0.0, (-c.VEL_ASCENSO if alt < c.ALT_MAX_M - 0.5 else 0.0)
        return 0.0, 0.0, 0.0

    def paso(self, t, activo, alt, p):
        c = self.c
        if not activo:
            self.estado = INACTIVO
            self.clase_evasion = None
            self.t_falla = None
            self.modo_falla_pedido = False
            self._olvidar_candidato()
            return Salida(0.0, 0.0, 0.0, INACTIVO, "piloto al mando", False, False)

        # 1) Salud de la percepción
        vieja = p is None or (t - p.t) > c.TIMEOUT_PERCEPCION_S
        if vieja or not p.sensores_ok:
            if self.t_falla is None:
                self.t_falla = t
            pedir = (bool(c.MODO_FALLA) and not self.modo_falla_pedido and
                     t - self.t_falla > c.TIMEOUT_FALLA_PERSISTENTE_S)
            if pedir:
                self.modo_falla_pedido = True
            self.estado = FALLA
            self.clase_evasion = None
            self._olvidar_candidato()
            motivo = "percepcion detenida" if vieja else "falla " + p.problemas
            return Salida(0.0, 0.0, 0.0, FALLA, motivo, True, pedir)
        self.t_falla = None
        self.modo_falla_pedido = False

        # 2) Altura mínima para maniobrar
        if alt is None or alt < c.ALT_MIN_OPERACION_M:
            self.estado = ALTITUD_BAJA
            self.clase_evasion = None
            self._olvidar_candidato()
            return Salida(0.0, 0.0, 0.0, ALTITUD_BAJA, "altura < %.1f m" % c.ALT_MIN_OPERACION_M, True, False)

        # 3) Maniobra en curso: enclavada hasta terminar, luego freno
        if self.estado == EVADIENDO:
            if t - self.t_evasion < c.DURACION_EVASION_S:
                vx, vy, vz = self._vector(self.clase_evasion, alt)
                return Salida(vx, vy, vz, EVADIENDO, c.CLASES[self.clase_evasion], True, False)
            self.estado = ENFRIANDO
            self.t_enfriamiento = t
        if self.estado == ENFRIANDO and t - self.t_enfriamiento < c.ENFRIAMIENTO_S:
            return Salida(0.0, 0.0, 0.0, ENFRIANDO, "frenando", True, False)
        self.estado = VIGILANDO

        # 4) Decisión con confirmación (se cuenta por frame nuevo, no por ciclo)
        if p.persona:
            if p.n != self._ultimo_n:
                self._ultimo_n = p.n
                if p.clase in (1, 2, 3) and p.prob >= c.P_MIN:
                    if p.clase == self._cand:
                        self._cand_n += 1
                    else:
                        self._cand, self._cand_n = p.clase, 1
                else:
                    self._olvidar_candidato()
            if self._cand is not None and self._cand_n >= c.N_CONFIRMACION:
                self.estado = EVADIENDO
                self.clase_evasion = self._cand
                self.t_evasion = t
                self._olvidar_candidato()
                vx, vy, vz = self._vector(self.clase_evasion, alt)
                return Salida(vx, vy, vz, EVADIENDO, "inicio " + c.CLASES[self.clase_evasion], True, False)
            motivo = "persona: mantener"
            if self._cand is not None:
                motivo = "confirmando %s %d/%d" % (c.CLASES[self._cand], self._cand_n, c.N_CONFIRMACION)
            return Salida(0.0, 0.0, 0.0, VIGILANDO, motivo, True, False)

        self._olvidar_candidato()
        obstaculo = p.lidar_ok and p.lidar_cm < c.DIST_OBSTACULO_CM
        vx = 0.0 if obstaculo else c.VEL_AVANCE_LIBRE
        return Salida(vx, 0.0, 0.0, VIGILANDO, "obstaculo al frente" if obstaculo else "libre", True, False)


def yaw_hacia_persona(s, p, t, cfg):
    """Giro (deg/s, + = a la derecha) para centrar a la persona con la nariz del dron.

    El gimbal es de 2 ejes: en yaw la cámara va fija a la nariz, así que el dron gira para
    no perder a la persona. Solo mientras se vigila con una detección fresca: durante una
    evasión, el freno o una falla se sostiene el rumbo (0). Control proporcional sobre
    angulo_persona_deg, con zona muerta y saturación.
    """
    if not cfg.YAW_SEGUIR_PERSONA or s.estado != VIGILANDO or p is None or not p.persona:
        return 0.0
    if t - p.t > cfg.TIMEOUT_PERCEPCION_S or p.paneo != p.paneo:
        return 0.0
    if abs(p.paneo) < cfg.YAW_ZONA_MUERTA_DEG:
        return 0.0
    tasa = cfg.YAW_KP * p.paneo
    return max(-cfg.YAW_RATE_MAX_DPS, min(cfg.YAW_RATE_MAX_DPS, tasa))


class ModeloNulo(object):
    """Sustituto de la IA #2 para --sin-modelo: nunca propone evadir."""
    origen, clases = "ninguno", []

    def predecir(self, X):
        return None, 0.0, {}


def saturar(vx, vy, vz, hay_persona, cfg):
    """Última barrera antes de enviar: límites de velocidad y nunca avanzar hacia una persona."""
    if hay_persona:
        vx = min(vx, 0.0)
    h = math.hypot(vx, vy)
    if h > cfg.VEL_MAX_H:
        vx, vy = vx * cfg.VEL_MAX_H / h, vy * cfg.VEL_MAX_H / h
    vz = max(-cfg.VEL_MAX_V, min(cfg.VEL_MAX_V, vz))
    return vx, vy, vz


# ==========================================================================
# Enlace MAVLink con la Pixhawk
# ==========================================================================
class EnlaceMAVLink(object):
    # Usar solo velocidades (bits 3-5) y yaw_rate (bit 11): 0 sostiene el rumbo y distinto
    # de 0 gira hacia la persona. Si se ignorara yaw_rate, ArduCopter podría girar la nariz
    # hacia donde se mueve (WP_YAW_BEHAVIOR) y la cámara dejaría de mirar a la persona.
    MASCARA_VEL = 0b0000010111000111   # 0x05C7

    def __init__(self, conexion, baud, sysid, compid):
        from pymavlink import mavutil
        self.mavutil = mavutil
        self.mav_ = mavutil.mavlink
        self.conexion = conexion
        self.es_serial = conexion.startswith("/dev/") or conexion.upper().startswith("COM")
        self.m = mavutil.mavlink_connection(conexion, baud=baud, source_system=sysid,
                                            source_component=compid, autoreconnect=True)
        self.t0 = time.time()
        self.sys_obj = None
        self.comp_obj = None
        self.modo = "DESCONOCIDO"
        self.armado = False
        self.alt_rel_m = None
        self.volt = None
        self.t_hb = 0.0
        self._modos = dict((v, k) for k, v in mavutil.mode_mapping_acm.items())

    def esperar_autopiloto(self, timeout=30.0):
        fin = time.time() + timeout
        while time.time() < fin:
            msg = self.m.recv_match(type="HEARTBEAT", blocking=True, timeout=1.0)
            if msg is None:
                continue
            if msg.autopilot == self.mav_.MAV_AUTOPILOT_INVALID or msg.type in (
                    self.mav_.MAV_TYPE_GCS, self.mav_.MAV_TYPE_ONBOARD_CONTROLLER):
                continue
            self.sys_obj, self.comp_obj = msg.get_srcSystem(), msg.get_srcComponent()
            self.m.target_system, self.m.target_component = self.sys_obj, self.comp_obj
            self._procesar(msg)
            return True
        return False

    def solicitar_mensajes(self):
        for msg_id, hz in ((self.mav_.MAVLINK_MSG_ID_GLOBAL_POSITION_INT, 10),
                           (self.mav_.MAVLINK_MSG_ID_SYS_STATUS, 2)):
            self.m.mav.command_long_send(self.sys_obj, self.comp_obj,
                                         self.mav_.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
                                         msg_id, 1e6 / hz, 0, 0, 0, 0, 0)

    def _procesar(self, msg):
        tipo = msg.get_type()
        if msg.get_srcSystem() != self.sys_obj:
            return
        if tipo == "HEARTBEAT":
            if msg.get_srcComponent() != self.comp_obj:
                return
            self.t_hb = time.time()
            self.armado = bool(msg.base_mode & self.mav_.MAV_MODE_FLAG_SAFETY_ARMED)
            if msg.autopilot == self.mav_.MAV_AUTOPILOT_ARDUPILOTMEGA:
                self.modo = self.mavutil.mode_mapping_acm.get(msg.custom_mode, str(msg.custom_mode))
            else:
                self.modo = self.mavutil.mode_string_v10(msg)
        elif tipo == "GLOBAL_POSITION_INT":
            self.alt_rel_m = msg.relative_alt / 1000.0
        elif tipo == "SYS_STATUS":
            self.volt = msg.voltage_battery / 1000.0
        elif tipo == "STATUSTEXT":
            print("[PIXHAWK] %s" % msg.text)
        elif tipo == "COMMAND_ACK" and msg.result != 0:
            print("[PIXHAWK] comando %d rechazado (resultado %d)" % (msg.command, msg.result))

    def actualizar(self):
        for _ in range(300):
            msg = self.m.recv_match(blocking=False)
            if msg is None:
                break
            if msg.get_type() != "BAD_DATA":
                self._procesar(msg)

    def _t_boot_ms(self):
        return int((time.time() - self.t0) * 1000) & 0xFFFFFFFF

    def enviar_velocidad(self, vx, vy, vz, yaw_dps=0.0):
        self.m.mav.set_position_target_local_ned_send(
            self._t_boot_ms(), self.sys_obj, self.comp_obj,
            self.mav_.MAV_FRAME_BODY_OFFSET_NED, self.MASCARA_VEL,
            0, 0, 0, vx, vy, vz, 0, 0, 0, 0, math.radians(yaw_dps))

    def enviar_heartbeat(self):
        self.m.mav.heartbeat_send(self.mav_.MAV_TYPE_ONBOARD_CONTROLLER,
                                  self.mav_.MAV_AUTOPILOT_INVALID, 0, 0, self.mav_.MAV_STATE_ACTIVE)

    def solicitar_modo(self, nombre):
        numero = self._modos.get(nombre)
        if numero is None:
            print("[MAVLINK] modo desconocido: %s" % nombre)
            return
        self.m.mav.command_long_send(self.sys_obj, self.comp_obj, self.mav_.MAV_CMD_DO_SET_MODE, 0,
                                     self.mav_.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, numero, 0, 0, 0, 0, 0)

    def texto_gcs(self, texto, severidad=None):
        sev = self.mav_.MAV_SEVERITY_NOTICE if severidad is None else severidad
        try:
            self.m.mav.statustext_send(sev, texto[:50].encode("ascii", "ignore"))
        except Exception:
            pass

    def cerrar(self):
        self.m.close()


def sitl_despegue(enlace, alt):
    """Solo para el simulador: GUIDED, armar y despegar. Se niega en puertos seriales."""
    mav = enlace.mav_
    if enlace.es_serial:
        sys.exit("--sitl-despegue solo se permite con conexiones udp/tcp al simulador.")
    print("[SITL] GUIDED + armar + despegar a %.1f m" % alt)
    fin = time.time() + 90
    while time.time() < fin and not enlace.armado:
        enlace.solicitar_modo("GUIDED")
        enlace.m.mav.command_long_send(enlace.sys_obj, enlace.comp_obj,
                                       mav.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)
        for _ in range(30):
            time.sleep(0.1)
            enlace.actualizar()
    if not enlace.armado:
        sys.exit("[SITL] no armó (¿EKF/GPS del simulador aún no listos?)")
    enlace.m.mav.command_long_send(enlace.sys_obj, enlace.comp_obj, mav.MAV_CMD_NAV_TAKEOFF,
                                   0, 0, 0, 0, 0, 0, 0, alt)
    fin = time.time() + 40
    while time.time() < fin:
        time.sleep(0.2)
        enlace.actualizar()
        if enlace.alt_rel_m is not None and enlace.alt_rel_m >= 0.9 * alt:
            print("[SITL] en el aire a %.1f m" % enlace.alt_rel_m)
            return
    sys.exit("[SITL] no alcanzó la altura de despegue")


# ==========================================================================
# Programa principal
# ==========================================================================
COLUMNAS_LOG = ["t", "modo", "armado", "alt_m", "volt", "estado", "motivo", "persona", "track_id",
                "distancia_cm", "fuente_dist", "area", "angulo_persona_deg", "clase", "prob",
                "vx", "vy", "vz", "yaw_dps", "enviado", "edad_percepcion_ms", "lat_yolo_ms", "ciclo_ms"]


def main():
    ap = argparse.ArgumentParser(description="Evasión autónoma en GUIDED con IA")
    ap.add_argument("--conexion", default=C.PUERTO_PIXHAWK, help="puerto serial o udp:/tcp: (SITL)")
    ap.add_argument("--baud", type=int, default=C.BAUD_PIXHAWK)
    ap.add_argument("--modelo", default=C.MODELO_PKL)
    ap.add_argument("--sin-modelo", action="store_true",
                    help="sin IA de decisión: solo vigila y gira hacia la persona (nunca evade)")
    ap.add_argument("--simulacion", action="store_true",
                    help="decide como si estuviera en GUIDED a 5 m, pero NO envía nada a la Pixhawk")
    ap.add_argument("--sin-pixhawk", action="store_true", help="no abrir MAVLink (solo con --simulacion)")
    ap.add_argument("--sensores-falsos", action="store_true", help="escenario sintético sin cámara/LiDAR/gimbal")
    ap.add_argument("--fuente", help="índice de cámara o archivo de video")
    ap.add_argument("--sin-lidar", action="store_true")
    ap.add_argument("--sin-gimbal", action="store_true")
    ap.add_argument("--ventana", action="store_true", help="mostrar video con HUD (necesita monitor)")
    ap.add_argument("--video", help="grabar el HUD en este archivo .avi")
    ap.add_argument("--sitl-despegue", type=float, metavar="ALT", help="solo SITL: armar y despegar")
    a = ap.parse_args()

    if a.sin_pixhawk and not a.simulacion:
        sys.exit("--sin-pixhawk solo tiene sentido con --simulacion")
    usar_lidar = not a.sin_lidar and not a.sensores_falsos
    usar_gimbal = not a.sin_gimbal and not a.sensores_falsos
    if a.sensores_falsos:
        usar_lidar = usar_gimbal = True        # la fuente falsa entrega ambos
    if not usar_lidar and C.VEL_AVANCE_LIBRE > 0:
        print("Sin LiDAR no se permite avanzar: VEL_AVANCE_LIBRE = 0")
        C.VEL_AVANCE_LIBRE = 0.0

    # ---- Modelo ----
    if a.sin_modelo:
        modelo = ModeloNulo()
        print("[MODELO] ninguno (--sin-modelo): solo vigila y gira hacia la persona, no evade")
    else:
        ruta_json = os.path.join(os.path.dirname(os.path.abspath(a.modelo)), os.path.basename(C.MODELO_JSON))
        modelo = ModeloDecision(a.modelo, ruta_json, C.FEATURES)
        print("[MODELO] %s | entradas %s | clases %s" % (modelo.origen, C.FEATURES, modelo.clases))

    # ---- MAVLink ----
    enlace = None
    if not a.sin_pixhawk:
        print("[MAVLINK] conectando a %s ..." % a.conexion)
        enlace = EnlaceMAVLink(a.conexion, a.baud, C.SYSID_COMPANION, C.COMPID_COMPANION)
        if not enlace.esperar_autopiloto(30.0):
            sys.exit("[MAVLINK] sin HEARTBEAT de la Pixhawk (puerto, baudios, SERIAL2_PROTOCOL=2, TX/RX)")
        enlace.solicitar_mensajes()
        print("[MAVLINK] autopiloto sys %d comp %d, modo %s, armado %s"
              % (enlace.sys_obj, enlace.comp_obj, enlace.modo, enlace.armado))
        if a.sitl_despegue:
            sitl_despegue(enlace, a.sitl_despegue)

    # ---- Sensores ----
    if a.sensores_falsos:
        from sensores import FuenteFalsa
        fuente = FuenteFalsa(C)
    else:
        from sensores import FuenteReal
        fuente = FuenteReal(C, a.fuente, usar_lidar, usar_gimbal)
    hilo = HiloPercepcion(fuente, modelo, C, usar_lidar, usar_gimbal)
    hilo.start()
    t_esp = time.time()
    while hilo.ultima() is None and time.time() - t_esp < 30:
        time.sleep(0.1)
    if hilo.ultima() is None:
        fuente.detener()
        sys.exit("La percepción no produjo datos en 30 s")

    # ---- Registro ----
    if not os.path.isdir(C.LOG_DIR):
        os.makedirs(C.LOG_DIR)
    ruta_log = os.path.join(C.LOG_DIR, "vuelo_%s.csv" % time.strftime("%Y%m%d_%H%M%S"))
    f_log = open(ruta_log, "w", newline="", encoding="utf-8")
    log = csv.DictWriter(f_log, fieldnames=COLUMNAS_LOG)
    log.writeheader()
    video = None
    if a.video:
        import cv2
        video = cv2.VideoWriter(a.video, cv2.VideoWriter_fourcc(*"MJPG"), C.CONTROL_HZ,
                                (C.CAMARA_ANCHO, C.CAMARA_ALTO))

    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    arbitro = Arbitro(C)
    periodo = 1.0 / C.CONTROL_HZ
    t_sig = time.time()
    t_hb_env = 0.0
    t_imp = 0.0
    estado_prev, activo_prev = None, False
    activo = False
    print("\nListo. %s" % ("SIMULACION: no se envía nada a la Pixhawk." if a.simulacion else
                           "Despegue en STABILIZE/LOITER y cambie a GUIDED para ceder el control. "
                           "Cualquier otro modo lo recupera."))
    print("Registro: %s   (Ctrl+C para salir)\n" % ruta_log)

    try:
        while True:
            t_ciclo = time.time()
            ahora = t_ciclo
            if enlace is not None:
                enlace.actualizar()
                if ahora - t_hb_env >= 1.0:
                    enlace.enviar_heartbeat()
                    t_hb_env = ahora
            tel_ok = enlace is not None and (ahora - enlace.t_hb) < C.TIMEOUT_TELEMETRIA_S
            if a.simulacion:
                activo, alt = True, 5.0
            else:
                activo = tel_ok and enlace.armado and enlace.modo == "GUIDED"
                alt = enlace.alt_rel_m

            p = hilo.ultima()
            s = arbitro.paso(ahora, activo, alt, p)
            vx, vy, vz = saturar(s.vx, s.vy, s.vz, p is not None and p.persona, C)
            yaw = yaw_hacia_persona(s, p, ahora, C)

            enviado = False
            if s.enviar and activo and not a.simulacion:
                enlace.enviar_velocidad(vx, vy, vz, yaw)
                enviado = True
            if s.pedir_modo_falla and not a.simulacion:
                print("[SEGURIDAD] falla sostenida -> pidiendo %s" % C.MODO_FALLA)
                enlace.solicitar_modo(C.MODO_FALLA)
                enlace.texto_gcs("IA: falla sensores -> " + C.MODO_FALLA)

            # ---- Transiciones (consola + estación de tierra) ----
            if activo and not activo_prev:
                print(">>> IA CON EL CONTROL (GUIDED)")
                if enlace is not None and not a.simulacion:
                    enlace.texto_gcs("IA: control activo")
            if activo_prev and not activo:
                print("<<< PILOTO AL MANDO (modo %s)" % (enlace.modo if enlace else "?"))
                if enlace is not None and not a.simulacion:
                    enlace.texto_gcs("IA: piloto al mando")
            if s.estado != estado_prev and s.estado != INACTIVO:
                print("[%s] %s" % (s.estado, s.motivo))
                if s.estado in (EVADIENDO, FALLA) and enlace is not None and not a.simulacion:
                    enlace.texto_gcs("IA: %s %s" % (s.estado, s.motivo))
            estado_prev, activo_prev = s.estado, activo

            # ---- Registro por ciclo ----
            log.writerow({
                "t": round(ahora, 3),
                "modo": enlace.modo if enlace else "SIM",
                "armado": int(enlace.armado) if enlace else 0,
                "alt_m": None if alt is None else round(alt, 2),
                "volt": enlace.volt if enlace else None,
                "estado": s.estado, "motivo": s.motivo,
                "persona": int(p.persona) if p else "",
                "track_id": p.track_id if p else "",
                "distancia_cm": p.distancia_cm if p else "",
                "fuente_dist": p.fuente if p else "",
                "area": p.area if p else "",
                "angulo_persona_deg": p.paneo if p else "",
                "clase": "" if p is None or p.clase is None else p.clase,
                "prob": round(p.prob, 3) if p else "",
                "vx": round(vx, 2), "vy": round(vy, 2), "vz": round(vz, 2), "yaw_dps": round(yaw, 1),
                "enviado": int(enviado),
                "edad_percepcion_ms": round((ahora - p.t) * 1000, 1) if p else "",
                "lat_yolo_ms": round(p.lat_ms, 1) if p else "",
                "ciclo_ms": round((time.time() - t_ciclo) * 1000, 2),
            })
            if ahora - t_imp >= 1.0:
                f_log.flush()
                t_imp = ahora
                if p is not None:
                    print("  %-12s %-9s alt %5s  dist %6s cm [%s]  ang %6s  IA %s (%.2f)  cmd %+.1f %+.1f %+.1f  yaw %+5.1f deg/s"
                          % (s.estado, enlace.modo if enlace else "SIM",
                             "--" if alt is None else "%.1f" % alt,
                             "--" if p.distancia_cm != p.distancia_cm else "%.0f" % p.distancia_cm,
                             p.fuente, "--" if p.paneo != p.paneo else "%+.1f" % p.paneo,
                             C.CLASES.get(p.clase, "-"), p.prob, vx, vy, vz, yaw))

            # ---- Video ----
            if (a.ventana or video is not None) and p is not None and p.frame is not None:
                import cv2
                lineas = ["%s | %s" % (s.estado, s.motivo),
                          "IA: %s  p=%.2f" % (C.CLASES.get(p.clase, "-"), p.prob),
                          "cmd vx %+.1f vy %+.1f vz %+.1f yaw %+.0f  %s" % (vx, vy, vz, yaw, "ENVIADO" if enviado else "no enviado")]
                vis = dibujar_hud(p.frame.copy(), p.det, p.muestra, lineas,
                                  cartel=s.estado, color_cartel=(0, 0, 200) if s.estado in (EVADIENDO, FALLA) else (0, 130, 0))
                if video is not None:
                    video.write(cv2.resize(vis, (C.CAMARA_ANCHO, C.CAMARA_ALTO)))
                if a.ventana:
                    cv2.imshow("Vuelo IA", vis)
                    if (cv2.waitKey(1) & 0xFF) in (27, ord("q")):
                        break

            if not hilo.is_alive() and not hilo.activo and getattr(fuente, "fin", False):
                print("Fin del video de entrada.")
                break

            t_sig += periodo
            espera = t_sig - time.time()
            if espera > 0:
                time.sleep(espera)
            else:
                t_sig = time.time()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nCerrando...")
        if enlace is not None and not a.simulacion and activo:
            for _ in range(5):                             # frenar antes de soltar
                enlace.enviar_velocidad(0.0, 0.0, 0.0)
                time.sleep(0.1)
            if C.MODO_FALLA:
                enlace.solicitar_modo(C.MODO_FALLA)
                enlace.texto_gcs("IA: script detenido -> " + C.MODO_FALLA)
                print("Se pidió %s: el piloto tiene las palancas." % C.MODO_FALLA)
        hilo.activo = False
        fuente.detener()
        f_log.close()
        if video is not None:
            video.release()
        if enlace is not None:
            enlace.cerrar()
        print("Registro guardado en %s" % ruta_log)


if __name__ == "__main__":
    main()
