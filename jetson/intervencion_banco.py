# -*- coding: utf-8 -*-
"""
Paso 3 del plan mínimo (docs/PLAN_MINIMO_FISICO.md): intervención por MAVLink en el banco, SIN hélices.

Reglas (decisiones del arquitecto, 2026-10-11):
  · El modo experimental se ARMA solo con un flanco OFF→ON de CH7 y solo si el EKF tiene posición
    horizontal; si no, la Jetson queda en "solo registro".
  · Con el modo armado y el piloto en LOITER, si el LiDAR ve algo a menos de D_RIESGO_CM (riesgo
    simulado: la mano), la Jetson pide GUIDED y manda un objetivo de POSICIÓN: la posición horizontal
    actual y ALTURA_SEGURA_M sobre el despegue (GUIDED lo sostiene sin flujo continuo).
  · Si GUIDED se rechaza (ACK no aceptado o el modo no cambia en 300 ms): STATUSTEXT y se cuenta como
    "intervención fallida"; el piloto sigue mandando.
  · El piloto retoma moviendo CH5 (en vuelo: bajar a la posición 1 = ALT_HOLD). En cuanto el HEARTBEAT
    no dice GUIDED, la Jetson suelta y NO vuelve a pedir GUIDED hasta un nuevo flanco de CH7.
  · Nunca arma ni desarma: eso es del piloto.

Mide la latencia: lectura del LiDAR que dispara → orden enviada → ACK → HEARTBEAT en GUIDED.
Uso:  python3 intervencion_banco.py [--segundos 120]
"""
import argparse
import time

import config as C

D_RIESGO_CM = 300
ALTURA_SEGURA_M = 3.30
CH7_ON = 1700
CH7_OFF = 1300
GUIDED, LOITER = 4, 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segundos", type=float, default=120.0)
    a = ap.parse_args()

    from pymavlink import mavutil
    from lidar_tf import LidarTF
    mav = mavutil.mavlink
    m = mavutil.mavlink_connection(C.PUERTO_PIXHAWK, baud=C.BAUD_PIXHAWK, source_system=C.SYSID_COMPANION,
                                   source_component=C.COMPID_COMPANION)
    if not m.wait_heartbeat(timeout=10):
        raise SystemExit("sin HEARTBEAT de la Pixhawk")
    for msg_id, hz in ((mav.MAVLINK_MSG_ID_RC_CHANNELS, 10), (mav.MAVLINK_MSG_ID_GLOBAL_POSITION_INT, 10),
                       (mav.MAVLINK_MSG_ID_EKF_STATUS_REPORT, 2)):
        m.mav.command_long_send(1, 1, mav.MAV_CMD_SET_MESSAGE_INTERVAL, 0, msg_id, 1e6 / hz, 0, 0, 0, 0, 0)
    lidar = LidarTF(C.PUERTO_LIDAR, C.BAUD_LIDAR, C.LIDAR_MIN_CM, C.LIDAR_MAX_CM, C.LIDAR_FUERZA_MIN).iniciar()

    st = dict(modo=None, ch5=None, ch7=None, ekf_pos=False, lat=None, lon=None, alt=None)
    experimental = False
    ch7_estuvo_abajo = False        # flanco OFF -> ON aunque pase por el medio (interruptor de 3 posiciones)
    interviniendo = False
    resultados = []

    def texto(t):
        m.mav.statustext_send(mav.MAV_SEVERITY_WARNING, t[:50].encode())
        print(">>", t, flush=True)

    def procesar(x):
        tipo = x.get_type()
        if tipo == "HEARTBEAT" and x.autopilot == mav.MAV_AUTOPILOT_ARDUPILOTMEGA:
            st["modo"] = mavutil.mode_mapping_acm.get(x.custom_mode, str(x.custom_mode))
            st["armado"] = bool(x.base_mode & 128)
        elif tipo == "RC_CHANNELS":
            st["ch5"], st["ch7"] = x.chan5_raw, x.chan7_raw
        elif tipo == "EKF_STATUS_REPORT":
            st["ekf_pos"] = bool(x.flags & mav.EKF_POS_HORIZ_ABS)
        elif tipo == "GLOBAL_POSITION_INT":
            st["lat"], st["lon"], st["alt"] = x.lat, x.lon, x.relative_alt / 1000.0

    print("Listo. Mueva CH7 abajo -> arriba para armar el modo experimental (CH5 en LOITER).", flush=True)
    t_fin = time.time() + a.segundos
    t_estado = 0.0
    while time.time() < t_fin:
        if time.time() - t_estado >= 1.0:
            t_estado = time.time()
            lec0 = lidar.lectura()
            print("   estado: modo %s | CH5 %s CH7 %s | experimental %s | interviniendo %s | lidar %s cm"
                  % (st["modo"], st["ch5"], st["ch7"], experimental, interviniendo,
                     "--" if lec0 is None else "%d%s" % (lec0.dist_cm, "" if lec0.valido else " (no valido)")), flush=True)
        x = m.recv_match(blocking=True, timeout=0.01)
        while x is not None:
            procesar(x)
            x = m.recv_match(blocking=False)

        # --- modo experimental: flanco OFF -> ON de CH7 ---
        ch7 = st["ch7"]
        if ch7 is not None:
            if ch7 < CH7_OFF:
                ch7_estuvo_abajo = True
            if ch7_estuvo_abajo and ch7 > CH7_ON and not experimental:
                ch7_estuvo_abajo = False
                if st["ekf_pos"]:
                    experimental = True
                    texto("IA: modo experimental ARMADO")
                else:
                    texto("IA: sin posicion EKF, solo registro")
            if ch7 < CH7_OFF and experimental and not interviniendo:
                experimental = False
                texto("IA: modo experimental desarmado")

        # --- el piloto retoma: cualquier modo distinto de GUIDED ---
        if interviniendo and st["modo"] not in (None, "GUIDED"):
            interviniendo, experimental = False, False
            texto("IA: piloto al mando (%s); rearme con CH7" % st["modo"])
            resultados[-1]["retoma"] = st["modo"]

        # --- riesgo simulado por LiDAR ---
        lec = lidar.lectura()
        if (experimental and not interviniendo and st["modo"] == "LOITER" and lec is not None and lec.valido
                and lec.dist_cm < D_RIESGO_CM and time.time() - lec.t < 0.1):
            t_lidar = lec.t
            t_cmd = time.time()
            m.mav.command_long_send(1, 1, mav.MAV_CMD_DO_SET_MODE, 0, mav.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                                    GUIDED, 0, 0, 0, 0, 0)
            ack, t_ack, t_guided = None, None, None
            while time.time() - t_cmd < 0.3 and t_guided is None:
                x = m.recv_match(blocking=True, timeout=0.01)
                if x is None:
                    continue
                procesar(x)
                if x.get_type() == "COMMAND_ACK" and x.command == mav.MAV_CMD_DO_SET_MODE:
                    ack, t_ack = x.result, time.time()
                if st["modo"] == "GUIDED":
                    t_guided = time.time()
            r = dict(dist_cm=lec.dist_cm, lidar_a_orden_ms=(t_cmd - t_lidar) * 1000,
                     ack=ack, orden_a_ack_ms=(t_ack - t_cmd) * 1000 if t_ack else None,
                     orden_a_guided_ms=(t_guided - t_cmd) * 1000 if t_guided else None)
            if t_guided is None or ack not in (None, mav.MAV_RESULT_ACCEPTED):
                r["resultado"] = "INTERVENCION FALLIDA"
                texto("IA: GUIDED rechazado, piloto al mando")
                experimental = False
            else:
                # objetivo de POSICIÓN: aquí mismo y ALTURA_SEGURA_M sobre el despegue
                m.mav.set_position_target_global_int_send(
                    0, 1, 1, mav.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, 0b0000110111111000,
                    st["lat"], st["lon"], ALTURA_SEGURA_M, 0, 0, 0, 0, 0, 0, 0, 0)
                r["resultado"] = "INTERVENCION: freno + subida a %.2f m" % ALTURA_SEGURA_M
                r["lidar_a_objetivo_ms"] = (time.time() - t_lidar) * 1000
                interviniendo = True
                texto("IA: RIESGO %d cm -> GUIDED, subir a %.1f m" % (lec.dist_cm, ALTURA_SEGURA_M))
            resultados.append(r)
            print("   ", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)

    lidar.detener()
    print("\nResumen: %d intervenciones" % len(resultados))
    for r in resultados:
        print("  ", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()})


if __name__ == "__main__":
    main()
