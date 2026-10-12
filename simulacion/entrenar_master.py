# -*- coding: utf-8 -*-
"""
Versión Master del entrenamiento: Stable-Baselines3 (PPO) con transferencia de aprendizaje y currículo continuo.

Arquitectura de control (la red NO estabiliza nada):
    observación (sensores + mapa SLAM + memoria) ─▶ política PPO (Jetson) ─▶ acción táctica (10 clases)
        ─▶ lógica de la Jetson: consignas de velocidad X/Y/Z, tasa de guiñada y ángulo del gimbal
        ─▶ MAVLink ─▶ PID de ArduPilot en la Pixhawk (control.AutopilotoArduPilot: PSC + ATC, roll/pitch/yaw/Z)
        ─▶ PWM AUX1 ─▶ PID del gimbal BaseCam (control.GimbalBaseCam: 30°/s, -60°..+15°)

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

from entorno import CLASES, DT, N_ACC_PERSONA, OBS_DRON, OBS_PERSONA, EntornoDronPersona
from entrenar import ActorCritico, actuar, grabar_partida, guardar_json, sin_ahorro_de_energia
from mision import grabar_mision

SALIDA, MODELOS, MASTER = "salida", "modelos", "modelos_master"
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
        self.vaciar()

    def vaciar(self):
        self.fin, self.jit, self.esf, self.mando = [], 0.0, 0.0, 0
        self.cuenta_dec = np.zeros(len(CLASES))
        self.cuenta_busq = np.zeros(len(CLASES))

    def reset(self):
        return self.env.obs_dron().astype(np.float32)

    def step_async(self, actions):
        self.acciones = np.asarray(actions).astype(int)

    def step_wait(self):
        e = self.env
        ap, _, _, _ = actuar(self.red_p, e.obs_persona())
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
        infos = [{} for _ in range(self.num_envs)]
        for i in np.where(done)[0]:
            falla = info["choque"][i] or info["fuera"][i] or info["panel"][i] or info["perdido"][i] or info["no_encontrado"][i]
            infos[i]["terminal_observation"] = obs[i].copy()
            infos[i]["TimeLimit.truncated"] = bool(info["tiempo"][i] and not falla and not info["exito"][i])
            self.fin.append((bool(info["choque_ladron"][i]), bool(info["choque_peaton"][i]), bool(info["panel"][i]),
                             bool(info["fuera"][i]), self.ep_vis[i] / self.ep_len[i], self.ep_man[i], self.ep_ret[i],
                             int(info["peatones"][i]), bool(info["exito"][i]), bool(info["perdido"][i]),
                             bool(info["no_encontrado"][i]), self.ep_pierde[i], self.ep_recupera[i], self.ep_descubre[i]))
        for a in (self.ep_ret, self.ep_man, self.ep_vis, self.ep_len, self.ep_pierde, self.ep_recupera, self.ep_descubre):
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
    return {"n": len(lst), "alcanzado": float(arr[:, 0].mean()),
            "peaton": float(arr[con_pea, 1].mean()) if con_pea.any() else None,
            "panel": float(arr[:, 2].mean()), "fuera": float(arr[:, 3].mean()), "vista": float(arr[:, 4].mean()),
            "maniobras": float(arr[:, 5].mean()), "recompensa": float(arr[:, 6].mean()), "cumplida": float(arr[:, 8].mean()),
            "perdido": float(arr[:, 9].mean()), "no_encontrado": float(arr[:, 10].mean()), "perdidas": float(arr[:, 11].mean()),
            "recuperaciones": float(arr[:, 12].mean()), "redescubre": float(arr[:, 13].mean())}


class Maestro(BaseCallback):
    """Cada iteración (un rollout de 128 pasos x N entornos): métricas para el visor, currículo y, cada tanto,
    repeticiones, hitos, el último modelo y los pesos para la Jetson."""

    def __init__(self, venv, red_p, objetivo, metricas, iteracion, t_previo, hitos):
        super().__init__()
        self.venv, self.red_p, self.objetivo = venv, red_p, objetivo
        self.metricas, self.it, self.t_previo, self.hitos = metricas, iteracion, t_previo, hitos
        self.t0 = self.ti = time.time()
        self.pasos_ant = None
        self.historial = []

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
        control = ({"jitter": v.jit / seg, "esfuerzo": v.esf / seg, "total": (v.jit + v.esf) / seg, "seg_mando": round(v.mando * DT, 1)}
                   if v.mando else None)
        lg = self.model.logger.name_to_value
        m = {"it": self.it, "pasos": pasos, "seg": round(self.t_previo + time.time() - self.t0, 1), "adv": resumen(v.fin),
             "control": control, "nivel": round(float(v.env.nivel), 3),
             "acciones": [round(float(x), 4) for x in v.cuenta_dec / max(v.cuenta_dec.sum(), 1)],
             "acciones_busqueda": [round(float(x), 4) for x in v.cuenta_busq / max(v.cuenta_busq.sum(), 1)],
             "dron": {"l_pi": float(lg.get("train/policy_gradient_loss", 0.0)), "l_v": float(lg.get("train/value_loss", 0.0)),
                      "entropia": -float(lg.get("train/entropy_loss", 0.0))},
             "pasos_s": int(paso_it / max(dt_it, 1e-6)), "motor": "Stable-Baselines3 PPO", "autor": AUTOR}
        self.metricas.append(m)
        # CURRÍCULO: el nivel sube (o baja) despacio según la tasa de misiones cumplidas de las últimas iteraciones
        if m["adv"]:
            self.historial.append(m["adv"]["cumplida"])
        if len(self.historial) >= 10:
            meta = float(np.clip((np.mean(self.historial[-10:]) - 0.25) / 0.35, 0.0, 1.0))
            v.set_attr("nivel", float(np.clip(v.env.nivel + 0.01 * np.sign(meta - v.env.nivel), 0.0, 1.0)))
        v.vaciar()
        it = self.it
        if it % 2 == 0 or it < 5:
            guardar_json(os.path.join(SALIDA, "metricas.json"), self.metricas)
            guardar_json(os.path.join(SALIDA, "estado.json"), {"it": it, "pasos": pasos, "seg": m["seg"], "pasos_s": m["pasos_s"],
                                                               "objetivo": self.objetivo, "t": time.time(), "nivel": m["nivel"]})
        pol = PoliticaSB3(self.model)
        if it % 5 == 0 or it == 1:
            guardar_json(os.path.join(SALIDA, "replay_adv.json"), grabar_partida(pol, self.red_p, True, it, it, pasos))
            guardar_json(os.path.join(SALIDA, "replay_mision.json"), grabar_mision(pol, self.red_p, actuar, it, pasos, it + 2))
        if it % 20 == 0 or it == 1:
            for tipo, f in (("partida", lambda s: grabar_partida(pol, self.red_p, True, s, it, pasos)),
                            ("mision", lambda s: grabar_mision(pol, self.red_p, actuar, it, pasos, s))):
                nombre = "it%05d_%s.json" % (it, tipo)
                guardar_json(os.path.join(SALIDA, "hitos", nombre), f(1000 + it if tipo == "partida" else 2000 + it))
                self.hitos.append({"archivo": nombre, "it": it, "pasos": pasos, "adversaria": True, "mision": tipo == "mision"})
            guardar_json(os.path.join(SALIDA, "hitos", "lista.json"), self.hitos)
            self.model.save(os.path.join(MASTER, "ultimo.zip"))
            guardar_json(os.path.join(MASTER, "estado_entrenamiento.json"), {"it": it, "pasos": pasos, "seg": m["seg"], "nivel": m["nivel"]})
            guardar_json(os.path.join(MODELOS, "dron_politica.json"), exportar(self.model, iteracion=it, pasos=pasos))
        if it % 5 == 0 or it < 5:
            e = m["adv"] or {}
            c = control or {}
            f2 = lambda x: "--" if x is None else "%.2f" % x
            f3 = lambda x: "--" if x is None else "%.4f" % x
            print("it %5d | %7.1f M pasos | %5d p/s | nivel %.2f | CUMPLIDA %s | perdido %s | alcanzado %s | peatón %s | panel %s | sale %s | re-adquiridos %s | jitter %s/s, esfuerzo %s/s | entropía %.2f"
                  % (it, pasos / 1e6, m["pasos_s"], m["nivel"], f2(e.get("cumplida")), f2(e.get("perdido")), f2(e.get("alcanzado")),
                     f2(e.get("peaton")), f2(e.get("panel")), f2(e.get("fuera")), f2(e.get("redescubre")), f3(c.get("jitter")),
                     f3(c.get("esfuerzo")), m["dron"]["entropia"]), flush=True)


# ======================================================================= principal
def main():
    global SALIDA, MASTER, MODELOS
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="modelos/ultimo.pt", help="red PPO propia (.pt) de la que sale la base SB3")
    ap.add_argument("--continuar", action="store_true", help="retomar modelos_master/ultimo.zip")
    ap.add_argument("--pasos", type=float, default=1e9)
    ap.add_argument("--envs", type=int, default=512)
    ap.add_argument("--lr", type=float, default=2e-4, help="tasa de aprendizaje del afinado (menor que la de origen)")
    ap.add_argument("--checkpoint", type=float, default=1e6, help="cada cuántos pasos se guarda un checkpoint")
    ap.add_argument("--salida", default=SALIDA)
    ap.add_argument("--dir-master", default=MASTER)
    ap.add_argument("--dir-modelos", default=MODELOS)
    a = ap.parse_args()
    SALIDA, MASTER, MODELOS = a.salida, a.dir_master, a.dir_modelos
    sin_ahorro_de_energia()
    torch.set_num_threads(8)
    for d in (os.path.join(SALIDA, "hitos"), MODELOS, os.path.join(MASTER, "checkpoints")):
        os.makedirs(d, exist_ok=True)
    ruta_base, ruta_ultimo = os.path.join(MASTER, "base_v9.zip"), os.path.join(MASTER, "ultimo.zip")
    ruta_persona = os.path.join(MASTER, "ladron_congelado.pt")

    metricas, it, t_previo, hitos = [], 0, 0.0, []
    if a.continuar:
        red_p = ActorCritico(OBS_PERSONA, N_ACC_PERSONA)
        red_p.load_state_dict(torch.load(ruta_persona, weights_only=False))
        venv = VecDron(a.envs, int(time.time()) % 10000, red_p)
        modelo = PPO.load(ruta_ultimo, env=venv, device="cpu")
        est = json.load(open(os.path.join(MASTER, "estado_entrenamiento.json"), encoding="utf-8"))
        it, t_previo = est["it"], est["seg"]
        venv.set_attr("nivel", est.get("nivel", 0.0))
        metricas = [m for m in json.load(open(os.path.join(SALIDA, "metricas.json"), encoding="utf-8")) if m["it"] <= it]
        ruta_h = os.path.join(SALIDA, "hitos", "lista.json")
        hitos = [h for h in json.load(open(ruta_h, encoding="utf-8")) if h["it"] <= it] if os.path.exists(ruta_h) else []
        print("continuando desde la iteración %d (%.1f M pasos)" % (it, modelo.num_timesteps / 1e6), flush=True)
    else:
        ck = torch.load(a.base, weights_only=False)
        red_p = ActorCritico(OBS_PERSONA, N_ACC_PERSONA)
        red_p.load_state_dict(ck["persona"])
        torch.save(red_p.state_dict(), ruta_persona)
        venv = VecDron(a.envs, 7, red_p)
        crear_base(a.base, venv, ruta_base, a.lr)
        modelo = PPO.load(ruta_base, env=venv, device="cpu", custom_objects={"learning_rate": a.lr})
    for prm in red_p.parameters():
        prm.requires_grad_(False)
    congelar_capas_inferiores(modelo)
    cbs = [CheckpointCallback(save_freq=max(int(a.checkpoint // a.envs), 1), save_path=os.path.join(MASTER, "checkpoints"),
                              name_prefix="dron_master"),
           Maestro(venv, red_p, a.pasos, metricas, it, t_previo, hitos)]
    print("Versión Master · Stable-Baselines3 PPO · %d entornos · objetivo %.0f M pasos · checkpoint cada %.1f M · autor: %s"
          % (a.envs, a.pasos / 1e6, a.checkpoint / 1e6, AUTOR), flush=True)
    modelo.learn(total_timesteps=int(a.pasos), callback=cbs, reset_num_timesteps=not a.continuar)


if __name__ == "__main__":
    main()
