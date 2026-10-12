# Plan V16 · Misión de 2 paneles con física humana real y visor realista

Encargo para las **sesiones en la nube**. Lo prepararon el supervisor y el arquitecto con las decisiones de Brahian del
2026-10-12. Antes de programar, leer:
- `CLAUDE.md` (reglas duras y convenciones);
- `docs/ESTADO.md`;
- `docs/PLAN_V15_CURRICULO.md`;
- `simulacion/informes/diagnostico_v15_nivel4.md`;
- `docs/DECISIONES.md` (D-043, D-046);
- `jetson/visor_web.py` (lo que el operador ve hoy en el dron real).

## 1. Prioridad y forma de trabajo

- **Lo primero del proyecto es el mínimo indispensable** (`docs/PLAN_MINIMO_FISICO.md`), que hace Brahian en el
  portátil. La V16 es complementaria y se adelanta en la nube para que el entrenamiento quede listo.
- **Dos sesiones en la nube, cada una en su rama, para no pisarse:**
  - **Sesión A · Simulación**, rama `v16-simulacion`: entorno, física, sensores, recompensas, evaluación y
    preparación del entrenamiento.
  - **Sesión B · Visor**, rama `v16-visor`: gráficos realistas, animaciones e interfaz.
  - Las dos parten de `v15-curriculo`. B integra A con `git merge origin/v16-simulacion` cada vez que A publique una
    fase.
- **Autonomía.** Brahian autoriza a cada sesión a crear su rama, hacer commits y **push solo a su rama** (nunca a
  `main`, nunca `--force`, nunca borrar ramas ni etiquetas). Se trabaja fase por fase **sin pedir aprobación entre
  fases**. Al cerrar cada fase:
  - pruebas pasando;
  - commit;
  - push;
  - una entrada en `docs/PROGRESO_V16.md` (fecha, sesión, qué se hizo, números medidos, qué sigue).

  Solo se detiene a preguntar si algo choca con una regla dura de `CLAUDE.md`.
- **Entorno de la nube:** Linux. Crear el entorno con `python3 -m venv .venv` dentro de `simulacion/`, luego
  `.venv/bin/pip install numpy gymnasium stable-baselines3 scikit-learn` y torch para CPU
  (`--index-url https://download.pytorch.org/whl/cpu`; si no hay acceso, `pip install torch`). Los comandos de
  `CLAUDE.md` son de Windows: aquí van con `/` y `.venv/bin/python`.
- **Entrenamientos largos, no.** En la nube solo pruebas y corridas cortas (≤ 15 min) para verificar que aprende.
  El entrenamiento real lo lanza Brahian en el portátil con `CONTINUAR_ENTRENAMIENTO.bat`. Los modelos (`.zip`,
  `.pt`) no están en Git: la V16 arranca su propio modelo o hace el fine-tuning desde el que indique Brahian.
- Copias `_v15` (o `index_v19.html`) antes de reescribir un archivo. Commits en español con coautoría de Claude.
  Escribir "proyecto de grado", nunca "tesis".

## 2. Decisiones de Brahian (2026-10-12)

| # | Decisión |
|---|---|
| 1 | **Gimbal en simulación: −45°..+15°** (regla dura 1, sin cambios). El real hoy llega a −10° porque el cable del TF03 hace palanca. Se arreglará en hardware (ver sección 6). El entrenamiento se hace para −45° |
| 2 | **Segunda cámara fija mirando al piso**: CSI IMX219, HFOV 62.2° y VFOV 48.8° nominales (sin medir). Montaje **recto hacia abajo (−90°)**. Parametrizar `CAM_PISO_HFOV`, `CAM_PISO_VFOV` y `CAM_PISO_PITCH` |
| 3 | **Alturas variables entre 2.0 y 3.0 m** (2.0 / 2.5 / 3.0, que suba y baje) **solo sin personas a menos de ~8 m**: tránsito, 360° de entrada, inspección detrás de los muros. Con alguien cerca, **altura segura 3.30 m** (D-043 sigue vigente: una persona colombiana alcanza ~2.9-3.0 m saltando) |
| 4 | **Un solo caso de entrenamiento: misión completa con 2 paneles.** Sin el currículo de 5 niveles |
| 5 | **Ladrón con física humana real**: corre detrás de los muros, se esconde, se agacha, se recuesta de espalda contra la pared, gatea e **intenta saltar y agarrar el dron**. No lanza objetos |
| 6 | **Civiles realistas**: caminan tranquilos atravesando la zona. Al ver el dron unos lo esquivan, otros se quedan mirándolo ("chismoseando"), otros se alejan o salen de la zona. Nunca pasan a propósito por debajo |
| 7 | **Suavidad**: entrenar para movimientos suaves (sin tirones de cabeceo, guiñada ni gimbal) y para **la forma óptima de abordar al ladrón** dentro de las reglas duras |
| 8 | **Visor realista** en three.js. La cámara virtual debe mostrar **lo mismo que verá el operador en vuelo**: es la interfaz real, en virtual. Interfaz menos saturada y con menos aspecto de "IA" |
| 9 | **Vista previa (no entrenada)** de escenarios futuros: hangar o campo con columnas, vigas, cajas, habitaciones y árboles. Rotulada "vista previa: no entrenado" |
| 10 | Búsqueda detrás de obstáculos más precisa, estable y menos errática. A futuro: detector de obstáculos por cámara (muros, árboles, formas) que razone "hay algo detrás, vamos a mirar" |
| 11 | **Sensores**: TF03 y TF-Luna en la posición que recomienda el supervisor (sección 6). La simulación modela esa configuración |

**Criterio de éxito** (propuesta del supervisor; Brahian puede cambiarlo): **custodia** como número principal (vista
acumulada y nunca "perdido") y **rendición** (V15 con C1-C3) como secundario. Las dos se reportan.

## 3. Sesión A · Simulación (`simulacion/entorno.py`, `control.py`, `entrenar_master.py`, herramientas, pruebas)

**Fase A1 · Escenario y alturas**
- Partida única: misión completa con 2 paneles (de 4-6.5 m, 2.6 m de alto), 0-2 civiles y el ladrón.
- Alturas variables de la decisión 3, con transiciones suaves (rampa de velocidad vertical; sin escalones).
- Prueba nueva: con una persona a < 8 m, la altura nunca baja de 3.30 m.

**Fase A2 · Posturas humanas en la física.** Las posturas existen en el entorno, no solo en el dibujo:

| Postura | Alto del cuerpo | Velocidad | Detección (caja YOLO) | Oclusión tras el muro | Alcance |
|---|---|---|---|---|---|
| De pie | estatura (N(1.72, 0.07) m) | hasta esprint | completa | normal | de pie y salto |
| Agachado | ~1.1-1.2 m | ≤ 1 m/s | más baja y ancha; YOLO algo menos seguro | se oculta mejor | no salta |
| Recostado de espalda contra la pared | estatura, a ≤ 0.3 m del muro | 0 | de lado o de frente según el ángulo | casi total desde el lado opuesto | sale y ataca |
| Gateando | ~0.6 m | ~0.5-0.8 m/s | baja; YOLO bastante menos seguro | casi total | no salta |

- Transiciones de 0.5-1 s (pararse, agacharse, tirarse al piso).
- El ladrón táctico elige la postura según la situación.
- **Salto para agarrar el dron**: impulso, vuelo balístico y brazo extendido, con alcance de la mano = alcance de
  pie + salto. "Alcanzado" si la mano entra en el radio del dron. Tras el salto: aterrizaje y recuperación. El
  árbitro reacciona como hoy.
- Civiles con máquina de estados: transitar, notar el dron (< 15 m y a la vista), mirarlo 5-20 s, esquivarlo,
  alejarse o salir de la zona; algunos lo graban con el celular (solo animación).

**Fase A3 · Sensores**
- **Cámara al piso** (decisión 2), con el mismo ruido, pérdidas y retardo que la principal. Sus detecciones sirven
  para el punto ciego bajo el dron.
- **Montaje de los LiDAR** (sección 6): TF03 fijo al chasis mirando al frente y TF-Luna en el gimbal. Al cabecear
  el chasis, descartar los impactos en el suelo con la actitud de la Pixhawk.
- **Desenfoque por movimiento**: la probabilidad de detección baja con la velocidad angular de la cámara (guiñada y
  pitch) y con la velocidad relativa. Le da a la red un motivo físico para moverse suave.
- **Tipo de gimbal**: `GIMBAL_TIPO` = "basecam" (hoy) o "servo" (MG90D en la carcasa del pitch, estabilizado por la
  Pixhawk con ~50-100 ms de retraso, ~600°/s, zona muerta ~1°, topes mecánicos −45°/+15°). Entrenar con los dos
  (aleatorización del dominio).
- Ruido realista de posición GPS/EKF (deriva de 0.5-1.5 m) y de altura barométrica (±0.3-0.5 m).

**Fase A4 · Recompensa y abordaje**
- Custodia como recompensa principal. Rendición como bono.
- Suavidad: multa a la sacudida (jerk) solo en los canales que comanda la red (como la V12).
- **Abordaje con conciencia de coberturas** (idea del supervisor): un término de recompensa (shaping) por la
  fracción del área a la que el ladrón puede llegar en 2-3 s que el dron ve desde donde está. Así aprende a
  ubicarse donde el ladrón no tiene dónde esconderse.
- Mantener la distancia de 3.5-5 m, nunca sobrevolarlo, ángulo vertical dentro del rango del gimbal y acercarse
  por el lado contrario a su ruta de escape.
- Evaluar cada término por separado (con y sin él) antes de dejarlo.

**Fase A5 · Evaluación y preparación del entrenamiento**
- Escenarios fijos de 2 paneles en `herramientas/evaluar_politica.py`:
  - escape tras el muro;
  - agachado detrás del muro;
  - gateo entre muros;
  - recostado contra la pared y ataque;
  - salto bajo el dron;
  - civiles curiosos alrededor.

  Métricas por altura y por postura: custodia, rendición, re-adquisición, alcanzado, punto ciego y suavidad.
- Corrida corta en la nube para verificar que aprende. Dejar el comando exacto del entrenamiento largo en
  `docs/PROGRESO_V16.md`.
- **Contrato con el visor (`foto()`).** Campos nuevos:
  - `pos`: 0 de pie, 1 agachado, 2 recostado, 3 gateando;
  - `pt`: avance de la transición, 0-1;
  - `salto`: fase y altura de la mano;
  - `mira`: hacia dónde mira cada persona;
  - `civ`: estado del civil (transita, mira el dron, esquiva, se va, graba);
  - `alt_obj`: altura objetivo del dron;
  - `cam_piso`: detecciones de la cámara de abajo.

  Escribir el contrato en `docs/PROGRESO_V16.md` en la fase A2 para que el visor lo use.

## 4. Sesión B · Visor (`simulacion/index.html`, copia `index_v19.html` antes)

**Fase B1 · Motor gráfico y escena**
- three.js reciente (versión fija de un CDN permitido) con:
  - PBR, sombras suaves y tonemapping ACES;
  - cielo HDRI y niebla atmosférica;
  - piso con textura (pasto, concreto);
  - muros de concreto con desgaste.
- Recursos **CC0** (Poly Haven, ambientCG, Quaternius, Kenney) guardados en `simulacion/recursos/`, livianos
  (texturas de 1-2 K). Debe correr fluido en el portátil de Brahian: medir los cuadros por segundo.

**Fase B2 · Personas realistas**
- Modelos con esqueleto y animación (GLTF), en proporciones humanas reales, con la estatura de cada persona.
- Animaciones: quieto, caminar, trotar, correr, agacharse y caminar agachado, gatear, recostarse contra la pared y
  asomarse, saltar para agarrar el dron (brazo extendido), mirar hacia arriba, grabar con el celular y esquivar.
- Transiciones mezcladas, no saltos de pose. Pies anclados al piso.
- Las posturas que no traiga el paquete se arman procedurales sobre los huesos (con IK de brazos y piernas).
- **La animación del salto al dron tiene que verse de lo mejor**: impulso, vuelo, brazo hacia el dron y caída.

**Fase B3 · Cámaras reales e interfaz**
- **La vista de la cámara es la del dron real.** Cámara principal de 38.9° y 640 × 480 con la distorsión, el ruido,
  la exposición y el desenfoque por movimiento. La cámara al piso (IMX219) en una segunda ventana.
- Cajas de YOLO con ID y confianza **como en `jetson/visor_web.py`**.
- Interfaz de estación de tierra limpia:
  - las dos cámaras, un mapa pequeño, altura, batería, modo, estado del objetivo y el clic del operador;
  - todo lo técnico (estados, árbitro, recompensas, curvas) en un "modo ingeniería" plegado.
- Respetar la autoría de Brahian ya presente en el visor.

**Fase B4 · Vista previa de escenarios futuros**
- Hangar con columnas, vigas, cajas y estanterías, y campo con árboles. Rotulado "vista previa: no entrenado". Se
  puede recorrer con la cámara libre.

## 5. Geometría de referencia (calculada por el supervisor)

- Cámara principal: VFOV 29.7°. Con el gimbal en −45° el borde inferior mira a −59.9°: a 3.30 m ve la cabeza (1.5 m)
  desde ~1.05 m en horizontal y el torso desde ~1.4 m.
- IMX219 recta hacia abajo a 3.30 m: huella de ~4.0 × 3.0 m. Ve cabezas a menos de ~0.8-1.1 m del eje. Con el gimbal
  en −45° las dos cámaras casi empalman (hueco de ~0.2-0.3 m).
- Con el gimbal real en −10° (hoy): la principal no ve a nadie a menos de ~4-5 m y queda un anillo ciego de ~1 a
  ~4-5 m. Hay que tenerlo en cuenta en las pruebas de campo hasta arreglar el pitch.

## 6. Sensores y gimbal (recomendación del supervisor)

- **TF03 fijo al chasis, mirando al frente, horizontal (0° a +2°), fuera del gimbal.**
  - Es el sensor de frenado: a 4 m/s hacen falta ~6-9 m contando la latencia medida (0.6-1.4 s), y solo el TF03 los
    da en exteriores.
  - Al girar 360° también mapea los muros mejor que inclinado con la cámara.
  - Quitarlo del gimbal **elimina la palanca del cable que hoy traba el pitch en −10°**.
  - La Jetson descarta los impactos en el suelo con la actitud de la Pixhawk: obstáculo solo si
    d < h / sin(cabeceo hacia abajo) − 0.4 m.
- **TF-Luna en el gimbal, coaxial con la cámara.**
  - Es liviano y de cable flexible, así que no frena el pitch.
  - Mide la distancia a lo que la cámara centra. Su alcance (~8 m con blanco claro, ~2.5 m con oscuro y menos a pleno
    sol, según su hoja de datos) cubre justo la zona de peligro (< 3-5 m).
  - La distancia por la caja de YOLO + Kalman sigue siendo la principal.
  - Alternativa: un segundo TF-Luna mirando al piso como altímetro para volar a 2-3 m (ArduPilot lo acepta como
    telémetro).
- **Servo MG90D en la carcasa del pitch.**
  - ~2 kg·cm: mueve la cámara y el Luna. Pero no estabiliza: el pitch lo estabilizaría la Pixhawk como montura por
    servo, con su IMU.
  - Topes mecánicos en −45° y +15° harían la regla dura 1 física.
  - Revisar el ruido eléctrico del servo cerca de la cámara CSI y alimentarlo aparte (5-6 V).
