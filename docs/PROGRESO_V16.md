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
