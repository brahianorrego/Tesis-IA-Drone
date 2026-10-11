# V15 · Fase A · Sensores y mundo

Fecha: 2026-10-10. Plan: `docs/PLAN_V15_CURRICULO.md` (sección 4B, 4C, 4D, 4F-b, 4G y fase A de la sección 7).
Medido con el último modelo de la V14 (`dron_master_6999552_steps.zip`, 7.0 M pasos) **sin reentrenar**.

## Qué se hizo (`entorno.py`, `control.py` sin cambios)

| Cambio | Detalle |
|---|---|
| LiDAR TF03 | `LIDAR_MAX` 20 → **30 m**; **10 rayos por paso** (100 Hz) repartidos en el giro del paso, solo para los drones que giran (> 1°); el mapa ya no exige 3° entre impactos (los repetidos los filtra `D_DEDUP_LIDAR`) |
| 360° de entrada (D5) | El primero de la zona: **2.5 m, cámara −3°, una vuelta**. Guarda: alguien a < 6 m o acercándose > 1 m/s → sube rápido a la altura segura y termina la vuelta arriba (−8°) |
| 360° de búsqueda (D5) | `Z_GIRO` = altura segura (3.30 m), `GIMBAL_GIRO` = **−8°** (comparado con −15°: igual dentro del ruido; se deja −8°, que mapea muros de 5 a 23 m) |
| Cuerpo colombiano (D7) | Estatura de cada persona ~ N(1.72, 0.07) entre 1.58 y 1.88; alcance de pie 1.33 × estatura; salto 0.30-0.50 m; hombros 0.45 m. La Jetson sigue suponiendo 1.72 m para la distancia por bbox |
| Altura segura | p99 del alcance saltando + 0.3 m = **3.30 m** → `Z_ATAQUE`, `Z_FLANCO`, `Z_TRANSITO`, `Z_GIRO` |
| Cansancio | Velocidad crítica 3.0 m/s, reserva D′ 150 m, recuperación exponencial (τ 400 s); sin reserva solo trota (2.5 m/s), se esconde hasta el doble y ataca menos. Pulso: 70 + 30 de estrés + 18·v + 60·(1 − reserva), máx. 190, retardo 30 s, arranca en 100-110. El dron no lo observa |
| Muros con grosor | 0.2 m: tapan la vista con sus 4 caras y chocan a `RADIO_DRON + 0.1`; la guarda frena 0.1 m antes |
| Detección parcial | Muestras en **alto (8) y ancho (5 columnas)** con el perfil del cuerpo (piernas ±0.13, torso ±0.225, cabeza ±0.09 m); probabilidad = la de la persona entera × rampa de 5 % a 35 % visible |
| Velocidad | La oclusión solo se calcula para pares dron-persona en cámara (y el ladrón), con descarte rápido; `_ruta` solo arma el grafo si la recta cruza un muro |

## Hallazgo: el "muro de canto" (4F) con perspectiva
El plan supone que el ladrón detrás de la punta lejana sobresale ~0.12 m por cada lado. Con perspectiva desde 6 m de
la punta cercana, esa punta (0.2 m) tapa una franja que se ensancha: a 11.6 m tapa ±0.19 m, así que los hombros
(±0.225 m) asoman **~3 cm por lado**. Con el perfil del cuerpo el simulador lo detecta (prueba
`test_muro_de_canto_y_ancho_del_cuerpo`: ~15 % visible → detección probable, no segura). Para la fase D conviene
alejar algo más el punto de canto o subirlo para ganar margen.

## Números (192 entornos × 150 s por nivel, misma semilla, uno detrás del otro)

| Nivel (V14) | Cumplida V14 → V15-A | Perdido | Alcanzado | Panel | Peatón | Pasos/s V14 → V15-A |
|---|---|---|---|---|---|---|
| 0 Duelo abierto | 74 → 69 % | 16 → 19 % | 6 → 8 % | 0 → 0 % | 0 → 0 % | 7 655 → 9 015 |
| 1 Muro único | 93 → 92 % | 0 → 0 % | 2 → 3 % | 5 → 5 % | 0 → 0 % | 6 399 → 7 647 |
| 2 Ruido visual | 89 → 88 % | 0 → 0 % | 3 → 3 % | 6 → 7 % | 2 → 2 % | 5 634 → 7 260 |
| 3 Misión completa | 58 → 59 % | **10 → 4 %** | 20 → 22 % | 5 → 6 % | 5 → 8 % | 5 812 → 6 816 |

Perfil del paso (nivel 3, mismas acciones): V14 5.51 s, V15-A 5.52 s. La velocidad no cae (criterio: ≤ 30 %).
La caída en el nivel 0 viene del cuerpo real: un ladrón alto alcanza 2.3-2.5 m con el brazo y el dron persigue a 2.3 m
(`Z_NOMINAL`, fuera del alcance de la fase A). **Propuesta para la fase B:** con la distancia adaptativa de ~6 m deja de
importar; si no, revisar `Z_NOMINAL`.

Escenarios fijos (50 partidas, política determinista; `evaluacion_v15-ref-entorno-v14.md` vs `evaluacion_v15-fase-A.md`):

| Escenario | Cumplida V14 → V15-A | t re-adquisición |
|---|---|---|
| abierto | 100 → 100 % | — |
| cambio brusco | 100 → 98 % | 8.0 → 7.2 s |
| tras muro | 100 → 100 % | 10.2 → 10.3 s |
| debajo | 2 → 4 % | — |

## Criterios de aceptación de la fase A
- El 360° de entrada mapea muros a 25 m: **sí** (`test_360_de_entrada_mapea_un_muro_a_25_m`; la V14 llegaba a 20 m).
- Pruebas: **46 pasan** (8 nuevas en `tests/test_v15.py`; `test_v13.test_deteccion_parcial` se reescribió para la
  detección probabilística aprobada en el plan, sección G).
- Pasos/s no caen más de 30 %: **sí** (no caen).

---

## Anexo · salida de herramientas/evaluar_politica.py (entorno V15-A)

### Evaluación en escenarios fijos · v15-fase-A

Modelo: `..\..\..\..\AppData\Local\Temp\claude\C--Users-Brahi-Desktop-Claude\acb305c0-ec86-4acf-8f4d-4a0cb137aa56\scratchpad\v14_ultimo.zip`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-10 14:16

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 30.0 | 0.97 | 0.00 | 0.00 | -- | 4.7 | 2.7 | -44 / 6 | 13.5 | -0.7 | 2.96 | 0.88 | 4.65 |
| cambio_brusco | 0.98 | 0.00 | 0.02 | 0.00 | 0.00 | 0.00 | 38.1 | 0.74 | 1.30 | 1.28 | 7.2 | 0.9 | 4.2 | -45 / 3 | 14.0 | -0.3 | 0.86 | 0.53 | 2.45 |
| tras_muro | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 40.3 | 0.72 | 1.00 | 1.00 | 10.3 | 3.4 | 3.8 | -45 / 2 | 16.0 | -0.2 | 0.57 | 0.46 | 1.60 |
| debajo | 0.04 | 0.94 | 0.00 | 0.00 | 0.02 | 0.00 | 90.2 | 0.07 | 1.40 | 0.46 | 0.9 | 0.1 | 5.6 | -45 / -3 | -9.7 | -0.0 | 1.04 | 1.09 | 1.35 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 0.01 | 0.01 | 0.15 | 0.12 | 0.22 | 0.32 | 0.05 | 0.07 | 0.02 | 0.03 |
| cambio_brusco | 0.12 | 0.02 | 0.09 | 0.06 | 0.46 | 0.17 | 0.03 | 0.02 | 0.02 | 0.02 |
| tras_muro | 0.07 | 0.17 | 0.04 | 0.03 | 0.02 | 0.07 | 0.01 | 0.09 | 0.44 | 0.06 |
| debajo | 0.12 | 0.02 | 0.07 | 0.01 | 0.36 | 0.12 | 0.00 | 0.06 | 0.05 | 0.19 |
