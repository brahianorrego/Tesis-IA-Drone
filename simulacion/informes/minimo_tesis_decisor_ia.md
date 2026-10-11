# Decisor IA del mínimo indispensable (fase G)

Generado por `minimo_tesis/evaluar_decisores.py` · 100 vuelos por variante · semilla base 2026 · 2026-10-11 · 1131 s

Se comparan tres formas de DECIDIR la intervención (detención y ascenso), con los mismos sensores (ruido y retardo de 100 ms) y el mismo control de ArduPilot:

- **Reglas:** umbrales fijos (obstáculo por distancia de frenado y tiempo al choque; persona según el árbitro).
- **IA sola:** un clasificador MLP decide con las entradas que tiene la Jetson.
- **IA + envolvente:** la misma IA dentro de las reglas duras: el bloqueo frontal (LiDAR < 3 m avanzando) y la persona a menos de 3 m mandan siempre, y el ascenso por una persona solo lo autoriza el árbitro (< 3 m, o < 8 m acercándose); antes, la IA solo puede DETENER. Es la regla dura 5 tal como está escrita (el árbitro autoriza; el LiDAR y la parada mandan) y es la versión que iría al dron.
- **IA + envolvente estricta:** además, una persona a menos de 3 m obliga a detenerse (más estricto que la regla).

## 1. El clasificador

- Arquitectura: MLP de scikit-learn 32-16, ReLU; 15 entradas: detectada, alto_caja, ancho_caja, area_caja, angulo_abs, d_angulo_abs, confianza, cuadros_seguidos, lidar, lidar_util, v_propia, d_seguimiento, v_acercamiento, v_lateral, t_sin_deteccion.
- Datos: vuelos sin intervención en mundos aleatorios (velocidades de 0 a 8 m/s; personas quietas, que vienen, que cruzan, paralelas o al azar; panel o no; sensores degradados al azar). Etiqueta automática con la verdad del simulador: "si el piloto sigue igual, ¿en los próximos 3 s choca o una persona queda a menos de 2 m?".
- Separación por semillas (mundos distintos): entrenamiento 2551725 cuadros (13 % con riesgo), validación 499021, prueba 533085 (12 % con riesgo).
- Umbral 0.7 y 2 cuadro(s) seguidos, elegidos en lazo cerrado sobre mundos de VALIDACIÓN (no con este protocolo): el mínimo de activaciones innecesarias sin dejar pasar más riesgos que las reglas.

Desempeño en la PRUEBA (mundos nunca vistos), por cuadro:

| AUC-ROC | Precisión media (AP) | Exhaustividad | Precisión | Tasa de falsos positivos |
|---:|---:|---:|---:|---:|
| 0.974 | 0.914 | 74.4 % | 97.0 % | 0.3 % |

Matriz de confusión (prueba, por cuadro, con el umbral elegido):

| | Predice CONTINUAR | Predice DETENER |
|---|---:|---:|
| Sin riesgo real | 470330 | 1420 |
| Con riesgo real | 15716 | 45619 |

Curvas ROC y precisión-exhaustividad: `minimo_tesis_decisor_curvas.png`. La exhaustividad por cuadro no es la seguridad: un riesgo dura muchos cuadros y basta uno (o k seguidos) para intervenir; la seguridad se mide abajo, en lazo cerrado.

## 2. Mundos de prueba en lazo cerrado (la comparación menos sesgada)

3840 vuelos en 60 mundos aleatorios de PRUEBA (semillas que no se usaron ni para entrenar ni para elegir el umbral): velocidades de 0 a 8 m/s, todo tipo de personas, paneles y sensores degradados al azar. 2043 vuelos (53 %) habrían tenido riesgo físico sin sistema.

| Decisor | Riesgos no evitados | Choques | Persona a < 2 m bajo 3.30 m (vuelos) | Distancia mínima a personas bajo 3.30 m (p1 / mediana, m) | Activaciones innecesarias | Tiempo detenido sin necesidad (s) | Tiempo detenido total (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sin sistema | 2043 | 1681 | 1488 | 0.08 / 3.30 | — | — | — |
| Reglas | 92 (4.5 %) | 39 | 420 | 0.39 / 6.63 | 137 | 2358 | 42193 |
| IA sola | 62 (3.0 %) | 27 | 143 | 0.59 / 9.22 | 54 | 813 | 41914 |
| IA + envolvente | 67 (3.3 %) | 28 | 218 | 0.40 / 8.97 | 67 | 1082 | 42213 |
| IA + envolvente estricta | 67 (3.3 %) | 28 | 218 | 0.40 / 8.97 | 79 | 1326 | 42460 |
| IA + envolvente, ascenso sin veto del árbitro (solo referencia) | 61 (3.0 %) | 27 | 142 | 0.59 / 9.22 | 67 | 1082 | 42213 |

Por velocidad del piloto (vuelos con persona a < 2 m bajo 3.30 m / riesgos no evitados / choques):

| Decisor | Piloto ≤ 4 m/s (2212 vuelos) | Piloto > 4 m/s (1628 vuelos) |
|---|---:|---:|
| Sin sistema | 661 / 946 / 789 | 827 / 1097 / 892 |
| Reglas | 75 / 22 / 13 | 345 / 70 / 26 |
| IA sola | 43 / 25 / 11 | 100 / 37 / 16 |
| IA + envolvente | 45 / 24 / 11 | 173 / 43 / 17 |
| IA + envolvente estricta | 45 / 24 / 11 | 173 / 43 / 17 |
| IA + envolvente, ascenso sin veto del árbitro (solo referencia) | 42 / 24 / 11 | 100 / 37 / 16 |

Riesgo no evitado: con el decisor al mando, la persona igual quedó a menos de 2 m del dron (a su alcance) o el panel a menos de 0.5 m. Incluye los casos imposibles (un panel a 5 m con el dron a 8 m/s, una persona que corre hacia el dron desde muy cerca).

## 3. Protocolo del comité y escenarios de discriminación (nominal)

Éxito en el protocolo: si debe activarse, se activa y no choca; si no, no se activa y no choca. En los escenarios de discriminación (f) el éxito es la decisión correcta POR VUELO: activarse si y solo si en ese mismo vuelo, sin sistema, la persona habría quedado a menos de 2 m. Innecesarias: activaciones en vuelos que sin sistema no habrían tenido ese riesgo físico.

| Escenario | Éxito Reglas | Éxito IA sola | Éxito IA + envolvente | Éxito IA + envolvente estricta | Choques R/IA/IA+E/est. | Innecesarias R/IA/IA+E/est. | Riesgo → comando (s) R / IA / IA+E / est. |
|---|---:|---:|---:|---:|---:|---:|---:|
| a) Panel fijo, avance a 1 m/s | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0.09 / -0.81 / -0.81 / -0.81 |
| a) Panel fijo, avance a 2 m/s | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0.09 / -0.76 / -0.76 / -0.76 |
| a) Panel fijo, avance a 3 m/s | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0.10 / -0.71 / -0.71 / -0.71 |
| a) Panel fijo, avance a 4 m/s | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0.10 / -0.70 / -0.70 / -0.70 |
| b) Persona quieta, avance a 1.5 m/s | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0.08 / 1.51 / 1.51 / 1.51 |
| b) Persona quieta, avance a 3.0 m/s | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0.10 / -0.79 / -0.79 / -0.79 |
| c) Persona de frente que camina (1.4 m/s), avance a 1 m/s | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0.06 / -0.52 / -0.52 / -0.52 |
| c) Persona de frente que corre (3.3 m/s), avance a 1 m/s | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0.11 / -1.40 / -1.40 / -1.40 |
| d) Persona que cruza lejos y camina (1.4 m/s), avance a 1 m/s | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | — / — / — / — |
| d) Persona que cruza lejos y corre (3.3 m/s), avance a 1 m/s | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | — / — / — / — |
| e) Modo estático: persona que viene y camina (1.4 m/s) | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0.11 / 1.67 / 1.67 / 1.67 |
| e) Modo estático: persona que viene y corre (3.3 m/s) | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0.12 / -0.82 / -0.82 / -0.82 |
| e) Modo estático: persona que pasa de lado a 5 m (1.4 m/s) | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | — / — / — / — |
| f) Cruza 3-4 m por delante del dron y sigue (no debe activarse) | 95 % [89, 98] | 98 % [93, 99] | 98 % [93, 99] | 95 % [89, 98] | 0 / 0 / 0 / 0 | 5 / 2 / 2 / 5 | 0.10 / — / — / — |
| f) Cruza justo por donde pasa el dron (debe activarse) | 65 % [55, 74] | 86 % [78, 91] | 77 % [68, 84] | 65 % [55, 74] | 0 / 0 / 0 / 0 | 35 / 10 / 23 / 35 | 0.84 / 1.45 / 1.19 / 1.16 |
| f) Viene de frente, 3 m al costado de la trayectoria (no debe activarse) | 96 % [90, 98] | 95 % [89, 98] | 95 % [89, 98] | 95 % [89, 98] | 0 / 0 / 0 / 0 | 4 / 5 / 5 / 5 | -2.08 / -2.38 / -2.38 / -2.38 |
| f) Viene de frente, 1 m al costado (debe activarse) | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0.10 / -1.17 / -1.17 / -1.17 |
| f) Camina delante en el mismo sentido, más rápido que el dron (no debe activarse) | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 100 % [96, 100] | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | — / — / — / — |

| Total | Reglas | IA sola | IA + envolvente | IA + envolvente estricta |
|---|---:|---:|---:|---:|
| Éxito, 13 variantes del protocolo | 100.0 % [99.7, 100.0] | 100.0 % [99.7, 100.0] | 100.0 % [99.7, 100.0] | 100.0 % [99.7, 100.0] |
| Éxito, 5 de discriminación | 91.2 % [88.4, 93.4] | 95.8 % [93.7, 97.2] | 94.0 % [91.6, 95.8] | 91.0 % [88.2, 93.2] |
| Choques (todos) | 0 | 0 | 0 | 0 |
| Activaciones innecesarias (todos) | 44 | 17 | 30 | 45 |
| Tiempo detenido sin necesidad (s, todos) | 515 | 186 | 349 | 513 |
| Riesgos físicos omitidos (necesaria y no se activó) | 0 | 4 | 0 | 0 |
| Paradas del operador | 161 | 168 | 148 | 148 |
| Vuelos con persona a < 2 m bajo 3.30 m (todos) | 0 | 0 | 0 | 0 |

## 4. Condiciones degradadas

Por condición, sumando las 18 variantes (13 del protocolo + 5 de discriminación), 100 vuelos cada una: éxitos, choques e innecesarias.

| Condición | Reglas: éxito · choques · innec. | IA sola: éxito · choques · innec. | IA + envolvente: éxito · choques · innec. | IA + envolvente estricta: éxito · choques · innec. |
|---|---:|---:|---:|---:|
| C0 Nominal | 97.6 % · 0 · 44 | 98.8 % · 0 · 17 | 98.3 % · 0 · 30 | 97.5 % · 0 · 45 |
| C1 YOLO recall 0.85 (sol de frente) | 97.6 % · 0 · 43 | 98.7 % · 0 · 19 | 98.4 % · 0 · 28 | 97.6 % · 0 · 44 |
| C2 YOLO recall 0.70 (desenfoque) | 97.7 % · 0 · 42 | 98.7 % · 0 · 23 | 98.3 % · 0 · 30 | 97.6 % · 0 · 43 |
| C3 Oclusión: medio cuerpo visible | 97.1 % · 0 · 52 | 98.7 % · 0 · 20 | 97.8 % · 0 · 39 | 97.2 % · 0 · 51 |
| C4 Oclusión: solo torso visible | 97.1 % · 0 · 53 | 98.0 % · 0 · 35 | 97.3 % · 0 · 48 | 96.8 % · 0 · 58 |
| C5 LiDAR ruido ×3 y 5 % sin retorno | 97.6 % · 0 · 44 | 98.8 % · 0 · 17 | 98.3 % · 0 · 30 | 97.5 % · 0 · 45 |
| C6 Latencia total 200 ms | 97.6 % · 0 · 44 | 98.8 % · 0 · 17 | 98.3 % · 0 · 30 | 97.5 % · 0 · 45 |
| C7 Latencia total 300 ms | 97.6 % · 0 · 44 | 98.8 % · 0 · 17 | 98.3 % · 0 · 30 | 97.5 % · 0 · 45 |
| C8 Viento de cola 3 m/s con ráfagas | 97.2 % · 0 · 50 | 98.4 % · 0 · 23 | 98.3 % · 0 · 30 | 97.4 % · 0 · 46 |
| C9 Viento de cola 5 m/s con ráfagas | 97.2 % · 0 · 51 | 97.9 % · 0 · 30 | 98.1 % · 0 · 33 | 97.1 % · 0 · 52 |
| C10 Combinada: recall 0.85 + medio cuerpo + LiDAR + 200 ms + viento 4 m/s | 96.8 % · 0 · 57 | 98.6 % · 0 · 21 | 98.0 % · 0 · 35 | 97.0 % · 0 · 54 |
| C11 Extrema: YOLO recall 0.40 | 97.4 % · 0 · 45 | 97.5 % · 0 · 45 | 97.4 % · 0 · 46 | 96.9 % · 0 · 55 |
| C12 Extrema: solo cabeza y hombros (15 % del alto) | 96.9 % · 1 · 52 | 96.7 % · 2 · 57 | 96.5 % · 1 · 61 | 96.3 % · 0 · 65 |
| C13 Extrema: latencia total 500 ms | 97.6 % · 0 · 44 | 98.8 % · 0 · 17 | 98.3 % · 0 · 30 | 97.5 % · 0 · 45 |

## 5. Velocidad máxima segura (m/s, detenerse con margen en ≥ 95 %)

| Condición | Escenario | Reglas | IA sola | IA + envolvente | IA + envolvente estricta |
|---|---|---:|---:|---:|---:|
| C0 Nominal | Panel fijo | 11 | 12 | 12 | 12 |
| C0 Nominal | Persona quieta | 4 | 12 | 12 | 12 |
| C0 Nominal | Persona de frente corriendo | 10 | 12 | 12 | 12 |
| C7 Latencia total 300 ms | Panel fijo | 10 | 10 | 10 | 10 |
| C7 Latencia total 300 ms | Persona quieta | 4 | 10 | 10 | 10 |
| C7 Latencia total 300 ms | Persona de frente corriendo | 7 | 12 | 12 | 12 |
| C10 Combinada: recall 0.85 + medio cuerpo + LiDAR + 200 ms + viento 4 m/s | Panel fijo | 11 | 10 | 10 | 10 |
| C10 Combinada: recall 0.85 + medio cuerpo + LiDAR + 200 ms + viento 4 m/s | Persona quieta | 4 | 12 | 12 | 12 |
| C10 Combinada: recall 0.85 + medio cuerpo + LiDAR + 200 ms + viento 4 m/s | Persona de frente corriendo | 8 | 12 | 12 | 12 |
| C12 Extrema: solo cabeza y hombros (15 % del alto) | Panel fijo | 11 | 12 | 12 | 12 |
| C12 Extrema: solo cabeza y hombros (15 % del alto) | Persona quieta | 4 | 6 | 6 | 6 |
| C12 Extrema: solo cabeza y hombros (15 % del alto) | Persona de frente corriendo | 0 | 12 | 12 | 12 |

## 6. Lectura

- **Protocolo del comité (13 variantes):** los cuatro decisores cumplen el 100 %, sin choques y sin ninguna persona a menos de 2 m con el dron por debajo de 3.30 m. El protocolo no distingue entre ellos: sus escenarios son claros (panel o persona en la trayectoria, cruce lejano) y las reglas ya los resuelven.
- **Discriminación (personas cerca de la trayectoria que no van a chocar):** éxito por vuelo 91.2 % con las reglas, 95.8 % con la IA sola y 94.0 % con la IA + envolvente; activaciones innecesarias 44 / 17 / 30 y tiempo detenido sin necesidad 515 / 186 / 349 s. Riesgos omitidos: 0 / 4 / 0. La IA sola omitía riesgos con personas que entran de lado al campo de la cámara a 5-6 m; la salvaguarda geométrica de la envolvente (persona seguida que va a pasar a < 2 m en menos de 1.5 s) los recupera, a cambio de parte de las innecesarias.
- **La envolvente estricta** (persona a < 3 m obliga) vuelve a dar lo mismo que las reglas (45 innecesarias): las activaciones innecesarias de las reglas vienen justamente de personas que pasan a menos de 3 m sin llegar a 2 m. Por eso la regla dura 5 se aplica como está escrita: el árbitro autoriza, no obliga.
- **Anticipación (riesgo → comando, protocolo):** media 0.09 s con las reglas y -0.33 s con la IA + envolvente (negativo: la orden sale antes de que el riesgo, con los umbrales de las reglas, exista). La IA se adelanta casi en todos los escenarios; en los acercamientos lentos (persona quieta a 1.5 m/s, persona que camina hacia el dron quieto) decide más tarde que las reglas, pero igual con margen (sin choques ni personas a < 2 m).
- **Mundos de prueba (3840 vuelos nunca vistos):** con la IA + envolvente frente a las reglas: choques 39 → 28, riesgos no evitados 92 → 67, vuelos con una persona a < 2 m bajo 3.30 m 420 → 218, activaciones innecesarias 137 → 67 y tiempo detenido sin necesidad 2358 → 1082 s. Ninguno llega a cero: el conjunto incluye casos físicamente imposibles (panel a pocos metros con el dron a 8 m/s, persona que corre hacia el dron desde muy cerca).
- **Lo que NO mejora (honesto):** con el piloto a 4 m/s o menos (el LOIT_SPEED recomendado), la IA + envolvente deja 24 riesgos no evitados frente a 22 de las reglas (prácticamente igual), aunque 45 vuelos con persona a < 2 m bajo 3.30 m frente a 75: en la operación recomendada la mejora en seguridad es moderada y la ventaja más clara es la eficiencia (menos detenciones innecesarias). Por encima de 4 m/s la IA + envolvente deja 173 vuelos con persona a < 2 m y la IA sola 100: la diferencia es el veto del árbitro al ascenso (sube solo con la persona a < 8 m acercándose), que con acercamientos rápidos llega tarde; la variante de referencia sin ese veto da 100.
- **Condiciones degradadas (reglas → IA + envolvente):** YOLO recall 0.70 (desenfoque): éxito 97.7 → 98.3 %, innecesarias 42 → 30; Oclusión: medio cuerpo visible: éxito 97.1 → 97.8 %, innecesarias 52 → 39; Latencia total 200 ms: éxito 97.6 → 98.3 %, innecesarias 44 → 30; Combinada: recall 0.85 + medio cuerpo + LiDAR + 200 ms + viento 4 m/s: éxito 96.8 → 98.0 %, innecesarias 57 → 35. En las condiciones realistas la IA conserva su ventaja, sin choques. En la extrema de solo cabeza y hombros no: éxito 96.9 → 96.5 %, innecesarias 52 → 61, choques 1 → 1 (es el límite de la percepción para los dos).
- **Velocidad máxima segura (detenerse con margen):** con una persona quieta, 4 m/s con las reglas y 12 m/s con la IA + envolvente (la IA puede DETENER antes de los 8 m; las reglas no se activan antes); con una persona que corre hacia el dron, 10 → 12 m/s (con 300 ms de latencia, 7 → 12). Frente al panel son equivalentes (11 y 12 m/s; con la condición combinada la IA baja a 10 frente a 11 de las reglas).
- **Decisión pendiente (Brahian):** si el ascenso vertical de protección del mínimo cuenta como "evasión" (hoy lo veta el árbitro hasta los 8 m) o no. Con el LOIT_SPEED de 4 m/s recomendado el costo del veto es pequeño; por encima de 4 m/s es la principal fuente de personas a < 2 m.

## 7. Justificación del uso de IA en la decisión

En el mínimo indispensable del proyecto de grado, la inteligencia artificial no se limita a detectar personas: también decide si el dron debe intervenir. Esa decisión se modela como un problema de clasificación: a partir de las mediciones disponibles a bordo (la caja que entrega YOLO, la distancia del LiDAR, la velocidad estimada por ArduPilot y un seguimiento alfa-beta de la persona), un perceptrón multicapa estima la probabilidad de que, si el piloto mantiene su mando, en los próximos 3 s ocurra un choque o una persona quede a menos de 2 m del dron.

El uso de un modelo aprendido se justifica porque el riesgo depende de la combinación de varias magnitudes ruidosas (distancia estimada por el tamaño de la caja, rumbo, velocidad relativa, persistencia de la detección), y un conjunto de umbrales fijos debe elegir entre ser conservador, con detenciones innecesarias, o permisivo, con riesgos omitidos. El clasificador aprende esa frontera de decisión a partir de vuelos simulados etiquetados de forma automática con la verdad del simulador, sin intervención manual, y se evalúa en mundos que no participaron ni en el entrenamiento ni en la elección del umbral.

El aporte se observa en tres aspectos. Primero, en la discriminación: frente a personas que pasan cerca de la trayectoria sin riesgo real, el sistema con IA redujo las activaciones innecesarias de 44 a 30, y con ello el tiempo de misión perdido. Segundo, en la anticipación: la IA puede ordenar la detención antes del límite de 8 m que imponen las reglas, lo que eleva la velocidad de avance a la que el dron se detiene con margen frente a una persona inmóvil. En la simulación esa velocidad pasó de 4 m/s a 12 m/s. Tercero, en la operación con condiciones variadas: en 3840 vuelos de prueba los choques bajaron de 39 a 28 y los casos con una persona a menos de 2 m del dron por debajo de la altura segura, de 420 a 218.

La IA no reemplaza las reglas de seguridad: opera dentro de una envolvente de reglas duras. El bloqueo frontal por LiDAR y la parada del operador mandan siempre sobre ella; el árbitro de seguridad conserva la autoridad para autorizar el ascenso, y una salvaguarda geométrica detiene el dron si una persona seguida va a pasar a menos de 2 m en menos de 1.5 s. El operador humano puede intervenir en todo momento. Así, la IA aporta criterio donde las reglas fijas son ineficientes, y las reglas garantizan un comportamiento verificable donde la IA podría fallar.

Los resultados también muestran los límites del enfoque. Con la velocidad de avance recomendada (4 m/s), la IA deja prácticamente los mismos riesgos sin evitar que las reglas, aunque menos aproximaciones a menos de 2 m, y su ventaja más clara es la eficiencia. La percepción sigue siendo el límite cuando solo son visibles la cabeza y los hombros de la persona. Además, el detector se modeló estadísticamente, por lo que estos resultados deben confirmarse con el protocolo de campo descrito para el dron real.

## 8. Exportación a la Jetson

- `minimo_tesis/decision.pkl`: el modelo de scikit-learn con la normalización, el umbral y la persistencia.
- `minimo_tesis/decision.json`: pesos, sesgos, media y desviación de cada entrada, umbral, persistencia y el nombre y orden de las entradas. `decisor_ia.predecir_json` lo evalúa con NumPy puro (sin scikit-learn) y da lo mismo (prueba en `tests/test_decisor_ia.py`).
- En la Jetson, cada cuadro: calcular las 15 entradas con la caja de YOLO, el LiDAR, la velocidad del EKF y el seguimiento alfa-beta; evaluar la red (~1 000 multiplicaciones); si la probabilidad supera el umbral durante k cuadros, mandar la detención (y el ascenso si la envolvente lo autoriza). Las reglas duras corren al lado y mandan siempre.

Datos crudos: `minimo_tesis_decisor_ia.csv`. Repetición en el visor: grupo "Proyecto de grado", una opción por decisor.
