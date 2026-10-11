# -*- coding: utf-8 -*-
"""
Lector del LiDAR Benewake TF03 (también sirve para TF-Luna / TF-Mini) por UART.

Trama estándar de 9 bytes (formato de fábrica, 100 Hz):
    0x59 0x59 DIST_L DIST_H FUERZA_L FUERZA_H B6 B7 CHECKSUM
    CHECKSUM = (suma de los 8 primeros bytes) & 0xFF,  DIST en cm.

Uso rápido en banco:
    python3 lidar_tf.py --puerto /dev/ttyUSB0
"""
import argparse
import threading
import time
from collections import namedtuple

LecturaLidar = namedtuple("LecturaLidar", "dist_cm fuerza valido t")

CABECERA = 0x59
LARGO_TRAMA = 9


def parsear_tramas(buffer):
    """Extrae tramas válidas de un bytearray.

    Devuelve (lista_de_(dist_cm, fuerza), bytes_sobrantes). Resincroniza solo
    si hay basura o bytes perdidos. Función pura: se prueba sin hardware.
    """
    tramas = []
    i = 0
    n = len(buffer)
    while i + LARGO_TRAMA <= n:
        if buffer[i] != CABECERA or buffer[i + 1] != CABECERA:
            i += 1
            continue
        trama = buffer[i:i + LARGO_TRAMA]
        if (sum(trama[:8]) & 0xFF) != trama[8]:
            i += 1  # checksum malo: puede ser un 0x59 dentro de los datos
            continue
        dist = trama[2] | (trama[3] << 8)
        fuerza = trama[4] | (trama[5] << 8)
        tramas.append((dist, fuerza))
        i += LARGO_TRAMA
    return tramas, bytearray(buffer[i:])


class LidarTF(object):
    """Lee el LiDAR en un hilo propio y guarda siempre la última medición."""

    def __init__(self, puerto, baud=115200, min_cm=10, max_cm=18000, fuerza_min=0):
        self.puerto = puerto
        self.baud = baud
        self.min_cm = min_cm
        self.max_cm = max_cm
        self.fuerza_min = fuerza_min
        self._ser = None
        self._hilo = None
        self._activo = False
        self._lock = threading.Lock()
        self._ultima = None
        self.tramas_ok = 0

    def iniciar(self):
        import serial  # pyserial
        self._ser = serial.Serial(self.puerto, self.baud, timeout=0.05)
        self._ser.reset_input_buffer()
        self._activo = True
        self._hilo = threading.Thread(target=self._bucle, name="lidar", daemon=True)
        self._hilo.start()
        return self

    def _es_valida(self, dist, fuerza):
        if dist < self.min_cm or dist >= self.max_cm:
            return False  # 0 o 18000 = sin retorno útil
        if self.fuerza_min > 0 and (fuerza < self.fuerza_min or fuerza == 65535):
            return False
        return True

    def _bucle(self):
        buf = bytearray()
        while self._activo:
            try:
                datos = self._ser.read(64)
            except Exception as e:  # cable suelto, puerto cerrado
                print("[LIDAR] error de lectura: %s" % e)
                time.sleep(0.2)
                continue
            if not datos:
                continue
            buf.extend(datos)
            tramas, buf = parsear_tramas(buf)
            if len(buf) > 256:  # nunca debería pasar; evita crecer sin límite
                buf = buf[-LARGO_TRAMA:]
            if tramas:
                dist, fuerza = tramas[-1]
                lectura = LecturaLidar(dist, fuerza, self._es_valida(dist, fuerza), time.time())
                with self._lock:
                    self._ultima = lectura
                    self.tramas_ok += len(tramas)

    def lectura(self):
        """Última LecturaLidar o None si todavía no llega nada."""
        with self._lock:
            return self._ultima

    def detener(self):
        self._activo = False
        if self._hilo is not None:
            self._hilo.join(timeout=1.0)
        if self._ser is not None:
            self._ser.close()


def _main():
    import config as C
    ap = argparse.ArgumentParser(description="Prueba del LiDAR TF03 en banco")
    ap.add_argument("--puerto", default=C.PUERTO_LIDAR)
    ap.add_argument("--baud", type=int, default=C.BAUD_LIDAR)
    a = ap.parse_args()
    lidar = LidarTF(a.puerto, a.baud, C.LIDAR_MIN_CM, C.LIDAR_MAX_CM, C.LIDAR_FUERZA_MIN).iniciar()
    print("Leyendo %s a %d baud. Ctrl+C para salir." % (a.puerto, a.baud))
    t0, n0 = time.time(), 0
    try:
        while True:
            time.sleep(0.2)
            lec = lidar.lectura()
            hz = (lidar.tramas_ok - n0) / max(time.time() - t0, 1e-3)
            t0, n0 = time.time(), lidar.tramas_ok
            if lec is None:
                print("sin datos... (revise TX/RX cruzados, 5 V y GND común)")
            else:
                print("dist = %6d cm  fuerza = %5d  valido = %-5s  %5.0f Hz"
                      % (lec.dist_cm, lec.fuerza, lec.valido, hz))
    except KeyboardInterrupt:
        pass
    finally:
        lidar.detener()


if __name__ == "__main__":
    _main()
