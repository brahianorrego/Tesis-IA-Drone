# Plan V16 · Misión de 2 paneles con física humana real (trabajo complementario)

Encargo para las sesiones en la nube. Lo prepararon el supervisor y el arquitecto con las decisiones de Brahian del
2026-10-12. Antes de programar, leer `CLAUDE.md` (reglas duras y convenciones), `docs/ESTADO.md`,
`docs/PLAN_V15_CURRICULO.md`, `simulacion/informes/diagnostico_v15_nivel4.md` y `docs/DECISIONES.md` (D-043, D-046).

## Prioridad y forma de trabajo

- **Lo primero del proyecto es el mínimo indispensable** (parte física, `docs/PLAN_MINIMO_FISICO.md`). Esta V16 es
  complementaria: Brahian salta a ella al terminar el mínimo. Se adelanta para que el entrenamiento esté listo.
- Se programa en **sesiones en la nube** (créditos de nube; no gastar el uso semanal del portátil).
- Se **entrena en el portátil** cuando el código esté listo y probado. Los modelos (`.zip`, `.pt`) no están en Git.
- La V15 (nivel 4 estancado en ~32 % de rendición tras 157 M pasos) se detiene. La V16 parte de su código.
- Rama nueva desde `v11-hibrido`: `v16-realismo`. Copias `_v15` antes de reescribir cada archivo. Pruebas en
  `simulacion/tests/` siempre pasando. Commits en español; **push solo con permiso de Brahian**.

## Decisiones de Brahian (2026-10-12)

| # | Decisión |
|---|---|
| 1 | **Gimbal en simulación: −45°..+15°** (regla dura 1, sin cambios). El gimbal real hoy llega solo a −10° (el cable del TF03 hace palanca); se arreglará en hardware (servo en la carcasa del pitch o reubicar el LiDAR). El entrenamiento se hace para −45° |
| 2 | **Segunda cámara fija mirando al piso**: CSI IMX219, HFOV 62.2° y VFOV 48.8° nominales (sin medir). Montaje **recto hacia abajo (−90°)**. Parametrizar `CAM_PISO_HFOV`, `CAM_PISO_VFOV`, `CAM_PISO_PITCH` (probar también −50°) |
| 3 | **Un solo caso: misión completa con 2 paneles.** Sin el currículo de 5 niveles |
| 4 | **Ladrón con física real**: corre detrás de los muros, se esconde, intenta alcanzar al dron (salto). Posturas nuevas: **agachado, recostado de espalda contra la pared, gateando**. **No** lanza objetos |
| 5 | **Visor más realista** en three.js (personas con esqueleto y animación, materiales PBR, sombras, cielo y luz natural). Nada de otro motor (Unreal, AirSim, Isaac) |
| 6 | Búsqueda detrás de obstáculos **más precisa, estable y menos errática**. A futuro: detector de obstáculos por cámara (muros, árboles, formas) que razone "hay algo detrás, vamos a mirar" |

## Pendiente de confirmar por Brahian

- **Alturas variables (2.0 / 2.5 / 3.0 / 3.3 m).** Propuesta del supervisor y del arquitecto: volar entre 2.0 y 3.3 m
  solo sin personas a menos de ~8 m (tránsito, 360° de entrada, inspección detrás de los muros) y ≥ 3.30 m en cuanto
  alguien se acerque. D-043 (decisión de Brahian) exige 3.30 m cerca de personas: el alcance de pie es ~2.3 m y
  saltando 2.6-2.9 m.
- **Civiles**: ¿0-2 como en la V15 nivel 4, o ninguno?
- **Criterio de éxito**: rendición (V15) o custodia (vista acumulada y sin perderlo), o las dos. El diagnóstico de la
  V15 recomienda reportar la custodia como número principal.

## Qué cambiar

**Entorno (`simulacion/entorno.py`).** Las posturas existen en la física, no solo en el dibujo:

| Postura | Alto del cuerpo | Velocidad | Detección (caja YOLO) | Oclusión tras el muro | Alcance |
|---|---|---|---|---|---|
| De pie | estatura (~1.72 m) | hasta esprint | completa | normal | de pie y salto |
| Agachado | ~1.1-1.2 m | ≤ 1 m/s | más baja y ancha | se oculta mejor | no salta |
| Recostado de espalda contra la pared | ~1.7 m, a ≤ 0.3 m del muro | 0 | de lado o de frente según el ángulo | casi total desde el lado opuesto | sí puede salir y atacar |
| Gateando | ~0.6 m | ~0.5-0.8 m/s | baja, en el suelo | casi total | no salta |

- Las transiciones (pararse, agacharse) toman tiempo realista (~0.5-1 s).
- El ladrón táctico elige postura según la situación: agachado o recostado al esconderse, gateando para cambiar de
  cubierta cerca del dron y de pie para correr o atacar.
- La cámara de abajo va en los sensores, con su FOV, su montaje y el mismo modelo de ruido y retardo que la principal.
- Alturas variables según la decisión pendiente.

**Contrato con el visor (`foto()`).** Campos nuevos:
- `pos`: 0 de pie, 1 agachado, 2 recostado, 3 gateando.
- `alt_obj`: altura objetivo del dron.
- `cam_piso`: detecciones de la cámara de abajo.

**Visor (`simulacion/index.html`, copia `index_v19.html` antes).**
- Personas GLTF con esqueleto y animaciones de caminar, correr, agacharse, gatear y recostarse. Si no hay clip, las
  posturas se hacen de forma procedural sobre los huesos.
- PBR, sombras suaves, cielo HDRI, muros de concreto y piso con textura.
- Cono de la cámara de abajo.
- Librerías solo de CDN con versión fija.

**Evaluación.** Escenarios fijos de 2 paneles en `herramientas/evaluar_politica.py`, con métricas por altura y por
postura: custodia, rendición, re-adquisición, alcanzado y punto ciego. `herramientas/resumir_metricas.py` al día.

## Geometría de referencia (calculada por el supervisor)

- Cámara principal: VFOV 29.7°. Con el gimbal en −45° el borde inferior mira a −59.9°: a 3.30 m ve la cabeza (1.5 m)
  desde ~1.05 m en horizontal y el torso (0.9 m) desde ~1.4 m.
- IMX219 recta hacia abajo a 3.30 m: huella de ~4.0 × 3.0 m. Ve cabezas a menos de ~0.8-1.1 m del eje. Con el gimbal en
  −45° las dos cámaras casi empalman (hueco de ~0.2-0.3 m).
- Si el gimbal real se queda en −10°, la principal no ve a nadie a menos de ~4-5 m y queda un anillo ciego de ~1 a
  ~4-5 m. En ese caso conviene montar la IMX219 a ~−50°.

## Notas de hardware para la sesión física (no son de la simulación)

- **Servo MG90D** (piñones metálicos, ~2 kg·cm, 180°): puede mover una cámara liviana, pero no estabiliza. La
  estabilización del pitch tendría que darla ArduPilot como montura por servo con la IMU de la Pixhawk. El tope
  mecánico en −45° haría la regla 1 física.
- **TF-Luna**: más liviano y con cables flexibles, pero de mucho menos alcance que el TF03. Según su hoja de datos,
  ~8 m con blanco claro y ~2.5 m con blanco oscuro, y menos a pleno sol. Sirve mirando al piso (altura) o hacia atrás,
  no como sensor frontal de frenado en exteriores. Revisar la hoja de datos antes de comprar.
