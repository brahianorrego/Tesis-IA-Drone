# Plan del mínimo indispensable en el dron real

Arquitecto, 2026-10-11. Objetivo: cumplir **exactamente** lo aprobado por el comité (documento "Cambio de objetivos",
2026-09-01) con el dron real, y poder defender que la IA **detecta y decide**. Todo lo demás (misión del policía, V15)
es trabajo complementario y no bloquea este plan.

---

## 1. Qué exige el comité (resumen)

- **Objetivo general:** sistema experimental de detección de personas y evasión de obstáculos para un cuadricóptero,
  con IA preentrenada y sensores de proximidad, en **exteriores**.
- **Objetivos específicos:** (1) definir la arquitectura (modelo preentrenado + LiDAR); (2) evaluar la integración en el
  dron con pruebas de activación, comunicación y respuesta; (3) validar el protocolo de evasión con experimentos
  repetibles (tasa de éxito y seguridad).
- **Cómo opera:** el **piloto mantiene el avance frontal en línea recta**; el sistema interviene **solo ante un riesgo
  definido** y **anula temporalmente el avance** con la maniobra **DETENCIÓN + ASCENSO VERTICAL** dentro de un margen
  seguro. También un **modo estático** (dron quieto, sin desplazarse). El operador puede intervenir siempre.
- **Límites:** una persona como objetivo principal; sin evasión lateral, sin navegación autónoma, sin planeación de
  trayectorias; solo LiDAR frontal + computador de a bordo + Pixhawk (el documento dice Raspberry Pi: **hay que
  actualizarlo a Jetson Orin Nano**); entorno exterior controlado con paneles.
- **Métricas:** tasa de éxito, activaciones de evasión, eventos de riesgo, latencia de respuesta e intervenciones del
  operador.

Lo que **NO** hace falta para el mínimo: seguir a la persona con el gimbal, girar en yaw hacia ella, búsquedas, 360°,
la política PPO. El gimbal solo **estabiliza** con el pitch fijo.

## 2. La misión mínima (lo que hace el dron)

1. El piloto despega y se pone a **2.3 m** de altura en el campo de pruebas (geocerca de ArduPilot activa).
2. Activa el **modo experimental** con un interruptor (propuesta: CH7). Desde ahí la Jetson puede intervenir.
3. El piloto **avanza en línea recta** (LOITER, velocidad limitada con `LOIT_SPEED` = 4 m/s o menos).
4. La Jetson, a 30 cuadros por segundo: YOLO busca personas, el TF03 mide lo que hay al frente y el **decisor IA** decide
   en cada cuadro: **CONTINUAR** o **DETENER_Y_ASCENDER**.
5. Si decide intervenir: pasa la Pixhawk a GUIDED por MAVLink y manda velocidad horizontal 0 y subida hasta **3.30 m**
   (fuera del alcance de una persona). Se queda ahí.
6. **El piloto retoma** moviendo el interruptor de modo (CH5): ArduPilot obedece al piloto y la Jetson deja de mandar.
   **CH8** sigue siendo la parada de emergencia de motores.
7. **Modo estático:** el dron en hover (sin avance); si alguien se le viene encima, sube.
8. Si alguien pasa de lado o lejos, **no hace nada** (eso también se mide: falsas activaciones).

**Ajustes tras la revisión de la sesión física (2026-10-11):**
- CH5: pos1 **ALT_HOLD** (retoma), pos2 **LOITER** (vuelo de prueba), pos3 **LAND**. GUIDED sale del interruptor: ArduPilot
  solo cambia de modo cuando el interruptor cambia de posición, así que la retoma es **bajar a pos1**.
- La Jetson suelta el mando en cuanto el HEARTBEAT no muestra GUIDED y no vuelve a pedirlo hasta rearmar CH7 (OFF→ON).
  CH7 = interruptor físico de "modo experimental", leído por RC_CHANNELS; solo arma si el EKF tiene posición (GPS).
- La subida usa un **objetivo de posición** (posición actual + 3.30 m), que GUIDED sostiene solo. Si el cambio a GUIDED es
  rechazado: alerta por STATUSTEXT, se cuenta como "intervención fallida" y manda el piloto.
- **Pitch fijo = −5°** (1444 µs por AUX1), el mismo de `simulacion/minimo_tesis/sistema.py`.

Por qué así: es la forma estándar de que un computador de a bordo "anule temporalmente" al piloto en ArduPilot sin
tocar el radio, y el piloto conserva siempre la última palabra (cumple "el operador podrá intervenir en cualquier
momento"). La sesión física debe verificar en banco que el cambio de modo por MAVLink funciona con la configuración
actual (FLTMODE, GUIDED en CH5 posición 3).

## 3. Cómo se defiende que hay IA (las dos IAs del sistema)

| IA | Qué hace | Cómo se obtuvo | Por qué IA y no reglas |
|---|---|---|---|
| **YOLO26n** (TensorRT) | Detecta personas en la imagen (caja + confianza) | Preentrenada (COCO); no se entrena desde cero (lo dice el alcance) | Detectar una persona en una imagen no se puede hacer con condicionales |
| **Decisor MLP** (`decision.pkl`) | Decide CONTINUAR o DETENER_Y_ASCENDER con las medidas de los sensores | Entrenado con millones de ejemplos **etiquetados automáticamente en simulación** y validado con datos reales del dron | Las medidas reales son ruidosas: la distancia por la caja sobreestima ~2× de cerca (medido el 2026-10-07), YOLO pierde cuadros, y una persona que cruza se parece a una que viene. Con umbrales fijos hay que adivinar números a mano (en simulación se encontraron varios errores de umbrales); la red aprende la frontera de decisión a partir de los datos |

- **Qué es un MLP** (perceptrón multicapa): una red neuronal pequeña. Recibe unos números (por ejemplo, tamaño de la
  caja, distancia del LiDAR, velocidad propia, qué tan rápido se acerca la persona), los pasa por dos capas de
  "neuronas" (32 y 16) y devuelve una probabilidad de riesgo. Si la probabilidad pasa de un umbral (0.7) en 2 cuadros
  seguidos, interviene. Aprende viendo ejemplos con la respuesta correcta.
- **Las reglas no desaparecen:** quedan como **envolvente de seguridad** (LiDAR < 3 m frena siempre; árbitro de
  amenaza). La IA decide dentro de esa envolvente. Así se puede decir con honestidad: "la IA decide y las reglas
  garantizan el mínimo de seguridad".
- **Evidencia que se presenta:** comparación REGLAS vs IA vs IA+envolvente en los mismos escenarios (simulación:
  `simulacion/informes/minimo_tesis_decisor_ia.md`, en preparación) y en los datos reales (paso 4). Resultado
  preliminar en validación con vuelos aleatorios: la IA con envolvente tuvo **menos choques (18 vs 24) y menos frenadas
  innecesarias (42 vs 62)** que las reglas, con AUC-ROC 0.97. Si en los datos reales no gana en algo, se reporta.

## 4. Estado real del hardware (para no repetir lo hecho)

| Pieza | Estado | Dónde |
|---|---|---|
| LiDAR TF03 | ✅ Lee por USB-TTL (driver pl2303), 100 Hz, validado el 2026-10-06 | `~/Escritorio/dron_ia/lidar_tf.py` |
| Cámara USB + YOLO26n TensorRT FP16 | ✅ 30 FPS de cámara, 9-11 ms de inferencia (90+ FPS) | `percepcion.py`, `yolo26n.engine` |
| Gimbal BaseCam | ⚠ Lectura de ángulos OK por USB; **el control por UART NO funciona** (firmware 2.2 ignora CMD_CONTROL). El pitch se manda por PWM desde AUX1 de la Pixhawk (DO_SET_SERVO, verificado). Falta confirmar con la BaseCam alimentada que lee el pulso | `gimbal_basecam.py` |
| Jetson ↔ Pixhawk | ✅ MAVLink por TELEM2 a 115200 (DO_SET_SERVO 10/10 con ACK) | `config.py` |
| Yaw hacia la persona | ✅ implementado (no hace falta para el mínimo) | `vuelo_evasion.py` |
| Batería | Nueva (la vieja quedó sobredescargada y se retiró) | — |

Pendiente desde hace días: **copiar `~/Escritorio/dron_ia` de la Jetson a `jetson/` del repositorio** (sin IPs ni
claves).

## 5. Hoja de ruta física (un paso a la vez; no se avanza sin la confirmación de Brahian)

Reglas de todos los pasos: **sin hélices** hasta el paso 6; vigilar el voltaje de la batería por MAVLink (aviso 14.4 V,
desconectar a 14.0 V); la Jetson con su cargador cuando no haga falta la batería; Claude opera la Jetson por SSH y a
Brahian solo le pide acciones físicas.

| Paso | Qué | Cómo se hace | Se acepta si |
|---|---|---|---|
| **0** | Inventario | Copiar el código de la Jetson al repo; revisar `lidar_tf.py`, `percepcion.py`, `vuelo_evasion.py`, `config.py` | Todo en `jetson/`, sin secretos |
| **1** | Percepción + registro (banco) | Un script `registro_minimo.py` que en cada cuadro guarda: hora, caja de YOLO (x, y, ancho, alto, confianza, ID), LiDAR (distancia, intensidad), pitch del gimbal y, si está conectada, velocidad y altura de la Pixhawk. Manejo de desconexiones (cable del LiDAR, cámara) | 30 FPS sostenidos 10 min, LiDAR sin huecos, reconecta solo |
| **2** | Gimbal fijo | Pitch fijo (0 a −3°) por AUX1 y estabilización; confirmar con la BaseCam alimentada (pendiente desde el 10-07). **No hay seguimiento con el gimbal en el mínimo** | El pitch se queda donde se manda y la imagen no vibra |
| **3** | Intervención por MAVLink (banco, sin hélices) | Script que, ante un riesgo simulado (mano delante del LiDAR a < 3 m), pasa a GUIDED y manda freno + subida; ver en Mission Planner el modo y la consigna; CH5 devuelve el mando al piloto; CH8 corta. Armar sin hélices solo si Brahian lo autoriza | Latencia riesgo → comando < 150 ms medida en el log; el piloto siempre recupera el mando |
| **4** | Datos reales (sin hélices, dron en un carrito o trípode a ~2 m) | Ver sección 6 | Dataset con los escenarios a-e, sincronizado y etiquetado |
| **5** | Decisor en "modo sombra" | `sistema_minimo.py` (portado de `simulacion/minimo_tesis/sistema.py` + `decision.pkl`) decide y lo registra, pero **no manda nada**; se prueba con el carrito | Decide igual que en simulación con los mismos datos; latencia < 50 ms |
| **6** | Vuelos | (a) hover y avance del piloto sin el sistema; (b) sistema activo contra un **panel de cartón** a 1 y luego 2 m/s; (c) **maniquí** en vez de persona; (d) persona real solo quieta o cruzando lejos, y solo tras 10/10 con el maniquí | Cada etapa 10/10 antes de la siguiente |
| **7** | Protocolo del comité | 10 repeticiones por escenario con el registro de la Jetson y el DataFlash; mismas métricas que la simulación | Tablas para el documento |
| **8** | Optimización | Solo si la latencia medida no cumple (hoy YOLO va sobrado) | — |

## 6. Cómo se graban los datos reales (paso 4)

- **El dron no vuela.** Va **sin hélices**, montado en un **carrito** (o una mesa con ruedas) con la cámara a ~2 m de
  altura si se puede (un trípode o un palo sobre el carrito), porque la geometría de la caja depende de la altura. Para
  el modo estático, el mismo montaje quieto.
- **Marcas en el piso:** conos a 2, 4, 6, 8, 10, 12 y 15 m del dron, medidos con cinta.
- **Escenarios** (los mismos del protocolo, 5-10 repeticiones cada uno):
  1. Persona quieta en cada cono (5 s por cono): calibra la distancia por caja contra la cinta y el LiDAR.
  2. Persona que camina directo hacia el dron desde 15 m hasta 3 m (y se detiene a 3 m: **nunca más cerca**).
  3. Persona que trota hacia el dron desde 15 m hasta 4 m.
  4. Persona que cruza de lado a 5, 8 y 12 m (caminando y trotando).
  5. Carrito empujado a ~1 m/s hacia la persona quieta (simula el avance del dron), detenerse a 3 m.
  6. Carrito hacia un panel de cartón (sin persona).
- **Etiquetas automáticas:** después, con las marcas y el LiDAR, se calcula para cada cuadro si "siguiendo igual, la
  persona estaría a menos de 2 m en los próximos segundos", con la misma definición de la simulación. Nadie etiqueta a
  mano.
- **Para qué sirven:** (a) comprobar que el modelo de sensores de la simulación se parece a la realidad (tasa de
  detección y error de distancia según la distancia); (b) evaluar el `decision.pkl` entrenado en simulación con datos
  reales; (c) si hace falta, reentrenarlo mezclando datos reales y simulados.
- **Hiperparámetros iniciales del MLP** (de la simulación, `minimo_tesis/decision_entrenamiento.json`): capas (32, 16),
  umbral 0.7, 2 cuadros seguidos; se confirman con el informe final del decisor.

## 7. Lo que tiene que actualizar Tania en el documento

- Raspberry Pi → **Jetson Orin Nano**; cámara USB (HFOV 38.9°); gimbal de 2 ejes con pitch fijo en el mínimo.
- Módulo de decisión: **MLP entrenado con datos de simulación etiquetados automáticamente y validado con datos reales**,
  con reglas de seguridad como envolvente.
- Metodología: sección "Cómo se reproduce en campo" de `simulacion/informes/minimo_tesis_protocolo.md`.
