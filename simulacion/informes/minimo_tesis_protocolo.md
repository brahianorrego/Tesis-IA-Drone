# Protocolo del comité · mínimo indispensable

Generado por `minimo_tesis/protocolo_comite.py` · 100 vuelos por variante · semilla base 2026 · 2026-10-10 · 315 s

El piloto avanza de frente en línea recta (o deja el dron quieto en el modo estático). El sistema solo interviene ante el riesgo definido, con **DETENCIÓN + ASCENSO VERTICAL** a 3.30 m, y espera al operador. Sensores con ruido y retardo de 100 ms; control de ArduPilot modelado (copias congeladas en `minimo_tesis/`). Entre corchetes, el intervalo de confianza del 95 % (Wilson para porcentajes; media ± 1.96·σ/√n para tiempos).

## Éxito

Éxito: si el escenario pide activarse, se activa y no choca; si no lo pide, no se activa y no choca. *Éxito sin ayuda del operador*: lo mismo y, además, el operador no apretó la parada en ningún momento (la diferencia entre las dos columnas son los vuelos en que el operador apretó a la vez que el sistema). *Vuelo seguro sin el sistema*: el mismo vuelo con el operador solo, sin choque y sin que haya tenido que apretar la parada (la parada la aprieta al ver un choque a menos de 2.0 s, con 0.7 s de reacción).

| Escenario | ¿Debe activarse? | Éxito con el sistema | Éxito sin ayuda del operador | Vuelo seguro sin el sistema | Choques con / sin | Paradas del operador con / sin | Operador antes que el sistema |
|---|:---:|---:|---:|---:|---:|---:|---:|
| a) Panel fijo, avance a 1 m/s | sí | 100 % [96, 100] | 100 % [96, 100] | 0 % [0, 4] | 0 / 2 | 0 / 100 | 0 |
| a) Panel fijo, avance a 2 m/s | sí | 100 % [96, 100] | 100 % [96, 100] | 0 % [0, 4] | 0 / 0 | 0 / 100 | 0 |
| a) Panel fijo, avance a 3 m/s | sí | 100 % [96, 100] | 100 % [96, 100] | 0 % [0, 4] | 0 / 0 | 0 / 100 | 0 |
| a) Panel fijo, avance a 4 m/s | sí | 100 % [96, 100] | 100 % [96, 100] | 0 % [0, 4] | 0 / 0 | 0 / 100 | 0 |
| b) Persona quieta, avance a 1.5 m/s | sí | 100 % [96, 100] | 100 % [96, 100] | 0 % [0, 4] | 0 / 1 | 0 / 100 | 0 |
| b) Persona quieta, avance a 3.0 m/s | sí | 100 % [96, 100] | 100 % [96, 100] | 0 % [0, 4] | 0 / 0 | 0 / 100 | 0 |
| c) Persona de frente que camina (1.4 m/s), avance a 1 m/s | sí | 100 % [96, 100] | 100 % [96, 100] | 0 % [0, 4] | 0 / 99 | 0 / 100 | 0 |
| c) Persona de frente que corre (3.3 m/s), avance a 1 m/s | sí | 100 % [96, 100] | 72 % [63, 80] | 0 % [0, 4] | 0 / 98 | 28 / 100 | 28 |
| d) Persona que cruza lejos y camina (1.4 m/s), avance a 1 m/s | no | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 | 0 / 0 | 0 |
| d) Persona que cruza lejos y corre (3.3 m/s), avance a 1 m/s | no | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 | 0 / 0 | 0 |
| e) Modo estático: persona que viene y camina (1.4 m/s) | sí | 100 % [96, 100] | 100 % [96, 100] | 0 % [0, 4] | 0 / 100 | 0 / 100 | 0 |
| e) Modo estático: persona que viene y corre (3.3 m/s) | sí | 100 % [96, 100] | 100 % [96, 100] | 0 % [0, 4] | 0 / 100 | 0 / 100 | 0 |
| e) Modo estático: persona que pasa de lado a 5 m (1.4 m/s) | no | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 | 0 / 0 | 0 |

## Activaciones y eventos de riesgo

Verdadera: se activó y hubo riesgo real (medido con la verdad del simulador, sin ruido). Falsa: se activó sin riesgo real. Eventos: veces que empieza una situación de riesgo real en el vuelo.

| Escenario | Vuelos con riesgo real | Eventos de riesgo (media) | Activaciones verdaderas | Activaciones falsas | Riesgo real sin activación |
|---|---:|---:|---:|---:|---:|
| a) Panel fijo, avance a 1 m/s | 100 | 1.02 | 100 % [96, 100] | 0 % [0, 4] | 0 |
| a) Panel fijo, avance a 2 m/s | 100 | 1.40 | 100 % [96, 100] | 0 % [0, 4] | 0 |
| a) Panel fijo, avance a 3 m/s | 100 | 1.69 | 100 % [96, 100] | 0 % [0, 4] | 0 |
| a) Panel fijo, avance a 4 m/s | 100 | 1.49 | 100 % [96, 100] | 0 % [0, 4] | 0 |
| b) Persona quieta, avance a 1.5 m/s | 100 | 1.00 | 100 % [96, 100] | 0 % [0, 4] | 0 |
| b) Persona quieta, avance a 3.0 m/s | 100 | 1.03 | 100 % [96, 100] | 0 % [0, 4] | 0 |
| c) Persona de frente que camina (1.4 m/s), avance a 1 m/s | 100 | 1.00 | 100 % [96, 100] | 0 % [0, 4] | 0 |
| c) Persona de frente que corre (3.3 m/s), avance a 1 m/s | 100 | 1.00 | 100 % [96, 100] | 0 % [0, 4] | 0 |
| d) Persona que cruza lejos y camina (1.4 m/s), avance a 1 m/s | 0 | 0.00 | 0 % [0, 4] | 0 % [0, 4] | 0 |
| d) Persona que cruza lejos y corre (3.3 m/s), avance a 1 m/s | 0 | 0.00 | 0 % [0, 4] | 0 % [0, 4] | 0 |
| e) Modo estático: persona que viene y camina (1.4 m/s) | 100 | 1.00 | 100 % [96, 100] | 0 % [0, 4] | 0 |
| e) Modo estático: persona que viene y corre (3.3 m/s) | 100 | 1.00 | 100 % [96, 100] | 0 % [0, 4] | 0 |
| e) Modo estático: persona que pasa de lado a 5 m (1.4 m/s) | 0 | 0.00 | 0 % [0, 4] | 0 % [0, 4] | 0 |

## Latencias (s)

Riesgo → comando: desde que el riesgo es real hasta que el sistema manda detenerse (negativo: se adelantó por la predicción del acercamiento). Comando → frenado efectivo: hasta que la rapidez de avance cae por debajo de 0.3 m/s. Comando → fuera de alcance: hasta pasar los 2.6 m de altura. Distancia mínima: al panel, la holgura (sin el radio del dron); a la persona, la horizontal mientras el dron estaba a su alcance (por debajo de 2.6 m).

| Escenario | Riesgo → comando | Comando → frenado efectivo | Comando → fuera de alcance | Distancia mínima (m) |
|---|---:|---:|---:|---:|
| a) Panel fijo, avance a 1 m/s | 0.09 [0.08, 0.10] | 0.59 [0.58, 0.60] | 0.40 [0.40, 0.40] | 1.77 [1.73, 1.82] |
| a) Panel fijo, avance a 2 m/s | 0.09 [0.08, 0.11] | 0.90 [0.89, 0.90] | 0.40 [0.40, 0.40] | 3.14 [3.09, 3.18] |
| a) Panel fijo, avance a 3 m/s | 0.10 [0.09, 0.11] | 1.11 [1.11, 1.12] | 0.40 [0.40, 0.40] | 4.34 [4.29, 4.39] |
| a) Panel fijo, avance a 4 m/s | 0.10 [0.09, 0.11] | 1.39 [1.38, 1.39] | 0.40 [0.40, 0.40] | 5.35 [5.30, 5.40] |
| b) Persona quieta, avance a 1.5 m/s | 0.08 [0.03, 0.12] | 0.73 [0.72, 0.74] | 0.40 [0.40, 0.40] | 7.27 [7.20, 7.33] |
| b) Persona quieta, avance a 3.0 m/s | 0.10 [0.07, 0.12] | 1.12 [1.11, 1.13] | 0.40 [0.40, 0.40] | 6.44 [6.38, 6.51] |
| c) Persona de frente que camina (1.4 m/s), avance a 1 m/s | 0.06 [0.03, 0.09] | 0.58 [0.58, 0.59] | 0.40 [0.40, 0.40] | 6.82 [6.75, 6.89] |
| c) Persona de frente que corre (3.3 m/s), avance a 1 m/s | 0.11 [0.10, 0.13] | 0.58 [0.57, 0.59] | 0.40 [0.40, 0.40] | 5.65 [5.57, 5.72] |
| d) Persona que cruza lejos y camina (1.4 m/s), avance a 1 m/s | — | — | — | 9.67 [9.54, 9.80] |
| d) Persona que cruza lejos y corre (3.3 m/s), avance a 1 m/s | — | — | — | 16.13 [16.03, 16.22] |
| e) Modo estático: persona que viene y camina (1.4 m/s) | 0.11 [0.06, 0.16] | — (quieto) | 0.40 [0.40, 0.40] | 7.21 [7.14, 7.28] |
| e) Modo estático: persona que viene y corre (3.3 m/s) | 0.12 [0.09, 0.14] | — (quieto) | 0.40 [0.40, 0.40] | 6.12 [6.05, 6.20] |
| e) Modo estático: persona que pasa de lado a 5 m (1.4 m/s) | — | — (quieto) | — | 5.00 [4.94, 5.06] |

## Resumen

- Éxito global con el sistema: 100.0 % [99.7, 100.0] de 1300 vuelos. Vuelos seguros sin el sistema (operador solo): 23 % [21, 25].
- Paradas de emergencia del operador con el sistema: 28 de 1300 vuelos (c_frente_corre: 28); terminaron en choque: 0. Con una persona que corre hacia el dron el acercamiento es tan rápido que el tope de 8 m de la regla dura deja menos de 2 s, y un operador atento aprieta a la vez que el sistema.
- Activaciones falsas en los escenarios que no deben activarse (d y paso de lado): 0 de 300.

## Condiciones degradadas

Los mismos escenarios con una degradación a la vez y una combinada, 100 vuelos cada uno, SIN reajustar el sistema (sus umbrales suponen 100 ms de latencia y sensores nominales). Recall de YOLO: tope de la probabilidad de detección por cuadro. Oclusión: algo tapa el resto del cuerpo y la caja sale cortada (la distancia sale de los hombros). LiDAR: ruido ×3 y 5 % de lecturas sin retorno. Viento: de cola (empuja hacia el obstáculo), con ráfagas de ±1 m/s.

### Éxito por escenario (%)

| Escenario | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | C11 | C12 | C13 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a) Panel fijo, avance a 1 m/s | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| a) Panel fijo, avance a 2 m/s | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| a) Panel fijo, avance a 3 m/s | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| a) Panel fijo, avance a 4 m/s | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| b) Persona quieta, avance a 1.5 m/s | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| b) Persona quieta, avance a 3.0 m/s | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| c) Persona de frente que camina (1.4 m/s), avance a 1 m/s | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| c) Persona de frente que corre (3.3 m/s), avance a 1 m/s | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| d) Persona que cruza lejos y camina (1.4 m/s), avance a 1 m/s | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| d) Persona que cruza lejos y corre (3.3 m/s), avance a 1 m/s | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| e) Modo estático: persona que viene y camina (1.4 m/s) | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| e) Modo estático: persona que viene y corre (3.3 m/s) | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| e) Modo estático: persona que pasa de lado a 5 m (1.4 m/s) | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |

Condiciones: **C0** Nominal; **C1** YOLO recall 0.85 (sol de frente); **C2** YOLO recall 0.70 (desenfoque); **C3** Oclusión: medio cuerpo visible; **C4** Oclusión: solo torso visible; **C5** LiDAR ruido ×3 y 5 % sin retorno; **C6** Latencia total 200 ms; **C7** Latencia total 300 ms; **C8** Viento de cola 3 m/s con ráfagas; **C9** Viento de cola 5 m/s con ráfagas; **C10** Combinada: recall 0.85 + medio cuerpo + LiDAR + 200 ms + viento 4 m/s; **C11** Extrema: YOLO recall 0.40; **C12** Extrema: solo cabeza y hombros (15 % del alto); **C13** Extrema: latencia total 500 ms. (ch.: vuelos con choque; f.: activaciones falsas.)

### Hasta dónde funciona: velocidad de avance máxima segura (m/s)

Barrido de 1 a 12 m/s, 100 vuelos por velocidad. Segura: esa velocidad y todas las menores cumplen el criterio en al menos el 95 % de los vuelos. El criterio es **detenerse con margen**, más exigente que no chocar: panel, holgura de 0.5 m sin pasarle por encima (un muro real puede ser más alto); persona quieta, detenerse a 2 m o más; persona que corre hacia el dron (que la velocidad es del dron), estar fuera de su alcance antes de que llegue a 2 m. El dron parte de más lejos para llegar a crucero antes del alcance útil del LiDAR.

| Condición | Panel fijo | Persona quieta | Persona de frente corriendo | Primera falla (vuelos con margen / choques) |
|---|---:|---:|---:|---|
| C0 Nominal | 11 | 4 | 10 | panel fijo a 12 m/s: 1/100, 0 ch.; persona quieta a 5 m/s: 80/100, 0 ch.; persona de frente corriendo a 11 m/s: 81/100, 0 ch. |
| C1 YOLO recall 0.85 (sol de frente) | 11 | 4 | 10 | panel fijo a 12 m/s: 1/100, 0 ch.; persona quieta a 5 m/s: 80/100, 0 ch.; persona de frente corriendo a 11 m/s: 82/100, 0 ch. |
| C2 YOLO recall 0.70 (desenfoque) | 11 | 4 | 10 | panel fijo a 12 m/s: 1/100, 0 ch.; persona quieta a 5 m/s: 80/100, 0 ch.; persona de frente corriendo a 11 m/s: 87/100, 0 ch. |
| C3 Oclusión: medio cuerpo visible | 11 | 4 | 10 | panel fijo a 12 m/s: 1/100, 0 ch.; persona quieta a 5 m/s: 80/100, 0 ch.; persona de frente corriendo a 11 m/s: 87/100, 0 ch. |
| C4 Oclusión: solo torso visible | 11 | 4 | 10 | panel fijo a 12 m/s: 1/100, 0 ch.; persona quieta a 5 m/s: 82/100, 0 ch.; persona de frente corriendo a 11 m/s: 84/100, 0 ch. |
| C5 LiDAR ruido ×3 y 5 % sin retorno | 11 | 4 | 10 | panel fijo a 12 m/s: 1/100, 0 ch.; persona quieta a 5 m/s: 80/100, 0 ch.; persona de frente corriendo a 11 m/s: 81/100, 0 ch. |
| C6 Latencia total 200 ms | 11 | 4 | 9 | panel fijo a 12 m/s: 0/100, 0 ch.; persona quieta a 5 m/s: 77/100, 0 ch.; persona de frente corriendo a 10 m/s: 70/100, 1 ch. |
| C7 Latencia total 300 ms | 10 | 4 | 7 | panel fijo a 11 m/s: 29/100, 0 ch.; persona quieta a 5 m/s: 77/100, 0 ch.; persona de frente corriendo a 8 m/s: 82/100, 0 ch. |
| C8 Viento de cola 3 m/s con ráfagas | 11 | 4 | 10 | panel fijo a 12 m/s: 4/100, 0 ch.; persona quieta a 5 m/s: 68/100, 0 ch.; persona de frente corriendo a 11 m/s: 86/100, 0 ch. |
| C9 Viento de cola 5 m/s con ráfagas | 11 | 4 | 10 | panel fijo a 12 m/s: 7/100, 0 ch.; persona quieta a 5 m/s: 61/100, 0 ch.; persona de frente corriendo a 11 m/s: 87/100, 0 ch. |
| C10 Combinada: recall 0.85 + medio cuerpo + LiDAR + 200 ms + viento 4 m/s | 11 | 4 | 8 | panel fijo a 12 m/s: 0/100, 0 ch.; persona quieta a 5 m/s: 64/100, 0 ch.; persona de frente corriendo a 9 m/s: 93/100, 0 ch. |
| C11 Extrema: YOLO recall 0.40 | 11 | 4 | 7 | panel fijo a 12 m/s: 1/100, 0 ch.; persona quieta a 5 m/s: 80/100, 0 ch.; persona de frente corriendo a 8 m/s: 94/100, 2 ch. |
| C12 Extrema: solo cabeza y hombros (15 % del alto) | 11 | 4 | 0 | panel fijo a 12 m/s: 1/100, 0 ch.; persona quieta a 5 m/s: 81/100, 0 ch.; persona de frente corriendo a 1 m/s: 93/100, 2 ch. |
| C13 Extrema: latencia total 500 ms | 10 | 4 | 5 | panel fijo a 11 m/s: 0/100, 0 ch.; persona quieta a 5 m/s: 77/100, 0 ch.; persona de frente corriendo a 6 m/s: 78/100, 0 ch. |

### Lectura

- **A las velocidades del protocolo (hasta 4 m/s) ninguna degradación realista lo hace fallar.** No es casualidad: el riesgo se evalúa 10 veces por segundo durante los ~2 s que la persona está entre 8 m y el punto de frenado, así que perder el 30 % de los cuadros (recall 0.70) casi nunca deja sin detección más de 0.3 s; y el LiDAR toca el panel en decenas de lecturas seguidas, así que un 5 % sin retorno no cambia nada. Por eso los límites se buscan subiendo la velocidad y con las condiciones extremas.
- **Panel:** el límite lo pone el alcance útil del LiDAR. Con la cámara a −5° desde 2.3 m el rayo toca el suelo a ~26 m, y por encima de ~11 m/s la distancia de frenado más el margen no cabe en ese alcance. La latencia de 300 ms lo baja a 10 m/s.
- **Persona quieta:** el límite (4 m/s) lo pone la regla dura de los 8 m, no la percepción: aunque la vea desde lejos, el sistema no se activa antes de los 8 m, y por encima de 4 m/s no alcanza a detenerse a 2 m (sube y le pasa por encima, fuera de su alcance, sin chocar, pero no se detiene con margen). El viento de cola lo empeora (menos vuelos con margen a 5 m/s). Si el comité acepta activarse antes con una persona inmóvil al frente, este límite sube.
- **Persona que corre hacia el dron:** lo que más pesa es la latencia (de 10 m/s con 100 ms a 7 m/s con 300 ms).
- **Condiciones extremas (C11-C13), donde se rompe:** con recall 0.40 o latencia de 500 ms aparecen las primeras fallas con la persona que corre hacia el dron (velocidad segura 7 y 5 m/s). Con solo cabeza y hombros a la vista (15 % del alto) la detección llega tarde incluso a 1 m/s y aparecen choques (2 de 100 en el barrido; en la tabla de escenarios, con otras semillas, 0 de 100: el mismo orden de magnitud). Ese es el límite de la percepción: el sistema necesita ver al menos un tercio del cuerpo.
- **Recomendación operativa:** limitar en ArduPilot la velocidad de avance del piloto (LOIT_SPEED) a la menor velocidad segura de la condición esperada; con personas en la zona, 4 m/s.

## Cómo se reproduce en campo

El mismo protocolo, con el dron real, en un campo abierto y plano, sin público y con la geocerca de ArduPilot activa:

1. **Panel (a):** un panel de 2 × 2.6 m (cartón pluma o lona sobre un marco) a 20 m del punto de partida. El piloto avanza en línea recta a 1, 2 y 3 m/s (velocidad limitada con LOIT_SPEED), 10 repeticiones por velocidad.
2. **Persona quieta (b):** primero un maniquí o una silueta de 1.7 m en el lugar del panel. Una persona real solo después de que (a) y (b) con maniquí den 10 de 10, y siempre con la parada (CH8) en la mano del operador.
3. **Persona que se acerca (c, e):** un voluntario camina hacia el dron, que vuela en estático a 2.3 m o avanza a 1 m/s; se empieza desde 15 m, 10 repeticiones. Correr hacia el dron solo con maniquí sobre un carro.
4. **Persona que cruza lejos (d):** cruza a 12 m al frente, caminando y trotando, 10 repeticiones de cada una.
5. **Condiciones:** repetir (a) y (b) con sol de frente y con viento de más de 3 m/s, si se dan.

Qué se mide con el registro de la Jetson (una línea por cuadro con la marca de tiempo del reloj del sistema): detección de YOLO (caja, confianza, distancia estimada), lectura del LiDAR, decisión de riesgo y comando enviado por MAVLink; y del log de ArduPilot (DataFlash): velocidad, altura, actitud y canal CH8. Con eso se calculan las mismas métricas: éxito, activaciones verdaderas y falsas, latencia riesgo → comando (Jetson) y comando → frenado efectivo (DataFlash), distancia mínima (marcas en el suelo y video lateral, o RTK si se dispone) e intervenciones del operador (CH8). Con 10 repeticiones, 10 de 10 tiene un intervalo de confianza del 95 % de [72 %, 100 %]: el campo muestra que funciona y valida la latencia y la distancia de frenado; la tasa fina la da la simulación.

## Límites del protocolo

- Una sola persona o un solo panel por vuelo, suelo plano, panel de 2.6 m (por debajo del rayo del LiDAR desde 2.3 m) y viento suave. No hay lluvia, noche ni oclusiones parciales por otros objetos.
- El detector es un modelo estadístico de YOLO (probabilidad por distancia, ruido, estatura supuesta de 1.72 m y caja cortada); no son imágenes reales. La validación de campo debe repetir los escenarios a, b y d.
- La parada del operador es un modelo (ve el choque a 2 s y reacciona en 0.7 s).

Datos crudos: `minimo_tesis_protocolo.csv` (un renglón por vuelo). Repetición en el visor: selector "Mínimo indispensable · protocolo del comité".
