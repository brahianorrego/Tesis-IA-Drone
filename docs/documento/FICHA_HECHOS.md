# Ficha de hechos verificados para el documento

Actualizada: 2026-10-12. Cada dato tiene su fuente en el repositorio (ramas `v15-curriculo` y `v16-simulacion`).
Lo que no está medido todavía va en la última sección. **No escribir en el documento un número que no esté aquí.**

## 1. Lo que aprobó el comité (carta del 01/09/2026)

- Objetivos y pregunta de investigación: **no se cambian**. Solo se pasó de interiores a exteriores.
- La carta todavía dice **Raspberry Pi**. El sistema real usa **NVIDIA Jetson Orin Nano**. La **Pixhawk** sigue.
- Alcances y limitaciones: se pueden ajustar un poco (decisión de Brahian, 2026-10-12).
- Contradicciones de la carta que se corrigieron en la copia intervenida:
  - "El dron permanecerá fijo y sin evasión" frente a "detención y ascenso vertical". Ahora el modo estático es un escenario
    más, y en él la única respuesta es subir.
  - "Solo LiDAR, Raspberry y Pixhawk, sin sensores adicionales" frente a la cámara, el estabilizador y el GPS. Ahora se
    dice que no se agregan sensores **de percepción**, y que el GPS y el estabilizador son de la plataforma.
  - "No hay entrenamiento desde cero" frente al MLP entrenado. Ahora la frase se refiere al **detector**, y se aclara que
    lo único que se entrena es un clasificador pequeño que no procesa imágenes.
  - "Esta fase no corresponde a la validación por repeticiones" contradice el objetivo 3. Se quitó.
  - Un alcance aparece repetido (el del escenario con paneles). En el Word no está repetido; en la carta sí.

## 2. Hardware

| Pieza | Dato | Fuente |
|---|---|---|
| Controladora | Pixhawk 2.4.8 (fmuv3), ArduPilot (ArduCopter) 4.7.0, Quad X | `docs/hardware.md`, `docs/pixhawk.md` |
| Computadora | NVIDIA Jetson Orin Nano, Ubuntu 24.04, L4T R39.2.1 (JetPack 7), Python 3.12 | `docs/jetson.md` |
| Cámara | Webcam USB Sonix 640×480, 30 cuadros/s, HFOV medido 38.9°, VFOV ≈ 29.7°, sin filtro IR-cut | `docs/hardware.md` |
| Detector | YOLO26n en TensorRT FP16, 9–11 ms por cuadro con seguimiento | `docs/hardware.md` |
| LiDAR | Benewake TF03 (UART) por USB-TTL PL2303, 100 Hz | `docs/hardware.md` |
| Estabilizador | BaseCam SimpleBGC 2 ejes; pitch por PWM desde AUX1 (`DO_SET_SERVO`), `pwm = 1500 + θ·500/45`, límite ±45° | `docs/hardware.md`, D-003, D-014 |
| Enlace | MAVLink 2 por TELEM2 a **115200** baudios, sin cable de 5 V | D-004 |
| Energía | LiPo 4S 6200 mAh; buck a 12.02 V para la Jetson; failsafe 13.5 V / 13.2 V | `docs/hardware.md`, Word 2.2.3 |
| Chasis y motores | ZD550 en X, 4 × 2212-920 KV, ESC 40 A OPTO | Word 2.2.1 |
| Radio | Futaba T14SG; CH5 modo de vuelo; CH8 parada de emergencia (`RC8_OPTION = 31`); CH7 propuesto para "modo experimental" | `docs/pixhawk.md`, `docs/PLAN_MINIMO_FISICO.md` |

**Datos que no coinciden entre documentos (decidir con la sesión física):**
- Modos en CH5: `docs/pixhawk.md` dice STABILIZE / ALT_HOLD / GUIDED; el plan del mínimo propone ALT_HOLD / LOITER / LAND,
  con CH7 como interruptor del modo experimental.
- El Word decía 921600 baudios y Ubuntu 20.04: ya corregido a 115200 y Ubuntu 24.04.

## 3. Lo verificado en banco (sin vuelo)

| Prueba | Resultado | Fecha / fuente |
|---|---|---|
| Arranque de la Jetson con alimentación de a bordo | Sin reinicios | Word, Tabla 14 |
| Cámara + detector con personas en movimiento | Recuadro estable con ID | Word, Tabla 14 |
| LiDAR TF03 | 100 Hz por USB-TTL | 2026-10-06, `PLAN_MINIMO_FISICO.md` §4 |
| Enlace MAVLink | `DO_SET_SERVO` 10 de 10 con ACK | `PLAN_MINIMO_FISICO.md` §4 |
| Lectura de ángulos de la BaseCam | Funciona por USB; el control por UART no (firmware 2.2) | `docs/hardware.md` |

## 4. El decisor de IA (MLP) del mínimo indispensable

Fuente: `simulacion/informes/minimo_tesis_decisor_ia.md` y `simulacion/minimo_tesis/README.md`.

- MLP de scikit-learn, capas ocultas 32 y 16 (ReLU), 15 entradas, una salida: probabilidad de que en 3 s haya un choque
  o una persona a menos de 2 m si el piloto sigue igual.
- Interviene si la probabilidad pasa de **0.7 durante 2 cuadros seguidos** (elegidos con mundos de validación).
- Datos: 2 551 725 cuadros de entrenamiento (13 % con riesgo), 499 021 de validación, 533 085 de prueba, separados por
  semillas. Etiquetado automático con la verdad del simulador.
- Prueba, por cuadro: AUC-ROC 0.974; precisión media 0.914; exhaustividad 74.4 %; precisión 97.0 %; falsos positivos 0.3 %.
- **No es PPO.** Es aprendizaje supervisado. La política PPO del seguimiento es trabajo complementario o futuro.

## 5. Resultados de simulación (con su experimento de origen)

> No mezclar experimentos. Son tres pruebas distintas.

**A. Protocolo del comité** (`minimo_tesis_protocolo.md`, 13 variantes × 100 vuelos = 1300 vuelos)
- Éxito con el sistema: 100.0 % [99.7, 100.0]. Operador solo: 23 % [21, 25] de vuelos seguros.
- 0 activaciones falsas en los 300 vuelos que no debían activarlo.
- 28 paradas del operador, todas con la persona que corre hacia el dron; 0 choques.
- Riesgo → comando: 0.06 a 0.12 s. Comando → salir del alcance de una persona: 0.40 s.

**B. Discriminación** (`minimo_tesis_decisor_ia.md` §3, 5 escenarios × 100 vuelos por decisor)
- Éxito: reglas 91.2 % [88.4, 93.4]; IA sola 95.8 % [93.7, 97.2]; IA + envolvente **94.0 % [91.6, 95.8]**.
- Activaciones innecesarias en los 1800 vuelos del protocolo + discriminación: reglas 44, IA + envolvente 30.
- McNemar exacto (pares, calculado el 2026-10-12 con `minimo_tesis_decisor_ia.csv`): 16 vuelos en que acierta la IA y
  fallan las reglas, 2 al revés, **p = 0.0013**. La prueba de dos proporciones sin emparejar daría p = 0.09: no es la
  adecuada porque los decisores enfrentan los mismos mundos.

**C. Mundos de prueba** (`minimo_tesis_decisor_ia.md` §2, 3840 vuelos en 60 mundos nunca vistos)
- Choques: reglas 39, IA + envolvente 28 (p ≈ 0.18 sin emparejar: **no significativo**).
- Vuelos con persona a < 2 m por debajo de 3.30 m: 420 → 218 (p < 0.001).
- Riesgos no evitados: 92 → 67 (p ≈ 0.045). Activaciones innecesarias: 137 → 67.
- Con el piloto a ≤ 4 m/s: 24 riesgos no evitados con IA + envolvente frente a 22 con reglas (prácticamente igual).

**D. Robustez** (`minimo_tesis_protocolo.md`)
- Ninguna degradación realista hace fallar el protocolo a ≤ 4 m/s.
- Velocidad máxima segura con reglas: 11 m/s (panel), 4 m/s (persona quieta), 10 m/s (persona que corre); con 300 ms de
  latencia, 7 m/s. Con IA + envolvente, persona quieta 12 m/s.
- Límite de la percepción: con solo cabeza y hombros visibles (15 % del alto) aparecen choques.

## 6. De dónde sale cada número

| Valor | Origen | ¿Tiene fuente externa? |
|---|---|---|
| 2.3 m (altura del piloto) | Con −5° de inclinación el LiDAR toca el suelo a 26 m; el panel de 2.6 m queda por encima del rayo | Falta documentar la decisión |
| 3.30 m (altura segura) | Burbuja de una persona: 1.0 m horizontal y 2.6 m de alto, más 0.7 m de margen | **Falta** fuente de alcance de pie y salto |
| 1.72 m (estatura supuesta) | Modelo de población (σ 0.07 m, 1.58–1.88 m) | Meisel y Vega (2007): 170.6 cm, hombres nacidos en 1980–1984 |
| 2 m (zona de riesgo) | Brazo 1.0 m + radio del dron 0.4 m + 0.6 m | Diseño propio |
| 3 m (bloqueo frontal) | d_safe a ≈ 1.4 m/s; regla dura 5 (D-008) | Diseño propio verificado en simulación |
| 8 m (árbitro) | (8 − 2)/3.3 m/s = 1.8 s > 0.5 s que necesita el sistema | Diseño propio (D-008) |
| d_safe = v·0.5 + v²/(2·2.5) + 1.5 + 0.4 | Reacción + frenado + margen + radio | 2.5 m/s² = `LOIT_BRK_ACCEL` por defecto (confirmar en la Pixhawk) |
| 0.7 y 2 cuadros | Elegidos en lazo cerrado con validación | `decision_entrenamiento.json` |
| 100 ms | Retardo conservador de sensores | Medido: inferencia 9–11 ms, cuadro 33 ms |
| 150 ms | Criterio de latencia en banco | `PLAN_MINIMO_FISICO.md` paso 3 |
| 10 repeticiones | Wilson 10/10 → [72 %, 100 %] | Wilson (1927). Para afirmar ≥ 90 % harían falta 35/35 |
| 4 m/s (`LOIT_SPEED`) | Velocidad máxima segura con persona quieta (reglas) | `minimo_tesis_protocolo.md` |
| Escala 1–10 de Pugh | Resolución; cada nivel anclado a un descriptor; el orden no cambia con 1–5 (Tabla N2) | Pugh (1991); Ulrich y Eppinger (2016) |

## 7. Lo que falta medir (pasos del `docs/PLAN_MINIMO_FISICO.md`)

1. Paso 2: que la BaseCam alimentada lea el pulso de AUX1.
2. Paso 3: cambio a GUIDED y retoma del piloto en banco; latencia riesgo → comando medida (< 150 ms).
3. Paso 4: datos reales en carrito con conos (escenarios a–e). Sirve para comparar el modelo de sensores con la realidad.
4. Paso 5: decisor en modo sombra con esos datos.
5. Pasos 6 y 7: vuelos y protocolo de campo, 10 repeticiones por escenario.
6. Masa de despegue (para la relación empuje–peso).
7. Fotos del montaje, del banco y del campo (son las figuras del capítulo 3).
