# -*- coding: utf-8 -*-
"""
Versión Master del entrenamiento: Stable-Baselines3 (PPO) con transferencia de aprendizaje y currículo continuo.

V16 (docs/PLAN_V16_REALISMO.md, avance y comando en docs/PROGRESO_V16.md): UN SOLO CASO, la misión completa con 2 paneles
(NIVEL_V16), sin currículo. Física humana (posturas, salto con el brazo), civiles realistas, sensores nuevos (cámara al
piso, TF03 al chasis, TF-Luna, desenfoque, gimbal BaseCam o servo, GPS y barómetro con error) y recompensa con la
custodia como número principal. La red tiene 3 entradas más (195): al arrancar desde la V15 sus pesos nuevos van en cero
(la red empieza haciendo exactamente lo mismo que la V15) y aprenden; las conexiones de las 192 entradas viejas de la
primera capa quedan congeladas (--congelar viejas, por defecto). Orden de arranque:
  1. modelos_v16/ultimo.zip si existe (continúa);
  2. si no, --desde ZIP o el checkpoint más nuevo de modelos_v15/ (modelo SB3 completo de la V15: actor y crítico);
  3. si no hay ninguno, la política para la Jetson modelos/dron_politica.json (solo el actor; el crítico arranca de cero).
El ladrón de la V16 es siempre el táctico: si no está ladron_congelado.pt, se usa una red al azar que no se usa.

V15 (docs/PLAN_V15_CURRICULO.md): parte del último checkpoint de la V14 y empieza en el NIVEL 0. Cinco niveles (duelo
abierto, duelo con civil, muro, muro y civil, misión completa) con criterios propios para subir (rendición, cenit,
identidad, choques, re-adquisición). La misión se cumple cuando el ladrón se rinde; sin rendición en 5 min gana el ladrón.
Graba una repetición por nivel (replay_nivel_K.json) y hitos densos al empezar cada nivel.

V14 · CURRÍCULO PROGRESIVO (gatear -> caminar -> correr -> volar): niveles 0-3 del entorno (Duelo abierto, Muro único,
Ruido visual, Misión completa). CurriculumCallback sube de nivel cuando el éxito en el nivel actual supera el umbral en
una ventana de partidas, con un mínimo de pasos en el nivel y una paciencia máxima. Un 25 % de las partidas repasa
niveles ya superados (sin repaso, la red olvida lo anterior). Registra la competencia dron vs ladrón para el visor.
Parte del checkpoint más nuevo de la V12 (la V13 no llegó a entrenar; su entorno está incluido).

V13 · CURRÍCULO Y GEOMETRÍA DE LA BÚSQUEDA: fine-tuning desde el checkpoint más nuevo de la V12 (modelos_v12/), con
el entorno V13 (partidas "Un Solo Muro", GIRO_360 fijo, interrupción táctica, stand-off por FOV, detección parcial).
Al arrancar por primera vez guarda la salida de la V12 en salida_v12/ (el visor empieza limpio con la V13).

V12 · CONTROL JERÁRQUICO HÍBRIDO: FINE-TUNING ESTRICTO desde el último checkpoint de la V10 master (769.6 M pasos).
  · Capa FÍSICA (no es una red, no aprende): PID de ArduPilot y del gimbal en control.py (inercia, gravedad, jerk).
  · Capa INFERIOR del actor (policy_net[0], 192 -> 128): CONGELADA ENTERA (pesos y sesgo, requires_grad = False). Es la
    lectura de los sensores aprendida en 1 000+ M pasos; no se toca.
  · Capa TÁCTICA (policy_net[2], 128 -> 128) y la salida de decisiones (action_net): lo ÚNICO del actor que se afina.
  · Crítico (value_net): se reentrena entero; no vuela, solo estima el valor con las recompensas nuevas de la V12.
  Sin argumentos: si ya existe modelos_v13/ultimo.zip lo retoma; si no, arranca desde el checkpoint más nuevo de la V12.

Arquitectura de control (la red NO estabiliza nada):
    observación (sensores + mapa SLAM + memoria) ─▶ política PPO (Jetson) ─▶ acción táctica (10 clases)
        ─▶ lógica de la Jetson: consignas de velocidad X/Y/Z, tasa de guiñada y ángulo del gimbal
        ─▶ MAVLink ─▶ PID de ArduPilot en la Pixhawk (control.AutopilotoArduPilot: PSC + ATC, roll/pitch/yaw/Z)
        ─▶ PWM AUX1 ─▶ PID del gimbal BaseCam (control.GimbalBaseCam: 30°/s, -45°..+15°)

Transferencia de aprendizaje: la política base es la red PPO entrenada hasta la V9 (autojuego propio). La primera
vez se convierte a un modelo SB3 y se guarda (PPO.save); después siempre se arranca con PPO.load. Se CONGELA la capa
inferior del actor para las 36 entradas de los sensores de seguimiento y de la memoria (lo aprendido en 300+ M pasos:
cómo leer YOLO, el LiDAR y el tracker). Se afinan (fine-tuning) las conexiones de las entradas nuevas (mapa SLAM, estado
propio, predicción), la capa táctica superior y la salida. El crítico se reentrena completo.

El ladrón aprendido de las versiones anteriores queda congelado dentro del entorno (30% de las partidas); el resto es
el ladrón táctico con biomecánica, pathfinding y campos potenciales. Los peatones y el ladrón cambian en cada partida
(aleatorización del dominio) y un currículo sube la exigencia cuando el dron mejora.

Salidas: salida/ (lo lee el visor, igual que antes), modelos_master/ (modelos SB3: base, último y un checkpoint por cada
millón de pasos) y modelos/dron_politica.json (pesos para la Jetson, mismo formato).

Uso:  python entrenar_master.py --base modelos/ultimo.pt [--pasos 1e9]      (primera vez: crea la base SB3)
      python entrenar_master.py --continuar                                   (retoma modelos_master/ultimo.zip)
"""
import argparse
import json
import os
import time

import numpy as np
import torch
import torch.nn as nn
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.vec_env import VecEnv

from collections import deque

from entorno import (CLASES, DT, EJES_U, N_ACC_PERSONA, N_NIVELES, NIVELES, NOMBRE_ESTADO, OBS_DRON, OBS_PERSONA, R_COMP,
                     NIVEL_V16, NOMBRE_V16, N_OBS_V16,
                     ASOMO, CUSTODIA_S, INVESTIGAR, MURO_CANTO, PASOS_EPISODIO, PREDECIR, SIGUIENTE_OBSTACULO, T_RINDE_BASE,
                     T_RINDE_RESERVA, VENTAJA_ALTURA, EntornoDronPersona, resultado_de)

BUSQUEDA_V15 = (PREDECIR, INVESTIGAR, ASOMO, SIGUIENTE_OBSTACULO, VENTAJA_ALTURA, MURO_CANTO)
from entrenar import ActorCritico, actuar, grabar_partida, guardar_json, sin_ahorro_de_energia
from mision import grabar_mision

VERSION = "V16"
SALIDA, MODELOS, MASTER = "salida", "modelos", "modelos_v16"
ORIGEN_PREVIO = "modelos_v15"    # checkpoints de la versión anterior (de aquí sale el punto de partida del fine-tuning)
OBS_PREVIA = OBS_DRON - N_OBS_V16   # entradas de la red de la V15
# V15 · criterios para subir de cada nivel (plan, sección 3), sobre las últimas `ventana` partidas del nivel
CRITERIOS = {
    0: dict(rinde=0.85, cenit=0.70),                          # duelo abierto (las partidas de cenit cuentan)
    1: dict(rinde=0.85, id_ok=0.98, nodet=0, choques=0.0),    # duelo con civil
    2: dict(rinde=0.80, readq=8.0),                           # muro
    3: dict(rinde=0.75, id_ok=0.98),                          # muro y civil
}
N_BASE_CONGELADAS = 36           # entradas de seguimiento + memoria (las de la v8) cuya capa inferior se congela
AUTOR = "Brahian Andrés Orrego Osorio"


# ======================================================================= el entorno para SB3
class VecDron(VecEnv):
    """Los N entornos vectorizados de entorno.py como un VecEnv de SB3 (un solo agente: el dron). El ladrón aprendido
    juega dentro con su red congelada. Acumula las métricas por partida para el visor."""

    def __init__(self, n, semilla, red_persona):
        self.env = EntornoDronPersona(n, semilla=semilla)
        super().__init__(n, spaces.Box(-np.inf, np.inf, (OBS_DRON,), np.float32), spaces.Discrete(len(CLASES)))
        self.red_p = red_persona
        self.acciones = np.zeros(n, int)
        z = lambda: np.zeros(n)
        self.ep_ret, self.ep_man, self.ep_vis, self.ep_len = z(), z(), z(), z()
        self.ep_pierde, self.ep_recupera, self.ep_descubre = z(), z(), z()
        self.ep_comp = np.zeros((n, len(R_COMP)))           # V12: recompensa por componente de cada partida
        self.ep_interr = z()                                # V13: interrupciones tácticas por partida
        self.ep_idok, self.ep_desig, self.ep_nodet, self.ep_busca = z(), z(), z(), z()   # V15: identidad y búsqueda
        self.vaciar()

    def vaciar(self):
        self.fin, self.jit, self.esf, self.mando = [], 0.0, 0.0, 0
        self.fin_x = []                                     # V15: datos extra de cada partida terminada (dict)
        self.cuenta_dec = np.zeros(len(CLASES))
        self.cuenta_busq = np.zeros(len(CLASES))
        self.du = np.zeros(len(EJES_U))                     # V12: jitter físico por eje (Σ|Δu| con la IA al mando)
        self.estados = np.zeros(len(NOMBRE_ESTADO))         # V12: pasos en cada estado de la máquina
        self.ciego = 0

    def reset(self):
        return self.env.obs_dron().astype(np.float32)

    def step_async(self, actions):
        self.acciones = np.asarray(actions).astype(int)

    def step_wait(self):
        e = self.env
        ap, _, _, _ = actuar(self.red_p, e.obs_persona())        # (en la V16 el ladrón táctico no la usa)
        md = e.mascara_decision()
        r, _, done, info = e.step(self.acciones, ap, auto_reset=False)
        obs = e.obs_dron().astype(np.float32)
        self.cuenta_dec += np.bincount(self.acciones[md], minlength=len(CLASES))
        self.cuenta_busq += np.bincount(self.acciones[info["busqueda_ia"]], minlength=len(CLASES))
        self.jit += float(info["jitter"].sum())
        self.esf += float(info["esfuerzo"].sum())
        self.mando += int(info["al_mando"].sum())
        self.ep_ret += r
        self.ep_man += info["inicia"]
        self.ep_vis += info["visto"]
        self.ep_len += 1
        self.ep_pierde += info["pierde"]
        self.ep_recupera += info["recupera"]
        self.ep_descubre += info["descubre"]
        self.ep_comp += info["r_comp"]
        self.ep_interr += info["interrumpe"]
        self.ep_idok += info["id_ok"]
        self.ep_desig += info["fijado"]
        self.ep_nodet += info["cambio_nodet"]
        self.ep_busca += np.isin(info["estado_busq"], BUSQUEDA_V15)
        self.du += info["du"].sum(0)
        self.estados += np.bincount(info["estado_busq"], minlength=len(NOMBRE_ESTADO))[:len(NOMBRE_ESTADO)]
        self.ciego += int(info["ciego"].sum())
        infos = [{} for _ in range(self.num_envs)]
        for i in np.where(done)[0]:
            falla = info["choque"][i] or info["fuera"][i] or info["panel"][i] or info["perdido"][i] or info["no_encontrado"][i]
            infos[i]["terminal_observation"] = obs[i].copy()
            # C2 (diagnóstico del nivel 4): el tope de 5 min sin rendición es TERMINAL (pierde el dron, R_TOPE en el
            # entorno), no un corte por tiempo: antes SB3 hacía bootstrap del valor y perder por tiempo no costaba nada
            infos[i]["TimeLimit.truncated"] = False
            self.fin.append((bool(info["choque_ladron"][i]), bool(info["choque_peaton"][i]), bool(info["panel"][i]),
                             bool(info["fuera"][i]), self.ep_vis[i] / self.ep_len[i], self.ep_man[i], self.ep_ret[i],
                             int(info["peatones"][i]), bool(info["exito"][i]), bool(info["perdido"][i]),
                             bool(info["no_encontrado"][i]), self.ep_pierde[i], self.ep_recupera[i], self.ep_descubre[i],
                             float(info["t_ep"][i]), float(info["gmb_min"][i]), *self.ep_comp[i],
                             float(info["un_muro"][i]), self.ep_interr[i], int(info["nivel_ep"][i]), bool(info["cenit_ep"][i])))
            self.fin_x.append(dict(
                rinde=bool(info["exito"][i]), cenit=bool(info["cenit_ep"][i]), nivel=int(info["nivel_ep"][i]),
                tiempo=bool(info["tiempo"][i] and not falla and not info["exito"][i]),
                idok=float(self.ep_idok[i]), desig=float(self.ep_desig[i]), nodet=int(self.ep_nodet[i]),
                choque=bool(info["choque"][i] or info["panel"][i]),
                readq=(float(self.ep_busca[i]) * DT / self.ep_recupera[i]) if self.ep_recupera[i] > 0 else None,
                # C3: custodia y búsqueda
                racha=float(info["racha"][i]), trinde=float(info["t_rinde"][i]), vista=float(info["t_vista_ac"][i]),
                readq_s=(float(info["t_readq_sum"][i] / info["n_readq"][i]) if info["n_readq"][i] > 0 else None),
                n_readq=int(info["n_readq"][i]), busq=[round(float(v), 1) for v in info["t_busq_est"][i]],
                readq_est=[int(v) for v in info["readq_est"][i]]))
        for a in (self.ep_ret, self.ep_man, self.ep_vis, self.ep_len, self.ep_pierde, self.ep_recupera, self.ep_descubre, self.ep_comp, self.ep_interr,
                  self.ep_idok, self.ep_desig, self.ep_nodet, self.ep_busca):
            a[done] = 0.0
        if done.any():
            e.reset(done)
            obs[done] = e.obs_dron()[done]
        return obs, r.astype(np.float32), done, infos

    def close(self):
        pass

    def get_attr(self, attr_name, indices=None):
        return [getattr(self.env, attr_name)] * self.num_envs

    def set_attr(self, attr_name, value, indices=None):
        setattr(self.env, attr_name, value)

    def env_method(self, method_name, *args, indices=None, **kwargs):
        return [getattr(self.env, method_name)(*args, **kwargs)]

    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * self.num_envs


# ======================================================================= modelo SB3 y transferencia
def nuevo_ppo(venv, lr):
    return PPO("MlpPolicy", venv, learning_rate=lr, n_steps=128, batch_size=8192, n_epochs=4, gamma=0.99,
               gae_lambda=0.95, clip_range=0.2, ent_coef=0.01, vf_coef=0.5, max_grad_norm=0.5, device="cpu", verbose=0,
               policy_kwargs=dict(net_arch=dict(pi=[128, 128], vf=[128, 128]), activation_fn=nn.Tanh, ortho_init=False))


def crear_base(ruta_pt, venv, ruta_zip, lr):
    """Convierte la red PPO propia (V9) en un modelo SB3 equivalente capa por capa y lo guarda (PPO.save)."""
    ck = torch.load(ruta_pt, weights_only=False)
    red = ActorCritico(OBS_DRON, len(CLASES))
    red.load_state_dict(ck["dron"])
    modelo = nuevo_ppo(venv, lr)
    p = modelo.policy
    with torch.no_grad():
        for dst, src in ((p.mlp_extractor.policy_net[0], red.pi[0]), (p.mlp_extractor.policy_net[2], red.pi[2]),
                         (p.action_net, red.pi[4]), (p.mlp_extractor.value_net[0], red.v[0]),
                         (p.mlp_extractor.value_net[2], red.v[2]), (p.value_net, red.v[4])):
            dst.weight.copy_(src.weight)
            dst.bias.copy_(src.bias)
        o = torch.randn(64, OBS_DRON)
        dif = (p.get_distribution(o).distribution.logits - torch.log_softmax(red.pi(o), -1)).abs().max().item()
    modelo.save(ruta_zip)
    print("base SB3 creada desde %s (iteración %d, %.1f M pasos) · diferencia de salida %.1e" % (ruta_pt, ck["iteracion"], ck["pasos"] / 1e6, dif), flush=True)
    return ck


def congelar_capas_fisicas(modelo):
    """V12 · FINE-TUNING ESTRICTO: la capa inferior del actor queda congelada ENTERA (requires_grad = False: el optimizador
    no la toca). Solo aprenden la capa táctica (policy_net[2]), la salida de decisiones (action_net) y el crítico."""
    p = modelo.policy
    for prm in p.mlp_extractor.policy_net[0].parameters():
        prm.requires_grad_(False)
    afina = [p.mlp_extractor.policy_net[2], p.action_net]
    n_con = sum(q.numel() for q in p.mlp_extractor.policy_net[0].parameters())
    n_tac = sum(q.numel() for c in afina for q in c.parameters())
    n_crit = sum(q.numel() for q in list(p.mlp_extractor.value_net.parameters()) + list(p.value_net.parameters()))
    print("fine-tuning estricto · capa inferior CONGELADA: %d parámetros · capa táctica + salida que se afinan: %d · crítico: %d"
          % (n_con, n_tac, n_crit), flush=True)


def archivar_salida_previa():
    """Al empezar una versión nueva, la salida de la anterior (métricas, repeticiones, hitos) pasa a salida_<versión>/."""
    ruta = os.path.join(SALIDA, "metricas.json")
    if not os.path.exists(ruta):
        return
    try:
        previa = (json.load(open(ruta, encoding="utf-8")) or [{}])[-1].get("version", "previa")
    except (ValueError, OSError):
        previa = "previa"
    destino = "%s_%s" % (SALIDA, str(previa).lower())
    if previa != VERSION and not os.path.exists(destino):
        os.replace(SALIDA, destino)
        os.makedirs(os.path.join(SALIDA, "hitos"), exist_ok=True)
        print("salida de la %s guardada en %s" % (previa, destino), flush=True)


def ultimo_checkpoint(carpeta):
    """El modelo SB3 más nuevo de una corrida (los checkpoints de cada millón de pasos y ultimo.zip)."""
    d = os.path.join(carpeta, "checkpoints")
    cands = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".zip")] if os.path.isdir(d) else []
    cands.append(os.path.join(carpeta, "ultimo.zip"))
    cands = [c for c in cands if os.path.exists(c)]
    return max(cands, key=os.path.getmtime) if cands else None


def congelar_capas_inferiores(modelo, n_base=N_BASE_CONGELADAS):
    """Transferencia: la capa inferior del actor queda fija para las n_base entradas de seguimiento (y su sesgo);
    aprenden las conexiones de las entradas nuevas, la capa táctica superior y la salida."""
    capa = modelo.policy.mlp_extractor.policy_net[0]
    mascara = torch.ones_like(capa.weight)
    mascara[:, :n_base] = 0.0
    capa.weight.register_hook(lambda g: g * mascara)
    capa.bias.register_hook(lambda g: g * 0.0)
    libres = sum(p.numel() for p in modelo.policy.parameters()) - int((mascara == 0).sum()) - capa.bias.numel()
    print("transferencia: capa inferior congelada para %d entradas · %d parámetros se afinan" % (n_base, libres), flush=True)


class PoliticaSB3(object):
    """Adaptador: la política SB3 con la interfaz de ActorCritico (dist, v) para grabar repeticiones y misiones."""

    def __init__(self, modelo):
        self.m = modelo

    def dist(self, o):
        return self.m.policy.get_distribution(o).distribution

    def v(self, o):
        return self.m.policy.predict_values(o)


def exportar(modelo, **extra):
    p = modelo.policy
    capas = [p.mlp_extractor.policy_net[0], p.mlp_extractor.policy_net[2], p.action_net]
    return dict({"capas": [{"W": c.weight.detach().numpy().round(6).tolist(), "b": c.bias.detach().numpy().round(6).tolist()}
                           for c in capas], "activacion": "tanh", "clases": CLASES, "autor": AUTOR}, **extra)


# ======================================================================= callbacks: métricas, repeticiones y currículo
def resumen(lst):
    if not lst:
        return None
    arr = np.array(lst, dtype=float)
    con_pea = arr[:, 7] > 0
    comp = arr[:, 16:16 + len(R_COMP)].mean(0)
    um = arr[:, 16 + len(R_COMP)] > 0.5
    interr = arr[:, 17 + len(R_COMP)]
    return {"n": len(lst), "alcanzado": float(arr[:, 0].mean()),
            "peaton": float(arr[con_pea, 1].mean()) if con_pea.any() else None,
            "panel": float(arr[:, 2].mean()), "fuera": float(arr[:, 3].mean()), "vista": float(arr[:, 4].mean()),
            "maniobras": float(arr[:, 5].mean()), "recompensa": float(arr[:, 6].mean()), "cumplida": float(arr[:, 8].mean()),
            "perdido": float(arr[:, 9].mean()), "no_encontrado": float(arr[:, 10].mean()), "perdidas": float(arr[:, 11].mean()),
            "recuperaciones": float(arr[:, 12].mean()), "redescubre": float(arr[:, 13].mean()),
            "t_ep": float(arr[:, 14].mean()), "gmb_min": float(arr[:, 15].min()),
            "r_comp": {k: round(float(v), 4) for k, v in zip(R_COMP, comp)},
            "frac_un_muro": float(um.mean()), "interrupciones": float(interr.mean()),
            "cumplida_un_muro": float(arr[um, 8].mean()) if um.any() else None,
            "cumplida_completo": float(arr[~um, 8].mean()) if (~um).any() else None}


# índices en la tupla de cada partida terminada (VecDron.fin)
I_EXITO, I_ALCANZADO, I_PERDIDO, I_NO_ENC = 8, 0, 9, 10
I_NIVEL = 18 + len(R_COMP)
I_CENIT = I_NIVEL + 1


def ganador(f, x=None):
    """Competencia dron vs ladrón. Gana el DRON si el ladrón se rindió; gana el LADRÓN si alcanzó al dron, si el dron lo
    perdió (90 s de búsqueda sin éxito), si nunca lo encontró o (V15) si pasaron los 5 minutos sin rendición. Lo demás
    (choque con un muro o un civil, geocerca) son fallas propias del dron: no cuentan como victoria de nadie."""
    if f[I_EXITO]:
        return "dron"
    if f[I_ALCANZADO] or f[I_PERDIDO] or f[I_NO_ENC] or (x is not None and x.get("tiempo")):
        return "ladron"
    return "otros"


def evaluar_criterios(nivel, xs):
    """V15: estado de cada criterio del nivel sobre las partidas xs (dicts de VecDron.fin_x). Devuelve (valores, cumple)."""
    if not xs:
        return {}, False
    c = CRITERIOS.get(nivel, {})
    val = {"rinde": float(np.mean([x["rinde"] for x in xs]))}
    ce = [x["rinde"] for x in xs if x["cenit"]]
    val["cenit"] = float(np.mean(ce)) if len(ce) >= 30 else None
    des = sum(x["desig"] for x in xs)
    val["id_ok"] = sum(x["idok"] for x in xs) / des if des else None
    val["nodet"] = int(sum(x["nodet"] for x in xs))
    val["choques"] = float(np.mean([x["choque"] for x in xs]))
    rq = [x["readq"] for x in xs if x["readq"] is not None]
    val["readq"] = float(np.mean(rq)) if rq else None
    ok = True
    for k, umbral in c.items():
        v = val.get(k)
        if v is None:
            ok = False
        elif k in ("rinde", "cenit", "id_ok"):
            ok &= v >= umbral
        elif k == "readq":
            ok &= v < umbral
        else:                                             # nodet, choques: como máximo el umbral
            ok &= v <= umbral
    return val, ok


def resumen_nivel(xs):
    """C3: resumen de las partidas de un nivel. Para el nivel 4 el número principal es la CUSTODIA: vista acumulada de al
    menos 60 (o 90) s en la partida de 5 min, o el ladrón se rindió (la partida termina antes: también es custodia
    cumplida). Es lo que se le pide al dron en el caso policial."""
    if not xs:
        return {}
    med = lambda v: float(np.median(v)) if len(v) else None
    rq = [x["readq_s"] for x in xs if x.get("readq_s") is not None]
    busq = np.array([x["busq"] for x in xs])
    rqe = np.array([x["readq_est"] for x in xs]).sum(0)
    return {"n": len(xs), "rinde": float(np.mean([x["rinde"] for x in xs])),
            "tope": float(np.mean([x["tiempo"] for x in xs])),
            "custodia_%d" % CUSTODIA_S[0]: float(np.mean([x["rinde"] or x["vista"] >= CUSTODIA_S[0] for x in xs])),
            "custodia_%d" % CUSTODIA_S[1]: float(np.mean([x["rinde"] or x["vista"] >= CUSTODIA_S[1] for x in xs])),
            "vista_med": med([x["vista"] for x in xs]), "racha_med": med([x["racha"] for x in xs]),
            "trinde_med": med([x["trinde"] for x in xs]), "readq_s": float(np.mean(rq)) if rq else None,
            "busq_s": {NOMBRE_ESTADO[k]: round(float(busq[:, k].mean()), 1) for k in range(busq.shape[1]) if busq[:, k].any()},
            "readq_desde": {NOMBRE_ESTADO[k]: round(float(rqe[k] / max(rqe.sum(), 1)), 3) for k in range(len(rqe)) if rqe[k]}}


def texto_resumen_nivel(k, r):
    """Línea del log por nivel; en el nivel 4 la custodia va primero."""
    f = lambda v, fmt="%.0f %%", k_=100: "--" if v is None else fmt % (k_ * v)
    cus = "CUSTODIA ≥%ds %s · ≥%ds %s" % (CUSTODIA_S[0], f(r.get("custodia_%d" % CUSTODIA_S[0])), CUSTODIA_S[1],
                                          f(r.get("custodia_%d" % CUSTODIA_S[1])))
    resto = "rendición %s · tope %s · racha med %s s · T_rinde med %s s · re-adquiere en %s s" % (
        f(r.get("rinde")), f(r.get("tope")), f(r.get("racha_med"), "%.0f", 1), f(r.get("trinde_med"), "%.0f", 1),
        f(r.get("readq_s"), "%.1f", 1))
    principal = (cus + " | " + resto) if k == N_NIVELES - 1 else (resto + " | " + cus)
    return "     N%d (%d partidas) %s" % (k, r.get("n", 0), principal)


class CurriculumCallback(BaseCallback):
    """V14 · ÁRBITRO DE PROGRESIÓN. Mira las partidas terminadas del NIVEL ACTUAL (sin las de repaso y sin las de cenit,
    que son práctica y se reportan aparte) y, cuando el éxito en las últimas `ventana` supera `umbral` y el nivel lleva al
    menos `min_pasos`, sube current_level en el entorno. Si tras `paciencia` pasos no lo supera, también sube (con aviso),
    para que un nivel imposible no trabe el entrenamiento. Lleva además la competencia dron vs ladrón."""

    def __init__(self, venv, nivel=0, umbral=0.85, ventana=1000, min_pasos=2e6, paciencia=5e7, pasos_inicio=0):
        super().__init__()
        self.venv, self.umbral, self.ventana = venv, umbral, int(ventana)
        self.min_pasos, self.paciencia = min_pasos, paciencia
        self.nivel, self.pasos_inicio = int(nivel), int(pasos_inicio)
        self.exitos = deque(maxlen=self.ventana)          # éxito (0/1) de las partidas del nivel actual que cuentan
        self.xs = deque(maxlen=self.ventana)              # V15: datos de las partidas del nivel actual (criterios)
        self.xs_nivel = {k: deque(maxlen=self.ventana) for k in range(N_NIVELES)}   # C3: últimas partidas de cada nivel
        self.valores, self.cumple = {}, False
        self.cenit = deque(maxlen=self.ventana)           # éxito en las partidas de cenit (práctica de punto ciego)
        self.duelo = deque(maxlen=self.ventana)           # ganador de cada partida del nivel actual (incluye cenit)
        self.total = {"dron": 0, "ladron": 0, "otros": 0}  # acumulado de todo el entrenamiento
        self.exito_iter = None
        self.historia = []                                # ascensos: {nivel, pasos, motivo}
        self.aplicar(self.nivel)

    def aplicar(self, nivel):
        """Manda el nivel al entorno de entrenamiento y a los entornos que se creen después (repeticiones)."""
        self.nivel = int(np.clip(nivel, 0, N_NIVELES - 1))
        EntornoDronPersona.nivel_inicial = self.nivel
        self.venv.env.current_level = self.nivel

    def _on_step(self):
        return True

    def _on_rollout_end(self):
        nuevos = 0
        exitos_it = []
        fx = getattr(self.venv, "fin_x", None) or [None] * len(self.venv.fin)
        for f, x in zip(self.venv.fin, fx):
            g = ganador(f, x)
            self.total[g] += 1
            if x is not None and "vista" in x:
                self.xs_nivel[int(f[I_NIVEL])].append(x)
            if f[I_NIVEL] != self.nivel:
                continue                                   # repaso de un nivel anterior
            self.duelo.append(g)
            if x is not None:
                self.xs.append(x)
            # V15: las partidas de cenit también cuentan para subir (y se miden aparte)
            if f[I_CENIT]:
                self.cenit.append(float(f[I_EXITO]))
            self.exitos.append(float(f[I_EXITO]))
            exitos_it.append(float(f[I_EXITO]))
            nuevos += 1
        self.exito_iter = float(np.mean(exitos_it)) if exitos_it else None
        pasos = int(self.model.num_timesteps)
        self.valores, self.cumple = evaluar_criterios(self.nivel, list(self.xs))
        en_nivel = pasos - self.pasos_inicio
        if self.nivel >= N_NIVELES - 1 or en_nivel < self.min_pasos:
            return
        exito = float(np.mean(self.exitos)) if len(self.exitos) >= self.ventana else None
        self.valores, self.cumple = evaluar_criterios(self.nivel, list(self.xs))
        supera = exito is not None and (self.cumple if self.nivel in CRITERIOS else exito >= self.umbral)
        agota = self.paciencia > 0 and en_nivel >= self.paciencia
        if supera or agota:
            anterior = self.nivel
            self.aplicar(self.nivel + 1)
            self.venv.set_attr("nivel", 0.0)               # la intensidad (viento, rapidez del ladrón) arranca suave
            self.historia.append({"de": anterior, "a": self.nivel, "pasos": pasos,
                                  "motivo": "umbral" if supera else "paciencia", "exito": exito})
            self.pasos_inicio = pasos
            self.exitos.clear()
            self.cenit.clear()
            self.duelo.clear()
            self.xs.clear()
            if supera:
                print(">>> NIVEL SUPERADO: Ascendiendo a Nivel %d (%s) <<<  (éxito %.1f %% en las últimas %d partidas del "
                      "nivel %d · %.1f M pasos)" % (self.nivel, NIVELES[self.nivel], 100 * exito, self.ventana, anterior,
                                                   pasos / 1e6), flush=True)
            else:
                print(">>> PACIENCIA AGOTADA: el nivel %d (%s) no llegó al %.0f %% en %.0f M pasos (éxito %s). Ascendiendo a "
                      "Nivel %d (%s) <<<" % (anterior, NIVELES[anterior], 100 * self.umbral, en_nivel / 1e6,
                                             "--" if exito is None else "%.1f %%" % (100 * exito), self.nivel,
                                             NIVELES[self.nivel]), flush=True)

    def competencia(self):
        n = len(self.duelo)
        c = {k: sum(1 for g in self.duelo if g == k) for k in ("dron", "ladron", "otros")}
        decisivas = c["dron"] + c["ladron"]
        return {"dron": c["dron"] / decisivas if decisivas else None, "ladron": c["ladron"] / decisivas if decisivas else None,
                "otros": c["otros"] / n if n else None, "n": n, "decisivas": decisivas, "total": dict(self.total)}

    def estado(self):
        return {"nivel": self.nivel, "nombre": NIVELES[self.nivel], "niveles": NIVELES, "umbral": self.umbral,
                "ventana": self.ventana, "partidas": len(self.exitos),
                "exito": float(np.mean(self.exitos)) if self.exitos else None,
                "exito_cenit": float(np.mean(self.cenit)) if self.cenit else None,
                "pasos_en_nivel": int(self.model.num_timesteps) - self.pasos_inicio if self.model else 0,
                "min_pasos": self.min_pasos, "paciencia": self.paciencia, "historia": self.historia,
                "pasos_inicio": self.pasos_inicio, "criterios": CRITERIOS.get(self.nivel, {}),
                "valores": evaluar_criterios(self.nivel, list(self.xs))[0] if self.xs else {},
                "por_nivel": {k: resumen_nivel(list(v)) for k, v in self.xs_nivel.items() if v}}


class CurriculoV16(BaseCallback):
    """V16 · sin currículo: una sola partida (NIVEL_V16). Lleva las métricas de custodia y rendición de las últimas
    `ventana` partidas y la competencia dron vs ladrón, con la misma interfaz que CurriculumCallback para el Maestro.
    El "éxito" que gobierna la intensidad (viento, rapidez del ladrón) es la custodia de 60 s."""

    def __init__(self, venv, ventana=1000):
        super().__init__()
        self.venv, self.ventana = venv, int(ventana)
        self.nivel, self.pasos_inicio, self.historia = NIVEL_V16, 0, []
        self.xs = deque(maxlen=self.ventana)
        self.duelo = deque(maxlen=self.ventana)
        self.total = {"dron": 0, "ladron": 0, "otros": 0}
        self.exito_iter = None
        EntornoDronPersona.nivel_inicial = NIVEL_V16
        venv.env.current_level = NIVEL_V16

    def _on_step(self):
        return True

    def _on_rollout_end(self):
        fx = getattr(self.venv, "fin_x", None) or [None] * len(self.venv.fin)
        it_ = []
        for f, x in zip(self.venv.fin, fx):
            g = ganador(f, x)
            self.total[g] += 1
            self.duelo.append(g)
            if x is not None:
                self.xs.append(x)
                it_.append(float(x["rinde"] or x["vista"] >= CUSTODIA_S[0]))
        self.exito_iter = float(np.mean(it_)) if it_ else None

    competencia = CurriculumCallback.competencia

    def estado(self):
        r = resumen_nivel(list(self.xs))
        return {"nivel": NIVEL_V16, "nombre": NOMBRE_V16, "niveles": NIVELES + [NOMBRE_V16], "umbral": 0.0,
                "ventana": self.ventana, "partidas": len(self.xs), "exito": r.get("custodia_%d" % CUSTODIA_S[0]),
                "exito_cenit": None, "pasos_en_nivel": int(self.model.num_timesteps) if self.model else 0,
                "min_pasos": 0, "paciencia": 0, "historia": [], "pasos_inicio": 0, "criterios": {}, "valores": {},
                "por_nivel": {NIVEL_V16: r} if r else {}}


def _copiar_pesos(dst, src, n_viejas=None):
    """Copia una capa lineal; si src tiene menos entradas (n_viejas), las columnas nuevas de dst quedan en cero."""
    with torch.no_grad():
        dst.bias.copy_(src.bias)
        if src.weight.shape == dst.weight.shape:
            dst.weight.copy_(src.weight)
        else:
            dst.weight.zero_()
            dst.weight[:, :src.weight.shape[1]].copy_(src.weight)


def desde_v15_zip(ruta, venv, lr):
    """V16: modelo nuevo de 195 entradas con los pesos del modelo SB3 de la V15 (192): actor y crítico completos; las
    columnas de las entradas nuevas en cero (al empezar decide exactamente igual que la V15)."""
    viejo = PPO.load(ruta, device="cpu", custom_objects={"learning_rate": lr})
    modelo = nuevo_ppo(venv, lr)
    pv, pn = viejo.policy, modelo.policy
    for a, b in ((pn.mlp_extractor.policy_net[0], pv.mlp_extractor.policy_net[0]),
                 (pn.mlp_extractor.policy_net[2], pv.mlp_extractor.policy_net[2]), (pn.action_net, pv.action_net),
                 (pn.mlp_extractor.value_net[0], pv.mlp_extractor.value_net[0]),
                 (pn.mlp_extractor.value_net[2], pv.mlp_extractor.value_net[2]), (pn.value_net, pv.value_net)):
        _copiar_pesos(a, b)
    return modelo


def desde_json(ruta, venv, lr):
    """V16 sin modelos SB3 (por ejemplo en la nube): el actor sale de la política exportada para la Jetson
    (modelos/dron_politica.json, entradas nuevas en cero); el crítico arranca de cero."""
    d = json.load(open(ruta, encoding="utf-8"))
    modelo = nuevo_ppo(venv, lr)
    pn = modelo.policy
    for capa, c in zip((pn.mlp_extractor.policy_net[0], pn.mlp_extractor.policy_net[2], pn.action_net), d["capas"]):
        src = nn.Linear(len(c["W"][0]), len(c["W"]))
        with torch.no_grad():
            src.weight.copy_(torch.tensor(c["W"]))
            src.bias.copy_(torch.tensor(c["b"]))
        _copiar_pesos(capa, src)
    return modelo, d.get("pasos")


def red_ladron(ruta):
    """La red del ladrón congelada; en la V16 el ladrón es siempre el táctico y la red no se usa (si falta, una al azar)."""
    red_p = ActorCritico(OBS_PERSONA, N_ACC_PERSONA)
    if ruta and os.path.exists(ruta):
        red_p.load_state_dict(torch.load(ruta, weights_only=False))
    return red_p


def grabar_nivel(red_d, red_p, nivel, semilla, iteracion, pasos_tot):
    """V15: una partida con la política actual FORZADA a un nivel del currículo (para la pestaña de ese nivel)."""
    env = EntornoDronPersona(1, semilla=semilla, nivel=nivel)
    cuadros = []
    resultado, maniobras = "tiempo", 0
    for _ in range(PASOS_EPISODIO + 5):
        od, op = env.obs_dron(), env.obs_persona()
        ad, _, _, probs = actuar(red_d, od, codicioso=True)
        ap, _, _, _ = actuar(red_p, op, codicioso=False)
        foto = env.foto(0)
        foto["a"] = int(ad[0])
        foto["dec"] = bool(env.mascara_decision()[0])
        foto["pr"] = [round(float(x), 3) for x in probs[0]]
        cuadros.append(foto)
        _, _, done, info = env.step(ad, ap, auto_reset=False)
        maniobras += int(info["inicia"][0])
        if done[0]:
            resultado = resultado_de(info, 0)
            f = env.foto(0)
            f["dec"], f["pr"] = False, cuadros[-1]["pr"]
            cuadros.append(f)
            break
    return {"iteracion": iteracion, "pasos": pasos_tot, "adversaria": True, "guion": None, "paneles": env.paneles(0),
            "resultado": resultado, "maniobras": maniobras, "dt": DT, "cuadros": cuadros, "version": VERSION,
            "nivel": int(nivel), "nombre_nivel": NOMBRE_V16 if nivel == NIVEL_V16 else NIVELES[nivel],
            "t_rinde": [T_RINDE_BASE, T_RINDE_RESERVA],
            "autor": AUTOR}


class Maestro(BaseCallback):
    """Cada iteración (un rollout de 128 pasos x N entornos): métricas para el visor, currículo y, cada tanto,
    repeticiones, hitos, el último modelo y los pesos para la Jetson."""
    cada_rep = 5                                          # V16: cada cuántas iteraciones se graban repeticiones (0 = nunca)

    def __init__(self, venv, red_p, objetivo, metricas, iteracion, t_previo, hitos, curriculo=None):
        super().__init__()
        self.curriculo = curriculo
        self.venv, self.red_p, self.objetivo = venv, red_p, objetivo
        self.metricas, self.it, self.t_previo, self.hitos = metricas, iteracion, t_previo, hitos
        self.t0 = self.ti = time.time()
        self.pasos_ant = None
        self.historial = []
        self.replays_nivel = {}                           # V15: nivel -> iteración de su última repetición
        self.it_ini_nivel, self.nivel_ant, self.turno = iteracion, None, 0

    def _on_step(self):
        return True

    def _on_rollout_end(self):
        v = self.venv
        self.it += 1
        pasos = int(self.model.num_timesteps)
        dt_it = time.time() - self.ti
        self.ti = time.time()
        paso_it = pasos - (self.pasos_ant if self.pasos_ant is not None else pasos - v.num_envs * self.model.n_steps)
        self.pasos_ant = pasos
        seg = max(v.mando, 1) * DT
        control = ({"jitter": v.jit / seg, "esfuerzo": v.esf / seg, "total": (v.jit + v.esf) / seg, "seg_mando": round(v.mando * DT, 1),
                    "jitter_eje": {k: round(float(x) / seg, 4) for k, x in zip(EJES_U, v.du)}}
                   if v.mando else None)
        lg = self.model.logger.name_to_value
        m = {"it": self.it, "pasos": pasos, "seg": round(self.t_previo + time.time() - self.t0, 1), "adv": resumen(v.fin),
             "control": control, "nivel": round(float(v.env.nivel), 3),
             "acciones": [round(float(x), 4) for x in v.cuenta_dec / max(v.cuenta_dec.sum(), 1)],
             "acciones_busqueda": [round(float(x), 4) for x in v.cuenta_busq / max(v.cuenta_busq.sum(), 1)],
             "dron": {"l_pi": float(lg.get("train/policy_gradient_loss", 0.0)), "l_v": float(lg.get("train/value_loss", 0.0)),
                      "entropia": -float(lg.get("train/entropy_loss", 0.0))},
             "pasos_s": int(paso_it / max(dt_it, 1e-6)), "motor": "Stable-Baselines3 PPO", "autor": AUTOR, "version": VERSION,
             "estados": {k: round(float(x), 4) for k, x in zip(NOMBRE_ESTADO, v.estados / max(v.estados.sum(), 1))},
             "ciego": round(v.ciego / max(v.estados.sum(), 1), 5)}
        cur = self.curriculo
        if cur is not None:
            m["curriculo"] = cur.estado()
            m["competencia"] = cur.competencia()
        self.metricas.append(m)
        # INTENSIDAD (viento, rapidez y agresividad del ladrón, peatones): sube o baja despacio según el éxito de las
        # últimas iteraciones; con el currículo V14, el éxito del nivel actual
        exito_it = cur.exito_iter if cur is not None else (m["adv"]["cumplida"] if m["adv"] else None)
        if exito_it is not None:
            self.historial.append(exito_it)
        if len(self.historial) >= 10:
            meta = float(np.clip((np.mean(self.historial[-10:]) - 0.25) / 0.35, 0.0, 1.0))
            v.set_attr("nivel", float(np.clip(v.env.nivel + 0.01 * np.sign(meta - v.env.nivel), 0.0, 1.0)))
        v.vaciar()
        it = self.it
        if it % 2 == 0 or it < 5:
            guardar_json(os.path.join(SALIDA, "metricas.json"), self.metricas)
            guardar_json(os.path.join(SALIDA, "estado.json"), {"it": it, "pasos": pasos, "seg": m["seg"], "pasos_s": m["pasos_s"],
                                                               "objetivo": self.objetivo, "t": time.time(), "nivel": m["nivel"],
                                                               "version": VERSION, "curriculo": m.get("curriculo"),
                                                               "competencia": m.get("competencia"),
                                                               "replays_nivel": self.replays_nivel, "niveles": NIVELES + [NOMBRE_V16]})
        pol = PoliticaSB3(self.model)
        nv = cur.nivel if cur is not None else N_NIVELES - 1
        if nv != self.nivel_ant:
            self.it_ini_nivel, self.nivel_ant = it, nv
        rep_ok = self.cada_rep > 0
        if nv == NIVEL_V16 and rep_ok and (it % self.cada_rep == 0 or it == 1):
            # V16: la misión de 2 paneles (replay_v16.json; replay_adv.json para los visores viejos) y la misión con piloto
            rep = grabar_nivel(pol, self.red_p, NIVEL_V16, it, it, pasos)
            guardar_json(os.path.join(SALIDA, "replay_v16.json"), rep)
            guardar_json(os.path.join(SALIDA, "replay_adv.json"), rep)
            guardar_json(os.path.join(SALIDA, "replay_nivel_%d.json" % NIVEL_V16), rep)   # el visor V15 lo muestra como nivel 5
            self.replays_nivel["v16"] = self.replays_nivel[NIVEL_V16] = it
            guardar_json(os.path.join(SALIDA, "replay_mision.json"), grabar_mision(pol, self.red_p, actuar, it, pasos, it + 2))
            self.replays_nivel["mision"] = it
        elif rep_ok and (it % 5 == 0 or it == 1):
            # V15: cada 5 iteraciones, el nivel actual y la misión; los niveles ya superados, uno por turno
            rep = grabar_nivel(pol, self.red_p, nv, it, it, pasos)
            guardar_json(os.path.join(SALIDA, "replay_nivel_%d.json" % nv), rep)
            guardar_json(os.path.join(SALIDA, "replay_adv.json"), rep)                  # compatibilidad con visores viejos
            self.replays_nivel[nv] = it
            if nv > 0:
                k = self.turno % nv
                self.turno += 1
                guardar_json(os.path.join(SALIDA, "replay_nivel_%d.json" % k), grabar_nivel(pol, self.red_p, k, it + 7, it, pasos))
                self.replays_nivel[k] = it
            guardar_json(os.path.join(SALIDA, "replay_mision.json"), grabar_mision(pol, self.red_p, actuar, it, pasos, it + 2))
            self.replays_nivel["mision"] = it
            guardar_json(os.path.join(SALIDA, "estado.json"), {"it": it, "pasos": pasos, "seg": m["seg"], "pasos_s": m["pasos_s"],
                                                               "objetivo": self.objetivo, "t": time.time(), "nivel": m["nivel"],
                                                               "version": VERSION, "curriculo": m.get("curriculo"),
                                                               "competencia": m.get("competencia"),
                                                               "replays_nivel": self.replays_nivel, "niveles": NIVELES + [NOMBRE_V16]})
        # hitos del nivel actual: cada 5 iteraciones durante sus primeras 50, después cada 20; la misión cada 20
        en_nivel = it - self.it_ini_nivel
        if rep_ok and ((it % 5 == 0 and en_nivel <= 50) or it % 20 == 0 or it == 1):
            nombre = "nivel%d_it%05d.json" % (nv, it)
            guardar_json(os.path.join(SALIDA, "hitos", nombre), grabar_nivel(pol, self.red_p, nv, 1000 + it, it, pasos))
            self.hitos.append({"archivo": nombre, "it": it, "pasos": pasos, "adversaria": True, "mision": False, "nivel": nv})
            if it % 20 == 0 or it == 1:
                nombre = "it%05d_mision.json" % it
                guardar_json(os.path.join(SALIDA, "hitos", nombre), grabar_mision(pol, self.red_p, actuar, it, pasos, 2000 + it))
                self.hitos.append({"archivo": nombre, "it": it, "pasos": pasos, "adversaria": True, "mision": True})
            guardar_json(os.path.join(SALIDA, "hitos", "lista.json"), self.hitos)
        if it % 20 == 0 or it == 1:
            self.model.save(os.path.join(MASTER, "ultimo.zip"))
            guardar_json(os.path.join(MASTER, "estado_entrenamiento.json"), {
                "it": it, "pasos": pasos, "seg": m["seg"], "nivel": m["nivel"],
                "current_level": cur.nivel if cur is not None else None,
                "pasos_inicio_nivel": cur.pasos_inicio if cur is not None else None,
                "historia_curriculo": cur.historia if cur is not None else []})
            # V16: archivo aparte (195 entradas); el de la Jetson (dron_politica.json, 192) no se toca hasta adaptar su código
            guardar_json(os.path.join(MODELOS, "dron_politica_v16.json"), exportar(self.model, iteracion=it, pasos=pasos))
        if it % 5 == 0 or it < 5:
            e = m["adv"] or {}
            c = control or {}
            f2 = lambda x: "--" if x is None else "%.2f" % x
            f3 = lambda x: "--" if x is None else "%.4f" % x
            if isinstance(cur, CurriculoV16):
                cc = m["competencia"]
                r_ = m["curriculo"]["por_nivel"].get(NIVEL_V16) or {}
                print(texto_resumen_nivel(N_NIVELES - 1, r_).replace("N%d" % (N_NIVELES - 1), "V16") +
                      " | DOMINIO dron %s · ladrón %s" % ("--" if cc["dron"] is None else "%.0f %%" % (100 * cc["dron"]),
                                                          "--" if cc["ladron"] is None else "%.0f %%" % (100 * cc["ladron"])),
                      flush=True)
            elif cur is not None:
                ce, cc = m["curriculo"], m["competencia"]
                vl = ce.get("valores") or {}
                print("     criterios del nivel: " + (" · ".join("%s %s (meta %s)" % (k, "--" if vl.get(k) is None else
                      ("%.3f" % vl[k] if isinstance(vl[k], float) else vl[k]), u) for k, u in (ce.get("criterios") or {}).items())
                      or "nivel final"), flush=True)
                print("     NIVEL %d · %s | rendición %s / %.0f %% (%d de %d partidas, %.1f M pasos en el nivel) | cenit %s | "
                      "DOMINIO dron %s · ladrón %s · otras fallas %s" % (
                          ce["nivel"], ce["nombre"], "--" if ce["exito"] is None else "%.1f %%" % (100 * ce["exito"]),
                          100 * ce["umbral"], ce["partidas"], ce["ventana"], ce["pasos_en_nivel"] / 1e6,
                          "--" if ce["exito_cenit"] is None else "%.0f %%" % (100 * ce["exito_cenit"]),
                          "--" if cc["dron"] is None else "%.0f %%" % (100 * cc["dron"]),
                          "--" if cc["ladron"] is None else "%.0f %%" % (100 * cc["ladron"]),
                          "--" if cc["otros"] is None else "%.0f %%" % (100 * cc["otros"])), flush=True)
                for k, r_ in sorted((ce.get("por_nivel") or {}).items()):
                    if k == ce["nivel"] or k == N_NIVELES - 1:
                        print(texto_resumen_nivel(k, r_), flush=True)
            print("it %5d | %7.1f M pasos | %5d p/s | intensidad %.2f | CUMPLIDA %s (1 muro %s) | perdido %s | alcanzado %s | peatón %s | panel %s | sale %s | re-adquiridos %s | jitter %s/s, esfuerzo %s/s | entropía %.2f | partida %s s | gimbal mín %s°"
                  % (it, pasos / 1e6, m["pasos_s"], m["nivel"], f2(e.get("cumplida")), f2(e.get("cumplida_un_muro")), f2(e.get("perdido")), f2(e.get("alcanzado")),
                     f2(e.get("peaton")), f2(e.get("panel")), f2(e.get("fuera")), f2(e.get("redescubre")), f3(c.get("jitter")),
                     f3(c.get("esfuerzo")), m["dron"]["entropia"], f2(e.get("t_ep")), f2(e.get("gmb_min"))), flush=True)


# ======================================================================= principal
def main():
    global SALIDA, MASTER, MODELOS
    ap = argparse.ArgumentParser()
    ap.add_argument("--continuar", action="store_true", help="retomar <dir-master>/ultimo.zip (lo hace solo si existe)")
    ap.add_argument("--desde", default=None, help="modelo SB3 de la V15 (.zip) del que arranca la V16 "
                                                     "(por defecto, el checkpoint más nuevo de modelos_v15/)")
    ap.add_argument("--desde-json", default=None, help="arrancar del actor exportado para la Jetson (si no hay .zip)")
    ap.add_argument("--congelar", choices=["viejas", "capa", "nada"], default="viejas",
                    help="viejas: congela en la 1.a capa del actor las conexiones de las 192 entradas de la V15 (las 3 "
                         "nuevas aprenden); capa: la 1.a capa entera (como la V12); nada: todo aprende")
    ap.add_argument("--pasos", type=float, default=1e9)
    ap.add_argument("--envs", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-4, help="tasa de aprendizaje del afinado")
    ap.add_argument("--checkpoint", type=float, default=1e6, help="cada cuántos pasos se guarda un checkpoint")
    ap.add_argument("--ventana", type=int, default=1000, help="partidas que se promedian en las métricas de custodia")
    ap.add_argument("--hilos", type=int, default=8, help="hilos de torch")
    ap.add_argument("--semilla", type=int, default=None)
    ap.add_argument("--repeticiones", type=int, default=5, help="cada cuántas iteraciones se graban repeticiones e hitos "
                                                                 "para el visor (0 = nunca, para corridas de prueba)")
    ap.add_argument("--set", action="append", default=[], help="NOMBRE=VALOR: cambia una constante de entorno.py "
                                                               "(comparaciones con y sin un término)")
    ap.add_argument("--salida", default=SALIDA)
    ap.add_argument("--dir-master", default=MASTER)
    ap.add_argument("--dir-modelos", default=MODELOS)
    a = ap.parse_args()
    SALIDA, MASTER, MODELOS = a.salida, a.dir_master, a.dir_modelos
    import entorno as E_
    for kv in a.set:
        k, v = kv.split("=", 1)
        viejo = getattr(E_, k)
        setattr(E_, k, v if isinstance(viejo, str) else (bool(float(v)) if isinstance(viejo, bool) else type(viejo)(float(v))))
        print("constante cambiada: %s = %s" % (k, getattr(E_, k)), flush=True)
    Maestro.cada_rep = a.repeticiones
    sin_ahorro_de_energia()
    torch.set_num_threads(a.hilos)
    for d in (os.path.join(SALIDA, "hitos"), MODELOS, os.path.join(MASTER, "checkpoints")):
        os.makedirs(d, exist_ok=True)
    ruta_ultimo = os.path.join(MASTER, "ultimo.zip")
    ruta_persona = os.path.join(MASTER, "ladron_congelado.pt")
    semilla = a.semilla if a.semilla is not None else int(time.time()) % 10000
    EntornoDronPersona.nivel_inicial = NIVEL_V16

    metricas, it, t_previo, hitos = [], 0, 0.0, []
    continuar = a.continuar or (a.desde is None and a.desde_json is None and os.path.exists(ruta_ultimo))
    if continuar:
        red_p = red_ladron(ruta_persona)
        venv = VecDron(a.envs, semilla, red_p)
        modelo = PPO.load(ruta_ultimo, env=venv, device="cpu", custom_objects={"learning_rate": a.lr})
        est = json.load(open(os.path.join(MASTER, "estado_entrenamiento.json"), encoding="utf-8"))
        it, t_previo = est["it"], est["seg"]
        venv.set_attr("nivel", est.get("nivel", 0.0))
        ruta_m = os.path.join(SALIDA, "metricas.json")
        metricas = [m for m in json.load(open(ruta_m, encoding="utf-8")) if m["it"] <= it] if os.path.exists(ruta_m) else []
        ruta_h = os.path.join(SALIDA, "hitos", "lista.json")
        hitos = [h for h in json.load(open(ruta_h, encoding="utf-8")) if h["it"] <= it] if os.path.exists(ruta_h) else []
        print("continuando desde la iteración %d (%.1f M pasos)" % (it, modelo.num_timesteps / 1e6), flush=True)
    else:
        archivar_salida_previa()
        origen = a.desde or (None if a.desde_json else ultimo_checkpoint(ORIGEN_PREVIO))
        red_p = red_ladron(os.path.join(ORIGEN_PREVIO, "ladron_congelado.pt"))
        torch.save(red_p.state_dict(), ruta_persona)
        venv = VecDron(a.envs, semilla, red_p)
        if origen:
            modelo = desde_v15_zip(origen, venv, a.lr)
            desde = origen
        else:
            ruta_json = a.desde_json or os.path.join(MODELOS, "dron_politica.json")
            modelo, pasos_json = desde_json(ruta_json, venv, a.lr)
            desde = "%s (%s pasos; crítico nuevo)" % (ruta_json, pasos_json)
        modelo.num_timesteps = 0
        modelo.save(os.path.join(MASTER, "base_%s.zip" % VERSION.lower()))
        guardar_json(os.path.join(MASTER, "origen.json"), {"desde": str(desde).replace("\\", "/"),
                                                           "fecha": time.strftime("%Y-%m-%d %H:%M")})
        print("%s · arranca desde %s · entradas %d -> %d (las nuevas en cero)" % (VERSION, desde, OBS_PREVIA, OBS_DRON),
              flush=True)
    for prm in red_p.parameters():
        prm.requires_grad_(False)
    if a.congelar == "viejas":
        congelar_capas_inferiores(modelo, OBS_PREVIA)
    elif a.congelar == "capa":
        congelar_capas_fisicas(modelo)
    curriculo = CurriculoV16(venv, a.ventana)
    venv.env.reset(np.ones(venv.num_envs, bool))
    cbs = [CheckpointCallback(save_freq=max(int(a.checkpoint // a.envs), 1), save_path=os.path.join(MASTER, "checkpoints"),
                              name_prefix="dron_master"),
           curriculo, Maestro(venv, red_p, a.pasos, metricas, it, t_previo, hitos, curriculo)]
    print(VERSION + " · %s · Stable-Baselines3 PPO · %d entornos · objetivo %.0f M pasos · checkpoint cada %.1f M · "
          "congelar: %s · autor: %s" % (NOMBRE_V16, a.envs, a.pasos / 1e6, a.checkpoint / 1e6, a.congelar, AUTOR), flush=True)
    modelo.learn(total_timesteps=int(a.pasos), callback=cbs, reset_num_timesteps=not continuar)


if __name__ == "__main__":
    main()
