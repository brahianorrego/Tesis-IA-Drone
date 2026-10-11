# Informe de la jornada · 2026-10-10 (tarde)

Lo escribe el arquitecto, que quedó a cargo del proyecto mientras Brahian estaba fuera. No se hizo ningún commit ni push
(los hace Brahian). No se tocó nada físico.

## Resultado en una línea

La V15 quedó implementada, probada y **entrenando**: superó los niveles 0 a 3 del currículo y desde las 20:43 entrena el
nivel 4 (misión completa). Además quedó lista la versión **"mínimo indispensable proyecto de grado"** con el protocolo del
comité.

## Entrenamiento V15 (pestaña "Entrenamiento V15 (D-041)" de la sesión del arquitecto)

| Nivel | Superado | Pasos | Criterio | Resultado |
|---|---|---|---|---|
| 0 · Duelo abierto | 17:11 | 2.0 M | rendición ≥ 85 % y cenit ≥ 70 % | 91.6 % y **cenit 87.7 %** (llevaba versiones en 0 %) |
| 1 · Duelo con civil | 19:34 | 17.8 M | rendición ≥ 85 %, ID ≥ 98 %, 0 sin detectar, 0 choques | 86.1 %, 98.4 %, 0, 0 |
| 2 · Muro | 20:08 | 20.7 M | rendición ≥ 80 %, re-adquisición < 8 s | 91.0 %, 6.7 s |
| 3 · Muro y civil | 20:43 | 24.4 M | rendición ≥ 75 %, ID ≥ 98 % | 75.4 %, 98.7 % |
| 4 · Misión completa | entrenando | — | nivel final | se pule toda la noche |

- Arrancó a las 16:45 desde el último checkpoint de la V14. A las 19:16 se detuvo justo después de un guardado y se
  retomó con los ajustes D-041 (el nivel 1 estaba trabado en 44-49 % de rendición).
- Para retomarlo si se detiene: desde `simulacion\`, `.venv\Scripts\python.exe -u entrenar_master.py` (sigue solo desde
  `modelos_v15\ultimo.zip` con su nivel). Visor: `http://127.0.0.1:8765/` (pestaña "Visor 8765").

## Decisiones tomadas en la jornada (todas dentro de las reglas duras)

| Decisión | Por qué |
|---|---|
| Altura normal de vuelo 2.3 → **3.30 m** (altura segura), salvo el 360° de entrada bajo con guarda | A 2.3 m un ladrón alto lo tocaba con el brazo; con 3.30 m "alcanzado" en la misión completa bajó de 23 % a 5 % y los choques con muros de 14 % a 0 % |
| Muro de canto a **6 m con desplazamiento lateral** de 1 m a cada lado (en vez de un giro) | Por perspectiva, de canto puro solo asomaba 7-24 % del ladrón; corrido, ~40 % (margen para el YOLO real) |
| 360° de búsqueda a **−12°** (D-045) | A −8° la cámara no veía a nadie a menos de 4.4 m detrás del muro |
| **D-041**: cansancio realista (VC 2.5 m/s, D′ 120 m, tensión, esprint) y **moral del ladrón** (baja ×0.8 cada vez que el dron lo vuelve a encontrar) | La rendición era casi imposible con muros (5-12 %). Con la moral (la idea de Brahian de que "se dé por vencido") pasó a 78-97 % en los niveles 1-3 sin reentrenar |
| Civil distractor con descansos de 15-30 s y **memoria de apariencia** de civiles ya descartados | Preguntaba al operador ~16 veces por misión; ahora ~6.5, sin ningún cambio de ID sin detectar |
| Guarda del 360° de entrada con personas recordadas y civiles a ≥ 6.5 m | Los 4 choques con civiles que quedaban eran todos en esa vuelta baja |

Detalle: `docs/PLAN_V15_CURRICULO.md`, `simulacion/informes/evaluacion_v15-*.md` y `evaluacion_v15-ajustes-D041.md`.

## Hallazgo importante: la V15 NO es peor que la V14

Con el mismo criterio de éxito, la V15 supera a la V14 en todo (misión completa 62 → 92 %, duelo 67 → 96 %). Los números
más bajos que se veían eran del criterio nuevo (rendición), que es mucho más exigente
(`informes/evaluacion_v15-comparacion-v14.md`).

## Mínimo indispensable (objetivos, alcances y limitaciones del comité)

Carpeta congelada `simulacion/minimo_tesis/` (no depende del código que sigue cambiando). Protocolo del comité: el piloto
avanza en línea recta y el sistema solo hace DETENCIÓN + ASCENSO ante un riesgo; panel, persona quieta, persona que se
acerca, persona que cruza lejos y modo estático.

- 1300 vuelos: éxito **100 % [99.7, 100]**, 0 choques, **0 activaciones falsas** en 300 vuelos sin riesgo. Con el
  operador solo, 23 % de vuelos seguros. Con una persona que corre hacia el dron, el operador aprieta la parada a la vez
  que el sistema en 28 % de los vuelos (sin choques): "éxito sin ayuda del operador" 72 %.
- Latencias: riesgo → comando 0.07-0.12 s; comando → frenado 0.6-1.4 s; fuera del alcance en 0.4 s.
- **Hasta dónde funciona** (condiciones degradadas: sol, desenfoque, oclusión, LiDAR ruidoso, latencia, viento): frena
  con margen frente a un panel hasta ~11 m/s, frente a una persona quieta hasta 4 m/s, con una persona que corre hasta
  7-10 m/s. Se rompe cuando solo se ve la cabeza y los hombros. Recomendación: **LOIT_SPEED = 4 m/s** con personas.
- Informe: `simulacion/informes/minimo_tesis_protocolo.md` (incluye "Cómo se reproduce en campo"). Resumen para Tania:
  `docs/RESUMEN_V15_Y_MINIMO.md`. Visor: selector "Mínimo indispensable · protocolo del comité".

## Avisos para Brahian

1. El documento del comité todavía dice **Raspberry Pi**; el sistema usa la **Jetson Orin Nano**. Además, la misión del
   policía (seguir, flanquear, 360°) va más allá de los alcances aprobados: conviene presentarla como trabajo
   complementario y mantener el mínimo como núcleo evaluable.
2. **Commits pendientes**: todo lo de la V12 a la V15, el mínimo indispensable y los informes están sin commit en la rama
   `v11-hibrido`. Sugerencia: una rama `v15-curriculo`.
3. Las pruebas de reglas duras se **ampliaron** (RECONFIRMAR, MURO_DE_CANTO), siempre más estrictas: revísalas.
4. Pendiente medir: el nivel 4 después de una noche de entrenamiento (`herramientas/evaluar_politica.py` y la tabla por
   nivel) y llevar la política a la Jetson.
