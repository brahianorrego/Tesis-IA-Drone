# -*- coding: utf-8 -*-
"""
Entrenamiento multiagente por refuerzo (PPO) del dron y la persona, en autojuego.

El dron y el ladrón aprenden a la vez con objetivos opuestos (como Baker et al., 2020): el dron
gana manteniendo al ladrón en la vista sin dejarse alcanzar; el ladrón gana escondiéndose (detrás
de los paneles) o alcanzándolo. Los peatones guionados no juegan: son obstáculos que el dron debe
esquivar sin perder de vista al ladrón.

Salidas (las lee el visor):
  salida/metricas.json          curvas de aprendizaje por iteración
  salida/estado.json            progreso actual
  salida/replay_adv.json        última partida contra la persona adversaria
  salida/replay_guion.json      última partida contra un peatón normal
  salida/hitos/*.json           partidas guardadas a lo largo del entrenamiento
  modelos/                      redes (torch) y el dron exportado en JSON para la Jetson

Uso:  python entrenar.py [--pasos 200e6] [--continuar]
"""
import argparse
import json
import os
import time

import numpy as np
import torch
import torch.nn as nn

from entorno import (CLASES, GUIONES, N_ACC_PERSONA, OBS_DRON, OBS_PERSONA, PASOS_EPISODIO, EntornoDronPersona,
                     resultado_de)
from mision import grabar_mision

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "salida")
MODELOS = os.path.join(AQUI, "modelos")


def sin_ahorro_de_energia():
    """Windows manda los procesos en segundo plano a los núcleos de eficiencia (EcoQoS) y el
    entrenamiento corre ~3 veces más lento. Esto lo desactiva solo para este proceso."""
    if os.name != "nt":
        return
    try:
        import ctypes

        class Estado(ctypes.Structure):
            _fields_ = [("Version", ctypes.c_ulong), ("ControlMask", ctypes.c_ulong), ("StateMask", ctypes.c_ulong)]
        e = Estado(1, 0x1, 0x0)          # PROCESS_POWER_THROTTLING_EXECUTION_SPEED: apagado
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = ctypes.c_void_p          # HANDLE de 64 bits (sin esto se trunca)
        k32.SetProcessInformation.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong]
        k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        yo = k32.GetCurrentProcess()
        ok = k32.SetProcessInformation(yo, 4, ctypes.byref(e), ctypes.sizeof(e))
        k32.SetPriorityClass(yo, 0x00008000)   # ABOVE_NORMAL
        print("[energia] ahorro de energía del proceso desactivado" if ok else "[energia] no se pudo desactivar EcoQoS", flush=True)
    except Exception as ex:
        print("[energia] %r" % ex, flush=True)


def guardar_json(ruta, datos):
    """Escritura atómica. En Windows el reemplazo falla si el visor está leyendo el archivo
    justo en ese instante: se reintenta y, si sigue ocupado, se omite (nunca detiene el entrenamiento)."""
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, separators=(",", ":"))
    for intento in range(20):
        try:
            os.replace(tmp, ruta)
            return True
        except PermissionError:
            time.sleep(0.05 * (intento + 1))
    print("[aviso] no se pudo actualizar %s (archivo ocupado); se reintenta en la próxima iteración" % ruta, flush=True)
    return False


class ActorCritico(nn.Module):

    def __init__(self, n_obs, n_acc, ancho=128):
        super().__init__()
        self.pi = nn.Sequential(nn.Linear(n_obs, ancho), nn.Tanh(), nn.Linear(ancho, ancho), nn.Tanh(),
                                nn.Linear(ancho, n_acc))
        self.v = nn.Sequential(nn.Linear(n_obs, ancho), nn.Tanh(), nn.Linear(ancho, ancho), nn.Tanh(),
                               nn.Linear(ancho, 1))
        nn.init.orthogonal_(self.pi[-1].weight, 0.01)
        nn.init.zeros_(self.pi[-1].bias)

    def dist(self, obs):
        return torch.distributions.Categorical(logits=self.pi(obs))

    def exportar(self):
        capas = [m for m in self.pi if isinstance(m, nn.Linear)]
        return {"capas": [{"W": c.weight.detach().numpy().round(6).tolist(),
                           "b": c.bias.detach().numpy().round(6).tolist()} for c in capas],
                "activacion": "tanh", "clases": CLASES}


class PPO(object):

    def __init__(self, red, lr=3e-4, clip=0.2, ent=0.01, vf=0.5, epocas=4, minilotes=8):
        self.red = red
        self.opt = torch.optim.Adam(red.parameters(), lr=lr, eps=1e-5)
        self.clip, self.ent, self.vf, self.epocas, self.minilotes = clip, ent, vf, epocas, minilotes

    def actualizar(self, obs, acc, logp_v, ventaja, retorno, mascara):
        idx = np.where(mascara)[0]
        if len(idx) < 256:
            return {}
        obs, acc, logp_v = obs[idx], acc[idx], logp_v[idx]
        ventaja, retorno = ventaja[idx], retorno[idx]
        ventaja = (ventaja - ventaja.mean()) / (ventaja.std() + 1e-8)
        o = torch.as_tensor(obs, dtype=torch.float32)
        a = torch.as_tensor(acc)
        lv = torch.as_tensor(logp_v, dtype=torch.float32)
        adv = torch.as_tensor(ventaja, dtype=torch.float32)
        ret = torch.as_tensor(retorno, dtype=torch.float32)
        n = len(idx)
        tam = max(n // self.minilotes, 64)
        stats = []
        for _ in range(self.epocas):
            perm = torch.randperm(n)
            for i in range(0, n, tam):
                j = perm[i:i + tam]
                d = self.red.dist(o[j])
                logp = d.log_prob(a[j])
                razon = torch.exp(logp - lv[j])
                l_pi = -torch.min(razon * adv[j], torch.clamp(razon, 1 - self.clip, 1 + self.clip) * adv[j]).mean()
                l_v = ((self.red.v(o[j]).squeeze(-1) - ret[j]) ** 2).mean()
                entropia = d.entropy().mean()
                perdida = l_pi + self.vf * l_v - self.ent * entropia
                self.opt.zero_grad()
                perdida.backward()
                nn.utils.clip_grad_norm_(self.red.parameters(), 0.5)
                self.opt.step()
                stats.append((l_pi.item(), l_v.item(), entropia.item()))
        s = np.mean(stats, axis=0)
        return {"l_pi": float(s[0]), "l_v": float(s[1]), "entropia": float(s[2])}


def gae(recompensas, valores, dones, ultimo_valor, gamma=0.99, lam=0.95):
    T = len(recompensas)
    ventaja = np.zeros_like(recompensas)
    ult = 0.0
    for t in reversed(range(T)):
        siguiente = ultimo_valor if t == T - 1 else valores[t + 1]
        no_fin = 1.0 - dones[t]
        delta = recompensas[t] + gamma * siguiente * no_fin - valores[t]
        ult = delta + gamma * lam * no_fin * ult
        ventaja[t] = ult
    return ventaja, ventaja + valores


@torch.no_grad()
def actuar(red, obs, codicioso=False):
    o = torch.as_tensor(obs, dtype=torch.float32)
    d = red.dist(o)
    a = d.probs.argmax(-1) if codicioso else d.sample()
    return a.numpy(), d.log_prob(a).numpy(), red.v(o).squeeze(-1).numpy(), d.probs.numpy()


def grabar_partida(red_d, red_p, adversaria, semilla, iteracion, pasos_tot):
    env = EntornoDronPersona(1, semilla=semilla)
    paneles = env.paneles(0)
    cuadros = []
    resultado = "tiempo"
    maniobras = 0
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
    return {"iteracion": iteracion, "pasos": pasos_tot, "adversaria": True, "guion": None, "paneles": paneles,
            "resultado": resultado, "maniobras": maniobras, "dt": 0.1, "cuadros": cuadros}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasos", type=float, default=200e6)
    ap.add_argument("--envs", type=int, default=512)
    ap.add_argument("--horizonte", type=int, default=128)
    ap.add_argument("--continuar", action="store_true")
    ap.add_argument("--hito-cada", type=int, default=20)
    ap.add_argument("--desde", help="arrancar con los pesos de otro entrenamiento (.pt); si el dron tiene "
                                    "acciones nuevas, se agregan a su capa de salida")
    a = ap.parse_args()
    sin_ahorro_de_energia()
    torch.set_num_threads(8)
    os.makedirs(os.path.join(SALIDA, "hitos"), exist_ok=True)
    os.makedirs(MODELOS, exist_ok=True)

    red_d, red_p = ActorCritico(OBS_DRON, len(CLASES)), ActorCritico(OBS_PERSONA, N_ACC_PERSONA)
    ppo_d, ppo_p = PPO(red_d), PPO(red_p)
    metricas, iteracion, pasos_tot, t_previo = [], 0, 0, 0.0
    ruta_ckpt = os.path.join(MODELOS, "ultimo.pt")
    if a.desde and not a.continuar:
        ck = torch.load(a.desde, weights_only=False)
        red_p.load_state_dict(ck["persona"])
        viejo, nuevo = ck["dron"], red_d.state_dict()
        for k, v in viejo.items():
            if v.shape == nuevo[k].shape:
                nuevo[k] = v
            else:                                   # capa de salida con acciones nuevas: se conservan las viejas
                nuevo[k][:v.shape[0]] = v
                nuevo[k][v.shape[0]:] = 0.0 if v.dim() == 1 else nuevo[k][v.shape[0]:] * 0.01
        red_d.load_state_dict(nuevo)
        print("pesos iniciales tomados de %s (iteración %d)" % (a.desde, ck["iteracion"]), flush=True)
    if a.continuar and os.path.exists(ruta_ckpt):
        ck = torch.load(ruta_ckpt, weights_only=False)
        red_d.load_state_dict(ck["dron"]); red_p.load_state_dict(ck["persona"])
        ppo_d.opt.load_state_dict(ck["opt_d"]); ppo_p.opt.load_state_dict(ck["opt_p"])
        iteracion, pasos_tot, t_previo = ck["iteracion"], ck["pasos"], ck.get("tiempo", 0.0)
        with open(os.path.join(SALIDA, "metricas.json"), encoding="utf-8") as f:
            metricas = [m for m in json.load(f) if m["it"] <= iteracion]   # descartar lo posterior al punto guardado
        print("continuando desde la iteración %d (%.1f M pasos)" % (iteracion, pasos_tot / 1e6))

    N, T = a.envs, a.horizonte
    env = EntornoDronPersona(N, semilla=iteracion + 7)
    ep_ret = np.zeros(N)
    ep_man = np.zeros(N)
    ep_dmin = np.full(N, 99.0)
    ep_vis = np.zeros(N)
    ep_len = np.zeros(N)
    ep_pierde, ep_recupera = np.zeros(N), np.zeros(N)
    hitos = []
    ruta_hitos = os.path.join(SALIDA, "hitos", "lista.json")
    if os.path.exists(ruta_hitos):
        with open(ruta_hitos, encoding="utf-8") as f:
            hitos = [h for h in json.load(f) if h["it"] <= iteracion]
    t0 = time.time()

    while pasos_tot < a.pasos:
        ti = time.time()
        B = lambda *s: np.zeros((T, N) + s, np.float32)
        od_b, op_b = B(OBS_DRON), B(OBS_PERSONA)
        ad_b, ap_b = np.zeros((T, N), np.int64), np.zeros((T, N), np.int64)
        lpd_b, lpp_b, vd_b, vp_b, rd_b, rp_b, done_b = B(), B(), B(), B(), B(), B(), B()
        md_b, mp_b = np.zeros((T, N), bool), np.zeros((T, N), bool)
        fin = []
        for t in range(T):
            od, op = env.obs_dron(), env.obs_persona()
            md, mp = env.mascara_decision(), ~env.tactico.copy()     # el ladrón aprendido solo entrena en sus partidas
            ad, lpd, vd, _ = actuar(red_d, od)
            app, lpp, vp, _ = actuar(red_p, op)
            rd, rp, done, info = env.step(ad, app)
            od_b[t], op_b[t], ad_b[t], ap_b[t] = od, op, ad, app
            lpd_b[t], lpp_b[t], vd_b[t], vp_b[t] = lpd, lpp, vd, vp
            rd_b[t], rp_b[t], done_b[t], md_b[t], mp_b[t] = rd, rp, done, md, mp
            ep_ret += rd
            ep_man += info["inicia"]
            ep_dmin = np.minimum(ep_dmin, info["dist"])
            ep_vis += info["visto"]
            ep_len += 1
            ep_pierde += info["pierde"]
            ep_recupera += info["recupera"]
            for i in np.where(done)[0]:
                fin.append((bool(info["choque_ladron"][i]), bool(info["choque_peaton"][i]), bool(info["panel"][i]),
                            bool(info["fuera"][i]), ep_vis[i] / ep_len[i], ep_man[i], ep_ret[i], int(info["peatones"][i]),
                            bool(info["exito"][i]), bool(info["perdido"][i]), bool(info["no_encontrado"][i]),
                            ep_pierde[i], ep_recupera[i]))
            ep_ret[done] = 0.0
            ep_man[done] = 0.0
            ep_dmin[done] = 99.0
            ep_vis[done] = 0.0
            ep_len[done] = 0.0
            ep_pierde[done] = 0.0
            ep_recupera[done] = 0.0
        _, _, ultd, _ = actuar(red_d, env.obs_dron())
        _, _, ultp, _ = actuar(red_p, env.obs_persona())
        advd, retd = gae(rd_b, vd_b, done_b, ultd)
        advp, retp = gae(rp_b, vp_b, done_b, ultp)
        aplanar = lambda x: x.reshape((T * N,) + x.shape[2:])
        sd = ppo_d.actualizar(aplanar(od_b), aplanar(ad_b), aplanar(lpd_b), aplanar(advd), aplanar(retd), aplanar(md_b))
        sp = ppo_p.actualizar(aplanar(op_b), aplanar(ap_b), aplanar(lpp_b), aplanar(advp), aplanar(retp), aplanar(mp_b))
        iteracion += 1
        pasos_tot += T * N
        dt_it = time.time() - ti

        def resumen(lst):
            if not lst:
                return None
            arr = np.array(lst, dtype=float)
            con_pea = arr[:, 7] > 0
            return {"n": len(lst), "alcanzado": float(arr[:, 0].mean()),
                    "peaton": float(arr[con_pea, 1].mean()) if con_pea.any() else None,
                    "panel": float(arr[:, 2].mean()), "fuera": float(arr[:, 3].mean()),
                    "vista": float(arr[:, 4].mean()), "maniobras": float(arr[:, 5].mean()),
                    "recompensa": float(arr[:, 6].mean()), "cumplida": float(arr[:, 8].mean()),
                    "perdido": float(arr[:, 9].mean()), "no_encontrado": float(arr[:, 10].mean()),
                    "perdidas": float(arr[:, 11].mean()), "recuperaciones": float(arr[:, 12].mean())}
        dec = aplanar(ad_b)[aplanar(md_b)]
        frec = np.bincount(dec, minlength=len(CLASES)) / max(len(dec), 1)
        m = {"it": iteracion, "pasos": pasos_tot, "seg": round(t_previo + time.time() - t0, 1),
             "adv": resumen(fin),
             "acciones": [round(float(x), 4) for x in frec], "dron": sd, "persona": sp,
             "pasos_s": int(T * N / dt_it)}
        metricas.append(m)
        if iteracion % 2 == 0 or iteracion < 5:
            guardar_json(os.path.join(SALIDA, "metricas.json"), metricas)
            guardar_json(os.path.join(SALIDA, "estado.json"), {"it": iteracion, "pasos": pasos_tot, "seg": m["seg"],
                                                               "pasos_s": m["pasos_s"], "objetivo": a.pasos, "t": time.time()})
        if iteracion % 5 == 0 or iteracion == 1:
            guardar_json(os.path.join(SALIDA, "replay_adv.json"), grabar_partida(red_d, red_p, True, iteracion, iteracion, pasos_tot))
            guardar_json(os.path.join(SALIDA, "replay_mision.json"), grabar_mision(red_d, red_p, actuar, iteracion, pasos_tot, iteracion + 2))
        if iteracion % a.hito_cada == 0 or iteracion == 1:
            nombre = "it%05d_partida.json" % iteracion
            guardar_json(os.path.join(SALIDA, "hitos", nombre), grabar_partida(red_d, red_p, True, 1000 + iteracion, iteracion, pasos_tot))
            hitos.append({"archivo": nombre, "it": iteracion, "pasos": pasos_tot, "adversaria": True, "mision": False})
            nombre = "it%05d_mision.json" % iteracion
            guardar_json(os.path.join(SALIDA, "hitos", nombre), grabar_mision(red_d, red_p, actuar, iteracion, pasos_tot, 2000 + iteracion))
            hitos.append({"archivo": nombre, "it": iteracion, "pasos": pasos_tot, "adversaria": True, "mision": True})
            guardar_json(ruta_hitos, hitos)
            torch.save({"dron": red_d.state_dict(), "persona": red_p.state_dict(), "opt_d": ppo_d.opt.state_dict(),
                        "opt_p": ppo_p.opt.state_dict(), "iteracion": iteracion, "pasos": pasos_tot,
                        "tiempo": t_previo + time.time() - t0}, ruta_ckpt)
            guardar_json(os.path.join(MODELOS, "dron_politica.json"), dict(red_d.exportar(), iteracion=iteracion, pasos=pasos_tot))
        if iteracion % 5 == 0 or iteracion < 5:
            e = m["adv"] or {}
            fmt = lambda v: "--" if v is None else "%.2f" % v
            print("it %5d | %6.1f M pasos | %5d p/s | CUMPLIDA %s | perdido %s | no encontrado %s | pérdidas %s, recuperadas %s | vista %s | lo alcanza: ladrón %s, peatón %s | panel %s | sale %s | maniobras %s | acciones %s"
                  % (iteracion, pasos_tot / 1e6, m["pasos_s"], fmt(e.get("cumplida")), fmt(e.get("perdido")), fmt(e.get("no_encontrado")), fmt(e.get("perdidas")), fmt(e.get("recuperaciones")),
                     fmt(e.get("vista")), fmt(e.get("alcanzado")), fmt(e.get("peaton")),
                     fmt(e.get("panel")), fmt(e.get("fuera")), fmt(e.get("maniobras")), m["acciones"]), flush=True)


if __name__ == "__main__":
    main()
