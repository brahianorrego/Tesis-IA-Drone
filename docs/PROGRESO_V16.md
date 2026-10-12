# Progreso de la V16

Bitácora de las dos sesiones en la nube del plan `docs/PLAN_V16_REALISMO.md`. Cada fase cerrada deja aquí: fecha,
sesión, qué se hizo, números medidos y qué sigue.

## Sesión B · Visor (rama `v16-visor`)

### Cómo abrir el visor nuevo

- Windows: doble clic en `simulacion\ABRIR_VISOR.bat` (ahora usa `servidor_visor.py`, que entrega los `.js` con el tipo
  correcto; con `python -m http.server` en Windows los módulos de three.js a veces no cargan).
- Abre `http://127.0.0.1:8765/`. El visor técnico de la V15 sigue en `http://127.0.0.1:8765/index_v20.html`.
- Copia del visor anterior: `simulacion/index_v20.html` (el plan pedía `index_v19.html`, pero ese nombre ya era la copia
  previa a los ajustes C1-C3 de la V15; se usó el siguiente número libre para no borrarla).

### Contrato de `foto()` que usa el visor (provisional, mientras la sesión A publica el suyo)

El visor lee los campos de la V15 y, si vienen, los nuevos del plan (fase A5). Si la sesión A los define distinto, el
visor se adapta en `visor/datos.js` (un solo lugar).

| Campo | Dónde | Formato que espera el visor |
|---|---|---|
| `pos` | cada persona | 0 de pie, 1 agachado, 2 recostado de espalda contra la pared, 3 gateando |
| `pt` | cada persona | avance de la transición hacia `pos`, 0-1 (1 = postura completa) |
| `salto` | cada persona | `[fase, altura de la mano (m), avance de la fase 0-1]`; fase 0 nada, 1 impulso, 2 vuelo, 3 aterrizaje, 4 recuperación. Si falta el avance, el visor lo estima |
| `mira` | cada persona | ángulo (rad) hacia donde mira el cuerpo, igual que `psi` del dron (0 = +x, antihorario) |
| `civ` | cada persona | 0 transita, 1 mira el dron, 2 esquiva, 3 se va, 4 graba con el celular; `null` en el ladrón |
| `alt_obj` | cuadro | altura objetivo del dron (m) |
| `cam_piso` | cuadro | `[{"id": 3, "bb": [x0, y0, x1, y1] normalizados 0-1, "cf": 0.8}]` |
| `bat` | cuadro | batería (%). Propuesta del visor; si no viene, se estima por tiempo y se rotula "est." |
| `rinde` | persona o cuadro | el ladrón se rindió (el visor lo dibuja con las manos arriba) |

Las repeticiones de prueba con esos campos las genera `simulacion/herramientas/repeticion_prueba_v16.py` en
`simulacion/replays_prueba/` (coreografía escrita a mano, **no son partidas de la IA**). El selector del visor lista lo
que diga `replays_prueba/lista.json`; la sesión A puede agregar ahí sus repeticiones. Si `salida/estado.json` trae
`"replay_v16": "archivo.json"`, el visor lo muestra como "Misión V16 · en vivo".

### 2026-10-12 · Fase B1 · Motor gráfico y escena

**Qué se hizo**
- Visor nuevo modular en `simulacion/visor/` (`principal.js`, `escena.js`, `dron.js`, `datos.js`, `interfaz.js`,
  `personas.js`, `util.js`) con three.js **0.185.1** guardado en `simulacion/recursos/three/` (versión fija, funciona sin
  internet en el campo).
- Render físico (PBR), mapeo de tonos ACES, sombras con la caja de sombras siguiendo la acción, cielo HDRI con luz de
  ambiente (Poly Haven, CC0: "amanecer" y "mediodía"), niebla de distancia.
- Piso de pasto con variación de color a gran escala (no se nota la repetición), parches de tierra, muros de concreto de
  0.2 m con manchas de humedad, escurrimientos y suciedad al pie, franja de árboles fuera de la arena.
- Texturas propias (`herramientas/generar_texturas.py`, CC0): pasto, tierra, concreto de muro y de piso, con mapas de
  color, normales y rugosidad. Poly Haven, ambientCG, Kenney y Quaternius están bloqueados desde la nube; los cielos se
  tomaron de la copia que trae el repositorio de three.js. Licencias en `simulacion/recursos/LICENCIAS.md`.
- Dron del proyecto: marco de 450 mm, hélices, Pixhawk, Jetson, GPS, batería, **TF03 fijo al chasis** y gimbal de pitch con
  la cámara y el **TF-Luna** (sección 6 del plan). El visor limita el gimbal a −45°..+15° (regla dura 1).
- Distribución de estación de tierra: la cámara del dron en grande; a la derecha la vista externa (clic para
  intercambiar), la cámara al piso y el mapa; abajo la telemetría y el reproductor. Lo técnico en el panel
  "Ingeniería" (plegado).
- Cámara externa automática: se pone de lado respecto a la línea dron-sospechoso; también "Seguir", "Libre" y "Arriba".
- Calidad automática (alta / media / baja) según los cuadros por segundo, y contador en el panel de ingeniería.
- Pruebas nuevas: `tests/test_visor_v16.py` (recursos, módulos que se encuentran, servidor, contrato de la repetición y
  reglas duras en la repetición de prueba).

**Números**
- Pruebas: 96 pasan (1 omitida, como antes).
- Peso: recursos 7.6 MB (three.js 0.7 MB, cielos 3 MB, texturas 3.9 MB); repeticiones de prueba 0.9 MB.
- Cuadros por segundo: en la nube no hay tarjeta gráfica (render por software) y da ~1 cps, que no sirve como medida.
  **Pendiente que Brahian lo mida en el portátil**: panel "Ingeniería" → "Cuadros por segundo".

**Qué sigue:** B2, personas con esqueleto y animación (la figura actual es provisional).

### 2026-10-12 · Fase B2 · Personas con esqueleto y animación

**Qué se hizo**
- `visor/humano.js`: cada persona es una malla con piel (SkinnedMesh) sobre **21 huesos** (cadera, columna, pecho, cuello,
  cabeza, clavículas, brazos, antebrazos, manos, muslos, piernas, pies y dedos), con proporciones reales para 1.72 m y
  escalada a la estatura de cada persona (`est`). La piel se deforma suave en codos, rodillas y hombros (pesos
  automáticos por distancia a cada hueso).
- Ropa y piel según el ID (siempre la misma para la misma persona): tonos de piel trigueños, camisa de manga corta o
  larga, gorra, cuerpo más ancho o con barriga; el sospechoso con buzo oscuro y capucha.
- No se pudieron descargar modelos GLTF (Quaternius, Mixamo y Kenney están bloqueados desde la nube); por eso el cuerpo
  y **todas** las animaciones son procedurales sobre los huesos, como el plan permite para lo que no trae el paquete.
- Animación por **poses que se mezclan** (transiciones, no saltos de pose) y **cinemática inversa** de 2 huesos en
  brazos y piernas:
  - quieto (respira y cambia el peso de pierna), caminar, trotar y correr: los pies avanzan con la distancia recorrida,
    así en el apoyo quedan **quietos en el piso** (no patinan); el talón se levanta al despegar; la cadera sube y baja;
    los brazos van al contrario de las piernas y al correr el codo se dobla;
  - agachado y caminar agachado; gatear en cuatro patas (manos y rodillas en el piso, gateo cruzado);
  - recostado de espalda contra la pared con un pie apoyado en el muro, **asomándose** cada tanto hacia el borde más
    cercano del muro;
  - **salto para agarrar el dron**: impulso (se agacha con los brazos atrás y estalla), vuelo (brazo derecho estirado
    hacia el dron, cuerpo arqueado, piernas recogidas en el punto alto; la altura sale de la altura de la mano que da
    la simulación), aterrizaje (pies anclados, amortigua con las rodillas) y recuperación mirando el dron;
  - civiles: mirar el dron ("chismoseando": visera con la mano, brazos cruzados o manos en la cintura), **grabar con el
    celular** (aparece el teléfono en la mano), esquivar (se encoge y se cubre) y seguir caminando mirando de reojo;
  - rendirse: manos arriba a los lados de la cabeza.
- Cámara externa automática: plano de lado; **en el salto corta a un plano bajo y cercano con el sol a la espalda** y
  la repetición pasa a **cámara lenta** (0.3×, se puede apagar en Ingeniería); si un muro tapa al sospechoso, corta al
  otro lado.
- Galería de animaciones: `http://127.0.0.1:8765/visor/probador.html` muestra las 13 animaciones a la vez
  (`?i=8` solo el salto).

**Números**
- 96 pruebas pasan. Malla de ~7 000 vértices por persona.

**Qué sigue:** B3, la imagen de las cámaras como la del sensor real (distorsión, ruido, exposición, desenfoque), las cajas
de YOLO como en `jetson/visor_web.py` y el clic del operador.

### 2026-10-12 · Fase B3 · Cámaras reales e interfaz

**Qué se hizo**
- `visor/camaras.js`: cada cámara del dron se dibuja en una imagen de **640 × 480** (la resolución que recibe YOLO) y
  pasa por un revelado como el del sensor real: distorsión de barril del lente (sin bordes negros), aberración de color
  en los bordes, viñeteo, ruido del sensor (más en las sombras), **exposición automática lenta** como una webcam (si mira
  al cielo, el piso se oscurece) y **desenfoque por movimiento** según cuánto giró la cámara mientras el obturador
  estuvo abierto (1/60 s). La imagen se refresca a 30 cuadros por segundo, como la cámara real.
  - Principal: HFOV 38.9°, en el gimbal (−45° a +15°).
  - Al piso: IMX219, 62.2° × 48.8°, fija al chasis y recta hacia abajo (más distorsión y viñeteo, lente gran angular).
- **Cajas de YOLO como en `jetson/visor_web.py`**: rectángulo verde, `ID n  +x.x deg` (el ángulo respecto a la nariz
  calculado igual que en la Jetson) más la confianza; línea cian de la nariz; cuadros por segundo en rojo arriba a la
  izquierda. Las cajas salen de proyectar el esqueleto de cada persona con la misma distorsión del lente. La confianza
  baja agachado, recostado y gateando (o la que mande la simulación). La cámara al piso usa `cam_piso`.
- **Clic del operador**: en modo manual la repetición se detiene cuando hay que confirmar; la persona aparece con caja
  ámbar punteada "¿Es el sospechoso? clic aquí" y se confirma con un clic dentro de la caja (probado: espera en
  8.95 s, el clic confirma y la partida sigue).
- Interfaz limpia: en pantalla solo lo que verá el operador en vuelo (las dos cámaras, el mapa pequeño con lo que sabe
  el dron, modo, altura y altura objetivo, batería, velocidad, ángulo de la cámara, estado del objetivo y tiempo a la
  vista). Todo lo técnico (estado de la búsqueda, árbitro, personas, recompensas, bitácora) está en **Ingeniería**
  (tecla I), plegado por defecto. La vista externa es un recuadro que se agranda con un clic (o tecla V).

**Números**
- 96 pruebas pasan.

**Qué sigue:** B4, la vista previa de escenarios futuros (hangar y campo con árboles).

### 2026-10-12 · Fase B4 · Vista previa de escenarios futuros

**Qué se hizo**
- `visor/previa.js` y el selector **Escenario** de la barra superior:
  - **Hangar** (40 × 30 m, 9.5 m de alto): piso de concreto con franjas de pasillo, columnas de perfil I cada 8 m, vigas
    reticuladas, techo de lámina con claraboyas (entra el sol), portón abierto de 16 m, tres estanterías industriales con
    cajas, cajas sueltas y estibas para esconderse, y una oficina con puerta y ventana.
  - **Campo con árboles**: 46 árboles dentro de la arena con un claro en el centro, arbustos, piedras y un tronco caído.
- Rotulado **"VISTA PREVIA · NO ENTRENADO"** sobre la vista, con la explicación. La vista externa pasa a grande con la
  **cámara libre**: arrastrar para girar, rueda para acercar y teclas **W A S D** (Q/E bajar y subir) para recorrerlo.
- Cada escenario trae una escena de ejemplo (dron y personas con recorridos fijos: en el hangar el sospechoso agachado
  detrás de las cajas, un operario entre las estanterías, alguien recostado en una columna y otro grabando; en el campo
  el sospechoso gateando entre arbustos y civiles caminando o mirando el dron). Pasa por las mismas cámaras, cajas de
  YOLO e interfaz; la visibilidad se calcula con rayos contra el escenario (los árboles y las cajas tapan).
- Arreglos de paso: cajas falsas en la cámara al piso por puntos muy fuera de la imagen; copas de los árboles sin
  facetas.

**Números**
- 96 pruebas pasan.

## Resumen de la sesión B (fases B1-B4 cerradas)

- Abrir: `simulacion\ABRIR_VISOR.bat` → `http://127.0.0.1:8765/`. Galería de animaciones:
  `http://127.0.0.1:8765/visor/probador.html`. Visor técnico anterior: `index_v20.html`.
- **Pendiente de Brahian**: medir los cuadros por segundo en el portátil (Ingeniería → "Cuadros por segundo"; la calidad
  baja sola si no alcanza 26). En la nube no hay tarjeta gráfica y la medida no sirve.
- **Pendiente con la sesión A**: cuando publique su contrato de `foto()` en `v16-simulacion`, integrarlo con
  `git merge origin/v16-simulacion` y ajustar `visor/datos.js` si los campos cambian. Hasta hoy (2026-10-12) la rama
  `v16-simulacion` no existe en GitHub.
- Límites conocidos: el cuerpo de las personas es procedural (no se pudieron descargar modelos GLTF desde la nube); las
  caras son simples, pero a la distancia de la cámara del dron (3-15 m, 640 × 480) se leen como personas. Si más
  adelante se consigue un personaje GLTF CC0 con esqueleto, se puede cambiar la malla manteniendo la animación.
