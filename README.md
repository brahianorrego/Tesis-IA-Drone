# Tesis-IA-Drone

Sistema experimental de **detección y seguimiento de personas con evasión de obstáculos** para un
cuadricóptero autónomo en exteriores. La IA corre a bordo en una NVIDIA Jetson Orin Nano y le da
órdenes a una Pixhawk con ArduPilot por MAVLink.

Proyecto de grado en Ingeniería Aeronáutica, Universidad de San Buenaventura · Brahian Andrés Orrego Osorio
([@brahianorrego](https://github.com/brahianorrego)).

## La misión

Caso de uso: la policía necesita **mantener a la vista a un sospechoso** hasta que lleguen los refuerzos.

1. **Traslado (piloto al mando).** El piloto vuela hasta la zona. El sistema solo protege el frente:
   si el LiDAR ve un obstáculo o la cámara ve a una persona en riesgo, **detiene el avance y sube**.
   Este es el **mínimo indispensable** que evalúa el comité.
2. **Zona (IA al mando, trabajo complementario).** El piloto pasa CH5 a GUIDED: el dron busca, el operador
   confirma con un clic quién es el sospechoso y el dron lo mantiene a la vista, lo sigue y lo vuelve a encontrar si
   se esconde. La parada de emergencia (CH8) y el piloto siempre tienen prioridad.

## Arquitectura

```
 Percepción                          Decisión (híbrida)                       Control
 ───────────                         ───────────────────                      ───────
 Cámara USB + YOLO26n TensorRT ┐     Máquina de estados determinista ─┐
 (tracking con ID, ReID)       │     (buscar · verificar · búsqueda    │
 Cámara CSI IMX219             ├──►   tras la pérdida, con mapa LiDAR) ├─► Árbitro de ─► MAVLink ─► Pixhawk
 LiDAR TF03                    │     Política PPO (solo con el        │   seguridad     (GUIDED: velocidades,
 Ángulo del gimbal, Pixhawk    ┘      objetivo fijado)                ┘                 yaw, pitch por AUX1)
```

- **Reglas deterministas** para lo que debe ser predecible y auditable: búsqueda, confirmación humana,
  recuperación del objetivo y seguridad.
- **Red neuronal (PPO, Stable-Baselines3)** entrenada por refuerzo en simulación, solo para la parte táctica con el
  objetivo fijado.
- **Reglas duras** (no negociables): ver [CLAUDE.md](CLAUDE.md). Gimbal entre −45° y +15°, geocerca, búsqueda
  determinista, humano en el lazo, árbitro de seguridad y la red no estabiliza nada.

## Hardware

Pixhawk 2.4.8 (ArduCopter 4.7) · Jetson Orin Nano · cámara USB (HFOV 38.9°) y cámara CSI IMX219 · LiDAR Benewake
TF03 · gimbal BaseCam SimpleBGC de 2 ejes (pitch por PWM desde AUX1) · emisora Futaba · LiPo 4S.

- [docs/hardware.md](docs/hardware.md): componentes, conexiones y problemas resueltos.
- [docs/pixhawk.md](docs/pixhawk.md): parámetros de ArduPilot.
- [docs/jetson.md](docs/jetson.md): software de a bordo, puertos y puesta a punto.

## Estructura del repositorio

```
├── README.md                 este archivo
├── CLAUDE.md                 guía y reglas duras del proyecto
├── .claude/                  agentes (arquitecto, supervisor-rl, implementador) y la skill /cierre-sesion
├── docs/                     estado, bitácora, decisiones, planes (V15, V16, mínimo físico) y documentación técnica
├── jetson/                   código de a bordo (copia de ~/Escritorio/dron_ia de la Jetson)
└── simulacion/               entrenamiento por refuerzo, mínimo indispensable y visor 3D
    ├── entorno.py            mundo, sensores, máquina de estados, árbitro, ladrón, civiles y recompensas (V15)
    ├── control.py            modelo de los controladores: cascada PSC/ATC de ArduPilot y PID del gimbal
    ├── entrenar_master.py    entrenamiento actual (Stable-Baselines3, currículo)
    ├── entrenar.py           PPO propio de las versiones 1 a 9 (y utilidades que usa el master)
    ├── mision.py             misión completa (piloto + IA) para el visor
    ├── index.html            visor 3D tipo estación de tierra
    ├── minimo_tesis/         mínimo indispensable del comité (congelado): protocolo, decisor IA y repeticiones
    ├── herramientas/         resumir_metricas.py y evaluar_politica.py
    ├── informes/             evaluaciones, resúmenes y diagnósticos de cada versión
    ├── tests/                pruebas (reglas duras, entorno, niveles, mínimo)
    ├── modelos/              dron_politica.json (pesos para la Jetson)
    └── *_vN.*                versiones anteriores de cada archivo (no se editan)
```

Los modelos (`.zip`, `.pt`), las salidas (`salida*/`) y los registros no se suben (pesan GB). Los esenciales de la
V10 están en el Release `v10-master-759M`.

## Cómo ejecutar (Windows, desde `simulacion\`)

```
CONTINUAR_ENTRENAMIENTO.bat                            :: retoma el entrenamiento actual (entrenar_master.py)
ABRIR_VISOR.bat                                        :: visor en http://127.0.0.1:8765/
.venv\Scripts\python.exe -m unittest discover -s tests :: pruebas
```

Detalle en [simulacion/README.md](simulacion/README.md) y [CLAUDE.md](CLAUDE.md).

## Estado

Ver [docs/ESTADO.md](docs/ESTADO.md). En resumen:
- **Mínimo indispensable:** 1300 vuelos del protocolo del comité, 100 % de éxito, 0 activaciones falsas. Falta la
  validación con datos reales.
- **V15:** misión policial con currículo de 5 niveles. Detenida en el nivel 4 (rendición ~32 %, ver
  `simulacion/informes/diagnostico_v15_nivel4.md`).
- **V16 (en preparación):** misión de 2 paneles con física humana real y visor realista
  ([docs/PLAN_V16_REALISMO.md](docs/PLAN_V16_REALISMO.md)).

## Historial de versiones de la simulación

| Versión | Cambio principal |
|---|---|
| v1-v2 | Dron vs persona por autojuego PPO; después, mantener a la persona a la vista |
| v3-v5 | Dron vs ladrón con paneles y peatones; árbitro ante amenaza real; operador que designa; ladrón táctico |
| v6 | Arquitectura híbrida: reglas deterministas (banda muerta, gimbal, protocolo de pérdida, operador) + PPO |
| v7-v9 | Mapa LiDAR, flanqueo, intercepción predictiva, suavidad, límites físicos del gimbal y jerk del autopiloto |
| V10 | Stable-Baselines3 con transferencia desde la v9 (770 M pasos). Etiqueta `v10-master-759M` |
| v11 | Gimbal estricto −45° y búsqueda determinista tras perder el objetivo |
| V12 | Control jerárquico: la red solo se multa por lo que comanda, reflejo de punto ciego y búsqueda con memoria |
| V13-V14 | Currículo progresivo, interrupción táctica, detección parcial y oclusión entre personas |
| V15 | Currículo de 5 niveles, rendición del ladrón (cansancio y moral), Kalman + partículas, identidad con reconfirmación |
| Mínimo | `minimo_tesis/`: protocolo del comité (frenar y subir ante un riesgo) y decisor IA con scikit-learn |
| V16 | (plan) 2 paneles, posturas humanas, alturas variables, cámara al piso y visor realista |
