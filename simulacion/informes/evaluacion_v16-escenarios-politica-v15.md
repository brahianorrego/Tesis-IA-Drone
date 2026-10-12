# Evaluación en escenarios fijos · v16-escenarios-politica-v15

Modelo: `modelos/dron_politica.json`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-12 17:37

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| escape_muro | 0.98 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 59.6 | 0.66 | 1.60 | 1.60 | 16.3 | 2.9 | 4.7 | -45 / -0 | 133.7 | -0.4 | 0.68 | 1.02 | 1.52 |
| agachado_muro | 0.68 | 0.08 | 0.00 | 0.00 | 0.00 | 0.24 | 87.6 | 0.44 | 3.86 | 3.66 | 19.0 | 0.8 | 4.8 | -45 / -0 | 77.8 | -1.0 | 3.25 | 4.25 | 3.29 |
| gateo_muros | 0.00 | 0.02 | 0.00 | 0.00 | 0.00 | 0.98 | 119.8 | 0.28 | 11.94 | 11.46 | 9.6 | 0.2 | 4.9 | -45 / 12 | -6.1 | -0.8 | 7.90 | 7.37 | 6.57 |
| recostado_ataque | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 32.7 | 0.92 | 0.06 | 0.06 | 0.1 | 4.6 | 4.2 | -45 / 1 | 147.3 | -0.1 | 0.73 | 0.80 | 1.44 |
| salto_debajo | 0.78 | 0.22 | 0.00 | 0.00 | 0.00 | 0.00 | 60.5 | 0.55 | 2.34 | 2.12 | 5.4 | 0.7 | 5.4 | -45 / 2 | 89.4 | -0.1 | 2.14 | 4.83 | 2.98 |
| civiles_curiosos | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 34.1 | 0.92 | 0.50 | 0.52 | 0.5 | 2.2 | 4.6 | -45 / 1 | 146.0 | -0.1 | 2.90 | 2.35 | 3.70 |

V16 · vista por POSTURA del ladrón (fracción del tiempo a la vista en esa postura; entre paréntesis, fracción del tiempo en esa postura) y por ALTURA del dron (según su barómetro), punto ciego y cámara al piso:

| Escenario | De pie | Agachado | Recostado | Gateando | < 2.5 m | 2.5-3.25 m | ≥ 3.25 m | Punto ciego | Cám. piso |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| escape_muro | 0.63 (1.00) | -- | -- | -- | -- | 0.58 (0.03) | 0.63 (0.97) | 0.01 | 0.01 |
| agachado_muro | 0.96 (0.04) | 0.38 (0.96) | -- | -- | -- | 0.45 (0.02) | 0.40 (0.98) | 0.09 | 0.10 |
| gateo_muros | 0.96 (0.03) | 0.42 (0.08) | -- | 0.24 (0.89) | -- | 0.41 (0.03) | 0.27 (0.97) | 0.17 | 0.07 |
| recostado_ataque | 0.96 (0.10) | -- | 0.92 (0.90) | -- | -- | 0.93 (0.04) | 0.92 (0.96) | 0.02 | 0.00 |
| salto_debajo | 0.42 (1.00) | -- | -- | -- | -- | 0.62 (0.01) | 0.42 (0.99) | 0.25 | 0.30 |
| civiles_curiosos | 0.92 (1.00) | -- | -- | -- | -- | 0.93 (0.05) | 0.92 (0.95) | 0.11 | 0.03 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| escape_muro | 0.00 | 0.18 | 0.05 | 0.35 | 0.07 | 0.22 | 0.00 | 0.01 | 0.06 | 0.07 |
| agachado_muro | 0.00 | 0.26 | 0.04 | 0.17 | 0.05 | 0.23 | 0.00 | 0.02 | 0.17 | 0.06 |
| gateo_muros | 0.00 | 0.42 | 0.03 | 0.22 | 0.01 | 0.18 | 0.00 | 0.01 | 0.06 | 0.06 |
| recostado_ataque | 0.00 | 0.11 | 0.01 | 0.25 | 0.02 | 0.36 | 0.00 | 0.00 | 0.24 | 0.01 |
| salto_debajo | 0.00 | 0.11 | 0.01 | 0.28 | 0.09 | 0.37 | 0.00 | 0.00 | 0.12 | 0.02 |
| civiles_curiosos | 0.00 | 0.16 | 0.01 | 0.16 | 0.05 | 0.50 | 0.00 | 0.01 | 0.09 | 0.02 |
