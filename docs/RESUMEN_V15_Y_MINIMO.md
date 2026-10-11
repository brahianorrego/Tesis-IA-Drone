# Resumen para el documento: versión V15 y mínimo indispensable

Fecha: 10 de octubre de 2026. Fuentes: `simulacion/informes/evaluacion_v15-*.md` y `simulacion/informes/minimo_tesis_protocolo.md`.

## 1. Versión V15 del simulador de entrenamiento

La V15 aumenta el realismo del entorno de simulación en el que se entrena, por refuerzo (PPO), la política de seguimiento
del dron del proyecto de grado. Agrega:

- **Percepción y cuerpo humano realistas.** La estatura de las personas es variable y sigue la distribución de la
  población adulta colombiana (1.72 ± 0.07 m). Los muros tienen grosor. La detección es parcial (cuando solo se ve una
  parte del cuerpo) y el LiDAR tiene un alcance de 30 m.
- **Estimación del objetivo cuando deja de verse.** Usa un filtro de Kalman y un filtro de partículas con información
  negativa: las zonas que la cámara revisa y encuentra vacías pierden probabilidad.
- **Identidad del objetivo.** El simulador modela cruces con civiles parecidos y el riesgo de cambiar de objetivo por
  error. Ante una duda, el sistema pide confirmación al operador (estado RECONFIRMAR) y nunca cambia de objetivo por su
  cuenta.
- **Búsqueda determinista detrás de muros**, en este orden: lado previsto, extremo opuesto del muro, vista de canto con
  desplazamiento lateral y giro de 360°.
- **Criterio de éxito basado en la rendición del sospechoso.** El dron debe mantenerlo a la vista de forma continua
  durante un tiempo que depende de su cansancio y de su moral.
- **Currículo de cinco niveles de dificultad:** duelo abierto, duelo con civil, muro, muro con civil y misión completa.
- **Altura nominal de vuelo de 3.30 m** cerca de personas, fuera del alcance de una persona de pie y de su salto.

Para comparar con la versión anterior se usó la misma política, sin reentrenar, y el mismo criterio de éxito de la V14:
30 s con el objetivo fijado. Con ese criterio, la V15 supera a la V14 en todos los niveles comparables. En la misión
completa el éxito sube de 62 % a 92 %. La disminución que se observa con el criterio nuevo se debe a que la rendición es
más exigente que el criterio anterior, no a errores de la lógica.

Con los ajustes finales de cansancio, moral y civil distractor (decisión D-041), la rendición por nivel queda así, sin
reentrenar:

| Nivel | Rendición |
|---|---:|
| 0 Duelo abierto | 92 % |
| 1 Duelo con civil | 83 % |
| 2 Muro | 97 % |
| 3 Muro y civil | 78 % |
| 4 Misión completa | 37 % |

En los niveles 1 y 3 hubo cero cambios de identidad sin detectar. El entrenamiento de la V15 está en curso.

## 2. Mínimo indispensable

Es una versión reducida y congelada del sistema, independiente del entrenamiento. Define lo mínimo que el dron debe
cumplir:

- **El piloto conserva el mando.** Avanza en línea recta o mantiene el dron en vuelo estacionario (modo estático).
- **El sistema solo interviene ante un riesgo definido**, con una única maniobra: detención y ascenso vertical hasta
  3.30 m. Los riesgos definidos son dos:
  - un obstáculo frontal detectado por el LiDAR, dentro de la distancia de frenado o a menos de 2.5 s de impacto;
  - una persona detectada por YOLO a menos de 3 m, o a menos de 8 m acercándose con trayectoria de colisión.
- **El sistema no realiza** esquives laterales ni navegación autónoma.
- **El operador puede intervenir en todo momento.**
- **El modelo de simulación incluye:** ruido en los sensores, un retardo de 100 ms y la dinámica del controlador de
  ArduPilot.

**Protocolo de evaluación.** Se definieron cinco escenarios con semillas fijas, 100 vuelos por variante:
- (a) avance hacia un panel a 1–4 m/s;
- (b) avance hacia una persona inmóvil;
- (c) persona que se aproxima de frente;
- (d) persona que cruza a distancia, para medir los falsos positivos;
- (e) modo estático.

**Resultados.**

| Indicador | Resultado |
|---|---|
| Éxito con el sistema | 1300 de 1300 vuelos (IC 95 %: 99.7–100 %) |
| Colisiones | 0 |
| Activaciones falsas | 0 de 300 vuelos en los que no correspondía activarse |
| Vuelos seguros con el operador solo, sin el sistema | 23 % |
| Latencia del riesgo al comando | ≈ 0.1 s |
| Tiempo de frenado | de 0.6 s a 1 m/s hasta 1.4 s a 4 m/s |

**Límites de funcionamiento.** Se evaluaron condiciones degradadas:
- pérdida de detecciones;
- oclusión parcial de la persona;
- ruido y pérdidas del LiDAR;
- latencia de 200–500 ms;
- viento.

A las velocidades del protocolo ninguna condición realista produjo fallas. Al aumentar la velocidad, la velocidad máxima
de avance con detención segura es:
- **11 m/s frente a obstáculos**, limitada por el alcance útil del LiDAR;
- **4 m/s frente a una persona inmóvil**, limitada por la regla de no intervenir antes de 8 m;
- **7–10 m/s frente a una persona que se aproxima**, según la latencia.

El límite real de la percepción aparece cuando solo son visibles la cabeza y los hombros: en ese caso se registran
colisiones incluso a baja velocidad.

**Recomendación operativa:** limitar la velocidad de avance del piloto en ArduPilot (parámetro `LOIT_SPEED`) a 4 m/s
cuando haya personas en la zona.

## 3. Validación en campo (metodología)

El mismo protocolo se repite con el dron real: 10 repeticiones por escenario, primero con un maniquí y luego con
voluntarios, siempre con el operador listo para la parada de emergencia.

Fuentes de datos:
- **Jetson:** registra por cuadro la detección, la lectura del LiDAR, la decisión de riesgo y el comando enviado.
- **Registro de ArduPilot:** aporta la velocidad, la altura y las intervenciones del operador.

Diez éxitos en diez ensayos corresponden a un intervalo de confianza de 72–100 %. Por eso el campo valida el
funcionamiento, la latencia y la distancia de frenado, y la tasa de éxito fina se estima en simulación.

**Limitaciones declaradas:**
- La detección de YOLO está modelada estadísticamente, no con imágenes reales.
- El escenario es simplificado: una persona o un obstáculo por vuelo, sobre terreno plano.
