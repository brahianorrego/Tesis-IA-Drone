# Bitácora

Registro cronológico, lo más reciente arriba. Lo agrega la skill `/cierre-sesion` al terminar cada sesión.
Fechas de 2026.

## 11 de octubre
- **Fase G · decisor IA del mínimo indispensable** (`simulacion/minimo_tesis/decisor_ia.py`): MLP de scikit-learn con las
  entradas que tiene la Jetson, etiquetas automáticas con la verdad del simulador y separación por semillas; exportado a
  `decision.pkl` y `decision.json`. Comparado con las reglas en el protocolo, la discriminación, condiciones degradadas,
  barrido de velocidad y 3840 vuelos de prueba nunca vistos. Gana en eficiencia y anticipación (velocidad segura con
  persona quieta 4 → 12 m/s) y en seguridad en vuelos variados; con 4 m/s la seguridad es parecida a la de las reglas.
  Hallazgos que cambiaron el diseño: faltaban en los datos personas delante en el mismo sentido; la persona < 3 m como
  obligación anulaba el aporte de la IA (la regla 5 autoriza, no obliga); hizo falta una salvaguarda geométrica para
  personas que entran de lado al campo de la cámara. Abierto: el veto del árbitro al ascenso (D-048).
- **Nivel 4 (C1-C3)** aplicado y medido; el arquitecto retomó el entrenamiento con esos cambios.

## 10 de octubre
- **Mínimo indispensable (fase F)** en `simulacion/minimo_tesis/`: copia congelada del control, sensores con ruido y
  retardo de 100 ms y una lógica que solo frena y sube ante un riesgo definido, con el piloto y el operador al mando.
  Protocolo del comité con semillas fijas (panel a 1-4 m/s, persona quieta, persona de frente, persona que cruza lejos,
  modo estático): 1300 vuelos sin choques ni activaciones falsas; el operador solo deja 23 % de vuelos seguros. Para
  llegar ahí hubo que corregir dos cosas que también valen para la Jetson: la velocidad de la persona se estima con un
  filtro alfa-beta (restar distancias de la caja da ±3 m/s de ruido) y, si la caja sale cortada, la distancia sale del
  ancho de los hombros.
- **V15 · ajustes del arquitecto** (sin lanzar): altura nominal 3.30 m (D-043) y muro de canto con desplazamiento lateral
  (D-044). Comparación justa V14 contra V15 con el mismo modelo (`informes/evaluacion_v15-comparacion-v14.md`): con el
  criterio de éxito de la V14, la V15 es mejor en todos los niveles (misión completa 62 % → 92 %); la caída que se veía
  viene de la rendición (contador continuo de ~2 min) y de los civiles parecidos, no de errores de lógica. Geocerca en
  cenit y en "debajo": 0 %. Choques con peatones: venían de volar a 2.3 m; quedan 0.6 % en el 360° de entrada.
- **V15 implementada** (fases A-E del plan del arquitecto, aprobado por Brahian), sin lanzar. La V14 se detuvo sola en
  7.5 M pasos (ya en su nivel 3). Hallazgos que cambiaron el plan: el muro de canto va a 8 m (con perspectiva los hombros
  asoman 3 cm a 6 m); el 360° de búsqueda a −12° (a −8° no ve a nadie a menos de 4.4 m); el Kalman divergía con el ladrón
  debajo (se arregló con compuerta y distancia geométrica); hicieron falta guardas de geocerca y de personas para partidas
  de 5 min. Abierto: el ladrón casi no se cansa y la rendición es rara con muros; el civil distractor genera ~16
  reconfirmaciones por misión.
- **V14 preparada** (la V12 quedó detenida en 10.5 M pasos; la V13 nunca entrenó y se absorbe en la V14): currículo
  progresivo de 4 niveles con árbitro de progresión (`CurriculumCallback`), repaso de niveles, oclusión entre personas,
  civil distractor y barra "Dominio táctico" en el visor. Se midió cada nivel antes de fijar umbrales: el "duelo de
  cenit" puro da 0 % (no puede ser el primer nivel); quedó como práctica dentro del nivel 0 y se reporta aparte.
- **V13 preparada** (sin lanzar; la V12 sigue entrenando, iba en 4 M pasos): currículo "Un Solo Muro" (30 % → 10 %),
  GIRO_360 a altura y pitch fijos con tope de guiñada de 120°/s, interrupción táctica por YOLO, stand-off de 2.5 m
  calculado con el FOV, detección parcial con el 15 % del cuerpo y despeje de 1.2 m. El pedido de girar a 2.5 m con
  el gimbal en 0° se midió: el ladrón alcanzaba al dron en el 48 % de las partidas; queda 3.0 m / -15° (D-027).
  Con el modelo de la V12: cumplida 33.5 % → 67 %, cambio brusco 58 % → 100 %. 30 pruebas pasan.
- **V12 · Control jerárquico híbrido.** Fine-tuning estricto desde el checkpoint de 769.6 M de la V10 (capa inferior
  congelada entera, verificado). Multa de suavidad solo a lo que comanda la red. Bono de re-adquisición ±8 por el
  mismo evento (1 s oculto). `info` con duración, recompensa por componente, jitter por eje y gimbal mínimo. Barrera de
  -45° también tras el PID. Reflejo de punto ciego (d = h/tan(45°+VFOV/2)+1 m). Búsqueda determinista con memoria
  espacial y nuevo estado SIGUIENTE_OBSTÁCULO, misión perdida a los 90 s. Visor con minimapa SLAM y panel de estados.
  Con el modelo de la V10 sin reentrenar: cumplida 13 % → 43.5 %. "Debajo" sigue en 0 %. 24 pruebas pasan.
  El entrenamiento V10 se detuvo en 769.8 M; su salida pasó a `salida_v10/`.
- Diagnóstico de la V10 (`simulacion/informes/diagnostico_v10.md`): 767 M pasos estancados (cumplida ~31 %); la búsqueda por IA nunca gira ni avanza. Con las reglas v11 el mismo modelo sube en escenarios fijos: tras muro 0 → 94 %, cambio brusco 0 → 60 %; "debajo" sigue en 0 %. Propone 3 cambios (registro de métricas, separación según la altura, multa solo a lo que comanda la red).
- v11-hibrido: gimbal estricto en -45° (D-014) y búsqueda determinista `PERDIDA_IA = False` (D-015), por decisión de Brahian. Antes se había ajustado la regla al código (-60°, IA); se revirtió el mismo día. Pruebas de reglas duras actualizadas (17, pasan).
- Ciclo de mejora: agentes `supervisor-rl` e `implementador`, `resumir_metricas.py` y `evaluar_politica.py` (4 escenarios fijos); barrido de toda la V10.
- Release `v10-master-759M` en GitHub con los modelos esenciales (10 archivos, 12 MB). El entrenamiento viejo sigue corriendo con las reglas anteriores (766.8 M pasos).
- El entrenamiento master (Stable-Baselines3) sigue corriendo: 759 M pasos, 761 archivos de modelo (1.1 GB).
- Se ordenó el repositorio: `.gitignore` con modelos, salidas y secretos; `CLAUDE.md` y `docs/` nuevos.
- Se detectó que `.zip` no estaba ignorado: un `git add .` habría subido 759 checkpoints.
- Etiqueta nombrada `v10-master-759M` (la corrida ya iba en 759 M, no en 350 M).

## 8 de octubre
- Se subió al repositorio la simulación v6 y la documentación del hardware (PR #2).
- Versiones v7 a v9: mapa LiDAR, búsqueda activa tras los paneles, ladrón con saltos y campos potenciales,
  gimbal con límite duro, jerk del autopiloto, observación de 192 entradas.
- Búsqueda tras perder el objetivo a cargo de la IA (`PERDIDA_IA = True`), para compararla con la determinista.
- Se agregó la autoría de Brahian al visor (barra superior y letras 3D en el piso).
- Nace `entrenar_master.py` (SB3, transferencia de la v9, ladrón congelado en el 30 % de las partidas).

## 7 de octubre
- El proyecto de grado pasa a **exteriores** (GPS, modo GUIDED). Alcance en dos fases: piloto traslada, IA vigila.
- Pixhawk configurada: modos de vuelo por CH5, parada de emergencia en CH8, enlace TELEM2 a 115200.
- Pitch del gimbal por AUX1 (`DO_SET_SERVO`): los pines PWM de la Jetson no daban señal.
- Cámara: HFOV medido 38.9°; cuadrícula por falta de filtro IR-cut; YOLO26n en TensorRT a 90+ FPS.
- Yaw hacia la persona en `vuelo_evasion.py`. LiPo 4S sobredescargada: retirada.
- Simulación RL v1 a v5: del "dron esquiva" al "dron mantiene al ladrón a la vista" con operador humano.

## 6 de octubre
- LiDAR TF03 validado (driver `pl2303`). Gimbal de 2 ejes: lectura por USB, el control por serie no responde.
- Primera versión del repositorio y primer Pull Request (README).

## 5 de octubre
- Hardware configurado; arranca el Paso 1 de la hoja de ruta (validar el LiDAR).
