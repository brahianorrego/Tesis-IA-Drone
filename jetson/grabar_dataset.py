# -*- coding: utf-8 -*-
"""
Grabador del dataset para la IA #2 (aprendizaje supervisado por demostración).

Procedimiento (dron en estático, SIN HÉLICES):
  1. python3 grabar_dataset.py
  2. Una persona se acerca al dron desde distintos ángulos y distancias.
  3. El operario deja seleccionada la etiqueta de la maniobra correcta:
        0 MANTENER   1 EVADIR_IZQ   2 EVADIR_DER   3 DETENER_ASCENDER
     La etiqueta queda fija hasta que se pulse otra (no hay que mantener la tecla).
  4. R o ESPACIO inicia / pausa la grabación. Cada inicio cuenta como una "toma"
     nueva; el entrenamiento separa prueba y entrenamiento por tomas.

Teclas: 0-3 etiqueta | R/ESPACIO grabar | C cero del gimbal | T seguimiento on/off | Q/ESC salir

Opciones útiles:
  --sin-lidar / --sin-gimbal   probar por partes
  --fuente video.mp4           reproducir un video en lugar de la cámara
  --guardar-imagenes 10        guarda 1 de cada 10 frames grabados (evidencia para el documento)
"""
import argparse
import csv
import os
import time
from collections import Counter

import cv2

import config as C
from comun import COLUMNAS_DATASET, construir_muestra, dibujar_hud, es_nan
from sensores import FuenteReal

VENTANA = "Dataset IA #2 - Jetson"
COLORES = {0: (0, 150, 0), 1: (200, 90, 0), 2: (160, 0, 160), 3: (0, 0, 200)}


def _fmt(v, patron):
    return "---" if es_nan(v) else patron % v


def main():
    ap = argparse.ArgumentParser(description="Grabación de dataset YOLO + LiDAR + gimbal con etiquetas")
    ap.add_argument("--salida", help="ruta del CSV (por defecto datos/dataset_FECHA.csv)")
    ap.add_argument("--fuente", help="índice de cámara o archivo de video")
    ap.add_argument("--hz", type=float, default=C.DATASET_HZ)
    ap.add_argument("--sin-lidar", action="store_true")
    ap.add_argument("--sin-gimbal", action="store_true")
    ap.add_argument("--sin-seguimiento", action="store_true", help="leer el gimbal pero no moverlo")
    ap.add_argument("--guardar-imagenes", type=int, default=0, metavar="N")
    a = ap.parse_args()

    if not os.path.isdir(C.DATASET_DIR):
        os.makedirs(C.DATASET_DIR)
    ruta = a.salida or os.path.join(C.DATASET_DIR, "dataset_%s.csv" % time.strftime("%Y%m%d_%H%M%S"))
    dir_img = os.path.splitext(ruta)[0] + "_img"
    if a.guardar_imagenes and not os.path.isdir(dir_img):
        os.makedirs(dir_img)

    fuente = FuenteReal(C, a.fuente, not a.sin_lidar, not a.sin_gimbal, not a.sin_seguimiento)
    archivo = open(ruta, "w", newline="", encoding="utf-8")
    escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_DATASET, extrasaction="ignore")
    escritor.writeheader()
    print("Grabando en %s" % ruta)

    etiqueta, grabando, toma, filas = 0, False, 0, 0
    conteo = Counter()
    t_ult_fila = 0.0
    periodo = 1.0 / a.hz
    t_fps, n_fps, fps = time.time(), 0, 0.0
    cv2.namedWindow(VENTANA)

    try:
        while True:
            r = fuente.obtener(timeout=1.0)
            if r is None:
                if fuente.fin:
                    break
                print("[CAMARA] sin frames nuevos...")
                continue
            frame, det, lec, est = r
            m = construir_muestra(det, lec, est, C)

            # ---- Escritura (a tasa fija para no llenar el CSV de frames casi iguales) ----
            if grabando and m["timestamp"] - t_ult_fila >= periodo:
                m.update(toma=toma, etiqueta=etiqueta, etiqueta_nombre=C.CLASES[etiqueta])
                escritor.writerow(m)
                filas += 1
                conteo[etiqueta] += 1
                t_ult_fila = m["timestamp"]
                if filas % 20 == 0:
                    archivo.flush()
                if a.guardar_imagenes and filas % a.guardar_imagenes == 0:
                    cv2.imwrite(os.path.join(dir_img, "f%05d_e%d.jpg" % (filas, etiqueta)), frame)

            # ---- Pantalla ----
            n_fps += 1
            if time.time() - t_fps >= 1.0:
                fps = n_fps / (time.time() - t_fps)
                t_fps, n_fps = time.time(), 0
            faltan = [f for f in C.FEATURES if es_nan(m.get(f))]
            seg = fuente.seguidor is not None and fuente.seguidor.activo
            lineas = [
                "%s   toma %d   filas %d / %d" % ("REC" if grabando else "PAUSA", toma, filas,
                                                  C.DATASET_OBJETIVO_FILAS),
                "dist %s cm [%s]  lidar %s  laser_en_persona=%d" % (
                    _fmt(m["distancia_cm"], "%.0f"), m["fuente_distancia"],
                    _fmt(m["lidar_cm"], "%.0f"), m["laser_en_persona"]),
                "area %.3f   angulo persona %s deg   zona %s   ID %d" % (
                    m["area_bbox_norm"], _fmt(m["angulo_persona_deg"], "%+.1f"), m["zona"], m["track_id"]),
                "por clase  0:%d  1:%d  2:%d  3:%d" % (conteo[0], conteo[1], conteo[2], conteo[3]),
                "gimbal seguimiento %s   %.1f fps   yolo %.0f ms" % ("ON" if seg else "OFF", fps, m["lat_yolo_ms"]),
            ]
            if faltan and det.persona:
                lineas.append("FALTAN: " + ", ".join(faltan) + "  (fila no servira)")
            vis = dibujar_hud(frame.copy(), det, m, lineas,
                              cartel="%d %s" % (etiqueta, C.CLASES[etiqueta]),
                              color_cartel=COLORES[etiqueta])
            if grabando:
                cv2.circle(vis, (vis.shape[1] - 20, 20), 9, (0, 0, 255), -1)
            cv2.imshow(VENTANA, vis)

            # ---- Teclado ----
            k = cv2.waitKey(1) & 0xFF
            if k in (27, ord("q")):
                break
            if ord("0") <= k <= ord("3"):
                etiqueta = k - ord("0")
            elif k in (ord("r"), 32):
                grabando = not grabando
                if grabando:
                    toma += 1
                print("%s (toma %d)" % ("GRABANDO" if grabando else "PAUSA", toma))
            elif k == ord("c") and fuente.gimbal is not None:
                print("Cero del gimbal fijado" if fuente.gimbal.fijar_cero() else "Gimbal sin datos")
            elif k == ord("t") and fuente.seguidor is not None:
                fuente.seguidor.activo = not fuente.seguidor.activo
    except KeyboardInterrupt:
        pass
    finally:
        archivo.close()
        fuente.detener()
        cv2.destroyAllWindows()
        print("\n%d filas guardadas en %s" % (filas, ruta))
        for c in sorted(C.CLASES):
            print("  %d %-17s %d" % (c, C.CLASES[c], conteo[c]))


if __name__ == "__main__":
    main()
