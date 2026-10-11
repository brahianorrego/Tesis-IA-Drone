# -*- coding: utf-8 -*-
"""
Funciones compartidas por el grabador de dataset, el entrenamiento y el vuelo.

Regla de oro: las entradas de la IA #2 se calculan con construir_muestra()
tanto al grabar el dataset como en vuelo. Si se calcularan distinto, el modelo
vería en el aire datos diferentes a los que vio al entrenar.
"""
import json
import math
import time

import numpy as np

NAN = float("nan")

COLUMNAS_DATASET = [
    "timestamp", "toma", "etiqueta", "etiqueta_nombre",
    "persona", "track_id", "confianza", "x1", "y1", "x2", "y2",
    "cx_norm", "cy_norm", "area_bbox_norm", "alto_bbox_norm", "zona", "n_personas",
    "lidar_cm", "lidar_valido", "laser_en_persona", "dist_bbox_cm",
    "distancia_cm", "fuente_distancia",
    "angulo_persona_deg", "gimbal_fuente", "gimbal_valido", "yaw_imu_deg", "pitch_imu_deg",
    "lat_yolo_ms", "edad_lidar_ms", "edad_gimbal_ms",
]


def es_nan(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def vfov_desde_hfov(hfov_deg, ancho, alto):
    return math.degrees(2.0 * math.atan(math.tan(math.radians(hfov_deg) / 2.0) * alto / float(ancho)))


def laser_sobre_persona(det, margen=0.10):
    """True si el centro de la imagen (donde pega el láser coaxial) cae dentro
    del bbox recortado un 'margen' por cada lado."""
    if not det.persona:
        return False
    w, h = det.x2 - det.x1, det.y2 - det.y1
    cx, cy = det.ancho / 2.0, det.alto / 2.0
    return (det.x1 + margen * w <= cx <= det.x2 - margen * w and
            det.y1 + margen * h <= cy <= det.y2 - margen * h)


def distancia_por_bbox(det, hfov_deg, altura_persona_m):
    """Distancia aproximada (cm) por modelo pinhole: d = H_real * f_px / h_px.
    Error típico +/-30 %. Si la persona está tan cerca que el bbox se corta en el
    borde, la distancia real es MENOR que la estimada; el área del bbox lo delata."""
    if not det.persona or det.alto_norm <= 0.02:
        return NAN
    vfov = math.radians(vfov_desde_hfov(hfov_deg, det.ancho, det.alto))
    f_px = (det.alto / 2.0) / math.tan(vfov / 2.0)
    h_px = det.alto_norm * det.alto
    return altura_persona_m * 100.0 * f_px / h_px


def angulo_horizontal_persona(det, hfov_deg):
    """Rumbo de la persona respecto a la nariz del dron (deg, + = derecha), por modelo pinhole.

    El gimbal es de 2 ejes (pitch y roll): en yaw la cámara va fija a la nariz y es
    el dron el que gira. Por eso el rumbo sale de la posición horizontal del bbox en
    la imagen, no de un ángulo de paneo del gimbal. Sin persona devuelve 0.0.
    """
    if not det.persona:
        return 0.0
    ex = 2.0 * det.cx_norm - 1.0                    # -1 borde izquierdo ... +1 borde derecho
    return math.degrees(math.atan(ex * math.tan(math.radians(hfov_deg) / 2.0)))


def construir_muestra(det, lec_lidar, est_gimbal, cfg, t_ahora=None):
    """Une YOLO + LiDAR + gimbal en un diccionario con las columnas del dataset."""
    t = time.time() if t_ahora is None else t_ahora
    lidar_fresco = lec_lidar is not None and (t - lec_lidar.t) <= cfg.TIMEOUT_LIDAR_S
    lidar_ok = lidar_fresco and lec_lidar.valido
    gimbal_ok = est_gimbal is not None and (t - est_gimbal.t) <= cfg.TIMEOUT_GIMBAL_S
    en_persona = laser_sobre_persona(det, cfg.MARGEN_LASER)
    d_bbox = distancia_por_bbox(det, cfg.CAMARA_HFOV_DEG, cfg.ALTURA_PERSONA_M)

    # ---- Fusión de distancia ----
    if det.persona:
        if lidar_ok and en_persona:
            dist, fuente = float(lec_lidar.dist_cm), "lidar"
        elif not es_nan(d_bbox):
            dist, fuente = d_bbox, "bbox"
        else:
            dist, fuente = NAN, "ninguna"
    else:
        if lidar_ok:
            dist, fuente = float(lec_lidar.dist_cm), "lidar"
        elif lidar_fresco:                         # fresco pero sin retorno = nada al frente
            dist, fuente = float(cfg.DIST_FEATURE_MAX_CM), "sin_retorno"
        else:
            dist, fuente = NAN, "ninguna"
    if not es_nan(dist):
        dist = min(dist, float(cfg.DIST_FEATURE_MAX_CM))

    return {
        "timestamp": round(t, 3),
        "persona": int(det.persona),
        "track_id": det.track_id,
        "confianza": round(det.conf, 3),
        "x1": det.x1, "y1": det.y1, "x2": det.x2, "y2": det.y2,
        "cx_norm": round(det.cx_norm, 4), "cy_norm": round(det.cy_norm, 4),
        "area_bbox_norm": round(det.area_norm, 5), "alto_bbox_norm": round(det.alto_norm, 4),
        "zona": det.zona, "n_personas": det.n_personas,
        "lidar_cm": lec_lidar.dist_cm if lidar_fresco else NAN,
        "lidar_valido": int(lidar_ok),
        "laser_en_persona": int(en_persona),
        "dist_bbox_cm": NAN if es_nan(d_bbox) else round(d_bbox, 1),
        "distancia_cm": NAN if es_nan(dist) else round(dist, 1),
        "fuente_distancia": fuente,
        "angulo_persona_deg": round(angulo_horizontal_persona(det, cfg.CAMARA_HFOV_DEG), 2),
        "gimbal_fuente": est_gimbal.fuente if gimbal_ok else "",
        "gimbal_valido": int(gimbal_ok),
        "yaw_imu_deg": round(est_gimbal.yaw_imu_deg, 2) if gimbal_ok else NAN,
        "pitch_imu_deg": round(est_gimbal.pitch_imu_deg, 2) if gimbal_ok else NAN,
        "lat_yolo_ms": round(det.lat_ms, 1),
        "edad_lidar_ms": round((t - lec_lidar.t) * 1000.0, 1) if lec_lidar is not None else NAN,
        "edad_gimbal_ms": round((t - est_gimbal.t) * 1000.0, 1) if est_gimbal is not None else NAN,
    }


def vector_features(muestra, features):
    """Arreglo (1, n) listo para el modelo, o None si falta algún dato."""
    valores = []
    for f in features:
        v = muestra.get(f)
        if es_nan(v):
            return None
        valores.append(float(v))
    return np.array([valores], dtype=float)


# --------------------------------------------------------------------------
# Modelo de decisión (IA #2)
# --------------------------------------------------------------------------
class MLPNumpy(object):
    """Pasada hacia adelante del MLP con solo numpy, a partir de los pesos en JSON.
    Da exactamente lo mismo que scikit-learn y no depende de su versión."""

    def __init__(self, d):
        self.media = np.array(d["escalador_media"], dtype=float)
        self.escala = np.array(d["escalador_escala"], dtype=float)
        self.W = [np.array(w, dtype=float) for w in d["coefs"]]
        self.b = [np.array(b, dtype=float) for b in d["intercepts"]]
        self.activacion = d["activacion"]
        self.salida = d["salida"]
        self.classes_ = np.array(d["clases"])

    def _act(self, z):
        if self.activacion == "relu":
            return np.maximum(z, 0.0)
        if self.activacion == "tanh":
            return np.tanh(z)
        if self.activacion == "logistic":
            return 1.0 / (1.0 + np.exp(-z))
        return z

    def predict_proba(self, X):
        a = (np.asarray(X, dtype=float) - self.media) / self.escala
        for W, b in zip(self.W[:-1], self.b[:-1]):
            a = self._act(a.dot(W) + b)
        z = a.dot(self.W[-1]) + self.b[-1]
        if self.salida == "softmax":
            e = np.exp(z - z.max(axis=1, keepdims=True))
            return e / e.sum(axis=1, keepdims=True)
        p1 = 1.0 / (1.0 + np.exp(-z))
        return np.hstack([1.0 - p1, p1])


def exportar_pesos_json(pipeline, features, clases_nombres, ruta):
    esc = pipeline.named_steps["escalador"]
    mlp = pipeline.named_steps["mlp"]
    d = {
        "features": list(features),
        "clases": [int(c) for c in mlp.classes_],
        "clases_nombres": {str(k): v for k, v in clases_nombres.items()},
        "escalador_media": esc.mean_.tolist(),
        "escalador_escala": esc.scale_.tolist(),
        "coefs": [w.tolist() for w in mlp.coefs_],
        "intercepts": [b.tolist() for b in mlp.intercepts_],
        "activacion": mlp.activation,
        "salida": mlp.out_activation_,
    }
    with open(ruta, "w") as f:
        json.dump(d, f)


class ModeloDecision(object):
    """Carga decision.pkl; si falla (versiones distintas de scikit-learn/numpy entre
    PC y Jetson) usa decision_pesos.json, que da el mismo resultado."""

    def __init__(self, ruta_pkl, ruta_json, features):
        self.features = list(features)
        self.origen = None
        self._modelo = None
        error_pkl = None
        try:
            import joblib
            paquete = joblib.load(ruta_pkl)
            if isinstance(paquete, dict):
                self._revisar_features(paquete.get("features"), ruta_pkl)
                self._modelo = paquete["modelo"]
                try:
                    import sklearn
                    v = paquete.get("version_sklearn")
                    if v and v != sklearn.__version__:
                        print("[MODELO] Aviso: entrenado con scikit-learn %s, aquí hay %s"
                              % (v, sklearn.__version__))
                except ImportError:
                    pass
            else:
                self._modelo = paquete                 # pipeline suelto
            self.origen = ruta_pkl
        except Exception as e:
            error_pkl = e
        if self._modelo is None:
            try:
                with open(ruta_json) as f:
                    d = json.load(f)
                self._revisar_features(d.get("features"), ruta_json)
                self._modelo = MLPNumpy(d)
                self.origen = ruta_json
                print("[MODELO] %s no cargó (%s). Usando pesos JSON." % (ruta_pkl, error_pkl))
            except IOError:
                raise RuntimeError("No se pudo cargar %s (%s) ni %s" % (ruta_pkl, error_pkl, ruta_json))
        self.clases = [int(c) for c in self._modelo.classes_]

    def _revisar_features(self, feats, ruta):
        if feats is not None and list(feats) != self.features:
            raise RuntimeError("%s se entrenó con %s pero config.FEATURES = %s"
                               % (ruta, feats, self.features))

    def predecir(self, X):
        """Devuelve (clase, probabilidad, {clase: prob})."""
        p = self._modelo.predict_proba(X)[0]
        k = int(np.argmax(p))
        return self.clases[k], float(p[k]), dict(zip(self.clases, [float(x) for x in p]))


# --------------------------------------------------------------------------
# Pantalla
# --------------------------------------------------------------------------
def dibujar_hud(img, det, muestra, lineas, color_texto=(255, 255, 255), cartel=None, color_cartel=(0, 0, 255)):
    import cv2
    h, w = img.shape[:2]
    cv2.line(img, (w // 3, 0), (w // 3, h), (255, 255, 0), 1)
    cv2.line(img, (2 * w // 3, 0), (2 * w // 3, h), (255, 255, 0), 1)
    cv2.drawMarker(img, (w // 2, h // 2), (0, 0, 255), cv2.MARKER_CROSS, 18, 2)   # punto del láser
    if det is not None and det.persona:
        color = (0, 255, 0) if muestra.get("laser_en_persona") else (0, 165, 255)
        cv2.rectangle(img, (det.x1, det.y1), (det.x2, det.y2), color, 3)
        cv2.putText(img, "ID:%d conf:%.2f" % (det.track_id, det.conf), (det.x1, max(det.y1 - 8, 18)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    y = 22
    for txt in lineas:
        cv2.putText(img, txt, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 4)
        cv2.putText(img, txt, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_texto, 1)
        y += 22
    if cartel:
        (tw, th), _ = cv2.getTextSize(cartel, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
        cv2.rectangle(img, (w - tw - 20, h - th - 24), (w - 4, h - 4), color_cartel, -1)
        cv2.putText(img, cartel, (w - tw - 12, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    return img
