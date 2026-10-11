# Estado del proyecto

Actualizado: 2026-10-10, V15 entrenando (la lanzó el arquitecto; retomada a las 19:17 con D-041) y mínimo indispensable listo

## Resumen

Dron autónomo que busca, fija y mantiene a la vista a un sospechoso (PPO + reglas + operador humano).
El hardware está configurado y probado en banco; la IA se entrena en simulación y aún no vuela.

## Simulación y entrenamiento

- **Mínimo indispensable del proyecto de grado** (`simulacion/minimo_tesis/`, carpeta congelada e independiente del
  entrenamiento). El piloto avanza de frente; el sistema solo frena y sube a 3.30 m ante un riesgo definido (obstáculo
  por LiDAR, persona por YOLO según el árbitro); el operador siempre manda; modo estático. Protocolo del comité
  (`informes/minimo_tesis_protocolo.md`, CSV y repetición en el visor): 1300 vuelos, éxito 100 % [99.7, 100], 0
  activaciones falsas en 300; con el operador solo, 23 % de vuelos seguros. Condiciones degradadas y velocidad máxima
  segura (detenerse con margen): panel 11 m/s (alcance del LiDAR), persona quieta 4 m/s (regla de los 8 m), persona que
  corre de frente 10 m/s (7 con 300 ms de latencia); se rompe con solo cabeza y hombros a la vista. 13 pruebas.
  - Fase G · decisor IA (`informes/minimo_tesis_decisor_ia.md`): MLP con las entradas de la Jetson dentro de la envolvente
    de reglas duras. Protocolo 100 % como las reglas; discriminación 91.2 → 94.0 %, activaciones innecesarias 44 → 30;
    mundos de prueba: choques 39 → 28, personas a < 2 m bajo 3.30 m 420 → 218. Abierta D-048 (veto del árbitro al ascenso).
- **V15 · nivel 4** (C1-C3, `informes/evaluacion_v15-nivel4-C1-C3.md`): pausa de 4 s, tope terminal, custodia como número
  principal (~89 % a 60 s). El entrenamiento se retomó con esos cambios.

- **V15** (plan `docs/PLAN_V15_CURRICULO.md`, fases A-E implementadas y medidas; informes `simulacion/informes/
  evaluacion_v15-fase-{A..E}.md`). **Entrenando**: la lanzó el arquitecto a las 16:45 y la retomó a las 19:17 con D-041
  (`informes/evaluacion_v15-ajustes-D041.md`). Sale del último
  checkpoint de la V14 (`modelos_v14/`, 7.0 M) y empieza en el nivel 0. Copias previas: `*_v14.py`, `index_v17.html`.
  - A: LiDAR 30 m y 10 rayos/paso, 360° de entrada bajo (2.5 m, −3°) y de búsqueda alto (3.3 m, −12°), cuerpo colombiano
    (altura segura 3.30 m), cansancio y pulso, muros de 0.2 m, detección por alto y ancho.
  - B: Kalman (con compuerta y distancia geométrica), 200 partículas con información negativa, búsqueda guiada por la nube,
    anti-cenit predictivo, distancia adaptativa. Escenario "debajo": 2 → 68 % (82 % al final de la fase E).
  - C: cambio de ID en cruces, estado RECONFIRMAR con el operador: 0 cambios sin detectar en 1 556 partidas.
  - D: secuencia tras el muro (lado proyectado → otro extremo → muro de canto → 360°); tras muro 10.2 → 9.6 s.
  - E: rendición (contador continuo, 20 s + 100 s × reserva, tope 5 min), 5 niveles, ataques desde el nivel 2, guardas de
    geocerca y de personas, visor con una pestaña por nivel. **Decisiones abiertas** en el informe de la fase E (cansancio,
    civil distractor, choques en partidas largas).
  - Ajustes del arquitecto (`informes/evaluacion_v15-ajustes-arquitecto.md`): altura nominal 3.30 m salvo el 360° de
    entrada (D-043); muro de canto a 6 m con desplazamiento lateral de 1 m a cada lado (D-044). Geocerca en cenit y
    "debajo": 0 %; choques con peatones 0-0.6 %. Rendición por nivel: 89 / 51 / 66 / 9 / 12 %. 62 pruebas pasan.
  - Comparación con la V14 (`informes/evaluacion_v15-comparacion-v14.md`): con el mismo criterio de éxito la V15 gana en
    todos los niveles (misión completa 62 % → 92 %); la rendición baja por el contador de ~2 min y los civiles parecidos
    (D-041). Abierta D-045 (pitch del 360°: −8° o −12°).

- **V14 · Currículo progresivo** (2026-10-10, listo y probado, sin lanzar). Incluye todo lo de la V13. Parte del
  checkpoint más nuevo de la V12 (10.1 M pasos; la V12 está detenida). Copias previas: `*_v13.py`, `index_v16.html`.
  - Niveles (en `reset()`): 0 Duelo abierto (sin muros ni civiles; ladrón en huida zigzag, 30 % cenit), 1 Muro único,
    2 Ruido visual (muro + civil que cruza la línea de vista), 3 Misión completa. 25 % de partidas repasan niveles
    anteriores. Oclusión entre personas (nueva) y civil distractor que no se acerca a menos de 3 m del dron.
  - `CurriculumCallback`: sube con éxito ≥ 85 % en las últimas 1000 partidas del nivel (sin repaso ni cenit), con
    mínimo 2 M pasos por nivel y paciencia de 50 M. Log `>>> NIVEL SUPERADO … <<<`. Guarda el nivel para continuar.
  - Competencia dron vs ladrón en `salida/estado.json`; visor con barra "Dominio táctico" y nivel actual.
  - Medido con el modelo de la V12 (192 entornos × 150 s): N0 huida 97 %, **N0 cenit 0 %**, N1 90 %, N2 89 %,
    N3 55 %. El modelo ya domina 0-2: subirá rápido; el trabajo real está en el nivel 3 y en el cenit. 38 pruebas pasan.

- **V13 · Currículo y geometría de la búsqueda** (2026-10-10, código listo y probado; NO se lanzó: la V12 sigue
  entrenando hasta que Brahian decida). Copias previas: `*_v12.py` e `index_v15.html`.
  - Currículo: 30 % de las partidas con "Un Solo Muro" (baja a 10 % al subir el nivel); métricas `cumplida_un_muro`.
  - GIRO_360 con altura y gimbal fijos y 90°/s, con tope `RATE_Y_MAX = 120°/s` en `control.py`. Valores por defecto
    **3.0 m y -15°** (el pedido era 2.5 m y 0°: dentro del salto del ladrón, alcanzado 48 %; ver D-027).
  - Interrupción táctica: si YOLO ve al ID designado en cualquier estado de búsqueda, PERSECUCIÓN en el mismo cuadro.
  - Stand-off por FOV: 2.4 m por fuera de la esquina y 0.8 m detrás del muro (2.53 m en diagonal).
  - Detección parcial: basta el 15 % del bounding box (12 muestras del cuerpo; dentro de la imagen y sin tapar).
  - Despeje ampliado a 1.2 m, también contra la nube de puntos (evita bajar sobre un muro tras una interrupción).
  - Con el modelo actual de la V12 (sin reentrenar), entorno general 192 × 150 s: cumplida 33.5 % → **67 %**,
    alcanzado 22.8 % → 18 %, panel 7.1 % → 3 %, perdido 22.8 % → 7 %. Escenarios fijos: cambio brusco 58 % → **100 %**,
    debajo 0 % → 8 %, abierto y tras muro 100 % (`informes/evaluacion_v13-con-modelo-v12.md`). 30 pruebas pasan.
  - Al lanzarla: retoma sola `modelos_v13/ultimo.zip` o, la primera vez, arranca del checkpoint más nuevo de
    `modelos_v12/` y guarda la salida de la V12 en `salida_v12/`.

- **V12 · Control jerárquico híbrido** (2026-10-10, código listo y probado; el entrenamiento lo lanza Brahian):
  - **Fine-tuning estricto** desde el último checkpoint de la V10 (`dron_master_769612800_steps.zip`, 769.6 M pasos).
    Capa inferior del actor congelada entera (24 704 parámetros, verificado: cambio 0); solo se afinan la capa táctica
    y la salida (17 802) y el crítico. Modelos nuevos en `simulacion/modelos_v12/` (fuera de Git), tasa 1e-4.
  - **Recompensa:** la multa de suavidad solo cobra lo que comanda la red (en "abierto": -18.9 → -0.5 por partida, mismo
    jitter físico). Bono de re-adquisición +8 y multa -8 por el MISMO evento (oculto más de 1 s). `info` registra
    `t_ep`, `r_comp` (8 componentes), `du` (jitter físico por eje) y `gmb_min`.
  - **Gimbal:** barrera dura de -45° también después del PID (prueba con comandos de -120° y cabeceo de ±25°).
    **Reflejo de punto ciego:** retrocede a d = h / tan(45° + VFOV/2) + 1 m si el objetivo va a quedar debajo.
  - **Búsqueda determinista con memoria espacial** (`PERDIDA_IA = False`): PERSECUCIÓN → PÉRDIDA → FLANQUEO_PROFUNDO →
    GIRO_360 → SIGUIENTE_OBSTÁCULO → … → ALTURA_TÁCTICA → MISIÓN_PERDIDA a los 90 s; histéresis de 1 s por estado;
    raycasting contra la nube del LiDAR para elegir el muro y para que la ruta no roce las esquinas.
  - **Visor:** paneles "Búsqueda · estados" y "Mapa SLAM · LiDAR 1D" (minimapa con nube de puntos, barrido del rayo,
    muros, zona ciega) y datos brutos del LiDAR. Arreglado: la nube nunca llegaba al visor (clave `lm` repetida).
  - **Mismo modelo de la V10, sin reentrenar** (entorno general, 256 partidas): cumplida 13 % → **43.5 %**, perdido
    62.5 % → 21.8 %. Escenarios fijos (`informes/evaluacion_v12-sin-reentrenar-769M.md`): abierto 100 %, tras muro
    100 % (antes 94 %), cambio brusco 56 %, **debajo sigue en 0 %** (el ladrón del escenario persigue al dron y se mete
    debajo desde 3.5 m a 3.5 m/s; el dron, con el jerk limitado, no alcanza a apartarse). 24 pruebas pasan.
- Rama `v11-hibrido`: gimbal estricto en **-45°..+15°** (D-014) y búsqueda tras perder el objetivo
  **determinista**, `PERDIDA_IA = False` (D-015). Probado: el gimbal toca -45,00° y nunca baja; con la
  bandera en False se recorren PREDECIR, INVESTIGAR, ASOMO y VENTAJA_ALTURA. 17 pruebas pasan.
- Código base: V10 (entorno `v8`/`v9` en el docstring): mapa LiDAR, 10 acciones, `OBS_DRON = 192`,
  controladores PSC/ATC y gimbal modelados en `control.py`. Copias previas a los cambios: `*_v10.py`.
- Entrenamiento V10 master **detenido** en 769.8 M pasos (2026-10-10). Su salida quedó en `simulacion/salida_v10/`.
- Referencia: V9 con pesos v8 sin reentrenar → cumplida 44 %, perdido 26 %, alcanzado 15 %.
- Evaluación en escenarios fijos y resúmenes: `simulacion/herramientas/` → `simulacion/informes/`.
  Pruebas: `simulacion/tests/`. Agentes: `.claude/agents/` (`supervisor-rl`, `implementador`).

## Modelos

- `simulacion/modelos_master/` (fuera de Git): V10, 761+ `.zip`, ~1,1 GB. Brahian los copia a mano a Google Drive.
- `simulacion/modelos_v12/` (fuera de Git): V12 (`base_v12.zip`, `ultimo.zip`, un checkpoint por millón de pasos).
- **Release `v10-master-759M`** en GitHub: 10 archivos, 12 MB (`ultimo.zip`, `base_v9.zip`,
  `ladron_congelado.pt` y un checkpoint cada 100 M pasos hasta 700 M).
- `simulacion/modelos/dron_politica.json`: pesos exportados para la Jetson (sí está en Git).

## Hardware

- Pixhawk (ArduPilot 4.7) ↔ Jetson por TELEM2 a 115200; pitch del gimbal por AUX1 (`pwm = 1500 + θ·500/45`).
- Batería LiPo 4S original sobredescargada: **retirada**; no volar con ella.
- Detalle en `hardware.md`, `pixhawk.md` y `jetson.md`.

## Git

- Rama de trabajo: `v11-hibrido` (los cambios de la V12 están sin commit; conviene pasarlos a una rama `v12-jerarquico`). Etiqueta `v10-master-759M` (código de la V10, 759 M pasos).
- PR #2 (`docs/proyecto-completo-v6`) abierto, sin fusionar: lo hace Brahian en GitHub.

## Pendientes (por prioridad)

1. Brahian: revisar las decisiones abiertas de la fase E y confirmar el lanzamiento de la V15 (comando en `CLAUDE.md`).
2. Escenario "debajo" (0 %): decidir si se acepta como límite físico o si se agrega una regla anti-acecho en la búsqueda.
3. Brahian: copiar `modelos_master/` (1,1 GB) a Google Drive.
4. Ciclo de mejora: pasar `informes/resumen_*` y `barrido_*` a `supervisor-rl` y decidir sus cambios.
5. Fusionar el PR #2 a `main`.
6. Copiar el código de la Jetson (`~/Escritorio/dron_ia`) a `jetson/` cuando esté encendida.
7. Llevar la política a la Jetson: sus entradas deben calcularse igual que en `entorno.py`.
8. Validación sim-to-real con datos de campo; evaluar la cuadrícula de la cámara al sol.
