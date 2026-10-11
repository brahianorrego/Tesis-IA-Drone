# Mínimo indispensable del proyecto de grado

Versión reducida y **congelada** del sistema, para presentar al comité lo mínimo que el dron debe cumplir. Es
independiente del entrenamiento por refuerzo: no importa `entorno.py`, `mision.py` ni `entrenar_master.py`, así que sus
resultados no cambian aunque el entrenamiento siga.

## Qué hace

- **El piloto manda.** Avanza de frente en línea recta, o deja el dron quieto (**modo estático**).
- **El sistema solo interviene ante un riesgo definido**, y siempre con la misma maniobra: **DETENCIÓN + ASCENSO
  VERTICAL** hasta 3.30 m (fuera del alcance de una persona de pie y de su salto). La intervención queda retenida
  hasta que el operador la libera.
- **No hace** esquives laterales, navegación autónoma ni elección de objetivos.
- **El operador puede intervenir siempre:**
  - PARADA (CH8): frena en el sitio; el ascenso de protección, si ya empezó, sigue.
  - ANULAR: mando total del piloto, sin el sistema.
  - REANUDAR: libera una intervención.

### Riesgo definido

Se evalúa con las medidas de los sensores, retrasadas 100 ms y con ruido.

**1. Obstáculo al frente (LiDAR).** Hay riesgo si se cumple cualquiera de estas condiciones:
- no alcanza la distancia de frenado más un margen:
  `L < v·0.5 + v²/(2·2.5) + 1.5 + 0.4`;
- faltan menos de 2.5 s para tocarlo;
- está a menos de 3 m mientras avanza (bloqueo frontal de las reglas duras).

**2. Persona (YOLO).** Se aplica el árbitro de las reglas duras. Hay riesgo si:
- está a menos de 3 m; o
- está a menos de 8 m, se acerca a más de 0.4 m/s **y** el punto de máximo acercamiento previsto en 6 s queda a menos
  de 2 m. Esta última condición es más estricta que la regla dura: evita activarse con quien pasa de lado.

## Archivos

| Archivo | Qué es |
|---|---|
| `control.py` | Copia congelada del control de ArduPilot (PSC/ATC) y del gimbal BaseCam (−45°..+15°) |
| `sensores.py` | Cámara + YOLO (probabilidad por distancia, ruido, estatura supuesta 1.72 m, caja cortada → distancia por el ancho de los hombros), LiDAR TF03 (un rayo, 0.1-30 m, 2 cm) y retardo de 100 ms |
| `sistema.py` | El mundo (dron, una persona, paneles) y la lógica mínima (`SistemaMinimo`): la que correría en la Jetson |
| `protocolo_comite.py` | Escenarios con semillas fijas, métricas, informe, CSV y repetición para el visor |
| `replay/replay_protocolo.json` | Un vuelo de cada escenario, en el formato de la fase 1 del visor |

## Protocolo del comité

Escenarios del protocolo:
- **a)** Avance hacia un panel fijo a 1, 2, 3 y 4 m/s.
- **b)** Avance hacia una persona quieta.
- **c)** Persona que viene de frente, caminando o corriendo.
- **d)** Persona que cruza lejos. No debe activarse: mide los falsos positivos.
- **e)** Modo estático: persona que viene caminando o corriendo, y persona que pasa de lado a 5 m (esta última no debe
  activarlo).

Cada variante tiene 100 vuelos, con el sistema y sin él (operador solo, como referencia).

Métricas:
- tasa de éxito;
- activaciones verdaderas y falsas;
- eventos de riesgo;
- latencia riesgo → comando → frenado efectivo;
- paradas del operador.

Los intervalos de confianza son del 95 %.

**Condiciones degradadas** (cada una por separado, una combinada y tres extremas):
- recall de YOLO 0.85 y 0.70;
- medio cuerpo o solo torso visible;
- LiDAR con ruido ×3 y 5 % de lecturas perdidas;
- latencia de 200 y 300 ms;
- viento de cola de 3 y 5 m/s con ráfagas;
- extremas: recall 0.40, solo cabeza y hombros, latencia de 500 ms.

Para cada condición se barre la velocidad de avance de 1 a 12 m/s para encontrar la **velocidad máxima segura**: la
mayor velocidad que, junto con todas las menores, se detiene con margen en ≥ 95 % de los vuelos. El informe trae además
cómo se reproduce el protocolo en campo. Todo junto tarda ~5 min; `--sin-degradadas` corre solo el protocolo (~10 s).

```
cd simulacion
.venv\Scripts\python.exe -m minimo_tesis.protocolo_comite
```

Salidas:
- `informes/minimo_tesis_protocolo.md` (tablas);
- `informes/minimo_tesis_protocolo.csv` (un renglón por vuelo) y `informes/minimo_tesis_degradadas.csv`;
- la repetición en el visor (`ABRIR_VISOR.bat`), en el selector: **"Mínimo indispensable · protocolo del comité"**.

Pruebas: `.venv\Scripts\python.exe -m unittest tests.test_minimo_tesis`.

## Límites

- Una persona o un panel por vuelo, suelo plano y viento suave.
- YOLO está modelado estadísticamente, no con imágenes.
- La validación en campo debe repetir los escenarios a, b y d con el dron real.

## Fase G · Decisor IA

Además de las reglas, el mínimo tiene un **decisor aprendido**: la IA no solo detecta, también decide si intervenir.

- **Modelo:** clasificador MLP de scikit-learn (capas de 32 y 16 neuronas, ReLU), en `decisor_ia.py`.
- **Entradas:** solo lo que tiene la Jetson, calculado igual que en el dron:
  - la caja de YOLO: alto, ancho, área, ángulo horizontal y su variación, confianza y cuadros seguidos;
  - el LiDAR;
  - la velocidad propia del EKF de ArduPilot;
  - el seguimiento alfa-beta: distancia, velocidad de acercamiento y lateral, y tiempo sin detección.
- **Salida:** probabilidad de que, si el piloto sigue igual, en 3 s haya un choque o una persona a menos de 2 m.
  Sobre el umbral durante k cuadros seguidos: CONTINUAR → DETENER_Y_ASCENDER (o solo DETENER si el árbitro no
  autoriza subir).
- **Etiquetas automáticas:** se toman de vuelos sin intervención con la verdad del simulador. Entrenamiento, validación
  y prueba se separan por semillas. El umbral se elige en lazo cerrado sobre la validación, nunca sobre el protocolo.
- **Decisores comparables:**
  - `reglas`;
  - `ia` (la IA sola);
  - `ia_env`: la IA dentro de las reglas duras de CLAUDE.md. El LiDAR a menos de 3 m y la parada mandan; el árbitro
    autoriza el ascenso;
  - `ia_env_estricta`: además, una persona a menos de 3 m obliga a detenerse.
- **Exportación a la Jetson:** `decision.pkl` y `decision.json`. `decisor_ia.predecir_json` evalúa el JSON con NumPy puro.

```
.venv\Scripts\python.exe -m minimo_tesis.entrenar_decisor        (datos, MLP, umbral, curvas; ~15-20 min)
.venv\Scripts\python.exe -m minimo_tesis.evaluar_decisores       (comparación completa; ~1 h)
```

Informe: `informes/minimo_tesis_decisor_ia.md` (con la justificación para el documento). Pruebas:
`tests/test_decisor_ia.py`. En el visor, una opción por decisor en el grupo "Proyecto de grado".
