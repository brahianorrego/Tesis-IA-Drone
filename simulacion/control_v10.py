# -*- coding: utf-8 -*-
"""
Controladores de bajo nivel: el modelo de lo que YA hace el hardware. La red neuronal no estabiliza nada.

Cadena real del dron (y de la simulación):

    política PPO (Jetson Orin Nano) ──acción táctica──▶ lógica de la Jetson ──consignas──▶
        · MAVLink SET_POSITION_TARGET_LOCAL_NED (GUIDED): velocidad X/Y/Z y tasa de guiñada ──▶ ArduPilot (Pixhawk)
        · MAV_CMD_DO_SET_SERVO (AUX1, PWM): ángulo de la cámara                               ──▶ gimbal BaseCam

AutopilotoArduPilot reproduce la cascada de ArduPilot Copter (vectorizada para N drones):
    PSC  · PID de velocidad horizontal ──▶ aceleración pedida (límite PSC_ACC, conformado de jerk PSC_JERK_XY)
         · PID de velocidad vertical
    ATC  · inclinación objetivo  pitch = -atan(a_adelante / g),  roll = atan(a_derecha / g)  (límite ANGLE_MAX)
         · P de ángulo (ATC_ANG_PIT_P / RLL_P) ──▶ tasa objetivo ──▶ PID de tasa (ATC_RAT_PIT / RLL, salida
           normalizada a aceleración angular, límite ATC_ACCEL_P_MAX / R_MAX)
         · tasa de guiñada con aceleración limitada (ATC_ACCEL_Y_MAX)
    física · la aceleración horizontal real sale de la inclinación real (a = g·tan θ), más arrastre y ráfagas de viento
Seis grados de libertad: X, Y, Z (lazos de velocidad), roll y pitch (lazo de actitud) y yaw (lazo de tasa).

GimbalBaseCam: consigna de ángulo filtrada en la Jetson (EMA) ──▶ PID de ángulo del gimbal ──▶ motor brushless con la
velocidad limitada a 30°/s y el recorrido a [-60°, +15°]; su IMU compensa el cabeceo del chasis con un retardo.

Las ganancias tienen el nombre de su parámetro equivalente en ArduPilot; están ajustadas para el dron de la tesis
(respuesta de velocidad sin sobrepaso, actitud en ~0.2 s), no copiadas de los valores por defecto.
"""
import numpy as np

G = 9.81
N_SUB = 5                          # sub-pasos por paso de 0.1 s: los lazos internos corren a 50 Hz


class AutopilotoArduPilot(object):
    PSC_VELXY_P, PSC_VELXY_I, PSC_VELXY_IMAX = 2.4, 0.4, 1.5      # IMAX: tope del término I (m/s²)
    PSC_ACC_XY = 4.0               # m/s² máximos pedidos (≈ 22° de inclinación)
    PSC_JERK_XY = 5.0              # m/s³: conformado de la aceleración pedida
    PSC_VELZ_P, PSC_VELZ_I = 3.0, 0.5
    PSC_ACC_Z_ARRIBA, PSC_ACC_Z_ABAJO = 3.0, 2.0
    ANGLE_MAX = 30.0               # °
    ATC_ANG_P = 6.0                # 1/s: P del ángulo (pitch y roll)
    ATC_RAT_P, ATC_RAT_I = 25.0, 4.0   # PID de tasa normalizado (1/s y 1/s²; D despreciable a 50 Hz)
    ATC_ACCEL_PR_MAX = 1100.0      # °/s² de aceleración angular en pitch y roll
    ATC_ACCEL_Y_MAX = 180.0        # °/s² en guiñada (más bajo que el de fábrica: la cámara no lo tolera)
    ARRASTRE = 0.12                # 1/s: arrastre lineal del cuadricóptero

    def __init__(self, n, rng):
        self.n, self.rng = n, rng
        z = lambda: np.zeros(n)
        self.ix, self.iy, self.iz = z(), z(), z()            # integradores de velocidad (PSC)
        self.ax_t, self.ay_t = z(), z()                       # aceleración de la referencia (conformada en jerk)
        self.vrx, self.vry = z(), z()                         # velocidad de referencia conformada
        self.q_p, self.q_r = z(), z()                         # tasas de pitch y roll (°/s)
        self.ip, self.ir = z(), z()                           # integradores de tasa (ATC)
        self.viento_x, self.viento_y = z(), z()               # ráfaga actual (m/s²)
        self.k_planta = np.ones(n)                            # dispersión de la planta (masa, hélices): aleatoria
        self.sigma_viento = z()

    def reset(self, m, nivel=0.0):
        k = int(np.sum(m))
        if k == 0:
            return
        for a in (self.ix, self.iy, self.iz, self.ax_t, self.ay_t, self.vrx, self.vry, self.q_p, self.q_r, self.ip,
                  self.ir, self.viento_x, self.viento_y):
            a[m] = 0.0
        # aleatorización del dominio: cada partida un dron un poco distinto y otro viento (generalización)
        self.k_planta[m] = self.rng.uniform(0.85, 1.15, k)
        self.sigma_viento[m] = self.rng.uniform(0.0, 0.25 + 0.35 * nivel, k)

    def sincronizar(self, e, m):
        """Cuando la velocidad la impuso alguien más (el piloto en la fase 1), la referencia arranca desde ella."""
        self.vrx[m], self.vry[m] = e.dvx[m], e.dvy[m]
        self.ax_t[m] = self.ay_t[m] = self.ix[m] = self.iy[m] = 0.0

    def paso(self, e, vx_sp, vy_sp, vz_sp, dt):
        """Un paso de dt con N_SUB sub-pasos. Lee y escribe el estado físico del entorno e (dvx, dvy, dvz,
        chasis_pitch, chasis_roll, acc_x, acc_y). Devuelve el cabeceo que pide el comando ANTES del conformado
        de jerk (lo califica la suavidad del control: la política aprende a no pedir saltos)."""
        h = dt / N_SUB
        cps, sps = np.cos(e.psi), np.sin(e.psi)
        # ráfagas de viento: proceso de Ornstein-Uhlenbeck (correlación ~2 s)
        a_ou = np.exp(-dt / 2.0)
        ruido = self.sigma_viento * np.sqrt(1 - a_ou ** 2)
        self.viento_x = a_ou * self.viento_x + ruido * self.rng.normal(size=self.n)
        self.viento_y = a_ou * self.viento_y + ruido * self.rng.normal(size=self.n)
        cab_pedido = None
        # cabeceo que pide la consigna en bruto (antes de todo conformado): lo califica la suavidad del control
        axb, ayb = (vx_sp - e.dvx) / 0.35, (vy_sp - e.dvy) / 0.35
        escb = np.minimum(1.0, self.PSC_ACC_XY / np.maximum(np.hypot(axb, ayb), 1e-9))
        cab_pedido = -np.degrees(np.arctan((axb * cps + ayb * sps) * escb / G))
        for k in range(N_SUB):
            # ---- PSC, conformado de la consigna (como shape_vel_accel de ArduPilot): una velocidad de referencia que
            # llega a la consigna sin sobrepaso, con la aceleración limitada (raíz cuadrada) y el jerk limitado
            dx_, dy_ = vx_sp - self.vrx, vy_sp - self.vry
            dv = np.hypot(dx_, dy_)
            a_mod = np.minimum.reduce([np.full(self.n, self.PSC_ACC_XY), np.sqrt(2.0 * 0.8 * self.PSC_JERK_XY * dv), 4.0 * dv])
            adx, ady = dx_ / np.maximum(dv, 1e-9) * a_mod, dy_ / np.maximum(dv, 1e-9) * a_mod
            jx, jy = adx - self.ax_t, ady - self.ay_t
            escj = np.minimum(1.0, self.PSC_JERK_XY * h / np.maximum(np.hypot(jx, jy), 1e-9))
            self.ax_t += jx * escj
            self.ay_t += jy * escj
            self.vrx += self.ax_t * h
            self.vry += self.ay_t * h
            # ---- PSC, PID de velocidad: corrige el error respecto a la referencia, con la aceleración de la
            # referencia como prealimentación (I con tope); límite de aceleración como vector
            ex, ey = self.vrx - e.dvx, self.vry - e.dvy
            self.ix = np.clip(self.ix + ex * h, -self.PSC_VELXY_IMAX / self.PSC_VELXY_I, self.PSC_VELXY_IMAX / self.PSC_VELXY_I)
            self.iy = np.clip(self.iy + ey * h, -self.PSC_VELXY_IMAX / self.PSC_VELXY_I, self.PSC_VELXY_IMAX / self.PSC_VELXY_I)
            ax = self.ax_t + self.PSC_VELXY_P * ex + self.PSC_VELXY_I * self.ix
            ay = self.ay_t + self.PSC_VELXY_P * ey + self.PSC_VELXY_I * self.iy
            esc = np.minimum(1.0, self.PSC_ACC_XY / np.maximum(np.hypot(ax, ay), 1e-9))
            ax, ay = ax * esc, ay * esc
            # ---- ATC: inclinación objetivo en el marco del dron
            af = ax * cps + ay * sps
            al = ax * sps - ay * cps                               # + = a la derecha
            p_t = np.clip(-np.degrees(np.arctan(af / G)), -self.ANGLE_MAX, self.ANGLE_MAX)
            r_t = np.clip(np.degrees(np.arctan(al / G)), -self.ANGLE_MAX, self.ANGLE_MAX)
            # P de ángulo -> tasa objetivo -> PID de tasa -> aceleración angular (limitada) -> tasa -> ángulo
            for ang, q, integ, obj, cual in ((e.chasis_pitch, self.q_p, self.ip, p_t, "p"), (e.chasis_roll, self.q_r, self.ir, r_t, "r")):
                q_t = self.ATC_ANG_P * (obj - ang)
                eq = q_t - q
                integ += eq * h
                alfa = np.clip(self.k_planta * (self.ATC_RAT_P * eq + self.ATC_RAT_I * integ), -self.ATC_ACCEL_PR_MAX, self.ATC_ACCEL_PR_MAX)
                q += alfa * h
                ang += q * h
            # ---- física: la aceleración real sale de la inclinación real
            af_r = -G * np.tan(np.radians(e.chasis_pitch))
            al_r = G * np.tan(np.radians(e.chasis_roll))
            axr = af_r * cps + al_r * sps - self.ARRASTRE * e.dvx + self.viento_x
            ayr = af_r * sps - al_r * cps - self.ARRASTRE * e.dvy + self.viento_y
            e.dvx += axr * h
            e.dvy += ayr * h
            e.acc_x, e.acc_y = axr, ayr
            # ---- PSC vertical
            ez = vz_sp - e.dvz
            self.iz = np.clip(self.iz + ez * h, -2.0, 2.0)
            azr = np.clip(self.PSC_VELZ_P * ez + self.PSC_VELZ_I * self.iz, -self.PSC_ACC_Z_ABAJO, self.PSC_ACC_Z_ARRIBA)
            e.dvz += azr * h
        return cab_pedido

    def guinada(self, e, yaw_sp, dt):
        """Tasa de guiñada con la aceleración limitada (ATC_ACCEL_Y_MAX)."""
        e.yaw_dps += np.clip(yaw_sp - e.yaw_dps, -self.ATC_ACCEL_Y_MAX * dt, self.ATC_ACCEL_Y_MAX * dt)


class GimbalBaseCam(object):
    VEL_MAX = 30.0                 # °/s: motor brushless del pitch
    MIN, MAX = -60.0, 15.0         # recorrido (límite duro)
    ALPHA_CONSIGNA = 0.2           # EMA de la consigna en la Jetson (antes del PWM)
    KP, KI = 4.0, 0.6              # PID de ángulo del gimbal (1/s y 1/s²)
    TAU_MOTOR = 0.03               # s: respuesta del motor a la tasa pedida
    TAU_ESTAB = 0.15               # s: la IMU del gimbal compensa el cabeceo del chasis con este retardo

    def __init__(self, n, angulo=-10.0):
        self.ang = np.full(n, angulo)        # ángulo físico del motor de pitch (respecto al horizonte)
        self.sp = np.full(n, angulo)         # consigna filtrada (EMA)
        self.q = np.zeros(n)                 # tasa del motor (°/s)
        self.i = np.zeros(n)
        self.err = np.zeros(n)               # error de estabilización por el cabeceo del chasis

    def reset(self, m, angulo=-10.0):
        self.ang[m] = self.sp[m] = angulo
        self.q[m] = self.i[m] = self.err[m] = 0.0

    def fijar(self, angulo):
        self.ang[:] = self.sp[:] = angulo
        self.q[:] = self.i[:] = self.err[:] = 0.0

    def paso(self, consigna, d_chasis, dt):
        """consigna: ángulo que manda la Jetson; d_chasis: cuánto cambió el cabeceo del chasis en el paso.
        Devuelve el ángulo de la cámara respecto al horizonte (con el límite duro)."""
        self.sp += self.ALPHA_CONSIGNA * (np.clip(consigna, self.MIN, self.MAX) - self.sp)
        h = dt / N_SUB
        for _ in range(N_SUB):
            e = self.sp - self.ang
            q_lib = self.KP * e + self.KI * self.i
            # anti-windup: el integrador solo acumula si el motor no está saturado en velocidad
            self.i = np.where(np.abs(q_lib) < self.VEL_MAX, np.clip(self.i + e * h, -10.0, 10.0), self.i)
            q_t = np.clip(self.KP * e + self.KI * self.i, -self.VEL_MAX, self.VEL_MAX)
            self.q += (q_t - self.q) * min(1.0, h / self.TAU_MOTOR)
            self.ang = np.clip(self.ang + self.q * h, self.MIN, self.MAX)
            self.q = np.where((self.ang <= self.MIN) | (self.ang >= self.MAX), 0.0, self.q)
        self.err += d_chasis - self.err * dt / self.TAU_ESTAB
        return np.clip(self.ang + self.err, self.MIN, self.MAX)


if __name__ == "__main__":
    # respuesta al escalón: velocidad 0 -> 3 m/s y frenado; gimbal 0° -> -45°
    class Estado(object):
        pass
    e = Estado()
    n = 1
    for nombre in ("dvx", "dvy", "dvz", "chasis_pitch", "chasis_roll", "acc_x", "acc_y", "psi", "yaw_dps"):
        setattr(e, nombre, np.zeros(n))
    ap = AutopilotoArduPilot(n, np.random.default_rng(0))
    print("t(s)  vx(m/s)  pitch(°)  ax(m/s²)")
    for t in range(40):
        sp = 3.0 if t < 20 else 0.0
        ap.paso(e, np.full(n, sp), np.zeros(n), np.zeros(n), 0.1)
        if t % 2 == 1:
            print("%.1f   %5.2f   %6.1f   %5.2f" % ((t + 1) * 0.1, e.dvx[0], e.chasis_pitch[0], e.acc_x[0]))
    gb = GimbalBaseCam(1, 0.0)
    print("gimbal 0 -> -45°:", " ".join("%.0f" % gb.paso(np.array([-45.0]), np.zeros(1), 0.1)[0] for _ in range(25)))
