# Evaluación en escenarios fijos · v16-escenarios-corrida-corta

Modelo: `../../../../tmp/claude-0/-home-user-Tesis-IA-Drone/a89b34d7-c9ff-557d-bb02-cd2ecd57498f/scratchpad/v16_corrida_corta.zip`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-12 17:36

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| escape_muro | 0.96 | 0.04 | 0.00 | 0.00 | 0.00 | 0.00 | 54.0 | 0.67 | 1.30 | 1.26 | 13.1 | 2.7 | 4.6 | -45 / 0 | 131.2 | -0.0 | 0.79 | 0.73 | 1.32 |
| agachado_muro | 0.62 | 0.06 | 0.00 | 0.00 | 0.00 | 0.32 | 89.1 | 0.43 | 3.26 | 3.02 | 21.6 | 0.7 | 4.7 | -45 / 1 | 72.7 | -0.1 | 2.98 | 3.66 | 3.14 |
| gateo_muros | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 120.0 | 0.23 | 9.92 | 9.40 | 11.5 | 0.3 | 5.1 | -45 / 1 | -7.4 | -0.1 | 7.61 | 6.31 | 6.33 |
| recostado_ataque | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 33.8 | 0.92 | 0.10 | 0.10 | 1.2 | 4.6 | 3.7 | -45 / 1 | 147.1 | 0.0 | 0.71 | 0.73 | 1.23 |
| salto_debajo | 0.82 | 0.18 | 0.00 | 0.00 | 0.00 | 0.00 | 56.1 | 0.59 | 2.86 | 2.68 | 3.5 | 0.6 | 5.1 | -45 / 7 | 99.8 | -0.0 | 2.01 | 3.62 | 3.38 |
| civiles_curiosos | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 33.6 | 0.92 | 0.46 | 0.48 | 0.6 | 2.1 | 4.4 | -45 / 1 | 146.4 | -0.0 | 3.15 | 2.12 | 3.51 |

V16 · vista por POSTURA del ladrón (fracción del tiempo a la vista en esa postura; entre paréntesis, fracción del tiempo en esa postura) y por ALTURA del dron (según su barómetro), punto ciego y cámara al piso:

| Escenario | De pie | Agachado | Recostado | Gateando | < 2.5 m | 2.5-3.25 m | ≥ 3.25 m | Punto ciego | Cám. piso |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| escape_muro | 0.63 (1.00) | -- | -- | -- | -- | 0.52 (0.03) | 0.64 (0.97) | 0.01 | 0.03 |
| agachado_muro | 0.96 (0.04) | 0.37 (0.96) | -- | -- | -- | 0.48 (0.02) | 0.39 (0.98) | 0.09 | 0.11 |
| gateo_muros | 0.96 (0.03) | 0.40 (0.08) | -- | 0.19 (0.89) | -- | 0.40 (0.02) | 0.22 (0.98) | 0.13 | 0.07 |
| recostado_ataque | 0.96 (0.10) | -- | 0.91 (0.90) | -- | -- | 0.93 (0.04) | 0.92 (0.96) | 0.02 | 0.00 |
| salto_debajo | 0.47 (1.00) | -- | -- | -- | -- | 0.57 (0.02) | 0.47 (0.98) | 0.28 | 0.26 |
| civiles_curiosos | 0.92 (1.00) | -- | -- | -- | -- | 0.92 (0.06) | 0.92 (0.94) | 0.09 | 0.02 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| escape_muro | 0.32 | 0.07 | 0.31 | 0.10 | 0.12 | 0.00 | 0.00 | 0.00 | 0.07 | 0.01 |
| agachado_muro | 0.29 | 0.11 | 0.24 | 0.06 | 0.06 | 0.02 | 0.00 | 0.00 | 0.18 | 0.04 |
| gateo_muros | 0.34 | 0.16 | 0.12 | 0.12 | 0.05 | 0.02 | 0.00 | 0.00 | 0.16 | 0.03 |
| recostado_ataque | 0.30 | 0.02 | 0.36 | 0.06 | 0.09 | 0.01 | 0.00 | 0.00 | 0.15 | 0.02 |
| salto_debajo | 0.35 | 0.05 | 0.28 | 0.07 | 0.09 | 0.04 | 0.00 | 0.00 | 0.10 | 0.01 |
| civiles_curiosos | 0.20 | 0.03 | 0.26 | 0.06 | 0.18 | 0.03 | 0.00 | 0.00 | 0.23 | 0.01 |
