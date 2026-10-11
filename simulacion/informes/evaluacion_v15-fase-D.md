# V15 · Fase D · Secuencia tras el muro (D2)

Fecha: 2026-10-10. Plan: `docs/PLAN_V15_CURRICULO.md` (sección 4F y fase D de la sección 7). Medido con el último
modelo de la V14 **sin reentrenar**. Búsqueda determinista (regla 3 intacta); la red no decide en estos estados.

## Qué se hizo (`entorno.py`, `herramientas/evaluar_politica.py`)

| Paso | Detalle |
|---|---|
| 1 · Lado proyectado | El flanqueo va detrás del muro por la esquina donde la nube proyecta al ladrón (fase B) y barre **180°** hacia la zona oculta (el giro empieza siempre hacia ese lado: prueba `test_sentido_del_giro_hacia_la_zona_oculta`) |
| 2 · Otro extremo | Si no está, flanqueo del **mismo muro por el extremo contrario** y otro barrido de 180° |
| 3 · Muro de canto | Estado nuevo **MURO_DE_CANTO** (10): punto en la prolongación del muro a `A_CANTO` = **8 m** de una punta (dentro de la arena; si se puede, con la ruta libre según la nube), a la altura segura, cámara ≈ −11° (encuadra el torso de la punta cercana a la lejana); se alinea a lo largo del muro (1.5 s) y hace **un solo barrido**: 20° a la derecha, 20° a la izquierda y al centro (30°/s) |
| 4 · 360° | Después, 360° de búsqueda y lo de siempre (siguiente obstáculo, altura táctica, misión perdida a los 90 s) |
| Interrupción | En cualquier paso, si YOLO lo ve → PERSECUCIÓN (V13) |

**Cambio respecto del plan:** `A_CANTO` = 8 m en vez de 6 m. El plan calcula 6 m como lo mínimo para que el cono cubra
2 m a cada lado del muro; con perspectiva, a 6 m la punta cercana (0.2 m) tapa ±0.19 m a la altura de la punta lejana
y al ladrón le asoman ~3 cm de hombro. A 8 m asoman ~6 cm y el cono sigue cubriendo más de 2 m (fase A).

Ajustes que hicieron falta para bajar el tiempo de re-adquisición (todos deterministas):
- **360° de búsqueda a −12°** (fase A dejó −8°): a −8° desde 3.3 m la cámara no ve a nadie a menos de ~4.4 m, justo donde
  queda el ladrón escondido visto desde el punto de flanqueo (los barridos de 180° no lo veían y el dron iba al otro extremo).
  Comparación tras el muro: −8° 9.7 s / 98 %, **−12° 9.4 s / 100 %**, −15° 10.9 s / 100 %.
- Vuelos de búsqueda: guiñada hasta 120°/s (antes 60°/s), avanza con ±20° de error (antes ±12°), velocidad 4.0 m/s
  (antes 3.0; la guarda del mapa frena cerca de los muros), altura con ganancia 2.0 (sube 1 m en ~0.7 s, no ~1.7 s).
- La PÉRDIDA respeta el bloqueo frontal del LiDAR cuando va hacia la nube (sin eso, el dron chocaba con el muro que
  tapaba al ladrón) y pasa directo al flanqueo si ≥ 60 % de la nube queda detrás de un muro conocido.
- Probado y **descartado**: avanzar mientras sube si no hay muros detectados a < 3 m (el muro todavía no agrupado en el
  mapa causó 8 % de choques).

## Escenarios fijos nuevos
- `detras_punta`: el ladrón corre detrás de un panel y se queda justo detrás de su punta lejana, en la línea del muro.
- `cambia_lado`: se esconde detrás de un panel y gatea por detrás hasta el otro extremo.

## Números (50 partidas por escenario, política determinista)

| Escenario | V14 (entorno) | Fase C | **Fase D** | t re-adquisición V14 → D |
|---|---|---|---|---|
| tras muro | 100 % | 100 % | **100 %** | 10.2 → **9.6 s** |
| detrás de la punta | — | 96 % | **98 %** (geocerca 2 %) | — → 9.1 s (fase C 12.1 s) |
| cambia de lado | — | 96 % | **100 %** | — → 8.1 s (fase C 10.8 s) |
| abierto | 100 % | 100 % | 100 % | — |
| cambio brusco | 100 % | 98 % | 98 % | — |
| debajo | 2 % | 66 % | 68 % | — |

Entorno de entrenamiento (192 entornos × 150 s): nivel 0 83 % (fase B 87 %), nivel 1 93 %, nivel 2 85 %, nivel 3 70 %.

## Criterio de aceptación de la fase D
- "Tras muro" ≥ la de hoy: **sí** (100 %).
- Menos tiempo de re-adquisición: **sí** (10.2 → 9.6 s; las fases B y C lo habían subido a ~11.7 s).
- El ladrón detrás de la punta se detecta: **sí** (98 %; prueba `test_muro_de_canto_y_ancho_del_cuerpo`).

## Pruebas
56 pasan. Nuevas (`TestFaseD`): sentido del giro hacia la zona oculta (con y sin nube), punto de canto en la
prolongación del muro mirando a lo largo, y la secuencia completa sin ladrón (lado → otro extremo → canto → 360°, sin
chocar).

**Prueba de reglas duras modificada (para que Brahian lo revise):** `test_secuencia_de_la_busqueda` agrega las
transiciones de la secuencia D2 (GIRO_360 → FLANQUEO por el otro extremo, GIRO_360 → MURO_DE_CANTO → GIRO_360) y
`test_humano_en_el_lazo` acepta MURO_DE_CANTO como estado de búsqueda desde el que se re-identifica al mismo objetivo.

---

## Anexo · salida de herramientas/evaluar_politica.py (entorno V15-D)

### Evaluación en escenarios fijos · v15-fase-D

Modelo: `..\..\..\..\AppData\Local\Temp\claude\C--Users-Brahi-Desktop-Claude\acb305c0-ec86-4acf-8f4d-4a0cb137aa56\scratchpad\v14_ultimo.zip`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-10 15:27

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 30.3 | 0.97 | 0.00 | 0.00 | -- | 4.8 | 2.8 | -45 / 8 | 13.7 | -0.7 | 2.83 | 0.96 | 4.50 |
| cambio_brusco | 0.98 | 0.00 | 0.02 | 0.00 | 0.00 | 0.00 | 31.5 | 0.89 | 2.08 | 2.06 | 0.8 | 1.4 | 5.1 | -45 / 5 | 13.8 | -0.2 | 1.41 | 1.65 | 2.93 |
| tras_muro | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 40.9 | 0.71 | 1.18 | 1.18 | 9.6 | 3.2 | 4.5 | -45 / 4 | 15.8 | -0.2 | 0.62 | 0.53 | 1.51 |
| detras_punta | 0.98 | 0.00 | 0.00 | 0.00 | 0.02 | 0.00 | 40.9 | 0.71 | 1.36 | 1.34 | 9.1 | 3.2 | 3.5 | -45 / 3 | 13.4 | -0.1 | 0.78 | 0.83 | 1.67 |
| cambia_lado | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 38.2 | 0.76 | 1.04 | 1.04 | 8.1 | 3.3 | 3.5 | -45 / 11 | 14.1 | -0.1 | 0.51 | 0.62 | 1.25 |
| debajo | 0.68 | 0.28 | 0.00 | 0.00 | 0.04 | 0.00 | 48.9 | 0.64 | 2.46 | 2.18 | 0.9 | 1.8 | 5.4 | -45 / -2 | 7.1 | -0.1 | 2.38 | 5.10 | 3.60 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 0.01 | 0.01 | 0.16 | 0.10 | 0.22 | 0.33 | 0.05 | 0.06 | 0.04 | 0.03 |
| cambio_brusco | 0.12 | 0.03 | 0.18 | 0.04 | 0.15 | 0.23 | 0.02 | 0.08 | 0.06 | 0.09 |
| tras_muro | 0.25 | 0.15 | 0.13 | 0.02 | 0.02 | 0.06 | 0.02 | 0.07 | 0.12 | 0.15 |
| detras_punta | 0.23 | 0.05 | 0.08 | 0.03 | 0.03 | 0.14 | 0.01 | 0.19 | 0.18 | 0.06 |
| cambia_lado | 0.07 | 0.14 | 0.07 | 0.02 | 0.32 | 0.11 | 0.00 | 0.08 | 0.09 | 0.09 |
| debajo | 0.15 | 0.02 | 0.08 | 0.01 | 0.08 | 0.15 | 0.00 | 0.11 | 0.15 | 0.25 |
