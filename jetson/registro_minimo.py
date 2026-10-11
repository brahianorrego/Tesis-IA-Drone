# -*- coding: utf-8 -*-
"""
Paso 1 del plan mínimo (docs/PLAN_MINIMO_FISICO.md): registro de percepción en el banco.

Por cada cuadro de la cámara guarda una fila con YOLO (la persona más grande: caja, confianza,
ID), el LiDAR TF03, el pitch del gimbal y el estado de la Pixhawk (modo, altura, velocidad,
voltaje). No manda nada a la Pixhawk: solo escucha.

Cada sensor corre en su hilo y se reconecta solo si se suelta el cable; la fila deja el campo
vacío y marca la edad del dato, así que un hueco se ve en el CSV en vez de detener el registro.

Uso (en ~/Escritorio/dron_ia):
    python3 registro_minimo.py                 # hasta Ctrl+C
    python3 registro_minimo.py --minutos 10    # prueba de aceptación del paso 1
    python3 registro_minimo.py --video         # además guarda el video (para etiquetar después)
Salida: registros/AAAAMMDD_HHMMSS/datos.csv (+ video.avi) y un resumen al final.
"""
import argparse
import csv
import os
import threading
import time

import config as C

NAN = float("nan")


def edad_ms(t):
    return round((time.time() - t) * 1000.0, 1) if t else ""


# --------------------------------------------------------------------------
# Sensores con reconexión
# --------------------------------------------------------------------------
class Reconectable(object):
    """Hilo que mantiene vivo un sensor: si su dato envejece más de 'tolerancia_s', lo reabre."""
    nombre = "sensor"
    tolerancia_s = 1.5

    def __init__(self):
        self.reconexiones = 0
        self.ultimo_error = ""
        self._activo = True
        threading.Thread(target=self._vigilar, name=self.nombre, daemon=True).start()

    def _vigilar(self):
        abierto = False
        t_abierto = 0.0
        while self._activo:
            if not abierto:
                try:
                    self.abrir()
                    abierto, t_abierto = True, time.time()
                except Exception as e:
                    self.ultimo_error = str(e)[:80]
                    time.sleep(1.0)
                    continue
            time.sleep(0.2)
            t = self.t_dato()
            arranque = self.arranque_s()
            if time.time() - (t or t_abierto) > self.tolerancia_s + (arranque if not t else 0.0):
                print("[%s] sin datos: reabriendo (%s)" % (self.nombre, self.ultimo_error or "envejeció"), flush=True)
                try:
                    self.cerrar()
                except Exception:
                    pass
                abierto = False
                self.reconexiones += 1

    def arranque_s(self):
        return 0.0

    def detener(self):
        self._activo = False
        try:
            self.cerrar()
        except Exception:
            pass


class Lidar(Reconectable):
    nombre = "LIDAR"
    tolerancia_s = 1.0

    def __init__(self):
        self._l = None
        Reconectable.__init__(self)

    def abrir(self):
        from lidar_tf import LidarTF
        self._l = LidarTF(C.PUERTO_LIDAR, C.BAUD_LIDAR, C.LIDAR_MIN_CM, C.LIDAR_MAX_CM, C.LIDAR_FUERZA_MIN).iniciar()

    def cerrar(self):
        if self._l is not None:
            self._l.detener()
            self._l = None

    def lectura(self):
        return self._l.lectura() if self._l is not None else None

    def t_dato(self):
        x = self.lectura()
        return x.t if x is not None else None


class Gimbal(Reconectable):
    nombre = "GIMBAL"
    tolerancia_s = 2.0

    def __init__(self):
        self._g = None
        Reconectable.__init__(self)

    def abrir(self):
        from gimbal_basecam import GimbalBaseCam
        self._g = GimbalBaseCam(C.PUERTO_GIMBAL, C.BAUD_GIMBAL, C.GIMBAL_PROTOCOLO, "imu",
                                C.GIMBAL_SIGNO_PANEO, C.GIMBAL_HZ_LECTURA).iniciar()

    def arranque_s(self):
        return 15.0         # la placa de 8 bits tarda ~10 s en contestar tras reiniciarse

    def cerrar(self):
        if self._g is not None:
            self._g.detener(liberar=False)       # solo lee: nunca manda CMD_CONTROL
            self._g = None

    def estado(self):
        return self._g.estado() if self._g is not None else None

    def t_dato(self):
        e = self.estado()
        return e.t if e is not None else None


class Pixhawk(Reconectable):
    """Solo escucha por TELEM2 (y pide la frecuencia de algunos mensajes)."""
    nombre = "PIXHAWK"
    tolerancia_s = C.TIMEOUT_TELEMETRIA_S + 1.0

    def __init__(self):
        self._m = None
        self._lock = threading.Lock()
        self.d = {}
        self.t_hb = None
        self.desfase_gps = None          # segundos que hay que sumarle a time.time() para tener la hora GPS
        Reconectable.__init__(self)

    def abrir(self):
        from pymavlink import mavutil
        self._mavutil = mavutil
        m = mavutil.mavlink_connection(C.PUERTO_PIXHAWK, baud=C.BAUD_PIXHAWK, source_system=C.SYSID_COMPANION,
                                       source_component=C.COMPID_COMPANION)
        if not m.wait_heartbeat(timeout=5):
            m.close()
            raise RuntimeError("sin HEARTBEAT en %s" % C.PUERTO_PIXHAWK)
        for msg_id, hz in ((mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT, 10),
                           (mavutil.mavlink.MAVLINK_MSG_ID_SYS_STATUS, 2),
                           (mavutil.mavlink.MAVLINK_MSG_ID_ATTITUDE, 10),
                           (mavutil.mavlink.MAVLINK_MSG_ID_SYSTEM_TIME, 1)):
            m.mav.command_long_send(m.target_system, m.target_component,
                                    mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0, msg_id, 1e6 / hz, 0, 0, 0, 0, 0)
        self.t_hb = time.time()
        self._m = m
        threading.Thread(target=self._leer, args=(m,), name="mavlink", daemon=True).start()

    def arranque_s(self):
        return 6.0          # wait_heartbeat puede tardar hasta 5 s al abrir

    def _leer(self, m):
        while self._m is m:
            try:
                x = m.recv_match(blocking=True, timeout=0.5)
            except Exception as e:
                self.ultimo_error = str(e)[:80]
                return
            if x is None or x.get_srcSystem() != m.target_system:
                continue
            tipo = x.get_type()
            with self._lock:
                # wait_heartbeat deja target_component en 0: se reconoce al autopiloto por el propio latido
                if tipo == "HEARTBEAT" and x.autopilot != self._mavutil.mavlink.MAV_AUTOPILOT_INVALID \
                        and x.type != self._mavutil.mavlink.MAV_TYPE_GCS:
                    self.t_hb = time.time()
                    self.d["modo"] = self._mavutil.mode_mapping_acm.get(x.custom_mode, str(x.custom_mode))
                    self.d["armado"] = int(bool(x.base_mode & 128))
                elif tipo == "GLOBAL_POSITION_INT":
                    self.d.update(alt_rel_m=x.relative_alt / 1000.0, vx=x.vx / 100.0, vy=x.vy / 100.0, vz=x.vz / 100.0)
                elif tipo == "SYS_STATUS":
                    self.d.update(volt=x.voltage_battery / 1000.0,
                                  amp=x.current_battery / 100.0 if x.current_battery >= 0 else NAN)
                elif tipo == "ATTITUDE":
                    self.d.update(cabeceo_deg=round(x.pitch * 57.2958, 2), alabeo_deg=round(x.roll * 57.2958, 2))
                elif tipo == "SYSTEM_TIME" and x.time_unix_usec > 1.6e15:
                    # hora del GPS: el reloj de la Jetson arranca en 1969 sin red (en la cancha no hay NTP)
                    self.desfase_gps = x.time_unix_usec / 1e6 - time.time()
                elif tipo == "STATUSTEXT":
                    print("[PIXHAWK] %s" % x.text, flush=True)

    def cerrar(self):
        m, self._m = self._m, None
        if m is not None:
            m.close()

    def t_dato(self):
        return self.t_hb if self._m is not None else None

    def foto(self):
        with self._lock:
            return dict(self.d), self.t_hb


# --------------------------------------------------------------------------
# Programa principal
# --------------------------------------------------------------------------
COLUMNAS = ["t", "t_gps", "n", "fps", "lat_yolo_ms", "personas", "track_id", "conf", "x1", "y1", "x2", "y2",
            "cx_norm", "cy_norm", "ancho_norm", "alto_norm", "area_norm",
            "lidar_cm", "lidar_fuerza", "lidar_valido", "edad_lidar_ms",
            "gimbal_pitch_deg", "gimbal_roll_deg", "edad_gimbal_ms",
            "modo", "armado", "alt_rel_m", "vx", "vy", "vz", "cabeceo_deg", "alabeo_deg",
            "volt", "amp", "edad_pixhawk_ms"]


def abrir_camara_con_reintentos():
    from percepcion import abrir_camara
    while True:
        try:
            cap, tipo = abrir_camara(C)
            return cap, tipo
        except Exception as e:
            print("[CAMARA] no abre (%s): reintento en 1 s" % e, flush=True)
            time.sleep(1.0)


def main():
    ap = argparse.ArgumentParser(description="Registro de percepción del paso 1 (solo lectura)")
    ap.add_argument("--minutos", type=float, default=0.0, help="0 = hasta Ctrl+C")
    ap.add_argument("--video", action="store_true", help="guardar también el video")
    ap.add_argument("--sin-gimbal", action="store_true")
    ap.add_argument("--sin-pixhawk", action="store_true")
    a = ap.parse_args()

    carpeta = os.path.join("registros", time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(carpeta)
    f = open(os.path.join(carpeta, "datos.csv"), "w", newline="", encoding="utf-8")
    log = csv.DictWriter(f, fieldnames=COLUMNAS)
    log.writeheader()

    lidar = Lidar()
    gimbal = None if a.sin_gimbal else Gimbal()
    pix = None if a.sin_pixhawk else Pixhawk()

    from ultralytics import YOLO
    modelo = YOLO(C.YOLO_MODELO, task="detect")
    cap, tipo = abrir_camara_con_reintentos()
    print("[CAMARA] %s | YOLO %s | registro en %s" % (tipo, C.YOLO_MODELO, carpeta), flush=True)
    video = None
    if a.video:
        import cv2
        video = cv2.VideoWriter(os.path.join(carpeta, "video.avi"), cv2.VideoWriter_fourcc(*"MJPG"), 30,
                                (C.CAMARA_ANCHO, C.CAMARA_ALTO))

    # calentar TensorRT antes de empezar a registrar (el primer cuadro tarda ~5 s)
    for _ in range(30):
        ok, frame = cap.read()
        if ok:
            modelo.track(frame, imgsz=C.YOLO_IMGSZ, conf=C.YOLO_CONF_MIN, classes=[0], persist=True,
                         tracker=C.YOLO_TRACKER, verbose=False)
    n = 0
    t_ini = time.time()
    t_seg, n_seg, fps = t_ini, 0, 0.0
    fallas_cam, huecos_lidar, aviso_bat = 0, 0, 0.0
    t_ultimo_cuadro = time.time()
    try:
        while a.minutos <= 0 or time.time() - t_ini < a.minutos * 60:
            ok, frame = cap.read()
            if not ok or frame is None:
                if time.time() - t_ultimo_cuadro > 1.0:
                    fallas_cam += 1
                    print("[CAMARA] sin cuadros: reabriendo", flush=True)
                    try:
                        cap.release()
                    except Exception:
                        pass
                    cap, tipo = abrir_camara_con_reintentos()
                    t_ultimo_cuadro = time.time()
                continue
            t_ultimo_cuadro = t = time.time()
            r = modelo.track(frame, imgsz=C.YOLO_IMGSZ, conf=C.YOLO_CONF_MIN, classes=[0], persist=True,
                             tracker=C.YOLO_TRACKER, verbose=False)[0]
            lat = (time.time() - t) * 1000.0
            h, w = frame.shape[:2]
            fila = dict(t=round(t, 3), n=n, fps=round(fps, 1), lat_yolo_ms=round(lat, 1), personas=len(r.boxes))
            if len(r.boxes):
                areas = (r.boxes.xywh[:, 2] * r.boxes.xywh[:, 3]).tolist()
                k = areas.index(max(areas))
                x1, y1, x2, y2 = [float(v) for v in r.boxes.xyxy[k].tolist()]
                fila.update(track_id=int(r.boxes.id[k]) if r.boxes.id is not None else -1,
                            conf=round(float(r.boxes.conf[k]), 3), x1=round(x1), y1=round(y1), x2=round(x2), y2=round(y2),
                            cx_norm=round((x1 + x2) / 2 / w, 4), cy_norm=round((y1 + y2) / 2 / h, 4),
                            ancho_norm=round((x2 - x1) / w, 4), alto_norm=round((y2 - y1) / h, 4),
                            area_norm=round((x2 - x1) * (y2 - y1) / (w * h), 5))
            lec = lidar.lectura()
            if lec is not None and t - lec.t <= C.TIMEOUT_LIDAR_S:
                fila.update(lidar_cm=lec.dist_cm, lidar_fuerza=lec.fuerza, lidar_valido=int(lec.valido))
            else:
                huecos_lidar += 1
            fila["edad_lidar_ms"] = edad_ms(lec.t) if lec is not None else ""
            if gimbal is not None:
                e = gimbal.estado()
                if e is not None:
                    fila.update(gimbal_pitch_deg=round(e.pitch_imu_deg, 2), gimbal_roll_deg=round(e.roll_imu_deg, 2),
                                edad_gimbal_ms=edad_ms(e.t))
            if pix is not None:
                d, t_hb = pix.foto()
                fila.update(d)
                fila["edad_pixhawk_ms"] = edad_ms(t_hb)
                if pix.desfase_gps is not None:
                    fila["t_gps"] = round(t + pix.desfase_gps, 3)
                v = d.get("volt")
                if v and v < 14.4 and time.time() - aviso_bat > 30:
                    aviso_bat = time.time()
                    print("[BATERIA] %.2f V %s" % (v, "DESCONECTAR YA" if v < 14.0 else "baja: ir terminando"), flush=True)
            log.writerow(fila)
            if video is not None:
                video.write(frame)
            n += 1
            n_seg += 1
            if t - t_seg >= 1.0:
                fps, n_seg, t_seg = n_seg / (t - t_seg), 0, t
                f.flush()
                if n % 150 < 31:          # una línea cada ~5 s
                    print("%5.0f s | %4.1f FPS | yolo %4.1f ms | personas %d | lidar %s | gimbal %s | pixhawk %s %s V"
                          % (t - t_ini, fps, lat, fila["personas"], fila.get("lidar_cm", "--"),
                             fila.get("gimbal_pitch_deg", "--"), fila.get("modo", "--"), fila.get("volt", "--")),
                          flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        dur = time.time() - t_ini
        f.close()
        if video is not None:
            video.release()
        cap.release()
        for s in (lidar, gimbal, pix):
            if s is not None:
                s.detener()
        resumen = ["Duración %.1f s, %d cuadros, %.1f FPS de promedio" % (dur, n, n / max(dur, 1e-3)),
                   "Cuadros sin LiDAR fresco: %d (%.2f %%)" % (huecos_lidar, 100.0 * huecos_lidar / max(n, 1)),
                   "Reaperturas: cámara %d, LiDAR %d, gimbal %s, Pixhawk %s"
                   % (fallas_cam, lidar.reconexiones, gimbal.reconexiones if gimbal else "-", pix.reconexiones if pix else "-")]
        with open(os.path.join(carpeta, "resumen.txt"), "w", encoding="utf-8") as g:
            g.write("\n".join(resumen) + "\n")
        print("\n" + "\n".join(resumen) + "\nGuardado en %s" % carpeta, flush=True)


if __name__ == "__main__":
    main()
