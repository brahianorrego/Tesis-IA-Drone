# -*- coding: utf-8 -*-
"""
Interfaz con el gimbal BaseCam (controlador SimpleBGC 32) por la
"SimpleBGC Serial API". Hace dos cosas:

1. LECTURA: consulta el ángulo del pod en tiempo real y entrega el
   ángulo de paneo (yaw del pod respecto a la nariz del dron).
2. SEGUIMIENTO: ordena al gimbal girar para mantener a la persona en el
   centro de la imagen, así el LiDAR coaxial siempre apunta a la persona.

Formato de trama
----------------
  Versión 1:  '>' CMD LARGO (CMD+LARGO)&0xFF  PAYLOAD  (suma PAYLOAD)&0xFF
  Versión 2:  '$' CMD LARGO (CMD+LARGO)&0xFF  PAYLOAD  CRC16 (LSB primero)
  Enteros little-endian. La placa responde en la misma versión en que se le pregunta.

Comandos usados
---------------
  CMD_BOARD_INFO     (86)  versión de firmware (diagnóstico)
  CMD_GET_ANGLES_EXT (61)  por eje: IMU_ANGLE int16, TARGET int16, FRAME_CAM_ANGLE int32, 10 reservados
  CMD_GET_ANGLES     (73)  por eje: IMU_ANGLE int16, TARGET int16, TARGET_SPEED int16
  CMD_REALTIME_DATA  (68)  único que responde la placa de 8 bits con firmware 2.2x
                           (ver parsear_realtime_data)
  CMD_CONTROL        (67)  MODE_ANGLE: el pod va a un ángulo y lo sostiene
  Unidades: ángulo 0.02197265625 deg/unidad; velocidad 0.1220740379 deg/s por unidad.

Placa de 8 bits (firmware 2.2x)
-------------------------------
  Al abrir el puerto la placa se reinicia (DTR) y tarda ~10 s en responder
  mientras calibra el giroscopio: NO mueva el gimbal en ese tiempo. Para que
  las siguientes aperturas no la reinicien se aplica `stty -hupcl` al puerto.
  La lectura cae sola a REALTIME_DATA si GET_ANGLES_EXT y GET_ANGLES no responden.

Pruebas en banco (HÉLICES RETIRADAS):
    python3 gimbal_basecam.py                   # imprime el paneo en vivo
    python3 gimbal_basecam.py --prueba-signos   # calibra los signos de config.py
"""
import argparse
import math
import struct
import threading
import time
from collections import namedtuple

UNIDAD_ANGULO = 0.02197265625       # grados por unidad (360 / 16384)
UNIDAD_VELOCIDAD = 0.1220740379     # (grados/s) por unidad
# Ángulos de REALTIME_DATA en firmware 2.2x: 360/4096 deg por unidad. Medido en banco
# el 2026-10-06 contra el acelerómetro de la placa (~0.088 deg/unidad en pitch y roll).
UNIDAD_ANGULO_RT = 0.1                 # 2026-10-11: con pulsos de AUX1 conocidos (−5° y −10°) la unidad es 0.1°, no 360/4096

CMD_GET_ANGLES_EXT = 61
CMD_CONTROL = 67                    # el mismo ID llega como CMD_CONFIRM
CMD_REALTIME_DATA = 68
CMD_GET_ANGLES = 73
CMD_BOARD_INFO = 86
CMD_ERROR = 255

MODE_NO_CONTROL = 0
MODE_ANGLE = 2

ROLL, PITCH, YAW = 0, 1, 2

EstadoGimbal = namedtuple(
    "EstadoGimbal",
    "paneo_deg yaw_imu_deg pitch_imu_deg roll_imu_deg yaw_marco_deg fuente valido t")


def envolver180(grados):
    """Lleva un ángulo a [-180, 180)."""
    return (grados + 180.0) % 360.0 - 180.0


def _limitar(x, a, b):
    return max(a, min(b, x))


# --------------------------------------------------------------------------
# Protocolo
# --------------------------------------------------------------------------
def crc16_sbgc(datos):
    """CRC16 de la API SimpleBGC v2 (polinomio 0x8005, inicial 0, bits LSB primero)."""
    crc = 0
    for byte in bytearray(datos):
        for bit in range(8):
            bit_dato = (byte >> bit) & 1
            bit_crc = (crc >> 15) & 1
            crc = (crc << 1) & 0xFFFF
            if bit_dato != bit_crc:
                crc ^= 0x8005
    return crc


def construir_trama(cmd, payload=b"", version=1):
    payload = bytes(payload)
    n = len(payload)
    cab = bytes(bytearray([cmd & 0xFF, n & 0xFF, (cmd + n) & 0xFF]))
    if version == 1:
        return b">" + cab + payload + bytes(bytearray([sum(bytearray(payload)) & 0xFF]))
    return b"$" + cab + payload + struct.pack("<H", crc16_sbgc(cab + payload))


class ParserSBGC(object):
    """Máquina de estados que separa mensajes de un flujo de bytes (v1 y v2)."""

    def __init__(self):
        self.buf = bytearray()
        self.errores = 0

    def alimentar(self, datos):
        self.buf.extend(datos)
        mensajes = []
        while True:
            inicios = [i for i in (self.buf.find(b">"), self.buf.find(b"$")) if i >= 0]
            if not inicios:
                del self.buf[:]
                break
            i = min(inicios)
            if i:
                del self.buf[:i]
            if len(self.buf) < 4:
                break
            inicio, cmd, n, ck = self.buf[0], self.buf[1], self.buf[2], self.buf[3]
            if (cmd + n) & 0xFF != ck:
                self.errores += 1
                del self.buf[0]
                continue
            v1 = inicio == 0x3E
            total = 4 + n + (1 if v1 else 2)
            if len(self.buf) < total:
                break
            payload = bytes(self.buf[4:4 + n])
            if v1:
                ok = (sum(bytearray(payload)) & 0xFF) == self.buf[4 + n]
            else:
                crc = self.buf[4 + n] | (self.buf[5 + n] << 8)
                ok = crc16_sbgc(bytes(self.buf[1:4]) + payload) == crc
            if ok:
                mensajes.append((cmd, payload))
                del self.buf[:total]
            else:
                self.errores += 1
                del self.buf[0]
        return mensajes


def parsear_get_angles(p):
    if len(p) < 18:
        return None
    v = struct.unpack_from("<9h", p)
    return {"imu": [v[0] * UNIDAD_ANGULO, v[3] * UNIDAD_ANGULO, v[6] * UNIDAD_ANGULO],
            "objetivo": [v[1] * UNIDAD_ANGULO, v[4] * UNIDAD_ANGULO, v[7] * UNIDAD_ANGULO],
            "marco": None}


def parsear_get_angles_ext(p):
    if len(p) < 54:
        return None
    imu, obj, marco = [], [], []
    for eje in range(3):
        a_imu, a_obj, a_marco = struct.unpack_from("<hhi", p, eje * 18)
        imu.append(a_imu * UNIDAD_ANGULO)
        obj.append(a_obj * UNIDAD_ANGULO)
        marco.append(a_marco * UNIDAD_ANGULO)
    return {"imu": imu, "objetivo": obj, "marco": marco}


def parsear_realtime_data(p):
    """REALTIME_DATA del firmware 2.2x (49 bytes = 24 int16 + 1 byte).

    Mapa medido en banco: v[19] = roll, v[20] = pitch, v[21] = yaw IMU.
    v[0..7] incluyen acelerómetro/giro (v[6] ~ 512 = 1 g). Mientras la placa
    arranca y calibra todo llega en cero: eso se descarta (devuelve None).
    """
    if len(p) < 44:
        return None
    v = struct.unpack_from("<22h", p)
    if not any(v[:8]):
        return None
    imu = [v[19] * UNIDAD_ANGULO_RT, v[20] * UNIDAD_ANGULO_RT, v[21] * UNIDAD_ANGULO_RT]
    return {"imu": imu, "objetivo": None, "marco": None}


def payload_control(modo, roll_deg=0.0, pitch_deg=0.0, yaw_deg=0.0, vel_dps=0.0):
    """CMD_CONTROL formato clásico de 13 bytes (compatible con todo firmware)."""
    v = int(round(_limitar(vel_dps / UNIDAD_VELOCIDAD, -32768, 32767)))

    def a(grados):
        return int(round(_limitar(grados, -719.0, 719.0) / UNIDAD_ANGULO))
    return struct.pack("<Bhhhhhh", modo, v, a(roll_deg), v, a(pitch_deg), v, a(yaw_deg))


# --------------------------------------------------------------------------
# Lectura en tiempo real
# --------------------------------------------------------------------------
class GimbalBaseCam(object):

    def __init__(self, puerto, baud=115200, version=1, fuente="marco", signo_paneo=1, hz=25):
        self.puerto = puerto
        self.baud = baud
        self.version = version
        self.fuente = fuente
        self.signo = 1 if signo_paneo >= 0 else -1
        self.hz = hz
        # Comando de lectura actual: "ext" -> "angles" -> "rt" (se degrada solo)
        self.lectura = "ext" if fuente == "marco" else "angles"
        self._t_viva = None                 # cuándo respondió la placa por primera vez
        self._t_modo = None                 # cuándo empezó el comando de lectura actual
        self._ser = None
        self._hilo = None
        self._activo = False
        self._lock = threading.Lock()
        self._lock_tx = threading.Lock()
        self._estado = None
        self._raw_paneo = None
        self._cero = 0.0
        self._cero_auto = fuente == "imu"
        self.firmware = None
        self.respuestas = 0
        self.parser = ParserSBGC()

    # --- conexión ---
    def iniciar(self):
        import serial
        import subprocess
        # Sin -hupcl, cerrar el puerto baja DTR y la próxima apertura reinicia la placa de 8 bits
        subprocess.call(["stty", "-F", self.puerto, "-hupcl"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._ser = serial.Serial(self.puerto, self.baud, timeout=0.02)
        self._ser.reset_input_buffer()
        self._activo = True
        self._hilo = threading.Thread(target=self._bucle, name="gimbal", daemon=True)
        self._hilo.start()
        return self

    def detener(self, liberar=True):
        if liberar and self._ser is not None:
            try:
                self.liberar()
                time.sleep(0.05)
            except Exception:
                pass
        self._activo = False
        if self._hilo is not None:
            self._hilo.join(timeout=1.0)
        if self._ser is not None:
            self._ser.close()

    def _enviar(self, cmd, payload=b""):
        with self._lock_tx:
            self._ser.write(construir_trama(cmd, payload, self.version))

    # --- hilo ---
    def _bucle(self):
        periodo = 1.0 / self.hz
        t_sig = 0.0
        t_info = 0.0
        comandos = {"ext": CMD_GET_ANGLES_EXT, "angles": CMD_GET_ANGLES, "rt": CMD_REALTIME_DATA}
        while self._activo:
            ahora = time.time()
            if self._t_viva is None:
                # La placa puede estar arrancando (~10 s en la de 8 bits): insistir con BOARD_INFO
                if ahora >= t_info:
                    t_info = ahora + 1.0
                    try:
                        self._enviar(CMD_BOARD_INFO, b"\x00\x00")
                    except Exception as e:
                        print("[GIMBAL] no se pudo escribir: %s" % e)
            elif ahora >= t_sig:
                t_sig = ahora + periodo
                if self._t_modo is None:
                    self._t_modo = ahora
                if self._estado is None and self.lectura != "rt" and ahora - self._t_modo > 1.5:
                    sig = "angles" if self.lectura == "ext" else "rt"
                    print("[GIMBAL] sin respuesta a %s; se usa %s "
                          "(paneo desde la IMU de la cámara, relativo al arranque)"
                          % (self.lectura, sig))
                    self.lectura = sig
                    self._t_modo = ahora
                    self._cero_auto = True
                try:
                    self._enviar(comandos[self.lectura])
                except Exception as e:
                    print("[GIMBAL] error de escritura: %s" % e)
                    time.sleep(0.2)
                    continue
            try:
                datos = self._ser.read(self._ser.in_waiting or 1)
            except Exception as e:
                print("[GIMBAL] error de lectura: %s" % e)
                time.sleep(0.2)
                continue
            if datos:
                for cmd, p in self.parser.alimentar(datos):
                    self._procesar(cmd, p)

    def _procesar(self, cmd, p):
        if self._t_viva is None:
            self._t_viva = time.time()
        if cmd == CMD_GET_ANGLES_EXT:
            d = parsear_get_angles_ext(p)
        elif cmd == CMD_GET_ANGLES:
            d = parsear_get_angles(p)
        elif cmd == CMD_REALTIME_DATA:
            d = parsear_realtime_data(p)
        elif cmd == CMD_BOARD_INFO and len(p) >= 3:
            fw = struct.unpack_from("<H", p, 1)[0]
            self.firmware = "%d.%d b%d" % (fw // 1000, (fw % 1000) // 10, fw % 10)
            print("[GIMBAL] placa v%d, firmware %s (crudo %d)" % (p[0], self.firmware, fw))
            return
        elif cmd == CMD_ERROR:
            print("[GIMBAL] la placa reportó CMD_ERROR: %s" % p.hex())
            return
        else:
            return
        if d is None:
            return
        if d["marco"] is not None and self.fuente == "marco":
            raw, fuente = d["marco"][YAW], "marco"
        else:
            raw, fuente = d["imu"][YAW], "imu"
        with self._lock:
            if self._cero_auto:
                self._cero = raw
                self._cero_auto = False
            self._raw_paneo = raw
            paneo = envolver180(self.signo * (raw - self._cero))
            self._estado = EstadoGimbal(
                paneo_deg=paneo,
                yaw_imu_deg=d["imu"][YAW], pitch_imu_deg=d["imu"][PITCH], roll_imu_deg=d["imu"][ROLL],
                yaw_marco_deg=d["marco"][YAW] if d["marco"] is not None else float("nan"),
                fuente=fuente, valido=True, t=time.time())
            self.respuestas += 1

    # --- API pública ---
    def estado(self):
        """Último EstadoGimbal o None. Revise estado.t para saber su edad."""
        with self._lock:
            return self._estado

    def fijar_cero(self):
        """Toma la posición actual del pod como 'mirando a la nariz' (paneo = 0)."""
        with self._lock:
            if self._raw_paneo is not None:
                self._cero = self._raw_paneo
                return True
        return False

    def comandar_angulos(self, pitch_deg, yaw_deg, vel_dps=60.0, roll_deg=0.0):
        """MODE_ANGLE: el pod gira hasta esos ángulos (marco de la IMU) y los sostiene.
        Es un comando de posición: si el programa se cae, el pod se queda quieto."""
        self._enviar(CMD_CONTROL, payload_control(MODE_ANGLE, roll_deg, pitch_deg, yaw_deg, vel_dps))

    def liberar(self):
        """Devuelve el control al modo normal del gimbal (RC / follow)."""
        self._enviar(CMD_CONTROL, payload_control(MODE_NO_CONTROL))


# --------------------------------------------------------------------------
# Seguimiento visual: centrar a la persona
# --------------------------------------------------------------------------
class SeguidorGimbal(object):
    """Control proporcional: convierte el error del bbox en píxeles a grados
    y pide al gimbal corregirlo. Convención interna: 'derecha' y 'arriba' positivos;
    los signos GIMBAL_SIGNO_*_CMD traducen eso a los ejes de la placa."""

    def __init__(self, gimbal, cfg, ancho, alto):
        self.g = gimbal
        self.c = cfg
        hfov = math.radians(cfg.CAMARA_HFOV_DEG)
        self.tan_h = math.tan(hfov / 2.0)
        self.tan_v = self.tan_h * float(alto) / float(ancho)
        self.activo = bool(cfg.GIMBAL_SEGUIMIENTO) and gimbal is not None
        self._t_cmd = 0.0
        self._t_visto = time.time()
        self.ultimo_cmd = None

    def _corregir(self, error_deg):
        if abs(error_deg) < self.c.GIMBAL_ZONA_MUERTA_DEG:
            return 0.0
        paso = self.c.GIMBAL_PASO_MAX_DEG
        return _limitar(self.c.GIMBAL_KP * error_deg, -paso, paso)

    def actualizar(self, det, t=None):
        if not self.activo:
            return
        t = time.time() if t is None else t
        if t - self._t_cmd < 1.0 / self.c.GIMBAL_HZ_COMANDO:
            return
        est = self.g.estado()
        if est is None or t - est.t > self.c.TIMEOUT_GIMBAL_S:
            return
        pitch_arriba = self.c.GIMBAL_SIGNO_PITCH_CMD * est.pitch_imu_deg
        if det is not None and det.persona:
            self._t_visto = t
            self.tan_v = self.tan_h * float(det.alto) / float(det.ancho)
            ex = 2.0 * det.cx_norm - 1.0                       # -1 izquierda ... +1 derecha
            ey = 2.0 * det.cy_norm - 1.0                       # -1 arriba ... +1 abajo
            d_der = self._corregir(math.degrees(math.atan(ex * self.tan_h)))
            d_arr = self._corregir(-math.degrees(math.atan(ey * self.tan_v)))
        elif t - self._t_visto > self.c.GIMBAL_T_REGRESO_S:
            d_der = self._corregir(-est.paneo_deg)             # volver a la nariz
            d_arr = self._corregir(self.c.GIMBAL_PITCH_REPOSO_DEG - pitch_arriba)
        else:
            return                                             # perdida reciente: sostener
        if not getattr(self.c, "GIMBAL_TIENE_YAW", True):
            d_der = 0.0                                        # gimbal de 2 ejes: el yaw lo hace el dron
        # Nunca pasar del límite de paneo respecto a la nariz
        lim = self.c.GIMBAL_PANEO_LIMITE_DEG
        d_der = _limitar(est.paneo_deg + d_der, -lim, lim) - est.paneo_deg
        if not self.c.GIMBAL_SEGUIR_PITCH:
            d_arr = self._corregir(self.c.GIMBAL_PITCH_REPOSO_DEG - pitch_arriba)
        if d_der == 0.0 and d_arr == 0.0:
            return
        yaw_obj = est.yaw_imu_deg + self.c.GIMBAL_SIGNO_YAW_CMD * d_der
        pitch_obj_arriba = _limitar(pitch_arriba + d_arr,
                                    self.c.GIMBAL_PITCH_MIN_DEG, self.c.GIMBAL_PITCH_MAX_DEG)
        pitch_obj = self.c.GIMBAL_SIGNO_PITCH_CMD * pitch_obj_arriba
        try:
            self.g.comandar_angulos(pitch_obj, yaw_obj, self.c.GIMBAL_VEL_DPS)
            self.ultimo_cmd = (t, d_der, d_arr)
        except Exception as e:
            print("[GIMBAL] no se pudo enviar CMD_CONTROL: %s" % e)
        self._t_cmd = t


# --------------------------------------------------------------------------
# Herramientas de banco
# --------------------------------------------------------------------------
def _esperar_estado(g, timeout=15.0):   # la placa de 8 bits tarda ~10 s en arrancar
    t0 = time.time()
    while time.time() - t0 < timeout:
        e = g.estado()
        if e is not None:
            return e
        time.sleep(0.05)
    return None


def _prueba_signos(g, C):
    print("\n=== PRUEBA DE SIGNOS (hélices retiradas, pod libre de obstáculos) ===")
    e0 = _esperar_estado(g)
    if e0 is None:
        print("No hay respuesta del gimbal.")
        return
    print("Inicio: paneo %+.1f  yaw IMU %+.1f  pitch IMU %+.1f" % (e0.paneo_deg, e0.yaw_imu_deg, e0.pitch_imu_deg))
    input("ENTER para girar el yaw +15 deg (en unidades de la placa)...")
    g.comandar_angulos(e0.pitch_imu_deg, e0.yaw_imu_deg + 15.0, 30.0)
    time.sleep(2.0)
    e1 = g.estado()
    der = input("¿El pod giró hacia la DERECHA del dron? [s/n]: ").strip().lower().startswith("s")
    d_paneo = e1.paneo_deg - e0.paneo_deg
    signo_yaw = 1 if der else -1
    paneo_ok = (d_paneo > 0) == der
    signo_paneo = C.GIMBAL_SIGNO_PANEO if paneo_ok else -C.GIMBAL_SIGNO_PANEO
    print("  paneo cambió %+.1f deg" % d_paneo)

    input("ENTER para subir el pitch +10 deg (en unidades de la placa)...")
    g.comandar_angulos(e1.pitch_imu_deg + 10.0, e1.yaw_imu_deg, 30.0)
    time.sleep(2.0)
    sube = input("¿La cámara apuntó más ARRIBA? [s/n]: ").strip().lower().startswith("s")
    signo_pitch = 1 if sube else -1

    g.comandar_angulos(e0.pitch_imu_deg, e0.yaw_imu_deg, 30.0)
    time.sleep(2.0)
    print("\nCopie en config.py:")
    print("  GIMBAL_SIGNO_PANEO = %d" % signo_paneo)
    print("  GIMBAL_SIGNO_YAW_CMD = %d" % signo_yaw)
    print("  GIMBAL_SIGNO_PITCH_CMD = %d" % signo_pitch)
    if e1.fuente == "imu":
        print("Nota: el paneo viene de la IMU (su firmware no respondió a GET_ANGLES_EXT).")


def _main():
    import config as C
    ap = argparse.ArgumentParser(description="Lectura del ángulo de paneo de la BaseCam")
    ap.add_argument("--puerto", default=C.PUERTO_GIMBAL)
    ap.add_argument("--baud", type=int, default=C.BAUD_GIMBAL)
    ap.add_argument("--protocolo", type=int, choices=[1, 2], default=C.GIMBAL_PROTOCOLO)
    ap.add_argument("--fuente", choices=["marco", "imu"], default=C.GIMBAL_FUENTE_PANEO)
    ap.add_argument("--prueba-signos", action="store_true")
    a = ap.parse_args()

    g = GimbalBaseCam(a.puerto, a.baud, a.protocolo, a.fuente, C.GIMBAL_SIGNO_PANEO,
                      C.GIMBAL_HZ_LECTURA).iniciar()
    try:
        if a.prueba_signos:
            _prueba_signos(g, C)
            return
        print("Leyendo %s. Gire el pod a mano o con el RC. Ctrl+C para salir." % a.puerto)
        n0, t0 = 0, time.time()
        while True:
            time.sleep(0.2)
            e = g.estado()
            hz = (g.respuestas - n0) / max(time.time() - t0, 1e-3)
            n0, t0 = g.respuestas, time.time()
            if e is None:
                print("sin respuesta... (placa arrancando ~10 s, o TX/RX cruzados, baud, GND común; "
                      "lectura=%s, errores de trama: %d)" % (g.lectura, g.parser.errores))
            else:
                print("PANEO %+7.2f deg | yaw IMU %+8.2f  pitch %+7.2f  roll %+7.2f | fuente=%s  %4.1f Hz"
                      % (e.paneo_deg, e.yaw_imu_deg, e.pitch_imu_deg, e.roll_imu_deg, e.fuente, hz))
    except KeyboardInterrupt:
        pass
    finally:
        g.detener(liberar=True)


if __name__ == "__main__":
    _main()
