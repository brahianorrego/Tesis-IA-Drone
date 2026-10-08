# Tesis-IA-Drone

Sistema experimental de **detección y seguimiento de personas con evasión de obstáculos** para un
cuadricóptero autónomo en exteriores. La IA corre a bordo en una NVIDIA Jetson Orin Nano y le da
órdenes a una Pixhawk con ArduPilot por MAVLink.

Tesis de grado en Ingeniería Aeronáutica · Brahian Orrego ([@brahianorrego](https://github.com/brahianorrego)) y Tania.

## La misión

Caso de uso: la policía necesita **mantener a la vista a un sospechoso** hasta que lleguen los refuerzos.

1. **Traslado (piloto al mando).** El piloto vuela hasta la zona. El sistema solo protege el frente:
   si el LiDAR ve un obstáculo a menos de 3 m, o la cámara ve a una persona de frente, bloquea el avance.
2. **Zona (IA al mando).** El piloto pasa el interruptor CH5 a GUIDED y la IA toma el control: busca
   personas, el operador en tierra confirma cuál es el sospechoso, y el dron lo mantiene en la vista,
   lo sigue y lo esquiva si se le viene encima. La parada de emergencia (CH8) y el retorno del piloto
   siempre tienen prioridad.

## Arquitectura

```
 Percepción                      Decisión (híbrida)                        Control
 ───────────                     ───────────────────                       ───────
 Cámara USB + YOLO26n TensorRT ┐  Máquina de estados determinista ─┐
 (tracking con ID y ReID)      │  (buscar · verificar · protocolo   │
 LiDAR TF03 (frontal)          ├─►  de pérdida)                     ├─► Árbitro de ─► MAVLink ─► Pixhawk
 Telemetría del gimbal         │  Política PPO (solo con el        │   seguridad     (GUIDED: velocidades,
 Estado de la Pixhawk (GPS,    ┘   objetivo fijado)                ┘                  yaw_rate, gimbal)
 rumbo, altura)
```

- **Reglas deterministas** para todo lo que debe ser predecible y auditable: búsqueda, confirmación
  humana, recuperación del objetivo y seguridad.
- **Red neuronal (PPO)** entrenada por aprendizaje por refuerzo en simulación, solo para la parte
  táctica: cómo mantener al sospechoso a la vista y esquivarlo cuando está fijado.
- **Árbitro de seguridad:** tiene la última palabra. Solo autoriza una evasión ante una amenaza real
  (una persona a menos de 3 m, o a menos de 8 m acercándose).

## Arquitectura Híbrida - Versión 6

La versión 6 suma seis reglas deterministas alrededor de la red neuronal. Todas están en
[`simulacion/entorno.py`](simulacion/entorno.py) y se ven en el visor (`simulacion/index.html`).

| # | Regla | Comportamiento | Parámetros |
|---|---|---|---|
| 1 | **Banda muerta de yaw** | El dron no corrige la guiñada mientras el objetivo esté en el 20% central del FOV horizontal. Si sale de esa banda, recentra hasta un margen menor y se detiene (histéresis): no hay vaivén. Ganancia proporcional con rampa de aceleración. | `BANDA_MUERTA = 0.10·HFOV` (±3.9°), `BANDA_RECENTRA = 0.04·HFOV` (±1.6°), `YAW_KP = 2.0`, `YAW_MAX = 60°/s`, `ACEL_YAW = 180°/s²` |
| 2 | **Pitch del gimbal** | El seguimiento vertical lo hace la cámara, no el dron: el gimbal inclina el pitch para centrar al objetivo (con su propia banda muerta) y el dron no sube ni baja para verlo. Sin objetivo, la cámara mira al suelo a 8 m. En el dron real el ángulo se manda por AUX1 de la Pixhawk. | `GIMBAL_MIN/MAX = −45°/+10°`, `GIMBAL_VEL = 90°/s`, `GIMBAL_KP = 4`, `GIMBAL_BANDA = 0.10·VFOV`, `D_REPOSO = 8 m` |
| 3 | **Máquina de estados para la pérdida del objetivo** | Si el tracker suelta el ID por más de 1 s: **INVESTIGAR** (vuela a la última posición X, Y conocida, por encima de los paneles) → **BARRIDO** de 360° allí → **BARRIDO ALTO** (sube a 4.8 m y barre otra vez). Si en cualquier paso se reconfirma el ID por apariencia (ReID), vuelve a FIJADO. Solo al agotar el protocolo la misión se da por fallida. | `T_TRACKER = 1 s`, `N_REID = 4` cuadros, `Z_TRANSITO = 3.2 m`, `VEL_INVESTIGA = 1.8 m/s`, `T_INVESTIGA_MAX = 12 s`, `Z_ALTO = 4.8 m`, `R_PIERDE = −1` |
| 4 | **Búsqueda tras obstáculos** | Si el giro inicial de 360° no encuentra a nadie, el dron hace búsqueda activa: vuela por encima de cada panel a un punto detrás de él y barre 360° allí, uno por uno. Un giro iniciado no se corta antes de 1.5 s y solo lo pausa alguien dentro del perímetro de colisión. | `D_INSPECCION = 3.5 m`, `Z_TRANSITO = 3.2 m`, `YAW_BUSQUEDA = 40°/s`, `T_GIRO_MIN = 1.5 s`, `D_PERIMETRO = 2 m` |
| 5 | **Retícula de error PID** | En la cámara FPV del visor, un recuadro fijo marca la banda muerta (20% central del FOV horizontal y vertical) y un punto marca el centro del objetivo. Se muestra el error en grados (`ERR X ±…° Y ±…°`), que es la entrada de los lazos de yaw y de pitch. Verde "EN BANDA · YAW 0" mientras el punto está dentro; naranja "CORRIGIENDO" si sale. | `ex = (px − cx)/W · HFOV`, `ey = (py − cy)/H · VFOV`; bandas de las reglas 1 y 2 |
| 6 | **Confirmación Human-in-the-Loop** | El sistema nunca decide solo quién es el sospechoso (YOLO solo detecta "persona"). Al ver a alguien, el dron queda en hover, lo centra y alerta al operador. El operador confirma con un clic sobre la persona → lock-on. Sin clic en 3 s, ese ID se descarta y la búsqueda sigue. La política PPO solo actúa con el objetivo fijado. | `T_ESPERA_CLIC = 3 s`, `T_VER_MIN = 0.5 s`, `T_OPERADOR = 1–2 s` (operador simulado) |

**Éxito y fracaso:** la misión se cumple al mantener el rastreo 30 s desde el lock-on (con las
recuperaciones que hagan falta). Falla si se agota el protocolo de pérdida, si no se fija al
sospechoso en 60 s, si hay un choque o si el dron sale de la geocerca.

## Hardware

Pixhawk (ArduPilot 4.7) · Jetson Orin Nano · cámara USB (HFOV 38.9°) · LiDAR Benewake TF03 ·
gimbal BaseCam SimpleBGC de 2 ejes · emisora Futaba · LiPo 4S.

- [docs/hardware.md](docs/hardware.md): componentes, diagrama de conexiones y problemas resueltos.
- [docs/pixhawk.md](docs/pixhawk.md): parámetros de ArduPilot (enlace, modos de vuelo, failsafes, gimbal).
- [docs/jetson.md](docs/jetson.md): software de a bordo, puertos y puesta a punto.

## Estructura del repositorio

```
├── README.md            este archivo
├── docs/                documentación técnica del dron
├── jetson/              código de a bordo (pendiente de copiar desde la Jetson)
└── simulacion/          entrenamiento de la IA por refuerzo y visor 3D
    ├── entorno.py       mundo, sensores, máquina de estados, árbitro y recompensas (v6)
    ├── entrenar.py      PPO para el dron y el ladrón (autojuego)
    ├── mision.py        misión completa (fase piloto + fase IA) para el visor
    ├── evaluar.py       comparación IA vs reglas
    ├── index.html       visor 3D tipo estación de tierra
    ├── modelos/         pesos de la política del dron (dron_politica.json)
    └── *_vN.*           versiones anteriores de cada experimento
```

## Cómo ejecutar la simulación (Windows)

Ver [simulacion/README.md](simulacion/README.md). En resumen:

```
cd simulacion
.venv\Scripts\python.exe -u entrenar.py --pasos 600e6      # entrenar (--continuar para retomar)
.venv\Scripts\python.exe -m http.server 8765 --bind 127.0.0.1   # visor en http://127.0.0.1:8765/
```

## Historial de versiones de la simulación

| Versión | Cambio principal |
|---|---|
| v1 | Dron vs persona (autojuego PPO); el dron aprende a no dejarse alcanzar |
| v2 | Objetivo: mantener a la persona en la vista; acción SEGUIR |
| v3 | Dron vs ladrón; peatones como obstáculos; paneles que tapan la vista |
| v4 | Árbitro solo ante amenaza real; designación del objetivo por el operador y ReID |
| v5 | Máquina de estados BUSCAR → VERIFICAR → FIJADO; ladrón táctico; misión cumplida/fallida |
| v6 | Arquitectura híbrida: las 6 reglas deterministas de arriba |
